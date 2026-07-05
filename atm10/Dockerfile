FROM eclipse-temurin:21-jdk

RUN apt-get update && \
    apt-get install -y \
        bash \
        curl \
        wget \
        unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /data

COPY start.sh /start.sh

RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]