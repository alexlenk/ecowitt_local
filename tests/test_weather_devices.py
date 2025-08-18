"""Test weather device support (WH68, WH31, etc)."""
from __future__ import annotations

import pytest
from typing import Any, Dict

from custom_components.ecowitt_local.sensor_mapper import SensorMapper


class TestWH68WeatherStation:
    """Test WH68 weather station support."""

    def test_wh68_sensor_mapping(self, mock_wh68_sensor_mapping):
        """Test WH68 sensor mapping and key generation."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh68_sensor_mapping])
        
        # Verify hardware ID is stored
        assert "A1B2C3" in mapper.get_all_hardware_ids()
        
        # Test sensor info
        sensor_info = mapper.get_sensor_info("A1B2C3")
        assert sensor_info is not None
        assert sensor_info["sensor_type"] == "WH68"
        assert sensor_info["device_model"] == "wh68"
        assert sensor_info["battery"] == "2.8"
        assert sensor_info["signal"] == "4"

    def test_wh68_live_data_keys(self, mock_wh68_sensor_mapping):
        """Test WH68 generates correct live data keys."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh68_sensor_mapping])
        
        # Test key mappings for weather station sensors
        expected_keys = [
            "tempf", "humidity", "windspeedmph", "windspdmph_avg10m",
            "windgustmph", "maxdailygust", "winddir", "winddir_avg10m", 
            "baromrelin", "baromabsin", "solarradiation", "uv", "wh68batt"
        ]
        
        for key in expected_keys:
            hardware_id = mapper.get_hardware_id(key)
            assert hardware_id == "A1B2C3", f"Key {key} should map to A1B2C3"

    def test_wh68_entity_id_generation(self, mock_wh68_sensor_mapping):
        """Test WH68 entity ID generation."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh68_sensor_mapping])
        
        # Test temperature sensor
        entity_id, name = mapper.generate_entity_id("tempf", "A1B2C3")
        assert entity_id == "sensor.ecowitt_temperature_a1b2c3"
        assert "Temperature" in name
        
        # Test wind sensor  
        entity_id, name = mapper.generate_entity_id("windspeedmph", "A1B2C3")
        assert entity_id == "sensor.ecowitt_wind_a1b2c3"
        assert "Wind" in name
        
        # Test battery sensor
        entity_id, name = mapper.generate_entity_id("wh68batt", "A1B2C3")
        assert entity_id == "sensor.ecowitt_weather_station_battery_a1b2c3"
        assert "Battery" in name

    def test_wh68_multiple_weather_sensors(self, mock_wh68_live_data):
        """Test handling multiple weather sensors from same device."""
        mapper = SensorMapper()
        mapping = {
            "id": "A1B2C3",
            "img": "wh68", 
            "type": "1",
            "name": "Solar & Wind",
            "batt": "2.8",
            "signal": "4"
        }
        mapper.update_mapping([mapping])
        
        # Verify all sensors map to same hardware ID
        weather_keys = ["tempf", "humidity", "windspeedmph", "solarradiation", "uv"]
        for key in weather_keys:
            assert mapper.get_hardware_id(key) == "A1B2C3"


class TestWH31TempHumidity:
    """Test WH31 temperature/humidity sensor support."""

    def test_wh31_sensor_mapping(self, mock_wh31_sensor_mapping):
        """Test WH31 sensor mapping with channel extraction."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh31_sensor_mapping])
        
        # Verify mapping  
        assert "D1E2F3" in mapper.get_all_hardware_ids()
        
        sensor_info = mapper.get_sensor_info("D1E2F3")
        assert sensor_info is not None
        assert sensor_info["sensor_type"] == "WH31"
        assert sensor_info["channel"] == "1"  # Extracted from "CH1"
        assert sensor_info["battery"] == "85"

    def test_wh31_live_data_keys(self, mock_wh31_sensor_mapping):
        """Test WH31 generates channel-specific keys."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh31_sensor_mapping])
        
        # Test channel 1 mappings
        expected_keys = ["temp1f", "humidity1", "batt1"]
        for key in expected_keys:
            hardware_id = mapper.get_hardware_id(key)
            assert hardware_id == "D1E2F3", f"Key {key} should map to D1E2F3"

    def test_wh31_entity_id_generation(self, mock_wh31_sensor_mapping):
        """Test WH31 entity ID generation with channels."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh31_sensor_mapping])
        
        # Test temperature sensor
        entity_id, name = mapper.generate_entity_id("temp1f", "D1E2F3")
        assert entity_id == "sensor.ecowitt_temperature_d1e2f3"
        assert "Temperature" in name
        
        # Test humidity sensor
        entity_id, name = mapper.generate_entity_id("humidity1", "D1E2F3")  
        assert entity_id == "sensor.ecowitt_humidity_d1e2f3"
        assert "Humidity" in name
        
        # Test battery sensor
        entity_id, name = mapper.generate_entity_id("batt1", "D1E2F3")
        assert entity_id == "sensor.ecowitt_temperature_humidity_battery_d1e2f3"

    def test_wh31_multiple_channels(self):
        """Test multiple WH31 sensors with different channels."""
        mapper = SensorMapper()
        mappings = [
            {
                "id": "D1E2F3",
                "img": "wh31",
                "type": "6", 
                "name": "Temp & Humidity CH1",
                "batt": "85",
                "signal": "4"
            },
            {
                "id": "E4F5A6", 
                "img": "wh31",
                "type": "7",
                "name": "Temp & Humidity CH2", 
                "batt": "78",
                "signal": "3"
            }
        ]
        mapper.update_mapping(mappings)
        
        # Test channel separation
        assert mapper.get_hardware_id("temp1f") == "D1E2F3"
        assert mapper.get_hardware_id("temp2f") == "E4F5A6"
        assert mapper.get_hardware_id("humidity1") == "D1E2F3"
        assert mapper.get_hardware_id("humidity2") == "E4F5A6"


class TestWeatherDeviceIntegration:
    """Test integration of weather devices with existing soil sensors."""

    def test_mixed_device_mapping(self, mock_complete_sensor_mappings):
        """Test mapping with both soil and weather sensors."""
        mapper = SensorMapper()
        mapper.update_mapping(mock_complete_sensor_mappings)
        
        # Verify all hardware IDs are present
        hardware_ids = mapper.get_all_hardware_ids()
        assert "D8174" in hardware_ids  # Soil sensor
        assert "A1B2C3" in hardware_ids  # Weather station
        assert "D1E2F3" in hardware_ids  # Temp/humidity
        
        # Test mapping stats
        stats = mapper.get_mapping_stats()
        assert stats["total_sensors"] == 3
        assert stats["sensor_types"] >= 3  # WH51, WH68, WH31

    def test_no_mapping_conflicts(self, mock_complete_sensor_mappings):
        """Test no conflicts between device mappings.""" 
        mapper = SensorMapper()
        mapper.update_mapping(mock_complete_sensor_mappings)
        
        # Test soil sensor keys still work
        assert mapper.get_hardware_id("soilmoisture2") == "D8174"
        assert mapper.get_hardware_id("soilbatt2") == "D8174"
        
        # Test weather sensor keys work  
        assert mapper.get_hardware_id("tempf") == "A1B2C3"
        assert mapper.get_hardware_id("windspeedmph") == "A1B2C3"
        
        # Test temp/humidity keys work
        assert mapper.get_hardware_id("temp1f") == "D1E2F3"
        assert mapper.get_hardware_id("humidity1") == "D1E2F3"

    def test_entity_id_stability(self, mock_complete_sensor_mappings):
        """Test entity IDs remain stable across remapping."""
        mapper = SensorMapper()
        
        # Initial mapping
        mapper.update_mapping(mock_complete_sensor_mappings)
        
        # Get initial entity IDs
        soil_entity, _ = mapper.generate_entity_id("soilmoisture2", "D8174")
        weather_entity, _ = mapper.generate_entity_id("tempf", "A1B2C3") 
        temp_entity, _ = mapper.generate_entity_id("temp1f", "D1E2F3")
        
        # Remap (simulating integration reload)
        mapper.update_mapping(mock_complete_sensor_mappings)
        
        # Verify entity IDs unchanged
        soil_entity2, _ = mapper.generate_entity_id("soilmoisture2", "D8174")
        weather_entity2, _ = mapper.generate_entity_id("tempf", "A1B2C3")
        temp_entity2, _ = mapper.generate_entity_id("temp1f", "D1E2F3")
        
        assert soil_entity == soil_entity2
        assert weather_entity == weather_entity2 
        assert temp_entity == temp_entity2


class TestWeatherDeviceEdgeCases:
    """Test edge cases for weather device support."""

    def test_missing_channel_in_name(self):
        """Test handling sensor name without channel number."""
        mapper = SensorMapper()
        mapping = {
            "id": "TEST123",
            "img": "wh68",
            "type": "1",
            "name": "Weather Station",  # No CH in name
            "batt": "3.0", 
            "signal": "4"
        }
        mapper.update_mapping([mapping])
        
        # Should still work without channel extraction
        sensor_info = mapper.get_sensor_info("TEST123")
        assert sensor_info is not None
        assert sensor_info["channel"] == ""  # Empty channel

    def test_unknown_sensor_type(self):
        """Test handling unknown sensor types gracefully."""
        mapper = SensorMapper()
        mapping = {
            "id": "UNKNOWN1",
            "img": "wh99",  # Unknown type
            "type": "999",
            "name": "Unknown Device",
            "batt": "2.5",
            "signal": "3"
        }
        mapper.update_mapping([mapping])
        
        # Should store sensor info but not generate mappings
        sensor_info = mapper.get_sensor_info("UNKNOWN1")
        assert sensor_info is not None
        assert sensor_info["sensor_type"] == "WH99"

    def test_empty_hardware_id(self):
        """Test handling empty/missing hardware IDs."""
        mapper = SensorMapper()
        mapping = {
            "id": "",  # Empty ID
            "img": "wh68",
            "type": "1", 
            "name": "Test Device",
            "batt": "3.0",
            "signal": "4"
        }
        mapper.update_mapping([mapping])
        
        # Should be skipped
        assert len(mapper.get_all_hardware_ids()) == 0

    def test_mapping_error_handling(self):
        """Test error handling during mapping updates."""
        mapper = SensorMapper()
        
        # Test with malformed mapping data  
        bad_mappings = [
            {"id": "GOOD1", "img": "wh68", "type": "1", "name": "Good"},
            {"malformed": "data"},  # Missing required fields
            {"id": "GOOD2", "img": "wh31", "type": "6", "name": "Good CH1"}
        ]
        
        # Should not crash and should process valid entries
        mapper.update_mapping(bad_mappings)
        
        # Valid entries should be processed
        hardware_ids = mapper.get_all_hardware_ids()
        assert "GOOD1" in hardware_ids
        assert "GOOD2" in hardware_ids
        assert len(hardware_ids) == 2