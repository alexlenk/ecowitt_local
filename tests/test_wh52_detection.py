"""Tests for WH52 sensors that get_sensors_info reports as WH51 (issue #279)."""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.ecowitt_local.const import DOMAIN
from custom_components.ecowitt_local.device_naming import device_name
from custom_components.ecowitt_local.sensor_mapper import SensorMapper
from tests.test_entity_naming import _entry, _mapping, _set_gateway, _setup

# get_sensors_info from a GW3000A V1.2.4 with one WH51 (CH1) and two WH52s
# (CH2, CH3): all three are reported as "wh51" with WH51 type numbers.
_WH51 = _mapping("F22E1", "wh51", 14, "Soil moisture CH1")
_WH52_CH2 = _mapping("8BA1", "wh51", 15, "Soil moisture CH2")
_WH52_CH3 = _mapping("8CA4", "wh51", 16, "Soil moisture CH3")
_MAPPINGS = [_WH51, _WH52_CH2, _WH52_CH3]


def _soil(channel: int, name: str = "") -> Dict[str, Any]:
    """Return a ch_soil live-data item (WH51)."""
    return {
        "channel": str(channel),
        "name": name,
        "battery": "5",
        "voltage": "1.70",
        "humidity": "27%",
    }


def _ec(channel: int, name: str = "") -> Dict[str, Any]:
    """Return a ch_ec live-data item (WH52)."""
    return {
        "channel": str(channel),
        "name": name,
        "battery": "5",
        "voltage": "1.70",
        "humidity": "43%",
        "temp": "14.9",
        "unit": "C",
        "ec": "60 uS/cm",
    }


def _live(ec_channels: List[int], ec_name: str = "") -> Dict[str, Any]:
    """Return live data with the WH51 on CH1 and WH52s on the given channels."""
    return {
        "ch_soil": [_soil(1)],
        "ch_ec": [_ec(ch, ec_name if ch == 2 else "") for ch in ec_channels],
    }


def test_mapper_marks_ec_devices_and_keeps_them():
    """Marked sensors get the WH52 model, survive refreshes and are never unmarked."""
    mapper = SensorMapper()
    mapper.update_mapping(_MAPPINGS)

    assert mapper.mark_ec_devices({"8BA1", "8CA4"}) == {"8BA1", "8CA4"}
    assert mapper.mark_ec_devices({"8BA1"}) == set()

    for unique_id in ("8BA1", "8CA4"):
        info = mapper.get_sensor_info(unique_id)
        assert info is not None
        assert info["device_model"] == "wh52" and info["live_model"] == "wh52"
        # The sensor type stays WH51: key generation and battery fallback use it.
        assert info["sensor_type"] == "WH51"
    wh51 = mapper.get_sensor_info("F22E1")
    assert wh51 is not None and wh51["device_model"] == "wh51"
    assert "live_model" not in wh51

    # A refresh after a poll that only listed CH2 keeps CH3 marked too.
    mapper.update_mapping(_MAPPINGS)
    for unique_id in ("8BA1", "8CA4"):
        info = mapper.get_sensor_info(unique_id)
        assert info is not None and info["device_model"] == "wh52"


def test_mapper_marks_ec_device_before_it_is_mapped():
    """A sensor marked before get_sensors_info lists it gets the model on mapping.

    The coordinator only marks IDs it found through the mapping, so this does not
    happen in practice; it covers the defensive check in mark_ec_devices.
    """
    mapper = SensorMapper()
    assert mapper.mark_ec_devices({"8BA1"}) == {"8BA1"}
    mapper.update_mapping(_MAPPINGS)
    info = mapper.get_sensor_info("8BA1")
    assert info is not None and info["device_model"] == "wh52"


def test_device_name_uses_live_model():
    """The type name follows live_model; a title or gateway name still wins."""
    info: Dict[str, Any] = {
        "sensor_type": "WH51",
        "channel": "2",
        "raw_data": {"name": "Soil moisture CH2"},
    }
    assert device_name("8BA1", info) == "Ecowitt Soil Moisture Sensor 8BA1"
    info["live_model"] = "wh52"
    assert device_name("8BA1", info) == "Ecowitt Soil Moisture & EC Sensor 8BA1"
    info["live_title"] = "Raised Bed"
    assert device_name("8BA1", info) == "Raised Bed"


def test_renamed_wh52_gets_its_channel_from_the_type_number():
    """A WH52 renamed on the gateway maps by the WH51 type range (issue #265)."""
    mapper = SensorMapper()
    mapper.update_mapping([_mapping("8BA1", "wh51", 15, "Garden Bed")])
    info = mapper.get_sensor_info("8BA1")
    assert info is not None and info["channel"] == "2"
    assert mapper.get_hardware_id("soilec2") == "8BA1"
    assert mapper.get_hardware_id("soiltemp2") == "8BA1"


async def test_wh52_devices_get_wh52_name_and_model(
    hass: HomeAssistant, mock_ecowitt_api
):
    """Sensors in ch_ec are named and modelled as WH52; the WH51 is unchanged."""
    entry = _entry(hass)
    await _setup(hass, mock_ecowitt_api, entry, _MAPPINGS, _live([2, 3]))
    devices = dr.async_get(hass)

    for unique_id in ("8BA1", "8CA4"):
        device = devices.async_get_device(identifiers={(DOMAIN, unique_id)})
        assert device is not None
        assert device.name == f"Ecowitt Soil Moisture & EC Sensor {unique_id}"
        assert device.model == "wh52"
    wh51 = devices.async_get_device(identifiers={(DOMAIN, "F22E1")})
    assert wh51 is not None
    assert wh51.name == "Ecowitt Soil Moisture Sensor F22E1"
    assert wh51.model == "wh51"


async def test_devices_created_as_wh51_switch_once_ch_ec_appears(
    hass: HomeAssistant, mock_ecowitt_api
):
    """WH52s first seen without ch_ec switch to WH52; user names are kept."""
    entry = _entry(hass)
    # No ch_ec in the first live data: the WH52s are created as WH51.
    await _setup(hass, mock_ecowitt_api, entry, _MAPPINGS, _live([]))
    coordinator = hass.data[DOMAIN][entry.entry_id]
    devices = dr.async_get(hass)

    def device_of(unique_id: str) -> Any:
        device = devices.async_get_device(identifiers={(DOMAIN, unique_id)})
        assert device is not None
        return device

    assert device_of("8BA1").name == "Ecowitt Soil Moisture Sensor 8BA1"
    assert device_of("8BA1").model == "wh51"
    devices.async_update_device(device_of("8CA4").id, name_by_user="WH52 Lawn")

    async def poll(ec_channels: List[int], ec_name: str = "") -> None:
        _set_gateway(mock_ecowitt_api, _MAPPINGS, _live(ec_channels, ec_name))
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    await poll([2, 3])
    assert device_of("8BA1").name == "Ecowitt Soil Moisture & EC Sensor 8BA1"
    assert device_of("8BA1").model == "wh52"
    lawn = device_of("8CA4")
    assert lawn.name == "Ecowitt Soil Moisture & EC Sensor 8CA4"
    assert lawn.model == "wh52" and lawn.name_by_user == "WH52 Lawn"
    assert device_of("F22E1").model == "wh51"

    # A poll without the CH2 item, followed by a mapping refresh, does not
    # switch the sensor back to WH51.
    await poll([3])
    await coordinator.async_refresh_mapping()
    await hass.async_block_till_done()
    info = coordinator.sensor_mapper.get_sensor_info("8BA1")
    assert info is not None and info["device_model"] == "wh52"

    # A gateway title names the device; clearing it restores the WH52 name.
    await poll([2, 3], "Raised Bed")
    assert device_of("8BA1").name == "Raised Bed"
    await poll([2, 3])
    assert device_of("8BA1").name == "Ecowitt Soil Moisture & EC Sensor 8BA1"
    assert device_of("8BA1").model == "wh52"


async def test_restart_keeps_wh52_devices_unchanged(
    hass: HomeAssistant, mock_ecowitt_api
):
    """After a restart the WH52 is detected before its device is registered."""
    entry = _entry(hass)
    await _setup(hass, mock_ecowitt_api, entry, _MAPPINGS, _live([2, 3]))
    devices = dr.async_get(hass)
    before = devices.async_get_device(identifiers={(DOMAIN, "8BA1")})
    assert before is not None and before.model == "wh52"

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

    after = devices.async_get_device(identifiers={(DOMAIN, "8BA1")})
    assert after is not None
    assert after.model == "wh52"
    assert after.name == "Ecowitt Soil Moisture & EC Sensor 8BA1"
    # Setup never wrote WH51 values in between.
    assert after.modified_at == before.modified_at
