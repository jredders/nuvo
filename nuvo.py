#from __future__ import absolute_import, division, print_function
import re, serial, time, logging, threading, sys

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
        self.asleep  = True
        self.ser          = serial.Serial()
        self.ser.port     = port
        self.ser.baudrate = 57600
        self.ser.timeout  = to
        self.rl      = threading.Thread(target=self.respLoop, daemon=True)
        self.sources = {k+1:{'enabled':False, 'name':None} for k in range(self.numSources)}
        self.zones   = {k+1:{'enabled':False, 'name':None, 'slaveto':None, 'power':None, 'source':None, 'volume':None, 'muted':None} for k in range(self.numZones)}

    def __enter__(self):
        logging.debug("enter...")
        self.open()
        return self
        
    def __exit__(self, type, value, traceback):
        logging.debug("exit...")
        self.ser.close()
        
    def open(self):
        self.ser.open()
        self.ser.flushInput()
        if self.commCheck() == True:
            logging.debug("open: commCheck Passed")
            self.rl.start()
            self.getSourceInfo()
            self.getZoneInfo()
            return True
        else:
            logging.warning("open: commCheck Failed")
            self.ser.close()
            return False
    
    def wakeNuvo(self):
        """Sends a CR and pauses 5 ms to wake up Novo"""
        logging.debug("wakeNuvo...")
        self.ser.write(b'\r')
        time.sleep(0.05)
        self.asleep = False
    
    def parseResponse(self, rsp):
        """Parses Nuvo response"""
        m = self.verre.match(rsp)
        if m:
            logging.debug("parseResponse: #VER match %s", rsp)
            if m.group('device') == 'NV-E6G':
                logging.debug("Nuvo E6G detected")
                return True
            else:
                logging.warning("Nuvo E6G not detected")
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
        
        logging.warning("parseResponse no match %s", rsp)
        return False

    def sendCommand(self, cmd):
        """Makes sure the Nuvo is awake and converts the cmd string to bytes and sends it"""
        if self.asleep == True:
            self.wakeNuvo()
        logging.debug("sendCommand: Sending *%s", cmd)
        self.ser.write(b'*' + bytes(cmd, 'ascii') + b'\r')
        # Limit Sends to once every 50 ms
        time.sleep(0.05)

    def respLoop(self):
        """Response parsing loop run in a separate thread"""
        logging.debug("respLoop: Thread starting...")
        while True:
            if self.ser.in_waiting:
                rsp = self.ser.readline().decode('ascii').rstrip()
                self.parseResponse(rsp)
            
            # Pause for 5 ms to let other threads do their thing
            time.sleep(0.005)
        
        logging.debug("respLoop: Thread ending...")
            
    def commCheck(self):
        """Checks for communication with the Nuvo by asking for the version"""
        logging.debug("commCheck...")
        self.sendCommand(f'VER')
        rsp = self.ser.readline().decode('ascii').rstrip()
        return self.parseResponse(rsp)
    
    def getSourceInfo(self):
        """Updates the sources dictionary based on the output of the SCFG command sent to all sources"""
        logging.debug("getSourceInfo...")
        for source in self.sources.keys():
            self.sendCommand(f'SCFG{source}STATUS?')

    def getZoneInfo(self):
        """Updates the zones dictionary based on the output of the ZCFG and ZON commands sent to all zones"""
        logging.debug("getZoneInfo...")
        for zone in self.zones.keys():
            self.sendCommand(f'ZCFG{zone}STATUS?')
            # Need Zone on to get most details
            self.sendCommand(f'Z{zone}ON')
        self.sendCommand(f'ALLOFF')

    def getSourceNames(self):
        """Returns a dictionary of Source#:SourceName pairs"""    
        logging.debug("getSourceNames...")
        return {k+1:self.sources[k+1]['name'] for k in range(self.numSources)}
    
    def getZoneNames(self):
        """Returns a dictionary of Zone#:Zone Name pairs"""
        logging.debug("getZoneNames...")
        return {k+1:self.zones[k+1]['name'] for k in range(self.numZones)}

    def status(self):
        """Returns a dictionary of all Zones"""
        zonelist = {}
        for zone in range(1, self.numZones+1):
            zonelist[zone] = {}
            zonelist[zone]['power'] = "on" if self.getPower(zone) == 1 else "off"
            zonelist[zone]['input'] = self.getSource(zone)
            zonelist[zone]['input_name'] = self.getSourceName(zone)
            zonelist[zone]['vol'] = self.getVol(zone)
            zonelist[zone]['mute'] = "on" if self.getMute(zone) == 1 else "off"
        return zonelist

    def zoneOutOfRange(self, zone):
        """Returns True and logs a warning if Zone is out of range"""
        if zone not in range(1, self.numZones+1):
            logging.warning("%s: Zone %s out of range", sys._getframe().f_back.f_code.co_name, zone)
            return True

    def sourceOutOfRange(self, source):
        """Returns True and logs a warning if Source is out of range"""
        if source not in range(1, self.numSources+1):
            logging.warning("%s: Source %s out of range", sys._getframe().f_back.f_code.co_name, source)
            return True

    def getSourceName(self, zone):
        """Returns Zone's source name"""
        if self.zoneOutOfRange(zone):
            return
        return self.sources[self.getSource(zone)]['name']
        
    def getZoneName(self, zone):
        """Returns Zone's name"""
        if self.zoneOutOfRange(zone):
            return
        return self.zones[zone]['name']

    def getZoneSlave(self, zone):
        """Returns the slaved Zone if it exists or None"""
        if self.zoneOutOfRange(zone):
            return
        return self.zones[zone]['slaveto']

    def getCmdZone(self, zone):
        """Returns the Zone where the command needs to be sent"""
        if self.zoneOutOfRange(zone):
            return
        if self.getZoneSlave(zone):
            return self.getZoneSlave(zone)
        else:
            return zone
        
    def printZone(self, zone):
        """Prints dictionary of Zone and if slaved, the zone it's slaved to"""
        if self.zoneOutOfRange(zone):
            return
        name    = self.getZoneName(zone)
        slvnum  = self.getZoneSlave(zone)
        slvname = self.getZoneName(slvnum) if slvnum else ""
        slaved  = f"-> {slvnum:2}:{slvname}" if slvnum else ""
        power   = "ON" if self.getPower(zone) == 1 else "OFF"
        srcnum  = self.getSource(zone)
        srcname = self.getSourceName(zone)
        source  = f"{srcnum}:{srcname}"
        volnum  = self.getVol(zone)
        volume  = "MUTED" if self.getMute(zone) == 1 else f"{volnum:5}"
        print(f"{zone:2}:{name:20} {power:3} {volume} {source} {slaved}")

    def queryZone(self, zone):
        """Commands the Nuvo to refresh Zone's status"""
        if self.zoneOutOfRange(zone):
            return
        self.sendCommand(f'Z{zone}STATUS?')

    def getPower(self, zone):
        """Returnes the Zone's power status 1/0"""
        if self.zoneOutOfRange(zone):
            return
        zone = self.getCmdZone(zone)
        if self.zones[zone]['power'] == 'ON':
            return 1
        else:
            return 0

    def setPower(self, zone, power):
        """"Commands the Nuvo to set the Zone's power status"""
        if self.zoneOutOfRange(zone):
            return
        if power not in [0, 1]:
            logging.warning("setPower: Power %s is invalid", power)
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
        if self.zoneOutOfRange(zone):
            return
        zone = self.getCmdZone(zone)
        return self.zones[zone]['source']

    def setSource(self, zone, source):
        """Commands Nuvo to set the Zone's source"""
        if self.zoneOutOfRange(zone):
            return
        if self.sourceOutOfRange(source):
            return
        zone = self.getCmdZone(zone)
        self.sendCommand(f'Z{zone}SRC{source}')

    def getVol(self, zone):
        """Returns the Zone's volume"""
        if self.zoneOutOfRange(zone):
            return
        zone = self.getCmdZone(zone)
        return self.zones[zone]['volume']

    def setVol(self, zone, volume):
        """Commands the Nuvo to set the Zone's volume"""
        if self.zoneOutOfRange(zone):
            return
        if volume not in range(0, 80):
            logging.warning("setVol: Volume %s out of range", volume)
            return
        zone = self.getCmdZone(zone)
        volume = 79 - volume
        self.sendCommand(f'Z{zone}VOL{volume}')

    def volUp(self, zone):
        """Commands the Nuvo to increase the Zone's volume"""
        if self.zoneOutOfRange(zone):
            return
        zone = self.getCmdZone(zone)
        self.sendCommand(f'Z{zone}VOL+')

    def volDown(self, zone):
        """Commands the Nuvo to decrease the Zone's volume"""
        if self.zoneOutOfRange(zone):
            return
        zone = self.getCmdZone(zone)
        self.sendCommand(f'Z{zone}VOL-')

    def getMute(self, zone):
        """Returns the Zone's muted status 1/0"""
        if self.zoneOutOfRange(zone):
            return
        zone = self.getCmdZone(zone)
        if self.zones[zone]['muted']:
            return 1
        else:
            return 0

    def setMute(self, zone, mute):
        """Commands the Nuvo to set the Zone's muted status"""
        if self.zoneOutOfRange(zone):
            return
        if mute not in [0,1]:
            logging.warning("setMute: Mute %s is invalid", mute)
            return
        zone = self.getCmdZone(zone)
        if mute == 1:
            self.sendCommand(f'Z{zone}MUTEON')
        else:
            self.sendCommand(f'Z{zone}MUTEOFF')
        
    def toggleMute(self, zone):
        """Commands the Nuvo to toggle the Zone's muted status"""
        if self.zoneOutOfRange(zone):
            return
        zone = self.getCmdZone(zone)
        self.sendCommand(f'Z{zone}MUTE')
