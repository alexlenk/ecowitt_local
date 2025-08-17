"""Fixtures for Ecowitt Local integration tests."""
from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
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
            "type": "WH51",
            "channel": "1",
            "sensor_model": "WH51",
            "battery": "85",
            "signal": "4",
        },
        {
            "id": "D8648",
            "type": "WH51", 
            "channel": "2",
            "sensor_model": "WH51",
            "battery": "78",
            "signal": "3",
        },
        {
            "id": "EF891",
            "type": "WH41",
            "channel": "1", 
            "sensor_model": "WH41",
            "battery": "92",
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
    mock_instance.close.return_value = None
    
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
    
    # Mock the coordinator and create a minimal working one for the test
    from custom_components.ecowitt_local.coordinator import EcowittLocalDataUpdateCoordinator
    from unittest.mock import AsyncMock, MagicMock
    
    mock_coordinator = MagicMock()
    mock_coordinator.async_setup = AsyncMock(return_value=None)
    mock_coordinator.async_shutdown = AsyncMock(return_value=None)
    mock_coordinator.gateway_info = mock_gateway_version
    mock_coordinator.data = {"test": "data"}
    
    # Patch multiple components to ensure integration loads successfully
    with patch("custom_components.ecowitt_local.api.EcowittLocalAPI", return_value=mock_ecowitt_api), \
         patch("custom_components.ecowitt_local.coordinator.EcowittLocalDataUpdateCoordinator", return_value=mock_coordinator):
        
        # Add config entry to hass
        mock_config_entry.add_to_hass(hass)
        
        # Setup the integration
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        
        return mock_config_entry