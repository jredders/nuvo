#!/usr/bin/python3
import web, nuvo, sys, json, time, logging

logfile = 'server.log'
serial_port = '/dev/ttyUSB0'

# set up logger
logging.basicConfig(filename=logfile,level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# get the Nuvo object
nv = nuvo.Nuvo(serial_port)

# define list of commands we handle
commands = ['open','alloff','pwr','volup','voldwn','setvol','setinput','togglemute','status','getzonelabels']
            
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
        print("Received GET")
        # we're going to return JSON
        web.header('Content-Type', 'application/json')
        # Grab the arguements from the URL
        user_data = web.input()
        logging.debug("user_data:",user_data)
        
        # do some input validation
        if 'command' in user_data:
            command = user_data.command.lower()
            if command in commands: 
                logging.info("Processing...",command)
                zone = int(user_data.zone) if 'zone' in user_data else None
                value = int(user_data.value) if 'value' in user_data else None

                # Process the commnads
                if command == "open":
                    nv.open()
                elif command == "status":
                    if zone:
                        nv.queryZone(zone)
                    else:
                        logging.error("Error - no zone specified.")
                elif command == "alloff":
                    nv.allOff()
                elif command == "pwr":
                    if zone and value is not None:
                        nv.setPower(zone, value)
                    else:
                        loggin.error("Zone or Value not specified: Zone: %s, Value: %s",zone,value)
                elif command == "volup":
                    if zone:
                        nv.volUp(zone)
                    else:
                        logging.error("Error - no zone specified.")
                elif command == "voldwn":
                    if zone:
                        nv.volDown(zone)
                    else:
                        logging.error("Error - no zone specified.")
                elif command == "setvol":
                    if zone and value is not None:
                        nv.setVol(zone, value)
                    else:
                        loggin.error("Zone or Value not specified: Zone: %s, Value: %s",zone,value)
                elif command == "setinput":
                    if zone and value:
                        nv.setSource(zone, value)
                    else:
                        loggin.error("Zone or Value not specified: Zone: %s, Value: %s",zone,value)
                elif command == "togglemute":
                    if zone:
                        nv.toggleMute(zone)
                    else:
                        logging.error("Error - no zone specified.")
                elif command == "getzonelabels":
                    return json.dumps(nv.getZoneNames())
            else:
                loggin.warning("Invalid command specified:", command)
        else:
            logging.warning("No command specified")

        # give the Amp time to reply 
        time.sleep(0.5)
        
        return json.dumps(nv.status())

if __name__ == "__main__":

    # open the Nuvo device - wait until we can reach it.  Most common reason - power is off on the Amp
    #logging.info("Opening Nuvo at %s", serial_port)
    #while nv.open() is False:
    #    logging.warning("Could not open Nuvo comm - is it on? Retrying in 15s...")
    #    time.sleep(15)

    app = web.application(urls, globals())
    app.run()
