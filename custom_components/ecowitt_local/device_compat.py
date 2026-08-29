"""Compatibility helper for the HA core via_device -> via_device_id migration."""

from __future__ import annotations

import inspect
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN


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
        gateway_device = device_registry.async_get_device(
            identifiers={(DOMAIN, gateway_id)}
        )
        return {"via_device_id": gateway_device.id} if gateway_device else {}
    return {"via_device": (DOMAIN, gateway_id)}
