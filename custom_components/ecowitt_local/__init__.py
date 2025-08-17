"""The Ecowitt Local integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .api import EcowittLocalAPI
from .const import DOMAIN, SERVICE_REFRESH_MAPPING, SERVICE_UPDATE_DATA
from .coordinator import EcowittLocalDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ecowitt Local from a config entry."""
    _LOGGER.info("Setting up Ecowitt Local integration for %s", entry.data[CONF_HOST])
    
    # Create and setup coordinator
    coordinator = EcowittLocalDataUpdateCoordinator(hass, entry)
    
    try:
        await coordinator.async_setup()
    except Exception as err:
        _LOGGER.error("Failed to setup coordinator: %s", err)
        raise ConfigEntryNotReady(f"Failed to setup coordinator: {err}") from err
    
    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await _async_register_services(hass)
    
    # Setup device registry entry
    await _async_setup_device_registry(hass, entry, coordinator)
    
    _LOGGER.info("Ecowitt Local integration setup complete")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Ecowitt Local integration for %s", entry.data[CONF_HOST])
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Shutdown coordinator
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_shutdown()
        
        # Remove from hass data
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Remove services if no other instances
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH_MAPPING)
            hass.services.async_remove(DOMAIN, SERVICE_UPDATE_DATA)
    
    return bool(unload_ok)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload config entry."""
    unload_ok = await async_unload_entry(hass, entry)
    if unload_ok:
        return await async_setup_entry(hass, entry)
    return False


async def _async_setup_device_registry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: EcowittLocalDataUpdateCoordinator,
) -> None:
    """Set up device registry entries for gateway and individual sensors."""
    device_registry = dr.async_get(hass)
    gateway_info = coordinator.gateway_info
    gateway_id = gateway_info.get("gateway_id", "unknown")
    
    # Create configuration URL only if host is available
    host = gateway_info.get('host', '')
    config_url = f"http://{host}" if host else None
    
    # Create gateway device
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, gateway_id)},
        name=f"Ecowitt Gateway {host}",
        manufacturer="Ecowitt",
        model=gateway_info.get("model", "Unknown"),
        sw_version=gateway_info.get("firmware_version", "Unknown"),
        configuration_url=config_url,
    )
    
    # Create individual sensor devices
    hardware_ids = coordinator.sensor_mapper.get_all_hardware_ids()
    for hardware_id in hardware_ids:
        # Skip invalid hardware IDs
        if not hardware_id or hardware_id.upper() in ("FFFFFFFE", "FFFFFFFF", "00000000"):
            _LOGGER.debug("Skipping invalid hardware_id: %s", hardware_id)
            continue
            
        sensor_info = coordinator.sensor_mapper.get_sensor_info(hardware_id)
        if sensor_info:
            sensor_type = sensor_info.get("sensor_type", "Unknown")
            device_model = sensor_info.get("device_model") or sensor_type
            
            # Get display name for sensor type
            sensor_type_name = _get_sensor_type_display_name(sensor_type)
            
            # Determine if outdoor sensor for suggested area
            is_outdoor = _is_outdoor_sensor(sensor_type)
            
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, hardware_id)},
                name=f"Ecowitt {sensor_type_name} {hardware_id}",
                manufacturer="Ecowitt",
                model=device_model,
                via_device=(DOMAIN, gateway_id),
                suggested_area="Outdoor" if is_outdoor else None,
            )
            _LOGGER.debug("Created device for hardware_id: %s", hardware_id)


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    
    async def async_refresh_mapping(call: ServiceCall) -> None:
        """Service to refresh sensor mapping."""
        _LOGGER.info("Refreshing sensor mapping via service call")
        
        # Get target device or all coordinators
        device_id = call.data.get("device_id")
        coordinators = []
        
        if device_id:
            # Find coordinator for specific device
            device_registry = dr.async_get(hass)
            device = device_registry.async_get(device_id)
            if device:
                for entry_id in device.config_entries:
                    if entry_id in hass.data.get(DOMAIN, {}):
                        coordinators.append(hass.data[DOMAIN][entry_id])
        else:
            # Refresh all coordinators
            coordinators = list(hass.data.get(DOMAIN, {}).values())
        
        # Refresh mapping for all coordinators
        tasks = []
        for coordinator in coordinators:
            tasks.append(coordinator.async_refresh_mapping())
        
        if tasks:
            await asyncio.gather(*tasks)
            _LOGGER.info("Refreshed sensor mapping for %d gateways", len(tasks))
    
    async def async_update_data(call: ServiceCall) -> None:
        """Service to force data update."""
        _LOGGER.info("Forcing data update via service call")
        
        # Get target device or all coordinators
        device_id = call.data.get("device_id")
        coordinators = []
        
        if device_id:
            # Find coordinator for specific device
            device_registry = dr.async_get(hass)
            device = device_registry.async_get(device_id)
            if device:
                for entry_id in device.config_entries:
                    if entry_id in hass.data.get(DOMAIN, {}):
                        coordinators.append(hass.data[DOMAIN][entry_id])
        else:
            # Update all coordinators
            coordinators = list(hass.data.get(DOMAIN, {}).values())
        
        # Force data update for all coordinators
        tasks = []
        for coordinator in coordinators:
            tasks.append(coordinator.async_request_refresh())
        
        if tasks:
            await asyncio.gather(*tasks)
            _LOGGER.info("Forced data update for %d gateways", len(tasks))
    
    # Register services if not already registered
    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH_MAPPING):
        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH_MAPPING,
            async_refresh_mapping,
            schema=None,
        )
    
    if not hass.services.has_service(DOMAIN, SERVICE_UPDATE_DATA):
        hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_DATA,
            async_update_data,
            schema=None,
        )


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.info(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )
    
    # Migration from version 1.0 to 1.1: Individual sensor devices
    if config_entry.version == 1 and config_entry.minor_version < 1:
        _LOGGER.info("Migrating to individual sensor devices (v1.1)")
        
        # Get device registry to handle device migration
        device_registry = dr.async_get(hass)
        entity_registry = hass.helpers.entity_registry.async_get(hass)
        
        # Find all entities belonging to this config entry
        entities = hass.helpers.entity_registry.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
        
        # Get coordinator to access sensor mapping
        if config_entry.entry_id in hass.data.get(DOMAIN, {}):
            coordinator = hass.data[DOMAIN][config_entry.entry_id]
            
            # Create individual sensor devices
            await _async_setup_device_registry(hass, config_entry, coordinator)
            
            # Update entities to point to new devices
            for entity in entities:
                if entity.unique_id and "_" in entity.unique_id:
                    # Extract hardware_id from unique_id pattern: ecowitt_local_{hardware_id}_{sensor_key}
                    unique_id_parts = entity.unique_id.split("_", 2)
                    if len(unique_id_parts) >= 3:
                        hardware_id = unique_id_parts[2].split("_")[0]
                        
                        # Check if this hardware_id exists in sensor mapping and is valid
                        if (hardware_id and 
                            hardware_id.upper() not in ("FFFFFFFE", "FFFFFFFF", "00000000") and
                            coordinator.sensor_mapper.get_sensor_info(hardware_id)):
                            # Find the new device for this hardware_id
                            new_device = device_registry.async_get_device(
                                identifiers={(DOMAIN, hardware_id)}
                            )
                            if new_device:
                                # Update entity to point to new device
                                entity_registry.async_update_entity(
                                    entity.entity_id,
                                    device_id=new_device.id
                                )
                                _LOGGER.debug(
                                    "Migrated entity %s to device %s", 
                                    entity.entity_id, 
                                    new_device.name
                                )
        
        # Update config entry version using proper API
        hass.config_entries.async_update_entry(
            config_entry,
            minor_version=1
        )
        
        _LOGGER.info("Migration to v1.1 completed successfully")
    
    return True


def _get_sensor_type_display_name(sensor_type: str) -> str:
    """Get display name for sensor type."""
    sensor_type_lower = sensor_type.lower()
    
    type_names = {
        "wh51": "Soil Moisture Sensor",
        "wh31": "Temperature/Humidity Sensor", 
        "wh41": "PM2.5 Air Quality Sensor",
        "wh55": "Leak Sensor",
        "wh57": "Lightning Sensor",
        "wh40": "Rain Sensor",
        "wh68": "Weather Station",
        "soil": "Soil Moisture Sensor",
        "temp_hum": "Temperature/Humidity Sensor",
        "pm25": "PM2.5 Air Quality Sensor",
        "leak": "Leak Sensor",
        "lightning": "Lightning Sensor",
        "rain": "Rain Sensor",
        "weather_station": "Weather Station",
    }
    
    return type_names.get(sensor_type_lower, "Sensor")


def _is_outdoor_sensor(sensor_type: str) -> bool:
    """Check if sensor is typically outdoor."""
    sensor_type_lower = sensor_type.lower()
    
    outdoor_types = {
        "wh51", "wh41", "wh55", "wh57", "wh40", "wh68",
        "soil", "pm25", "leak", "lightning", "rain", "weather_station"
    }
    
    return sensor_type_lower in outdoor_types


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    _LOGGER.info("Removing Ecowitt Local integration for %s", entry.data[CONF_HOST])
    
    # Clean up any persistent data if needed
    # Currently no cleanup required