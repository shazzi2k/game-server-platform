#!/bin/bash
set -e

echo "Checking for DontStarve updates..."

/steamcmd/steamcmd.sh \
  +force_install_dir /dontstarve \
  +login anonymous \
  +app_update 343050  validate \
  +quit

cd /dontstarve/bin64

echo "Config contents:"
ls -R /dontstarve/.klei
if [ ! -d "/dontstarve/.klei/DoNotStarveTogether/MyDediServer" ]; then
    echo "Cluster MyDediServer not found!"
    exit 1
fi




echo "Starting DontStarve server..."
echo "Finding DST binaries..."
find /dontstarve -type f | grep -i dedicated

exec ./dontstarve_dedicated_server_nullrenderer_x64 -console -cluster MyDediServer -shard Master

