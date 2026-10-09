"""Tests for gateway "Customize Title" names as device names."""

from __future__ import annotations

from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecowitt_local.const import DOMAIN
from custom_components.ecowitt_local.coordinator import _TITLE_BLOCKS
from custom_components.ecowitt_local.sensor_mapper import SensorMapper
from tests.test_entity_naming import (
    _entry,
    _friendly_name,
    _mapping,
    _set_gateway,
    _setup,
)


def _aisle(channel: int, name: str, temp: str = "27.8") -> Dict[str, Any]:
    """Return a ch_aisle item with a gateway title."""
    return {
        "channel": str(channel),
        "name": name,
        "battery": "0",
        "temp": temp,
        "unit": "C",
        "humidity": "None" if channel == 1 else "50%",
    }


_WN36 = _mapping("FD", "wh31", 6, "Temp & Humidity CH1")
_WN31 = _mapping("A2", "wh31", 7, "Temp & Humidity CH2")


def test_title_keys_belong_to_the_channel_family():
    """Each block's lookup key is one the mapper assigns to that sensor family."""
    families = {
        "ch_aisle": "wh31",
        "ch_soil": "wh51",
        "ch_temp": "wh34",
        "ch_leaf": "wh35",
        "ch_leak": "wh55",
        "ch_lds": "wh54",
        "ch_ec": "wh52",
    }
    assert set(families) == set(_TITLE_BLOCKS)
    mapper = SensorMapper()
    for block, sensor_type in families.items():
        key = _TITLE_BLOCKS[block].format(ch=2)
        assert key in mapper._generate_live_data_keys(sensor_type, "2"), block


def test_mapper_keeps_titles_across_mapping_refresh():
    """Titles are set on the sensor info and survive a get_sensors_info refresh."""
    mapper = SensorMapper()
    mapper.update_mapping([_WN36, _WN31])
    mapper.set_live_titles({"FD": "Jacuzzi Temp"})
    info = mapper.get_sensor_info("FD")
    assert info is not None and info["live_title"] == "Jacuzzi Temp"
    a2 = mapper.get_sensor_info("A2")
    assert a2 is not None and "live_title" not in a2

    mapper.update_mapping([_WN36, _WN31])
    info = mapper.get_sensor_info("FD")
    assert info is not None and info["live_title"] == "Jacuzzi Temp"

    mapper.set_live_titles({})
    info = mapper.get_sensor_info("FD")
    assert info is not None and "live_title" not in info


async def test_gateway_title_names_the_device(hass: HomeAssistant, mock_ecowitt_api):
    """The title from the live data becomes the device and entity name prefix."""
    entry = _entry(hass)
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        [_WN36, _WN31],
        {"ch_aisle": [_aisle(1, " Jacuzzi Temp "), _aisle(2, "", "22.5")]},
    )
    devices = dr.async_get(hass)
    titled = devices.async_get_device(identifiers={(DOMAIN, "FD")})
    untitled = devices.async_get_device(identifiers={(DOMAIN, "A2")})
    assert titled is not None and titled.name == "Jacuzzi Temp"
    assert untitled is not None
    assert untitled.name == "Ecowitt Temperature/Humidity Sensor A2"

    # Entity IDs are unchanged; friendly names follow the device.
    assert _friendly_name(hass, "sensor.ecowitt_temperature_fd") == (
        "Jacuzzi Temp Temperature"
    )
    assert _friendly_name(hass, "sensor.ecowitt_temperature_humidity_battery_fd") == (
        "Jacuzzi Temp Battery"
    )
    assert _friendly_name(hass, "sensor.ecowitt_temperature_a2") == (
        "Ecowitt Temperature/Humidity Sensor A2 Temperature"
    )


async def test_title_changes_follow_at_runtime(hass: HomeAssistant, mock_ecowitt_api):
    """Setting, changing and clearing a title renames the device; user names win."""
    entry = _entry(hass)
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        [_WN36, _WN31],
        {"ch_aisle": [_aisle(1, ""), _aisle(2, "", "22.5")]},
    )
    coordinator = hass.data[DOMAIN][entry.entry_id]
    devices = dr.async_get(hass)

    async def poll(name_ch1: str, name_ch2: str = "") -> None:
        _set_gateway(
            mock_ecowitt_api,
            [_WN36, _WN31],
            {"ch_aisle": [_aisle(1, name_ch1), _aisle(2, name_ch2, "22.5")]},
        )
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    def name_of(hardware_id: str) -> Any:
        device = devices.async_get_device(identifiers={(DOMAIN, hardware_id)})
        assert device is not None
        return device

    assert name_of("FD").name == "Ecowitt Temperature/Humidity Sensor FD"

    await poll("Jacuzzi Temp")
    assert name_of("FD").name == "Jacuzzi Temp"
    assert _friendly_name(hass, "sensor.ecowitt_temperature_fd") == (
        "Jacuzzi Temp Temperature"
    )

    await poll("Hot Tub")
    assert name_of("FD").name == "Hot Tub"

    await poll("")
    assert name_of("FD").name == "Ecowitt Temperature/Humidity Sensor FD"

    # A name set in Home Assistant is kept; the gateway title only updates the
    # default name underneath it.
    devices.async_update_device(name_of("A2").id, name_by_user="Living Room")
    await poll("", "Kitchen")
    a2 = name_of("A2")
    assert a2.name == "Kitchen" and a2.name_by_user == "Living Room"
    assert _friendly_name(hass, "sensor.ecowitt_temperature_a2") == (
        "Living Room Temperature"
    )


async def test_titles_without_a_known_sensor_are_ignored(
    hass: HomeAssistant, mock_ecowitt_api
):
    """Titles for unmapped channels or malformed items do not touch any device."""
    entry = _entry(hass)
    live = {
        "ch_aisle": [
            _aisle(2, "", "22.5"),
            _aisle(5, "Garage"),  # no sensor mapped on channel 5
            {"name": "No Channel"},
            "not-a-dict",
        ],
        "ch_soil": None,
    }
    await _setup(hass, mock_ecowitt_api, entry, [_WN31], live)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator._live_titles == {}
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "A2")})
    assert device is not None
    assert device.name == "Ecowitt Temperature/Humidity Sensor A2"
    assert er.async_get(hass).async_get("sensor.ecowitt_temperature_a2") is not None


async def test_title_for_device_not_yet_registered(
    hass: HomeAssistant, mock_ecowitt_api
):
    """A title for a sensor whose device does not exist yet is applied on creation."""
    entry = _entry(hass)
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        [_WN31],
        {"ch_aisle": [_aisle(2, "", "22.5")]},
    )
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # The WN36 is paired and titled while HA runs: its device is created by the
    # new entities, already with the title.
    _set_gateway(
        mock_ecowitt_api,
        [_WN36, _WN31],
        {"ch_aisle": [_aisle(1, "Jacuzzi Temp"), _aisle(2, "", "22.5")]},
    )
    await coordinator.async_refresh_mapping()
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "FD")})
    assert device is not None and device.name == "Jacuzzi Temp"


async def test_devices_of_other_entries_are_not_renamed(
    hass: HomeAssistant, mock_ecowitt_api
):
    """With two gateways, a title only renames this gateway's own device."""
    entry = _entry(hass)
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        [_WN31],
        {"ch_aisle": [_aisle(2, "", "22.5")]},
    )
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # A sensor with the same hardware ID is registered by another gateway only.
    other_entry = MockConfigEntry(domain=DOMAIN, entry_id="other_gateway")
    other_entry.add_to_hass(hass)
    devices = dr.async_get(hass)
    other = devices.async_get_or_create(
        config_entry_id=other_entry.entry_id,
        identifiers={(DOMAIN, "FD")},
        name="Other Gateway Sensor",
    )
    coordinator.sensor_mapper.update_mapping([_WN36, _WN31])

    coordinator._apply_live_titles({"ch_aisle": [_aisle(1, "Jacuzzi Temp")]})

    assert coordinator._live_titles == {"FD": "Jacuzzi Temp"}
    device = devices.async_get(other.id)
    assert device is not None and device.name == "Other Gateway Sensor"
