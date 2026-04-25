"""MQTT discovery payload builders for Home Assistant."""


def _device_block(device_id: str, device_name: str) -> dict:
    return {
        "identifiers": [device_id],
        "name": device_name,
        "model": "DripDrop ESP32",
        "manufacturer": "DripDrop",
    }


def _availability(device_id: str) -> dict:
    return {
        "availability_topic": f"dripdrop/{device_id}/status",
        "payload_available": "online",
        "payload_not_available": "offline",
    }


def system_sensor_configs(device_id: str, device_name: str) -> list[tuple[str, str, dict]]:
    """Return list of (entity_type, object_id, config) for system entities."""
    device = _device_block(device_id, device_name)
    avail = _availability(device_id)
    prefix = f"dripdrop/{device_id}/system"

    configs = []

    # Uptime sensor
    configs.append(("sensor", "uptime", {
        "name": "Uptime",
        "unique_id": f"{device_id}_uptime",
        "state_topic": f"{prefix}/uptime",
        "unit_of_measurement": "ms",
        "device_class": "duration",
        "entity_category": "diagnostic",
        "device": device,
        **avail,
    }))

    # Free heap sensor
    configs.append(("sensor", "heap", {
        "name": "Free Heap",
        "unique_id": f"{device_id}_heap",
        "state_topic": f"{prefix}/heap",
        "unit_of_measurement": "B",
        "entity_category": "diagnostic",
        "device": device,
        **avail,
    }))

    # RSSI sensor
    configs.append(("sensor", "rssi", {
        "name": "WiFi RSSI",
        "unique_id": f"{device_id}_rssi",
        "state_topic": f"{prefix}/rssi",
        "unit_of_measurement": "dBm",
        "device_class": "signal_strength",
        "entity_category": "diagnostic",
        "device": device,
        **avail,
    }))

    # WiFi connected binary sensor
    configs.append(("binary_sensor", "wifi", {
        "name": "WiFi Connected",
        "unique_id": f"{device_id}_wifi",
        "state_topic": f"{prefix}/wifi",
        "payload_on": "ON",
        "payload_off": "OFF",
        "device_class": "connectivity",
        "entity_category": "diagnostic",
        "device": device,
        **avail,
    }))

    # NTP synced binary sensor
    configs.append(("binary_sensor", "ntp", {
        "name": "NTP Synced",
        "unique_id": f"{device_id}_ntp",
        "state_topic": f"{prefix}/ntp",
        "payload_on": "ON",
        "payload_off": "OFF",
        "entity_category": "diagnostic",
        "device": device,
        **avail,
    }))

    # AP mode binary sensor
    configs.append(("binary_sensor", "ap_mode", {
        "name": "AP Mode",
        "unique_id": f"{device_id}_ap_mode",
        "state_topic": f"{prefix}/ap_mode",
        "payload_on": "ON",
        "payload_off": "OFF",
        "entity_category": "diagnostic",
        "device": device,
        **avail,
    }))

    return configs


def valve_configs(device_id: str, device_name: str, valve_count: int) -> list[tuple[str, str, dict]]:
    """Return discovery configs for all valves."""
    device = _device_block(device_id, device_name)
    avail = _availability(device_id)
    configs = []

    for vid in range(1, valve_count + 1):
        # Valve state binary sensor
        configs.append(("binary_sensor", f"valve_{vid}", {
            "name": f"Valve {vid}",
            "unique_id": f"{device_id}_valve_{vid}",
            "state_topic": f"dripdrop/{device_id}/valves/{vid}/state",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device_class": "opening",
            "device": device,
            **avail,
        }))

        # Valve source sensor
        configs.append(("sensor", f"valve_{vid}_source", {
            "name": f"Valve {vid} Source",
            "unique_id": f"{device_id}_valve_{vid}_source",
            "state_topic": f"dripdrop/{device_id}/valves/{vid}/source",
            "device": device,
            **avail,
        }))

        # Valve last run sensor
        configs.append(("sensor", f"valve_{vid}_last_run", {
            "name": f"Valve {vid} Last Run",
            "unique_id": f"{device_id}_valve_{vid}_last_run",
            "state_topic": f"dripdrop/{device_id}/valves/{vid}/last_run",
            "device_class": "timestamp",
            "device": device,
            **avail,
        }))

    return configs


def timer_configs(device_id: str, device_name: str, valve_count: int) -> list[tuple[str, str, dict]]:
    """Return discovery configs for all timer entities."""
    device = _device_block(device_id, device_name)
    avail = _availability(device_id)
    configs = []

    for vid in range(1, valve_count + 1):
        # Timer active binary sensor
        configs.append(("binary_sensor", f"timer_{vid}", {
            "name": f"Timer {vid}",
            "unique_id": f"{device_id}_timer_{vid}",
            "state_topic": f"dripdrop/{device_id}/timers/{vid}/active",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device": device,
            **avail,
        }))

        # Timer remaining sensor
        configs.append(("sensor", f"timer_{vid}_remaining", {
            "name": f"Timer {vid} Remaining",
            "unique_id": f"{device_id}_timer_{vid}_remaining",
            "state_topic": f"dripdrop/{device_id}/timers/{vid}/remaining",
            "unit_of_measurement": "s",
            "device": device,
            **avail,
        }))

    return configs


def module_configs(device_id: str, device_name: str, modules: list[dict]) -> list[tuple[str, str, dict]]:
    """Return discovery configs for all registered modules."""
    device = _device_block(device_id, device_name)
    avail = _availability(device_id)
    configs = []

    for mod in modules:
        uid = mod["uid"]
        mod_type = mod.get("type", "SENSOR")
        unit = mod.get("unit", "")
        short_uid = uid[-6:]

        configs.append(("sensor", f"module_{uid}", {
            "name": f"{mod_type} {short_uid}",
            "unique_id": f"{device_id}_module_{uid}",
            "state_topic": f"dripdrop/{device_id}/modules/{uid}/reading",
            "unit_of_measurement": unit,
            "device": device,
            **avail,
        }))

    return configs
