from __future__ import absolute_import, division, print_function
import serial, time, logging

class NUVO:
    
    numSources = 6
    numZones   = 12
    
    def __init__(self, device, to = 1):
        logging.debug("Nuvo: Init...")
        self.device = device
        self.to = to
        self.sources = {k+1:{'enabled':False, 'name':None} for k in range(numSources)}
        self.zones   = {k+1:{'enabled':False, 'name':None, 'power':None, 'source':None, 'volume':None, 'muted':None, 'dnd':None, 'locked':None} for k in range(numZones)}

    def __enter__(self):
        logging.debug("Nuvo: Enter...")
        self.open()
        return self
        
    def __exit__(self, type, value, traceback):
        logging.debug("Nuvo: Exit...")
        self.ser.close()
        
    def open(self):
        self.ser = serial.Serial(port = self.device, baudrate = 57600, timeout = self.to)
        self.ser.flushInput()
        if self.commCheck() == True:
            self.getZoneInfo(self)
            self.getSourceInfo(self)
            return True
        else:
            return False
        
    def commCheck(self):
        # Send 33 CRs to make sure Novo is awake
        self.ser.write(b'\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r\r')
        # Send *VER command
        self.ser.write(b'*VER\r')
        rsp = self.ser.readline.decode("utf-8")
        if len(rsp) == 25 and rsp == '#VER"NV-E6G FWv2.66 HWv0"':
            logging.debug("commCheck: Nuvo E6G detected. Received: %s", str(rsp))
            return True
        else:
            logging.warning("commCheck: Nuvo E6G not detected. Received %s", str(rsp))
            return False
    
    def getZoneNames(self):
        self.getZoneInfo(self)
        return {k+1:self.zones[k+1]["name"] for k in range(numZones)}

    def getZoneNames(self)
        self.getSourceInfo(self)
        return {k+1:self.soures[k+1]["name"] for k in range(numSources)}
    
    def getZoneInfo(self):
        for zone in self.zones.keys():
          self.sendCommand(b'*Z{zone}STATUS?\r')
        
    def getSourceInfo(self):
        for source in self.sources.keys():
          self.sendCommand(b'*SCFG{source}STATUS?\r')
        
    def printZone(self, zone):
        logging.debug("Zone: %s", zone)
        logging.debug("Enabled: %s", self.zones[zone]["enabled"])
        logging.debug("Name: %s", self.zones[zone]['name'])
        logging.debug("Source: %s: %s", self.zones[zone]['source'], self.sources[self.zones[zone]['source']]['name'])
        logging.debug("Volume: %s", self.zones[zone]['volume'])
        logging.debug("Muted: %s", self.zones[zone]['muted'])
        logging.debug("DND: %s", self.zones[zone]['dnd'])
        logging.debug("Locked: %s", self.zones[zone]['locked'])        

    def sendCommand(self, cmd):
        self.ser.write(cmd)
        self.getReply() 

    def getReply(self):
        msg_count = 0
        time.sleep(0.05)
        while self.ser.inWaiting() > 0:
            reply = bytearray(self.ser.readline.decode("utf-8"))    
            if len(reply) == 0:
                break
                
            msg_count = msg_count + 1
            self.parseReply(reply)

        return msg_count

    def parseReply(self, message):
        zone = message[2]
        self.zones[zone]['power'] = "on" if (message[4] & 1<<7)>>7 else "off"
        self.zones[zone]['source'] = message[8]+1
        self.zones[zone]['volume'] = message[9]-195 if message[9] else 0
        self.zones[zone]['muted'] = "on" if (message[4] & 1<<6)>>6 else "off"

    def setSource(self, zone, source):
        if zone not in range(1, numZones):
            logging.warning("Invalid Zone")
            return
        if source not in range(1, numSources):
            logging.warning("invalid Source")
            return
        self.sendCommand(b'*Z{zone}SRC{source}\r')
    
    def volUp(self, zone):
        if zone not in range(1, numZones):
            logging.warning("Invalid Zone")
            return    
        self.sendCommand(b'*Z{zone}VOL+\r')

    def volDwn(self, zone):
        if zone not in range(1, numZones):
            logging.warning("Invalid Zone")
            return    
        self.sendCommand(b'*Z{zone}VOL-\r')

    def setVol(self, zone, volume):
        if volume not in range(0, 79):
            logging.warning("Invald Volume")
            return
        self.sendCommand(b'Z{zone}VOL{volume}\r')

    def setMute(self, zone, mute):
        if zone not in range(1, numZones):
            logging.warning("Invalid Zone")
            return
        if mute not in [0,1]:
            logging.warning("Invalid Mute")
            return
        if mute == 0:
            self.sendCommand(b'*Z{zone}MUTEOFF\r')
        else:
            self.sendCommand(b'*Z{zone}MUTEON\r')

    def toggleMute(self, zone):
        if zone not in range(1, numZones):
            logging.warning("Invalid Zone")
            return    
        self.sendCommand(b'*Z{zone}MUTE\r')

    def queryZone(self, zone):
        if zone not in range(1, numZones):
            logging.warning("Invalid Zone")
            return
        self.sendCommand(b'*Z{zone}STATUS?\r')

    def setPower(self, zone, power):
        if zone not in range(1, numZones):
            logging.warning("Invalid Zone")
            return
        if power not in [0, 1]:
            logging.warning("Invalid Power")
            return
        if power == 0:
            self.sendCommand(b'*Z{zone}OFF\r')
        else:
            self.sendCommand(b'*Z{zone}ON\r')

    def status(self):
        return self.zones
