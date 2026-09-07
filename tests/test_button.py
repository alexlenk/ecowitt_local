"""Test the Ecowitt Local button platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from custom_components.ecowitt_local.button import (
    EcowittResyncMappingButton,
    async_setup_entry,
)
from custom_components.ecowitt_local.const import DOMAIN, MANUFACTURER
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
    coordinator.async_refresh_mapping = AsyncMock()
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    return entry


@pytest.mark.asyncio
async def test_async_setup_entry(mock_coordinator, mock_config_entry):
    """Test setting up the resync mapping button entity."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {DOMAIN: {"test_entry": mock_coordinator}}

    added_entities = []
    async_add_entities = Mock(
        side_effect=lambda entities: added_entities.extend(entities)
    )

    await async_setup_entry(hass, mock_config_entry, async_add_entities)

    assert len(added_entities) == 1
    assert isinstance(added_entities[0], EcowittResyncMappingButton)


def test_resync_button_init(mock_coordinator):
    """Test EcowittResyncMappingButton initialization."""
    entity = EcowittResyncMappingButton(mock_coordinator)

    assert entity.unique_id == f"{DOMAIN}_test_gateway_resync_mapping"
    assert entity.entity_id == "button.ecowitt_gateway_test_gateway_resync_mapping"
    assert "Resync Sensor Mappings" in entity.name
    assert entity.entity_category == EntityCategory.DIAGNOSTIC


@pytest.mark.asyncio
async def test_resync_button_press(mock_coordinator):
    """Test pressing the button refreshes the sensor mapping."""
    entity = EcowittResyncMappingButton(mock_coordinator)

    await entity.async_press()

    mock_coordinator.async_refresh_mapping.assert_called_once()


def test_resync_button_device_info(mock_coordinator):
    """Test resync button device_info property."""
    entity = EcowittResyncMappingButton(mock_coordinator)

    device_info = entity.device_info

    assert device_info["identifiers"] == {(DOMAIN, "test_gateway")}
    assert "Gateway 192.168.1.100" in device_info["name"]
    assert device_info["manufacturer"] == MANUFACTURER
    assert device_info["model"] == "GW1100A"
    assert device_info["sw_version"] == "1.7.3"
    assert device_info["configuration_url"] == "http://192.168.1.100"
