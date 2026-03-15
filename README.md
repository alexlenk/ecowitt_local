# Ecowitt Local Web Interface Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-green.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/alexlenk/ecowitt_local.svg)](https://github.com/alexlenk/ecowitt_local/releases)
[![License](https://img.shields.io/github/license/alexlenk/ecowitt_local.svg)](https://github.com/alexlenk/ecowitt_local/blob/main/LICENSE)
[![CI](https://github.com/alexlenk/ecowitt_local/workflows/CI/badge.svg)](https://github.com/alexlenk/ecowitt_local/actions/workflows/ci.yml)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

Integrate your Ecowitt weather station with Home Assistant using **local network polling** — no cloud, no webhooks, no exposure of your Home Assistant to the internet.

The key feature is **stable entity IDs based on sensor hardware IDs**. When a battery dies and you replace it, your automations, dashboards, and history continue to work without any changes.

## ✅ What You Get

- **Entity IDs that never change** — based on the sensor's hardware ID, not its channel number
- **Each sensor is its own device** — with its own battery level, signal strength, and online status
- **No internet required** — the integration talks directly to your gateway over your local network
- **No HTTP exposure** — Home Assistant does not need to be reachable from the gateway
- **Configurable polling** — choose how often live data and sensor mappings are refreshed
- **Inactive sensor support** — optionally include sensors that are currently offline

```
sensor.ecowitt_soil_moisture_d8174   ← permanent, based on hardware ID
sensor.ecowitt_temperature_a1b2c3    ← never changes when battery is replaced
```

## 🛠️ Installation

Available in the **HACS default store** — no custom repository required.

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Search for **"Ecowitt Local"**
4. Click **Download** and restart Home Assistant

**Manual installation**: copy the `custom_components/ecowitt_local` folder to your `custom_components` directory and restart.

## ⚙️ Setup

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **"Ecowitt Local"**
3. Enter your gateway's IP address
4. Enter the gateway password if one is set (most gateways don't require this)
5. Optionally adjust polling intervals and whether to include inactive sensors

To find your gateway's IP address, check your router's connected devices list. The gateway hostname usually starts with `GW` or `EWS`.

## 📡 Supported Gateways

| Gateway | Supported |
|---|---|
| GW1000 | ✅ |
| GW1100 / GW1100A | ✅ |
| GW1200 | ✅ |
| GW2000 / GW2000A | ✅ |
| GW3000 | ✅ |

### Gateways that are NOT supported

The following devices use a different firmware or API and are **not compatible** with this integration:

| Device | Reason |
|---|---|
| **WS2910** | Different firmware — does not expose the local API endpoints this integration uses |
| **Ecowitt display units** (HP2550, HP2564, etc.) | Display-only units, no sensor mapping API |

If your gateway is not in either list and setup fails with a connection or 404 error, please [open an issue](https://github.com/alexlenk/ecowitt_local/issues) with your gateway model and firmware version.

## 🌡️ Supported Sensors

| Sensor | Description |
|---|---|
| **WH25** | Indoor temperature, humidity, barometric pressure |
| **WH26 / WN32** | Outdoor temperature, humidity, dew point |
| **WH31** | Multi-channel temperature & humidity (CH1–8) |
| **WH34** | Multi-channel temperature (CH1–8) |
| **WH35** | Leaf wetness (CH1–8) |
| **WH40** | Traditional rain gauge |
| **WH41** | PM2.5 air quality (CH1–4) |
| **WH45 / WH46D** | CO2 + PM1/PM2.5/PM4/PM10 combo |
| **WH51** | Soil moisture (CH1–16) |
| **WH52** | Soil moisture + electrical conductivity (CH1–16) |
| **WH55** | Leak detection (CH1–4) |
| **WH57** | Lightning (strike count, distance, last strike time) |
| **WH68** | Weather station (temp, humidity, wind, solar, UV) |
| **WH69** | Weather station with piezo rain |
| **WH80 / WS80** | Weather station |
| **WH90 / WS90** | Weather station with piezo rain and solar |
| **WN38** | Black Globe Thermometer (BGT + WBGT) |

All built-in gateway sensors (indoor temperature/humidity/pressure, wind, rain) are also supported.

## 📱 How Devices Are Organized

Each physical sensor gets its own Home Assistant device with relevant entities:

```
🌱 Ecowitt Soil Moisture D8174
├── 💧 Soil Moisture (24%)          [Sensor]
├── 🔋 Battery (85%)                [Diagnostic]
├── 📶 Signal Strength              [Diagnostic]
└── 🟢 Online Status                [Diagnostic]
```

Battery, signal strength, and online status are grouped under **Diagnostic** so they stay out of your main dashboard view.

## 🔧 Services

**`ecowitt_local.refresh_mapping`** — Force a fresh scan of sensor hardware IDs. Use this after pairing a new sensor or re-pairing an existing one.

**`ecowitt_local.update_data`** — Request an immediate live data update instead of waiting for the next polling interval.

## ⚠️ Migrating From the Webhook Integration

This integration uses hardware-based entity IDs, which are different from the channel-based IDs used by the built-in HA Ecowitt integration:

| Old (webhook, channel-based) | New (hardware ID-based) |
|---|---|
| `sensor.soil_moisture_1` | `sensor.ecowitt_soil_moisture_d8174` |
| `sensor.soil_moisture_2` | `sensor.ecowitt_soil_moisture_d8648` |

After installing you will need to update any automations, dashboard cards, and scripts that reference the old entity IDs. Check the Home Assistant logs for the new entity IDs after first setup.

## 🐛 Troubleshooting

**Can't connect / HTTP 404**: Verify the gateway IP is correct and reachable from Home Assistant. Open `http://[gateway-ip]/get_livedata_info` in a browser — if it returns JSON, the integration should work. If it returns a 404 or doesn't load, your gateway model is likely not supported (see the unsupported gateways list above).

**Missing sensors**: Use the `refresh_mapping` service after adding or re-pairing sensors. Enable "Include Inactive Sensors" to see sensors that are currently offline.

**Wrong units**: Units follow the gateway's current setting. Change them in the Ecowitt app or gateway web interface, then reload the integration.

**Entities not updating**: Check HA logs for API errors. If the gateway becomes unresponsive, try increasing the polling interval in the integration options.

## 🔄 Alternatives

If this integration doesn't fit your setup, there are two other options:

| | [HA Ecowitt](https://www.home-assistant.io/integrations/ecowitt/) (built-in) | [ha-ecowitt-iot](https://github.com/ecowitt-iot/ha-ecowitt-iot) (by Ecowitt) |
|---|---|---|
| **How it works** | Gateway pushes data to HA via webhook | Local HTTP polling |
| **HA must be reachable** | Yes (from gateway over HTTP) | No |
| **Gateway support** | All webhook-capable gateways | GW1200+ only |
| **Entity IDs** | Channel-based (change with battery) | Key-based (e.g. `tempf`) |
| **Battery / signal** | No | Yes |

## 🤝 Contributing

Contributions are welcome. Fork the repository, make your changes with tests, and open a pull request. See [CLAUDE.md](CLAUDE.md) for architecture details.

## 📜 License

MIT — see [LICENSE](LICENSE).

## 📞 Support

- [GitHub Issues](https://github.com/alexlenk/ecowitt_local/issues) — bugs and feature requests
- [GitHub Discussions](https://github.com/alexlenk/ecowitt_local/discussions) — questions

---

**⭐ If this integration is useful to you, consider starring the repository!**
