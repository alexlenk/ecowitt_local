"""Button platform for Ecowitt Local integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import EcowittLocalDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ecowitt Local button entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([EcowittResyncMappingButton(coordinator)])


class EcowittResyncMappingButton(
    CoordinatorEntity[EcowittLocalDataUpdateCoordinator], ButtonEntity
):
    """Button that forces an immediate sensor mapping resync."""

    def __init__(self, coordinator: EcowittLocalDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)

        gateway_info = coordinator.gateway_info
        gateway_id = gateway_info.get("gateway_id", "unknown")
        host = gateway_info.get("host", "")

        self._attr_unique_id = f"{DOMAIN}_{gateway_id}_resync_mapping"
        self.entity_id = f"button.ecowitt_gateway_{gateway_id.lower()}_resync_mapping"
        self._attr_name = f"Ecowitt Gateway {host} Resync Sensor Mappings"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Force an immediate sensor mapping refresh."""
        _LOGGER.info("Resyncing sensor mappings via button press")
        await self.coordinator.async_refresh_mapping()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        gateway_info = self.coordinator.gateway_info
        gateway_id = gateway_info.get("gateway_id", "unknown")

        return DeviceInfo(
            identifiers={(DOMAIN, gateway_id)},
            name=f"Ecowitt Gateway {gateway_info.get('host', '')}",
            manufacturer=MANUFACTURER,
            model=gateway_info.get("model", "Unknown"),
            sw_version=gateway_info.get("firmware_version", "Unknown"),
            configuration_url=f"http://{gateway_info.get('host', '')}",
        )
