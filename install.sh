#!/bin/sh
mkdir -v /usr/local/bin/nuvo_server
cp -v nuvo.py /usr/local/bin/nuvo_server/
cp -v nuvo_server.py /usr/local/bin/nuvo_server/
cp -v nuvo_server /etc/init.d/
