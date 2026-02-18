"""Test the Ecowitt Local sensor platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import PERCENTAGE

from custom_components.ecowitt_local.sensor import (
    async_setup_entry,
    EcowittLocalSensor,
    UNIT_CONVERSIONS,
)
from custom_components.ecowitt_local.const import (
    DOMAIN,
    ATTR_HARDWARE_ID,
    ATTR_CHANNEL,
    ATTR_BATTERY_LEVEL,
    ATTR_SIGNAL_STRENGTH,
    ATTR_LAST_SEEN,
    ATTR_SENSOR_TYPE,
    ATTR_DEVICE_MODEL,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator for testing."""
    coordinator = Mock()
    coordinator.config_entry = Mock()
    coordinator.config_entry.entry_id = "test_entry_id"
    coordinator.config_entry.data = {"include_inactive": False}
    coordinator.last_update_success = True
    
    # Mock gateway info
    coordinator.gateway_info = {
        "gateway_id": "GW1100A",
        "host": "192.168.1.100",
        "model": "GW1100A",
        "firmware_version": "1.7.3"
    }
    
    # Mock sensor mapper
    coordinator.sensor_mapper = Mock()
    coordinator.sensor_mapper.get_sensor_info.return_value = {
        "sensor_type": "wh51",
        "device_model": "WH51"
    }
    
    # Mock data methods
    coordinator.get_all_sensors.return_value = {}
    coordinator.get_sensor_data.return_value = None
    
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    config_entry = Mock(spec=ConfigEntry)
    config_entry.entry_id = "test_entry_id"
    config_entry.data = {"include_inactive": False}
    return config_entry


@pytest.mark.asyncio
async def test_async_setup_entry(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test sensor platform setup."""
    # Mock hass data
    hass.data = {DOMAIN: {"test_entry_id": mock_coordinator}}
    
    # Mock sensor data - add diagnostic and system categories that are also included
    mock_coordinator.get_all_sensors.return_value = {
        "sensor.test_sensor": {
            "sensor_key": "tempf",
            "category": "sensor",
            "name": "Temperature",
            "state": 72.5
        },
        "sensor.test_battery": {
            "sensor_key": "soilbatt1",
            "category": "battery",
            "name": "Battery",
            "state": 85
        },
        "sensor.test_diagnostic": {
            "sensor_key": "signal",
            "category": "diagnostic",
            "name": "Signal",
            "state": 4
        },
        "sensor.test_system": {
            "sensor_key": "heap",
            "category": "system",
            "name": "Heap",
            "state": 1024
        },
        "binary_sensor.test_binary": {
            "sensor_key": "status",
            "category": "binary_sensor",
            "name": "Status",
            "state": True
        }
    }
    
    # Mock async_add_entities - not async
    entities_added = []
    def mock_add_entities(entities, update_before_add):
        entities_added.extend(entities)
    
    # Call setup
    await async_setup_entry(hass, mock_config_entry, mock_add_entities)
    
    # Verify setup
    assert len(entities_added) == 4  # sensor, battery, diagnostic, system categories
    assert all(isinstance(entity, EcowittLocalSensor) for entity in entities_added)


@pytest.mark.asyncio
async def test_sensor_unique_id_with_hardware_id(mock_coordinator):
    """Test sensor unique ID generation with hardware ID."""
    sensor_info = {
        "sensor_key": "soilmoisture1",
        "hardware_id": "D8174",
        "category": "sensor",
        "name": "Soil Moisture CH1",
        "state": 50
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_soil",
        sensor_info=sensor_info
    )
    
    assert sensor.unique_id == f"{DOMAIN}_D8174_soilmoisture1"


@pytest.mark.asyncio
async def test_sensor_unique_id_without_hardware_id(mock_coordinator):
    """Test sensor unique ID generation without hardware ID."""
    sensor_info = {
        "sensor_key": "tempf",
        "hardware_id": None,
        "category": "sensor",
        "name": "Temperature",
        "state": 72.5
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_temp",
        sensor_info=sensor_info
    )
    
    assert sensor.unique_id == f"{DOMAIN}_test_entry_id_tempf"


@pytest.mark.asyncio
async def test_sensor_entity_category_diagnostic(mock_coordinator):
    """Test diagnostic category sensors get proper entity category."""
    sensor_info = {
        "sensor_key": "signal",
        "hardware_id": "D8174",
        "category": "diagnostic",
        "name": "Signal Strength",
        "state": 4
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_signal",
        sensor_info=sensor_info
    )
    
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC


@pytest.mark.asyncio
async def test_sensor_unit_conversion(mock_coordinator):
    """Test unit of measurement conversion."""
    sensor_info = {
        "sensor_key": "tempf",
        "category": "sensor",
        "name": "Temperature",
        "state": 72.5,
        "unit_of_measurement": "°F"
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_temp",
        sensor_info=sensor_info
    )
    
    assert sensor.native_unit_of_measurement == "°F"
    

@pytest.mark.asyncio
async def test_sensor_unit_unknown(mock_coordinator):
    """Test unknown unit of measurement handling."""
    sensor_info = {
        "sensor_key": "custom",
        "category": "sensor", 
        "name": "Custom Sensor",
        "state": 42.0,
        "unit_of_measurement": "custom_unit"
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_custom",
        sensor_info=sensor_info
    )
    
    assert sensor.native_unit_of_measurement == "custom_unit"


@pytest.mark.asyncio
async def test_sensor_state_class_measurement(mock_coordinator):
    """Test state class assignment for measurement sensors."""
    sensor_info = {
        "sensor_key": "tempf",
        "category": "sensor",
        "name": "Temperature",
        "state": 72.5,
        "device_class": "temperature"
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_temp",
        sensor_info=sensor_info
    )
    
    assert sensor.state_class == SensorStateClass.MEASUREMENT


@pytest.mark.asyncio
async def test_sensor_state_class_total_increasing(mock_coordinator):
    """Test state class assignment for total sensors using state_class from sensor_info."""
    sensor_info = {
        "sensor_key": "totalrainin",
        "category": "sensor",
        "name": "Rain Total",
        "state": 25.4,
        "device_class": "precipitation",
        "state_class": "total_increasing",  # coordinator now passes this from SENSOR_TYPES
    }

    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_rain_total",
        sensor_info=sensor_info
    )

    assert sensor.state_class == SensorStateClass.TOTAL_INCREASING


@pytest.mark.asyncio
async def test_rain_sensor_state_classes(mock_coordinator):
    """Test that rain sensors get correct state_class from sensor_info (not device_class heuristic).

    Regression test for issues #32, #45: rain entities were missing state_class
    because sensor.py set MEASUREMENT for all precipitation device_class sensors,
    ignoring the state_class defined in SENSOR_TYPES.
    """
    rain_cases = [
        # (sensor_key, state_class_from_coordinator, expected_state_class)
        ("rainratein",   "measurement",       SensorStateClass.MEASUREMENT),
        ("eventrainin",  "total",             SensorStateClass.TOTAL),
        ("hourlyrainin", "total_increasing",  SensorStateClass.TOTAL_INCREASING),
        ("dailyrainin",  "total_increasing",  SensorStateClass.TOTAL_INCREASING),
        ("weeklyrainin", "total_increasing",  SensorStateClass.TOTAL_INCREASING),
        ("monthlyrainin","total_increasing",  SensorStateClass.TOTAL_INCREASING),
        ("yearlyrainin", "total_increasing",  SensorStateClass.TOTAL_INCREASING),
        ("totalrainin",  "total_increasing",  SensorStateClass.TOTAL_INCREASING),
    ]

    for sensor_key, state_class_val, expected in rain_cases:
        sensor_info = {
            "sensor_key": sensor_key,
            "category": "sensor",
            "name": sensor_key,
            "state": 1.0,
            "device_class": "precipitation",
            "state_class": state_class_val,
        }
        sensor = EcowittLocalSensor(
            coordinator=mock_coordinator,
            entity_id=f"sensor.test_{sensor_key}",
            sensor_info=sensor_info,
        )
        assert sensor.state_class == expected, (
            f"{sensor_key}: expected {expected}, got {sensor.state_class}"
        )


@pytest.mark.asyncio
async def test_battery_sensor_attributes(mock_coordinator):
    """Test battery sensor specific attributes."""
    sensor_info = {
        "sensor_key": "soilbatt1",
        "category": "battery",
        "name": "Soil Battery",
        "state": 85,
        "device_class": "battery"
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_battery",
        sensor_info=sensor_info
    )
    
    assert sensor.device_class == SensorDeviceClass.BATTERY
    assert sensor.native_unit_of_measurement == PERCENTAGE
    assert sensor.state_class == SensorStateClass.MEASUREMENT


@pytest.mark.asyncio
async def test_sensor_coordinator_update(mock_coordinator):
    """Test sensor update from coordinator."""
    sensor_info = {
        "sensor_key": "tempf",
        "category": "sensor",
        "name": "Temperature",
        "state": 72.5
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_temp",
        sensor_info=sensor_info
    )
    
    # Mock updated sensor data
    updated_info = {
        "sensor_key": "tempf",
        "category": "sensor",
        "name": "Temperature",
        "state": 75.0
    }
    mock_coordinator.get_sensor_data.return_value = updated_info
    
    # Mock async_write_ha_state
    sensor.async_write_ha_state = Mock()
    
    # Trigger update
    sensor._handle_coordinator_update()
    
    # Verify update
    assert sensor.native_value == 75.0
    sensor.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio 
async def test_sensor_coordinator_update_no_data(mock_coordinator):
    """Test sensor update when coordinator has no data."""
    sensor_info = {
        "sensor_key": "tempf",
        "category": "sensor",
        "name": "Temperature",
        "state": 72.5
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_temp",
        sensor_info=sensor_info
    )
    
    # Mock no sensor data
    mock_coordinator.get_sensor_data.return_value = None
    
    # Mock async_write_ha_state
    sensor.async_write_ha_state = Mock()
    
    # Trigger update
    sensor._handle_coordinator_update()
    
    # Should still call async_write_ha_state
    sensor.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_device_info_with_hardware_id(mock_coordinator):
    """Test device info for sensor with hardware ID."""
    sensor_info = {
        "sensor_key": "soilmoisture1",
        "hardware_id": "D8174",
        "category": "sensor",
        "name": "Soil Moisture CH1",
        "state": 50
    }
    
    # Mock sensor mapper info
    mock_coordinator.sensor_mapper.get_sensor_info.return_value = {
        "sensor_type": "wh51",
        "device_model": "WH51"
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_soil",
        sensor_info=sensor_info
    )
    
    device_info = sensor.device_info
    
    assert device_info["identifiers"] == {(DOMAIN, "D8174")}
    assert "Ecowitt Soil Moisture Sensor D8174" in device_info["name"]
    assert device_info["manufacturer"] == "Ecowitt"
    assert device_info["model"] == "WH51"
    assert device_info["via_device"] == (DOMAIN, "GW1100A")
    assert device_info["suggested_area"] == "Outdoor"


@pytest.mark.asyncio
async def test_device_info_invalid_hardware_id(mock_coordinator):
    """Test device info for sensor with invalid hardware ID."""
    sensor_info = {
        "sensor_key": "soilmoisture1",
        "hardware_id": "FFFFFFFE",  # Invalid hardware ID
        "category": "sensor",
        "name": "Soil Moisture CH1",
        "state": 50
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_soil",
        sensor_info=sensor_info
    )
    
    device_info = sensor.device_info
    
    # Should fall back to gateway device
    assert device_info["identifiers"] == {(DOMAIN, "GW1100A")}
    assert "Ecowitt Gateway" in device_info["name"]


@pytest.mark.asyncio
async def test_device_info_no_sensor_info(mock_coordinator):
    """Test device info when sensor mapper has no info."""
    sensor_info = {
        "sensor_key": "soilmoisture1",
        "hardware_id": "D8174",
        "category": "sensor",
        "name": "Soil Moisture CH1", 
        "state": 50
    }
    
    # Mock no sensor mapper info
    mock_coordinator.sensor_mapper.get_sensor_info.return_value = None
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_soil",
        sensor_info=sensor_info
    )
    
    device_info = sensor.device_info
    
    # Should fall back to gateway device
    assert device_info["identifiers"] == {(DOMAIN, "GW1100A")}
    assert "Ecowitt Gateway" in device_info["name"]


@pytest.mark.asyncio
async def test_device_info_gateway_fallback(mock_coordinator):
    """Test device info for built-in gateway sensors."""
    sensor_info = {
        "sensor_key": "tempinf", 
        "hardware_id": None,
        "category": "sensor",
        "name": "Indoor Temperature",
        "state": 72.0
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_indoor_temp",
        sensor_info=sensor_info
    )
    
    device_info = sensor.device_info
    
    assert device_info["identifiers"] == {(DOMAIN, "GW1100A")}
    assert "Ecowitt Gateway 192.168.1.100" == device_info["name"]
    assert device_info["manufacturer"] == "Ecowitt"
    assert device_info["model"] == "GW1100A"
    assert device_info["sw_version"] == "1.7.3"
    assert device_info["configuration_url"] == "http://192.168.1.100"


@pytest.mark.asyncio
async def test_extra_state_attributes_basic(mock_coordinator):
    """Test basic extra state attributes."""
    sensor_info = {
        "sensor_key": "tempf",
        "category": "sensor",
        "name": "Temperature",
        "state": 72.5,
        "attributes": {}
    }
    
    mock_coordinator.get_sensor_data.return_value = sensor_info
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_temp",
        sensor_info=sensor_info
    )
    
    attributes = sensor.extra_state_attributes
    
    assert attributes["sensor_key"] == "tempf"
    assert attributes["category"] == "sensor"
    assert attributes[ATTR_SENSOR_TYPE] == "sensor"


@pytest.mark.asyncio
async def test_extra_state_attributes_hardware(mock_coordinator):
    """Test extra state attributes with hardware info."""
    sensor_info = {
        "sensor_key": "soilmoisture1",
        "hardware_id": "D8174",
        "category": "sensor",
        "name": "Soil Moisture CH1",
        "state": 50,
        "attributes": {
            "channel": "1",
            "device_model": "WH51",
            "battery": "85",
            "signal": "4",
            "last_update": "2023-01-01T12:00:00Z"
        }
    }
    
    mock_coordinator.get_sensor_data.return_value = sensor_info
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_soil",
        sensor_info=sensor_info
    )
    
    attributes = sensor.extra_state_attributes
    
    assert attributes[ATTR_HARDWARE_ID] == "D8174"
    assert attributes[ATTR_CHANNEL] == "1"
    assert attributes[ATTR_DEVICE_MODEL] == "WH51"
    assert attributes[ATTR_BATTERY_LEVEL] == 85.0
    assert attributes[ATTR_SIGNAL_STRENGTH] == 4
    assert attributes[ATTR_LAST_SEEN] == "2023-01-01T12:00:00Z"


@pytest.mark.asyncio
async def test_extra_state_attributes_invalid_values(mock_coordinator):
    """Test extra state attributes with invalid battery/signal values."""
    sensor_info = {
        "sensor_key": "soilmoisture1",
        "hardware_id": "D8174",
        "category": "sensor", 
        "name": "Soil Moisture CH1",
        "state": 50,
        "attributes": {
            "battery": "invalid",
            "signal": "also_invalid"
        }
    }
    
    mock_coordinator.get_sensor_data.return_value = sensor_info
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_soil",
        sensor_info=sensor_info
    )
    
    attributes = sensor.extra_state_attributes
    
    # Invalid values should not be included
    assert ATTR_BATTERY_LEVEL not in attributes
    assert ATTR_SIGNAL_STRENGTH not in attributes


@pytest.mark.asyncio
async def test_extra_state_attributes_raw_value(mock_coordinator):
    """Test extra state attributes with raw value."""
    sensor_info = {
        "sensor_key": "tempf",
        "category": "sensor",
        "name": "Temperature",
        "state": 72.5,
        "raw_value": "72.5°F",
        "attributes": {}
    }
    
    mock_coordinator.get_sensor_data.return_value = sensor_info
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_temp",
        sensor_info=sensor_info
    )
    
    attributes = sensor.extra_state_attributes
    
    assert attributes["raw_value"] == "72.5°F"


@pytest.mark.asyncio
async def test_extra_state_attributes_no_sensor_data(mock_coordinator):
    """Test extra state attributes when no sensor data available."""
    sensor_info = {
        "sensor_key": "tempf",
        "category": "sensor",
        "name": "Temperature",
        "state": 72.5
    }
    
    mock_coordinator.get_sensor_data.return_value = None
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_temp",
        sensor_info=sensor_info
    )
    
    attributes = sensor.extra_state_attributes
    
    assert attributes == {}


@pytest.mark.asyncio
async def test_available_coordinator_success(mock_coordinator):
    """Test sensor availability when coordinator is successful."""
    sensor_info = {
        "sensor_key": "tempf",
        "category": "sensor",
        "name": "Temperature",
        "state": 72.5
    }
    
    mock_coordinator.last_update_success = True
    mock_coordinator.get_sensor_data.return_value = sensor_info
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_temp",
        sensor_info=sensor_info
    )
    
    assert sensor.available is True


@pytest.mark.asyncio
async def test_available_coordinator_failure(mock_coordinator):
    """Test sensor availability when coordinator fails."""
    sensor_info = {
        "sensor_key": "tempf",
        "category": "sensor",
        "name": "Temperature",
        "state": 72.5
    }
    
    mock_coordinator.last_update_success = False
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_temp",
        sensor_info=sensor_info
    )
    
    assert sensor.available is False


@pytest.mark.asyncio
async def test_available_no_sensor_data(mock_coordinator):
    """Test sensor availability when no sensor data."""
    sensor_info = {
        "sensor_key": "tempf",
        "category": "sensor",
        "name": "Temperature",
        "state": 72.5
    }
    
    mock_coordinator.last_update_success = True
    mock_coordinator.get_sensor_data.return_value = None
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_temp",
        sensor_info=sensor_info
    )
    
    assert sensor.available is False


@pytest.mark.asyncio
async def test_available_hardware_sensor_none_state(mock_coordinator):
    """Test availability for hardware sensor with None state."""
    sensor_info = {
        "sensor_key": "soilmoisture1",
        "hardware_id": "D8174",
        "category": "sensor",
        "name": "Soil Moisture CH1",
        "state": None
    }
    
    mock_coordinator.last_update_success = True
    mock_coordinator.get_sensor_data.return_value = sensor_info
    mock_coordinator.config_entry.data = {"include_inactive": False}
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_soil",
        sensor_info=sensor_info
    )
    
    assert sensor.available is False


@pytest.mark.asyncio
async def test_available_hardware_sensor_none_state_include_inactive(mock_coordinator):
    """Test availability for hardware sensor with None state when include_inactive is True."""
    sensor_info = {
        "sensor_key": "soilmoisture1",
        "hardware_id": "D8174",
        "category": "sensor",
        "name": "Soil Moisture CH1",
        "state": None
    }
    
    mock_coordinator.last_update_success = True
    mock_coordinator.get_sensor_data.return_value = sensor_info
    mock_coordinator.config_entry.data = {"include_inactive": True}
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_soil", 
        sensor_info=sensor_info
    )
    
    assert sensor.available is True


@pytest.mark.asyncio
async def test_icon_battery_levels(mock_coordinator):
    """Test icon selection for different battery levels."""
    test_cases = [
        (5, "mdi:battery-outline"),
        (15, "mdi:battery-20"),
        (25, "mdi:battery-30"),
        (35, "mdi:battery-40"),
        (45, "mdi:battery-50"),
        (55, "mdi:battery-60"),
        (65, "mdi:battery-70"),
        (75, "mdi:battery-80"),
        (85, "mdi:battery-90"),
        (95, "mdi:battery"),
    ]
    
    for battery_level, expected_icon in test_cases:
        sensor_info = {
            "sensor_key": "soilbatt1",
            "hardware_id": "D8174",
            "category": "diagnostic",
            "device_class": "battery",
            "name": "Soil Battery",
            "state": battery_level,
            "attributes": {"battery": str(battery_level)}
        }
        
        mock_coordinator.get_sensor_data.return_value = sensor_info
        
        sensor = EcowittLocalSensor(
            coordinator=mock_coordinator,
            entity_id="sensor.test_battery",
            sensor_info=sensor_info
        )
        
        assert sensor.icon == expected_icon


@pytest.mark.asyncio
async def test_icon_battery_no_level(mock_coordinator):
    """Test icon for battery sensor without level."""
    sensor_info = {
        "sensor_key": "soilbatt1",
        "category": "diagnostic",
        "device_class": "battery",
        "name": "Soil Battery",
        "state": 85,
        "attributes": {}
    }
    
    mock_coordinator.get_sensor_data.return_value = sensor_info
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test_battery",
        sensor_info=sensor_info
    )
    
    assert sensor.icon == "mdi:battery"


@pytest.mark.asyncio
async def test_icon_sensor_types(mock_coordinator):
    """Test icon selection for different sensor types."""
    test_cases = [
        ("soilmoisture1", "mdi:sprout"),
        ("leak_ch1", "mdi:water-alert"),
        ("lightning_num", "mdi:flash"),
        ("uv_index", "mdi:weather-sunny-alert"),
        ("heap_usage", "mdi:memory"),
        ("runtime_days", "mdi:clock-outline"),
        ("tempf", None),  # No custom icon
    ]
    
    for sensor_key, expected_icon in test_cases:
        sensor_info = {
            "sensor_key": sensor_key,
            "category": "sensor",
            "name": "Test Sensor",
            "state": 42,
            "attributes": {}
        }
        
        mock_coordinator.get_sensor_data.return_value = sensor_info
        
        sensor = EcowittLocalSensor(
            coordinator=mock_coordinator,
            entity_id="sensor.test",
            sensor_info=sensor_info
        )
        
        assert sensor.icon == expected_icon


@pytest.mark.asyncio
async def test_get_sensor_type_display_name(mock_coordinator):
    """Test sensor type display name generation."""
    sensor_info = {
        "sensor_key": "test",
        "category": "sensor",
        "name": "Test",
        "state": 42
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test",
        sensor_info=sensor_info
    )
    
    test_cases = [
        ({"sensor_type": "wh51"}, "Soil Moisture Sensor"),
        ({"sensor_type": "WH31"}, "Temperature/Humidity Sensor"),
        ({"sensor_type": "wh41"}, "PM2.5 Air Quality Sensor"),
        ({"sensor_type": "soil"}, "Soil Moisture Sensor"),
        ({"sensor_type": "unknown"}, "Sensor"),
    ]
    
    for sensor_info_input, expected_name in test_cases:
        result = sensor._get_sensor_type_display_name(sensor_info_input)
        assert result == expected_name


@pytest.mark.asyncio
async def test_is_outdoor_sensor(mock_coordinator):
    """Test outdoor sensor detection."""
    sensor_info = {
        "sensor_key": "test",
        "category": "sensor",
        "name": "Test",
        "state": 42
    }
    
    sensor = EcowittLocalSensor(
        coordinator=mock_coordinator,
        entity_id="sensor.test",
        sensor_info=sensor_info
    )
    
    test_cases = [
        ({"sensor_type": "wh51"}, True),
        ({"sensor_type": "WH41"}, True),
        ({"sensor_type": "soil"}, True),
        ({"sensor_type": "pm25"}, True),
        ({"sensor_type": "wh31"}, False),
        ({"sensor_type": "indoor"}, False),
    ]
    
    for sensor_info_input, expected_outdoor in test_cases:
        result = sensor._is_outdoor_sensor(sensor_info_input)
        assert result == expected_outdoor