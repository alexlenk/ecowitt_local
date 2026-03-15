# Ecowitt Local Web Interface Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-green.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/alexlenk/ecowitt_local.svg)](https://github.com/alexlenk/ecowitt_local/releases)
[![License](https://img.shields.io/github/license/alexlenk/ecowitt_local.svg)](https://github.com/alexlenk/ecowitt_local/blob/main/LICENSE)
[![CI](https://github.com/alexlenk/ecowitt_local/workflows/CI/badge.svg)](https://github.com/alexlenk/ecowitt_local/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/alexlenk/ecowitt_local/graph/badge.svg?token=ENNYU0GH1F)](https://codecov.io/gh/alexlenk/ecowitt_local)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

A Home Assistant custom integration for Ecowitt weather stations that uses **local HTTP polling** of the gateway web interface. It was created to solve a specific problem: webhook-based integrations use channel-based entity IDs that change whenever batteries die or sensors reconnect — breaking automations, dashboards, and historical data. This integration uses hardware IDs from the gateway's local API to create entity IDs that are permanent.

## 🎯 Why This Integration?

### The Problem with Webhooks

The built-in HA Ecowitt integration (and other webhook-based integrations) have fundamental limitations:

- **Unstable Entity IDs**: IDs are channel-based and change when batteries die or sensors reconnect in a different order
- **HTTP exposure required**: Your Home Assistant must be reachable from the gateway over HTTP to receive push data
- **Missing data**: Battery levels, signal strength, and hardware IDs are not available via the webhook protocol
- **No gateway control**: Polling interval is not configurable — you get data when the gateway decides to push it

### How Does It Compare to Other Integrations?

| Feature | **ecowitt_local** | [HA Ecowitt](https://www.home-assistant.io/integrations/ecowitt/) (built-in) | [ha-ecowitt-iot](https://github.com/ecowitt-iot/ha-ecowitt-iot) (official Ecowitt) |
|---|---|---|---|
| **HACS** | ✅ Default store | ✅ Built into HA | ❌ Custom repo required |
| **Protocol** | Local HTTP polling | Webhook (gateway pushes to HA) | Local HTTP polling |
| **HA must be reachable** | ❌ No | ✅ Yes (HTTP from gateway) | ❌ No |
| **Gateway support** | GW1000, GW1100, GW1200, GW2000, GW3000 | All (webhook-capable) | GW1200+ only |
| **Entity IDs** | ✅ Stable (hardware ID based) | ❌ Unstable (channel-based) | ❌ Key-based (e.g. `tempf`) |
| **Battery levels** | ✅ Yes | ❌ No | ✅ Yes |
| **Signal strength** | ✅ Yes | ❌ No | ✅ Yes |
| **Polling interval** | Configurable (30–300s) | Fixed (gateway push) | Fixed 10s |
| **External dependencies** | None | None | `wittiot` library |
| **Inactive sensors** | Configurable | ❌ No | ❌ No |

The built-in HA integration requires your Home Assistant to be reachable over HTTP from the gateway to receive push data — which is a security and setup concern for many users. It also uses channel-based entity IDs that change when batteries die or sensors reconnect in a different order, which breaks automations and dashboards.

**The core motivation for this project is stable hardware-based entity IDs.** When a sensor battery dies and you replace it, or when the gateway reboots and sensors reconnect in a different order, the entity IDs should not change. Without stable IDs, every battery replacement potentially breaks irrigation automations, dashboard cards, and notification rules. This is a fundamental problem with the webhook/channel-based approach that cannot be fixed without a different data source — which is exactly what polling the gateway's local web interface provides.

The official Ecowitt integration (`ha-ecowitt-iot`) also does not support GW1000 or GW1100 gateways, and its entity IDs are not hardware-based either.

### Our Solution: Hardware-Based Stable Entity IDs

This integration polls the gateway's raw web interface, which exposes the physical hardware ID of each paired sensor. This is what makes stable entity IDs possible:

```
sensor.ecowitt_soil_moisture_d8174   ← Always this ID, regardless of battery changes
sensor.ecowitt_temperature_a1b2c3    ← Based on hardware, not channel number
```

Entity IDs never change when batteries die, sensors reconnect, or the gateway reboots.

## ✅ Key Features

- **Stable hardware-ID entity IDs** — automations that never break
- **Individual sensor devices** — each physical sensor is its own HA device with its own battery/signal/online status
- **No HTTP exposure** — HA does not need to be reachable from the gateway
- **Configurable polling** — live data (30–300s) and sensor mapping (300–3600s) intervals
- **Rich diagnostic data** — battery levels, signal strength (RSSI), online/offline status per sensor
- **Inactive sensor support** — optionally include sensors that are offline
- **No external dependencies** — communicates directly with gateway HTTP API

## 📋 Requirements

- Home Assistant Core 2024.1.0+
- Ecowitt Gateway on the local network (see supported gateways below)
- Network access from Home Assistant to the gateway web interface

## 🛠️ Installation

### Via HACS (Recommended)

This integration is available in the **HACS default store** — no custom repository required.

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Search for **"Ecowitt Local"**
4. Click **Download**
5. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/ecowitt_local` folder from this repository
2. Copy it to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## ⚙️ Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **"Ecowitt Local"**
4. Enter your gateway IP address (e.g. `192.168.1.100`)
5. Enter the gateway password if one is set (most gateways do not require this)
6. Configure polling intervals:
   - **Live Data**: 30–300 seconds (default: 60s)
   - **Sensor Mapping**: 300–3600 seconds (default: 600s)
7. Optionally enable **Include Inactive Sensors** to see offline devices

### Finding Your Gateway IP

Check your router's connected device list or use a network scanner. The gateway hostname usually starts with `GW` or `EWS`.

## 📱 Supported Hardware

### Gateways

| Model | Status |
|---|---|
| GW1000 | ✅ Supported |
| GW1100 / GW1100A | ✅ Supported (primary development hardware) |
| GW1200 | ✅ Supported |
| GW2000 / GW2000A | ✅ Supported |
| GW3000 | ✅ Supported |

### Sensors

| Sensor | Description |
|---|---|
| **WH25** | Indoor temperature, humidity, barometric pressure |
| **WH26 / WN32** | Outdoor temperature & humidity |
| **WH31** | Multi-channel temperature & humidity (CH1–8) |
| **WH34** | Multi-channel temperature only (CH1–8) |
| **WH35** | Leaf wetness (CH1–8) |
| **WH40** | Traditional rain gauge |
| **WH41** | PM2.5 air quality (CH1–4) |
| **WH45 / WH46** | CO2 + PM2.5/PM10 combo sensor |
| **WH51** | Soil moisture (CH1–16) |
| **WH52** | Soil moisture + electrical conductivity (CH1–16) |
| **WH55** | Leak detection (CH1–4) |
| **WH57** | Lightning detection (strike count, distance, timestamp) |
| **WH68** | Weather station (temp, humidity, wind, solar, UV) |
| **WH69** | Weather station with piezo rain sensor |
| **WH80 / WS80** | Weather station |
| **WH90 / WS90** | Weather station with piezo rain and solar |
| **WN38** | Black Globe Thermometer (BGT + WBGT) |

> **Note**: All gateway-integrated sensors (pressure, indoor temp/hum, wind, rain from station combos) are also supported.

### What Is Not Supported

- Ecowitt cloud-only features (remote access, cloud history)
- Gateway configuration changes (this integration is read-only)
- Any Ecowitt devices that communicate only via the Ecowitt cloud app

## 📱 Device Organization

Each physical sensor becomes its own Home Assistant device:

**Soil Moisture Sensor (Hardware ID: D8174)**
```
🌱 Ecowitt Soil Moisture D8174
├── 💧 Soil Moisture (24%)          [Sensor]
├── 🔋 Battery (85%)                [Diagnostic]
├── 📶 Signal Strength (4)          [Diagnostic]
└── 🟢 Online Status                [Diagnostic]
```

**Weather Station (Hardware ID: A1B2C)**
```
🌤️ Ecowitt Weather Station A1B2C
├── 🌡️ Temperature (22.5°C)         [Sensor]
├── 💨 Humidity (45%)               [Sensor]
├── 🌪️ Wind Speed (12 km/h)         [Sensor]
├── 🔋 Battery (90%)                [Diagnostic]
├── 📶 Signal Strength (5)          [Diagnostic]
└── 🟢 Online Status                [Diagnostic]
```

## 🔧 Services

### `ecowitt_local.refresh_mapping`
Force refresh of sensor hardware ID mapping. Use this after adding new sensors or re-pairing existing ones.

### `ecowitt_local.update_data`
Force an immediate live data update. Useful for getting fresh readings before an automation runs.

## ⚠️ Migrating From the Webhook Integration

This integration uses **hardware-based entity IDs** instead of **channel-based IDs**.

| Old (unstable) | New (permanent) |
|---|---|
| `sensor.soil_moisture_1` | `sensor.ecowitt_soil_moisture_d8174` |
| `sensor.soil_moisture_2` | `sensor.ecowitt_soil_moisture_d8648` |

After installing, you will need to update:
- **Automations** — update entity IDs in triggers and conditions
- **Dashboards** — update cards with new entity IDs
- **Scripts** — update any hardcoded entity references

The integration logs which entities were created to help you identify the new IDs.

## 🐛 Troubleshooting

**Connection issues**: Verify the gateway IP is reachable from HA. Try opening the gateway web interface in a browser from the same network.

**Missing sensors**: Use the `refresh_mapping` service after adding new sensors. Check that the sensor is paired and active in the Ecowitt app. Enable "Include Inactive Sensors" to see offline devices.

**Wrong units**: Units are read from the gateway's current configuration. Change units in the Ecowitt app or gateway web interface, then restart the integration.

**Entities not updating**: Increase the live data polling interval if the gateway becomes unresponsive. Check HA logs for API errors.

## 🧪 Quality & Testing

- **100% test coverage** — every code path is tested
- **322+ automated tests** — device discovery, entity creation, hardware ID mapping, edge cases
- **Multiple Python versions** — tested on 3.11 and 3.12
- **Type-checked** — full mypy compliance
- **CI/CD pipeline** — all tests must pass before any release

Physical development hardware: **GW1100A** gateway with **WH51** soil moisture sensors.

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass: `PYTHONPATH="$PWD" python -m pytest tests/ -v`
5. Submit a pull request

See [CLAUDE.md](CLAUDE.md) for architecture details and development guidelines.

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- The Home Assistant community for feedback, bug reports, and hardware testing
- Ecowitt for reliable weather station hardware and a documented local API

## 📞 Support

- [GitHub Issues](https://github.com/alexlenk/ecowitt_local/issues) — bug reports and feature requests
- [GitHub Discussions](https://github.com/alexlenk/ecowitt_local/discussions) — questions and community support

---

**⭐ If this integration is useful to you, consider starring the repository!**
