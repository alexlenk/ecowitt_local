"""Device localization preserves names, identifiers and user configuration."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.ecowitt_local import (
    _async_setup_device_registry,
    async_setup_entry,
)
from custom_components.ecowitt_local.api import AuthenticationError
from custom_components.ecowitt_local.api import ConnectionError as APIConnectionError
from custom_components.ecowitt_local.const import DOMAIN
from custom_components.ecowitt_local.coordinator import (
    EcowittLocalDataUpdateCoordinator,
)
from custom_components.ecowitt_local.device_compat import async_get_device_by_identifier
from custom_components.ecowitt_local.device_naming import (
    _TYPE_NAMES,
    device_name,
    device_name_kwargs,
    gateway_name_kwargs,
)


@pytest.mark.parametrize("language", ["en", "de"])
async def test_all_device_models_have_real_ha_translations(
    hass: HomeAssistant, mock_config_entry, language: str
):
    """Every known model resolves through HA's native device registry path."""
    hass.config.language = language
    mock_config_entry.add_to_hass(hass)
    translations = await async_get_translations(hass, language, "device", {DOMAIN})
    registry = dr.async_get(hass)

    for index, (sensor_type, english_type) in enumerate(_TYPE_NAMES.items()):
        hardware_id = f"MODEL{index}"
        info = {"sensor_type": sensor_type}
        kwargs = device_name_kwargs(hardware_id, info)
        key = f"component.{DOMAIN}.device.{kwargs['translation_key']}.name"
        assert key in translations, sensor_type
        registered = registry.async_get_or_create(
            config_entry_id=mock_config_entry.entry_id,
            identifiers={(DOMAIN, hardware_id)},
            **kwargs,
        )
        assert registered.name == device_name(hardware_id, info, hass)
        assert registered.identifiers == {(DOMAIN, hardware_id)}
        if language == "en":
            assert registered.name == f"Ecowitt {english_type} {hardware_id}"
        else:
            assert registered.name != f"Ecowitt {english_type} {hardware_id}"

    for hardware_id, info, expected in (
        ("GENERIC", {}, "Ecowitt Sensor GENERIC"),
        ("UNKNOWN", {"sensor_type": "WH99"}, "Ecowitt WH99 UNKNOWN"),
    ):
        device = registry.async_get_or_create(
            config_entry_id=mock_config_entry.entry_id,
            identifiers={(DOMAIN, hardware_id)},
            **device_name_kwargs(hardware_id, info),
        )
        assert device.name == expected

    live_model = {"sensor_type": "wh31", "live_model": "wn30/wn36"}
    expected = (
        "Ecowitt Temperatursensor PROBE"
        if language == "de"
        else "Ecowitt Temperature Sensor PROBE"
    )
    assert device_name("PROBE", live_model, hass) == expected


@pytest.mark.parametrize("language", ["en", "de"])
@pytest.mark.parametrize(
    "info",
    [
        {"sensor_type": "wh31", "live_title": " My Patio "},
        {
            "sensor_type": "wh31",
            "channel": "2",
            "raw_data": {"name": " My Patio "},
        },
    ],
)
async def test_gateway_custom_titles_are_not_translated(
    hass: HomeAssistant, mock_config_entry, language: str, info
):
    """A gateway's custom title bypasses translation in both languages."""
    hass.config.language = language
    mock_config_entry.add_to_hass(hass)
    await async_get_translations(hass, language, "device", {DOMAIN})
    kwargs = device_name_kwargs("A2", info)
    assert kwargs == {"name": "My Patio"}
    assert device_name("A2", info, hass) == "My Patio"
    registered = dr.async_get(hass).async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "A2")},
        **kwargs,
    )
    assert registered.name == "My Patio"


@pytest.mark.parametrize("language", ["en", "de"])
@pytest.mark.parametrize("existing_area", ["new", "assigned", "unassigned"])
async def test_localized_device_registration_preserves_existing_area_and_user_name(
    hass: HomeAssistant, mock_config_entry, language: str, existing_area: str
):
    """Only new outdoor devices get a localized suggested area."""
    hass.config.language = language
    mock_config_entry.add_to_hass(hass)
    await async_get_translations(hass, language, "device", {DOMAIN})
    devices = dr.async_get(hass)
    areas = ar.async_get(hass)
    previous_area = areas.async_create("Mein Garten")
    previous_device_id = None
    if existing_area != "new":
        previous = devices.async_get_or_create(
            config_entry_id=mock_config_entry.entry_id,
            identifiers={(DOMAIN, "D8174")},
            name="Legacy name",
        )
        previous_device_id = previous.id
        devices.async_update_device(
            previous.id,
            name_by_user="Eigener Gerätename",
            area_id=previous_area.id if existing_area == "assigned" else None,
        )
    gateway_info = {
        "gateway_id": "GW1100A",
        "host": "192.168.1.100",
        "model": "GW1100A",
    }
    mapper = Mock()
    mapper.get_all_hardware_ids.return_value = ["D8174"]
    mapper.get_sensor_info.return_value = {"sensor_type": "wh51"}
    coordinator = SimpleNamespace(gateway_info=gateway_info, sensor_mapper=mapper)
    await _async_setup_device_registry(hass, mock_config_entry, coordinator)

    device = async_get_device_by_identifier(devices, (DOMAIN, "D8174"))
    assert device is not None
    assert device.name == (
        "Ecowitt Bodenfeuchtesensor D8174"
        if language == "de"
        else "Ecowitt Soil Moisture Sensor D8174"
    )
    if existing_area == "new":
        area = areas.async_get_area(device.area_id)
        assert area is not None
        assert area.name == ("Außenbereich" if language == "de" else "Outdoor")
    else:
        assert device.id == previous_device_id
        assert device.name_by_user == "Eigener Gerätename"
        assert device.area_id == (
            previous_area.id if existing_area == "assigned" else None
        )
    gateway = async_get_device_by_identifier(devices, (DOMAIN, "GW1100A"))
    assert gateway is not None
    assert gateway.name == (
        "Ecowitt-Gateway 192.168.1.100"
        if language == "de"
        else "Ecowitt Gateway 192.168.1.100"
    )
    assert gateway_name_kwargs(gateway_info)["translation_placeholders"] == {
        "host": "192.168.1.100"
    }


async def test_gateway_title_reset_restores_german_name_without_changing_identity(
    hass: HomeAssistant, mock_config_entry, mock_ecowitt_api
):
    """Gateway title changes never reset defaults to English or erase user names."""
    hass.config.language = "de"
    mock_config_entry.add_to_hass(hass)
    await async_get_translations(hass, "de", "device", {DOMAIN})
    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        coordinator = EcowittLocalDataUpdateCoordinator(hass, mock_config_entry)
    # Real integration setup supplies HA's current config-entry context.
    coordinator.config_entry = mock_config_entry
    coordinator.sensor_mapper.update_mapping(
        [
            {
                "id": "A2",
                "img": "wh31",
                "type": "7",
                "name": "Temp & Humidity CH2",
                "signal": "4",
                "batt": "4",
            }
        ]
    )
    info = coordinator.sensor_mapper.get_sensor_info("A2")
    assert info is not None
    devices = dr.async_get(hass)
    initial = devices.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "A2")},
        **device_name_kwargs("A2", info),
    )
    devices.async_update_device(initial.id, name_by_user="Mein Messgerät")
    entities = er.async_get(hass)
    entity = entities.async_get_or_create(
        "sensor",
        DOMAIN,
        "ecowitt_local_A2_temp2f",
        suggested_object_id="ecowitt_temperature_a2",
        config_entry=mock_config_entry,
        device_id=initial.id,
    )
    entities.async_update_entity(entity.entity_id, name="Meine Temperatur")
    base = {"channel": "2", "temp": "21.5", "humidity": "50"}
    for title in ("My Patio", "My Shed", ""):
        coordinator._apply_live_titles({"ch_aisle": [{**base, "name": title}]})
        device = devices.async_get(initial.id)
        assert device is not None
        assert device.name == (
            title or "Ecowitt Temperatur-/Luftfeuchtigkeitssensor A2"
        )
        assert device.name_by_user == "Mein Messgerät"
        assert device.identifiers == {(DOMAIN, "A2")}
        current_entity = entities.async_get(entity.entity_id)
        assert current_entity is not None
        assert current_entity.unique_id == "ecowitt_local_A2_temp2f"
        assert current_entity.device_id == initial.id
        assert current_entity.name == "Meine Temperatur"
    await coordinator.async_shutdown()


@pytest.mark.parametrize(
    ("phase", "source_error", "exception_type", "key", "message"),
    [
        (
            "update",
            AuthenticationError,
            ConfigEntryAuthFailed,
            "authentication_failed",
            "Authentication failed: detail",
        ),
        (
            "update",
            APIConnectionError,
            UpdateFailed,
            "communication_failed",
            "Error communicating with gateway: detail",
        ),
        (
            "update",
            ValueError,
            UpdateFailed,
            "unexpected_error",
            "Unexpected error: detail",
        ),
        (
            "setup",
            AuthenticationError,
            ConfigEntryAuthFailed,
            "authentication_failed",
            "Authentication failed: detail",
        ),
        (
            "setup",
            APIConnectionError,
            ConfigEntryNotReady,
            "cannot_connect",
            "Cannot connect to gateway: detail",
        ),
        (
            "setup",
            ValueError,
            ConfigEntryNotReady,
            "setup_failed",
            "Setup failed: detail",
        ),
    ],
)
async def test_coordinator_errors_keep_english_messages_and_add_translation_metadata(
    hass: HomeAssistant,
    mock_config_entry,
    mock_ecowitt_api,
    phase,
    source_error,
    exception_type,
    key,
    message,
):
    """Localizing setup/update errors preserves exception classes and diagnostics."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
        return_value=mock_ecowitt_api,
    ):
        coordinator = EcowittLocalDataUpdateCoordinator(hass, mock_config_entry)
    coordinator._update_sensor_mapping_if_needed = AsyncMock()
    if phase == "setup":
        mock_ecowitt_api.test_connection.side_effect = source_error("detail")
        operation = coordinator.async_setup
    else:
        mock_ecowitt_api.get_live_data.side_effect = source_error("detail")
        operation = coordinator._async_update_data
    with pytest.raises(exception_type) as raised:
        await operation()
    assert str(raised.value) == message
    assert raised.value.translation_domain == DOMAIN
    assert raised.value.translation_key == key
    assert raised.value.translation_placeholders == {"error": "detail"}
    await coordinator.async_shutdown()


async def test_coordinator_setup_wrapper_keeps_error_metadata(
    hass: HomeAssistant, mock_config_entry
):
    """The outer setup error remains retryable and exposes localized metadata."""
    mock_config_entry.add_to_hass(hass)
    coordinator = Mock()
    coordinator.async_setup = AsyncMock(side_effect=ValueError("detail"))
    with patch(
        "custom_components.ecowitt_local.EcowittLocalDataUpdateCoordinator",
        return_value=coordinator,
    ):
        with pytest.raises(ConfigEntryNotReady) as raised:
            await async_setup_entry(hass, mock_config_entry)
    assert str(raised.value) == "Failed to setup coordinator: detail"
    assert raised.value.translation_domain == DOMAIN
    assert raised.value.translation_key == "setup_coordinator_failed"
    assert raised.value.translation_placeholders == {"error": "detail"}
