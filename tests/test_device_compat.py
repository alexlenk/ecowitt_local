"""Tests for the HA core device registry compatibility helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from custom_components.ecowitt_local.const import DOMAIN
from custom_components.ecowitt_local.device_compat import (
    async_get_device_by_identifier,
    async_get_entry_id_for_device,
    device_belongs_to_entry,
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


class SingleEntryDevice:
    """A HA 2026.8+ `DeviceEntry`: reading `config_entries` is deprecated.

    The property raises here so a regression back to the deprecated read
    fails the test instead of passing silently.
    """

    def __init__(self, config_entry_id):
        self.config_entry_id = config_entry_id

    @property
    def config_entries(self):
        raise AssertionError("deprecated DeviceEntry.config_entries was read")


def test_device_belongs_to_entry_single_entry_device():
    """HA 2026.8+ devices are matched on config_entry_id alone."""
    device = SingleEntryDevice("entry-1")
    assert device_belongs_to_entry(device, "entry-1") is True
    assert device_belongs_to_entry(device, "entry-2") is False


def test_device_belongs_to_entry_legacy_device():
    """Older HA cores (no config_entry_id) fall back to config_entries."""
    device = SimpleNamespace(config_entries={"entry-1", "other-entry"})
    assert device_belongs_to_entry(device, "entry-1") is True
    assert device_belongs_to_entry(device, "entry-2") is False


def test_entry_id_for_device_uses_domain_lookup_helper():
    """HA 2026.9+ resolves the owning entry through the registry helper."""
    lookup = MagicMock(
        return_value=(SingleEntryDevice("entry-1"), SimpleNamespace(entry_id="entry-1"))
    )
    hass = MagicMock()
    with patch(
        "custom_components.ecowitt_local.device_compat.dr",
        SimpleNamespace(async_get_device_and_config_entry_for_domain=lookup),
    ):
        assert async_get_entry_id_for_device(hass, "device-1") == "entry-1"
    lookup.assert_called_once_with(hass, "device-1", domain=DOMAIN)


def test_entry_id_for_device_not_ours():
    """A device owned by no Ecowitt Local entry resolves to None."""
    lookup = MagicMock(return_value=(SingleEntryDevice("other-entry"), None))
    with patch(
        "custom_components.ecowitt_local.device_compat.dr",
        SimpleNamespace(async_get_device_and_config_entry_for_domain=lookup),
    ):
        assert async_get_entry_id_for_device(MagicMock(), "device-1") is None


def test_entry_id_for_device_legacy_core():
    """Older HA cores scan config_entries for the entry of our domain."""
    entries = {
        "other-entry": SimpleNamespace(domain="other_domain"),
        "entry-1": SimpleNamespace(domain=DOMAIN),
    }
    hass = MagicMock()
    hass.config_entries.async_get_entry.side_effect = entries.get
    registry = MagicMock()
    registry.async_get.side_effect = lambda device_id: (
        SimpleNamespace(config_entries=set(entries))
        if device_id == "device-1"
        else None
    )
    with patch(
        "custom_components.ecowitt_local.device_compat.dr",
        SimpleNamespace(async_get=lambda _hass: registry),
    ):
        assert async_get_entry_id_for_device(hass, "device-1") == "entry-1"
        assert async_get_entry_id_for_device(hass, "unknown-device") is None
