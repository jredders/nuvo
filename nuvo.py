import re, serial, time, logging, sys

class Nuvo:
    
    numSources = 6
    numZones = 12

    #VER"DEV FWvx.xx HWvx"
    verre = re.compile(r'#VER"(?P<device>[A-Za-z0-9-]+) '
                       r'FWv(?P<fw>[0-9.]+) '
                       r'HWv(?P<hw>[0-9]+)"')

    #ALLOFF
    alloffre = re.compile(r'#ALLOFF')
    
    #SCFGx,ENABLE0
    #SCFGx,ENABLE1,NAME"Source Name",GAINx,NUVONETx,SHORTNAME"XYZ"
    scfgre = re.compile(r'#SCFG(?P<source>[1-6]),'
                        r'ENABLE(?P<enabled>[01])(?:,'
                        r'NAME"(?P<name>[A-Za-z0-9\'_ ]+)",'
                        r'GAIN(?P<gain>[0-9]+),'
                        r'NUVONET(?P<nuvonet>[01]),'
                        r'SHORTNAME"(?P<shortname>[A-Z]+)"|)')

    #ZCFGx,ENABLE0
    #ZCFGx,ENABLE1,NAME"Zone Name",SLAVETOx,GROUPx,SOURCESx,XSRCx,IRx,DNDx,LOCKEDx
    zcfgre = re.compile(r'#ZCFG(?P<zone>[0-9]+),'
                        r'ENABLE(?P<enabled>[01])(?:,'
                        r'NAME"(?P<name>[A-Za-z0-9\'_ ]+)",'
                        r'SLAVETO(?P<slaveto>[0-9]+),'
                        r'GROUP(?P<group>[0-9]+),'
                        r'SOURCES(?P<sources>[0-9]+),'
                        r'XSRC(?P<xsrc>[01]),'
                        r'IR(?P<ir>[012]),'
                        r'DND(?P<dnd>[0-7]),'
                        r'LOCKED(?P<locked>[01])|)')
    #Zx,OFF
    #Zx,ON,SRCx,VOLx,DNDx,LOCKx
    zre = re.compile(r'#Z(?P<zone>[0-9]+),'
                     r'(?P<power>ON|OFF)(?:,'
                     r'SRC(?P<source>[1-6]),'
                     r'(?:VOL|)(?P<volume>(?:[0-9]+|MUTE)),'
                     r'DND(?P<dnd>[01]),'
                     r'LOCK(?P<locked>[01])|)')

    def __init__(self, port, to = 1):
        logging.debug("init...")
        self.asleep       = True
        self.ser          = serial.Serial()
        self.ser.port     = port
        self.ser.baudrate = 57600
        self.ser.timeout  = to
        self.sources      = {k+1:{'enabled':False, 'name':None} for k in range(self.numSources)}
        self.zones        = {k+1:{'enabled':False, 'name':None, 'slaveto':None, 'power':None, 'source':None, 'volume':None, 'muted':None} for k in range(self.numZones)}
        self.zonelist     = {k+1:{'power':None, 'input':None, 'input_name':None, 'vol':None, 'mute':None} for k in range(self.numZones)}

    def __enter__(self):
        logging.debug("enter...")
        self.open()
        return self
        
    def __exit__(self, type, value, traceback):
        logging.debug("exit...")
        self.ser.close()
        
    def open(self):
        """Opens serial port, and updates status of all Sources and Zones"""
        logging.debug("open...")
        self.ser.open()
        self.ser.flushInput()
        if self.sendCommand(f'VER') == True:
            self.getStatus()
            return True
        else:
            self.ser.close()
            return False
    
    def sendCommand(self, cmd):
        """Handles actually sending the command and parsing the response"""
        # Parse all waiting messages
        while self.ser.in_waiting:
            logging.debug("sendCommand: Parsing waiting message")
            self.parseResponse()
        
        # Wake up Nuvo if needed    
        if self.asleep == True:
            logging.debug("sendCommand: Waking Nuvo...")
            self.ser.write(b'\r')
            time.sleep(0.05)
            self.asleep = False

        # Send Command to Nuvo
        logging.debug("sendCommand: Sending *%s", cmd)
        self.ser.write(b'*' + bytes(cmd, 'ascii') + b'\r')
        
        # Parse response from Nuvo
        return self.parseResponse()

    def parseResponse(self):
        """Parses Nuvo response"""
        # Read line from serial
        rsp = self.ser.readline().decode('ascii').rstrip()

        # Parse it
        m = self.verre.match(rsp)
        if m:
            logging.debug("parseResponse: #VER match %s", rsp)
            if m.group('device') == 'NV-E6G':
                logging.debug("parseRespones: Device is Nuvo E6G")
                return True
            else:
                logging.error("parseResponse: Device is not Nuvo E6G")
                return False

        m = self.alloffre.match(rsp)
        if m:
            logging.debug("parseResponse: #ALLOFF match %s", rsp)
            for zone in self.zones.keys():
                self.zones[zone]['power'] = 'OFF'
            self.asleep = True
            return True
        
        m = self.zre.match(rsp)
        if m:
            logging.debug("parseResponse: #Z match %s", rsp)
            zone = int(m.group('zone'))
            self.zones[zone]['power'] = m.group('power')
            if m.group('power') == 'ON':
                self.zones[zone]['source'] = int(m.group('source'))
                if m.group('volume') == 'MUTE':
                    self.zones[zone]['muted'] = True
                else:
                    self.zones[zone]['volume'] = 79 - int(m.group('volume'))
                    self.zones[zone]['muted'] = False
            return True
        
        m = self.scfgre.match(rsp)
        if m:
            logging.debug("parseResponse: #SCFG match %s", rsp)
            source = int(m.group('source'))
            if m.group('enabled') == '1':
                self.sources[source]['enabled'] = True
            else:
                self.sources[source]['enabled'] = False
            self.sources[source]['name'] = m.group('name')
            return True

        m = self.zcfgre.match(rsp)
        if m:
            logging.debug("parseResponse: #ZCFG match %s", rsp)
            zone = int(m.group('zone'))
            if m.group('enabled') == '1':
                self.zones[zone]['enabled'] = True
            else:
                self.zones[zone]['enabled'] = False
            self.zones[zone]['name'] = m.group('name')
            if m.group('slaveto') != '0':
                self.zones[zone]['slaveto'] = int(m.group('slaveto'))
            return True
        
        logging.warning("parseResponse: No match %s", rsp)
        return False

    def getStatus(self):
        """Asks the Nuvo for status of all the Sources and Zones"""
        logging.debug("getStatus...")
        for source in self.sources.keys():
            self.sendCommand(f'SCFG{source}STATUS?')
        for zone in self.zones.keys():
            self.sendCommand(f'ZCFG{zone}STATUS?')
            self.sendCommand(f'Z{zone}STATUS?')
            if self.getPower(zone) == 0:
              # Zone needs to be turned on to get most of it's status
              self.sendCommand(f'Z{zone}ON')
              time.sleep(0.5)
              self.sendCommand(f'Z{zone}OFF')

    def getSourceNames(self):
        """Returns a dictionary of Source#:SourceName pairs"""    
        logging.debug("getSourceNames...")
        return {k+1:self.sources[k+1]['name'] for k in range(self.numSources)}
    
    def getZoneNames(self):
        """Returns a dictionary of Zone#:Zone Name pairs"""
        logging.debug("getZoneNames...")
        return {k+1:self.zones[k+1]['name'] for k in range(self.numZones)}

    def status(self):
        """Returns a dictionary of status for all Zones"""
        for zone in self.zones.keys():
            self.zonelist[zone]['power']      = "on" if self.getPower(zone) == 1 else "off"
            self.zonelist[zone]['input']      = self.getSource(zone)
            self.zonelist[zone]['input_name'] = self.getSourceName(zone)
            self.zonelist[zone]['vol']        = self.getVol(zone)
            self.zonelist[zone]['mute']       = "on" if self.getMute(zone) == 1 else "off"
        return self.zonelist

    def zoneInvalid(self, zone):
        """Returns True and logs a warning if Zone is not valid"""
        if zone not in self.zones.keys():
            logging.warning("%s: Zone %s invalid", sys._getframe().f_back.f_code.co_name, zone)
            return True
        else:
            return False

    def sourceInvalid(self, source):
        """Returns True and logs a warning if Source is not valid"""
        if source not in self.sources.keys():
            logging.warning("%s: Source %s invalid", sys._getframe().f_back.f_code.co_name, source)
            return True
        else:
            return False

    def powerInvalid(self, power):
        """Returns True and logs a warning if Power is not valid"""
        if power not in range [0, 1]:
            logging.warning("%s: Power %s invalid", sys._getframe().f_back.f_code.co_name, power)
            return True
        else:
            return False
    
    def volumeInvalid(self, volume):
        """Returns True and logs a warning if Volume is not valid"""
        if volume not in range(0, 80):
            logging.warning("%s: Volume %s invalid", sys._getframe().f_back.f_code.co_name, volume)
            return True
        else:
            return False
        
    def muteInvalid(self, mute):
        """Returns True and logs a warning if Mute is not valid"""
        if mute not in range [0, 1]:
            logging.warning("%s: Mute %s invalid", sys._getframe().f_back.f_code.co_name, mute)
            return True
        else:
            return False

    def getSourceName(self, zone):
        """Returns Zone's source name"""
        if self.zoneInvalid(zone):
            return ""
        if self.getSource(zone) != None:
            return self.sources[self.getSource(zone)]['name']
        else:
            return ""
        
    def getZoneName(self, zone):
        """Returns Zone's name"""
        if self.zoneInvalid(zone):
            return ""
        return self.zones[zone]['name']

    def getZoneSlave(self, zone):
        """Returns the slaved Zone if it exists or None"""
        if self.zoneInvalid(zone):
            return None
        return self.zones[zone]['slaveto']

    def getCmdZone(self, zone):
        """Returns the Zone where the command needs to be sent"""
        if self.zoneInvalid(zone):
            return None
        if self.getZoneSlave(zone):
            return self.getZoneSlave(zone)
        else:
            return zone
        
    def printZone(self, zone):
        """Prints a nicely formatted line about the Zone"""
        if self.zoneInvalid(zone):
            return
        name = self.getZoneName(zone)
        if self.getPower(zone) == 1:
            volume  = "MUTED" if self.getMute(zone) == 1 else f" {self.getVol(zone):2}  "
            source  = f"{self.getSource(zone)}:{self.getSourceName(zone)}"
            slvnum  = self.getZoneSlave(zone)
            slvname = self.getZoneName(slvnum) if slvnum else ""
            slaved  = f"-> {slvnum:2}:{slvname}" if slvnum else ""
            print(f"{zone:2}:{name:20} ON  {volume} {source} {slaved}")
        else:
            print(f"{zone:2}:{name:20} OFF")

    def queryZone(self, zone):
        """Commands the Nuvo to refresh Zone's status"""
        if self.zoneInvalid(zone):
            return
        self.sendCommand(f'Z{zone}STATUS?')

    def getPower(self, zone):
        """Returnes the Zone's power status 1/0"""
        if self.zoneInvalid(zone):
            return None
        zone = self.getCmdZone(zone)
        if self.zones[zone]['power'] == 'ON':
            return 1
        else:
            return 0

    def setPower(self, zone, power):
        """"Commands the Nuvo to set the Zone's power status"""
        if self.zoneInvalid(zone):
            return
        if self.powerInvalid(power):
            return
        zone = self.getCmdZone(zone)
        if power == 1:
            self.sendCommand(f'Z{zone}ON')
        else:
            self.sendCommand(f'Z{zone}OFF')

    def allOff(self):
        """Command Nuvo to turn off all Zones"""
        self.sendCommand(f'ALLOFF')

    def getSource(self, zone):
        """Returns Zone's source"""
        if self.zoneInvalid(zone):
            return None
        zone = self.getCmdZone(zone)
        return self.zones[zone]['source']

    def setSource(self, zone, source):
        """Commands Nuvo to set the Zone's source"""
        if self.zoneInvalid(zone):
            return
        if self.sourceInvalid(source):
            return
        zone = self.getCmdZone(zone)
        self.sendCommand(f'Z{zone}SRC{source}')

    def getVol(self, zone):
        """Returns the Zone's volume"""
        if self.zoneInvalid(zone):
            return None
        zone = self.getCmdZone(zone)
        return self.zones[zone]['volume']

    def setVol(self, zone, volume):
        """Commands the Nuvo to set the Zone's volume"""
        if self.zoneInvalid(zone):
            return
        if self.volumeInvalid(zone):
            return
        zone = self.getCmdZone(zone)
        # Convert to Nuvo's 0 = Max, 79 = Min format
        volume = 79 - volume
        self.sendCommand(f'Z{zone}VOL{volume}')

    def volUp(self, zone):
        """Commands the Nuvo to increase the Zone's volume"""
        if self.zoneInvalid(zone):
            return
        zone = self.getCmdZone(zone)
        self.sendCommand(f'Z{zone}VOL+')

    def volDown(self, zone):
        """Commands the Nuvo to decrease the Zone's volume"""
        if self.zoneInvalid(zone):
            return
        zone = self.getCmdZone(zone)
        self.sendCommand(f'Z{zone}VOL-')

    def getMute(self, zone):
        """Returns the Zone's muted status 1/0"""
        if self.zoneInvalid(zone):
            return None
        zone = self.getCmdZone(zone)
        if self.zones[zone]['muted']:
            return 1
        else:
            return 0

    def setMute(self, zone, mute):
        """Commands the Nuvo to set the Zone's muted status"""
        if self.zoneInvalid(zone):
            return
        if self.muteInvalid(zone):
            return
        zone = self.getCmdZone(zone)
        if mute == 1:
            self.sendCommand(f'Z{zone}MUTEON')
        else:
            self.sendCommand(f'Z{zone}MUTEOFF')
        
    def toggleMute(self, zone):
        """Commands the Nuvo to toggle the Zone's muted status"""
        if self.zoneInvalid(zone):
            return
        zone = self.getCmdZone(zone)
        self.sendCommand(f'Z{zone}MUTE')
