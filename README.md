# Ecowitt Local Web Interface Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/alexlenk/ecowitt_local.svg)](https://github.com/alexlenk/ecowitt_local/releases)
[![License](https://img.shields.io/github/license/alexlenk/ecowitt_local.svg)](https://github.com/alexlenk/ecowitt_local/blob/main/LICENSE)
[![CI](https://github.com/alexlenk/ecowitt_local/workflows/CI/badge.svg)](https://github.com/alexlenk/ecowitt_local/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/alexlenk/ecowitt_local/branch/main/graph/badge.svg)](https://codecov.io/gh/alexlenk/ecowitt_local)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

A Home Assistant custom integration that replaces the webhook-based Ecowitt integration with local web interface polling to solve sensor ID stability issues.

## 🎯 Problem Solved

The existing Home Assistant Ecowitt integration relies on webhooks with fundamental limitations:
- **Unstable Entity IDs**: Channel-based naming that changes when batteries die
- **HTTP-Only**: Security vulnerability requiring non-encrypted endpoints  
- **Limited Data**: Missing battery levels, signal strength, and hardware IDs
- **Protocol Constraints**: Cannot be fixed within webhook paradigm

## ✅ Our Solution

**Hardware-Based Stable Entity IDs**: Use sensor hardware IDs for permanent entity identification
- `sensor.soil_moisture_1` → `sensor.ecowitt_soil_moisture_d8174`
- Entity IDs never change when batteries are replaced
- Perfect historical data continuity
- Automations that never break

## 🚀 Key Features

- **🔒 Enhanced Security**: No HTTP requirement, full HTTPS compatibility
- **📊 Rich Data**: Battery levels, signal strength, inactive sensors
- **🔄 Reliable Updates**: Direct polling instead of webhook dependency  
- **🏷️ Stable IDs**: Hardware-based entity naming that survives battery replacements
- **📱 HACS Compatible**: Easy installation and updates
- **🔧 Comprehensive Support**: All Ecowitt sensor types (soil, weather, air quality, etc.)

## 📋 Requirements

- Home Assistant Core 2024.1.0+
- Ecowitt Gateway (GW1000, GW1100A, GW2000, etc.) with firmware 2.0.0+
- Local network access to gateway web interface

## 🛠️ Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/alexlenk/ecowitt_local`
6. Select "Integration" as the category
7. Click "Add"
8. Find "Ecowitt Local" in the HACS integrations list
9. Click "Download"
10. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/ecowitt_local` folder
2. Copy it to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## ⚙️ Configuration

### Setup Integration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Ecowitt Local"
4. Enter your gateway IP address (e.g., `192.168.1.100`)
5. Enter gateway password (if required)
6. Configure polling intervals:
   - **Live Data**: 30-300 seconds (default: 60)
   - **Sensor Mapping**: 300-3600 seconds (default: 600)
7. Choose whether to include inactive sensors

### Find Your Gateway IP

Check your router's connected devices or use network scanning tools to find your Ecowitt gateway's IP address.

## 📊 Entity Examples

### Soil Moisture Sensors
```
sensor.ecowitt_soil_moisture_d8174          # Hardware ID D8174
sensor.ecowitt_soil_moisture_d8174_battery  # Battery level
binary_sensor.ecowitt_soil_moisture_d8174_online  # Online status
```

### Weather Sensors  
```
sensor.ecowitt_temperature_outdoor
sensor.ecowitt_humidity_outdoor
sensor.ecowitt_wind_speed
sensor.ecowitt_pressure_relative
```

### Air Quality
```
sensor.ecowitt_pm25_ch1_ef891               # Hardware ID EF891
sensor.ecowitt_pm25_ch1_ef891_battery       # Battery level
```

## 🔧 Services

The integration provides services for manual control:

### `ecowitt_local.refresh_mapping`
Force refresh of sensor hardware ID mapping

### `ecowitt_local.update_data`  
Force immediate update of live sensor data

## ⚠️ Breaking Changes from Original Integration

This integration uses **hardware-based entity IDs** instead of **channel-based IDs**:

**Old naming (unstable)**:
- `sensor.soil_moisture_1` ← Changes when batteries die
- `sensor.soil_moisture_2` ← Assignment depends on reconnection order

**New naming (permanent)**:  
- `sensor.ecowitt_soil_moisture_d8174` ← Never changes
- `sensor.ecowitt_soil_moisture_d8648` ← Hardware ID based

### Migration Required

You will need to update automations and dashboards to use new entity IDs. The integration provides tools to help with this transition.

## 🐛 Troubleshooting

### Connection Issues
- Verify gateway IP address is correct
- Ensure Home Assistant can reach the gateway on your network
- Check if gateway web interface is accessible via browser
- Confirm gateway firmware is 2.0.0+

### Authentication Issues  
- Verify password if gateway requires authentication
- Try accessing gateway web interface manually
- Some gateways may not require a password

### Missing Sensors
- Use "Refresh Sensor Mapping" service to update hardware mappings
- Check if sensors are properly paired with gateway
- Enable "Include Inactive Sensors" option to see offline devices

### Performance Issues
- Increase polling intervals if gateway becomes unresponsive
- Default settings work well for most setups
- Monitor Home Assistant logs for API errors

## 📝 Supported Sensors

- **Environmental**: Temperature, humidity, pressure, wind, rain, solar, UV
- **Soil Monitoring**: Moisture levels (CH1-16), soil temperature  
- **Air Quality**: PM2.5, PM10, CO2 (model dependent)
- **Specialized**: Leak detection, leaf wetness, lightning detection
- **System**: Battery levels, signal strength, gateway status

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Home Assistant team for the excellent platform
- Ecowitt for their weather station hardware
- Community for feedback and testing

## 📞 Support

- [GitHub Issues](https://github.com/alexlenk/ecowitt_local/issues) for bug reports
- [Home Assistant Community](https://community.home-assistant.io/) for questions
- [HACS Discord](https://discord.gg/apgchf8) for HACS-related support