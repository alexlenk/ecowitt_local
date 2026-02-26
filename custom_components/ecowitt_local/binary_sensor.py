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
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_BATTERY_LEVEL,
    ATTR_CHANNEL,
    ATTR_DEVICE_MODEL,
    ATTR_HARDWARE_ID,
    ATTR_LAST_SEEN,
    ATTR_SENSOR_TYPE,
    ATTR_SIGNAL_STRENGTH,
    DOMAIN,
    MANUFACTURER,
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

    # Create binary sensor entities for sensor online/offline status
    entities = []

    # Get all hardware IDs with their associated sensors
    hardware_sensors: Dict[str, List[Dict[str, Any]]] = {}
    sensor_data = coordinator.get_all_sensors()
    _LOGGER.debug("Binary sensor setup: Found %d total sensors", len(sensor_data))

    for entity_id, sensor_info in sensor_data.items():
        hardware_id = sensor_info.get("hardware_id")
        category = sensor_info.get("category")
        _LOGGER.debug(
            "Binary sensor check: %s -> hardware_id=%s, category=%s",
            entity_id,
            hardware_id,
            category,
        )
        if hardware_id and category == "sensor":
            if hardware_id not in hardware_sensors:
                hardware_sensors[hardware_id] = []
            hardware_sensors[hardware_id].append(sensor_info)

    _LOGGER.debug("Hardware sensors found: %s", list(hardware_sensors.keys()))

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
        self.entity_id = (
            f"binary_sensor.ecowitt_{sensor_type}_{hardware_id.lower()}_online"
        )
        self._attr_name = (
            f"Ecowitt {sensor_type.replace('_', ' ').title()} {hardware_id} Online"
        )

        # Set device class and entity category
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

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
                state = sensor_info.get("state")

                # Check if sensor has a meaningful value (not None and not invalid values)
                if state is not None:
                    # Convert to string and check if it's a valid value
                    state_str = str(state).lower()
                    invalid_states = {
                        "unknown",
                        "n/a",
                        "none",
                        "",
                        "null",
                        "unavailable",
                    }

                    # If state is not in invalid states, sensor is online
                    if state_str not in invalid_states:
                        return True

                # Check timestamp if available (fallback for sensors without valid state)
                last_update_str = sensor_info.get("attributes", {}).get("last_update")
                if last_update_str:
                    try:
                        last_update = datetime.fromisoformat(
                            last_update_str.replace("Z", "+00:00")
                        )
                        threshold = datetime.now() - timedelta(
                            minutes=OFFLINE_THRESHOLD_MINUTES
                        )
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

        # Create individual device for sensor hardware
        if self._hardware_id and self._hardware_id.upper() not in (
            "FFFFFFFE",
            "FFFFFFFF",
            "00000000",
        ):
            sensor_info = self.coordinator.sensor_mapper.get_sensor_info(
                self._hardware_id
            )
            if sensor_info:
                device_model = sensor_info.get("device_model") or sensor_info.get(
                    "sensor_type", "Unknown"
                )
                sensor_type_name = self._get_sensor_type_display_name(sensor_info)

                return DeviceInfo(
                    identifiers={(DOMAIN, self._hardware_id)},
                    name=f"Ecowitt {sensor_type_name} {self._hardware_id}",
                    manufacturer=MANUFACTURER,
                    model=device_model,
                    via_device=(DOMAIN, gateway_id),
                    suggested_area=(
                        "Outdoor" if self._is_outdoor_sensor(sensor_info) else None
                    ),
                )

        # Fall back to gateway device
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
                        attributes[ATTR_BATTERY_LEVEL] = float(
                            sensor_attributes["battery"]
                        )
                    except (ValueError, TypeError):
                        pass
                if sensor_attributes.get("signal"):
                    try:
                        attributes[ATTR_SIGNAL_STRENGTH] = int(
                            sensor_attributes["signal"]
                        )
                    except (ValueError, TypeError):
                        pass
                if sensor_attributes.get("last_update"):
                    attributes[ATTR_LAST_SEEN] = sensor_attributes["last_update"]

                # Only need info from one sensor with this hardware ID
                break

        return attributes

    def _get_sensor_type_display_name(self, sensor_info: Dict[str, Any]) -> str:
        """Get display name for sensor type."""
        sensor_type = sensor_info.get("sensor_type", "").lower()

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

        return type_names.get(sensor_type, "Sensor")

    def _is_outdoor_sensor(self, sensor_info: Dict[str, Any]) -> bool:
        """Check if sensor is typically outdoor."""
        sensor_type = sensor_info.get("sensor_type", "").lower()

        outdoor_types = {
            "wh51",
            "wh41",
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

        return sensor_type in outdoor_types

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

        # Set device class and entity category
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

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

        # Add last update time if available
        if (
            hasattr(self.coordinator, "last_update_success_time")
            and self.coordinator.last_update_success_time
        ):
            attributes["last_successful_update"] = (
                self.coordinator.last_update_success_time.isoformat()
            )
        elif (
            hasattr(self.coordinator, "last_update_time")
            and self.coordinator.last_update_time
        ):
            attributes["last_update_time"] = (
                self.coordinator.last_update_time.isoformat()
            )

        return attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
