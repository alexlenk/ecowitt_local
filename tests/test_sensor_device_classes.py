"""Test sensor device class functionality."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant

from custom_components.ecowitt_local.sensor import EcowittLocalSensor


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = Mock()
    coordinator.data = {
        "tempf": 72.5,
        "humidity": 45.0,
        "baromrelin": 29.92,
        "soilmoisture1": 50,
        "soilbatt1": 85,
        "pm25_ch1": 15.2,
        "windspeedmph": 5.5,
    }
    coordinator.config_entry = Mock()
    coordinator.config_entry.entry_id = "test_entry"
    return coordinator


@pytest.mark.asyncio
async def test_temperature_sensor_device_class(hass: HomeAssistant, mock_coordinator):
    """Test temperature sensor device class assignment."""
    sensor_info = {
        "sensor_key": "tempf",
        "hardware_id": None,
        "category": "sensor",
        "name": "Outdoor Temperature",
        "device_class": "temperature",
        "state": 72.5,  # This is where native_value comes from
    }

    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_outdoor_temperature",
        sensor_info=sensor_info,
    )

    # Test that device class is set correctly
    assert sensor.device_class == SensorDeviceClass.TEMPERATURE
    # Test native value
    assert sensor.native_value == 72.5
    # Test state class for numeric sensor
    assert sensor.state_class == SensorStateClass.MEASUREMENT


@pytest.mark.asyncio
async def test_battery_sensor_device_class(hass: HomeAssistant, mock_coordinator):
    """Test battery sensor device class assignment."""
    sensor_info = {
        "sensor_key": "soilbatt1",
        "hardware_id": "D8174",
        "category": "battery",
        "name": "Soil Moisture Battery",
        "device_class": "battery",
        "state": 85,
    }

    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_soil_moisture_battery_d8174",
        sensor_info=sensor_info,
    )

    # Test that device class is set correctly
    assert sensor.device_class == SensorDeviceClass.BATTERY
    # Test native value
    assert sensor.native_value == 85
    # Test state class for battery sensor
    assert sensor.state_class == SensorStateClass.MEASUREMENT


@pytest.mark.asyncio
async def test_soil_moisture_sensor_device_class(hass: HomeAssistant, mock_coordinator):
    """Test soil moisture sensor device class assignment."""
    sensor_info = {
        "sensor_key": "soilmoisture1",
        "hardware_id": "D8174",
        "category": "sensor",
        "name": "Soil Moisture CH1",
        "device_class": "moisture",
        "state": 50,
    }

    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_soil_moisture_d8174",
        sensor_info=sensor_info,
    )

    # Test that device class is set correctly
    assert sensor.device_class == SensorDeviceClass.MOISTURE
    # Test native value
    assert sensor.native_value == 50
    # Test state class
    assert sensor.state_class == SensorStateClass.MEASUREMENT


@pytest.mark.asyncio
async def test_pm25_sensor_device_class(hass: HomeAssistant, mock_coordinator):
    """Test PM2.5 sensor device class assignment."""
    sensor_info = {
        "sensor_key": "pm25_ch1",
        "hardware_id": "EF891",
        "category": "sensor",
        "name": "PM2.5 Air Quality CH1",
        "device_class": "pm25",
        "state": 15.2,
    }

    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_pm25_ef891",
        sensor_info=sensor_info,
    )

    # Test that device class is set correctly
    assert sensor.device_class == SensorDeviceClass.PM25
    # Test native value
    assert sensor.native_value == 15.2


@pytest.mark.asyncio
async def test_unknown_device_class_handling(hass: HomeAssistant, mock_coordinator):
    """Test handling of unknown device class string."""
    sensor_info = {
        "sensor_key": "unknown_sensor",
        "hardware_id": None,
        "category": "sensor",
        "name": "Unknown Sensor",
        "device_class": "invalid_device_class",
        "state": 42.0,
    }

    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_unknown",
        sensor_info=sensor_info,
    )

    # Should handle invalid device class gracefully
    assert sensor.device_class is None
    # Test native value still works
    assert sensor.native_value == 42.0


@pytest.mark.asyncio
async def test_sensor_with_none_value(hass: HomeAssistant, mock_coordinator):
    """Test sensor handling None value."""
    sensor_info = {
        "sensor_key": "null_sensor",
        "hardware_id": None,
        "category": "sensor",
        "name": "Null Sensor",
        "device_class": None,
        "state": None,
    }

    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_null",
        sensor_info=sensor_info,
    )

    # Test native value is None
    assert sensor.native_value is None
    # No state class for None values
    assert sensor.state_class is None


@pytest.mark.asyncio
async def test_sensor_without_device_class(hass: HomeAssistant, mock_coordinator):
    """Test sensor without device_class in sensor_info."""
    sensor_info = {
        "sensor_key": "tempf",
        "hardware_id": None,
        "category": "sensor",
        "name": "Temperature",
        "state": 72.5,
        # No device_class specified
    }

    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_temp",
        sensor_info=sensor_info,
    )

    # Should not have device class if not specified
    assert sensor.device_class is None
    # But still work with native value
    assert sensor.native_value == 72.5
