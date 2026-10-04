"""Compatibility helpers for HA core device registry migrations."""

from __future__ import annotations

import inspect
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN


def async_get_device_by_identifier(
    device_registry: Any, identifier: tuple[str, str]
) -> Any:
    """Look up a device by identifier without the deprecated async_get_device().

    HA core is deprecating `async_get_device(identifiers=...)` because device
    identifiers are no longer unique across config entries. It's tempting to
    replace it with `device_registry.devices.get_entry(...)`, but that's a
    trap on HA 2026.9+: `device_registry.devices` there is a
    `_DeprecatedDeviceRegistryItemsView` whose `__getattr__` reports the
    *same* deprecation warning for any attribute access other than
    `__iter__`/`__len__`/`__contains__`/`__getitem__` — including
    `.get_entry`/`.values()`.

    Iterating it is the one access that's safe on every supported HA
    version, but what it yields differs by version:
    - HA 2026.9+: `.devices` is that deprecated view, and its `__iter__` is
      overridden to yield `DeviceEntry` objects directly.
    - Older HA (our minimum is 2026.1.0): `.devices` is a plain
      `dict[str, DeviceEntry]`-like container, so iterating it yields device
      *id strings* — `.devices[device_id]` resolves the entry, which is a
      plain (non-deprecated) dict lookup on these older versions.
    """
    for device in device_registry.devices:
        if isinstance(device, str):
            device = device_registry.devices[device]
        if identifier in device.identifiers:
            return device
    return None


def via_device_kwargs(hass: Optional[HomeAssistant], gateway_id: str) -> Dict[str, Any]:
    """Return the correct via-device kwarg for the installed HA core version.

    HA core is removing the `via_device` identifier-tuple parameter from
    `device_registry.async_get_or_create` (and the matching `DeviceInfo` field)
    in favor of a pre-resolved `via_device_id`. Passing the wrong one raises on
    the respective HA version, so detect support at runtime instead of picking
    one — older releases don't accept `via_device_id` at all, and the newest
    ones raise for `via_device`. Falls back to the legacy kwarg if `hass` isn't
    available yet (e.g. device_info accessed before the entity is added to hass).
    """
    if hass is None:
        return {"via_device": (DOMAIN, gateway_id)}

    device_registry = dr.async_get(hass)
    if (
        "via_device_id"
        in inspect.signature(device_registry.async_get_or_create).parameters
    ):
        gateway_device = async_get_device_by_identifier(
            device_registry, (DOMAIN, gateway_id)
        )
        return {"via_device_id": gateway_device.id} if gateway_device else {}
    return {"via_device": (DOMAIN, gateway_id)}


def device_belongs_to_entry(device: Any, entry_id: str) -> bool:
    """Return whether a device belongs to the given config entry.

    HA 2026.8 restricted a device to a single config entry, exposed as
    `DeviceEntry.config_entry_id`, and deprecated `DeviceEntry.config_entries`.
    From HA 2026.10 reading `config_entries` logs a deprecation warning for
    custom integrations, and it is removed in HA 2027.10. Older HA (our
    minimum is 2026.1.0) has no `config_entry_id`, so fall back to
    `config_entries` there, where reading it is not deprecated.
    """
    config_entry_id = getattr(device, "config_entry_id", None)
    if config_entry_id is not None:
        matches: bool = config_entry_id == entry_id
        return matches
    config_entries: set[str] = device.config_entries
    return entry_id in config_entries


def async_get_entry_id_for_device(hass: HomeAssistant, device_id: str) -> Optional[str]:
    """Return the id of the Ecowitt Local config entry that owns a device.

    HA 2026.9+ provides `dr.async_get_device_and_config_entry_for_domain()`,
    which reads `config_entry_id` and also resolves a device id stored before
    the HA 2026.8 device split (e.g. in an automation calling one of our
    services) to the split device owned by this domain. Older HA has no such
    helper; scan the device's config entries for one of ours there, where
    reading `DeviceEntry.config_entries` is not yet deprecated.
    """
    lookup = getattr(dr, "async_get_device_and_config_entry_for_domain", None)
    if lookup is not None:
        _device, config_entry = lookup(hass, device_id, domain=DOMAIN)
        if config_entry is None:
            return None
        owner_entry_id: str = config_entry.entry_id
        return owner_entry_id

    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    candidate_entry_ids: set[str] = device.config_entries
    for entry_id in candidate_entry_ids:
        config_entry = hass.config_entries.async_get_entry(entry_id)
        if config_entry is not None and config_entry.domain == DOMAIN:
            return entry_id
    return None
