"""Test the Ecowitt Local API client."""
from __future__ import annotations

import asyncio
import base64
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.ecowitt_local.api import (
    EcowittLocalAPI,
    AuthenticationError,
    ConnectionError,
    DataError,
)


@pytest.fixture
def api_client():
    """Create an API client for testing."""
    return EcowittLocalAPI("192.168.1.100", "test_password")


@pytest.mark.asyncio
async def test_init():
    """Test API client initialization."""
    api = EcowittLocalAPI("192.168.1.100", "test_password")
    
    assert api._host == "192.168.1.100"
    assert api._password == "test_password"
    assert api._base_url == "http://192.168.1.100"
    assert not api._authenticated
    
    await api.close()


@pytest.mark.asyncio
async def test_authenticate_success():
    """Test successful authentication."""
    api = EcowittLocalAPI("192.168.1.100", "test_password")
    
    with aioresponses() as m:
        m.post("http://192.168.1.100/set_login_info", status=200)
        
        result = await api.authenticate()
        
        assert result is True
        assert api._authenticated is True
        
        # Check that the request was made
        assert len(m.requests) > 0
        
    await api.close()


@pytest.mark.asyncio
async def test_authenticate_no_password():
    """Test authentication with no password."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    result = await api.authenticate()
    
    assert result is True
    assert api._authenticated is True
    
    await api.close()


@pytest.mark.asyncio
async def test_authenticate_invalid_credentials():
    """Test authentication with invalid credentials."""
    api = EcowittLocalAPI("192.168.1.100", "wrong_password")
    
    with aioresponses() as m:
        m.post("http://192.168.1.100/set_login_info", status=401)
        
        with pytest.raises(AuthenticationError):
            await api.authenticate()
    
    await api.close()


@pytest.mark.asyncio
async def test_authenticate_connection_error():
    """Test authentication with connection error."""
    api = EcowittLocalAPI("192.168.1.100", "test_password")
    
    with aioresponses() as m:
        m.post("http://192.168.1.100/set_login_info", exception=aiohttp.ClientError())
        
        with pytest.raises(ConnectionError):
            await api.authenticate()
    
    await api.close()


@pytest.mark.asyncio
async def test_get_live_data():
    """Test getting live data."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    mock_data = {
        "common_list": [
            {"id": "tempinf", "val": "72.5"},
            {"id": "humidity", "val": "45"},
        ]
    }
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_livedata_info", payload=mock_data)
        
        result = await api.get_live_data()
        
        assert result == mock_data
        assert "common_list" in result
    
    await api.close()


@pytest.mark.asyncio
async def test_get_live_data_invalid_response():
    """Test getting live data with invalid response."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_livedata_info", payload={"invalid": "data"})
        
        with pytest.raises(DataError):
            await api.get_live_data()
    
    await api.close()


@pytest.mark.asyncio
async def test_get_sensor_mapping():
    """Test getting sensor mapping."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    mock_data = {
        "sensor": [
            {"id": "D8174", "type": "WH51", "channel": "1"},
            {"id": "D8648", "type": "WH51", "channel": "2"},
        ]
    }
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_sensors_info?page=1", payload=mock_data)
        
        result = await api.get_sensor_mapping(1)
        
        assert result == mock_data["sensor"]
        assert len(result) == 2
    
    await api.close()


@pytest.mark.asyncio
async def test_get_all_sensor_mappings():
    """Test getting all sensor mappings."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    page1_data = {
        "sensor": [
            {"id": "D8174", "type": "WH51", "channel": "1"},
        ]
    }
    page2_data = {
        "sensor": [
            {"id": "D8648", "type": "WH51", "channel": "2"},
        ]
    }
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_sensors_info?page=1", payload=page1_data)
        m.get("http://192.168.1.100/get_sensors_info?page=2", payload=page2_data)
        
        result = await api.get_all_sensor_mappings()
        
        assert len(result) == 2
        assert result[0]["id"] == "D8174"
        assert result[1]["id"] == "D8648"
    
    await api.close()


@pytest.mark.asyncio
async def test_get_version():
    """Test getting version information."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    mock_data = {
        "stationtype": "GW1100A",
        "version": "1.7.3",
    }
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_version", payload=mock_data)
        
        result = await api.get_version()
        
        assert result == mock_data
        assert result["stationtype"] == "GW1100A"
    
    await api.close()


@pytest.mark.asyncio
async def test_test_connection():
    """Test connection test."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_version", payload={"version": "1.7.3"})
        
        result = await api.test_connection()
        
        assert result is True
    
    await api.close()


@pytest.mark.asyncio
async def test_test_connection_auth_error():
    """Test connection test with auth error."""
    api = EcowittLocalAPI("192.168.1.100", "wrong_password")
    
    with aioresponses() as m:
        # Mock the authentication call that will be triggered
        m.post("http://192.168.1.100/set_login_info", status=401)
        m.get("http://192.168.1.100/get_version", status=401)
        
        # Should return True because auth error means we can connect
        result = await api.test_connection()
        
        assert result is True
    
    await api.close()


@pytest.mark.asyncio
async def test_test_connection_failure():
    """Test connection test failure."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_version", exception=aiohttp.ClientError())
        
        result = await api.test_connection()
        
        assert result is False
    
    await api.close()


@pytest.mark.asyncio
async def test_context_manager():
    """Test API client as context manager."""
    async with EcowittLocalAPI("192.168.1.100", "") as api:
        assert api._session is not None
    
    # Session should be closed after context manager exit


@pytest.mark.asyncio
async def test_reauthentication_on_401():
    """Test automatic re-authentication on 401 error."""
    api = EcowittLocalAPI("192.168.1.100", "test_password")
    
    with aioresponses() as m:
        # Mock re-authentication and successful request
        m.post("http://192.168.1.100/set_login_info", status=200)
        m.get("http://192.168.1.100/get_livedata_info", 
              payload={"common_list": []})
        
        result = await api.get_live_data()
        
        assert result == {"common_list": []}
    
    await api.close()


@pytest.mark.asyncio
async def test_authenticate_session_not_initialized():
    """Test authentication with session not initialized."""
    api = EcowittLocalAPI("192.168.1.100", "test_password")
    
    # Close session to simulate uninitialized state
    await api.close()
    api._session = None
    
    with pytest.raises(ConnectionError, match="Session not initialized"):
        await api.authenticate()


@pytest.mark.asyncio
async def test_authenticate_timeout_error():
    """Test authentication with timeout error."""
    api = EcowittLocalAPI("192.168.1.100", "test_password")
    
    with aioresponses() as m:
        m.post("http://192.168.1.100/set_login_info", exception=asyncio.TimeoutError())
        
        with pytest.raises(ConnectionError, match="Timeout during authentication"):
            await api.authenticate()
    
    await api.close()


@pytest.mark.asyncio
async def test_make_request_session_not_initialized():
    """Test _make_request with session not initialized."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    # Close session to simulate uninitialized state
    await api.close()
    api._session = None
    
    with pytest.raises(ConnectionError, match="Session not initialized"):
        await api._make_request("/test")


@pytest.mark.asyncio
async def test_make_request_401_reauth_fails():
    """Test _make_request with 401 error and re-authentication failure."""
    api = EcowittLocalAPI("192.168.1.100", "test_password")
    
    # Mock authenticate to return False instead of raising exception
    async def mock_authenticate():
        return False
    
    api.authenticate = mock_authenticate
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/test", status=401)
        
        with pytest.raises(AuthenticationError, match="Re-authentication failed"):
            await api._make_request("/test")
    
    await api.close()


@pytest.mark.asyncio
async def test_make_request_401_reauth_succeeds_then_fails():
    """Test _make_request with 401, successful reauth, then 401 again."""
    api = EcowittLocalAPI("192.168.1.100", "test_password")
    
    with aioresponses() as m:
        # Mock successful re-authentication but still get 401 on retry
        m.post("http://192.168.1.100/set_login_info", status=200)
        m.get("http://192.168.1.100/test", status=401)
        m.get("http://192.168.1.100/test", status=401)  # Retry also fails
        
        with pytest.raises(AuthenticationError, match="Authentication expired"):
            await api._make_request("/test")
    
    await api.close()


@pytest.mark.asyncio
async def test_make_request_401_reauth_session_none():
    """Test _make_request with 401, successful reauth, but session becomes None."""
    api = EcowittLocalAPI("192.168.1.100", "test_password")
    
    # Mock the authenticate method to succeed but clear session
    async def mock_authenticate():
        api._session = None
        return True
    
    api.authenticate = mock_authenticate
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/test", status=401)
        
        with pytest.raises(ConnectionError, match="Session not initialized"):
            await api._make_request("/test")


@pytest.mark.asyncio
async def test_make_request_non_200_status():
    """Test _make_request with non-200 HTTP status."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/test", status=500, body="Server Error")
        
        with pytest.raises(ConnectionError, match="HTTP 500"):
            await api._make_request("/test")
    
    await api.close()


@pytest.mark.asyncio
async def test_make_request_invalid_json():
    """Test _make_request with invalid JSON response."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/test", status=200, body="invalid json")
        
        with pytest.raises(DataError, match="Invalid JSON response"):
            await api._make_request("/test")
    
    await api.close()


@pytest.mark.asyncio
async def test_make_request_timeout_error():
    """Test _make_request with timeout error."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/test", exception=asyncio.TimeoutError())
        
        with pytest.raises(ConnectionError, match="Request timeout"):
            await api._make_request("/test")
    
    await api.close()


@pytest.mark.asyncio
async def test_get_sensor_mapping_with_authentication():
    """Test get_sensor_mapping that triggers authentication."""
    api = EcowittLocalAPI("192.168.1.100", "test_password")
    
    mock_data = {
        "sensor": [
            {"id": "D8174", "type": "WH51", "channel": "1"},
        ]
    }
    
    with aioresponses() as m:
        m.post("http://192.168.1.100/set_login_info", status=200)
        m.get("http://192.168.1.100/get_sensors_info?page=1", payload=mock_data)
        
        result = await api.get_sensor_mapping(1)
        
        assert result == mock_data["sensor"]
        assert api._authenticated is True
    
    await api.close()


@pytest.mark.asyncio
async def test_get_sensor_mapping_array_response():
    """Test get_sensor_mapping with direct array response."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    mock_data = [
        {"id": "D8174", "type": "WH51", "channel": "1"},
        {"id": "D8648", "type": "WH51", "channel": "2"},
    ]
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_sensors_info?page=1", payload=mock_data)
        
        result = await api.get_sensor_mapping(1)
        
        assert result == mock_data
        assert len(result) == 2
    
    await api.close()


@pytest.mark.asyncio
async def test_get_sensor_mapping_invalid_response():
    """Test get_sensor_mapping with invalid response format."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_sensors_info?page=1", payload={"invalid": "format"})
        
        with pytest.raises(DataError, match="Invalid sensor mapping response"):
            await api.get_sensor_mapping(1)
    
    await api.close()


@pytest.mark.asyncio
async def test_get_all_sensor_mappings_with_data_error():
    """Test get_all_sensor_mappings handling DataError from a page."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    page1_data = {
        "sensor": [
            {"id": "D8174", "type": "WH51", "channel": "1"},
        ]
    }
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_sensors_info?page=1", payload=page1_data)
        m.get("http://192.168.1.100/get_sensors_info?page=2", payload={"invalid": "format"})
        
        # Should handle DataError on page 2 and continue
        result = await api.get_all_sensor_mappings()
        
        # Should only have page 1 data
        assert len(result) == 1
        assert result[0]["id"] == "D8174"
    
    await api.close()


@pytest.mark.asyncio
async def test_get_units():
    """Test getting unit settings."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    mock_data = {
        "temperature": "F",
        "pressure": "inHg",
        "wind": "mph",
        "rain": "in"
    }
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_units_info", payload=mock_data)
        
        result = await api.get_units()
        
        assert result == mock_data
        assert result["temperature"] == "F"
    
    await api.close()


@pytest.mark.asyncio
async def test_get_units_with_authentication():
    """Test get_units that triggers authentication."""
    api = EcowittLocalAPI("192.168.1.100", "test_password")
    
    mock_data = {
        "temperature": "C",
        "pressure": "hPa"
    }
    
    with aioresponses() as m:
        m.post("http://192.168.1.100/set_login_info", status=200)
        m.get("http://192.168.1.100/get_units_info", payload=mock_data)
        
        result = await api.get_units()
        
        assert result == mock_data
        assert api._authenticated is True
    
    await api.close()


@pytest.mark.asyncio
async def test_make_request_html_content_type_with_valid_json():
    """Test _make_request with HTML content-type but valid JSON content (GW3000 issue)."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    # Mock response with text/html content type but valid JSON body
    json_content = '{"stationtype": "GW3000", "version": "1.1.0"}'
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_version", 
              status=200,
              body=json_content,
              headers={'content-type': 'text/html; charset=utf-8'})
        
        result = await api._make_request("/get_version")
        
        assert result == {"stationtype": "GW3000", "version": "1.1.0"}
    
    await api.close()


@pytest.mark.asyncio
async def test_make_request_html_content_type_with_malformed_json():
    """Test _make_request with HTML content-type and malformed JSON."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    # Mock response with text/html content type and malformed JSON
    malformed_json = '{"stationtype": "GW3000", "version": malformed}'
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_version",
              status=200, 
              body=malformed_json,
              headers={'content-type': 'text/html'})
        
        with pytest.raises(DataError, match="Gateway returned malformed JSON"):
            await api._make_request("/get_version")
    
    await api.close()


@pytest.mark.asyncio
async def test_make_request_html_content_type_with_html_content():
    """Test _make_request with HTML content-type and actual HTML content."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    # Mock response with text/html content type and actual HTML
    html_content = '<html><body>Error page</body></html>'
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_version",
              status=200,
              body=html_content, 
              headers={'content-type': 'text/html'})
        
        with pytest.raises(DataError, match="Gateway returned non-JSON content"):
            await api._make_request("/get_version")
    
    await api.close()


@pytest.mark.asyncio
async def test_make_request_text_plain_content_type_with_json():
    """Test _make_request with text/plain content-type but valid JSON content."""
    api = EcowittLocalAPI("192.168.1.100", "")
    
    # Mock response with text/plain content type but valid JSON body
    json_content = '{"stationtype": "GW3000", "version": "1.1.0"}'
    
    with aioresponses() as m:
        m.get("http://192.168.1.100/get_version",
              status=200,
              body=json_content,
              headers={'content-type': 'text/plain'})
        
        result = await api._make_request("/get_version")
        
        assert result == {"stationtype": "GW3000", "version": "1.1.0"}
    
    await api.close()