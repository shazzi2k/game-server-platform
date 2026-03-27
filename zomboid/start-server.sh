#!/bin/bash
set -e

echo "Starting Project Zomboid server..."

# install if missing
if [ ! -f /pz/start-server.sh ]; then
    echo "Installing Zomboid server..."
    /steamcmd/steamcmd.sh +login anonymous +force_install_dir /pz +app_update 380870 -beta unstable validate +quit
fi

cd /pz

#  limit Java memory
export JAVA_OPTS="-Xms2g -Xmx4g"


# First run fix: create admin automatically
if [ ! -f /root/Zomboid/db/shazcloud.db ]; then
    echo "First run detected, creating admin user..."
    echo "civ6" | ./start-server.sh -servername shazcloud
    sleep 5
fi

exec ./start-server.sh -servername shazcloud -adminpassword civ6
