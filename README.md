# Ecowitt Local Web Interface Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/alexlenk/ecowitt_local.svg)](https://github.com/alexlenk/ecowitt_local/releases)
[![License](https://img.shields.io/github/license/alexlenk/ecowitt_local.svg)](https://github.com/alexlenk/ecowitt_local/blob/main/LICENSE)
[![CI](https://github.com/alexlenk/ecowitt_local/workflows/CI/badge.svg)](https://github.com/alexlenk/ecowitt_local/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/alexlenk/ecowitt_local/branch/main/graph/badge.svg)](https://codecov.io/gh/alexlenk/ecowitt_local)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

A Home Assistant custom integration that replaces the webhook-based Ecowitt integration with local web interface polling to solve sensor ID stability issues and provide enhanced device organization.

## 🎯 Problem Solved

The existing Home Assistant Ecowitt integration relies on webhooks with fundamental limitations:
- **Unstable Entity IDs**: Channel-based naming that changes when batteries die
- **HTTP Exposure Required**: Must expose Home Assistant over HTTP for gateway webhook delivery
- **Limited Data**: Missing battery levels, signal strength, and hardware IDs
- **Poor Organization**: All sensors lumped under gateway device
- **Protocol Constraints**: Cannot be fixed within webhook paradigm

## ✅ Our Solution

**🏷️ Hardware-Based Stable Entity IDs**: Use sensor hardware IDs for permanent entity identification
- `sensor.soil_moisture_1` → `sensor.ecowitt_soil_moisture_d8174`
- Entity IDs never change when batteries are replaced
- Perfect historical data continuity
- Automations that never break

**📱 Individual Sensor Devices**: Each physical sensor gets its own Home Assistant device
- Soil moisture sensors as dedicated devices with moisture + battery + online status
- Weather sensors organized by function (temperature/humidity, wind, rain, etc.)
- Clean device tree matching your physical sensor setup

## 🚀 Key Features

### 🔒 Enhanced Security & Reliability
- **No HTTP exposure required** - Unlike webhook integration that requires HA accessible over HTTP
- **Direct polling** - More reliable than webhook dependency  
- **Robust error handling** - Continues working during network hiccups

### 📊 Rich Data & Monitoring
- **Battery levels** - Monitor all sensor batteries
- **Signal strength** - Track RF connection quality
- **Online status** - Know when sensors go offline
- **Inactive sensors** - Option to include offline devices
- **Hardware information** - Channel, device model, firmware version

### 🏠 Superior Device Organization  
- **Individual sensor devices** - Each physical sensor becomes a HA device
- **Diagnostic categorization** - Monitoring info in diagnostic section
- **Clean main view** - Focus on sensor data, not system health
- **Automatic device assignment** - Entities go to correct sensor devices

### 🔧 Developer & Maintainer Friendly
- **89% test coverage** - Comprehensive automated testing
- **Type safety** - Full mypy type checking
- **Code optimization** - Dynamic sensor generation reduces duplication
- **CI/CD pipeline** - Automated testing and quality checks

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

## 📱 Device Organization

### Individual Sensor Devices
Each physical sensor becomes its own Home Assistant device with relevant entities:

**Soil Moisture Sensor (Hardware ID: D8174)**
```
🌱 Ecowitt Soil Moisture D8174                 [Device]
├── 💧 Soil Moisture (24%)                     [Main View]
├── 🔋 Battery (85%)                          [Diagnostic]
├── 📶 Signal Strength (4)                    [Diagnostic] 
└── 🔧 Online Status                          [Diagnostic]
```

**Weather Station (Hardware ID: A1B2C)**
```
🌤️ Ecowitt Weather Station A1B2C             [Device]
├── 🌡️ Temperature (72.5°F)                   [Main View]
├── 💨 Humidity (45%)                         [Main View]
├── 🌪️ Wind Speed (12 mph)                    [Main View]
├── 🔋 Battery (90%)                          [Diagnostic]
├── 📶 Signal Strength (5)                    [Diagnostic]
└── 🔧 Online Status                          [Diagnostic]
```

### Clean UI Organization

**Main View** - Focus on sensor data:
- Temperature, humidity, soil moisture values
- Wind speed, rainfall amounts
- Air quality readings

**Diagnostic View** - Health monitoring:
- Battery levels and alerts
- Signal strength indicators  
- Online/offline status
- Hardware information (channel, model, firmware)

## 📊 Entity Examples

### Soil Moisture Sensors
```
sensor.ecowitt_soil_moisture_d8174          # Hardware ID D8174 (24%)
sensor.ecowitt_soil_moisture_d8174_battery  # Battery level (85%) [Diagnostic]
binary_sensor.ecowitt_soil_moisture_d8174_online  # Online status [Diagnostic]
sensor.ecowitt_soil_moisture_d8174_signal   # Signal strength [Diagnostic]
```

### Weather Sensors  
```
sensor.ecowitt_temperature_outdoor           # Outdoor temperature
sensor.ecowitt_humidity_outdoor              # Outdoor humidity  
sensor.ecowitt_wind_speed                    # Current wind speed
sensor.ecowitt_wind_gust                     # Wind gusts
sensor.ecowitt_pressure_relative             # Barometric pressure
sensor.ecowitt_pressure_absolute             # Absolute pressure
```

### Air Quality Sensors
```
sensor.ecowitt_pm25_ch1_ef891               # PM2.5 readings (Hardware ID EF891)
sensor.ecowitt_pm25_ch1_ef891_battery       # Battery level [Diagnostic]
sensor.ecowitt_pm25_ch1_ef891_signal        # Signal strength [Diagnostic]
binary_sensor.ecowitt_pm25_ch1_ef891_online # Online status [Diagnostic]
```

### Lightning Detection
```
sensor.ecowitt_lightning_e4f5a6             # Lightning strikes count (Hardware ID E4F5A6)
sensor.ecowitt_lightning_e4f5a6_distance    # Lightning distance (km/mi)
sensor.ecowitt_lightning_e4f5a6_time        # Last lightning timestamp
sensor.ecowitt_lightning_e4f5a6_battery     # Battery level [Diagnostic]
binary_sensor.ecowitt_lightning_e4f5a6_online # Online status [Diagnostic]
```

### Rain Gauge
```
sensor.ecowitt_rain_f6g7h8                  # Rain rate (Hardware ID F6G7H8)
sensor.ecowitt_rain_f6g7h8_daily            # Daily rainfall accumulation
sensor.ecowitt_rain_f6g7h8_hourly           # Hourly rainfall accumulation
sensor.ecowitt_rain_f6g7h8_weekly           # Weekly rainfall accumulation
sensor.ecowitt_rain_f6g7h8_monthly          # Monthly rainfall accumulation
sensor.ecowitt_rain_f6g7h8_yearly           # Yearly rainfall accumulation
sensor.ecowitt_rain_f6g7h8_total            # Total rainfall since reset
sensor.ecowitt_rain_f6g7h8_battery          # Battery level [Diagnostic]
binary_sensor.ecowitt_rain_f6g7h8_online    # Online status [Diagnostic]
```

### Air Quality Sensors
```
sensor.ecowitt_pm25_g8h9i0                  # PM2.5 current reading (Hardware ID G8H9I0)
sensor.ecowitt_pm25_g8h9i0_24h              # PM2.5 24-hour average
sensor.ecowitt_pm25_g8h9i0_battery          # Battery level [Diagnostic]
binary_sensor.ecowitt_pm25_g8h9i0_online    # Online status [Diagnostic]
```

### Leak Detection Sensors
```
sensor.ecowitt_leak_j1k2l3                  # Leak status (Hardware ID J1K2L3)
sensor.ecowitt_leak_j1k2l3_battery          # Battery level [Diagnostic]
binary_sensor.ecowitt_leak_j1k2l3_online    # Online status [Diagnostic]
```

### Multi-Sensor Combo Units (WH45)
```
sensor.ecowitt_co2_m4n5o6                   # CO2 concentration (Hardware ID M4N5O6)
sensor.ecowitt_co2_m4n5o6_24h               # CO2 24-hour average
sensor.ecowitt_pm25_m4n5o6                  # PM2.5 from combo sensor
sensor.ecowitt_pm10_m4n5o6                  # PM10 from combo sensor
sensor.ecowitt_temperature_m4n5o6           # Temperature from combo sensor
sensor.ecowitt_humidity_m4n5o6              # Humidity from combo sensor
sensor.ecowitt_combo_m4n5o6_battery         # Battery level [Diagnostic]
binary_sensor.ecowitt_combo_m4n5o6_online   # Online status [Diagnostic]
```

## 🔧 Services

The integration provides services for manual control:

### `ecowitt_local.refresh_mapping`
Force refresh of sensor hardware ID mapping
- **Use case**: After adding new sensors or changing gateway configuration
- **Target**: Specific device or all devices

### `ecowitt_local.update_data`  
Force immediate update of live sensor data
- **Use case**: Get fresh readings before automations run
- **Target**: Specific device or all devices

## ⚠️ Breaking Changes from Original Integration

This integration uses **hardware-based entity IDs** instead of **channel-based IDs**:

**Old naming (unstable)**:
- `sensor.soil_moisture_1` ← Changes when batteries die
- `sensor.soil_moisture_2` ← Assignment depends on reconnection order

**New naming (permanent)**:  
- `sensor.ecowitt_soil_moisture_d8174` ← Never changes
- `sensor.ecowitt_soil_moisture_d8648` ← Hardware ID based

### Migration & Device Organization

**From webhook integration**: Entities will be recreated with new IDs and organized into individual sensor devices

**From earlier versions**: Automatic migration reassigns entities to proper devices

You will need to update:
- 🏠 **Automations** - Update entity IDs in triggers and conditions
- 📊 **Dashboards** - Update cards with new entity IDs  
- 📜 **Scripts** - Update any hardcoded entity references
- 🔔 **Notifications** - Update entity IDs in notification templates

The integration provides detailed logging to help identify which entities need updating.

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
- Check diagnostic logs for sensor discovery issues

### Device Assignment Issues
- Entities should appear under individual sensor devices after installation
- For existing installations, restart Home Assistant to trigger migration
- Check logs for migration messages and any assignment failures
- Use the refresh mapping service if devices aren't organized correctly

### Performance Issues
- Increase polling intervals if gateway becomes unresponsive
- Default settings work well for most setups
- Monitor Home Assistant logs for API errors
- Consider reducing number of inactive sensors if performance is poor

## 📝 Supported Sensors

### Environmental Monitoring
- **Temperature & Humidity**: Indoor/outdoor, multi-channel (CH1-8)
- **Barometric Pressure**: Absolute and relative readings
- **Wind**: Speed, direction, gusts, averages
- **Precipitation**: Rate, hourly, daily, weekly, monthly totals
- **Solar & UV**: Radiation levels, UV index

### Soil & Plant Monitoring
- **Soil Moisture**: Multi-channel support (CH1-16)
- **Soil Temperature**: Per-channel readings
- **Leaf Wetness**: Plant moisture detection (CH1-8)

### Air Quality Monitoring
- **PM2.5**: Particulate matter with 24h averages (CH1-4)
- **PM10**: Where supported by sensor hardware
- **Air Quality Index**: Calculated values

### Specialized Sensors  
- **Leak Detection**: Water leak sensors (CH1-4)
- **Lightning Detection**: Strike count, distance, timing
- **Multi-sensor Units**: Combined temperature/humidity sensors

### System Monitoring
- **Battery Levels**: Individual sensor battery status
- **Signal Strength**: RF connection quality (RSSI)
- **Online Status**: Per-device connectivity monitoring
- **Gateway Health**: Uptime, memory usage, firmware info

## 🧪 Testing & Device Support Status

This integration is tested using a combination of **physical hardware** and **comprehensive mock data** to ensure reliability across all supported device types.

### ✅ **Tested with Physical Hardware**
- **WH51 Soil Moisture Sensors**: 6 active sensors (CH1-CH6) - *Primary development hardware*
- **Gateway Communication**: GW2000A with various firmware versions
- **Hardware ID Mapping**: Real sensor hardware IDs and battery monitoring
- **RF Signal Quality**: Live RSSI and signal strength data

### 🎯 **Tested with Comprehensive Mock Data**
All other sensor types are tested using detailed mock datasets derived from:
- **aioecowitt sensor mappings**: Authoritative EcoWitt protocol implementation
- **Real API responses**: Actual gateway responses from various hardware setups
- **Community contributions**: Mock data from users with different device types

**Mock-tested devices include:**
- **WH68**: Weather station (temp, humidity, wind, solar, UV) ✅ *Implemented*
- **WH31**: Temperature/humidity sensors (CH1-8) ✅ *Implemented*
- **WH57**: Lightning detector (strikes, distance, timestamp) ✅ *Implemented*
- **WH40**: Rain gauge (rate, accumulations, battery) ✅ *Implemented*
- **WH41**: PM2.5 air quality sensors (CH1-4) ✅ *Implemented*
- **WH45**: CO2/PM2.5/PM10 combo sensor ✅ *Implemented*
- **WH55**: Leak detection sensors (CH1-4) ✅ *Implemented*
- **WH25/WH26**: Indoor sensors ✅ *Implemented*
- **WH34**: Temperature-only sensors (CH1-8) ✅ *Implemented*
- **WH35**: Leaf wetness sensors (CH1-8) ✅ *Implemented*

### 🔬 **Testing Methodology**

**Mock Data Validation:**
- Cross-validated against aioecowitt's proven sensor mappings
- Based on real API response patterns from EcoWitt gateways
- Comprehensive test coverage for sensor discovery, entity creation, and hardware ID mapping
- Accurate battery level conversion (0-5 raw scale → 0-100% display)
- Accurate signal strength conversion (0-4 raw scale → 0-100% display)

**Regression Testing:**
- All tests must pass before new device types are added
- Existing soil moisture functionality protected from changes
- Entity ID stability verified across integration reloads
- Performance testing with large sensor counts (71+ devices)

**Quality Assurance:**
- **89% test coverage** maintained across all modules
- **96 automated tests** covering device discovery, mapping, and edge cases
- **Type safety** with full mypy compliance
- **CI/CD pipeline** prevents regressions

### 🚀 **Confidence Level**

**High confidence** for mock-tested devices because:
1. **Proven sensor mappings**: Uses aioecowitt's battle-tested sensor key mappings
2. **Real API patterns**: Mock data based on actual gateway responses
3. **Comprehensive testing**: Every sensor type has dedicated test coverage
4. **Conservative approach**: New devices added incrementally with thorough validation
5. **Community validation**: Mock data verified against user reports and documentation

**If you have hardware we don't physically test with**, please consider contributing mock data or reporting any issues to help improve support for your specific devices.

## 🔄 Version History & Latest Features

### v1.2.11+ - UI & Organization Improvements
- **Diagnostic categorization** - Battery, signal, online status moved to diagnostic section
- **Cleaner main view** - Focus on actual sensor readings
- **Enhanced device organization** - Individual sensor devices with proper entity assignment
- **Improved migration** - Better handling of existing installations

### v1.2.0+ - Code Optimization & Maintainability  
- **Dynamic sensor generation** - Reduced code duplication
- **Enhanced type safety** - Full mypy compliance
- **Improved test coverage** - 89% coverage with 96 passing tests
- **Better maintainability** - Easier to add new sensor types

### v1.1.0+ - Core Features
- **Hardware-based entity IDs** - Stable naming that survives battery changes
- **Individual sensor devices** - Each sensor gets its own HA device
- **Rich sensor data** - Battery, signal strength, hardware information
- **Local polling** - Reliable alternative to webhook-based approach

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with appropriate tests
4. Ensure all tests pass (`pytest tests/`)
5. Follow code style guidelines (`flake8`, `mypy`)
6. Submit a pull request

### Development Setup
```bash
# Clone repository
git clone https://github.com/alexlenk/ecowitt_local.git
cd ecowitt_local

# Install development dependencies  
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run type checking
mypy custom_components/ecowitt_local/

# Run linting
flake8 custom_components/ecowitt_local/
```

### Automated Releases

This project uses automated GitHub Actions workflows for releases:

- **Auto-PR**: When you push to a `claude/**` branch with a version bump, a PR is automatically created
- **Auto-Merge**: Once all CI checks pass, the PR is automatically merged
- **Auto-Release**: After merge to main, a GitHub release is created automatically with CHANGELOG notes

For details, see [`.github/workflows/README.md`](.github/workflows/README.md) and [`CLAUDE.md`](CLAUDE.md#-release-process).

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Home Assistant team for the excellent platform and integration framework
- Ecowitt for their reliable weather station hardware and local API
- Home Assistant community for feedback, testing, and feature requests
- Contributors who have helped improve the integration

## 📞 Support

- [GitHub Issues](https://github.com/alexlenk/ecowitt_local/issues) for bug reports and feature requests
- [GitHub Discussions](https://github.com/alexlenk/ecowitt_local/discussions) for questions and community support
- [Home Assistant Community](https://community.home-assistant.io/) for general Home Assistant questions
- [HACS Discord](https://discord.gg/apgchf8) for HACS-related support

---

**⭐ If this integration helps you, please consider starring the repository to support development!**