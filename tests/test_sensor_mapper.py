"""Test the Ecowitt Local sensor mapper."""
from __future__ import annotations

import pytest

from custom_components.ecowitt_local.sensor_mapper import SensorMapper


@pytest.fixture
def sensor_mapper():
    """Create a sensor mapper for testing."""
    return SensorMapper()


@pytest.fixture
def mock_sensor_mappings():
    """Mock sensor mapping data."""
    return [
        {
            "id": "D8174",
            "img": "WH51",
            "name": "Soil moisture CH1",
            "batt": "85",
            "signal": "4",
        },
        {
            "id": "D8648",
            "img": "WH51",
            "name": "Soil moisture CH2",
            "batt": "78",
            "signal": "3",
        },
        {
            "id": "EF891",
            "img": "WH41",
            "name": "PM2.5 air quality sensor CH1",
            "batt": "92", 
            "signal": "4",
        },
        {
            "id": "A7C42",
            "img": "WH31",
            "name": "Temp & Humidity CH1",
            "batt": "88",
            "signal": "3",
        },
    ]


def test_update_mapping(sensor_mapper: SensorMapper, mock_sensor_mappings):
    """Test updating sensor mapping."""
    sensor_mapper.update_mapping(mock_sensor_mappings)
    
    # Test hardware ID retrieval
    assert sensor_mapper.get_hardware_id("soilmoisture1") == "D8174"
    assert sensor_mapper.get_hardware_id("soilmoisture2") == "D8648"
    assert sensor_mapper.get_hardware_id("pm25_ch1") == "EF891"
    assert sensor_mapper.get_hardware_id("temp1f") == "A7C42"
    
    # Test sensor info retrieval
    soil_info = sensor_mapper.get_sensor_info("D8174")
    assert soil_info["hardware_id"] == "D8174"
    assert soil_info["sensor_type"] == "WH51"
    assert soil_info["channel"] == "1"
    assert soil_info["battery"] == "85"


def test_generate_live_data_keys(sensor_mapper: SensorMapper):
    """Test generating live data keys."""
    # Test soil moisture sensor
    keys = sensor_mapper._generate_live_data_keys("WH51", "1")
    assert "soilmoisture1" in keys
    assert "soilbatt1" in keys
    
    # Test temperature/humidity sensor  
    keys = sensor_mapper._generate_live_data_keys("WH31", "1")
    assert "temp1f" in keys
    assert "humidity1" in keys
    assert "batt1" in keys
    
    # Test PM2.5 sensor
    keys = sensor_mapper._generate_live_data_keys("WH41", "1")
    assert "pm25_ch1" in keys
    assert "pm25batt1" in keys
    
    # Test invalid inputs
    keys = sensor_mapper._generate_live_data_keys("", "1")
    assert len(keys) == 0
    
    keys = sensor_mapper._generate_live_data_keys("WH51", "")
    assert len(keys) == 0


def test_generate_entity_id(sensor_mapper: SensorMapper, mock_sensor_mappings):
    """Test generating entity IDs."""
    sensor_mapper.update_mapping(mock_sensor_mappings)
    
    # Test with hardware ID
    entity_id, name = sensor_mapper.generate_entity_id("soilmoisture1", "D8174")
    assert entity_id == "sensor.ecowitt_soil_moisture_d8174"
    assert "Soil Moisture" in name
    
    # Test without hardware ID
    entity_id, name = sensor_mapper.generate_entity_id("tempf", None, "outdoor")
    assert entity_id == "sensor.ecowitt_temperature_outdoor"
    
    # Test battery sensor
    entity_id, name = sensor_mapper.generate_entity_id("soilbatt1", "D8174")
    assert entity_id == "sensor.ecowitt_soil_moisture_battery_d8174"
    assert "Battery" in name


def test_extract_sensor_type_from_key(sensor_mapper: SensorMapper):
    """Test extracting sensor type from key."""
    assert sensor_mapper._extract_sensor_type_from_key("tempf") == "temperature"
    assert sensor_mapper._extract_sensor_type_from_key("humidity1") == "humidity"
    assert sensor_mapper._extract_sensor_type_from_key("soilmoisture1") == "soil_moisture"
    assert sensor_mapper._extract_sensor_type_from_key("pm25_ch1") == "pm25"
    assert sensor_mapper._extract_sensor_type_from_key("windspeedmph") == "wind"
    assert sensor_mapper._extract_sensor_type_from_key("baromrelin") == "pressure"


def test_extract_identifier_from_key(sensor_mapper: SensorMapper):
    """Test extracting identifier from key."""
    assert sensor_mapper._extract_identifier_from_key("soilmoisture1") == "ch1"
    assert sensor_mapper._extract_identifier_from_key("temp2f") == "ch2"
    assert sensor_mapper._extract_identifier_from_key("pm25_ch3") == "ch3"
    assert sensor_mapper._extract_identifier_from_key("tempinf") == "indoor"
    assert sensor_mapper._extract_identifier_from_key("tempf") == "outdoor"
    assert sensor_mapper._extract_identifier_from_key("baromrelin") == "relative"
    assert sensor_mapper._extract_identifier_from_key("baromabsin") == "absolute"


def test_get_mapping_stats(sensor_mapper: SensorMapper, mock_sensor_mappings):
    """Test getting mapping statistics."""
    sensor_mapper.update_mapping(mock_sensor_mappings)
    
    stats = sensor_mapper.get_mapping_stats()
    assert stats["total_sensors"] == 4
    assert stats["mapped_keys"] > 0
    assert stats["sensor_types"] >= 3  # WH51, WH41, WH31


def test_get_all_hardware_ids(sensor_mapper: SensorMapper, mock_sensor_mappings):
    """Test getting all hardware IDs."""
    sensor_mapper.update_mapping(mock_sensor_mappings)
    
    hardware_ids = sensor_mapper.get_all_hardware_ids()
    assert "D8174" in hardware_ids
    assert "D8648" in hardware_ids
    assert "EF891" in hardware_ids
    assert "A7C42" in hardware_ids
    assert len(hardware_ids) == 4


def test_empty_mapping(sensor_mapper: SensorMapper):
    """Test behavior with empty mapping."""
    sensor_mapper.update_mapping([])
    
    assert sensor_mapper.get_hardware_id("soilmoisture1") is None
    assert sensor_mapper.get_sensor_info("D8174") is None
    assert len(sensor_mapper.get_all_hardware_ids()) == 0
    
    stats = sensor_mapper.get_mapping_stats()
    assert stats["total_sensors"] == 0
    assert stats["mapped_keys"] == 0


def test_invalid_sensor_data(sensor_mapper: SensorMapper):
    """Test handling invalid sensor data."""
    invalid_mappings = [
        {"id": "", "type": "WH51", "channel": "1"},  # Empty ID
        {"type": "WH51", "channel": "1"},  # Missing ID
        {"id": "D8174"},  # Missing type and channel
    ]
    
    sensor_mapper.update_mapping(invalid_mappings)
    
    # Should handle gracefully without crashing
    stats = sensor_mapper.get_mapping_stats()
    assert stats["total_sensors"] >= 0