"""Config flow for Ecowitt Local integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .api import EcowittLocalAPI, AuthenticationError, ConnectionError as APIConnectionError
from .const import (
    DOMAIN,
    CONF_SCAN_INTERVAL,
    CONF_MAPPING_INTERVAL,
    CONF_INCLUDE_INACTIVE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MAPPING_INTERVAL,
    DEFAULT_INCLUDE_INACTIVE,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_AUTH,
    ERROR_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Optional(CONF_PASSWORD, default=""): str,
})

STEP_OPTIONS_DATA_SCHEMA = vol.Schema({
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
        int, vol.Range(min=30, max=300)
    ),
    vol.Optional(CONF_MAPPING_INTERVAL, default=DEFAULT_MAPPING_INTERVAL): vol.All(
        int, vol.Range(min=300, max=3600)
    ),
    vol.Optional(CONF_INCLUDE_INACTIVE, default=DEFAULT_INCLUDE_INACTIVE): bool,
})


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    host = data[CONF_HOST].strip()
    password = data.get(CONF_PASSWORD, "")

    api = EcowittLocalAPI(host, password)
    
    try:
        # Test connection and authentication
        await api.test_connection()
        
        # Get basic info to validate the device
        version_info = await api.get_version()
        
        # Extract gateway information
        gateway_id = version_info.get("stationtype", "unknown")
        model = version_info.get("stationtype", "Unknown")
        firmware_version = version_info.get("version", "Unknown")
        
        return {
            "title": f"Ecowitt Gateway ({host})",
            "gateway_id": gateway_id,
            "model": model,
            "firmware_version": firmware_version,
            "host": host,
        }
        
    except AuthenticationError:
        raise InvalidAuth
    except APIConnectionError:
        raise CannotConnect
    except Exception as err:
        _LOGGER.exception("Unexpected error validating input: %s", err)
        raise CannotConnect
    finally:
        await api.close()


@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for Ecowitt Local."""

    VERSION = 1
    MINOR_VERSION = 2
    
    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self._discovered_info: Optional[Dict[str, Any]] = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Optional[Dict[str, str]] = None
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors = {"base": ERROR_CANNOT_CONNECT}
            except InvalidAuth:
                errors = {"base": ERROR_INVALID_AUTH}
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors = {"base": ERROR_UNKNOWN}
            else:
                # Check if already configured
                await self.async_set_unique_id(f"{info['gateway_id']}_{info['host']}")
                self._abort_if_unique_id_configured()
                
                # Store the validated info
                if self._discovered_info is None:
                    self._discovered_info = {}
                self._discovered_info.update(user_input)
                self._discovered_info.update(info)
                
                # Proceed to options step
                return await self.async_step_options()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "host_example": "192.168.1.100",
            },
        )

    async def async_step_options(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the options step."""
        if user_input is not None:
            # Combine base config with options
            if self._discovered_info is None:
                self._discovered_info = {}
            final_data = {}
            final_data.update(self._discovered_info)
            final_data.update(user_input)
            
            return self.async_create_entry(
                title=self._discovered_info.get("title", "Ecowitt Gateway"),
                data=final_data,
            )

        return self.async_show_form(
            step_id="options",
            data_schema=STEP_OPTIONS_DATA_SCHEMA,
            description_placeholders={
                "scan_interval_desc": "How often to poll for live data (30-300 seconds)",
                "mapping_interval_desc": "How often to refresh sensor mappings (5-60 minutes)",
                "inactive_desc": "Include sensors that are currently offline",
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Ecowitt Local."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values
        current_scan_interval = self.config_entry.data.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        current_mapping_interval = self.config_entry.data.get(
            CONF_MAPPING_INTERVAL, DEFAULT_MAPPING_INTERVAL
        )
        current_include_inactive = self.config_entry.data.get(
            CONF_INCLUDE_INACTIVE, DEFAULT_INCLUDE_INACTIVE
        )

        options_schema = vol.Schema({
            vol.Optional(
                CONF_SCAN_INTERVAL, default=current_scan_interval
            ): vol.All(int, vol.Range(min=30, max=300)),
            vol.Optional(
                CONF_MAPPING_INTERVAL, default=current_mapping_interval
            ): vol.All(int, vol.Range(min=300, max=3600)),
            vol.Optional(
                CONF_INCLUDE_INACTIVE, default=current_include_inactive
            ): bool,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            description_placeholders={
                "scan_interval_desc": "How often to poll for live data (30-300 seconds)",
                "mapping_interval_desc": "How often to refresh sensor mappings (5-60 minutes)",
                "inactive_desc": "Include sensors that are currently offline",
            },
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""