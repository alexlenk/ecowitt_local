"""Data update coordinator for Ecowitt Local integration."""
from __future__ import annotations

import asyncio
import logging
import re
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
        self._gateway_temp_unit: str = "°F"  # default; overridden by get_units_info ("0"=°C, "1"=°F)
        
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

            # Fetch gateway unit settings (temp: "0"=Celsius, "1"=Fahrenheit)
            try:
                units_data = await self.api.get_units()
                temp_unit_code = units_data.get("temp", "1")
                self._gateway_temp_unit = "°C" if temp_unit_code == "0" else "°F"
                _LOGGER.debug("Gateway temperature unit: %s (code=%s)", self._gateway_temp_unit, temp_unit_code)
            except Exception as err:
                _LOGGER.warning("Could not fetch gateway unit settings, assuming °F: %s", err)

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
                            # Convert battery level (1=20%, 2=40%, 3=60%, 4=80%, 5=100%)
                            battery_pct = str(int(battery) * 20) if battery.isdigit() else battery
                            all_sensor_items.append({"id": battery_key, "val": battery_pct})
                            _LOGGER.debug("Added soil battery sensor: %s = %s", battery_key, battery_pct)
                        
                        # Get signal strength from sensor mapping (we'll add this in processing)
        
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
        
        # Extract piezoRain data (rain sensor readings from WS90/WH40)
        piezo_rain = raw_data.get("piezoRain", [])
        if piezo_rain:
            _LOGGER.debug("Found piezoRain data with %d items", len(piezo_rain))
            # Process rain sensor data structure
            for item in piezo_rain:
                _LOGGER.debug("piezoRain item: %s", item)
                # Add rain sensor readings to main sensor list
                if isinstance(item, dict) and "id" in item and "val" in item:
                    sensor_id = item["id"]
                    sensor_val = item["val"]
                    all_sensor_items.append({"id": sensor_id, "val": sensor_val})
                    _LOGGER.debug("Added rain sensor: %s = %s", sensor_id, sensor_val)
                    
                    # Add battery sensor if present in the item
                    if "battery" in item and item["battery"]:
                        # For WS90, battery is associated with the last rain item
                        if sensor_id == "0x13":  # Total rain - usually the last item with battery info
                            battery_key = "ws90batt"
                            battery_val = str(int(item["battery"]) * 20) if item["battery"].isdigit() else item["battery"]
                            all_sensor_items.append({"id": battery_key, "val": battery_val})
                            _LOGGER.debug("Added WS90 battery sensor: %s = %s%%", battery_key, battery_val)
        
        # Extract ch_aisle data (WH31 temperature/humidity sensors)
        ch_aisle = raw_data.get("ch_aisle", [])
        if ch_aisle:
            _LOGGER.debug("Found ch_aisle data with %d items", len(ch_aisle))
            # Process WH31 sensor data structure
            for item in ch_aisle:
                _LOGGER.debug("ch_aisle item: %s", item)
                # Convert ch_aisle format to standard format
                if isinstance(item, dict):
                    channel = item.get("channel")
                    temp = item.get("temp")
                    humidity = item.get("humidity")
                    battery = item.get("battery")
                    
                    if channel:
                        # Create temperature sensor if temp data exists
                        if temp and temp != "None":
                            temp_key = f"temp{channel}f"
                            # Pass the actual gateway unit so the coordinator overrides the
                            # SENSOR_TYPES "°F" default. Ecowitt firmware always reports
                            # "unit": "F" in ch_aisle even when the gateway is in Celsius mode.
                            all_sensor_items.append({"id": temp_key, "val": temp, "unit": self._gateway_temp_unit})
                            _LOGGER.debug("Added WH31 temperature sensor: %s = %s (%s)", temp_key, temp, self._gateway_temp_unit)
                        
                        # Create humidity sensor if humidity data exists
                        if humidity and humidity != "None":
                            humidity_val = humidity.replace("%", "")
                            humidity_key = f"humidity{channel}"
                            all_sensor_items.append({"id": humidity_key, "val": humidity_val})
                            _LOGGER.debug("Added WH31 humidity sensor: %s = %s%%", humidity_key, humidity_val)
                        
                        # Create battery sensor if battery data exists
                        if battery and battery != "None":
                            battery_key = f"batt{channel}"
                            # Convert battery level (0-5 scale to percentage)
                            battery_pct = str(int(battery) * 20) if battery.isdigit() else battery
                            all_sensor_items.append({"id": battery_key, "val": battery_pct})
                            _LOGGER.debug("Added WH31 battery sensor: %s = %s%%", battery_key, battery_pct)
        
        _LOGGER.debug("Total sensor items to process: %d", len(all_sensor_items))
        
        for item in all_sensor_items:
            sensor_key = item.get("id") or ""
            sensor_value = item.get("val") or ""
            item_unit = item.get("unit")  # Check for separate unit field (e.g., {"id": "0x02", "val": "43.7", "unit": "F"})
            
            if not sensor_key:
                continue
                
            # Skip empty values unless we include inactive sensors
            if not sensor_value and not self._include_inactive:
                _LOGGER.debug("Skipping sensor %s with empty value (include_inactive=%s)", sensor_key, self._include_inactive)
                continue
            
            # Extract unit from either the separate "unit" field OR embedded in the value
            embedded_unit = None
            numeric_value = sensor_value
            
            # First, check for separate "unit" field in the item (temperature sensors use this)
            if item_unit:
                # Normalize unit to standard Home Assistant format
                embedded_unit = self._normalize_unit(item_unit)
                _LOGGER.debug("Found unit field in item: '%s' -> normalized='%s'", item_unit, embedded_unit)
            # Otherwise, try to extract unit from value string (e.g., "2.24 mph")
            elif sensor_value and isinstance(sensor_value, str):
                import re
                match = re.match(r'^([-+]?\d*\.?\d+)\s*([a-zA-Z%°/]+.*)$', sensor_value.strip())
                if match:
                    numeric_value = match.group(1)
                    embedded_unit = match.group(2).strip()
                    if embedded_unit:
                        # Normalize unit to standard Home Assistant format
                        unit_normalized = self._normalize_unit(embedded_unit)
                        
                        _LOGGER.debug("Extracted unit from value: '%s' -> numeric='%s', unit='%s' (normalized='%s')", 
                                     sensor_value, numeric_value, embedded_unit, unit_normalized)
                        embedded_unit = unit_normalized  # Use normalized unit
                        sensor_value = numeric_value  # Use just the numeric part
                
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
                category = "diagnostic"  # Move battery to diagnostic
                device_class = "battery"
                unit = "%"
                _LOGGER.debug("Battery sensor %s assigned to diagnostic category", sensor_key)
            elif system_info:
                category = "system"
                device_class = system_info.get("device_class") or ""
                unit = system_info.get("unit") or ""
            else:
                category = "sensor"
                device_class = sensor_info.get("device_class") or ""
                unit = sensor_info.get("unit") or ""
            
            # Override unit with detected unit from data if available
            if embedded_unit:
                unit = embedded_unit
            
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
            
            # Convert battery values from 0-5 scale to 0-100%
            converted_value = sensor_value
            if battery_info and sensor_value and str(sensor_value).isdigit():
                # Only convert if this is a raw 1-5 scale value
                int_value = int(sensor_value)
                if int_value <= 5:
                    # Raw scale 1-5, convert to percentage
                    converted_value = str(int_value * 20)
                    _LOGGER.debug("Converted battery value %s to %s%% for sensor %s", sensor_value, converted_value, sensor_key)
                else:
                    # Already a percentage value, keep as is
                    converted_value = sensor_value
                    _LOGGER.debug("Battery value %s already in percentage for sensor %s", sensor_value, sensor_key)
            else:
                converted_value = self._convert_sensor_value(sensor_value, unit)
            
            # Store processed sensor data
            sensors_data[entity_id] = {
                "entity_id": entity_id,
                "name": friendly_name,
                "state": converted_value,
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": sensor_info.get("state_class") or "",
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
        
        # Add diagnostic and signal strength sensors for hardware devices
        self._add_diagnostic_and_signal_sensors(sensors_data)
        
        # Process gateway information
        processed_data["gateway_info"] = await self._process_gateway_info()
        
        _LOGGER.debug("Processed data summary: %d sensors total", len(sensors_data))
        for entity_id, sensor_info in sensors_data.items():
            _LOGGER.debug("Final sensor: %s -> category=%s, key=%s, value=%s", 
                         entity_id, sensor_info.get("category"), 
                         sensor_info.get("sensor_key"), sensor_info.get("state"))
        
        return processed_data

    def _add_diagnostic_and_signal_sensors(self, sensors_data: Dict[str, Any]) -> None:
        """Add signal strength and diagnostic sensors for hardware devices."""
        # Track which hardware IDs we've already added diagnostics for
        added_hardware_ids = set()
        
        # Create a copy of the values to avoid "dictionary changed size during iteration" error
        for sensor_info in list(sensors_data.values()):
            hardware_id = sensor_info.get("hardware_id")
            if not hardware_id or hardware_id in added_hardware_ids:
                continue
                
            # Get hardware info from sensor mapper
            hardware_info = self.sensor_mapper.get_sensor_info(hardware_id)
            if not hardware_info:
                continue
                
            channel = hardware_info.get("channel")
            signal = hardware_info.get("signal")
            if not channel:
                continue
                
            # Add Signal Strength sensor (regular sensor, same level as battery)
            if signal and signal not in ("--", ""):
                signal_entity_id = f"sensor.ecowitt_signal_strength_{hardware_id.lower()}"
                # Convert signal strength (0-4 scale to 0-100%)
                signal_pct = str(int(signal) * 25) if signal.isdigit() else signal
                sensors_data[signal_entity_id] = {
                    "entity_id": signal_entity_id,
                    "name": "Signal Strength",
                    "state": signal_pct,
                    "unit_of_measurement": "%",
                    "device_class": "signal_strength",
                    "category": "diagnostic",  # Move signal strength to diagnostic
                    "sensor_key": f"signal_{hardware_id}",
                    "hardware_id": hardware_id,
                    "raw_value": signal,
                    "attributes": {
                        "sensor_key": f"signal_{hardware_id}",
                        "last_update": datetime.now().isoformat(),
                        "hardware_id": hardware_id,
                        "signal": signal,
                        "signal_percentage": signal_pct,
                    },
                }
                _LOGGER.debug("Added signal strength sensor for hardware_id: %s (signal: %s)", hardware_id, signal)
                
            # Add Hardware ID diagnostic sensor
            hardware_id_entity_id = f"sensor.ecowitt_hardware_id_{hardware_id.lower()}"
            sensors_data[hardware_id_entity_id] = {
                "entity_id": hardware_id_entity_id,
                "name": "Hardware ID",
                "state": hardware_id,
                "unit_of_measurement": None,
                "device_class": None,
                "category": "diagnostic",
                "sensor_key": f"hardware_id_{hardware_id}",
                "hardware_id": hardware_id,
                "raw_value": hardware_id,
                "attributes": {
                    "sensor_key": f"hardware_id_{hardware_id}",
                    "last_update": datetime.now().isoformat(),
                    "hardware_id": hardware_id,
                    "entity_category": "diagnostic",
                },
            }
            
            # Add Channel diagnostic sensor
            channel_entity_id = f"sensor.ecowitt_channel_{hardware_id.lower()}"
            sensors_data[channel_entity_id] = {
                "entity_id": channel_entity_id,
                "name": "Channel",
                "state": channel,
                "unit_of_measurement": None,
                "device_class": None,
                "category": "diagnostic",
                "sensor_key": f"channel_{hardware_id}",
                "hardware_id": hardware_id,
                "raw_value": channel,
                "attributes": {
                    "sensor_key": f"channel_{hardware_id}",
                    "last_update": datetime.now().isoformat(),
                    "hardware_id": hardware_id,
                    "channel": channel,
                    "entity_category": "diagnostic",
                },
            }
            
            added_hardware_ids.add(hardware_id)
            _LOGGER.debug("Added diagnostic sensors for hardware_id: %s (channel: %s, signal: %s)", hardware_id, channel, signal)

    def _normalize_unit(self, unit: str) -> str:
        """Normalize unit string to Home Assistant standard format."""
        if not unit:
            return unit
        
        unit_upper = unit.upper()
        
        # Temperature
        if unit_upper == "F":
            return "°F"
        elif unit_upper == "C":
            return "°C"
        # Irradiance - normalize W/m2 to W/m²
        elif unit_upper == "W/M2":
            return "W/m²"
        # Precipitation intensity - normalize in/Hr to in/h
        elif unit_upper == "IN/HR":
            return "in/h"
        elif unit_upper == "MM/HR":
            return "mm/h"
        # Pressure
        elif unit_upper == "INHG":
            return "inHg"
        elif unit_upper == "HPA":
            return "hPa"
        # Speed
        elif unit_upper == "MPH":
            return "mph"
        elif unit_upper == "KM/H" or unit_upper == "KPH":
            return "km/h"
        elif unit_upper == "M/S":
            return "m/s"
        # Length/precipitation
        elif unit_upper == "IN":
            return "in"
        elif unit_upper == "MM":
            return "mm"
        
        # Return original if no normalization needed
        return unit

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
            
            # Handle special cases and invalid sensor readings
            if (str_value.lower() in ("--", "null", "none", "n/a") or 
                str_value.startswith("--") or 
                str_value.replace("-", "").replace(".", "").strip() == ""):
                return None
            
            # Handle values with embedded units (e.g., "29.40 inHg", "46.4 F", "89%")
            import re
            # Extract numeric part from strings with units
            unit_match = re.match(r'^([-+]?\d*\.?\d+)\s*([a-zA-Z%/]+.*)?$', str_value)
            if unit_match:
                numeric_part = unit_match.group(1)
                try:
                    # Try integer first
                    if '.' not in numeric_part:
                        return int(numeric_part)
                    else:
                        return float(numeric_part)
                except ValueError:
                    pass
                
            # Fallback to original logic for pure numeric strings
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
                firmware_version = version_info.get("version", "Unknown")
                
                # Extract model from firmware version (e.g., "GW1100A_V2.4.3" -> "GW1100A")
                model = self._extract_model_from_firmware(firmware_version)
                if not model or model == "Unknown":
                    # Fallback to stationtype if model extraction fails
                    model = version_info.get("stationtype", "Unknown")
                
                self._gateway_info = {
                    "model": model,
                    "firmware_version": firmware_version,
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

    def _extract_model_from_firmware(self, firmware_version: str) -> str:
        """Extract gateway model from firmware version string.
        
        Args:
            firmware_version: Firmware version string (e.g., "GW1100A_V2.4.3")
            
        Returns:
            Gateway model (e.g., "GW1100A") or "Unknown" if extraction fails
        """
        if not firmware_version or firmware_version == "Unknown":
            return "Unknown"
        
        try:
            # Look for pattern like "GW1100A_V2.4.3" where model is before the first underscore
            if "_" in firmware_version:
                model = firmware_version.split("_")[0].strip()
                if model and model.upper().startswith("GW"):
                    return model
            
            # If no underscore, check if the entire string looks like a model
            if firmware_version.upper().startswith("GW") and not "." in firmware_version:
                return firmware_version.strip()
                
            # Look for other common patterns (model could be at the start)
            # Pattern to match gateway models like GW1100A, GW2000, etc.
            match = re.match(r'^(GW\w+)', firmware_version)
            if match:
                return match.group(1)
                
        except Exception as err:
            _LOGGER.debug("Error extracting model from firmware version '%s': %s", firmware_version, err)
        
        return "Unknown"

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
            # Try to find by iterating and matching by sensor_key for hex ID sensors
            # This handles entity_id mismatches during transition periods
            for eid, sdata in sensors_dict.items():
                if isinstance(sdata, dict):
                    # Extract the sensor_key from the stored entity_id
                    if sdata.get("sensor_key") and entity_id:
                        # Check if the sensor_key matches between stored and requested
                        stored_key = sdata.get("sensor_key", "")
                        # Also check by hardware_id match
                        stored_hw_id = sdata.get("hardware_id", "")
                        if stored_hw_id and stored_hw_id.lower() in entity_id.lower():
                            if stored_key.startswith("0x"):
                                _LOGGER.debug("Found sensor by hardware_id match: %s -> %s", entity_id, eid)
                                return dict(sdata)
            return None
        return dict(sensor_data) if isinstance(sensor_data, dict) else None

    def get_sensor_data_by_key(self, sensor_key: str, hardware_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get sensor data by sensor key and optional hardware ID.
        
        This is a fallback method for finding sensor data when entity_id lookup fails,
        which can happen with hex ID sensors during entity_id format transitions.
        """
        if not self.data:
            return None
        sensors_dict = self.data.get("sensors", {})
        
        for eid, sdata in sensors_dict.items():
            if isinstance(sdata, dict):
                if sdata.get("sensor_key") == sensor_key:
                    # If hardware_id specified, must match; otherwise any match works
                    if hardware_id is None or sdata.get("hardware_id") == hardware_id:
                        return dict(sdata)
        return None

    def get_all_sensors(self) -> Dict[str, Any]:
        """Get all sensor data."""
        if not self.data:
            return {}
        sensors_dict: Dict[str, Any] = self.data.get("sensors", {})
        return sensors_dict