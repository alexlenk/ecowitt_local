"""Tests for the via_device -> via_device_id HA core compatibility helper."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from custom_components.ecowitt_local.const import DOMAIN
from custom_components.ecowitt_local.device_compat import via_device_kwargs


def test_via_device_kwargs_hass_none():
    """Falls back to the legacy tuple kwarg when hass isn't available yet."""
    assert via_device_kwargs(None, "GW1100A") == {"via_device": (DOMAIN, "GW1100A")}


def test_via_device_kwargs_legacy_registry():
    """Old HA cores (no via_device_id param) still get the legacy tuple kwarg."""

    def legacy_async_get_or_create(*, config_entry_id, via_device=None, **kwargs):
        pass

    registry = MagicMock()
    registry.async_get_or_create = legacy_async_get_or_create

    with patch(
        "custom_components.ecowitt_local.device_compat.dr.async_get",
        return_value=registry,
    ):
        result = via_device_kwargs(MagicMock(), "GW1100A")

    assert result == {"via_device": (DOMAIN, "GW1100A")}


def test_via_device_kwargs_resolves_via_device_id():
    """New HA cores resolve the gateway device id instead of the legacy tuple."""

    def new_async_get_or_create(*, config_entry_id, via_device_id=None, **kwargs):
        pass

    registry = MagicMock()
    registry.async_get_or_create = new_async_get_or_create
    registry.async_get_device.return_value = SimpleNamespace(id="gateway-device-id")

    with patch(
        "custom_components.ecowitt_local.device_compat.dr.async_get",
        return_value=registry,
    ):
        result = via_device_kwargs(MagicMock(), "GW1100A")

    assert result == {"via_device_id": "gateway-device-id"}
    registry.async_get_device.assert_called_once_with(identifiers={(DOMAIN, "GW1100A")})


def test_via_device_kwargs_new_ha_device_not_yet_registered():
    """New HA cores with the gateway device not yet registered omit via_device*."""

    def new_async_get_or_create(*, config_entry_id, via_device_id=None, **kwargs):
        pass

    registry = MagicMock()
    registry.async_get_or_create = new_async_get_or_create
    registry.async_get_device.return_value = None

    with patch(
        "custom_components.ecowitt_local.device_compat.dr.async_get",
        return_value=registry,
    ):
        result = via_device_kwargs(MagicMock(), "GW1100A")

    assert result == {}
