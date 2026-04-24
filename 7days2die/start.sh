#!/bin/bash
set -e

echo "Starting 7 Days to Die server..."

INSTALL_DIR="/home/steam/7days"

# install/update
/steamcmd/steamcmd.sh \
    +force_install_dir "$INSTALL_DIR" \
    +login anonymous \
    +app_update 294420 \
    +quit

cd "$INSTALL_DIR"

echo "Checking for start script..."

if [ ! -f "./startserver.sh" ]; then
    echo "ERROR: startserver.sh not found in install dir"
    ls -la
    exit 1
fi

exec ./startserver.sh \
    -configfile=serverconfig.xml \
    -port=26900 \
    -servername="Shaz7DTD" \
    -logfile 7days.log
