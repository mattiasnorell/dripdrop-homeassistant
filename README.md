# DripDrop Home Assistant Add-on

Home Assistant add-on for the DripDrop ESP32 irrigation controller. Polls the ESP32 REST API and exposes all data to Home Assistant via MQTT auto-discovery.

## Prerequisites

- **Home Assistant OS** (or Supervised)
- **Mosquitto broker** add-on installed and running (Settings → Add-ons → Add-on Store → "Mosquitto broker")
- A **DripDrop ESP32** controller reachable on your network

## Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**
2. Open the three-dot menu (top right) → **Repositories**
3. Paste your repository URL and click **Add**:
   ```
   https://github.com/OWNER/dripdrop-homeassistant
   ```
4. The **DripDrop** add-on appears in the store — click it → **Install**
5. Go to the **Configuration** tab and set your options (see below)
6. **Start** the add-on

## Configuration

| Option | Default | Description |
|---|---|---|
| `esp32_host` | `dripdrop.local` | Hostname or IP of the ESP32 controller |
| `esp32_port` | `80` | HTTP port of the ESP32 REST API |
| `poll_interval` | `30` | Polling interval in seconds (5–3600) |
| `mqtt_host` | `core-mosquitto` | MQTT broker hostname |
| `mqtt_port` | `1883` | MQTT broker port |
| `mqtt_user` | _(empty)_ | MQTT username |
| `mqtt_password` | _(empty)_ | MQTT password |
| `valve_count` | `4` | Number of valves on your controller (1–8) |

> If you use the Mosquitto broker add-on with default settings, the MQTT host/port defaults should work as-is. Set `mqtt_user` and `mqtt_password` if your broker requires authentication.

## Exposed Entities

All entities are grouped under a single **DripDrop ESP32** device in Home Assistant.

### System (diagnostic)

| Entity | Type | Unit |
|---|---|---|
| Uptime | Sensor | ms |
| Free Heap | Sensor | B |
| WiFi RSSI | Sensor | dBm |
| WiFi Connected | Binary Sensor | — |
| NTP Synced | Binary Sensor | — |
| AP Mode | Binary Sensor | — |

### Valves (per valve)

| Entity | Type | Values |
|---|---|---|
| Valve _N_ | Binary Sensor | ON / OFF |
| Valve _N_ Source | Sensor | NONE, SCENARIO, TIMER, MANUAL |
| Valve _N_ Last Run | Sensor | ISO 8601 timestamp or "never" |

### Timers (per valve)

| Entity | Type | Unit |
|---|---|---|
| Timer _N_ | Binary Sensor | ON / OFF |
| Timer _N_ Remaining | Sensor | seconds |

### Modules (auto-discovered)

Sensor modules connected to the ESP32 (temperature, humidity, soil, etc.) are discovered automatically. Each module creates a sensor entity with the appropriate unit of measurement.

## How It Works

1. On startup, the add-on connects to MQTT with a Last Will and Testament (offline status)
2. It fetches the device name and module list from the ESP32, then publishes MQTT discovery configs so entities appear automatically in Home Assistant
3. Every `poll_interval` seconds, it polls all ESP32 endpoints and publishes updated state to MQTT
4. If the ESP32 becomes unreachable, the device shows as "offline" in HA; polling resumes automatically when it comes back
