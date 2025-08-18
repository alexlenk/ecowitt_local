"""Test the Ecowitt Local coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.ecowitt_local.api import AuthenticationError, ConnectionError as APIConnectionError
from custom_components.ecowitt_local.coordinator import EcowittLocalDataUpdateCoordinator


@pytest.fixture
def coordinator(hass, mock_config_entry, mock_ecowitt_api):
    """Create a coordinator for testing."""
    coordinator = EcowittLocalDataUpdateCoordinator(hass, mock_config_entry)
    # Replace the API with our mock
    coordinator.api = mock_ecowitt_api
    return coordinator


@pytest.mark.asyncio
async def test_coordinator_auth_error_handling(coordinator):
    """Test coordinator handling authentication errors."""
    coordinator.api.get_live_data = AsyncMock(side_effect=AuthenticationError("Auth failed"))
    
    with pytest.raises(ConfigEntryAuthFailed, match="Authentication failed"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_connection_error_handling(coordinator):
    """Test coordinator handling connection errors.""" 
    coordinator.api.get_live_data = AsyncMock(side_effect=APIConnectionError("Connection failed"))
    
    with pytest.raises(UpdateFailed, match="Error communicating with gateway"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_unexpected_error_handling(coordinator):
    """Test coordinator handling unexpected errors."""
    coordinator.api.get_live_data = AsyncMock(side_effect=ValueError("Unexpected error"))
    
    with pytest.raises(UpdateFailed, match="Unexpected error"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_process_live_data_error(coordinator):
    """Test coordinator handling data processing errors."""
    # Mock successful API call but processing failure
    coordinator.api.get_live_data = AsyncMock(return_value={"invalid": "data"})
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
    
    # Test successful refresh
    await coordinator.async_refresh_sensor_mapping()
    
    # Verify mapping was updated
    assert coordinator.sensor_mapper.get_hardware_id("soilmoisture2") == "D8174"


@pytest.mark.asyncio
async def test_coordinator_sensor_mapping_refresh_error(coordinator):
    """Test sensor mapping refresh error handling."""
    coordinator.api.get_all_sensor_mappings = AsyncMock(side_effect=APIConnectionError("Connection failed"))
    
    # Should not raise exception, but log error
    await coordinator.async_refresh_sensor_mapping()
    
    # Mapping should remain unchanged
    assert len(coordinator.sensor_mapper.get_all_hardware_ids()) == 0


@pytest.mark.asyncio
async def test_coordinator_gateway_info_processing(coordinator):
    """Test gateway info processing."""
    mock_version_info = {
        "stationtype": "GW1100A",
        "version": "1.7.3"
    }
    
    coordinator.api.get_version = AsyncMock(return_value=mock_version_info)
    
    await coordinator.async_refresh_gateway_info()
    
    assert coordinator.gateway_info["stationtype"] == "GW1100A"
    assert coordinator.gateway_info["version"] == "1.7.3"


@pytest.mark.asyncio
async def test_coordinator_gateway_info_error(coordinator):
    """Test gateway info processing with error."""
    coordinator.api.get_version = AsyncMock(side_effect=APIConnectionError("Connection failed"))
    
    # Should not raise exception
    await coordinator.async_refresh_gateway_info()
    
    # Gateway info should remain empty or unchanged
    assert "stationtype" not in coordinator.gateway_info or coordinator.gateway_info.get("stationtype") is None


@pytest.mark.asyncio
async def test_coordinator_data_processing_with_additional_keys(coordinator):
    """Test data processing with additional data keys."""
    mock_live_data = {
        "common_list": [{"id": "tempf", "val": "72.5"}],
        "wh25": [{"intemp": "28.9", "unit": "C"}],
        "ch_soil": [{"channel": "1", "humidity": "50%"}]
    }
    
    coordinator.api.get_live_data = AsyncMock(return_value=mock_live_data)
    
    # Should process successfully and log additional keys
    result = await coordinator._async_update_data()
    
    assert result is not None
    assert "tempf" in result


@pytest.mark.asyncio
async def test_coordinator_empty_common_list_handling(coordinator):
    """Test coordinator handling empty common_list."""
    mock_live_data = {
        "common_list": [],
        "wh25": [{"intemp": "28.9", "unit": "C"}]
    }
    
    coordinator.api.get_live_data = AsyncMock(return_value=mock_live_data)
    
    # Should handle gracefully
    result = await coordinator._async_update_data()
    
    assert result is not None
    assert isinstance(result, dict)