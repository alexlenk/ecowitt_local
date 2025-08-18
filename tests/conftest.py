"""Fixtures for Ecowitt Local integration tests."""
from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytest_plugins = "pytest_homeassistant_custom_component"

from custom_components.ecowitt_local.const import DOMAIN, CONF_HOST, CONF_PASSWORD


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PASSWORD: "test_password",
            "scan_interval": 60,
            "mapping_interval": 600,
            "include_inactive": False,
        },
        entry_id="test_entry_id",
        unique_id="gw1100a_192.168.1.100",
        title="Ecowitt Gateway (192.168.1.100)",
    )


@pytest.fixture
def mock_gateway_version() -> Dict[str, Any]:
    """Mock gateway version response."""
    return {
        "stationtype": "GW1100A",
        "version": "1.7.3",
        "build": "20231201",
    }


@pytest.fixture
def mock_wh68_sensor_mapping() -> Dict[str, Any]:
    """Mock WH68 weather station sensor mapping."""
    return {
        "id": "A1B2C3",
        "img": "wh68",
        "type": "1", 
        "name": "Solar & Wind",
        "batt": "2.8",
        "rssi": "-72",
        "signal": "4",
        "idst": "1"
    }


@pytest.fixture
def mock_wh68_live_data() -> Dict[str, Any]:
    """Mock WH68 weather station live data."""
    return {
        "tempf": "75.2",
        "humidity": "45",
        "windspeedmph": "5.2", 
        "windspdmph_avg10m": "4.8",
        "windgustmph": "8.1",
        "maxdailygust": "15.3",
        "winddir": "180",
        "winddir_avg10m": "185",
        "baromrelin": "29.85",
        "baromabsin": "29.85", 
        "solarradiation": "850.5",
        "uv": "6",
        "wh68batt": "2.8"
    }


@pytest.fixture
def mock_wh31_sensor_mapping() -> Dict[str, Any]:
    """Mock WH31 temp/humidity sensor mapping."""
    return {
        "id": "D1E2F3",
        "img": "wh31",
        "type": "6",
        "name": "Temp & Humidity CH1", 
        "batt": "85",
        "rssi": "-68",
        "signal": "4",
        "idst": "1"
    }


@pytest.fixture 
def mock_wh31_live_data() -> Dict[str, Any]:
    """Mock WH31 temp/humidity live data."""
    return {
        "temp1f": "72.5",
        "humidity1": "50",
        "dewpoint1f": "52.1",
        "batt1": "85"
    }


@pytest.fixture
def mock_complete_sensor_mappings(mock_wh68_sensor_mapping, mock_wh31_sensor_mapping, mock_wh57_sensor_mapping, mock_wh40_sensor_mapping, mock_wh41_sensor_mapping, mock_wh55_sensor_mapping, mock_wh45_sensor_mapping) -> list[Dict[str, Any]]:
    """Mock complete sensor mappings including soil sensors and all weather/environmental/air quality sensors."""
    return [
        {
            "id": "D8174", 
            "img": "wh51",
            "type": "15",
            "name": "Soil moisture CH2",
            "batt": "1",
            "rssi": "-83", 
            "signal": "4",
            "idst": "1"
        },
        mock_wh68_sensor_mapping,
        mock_wh31_sensor_mapping,
        mock_wh57_sensor_mapping,
        mock_wh40_sensor_mapping,
        mock_wh41_sensor_mapping,
        mock_wh55_sensor_mapping,
        mock_wh45_sensor_mapping
    ]


@pytest.fixture
def mock_wh57_sensor_mapping() -> Dict[str, Any]:
    """Mock WH57 lightning detector sensor mapping."""
    return {
        "id": "E4F5A6",
        "img": "wh57",
        "type": "26",
        "name": "Lightning",
        "batt": "90",
        "rssi": "-65",
        "signal": "4",
        "idst": "1"
    }


@pytest.fixture
def mock_wh57_live_data() -> Dict[str, Any]:
    """Mock WH57 lightning detector live data."""
    return {
        "lightning_num": "12",
        "lightning_time": "2024-08-18T14:30:15",
        "lightning": "8.5",
        "lightning_mi": "5.3",
        "wh57batt": "90"
    }


@pytest.fixture
def mock_wh40_sensor_mapping() -> Dict[str, Any]:
    """Mock WH40 rain gauge sensor mapping."""
    return {
        "id": "F6G7H8",
        "img": "wh40",
        "type": "3",
        "name": "Rain",
        "batt": "78",
        "rssi": "-70",
        "signal": "4",
        "idst": "1"
    }


@pytest.fixture
def mock_wh40_live_data() -> Dict[str, Any]:
    """Mock WH40 rain gauge live data."""
    return {
        "rainratein": "0.12",
        "eventrainin": "0.05",
        "hourlyrainin": "0.15",
        "dailyrainin": "0.87",
        "weeklyrainin": "2.34",
        "monthlyrainin": "5.67",
        "yearlyrainin": "45.23",
        "totalrainin": "112.56",
        "wh40batt": "2.8"
    }


@pytest.fixture
def mock_wh41_sensor_mapping() -> Dict[str, Any]:
    """Mock WH41 PM2.5 sensor mapping."""
    return {
        "id": "G8H9I0",
        "img": "wh41",
        "type": "22",
        "name": "PM2.5 CH1",
        "batt": "85",
        "rssi": "-72",
        "signal": "4",
        "idst": "1"
    }


@pytest.fixture
def mock_wh41_live_data() -> Dict[str, Any]:
    """Mock WH41 PM2.5 live data."""
    return {
        "pm25_ch1": "35.2",
        "pm25_avg_24h_ch1": "28.7",
        "pm25batt1": "85"
    }


@pytest.fixture
def mock_wh55_sensor_mapping() -> Dict[str, Any]:
    """Mock WH55 leak detection sensor mapping."""
    return {
        "id": "J1K2L3",
        "img": "wh55",
        "type": "27",
        "name": "Leak CH1",
        "batt": "92",
        "rssi": "-68",
        "signal": "4",
        "idst": "1"
    }


@pytest.fixture
def mock_wh55_live_data() -> Dict[str, Any]:
    """Mock WH55 leak detection live data."""
    return {
        "leak_ch1": "0",
        "leakbatt1": "92"
    }


@pytest.fixture
def mock_wh45_sensor_mapping() -> Dict[str, Any]:
    """Mock WH45 CO2/PM2.5/PM10 combo sensor mapping."""
    return {
        "id": "M4N5O6",
        "img": "wh45",
        "type": "39",
        "name": "PM25 & PM10 & CO2",
        "batt": "88",
        "rssi": "-65",
        "signal": "4",
        "idst": "1"
    }


@pytest.fixture
def mock_wh45_live_data() -> Dict[str, Any]:
    """Mock WH45 combo sensor live data."""
    return {
        "tf_co2": "72.1",
        "tf_co2c": "22.3",
        "humi_co2": "45",
        "pm25_co2": "28.5",
        "pm25_24h_co2": "31.2",
        "pm10_co2": "42.8",
        "pm10_24h_co2": "38.9",
        "co2": "487",
        "co2_24h": "512",
        "co2_batt": "88"
    }


@pytest.fixture
def mock_complete_live_data(mock_wh68_live_data, mock_wh31_live_data, mock_wh57_live_data, mock_wh40_live_data, mock_wh41_live_data, mock_wh55_live_data, mock_wh45_live_data) -> Dict[str, Any]:
    """Mock complete live data including soil, weather, lightning, rain, air quality, leak detection, and combo sensors."""
    return {
        "soilmoisture2": "24",
        "soilbatt2": "1.2",
        **mock_wh68_live_data,
        **mock_wh31_live_data,
        **mock_wh57_live_data,
        **mock_wh40_live_data,
        **mock_wh41_live_data,
        **mock_wh55_live_data,
        **mock_wh45_live_data
    }


@pytest.fixture
def mock_live_data() -> Dict[str, Any]:
    """Mock live data response."""
    return {
        "common_list": [
            {"id": "tempinf", "val": "72.5"},
            {"id": "humidityin", "val": "45"},
            {"id": "tempf", "val": "68.2"},
            {"id": "humidity", "val": "52"},
            {"id": "windspeedmph", "val": "5.4"},
            {"id": "winddir", "val": "225"},
            {"id": "baromrelin", "val": "30.12"},
            {"id": "soilmoisture1", "val": "35"},
            {"id": "soilmoisture2", "val": "42"},
            {"id": "soilbatt1", "val": "85"},
            {"id": "soilbatt2", "val": "78"},
            {"id": "pm25_ch1", "val": "12"},
            {"id": "pm25batt1", "val": "92"},
        ]
    }


@pytest.fixture
def mock_sensor_mapping() -> list[Dict[str, Any]]:
    """Mock sensor mapping response."""
    return [
        {
            "id": "D8174",
            "img": "WH51",
            "name": "Soil moisture CH1",
            "batt": "85",
            "signal": "4",
        },
        {
            "id": "D8648",
            "img": "WH51", 
            "name": "Soil moisture CH2",
            "batt": "78",
            "signal": "3",
        },
        {
            "id": "EF891",
            "img": "WH41",
            "name": "PM2.5 air quality sensor CH1",
            "batt": "92",
            "signal": "4",
        },
    ]


@pytest.fixture
def mock_units_data() -> Dict[str, Any]:
    """Mock units data response."""
    return {
        "temp": "1",  # Fahrenheit
        "pressure": "0",  # inHg
        "wind": "0",  # mph
        "rain": "0",  # inch
        "solar": "0",  # W/m²
    }


@pytest.fixture
def mock_ecowitt_api():
    """Mock the EcowittLocalAPI."""
    from unittest.mock import AsyncMock, MagicMock
    
    mock_instance = AsyncMock()
    mock_instance.authenticate.return_value = True
    mock_instance.test_connection.return_value = True
    mock_instance.close = AsyncMock(return_value=None)
    mock_instance.get_live_data = AsyncMock(return_value={"common_list": []})
    mock_instance.get_version = AsyncMock(return_value={"stationtype": "GW1100A", "version": "1.7.3"})
    mock_instance.get_all_sensor_mappings = AsyncMock(return_value=[])
    
    return mock_instance


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, 
    mock_config_entry: MockConfigEntry,
    mock_ecowitt_api,
    mock_gateway_version,
    mock_live_data,
    mock_sensor_mapping,
    mock_units_data,
):
    """Set up the integration with mocked data."""
    # Configure mock API responses  
    mock_ecowitt_api.get_version.return_value = mock_gateway_version
    mock_ecowitt_api.get_live_data.return_value = mock_live_data
    mock_ecowitt_api.get_all_sensor_mappings.return_value = mock_sensor_mapping
    mock_ecowitt_api.get_units.return_value = mock_units_data
    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.authenticate.return_value = True
    mock_ecowitt_api.close.return_value = None
    
    # Add config entry to hass
    mock_config_entry.add_to_hass(hass)
    
    # Patch the API class in both locations where it's imported
    with patch("custom_components.ecowitt_local.coordinator.EcowittLocalAPI", return_value=mock_ecowitt_api), \
         patch("custom_components.ecowitt_local.api.EcowittLocalAPI", return_value=mock_ecowitt_api):
        
        # Setup the integration
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        
        # Verify the entry was loaded
        assert result is True
        assert mock_config_entry.state == ConfigEntryState.LOADED
        
        yield mock_config_entry
