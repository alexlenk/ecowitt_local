"""Constants for the Ecowitt Local integration."""
from __future__ import annotations

from typing import Final

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

# Device information
MANUFACTURER: Final = "Ecowitt"
DEFAULT_NAME: Final = "Ecowitt Gateway"

# Entity naming patterns
ENTITY_ID_FORMAT: Final = "{domain}.ecowitt_{sensor_type}_{identifier}"
DEVICE_ID_FORMAT: Final = "ecowitt_{gateway_id}"

# Sensor types and their properties
SENSOR_TYPES: Final = {
    # Temperature sensors
    "tempinf": {"name": "Indoor Temperature", "unit": "°C", "device_class": "temperature"},
    "tempf": {"name": "Outdoor Temperature", "unit": "°F", "device_class": "temperature"},
    "temp1f": {"name": "Temperature CH1", "unit": "°F", "device_class": "temperature"},
    "temp2f": {"name": "Temperature CH2", "unit": "°F", "device_class": "temperature"},
    "temp3f": {"name": "Temperature CH3", "unit": "°F", "device_class": "temperature"},
    "temp4f": {"name": "Temperature CH4", "unit": "°F", "device_class": "temperature"},
    "temp5f": {"name": "Temperature CH5", "unit": "°F", "device_class": "temperature"},
    "temp6f": {"name": "Temperature CH6", "unit": "°F", "device_class": "temperature"},
    "temp7f": {"name": "Temperature CH7", "unit": "°F", "device_class": "temperature"},
    "temp8f": {"name": "Temperature CH8", "unit": "°F", "device_class": "temperature"},
    
    # Humidity sensors
    "humidityin": {"name": "Indoor Humidity", "unit": "%", "device_class": "humidity"},
    "humidity": {"name": "Outdoor Humidity", "unit": "%", "device_class": "humidity"},
    "humidity1": {"name": "Humidity CH1", "unit": "%", "device_class": "humidity"},
    "humidity2": {"name": "Humidity CH2", "unit": "%", "device_class": "humidity"},
    "humidity3": {"name": "Humidity CH3", "unit": "%", "device_class": "humidity"},
    "humidity4": {"name": "Humidity CH4", "unit": "%", "device_class": "humidity"},
    "humidity5": {"name": "Humidity CH5", "unit": "%", "device_class": "humidity"},
    "humidity6": {"name": "Humidity CH6", "unit": "%", "device_class": "humidity"},
    "humidity7": {"name": "Humidity CH7", "unit": "%", "device_class": "humidity"},
    "humidity8": {"name": "Humidity CH8", "unit": "%", "device_class": "humidity"},
    
    # Pressure sensors
    "baromrelin": {"name": "Relative Pressure", "unit": "hPa", "device_class": "atmospheric_pressure"},
    "baromabsin": {"name": "Absolute Pressure", "unit": "hPa", "device_class": "atmospheric_pressure"},
    
    # Wind sensors
    "windspeedmph": {"name": "Wind Speed", "unit": "mph", "device_class": "wind_speed"},
    "windspdmph_avg10m": {"name": "Wind Speed 10min Avg", "unit": "mph", "device_class": "wind_speed"},
    "windgustmph": {"name": "Wind Gust", "unit": "mph", "device_class": "wind_speed"},
    "maxdailygust": {"name": "Max Daily Gust", "unit": "mph", "device_class": "wind_speed"},
    "winddir": {"name": "Wind Direction", "unit": "°", "icon": "mdi:compass"},
    "winddir_avg10m": {"name": "Wind Direction 10min Avg", "unit": "°", "icon": "mdi:compass"},
    
    # Rain sensors
    "rainratein": {"name": "Rain Rate", "unit": "in/hr", "device_class": "precipitation_intensity"},
    "eventrainin": {"name": "Event Rain", "unit": "in", "device_class": "precipitation"},
    "hourlyrainin": {"name": "Hourly Rain", "unit": "in", "device_class": "precipitation"},
    "dailyrainin": {"name": "Daily Rain", "unit": "in", "device_class": "precipitation"},
    "weeklyrainin": {"name": "Weekly Rain", "unit": "in", "device_class": "precipitation"},
    "monthlyrainin": {"name": "Monthly Rain", "unit": "in", "device_class": "precipitation"},
    "yearlyrainin": {"name": "Yearly Rain", "unit": "in", "device_class": "precipitation"},
    "totalrainin": {"name": "Total Rain", "unit": "in", "device_class": "precipitation"},
    
    # Solar and UV sensors
    "solarradiation": {"name": "Solar Radiation", "unit": "W/m²", "device_class": "irradiance"},
    "uv": {"name": "UV Index", "unit": "UV Index", "icon": "mdi:weather-sunny-alert"},
    
    # Soil sensors
    "soilmoisture1": {"name": "Soil Moisture CH1", "unit": "%", "device_class": "moisture"},
    "soilmoisture2": {"name": "Soil Moisture CH2", "unit": "%", "device_class": "moisture"},
    "soilmoisture3": {"name": "Soil Moisture CH3", "unit": "%", "device_class": "moisture"},
    "soilmoisture4": {"name": "Soil Moisture CH4", "unit": "%", "device_class": "moisture"},
    "soilmoisture5": {"name": "Soil Moisture CH5", "unit": "%", "device_class": "moisture"},
    "soilmoisture6": {"name": "Soil Moisture CH6", "unit": "%", "device_class": "moisture"},
    "soilmoisture7": {"name": "Soil Moisture CH7", "unit": "%", "device_class": "moisture"},
    "soilmoisture8": {"name": "Soil Moisture CH8", "unit": "%", "device_class": "moisture"},
    "soilmoisture9": {"name": "Soil Moisture CH9", "unit": "%", "device_class": "moisture"},
    "soilmoisture10": {"name": "Soil Moisture CH10", "unit": "%", "device_class": "moisture"},
    "soilmoisture11": {"name": "Soil Moisture CH11", "unit": "%", "device_class": "moisture"},
    "soilmoisture12": {"name": "Soil Moisture CH12", "unit": "%", "device_class": "moisture"},
    "soilmoisture13": {"name": "Soil Moisture CH13", "unit": "%", "device_class": "moisture"},
    "soilmoisture14": {"name": "Soil Moisture CH14", "unit": "%", "device_class": "moisture"},
    "soilmoisture15": {"name": "Soil Moisture CH15", "unit": "%", "device_class": "moisture"},
    "soilmoisture16": {"name": "Soil Moisture CH16", "unit": "%", "device_class": "moisture"},
    
    # Air quality sensors
    "pm25_ch1": {"name": "PM2.5 CH1", "unit": "µg/m³", "device_class": "pm25"},
    "pm25_ch2": {"name": "PM2.5 CH2", "unit": "µg/m³", "device_class": "pm25"},
    "pm25_ch3": {"name": "PM2.5 CH3", "unit": "µg/m³", "device_class": "pm25"},
    "pm25_ch4": {"name": "PM2.5 CH4", "unit": "µg/m³", "device_class": "pm25"},
    "pm25_avg_24h_ch1": {"name": "PM2.5 24h Avg CH1", "unit": "µg/m³", "device_class": "pm25"},
    "pm25_avg_24h_ch2": {"name": "PM2.5 24h Avg CH2", "unit": "µg/m³", "device_class": "pm25"},
    "pm25_avg_24h_ch3": {"name": "PM2.5 24h Avg CH3", "unit": "µg/m³", "device_class": "pm25"},
    "pm25_avg_24h_ch4": {"name": "PM2.5 24h Avg CH4", "unit": "µg/m³", "device_class": "pm25"},
    
    # Leak sensors
    "leak_ch1": {"name": "Leak Sensor CH1", "device_class": "moisture"},
    "leak_ch2": {"name": "Leak Sensor CH2", "device_class": "moisture"},
    "leak_ch3": {"name": "Leak Sensor CH3", "device_class": "moisture"},
    "leak_ch4": {"name": "Leak Sensor CH4", "device_class": "moisture"},
    
    # Lightning sensor
    "lightning_num": {"name": "Lightning Strikes", "unit": "strikes", "icon": "mdi:flash"},
    "lightning_time": {"name": "Last Lightning", "device_class": "timestamp"},
    "lightning": {"name": "Lightning Distance", "unit": "km", "device_class": "distance"},
    
    # Leaf wetness sensors
    "leafwetness_ch1": {"name": "Leaf Wetness CH1", "unit": "%", "device_class": "moisture"},
    "leafwetness_ch2": {"name": "Leaf Wetness CH2", "unit": "%", "device_class": "moisture"},
    "leafwetness_ch3": {"name": "Leaf Wetness CH3", "unit": "%", "device_class": "moisture"},
    "leafwetness_ch4": {"name": "Leaf Wetness CH4", "unit": "%", "device_class": "moisture"},
    "leafwetness_ch5": {"name": "Leaf Wetness CH5", "unit": "%", "device_class": "moisture"},
    "leafwetness_ch6": {"name": "Leaf Wetness CH6", "unit": "%", "device_class": "moisture"},
    "leafwetness_ch7": {"name": "Leaf Wetness CH7", "unit": "%", "device_class": "moisture"},
    "leafwetness_ch8": {"name": "Leaf Wetness CH8", "unit": "%", "device_class": "moisture"},
}

# Battery sensors (companion to main sensors)
BATTERY_SENSORS: Final = {
    "soilbatt1": {"name": "Soil Moisture CH1 Battery", "sensor_key": "soilmoisture1"},
    "soilbatt2": {"name": "Soil Moisture CH2 Battery", "sensor_key": "soilmoisture2"},
    "soilbatt3": {"name": "Soil Moisture CH3 Battery", "sensor_key": "soilmoisture3"},
    "soilbatt4": {"name": "Soil Moisture CH4 Battery", "sensor_key": "soilmoisture4"},
    "soilbatt5": {"name": "Soil Moisture CH5 Battery", "sensor_key": "soilmoisture5"},
    "soilbatt6": {"name": "Soil Moisture CH6 Battery", "sensor_key": "soilmoisture6"},
    "soilbatt7": {"name": "Soil Moisture CH7 Battery", "sensor_key": "soilmoisture7"},
    "soilbatt8": {"name": "Soil Moisture CH8 Battery", "sensor_key": "soilmoisture8"},
    "soilbatt9": {"name": "Soil Moisture CH9 Battery", "sensor_key": "soilmoisture9"},
    "soilbatt10": {"name": "Soil Moisture CH10 Battery", "sensor_key": "soilmoisture10"},
    "soilbatt11": {"name": "Soil Moisture CH11 Battery", "sensor_key": "soilmoisture11"},
    "soilbatt12": {"name": "Soil Moisture CH12 Battery", "sensor_key": "soilmoisture12"},
    "soilbatt13": {"name": "Soil Moisture CH13 Battery", "sensor_key": "soilmoisture13"},
    "soilbatt14": {"name": "Soil Moisture CH14 Battery", "sensor_key": "soilmoisture14"},
    "soilbatt15": {"name": "Soil Moisture CH15 Battery", "sensor_key": "soilmoisture15"},
    "soilbatt16": {"name": "Soil Moisture CH16 Battery", "sensor_key": "soilmoisture16"},
    "batt1": {"name": "Temperature/Humidity CH1 Battery", "sensor_key": "temp1f"},
    "batt2": {"name": "Temperature/Humidity CH2 Battery", "sensor_key": "temp2f"},
    "batt3": {"name": "Temperature/Humidity CH3 Battery", "sensor_key": "temp3f"},
    "batt4": {"name": "Temperature/Humidity CH4 Battery", "sensor_key": "temp4f"},
    "batt5": {"name": "Temperature/Humidity CH5 Battery", "sensor_key": "temp5f"},
    "batt6": {"name": "Temperature/Humidity CH6 Battery", "sensor_key": "temp6f"},
    "batt7": {"name": "Temperature/Humidity CH7 Battery", "sensor_key": "temp7f"},
    "batt8": {"name": "Temperature/Humidity CH8 Battery", "sensor_key": "temp8f"},
    "wh57batt": {"name": "Lightning Sensor Battery", "sensor_key": "lightning"},
    "wh40batt": {"name": "Rain Sensor Battery", "sensor_key": "rainratein"},
    "wh68batt": {"name": "Weather Station Battery", "sensor_key": "tempf"},
    "pm25batt1": {"name": "PM2.5 CH1 Battery", "sensor_key": "pm25_ch1"},
    "pm25batt2": {"name": "PM2.5 CH2 Battery", "sensor_key": "pm25_ch2"},
    "pm25batt3": {"name": "PM2.5 CH3 Battery", "sensor_key": "pm25_ch3"},
    "pm25batt4": {"name": "PM2.5 CH4 Battery", "sensor_key": "pm25_ch4"},
    "leakbatt1": {"name": "Leak Sensor CH1 Battery", "sensor_key": "leak_ch1"},
    "leakbatt2": {"name": "Leak Sensor CH2 Battery", "sensor_key": "leak_ch2"},
    "leakbatt3": {"name": "Leak Sensor CH3 Battery", "sensor_key": "leak_ch3"},
    "leakbatt4": {"name": "Leak Sensor CH4 Battery", "sensor_key": "leak_ch4"},
}

# System sensors
SYSTEM_SENSORS: Final = {
    "runtime": {"name": "Gateway Uptime", "unit": "days", "device_class": "duration"},
    "heap": {"name": "Gateway Heap Memory", "unit": "KB", "device_class": "data_size"},
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