# nuvo
This is the serial controller that implements a REST API for the Nuvo Essentia NV-E6G Home Audio distribution amplifier. 

# Files
* nuvo.py: Python class for the Nuvo controller that handles the serial communication
* nuvo_server.py: Python server that implements the RESET API.  NOTE: It assumes nuvo.py is in the same directory
* nuvo_server: Server daemon
* install.sh: Script to install and set to run via /etc/init.d
