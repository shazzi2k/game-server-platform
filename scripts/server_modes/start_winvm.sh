#!/bin/bash

RUNNING=$(docker ps -q | wc -l)

if [ "$RUNNING" -gt 1 ]; then
    echo "Game containers running. Cannot start VM."
    exit 1
fi

echo "Starting Windows VM...Hell yeah."
virsh start windows-gaming
