"""The Ecowitt Local integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .api import EcowittLocalAPI
from .const import DOMAIN, GATEWAY_SENSORS, SERVICE_REFRESH_MAPPING, SERVICE_UPDATE_DATA
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

    # Fetch initial data here — ConfigEntryNotReady must be raised before
    # async_forward_entry_setups, not inside a forwarded platform.
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Setup device registry entries FIRST so devices exist when entities are created
    await _async_setup_device_registry(hass, entry, coordinator)

    # Clean up orphan decimal-id entities left over from before v1.6.21 (issue #178).
    _async_cleanup_decimal_id_orphans(hass, entry, coordinator)

    # Setup platforms (entities will now find their proper devices)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Remove phantom sensor devices that ended up with no entities (issue #155).
    # _async_setup_device_registry creates a device for every hardware_id reported
    # by get_sensors_info, but a stale slot left over from a previously paired
    # sensor (signal=0) can lose every shared common_list key to the active sensor
    # via signal-priority resolution and end up with no live data of its own —
    # leaving an empty device entry behind.
    _async_remove_empty_sensor_devices(hass, entry, coordinator)

    # Register services
    await _async_register_services(hass)

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
    host = gateway_info.get("host", "")
    config_url = f"http://{host}" if host else None

    # Create gateway device
    gateway_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, gateway_id)},
        name=f"Ecowitt Gateway {host}",
        manufacturer="Ecowitt",
        model=gateway_info.get("model", "Unknown"),
        sw_version=gateway_info.get("firmware_version", "Unknown"),
        configuration_url=config_url,
    )

    # Clean up stale "unknown" gateway device left over from before the gateway ID
    # fallback was introduced (v1.6.8). If the real gateway_id is now known, move any
    # entities that are still pointing at the old ghost device to the real one.
    if gateway_id != "unknown":
        old_device = device_registry.async_get_device(identifiers={(DOMAIN, "unknown")})
        if old_device and entry.entry_id in old_device.config_entries:
            entity_registry = er.async_get(hass)
            for entity in er.async_entries_for_device(
                entity_registry, old_device.id, include_disabled_entities=True
            ):
                entity_registry.async_update_entity(
                    entity.entity_id, device_id=gateway_device.id
                )
                _LOGGER.info(
                    "Migrated entity %s from ghost 'unknown' gateway device to %s",
                    entity.entity_id,
                    gateway_id,
                )
            device_registry.async_remove_device(old_device.id)
            _LOGGER.info("Removed stale 'unknown' gateway device")

    # Create individual sensor devices
    hardware_ids = coordinator.sensor_mapper.get_all_hardware_ids()
    for hardware_id in hardware_ids:
        # Skip invalid hardware IDs
        if not hardware_id or hardware_id.upper() in (
            "FFFFFFFE",
            "FFFFFFFF",
            "00000000",
        ):
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


@callback
def _async_remove_empty_sensor_devices(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: EcowittLocalDataUpdateCoordinator,
) -> None:
    """Remove phantom sensor devices left over from displaced stale slots.

    A previously paired sensor that is no longer transmitting (signal=0) can
    still appear in get_sensors_info — newer firmware moves it to a higher
    page that v1.6.17 began fetching. The signal-priority resolver in
    sensor_mapper.update_mapping correctly routes shared common_list keys to
    the active sensor with the stronger signal, but the stale slot's device
    was already registered by _async_setup_device_registry and now has no
    entities at all (issue #155 — phantom WH69 alongside the active WH90).

    Only remove devices whose hardware_id has signal=0 in the current sensor
    info AND have no entities for this entry. That keeps freshly paired
    sensors (signal>0 but no live data yet) untouched — their device will fill
    in once data arrives.
    """
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    gateway_id = coordinator.gateway_info.get("gateway_id", "unknown")

    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        sensor_hardware_id: str | None = None
        for ident_domain, ident in device.identifiers:
            if ident_domain != DOMAIN or ident == gateway_id:
                continue
            sensor_hardware_id = ident
            break
        if sensor_hardware_id is None:
            continue

        sensor_info = coordinator.sensor_mapper.get_sensor_info(sensor_hardware_id)
        if sensor_info is None:
            continue
        if str(sensor_info.get("signal", "")).strip() != "0":
            continue

        entities = er.async_entries_for_device(
            entity_registry, device.id, include_disabled_entities=True
        )
        if entities:
            continue

        _LOGGER.info(
            "Removing phantom sensor device %s (%s) — signal=0 with no "
            "entities, displaced by signal-priority resolution",
            device.name or device.id,
            device.model or "unknown model",
        )
        device_registry.async_remove_device(device.id)


@callback
def _async_cleanup_decimal_id_orphans(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: EcowittLocalDataUpdateCoordinator,
) -> None:
    """Clean up orphan decimal-id entities created before v1.6.21 (issue #178).

    v1.6.20 routed common_list decimal IDs "3" (Feels Like Temp) and "5" (VPD)
    to the outdoor weather station, and removed the spurious "4" sensor type
    that wasn't in the V1.0.6 spec. Pre-existing entities created on the gateway
    device kept their old gateway-based unique_id `ecowitt_local_<entry_id>_<key>`
    and went "unavailable" — the orphan VPD and "4" entries reported in #178.

    For "3" and "5": migrate the orphan to the outdoor weather station device
    by updating unique_id and device_id (preserves history). If a hardware-based
    equivalent already exists, remove the orphan instead.

    For "4": always remove. The key is not in the V1.0.6 spec.
    """
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    # Resolve the outdoor weather station's hardware ID by looking up any of
    # its battery keys; whichever is mapped wins (WH90 takes priority).
    outdoor_hardware_id: str | None = None
    for batt_key in ("wh90batt", "ws90batt", "wh80batt", "wh69batt"):
        outdoor_hardware_id = coordinator.sensor_mapper.get_hardware_id(batt_key)
        if outdoor_hardware_id:
            break

    outdoor_device = (
        device_registry.async_get_device(identifiers={(DOMAIN, outdoor_hardware_id)})
        if outdoor_hardware_id
        else None
    )

    prefix = f"{DOMAIN}_{entry.entry_id}_"
    for entity in list(
        er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    ):
        if not entity.unique_id.startswith(prefix):
            continue
        sensor_key = entity.unique_id[len(prefix) :]

        if sensor_key == "4":
            _LOGGER.info(
                "Removing orphan '4' entity %s — key is not in V1.0.6 spec",
                entity.entity_id,
            )
            entity_registry.async_remove(entity.entity_id)
            continue

        if sensor_key not in ("3", "5"):
            continue

        if outdoor_device is None or outdoor_hardware_id is None:
            continue

        new_unique_id = f"{DOMAIN}_{outdoor_hardware_id}_{sensor_key}"
        existing = entity_registry.async_get_entity_id("sensor", DOMAIN, new_unique_id)
        sensor_label = "Feels Like Temp" if sensor_key == "3" else "VPD"
        if existing and existing != entity.entity_id:
            _LOGGER.info(
                "Removing orphan %s entity %s — already migrated to %s",
                sensor_label,
                entity.entity_id,
                existing,
            )
            entity_registry.async_remove(entity.entity_id)
        else:
            _LOGGER.info(
                "Migrating orphan %s entity %s from gateway to outdoor station %s",
                sensor_label,
                entity.entity_id,
                outdoor_hardware_id,
            )
            entity_registry.async_update_entity(
                entity.entity_id,
                new_unique_id=new_unique_id,
                device_id=outdoor_device.id,
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
            # Handle case where device_id might be passed as a list
            if isinstance(device_id, list):
                device_id = device_id[0] if device_id else None
            device = device_registry.async_get(device_id) if device_id else None
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
            # Handle case where device_id might be passed as a list
            if isinstance(device_id, list):
                device_id = device_id[0] if device_id else None
            device = device_registry.async_get(device_id) if device_id else None
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
    # Migration from version 1.1 to 1.2: Fix entity device assignment
    # Migration from version 1.2 to 1.3: Fix gateway sensor device assignment
    if config_entry.version == 1 and config_entry.minor_version < 3:
        if config_entry.minor_version < 2:
            _LOGGER.info("Migrating to individual sensor devices (v1.2)")
        if config_entry.minor_version < 3:
            _LOGGER.info("Migrating gateway sensor device assignment (v1.3)")

        # Get device registry to handle device migration
        device_registry = dr.async_get(hass)
        entity_registry = er.async_get(hass)

        # Find all entities belonging to this config entry
        entities = er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )

        # Get coordinator to access sensor mapping
        if config_entry.entry_id in hass.data.get(DOMAIN, {}):
            coordinator = hass.data[DOMAIN][config_entry.entry_id]

            # Create individual sensor devices
            await _async_setup_device_registry(hass, config_entry, coordinator)

            # Update entities to point to new devices
            # This migration moves ALL entities with valid hardware IDs to their individual devices
            reassigned_count = 0
            for entity in entities:
                if entity.unique_id and "_" in entity.unique_id:
                    # Extract hardware_id from unique_id pattern: ecowitt_local_{hardware_id}_{sensor_key}
                    unique_id_parts = entity.unique_id.split("_")

                    # Try different patterns to extract hardware_id
                    hardware_id = None
                    if len(unique_id_parts) >= 3:
                        # Pattern: ecowitt_local_{hardware_id}_{sensor_key}
                        potential_hardware_id = unique_id_parts[2]
                        if coordinator.sensor_mapper.get_sensor_info(
                            potential_hardware_id
                        ):
                            hardware_id = potential_hardware_id

                    if not hardware_id and len(unique_id_parts) >= 4:
                        # Pattern: ecowitt_local_{entry_id}_{hardware_id}_{sensor_key}
                        potential_hardware_id = unique_id_parts[3]
                        if coordinator.sensor_mapper.get_sensor_info(
                            potential_hardware_id
                        ):
                            hardware_id = potential_hardware_id

                    # Also check if the entity has hardware_id in coordinator data
                    if not hardware_id:
                        sensor_data = coordinator.get_all_sensors()
                        for entity_id, sensor_info in sensor_data.items():
                            if entity_id == entity.entity_id:
                                potential_hardware_id = sensor_info.get("hardware_id")
                                if (
                                    potential_hardware_id
                                    and coordinator.sensor_mapper.get_sensor_info(
                                        potential_hardware_id
                                    )
                                ):
                                    hardware_id = potential_hardware_id
                                break

                    # Check if this hardware_id exists in sensor mapping and is valid
                    if (
                        hardware_id
                        and hardware_id.upper()
                        not in ("FFFFFFFE", "FFFFFFFF", "00000000")
                        and coordinator.sensor_mapper.get_sensor_info(hardware_id)
                    ):
                        # Find the new device for this hardware_id
                        new_device = device_registry.async_get_device(
                            identifiers={(DOMAIN, hardware_id)}
                        )
                        if new_device:
                            # Update entity to point to new device
                            entity_registry.async_update_entity(
                                entity.entity_id, device_id=new_device.id
                            )
                            reassigned_count += 1
                            _LOGGER.info(
                                "Migrated entity %s to device %s (%s)",
                                entity.entity_id,
                                new_device.name,
                                hardware_id,
                            )

            if config_entry.minor_version < 2:
                _LOGGER.info(
                    "Migration completed: reassigned %d entities to individual devices",
                    reassigned_count,
                )

            # v1.3 Migration: Move gateway sensors back to gateway device
            if config_entry.minor_version < 3:
                gateway_id = coordinator.gateway_info.get("gateway_id", "unknown")
                gateway_device = device_registry.async_get_device(
                    identifiers={(DOMAIN, gateway_id)}
                )

                if gateway_device:
                    gateway_reassigned_count = 0
                    for entity in entities:
                        if entity.unique_id:
                            # Check if this is a gateway sensor entity
                            for gateway_sensor in GATEWAY_SENSORS:
                                if gateway_sensor in entity.unique_id:
                                    # Move entity to gateway device
                                    entity_registry.async_update_entity(
                                        entity.entity_id, device_id=gateway_device.id
                                    )
                                    gateway_reassigned_count += 1
                                    _LOGGER.info(
                                        "Moved gateway sensor %s back to gateway device",
                                        entity.entity_id,
                                    )
                                    break

                    _LOGGER.info(
                        "Migration v1.3 completed: moved %d gateway sensors back to gateway device",
                        gateway_reassigned_count,
                    )

        # Update config entry version
        hass.config_entries.async_update_entry(config_entry, minor_version=3)

        _LOGGER.info("Migration to v1.3 completed successfully")

    return True


def _get_sensor_type_display_name(sensor_type: str) -> str:
    """Get display name for sensor type."""
    sensor_type_lower = sensor_type.lower()

    type_names = {
        "wh51": "Soil Moisture Sensor",
        "wh31": "Temperature/Humidity Sensor",
        "wh41": "PM2.5 Air Quality Sensor",
        "wh54": "Liquid Depth Sensor",
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
        "wh51",
        "wh41",
        "wh54",
        "wh55",
        "wh57",
        "wh40",
        "wh68",
        "soil",
        "pm25",
        "leak",
        "lightning",
        "rain",
        "weather_station",
    }

    return sensor_type_lower in outdoor_types


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    _LOGGER.info("Removing Ecowitt Local integration for %s", entry.data[CONF_HOST])

    # Clean up any persistent data if needed
    # Currently no cleanup required
