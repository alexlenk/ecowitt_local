"""Constants for the Ecowitt Local integration."""

from __future__ import annotations

from typing import Any, Dict, Final

# Integration domain
DOMAIN: Final = "ecowitt_local"

# Configuration keys
CONF_HOST: Final = "host"
CONF_PASSWORD: Final = "password"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_MAPPING_INTERVAL: Final = "mapping_interval"
CONF_INCLUDE_INACTIVE: Final = "include_inactive"

# Default values
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds
DEFAULT_MAPPING_INTERVAL: Final = 600  # seconds (10 minutes)
DEFAULT_INCLUDE_INACTIVE: Final = False

# API endpoints
API_LOGIN: Final = "/set_login_info"
API_LIVE_DATA: Final = "/get_livedata_info"
API_SENSORS: Final = "/get_sensors_info"
API_VERSION: Final = "/get_version"
API_UNITS: Final = "/get_units_info"
API_SOIL_CALIBRATION: Final = "/get_cli_soilad"

# Device information
MANUFACTURER: Final = "Ecowitt"
DEFAULT_NAME: Final = "Ecowitt Gateway"

# Entity naming patterns
ENTITY_ID_FORMAT: Final = "{domain}.ecowitt_{sensor_type}_{identifier}"
DEVICE_ID_FORMAT: Final = "ecowitt_{gateway_id}"

# Gateway built-in sensors (should not have individual hardware IDs)
GATEWAY_SENSORS: Final = {
    "tempinf",  # Indoor temperature
    "humidityin",  # Indoor humidity
    "baromabsin",  # Absolute pressure
    "baromrelin",  # Relative pressure
}


def _generate_channel_sensors(
    base_key: str, name_template: str, sensor_def: Dict[str, Any], max_channels: int
) -> Dict[str, Dict[str, Any]]:
    """Generate numbered channel sensors dynamically.

    Args:
        base_key: Base key for sensor (e.g., "temp", "humidity")
        name_template: Name template with {ch} placeholder
        sensor_def: Base sensor definition dict
        max_channels: Maximum number of channels to generate

    Returns:
        Dictionary of sensor definitions
    """
    sensors = {}
    for i in range(1, max_channels + 1):
        if not base_key.endswith("f"):
            key = f"{base_key}{i}"
        else:
            key = f"{base_key[:-1]}{i}f"

        if "_ch" in base_key:
            key = f"{base_key}{i}"
        elif base_key == "humidity":
            key = f"humidity{i}"
        elif base_key == "soilmoisture":
            key = f"soilmoisture{i}"
        # Note: "leafwetness_ch" also contains "_ch", so the if "_ch" branch above handles it

        name = name_template.format(ch=i)
        sensors[key] = {**sensor_def, "name": name}
    return sensors


# Sensor types and their properties
SENSOR_TYPES: Final[Dict[str, Dict[str, Any]]] = {
    # Temperature sensors
    "tempinf": {
        "name": "Indoor Temperature",
        "unit": "°C",
        "device_class": "temperature",
    },
    "tempf": {
        "name": "Outdoor Temperature",
        "unit": "°F",
        "device_class": "temperature",
    },
    "3": {
        "name": "Feels Like Temperature",
        "unit": "°C",
        "device_class": "temperature",
    },
    "5": {"name": "Vapor Pressure Deficit", "unit": "kPa", "device_class": "pressure"},
    # Humidity sensors
    "humidityin": {"name": "Indoor Humidity", "unit": "%", "device_class": "humidity"},
    "humidity": {"name": "Outdoor Humidity", "unit": "%", "device_class": "humidity"},
    # Pressure sensors
    "baromrelin": {
        "name": "Relative Pressure",
        "unit": "hPa",
        "device_class": "atmospheric_pressure",
    },
    "baromabsin": {
        "name": "Absolute Pressure",
        "unit": "hPa",
        "device_class": "atmospheric_pressure",
    },
    # Wind sensors
    "windspeedmph": {"name": "Wind Speed", "unit": "mph", "device_class": "wind_speed"},
    "windspdmph_avg10m": {
        "name": "Wind Speed 10min Avg",
        "unit": "mph",
        "device_class": "wind_speed",
    },
    "windgustmph": {"name": "Wind Gust", "unit": "mph", "device_class": "wind_speed"},
    "maxdailygust": {
        "name": "Max Daily Gust",
        "unit": "mph",
        "device_class": "wind_speed",
    },
    "winddir": {
        "name": "Wind Direction",
        "unit": "°",
        "icon": "mdi:compass",
        "state_class": "measurement_angle",
    },
    "winddir_avg10m": {
        "name": "Wind Direction 10min Avg",
        "unit": "°",
        "icon": "mdi:compass",
        "state_class": "measurement_angle",
    },
    # Rain sensors
    "rainratein": {
        "name": "Rain Rate",
        "unit": "in/hr",
        "device_class": "precipitation_intensity",
        "state_class": "measurement",
        "suggested_display_precision": 2,
    },
    "eventrainin": {
        "name": "Event Rain",
        "unit": "in",
        "device_class": "precipitation",
        "state_class": "total",
        "suggested_display_precision": 2,
    },
    "hourlyrainin": {
        "name": "Hourly Rain",
        "unit": "in",
        "device_class": "precipitation",
        "state_class": "total_increasing",
        "suggested_display_precision": 2,
    },
    "dailyrainin": {
        "name": "Daily Rain",
        "unit": "in",
        "device_class": "precipitation",
        "state_class": "total_increasing",
        "suggested_display_precision": 2,
    },
    "weeklyrainin": {
        "name": "Weekly Rain",
        "unit": "in",
        "device_class": "precipitation",
        "state_class": "total_increasing",
        "suggested_display_precision": 2,
    },
    "monthlyrainin": {
        "name": "Monthly Rain",
        "unit": "in",
        "device_class": "precipitation",
        "state_class": "total_increasing",
        "suggested_display_precision": 2,
    },
    "yearlyrainin": {
        "name": "Yearly Rain",
        "unit": "in",
        "device_class": "precipitation",
        "state_class": "total_increasing",
        "suggested_display_precision": 2,
    },
    "totalrainin": {
        "name": "Total Rain",
        "unit": "in",
        "device_class": "precipitation",
        "state_class": "total_increasing",
        "suggested_display_precision": 2,
    },
    # Solar and UV sensors
    "solarradiation": {
        "name": "Solar Radiation",
        "unit": "W/m²",
        "device_class": "irradiance",
    },
    "solar_lux": {
        "name": "Solar Illuminance",
        "unit": "lx",
        "device_class": "illuminance",
        "state_class": "measurement",
    },
    "uv": {"name": "UV Index", "unit": "UV Index", "icon": "mdi:weather-sunny-alert"},
    # Lightning sensor
    "lightning_num": {
        "name": "Lightning Strikes",
        "unit": "strikes",
        "icon": "mdi:flash",
    },
    "lightning_time": {"name": "Last Lightning", "device_class": "timestamp"},
    "lightning": {
        "name": "Lightning Distance",
        "unit": "km",
        "device_class": "distance",
    },
    "lightning_mi": {
        "name": "Lightning Distance",
        "unit": "mi",
        "device_class": "distance",
    },
    # WH45 combo sensor (CO2 + PM2.5 + PM10 + temp/humidity)
    "tf_co2": {
        "name": "CO2 Sensor Temperature",
        "unit": "°F",
        "device_class": "temperature",
    },
    "tf_co2c": {
        "name": "CO2 Sensor Temperature",
        "unit": "°C",
        "device_class": "temperature",
    },
    "humi_co2": {
        "name": "CO2 Sensor Humidity",
        "unit": "%",
        "device_class": "humidity",
    },
    "pm25_co2": {"name": "PM2.5", "unit": "µg/m³", "device_class": "pm25"},
    "pm25_24h_co2": {"name": "PM2.5 24h Avg", "unit": "µg/m³", "device_class": "pm25"},
    "pm10_co2": {"name": "PM10", "unit": "µg/m³", "device_class": "pm10"},
    "pm10_24h_co2": {"name": "PM10 24h Avg", "unit": "µg/m³", "device_class": "pm10"},
    "pm1_co2": {"name": "PM1.0", "unit": "µg/m³", "device_class": "pm1"},
    "pm1_24h_co2": {"name": "PM1.0 24h Avg", "unit": "µg/m³", "device_class": "pm1"},
    "pm4_co2": {"name": "PM4.0", "unit": "µg/m³", "device_class": "pm25"},
    "pm4_24h_co2": {"name": "PM4.0 24h Avg", "unit": "µg/m³", "device_class": "pm25"},
    # WH45/WH46D AQI index fields (dimensionless 0–500). Spec V1.0.6 §1 co2 block.
    "pm25_realaqi_co2": {
        "name": "PM2.5 AQI",
        "unit": "AQI",
        "icon": "mdi:air-filter",
        "state_class": "measurement",
    },
    "pm25_24haqi_co2": {
        "name": "PM2.5 24h AQI",
        "unit": "AQI",
        "icon": "mdi:air-filter",
        "state_class": "measurement",
    },
    "pm10_realaqi_co2": {
        "name": "PM10 AQI",
        "unit": "AQI",
        "icon": "mdi:air-filter",
        "state_class": "measurement",
    },
    "pm10_24haqi_co2": {
        "name": "PM10 24h AQI",
        "unit": "AQI",
        "icon": "mdi:air-filter",
        "state_class": "measurement",
    },
    "pm1_realaqi_co2": {
        "name": "PM1.0 AQI",
        "unit": "AQI",
        "icon": "mdi:air-filter",
        "state_class": "measurement",
    },
    "pm1_24haqi_co2": {
        "name": "PM1.0 24h AQI",
        "unit": "AQI",
        "icon": "mdi:air-filter",
        "state_class": "measurement",
    },
    "pm4_realaqi_co2": {
        "name": "PM4.0 AQI",
        "unit": "AQI",
        "icon": "mdi:air-filter",
        "state_class": "measurement",
    },
    "pm4_24haqi_co2": {
        "name": "PM4.0 24h AQI",
        "unit": "AQI",
        "icon": "mdi:air-filter",
        "state_class": "measurement",
    },
    "co2": {"name": "CO2", "unit": "ppm", "device_class": "carbon_dioxide"},
    "co2_24h": {"name": "CO2 24h Avg", "unit": "ppm", "device_class": "carbon_dioxide"},
    # Hex-ID sensors from common_list (spec V1.0.6 §1)
    # Indoor sensors — emitted via common_list by some firmware versions
    "0x01": {
        "name": "Indoor Temperature",
        "unit": "°C",
        "device_class": "temperature",
    },
    "0x06": {"name": "Indoor Humidity", "unit": "%", "device_class": "humidity"},
    "0x08": {
        "name": "Absolute Pressure",
        "unit": "hPa",
        "device_class": "atmospheric_pressure",
    },
    "0x09": {
        "name": "Relative Pressure",
        "unit": "hPa",
        "device_class": "atmospheric_pressure",
    },
    # Outdoor / weather-station sensors
    "0x02": {
        "name": "Outdoor Temperature",
        "unit": "°C",
        "device_class": "temperature",
    },
    "0x03": {
        "name": "Dewpoint Temperature",
        "unit": "°C",
        "device_class": "temperature",
    },
    "0x04": {
        "name": "Wind Chill",
        "unit": "°C",
        "device_class": "temperature",
    },
    "0x05": {
        "name": "Heat Index",
        "unit": "°C",
        "device_class": "temperature",
    },
    "0x07": {"name": "Outdoor Humidity", "unit": "%", "device_class": "humidity"},
    "0x0B": {"name": "Wind Speed", "unit": "m/s", "device_class": "wind_speed"},
    "0x0C": {"name": "Wind Gust", "unit": "m/s", "device_class": "wind_speed"},
    "0x19": {"name": "Max Daily Gust", "unit": "m/s", "device_class": "wind_speed"},
    "0x0A": {
        "name": "Wind Direction",
        "unit": "°",
        "icon": "mdi:compass",
        "state_class": "measurement_angle",
    },
    "0x6D": {
        "name": "Wind Direction Avg",
        "unit": "°",
        "icon": "mdi:compass",
        "state_class": "measurement_angle",
    },
    "0x15": {"name": "Solar Radiation", "unit": "W/m²", "device_class": "irradiance"},
    # 0x16 UV irradiance (µW/m²) — raw UV sensor value, distinct from 0x17 UV Index.
    # No HA device_class for µW/m² so we use a custom icon.
    "0x16": {
        "name": "UV Radiation",
        "unit": "µW/m²",
        "icon": "mdi:weather-sunny-alert",
        "state_class": "measurement",
    },
    "0x17": {"name": "UV Index", "unit": "UV Index", "icon": "mdi:weather-sunny-alert"},
    "0x0D": {
        "name": "Rain Event",
        "unit": "mm",
        "device_class": "precipitation",
        "state_class": "total",
        "suggested_display_precision": 1,
    },
    "0x0E": {
        "name": "Rain Rate",
        "unit": "mm/Hr",
        "device_class": "precipitation_intensity",
        "state_class": "measurement",
        "suggested_display_precision": 1,
    },
    "0x7C": {
        "name": "24-Hour Rain",
        "unit": "mm",
        "device_class": "precipitation",
        "state_class": "total_increasing",
        "suggested_display_precision": 1,
    },
    "0x10": {
        "name": "Daily Rain",
        "unit": "mm",
        "device_class": "precipitation",
        "state_class": "total_increasing",
        "suggested_display_precision": 1,
    },
    "0x11": {
        "name": "Weekly Rain",
        "unit": "mm",
        "device_class": "precipitation",
        "state_class": "total_increasing",
        "suggested_display_precision": 1,
    },
    "0x12": {
        "name": "Monthly Rain",
        "unit": "mm",
        "device_class": "precipitation",
        "state_class": "total_increasing",
        "suggested_display_precision": 1,
    },
    "0x13": {
        "name": "Yearly Rain",
        "unit": "mm",
        "device_class": "precipitation",
        "state_class": "total_increasing",
        "suggested_display_precision": 1,
    },
    # 0x14 Rain Totals — all-time cumulative rain (spec V1.0.6 §1, ITEM_RAINTOTALS)
    "0x14": {
        "name": "Total Rain",
        "unit": "mm",
        "device_class": "precipitation",
        "state_class": "total_increasing",
        "suggested_display_precision": 1,
    },
    # WN38 Black Globe Thermometer
    "0xA1": {
        "name": "Black Globe Temperature",
        "unit": "°C",
        "device_class": "temperature",
    },
    "0xA2": {
        "name": "WBGT",
        "unit": "°C",
        "device_class": "temperature",
    },
}

# Add dynamically generated channel sensors
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "tempf", "Temperature CH{ch}", {"unit": "°F", "device_class": "temperature"}, 8
    )
)
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "humidity", "Humidity CH{ch}", {"unit": "%", "device_class": "humidity"}, 8
    )
)
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "soilmoisture",
        "Soil Moisture CH{ch}",
        {"unit": "%", "device_class": "moisture"},
        16,
    )
)
# Add soil moisture AD (raw analog-to-digital) sensors
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "soilad",
        "Soil Moisture AD CH{ch}",
        {"icon": "mdi:sprout", "enabled_default": False},
        16,
    )
)

SENSOR_TYPES.update(
    _generate_channel_sensors(
        "pm25_ch", "PM2.5 CH{ch}", {"unit": "µg/m³", "device_class": "pm25"}, 4
    )
)
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "pm25_avg_24h_ch",
        "PM2.5 24h Avg CH{ch}",
        {"unit": "µg/m³", "device_class": "pm25"},
        4,
    )
)
# PM2.5 AQI indices (dimensionless 0–500) — distinct from concentrations above.
# Spec (V1.0.6 §1) ch_pm25 block: PM25_RealAQI, PM25_24HAQI.
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "pm25_aqi_realtime_ch",
        "PM2.5 AQI CH{ch}",
        {"unit": "AQI", "icon": "mdi:air-filter", "state_class": "measurement"},
        4,
    )
)
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "pm25_aqi_24h_ch",
        "PM2.5 24h AQI CH{ch}",
        {"unit": "AQI", "icon": "mdi:air-filter", "state_class": "measurement"},
        4,
    )
)
SENSOR_TYPES.update(_generate_channel_sensors("leak_ch", "Leak Sensor CH{ch}", {}, 4))
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "leafwetness_ch",
        "Leaf Wetness CH{ch}",
        {"unit": "%", "device_class": "moisture"},
        8,
    )
)

# WH54 liquid depth sensors (4 channels). Spec V1.0.6 §1 ch_lds block:
# air = distance from sensor to liquid surface; depth = liquid depth; both in
# mm (gateway always reports mm regardless of unit setting).
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "lds_air_ch",
        "Liquid Depth Air Gap CH{ch}",
        {"unit": "mm", "device_class": "distance", "state_class": "measurement"},
        4,
    )
)
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "lds_depth_ch",
        "Liquid Depth CH{ch}",
        {"unit": "mm", "device_class": "distance", "state_class": "measurement"},
        4,
    )
)
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "lds_voltage_ch",
        "Liquid Depth Sensor Voltage CH{ch}",
        {
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "entity_category": "diagnostic",
            "suggested_display_precision": 2,
        },
        4,
    )
)

# Add WH52 soil temperature sensors
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "soiltemp",
        "Soil Temperature CH{ch}",
        {"unit": "°C", "device_class": "temperature"},
        16,
    )
)

# Add WH52 soil electrical conductivity sensors
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "soilec",
        "Soil Conductivity CH{ch}",
        {"unit": "µS/cm", "device_class": "conductivity"},
        16,
    )
)

# Add temperature-only sensors (WH34)
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "tf_ch", "Temperature CH{ch}", {"unit": "°F", "device_class": "temperature"}, 8
    )
)

# Add temperature-only sensors Celsius (WH34)
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "tf_ch", "Temperature CH{ch}", {"unit": "°C", "device_class": "temperature"}, 8
    )
)

# Add dewpoint sensors (calculated from temp/humidity)
SENSOR_TYPES.update(
    _generate_channel_sensors(
        "dewpoint", "Dewpoint CH{ch}", {"unit": "°F", "device_class": "temperature"}, 8
    )
)

# WS90/WH90 voltage sensors (capacitor and battery)
SENSOR_TYPES.update(
    {
        "ws90cap_volt": {
            "name": "WS90 Capacitor Voltage",
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "entity_category": "diagnostic",
            "suggested_display_precision": 1,
        },
        "wh90cap_volt": {
            "name": "WH90 Capacitor Voltage",
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "entity_category": "diagnostic",
            "suggested_display_precision": 1,
        },
        "ws90_voltage": {
            "name": "WS90 Battery Voltage",
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "entity_category": "diagnostic",
            "suggested_display_precision": 2,
        },
        "wh90_voltage": {
            "name": "WH90 Battery Voltage",
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "entity_category": "diagnostic",
            "suggested_display_precision": 2,
        },
        "ws85cap_volt": {
            "name": "WS85 Capacitor Voltage",
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "entity_category": "diagnostic",
            "suggested_display_precision": 1,
        },
        "ws85_voltage": {
            "name": "WS85 Battery Voltage",
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "entity_category": "diagnostic",
            "suggested_display_precision": 2,
        },
    }
)


def _generate_battery_sensors(
    base_key: str, name_template: str, sensor_key_template: str, max_channels: int
) -> Dict[str, Dict[str, str]]:
    """Generate numbered battery sensors dynamically.

    Args:
        base_key: Base key for battery sensor (e.g., "soilbatt")
        name_template: Name template with {ch} placeholder
        sensor_key_template: Sensor key template with {ch} placeholder
        max_channels: Maximum number of channels to generate

    Returns:
        Dictionary of battery sensor definitions
    """
    sensors = {}
    for i in range(1, max_channels + 1):
        key = f"{base_key}{i}"
        name = name_template.format(ch=i)
        sensor_key = sensor_key_template.format(ch=i)
        sensors[key] = {"name": name, "sensor_key": sensor_key}
    return sensors


# Battery sensors (companion to main sensors)
BATTERY_SENSORS: Final = {
    # Fixed battery sensors
    "wh57batt": {"name": "Lightning Sensor Battery", "sensor_key": "lightning"},
    "wh40batt": {"name": "Rain Sensor Battery", "sensor_key": "rainratein"},
    "wh68batt": {"name": "Weather Station Battery", "sensor_key": "tempf"},
    "wh25batt": {"name": "Indoor Station Battery", "sensor_key": "tempinf"},
    "wh26batt": {"name": "Outdoor Sensor Battery", "sensor_key": "0x02"},
    "co2_batt": {"name": "CO2 Combo Sensor Battery", "sensor_key": "co2"},
    "wh80batt": {"name": "WH80 Weather Station Battery", "sensor_key": "0x02"},
    "wh69batt": {"name": "WH69 Weather Station Battery", "sensor_key": "0x02"},
    "ws90batt": {"name": "WS90 Weather Station Battery", "sensor_key": "0x02"},
    "wh90batt": {"name": "WH90 Weather Station Battery", "sensor_key": "0x02"},
    "wh77batt": {"name": "WH77 Multi-Sensor Station Battery", "sensor_key": "0x02"},
    "wn38batt": {"name": "WN38 Black Globe Thermometer Battery", "sensor_key": "0xA1"},
    "ws85batt": {"name": "WS85 Wind & Rain Battery", "sensor_key": "0x0B"},
}

# Add dynamically generated battery sensors
BATTERY_SENSORS.update(
    _generate_battery_sensors(
        "soilbatt", "Soil Moisture CH{ch} Battery", "soilmoisture{ch}", 16
    )
)
BATTERY_SENSORS.update(
    _generate_battery_sensors(
        "batt", "Temperature/Humidity CH{ch} Battery", "temp{ch}f", 8
    )
)
BATTERY_SENSORS.update(
    _generate_battery_sensors("pm25batt", "PM2.5 CH{ch} Battery", "pm25_ch{ch}", 4)
)
BATTERY_SENSORS.update(
    _generate_battery_sensors(
        "leakbatt", "Leak Sensor CH{ch} Battery", "leak_ch{ch}", 4
    )
)
BATTERY_SENSORS.update(
    _generate_battery_sensors("tf_batt", "Temperature CH{ch} Battery", "tf_ch{ch}", 8)
)
BATTERY_SENSORS.update(
    _generate_battery_sensors(
        "leaf_batt", "Leaf Wetness CH{ch} Battery", "leafwetness_ch{ch}", 8
    )
)
BATTERY_SENSORS.update(
    _generate_battery_sensors(
        "lds_batt", "Liquid Depth CH{ch} Battery", "lds_depth_ch{ch}", 4
    )
)

# System sensors
SYSTEM_SENSORS: Final = {
    "runtime": {"name": "Gateway Uptime", "unit": "days", "device_class": "duration"},
    "heap": {"name": "Gateway Heap Memory", "unit": "KB", "device_class": "data_size"},
}

# Binary sensors (exposed as HA binary_sensor entities, not regular sensors)
BINARY_SENSORS: Final = {
    "srain_piezo": {"name": "Rain State Piezo", "device_class": "moisture"},
}

# Signal strength sensors
SIGNAL_SENSORS: Final = [
    "rssi_",  # Prefix for RSSI sensors
]

# Attribute keys for enhanced sensor information
ATTR_HARDWARE_ID: Final = "hardware_id"
ATTR_CHANNEL: Final = "channel"
ATTR_BATTERY_LEVEL: Final = "battery_level"
ATTR_SIGNAL_STRENGTH: Final = "signal_strength"
ATTR_LAST_SEEN: Final = "last_seen"
ATTR_SENSOR_TYPE: Final = "sensor_type"
ATTR_DEVICE_MODEL: Final = "device_model"
ATTR_FIRMWARE_VERSION: Final = "firmware_version"

# Service names
SERVICE_REFRESH_MAPPING: Final = "refresh_mapping"
SERVICE_UPDATE_DATA: Final = "update_data"

# Error messages
ERROR_CANNOT_CONNECT: Final = "cannot_connect"
ERROR_INVALID_AUTH: Final = "invalid_auth"
ERROR_UNKNOWN: Final = "unknown"
