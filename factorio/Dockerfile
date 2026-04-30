FROM ubuntu:22.04

RUN apt update && apt install -y \
    libcurl4 \
    libsdl2-2.0-0 \
    libopenal1 \
    libgl1 \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /factorio
