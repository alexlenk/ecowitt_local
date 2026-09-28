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
        # not in the table: keep the model instead of a generic name
        "wh90": "WH90",
        "WS85": "WS85",
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
    for sensor_type in outdoor:
        assert is_outdoor_sensor(sensor_type) is True, sensor_type
    for sensor_type in ("WH31", "WH34", "indoor"):
        assert is_outdoor_sensor(sensor_type) is False, sensor_type


def test_device_name_default():
    """Default gateway names (with CH) give the type-based name."""
    info = {"sensor_type": "WH34", "raw_data": {"name": "Temp CH1"}}
    assert device_name("D1", info) == "Ecowitt Temperature Sensor D1"
    assert device_name("D1", {"sensor_type": "WH31"}) == (
        "Ecowitt Temperature/Humidity Sensor D1"
    )
    assert device_name("D1", {}) == "Ecowitt Sensor D1"
    assert device_name("W90", {"sensor_type": "WH90"}) == "Ecowitt WH90 W90"


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
        "WH90": ("WH90", "Ecowitt WH90 A1"),
    }
    for sensor_type, (raw_name, expected) in cases.items():
        info = {
            "sensor_type": sensor_type,
            "channel": None,
            "raw_data": {"name": raw_name},
        }
        assert device_name("A1", info) == expected, sensor_type
