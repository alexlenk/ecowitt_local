"""Tests for device-based entity names on hardware-ID devices (issues #244, #262)."""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import Mock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecowitt_local.const import (
    BATTERY_SENSORS,
    CONF_HOST,
    CONF_PASSWORD,
    DOMAIN,
    GATEWAY_SENSORS,
    SENSOR_TYPES,
)
from custom_components.ecowitt_local.sensor import EcowittLocalSensor
from custom_components.ecowitt_local.sensor_mapper import SensorMapper


def _mapping(hardware_id: str, img: str, type_num: int, name: str) -> Dict[str, Any]:
    """Return a get_sensors_info entry."""
    return {
        "id": hardware_id,
        "img": img,
        "type": str(type_num),
        "name": name,
        "batt": "4",
        "rssi": "-60",
        "signal": "4",
        "idst": "1",
    }


def _wh31(hardware_id: str, channel: int) -> Dict[str, Any]:
    """Return a get_sensors_info entry for a WH31 on the given channel."""
    return _mapping(hardware_id, "wh31", channel + 5, f"Temp & Humidity CH{channel}")


def _aisle(channel: int, temp: str) -> Dict[str, Any]:
    """Return a ch_aisle live-data item for a WH31 on the given channel."""
    return {
        "channel": str(channel),
        "name": "",
        "battery": "0",
        "temp": temp,
        "unit": "C",
        "humidity": "55",
    }


def _entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create and register the config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PASSWORD: ""},
        entry_id="naming_entry",
        unique_id="naming_unique",
    )
    entry.add_to_hass(hass)
    return entry


async def _setup(
    hass: HomeAssistant,
    mock_ecowitt_api,
    entry: MockConfigEntry,
    mappings: List[Dict[str, Any]],
    live: Dict[str, Any],
) -> None:
    """Set up the integration against a mocked gateway."""
    _set_gateway(mock_ecowitt_api, mappings, live)
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
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


def _set_gateway(
    mock_ecowitt_api, mappings: List[Dict[str, Any]], live: Dict[str, Any]
) -> None:
    """Point the mocked gateway API at the given sensors."""
    mock_ecowitt_api.get_live_data.return_value = {"common_list": [], **live}
    mock_ecowitt_api.get_all_sensor_mappings.return_value = mappings


def _friendly_name(hass: HomeAssistant, entity_id: str) -> str:
    """Return the friendly name HA shows for an entity."""
    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    return str(state.attributes["friendly_name"])


def _entities_by_key(hass: HomeAssistant, entry: MockConfigEntry) -> Dict[str, Any]:
    """Map unique_id to entity registry entry."""
    registry = er.async_get(hass)
    return {
        e.unique_id: e
        for e in er.async_entries_for_config_entry(registry, entry.entry_id)
    }


def test_channel_templates_define_channel_free_entity_name():
    """Every channel-templated sensor and battery has an entity_name without CH."""
    templated = {k: v for k, v in SENSOR_TYPES.items() if "CH" in v["name"]}
    assert templated, "channel templates should exist"
    for key, info in templated.items():
        assert "CH" not in info["entity_name"], key
        assert info["name"].startswith(info["entity_name"]), key

    assert SENSOR_TYPES["temp2f"]["entity_name"] == "Temperature"
    assert SENSOR_TYPES["temp2f"]["name"] == "Temperature CH2"
    assert SENSOR_TYPES["soilad3"]["entity_name"] == "Soil Moisture AD"
    assert SENSOR_TYPES["leak_ch1"]["entity_name"] == "Leak"
    assert SENSOR_TYPES["leak_ch1"]["name"] == "Leak Sensor CH1"

    batteries = {k: v for k, v in BATTERY_SENSORS.items() if "CH" in v["name"]}
    assert batteries
    for key, info in batteries.items():
        assert info["entity_name"] == "Battery", key


# Sensor types with their own hardware-ID device but no channel (issue #262).
_NON_CHANNEL_TYPES = (
    ["wh57", "wh40", "wn20", "wh68", "wh69", "wh65", "ws90", "wh90", "wh80", "ws80"]
    + ["wh85", "wh45", "wh46", "wh25", "wh26", "wn32", "wn38"]
    + ["solar & wind", "temp & humidity & solar & wind", "wind & rain"]
    + ["temp & humidity & solar & wind & rain", "pm25 & pm10 & co2"]
)

# Names that repeat the device (or its location) are reduced to what is measured.
_TRIMMED_ENTITY_NAMES = {
    "0x01": "Temperature",
    "tempf": "Temperature",
    "0x02": "Temperature",
    "0x06": "Humidity",
    "humidity": "Humidity",
    "0x07": "Humidity",
    "tf_co2": "Temperature",
    "tf_co2c": "Temperature",
    "humi_co2": "Humidity",
    "ws90_voltage": "Battery Voltage",
    "wh90_voltage": "Battery Voltage",
    "ws85_voltage": "Battery Voltage",
    "ws90cap_volt": "Capacitor Voltage",
    "wh90cap_volt": "Capacitor Voltage",
    "ws85cap_volt": "Capacitor Voltage",
}


def test_non_channel_keys_define_entity_name():
    """Every key a non-channel hardware device can own has an entity_name."""
    mapper = SensorMapper()
    keys = set()
    for sensor_type in _NON_CHANNEL_TYPES:
        type_keys = mapper._generate_live_data_keys(sensor_type, "")
        assert type_keys, sensor_type
        keys.update(type_keys)
    keys.add("solar_lux")  # computed by the coordinator next to solar radiation

    # The coordinator never looks up a hardware ID for gateway sensors, so they
    # always stay on the gateway device and keep their standalone names.
    for key in GATEWAY_SENSORS:
        assert key in keys, key
        assert "entity_name" not in SENSOR_TYPES[key], key
    keys -= GATEWAY_SENSORS

    for key in sorted(keys):
        if key in BATTERY_SENSORS:
            assert BATTERY_SENSORS[key]["entity_name"] == "Battery", key
            continue
        info = SENSOR_TYPES[key]
        expected = _TRIMMED_ENTITY_NAMES.get(key, info["name"])
        assert info["entity_name"] == expected, key
    assert set(_TRIMMED_ENTITY_NAMES) <= keys

    # What is measured stays in the name even if the device name repeats it.
    assert SENSOR_TYPES["lightning"]["entity_name"] == "Lightning Distance"
    assert SENSOR_TYPES["lightning_num"]["entity_name"] == "Lightning Strikes"
    assert SENSOR_TYPES["lightning_time"]["entity_name"] == "Last Lightning"
    assert SENSOR_TYPES["0xA1"]["entity_name"] == "Black Globe Temperature"


def _sensor(sensor_info: Dict[str, Any], mapper_result: Any) -> EcowittLocalSensor:
    """Build a sensor with a mocked coordinator."""
    coordinator = Mock()
    coordinator.config_entry.entry_id = "test"
    coordinator.sensor_mapper.get_sensor_info.return_value = mapper_result
    return EcowittLocalSensor(
        coordinator=coordinator,
        entity_id="sensor.ecowitt_temperature_d1e2f3",
        sensor_info=sensor_info,
    )


def test_entity_name_used_on_hardware_device():
    """With a hardware device the entity is named by what it measures."""
    sensor = _sensor(
        {
            "sensor_key": "temp2f",
            "hardware_id": "D1E2F3",
            "name": "Temperature CH2",
            "state": 21.5,
        },
        {"sensor_type": "WH31"},
    )
    assert sensor.has_entity_name is True
    assert sensor.name == "Temperature"

    # Coordinator updates carry the legacy name; it must not come back.
    sensor._update_attributes({"sensor_key": "temp2f", "name": "Temperature CH2"})
    assert sensor.name == "Temperature"


def test_legacy_name_without_hardware_device():
    """Without a hardware device the channel stays in the name."""
    base = {
        "sensor_key": "temp2f",
        "name": "Temperature CH2",
        "state": 21.5,
    }
    cases = [
        ({**base, "hardware_id": None}, {"sensor_type": "WH31"}),
        ({**base, "hardware_id": "FFFFFFFF"}, {"sensor_type": "WH31"}),
        ({**base, "hardware_id": "D1E2F3"}, None),  # mapping not found
    ]
    for sensor_info, mapper_result in cases:
        sensor = _sensor(sensor_info, mapper_result)
        assert sensor.has_entity_name is False, sensor_info
        assert sensor.name == "Temperature CH2", sensor_info


def test_sensor_without_entity_name_unchanged():
    """Sensors without entity_name (diagnostics) keep has_entity_name off."""
    sensor = _sensor(
        {
            "sensor_key": "rssi_D1E2F3",
            "hardware_id": "D1E2F3",
            "name": "RSSI",
        },
        {"sensor_type": "WH25"},
    )
    assert sensor.has_entity_name is False
    assert sensor.name == "RSSI"


def test_non_channel_entity_name_depends_on_device():
    """The same key is trimmed on a hardware device and standalone on the gateway."""
    base = {"sensor_key": "0x02", "name": "Outdoor Temperature", "state": 21.5}

    on_device = _sensor({**base, "hardware_id": "W90"}, {"sensor_type": "WH90"})
    assert on_device.has_entity_name is True
    assert on_device.name == "Temperature"

    for hardware_id, mapper_result in ((None, None), ("W90", None)):
        on_gateway = _sensor({**base, "hardware_id": hardware_id}, mapper_result)
        assert on_gateway.has_entity_name is False, hardware_id
        assert on_gateway.name == "Outdoor Temperature", hardware_id

    battery = _sensor(
        {
            "sensor_key": "wh57batt",
            "hardware_id": "L57",
            "name": "Lightning Sensor Battery",
        },
        {"sensor_type": "WH57"},
    )
    assert battery.has_entity_name is True
    assert battery.name == "Battery"


def test_coordinator_entity_name_overrides_static_one():
    """An entity_name supplied with the data wins and follows later updates."""
    lux_mode = {
        "sensor_key": "0x15",
        "hardware_id": "W90",
        "name": "Solar Illuminance",
        "entity_name": "Solar Illuminance",
    }
    sensor = _sensor(lux_mode, {"sensor_type": "WH90"})
    assert sensor.has_entity_name is True
    assert sensor.name == "Solar Illuminance"

    # Gateway switched back to W/m²: the static entity_name applies again.
    sensor._update_attributes({"sensor_key": "0x15", "name": "Solar Radiation"})
    assert sensor.name == "Solar Radiation"
    sensor._update_attributes(lux_mode)
    assert sensor.name == "Solar Illuminance"

    # A derived key without a static definition is named by the coordinator.
    derived = {
        "sensor_key": "0x15_wm2",
        "hardware_id": "W90",
        "name": "Solar Radiation",
        "entity_name": "Solar Radiation",
    }
    sensor = _sensor(derived, {"sensor_type": "WH90"})
    assert sensor.has_entity_name is True
    assert sensor.name == "Solar Radiation"
    assert _sensor({**derived, "hardware_id": None}, None).has_entity_name is False


async def test_wh31_friendly_names_follow_device(hass: HomeAssistant, mock_ecowitt_api):
    """End to end: names come from the device, diagnostics and IDs are unchanged."""
    entry = _entry(hass)
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        [_wh31("D1E2F3", 2)],
        {"ch_aisle": [_aisle(2, "21.5")]},
    )
    entities = _entities_by_key(hass, entry)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "D1E2F3")})
    assert device is not None and device.name
    assert "CH" not in device.name

    renamed = {
        # unique_id: (stable entity_id, entity name)
        "ecowitt_local_D1E2F3_temp2f": (
            "sensor.ecowitt_temperature_d1e2f3",
            "Temperature",
        ),
        "ecowitt_local_D1E2F3_humidity2": (
            "sensor.ecowitt_humidity_d1e2f3",
            "Humidity",
        ),
        "ecowitt_local_D1E2F3_batt2": (
            "sensor.ecowitt_temperature_humidity_battery_d1e2f3",
            "Battery",
        ),
    }
    for unique_id, (entity_id, name) in renamed.items():
        entity = entities[unique_id]
        assert entity.entity_id == entity_id
        assert entity.device_id == device.id
        assert entity.has_entity_name is True
        assert entity.original_name == name
        assert _friendly_name(hass, entity_id) == f"{device.name} {name}"

    unchanged = {
        "ecowitt_local_D1E2F3_channel_D1E2F3": "Channel",
        "ecowitt_local_D1E2F3_hardware_id_D1E2F3": "Hardware ID",
        "ecowitt_local_D1E2F3_rssi_D1E2F3": "RSSI",
        "ecowitt_local_D1E2F3_signal_D1E2F3": "Signal Strength",
        "ecowitt_local_D1E2F3_signal_quality_D1E2F3": "Signal Quality",
        "ecowitt_local_D1E2F3_online": "Ecowitt Temperature D1E2F3 Online",
    }
    for unique_id, name in unchanged.items():
        entity = entities[unique_id]
        assert entity.has_entity_name is False, unique_id
        assert entity.original_name == name
        assert _friendly_name(hass, entity.entity_id) == name


async def test_user_overrides_survive_switch(hass: HomeAssistant, mock_ecowitt_api):
    """Names users set before the upgrade win over the new default names."""
    entry = _entry(hass)
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    # State before the upgrade: user renamed the device and one entity.
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "D1E2F3")},
        name="Ecowitt Temperature/Humidity Sensor D1E2F3",
    )
    device_registry.async_update_device(device.id, name_by_user="Deep Freezer")
    entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "ecowitt_local_D1E2F3_temp2f",
        suggested_object_id="ecowitt_temperature_d1e2f3",
        config_entry=entry,
        device_id=device.id,
        original_name="Temperature CH2",
    )
    entity_registry.async_update_entity(
        "sensor.ecowitt_temperature_d1e2f3", name="Freezer Probe"
    )

    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        [_wh31("D1E2F3", 2)],
        {"ch_aisle": [_aisle(2, "21.5")]},
    )

    temp = entity_registry.async_get("sensor.ecowitt_temperature_d1e2f3")
    assert temp is not None
    assert temp.name == "Freezer Probe"
    assert temp.has_entity_name is True
    assert _friendly_name(hass, "sensor.ecowitt_temperature_d1e2f3") == "Freezer Probe"

    # Entities the user did not rename pick up the user's device name.
    assert (
        _friendly_name(hass, "sensor.ecowitt_humidity_d1e2f3")
        == "Deep Freezer Humidity"
    )
    assert (
        _friendly_name(hass, "sensor.ecowitt_temperature_humidity_battery_d1e2f3")
        == "Deep Freezer Battery"
    )


async def test_duplicate_hardware_ids_stay_distinct(
    hass: HomeAssistant, mock_ecowitt_api
):
    """Two sensors sharing a hardware ID (issue #211) keep distinct names."""
    entry = _entry(hass)
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        [_wh31("D1E2F3", 2), _wh31("D1E2F3", 5)],
        {"ch_aisle": [_aisle(2, "21.5"), _aisle(5, "4.0")]},
    )
    device_registry = dr.async_get(hass)
    names = set()
    for composite_id, entity_id in (
        ("D1E2F3_ch2", "sensor.ecowitt_temperature_d1e2f3_ch2"),
        ("D1E2F3_ch5", "sensor.ecowitt_temperature_d1e2f3_ch5"),
    ):
        device = device_registry.async_get_device(identifiers={(DOMAIN, composite_id)})
        assert device is not None and composite_id in str(device.name)
        friendly = _friendly_name(hass, entity_id)
        assert friendly == f"{device.name} Temperature"
        names.add(friendly)
    assert len(names) == 2


_DIAGNOSTIC_MARKERS = ("_channel_", "_hardware_id_", "_rssi_", "_signal_")


def _is_diagnostic(unique_id: str) -> bool:
    """Return True for the diagnostic entities that keep their legacy names."""
    return unique_id.endswith("_online") or any(
        marker in unique_id for marker in _DIAGNOSTIC_MARKERS
    )


async def test_all_channel_families(hass: HomeAssistant, mock_ecowitt_api):
    """Every channel-templated family follows one scheme per device."""
    families = {
        # hardware_id: (mapping, expected device name)
        "A1": (_mapping("A1", "wh51", 15, "Soil moisture CH2"), "Soil Moisture Sensor"),
        "B1": (_mapping("B1", "wh41", 22, "PM2.5 CH1"), "PM2.5 Air Quality Sensor"),
        "C1": (_mapping("C1", "wh55", 27, "Leak CH1"), "Leak Sensor"),
        "D1": (_mapping("D1", "wh34", 31, "Temp CH1"), "Temperature Sensor"),
        "E1": (_mapping("E1", "wh35", 40, "Leaf CH1"), "Leaf Wetness Sensor"),
        "F1": (_mapping("F1", "wh54", 66, "LDS CH1"), "Liquid Depth Sensor"),
        "G1": (
            _mapping("G1", "wh31", 7, "Temp & Humidity CH2"),
            "Temperature/Humidity Sensor",
        ),
        "H1": (_mapping("H1", "wh52", 90, "Soil EC CH3"), "Soil Moisture & EC Sensor"),
    }
    live = {
        "ch_soil": [{"channel": "2", "humidity": "40%", "battery": "4"}],
        "ch_pm25": [
            {
                "channel": "1",
                "PM25": "5",
                "PM25_24H": "6",
                "PM25_RealAQI": "20",
                "PM25_24HAQI": "22",
                "battery": "4",
            }
        ],
        "ch_leak": [{"channel": "1", "status": "Normal", "battery": "4"}],
        "ch_temp": [{"channel": "1", "temp": "5.0", "unit": "C", "battery": "4"}],
        "ch_leaf": [{"channel": "1", "humidity": "30%", "battery": "4"}],
        "ch_lds": [
            {
                "channel": "1",
                "air": "100 mm",
                "depth": "200 mm",
                "voltage": "3.1",
                "battery": "4",
            }
        ],
        "ch_aisle": [_aisle(2, "-18")],
        "ch_ec": [
            {
                "channel": "3",
                "humidity": "30%",
                "temp": "15",
                "unit": "C",
                "ec": "200",
                "battery": "4",
            }
        ],
    }
    entry = _entry(hass)
    await _setup(hass, mock_ecowitt_api, entry, [m for m, _ in families.values()], live)

    device_registry = dr.async_get(hass)
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    for hardware_id, (_, type_name) in families.items():
        device = device_registry.async_get_device(identifiers={(DOMAIN, hardware_id)})
        assert device is not None, hardware_id
        assert device.name == f"Ecowitt {type_name} {hardware_id}"
        on_device = [e for e in entities if e.device_id == device.id]
        renamed = [e for e in on_device if not _is_diagnostic(e.unique_id)]
        assert renamed, hardware_id
        for entity in on_device:
            if _is_diagnostic(entity.unique_id):
                assert entity.has_entity_name is False, entity.unique_id
                continue
            assert entity.has_entity_name is True, entity.unique_id
            assert "CH" not in str(entity.original_name), entity.unique_id
            assert _friendly_name(hass, entity.entity_id) == (
                f"{device.name} {entity.original_name}"
            )

    leak = er.async_get(hass).async_get("sensor.ecowitt_leak_c1")
    assert leak is not None and leak.original_name == "Leak"


async def test_gateway_name_reaches_entities(hass: HomeAssistant, mock_ecowitt_api):
    """A name set on the gateway (#243) survives platform setup and names entities."""
    entry = _entry(hass)
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        [_mapping("G1", "wh31", 7, "Deep Freezer")],
        {"ch_aisle": [_aisle(2, "-18")]},
    )
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "G1")})
    assert device is not None and device.name == "Deep Freezer"
    assert _friendly_name(hass, "sensor.ecowitt_temperature_g1") == (
        "Deep Freezer Temperature"
    )
    assert _friendly_name(hass, "sensor.ecowitt_temperature_humidity_battery_g1") == (
        "Deep Freezer Battery"
    )


async def test_sensor_added_at_runtime_gets_device_name(
    hass: HomeAssistant, mock_ecowitt_api
):
    """A sensor paired while HA runs gets the same device name as at setup."""
    wh31 = _wh31("D1E2F3", 2)
    entry = _entry(hass)
    await _setup(hass, mock_ecowitt_api, entry, [wh31], {"ch_aisle": [_aisle(2, "21")]})

    _set_gateway(
        mock_ecowitt_api,
        [wh31, _mapping("D1", "wh34", 31, "Temp CH1")],
        {
            "ch_aisle": [_aisle(2, "21")],
            "ch_temp": [{"channel": "1", "temp": "5.0", "unit": "C", "battery": "4"}],
        },
    )
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_refresh_mapping()
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "D1")})
    assert device is not None and device.name == "Ecowitt Temperature Sensor D1"
    assert _friendly_name(hass, "sensor.ecowitt_tf_d1") == (
        "Ecowitt Temperature Sensor D1 Temperature"
    )


async def test_device_names_for_gateway_default_names(
    hass: HomeAssistant,
    mock_ecowitt_api,
    mock_complete_sensor_mappings,
    mock_live_data,
):
    """Gateway default names without "CH{n}" are not treated as user renames.

    Non-channel sensors report defaults like "Solar & Wind", "Lightning" or
    "WH90"; only a renamed channel sensor may name its device (issue #243).
    """
    wh90 = _mapping("W90", "wh90", 48, "WH90")
    entry = _entry(hass)
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        mock_complete_sensor_mappings + [wh90],
        mock_live_data,
    )
    expected = {
        "A1B2C3": "Ecowitt Weather Station A1B2C3",  # gateway name "Solar & Wind"
        "D1E2F3": "Ecowitt Temperature/Humidity Sensor D1E2F3",
        "D8174": "Ecowitt Soil Moisture Sensor D8174",
        "E4F5A6": "Ecowitt Lightning Sensor E4F5A6",  # "Lightning"
        "F6G7H8": "Ecowitt Rain Sensor F6G7H8",  # "Rain"
        "G8H9I0": "Ecowitt PM2.5 Air Quality Sensor G8H9I0",
        "J1K2L3": "Ecowitt Leak Sensor J1K2L3",
        "M4N5O6": "Ecowitt CO2 Air Quality Sensor M4N5O6",  # "PM25 & PM10 & CO2"
        "W90": "Ecowitt WS90 Weather Station W90",  # "WH90"
    }
    device_registry = dr.async_get(hass)
    for hardware_id, name in expected.items():
        device = device_registry.async_get_device(identifiers={(DOMAIN, hardware_id)})
        assert device is not None, hardware_id
        assert device.name == name, hardware_id


_NON_CHANNEL_MAPPINGS = [
    _mapping("W90", "wh90", 48, "Temp & Humidity & Solar & Wind & Rain"),
    _mapping("L57", "wh57", 26, "Lightning"),
    _mapping("C45", "wh45", 39, "PM25 & PM10 & CO2"),
    _mapping("R40", "wh40", 3, "Rain"),
]

_NON_CHANNEL_LIVE: Dict[str, Any] = {
    "common_list": [
        {"id": "0x02", "val": "21.5", "unit": "C"},
        {"id": "0x07", "val": "55%"},
        {"id": "0x03", "val": "12.0", "unit": "C"},
        {"id": "3", "val": "21.0", "unit": "C"},
        {"id": "0x0B", "val": "1.2 m/s"},
        {"id": "0x0A", "val": "180"},
        {"id": "0x15", "val": "120.5 W/m2"},
        {"id": "0x17", "val": "3"},
    ],
    "piezoRain": [
        {"id": "srain_piezo", "val": "0"},
        {"id": "0x0E", "val": "0.0 mm/Hr"},
        {
            "id": "0x13",
            "val": "257.8 mm",
            "battery": "3",
            "voltage": "2.62",
            "ws90cap_volt": "5.3",
            "ws90_ver": "153",
        },
    ],
    "rain": [
        {"id": "0x0E", "val": "0.0 mm/Hr"},
        {"id": "0x13", "val": "29.5 mm", "battery": "0"},
    ],
    "lightning": [
        {
            "distance": "31 km",
            "date": "2026-02-22T18:00:18",
            "timestamp": "02/22/2026 18:00:18",
            "count": "3",
            "battery": "5",
        }
    ],
    "co2": [
        {
            "temp": "29.7",
            "unit": "C",
            "humidity": "47%",
            "PM25": "68.0",
            "CO2": "511",
            "battery": "6",
        }
    ],
    "wh25": [{"intemp": "28.9", "unit": "C", "inhumi": "40%"}],
}


async def test_non_channel_families(hass: HomeAssistant, mock_ecowitt_api):
    """Non-channel hardware devices follow the same scheme (issue #262)."""
    entry = _entry(hass)
    await _setup(
        hass, mock_ecowitt_api, entry, _NON_CHANNEL_MAPPINGS, _NON_CHANNEL_LIVE
    )
    entities = _entities_by_key(hass, entry)
    device_registry = dr.async_get(hass)

    expected = {
        # unique_id: (stable entity_id, entity name)
        "ecowitt_local_W90_0x02": ("sensor.ecowitt_outdoor_temp_w90", "Temperature"),
        "ecowitt_local_W90_0x07": ("sensor.ecowitt_outdoor_humidity_w90", "Humidity"),
        "ecowitt_local_W90_0x03": (
            "sensor.ecowitt_dewpoint_w90",
            "Dewpoint Temperature",
        ),
        "ecowitt_local_W90_3": (
            "sensor.ecowitt_feels_like_temp_w90",
            "Feels Like Temperature",
        ),
        "ecowitt_local_W90_0x0B": ("sensor.ecowitt_wind_speed_w90", "Wind Speed"),
        "ecowitt_local_W90_0x0E": ("sensor.ecowitt_rain_rate_w90", "Rain Rate"),
        "ecowitt_local_W90_0x15": (
            "sensor.ecowitt_solar_radiation_w90",
            "Solar Radiation",
        ),
        "ecowitt_local_W90_solar_lux": (
            "sensor.ecowitt_solar_lux_w90",
            "Solar Illuminance",
        ),
        "ecowitt_local_W90_wh90batt": ("sensor.ecowitt_battery_w90", "Battery"),
        "ecowitt_local_W90_wh90_voltage": (
            "sensor.ecowitt_voltage_w90",
            "Battery Voltage",
        ),
        "ecowitt_local_W90_wh90cap_volt": (
            "sensor.ecowitt_capacitor_voltage_w90",
            "Capacitor Voltage",
        ),
        "ecowitt_local_L57_lightning": (
            "sensor.ecowitt_lightning_l57",
            "Lightning Distance",
        ),
        "ecowitt_local_L57_lightning_num": (
            "sensor.ecowitt_lightning_strikes_l57",
            "Lightning Strikes",
        ),
        "ecowitt_local_L57_lightning_time": (
            "sensor.ecowitt_last_lightning_l57",
            "Last Lightning",
        ),
        "ecowitt_local_L57_wh57batt": (
            "sensor.ecowitt_lightning_battery_l57",
            "Battery",
        ),
        "ecowitt_local_C45_tf_co2c": ("sensor.ecowitt_tf_co2c_c45", "Temperature"),
        "ecowitt_local_C45_humi_co2": ("sensor.ecowitt_humi_co_c45", "Humidity"),
        "ecowitt_local_C45_pm25_co2": ("sensor.ecowitt_pm25_c45", "PM2.5"),
        "ecowitt_local_C45_co2": ("sensor.ecowitt_co_c45", "CO2"),
        "ecowitt_local_C45_co2_batt": ("sensor.ecowitt_battery_c45", "Battery"),
        "ecowitt_local_R40_0x0E": ("sensor.ecowitt_rain_rate_r40", "Rain Rate"),
        "ecowitt_local_R40_0x13": ("sensor.ecowitt_yearly_rain_r40", "Yearly Rain"),
        "ecowitt_local_R40_wh40batt": ("sensor.ecowitt_rain_battery_r40", "Battery"),
    }
    for unique_id, (entity_id, name) in expected.items():
        entity = entities[unique_id]
        assert entity.entity_id == entity_id
        assert entity.original_name == name, unique_id

    device_names = {
        "W90": "Ecowitt WS90 Weather Station W90",
        "L57": "Ecowitt Lightning Sensor L57",
        "C45": "Ecowitt CO2 Air Quality Sensor C45",
        "R40": "Ecowitt Rain Sensor R40",
    }
    for hardware_id, device_name in device_names.items():
        device = device_registry.async_get_device(identifiers={(DOMAIN, hardware_id)})
        assert device is not None and device.name == device_name, hardware_id
        on_device = [e for e in entities.values() if e.device_id == device.id]
        sensors = [e for e in on_device if e.domain == "sensor"]
        assert [e for e in sensors if not _is_diagnostic(e.unique_id)], hardware_id
        for entity in sensors:
            if _is_diagnostic(entity.unique_id):
                assert entity.has_entity_name is False, entity.unique_id
                assert _friendly_name(hass, entity.entity_id) == entity.original_name
                continue
            assert entity.has_entity_name is True, entity.unique_id
            assert _friendly_name(hass, entity.entity_id) == (
                f"{device_name} {entity.original_name}"
            )
        # Binary sensors (Online, rain state) are not part of this change.
        for entity in on_device:
            if entity.domain == "binary_sensor":
                assert entity.has_entity_name is False, entity.unique_id

    # The same kind of reading on the gateway device keeps its standalone name.
    gateway = {
        "ecowitt_local_naming_entry_tempinf": "Indoor Temperature",
        "ecowitt_local_naming_entry_humidityin": "Indoor Humidity",
    }
    for unique_id, name in gateway.items():
        entity = entities[unique_id]
        assert entity.has_entity_name is False, unique_id
        assert _friendly_name(hass, entity.entity_id) == name


async def test_solar_names_in_lux_mode(hass: HomeAssistant, mock_ecowitt_api):
    """In lux mode the renamed and the derived solar entity keep the right names."""
    entry = _entry(hass)
    await _setup(
        hass,
        mock_ecowitt_api,
        entry,
        [_mapping("W90", "wh90", 48, "WH90")],
        {"common_list": [{"id": "0x15", "val": "15000.0 Lux"}]},
    )
    device_name = "Ecowitt WS90 Weather Station W90"
    expected = {
        "sensor.ecowitt_solar_radiation_w90": ("Solar Illuminance", "lx"),
        "sensor.ecowitt_solar_radiation_wm2_w90": ("Solar Radiation", "W/m²"),
    }
    registry = er.async_get(hass)
    for entity_id, (name, unit) in expected.items():
        entity = registry.async_get(entity_id)
        assert entity is not None and entity.has_entity_name is True, entity_id
        assert entity.original_name == name
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.attributes["unit_of_measurement"] == unit
        assert state.attributes["friendly_name"] == f"{device_name} {name}"
