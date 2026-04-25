ARG BUILD_FROM=python:3.12-alpine
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip && \
    pip3 install --no-cache-dir --break-system-packages paho-mqtt requests PyYAML

COPY run.sh /
COPY dripdrop /dripdrop

RUN chmod a+x /run.sh

CMD ["/run.sh"]
