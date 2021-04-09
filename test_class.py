#!/usr/bin/python3
import logging, nuvo, time

logfile = 'test.log'
serial_port = '/dev/ttyUSB0'

# set up logger
logging.basicConfig(filename=logfile,level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# Get the Nuvo object
nv = nuvo.Nuvo(serial_port)

# Open the Nuvo
logging.info("Opening Nuvo at %s", serial_port)
while nv.open() is False:
    logging.warning("Could not open Nuvo - is it on? Retrying in 15s...")
    time.sleep(15)

# Test out functions
print(nv.getSourceNames())
print(nv.getZoneNames())
print(nv.status())
time.sleep(20)

# Run through functions on 3 Zones: 3 = Normal, 11 = Slaved, 69 = Invalid
for zone in [3, 11, 69]:
    print(f"\n\nZone {zone}:{nv.getZoneName(zone)}")
    nv.queryZone(zone)
    print(f"Power = {nv.getPower(zone)}")
    print(f"Turning on Zone")
    nv.setPower(zone, 1)
    nv.printZone(zone)

    origsource = nv.getSource(zone)
    print(f"\nSource = {nv.getSource(zone)}")
    print(f"Setting Source to 1:MediaCenter")
    nv.setSource(zone, 1)
    nv.printZone(zone)
    
    print(f"\nRestoring Source")
    nv.setSource(zone, origsource)
    nv.printZone(zone)

    origvol = nv.getVol(zone)
    print(f"\nVolume = {nv.getVol(zone)}")
    print(f"Setting Volume to 50")
    nv.setVol(zone, 50)
    nv.printZone(zone)
    
    print(f"\nVolume+")
    nv.volUp(zone)
    nv.printZone(zone)

    print(f"\nVolume-")
    nv.volDown(zone)
    nv.printZone(zone)
    
    print(f"\nRestoring Volume")
    nv.setVol(zone, origvol)
    nv.printZone(zone)

    print(f"\nMute = {nv.getMute(zone)}")
    print(f"Muting")
    nv.setMute(zone, 1)
    nv.printZone(zone)

    print(f"Unuting")
    nv.setMute(zone, 0)
    nv.printZone(zone)

    print(f"Toggline Mute")
    nv.toggleMute(zone)
    nv.printZone(zone)

    print(f"Toggline Mute")
    nv.toggleMute(zone)
    nv.printZone(zone)
    
    print("Turning off Zone")
    nv.setPower(zone, 0)
    nv.printZone(zone)
    
# Put in an endless loop to check that updates from Zones are handled properly
while True:
    print("\033[2J")
    nv.queryZone(1)
    for zone in range(1, nv.numZones+1):
        nv.printZone(zone)
    time.sleep(1)
