"""Verify translated binary/button names preserve identifiers and behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations

from custom_components.ecowitt_local.binary_sensor import (
    EcowittGatewayOnlineBinarySensor,
    EcowittSensorOnlineBinarySensor,
    EcowittStateBinarySensor,
)
from custom_components.ecowitt_local.button import EcowittResyncMappingButton
from custom_components.ecowitt_local.const import DOMAIN
from custom_components.ecowitt_local.coordinator import (
    EcowittLocalDataUpdateCoordinator,
)


@pytest.fixture
def localization_coordinator():
    """Return a gateway with a known live sensor and a mapping refresh action."""
    coordinator = Mock(spec=EcowittLocalDataUpdateCoordinator)
    coordinator.gateway_info = {
        "gateway_id": "gw_123",
        "host": "192.168.1.100",
        "model": "GW1100A",
        "firmware_version": "1.7.3",
    }
    coordinator.last_update_success = True
    coordinator.sensor_mapper = Mock()
    coordinator.sensor_mapper.get_sensor_info.return_value = None
    coordinator.get_all_sensors.return_value = {
        "sensor.example": {"hardware_id": "ABC123", "state": "0"}
    }
    coordinator.async_refresh_mapping = AsyncMock()
    return coordinator


@pytest.mark.parametrize("language", ["en", "de"])
@pytest.mark.parametrize(
    ("sensor_key", "type_key", "english_type", "german_type"),
    [
        ("soilmoisture1", "soil_moisture", "Soil Moisture", "Bodenfeuchtigkeit"),
        ("temp1f", "temperature", "Temperature", "Temperatur"),
        ("pm25_ch1", "pm25", "Pm25", "PM2.5"),
        ("leak_ch1", "leak", "Leak", "Leckage"),
        ("lightning_num", "lightning", "Lightning", "Blitz"),
        ("rainratein", "rain", "Rain", "Regen"),
        ("winddir", "wind", "Wind", "Wind"),
        ("unknown_sensor", "sensor", "Sensor", "Sensor"),
    ],
)
async def test_standalone_online_names_and_ids(
    hass: HomeAssistant,
    localization_coordinator,
    language,
    sensor_key,
    type_key,
    english_type,
    german_type,
):
    """All standalone online types translate without changing stable IDs."""
    entity = EcowittSensorOnlineBinarySensor(
        localization_coordinator, "ABC123", {"sensor_key": sensor_key}
    )
    english_name = f"Ecowitt {english_type} ABC123 Online"
    assert entity.name == english_name

    hass.config.language = language
    await async_get_translations(hass, language, "entity", {DOMAIN})
    entity.hass = hass

    expected_type = german_type if language == "de" else english_type
    assert entity.name == f"Ecowitt {expected_type} ABC123 Online"
    assert entity.entity_id == f"binary_sensor.ecowitt_{type_key}_abc123_online"
    assert entity.unique_id == f"{DOMAIN}_ABC123_online"
    assert entity.has_entity_name is False
    assert entity.is_on is True
    assert entity.device_class == BinarySensorDeviceClass.CONNECTIVITY


@pytest.mark.parametrize("language", ["en", "de"])
async def test_hardware_online_name_keeps_device_prefix_behavior(
    hass: HomeAssistant, localization_coordinator, language
):
    """Hardware online entities keep their short name and their own device."""
    localization_coordinator.sensor_mapper.get_sensor_info.return_value = {
        "sensor_type": "WH51",
        "device_model": "WH51",
    }
    entity = EcowittSensorOnlineBinarySensor(
        localization_coordinator, "ABC123", {"sensor_key": "soilmoisture1"}
    )
    hass.config.language = language
    await async_get_translations(hass, language, "entity", {DOMAIN})
    entity.hass = hass

    assert entity.name == "Online"
    assert entity.has_entity_name is True
    assert entity.device_info["identifiers"] == {(DOMAIN, "ABC123")}
    assert entity.device_info["name"] == "Ecowitt Soil Moisture Sensor ABC123"
    assert entity.device_info["translation_key"] == "soil_moisture_sensor"
    assert entity.unique_id == f"{DOMAIN}_ABC123_online"
    assert entity.entity_id == "binary_sensor.ecowitt_soil_moisture_abc123_online"


@pytest.mark.parametrize("language", ["en", "de"])
@pytest.mark.parametrize("english_name", ["Srain Piezo", "Rain State Piezo"])
async def test_rain_state_translation_preserves_values_and_ids(
    hass: HomeAssistant, localization_coordinator, language, english_name
):
    """Translate both existing rain labels while keeping moisture semantics."""
    entity_id = "sensor.ecowitt_srain_abc123"
    sensor_info = {
        "sensor_key": "srain_piezo",
        "hardware_id": "ABC123",
        "name": english_name,
    }
    entity = EcowittStateBinarySensor(localization_coordinator, entity_id, sensor_info)
    assert entity.name == english_name
    hass.config.language = language
    await async_get_translations(hass, language, "entity", {DOMAIN})
    entity.hass = hass

    assert entity.name == ("Regenstatus (Piezo)" if language == "de" else english_name)
    assert entity.unique_id == f"{DOMAIN}_{entity_id}"
    assert entity.entity_id == "binary_sensor.ecowitt_srain_abc123"
    assert entity.device_class == BinarySensorDeviceClass.MOISTURE
    assert entity.has_entity_name is False
    for state, expected in [("0", False), ("1", True), (None, None)]:
        localization_coordinator.get_all_sensors.return_value = {
            entity_id: {"state": state}
        }
        assert entity.is_on is expected


async def test_custom_rain_name_is_retained(
    hass: HomeAssistant, localization_coordinator
):
    """An unknown or user-defined state sensor name is never overwritten."""
    entity = EcowittStateBinarySensor(
        localization_coordinator,
        "sensor.ecowitt_srain_abc123",
        {
            "sensor_key": "srain_piezo",
            "hardware_id": "ABC123",
            "name": "Dachterrasse Regen",
        },
    )
    hass.config.language = "de"
    await async_get_translations(hass, "de", "entity", {DOMAIN})
    entity.hass = hass
    assert entity.name == "Dachterrasse Regen"


@pytest.mark.parametrize("language", ["en", "de"])
async def test_gateway_and_button_names_preserve_refresh_and_connectivity(
    hass: HomeAssistant, localization_coordinator, language
):
    """Gateway labels translate without affecting connectivity or resync."""
    gateway = EcowittGatewayOnlineBinarySensor(localization_coordinator)
    button = EcowittResyncMappingButton(localization_coordinator)
    hass.config.language = language
    await async_get_translations(hass, language, "entity", {DOMAIN})
    gateway.hass = hass
    button.hass = hass

    assert gateway.name == (
        "Ecowitt-Gateway 192.168.1.100 Online"
        if language == "de"
        else "Ecowitt Gateway 192.168.1.100 Online"
    )
    assert gateway.entity_id == "binary_sensor.ecowitt_gateway_gw_123_online"
    assert gateway.unique_id == f"{DOMAIN}_gw_123_gateway_online"
    assert gateway.has_entity_name is False
    assert gateway.is_on is True
    localization_coordinator.last_update_success = False
    assert gateway.is_on is False

    assert button.name == (
        "Ecowitt-Gateway 192.168.1.100 Sensorzuordnung neu einlesen"
        if language == "de"
        else "Ecowitt Gateway 192.168.1.100 Resync Sensor Mappings"
    )
    assert button.entity_id == "button.ecowitt_gateway_gw_123_resync_mapping"
    assert button.unique_id == f"{DOMAIN}_gw_123_resync_mapping"
    assert button.has_entity_name is False
    assert gateway.device_info["identifiers"] == {(DOMAIN, "gw_123")}
    assert button.device_info["identifiers"] == {(DOMAIN, "gw_123")}
    assert button.device_info["translation_key"] == "gateway"
    await button.async_press()
    localization_coordinator.async_refresh_mapping.assert_awaited_once()
