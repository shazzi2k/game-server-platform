#!/bin/bash

set -e

PACK=${1:-atm10}

source "./packs/$PACK.env"
source "./common.sh"

banner "Installing $PACK_NAME"

check_command unzip

create_dirs

extract_server_pack

success "Installation complete."