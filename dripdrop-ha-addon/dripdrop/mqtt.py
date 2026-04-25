"""MQTT client wrapper with publish helpers and LWT support."""

import json
import logging
import time

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTClient:
    """Wrapper around paho-mqtt with reconnect backoff and LWT."""

    def __init__(self, host: str, port: int, user: str, password: str, device_id: str):
        self.host = host
        self.port = port
        self.device_id = device_id
        self.status_topic = f"dripdrop/{device_id}/status"

        self.client = mqtt.Client(client_id=f"dripdrop-{device_id}")
        if user:
            self.client.username_pw_set(user, password)

        # Last Will and Testament
        self.client.will_set(self.status_topic, payload="offline", qos=1, retain=True)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self._connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker at %s:%s", self.host, self.port)
            self._connected = True
            # Publish online status on every (re)connect
            self.publish(self.status_topic, "online", retain=True)
        else:
            logger.error("MQTT connection failed with code %s", rc)

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc != 0:
            logger.warning("Unexpected MQTT disconnect (rc=%s), will reconnect", rc)

    def connect(self):
        """Connect to the broker with exponential backoff retry."""
        backoff = 1
        while True:
            try:
                self.client.connect(self.host, self.port, keepalive=60)
                self.client.loop_start()
                # Wait briefly for on_connect
                deadline = time.time() + 10
                while not self._connected and time.time() < deadline:
                    time.sleep(0.1)
                if self._connected:
                    return
                logger.warning("MQTT connect timed out, retrying in %ss", backoff)
            except Exception as e:
                logger.warning("MQTT connect error: %s, retrying in %ss", e, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)

    def publish(self, topic: str, payload, retain: bool = False):
        """Publish a message. Payload can be str, number, or dict (auto-serialized)."""
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        elif not isinstance(payload, str):
            payload = str(payload)
        self.client.publish(topic, payload, qos=1, retain=retain)

    def publish_discovery(self, entity_type: str, object_id: str, config: dict):
        """Publish an MQTT discovery config message."""
        topic = f"homeassistant/{entity_type}/{self.device_id}/{object_id}/config"
        self.publish(topic, config, retain=True)

    def publish_offline(self):
        """Publish offline status."""
        self.publish(self.status_topic, "offline", retain=True)

    def disconnect(self):
        """Publish offline and disconnect cleanly."""
        self.publish_offline()
        self.client.loop_stop()
        self.client.disconnect()
