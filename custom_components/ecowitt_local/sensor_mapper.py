"""Hardware ID mapping logic for Ecowitt Local integration."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .const import BATTERY_SENSORS, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)


class SensorMapper:
    """Handle mapping between sensor data and hardware IDs.
    
    This class is responsible for:
    1. Parsing sensor mapping data from the gateway
    2. Matching live data keys to hardware IDs
    3. Generating stable entity IDs based on hardware information
    """

    def __init__(self) -> None:
        """Initialize the sensor mapper."""
        self._hardware_mapping: Dict[str, str] = {}
        self._sensor_info: Dict[str, Dict[str, Any]] = {}
        self._last_mapping_update: Optional[float] = None

    def update_mapping(self, sensor_mappings: List[Dict[str, Any]]) -> None:
        """Update the hardware ID mapping from sensor mapping data.
        
        Args:
            sensor_mappings: List of sensor mapping dictionaries from API
        """
        self._hardware_mapping.clear()
        self._sensor_info.clear()
        
        for sensor in sensor_mappings:
            try:
                hardware_id = sensor.get("id", "").strip()
                sensor_type = sensor.get("type", "").strip()
                channel = sensor.get("channel", "")
                device_model = sensor.get("sensor_model", "")
                battery = sensor.get("battery", "")
                signal = sensor.get("signal", "")
                
                if not hardware_id:
                    continue
                    
                # Store sensor information
                self._sensor_info[hardware_id] = {
                    "hardware_id": hardware_id,
                    "sensor_type": sensor_type,
                    "channel": channel,
                    "device_model": device_model,
                    "battery": battery,
                    "signal": signal,
                    "raw_data": sensor,
                }
                
                # Map live data keys to hardware IDs
                live_keys = self._generate_live_data_keys(sensor_type, channel)
                for key in live_keys:
                    self._hardware_mapping[key] = hardware_id
                    
            except Exception as err:
                _LOGGER.warning("Error processing sensor mapping: %s", err)
                continue
        
        _LOGGER.debug("Updated hardware mapping with %d sensors", len(self._sensor_info))

    def _generate_live_data_keys(self, sensor_type: str, channel: str) -> List[str]:
        """Generate possible live data keys for a sensor type and channel.
        
        Args:
            sensor_type: Type of sensor (e.g., "WH51", "WH31")
            channel: Channel number or identifier
            
        Returns:
            List of possible live data keys
        """
        keys: List[str] = []
        
        if not sensor_type or not channel:
            return keys
            
        # Normalize channel to integer if possible
        try:
            ch_num = int(channel)
        except (ValueError, TypeError):
            ch_num = None
            
        # Map sensor types to live data keys
        if sensor_type.lower() in ("wh51", "soil"):
            # Soil moisture sensors
            if ch_num:
                keys.extend([
                    f"soilmoisture{ch_num}",
                    f"soilbatt{ch_num}",
                ])
        elif sensor_type.lower() in ("wh31", "temp_hum"):
            # Temperature/humidity sensors
            if ch_num:
                keys.extend([
                    f"temp{ch_num}f",
                    f"humidity{ch_num}",
                    f"batt{ch_num}",
                ])
        elif sensor_type.lower() in ("wh41", "pm25"):
            # PM2.5 sensors
            if ch_num:
                keys.extend([
                    f"pm25_ch{ch_num}",
                    f"pm25_avg_24h_ch{ch_num}",
                    f"pm25batt{ch_num}",
                ])
        elif sensor_type.lower() in ("wh55", "leak"):
            # Leak sensors
            if ch_num:
                keys.extend([
                    f"leak_ch{ch_num}",
                    f"leakbatt{ch_num}",
                ])
        elif sensor_type.lower() in ("wh57", "lightning"):
            # Lightning sensor
            keys.extend([
                "lightning_num",
                "lightning_time",
                "lightning",
                "wh57batt",
            ])
        elif sensor_type.lower() in ("wh40", "rain"):
            # Rain sensor
            keys.extend([
                "rainratein",
                "eventrainin",
                "hourlyrainin",
                "dailyrainin",
                "weeklyrainin",
                "monthlyrainin",
                "yearlyrainin",
                "totalrainin",
                "wh40batt",
            ])
        elif sensor_type.lower() in ("wh68", "weather_station"):
            # Main weather station
            keys.extend([
                "tempf",
                "humidity",
                "windspeedmph",
                "windspdmph_avg10m",
                "windgustmph",
                "maxdailygust",
                "winddir",
                "winddir_avg10m",
                "baromrelin",
                "baromabsin",
                "solarradiation",
                "uv",
                "wh68batt",
            ])
            
        return keys

    def get_hardware_id(self, live_data_key: str) -> Optional[str]:
        """Get hardware ID for a live data key.
        
        Args:
            live_data_key: Key from live data response
            
        Returns:
            Hardware ID if found, None otherwise
        """
        return self._hardware_mapping.get(live_data_key)

    def get_sensor_info(self, hardware_id: str) -> Optional[Dict[str, Any]]:
        """Get sensor information for a hardware ID.
        
        Args:
            hardware_id: Hardware ID of the sensor
            
        Returns:
            Sensor information dictionary if found, None otherwise
        """
        return self._sensor_info.get(hardware_id)

    def generate_entity_id(
        self,
        live_data_key: str,
        hardware_id: Optional[str] = None,
        fallback_suffix: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Generate stable entity ID and friendly name.
        
        Args:
            live_data_key: Key from live data
            hardware_id: Hardware ID if known
            fallback_suffix: Fallback suffix if no hardware ID available
            
        Returns:
            Tuple of (entity_id, friendly_name)
        """
        # Get sensor type information
        sensor_info = SENSOR_TYPES.get(live_data_key, {})
        
        # Determine sensor type for entity ID
        if live_data_key in BATTERY_SENSORS:
            # Battery sensor
            base_name = BATTERY_SENSORS[live_data_key]["name"]
            sensor_type_name = self._extract_sensor_type_from_battery(live_data_key)
        else:
            # Regular sensor
            base_name = sensor_info.get("name", live_data_key.replace("_", " ").title())
            sensor_type_name = self._extract_sensor_type_from_key(live_data_key)
        
        # Generate identifier part
        if hardware_id:
            identifier = hardware_id.lower()
        elif fallback_suffix:
            identifier = fallback_suffix
        else:
            # Extract channel or use the key itself
            identifier = self._extract_identifier_from_key(live_data_key)
        
        # Generate entity ID
        entity_id = f"sensor.ecowitt_{sensor_type_name}_{identifier}"
        
        return entity_id, base_name

    def _extract_sensor_type_from_key(self, key: str) -> str:
        """Extract sensor type name from live data key."""
        # Remove channel numbers and common suffixes
        clean_key = re.sub(r'\d+$', '', key)
        clean_key = re.sub(r'(in|f|ch\d*)$', '', clean_key)
        
        # Map common patterns
        type_mappings = {
            "temp": "temperature",
            "humid": "humidity",
            "barom": "pressure", 
            "wind": "wind",
            "rain": "rain",
            "soil": "soil_moisture",
            "pm25": "pm25",
            "leak": "leak",
            "lightning": "lightning",
            "batt": "battery",
            "solar": "solar_radiation",
        }
        
        for pattern, sensor_type in type_mappings.items():
            if pattern in clean_key.lower():
                return sensor_type
                
        return clean_key or "sensor"

    def _extract_sensor_type_from_battery(self, battery_key: str) -> str:
        """Extract sensor type name from battery key."""
        if "soil" in battery_key:
            return "soil_moisture_battery"
        elif "pm25" in battery_key:
            return "pm25_battery"
        elif "leak" in battery_key:
            return "leak_battery"
        elif "wh57" in battery_key:
            return "lightning_battery"
        elif "wh40" in battery_key:
            return "rain_battery"
        elif "wh68" in battery_key:
            return "weather_station_battery"
        elif battery_key.startswith("batt"):
            return "temperature_humidity_battery"
        else:
            return "battery"

    def _extract_identifier_from_key(self, key: str) -> str:
        """Extract identifier from live data key."""
        # Extract channel number if present
        channel_match = re.search(r'(\d+)$', key)
        if channel_match:
            return f"ch{channel_match.group(1)}"
        
        # Extract channel from middle (e.g., pm25_ch1)
        ch_match = re.search(r'ch(\d+)', key)
        if ch_match:
            return f"ch{ch_match.group(1)}"
            
        # Special cases
        if "indoor" in key or "in" in key:
            return "indoor"
        elif "outdoor" in key or key in ("tempf", "humidity", "windspeedmph"):
            return "outdoor"
        elif "relative" in key or "rel" in key:
            return "relative"
        elif "absolute" in key or "abs" in key:
            return "absolute"
        
        return key.lower()

    def get_all_hardware_ids(self) -> List[str]:
        """Get all known hardware IDs."""
        return list(self._sensor_info.keys())

    def get_mapping_stats(self) -> Dict[str, int]:
        """Get statistics about the current mapping."""
        return {
            "total_sensors": len(self._sensor_info),
            "mapped_keys": len(self._hardware_mapping),
            "sensor_types": len(set(
                info.get("sensor_type", "") for info in self._sensor_info.values()
            )),
        }