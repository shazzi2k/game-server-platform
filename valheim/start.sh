#!/bin/bash
set -e

echo "Starting Valheim server..."

# install if missing
if [ ! -f /home/steam/valheim/valheim_server.x86_64 ]; then
    echo "Installing Valheim server..."
    /steamcmd/steamcmd.sh +login anonymous \
        +force_install_dir /home/steam/valheim \
        +app_update 896660 validate \
        +quit
fi

cd /home/steam/valheim

exec ./valheim_server.x86_64 \
    -name "ShazValheim" \
    -port 2456 \
    -world "Dedicated" \
    -password "" \
    -public 1
