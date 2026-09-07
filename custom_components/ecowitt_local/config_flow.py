"""Config flow for Ecowitt Local integration."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr

from .api import (
    AuthenticationError,
)
from .api import ConnectionError as APIConnectionError
from .api import EcowittLocalAPI, EcowittLocalAPIError
from .const import (
    CONF_INCLUDE_INACTIVE,
    CONF_MAPPING_INTERVAL,
    CONF_SCAN_INTERVAL,
    DEFAULT_INCLUDE_INACTIVE,
    DEFAULT_MAPPING_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_AUTH,
    ERROR_UNKNOWN,
)
from .coordinator import extract_model_from_firmware

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PASSWORD, default=""): str,
    }
)

STEP_OPTIONS_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            int, vol.Range(min=30, max=300)
        ),
        vol.Optional(CONF_MAPPING_INTERVAL, default=DEFAULT_MAPPING_INTERVAL): vol.All(
            int, vol.Range(min=300, max=3600)
        ),
        vol.Optional(CONF_INCLUDE_INACTIVE, default=DEFAULT_INCLUDE_INACTIVE): bool,
    }
)

# A previously-generated unique_id that is a normalized MAC address, used to
# tell a fresh MAC-based identifier apart from a legacy model+host one when
# reconfiguring (see ConfigFlow.async_step_reconfigure).
_MAC_UNIQUE_ID_RE = re.compile(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$")


def _looks_like_mac(unique_id: Optional[str]) -> bool:
    """Return True if unique_id is a normalized MAC address."""
    if not unique_id:
        return False
    return bool(_MAC_UNIQUE_ID_RE.match(unique_id))


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

        # Older firmware (and this integration's test fixtures) reports a
        # dedicated `stationtype` field. Gateways observed in the field
        # instead omit it entirely and embed the model in the `version`
        # string, e.g. "Version: GW1100A_V2.4.5".
        stationtype = version_info.get("stationtype")
        model = stationtype or extract_model_from_firmware(
            version_info.get("version", "")
        )
        firmware_version = version_info.get("version", "Unknown")

        # The gateway's MAC address is a stable hardware identifier that
        # survives IP address changes (e.g. a DHCP lease renewal), unlike
        # the host-based identifier used as a fallback below. Not all
        # gateway models are confirmed to support this endpoint, so a
        # failure here is not fatal for the whole flow.
        mac: Optional[str] = None
        try:
            network_info = await api.get_network_info()
            raw_mac = network_info.get("mac")
            if raw_mac:
                mac = dr.format_mac(raw_mac)
        except EcowittLocalAPIError:
            mac = None

        unique_id = mac if mac else f"{model}_{host}"

        return {
            "title": f"Ecowitt Gateway ({host})",
            "unique_id": unique_id,
            "model": model,
            "firmware_version": firmware_version,
            "host": host,
            "mac": mac,
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
                await self.async_set_unique_id(info["unique_id"])
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

    async def async_step_reconfigure(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle reconfiguration of an existing entry.

        Lets the user update the gateway's IP address (and password) —
        e.g. after a DHCP lease change — without removing and re-adding
        the integration. Devices, entities, and any automations that
        reference them are preserved.
        """
        errors: Optional[Dict[str, str]] = None
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors = {"base": ERROR_CANNOT_CONNECT}
            except InvalidAuth:
                errors = {"base": ERROR_INVALID_AUTH}
            except Exception:
                _LOGGER.exception("Unexpected exception during reconfigure")
                errors = {"base": ERROR_UNKNOWN}
            else:
                # The gateway's local HTTP API exposes a MAC address on
                # most models (via /get_network_info), used here as a
                # stable hardware identifier — but some older or
                # unconfirmed models may not support that endpoint, and
                # entries created before this identifier existed still
                # carry the legacy model+host unique_id. Only apply the
                # strict "same physical device" check when both the
                # existing and the newly computed unique_id are
                # MAC-based; otherwise this is either a gateway with no
                # stable identifier, or a legacy entry being upgraded to
                # one for the first time, and the unique_id is expected
                # to change.
                new_unique_id = info["unique_id"]
                if info.get("mac") and _looks_like_mac(reconfigure_entry.unique_id):
                    await self.async_set_unique_id(new_unique_id)
                    self._abort_if_unique_id_mismatch(reason="wrong_device")
                else:
                    for entry in self._async_current_entries():
                        if (
                            entry.entry_id != reconfigure_entry.entry_id
                            and entry.unique_id == new_unique_id
                        ):
                            return self.async_abort(reason="already_configured")

                self.hass.config_entries.async_update_entry(
                    reconfigure_entry,
                    unique_id=new_unique_id,
                    title=info["title"],
                    data={**reconfigure_entry.data, **user_input},
                )
                await self.hass.config_entries.async_reload(reconfigure_entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA,
                {
                    CONF_HOST: reconfigure_entry.data.get(CONF_HOST, ""),
                    CONF_PASSWORD: reconfigure_entry.data.get(CONF_PASSWORD, ""),
                },
            ),
            errors=errors,
            description_placeholders={
                "host_example": "192.168.1.100",
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Ecowitt Local."""

    def _get_config_entry(self) -> config_entries.ConfigEntry:
        """Look up the config entry this options flow is attached to.

        `OptionsFlow.config_entry` is no longer available on the base class —
        the entry must be resolved via `handler` (the config entry ID) instead.
        See issues #50, #42, #31 for the earlier read-only-property regression;
        newer Home Assistant versions removed the attribute entirely.
        """
        entry = self.hass.config_entries.async_get_entry(self.handler)
        assert entry is not None
        return entry

    def _get_option(self, key: str, default: Any) -> Any:
        """Read from options first, fall back to data, then default."""
        config_entry = self._get_config_entry()
        return config_entry.options.get(key, config_entry.data.get(key, default))

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values — check .options first, fall back to .data, then defaults
        current_scan_interval = self._get_option(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        current_mapping_interval = self._get_option(
            CONF_MAPPING_INTERVAL, DEFAULT_MAPPING_INTERVAL
        )
        current_include_inactive = self._get_option(
            CONF_INCLUDE_INACTIVE, DEFAULT_INCLUDE_INACTIVE
        )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=current_scan_interval
                ): vol.All(int, vol.Range(min=30, max=300)),
                vol.Optional(
                    CONF_MAPPING_INTERVAL, default=current_mapping_interval
                ): vol.All(int, vol.Range(min=300, max=3600)),
                vol.Optional(
                    CONF_INCLUDE_INACTIVE, default=current_include_inactive
                ): bool,
            }
        )

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
