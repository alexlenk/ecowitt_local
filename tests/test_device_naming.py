"""Tests for shared device naming (device_naming.py)."""

from __future__ import annotations

from custom_components.ecowitt_local.device_naming import (
    device_name,
    is_outdoor_sensor,
    sensor_type_display_name,
)


def test_sensor_type_display_name():
    """Known types get a specific name, unknown ones fall back to "Sensor"."""
    cases = {
        "WH51": "Soil Moisture Sensor",
        "wh31": "Temperature/Humidity Sensor",
        "WH41": "PM2.5 Air Quality Sensor",
        "WH55": "Leak Sensor",
        "WH57": "Lightning Sensor",
        "WH40": "Rain Sensor",
        "WH68": "Weather Station",
        "soil": "Soil Moisture Sensor",
        # previously missing from the entity-side tables (issue #244)
        "WH34": "Temperature Sensor",
        "WH35": "Leaf Wetness Sensor",
        "WH52": "Soil Moisture & EC Sensor",
        "WH54": "Liquid Depth Sensor",
        "temp_only": "Temperature Sensor",
        "leaf_wetness": "Leaf Wetness Sensor",
        "soil_ec": "Soil Moisture & EC Sensor",
        "lds": "Liquid Depth Sensor",
        # non-channel devices (issue #262)
        "WS90": "WS90 Weather Station",
        "wh90": "WS90 Weather Station",
        "WH69": "WH69 Weather Station",
        "wh65": "WH69 Weather Station",
        "WH80": "WS80 Weather Station",
        "ws80": "WS80 Weather Station",
        "WH85": "WS85 Wind & Rain Sensor",
        "WS85": "WS85 Wind & Rain Sensor",
        "WH45": "CO2 Air Quality Sensor",
        "wh46": "CO2 Air Quality Sensor",
        "WH25": "Indoor Station",
        "WH26": "Outdoor Temperature/Humidity Sensor",
        "wn32": "Outdoor Temperature/Humidity Sensor",
        "WN38": "Black Globe Temperature Sensor",
        "weather_station_ws90": "WS90 Weather Station",
        "weather_station_wh90": "WS90 Weather Station",
        "weather_station_wh69": "WH69 Weather Station",
        "combo": "CO2 Air Quality Sensor",
        "co2_pm": "CO2 Air Quality Sensor",
        "indoor_station": "Indoor Station",
        "outdoor_temp_hum": "Outdoor Temperature/Humidity Sensor",
        "bgt": "Black Globe Temperature Sensor",
        # not in the table: keep the model instead of a generic name
        "wh99": "WH99",
        "WH77": "WH77",
        "": "Sensor",
    }
    for sensor_type, expected in cases.items():
        assert sensor_type_display_name(sensor_type) == expected, sensor_type


def test_is_outdoor_sensor():
    """Outdoor types get suggested_area=Outdoor."""
    outdoor = [
        "WH51",
        "WH52",
        "WH35",
        "wh41",
        "WH54",
        "WH55",
        "WH57",
        "WH40",
        "WH68",
    ] + ["pm25", "soil_ec", "leaf_wetness", "lds"]
    # non-channel devices (issue #262)
    outdoor += ["WS90", "wh90", "WH69", "wh65", "WH80", "ws80", "WH85", "WS85"]
    outdoor += ["WH26", "wn32", "WN38", "outdoor_temp_hum", "bgt"]
    outdoor += ["weather_station_ws90", "weather_station_wh90", "weather_station_wh69"]
    for sensor_type in outdoor:
        assert is_outdoor_sensor(sensor_type) is True, sensor_type
    indoor = ["WH31", "WH34", "indoor", "WH25", "WH45", "wh46", "indoor_station"]
    for sensor_type in indoor:
        assert is_outdoor_sensor(sensor_type) is False, sensor_type


def test_device_name_default():
    """Default gateway names (with CH) give the type-based name."""
    info = {"sensor_type": "WH34", "raw_data": {"name": "Temp CH1"}}
    assert device_name("D1", info) == "Ecowitt Temperature Sensor D1"
    assert device_name("D1", {"sensor_type": "WH31"}) == (
        "Ecowitt Temperature/Humidity Sensor D1"
    )
    assert device_name("D1", {}) == "Ecowitt Sensor D1"
    assert device_name("W90", {"sensor_type": "WH90"}) == (
        "Ecowitt WS90 Weather Station W90"
    )
    assert device_name("X1", {"sensor_type": "WH99"}) == "Ecowitt WH99 X1"


def test_device_name_gateway_rename():
    """A name set on the gateway (no CH) becomes the device name (issue #243)."""
    info = {
        "sensor_type": "WH31",
        "channel": "2",
        "raw_data": {"name": " Deep Freezer "},
    }
    assert device_name("G1", info) == "Deep Freezer"


def test_device_name_channel_pattern_is_a_whole_word():
    """Only a standalone "CH{n}" marks a default name, not letters inside a word."""
    base = {"sensor_type": "WH31", "channel": "1"}
    renamed = ["Porch1", "Kitchen 2", "Beach2"]
    defaults = ["Temp & Humidity CH1", "Soil moisture CH10", "PM2.5 ch3", "Leak CH 4"]
    for raw_name in renamed:
        info = {**base, "raw_data": {"name": raw_name}}
        assert device_name("G1", info) == raw_name, raw_name
    for raw_name in defaults:
        info = {**base, "raw_data": {"name": raw_name}}
        assert device_name("G1", info) == "Ecowitt Temperature/Humidity Sensor G1"


def test_device_name_ignores_non_channel_default_names():
    """Non-channel defaults lack "CH{n}" too and must not be taken as renames."""
    cases = {
        "WH68": ("Solar & Wind", "Ecowitt Weather Station A1"),
        "WH57": ("Lightning", "Ecowitt Lightning Sensor A1"),
        "WH40": ("Rain", "Ecowitt Rain Sensor A1"),
        "WH90": ("WH90", "Ecowitt WS90 Weather Station A1"),
        "WH45": ("PM25 & PM10 & CO2", "Ecowitt CO2 Air Quality Sensor A1"),
        "WH85": ("Wind & Rain", "Ecowitt WS85 Wind & Rain Sensor A1"),
        "WH99": ("Future Sensor", "Ecowitt WH99 A1"),
    }
    for sensor_type, (raw_name, expected) in cases.items():
        info = {
            "sensor_type": sensor_type,
            "channel": None,
            "raw_data": {"name": raw_name},
        }
        assert device_name("A1", info) == expected, sensor_type
