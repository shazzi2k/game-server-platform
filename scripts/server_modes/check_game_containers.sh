#!/bin/bash

containers=$(docker ps --format '{{.Names}}' | grep -E "zomboid|valheim|7day")

if [ -z "$containers" ]; then
    echo 0
else
    echo 1
fi
