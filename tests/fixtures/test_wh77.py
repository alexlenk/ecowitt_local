"""Test fixtures for WH77 Multi-Sensor Station testing.

This module provides realistic test data for validating the official Claude Code
bot's ability to implement device support following our documented patterns.
"""

# WH77 sensor mapping data - simulates what would come from gateway API
WH77_SENSOR_MAPPING = {
    "id": "C234", 
    "img": "wh77",
    "name": "Multi-Sensor Station",  # Key difference: name != img (like WH90 issue)
    "type": "52",
    "batt": "3", 
    "signal": "-65"
}

# WH77 live data - simulates sensor readings using hex IDs
WH77_LIVE_DATA = {
    "common_list": [
        {"id": "C234", "val": "23.5", "ch": "0x02"},  # Temperature
        {"id": "C234", "val": "65", "ch": "0x07"},    # Humidity
        {"id": "C234", "val": "12.5", "ch": "0x0B"},  # Wind Speed
        {"id": "C234", "val": "8.2", "ch": "0x0C"},   # Wind Gust
        {"id": "C234", "val": "180", "ch": "0x0A"},   # Wind Direction
        {"id": "C234", "val": "450", "ch": "0x15"},   # Solar Radiation
        {"id": "C234", "val": "5", "ch": "0x17"},     # UV Index
        {"id": "C234", "val": "22.1", "ch": "0x03"},  # Dewpoint
        {"id": "C234", "val": "200", "ch": "0x6D"},   # Wind Direction Avg
        {"id": "C234", "val": "15.8", "ch": "0x19"},  # Max Daily Gust
    ]
}

# Expected battery mapping (should be added to const.py)
WH77_BATTERY_MAPPING = {
    "wh77batt": {
        "name": "WH77 Multi-Sensor Station Battery",
        "sensor_key": "0x02"
    }
}

# Expected entities that should be created
WH77_EXPECTED_ENTITIES = [
    "sensor.ecowitt_outdoor_temperature_c234",
    "sensor.ecowitt_outdoor_humidity_c234", 
    "sensor.ecowitt_wind_speed_c234",
    "sensor.ecowitt_wind_gust_c234",
    "sensor.ecowitt_wind_direction_c234",
    "sensor.ecowitt_solar_radiation_c234",
    "sensor.ecowitt_uv_index_c234",
    "sensor.ecowitt_dewpoint_temperature_c234",
    "sensor.ecowitt_wind_direction_10min_avg_c234",
    "sensor.ecowitt_max_daily_gust_c234",
    "sensor.ecowitt_wh77_multi_sensor_station_battery_c234",
]

# Test validation data
WH77_TEST_SCENARIOS = {
    "device_type_mismatch": {
        "description": "Tests device type 'Multi-Sensor Station' vs 'wh77'",
        "pattern": "Device Type String Mismatch",
        "expected_fix": "Add device type matching to sensor_mapper.py",
        "architecture": "Reuse existing hex ID system"
    },
    "hex_id_usage": {
        "description": "Tests proper hex ID system usage", 
        "pattern": "Hex ID Sensor Mapping",
        "expected_behavior": "Use existing 0x02, 0x07, etc. definitions",
        "anti_pattern": "DO NOT create new hex ID definitions"
    },
    "entity_creation": {
        "description": "Tests entity creation and naming consistency",
        "expected_count": 11,  # 10 sensors + 1 battery
        "naming_pattern": "sensor.ecowitt_[sensor_type]_c234"
    }
}