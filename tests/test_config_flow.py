"""Test the Ecowitt Local config flow."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ecowitt_local.config_flow import CannotConnect, InvalidAuth
from custom_components.ecowitt_local.const import DOMAIN, CONF_HOST, CONF_PASSWORD


async def test_form(hass: HomeAssistant, mock_ecowitt_api) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW1100A",
        "version": "1.7.3",
    }

    with patch(
        "custom_components.ecowitt_local.config_flow.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.100", CONF_PASSWORD: "test_password"},
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "options"


async def test_form_invalid_auth(hass: HomeAssistant, mock_ecowitt_api) -> None:
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_ecowitt_api.test_connection.side_effect = InvalidAuth

    with patch(
        "custom_components.ecowitt_local.config_flow.validate_input",
        side_effect=InvalidAuth,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.100", CONF_PASSWORD: "wrong_password"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass: HomeAssistant, mock_ecowitt_api) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ecowitt_local.config_flow.validate_input",
        side_effect=CannotConnect,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.999", CONF_PASSWORD: ""},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_options_flow(hass: HomeAssistant, mock_config_entry) -> None:
    """Test options flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "scan_interval": 30,
            "mapping_interval": 300,
            "include_inactive": True,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["scan_interval"] == 30
    assert result["data"]["mapping_interval"] == 300
    assert result["data"]["include_inactive"] is True


async def test_options_flow_no_config_entry_setter_error(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test that OptionsFlowHandler does not set config_entry in __init__.

    Regression test for HA 2025.12+ where config_entry is a read-only property
    on OptionsFlow and setting it explicitly raises AttributeError.
    See issues #50, #42, #31.
    """
    mock_config_entry.add_to_hass(hass)

    # This must not raise AttributeError: property 'config_entry' has no setter
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    # Verify config_entry is accessible via the HA-managed property
    from custom_components.ecowitt_local.config_flow import OptionsFlowHandler
    handler = OptionsFlowHandler()
    assert not hasattr(handler, '__dict__') or 'config_entry' not in handler.__dict__


async def test_options_flow_reads_from_options_not_data(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test that options flow shows values from .options, not .data, on second open.

    Regression test for issue #50/#31: after saving options once, the values
    live in config_entry.options. Reopening the form must show those saved
    values, not the original .data values.
    """
    mock_config_entry.add_to_hass(hass)

    # First open: save new values (scan_interval 60->120, include_inactive False->True)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "scan_interval": 120,
            "mapping_interval": 600,
            "include_inactive": True,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    # Values now live in config_entry.options
    assert mock_config_entry.options["scan_interval"] == 120
    assert mock_config_entry.options["include_inactive"] is True

    # Second open: form defaults must come from .options (120), not .data (60)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    schema_keys = {str(k): k for k in result["data_schema"].schema}
    assert schema_keys["scan_interval"].default() == 120, (
        "Options form should show scan_interval=120 from .options, not 60 from .data"
    )
    assert schema_keys["include_inactive"].default() is True, (
        "Options form should show include_inactive=True from .options, not False from .data"
    )


async def test_complete_flow(hass: HomeAssistant, mock_ecowitt_api) -> None:
    """Test complete configuration flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_ecowitt_api.test_connection.return_value = True
    mock_ecowitt_api.get_version.return_value = {
        "stationtype": "GW1100A",
        "version": "1.7.3",
    }

    with patch(
        "custom_components.ecowitt_local.config_flow.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        # User step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.100", CONF_PASSWORD: "test_password"},
        )

        # Options step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "scan_interval": 60,
                "mapping_interval": 600,
                "include_inactive": False,
            },
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Ecowitt Gateway (192.168.1.100)"
    assert result["data"][CONF_HOST] == "192.168.1.100"
    assert result["data"][CONF_PASSWORD] == "test_password"
    assert result["data"]["scan_interval"] == 60