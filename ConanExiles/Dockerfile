FROM ubuntu:24.04

RUN dpkg --add-architecture i386 && \
    apt update && \
    apt install -y \
    wget \
    curl \
    unzip \
    ca-certificates \
    lib32gcc-s1 \
    lib32stdc++6 && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m steam

# Install SteamCMD
RUN mkdir -p /steamcmd && \
    cd /steamcmd && \
    wget https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz && \
    tar -xvzf steamcmd_linux.tar.gz && \
    rm steamcmd_linux.tar.gz && \
    chmod +x /steamcmd/steamcmd.sh && \
    chown -R steam:steam /steamcmd

RUN mkdir -p /home/steam/ConanExiles

WORKDIR /home/steam

COPY start.sh /start.sh
RUN chmod +x /start.sh

USER steam

ENTRYPOINT ["/start.sh"]
