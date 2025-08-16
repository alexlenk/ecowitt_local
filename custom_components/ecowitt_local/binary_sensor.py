"""Binary sensor platform for Ecowitt Local integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    ATTR_HARDWARE_ID,
    ATTR_CHANNEL,
    ATTR_BATTERY_LEVEL,
    ATTR_SIGNAL_STRENGTH,
    ATTR_LAST_SEEN,
    ATTR_SENSOR_TYPE,
    ATTR_DEVICE_MODEL,
)
from .coordinator import EcowittLocalDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Offline threshold in minutes
OFFLINE_THRESHOLD_MINUTES = 10


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ecowitt Local binary sensor entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Wait for initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Create binary sensor entities for sensor online/offline status
    entities = []
    
    # Get all hardware IDs with their associated sensors
    hardware_sensors: Dict[str, List[Dict[str, Any]]] = {}
    sensor_data = coordinator.get_all_sensors()
    
    for entity_id, sensor_info in sensor_data.items():
        hardware_id = sensor_info.get("hardware_id")
        if hardware_id and sensor_info.get("category") == "sensor":
            if hardware_id not in hardware_sensors:
                hardware_sensors[hardware_id] = []
            hardware_sensors[hardware_id].append(sensor_info)
    
    # Create online/offline binary sensors for each hardware sensor
    for hardware_id, sensors in hardware_sensors.items():
        # Use the first sensor to get basic info
        primary_sensor = sensors[0]
        entities.append(
            EcowittSensorOnlineBinarySensor(coordinator, hardware_id, primary_sensor)
        )
    
    # Add gateway online status
    entities.append(EcowittGatewayOnlineBinarySensor(coordinator))
    
    _LOGGER.info("Setting up %d Ecowitt Local binary sensor entities", len(entities))
    async_add_entities(entities, True)


class EcowittSensorOnlineBinarySensor(
    CoordinatorEntity[EcowittLocalDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor for individual sensor online/offline status."""

    def __init__(
        self,
        coordinator: EcowittLocalDataUpdateCoordinator,
        hardware_id: str,
        sensor_info: Dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        
        self._hardware_id = hardware_id
        self._sensor_key = sensor_info["sensor_key"]
        self._device_model = sensor_info.get("attributes", {}).get("device_model", "")
        
        # Set unique ID
        self._attr_unique_id = f"{DOMAIN}_{hardware_id}_online"
        
        # Set entity ID and name
        sensor_type = self._extract_sensor_type(sensor_info)
        self.entity_id = f"binary_sensor.ecowitt_{sensor_type}_{hardware_id.lower()}_online"
        self._attr_name = f"Ecowitt {sensor_type.replace('_', ' ').title()} {hardware_id} Online"
        
        # Set device class
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def _extract_sensor_type(self, sensor_info: Dict[str, Any]) -> str:
        """Extract sensor type from sensor info."""
        sensor_key = sensor_info.get("sensor_key", "")
        
        if "soil" in sensor_key:
            return "soil_moisture"
        elif "temp" in sensor_key:
            return "temperature"
        elif "pm25" in sensor_key:
            return "pm25"
        elif "leak" in sensor_key:
            return "leak"
        elif "lightning" in sensor_key:
            return "lightning"
        elif "rain" in sensor_key:
            return "rain"
        elif "wind" in sensor_key:
            return "wind"
        else:
            return "sensor"

    @property
    def is_on(self) -> bool:
        """Return true if the sensor is online."""
        # Check if any sensor with this hardware ID has recent data
        sensor_data = self.coordinator.get_all_sensors()
        
        for entity_id, sensor_info in sensor_data.items():
            if sensor_info.get("hardware_id") == self._hardware_id:
                # Check if sensor has a value (not None)
                if sensor_info.get("state") is not None:
                    return True
                    
                # Check timestamp if available
                last_update_str = sensor_info.get("attributes", {}).get("last_update")
                if last_update_str:
                    try:
                        last_update = datetime.fromisoformat(last_update_str.replace("Z", "+00:00"))
                        threshold = datetime.now() - timedelta(minutes=OFFLINE_THRESHOLD_MINUTES)
                        if last_update > threshold:
                            return True
                    except (ValueError, TypeError):
                        pass
        
        return False

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

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        # Get the first sensor with this hardware ID for details
        sensor_data = self.coordinator.get_all_sensors()
        
        attributes = {
            ATTR_HARDWARE_ID: self._hardware_id,
            "offline_threshold_minutes": OFFLINE_THRESHOLD_MINUTES,
        }
        
        for entity_id, sensor_info in sensor_data.items():
            if sensor_info.get("hardware_id") == self._hardware_id:
                sensor_attributes = sensor_info.get("attributes", {})
                
                if sensor_attributes.get("channel"):
                    attributes[ATTR_CHANNEL] = sensor_attributes["channel"]
                if sensor_attributes.get("device_model"):
                    attributes[ATTR_DEVICE_MODEL] = sensor_attributes["device_model"]
                if sensor_attributes.get("battery"):
                    try:
                        attributes[ATTR_BATTERY_LEVEL] = float(sensor_attributes["battery"])
                    except (ValueError, TypeError):
                        pass
                if sensor_attributes.get("signal"):
                    try:
                        attributes[ATTR_SIGNAL_STRENGTH] = int(sensor_attributes["signal"])
                    except (ValueError, TypeError):
                        pass
                if sensor_attributes.get("last_update"):
                    attributes[ATTR_LAST_SEEN] = sensor_attributes["last_update"]
                
                # Only need info from one sensor with this hardware ID
                break
        
        return attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class EcowittGatewayOnlineBinarySensor(
    CoordinatorEntity[EcowittLocalDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor for gateway online/offline status."""

    def __init__(self, coordinator: EcowittLocalDataUpdateCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        
        gateway_info = coordinator.gateway_info
        gateway_id = gateway_info.get("gateway_id", "unknown")
        host = gateway_info.get("host", "")
        
        # Set unique ID
        self._attr_unique_id = f"{DOMAIN}_{gateway_id}_gateway_online"
        
        # Set entity ID and name
        self.entity_id = f"binary_sensor.ecowitt_gateway_{gateway_id.lower()}_online"
        self._attr_name = f"Ecowitt Gateway {host} Online"
        
        # Set device class
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool:
        """Return true if the gateway is online."""
        # Gateway is online if we have successful coordinator updates
        return bool(self.coordinator.last_update_success)

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

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        gateway_info = self.coordinator.gateway_info
        
        attributes = {
            "gateway_id": gateway_info.get("gateway_id"),
            "host": gateway_info.get("host"),
            "model": gateway_info.get("model"),
            "firmware_version": gateway_info.get("firmware_version"),
        }
        
        if self.coordinator.last_update_success_time:
            attributes["last_successful_update"] = self.coordinator.last_update_success_time.isoformat()
        
        return attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()