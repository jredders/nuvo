#!/usr/bin/python3
import logging, nuvo, web, time, json

logfile = 'server.log'
serial_port = '/dev/ttyUSB0'

# set up logger
logging.basicConfig(filename=logfile,level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# get the Nuvo object
nv = nuvo.Nuvo(serial_port)

# Open the Nuvo
logging.info("Opening Nuvo at %s", serial_port)
while nv.open() is False:
    logging.warning("Could not open Nuvo - is it on? Retrying in 15s...")
    time.sleep(15)

# define list of commands we handle
commands = ['alloff','pwr','volup','voldwn','setvol','setinput','togglemute','status','getzonelabels']
            
# urls for the web app
urls = (
    '/', 'index',
    '/nuvo', 'controller'
)

# respond to /
class index:
    def GET(self):
        return "Nuvo Home Audio System Controller"

# respond to /nuvo
class controller:

    def GET(self):
        # we're going to return JSON
        web.header('Content-Type', 'application/json')
        # Grab the arguements from the URL
        user_data = web.input()
        logging.debug("user_data = %s", user_data)

        # do some input validation
        if 'command' in user_data:
            command = user_data.command.lower()
            if command in commands: 
                zone = int(user_data.zone) if 'zone' in user_data else None
                value = int(user_data.value) if 'value' in user_data else None
                if zone is not None:
                    if value is not None:
                        logging.info("Processing %s zone %s %s", command, zone, value)
                    else:
                        logging.info("Processing %s zone %s", command, zone)
                else:
                    logging.info("Processing %s", command)

                # Process the commnads
                if command == "status":
                    if zone is not None:
                        nv.queryZone(zone)
                    else:
                        logging.error("Zone not specified for status.")
                elif command == "alloff":
                    nv.allOff()
                elif command == "pwr":
                    if zone and value is not None:
                        nv.setPower(zone, value)
                    else:
                        logging.error("Zone or Value not specified for pwr: zone: %s, value: %s", zone, value)
                elif command == "volup":
                    if zone is not None:
                        nv.volUp(zone)
                    else:
                        logging.error("Zone not specified for volup.")
                elif command == "voldwn":
                    if zone:
                        nv.volDown(zone)
                    else:
                        logging.error("Zone not specified for voldwn.")
                elif command == "setvol":
                    if zone and value is not None:
                        nv.setVol(zone, value)
                    else:
                        logging.error("Zone or Value not specified for setvol: zone: %s, value: %s", zone, value)
                elif command == "setinput":
                    if zone and value is not None:
                        nv.setSource(zone, value)
                    else:
                        logging.error("Zone or Value not specified for setinput: zone: %s, value: %s", zone, value)
                elif command == "togglemute":
                    if zone is not None:
                        nv.toggleMute(zone)
                    else:
                        logging.error("Zone not specified for togglemute.")
                elif command == "getzonelabels":
                    return json.dumps(nv.getZoneNames())
            else:
                logging.warning("Invalid command specified: %s", command)
        else:
            logging.warning("No command specified")

        # give the Amp time to reply 
        #time.sleep(0.5)
        
        return json.dumps(nv.status())

if __name__ == "__main__":

    app = web.application(urls, globals())
    app.run()
