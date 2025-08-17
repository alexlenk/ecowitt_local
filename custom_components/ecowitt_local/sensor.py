"""Sensor platform for Ecowitt Local integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfVolumetricFlux,
    UnitOfIrradiance,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
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
    ATTR_FIRMWARE_VERSION,
)
from .coordinator import EcowittLocalDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Unit conversion mappings
UNIT_CONVERSIONS = {
    "°F": UnitOfTemperature.FAHRENHEIT,
    "°C": UnitOfTemperature.CELSIUS,
    "inHg": UnitOfPressure.INHG,
    "hPa": UnitOfPressure.HPA,
    "mph": UnitOfSpeed.MILES_PER_HOUR,
    "km/h": UnitOfSpeed.KILOMETERS_PER_HOUR,
    "in": UnitOfLength.INCHES,
    "mm": UnitOfLength.MILLIMETERS,
    "in/hr": UnitOfVolumetricFlux.INCHES_PER_HOUR,
    "mm/hr": UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
    "W/m²": UnitOfIrradiance.WATTS_PER_SQUARE_METER,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ecowitt Local sensor entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Wait for initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Create sensor entities
    entities = []
    
    sensor_data = coordinator.get_all_sensors()
    _LOGGER.debug("Found %d total sensors in coordinator data", len(sensor_data))
    for entity_id, sensor_info in sensor_data.items():
        category = sensor_info.get("category")
        _LOGGER.debug("Sensor %s: category=%s, sensor_key=%s", entity_id, category, sensor_info.get("sensor_key"))
        if category in ("sensor", "battery", "system"):
            entities.append(
                EcowittLocalSensor(coordinator, entity_id, sensor_info)
            )
    
    _LOGGER.info("Setting up %d Ecowitt Local sensor entities", len(entities))
    async_add_entities(entities, True)


class EcowittLocalSensor(CoordinatorEntity[EcowittLocalDataUpdateCoordinator], SensorEntity):
    """Representation of an Ecowitt Local sensor."""

    def __init__(
        self,
        coordinator: EcowittLocalDataUpdateCoordinator,
        entity_id: str,
        sensor_info: Dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self.entity_id = entity_id
        self._sensor_key = sensor_info["sensor_key"]
        self._hardware_id = sensor_info.get("hardware_id")
        self._category = sensor_info.get("category", "sensor")
        
        # Set unique ID based on hardware ID if available
        if self._hardware_id:
            self._attr_unique_id = f"{DOMAIN}_{self._hardware_id}_{self._sensor_key}"
        else:
            self._attr_unique_id = f"{DOMAIN}_{self.coordinator.config_entry.entry_id}_{self._sensor_key}"
        
        # Set initial attributes
        self._update_attributes(sensor_info)

    def _update_attributes(self, sensor_info: Dict[str, Any]) -> None:
        """Update sensor attributes from sensor info."""
        self._attr_name = sensor_info.get("name", self._sensor_key)
        self._attr_native_value = sensor_info.get("state")
        
        # Set unit of measurement
        unit = sensor_info.get("unit_of_measurement")
        if unit:
            self._attr_native_unit_of_measurement = UNIT_CONVERSIONS.get(unit, unit)
        else:
            self._attr_native_unit_of_measurement = None
        
        # Set device class
        device_class_str = sensor_info.get("device_class")
        if device_class_str:
            try:
                self._attr_device_class = SensorDeviceClass(device_class_str)
            except ValueError:
                _LOGGER.debug("Unknown device class: %s", device_class_str)
                self._attr_device_class = None
        
        # Set state class for numeric sensors
        if isinstance(self._attr_native_value, (int, float)) and self._attr_native_value is not None:
            if self._category == "battery":
                self._attr_state_class = SensorStateClass.MEASUREMENT
            elif device_class_str in (
                "temperature",
                "humidity", 
                "pressure",
                "wind_speed",
                "precipitation",
                "precipitation_intensity",
                "irradiance",
                "pm25",
                "moisture",
            ):
                self._attr_state_class = SensorStateClass.MEASUREMENT
            elif "total" in self._sensor_key or "yearly" in self._sensor_key:
                self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        
        # Set battery sensor specific attributes
        if self._category == "battery":
            self._attr_device_class = SensorDeviceClass.BATTERY
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        sensor_info = self.coordinator.get_sensor_data(self.entity_id)
        if sensor_info:
            self._update_attributes(sensor_info)
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        gateway_info = self.coordinator.gateway_info
        gateway_id = gateway_info.get("gateway_id", "unknown")
        
        # If this sensor has a hardware ID, create individual device
        if self._hardware_id and self._hardware_id.upper() not in ("FFFFFFFE", "FFFFFFFF", "00000000"):
            sensor_info = self.coordinator.sensor_mapper.get_sensor_info(self._hardware_id)
            if sensor_info:
                device_model = sensor_info.get("device_model") or sensor_info.get("sensor_type", "Unknown")
                sensor_type_name = self._get_sensor_type_display_name(sensor_info)
                
                _LOGGER.debug("Sensor %s using individual device: %s", self._sensor_key, self._hardware_id)
                return DeviceInfo(
                    identifiers={(DOMAIN, self._hardware_id)},
                    name=f"Ecowitt {sensor_type_name} {self._hardware_id}",
                    manufacturer=MANUFACTURER,
                    model=device_model,
                    via_device=(DOMAIN, gateway_id),
                    suggested_area="Outdoor" if self._is_outdoor_sensor(sensor_info) else None,
                )
            else:
                _LOGGER.debug("Sensor %s has hardware_id %s but no sensor info found", self._sensor_key, self._hardware_id)
        
        # Fall back to gateway device for built-in sensors
        _LOGGER.debug("Sensor %s using gateway device (hardware_id: %s)", self._sensor_key, self._hardware_id)
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
        sensor_info = self.coordinator.get_sensor_data(self.entity_id)
        if not sensor_info:
            return {}
        
        attributes = sensor_info.get("attributes", {})
        
        # Add standard attributes
        extra_attrs = {
            "sensor_key": self._sensor_key,
            "category": self._category,
        }
        
        # Add hardware-specific attributes if available
        if self._hardware_id:
            extra_attrs[ATTR_HARDWARE_ID] = self._hardware_id
            
            # Add hardware-specific details
            if attributes.get("channel"):
                extra_attrs[ATTR_CHANNEL] = attributes["channel"]
            if attributes.get("device_model"):
                extra_attrs[ATTR_DEVICE_MODEL] = attributes["device_model"]
            if attributes.get("battery"):
                try:
                    battery_level = float(attributes["battery"])
                    extra_attrs[ATTR_BATTERY_LEVEL] = battery_level
                except (ValueError, TypeError):
                    pass
            if attributes.get("signal"):
                try:
                    signal_strength = int(attributes["signal"])
                    extra_attrs[ATTR_SIGNAL_STRENGTH] = signal_strength
                except (ValueError, TypeError):
                    pass
        
        # Add timing information
        if attributes.get("last_update"):
            extra_attrs[ATTR_LAST_SEEN] = attributes["last_update"]
        
        # Add sensor type
        extra_attrs[ATTR_SENSOR_TYPE] = self._category
        
        # Add raw value for debugging
        if "raw_value" in sensor_info:
            extra_attrs["raw_value"] = sensor_info["raw_value"]
        
        return extra_attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
            
        # Check if sensor has recent data
        sensor_info = self.coordinator.get_sensor_data(self.entity_id)
        if not sensor_info:
            return False
            
        # If we have a hardware ID and the sensor value is None, 
        # it might be offline
        if self._hardware_id and sensor_info.get("state") is None:
            # Check if we should include inactive sensors
            include_inactive = self.coordinator.config_entry.data.get("include_inactive", False)
            return bool(include_inactive)
            
        return True

    @property
    def icon(self) -> Optional[str]:
        """Return the icon for the sensor."""
        # Custom icons based on sensor type
        if self._category == "battery":
            # Use battery icon based on level
            battery_level = self.extra_state_attributes.get(ATTR_BATTERY_LEVEL)
            if battery_level is not None:
                if battery_level <= 10:
                    return "mdi:battery-outline"
                elif battery_level <= 20:
                    return "mdi:battery-20"
                elif battery_level <= 30:
                    return "mdi:battery-30"
                elif battery_level <= 40:
                    return "mdi:battery-40"
                elif battery_level <= 50:
                    return "mdi:battery-50"
                elif battery_level <= 60:
                    return "mdi:battery-60"
                elif battery_level <= 70:
                    return "mdi:battery-70"
                elif battery_level <= 80:
                    return "mdi:battery-80"
                elif battery_level <= 90:
                    return "mdi:battery-90"
                else:
                    return "mdi:battery"
            return "mdi:battery"
        
        # Use device class icons or custom ones
        sensor_icons = {
            "soil": "mdi:sprout",
            "leak": "mdi:water-alert",
            "lightning": "mdi:flash",
            "uv": "mdi:weather-sunny-alert",
            "heap": "mdi:memory",
            "runtime": "mdi:clock-outline",
        }
        
        for key, icon in sensor_icons.items():
            if key in self._sensor_key.lower():
                return icon
                
        return None

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
            "wh51", "wh41", "wh55", "wh57", "wh40", "wh68",
            "soil", "pm25", "leak", "lightning", "rain", "weather_station"
        }
        
        return sensor_type in outdoor_types