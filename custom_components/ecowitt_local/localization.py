"""Localize display names without changing identifiers or device prefixes."""

from __future__ import annotations

import re
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_cached_translations

from .const import DOMAIN


def name_translation_spec(english_name: str) -> tuple[str, dict[str, str]]:
    """Return a stable name key and channel placeholder for an English name.

    Hardware identifiers never enter these keys. Channel variants share a
    translation while their existing English names remain the fallback.
    """
    channel = re.search(r"\bCH(\d+)\b", english_name)
    normalized = re.sub(r"\bCH\d+\b", "CH", english_name)
    key = re.sub(r"[^a-z0-9]+", "_", normalized.lower()).strip("_")
    placeholders = {"channel": channel.group(1)} if channel else {}
    return key, placeholders


def translated_text(
    hass: Optional[HomeAssistant],
    category: str,
    key: str,
    fallback: str,
    placeholders: Optional[dict[str, str]] = None,
) -> str:
    """Resolve a display string from HA's cache, retaining an English fallback."""
    if not isinstance(hass, HomeAssistant):
        return fallback
    translations = async_get_cached_translations(
        hass, hass.config.language, category, DOMAIN
    )
    template = translations.get(f"component.{DOMAIN}.{category}.{key}")
    if not isinstance(template, str):
        return fallback
    try:
        return template.format(**(placeholders or {}))
    except (KeyError, ValueError, IndexError):
        # A missing or malformed translation must never interrupt sensor updates.
        return fallback


class LocalizedEntityNameMixin:
    """Translate names while preserving the integration's existing prefix rules.

    Native entity name translation requires has_entity_name=True. Existing
    gateway entities deliberately have False and standalone names. Resolving
    the same HA translation catalog here preserves both styles and the exact
    English fallback, without adding a gateway prefix to existing entities.
    """

    _translation_platform: str
    _attr_name: Optional[str]
    _attr_translation_key: Optional[str] = None
    _attr_translation_placeholders: dict[str, str]

    @property
    def name(self) -> Optional[str]:
        """Return the translated display name in HA's configured system language."""
        fallback = self._attr_name
        if fallback is None or not self._attr_translation_key:
            return fallback
        return translated_text(
            getattr(self, "hass", None),
            "entity",
            f"{self._translation_platform}.{self._attr_translation_key}.name",
            fallback,
            self._attr_translation_placeholders,
        )
