#!/bin/bash

set -e

banner() {
    echo
    echo "========================================="
    echo "$1"
    echo "========================================="
    echo
}

info() {
    echo "[INFO] $1"
}

success() {
    echo "[ OK ] $1"
}

error() {
    echo "[FAIL] $1"
    exit 1
}

check_command() {
    command -v "$1" >/dev/null 2>&1 || error "$1 is not installed."
}

create_dirs() {
    mkdir -p "$DOWNLOAD_DIR"
    mkdir -p "$INSTALL_DIR"
}

extract_server_pack() {

    banner "Extracting Server Pack"

    ZIP_FILE=$(find "$DOWNLOAD_DIR" -maxdepth 1 -name "ServerFiles*.zip" | head -n 1)

    [ -z "$ZIP_FILE" ] && error "No ServerFiles ZIP found."

    info "Using $(basename "$ZIP_FILE")"

    mkdir -p "$INSTALL_DIR"

    info "Cleaning installation directory..."

    find "$INSTALL_DIR" -mindepth 1 -delete

    info "Extracting..."

    unzip -oq "$ZIP_FILE" -d "$INSTALL_DIR"

    success "Extraction complete."
}