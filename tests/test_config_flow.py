"""Test the Ecowitt Local config flow."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecowitt_local.api import EcowittLocalAPIError
from custom_components.ecowitt_local.config_flow import (
    CannotConnect,
    InvalidAuth,
    _looks_like_mac,
    validate_input,
)
from custom_components.ecowitt_local.const import CONF_HOST, CONF_PASSWORD, DOMAIN


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
    assert not hasattr(handler, "__dict__") or "config_entry" not in handler.__dict__


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
    assert (
        schema_keys["scan_interval"].default() == 120
    ), "Options form should show scan_interval=120 from .options, not 60 from .data"
    assert (
        schema_keys["include_inactive"].default() is True
    ), "Options form should show include_inactive=True from .options, not False from .data"


async def test_form_uses_mac_when_available(
    hass: HomeAssistant, mock_ecowitt_api
) -> None:
    """Test the unique_id is MAC-based when the gateway exposes /get_network_info."""
    mock_ecowitt_api.get_network_info.return_value = {"mac": "24:4C:AB:6C:37:D1"}

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.ecowitt_local.config_flow.EcowittLocalAPI",
            return_value=mock_ecowitt_api,
        ),
        patch(
            "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
            return_value=mock_ecowitt_api,
        ),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.100", CONF_PASSWORD: "test_password"},
        )
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                "scan_interval": 60,
                "mapping_interval": 600,
                "include_inactive": False,
            },
        )
        await hass.async_block_till_done()

    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["result"].unique_id == "24:4c:ab:6c:37:d1"


async def test_validate_input_parses_model_without_stationtype(
    hass: HomeAssistant, mock_ecowitt_api
) -> None:
    """Test validate_input falls back to parsing the model from the version string."""
    mock_ecowitt_api.get_version.return_value = {"version": "Version: GW1100A_V2.4.5"}

    with patch(
        "custom_components.ecowitt_local.config_flow.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        info = await validate_input(
            hass, {CONF_HOST: "192.168.1.100", CONF_PASSWORD: ""}
        )

    assert info["model"] == "GW1100A"


async def test_validate_input_network_info_unavailable(
    hass: HomeAssistant, mock_ecowitt_api
) -> None:
    """Test validate_input falls back to model_host when /get_network_info fails."""
    mock_ecowitt_api.get_network_info.side_effect = EcowittLocalAPIError("nope")

    with patch(
        "custom_components.ecowitt_local.config_flow.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        info = await validate_input(
            hass, {CONF_HOST: "192.168.1.100", CONF_PASSWORD: ""}
        )

    assert info["mac"] is None
    assert info["unique_id"] == "GW1100A_192.168.1.100"


async def test_reconfigure_flow_unknown_error(
    hass: HomeAssistant, mock_ecowitt_api
) -> None:
    """Test the reconfigure flow surfaces unexpected errors without changing the entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PASSWORD: "test_password"},
        entry_id="reconfigure_entry_id",
        unique_id="GW1100A_192.168.1.100",
        title="Ecowitt Gateway (192.168.1.100)",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    with patch(
        "custom_components.ecowitt_local.config_flow.validate_input",
        side_effect=ValueError("boom"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.200", CONF_PASSWORD: "test_password"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}
    assert entry.data[CONF_HOST] == "192.168.1.100"


def test_looks_like_mac_falsy_unique_id() -> None:
    """Test _looks_like_mac returns False for None/empty unique_id (no legacy entry yet)."""
    assert _looks_like_mac(None) is False
    assert _looks_like_mac("") is False


async def test_reconfigure_flow_updates_host(
    hass: HomeAssistant, mock_ecowitt_api
) -> None:
    """Test the reconfigure flow updates the host on the same entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PASSWORD: "test_password"},
        entry_id="reconfigure_entry_id",
        unique_id="GW1100A_192.168.1.100",
        title="Ecowitt Gateway (192.168.1.100)",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with (
        patch(
            "custom_components.ecowitt_local.config_flow.EcowittLocalAPI",
            return_value=mock_ecowitt_api,
        ),
        patch("custom_components.ecowitt_local.async_unload_entry", return_value=True),
        patch("custom_components.ecowitt_local.async_setup_entry", return_value=True),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.200", CONF_PASSWORD: "test_password"},
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "reconfigure_successful"

    updated_entry = hass.config_entries.async_get_entry("reconfigure_entry_id")
    assert updated_entry is not None
    assert updated_entry.data[CONF_HOST] == "192.168.1.200"
    assert updated_entry.unique_id == "GW1100A_192.168.1.200"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_reconfigure_flow_cannot_connect(
    hass: HomeAssistant, mock_ecowitt_api
) -> None:
    """Test the reconfigure flow shows an error and leaves the entry untouched."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PASSWORD: "test_password"},
        entry_id="reconfigure_entry_id",
        unique_id="GW1100A_192.168.1.100",
        title="Ecowitt Gateway (192.168.1.100)",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
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
    assert entry.data[CONF_HOST] == "192.168.1.100"


async def test_reconfigure_flow_invalid_auth(
    hass: HomeAssistant, mock_ecowitt_api
) -> None:
    """Test the reconfigure flow surfaces invalid-auth errors without changing the entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PASSWORD: "test_password"},
        entry_id="reconfigure_entry_id",
        unique_id="GW1100A_192.168.1.100",
        title="Ecowitt Gateway (192.168.1.100)",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

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
    assert entry.data[CONF_PASSWORD] == "test_password"


async def test_reconfigure_flow_conflicts_with_other_entry(
    hass: HomeAssistant, mock_ecowitt_api
) -> None:
    """Test reconfiguring toward a host already claimed by a different entry aborts."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PASSWORD: "test_password"},
        entry_id="reconfigure_entry_id",
        unique_id="GW1100A_192.168.1.100",
        title="Ecowitt Gateway (192.168.1.100)",
    )
    entry.add_to_hass(hass)

    other_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.200", CONF_PASSWORD: ""},
        entry_id="other_entry_id",
        unique_id="GW1100A_192.168.1.200",
        title="Ecowitt Gateway (192.168.1.200)",
    )
    other_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    with patch(
        "custom_components.ecowitt_local.config_flow.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.200", CONF_PASSWORD: "test_password"},
        )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == "192.168.1.100"


async def test_reconfigure_flow_upgrades_legacy_unique_id_to_mac(
    hass: HomeAssistant, mock_ecowitt_api
) -> None:
    """Test a legacy entry can adopt a MAC-based unique_id without a false wrong_device abort."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PASSWORD: "test_password"},
        entry_id="reconfigure_entry_id",
        unique_id="unknown_192.168.1.100",
        title="Ecowitt Gateway (192.168.1.100)",
    )
    entry.add_to_hass(hass)

    mock_ecowitt_api.get_network_info.return_value = {"mac": "24:4C:AB:6C:37:D1"}

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    with (
        patch(
            "custom_components.ecowitt_local.config_flow.EcowittLocalAPI",
            return_value=mock_ecowitt_api,
        ),
        patch("custom_components.ecowitt_local.async_unload_entry", return_value=True),
        patch("custom_components.ecowitt_local.async_setup_entry", return_value=True),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.100", CONF_PASSWORD: "test_password"},
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "reconfigure_successful"

    updated_entry = hass.config_entries.async_get_entry("reconfigure_entry_id")
    assert updated_entry is not None
    assert updated_entry.unique_id == "24:4c:ab:6c:37:d1"


async def test_reconfigure_flow_wrong_device_abort(
    hass: HomeAssistant, mock_ecowitt_api
) -> None:
    """Test reconfiguring toward a gateway with a different MAC aborts as wrong_device."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PASSWORD: "test_password"},
        entry_id="reconfigure_entry_id",
        unique_id="24:4c:ab:6c:37:d1",
        title="Ecowitt Gateway (192.168.1.100)",
    )
    entry.add_to_hass(hass)

    mock_ecowitt_api.get_network_info.return_value = {"mac": "AA:BB:CC:DD:EE:FF"}

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    with patch(
        "custom_components.ecowitt_local.config_flow.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.200", CONF_PASSWORD: "test_password"},
        )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "wrong_device"

    unchanged_entry = hass.config_entries.async_get_entry("reconfigure_entry_id")
    assert unchanged_entry is not None
    assert unchanged_entry.data[CONF_HOST] == "192.168.1.100"
    assert unchanged_entry.unique_id == "24:4c:ab:6c:37:d1"


async def test_reconfigure_flow_same_device_new_ip(
    hass: HomeAssistant, mock_ecowitt_api
) -> None:
    """Test reconfiguring to a new IP succeeds when the MAC still matches."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PASSWORD: "test_password"},
        entry_id="reconfigure_entry_id",
        unique_id="24:4c:ab:6c:37:d1",
        title="Ecowitt Gateway (192.168.1.100)",
    )
    entry.add_to_hass(hass)

    mock_ecowitt_api.get_network_info.return_value = {"mac": "24:4C:AB:6C:37:D1"}

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    with (
        patch(
            "custom_components.ecowitt_local.config_flow.EcowittLocalAPI",
            return_value=mock_ecowitt_api,
        ),
        patch("custom_components.ecowitt_local.async_unload_entry", return_value=True),
        patch("custom_components.ecowitt_local.async_setup_entry", return_value=True),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.200", CONF_PASSWORD: "test_password"},
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "reconfigure_successful"

    updated_entry = hass.config_entries.async_get_entry("reconfigure_entry_id")
    assert updated_entry is not None
    assert updated_entry.data[CONF_HOST] == "192.168.1.200"
    assert updated_entry.unique_id == "24:4c:ab:6c:37:d1"


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
