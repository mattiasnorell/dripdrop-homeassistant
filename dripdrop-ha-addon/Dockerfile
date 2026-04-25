ARG BUILD_FROM=python:3.12-alpine
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip && \
    pip3 install --no-cache-dir --break-system-packages paho-mqtt requests PyYAML

COPY dripdrop /dripdrop
COPY run.sh /etc/services.d/dripdrop/run

RUN chmod a+x /etc/services.d/dripdrop/run
