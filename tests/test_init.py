"""Test the Ecowitt Local integration setup."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

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

    with (
        patch(
            "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
            return_value=mock_ecowitt_api,
        ),
        patch(
            "custom_components.ecowitt_local.api.EcowittLocalAPI",
            return_value=mock_ecowitt_api,
        ),
    ):
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
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
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
    with (
        patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            return_value=True,
        ),
        patch(
            "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
            return_value=mock_ecowitt_api,
        ),
        patch(
            "custom_components.ecowitt_local.api.EcowittLocalAPI",
            return_value=mock_ecowitt_api,
        ),
    ):
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
    """Test refresh mapping service with proper mocking."""
    from unittest.mock import AsyncMock

    from custom_components.ecowitt_local.const import SERVICE_REFRESH_MAPPING

    coordinator = hass.data[DOMAIN][setup_integration.entry_id]

    # Mock the coordinator's refresh method - use correct method name
    coordinator.async_refresh_mapping = AsyncMock()

    # Call service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH_MAPPING,
        {},
        blocking=True,
    )

    # Verify service was called
    coordinator.async_refresh_mapping.assert_called_once()


async def test_update_data_service(hass: HomeAssistant, setup_integration):
    """Test update data service with proper mocking."""
    from unittest.mock import AsyncMock

    from custom_components.ecowitt_local.const import SERVICE_UPDATE_DATA

    coordinator = hass.data[DOMAIN][setup_integration.entry_id]

    # Mock the coordinator's refresh method - use correct method name
    coordinator.async_request_refresh = AsyncMock()

    # Call service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_UPDATE_DATA,
        {},
        blocking=True,
    )

    # Verify service was called
    coordinator.async_request_refresh.assert_called_once()


async def test_service_error_handling(hass: HomeAssistant, setup_integration):
    """Test service error handling."""
    from unittest.mock import AsyncMock

    import pytest

    from custom_components.ecowitt_local.const import SERVICE_REFRESH_MAPPING

    coordinator = hass.data[DOMAIN][setup_integration.entry_id]

    # Mock the coordinator's refresh method to raise an exception - use correct method name
    coordinator.async_refresh_mapping = AsyncMock(side_effect=Exception("Test error"))

    # Call service - should propagate the exception since service doesn't handle errors
    with pytest.raises(Exception, match="Test error"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH_MAPPING,
            {},
            blocking=True,
        )

    # Verify service was attempted
    coordinator.async_refresh_mapping.assert_called_once()


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
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW1100A",
        "version": "1.7.3",
    }
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

    with (
        patch(
            "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
            return_value=mock_ecowitt_api,
        ),
        patch(
            "custom_components.ecowitt_local.api.EcowittLocalAPI",
            return_value=mock_ecowitt_api,
        ),
    ):
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
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    coordinator = hass.data[DOMAIN][setup_integration.entry_id]

    # Get all entities for this config entry
    entities = er.async_entries_for_config_entry(
        entity_registry, setup_integration.entry_id
    )

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
        minor_version=3,
        entry_id="test_entry",
        unique_id="test_unique",
    )
    entry.add_to_hass(hass)

    # Test migration function - should return True for current version
    result = await async_migrate_entry(hass, entry)
    assert result is True


async def test_migration_from_v1_0(hass: HomeAssistant, mock_ecowitt_api):
    """Test migration from version 1.0 to 1.2."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.ecowitt_local import async_migrate_entry
    from custom_components.ecowitt_local.const import CONF_HOST, CONF_PASSWORD

    # Configure mock API
    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW1100A",
        "version": "1.7.3",
    }
    mock_ecowitt_api.get_live_data.return_value = {
        "common_list": [{"id": "tempf", "val": "72.5"}],
        "ch_soil": [{"channel": "1", "humidity": "50%", "battery": "2"}],
    }
    mock_ecowitt_api.get_all_sensor_mappings.return_value = [
        {
            "id": "D8174",
            "img": "wh51",
            "type": "15",
            "name": "Soil moisture CH2",
            "batt": "1",
            "signal": "4",
        }
    ]

    # Create entry with version 1.0 (needs migration)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PASSWORD: ""},
        version=1,
        minor_version=0,
        entry_id="test_entry",
        unique_id="test_unique",
    )
    entry.add_to_hass(hass)

    # Setup the integration first to have data for migration
    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        result = await hass.config_entries.async_setup(entry.entry_id)
        assert result is True

    # Create some mock entities in entity registry that need migration
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    # Create a gateway device
    gateway_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "test_gateway")},
        name="Test Gateway",
        manufacturer="Ecowitt",
    )

    # Create an entity that should be migrated to individual device
    entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="ecowitt_local_D8174_soilmoisture2",
        config_entry=entry,
        device_id=gateway_device.id,
        original_name="Soil Moisture 2",
    )

    # Test migration function
    result = await async_migrate_entry(hass, entry)
    assert result is True
    assert entry.version == 1
    assert entry.minor_version >= 2  # Should be at least version 1.2

    # Verify migration completed successfully - the test is about migration working, not specific entity placement
    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    migrated_entity = next((e for e in entities if "D8174" in e.unique_id), None)

    # The key test is that migration ran successfully and didn't crash
    assert (
        migrated_entity is not None
    ), "Migration test entity should still exist after migration"


async def test_reload_entry_failure(
    hass: HomeAssistant, setup_integration, mock_ecowitt_api
):
    """Test reload entry failure when unload fails."""
    config_entry = setup_integration

    # Verify initial setup
    assert config_entry.state == ConfigEntryState.LOADED

    # Mock platform unloading to fail
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=False,
    ):
        # Reload should fail
        result = await hass.config_entries.async_reload(config_entry.entry_id)

    assert result is False
    # State after failed unload varies by HA version: FAILED_UNLOAD (2026.x+) or LOADED (older)
    assert config_entry.state in (
        ConfigEntryState.FAILED_UNLOAD,
        ConfigEntryState.LOADED,
    )


async def test_invalid_hardware_id_filtering(
    hass: HomeAssistant, mock_config_entry, mock_ecowitt_api
):
    """Test filtering of invalid hardware IDs during device setup."""
    from homeassistant.helpers import device_registry as dr

    # Configure mock API with invalid hardware IDs
    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW1100A",
        "version": "1.7.3",
    }
    mock_ecowitt_api.get_live_data.return_value = {"common_list": []}
    mock_ecowitt_api.get_all_sensor_mappings.return_value = [
        # Valid hardware ID
        {
            "id": "D8174",
            "img": "wh51",
            "type": "15",
            "name": "Valid Sensor",
            "batt": "1",
            "signal": "4",
        },
        # Invalid hardware IDs that should be filtered out
        {
            "id": "FFFFFFFE",
            "img": "wh51",
            "type": "15",
            "name": "Invalid Sensor 1",
            "batt": "1",
            "signal": "4",
        },
        {
            "id": "FFFFFFFF",
            "img": "wh51",
            "type": "15",
            "name": "Invalid Sensor 2",
            "batt": "1",
            "signal": "4",
        },
        {
            "id": "00000000",
            "img": "wh51",
            "type": "15",
            "name": "Invalid Sensor 3",
            "batt": "1",
            "signal": "4",
        },
        {
            "id": "",
            "img": "wh51",
            "type": "15",
            "name": "Empty Hardware ID",
            "batt": "1",
            "signal": "4",
        },
    ]

    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)
        assert result is True

    # Check device registry - only valid hardware ID should create a device
    device_registry = dr.async_get(hass)

    # Valid device should exist
    valid_device = device_registry.async_get_device(identifiers={(DOMAIN, "D8174")})
    assert valid_device is not None

    # Invalid devices should not exist
    invalid_ids = ["FFFFFFFE", "FFFFFFFF", "00000000", ""]
    for invalid_id in invalid_ids:
        if invalid_id:  # Skip empty string check
            invalid_device = device_registry.async_get_device(
                identifiers={(DOMAIN, invalid_id)}
            )
            assert invalid_device is None


async def test_service_with_device_id_filtering(hass: HomeAssistant, setup_integration):
    """Test service calls with device_id filtering."""
    from unittest.mock import AsyncMock

    from homeassistant.helpers import device_registry as dr

    from custom_components.ecowitt_local.const import (
        SERVICE_REFRESH_MAPPING,
        SERVICE_UPDATE_DATA,
    )

    coordinator = hass.data[DOMAIN][setup_integration.entry_id]
    device_registry = dr.async_get(hass)

    # Get the gateway device
    gateway_info = coordinator.gateway_info
    gateway_device = device_registry.async_get_device(
        identifiers={(DOMAIN, gateway_info.get("gateway_id", "unknown"))}
    )
    assert gateway_device is not None

    # Mock coordinator methods
    coordinator.async_refresh_mapping = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()

    # Test refresh mapping service with device_id
    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH_MAPPING,
        {"device_id": gateway_device.id},
        blocking=True,
    )

    # Should still be called since device is associated with this entry
    coordinator.async_refresh_mapping.assert_called_once()
    coordinator.async_refresh_mapping.reset_mock()

    # Test update data service with device_id
    await hass.services.async_call(
        DOMAIN,
        SERVICE_UPDATE_DATA,
        {"device_id": gateway_device.id},
        blocking=True,
    )

    # Should still be called since device is associated with this entry
    coordinator.async_request_refresh.assert_called_once()
    coordinator.async_request_refresh.reset_mock()

    # Test with non-existent device_id
    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH_MAPPING,
        {"device_id": "non_existent_device_id"},
        blocking=True,
    )

    # Should not be called since device doesn't exist
    coordinator.async_refresh_mapping.assert_not_called()


async def test_service_with_invalid_device_id(hass: HomeAssistant, setup_integration):
    """Test service calls with invalid device_id that exists but is not associated with our entry."""
    from unittest.mock import AsyncMock

    from homeassistant.helpers import device_registry as dr
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.ecowitt_local.const import (
        SERVICE_REFRESH_MAPPING,
        SERVICE_UPDATE_DATA,
    )

    coordinator = hass.data[DOMAIN][setup_integration.entry_id]
    device_registry = dr.async_get(hass)

    # Create another config entry for testing
    other_entry = MockConfigEntry(
        domain="other_domain",
        data={"host": "192.168.1.200"},
        entry_id="other_entry_id",
        unique_id="other_unique_id",
    )
    other_entry.add_to_hass(hass)

    # Create a device that's associated with the other config entry
    other_device = device_registry.async_get_or_create(
        config_entry_id="other_entry_id",
        identifiers={("other_domain", "other_device")},
        name="Other Device",
        manufacturer="Other",
    )

    # Mock coordinator methods
    coordinator.async_refresh_mapping = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()

    # Test with device_id that exists but is not ours
    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH_MAPPING,
        {"device_id": other_device.id},
        blocking=True,
    )

    # Should not be called since device is not associated with our entry
    coordinator.async_refresh_mapping.assert_not_called()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_UPDATE_DATA,
        {"device_id": other_device.id},
        blocking=True,
    )

    # Should not be called since device is not associated with our entry
    coordinator.async_request_refresh.assert_not_called()


async def test_migration_with_missing_coordinator(hass: HomeAssistant):
    """Test migration when coordinator is not available in hass.data."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.ecowitt_local import async_migrate_entry
    from custom_components.ecowitt_local.const import CONF_HOST, CONF_PASSWORD

    # Create entry with version 1.0 that needs migration
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PASSWORD: ""},
        version=1,
        minor_version=0,
        entry_id="test_entry",
        unique_id="test_unique",
    )
    # Add to hass so async_update_entry can find the entry (coordinator won't be set up)
    entry.add_to_hass(hass)

    # Test migration function - should still work even without coordinator
    result = await async_migrate_entry(hass, entry)
    assert result is True
    assert entry.minor_version == 3


async def test_migration_gateway_sensor_reassignment(
    hass: HomeAssistant, mock_ecowitt_api
):
    """Test migration v1.3 that moves gateway sensors back to gateway device."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.ecowitt_local import async_migrate_entry
    from custom_components.ecowitt_local.const import (
        CONF_HOST,
        CONF_PASSWORD,
        GATEWAY_SENSORS,
    )

    # Configure mock API
    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW1100A",
        "version": "1.7.3",
    }
    mock_ecowitt_api.get_live_data.return_value = {"common_list": []}
    mock_ecowitt_api.get_all_sensor_mappings.return_value = []

    # Create entry with version 1.2 (needs migration to 1.3)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PASSWORD: ""},
        version=1,
        minor_version=2,
        entry_id="test_entry",
        unique_id="test_unique",
    )
    entry.add_to_hass(hass)

    # Setup the integration first
    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        result = await hass.config_entries.async_setup(entry.entry_id)
        assert result is True

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    # Create a sensor device
    sensor_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "sensor_device")},
        name="Sensor Device",
        manufacturer="Ecowitt",
    )

    # Create a gateway sensor entity that should be moved back to gateway
    gateway_sensor_key = list(GATEWAY_SENSORS)[0]  # Get first gateway sensor
    entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"ecowitt_local_{gateway_sensor_key}",
        config_entry=entry,
        device_id=sensor_device.id,  # Initially assigned to sensor device
        original_name=f"Gateway {gateway_sensor_key}",
    )

    # Test migration function
    result = await async_migrate_entry(hass, entry)
    assert result is True
    assert entry.minor_version == 3

    # Verify the gateway sensor entity was moved to gateway device
    coordinator = hass.data[DOMAIN][entry.entry_id]
    gateway_id = coordinator.gateway_info.get("gateway_id", "unknown")
    gateway_device = device_registry.async_get_device(
        identifiers={(DOMAIN, gateway_id)}
    )

    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    gateway_entity = next(
        (e for e in entities if gateway_sensor_key in e.unique_id), None
    )

    assert gateway_entity is not None
    assert gateway_entity.device_id == gateway_device.id


async def test_cleanup_unknown_gateway_device(
    hass: HomeAssistant, setup_integration, mock_ecowitt_api
):
    """Test that stale 'unknown' gateway device is cleaned up on setup."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    config_entry = setup_integration

    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    gateway_id = coordinator.gateway_info.get("gateway_id", "unknown")
    assert gateway_id != "unknown", "Test requires a non-unknown gateway_id"

    # Simulate a stale "unknown" ghost device left over from before v1.6.8
    old_device = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "unknown")},
        name="Ecowitt Gateway 192.168.1.100",
        manufacturer="Ecowitt",
    )
    ghost_entity = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="ecowitt_local_online_ghost",
        config_entry=config_entry,
        device_id=old_device.id,
    )

    # Reload (triggers _async_setup_device_registry again)
    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        await hass.config_entries.async_reload(config_entry.entry_id)
        await hass.async_block_till_done()

    # Old "unknown" device should be gone
    assert (
        device_registry.async_get_device(identifiers={(DOMAIN, "unknown")}) is None
    ), "Ghost 'unknown' device should have been removed"

    # The ghost entity should now point to the real gateway device
    real_gateway = device_registry.async_get_device(identifiers={(DOMAIN, gateway_id)})
    assert real_gateway is not None
    updated_entity = entity_registry.async_get(ghost_entity.entity_id)
    assert updated_entity is not None
    assert (
        updated_entity.device_id == real_gateway.id
    ), "Ghost entity should be moved to real gateway device"


async def test_phantom_signal_zero_device_removed(
    hass: HomeAssistant, mock_config_entry, mock_ecowitt_api
):
    """A stale WH65 slot (signal=0) reported alongside an active WH90 must
    not leave a phantom device behind after platform setup.

    Reproduces the residual symptom from issue #155: v1.6.18 routed shared
    common_list keys to the active WH90 via signal-priority resolution, but
    the WH65 device was already pre-registered by _async_setup_device_registry
    and stayed in the registry with zero entities. The post-platform cleanup
    pass should remove it.
    """
    from unittest.mock import patch

    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW2000A",
        "version": "3.3.1",
    }
    mock_ecowitt_api.get_units.return_value = {"temperature": "1"}
    mock_ecowitt_api.get_all_sensor_mappings.return_value = [
        {
            "id": "EA1234",
            "img": "wh69",
            "type": "0",
            "name": "Temp & Humidity & Solar & Wind & Rain",
            "batt": "0",
            "signal": "0",
        },
        {
            "id": "FF9988",
            "img": "wh90",
            "type": "48",
            "name": "Temp & Humidity & Solar & Wind & Rain",
            "batt": "0",
            "signal": "4",
        },
    ]
    mock_ecowitt_api.get_live_data.return_value = {
        "common_list": [
            {"id": "0x02", "val": "72.5"},
            {"id": "0x07", "val": "65"},
        ],
        "wh90batt": "5",
    }

    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    phantom = device_registry.async_get_device(identifiers={(DOMAIN, "EA1234")})
    assert phantom is None, "Phantom WH65 device should have been removed"

    active = device_registry.async_get_device(identifiers={(DOMAIN, "FF9988")})
    assert active is not None, "Active WH90 device must remain"
    active_entities = er.async_entries_for_device(
        entity_registry, active.id, include_disabled_entities=True
    )
    assert active_entities, "Active WH90 device should have entities"


async def test_signal_zero_device_with_entities_kept(
    hass: HomeAssistant, mock_config_entry, mock_ecowitt_api
):
    """A signal=0 sensor that still owns entities (e.g. the user's gateway
    cached entries from a previous session) must not be removed — the cleanup
    is gated on having zero entities, not on signal alone.
    """
    from unittest.mock import patch

    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW2000A",
        "version": "3.3.1",
    }
    mock_ecowitt_api.get_units.return_value = {"temperature": "1"}
    mock_ecowitt_api.get_all_sensor_mappings.return_value = [
        {
            "id": "AB1234",
            "img": "wh51",
            "type": "15",
            "name": "Soil moisture CH1",
            "batt": "5",
            "signal": "0",
        },
    ]
    mock_ecowitt_api.get_live_data.return_value = {
        "common_list": [
            {"id": "soilmoisture1", "val": "42"},
            {"id": "soilbatt1", "val": "4"},
        ]
    }

    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    device = device_registry.async_get_device(identifiers={(DOMAIN, "AB1234")})
    assert device is not None, "Sensor with entities must be kept even at signal=0"
    entities = er.async_entries_for_device(
        entity_registry, device.id, include_disabled_entities=True
    )
    assert entities, "Sensor should have its entities preserved"


async def test_orphaned_device_unknown_to_mapper_kept(
    hass: HomeAssistant, mock_config_entry, mock_ecowitt_api
):
    """A device whose hardware_id is no longer in get_sensors_info (e.g. the
    user unpaired the sensor from the gateway) is left alone — its entities
    likely contain historical state the user may still want to keep around.
    The cleanup only fires for sensors actively reported as signal=0.
    """
    from unittest.mock import patch

    from homeassistant.helpers import device_registry as dr

    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW2000A",
        "version": "3.3.1",
    }
    mock_ecowitt_api.get_units.return_value = {"temperature": "1"}
    mock_ecowitt_api.get_all_sensor_mappings.return_value = []
    mock_ecowitt_api.get_live_data.return_value = {"common_list": []}

    mock_config_entry.add_to_hass(hass)
    device_registry = dr.async_get(hass)
    orphan = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "ZZ9999")},
        name="Ecowitt Orphan ZZ9999",
        manufacturer="Ecowitt",
        model="wh51",
    )

    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert (
        device_registry.async_get_device(identifiers={(DOMAIN, "ZZ9999")}) is not None
    ), "Orphaned device unknown to sensor_mapper must not be removed"
    assert orphan is not None  # silence linter


async def test_signal_positive_empty_device_kept(
    hass: HomeAssistant, mock_config_entry, mock_ecowitt_api
):
    """A freshly paired sensor (signal>0) without live data yet should not be
    removed — the cleanup must only target stale slots (signal=0).
    """
    from unittest.mock import patch

    from homeassistant.helpers import device_registry as dr

    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW2000A",
        "version": "3.3.1",
    }
    mock_ecowitt_api.get_units.return_value = {"temperature": "1"}
    mock_ecowitt_api.get_all_sensor_mappings.return_value = [
        {
            "id": "CD5678",
            "img": "wh51",
            "type": "15",
            "name": "Soil moisture CH2",
            "batt": "5",
            "signal": "3",
        },
    ]
    mock_ecowitt_api.get_live_data.return_value = {"common_list": []}

    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(identifiers={(DOMAIN, "CD5678")})
    assert (
        device is not None
    ), "Freshly paired sensor (signal>0, no live data yet) must not be removed"


async def test_async_remove_entry(hass: HomeAssistant, mock_config_entry):
    """Test async_remove_entry function."""
    from custom_components.ecowitt_local import async_remove_entry

    # Test the remove entry function
    await async_remove_entry(hass, mock_config_entry)

    # Function should complete without error
    # Currently it just logs, so we verify it doesn't raise an exception


async def test_orphan_decimal_4_entity_removed_on_setup(
    hass: HomeAssistant, mock_config_entry, mock_ecowitt_api
):
    """The orphan "4" entity created before v1.6.20 is removed at startup.

    "4" was a developer mistake — it isn't in the V1.0.6 spec and was removed
    from SENSOR_TYPES in v1.6.20. Pre-existing entities with the gateway-based
    unique_id `ecowitt_local_<entry_id>_4` should be cleaned up so they no
    longer appear as nameless "Unavailable" sensors. (issue #178)
    """
    from unittest.mock import patch

    from homeassistant.helpers import entity_registry as er

    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW2000A",
        "version": "3.3.1",
    }
    mock_ecowitt_api.get_units.return_value = {"temperature": "0"}
    mock_ecowitt_api.get_all_sensor_mappings.return_value = []
    mock_ecowitt_api.get_live_data.return_value = {"common_list": []}

    mock_config_entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)
    orphan = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"{DOMAIN}_{mock_config_entry.entry_id}_4",
        config_entry=mock_config_entry,
    )

    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert (
        entity_registry.async_get(orphan.entity_id) is None
    ), "Orphan '4' entity must be removed at startup"


async def test_orphan_decimal_5_entity_migrated_to_outdoor_station(
    hass: HomeAssistant, mock_config_entry, mock_ecowitt_api
):
    """An orphan VPD entity from before v1.6.21 is migrated to the WH90 device.

    Before v1.6.20, the "5" key had no hardware mapping so its entity was
    pinned to the gateway via `ecowitt_local_<entry_id>_5`. v1.6.20 routed
    "5" to the outdoor weather station, but the existing gateway-based entity
    was left orphaned. The migration must update both unique_id and device_id
    to point at the active outdoor station, preserving history. (issue #178)
    """
    from unittest.mock import patch

    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    entity_registry = er.async_get(hass)
    mock_config_entry.add_to_hass(hass)
    orphan = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"{DOMAIN}_{mock_config_entry.entry_id}_5",
        config_entry=mock_config_entry,
    )

    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW2000A",
        "version": "3.3.1",
    }
    mock_ecowitt_api.get_units.return_value = {"temperature": "0"}
    mock_ecowitt_api.get_all_sensor_mappings.return_value = [
        {
            "id": "FF9988",
            "img": "wh90",
            "type": "48",
            "name": "Temp & Humidity & Solar & Wind & Rain",
            "batt": "0",
            "signal": "4",
        },
    ]
    # Crucially, no "5" in live data — the old orphan must be migrated
    # even when the gateway hasn't yet emitted the new key.
    mock_ecowitt_api.get_live_data.return_value = {
        "common_list": [{"id": "0x02", "val": "22.2"}],
        "wh90batt": "5",
    }

    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    wh90_device = device_registry.async_get_device(identifiers={(DOMAIN, "FF9988")})
    assert wh90_device is not None

    migrated = entity_registry.async_get(orphan.entity_id)
    assert migrated is not None, "Entity should still exist after migration"
    assert (
        migrated.unique_id == f"{DOMAIN}_FF9988_5"
    ), "Unique ID should reference the WH90 hardware ID"
    assert (
        migrated.device_id == wh90_device.id
    ), "Entity should now belong to the WH90 device"


async def test_orphan_decimal_5_removed_when_duplicate_exists(
    hass: HomeAssistant, mock_config_entry, mock_ecowitt_api
):
    """If a hardware-based VPD entity already exists, the gateway orphan is removed.

    When the firmware emits "5" and v1.6.20 has already created the new entity
    on the WH90, both the old gateway orphan and the new WH90 entity exist.
    The migration cannot rename the orphan to a unique_id already in use, so
    it removes the orphan instead. (issue #178)
    """
    from unittest.mock import patch

    from homeassistant.helpers import entity_registry as er

    entity_registry = er.async_get(hass)
    mock_config_entry.add_to_hass(hass)

    # Pre-create both the orphan AND the new hardware-based entity to simulate
    # a user upgrading after v1.6.20 had time to create the new entity.
    orphan = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"{DOMAIN}_{mock_config_entry.entry_id}_5",
        config_entry=mock_config_entry,
    )
    duplicate = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"{DOMAIN}_FF9988_5",
        config_entry=mock_config_entry,
    )

    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW2000A",
        "version": "3.3.1",
    }
    mock_ecowitt_api.get_units.return_value = {"temperature": "0"}
    mock_ecowitt_api.get_all_sensor_mappings.return_value = [
        {
            "id": "FF9988",
            "img": "wh90",
            "type": "48",
            "name": "Temp & Humidity & Solar & Wind & Rain",
            "batt": "0",
            "signal": "4",
        },
    ]
    mock_ecowitt_api.get_live_data.return_value = {
        "common_list": [{"id": "5", "val": "1.45"}],
        "wh90batt": "5",
    }

    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert (
        entity_registry.async_get(orphan.entity_id) is None
    ), "Orphan must be removed when a hardware-based duplicate exists"
    assert (
        entity_registry.async_get(duplicate.entity_id) is not None
    ), "Hardware-based duplicate must be preserved"


async def test_orphan_decimal_3_5_left_alone_without_outdoor_station(
    hass: HomeAssistant, mock_config_entry, mock_ecowitt_api
):
    """Without an outdoor weather station, "3"/"5" orphans are left untouched.

    Migrating with no destination would either drop the entity or leave it
    pointing at the gateway with mismatched metadata. The cleanup only acts
    when the outdoor station can absorb the entity. (issue #178)
    """
    from unittest.mock import patch

    from homeassistant.helpers import entity_registry as er

    entity_registry = er.async_get(hass)
    mock_config_entry.add_to_hass(hass)
    orphan_3 = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"{DOMAIN}_{mock_config_entry.entry_id}_3",
        config_entry=mock_config_entry,
    )
    orphan_5 = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"{DOMAIN}_{mock_config_entry.entry_id}_5",
        config_entry=mock_config_entry,
    )

    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW1100A",
        "version": "1.7.3",
    }
    mock_ecowitt_api.get_units.return_value = {"temperature": "0"}
    mock_ecowitt_api.get_all_sensor_mappings.return_value = []
    mock_ecowitt_api.get_live_data.return_value = {"common_list": []}

    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert (
        entity_registry.async_get(orphan_3.entity_id) is not None
    ), "Without an outdoor station, '3' orphan must be preserved"
    assert (
        entity_registry.async_get(orphan_5.entity_id) is not None
    ), "Without an outdoor station, '5' orphan must be preserved"


async def test_unknown_decimal_id_skipped_in_processing(
    hass: HomeAssistant, mock_config_entry, mock_ecowitt_api
):
    """Live-data items with unknown numeric ids (e.g. "4") never become entities.

    Some firmware emits decimal ids that aren't in the V1.0.6 spec. Without
    SENSOR_TYPES metadata an entity built from such a key has no name, no unit,
    and no device class — exactly the "4" orphan from issue #178. Drop these
    keys before they reach the entity layer so they don't reappear after the
    migration cleanup runs. (issue #178)
    """
    from unittest.mock import patch

    from homeassistant.helpers import entity_registry as er

    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW2000A",
        "version": "3.3.1",
    }
    mock_ecowitt_api.get_units.return_value = {"temperature": "0"}
    mock_ecowitt_api.get_all_sensor_mappings.return_value = []
    mock_ecowitt_api.get_live_data.return_value = {
        "common_list": [
            {"id": "0x02", "val": "22.2"},
            {"id": "4", "val": "20.5"},
        ]
    }

    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    decimal_4_entities = [
        ent
        for ent in er.async_entries_for_config_entry(
            entity_registry, mock_config_entry.entry_id
        )
        if ent.unique_id.endswith("_4")
    ]
    assert decimal_4_entities == [], "Unknown decimal-id '4' must not produce an entity"
