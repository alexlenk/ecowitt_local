"""Data update coordinator for Ecowitt Local integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EcowittLocalAPI, AuthenticationError, ConnectionError as APIConnectionError
from .const import (
    DOMAIN,
    CONF_SCAN_INTERVAL,
    CONF_MAPPING_INTERVAL,
    CONF_INCLUDE_INACTIVE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MAPPING_INTERVAL,
    SENSOR_TYPES,
    BATTERY_SENSORS,
    SYSTEM_SENSORS,
)
from .sensor_mapper import SensorMapper

_LOGGER = logging.getLogger(__name__)


class EcowittLocalDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Data coordinator for Ecowitt Local."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize coordinator."""
        self.config_entry = config_entry
        self.api = EcowittLocalAPI(
            host=config_entry.data[CONF_HOST],
            password=config_entry.data.get(CONF_PASSWORD, ""),
        )
        self.sensor_mapper = SensorMapper()
        self._gateway_info: Dict[str, Any] = {}
        self._last_mapping_update: Optional[datetime] = None
        self._include_inactive = config_entry.data.get(CONF_INCLUDE_INACTIVE, False)
        
        # Get update intervals
        scan_interval = config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Ecowitt gateway."""
        try:
            # Update sensor mapping if needed
            await self._update_sensor_mapping_if_needed()
            
            # Get live data
            live_data = await self.api.get_live_data()
            
            # Process the data
            processed_data = await self._process_live_data(live_data)
            
            return processed_data
            
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except APIConnectionError as err:
            raise UpdateFailed(f"Error communicating with gateway: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching data")
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _update_sensor_mapping_if_needed(self) -> None:
        """Update sensor mapping if enough time has passed."""
        mapping_interval = self.config_entry.data.get(
            CONF_MAPPING_INTERVAL, DEFAULT_MAPPING_INTERVAL
        )
        
        now = datetime.now()
        if (
            self._last_mapping_update is None
            or (now - self._last_mapping_update).total_seconds() >= mapping_interval
        ):
            await self._update_sensor_mapping()
            self._last_mapping_update = now

    async def _update_sensor_mapping(self) -> None:
        """Update sensor hardware ID mapping."""
        try:
            _LOGGER.debug("Updating sensor mapping")
            
            # Get sensor mappings from both pages
            sensor_mappings = await self.api.get_all_sensor_mappings()
            
            # Update the mapper
            self.sensor_mapper.update_mapping(sensor_mappings)
            
            stats = self.sensor_mapper.get_mapping_stats()
            _LOGGER.info(
                "Updated sensor mapping: %d sensors, %d mapped keys, %d sensor types",
                stats["total_sensors"],
                stats["mapped_keys"],
                stats["sensor_types"],
            )
            
        except Exception as err:
            _LOGGER.warning("Failed to update sensor mapping: %s", err)

    async def _process_live_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw live data into structured sensor data."""
        sensors_data: Dict[str, Any] = {}
        processed_data: Dict[str, Any] = {
            "sensors": sensors_data,
            "gateway_info": {},
            "last_update": datetime.now(),
        }
        
        # Extract common_list data (main sensor readings)
        common_list = raw_data.get("common_list", [])
        
        for item in common_list:
            sensor_key = item.get("id") or ""
            sensor_value = item.get("val") or ""
            
            if not sensor_key:
                continue
                
            # Skip empty values unless we include inactive sensors
            if not sensor_value and not self._include_inactive:
                continue
                
            # Get hardware ID for this sensor
            hardware_id = self.sensor_mapper.get_hardware_id(sensor_key)
            
            # Generate entity information
            entity_id, friendly_name = self.sensor_mapper.generate_entity_id(
                sensor_key, hardware_id
            )
            
            # Get sensor type information
            sensor_info = SENSOR_TYPES.get(sensor_key, {})
            battery_info = BATTERY_SENSORS.get(sensor_key, {})
            system_info = SYSTEM_SENSORS.get(sensor_key, {})
            
            # Determine sensor category
            if battery_info:
                category = "battery"
                device_class = "battery"
                unit = "%"
            elif system_info:
                category = "system"
                device_class = system_info.get("device_class") or ""
                unit = system_info.get("unit") or ""
            else:
                category = "sensor"
                device_class = sensor_info.get("device_class") or ""
                unit = sensor_info.get("unit") or ""
            
            # Get additional sensor information
            sensor_details: Dict[str, Any] = {}
            if hardware_id:
                hardware_info = self.sensor_mapper.get_sensor_info(hardware_id)
                if hardware_info:
                    sensor_details = {
                        "hardware_id": hardware_id,
                        "channel": hardware_info.get("channel"),
                        "device_model": hardware_info.get("device_model"),
                        "battery": hardware_info.get("battery"),
                        "signal": hardware_info.get("signal"),
                    }
            
            # Store processed sensor data
            sensors_data[entity_id] = {
                "entity_id": entity_id,
                "name": friendly_name,
                "state": self._convert_sensor_value(sensor_value, unit),
                "unit_of_measurement": unit,
                "device_class": device_class,
                "category": category,
                "sensor_key": sensor_key,
                "hardware_id": hardware_id,
                "raw_value": sensor_value,
                "attributes": {
                    "sensor_key": sensor_key,
                    "last_update": datetime.now().isoformat(),
                    **sensor_details,
                },
            }
        
        # Process gateway information
        processed_data["gateway_info"] = await self._process_gateway_info()
        
        return processed_data

    def _convert_sensor_value(self, value: Any, unit: Optional[str]) -> Any:
        """Convert sensor value to appropriate type."""
        if not value or value == "":
            return None
            
        try:
            # Handle numeric values
            if isinstance(value, (int, float)):
                return value
                
            # Try to convert string to number
            str_value = str(value).strip()
            
            # Handle special cases
            if str_value.lower() in ("--", "null", "none", "n/a"):
                return None
                
            # Try integer first
            try:
                return int(str_value)
            except ValueError:
                pass
                
            # Try float
            try:
                return float(str_value)
            except ValueError:
                pass
                
            # Return as string if conversion fails
            return str_value
            
        except Exception as err:
            _LOGGER.debug("Error converting sensor value '%s': %s", value, err)
            return str(value) if value else None

    async def _process_gateway_info(self) -> Dict[str, Any]:
        """Process gateway information."""
        if not self._gateway_info:
            try:
                version_info = await self.api.get_version()
                self._gateway_info = {
                    "model": version_info.get("stationtype", "Unknown"),
                    "firmware_version": version_info.get("version", "Unknown"),
                    "host": self.config_entry.data[CONF_HOST],
                    "gateway_id": version_info.get("stationtype", "unknown"),
                }
            except Exception as err:
                _LOGGER.warning("Failed to get gateway info: %s", err)
                self._gateway_info = {
                    "model": "Unknown",
                    "firmware_version": "Unknown",
                    "host": self.config_entry.data[CONF_HOST],
                    "gateway_id": "unknown",
                }
        
        return self._gateway_info

    async def async_refresh_mapping(self) -> None:
        """Force refresh of sensor mapping."""
        await self._update_sensor_mapping()
        await self.async_request_refresh()

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        try:
            # Test initial connection
            await self.api.test_connection()
            
            # Do initial sensor mapping update
            await self._update_sensor_mapping()
            
            _LOGGER.info("Ecowitt Local coordinator setup complete")
            
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except APIConnectionError as err:
            raise ConfigEntryNotReady(f"Cannot connect to gateway: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error during setup")
            raise ConfigEntryNotReady(f"Setup failed: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self.api.close()

    @property
    def gateway_info(self) -> Dict[str, Any]:
        """Get gateway information."""
        return self._gateway_info

    def get_sensor_data(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get sensor data for a specific entity."""
        if not self.data:
            return None
        sensors_dict = self.data.get("sensors", {})
        sensor_data = sensors_dict.get(entity_id)
        if sensor_data is None:
            return None
        return dict(sensor_data) if isinstance(sensor_data, dict) else None

    def get_all_sensors(self) -> Dict[str, Any]:
        """Get all sensor data."""
        if not self.data:
            return {}
        sensors_dict: Dict[str, Any] = self.data.get("sensors", {})
        return sensors_dict