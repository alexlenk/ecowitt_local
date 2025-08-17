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
    """Set up device registry entry for the gateway."""
    device_registry = dr.async_get(hass)
    gateway_info = coordinator.gateway_info
    
    # Create configuration URL only if host is available
    host = gateway_info.get('host', '')
    config_url = f"http://{host}" if host else None
    
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, gateway_info.get("gateway_id", "unknown"))},
        name=f"Ecowitt Gateway {host}",
        manufacturer="Ecowitt",
        model=gateway_info.get("model", "Unknown"),
        sw_version=gateway_info.get("firmware_version", "Unknown"),
        configuration_url=config_url,
    )


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
    
    # Currently version 1, no migrations needed yet
    # Future migrations would go here
    
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    _LOGGER.info("Removing Ecowitt Local integration for %s", entry.data[CONF_HOST])
    
    # Clean up any persistent data if needed
    # Currently no cleanup required