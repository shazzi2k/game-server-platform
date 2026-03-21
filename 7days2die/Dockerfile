FROM ubuntu:22.04

RUN apt update && \
    apt install -y \
    ca-certificates \
    wget \
    lib32gcc-s1 \
    lib32stdc++6 && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /7d

CMD ["bash", "-c", "./startserver.sh -configfile=serverconfig.xml"]
