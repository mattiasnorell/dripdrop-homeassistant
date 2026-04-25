"""DripDrop Home Assistant add-on — main poll loop."""

import json
import logging
import os
import re
import signal
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import DripDropAPI
from mqtt import MQTTClient
import entities

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("dripdrop")

SOURCE_MAP = {0: "NONE", 1: "SCENARIO", 2: "TIMER", 3: "MANUAL"}


def slugify(name: str) -> str:
    """Convert a device name to a slug suitable for use as device_id."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_") or "dripdrop"


def load_options() -> dict:
    """Load add-on options from /data/options.json."""
    try:
        with open("/data/options.json") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("/data/options.json not found, using defaults")
        return {}


def publish_system_state(mqtt_client: MQTTClient, device_id: str, status: dict, name: str):
    """Publish system status topics."""
    prefix = f"dripdrop/{device_id}/system"
    mqtt_client.publish(f"{prefix}/uptime", status.get("uptime", 0))
    mqtt_client.publish(f"{prefix}/heap", status.get("freeHeap", 0))
    mqtt_client.publish(f"{prefix}/rssi", status.get("wifiRssi", 0))
    mqtt_client.publish(f"{prefix}/wifi", "ON" if status.get("wifiConnected") else "OFF")
    mqtt_client.publish(f"{prefix}/ntp", "ON" if status.get("ntpSynced") else "OFF")
    mqtt_client.publish(f"{prefix}/ap_mode", "ON" if status.get("apMode") else "OFF")
    mqtt_client.publish(f"{prefix}/name", name)


def publish_valve_state(mqtt_client: MQTTClient, device_id: str, valves: list[dict]):
    """Publish valve state topics."""
    for valve in valves:
        vid = valve["id"]
        prefix = f"dripdrop/{device_id}/valves/{vid}"
        mqtt_client.publish(f"{prefix}/state", "ON" if valve.get("isOn") else "OFF")
        source_num = valve.get("source", 0)
        mqtt_client.publish(f"{prefix}/source", SOURCE_MAP.get(source_num, "NONE"))

        last_start = valve.get("lastRunStart", 0)
        if last_start and last_start > 0:
            dt = datetime.fromtimestamp(last_start, tz=timezone.utc)
            mqtt_client.publish(f"{prefix}/last_run", dt.isoformat())
        else:
            mqtt_client.publish(f"{prefix}/last_run", "never")


def publish_timer_state(mqtt_client: MQTTClient, device_id: str, timers: list[dict], valve_count: int):
    """Publish timer state topics."""
    active_timers = {t["valveId"]: t for t in timers}
    for vid in range(1, valve_count + 1):
        prefix = f"dripdrop/{device_id}/timers/{vid}"
        if vid in active_timers:
            mqtt_client.publish(f"{prefix}/active", "ON")
            mqtt_client.publish(f"{prefix}/remaining", active_timers[vid].get("remaining", 0))
        else:
            mqtt_client.publish(f"{prefix}/active", "OFF")
            mqtt_client.publish(f"{prefix}/remaining", 0)


def publish_module_readings(mqtt_client: MQTTClient, device_id: str, api: DripDropAPI, modules: list[dict]):
    """Fetch and publish each module reading sequentially."""
    for mod in modules:
        uid = mod["uid"]
        prefix = f"dripdrop/{device_id}/modules/{uid}"
        value = api.get_module_reading(uid)
        if value is not None:
            mqtt_client.publish(f"{prefix}/reading", value)
        else:
            mqtt_client.publish(f"{prefix}/reading", "unavailable")
        mqtt_client.publish(f"{prefix}/unit", mod.get("unit", ""))


def publish_all_discovery(mqtt_client: MQTTClient, device_id: str, device_name: str,
                          valve_count: int, modules: list[dict]):
    """Publish all MQTT discovery configs."""
    all_configs = (
        entities.system_sensor_configs(device_id, device_name)
        + entities.valve_configs(device_id, device_name, valve_count)
        + entities.timer_configs(device_id, device_name, valve_count)
        + entities.module_configs(device_id, device_name, modules)
    )
    for entity_type, object_id, config in all_configs:
        mqtt_client.publish_discovery(entity_type, object_id, config)
    logger.info("Published %d discovery configs", len(all_configs))


def main():
    opts = load_options()
    esp32_host = opts.get("esp32_host", "dripdrop.local")
    esp32_port = opts.get("esp32_port", 80)
    poll_interval = opts.get("poll_interval", 30)
    mqtt_host = opts.get("mqtt_host", "core-mosquitto")
    mqtt_port = opts.get("mqtt_port", 1883)
    mqtt_user = opts.get("mqtt_user", "")
    mqtt_password = opts.get("mqtt_password", "")
    valve_count = opts.get("valve_count", 4)

    api = DripDropAPI(esp32_host, esp32_port)

    # Fetch device name for device_id (retry until reachable)
    device_name = "dripdrop"
    while True:
        try:
            device_name = api.get_system_name()
            break
        except Exception as e:
            logger.warning("Cannot reach ESP32 to get device name: %s. Retrying in 5s...", e)
            time.sleep(5)

    device_id = slugify(device_name)
    logger.info("Device: %s (id: %s)", device_name, device_id)

    # Connect MQTT
    mqtt_client = MQTTClient(mqtt_host, mqtt_port, mqtt_user, mqtt_password, device_id)
    mqtt_client.connect()

    # Discover modules
    known_modules: list[dict] = []
    try:
        known_modules = api.get_modules()
        logger.info("Discovered %d modules", len(known_modules))
    except Exception as e:
        logger.warning("Failed to fetch modules on startup: %s", e)

    # Publish all discovery configs
    publish_all_discovery(mqtt_client, device_id, device_name, valve_count, known_modules)

    # Graceful shutdown
    running = True

    def shutdown(signum, frame):
        nonlocal running
        logger.info("Shutting down (signal %s)...", signum)
        running = False

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # Poll loop
    while running:
        try:
            # Ping check
            if not api.ping():
                logger.warning("ESP32 unreachable, publishing offline")
                mqtt_client.publish_offline()
                time.sleep(poll_interval)
                continue

            # Publish online
            mqtt_client.publish(mqtt_client.status_topic, "online", retain=True)

            # System status
            try:
                status = api.get_system_status()
                name = api.get_system_name()
                publish_system_state(mqtt_client, device_id, status, name)
            except Exception as e:
                logger.warning("Failed to fetch system status: %s", e)

            # Valves
            try:
                valves = api.get_valves()
                publish_valve_state(mqtt_client, device_id, valves)
            except Exception as e:
                logger.warning("Failed to fetch valves: %s", e)

            # Timers
            try:
                timers = api.get_timers()
                publish_timer_state(mqtt_client, device_id, timers, valve_count)
            except Exception as e:
                logger.warning("Failed to fetch timers: %s", e)

            # Modules — check for changes and re-publish discovery if needed
            try:
                current_modules = api.get_modules()
                current_uids = {m["uid"] for m in current_modules}
                known_uids = {m["uid"] for m in known_modules}
                if current_uids != known_uids:
                    logger.info("Module list changed, re-publishing discovery")
                    known_modules = current_modules
                    publish_all_discovery(mqtt_client, device_id, device_name, valve_count, known_modules)
                else:
                    known_modules = current_modules
            except Exception as e:
                logger.warning("Failed to fetch modules: %s", e)

            # Module readings (sequential)
            publish_module_readings(mqtt_client, device_id, api, known_modules)

        except Exception as e:
            logger.error("Unexpected error in poll loop: %s", e)

        # Sleep in small increments to allow signal handling
        for _ in range(poll_interval * 10):
            if not running:
                break
            time.sleep(0.1)

    # Clean shutdown
    mqtt_client.disconnect()
    logger.info("DripDrop add-on stopped")


if __name__ == "__main__":
    main()
