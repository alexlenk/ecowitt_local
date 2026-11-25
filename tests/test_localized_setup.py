"""End-to-end localization with real HA registries and a mocked Ecowitt gateway."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.ecowitt_local.const import DOMAIN
from custom_components.ecowitt_local.device_compat import async_get_device_by_identifier
from custom_components.ecowitt_local.localization import name_translation_spec
from tests.test_entity_naming import (
    _aisle,
    _entry,
    _friendly_name,
    _mapping,
    _sensor,
    _setup,
    _wh31,
)
from tests.test_localization import _catalog


@pytest.mark.parametrize("language", ["en", "de", "da", "fr", "it", "nl"])
async def test_names_localize_without_changing_identifiers_or_values(
    hass: HomeAssistant, mock_ecowitt_api, language
):
    """Full setup translates names, with English fallback for other locales."""
    hass.config.language = language
    mock_ecowitt_api.get_units.return_value = {"temperature": "0"}
    entry = _entry(hass)
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        [_wh31("D1E2F3", 2)],
        {"ch_aisle": [_aisle(2, "21.5")]},
    )
    catalog = _catalog(f"translations/{language if language != 'nl' else 'en'}.json")
    device_name = catalog["device"]["temperature_humidity_sensor"]["name"].format(
        hardware_id="D1E2F3"
    )
    device = async_get_device_by_identifier(dr.async_get(hass), (DOMAIN, "D1E2F3"))
    assert device is not None and device.name == device_name
    expected = {
        "sensor.ecowitt_temperature_d1e2f3": (
            "temp2f",
            "Temperature",
            "Temperatur",
            "21.5",
            "°C",
        ),
        "sensor.ecowitt_humidity_d1e2f3": (
            "humidity2",
            "Humidity",
            "Luftfeuchtigkeit",
            "55",
            "%",
        ),
        "sensor.ecowitt_temperature_humidity_battery_d1e2f3": (
            "batt2",
            "Battery",
            "Batterie",
            "100",
            "%",
        ),
        "sensor.ecowitt_signal_strength_d1e2f3": (
            "signal_D1E2F3",
            "Signal Strength",
            "Signalstärke",
            "100",
            "%",
        ),
        "sensor.ecowitt_signal_quality_d1e2f3": (
            "signal_quality_D1E2F3",
            "Signal Quality",
            "Signalqualität",
            "80",
            "%",
        ),
        "sensor.ecowitt_channel_d1e2f3": (
            "channel_D1E2F3",
            "Channel",
            "Kanal",
            "2",
            None,
        ),
    }
    registry = er.async_get(hass)
    for entity_id, (key, english, translated, value, unit) in expected.items():
        registered = registry.async_get(entity_id)
        assert registered is not None, entity_id
        assert registered.unique_id == f"{DOMAIN}_D1E2F3_{key}"
        assert registered.device_id == device.id
        assert registered.has_entity_name is True
        translation_key, placeholders = name_translation_spec(english)
        expected_name = catalog["entity"]["sensor"][translation_key]["name"].format(
            **placeholders
        )
        assert registered.original_name == expected_name
        assert _friendly_name(hass, entity_id) == f"{device_name} {expected_name}"
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == value, (entity_id, state)
        assert state.attributes.get("unit_of_measurement") == unit


async def test_german_upgrade_keeps_user_names_and_custom_entity_id(
    hass: HomeAssistant, mock_ecowitt_api
):
    """An upgrade/reload preserves user IDs, names and statistics-related attributes."""
    hass.config.language = "de"
    mock_ecowitt_api.get_units.return_value = {"temperature": "0"}
    entry = _entry(hass)
    devices = dr.async_get(hass)
    registry = er.async_get(hass)
    device = devices.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "D1E2F3")},
        name="Ecowitt Temperature/Humidity Sensor D1E2F3",
    )
    devices.async_update_device(device.id, name_by_user="Kühlraum")
    existing = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{DOMAIN}_D1E2F3_temp2f",
        suggested_object_id="freezer_probe",
        config_entry=entry,
        device_id=device.id,
        original_name="Temperature CH2",
    )
    registry.async_update_entity(existing.entity_id, name="Meine Temperatur")
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        [_wh31("D1E2F3", 2)],
        {"ch_aisle": [_aisle(2, "21.5")]},
    )
    upgraded = registry.async_get("sensor.freezer_probe")
    assert upgraded is not None and upgraded.id == existing.id
    assert upgraded.unique_id == existing.unique_id
    assert upgraded.device_id == existing.device_id
    assert upgraded.name == "Meine Temperatur"
    assert upgraded.original_name == "Temperatur"
    assert _friendly_name(hass, upgraded.entity_id) == "Meine Temperatur"
    assert registry.async_get("sensor.ecowitt_temperature_d1e2f3") is None
    assert devices.async_get(device.id).name_by_user == "Kühlraum"
    assert _friendly_name(hass, "sensor.ecowitt_humidity_d1e2f3") == (
        "Kühlraum Luftfeuchtigkeit"
    )
    state = hass.states.get(upgraded.entity_id)
    assert state is not None and state.state == "21.5"
    assert state.attributes["unit_of_measurement"] == "°C"
    assert state.attributes["state_class"] == "measurement"
    assert state.attributes["device_class"] == "temperature"
    registry_before_reload = {
        item.entity_id: (item.id, item.unique_id, item.device_id)
        for item in er.async_entries_for_config_entry(registry, entry.entry_id)
    }

    with (
        patch(
            "custom_components.ecowitt_local.coordinator.EcowittLocalAPI",
            return_value=mock_ecowitt_api,
        ),
        patch(
            "custom_components.ecowitt_local.api.EcowittLocalAPI",
            return_value=mock_ecowitt_api,
        ),
    ):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    registry_after_reload = {
        item.entity_id: (item.id, item.unique_id, item.device_id)
        for item in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    assert registry_after_reload == registry_before_reload
    assert not any(entity_id.endswith("_2") for entity_id in registry_after_reload)
    reloaded_state = hass.states.get(existing.entity_id)
    assert reloaded_state is not None
    assert reloaded_state.state == state.state
    for attr in ("unit_of_measurement", "state_class", "device_class", "friendly_name"):
        assert reloaded_state.attributes[attr] == state.attributes[attr]
    assert devices.async_get(device.id).name_by_user == "Kühlraum"
    assert registry.async_get(existing.entity_id).name == "Meine Temperatur"


async def test_german_gateway_title_remains_a_user_title(
    hass: HomeAssistant, mock_ecowitt_api
):
    """A gateway's custom title stays literal while its sensor names translate."""
    hass.config.language = "de"
    entry = _entry(hass)
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        [_wh31("A2", 2)],
        {"ch_aisle": [{**_aisle(2, "21.5"), "name": "Deep Freezer"}]},
    )
    device = async_get_device_by_identifier(dr.async_get(hass), (DOMAIN, "A2"))
    assert device is not None and device.name == "Deep Freezer"
    assert _friendly_name(hass, "sensor.ecowitt_temperature_a2") == (
        "Deep Freezer Temperatur"
    )
    assert _friendly_name(hass, "sensor.ecowitt_temperature_humidity_battery_a2") == (
        "Deep Freezer Batterie"
    )


async def test_gateway_and_unmapped_channel_keep_standalone_names(
    hass: HomeAssistant, mock_ecowitt_api
):
    """Gateway readings do not gain a prefix; unmapped channels stay distinct."""
    hass.config.language = "de"
    entry = _entry(hass)
    await _setup(hass, mock_ecowitt_api, entry, [], {})
    cases = [
        ("tempinf", "Indoor Temperature", "Innentemperatur"),
        ("temp2f", "Temperature CH2", "Temperatur Kanal 2"),
        ("temp16f", "Temperature CH16", "Temperatur Kanal 16"),
    ]
    for key, english, german in cases:
        sensor = _sensor({"sensor_key": key, "name": english, "state": 21.5}, None)
        sensor.hass = hass
        assert sensor.name == german
        assert sensor.has_entity_name is False
        assert sensor.native_value == 21.5
    gateway_id = hass.data[DOMAIN][entry.entry_id].gateway_info["gateway_id"]
    gateway = async_get_device_by_identifier(dr.async_get(hass), (DOMAIN, gateway_id))
    assert gateway is not None
    assert gateway.name == "Ecowitt-Gateway 192.168.1.100"


async def test_solar_names_follow_runtime_unit_changes_in_german(
    hass: HomeAssistant, mock_ecowitt_api
):
    """Live lux/radiation changes translate names while preserving the primary ID."""
    hass.config.language = "de"
    entry = _entry(hass)
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        [_mapping("W90", "wh90", 48, "WH90")],
        {"common_list": [{"id": "0x15", "val": "15000.0 Lux"}]},
    )
    registry = er.async_get(hass)
    primary_id = "sensor.ecowitt_solar_radiation_w90"
    primary = registry.async_get(primary_id)
    assert primary is not None
    assert primary.original_name == "Solare Beleuchtungsstärke"
    lux = hass.states.get(primary_id)
    assert lux is not None and lux.attributes["unit_of_measurement"] == "lx"
    derived_id = "sensor.ecowitt_solar_radiation_wm2_w90"
    derived = registry.async_get(derived_id)
    assert derived is not None and derived.original_name == "Solarstrahlung"
    derived_state = hass.states.get(derived_id)
    assert derived_state is not None
    assert derived_state.attributes["unit_of_measurement"] == "W/m²"

    mock_ecowitt_api.get_live_data.return_value = {
        "common_list": [{"id": "0x15", "val": "120.5 W/m2"}]
    }
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert registry.async_get(primary_id).id == primary.id
    assert registry.async_get(primary_id).original_name == "Solarstrahlung"
    radiation = hass.states.get(primary_id)
    assert radiation is not None
    assert radiation.attributes["unit_of_measurement"] == "W/m²"
    assert radiation.attributes["friendly_name"].endswith(" Solarstrahlung")
