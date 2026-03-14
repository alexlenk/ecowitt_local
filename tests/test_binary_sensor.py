"""Test the Ecowitt Local binary sensor platform."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from custom_components.ecowitt_local.binary_sensor import (
    OFFLINE_THRESHOLD_MINUTES,
    EcowittGatewayOnlineBinarySensor,
    EcowittSensorOnlineBinarySensor,
    EcowittStateBinarySensor,
    async_setup_entry,
)
from custom_components.ecowitt_local.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_CHANNEL,
    ATTR_DEVICE_MODEL,
    ATTR_HARDWARE_ID,
    ATTR_LAST_SEEN,
    ATTR_SIGNAL_STRENGTH,
    DOMAIN,
    MANUFACTURER,
)
from custom_components.ecowitt_local.coordinator import (
    EcowittLocalDataUpdateCoordinator,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = Mock(spec=EcowittLocalDataUpdateCoordinator)
    coordinator.gateway_info = {
        "gateway_id": "test_gateway",
        "host": "192.168.1.100",
        "model": "GW1100A",
        "firmware_version": "1.7.3",
    }
    coordinator.last_update_success = True
    coordinator.last_update_success_time = datetime.now()
    coordinator.last_update_time = datetime.now()

    # Mock sensor mapper
    coordinator.sensor_mapper = Mock()
    coordinator.sensor_mapper.get_sensor_info.return_value = {
        "sensor_type": "WH51",
        "device_model": "WH51",
    }

    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    return entry


@pytest.mark.asyncio
async def test_async_setup_entry(mock_coordinator, mock_config_entry):
    """Test setting up binary sensor entities."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {DOMAIN: {"test_entry": mock_coordinator}}

    # Mock coordinator methods
    mock_coordinator.get_all_sensors.return_value = {
        "sensor.test_soil_d8174": {
            "hardware_id": "D8174",
            "category": "sensor",
            "sensor_key": "soilmoisture1",
            "state": "45",
        },
        "sensor.test_temp_d8648": {
            "hardware_id": "D8648",
            "category": "sensor",
            "sensor_key": "temp1f",
            "state": "72.5",
        },
        "sensor.test_gateway": {
            "hardware_id": None,
            "category": "gateway",
            "sensor_key": "gateway_status",
            "state": "online",
        },
    }

    async_add_entities = AsyncMock()

    await async_setup_entry(hass, mock_config_entry, async_add_entities)

    # Verify entities were added (2 hardware sensors + 1 gateway)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 3  # 2 sensor online + 1 gateway online

    # Check entity types
    sensor_entities = [
        e for e in entities if isinstance(e, EcowittSensorOnlineBinarySensor)
    ]
    gateway_entities = [
        e for e in entities if isinstance(e, EcowittGatewayOnlineBinarySensor)
    ]
    assert len(sensor_entities) == 2
    assert len(gateway_entities) == 1


def test_sensor_online_binary_sensor_init(mock_coordinator):
    """Test EcowittSensorOnlineBinarySensor initialization."""
    sensor_info = {
        "sensor_key": "soilmoisture1",
        "attributes": {"device_model": "WH51"},
    }

    entity = EcowittSensorOnlineBinarySensor(mock_coordinator, "D8174", sensor_info)

    assert entity._hardware_id == "D8174"
    assert entity._sensor_key == "soilmoisture1"
    assert entity._device_model == "WH51"
    assert entity.unique_id == f"{DOMAIN}_D8174_online"
    assert entity.entity_id == "binary_sensor.ecowitt_soil_moisture_d8174_online"
    assert "Soil Moisture D8174 Online" in entity.name
    assert entity.device_class == BinarySensorDeviceClass.CONNECTIVITY
    assert entity.entity_category == EntityCategory.DIAGNOSTIC


def test_sensor_type_extraction(mock_coordinator):
    """Test _extract_sensor_type method."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "test", {"sensor_key": "test"}
    )

    # Test different sensor types
    test_cases = [
        ({"sensor_key": "soilmoisture1"}, "soil_moisture"),
        ({"sensor_key": "temp1f"}, "temperature"),
        ({"sensor_key": "pm25_ch1"}, "pm25"),
        ({"sensor_key": "leak_ch1"}, "leak"),
        ({"sensor_key": "lightning_time"}, "lightning"),
        ({"sensor_key": "rainratein"}, "rain"),
        ({"sensor_key": "windspeedmph"}, "wind"),
        ({"sensor_key": "unknown_sensor"}, "sensor"),
    ]

    for sensor_info, expected_type in test_cases:
        result = entity._extract_sensor_type(sensor_info)
        assert result == expected_type


def test_sensor_online_state_with_value(mock_coordinator):
    """Test is_on property when sensor has a value."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "D8174", {"sensor_key": "test"}
    )

    mock_coordinator.get_all_sensors.return_value = {
        "sensor.test": {
            "hardware_id": "D8174",
            "state": "45",  # Has value, should be online
        }
    }

    assert entity.is_on is True


def test_sensor_online_state_no_value(mock_coordinator):
    """Test is_on property when sensor has no value."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "D8174", {"sensor_key": "test"}
    )

    mock_coordinator.get_all_sensors.return_value = {
        "sensor.test": {"hardware_id": "D8174", "state": None}  # No value
    }

    assert entity.is_on is False


def test_sensor_online_state_with_recent_timestamp(mock_coordinator):
    """Test is_on property with recent naive timestamp - sensor is online."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "D8174", {"sensor_key": "test"}
    )

    # Use a naive timestamp (no Z suffix) so comparison with datetime.now() works
    recent_time = (datetime.now() - timedelta(minutes=5)).isoformat()
    mock_coordinator.get_all_sensors.return_value = {
        "sensor.test": {
            "hardware_id": "D8174",
            "state": None,
            "attributes": {"last_update": recent_time},
        }
    }

    assert entity.is_on is True


def test_sensor_online_state_with_recent_tz_timestamp(mock_coordinator):
    """Test is_on property with timezone-aware timestamp (Z suffix) - TypeError caught."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "D8174", {"sensor_key": "test"}
    )

    mock_coordinator.get_all_sensors.return_value = {
        "sensor.test": {
            "hardware_id": "D8174",
            "state": None,
            "attributes": {
                "last_update": (datetime.now() - timedelta(minutes=5)).isoformat() + "Z"
            },
        }
    }

    # Timezone-aware vs naive comparison raises TypeError → caught → returns False
    result = entity.is_on
    assert result is False


def test_sensor_online_state_with_old_timestamp(mock_coordinator):
    """Test is_on property with old timestamp."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "D8174", {"sensor_key": "test"}
    )

    # Old timestamp (beyond threshold)
    old_time = datetime.now() - timedelta(minutes=15)

    mock_coordinator.get_all_sensors.return_value = {
        "sensor.test": {
            "hardware_id": "D8174",
            "state": None,
            "attributes": {"last_update": old_time.isoformat() + "Z"},
        }
    }

    assert entity.is_on is False


def test_sensor_online_state_invalid_timestamp(mock_coordinator):
    """Test is_on property with invalid timestamp."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "D8174", {"sensor_key": "test"}
    )

    mock_coordinator.get_all_sensors.return_value = {
        "sensor.test": {
            "hardware_id": "D8174",
            "state": None,
            "attributes": {"last_update": "invalid_timestamp"},
        }
    }

    assert entity.is_on is False


def test_sensor_online_state_with_unknown_value(mock_coordinator):
    """Test is_on property when sensor has Unknown value."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "D8174", {"sensor_key": "test"}
    )

    mock_coordinator.get_all_sensors.return_value = {
        "sensor.test": {"hardware_id": "D8174", "state": "Unknown"}  # Invalid state
    }

    assert entity.is_on is False


def test_sensor_online_state_with_various_invalid_values(mock_coordinator):
    """Test is_on property with various invalid state values."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "D8174", {"sensor_key": "test"}
    )

    invalid_values = [
        "Unknown",
        "N/A",
        "None",
        "",
        "null",
        "unavailable",
        "UNKNOWN",
        "n/a",
    ]

    for invalid_value in invalid_values:
        mock_coordinator.get_all_sensors.return_value = {
            "sensor.test": {"hardware_id": "D8174", "state": invalid_value}
        }

        assert (
            entity.is_on is False
        ), f"Expected sensor to be offline with state '{invalid_value}'"


def test_sensor_online_state_with_valid_value(mock_coordinator):
    """Test is_on property when sensor has a valid numeric value."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "D8174", {"sensor_key": "test"}
    )

    mock_coordinator.get_all_sensors.return_value = {
        "sensor.test": {"hardware_id": "D8174", "state": 25.6}  # Valid numeric value
    }

    assert entity.is_on is True


def test_sensor_device_info_with_hardware_id(mock_coordinator):
    """Test device_info property with valid hardware ID."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "D8174", {"sensor_key": "test"}
    )

    device_info = entity.device_info

    assert device_info["identifiers"] == {(DOMAIN, "D8174")}
    assert "Ecowitt" in device_info["name"]
    assert "D8174" in device_info["name"]
    assert device_info["manufacturer"] == MANUFACTURER
    assert device_info["model"] == "WH51"
    assert device_info["via_device"] == (DOMAIN, "test_gateway")


def test_sensor_device_info_invalid_hardware_id(mock_coordinator):
    """Test device_info property with invalid hardware ID."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "FFFFFFFF", {"sensor_key": "test"}
    )

    device_info = entity.device_info

    # Should fall back to gateway device
    assert device_info["identifiers"] == {(DOMAIN, "test_gateway")}
    assert "Gateway" in device_info["name"]


def test_sensor_device_info_no_sensor_info(mock_coordinator):
    """Test device_info property when sensor info is not available."""
    mock_coordinator.sensor_mapper.get_sensor_info.return_value = None
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "D8174", {"sensor_key": "test"}
    )

    device_info = entity.device_info

    # Should fall back to gateway device
    assert device_info["identifiers"] == {(DOMAIN, "test_gateway")}


def test_sensor_extra_state_attributes(mock_coordinator):
    """Test extra_state_attributes property."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "D8174", {"sensor_key": "test"}
    )

    mock_coordinator.get_all_sensors.return_value = {
        "sensor.test": {
            "hardware_id": "D8174",
            "attributes": {
                "channel": "1",
                "device_model": "WH51",
                "battery": "85",
                "signal": "3",
                "last_update": "2023-01-01T12:00:00Z",
            },
        }
    }

    attributes = entity.extra_state_attributes

    assert attributes[ATTR_HARDWARE_ID] == "D8174"
    assert attributes["offline_threshold_minutes"] == OFFLINE_THRESHOLD_MINUTES
    assert attributes[ATTR_CHANNEL] == "1"
    assert attributes[ATTR_DEVICE_MODEL] == "WH51"
    assert attributes[ATTR_BATTERY_LEVEL] == 85.0
    assert attributes[ATTR_SIGNAL_STRENGTH] == 3
    assert attributes[ATTR_LAST_SEEN] == "2023-01-01T12:00:00Z"


def test_sensor_extra_state_attributes_invalid_values(mock_coordinator):
    """Test extra_state_attributes with invalid battery/signal values."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "D8174", {"sensor_key": "test"}
    )

    mock_coordinator.get_all_sensors.return_value = {
        "sensor.test": {
            "hardware_id": "D8174",
            "attributes": {"battery": "invalid", "signal": "invalid"},
        }
    }

    attributes = entity.extra_state_attributes

    # Invalid values should not be included
    assert ATTR_BATTERY_LEVEL not in attributes
    assert ATTR_SIGNAL_STRENGTH not in attributes


def test_sensor_get_sensor_type_display_name(mock_coordinator):
    """Test _get_sensor_type_display_name method."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "test", {"sensor_key": "test"}
    )

    test_cases = [
        ({"sensor_type": "WH51"}, "Soil Moisture Sensor"),
        ({"sensor_type": "WH31"}, "Temperature/Humidity Sensor"),
        ({"sensor_type": "WH41"}, "PM2.5 Air Quality Sensor"),
        ({"sensor_type": "WH55"}, "Leak Sensor"),
        ({"sensor_type": "WH57"}, "Lightning Sensor"),
        ({"sensor_type": "WH40"}, "Rain Sensor"),
        ({"sensor_type": "WH68"}, "Weather Station"),
        ({"sensor_type": "unknown"}, "Sensor"),
    ]

    for sensor_info, expected_name in test_cases:
        result = entity._get_sensor_type_display_name(sensor_info)
        assert result == expected_name


def test_sensor_is_outdoor_sensor(mock_coordinator):
    """Test _is_outdoor_sensor method."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "test", {"sensor_key": "test"}
    )

    # Outdoor sensor types
    outdoor_types = ["WH51", "WH41", "WH55", "WH57", "WH40", "WH68"]
    for sensor_type in outdoor_types:
        result = entity._is_outdoor_sensor({"sensor_type": sensor_type})
        assert result is True

    # Indoor sensor type
    result = entity._is_outdoor_sensor({"sensor_type": "WH31"})
    assert result is False


def test_sensor_handle_coordinator_update(mock_coordinator):
    """Test _handle_coordinator_update method."""
    entity = EcowittSensorOnlineBinarySensor(
        mock_coordinator, "test", {"sensor_key": "test"}
    )

    with patch.object(entity, "async_write_ha_state") as mock_write_state:
        entity._handle_coordinator_update()
        mock_write_state.assert_called_once()


def test_gateway_online_binary_sensor_init(mock_coordinator):
    """Test EcowittGatewayOnlineBinarySensor initialization."""
    entity = EcowittGatewayOnlineBinarySensor(mock_coordinator)

    assert entity.unique_id == f"{DOMAIN}_test_gateway_gateway_online"
    assert entity.entity_id == "binary_sensor.ecowitt_gateway_test_gateway_online"
    assert "Gateway 192.168.1.100 Online" in entity.name
    assert entity.device_class == BinarySensorDeviceClass.CONNECTIVITY
    assert entity.entity_category == EntityCategory.DIAGNOSTIC


def test_gateway_online_state_success(mock_coordinator):
    """Test gateway is_on property when updates are successful."""
    mock_coordinator.last_update_success = True
    entity = EcowittGatewayOnlineBinarySensor(mock_coordinator)

    assert entity.is_on is True


def test_gateway_online_state_failure(mock_coordinator):
    """Test gateway is_on property when updates fail."""
    mock_coordinator.last_update_success = False
    entity = EcowittGatewayOnlineBinarySensor(mock_coordinator)

    assert entity.is_on is False


def test_gateway_device_info(mock_coordinator):
    """Test gateway device_info property."""
    entity = EcowittGatewayOnlineBinarySensor(mock_coordinator)

    device_info = entity.device_info

    assert device_info["identifiers"] == {(DOMAIN, "test_gateway")}
    assert "Gateway 192.168.1.100" in device_info["name"]
    assert device_info["manufacturer"] == MANUFACTURER
    assert device_info["model"] == "GW1100A"
    assert device_info["sw_version"] == "1.7.3"
    assert device_info["configuration_url"] == "http://192.168.1.100"


def test_gateway_extra_state_attributes(mock_coordinator):
    """Test gateway extra_state_attributes property."""
    entity = EcowittGatewayOnlineBinarySensor(mock_coordinator)

    attributes = entity.extra_state_attributes

    assert attributes["gateway_id"] == "test_gateway"
    assert attributes["host"] == "192.168.1.100"
    assert attributes["model"] == "GW1100A"
    assert attributes["firmware_version"] == "1.7.3"
    assert "last_successful_update" in attributes


def test_gateway_extra_state_attributes_no_success_time(mock_coordinator):
    """Test gateway extra_state_attributes when no success time available."""
    # Remove success time but keep update time
    del mock_coordinator.last_update_success_time
    entity = EcowittGatewayOnlineBinarySensor(mock_coordinator)

    attributes = entity.extra_state_attributes

    assert "last_update_time" in attributes
    assert "last_successful_update" not in attributes


def test_gateway_extra_state_attributes_no_times(mock_coordinator):
    """Test gateway extra_state_attributes when no times available."""
    # Remove both times
    del mock_coordinator.last_update_success_time
    del mock_coordinator.last_update_time
    entity = EcowittGatewayOnlineBinarySensor(mock_coordinator)

    attributes = entity.extra_state_attributes

    assert "last_update_time" not in attributes
    assert "last_successful_update" not in attributes


def test_gateway_handle_coordinator_update(mock_coordinator):
    """Test gateway _handle_coordinator_update method."""
    entity = EcowittGatewayOnlineBinarySensor(mock_coordinator)

    with patch.object(entity, "async_write_ha_state") as mock_write_state:
        entity._handle_coordinator_update()
        mock_write_state.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_with_binary_sensor(
    mock_coordinator, mock_config_entry
):
    """Test setup creates EcowittStateBinarySensor for category=binary sensors."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {DOMAIN: {"test_entry": mock_coordinator}}

    mock_coordinator.get_all_sensors.return_value = {
        "ecowitt_rain_state_piezo_abc123": {
            "hardware_id": "ABC123",
            "category": "binary",
            "sensor_key": "srain_piezo",
            "state": "0",
            "name": "Rain State Piezo",
        },
    }

    async_add_entities = AsyncMock()
    await async_setup_entry(hass, mock_config_entry, async_add_entities)

    entities = async_add_entities.call_args[0][0]
    state_entities = [e for e in entities if isinstance(e, EcowittStateBinarySensor)]
    assert len(state_entities) == 1


@pytest.mark.asyncio
async def test_async_setup_entry_binary_unknown_key_skipped(
    mock_coordinator, mock_config_entry
):
    """Test setup skips category=binary sensors not in BINARY_SENSORS."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {DOMAIN: {"test_entry": mock_coordinator}}

    mock_coordinator.get_all_sensors.return_value = {
        "ecowitt_unknown_binary_abc123": {
            "hardware_id": "ABC123",
            "category": "binary",
            "sensor_key": "unknown_binary_key",
            "state": "0",
        },
    }

    async_add_entities = AsyncMock()
    await async_setup_entry(hass, mock_config_entry, async_add_entities)

    entities = async_add_entities.call_args[0][0]
    state_entities = [e for e in entities if isinstance(e, EcowittStateBinarySensor)]
    assert len(state_entities) == 0


def test_state_binary_sensor_init(mock_coordinator):
    """Test EcowittStateBinarySensor initialization."""
    sensor_info = {
        "sensor_key": "srain_piezo",
        "hardware_id": "ABC123",
        "name": "Rain State Piezo",
        "state": "0",
    }
    entity = EcowittStateBinarySensor(
        mock_coordinator, "ecowitt_rain_state_abc123", sensor_info
    )

    assert entity._sensor_key == "srain_piezo"
    assert entity._hardware_id == "ABC123"
    assert entity.unique_id == f"{DOMAIN}_ecowitt_rain_state_abc123"
    assert entity.entity_id == "binary_sensor.ecowitt_rain_state_abc123"
    assert entity.device_class == BinarySensorDeviceClass.MOISTURE


def test_state_binary_sensor_init_invalid_device_class(mock_coordinator):
    """Test EcowittStateBinarySensor with an unknown device class string."""
    from unittest.mock import patch as mpatch

    with mpatch.dict(
        "custom_components.ecowitt_local.binary_sensor.BINARY_SENSORS",
        {"srain_piezo": {"name": "Rain State", "device_class": "not_a_real_class"}},
    ):
        sensor_info = {
            "sensor_key": "srain_piezo",
            "hardware_id": "ABC123",
            "name": "Rain State Piezo",
        }
        entity = EcowittStateBinarySensor(
            mock_coordinator, "ecowitt_rain_state_abc123", sensor_info
        )
        assert entity._attr_device_class is None


def test_state_binary_sensor_is_on_true(mock_coordinator):
    """Test is_on returns True when state is non-zero."""
    sensor_info = {"sensor_key": "srain_piezo", "hardware_id": "ABC123", "name": ""}
    entity = EcowittStateBinarySensor(
        mock_coordinator, "ecowitt_rain_abc123", sensor_info
    )
    mock_coordinator.get_all_sensors.return_value = {
        "ecowitt_rain_abc123": {"state": "1"}
    }
    assert entity.is_on is True


def test_state_binary_sensor_is_on_false(mock_coordinator):
    """Test is_on returns False when state is zero."""
    sensor_info = {"sensor_key": "srain_piezo", "hardware_id": "ABC123", "name": ""}
    entity = EcowittStateBinarySensor(
        mock_coordinator, "ecowitt_rain_abc123", sensor_info
    )
    mock_coordinator.get_all_sensors.return_value = {
        "ecowitt_rain_abc123": {"state": "0"}
    }
    assert entity.is_on is False


def test_state_binary_sensor_is_on_none_missing(mock_coordinator):
    """Test is_on returns None when entity not in sensor data."""
    sensor_info = {"sensor_key": "srain_piezo", "hardware_id": "ABC123", "name": ""}
    entity = EcowittStateBinarySensor(
        mock_coordinator, "ecowitt_rain_abc123", sensor_info
    )
    mock_coordinator.get_all_sensors.return_value = {}
    assert entity.is_on is None


def test_state_binary_sensor_is_on_none_state(mock_coordinator):
    """Test is_on returns None when state is None."""
    sensor_info = {"sensor_key": "srain_piezo", "hardware_id": "ABC123", "name": ""}
    entity = EcowittStateBinarySensor(
        mock_coordinator, "ecowitt_rain_abc123", sensor_info
    )
    mock_coordinator.get_all_sensors.return_value = {
        "ecowitt_rain_abc123": {"state": None}
    }
    assert entity.is_on is None


def test_state_binary_sensor_is_on_invalid_state(mock_coordinator):
    """Test is_on returns None when state cannot be converted to number."""
    sensor_info = {"sensor_key": "srain_piezo", "hardware_id": "ABC123", "name": ""}
    entity = EcowittStateBinarySensor(
        mock_coordinator, "ecowitt_rain_abc123", sensor_info
    )
    mock_coordinator.get_all_sensors.return_value = {
        "ecowitt_rain_abc123": {"state": "notanumber"}
    }
    assert entity.is_on is None


def test_state_binary_sensor_device_info_with_hardware_id(mock_coordinator):
    """Test device_info with a real hardware ID uses sensor device."""
    sensor_info = {"sensor_key": "srain_piezo", "hardware_id": "ABC123", "name": ""}
    entity = EcowittStateBinarySensor(
        mock_coordinator, "ecowitt_rain_abc123", sensor_info
    )
    device_info = entity.device_info

    assert device_info["identifiers"] == {(DOMAIN, "ABC123")}
    assert device_info["manufacturer"] == MANUFACTURER
    assert device_info["via_device"] == (DOMAIN, "test_gateway")


def test_state_binary_sensor_device_info_no_sensor_info(mock_coordinator):
    """Test device_info falls back to gateway when sensor_mapper returns None."""
    mock_coordinator.sensor_mapper.get_sensor_info.return_value = None
    sensor_info = {"sensor_key": "srain_piezo", "hardware_id": "ABC123", "name": ""}
    entity = EcowittStateBinarySensor(
        mock_coordinator, "ecowitt_rain_abc123", sensor_info
    )
    device_info = entity.device_info

    assert device_info["identifiers"] == {(DOMAIN, "test_gateway")}


def test_state_binary_sensor_device_info_placeholder_id(mock_coordinator):
    """Test device_info uses gateway device when hardware_id is placeholder."""
    sensor_info = {"sensor_key": "srain_piezo", "hardware_id": "FFFFFFFF", "name": ""}
    entity = EcowittStateBinarySensor(
        mock_coordinator, "ecowitt_rain_abc123", sensor_info
    )
    device_info = entity.device_info

    assert device_info["identifiers"] == {(DOMAIN, "test_gateway")}


def test_state_binary_sensor_extra_state_attributes(mock_coordinator):
    """Test extra_state_attributes returns hardware_id and sensor attributes."""
    sensor_info = {"sensor_key": "srain_piezo", "hardware_id": "ABC123", "name": ""}
    entity = EcowittStateBinarySensor(
        mock_coordinator, "ecowitt_rain_abc123", sensor_info
    )
    mock_coordinator.get_all_sensors.return_value = {
        "ecowitt_rain_abc123": {
            "state": "0",
            "attributes": {"sensor_key": "srain_piezo", "last_update": "2024-01-01"},
        }
    }
    attrs = entity.extra_state_attributes
    assert attrs[ATTR_HARDWARE_ID] == "ABC123"
    assert attrs["sensor_key"] == "srain_piezo"
    assert attrs["last_update"] == "2024-01-01"


def test_state_binary_sensor_handle_coordinator_update(mock_coordinator):
    """Test _handle_coordinator_update calls async_write_ha_state."""
    sensor_info = {"sensor_key": "srain_piezo", "hardware_id": "ABC123", "name": ""}
    entity = EcowittStateBinarySensor(
        mock_coordinator, "ecowitt_rain_abc123", sensor_info
    )
    with patch.object(entity, "async_write_ha_state") as mock_write:
        entity._handle_coordinator_update()
        mock_write.assert_called_once()
