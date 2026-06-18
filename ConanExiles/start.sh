#!/bin/bash
set -e

INSTALL_DIR="/home/steam/Steam/steamapps/common/Conan Exiles Dedicated Server"

echo "Checking Conan Exiles installation..."

if [ ! -f "${INSTALL_DIR}/ConanSandboxServer.sh" ]; then

    echo "Conan Exiles not found. Installing..."

    /steamcmd/steamcmd.sh \
        +login anonymous \
        +app_update 443030 validate \
        +quit

    echo "Installation complete."
fi

echo "Starting Conan Exiles server..."

cd "${INSTALL_DIR}"

exec ./ConanSandboxServer.sh "ConanSandbox?ServerName=Shazcorp Conan Exiles"
