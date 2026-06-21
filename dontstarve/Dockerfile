FROM ubuntu:22.04

RUN dpkg --add-architecture i386 && \
    apt update && \
    apt install -y \
    wget \
    ca-certificates \
    lib32gcc-s1 \
    lib32stdc++6 \
    libcurl4 \
    libcurl4:i386 \
    libsdl2-2.0-0 \
    libsdl2-2.0-0:i386 \
    libcurl3-gnutls \
    libcurl3-gnutls:i386 \
    libopenal1 \
    libopenal1:i386 \
    libgl1 \
    libgl1:i386 && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# install steamcmd
RUN mkdir -p /steamcmd && \
    cd /steamcmd && \
    wget https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz && \
    tar -xvzf steamcmd_linux.tar.gz && \
    rm steamcmd_linux.tar.gz

WORKDIR /

COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
