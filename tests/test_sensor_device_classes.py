"""Test sensor device class functionality."""
from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from unittest.mock import Mock, patch

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
        "name": "Outdoor Temperature"
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_outdoor_temperature",
        sensor_info=sensor_info
    )
    
    # Test the device class determination
    device_class = sensor._determine_device_class("tempf")
    assert device_class == "temperature"
    
    # Test native value
    assert sensor.native_value == 72.5


@pytest.mark.asyncio
async def test_battery_sensor_device_class(hass: HomeAssistant, mock_coordinator):
    """Test battery sensor device class assignment."""
    sensor_info = {
        "sensor_key": "soilbatt1",
        "hardware_id": "D8174",
        "category": "battery",
        "name": "Soil Moisture Battery"
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_soil_moisture_battery_d8174",
        sensor_info=sensor_info
    )
    
    # Test the device class determination
    device_class = sensor._determine_device_class("soilbatt1")
    assert device_class == "battery"
    
    # Test native value
    assert sensor.native_value == 85


@pytest.mark.asyncio
async def test_soil_moisture_sensor_device_class(hass: HomeAssistant, mock_coordinator):
    """Test soil moisture sensor device class assignment."""
    sensor_info = {
        "sensor_key": "soilmoisture1",
        "hardware_id": "D8174",
        "category": "sensor",
        "name": "Soil Moisture CH1"
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_soil_moisture_d8174",
        sensor_info=sensor_info
    )
    
    # Test the device class determination
    device_class = sensor._determine_device_class("soilmoisture1")
    assert device_class == "moisture"
    
    # Test native value
    assert sensor.native_value == 50


@pytest.mark.asyncio
async def test_pm25_sensor_device_class(hass: HomeAssistant, mock_coordinator):
    """Test PM2.5 sensor device class assignment."""
    sensor_info = {
        "sensor_key": "pm25_ch1",
        "hardware_id": "EF891",
        "category": "sensor",
        "name": "PM2.5 Air Quality CH1"
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_pm25_ef891",
        sensor_info=sensor_info
    )
    
    # Test the device class determination
    device_class = sensor._determine_device_class("pm25_ch1")
    assert device_class == "pm25"
    
    # Test native value
    assert sensor.native_value == 15.2


@pytest.mark.asyncio
async def test_unknown_sensor_device_class(hass: HomeAssistant, mock_coordinator):
    """Test unknown sensor device class handling."""
    # Add an unknown sensor to mock data
    mock_coordinator.data["unknown_sensor"] = 42.0
    
    sensor_info = {
        "sensor_key": "unknown_sensor",
        "hardware_id": None,
        "category": "sensor",
        "name": "Unknown Sensor"
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_unknown",
        sensor_info=sensor_info
    )
    
    # Test the device class determination - should return None
    device_class = sensor._determine_device_class("unknown_sensor")
    assert device_class is None
    
    # Test native value
    assert sensor.native_value == 42.0


@pytest.mark.asyncio
async def test_sensor_with_none_value(hass: HomeAssistant, mock_coordinator):
    """Test sensor handling None value."""
    # Set a sensor to None
    mock_coordinator.data["null_sensor"] = None
    
    sensor_info = {
        "sensor_key": "null_sensor",
        "hardware_id": None,
        "category": "sensor",
        "name": "Null Sensor"
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_null",
        sensor_info=sensor_info
    )
    
    # Test native value is None
    assert sensor.native_value is None


@pytest.mark.asyncio 
async def test_device_class_mapping_coverage(hass: HomeAssistant, mock_coordinator):
    """Test coverage of device class mappings."""
    test_cases = [
        ("tempf", "temperature"),
        ("temp1f", "temperature"), 
        ("humidity", "humidity"),
        ("humidity1", "humidity"),
        ("baromrelin", "atmospheric_pressure"),
        ("baromabsin", "atmospheric_pressure"),
        ("soilmoisture1", "moisture"),
        ("pm25_ch1", "pm25"),
        ("pm25batt1", "battery"),
        ("soilbatt1", "battery"),
        ("batt1", "battery"),
        ("windspeedmph", "wind_speed"),
        ("windgustmph", "wind_speed"),
        ("winddirection", "wind_speed"),
        ("solarradiation", "irradiance"),
        ("uv", "irradiance"),
        ("rainratein", "precipitation_intensity"),
        ("eventrainin", "precipitation"),
        ("hourlyrainin", "precipitation"),
        ("dailyrainin", "precipitation"),
        ("weeklyrainin", "precipitation"),
        ("monthlyrainin", "precipitation"),
        ("yearlyrainin", "precipitation"),
        ("totalrainin", "precipitation"),
        ("unknown_sensor", None)
    ]
    
    sensor_info = {
        "sensor_key": "test",
        "hardware_id": None,
        "category": "sensor",
        "name": "Test Sensor"
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.ecowitt_test",
        sensor_info=sensor_info
    )
    
    for sensor_key, expected_device_class in test_cases:
        device_class = sensor._determine_device_class(sensor_key)
        assert device_class == expected_device_class, f"Failed for {sensor_key}: expected {expected_device_class}, got {device_class}"