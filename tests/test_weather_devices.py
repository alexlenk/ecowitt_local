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
        assert sensor_info["battery"] == "3"
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
        assert sensor_info["battery"] == "4"

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


class TestWH57LightningDetector:
    """Test WH57 lightning detector support."""

    def test_wh57_sensor_mapping(self, mock_wh57_sensor_mapping):
        """Test WH57 sensor mapping and key generation."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh57_sensor_mapping])
        
        # Verify hardware ID is stored
        assert "E4F5A6" in mapper.get_all_hardware_ids()
        
        # Test sensor info
        sensor_info = mapper.get_sensor_info("E4F5A6")
        assert sensor_info is not None
        assert sensor_info["sensor_type"] == "WH57"
        assert sensor_info["device_model"] == "wh57"
        assert sensor_info["battery"] == "4"
        assert sensor_info["signal"] == "4"
        assert sensor_info["channel"] == ""  # Lightning sensor has no channel

    def test_wh57_live_data_keys(self, mock_wh57_sensor_mapping):
        """Test WH57 generates correct live data keys."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh57_sensor_mapping])
        
        # Test key mappings for lightning sensor
        expected_keys = [
            "lightning_num", "lightning_time", "lightning", "wh57batt"
        ]
        
        for key in expected_keys:
            hardware_id = mapper.get_hardware_id(key)
            assert hardware_id == "E4F5A6", f"Key {key} should map to E4F5A6"

    def test_wh57_entity_id_generation(self, mock_wh57_sensor_mapping):
        """Test WH57 entity ID generation."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh57_sensor_mapping])
        
        # Test lightning count sensor
        entity_id, name = mapper.generate_entity_id("lightning_num", "E4F5A6")
        assert entity_id == "sensor.ecowitt_lightning_e4f5a6"
        assert "Lightning" in name
        
        # Test lightning time sensor  
        entity_id, name = mapper.generate_entity_id("lightning_time", "E4F5A6")
        assert entity_id == "sensor.ecowitt_lightning_e4f5a6"
        assert "Lightning" in name
        
        # Test lightning distance sensor
        entity_id, name = mapper.generate_entity_id("lightning", "E4F5A6")
        assert entity_id == "sensor.ecowitt_lightning_e4f5a6"
        assert "Lightning" in name
        
        # Test battery sensor
        entity_id, name = mapper.generate_entity_id("wh57batt", "E4F5A6")
        assert entity_id == "sensor.ecowitt_lightning_battery_e4f5a6"
        assert "Battery" in name

    def test_wh57_timestamp_sensor(self, mock_wh57_live_data):
        """Test handling of lightning timestamp data."""
        mapper = SensorMapper()
        mapping = {
            "id": "E4F5A6",
            "img": "wh57",
            "type": "26",
            "name": "Lightning",
            "batt": "90",
            "signal": "4"
        }
        mapper.update_mapping([mapping])
        
        # Verify timestamp sensor maps correctly
        assert mapper.get_hardware_id("lightning_time") == "E4F5A6"
        
        # Test entity ID for timestamp
        entity_id, name = mapper.generate_entity_id("lightning_time", "E4F5A6")
        assert "lightning" in entity_id.lower()

    def test_wh57_multiple_distance_units(self, mock_wh57_sensor_mapping):
        """Test WH57 supports both km and miles distance."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh57_sensor_mapping])
        
        # Both distance units should map to same hardware ID
        assert mapper.get_hardware_id("lightning") == "E4F5A6"  # km
        # Note: lightning_mi not currently mapped in sensor_mapper, but could be added

    def test_wh57_unique_sensor_type(self):
        """Test WH57 is unique environmental sensor type."""
        mapper = SensorMapper()
        
        # Lightning detector should be distinguishable from weather stations
        lightning_mapping = {
            "id": "LIGHTNING1",
            "img": "wh57", 
            "type": "26",
            "name": "Lightning",
            "batt": "85",
            "signal": "4"
        }
        
        weather_mapping = {
            "id": "WEATHER1",
            "img": "wh68",
            "type": "1", 
            "name": "Solar & Wind",
            "batt": "90",
            "signal": "4"
        }
        
        mapper.update_mapping([lightning_mapping, weather_mapping])
        
        # Different sensor types should not conflict
        assert mapper.get_hardware_id("lightning_num") == "LIGHTNING1"
        assert mapper.get_hardware_id("tempf") == "WEATHER1"
        assert mapper.get_hardware_id("wh57batt") == "LIGHTNING1"
        assert mapper.get_hardware_id("wh68batt") == "WEATHER1"


class TestWH40RainGauge:
    """Test WH40 rain gauge support."""

    def test_wh40_sensor_mapping(self, mock_wh40_sensor_mapping):
        """Test WH40 sensor mapping and key generation."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh40_sensor_mapping])
        
        # Verify hardware ID is stored
        assert "F6G7H8" in mapper.get_all_hardware_ids()
        
        # Test sensor info
        sensor_info = mapper.get_sensor_info("F6G7H8")
        assert sensor_info is not None
        assert sensor_info["sensor_type"] == "WH40"
        assert sensor_info["device_model"] == "wh40"
        assert sensor_info["battery"] == "3"
        assert sensor_info["signal"] == "4"
        assert sensor_info["channel"] == ""  # Rain gauge has no channel

    def test_wh40_live_data_keys(self, mock_wh40_sensor_mapping):
        """Test WH40 generates correct live data keys."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh40_sensor_mapping])
        
        # Test key mappings for rain gauge sensors
        expected_keys = [
            "rainratein", "eventrainin", "hourlyrainin", "dailyrainin",
            "weeklyrainin", "monthlyrainin", "yearlyrainin", "totalrainin",
            "wh40batt"
        ]
        
        for key in expected_keys:
            hardware_id = mapper.get_hardware_id(key)
            assert hardware_id == "F6G7H8", f"Key {key} should map to F6G7H8"

    def test_wh40_entity_id_generation(self, mock_wh40_sensor_mapping):
        """Test WH40 entity ID generation."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh40_sensor_mapping])
        
        # Test rain rate sensor
        entity_id, name = mapper.generate_entity_id("rainratein", "F6G7H8")
        assert entity_id == "sensor.ecowitt_rain_f6g7h8"
        assert "Rain" in name
        
        # Test daily rain sensor  
        entity_id, name = mapper.generate_entity_id("dailyrainin", "F6G7H8")
        assert entity_id == "sensor.ecowitt_rain_f6g7h8"
        assert "Rain" in name
        
        # Test total rain sensor
        entity_id, name = mapper.generate_entity_id("totalrainin", "F6G7H8")
        assert entity_id == "sensor.ecowitt_rain_f6g7h8"
        assert "Rain" in name
        
        # Test battery sensor
        entity_id, name = mapper.generate_entity_id("wh40batt", "F6G7H8")
        assert entity_id == "sensor.ecowitt_rain_battery_f6g7h8"
        assert "Battery" in name

    def test_wh40_multiple_rain_metrics(self, mock_wh40_live_data):
        """Test handling of multiple rain measurement types."""
        mapper = SensorMapper()
        mapping = {
            "id": "F6G7H8",
            "img": "wh40",
            "type": "3",
            "name": "Rain",
            "batt": "78",
            "signal": "4"
        }
        mapper.update_mapping([mapping])
        
        # Verify all rain sensors map to same hardware ID
        rain_sensors = [
            "rainratein", "eventrainin", "hourlyrainin", "dailyrainin",
            "weeklyrainin", "monthlyrainin", "yearlyrainin", "totalrainin"
        ]
        for sensor in rain_sensors:
            assert mapper.get_hardware_id(sensor) == "F6G7H8"

    def test_wh40_precipitation_units(self, mock_wh40_sensor_mapping):
        """Test WH40 supports imperial precipitation units."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh40_sensor_mapping])
        
        # All precipitation sensors should map to same device
        assert mapper.get_hardware_id("rainratein") == "F6G7H8"  # Rate in inches/hr
        assert mapper.get_hardware_id("dailyrainin") == "F6G7H8"  # Daily accumulation in inches
        assert mapper.get_hardware_id("totalrainin") == "F6G7H8"  # Total accumulation in inches

    def test_wh40_time_based_accumulation(self, mock_wh40_sensor_mapping):
        """Test WH40 supports different time-based rain accumulations."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh40_sensor_mapping])
        
        # Time-based accumulation sensors
        time_sensors = [
            "eventrainin",    # Current rain event
            "hourlyrainin",   # Last hour
            "dailyrainin",    # Last 24 hours  
            "weeklyrainin",   # Last 7 days
            "monthlyrainin",  # Last 30 days
            "yearlyrainin",   # Last 365 days
            "totalrainin"     # Since device reset
        ]
        
        for sensor in time_sensors:
            assert mapper.get_hardware_id(sensor) == "F6G7H8"

    def test_wh40_unique_rain_sensor_type(self):
        """Test WH40 is distinct from other weather sensors."""
        mapper = SensorMapper()
        
        # Rain gauge should be distinguishable from weather stations
        rain_mapping = {
            "id": "RAIN1",
            "img": "wh40", 
            "type": "3",
            "name": "Rain",
            "batt": "75",
            "signal": "4"
        }
        
        weather_mapping = {
            "id": "WEATHER1",
            "img": "wh68",
            "type": "1", 
            "name": "Solar & Wind",
            "batt": "90",
            "signal": "4"
        }
        
        mapper.update_mapping([rain_mapping, weather_mapping])
        
        # Different sensor types should not conflict
        assert mapper.get_hardware_id("rainratein") == "RAIN1"
        assert mapper.get_hardware_id("tempf") == "WEATHER1"
        assert mapper.get_hardware_id("wh40batt") == "RAIN1"
        assert mapper.get_hardware_id("wh68batt") == "WEATHER1"

    def test_wh40_battery_monitoring(self, mock_wh40_sensor_mapping):
        """Test WH40 battery monitoring integration."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh40_sensor_mapping])
        
        # Battery sensor should map correctly
        assert mapper.get_hardware_id("wh40batt") == "F6G7H8"
        
        # Entity ID should be properly formed
        entity_id, name = mapper.generate_entity_id("wh40batt", "F6G7H8")
        assert "battery" in entity_id.lower()
        assert "Battery" in name


class TestWH41PM25Sensor:
    """Test WH41 PM2.5 air quality sensor support."""

    def test_wh41_sensor_mapping(self, mock_wh41_sensor_mapping):
        """Test WH41 sensor mapping and channel extraction."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh41_sensor_mapping])
        
        # Verify hardware ID is stored
        assert "G8H9I0" in mapper.get_all_hardware_ids()
        
        # Test sensor info
        sensor_info = mapper.get_sensor_info("G8H9I0")
        assert sensor_info is not None
        assert sensor_info["sensor_type"] == "WH41"
        assert sensor_info["device_model"] == "wh41"
        assert sensor_info["battery"] == "4"
        assert sensor_info["signal"] == "4"
        assert sensor_info["channel"] == "1"  # Extracted from "CH1"

    def test_wh41_live_data_keys(self, mock_wh41_sensor_mapping):
        """Test WH41 generates correct live data keys."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh41_sensor_mapping])
        
        # Test key mappings for PM2.5 sensor
        expected_keys = [
            "pm25_ch1", "pm25_avg_24h_ch1", "pm25batt1"
        ]
        
        for key in expected_keys:
            hardware_id = mapper.get_hardware_id(key)
            assert hardware_id == "G8H9I0", f"Key {key} should map to G8H9I0"

    def test_wh41_entity_id_generation(self, mock_wh41_sensor_mapping):
        """Test WH41 entity ID generation."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh41_sensor_mapping])
        
        # Test PM2.5 sensor
        entity_id, name = mapper.generate_entity_id("pm25_ch1", "G8H9I0")
        assert entity_id == "sensor.ecowitt_pm25_g8h9i0"
        assert "PM2.5" in name
        
        # Test PM2.5 24h average sensor — must have a distinct entity_id from the real-time sensor
        entity_id, name = mapper.generate_entity_id("pm25_avg_24h_ch1", "G8H9I0")
        assert entity_id == "sensor.ecowitt_pm25_24h_avg_g8h9i0"
        assert "PM2.5" in name
        
        # Test battery sensor
        entity_id, name = mapper.generate_entity_id("pm25batt1", "G8H9I0")
        assert entity_id == "sensor.ecowitt_pm25_battery_g8h9i0"
        assert "Battery" in name

    def test_wh41_multiple_channels(self):
        """Test multiple WH41 sensors with different channels."""
        mapper = SensorMapper()
        mappings = [
            {
                "id": "PM251",
                "img": "wh41",
                "type": "22", 
                "name": "PM2.5 CH1",
                "batt": "85",
                "signal": "4"
            },
            {
                "id": "PM252", 
                "img": "wh41",
                "type": "23",
                "name": "PM2.5 CH2", 
                "batt": "78",
                "signal": "3"
            }
        ]
        mapper.update_mapping(mappings)
        
        # Test channel separation
        assert mapper.get_hardware_id("pm25_ch1") == "PM251"
        assert mapper.get_hardware_id("pm25_ch2") == "PM252"
        assert mapper.get_hardware_id("pm25batt1") == "PM251"
        assert mapper.get_hardware_id("pm25batt2") == "PM252"


class TestWH55LeakDetection:
    """Test WH55 leak detection sensor support."""

    def test_wh55_sensor_mapping(self, mock_wh55_sensor_mapping):
        """Test WH55 sensor mapping and channel extraction."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh55_sensor_mapping])
        
        # Verify hardware ID is stored
        assert "J1K2L3" in mapper.get_all_hardware_ids()
        
        # Test sensor info
        sensor_info = mapper.get_sensor_info("J1K2L3")
        assert sensor_info is not None
        assert sensor_info["sensor_type"] == "WH55"
        assert sensor_info["device_model"] == "wh55"
        assert sensor_info["battery"] == "5"
        assert sensor_info["signal"] == "4"
        assert sensor_info["channel"] == "1"  # Extracted from "CH1"

    def test_wh55_live_data_keys(self, mock_wh55_sensor_mapping):
        """Test WH55 generates correct live data keys."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh55_sensor_mapping])
        
        # Test key mappings for leak detection sensor
        expected_keys = [
            "leak_ch1", "leakbatt1"
        ]
        
        for key in expected_keys:
            hardware_id = mapper.get_hardware_id(key)
            assert hardware_id == "J1K2L3", f"Key {key} should map to J1K2L3"

    def test_wh55_entity_id_generation(self, mock_wh55_sensor_mapping):
        """Test WH55 entity ID generation."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh55_sensor_mapping])
        
        # Test leak detection sensor
        entity_id, name = mapper.generate_entity_id("leak_ch1", "J1K2L3")
        assert entity_id == "sensor.ecowitt_leak_j1k2l3"
        assert "Leak" in name
        
        # Test battery sensor
        entity_id, name = mapper.generate_entity_id("leakbatt1", "J1K2L3")
        assert entity_id == "sensor.ecowitt_leak_battery_j1k2l3"
        assert "Battery" in name

    def test_wh55_binary_sensor_support(self, mock_wh55_live_data):
        """Test WH55 leak detection binary sensor values."""
        mapper = SensorMapper()
        mapping = {
            "id": "J1K2L3",
            "img": "wh55",
            "type": "27",
            "name": "Leak CH1",
            "batt": "92",
            "signal": "4"
        }
        mapper.update_mapping([mapping])
        
        # Verify leak sensor maps correctly (0 = no leak, 1 = leak)
        assert mapper.get_hardware_id("leak_ch1") == "J1K2L3"


class TestWH45ComboSensor:
    """Test WH45 CO2/PM2.5/PM10 combo sensor support."""

    def test_wh45_sensor_mapping(self, mock_wh45_sensor_mapping):
        """Test WH45 sensor mapping for multi-function device."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh45_sensor_mapping])
        
        # Verify hardware ID is stored
        assert "M4N5O6" in mapper.get_all_hardware_ids()
        
        # Test sensor info
        sensor_info = mapper.get_sensor_info("M4N5O6")
        assert sensor_info is not None
        assert sensor_info["sensor_type"] == "WH45"
        assert sensor_info["device_model"] == "wh45"
        assert sensor_info["battery"] == "4"
        assert sensor_info["signal"] == "4"
        assert sensor_info["channel"] == ""  # No channel for combo device

    def test_wh45_live_data_keys(self, mock_wh45_sensor_mapping):
        """Test WH45 generates correct live data keys for all sensor types."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh45_sensor_mapping])
        
        # Test key mappings for combo sensor
        expected_keys = [
            "tf_co2", "tf_co2c", "humi_co2",  # Temperature & humidity
            "pm25_co2", "pm25_24h_co2",        # PM2.5 current & 24h avg
            "pm10_co2", "pm10_24h_co2",        # PM10 current & 24h avg  
            "co2", "co2_24h",                  # CO2 current & 24h avg
            "co2_batt"                         # Battery
        ]
        
        for key in expected_keys:
            hardware_id = mapper.get_hardware_id(key)
            assert hardware_id == "M4N5O6", f"Key {key} should map to M4N5O6"

    def test_wh45_entity_id_generation(self, mock_wh45_sensor_mapping):
        """Test WH45 entity ID generation for different sensor types."""
        mapper = SensorMapper()
        mapper.update_mapping([mock_wh45_sensor_mapping])
        
        # Test CO2 sensor
        entity_id, name = mapper.generate_entity_id("co2", "M4N5O6")
        assert entity_id == "sensor.ecowitt_co_m4n5o6"
        assert "CO2" in name
        
        # Test PM2.5 sensor
        entity_id, name = mapper.generate_entity_id("pm25_co2", "M4N5O6")
        assert entity_id == "sensor.ecowitt_pm25_m4n5o6"
        assert "PM2.5" in name
        
        # Test temperature sensor
        entity_id, name = mapper.generate_entity_id("tf_co2", "M4N5O6")
        assert entity_id == "sensor.ecowitt_tf_co_m4n5o6"
        assert "Temperature" in name
        
        # Test humidity sensor
        entity_id, name = mapper.generate_entity_id("humi_co2", "M4N5O6")
        assert entity_id == "sensor.ecowitt_humi_co_m4n5o6"
        assert "Humidity" in name
        
        # Test PM10 sensor
        entity_id, name = mapper.generate_entity_id("pm10_co2", "M4N5O6")
        assert entity_id == "sensor.ecowitt_pm10_co_m4n5o6"
        assert "PM10" in name

    def test_wh45_multi_function_device(self, mock_wh45_live_data):
        """Test WH45 handles multiple sensor types in single device."""
        mapper = SensorMapper()
        mapping = {
            "id": "M4N5O6",
            "img": "wh45",
            "type": "39",
            "name": "PM25 & PM10 & CO2",
            "batt": "88",
            "signal": "4"
        }
        mapper.update_mapping([mapping])
        
        # Verify all sensor types map to same hardware ID
        sensor_groups = {
            "co2": ["co2", "co2_24h"],
            "pm25": ["pm25_co2", "pm25_24h_co2"],
            "pm10": ["pm10_co2", "pm10_24h_co2"],
            "temp": ["tf_co2", "tf_co2c"],
            "humidity": ["humi_co2"],
            "battery": ["co2_batt"]
        }
        
        for group, sensors in sensor_groups.items():
            for sensor in sensors:
                assert mapper.get_hardware_id(sensor) == "M4N5O6", f"{group} sensor {sensor} should map to M4N5O6"


class TestWeatherDeviceIntegration:
    """Test integration of weather devices with existing soil sensors."""

    def test_mixed_device_mapping(self, mock_complete_sensor_mappings):
        """Test mapping with both soil, weather, and environmental sensors."""
        mapper = SensorMapper()
        mapper.update_mapping(mock_complete_sensor_mappings)
        
        # Verify all hardware IDs are present
        hardware_ids = mapper.get_all_hardware_ids()
        assert "D8174" in hardware_ids  # Soil sensor
        assert "A1B2C3" in hardware_ids  # Weather station
        assert "D1E2F3" in hardware_ids  # Temp/humidity
        assert "E4F5A6" in hardware_ids  # Lightning detector
        assert "F6G7H8" in hardware_ids  # Rain gauge
        assert "G8H9I0" in hardware_ids  # PM2.5 sensor
        assert "J1K2L3" in hardware_ids  # Leak detection
        assert "M4N5O6" in hardware_ids  # Combo sensor
        
        # Test mapping stats
        stats = mapper.get_mapping_stats()
        assert stats["total_sensors"] == 8
        assert stats["sensor_types"] >= 8  # WH51, WH68, WH31, WH57, WH40, WH41, WH55, WH45

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
        
        # Test lightning sensor keys work
        assert mapper.get_hardware_id("lightning_num") == "E4F5A6"
        assert mapper.get_hardware_id("lightning_time") == "E4F5A6"
        assert mapper.get_hardware_id("wh57batt") == "E4F5A6"
        
        # Test rain gauge keys work
        assert mapper.get_hardware_id("rainratein") == "F6G7H8"
        assert mapper.get_hardware_id("dailyrainin") == "F6G7H8"
        assert mapper.get_hardware_id("wh40batt") == "F6G7H8"
        
        # Test PM2.5 sensor keys work
        assert mapper.get_hardware_id("pm25_ch1") == "G8H9I0"
        assert mapper.get_hardware_id("pm25batt1") == "G8H9I0"
        
        # Test leak detection keys work
        assert mapper.get_hardware_id("leak_ch1") == "J1K2L3"
        assert mapper.get_hardware_id("leakbatt1") == "J1K2L3"
        
        # Test combo sensor keys work  
        assert mapper.get_hardware_id("co2") == "M4N5O6"
        assert mapper.get_hardware_id("pm25_co2") == "M4N5O6"
        assert mapper.get_hardware_id("co2_batt") == "M4N5O6"

    def test_entity_id_stability(self, mock_complete_sensor_mappings):
        """Test entity IDs remain stable across remapping."""
        mapper = SensorMapper()
        
        # Initial mapping
        mapper.update_mapping(mock_complete_sensor_mappings)
        
        # Get initial entity IDs
        soil_entity, _ = mapper.generate_entity_id("soilmoisture2", "D8174")
        weather_entity, _ = mapper.generate_entity_id("tempf", "A1B2C3") 
        temp_entity, _ = mapper.generate_entity_id("temp1f", "D1E2F3")
        lightning_entity, _ = mapper.generate_entity_id("lightning_num", "E4F5A6")
        rain_entity, _ = mapper.generate_entity_id("rainratein", "F6G7H8")
        pm25_entity, _ = mapper.generate_entity_id("pm25_ch1", "G8H9I0")
        leak_entity, _ = mapper.generate_entity_id("leak_ch1", "J1K2L3")
        combo_entity, _ = mapper.generate_entity_id("co2", "M4N5O6")
        
        # Remap (simulating integration reload)
        mapper.update_mapping(mock_complete_sensor_mappings)
        
        # Verify entity IDs unchanged
        soil_entity2, _ = mapper.generate_entity_id("soilmoisture2", "D8174")
        weather_entity2, _ = mapper.generate_entity_id("tempf", "A1B2C3")
        temp_entity2, _ = mapper.generate_entity_id("temp1f", "D1E2F3")
        lightning_entity2, _ = mapper.generate_entity_id("lightning_num", "E4F5A6")
        rain_entity2, _ = mapper.generate_entity_id("rainratein", "F6G7H8")
        
        assert soil_entity == soil_entity2
        assert weather_entity == weather_entity2 
        assert temp_entity == temp_entity2
        assert lightning_entity == lightning_entity2
        assert rain_entity == rain_entity2


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