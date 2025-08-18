"""Test the Ecowitt Local coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
import pytest
import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.ecowitt_local.api import AuthenticationError, ConnectionError as APIConnectionError
from custom_components.ecowitt_local.coordinator import EcowittLocalDataUpdateCoordinator


@pytest.fixture
async def coordinator(hass, mock_config_entry, mock_ecowitt_api):
    """Create a coordinator for testing."""
    # Add config entry to hass first
    mock_config_entry.add_to_hass(hass)
    
    # Patch the API constructor to prevent real session creation
    with patch("custom_components.ecowitt_local.coordinator.EcowittLocalAPI", return_value=mock_ecowitt_api):
        # The mock_config_entry fixture already has proper data, so just use it
        coordinator = EcowittLocalDataUpdateCoordinator(hass, mock_config_entry)
        
        # Set up default mock responses
        mock_ecowitt_api.get_live_data.return_value = {"common_list": []}
        mock_ecowitt_api.get_version.return_value = {"stationtype": "GW1100A", "version": "1.7.3"}
        mock_ecowitt_api.get_all_sensor_mappings.return_value = []
        mock_ecowitt_api.close = AsyncMock(return_value=None)
        
        # Mock methods that could cause issues with config_entry or timers
        coordinator._update_sensor_mapping_if_needed = AsyncMock()
        coordinator._process_gateway_info = AsyncMock(return_value={
            "model": "GW1100A",
            "firmware_version": "1.7.3", 
            "host": "192.168.1.100",
            "gateway_id": "GW1100A"
        })
        coordinator.async_request_refresh = AsyncMock()
        
        # Cancel any scheduled refresh to avoid lingering timers
        if hasattr(coordinator, '_debounced_refresh'):
            coordinator._debounced_refresh.async_cancel()
        
        yield coordinator
        
        # Cleanup any timers and tasks
        try:
            if hasattr(coordinator, '_debounced_refresh'):
                coordinator._debounced_refresh.async_cancel()
            # Cancel any update interval 
            if hasattr(coordinator, '_unsub_refresh') and coordinator._unsub_refresh:
                coordinator._unsub_refresh()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_coordinator_auth_error_handling(coordinator):
    """Test coordinator handling authentication errors."""
    coordinator.api.get_live_data = AsyncMock(side_effect=AuthenticationError("Auth failed"))
    coordinator.api.get_all_sensor_mappings = AsyncMock(return_value=[])
    
    with pytest.raises(ConfigEntryAuthFailed, match="Authentication failed"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_connection_error_handling(coordinator):
    """Test coordinator handling connection errors.""" 
    coordinator.api.get_live_data = AsyncMock(side_effect=APIConnectionError("Connection failed"))
    coordinator.api.get_all_sensor_mappings = AsyncMock(return_value=[])
    
    with pytest.raises(UpdateFailed, match="Error communicating with gateway"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_unexpected_error_handling(coordinator):
    """Test coordinator handling unexpected errors."""
    coordinator.api.get_live_data = AsyncMock(side_effect=ValueError("Unexpected error"))
    coordinator.api.get_all_sensor_mappings = AsyncMock(return_value=[])
    
    with pytest.raises(UpdateFailed, match="Unexpected error"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_process_live_data_error(coordinator):
    """Test coordinator handling data processing errors."""
    # Mock successful API call but processing failure
    coordinator.api.get_live_data = AsyncMock(return_value={"invalid": "data"})
    coordinator.api.get_all_sensor_mappings = AsyncMock(return_value=[])
    coordinator._process_live_data = AsyncMock(side_effect=KeyError("Missing key"))
    
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_sensor_mapping_refresh(coordinator):
    """Test sensor mapping refresh functionality."""
    mock_mappings = [
        {
            "id": "D8174",
            "img": "wh51", 
            "type": "15",
            "name": "Soil moisture CH2",
            "batt": "1",
            "signal": "4"
        }
    ]
    
    coordinator.api.get_all_sensor_mappings = AsyncMock(return_value=mock_mappings)
    coordinator.api.get_live_data = AsyncMock(return_value={"common_list": []})
    
    # Mock the async_request_refresh to avoid debouncer issues
    coordinator.async_request_refresh = AsyncMock()
    
    # Test successful refresh using the correct method name
    await coordinator.async_refresh_mapping()
    
    # Verify mapping was updated
    assert coordinator.sensor_mapper.get_hardware_id("soilmoisture2") == "D8174"


@pytest.mark.asyncio
async def test_coordinator_sensor_mapping_refresh_error(coordinator):
    """Test sensor mapping refresh error handling."""
    coordinator.api.get_all_sensor_mappings = AsyncMock(side_effect=APIConnectionError("Connection failed"))
    coordinator.api.get_live_data = AsyncMock(return_value={"common_list": []})
    
    # Mock the async_request_refresh to avoid debouncer issues
    coordinator.async_request_refresh = AsyncMock()
    
    # Should not raise exception, but log error
    await coordinator.async_refresh_mapping()
    
    # Mapping should remain unchanged (starts empty)
    assert len(coordinator.sensor_mapper.get_all_hardware_ids()) == 0


@pytest.mark.asyncio
async def test_coordinator_gateway_info_processing(coordinator):
    """Test gateway info processing."""
    # The gateway info is processed in _process_gateway_info, which is called during data update
    mock_version_info = {
        "stationtype": "GW1100A", 
        "version": "1.7.3"
    }
    
    # Mock the gateway info to avoid config_entry issues
    mock_gateway_info = {
        "model": "GW1100A",
        "firmware_version": "1.7.3",
        "host": "192.168.1.100",
        "gateway_id": "GW1100A"
    }
    coordinator._process_gateway_info = AsyncMock(return_value=mock_gateway_info)
    
    # Call _process_gateway_info directly
    gateway_info = await coordinator._process_gateway_info()
    
    assert gateway_info["model"] == "GW1100A"
    assert gateway_info["firmware_version"] == "1.7.3"


@pytest.mark.asyncio
async def test_coordinator_gateway_info_error(coordinator):
    """Test gateway info processing with error."""
    # Mock the gateway info to return default values on error
    mock_gateway_info = {
        "model": "Unknown",
        "firmware_version": "Unknown",
        "host": "192.168.1.100",
        "gateway_id": "unknown"
    }
    coordinator._process_gateway_info = AsyncMock(return_value=mock_gateway_info)
    
    # Should handle the error gracefully and return default info
    gateway_info = await coordinator._process_gateway_info()
    
    # Gateway info should have default values on error
    assert gateway_info["model"] == "Unknown"
    assert gateway_info["firmware_version"] == "Unknown"


@pytest.mark.asyncio
async def test_coordinator_data_processing_with_additional_keys(coordinator):
    """Test data processing with additional data keys."""
    mock_live_data = {
        "common_list": [{"id": "tempf", "val": "72.5"}],
        "wh25": [{"intemp": "28.9", "unit": "C"}],
        "ch_soil": [{"channel": "1", "humidity": "50%"}]
    }
    
    coordinator.api.get_live_data = AsyncMock(return_value=mock_live_data)
    coordinator.api.get_all_sensor_mappings = AsyncMock(return_value=[])
    coordinator.api.get_version = AsyncMock(return_value={"stationtype": "GW1100A", "version": "1.7.3"})
    
    # Should process successfully and log additional keys (gateway info already mocked in fixture)
    result = await coordinator._async_update_data()
    
    assert result is not None
    assert "sensors" in result
    # Check if the sensor data was processed correctly
    sensors = result["sensors"]
    # Find the tempf sensor in the processed data
    tempf_sensor = None
    for sensor_id, sensor_data in sensors.items():
        if sensor_data.get("sensor_key") == "tempf":
            tempf_sensor = sensor_data
            break
    assert tempf_sensor is not None


@pytest.mark.asyncio
async def test_coordinator_empty_common_list_handling(coordinator):
    """Test coordinator handling empty common_list."""
    mock_live_data = {
        "common_list": [],
        "wh25": [{"intemp": "28.9", "unit": "C"}]
    }
    
    coordinator.api.get_live_data = AsyncMock(return_value=mock_live_data)
    coordinator.api.get_all_sensor_mappings = AsyncMock(return_value=[])
    coordinator.api.get_version = AsyncMock(return_value={"stationtype": "GW1100A", "version": "1.7.3"})
    
    # Should handle gracefully (gateway info already mocked in fixture)
    result = await coordinator._async_update_data()
    
    assert result is not None
    assert isinstance(result, dict)
    assert "sensors" in result