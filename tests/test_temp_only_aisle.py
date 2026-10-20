"""Tests for temperature-only ch_aisle sensors (WN30/WN36) reported as WH31."""

from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.ecowitt_local.const import DOMAIN
from custom_components.ecowitt_local.device_naming import device_name
from custom_components.ecowitt_local.sensor_mapper import (
    TEMP_ONLY_AISLE_MODEL,
    SensorMapper,
)
from tests.test_entity_naming import _entry, _mapping, _set_gateway, _setup

# get_sensors_info from a GW3000A: a WN36 pool thermometer on CH1 and a WN31 on
# CH2, both reported as "wh31" with WH31 type numbers.
_WN36 = _mapping("FD", "wh31", 6, "Temp & Humidity CH1")
_WN31 = _mapping("A2", "wh31", 7, "Temp & Humidity CH2")
_MAPPINGS = [_WN36, _WN31]


def _aisle(channel: int, humidity: Optional[str], name: str = "") -> Dict[str, Any]:
    """Return a ch_aisle live-data item as the GW3000A reports it."""
    item: Dict[str, Any] = {
        "channel": str(channel),
        "name": name,
        "battery": "0",
        "temp": "27.9" if channel == 1 else "21.1",
        "unit": "C",
    }
    if humidity is not None:
        item["humidity"] = humidity
    return item


def _live(
    ch1_humidity: Optional[str] = "None",
    ch2_humidity: Optional[str] = "48%",
    ch1_name: str = "",
) -> Dict[str, Any]:
    """Return live data with the WN36 on CH1 and the WN31 on CH2."""
    return {
        "ch_aisle": [
            _aisle(1, ch1_humidity, ch1_name),
            _aisle(2, ch2_humidity),
        ]
    }


def test_mapper_marks_sensor_without_humidity():
    """Only a sensor never seen with humidity gets the WN30/WN36 model."""
    mapper = SensorMapper()
    mapper.update_mapping(_MAPPINGS)
    mapper.mark_aisle_humidity({"FD"}, {"A2"})

    wn36 = mapper.get_sensor_info("FD")
    assert wn36 is not None
    assert wn36["device_model"] == TEMP_ONLY_AISLE_MODEL
    assert wn36["live_model"] == TEMP_ONLY_AISLE_MODEL
    # The sensor type stays WH31: key generation and battery fallback use it.
    assert wn36["sensor_type"] == "WH31"
    wn31 = mapper.get_sensor_info("A2")
    assert wn31 is not None and wn31["device_model"] == "wh31"
    assert "live_model" not in wn31

    # A WN31 that once reported humidity is not switched by a missing value.
    mapper.mark_aisle_humidity({"A2"}, set())
    wn31 = mapper.get_sensor_info("A2")
    assert wn31 is not None and wn31["device_model"] == "wh31"

    # The marking survives a mapping refresh, also for a sensor that was not
    # in the last poll.
    mapper.mark_aisle_humidity(set(), {"A2"})
    mapper.update_mapping(_MAPPINGS)
    wn36 = mapper.get_sensor_info("FD")
    assert wn36 is not None and wn36["device_model"] == TEMP_ONLY_AISLE_MODEL
    assert wn36["live_model"] == TEMP_ONLY_AISLE_MODEL
    wn31 = mapper.get_sensor_info("A2")
    assert wn31 is not None and wn31["device_model"] == "wh31"
    assert "live_model" not in wn31


def test_mapper_unmarks_sensor_that_reports_humidity():
    """Humidity reported later makes the sensor a WH31 for the rest of the run."""
    mapper = SensorMapper()
    mapper.update_mapping(_MAPPINGS)
    mapper.mark_aisle_humidity({"FD"}, set())
    mapper.mark_aisle_humidity(set(), {"FD"})

    info = mapper.get_sensor_info("FD")
    assert info is not None
    assert info["device_model"] == "wh31" and "live_model" not in info

    mapper.mark_aisle_humidity({"FD"}, set())
    mapper.update_mapping(_MAPPINGS)
    info = mapper.get_sensor_info("FD")
    assert info is not None and info["device_model"] == "wh31"


def test_unmark_restores_the_reported_model():
    """Removing the mark restores the model get_sensors_info reported."""
    mapper = SensorMapper()
    mapper.update_mapping([_mapping("FD", "temp_hum", 6, "Temp & Humidity CH1")])
    mapper.mark_aisle_humidity({"FD"}, set())
    mapper.mark_aisle_humidity(set(), {"FD"})
    info = mapper.get_sensor_info("FD")
    assert info is not None and info["device_model"] == "temp_hum"


def test_mapper_ignores_unmapped_sensors():
    """IDs without mapping info are recorded but touch nothing."""
    mapper = SensorMapper()
    mapper.mark_aisle_humidity({"FD"}, {"A2"})
    mapper.update_mapping(_MAPPINGS)
    info = mapper.get_sensor_info("FD")
    assert info is not None and info["device_model"] == TEMP_ONLY_AISLE_MODEL


def test_device_name_for_temperature_only_sensor():
    """The type name follows live_model; a title still wins."""
    info: Dict[str, Any] = {
        "sensor_type": "WH31",
        "channel": "1",
        "raw_data": {"name": "Temp & Humidity CH1"},
        "live_model": TEMP_ONLY_AISLE_MODEL,
    }
    assert device_name("FD", info) == "Ecowitt Temperature Sensor FD"
    info["live_title"] = "Jacuzzi"
    assert device_name("FD", info) == "Jacuzzi"


async def test_devices_get_name_and_model_from_humidity(
    hass: HomeAssistant, mock_ecowitt_api
):
    """With the real GW3000A data the WN36 gets its title and the WN30/WN36 model.

    A WH34 in ch_temp also has no humidity, but only ch_aisle sensors are
    candidates, so it keeps its own model.
    """
    entry = _entry(hass)
    wh34 = _mapping("C3", "wh34", 31, "Temp CH1")
    live = _live(ch1_name="Jacuzzi")
    live["ch_temp"] = [
        {"channel": "1", "name": "", "battery": "5", "temp": "20.0", "unit": "C"}
    ]
    await _setup(hass, mock_ecowitt_api, entry, [*_MAPPINGS, wh34], live)
    devices = dr.async_get(hass)

    temp_only = devices.async_get_device(identifiers={(DOMAIN, "C3")})
    assert temp_only is not None
    assert temp_only.model == "wh34"
    assert temp_only.name == "Ecowitt Temperature Sensor C3"

    wn36 = devices.async_get_device(identifiers={(DOMAIN, "FD")})
    assert wn36 is not None
    assert wn36.name == "Jacuzzi" and wn36.model == TEMP_ONLY_AISLE_MODEL
    wn31 = devices.async_get_device(identifiers={(DOMAIN, "A2")})
    assert wn31 is not None
    assert wn31.name == "Ecowitt Temperature/Humidity Sensor A2"
    assert wn31.model == "wh31"


async def test_untitled_sensor_and_runtime_changes(
    hass: HomeAssistant, mock_ecowitt_api
):
    """An untitled sensor is named by type; humidity later makes it a WH31."""
    entry = _entry(hass)
    await _setup(hass, mock_ecowitt_api, entry, _MAPPINGS, _live())
    coordinator = hass.data[DOMAIN][entry.entry_id]
    devices = dr.async_get(hass)

    def device_of(unique_id: str) -> Any:
        device = devices.async_get_device(identifiers={(DOMAIN, unique_id)})
        assert device is not None
        return device

    async def poll(live: Dict[str, Any]) -> None:
        _set_gateway(mock_ecowitt_api, _MAPPINGS, live)
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert device_of("FD").name == "Ecowitt Temperature Sensor FD"
    assert device_of("FD").model == TEMP_ONLY_AISLE_MODEL

    # A WN31 poll without humidity, followed by a mapping refresh, keeps it WH31.
    await poll(_live(ch2_humidity=None))
    await coordinator.async_refresh_mapping()
    await hass.async_block_till_done()
    info = coordinator.sensor_mapper.get_sensor_info("A2")
    assert info is not None and info["device_model"] == "wh31"
    assert device_of("A2").model == "wh31"

    # Humidity from CH1: its humidity entity registers the device as a WH31.
    await poll(_live(ch1_humidity="61%"))
    assert device_of("FD").name == "Ecowitt Temperature/Humidity Sensor FD"
    assert device_of("FD").model == "wh31"


async def test_item_without_data_is_not_a_candidate(
    hass: HomeAssistant, mock_ecowitt_api
):
    """An item with no temperature (no data yet) does not mark the sensor."""
    entry = _entry(hass)
    live = _live(ch2_humidity="None")
    live["ch_aisle"][1]["temp"] = "None"
    await _setup(hass, mock_ecowitt_api, entry, _MAPPINGS, live)
    coordinator = hass.data[DOMAIN][entry.entry_id]

    info = coordinator.sensor_mapper.get_sensor_info("A2")
    assert info is not None and info["device_model"] == "wh31"
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "A2")})
    assert device is not None and device.model == "wh31"
    # The WN36 on CH1, which has a temperature, is still marked.
    wn36 = coordinator.sensor_mapper.get_sensor_info("FD")
    assert wn36 is not None and wn36["device_model"] == TEMP_ONLY_AISLE_MODEL


async def test_temperature_and_humidity_edge_values(
    hass: HomeAssistant, mock_ecowitt_api
):
    """Missing or empty temperatures never mark; humidity without a temperature
    still counts as humidity seen."""
    entry = _entry(hass)
    live = _live(ch2_humidity="None")
    live["ch_aisle"][1]["temp"] = "None"
    await _setup(hass, mock_ecowitt_api, entry, _MAPPINGS, live)
    coordinator = hass.data[DOMAIN][entry.entry_id]

    def model_of_a2() -> Any:
        info = coordinator.sensor_mapper.get_sensor_info("A2")
        assert info is not None
        return info["device_model"]

    # No usable temperature: missing key or empty string.
    coordinator._apply_live_titles({"ch_aisle": [{"channel": "2", "humidity": "None"}]})
    coordinator._apply_live_titles(
        {"ch_aisle": [{"channel": "2", "temp": "", "humidity": "None"}]}
    )
    assert model_of_a2() == "wh31"

    # Humidity reported while the temperature is missing still counts, so a
    # later item with a temperature but no humidity does not mark the sensor.
    coordinator._apply_live_titles(
        {"ch_aisle": [{"channel": "2", "temp": "None", "humidity": "48%"}]}
    )
    coordinator._apply_live_titles(
        {"ch_aisle": [{"channel": "2", "temp": "21.1", "humidity": "None"}]}
    )
    assert model_of_a2() == "wh31"


async def test_restart_keeps_temperature_only_device_unchanged(
    hass: HomeAssistant, mock_ecowitt_api
):
    """After a restart the sensor is detected before its device is registered."""
    entry = _entry(hass)
    await _setup(hass, mock_ecowitt_api, entry, _MAPPINGS, _live())
    devices = dr.async_get(hass)
    before = devices.async_get_device(identifiers={(DOMAIN, "FD")})
    assert before is not None and before.model == TEMP_ONLY_AISLE_MODEL

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

    after = devices.async_get_device(identifiers={(DOMAIN, "FD")})
    assert after is not None
    assert after.model == TEMP_ONLY_AISLE_MODEL
    assert after.name == "Ecowitt Temperature Sensor FD"
    # Setup never wrote WH31 values in between.
    assert after.modified_at == before.modified_at
