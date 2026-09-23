"""Tests for the via_device -> via_device_id HA core compatibility helper."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from custom_components.ecowitt_local.const import DOMAIN
from custom_components.ecowitt_local.device_compat import (
    async_get_device_by_identifier,
    via_device_kwargs,
)


class DeprecatedDevicesView:
    """Reproduces HA core's `_DeprecatedDeviceRegistryItemsView` semantics.

    Only `__iter__`/`__len__`/`__contains__`/`__getitem__` are real; any other
    attribute access (e.g. `.get_entry`, `.values()`) raises, matching the
    real view's `__getattr__` reporting a deprecation warning for those. A
    plain `MagicMock` can't stand in for this — it resolves any attribute
    name and would let a regression back into `.get_entry()`/`.values()`
    pass silently.
    """

    def __init__(self, devices):
        self._devices = devices

    def __iter__(self):
        return iter(self._devices)

    def __len__(self):
        return len(self._devices)

    def __contains__(self, key):
        return key in self._devices

    def __getitem__(self, key):
        return self._devices[key]

    def __getattr__(self, name):
        raise AttributeError(
            f"deprecated: device_registry.devices.{name} is not supported"
        )


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
    gateway_device = SimpleNamespace(
        id="gateway-device-id", identifiers={(DOMAIN, "GW1100A")}
    )
    registry.devices = DeprecatedDevicesView([gateway_device])

    with patch(
        "custom_components.ecowitt_local.device_compat.dr.async_get",
        return_value=registry,
    ):
        result = via_device_kwargs(MagicMock(), "GW1100A")

    assert result == {"via_device_id": "gateway-device-id"}


def test_via_device_kwargs_new_ha_device_not_yet_registered():
    """New HA cores with the gateway device not yet registered omit via_device*."""

    def new_async_get_or_create(*, config_entry_id, via_device_id=None, **kwargs):
        pass

    registry = MagicMock()
    registry.async_get_or_create = new_async_get_or_create
    registry.devices = DeprecatedDevicesView([])

    with patch(
        "custom_components.ecowitt_local.device_compat.dr.async_get",
        return_value=registry,
    ):
        result = via_device_kwargs(MagicMock(), "GW1100A")

    assert result == {}


def test_async_get_device_by_identifier_iterates_without_deprecated_access():
    """Looks up a device by iterating, never touching a deprecated attribute."""
    other_device = SimpleNamespace(
        id="other-device-id", identifiers={(DOMAIN, "OTHER")}
    )
    gateway_device = SimpleNamespace(
        id="gateway-device-id", identifiers={(DOMAIN, "GW1100A")}
    )
    registry = SimpleNamespace(
        devices=DeprecatedDevicesView([other_device, gateway_device])
    )

    result = async_get_device_by_identifier(registry, (DOMAIN, "GW1100A"))

    assert result is gateway_device


def test_async_get_device_by_identifier_not_found():
    """Returns None when no registered device matches the identifier."""
    registry = SimpleNamespace(devices=DeprecatedDevicesView([]))

    result = async_get_device_by_identifier(registry, (DOMAIN, "GW1100A"))

    assert result is None


def test_async_get_device_by_identifier_legacy_dict_like_devices():
    """Pre-2026.9 HA: `.devices` is a plain dict keyed by device id, so
    iterating it yields id strings rather than entries directly."""
    gateway_device = SimpleNamespace(
        id="gateway-device-id", identifiers={(DOMAIN, "GW1100A")}
    )
    registry = SimpleNamespace(devices={"gateway-device-id": gateway_device})

    result = async_get_device_by_identifier(registry, (DOMAIN, "GW1100A"))

    assert result is gateway_device
