"""Device naming shared by device registry setup and entity device_info.

The integration registers each hardware-ID device in two places: once in
``__init__.py`` at setup, and again through every entity's ``device_info``
(which is also what creates devices for sensors paired while HA is running).
Both must produce the same name, otherwise whichever registers last wins and
entity friendly names (``has_entity_name``) inherit the wrong device name.
"""

from __future__ import annotations

import re
from typing import Any, Dict

_TYPE_NAMES: Dict[str, str] = {
    "wh51": "Soil Moisture Sensor",
    "wh52": "Soil Moisture & EC Sensor",
    "wh31": "Temperature/Humidity Sensor",
    "wh34": "Temperature Sensor",
    "wh35": "Leaf Wetness Sensor",
    "wh41": "PM2.5 Air Quality Sensor",
    "wh54": "Liquid Depth Sensor",
    "wh55": "Leak Sensor",
    "wh57": "Lightning Sensor",
    "wh40": "Rain Sensor",
    "wn20": "Rain Gauge",
    "wh68": "Weather Station",
    "wh69": "WH69 Weather Station",
    "wh65": "WH69 Weather Station",
    "ws90": "WS90 Weather Station",
    "wh90": "WS90 Weather Station",
    "wh80": "WS80 Weather Station",
    "ws80": "WS80 Weather Station",
    "wh85": "WS85 Wind & Rain Sensor",
    "ws85": "WS85 Wind & Rain Sensor",
    "wh45": "CO2 Air Quality Sensor",
    "wh46": "CO2 Air Quality Sensor",
    "wh25": "Indoor Station",
    "wh26": "Outdoor Temperature/Humidity Sensor",
    "wn32": "Outdoor Temperature/Humidity Sensor",
    "wn38": "Black Globe Temperature Sensor",
    "soil": "Soil Moisture Sensor",
    "soil_ec": "Soil Moisture & EC Sensor",
    "temp_hum": "Temperature/Humidity Sensor",
    "temp_only": "Temperature Sensor",
    "leaf_wetness": "Leaf Wetness Sensor",
    "pm25": "PM2.5 Air Quality Sensor",
    "lds": "Liquid Depth Sensor",
    "leak": "Leak Sensor",
    "lightning": "Lightning Sensor",
    "rain": "Rain Sensor",
    "weather_station": "Weather Station",
    "weather_station_wh69": "WH69 Weather Station",
    "weather_station_ws90": "WS90 Weather Station",
    "weather_station_wh90": "WS90 Weather Station",
    "combo": "CO2 Air Quality Sensor",
    "co2_pm": "CO2 Air Quality Sensor",
    "indoor_station": "Indoor Station",
    "outdoor_temp_hum": "Outdoor Temperature/Humidity Sensor",
    "bgt": "Black Globe Temperature Sensor",
}

_OUTDOOR_TYPES = {
    "wh51",
    "wh52",
    "wh35",
    "wh41",
    "wh54",
    "wh55",
    "wh57",
    "wh40",
    "wn20",
    "wh68",
    "wh69",
    "wh65",
    "ws90",
    "wh90",
    "wh80",
    "ws80",
    "wh85",
    "ws85",
    "wh26",
    "wn32",
    "wn38",
    "soil",
    "soil_ec",
    "leaf_wetness",
    "pm25",
    "lds",
    "leak",
    "lightning",
    "rain",
    "weather_station",
    "weather_station_wh69",
    "weather_station_ws90",
    "weather_station_wh90",
    "outdoor_temp_hum",
    "bgt",
}


def sensor_type_display_name(sensor_type: str) -> str:
    """Return the display name for a sensor type (e.g. "WH31").

    Types without a table entry keep their model ("WH99") rather than a
    generic "Sensor", so the device name still says what it is.
    """
    return _TYPE_NAMES.get(sensor_type.lower()) or sensor_type.upper() or "Sensor"


def is_outdoor_sensor(sensor_type: str) -> bool:
    """Return True if the sensor type is typically installed outdoors."""
    return sensor_type.lower() in _OUTDOOR_TYPES


def device_name(hardware_id: str, sensor_info: Dict[str, Any]) -> str:
    """Return the device name for a hardware-ID device.

    For a channel sensor, a gateway-side name without "CH{n}" means the user
    renamed it on the gateway (e.g. "Deep Freezer") rather than leaving the
    default "Temp & Humidity CH2", so it is used as the device name (issue #243).
    Non-channel sensors have default names without "CH{n}" ("Solar & Wind",
    "Lightning", "WH90"), so the rule must not apply to them.
    """
    raw_name = str(sensor_info.get("raw_data", {}).get("name", "")).strip()
    if (
        sensor_info.get("channel")
        and raw_name
        and not re.search(r"\bCH\s?\d+\b", raw_name, re.IGNORECASE)
    ):
        return raw_name
    type_name = sensor_type_display_name(sensor_info.get("sensor_type", ""))
    return f"Ecowitt {type_name} {hardware_id}"
