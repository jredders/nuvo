# nuvo
This is the serial controller that implements a REST API for the Nuvo Essentia NV-E6GXS Home Audio distribution amplifier. 

# Files
* nuvo.py: Python class for the Nuvo controller that handles the serial communication
* nuvo_server.py: Python server that implements the RESET API.  NOTE: It assumes the above files are in the same directory as this script
* nuvo_server.sh: Put this in /etc/init.d/ so it will run at startup.  NOTE: It assumes everything is installed in /usr/local/bin/nuvo_server/
