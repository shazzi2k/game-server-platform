#!/bin/bash
set -e

echo "Starting 7 Days to Die server..."

# install if missing
if [ ! -f /home/steam/7days/startserver.sh ]; then
    echo "Installing 7DTD server..."
    /steamcmd/steamcmd.sh +login anonymous \
        +force_install_dir /home/steam/7days \
        +app_update 294420 validate \
        +quit
fi

cd /home/steam/7days

exec ./startserver.sh \
    -configfile=serverconfig.xml \
    -port=26900 \
    -servername="Shaz7DTD" \
    -logfile 7days.log
