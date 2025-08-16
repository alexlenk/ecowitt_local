"""Ecowitt Local API client for gateway communication."""
from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


class EcowittLocalAPIError(Exception):
    """Base exception for Ecowitt Local API errors."""


class AuthenticationError(EcowittLocalAPIError):
    """Authentication failed error."""


class ConnectionError(EcowittLocalAPIError):
    """Connection error."""


class DataError(EcowittLocalAPIError):
    """Data validation error."""


class EcowittLocalAPI:
    """Client for Ecowitt local web interface.
    
    This class handles authentication and data retrieval from
    Ecowitt weather station local web interface.
    
    Args:
        host: IP address or hostname of Ecowitt device
        password: Optional password for authentication
        session: Optional aiohttp session
        
    Raises:
        AuthenticationError: Invalid credentials
        ConnectionError: Cannot reach device
        DataError: Invalid response data
    """

    def __init__(
        self,
        host: str,
        password: str = "",
        session: Optional[ClientSession] = None,
    ) -> None:
        """Initialize the API client."""
        self._host = host.strip()
        self._password = password
        self._session = session
        self._close_session = False
        self._authenticated = False
        self._base_url = f"http://{self._host}"
        
        if self._session is None:
            self._session = ClientSession(
                timeout=ClientTimeout(total=DEFAULT_TIMEOUT),
                connector=aiohttp.TCPConnector(limit=10),
            )
            self._close_session = True

    async def close(self) -> None:
        """Close the session."""
        if self._close_session and self._session:
            await self._session.close()

    async def __aenter__(self) -> EcowittLocalAPI:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def authenticate(self) -> bool:
        """Authenticate with the Ecowitt gateway.
        
        Returns:
            True if authentication successful
            
        Raises:
            AuthenticationError: Invalid credentials
            ConnectionError: Cannot reach device
        """
        if not self._password:
            # No password required
            self._authenticated = True
            return True

        try:
            # Encode password in base64 as required by Ecowitt API
            encoded_password = base64.b64encode(self._password.encode()).decode()
            
            data = {"pwd": encoded_password}
            
            async with self._session.post(
                urljoin(self._base_url, "/set_login_info"),
                data=data,
            ) as response:
                if response.status == 200:
                    self._authenticated = True
                    _LOGGER.debug("Authentication successful")
                    return True
                elif response.status in (401, 403):
                    raise AuthenticationError("Invalid password")
                else:
                    raise ConnectionError(f"Authentication failed: HTTP {response.status}")
                    
        except asyncio.TimeoutError as err:
            raise ConnectionError("Timeout during authentication") from err
        except ClientError as err:
            raise ConnectionError(f"Network error during authentication: {err}") from err

    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make authenticated request to API endpoint.
        
        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            
        Returns:
            JSON response data
            
        Raises:
            AuthenticationError: Not authenticated or auth expired
            ConnectionError: Network error
            DataError: Invalid response data
        """
        url = urljoin(self._base_url, endpoint)
        
        try:
            async with self._session.get(url, params=params) as response:
                if response.status in (401, 403):
                    # Try to re-authenticate once
                    if not await self.authenticate():
                        raise AuthenticationError("Re-authentication failed")
                    
                    # Retry the request
                    async with self._session.get(url, params=params) as retry_response:
                        if retry_response.status in (401, 403):
                            raise AuthenticationError("Authentication expired")
                        response = retry_response
                
                if response.status != 200:
                    raise ConnectionError(f"HTTP {response.status}: {await response.text()}")
                
                try:
                    data = await response.json()
                    return data
                except Exception as err:
                    raise DataError(f"Invalid JSON response: {err}") from err
                    
        except asyncio.TimeoutError as err:
            raise ConnectionError("Request timeout") from err
        except ClientError as err:
            raise ConnectionError(f"Network error: {err}") from err

    async def get_live_data(self) -> Dict[str, Any]:
        """Get live sensor data from the gateway.
        
        Returns:
            Live sensor data including all current readings
            
        Raises:
            AuthenticationError: Not authenticated
            ConnectionError: Network error
            DataError: Invalid response data
        """
        if not self._authenticated and self._password:
            await self.authenticate()
            
        data = await self._make_request("/get_livedata_info")
        
        if "common_list" not in data:
            raise DataError("Invalid live data response: missing common_list")
            
        return data

    async def get_sensor_mapping(self, page: int = 1) -> List[Dict[str, Any]]:
        """Get sensor hardware ID mapping from the gateway.
        
        Args:
            page: Page number (1 or 2) for sensor mapping
            
        Returns:
            List of sensor mapping information with hardware IDs
            
        Raises:
            AuthenticationError: Not authenticated
            ConnectionError: Network error
            DataError: Invalid response data
        """
        if not self._authenticated and self._password:
            await self.authenticate()
            
        data = await self._make_request("/get_sensors_info", {"page": page})
        
        if "sensor" not in data:
            raise DataError("Invalid sensor mapping response: missing sensor data")
            
        return data["sensor"]

    async def get_all_sensor_mappings(self) -> List[Dict[str, Any]]:
        """Get all sensor mappings from both pages.
        
        Returns:
            Complete list of sensor mappings from both pages
        """
        mappings = []
        
        # Get mappings from both pages
        for page in [1, 2]:
            try:
                page_mappings = await self.get_sensor_mapping(page)
                mappings.extend(page_mappings)
            except DataError:
                # Page might not exist or be empty
                _LOGGER.debug("No sensor mappings found on page %d", page)
                continue
                
        return mappings

    async def get_version(self) -> Dict[str, Any]:
        """Get gateway version information.
        
        Returns:
            Version information including firmware version
            
        Raises:
            AuthenticationError: Not authenticated
            ConnectionError: Network error
            DataError: Invalid response data
        """
        if not self._authenticated and self._password:
            await self.authenticate()
            
        return await self._make_request("/get_version")

    async def get_units(self) -> Dict[str, Any]:
        """Get unit settings from the gateway.
        
        Returns:
            Unit configuration settings
            
        Raises:
            AuthenticationError: Not authenticated
            ConnectionError: Network error
            DataError: Invalid response data
        """
        if not self._authenticated and self._password:
            await self.authenticate()
            
        return await self._make_request("/get_units_info")

    async def test_connection(self) -> bool:
        """Test connection to the gateway.
        
        Returns:
            True if connection successful
            
        Raises:
            ConnectionError: Cannot reach device
        """
        try:
            await self.get_version()
            return True
        except AuthenticationError:
            # Authentication error means we can connect but credentials are wrong
            return True
        except ConnectionError:
            return False