ARG BUILD_FROM=python:3.12-alpine
FROM ${BUILD_FROM}

RUN pip3 install --no-cache-dir paho-mqtt requests PyYAML

COPY run.sh /
COPY dripdrop /dripdrop

RUN chmod a+x /run.sh

CMD ["/run.sh"]
