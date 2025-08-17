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
    GATEWAY_SENSORS,
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
            _LOGGER.debug("Raw live data keys: %s", list(live_data.keys()) if live_data else "None")
            if live_data.get("common_list"):
                _LOGGER.debug("Found %d items in common_list", len(live_data["common_list"]))
                for item in live_data["common_list"]:
                    _LOGGER.debug("Sensor item: id=%s, val=%s", item.get("id"), item.get("val"))
            else:
                _LOGGER.debug("No common_list found in live data")
            
            # Also check other data structures
            for key in live_data.keys():
                if key != "common_list":
                    _LOGGER.debug("Additional data key '%s': %s", key, live_data[key])
            
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
            _LOGGER.debug("Triggering sensor mapping update (last_update=%s, interval=%s)", self._last_mapping_update, mapping_interval)
            await self._update_sensor_mapping()
            self._last_mapping_update = now
        else:
            _LOGGER.debug("Skipping sensor mapping update (last_update=%s, interval=%s)", self._last_mapping_update, mapping_interval)

    async def _update_sensor_mapping(self) -> None:
        """Update sensor hardware ID mapping."""
        try:
            _LOGGER.debug("Updating sensor mapping")
            
            # Get sensor mappings from both pages
            sensor_mappings = await self.api.get_all_sensor_mappings()
            _LOGGER.debug("Retrieved %d sensor mappings from API", len(sensor_mappings))
            if not sensor_mappings:
                _LOGGER.warning("No sensor mappings returned from API - this will cause all sensors to appear on gateway device")
            for mapping in sensor_mappings:
                _LOGGER.debug("Sensor mapping: %s", mapping)
            
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
        
        # Process all sensor data sources
        all_sensor_items = []
        
        # Extract common_list data (main sensor readings)
        common_list = raw_data.get("common_list", [])
        all_sensor_items.extend(common_list)
        
        # Extract ch_soil data (soil sensor readings)
        ch_soil = raw_data.get("ch_soil", [])
        if ch_soil:
            _LOGGER.debug("Found ch_soil data with %d items", len(ch_soil))
            # Process soil sensor data structure
            for item in ch_soil:
                _LOGGER.debug("ch_soil item: %s", item)
                # Convert ch_soil format to standard format
                if isinstance(item, dict):
                    channel = item.get("channel")
                    humidity = item.get("humidity", "").replace("%", "")
                    battery = item.get("battery")
                    
                    if channel and humidity:
                        # Create soil moisture sensor
                        soil_key = f"soilmoisture{channel}"
                        all_sensor_items.append({"id": soil_key, "val": humidity})
                        _LOGGER.debug("Added soil sensor: %s = %s%%", soil_key, humidity)
                        
                        # Create battery sensor if battery data exists
                        if battery:
                            battery_key = f"soilbatt{channel}"
                            # Convert battery level (1=low, 9=high) to percentage
                            battery_pct = str((int(battery) - 1) * 12.5) if battery.isdigit() else battery
                            all_sensor_items.append({"id": battery_key, "val": battery_pct})
                            _LOGGER.debug("Added soil battery sensor: %s = %s", battery_key, battery_pct)
        
        # Extract wh25 data (indoor temp/humidity/pressure)
        wh25_data = raw_data.get("wh25", [])
        if wh25_data and len(wh25_data) > 0:
            _LOGGER.debug("Found wh25 data: %s", wh25_data[0])
            wh25_item = wh25_data[0]
            if isinstance(wh25_item, dict):
                # Indoor temperature
                if "intemp" in wh25_item:
                    temp_val = wh25_item["intemp"]
                    all_sensor_items.append({"id": "tempinf", "val": temp_val})
                    _LOGGER.debug("Added indoor temp: tempinf = %s", temp_val)
                
                # Indoor humidity  
                if "inhumi" in wh25_item:
                    humi_val = wh25_item["inhumi"].replace("%", "")
                    all_sensor_items.append({"id": "humidityin", "val": humi_val})
                    _LOGGER.debug("Added indoor humidity: humidityin = %s", humi_val)
                
                # Absolute pressure
                if "abs" in wh25_item:
                    abs_val = wh25_item["abs"].replace(" hPa", "")
                    _LOGGER.debug("Raw absolute pressure from gateway: '%s', cleaned: '%s'", wh25_item["abs"], abs_val)
                    all_sensor_items.append({"id": "baromabsin", "val": abs_val})
                    _LOGGER.debug("Added absolute pressure: baromabsin = %s", abs_val)
                
                # Relative pressure
                if "rel" in wh25_item:
                    rel_val = wh25_item["rel"].replace(" hPa", "")
                    _LOGGER.debug("Raw relative pressure from gateway: '%s', cleaned: '%s'", wh25_item["rel"], rel_val)
                    all_sensor_items.append({"id": "baromrelin", "val": rel_val})
                    _LOGGER.debug("Added relative pressure: baromrelin = %s", rel_val)
        
        _LOGGER.debug("Total sensor items to process: %d", len(all_sensor_items))
        
        for item in all_sensor_items:
            sensor_key = item.get("id") or ""
            sensor_value = item.get("val") or ""
            
            if not sensor_key:
                continue
                
            # Skip empty values unless we include inactive sensors
            if not sensor_value and not self._include_inactive:
                _LOGGER.debug("Skipping sensor %s with empty value (include_inactive=%s)", sensor_key, self._include_inactive)
                continue
                
            # Get hardware ID for this sensor (only for non-gateway sensors)
            hardware_id = None
            if sensor_key not in GATEWAY_SENSORS:
                hardware_id = self.sensor_mapper.get_hardware_id(sensor_key)
                _LOGGER.debug("Hardware ID lookup for %s: %s", sensor_key, hardware_id)
            
            # Generate entity information
            entity_id, friendly_name = self.sensor_mapper.generate_entity_id(
                sensor_key, hardware_id
            )
            _LOGGER.debug("Processing sensor: key=%s, value=%s, hardware_id=%s, entity_id=%s", 
                         sensor_key, sensor_value, hardware_id, entity_id)
            
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
        
        _LOGGER.debug("Processed data summary: %d sensors total", len(sensors_data))
        for entity_id, sensor_info in sensors_data.items():
            _LOGGER.debug("Final sensor: %s -> category=%s, key=%s, value=%s", 
                         entity_id, sensor_info.get("category"), 
                         sensor_info.get("sensor_key"), sensor_info.get("state"))
        
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
        # Cancel any pending refresh tasks
        if hasattr(self, '_debounced_refresh'):
            self._debounced_refresh.async_cancel()
        
        # Cancel the refresh interval timer
        if hasattr(self, '_unsub_refresh') and getattr(self, '_unsub_refresh', None):
            unsub_refresh = getattr(self, '_unsub_refresh')
            if unsub_refresh:
                unsub_refresh()
            setattr(self, '_unsub_refresh', None)
        
        # Close the API connection
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