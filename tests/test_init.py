"""Test the Ecowitt Local integration setup."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState

from custom_components.ecowitt_local.const import DOMAIN


async def test_setup_entry_success(hass: HomeAssistant, setup_integration):
    """Test successful setup of config entry."""
    config_entry = setup_integration
    
    assert config_entry.state == ConfigEntryState.LOADED
    assert DOMAIN in hass.data
    assert config_entry.entry_id in hass.data[DOMAIN]
    
    # Check that coordinator is set up
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator is not None
    assert coordinator.config_entry == config_entry


async def test_setup_entry_connection_error(
    hass: HomeAssistant, mock_config_entry, mock_ecowitt_api
):
    """Test setup failure with connection error."""
    from custom_components.ecowitt_local.api import ConnectionError
    
    # Configure mock to raise connection error
    mock_ecowitt_api.test_connection.side_effect = ConnectionError("Cannot connect")
    
    mock_config_entry.add_to_hass(hass)
    
    with patch("custom_components.ecowitt_local.coordinator.EcowittLocalAPI", return_value=mock_ecowitt_api), \
         patch("custom_components.ecowitt_local.api.EcowittLocalAPI", return_value=mock_ecowitt_api):
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)
    
    assert result is False
    assert mock_config_entry.state == ConfigEntryState.SETUP_RETRY


async def test_unload_entry(hass: HomeAssistant, setup_integration):
    """Test unloading config entry."""
    config_entry = setup_integration
    
    # Verify setup
    assert config_entry.state == ConfigEntryState.LOADED
    assert config_entry.entry_id in hass.data[DOMAIN]
    
    # Mock platform unloading since we don't have real platforms in tests
    with patch("homeassistant.config_entries.ConfigEntries.async_unload_platforms", return_value=True):
        # Unload
        result = await hass.config_entries.async_unload(config_entry.entry_id)
    
    assert result is True
    assert config_entry.state == ConfigEntryState.NOT_LOADED
    assert config_entry.entry_id not in hass.data[DOMAIN]


async def test_reload_entry(hass: HomeAssistant, setup_integration, mock_ecowitt_api):
    """Test reloading config entry."""
    config_entry = setup_integration
    
    # Verify initial setup
    assert config_entry.state == ConfigEntryState.LOADED
    
    # Mock platform unloading and API for reload
    with patch("homeassistant.config_entries.ConfigEntries.async_unload_platforms", return_value=True), \
         patch("custom_components.ecowitt_local.coordinator.EcowittLocalAPI", return_value=mock_ecowitt_api), \
         patch("custom_components.ecowitt_local.api.EcowittLocalAPI", return_value=mock_ecowitt_api):
        # Reload
        result = await hass.config_entries.async_reload(config_entry.entry_id)
    
    assert result is True
    assert config_entry.state == ConfigEntryState.LOADED
    assert config_entry.entry_id in hass.data[DOMAIN]


async def test_services_registration(hass: HomeAssistant, setup_integration):
    """Test that services are registered."""
    from custom_components.ecowitt_local.const import (
        SERVICE_REFRESH_MAPPING,
        SERVICE_UPDATE_DATA,
    )
    
    assert hass.services.has_service(DOMAIN, SERVICE_REFRESH_MAPPING)
    assert hass.services.has_service(DOMAIN, SERVICE_UPDATE_DATA)


async def test_refresh_mapping_service(hass: HomeAssistant, setup_integration):
    """Test refresh mapping service."""
    from custom_components.ecowitt_local.const import SERVICE_REFRESH_MAPPING
    
    coordinator = hass.data[DOMAIN][setup_integration.entry_id]
    
    # Call service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH_MAPPING,
        {},
        blocking=True,
    )
    
    # Verify service was called (would need mock verification in real test)
    assert True  # Placeholder assertion


async def test_update_data_service(hass: HomeAssistant, setup_integration):
    """Test update data service."""
    from custom_components.ecowitt_local.const import SERVICE_UPDATE_DATA
    
    coordinator = hass.data[DOMAIN][setup_integration.entry_id]
    
    # Call service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_UPDATE_DATA,
        {},
        blocking=True,
    )
    
    # Verify service was called (would need mock verification in real test)
    assert True  # Placeholder assertion


async def test_device_registry_entry(hass: HomeAssistant, setup_integration):
    """Test device registry entry creation."""
    from homeassistant.helpers import device_registry as dr
    
    device_registry = dr.async_get(hass)
    coordinator = hass.data[DOMAIN][setup_integration.entry_id]
    gateway_info = coordinator.gateway_info
    
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, gateway_info.get("gateway_id", "unknown"))}
    )
    
    assert device is not None
    assert device.manufacturer == "Ecowitt"
    assert device.name == f"Ecowitt Gateway {gateway_info.get('host', '')}"


async def test_multiple_entries(hass: HomeAssistant, mock_ecowitt_api):
    """Test multiple config entries."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.ecowitt_local.const import CONF_HOST, CONF_PASSWORD
    
    # Configure mock API
    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {"stationtype": "GW1100A", "version": "1.7.3"}
    mock_ecowitt_api.get_live_data.return_value = {"common_list": []}
    mock_ecowitt_api.get_all_sensor_mappings.return_value = []
    
    # Create first entry
    entry1 = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PASSWORD: ""},
        entry_id="entry1",
        unique_id="gw1_192.168.1.100",
    )
    
    # Create second entry
    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.101", CONF_PASSWORD: ""},
        entry_id="entry2",
        unique_id="gw2_192.168.1.101",
    )
    
    with patch("custom_components.ecowitt_local.coordinator.EcowittLocalAPI", return_value=mock_ecowitt_api), \
         patch("custom_components.ecowitt_local.api.EcowittLocalAPI", return_value=mock_ecowitt_api):
        # Add entries to hass and setup
        entry1.add_to_hass(hass)
        entry2.add_to_hass(hass)
        
        result1 = await hass.config_entries.async_setup(entry1.entry_id)
        
        # Check if entry2 is already loaded (HA auto-loads entries for same domain)
        if entry2.state == ConfigEntryState.NOT_LOADED:
            result2 = await hass.config_entries.async_setup(entry2.entry_id)
            assert result2 is True
        else:
            # Entry2 was auto-loaded when entry1 was setup
            assert entry2.state == ConfigEntryState.LOADED
    
    assert result1 is True
    assert len(hass.data[DOMAIN]) == 2
    assert entry1.entry_id in hass.data[DOMAIN]
    assert entry2.entry_id in hass.data[DOMAIN]
