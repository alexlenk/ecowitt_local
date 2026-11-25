"""Verify wind bearings use Home Assistant's dynamic direction icons."""

from unittest.mock import Mock

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import DEGREE
from homeassistant.core import HomeAssistant

from custom_components.ecowitt_local.const import DOMAIN, SENSOR_TYPES
from custom_components.ecowitt_local.sensor import EcowittLocalSensor

DIRECTION_KEYS = ("winddir", "winddir_avg10m", "0x0A", "0x6D")


@pytest.mark.parametrize("sensor_key", DIRECTION_KEYS)
@pytest.mark.parametrize("bearing", (0, 22.5, 45, 90, 135, 180, 225, 270, 315, 360))
def test_direction_uses_native_dynamic_icons(
    hass: HomeAssistant, mock_config_entry, sensor_key, bearing
):
    """Expose the native wind direction class without overriding its icons."""
    definition = SENSOR_TYPES[sensor_key]
    sensor_info = {
        **definition,
        "sensor_key": sensor_key,
        "unit_of_measurement": definition["unit"],
        "category": "sensor",
        "state": bearing,
    }
    coordinator = Mock()
    coordinator.hass = hass
    coordinator.config_entry = mock_config_entry
    coordinator.last_update_success = True
    coordinator.get_sensor_data_by_key.return_value = sensor_info
    sensor = EcowittLocalSensor(coordinator, "sensor.existing_direction", sensor_info)

    assert sensor.device_class == SensorDeviceClass.WIND_DIRECTION
    assert sensor.state_class == SensorStateClass.MEASUREMENT_ANGLE
    assert sensor.native_unit_of_measurement == DEGREE
    assert sensor.native_value == bearing
    # An explicit icon would override HA's direction-dependent arrow icons.
    assert sensor.icon is None
    assert sensor.entity_id == "sensor.existing_direction"
    assert sensor.unique_id == f"{DOMAIN}_{mock_config_entry.entry_id}_{sensor_key}"


@pytest.mark.parametrize("sensor_key", DIRECTION_KEYS)
def test_direction_updates_and_unavailable_values(
    hass: HomeAssistant, mock_config_entry, sensor_key
):
    """A new bearing reaches the frontend without changing identity or units."""
    definition = SENSOR_TYPES[sensor_key]
    sensor_info = {
        **definition,
        "sensor_key": sensor_key,
        "unit_of_measurement": definition["unit"],
        "category": "sensor",
        "state": 0,
    }
    coordinator = Mock()
    coordinator.hass = hass
    coordinator.config_entry = mock_config_entry
    coordinator.last_update_success = True
    coordinator.get_sensor_data_by_key.return_value = sensor_info
    sensor = EcowittLocalSensor(coordinator, "sensor.existing_direction", sensor_info)
    sensor.async_write_ha_state = Mock()
    unique_id = sensor.unique_id

    sensor_info["state"] = 270
    sensor._handle_coordinator_update()

    assert sensor.native_value == 270
    assert sensor.icon is None
    assert sensor.device_class == SensorDeviceClass.WIND_DIRECTION
    assert sensor.available is True
    assert sensor.unique_id == unique_id
    assert sensor.entity_id == "sensor.existing_direction"
    sensor.async_write_ha_state.assert_called_once()

    sensor_info["state"] = None
    sensor._handle_coordinator_update()
    assert sensor.native_value is None
    assert sensor.icon is None
    assert sensor.device_class == SensorDeviceClass.WIND_DIRECTION

    coordinator.last_update_success = False
    assert sensor.available is False

    coordinator.last_update_success = True
    coordinator.get_sensor_data_by_key.return_value = None
    coordinator.get_sensor_data.return_value = None
    assert sensor.available is False
