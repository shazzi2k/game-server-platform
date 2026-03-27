FROM ubuntu:22.04

RUN dpkg --add-architecture i386 && \
    apt update && \
    apt install -y \
    wget \
    ca-certificates \
    lib32gcc-s1 \
    lib32stdc++6 && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m steam

# install steamcmd
RUN mkdir -p /steamcmd && \
    cd /steamcmd && \
    wget https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz && \
    tar -xvzf steamcmd_linux.tar.gz && \
    rm steamcmd_linux.tar.gz && \
    chmod +x /steamcmd/steamcmd.sh && \
    chown -R steam:steam /steamcmd

WORKDIR /home/steam/7days

COPY start.sh /start.sh
RUN chmod +x /start.sh

USER steam
ENTRYPOINT ["/start.sh"]
