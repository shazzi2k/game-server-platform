#!/bin/bash
set -e

echo "Checking for Project Zomboid updates..."
rm -rf /pz/*
/steamcmd/steamcmd.sh \
  force_install_dir /pz \
  +login anonymous \
  +app_update 380870 -beta unstable validate \
  +quit

cd "/pz/Steam/steamapps/common/Project Zomboid Dedicated Server"

export JAVA_OPTS="-Xms2g -Xmx4g"

# First run fix: create admin automatically
if [ ! -f /root/Zomboid/db/shazcloud.db ]; then
    echo "First run detected, creating admin user..."
    echo "civ6" | ./start-server.sh -servername shazcloud
    sleep 5
fi

echo "Starting Project Zomboid server..."
exec ./start-server.sh -servername shazcloud -adminpassword civ6
