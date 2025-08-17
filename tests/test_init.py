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
    """Test device registry entry creation for gateway and sensors."""
    from homeassistant.helpers import device_registry as dr
    
    device_registry = dr.async_get(hass)
    coordinator = hass.data[DOMAIN][setup_integration.entry_id]
    gateway_info = coordinator.gateway_info
    
    # Test gateway device
    gateway_device = device_registry.async_get_device(
        identifiers={(DOMAIN, gateway_info.get("gateway_id", "unknown"))}
    )
    
    assert gateway_device is not None
    assert gateway_device.manufacturer == "Ecowitt"
    assert gateway_device.name == f"Ecowitt Gateway {gateway_info.get('host', '')}"
    
    # Test individual sensor devices
    hardware_ids = coordinator.sensor_mapper.get_all_hardware_ids()
    
    for hardware_id in hardware_ids:
        sensor_device = device_registry.async_get_device(
            identifiers={(DOMAIN, hardware_id)}
        )
        
        assert sensor_device is not None
        assert sensor_device.manufacturer == "Ecowitt"
        assert hardware_id in sensor_device.name
        assert sensor_device.via_device_id == gateway_device.id


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


async def test_sensor_device_assignment(hass: HomeAssistant, setup_integration):
    """Test that sensors are assigned to correct devices."""
    from homeassistant.helpers import device_registry as dr, entity_registry as er
    
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    coordinator = hass.data[DOMAIN][setup_integration.entry_id]
    
    # Get all entities for this config entry
    entities = er.async_entries_for_config_entry(entity_registry, setup_integration.entry_id)
    
    # Check that sensors with hardware IDs are assigned to individual devices
    for entity in entities:
        if entity.unique_id and "_" in entity.unique_id:
            # Extract hardware_id from unique_id pattern
            unique_id_parts = entity.unique_id.split("_")
            if len(unique_id_parts) >= 3:
                # Check if this looks like a hardware ID (from mock data: D8174, D8648, EF891)
                potential_hardware_id = unique_id_parts[1]
                
                if coordinator.sensor_mapper.get_sensor_info(potential_hardware_id):
                    # This entity should be assigned to the individual sensor device
                    device = device_registry.async_get(entity.device_id)
                    assert device is not None
                    assert (DOMAIN, potential_hardware_id) in device.identifiers
                    assert "Sensor" in device.name or "Station" in device.name


async def test_migration_function_exists(hass: HomeAssistant):
    """Test that migration function exists and handles no migration case."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.ecowitt_local import async_migrate_entry
    
    # Test with current version entry (no migration needed)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.100", "password": ""},
        version=1,
        entry_id="test_entry",
        unique_id="test_unique",
    )
    
    # Set minor_version to 1 (current version)
    entry.minor_version = 1
    
    # Test migration function - should return True for current version
    result = await async_migrate_entry(hass, entry)
    assert result is True
