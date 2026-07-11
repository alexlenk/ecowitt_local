"""Test the Ecowitt Local sensor mapper."""

from __future__ import annotations

import pytest

from custom_components.ecowitt_local.sensor_mapper import SensorMapper


@pytest.fixture
def sensor_mapper():
    """Create a sensor mapper for testing."""
    return SensorMapper()


@pytest.fixture
def mock_sensor_mappings():
    """Mock sensor mapping data."""
    return [
        {
            "id": "D8174",
            "img": "WH51",
            "name": "Soil moisture CH1",
            "batt": "85",
            "signal": "4",
        },
        {
            "id": "D8648",
            "img": "WH51",
            "name": "Soil moisture CH2",
            "batt": "78",
            "signal": "3",
        },
        {
            "id": "EF891",
            "img": "WH41",
            "name": "PM2.5 air quality sensor CH1",
            "batt": "92",
            "signal": "4",
        },
        {
            "id": "A7C42",
            "img": "WH31",
            "name": "Temp & Humidity CH1",
            "batt": "88",
            "signal": "3",
        },
    ]


def test_update_mapping(sensor_mapper: SensorMapper, mock_sensor_mappings):
    """Test updating sensor mapping."""
    sensor_mapper.update_mapping(mock_sensor_mappings)

    # Test hardware ID retrieval
    assert sensor_mapper.get_hardware_id("soilmoisture1") == "D8174"
    assert sensor_mapper.get_hardware_id("soiltemp1") == "D8174"
    assert sensor_mapper.get_hardware_id("soilec1") == "D8174"
    assert sensor_mapper.get_hardware_id("soilmoisture2") == "D8648"
    assert sensor_mapper.get_hardware_id("soiltemp2") == "D8648"
    assert sensor_mapper.get_hardware_id("soilec2") == "D8648"
    assert sensor_mapper.get_hardware_id("pm25_ch1") == "EF891"
    assert sensor_mapper.get_hardware_id("temp1f") == "A7C42"

    # Test sensor info retrieval
    soil_info = sensor_mapper.get_sensor_info("D8174")
    assert soil_info["hardware_id"] == "D8174"
    assert soil_info["sensor_type"] == "WH51"
    assert soil_info["channel"] == "1"
    assert soil_info["battery"] == "85"


def test_generate_live_data_keys(sensor_mapper: SensorMapper):
    """Test generating live data keys."""
    # Test soil moisture sensor (WH51 also maps soiltemp/soilec for WH52 compatibility)
    keys = sensor_mapper._generate_live_data_keys("WH51", "1")
    assert "soilmoisture1" in keys
    assert "soiltemp1" in keys
    assert "soilec1" in keys
    assert "soilbatt1" in keys

    # Test temperature/humidity sensor
    keys = sensor_mapper._generate_live_data_keys("WH31", "1")
    assert "temp1f" in keys
    assert "humidity1" in keys
    assert "batt1" in keys

    # Test PM2.5 sensor
    keys = sensor_mapper._generate_live_data_keys("WH41", "1")
    assert "pm25_ch1" in keys
    assert "pm25batt1" in keys

    # Test invalid inputs
    keys = sensor_mapper._generate_live_data_keys("", "1")
    assert len(keys) == 0

    keys = sensor_mapper._generate_live_data_keys("WH51", "")
    assert len(keys) == 0


def test_generate_entity_id(sensor_mapper: SensorMapper, mock_sensor_mappings):
    """Test generating entity IDs."""
    sensor_mapper.update_mapping(mock_sensor_mappings)

    # Test with hardware ID
    entity_id, name = sensor_mapper.generate_entity_id("soilmoisture1", "D8174")
    assert entity_id == "sensor.ecowitt_soil_moisture_d8174"
    assert "Soil Moisture" in name

    # Test without hardware ID
    entity_id, name = sensor_mapper.generate_entity_id("tempf", None, "outdoor")
    assert entity_id == "sensor.ecowitt_temperature_outdoor"

    # Test battery sensor
    entity_id, name = sensor_mapper.generate_entity_id("soilbatt1", "D8174")
    assert entity_id == "sensor.ecowitt_soil_moisture_battery_d8174"
    assert "Battery" in name


def test_extract_sensor_type_from_key(sensor_mapper: SensorMapper):
    """Test extracting sensor type from key."""
    assert sensor_mapper._extract_sensor_type_from_key("tempf") == "temperature"
    assert sensor_mapper._extract_sensor_type_from_key("humidity1") == "humidity"
    assert (
        sensor_mapper._extract_sensor_type_from_key("soilmoisture1") == "soil_moisture"
    )
    assert sensor_mapper._extract_sensor_type_from_key("pm25_ch1") == "pm25"
    assert sensor_mapper._extract_sensor_type_from_key("windspeedmph") == "wind"
    assert sensor_mapper._extract_sensor_type_from_key("baromrelin") == "pressure"
    # tf_ch1 (WH34) strips digit then strips "ch", leaving trailing "_" — must not produce double underscore
    assert sensor_mapper._extract_sensor_type_from_key("tf_ch1") == "tf"


def test_tf_ch_entity_id_no_double_underscore(sensor_mapper: SensorMapper):
    """Regression test for issue #189.

    tf_ch1 (WH34) was producing sensor.ecowitt_tf__b0d0 (double underscore)
    because _extract_sensor_type_from_key returned "tf_" with a trailing underscore.
    """
    entity_id, _ = sensor_mapper.generate_entity_id("tf_ch1", "B0D0")
    assert "__" not in entity_id, f"Double underscore in entity ID: {entity_id}"
    assert entity_id == "sensor.ecowitt_tf_b0d0"


def test_co2_pm25_keys_have_unique_entity_ids(sensor_mapper: SensorMapper):
    """Regression test for issue #182.

    v1.7.0 added pm25_realaqi_co2 and pm25_24haqi_co2 to the WH45/WH46D
    co2 block, but the substring "pm25" in pm25_realaqi_co2 matched the
    generic "pm25" pattern in type_mappings, collapsing it to the same
    sensor_type ("pm25") as pm25_co2 and clobbering the concentration
    entity in the coordinator's sensors_data dict. Same issue for
    pm25_24haqi_co2 vs pm25_24h_co2 via the "pm25_24h" pattern.
    """
    keys = ["pm25_co2", "pm25_24h_co2", "pm25_realaqi_co2", "pm25_24haqi_co2"]
    types = {k: sensor_mapper._extract_sensor_type_from_key(k) for k in keys}
    assert len(set(types.values())) == len(
        keys
    ), f"sensor_type collision among WH45/WH46D co2 PM2.5 keys: {types}"
    entity_ids = {k: sensor_mapper.generate_entity_id(k, "2859")[0] for k in keys}
    assert len(set(entity_ids.values())) == len(
        keys
    ), f"entity_id collision among WH45/WH46D co2 PM2.5 keys: {entity_ids}"


def test_extract_identifier_from_key(sensor_mapper: SensorMapper):
    """Test extracting identifier from key."""
    assert sensor_mapper._extract_identifier_from_key("soilmoisture1") == "ch1"
    assert sensor_mapper._extract_identifier_from_key("temp2f") == "ch2"
    assert sensor_mapper._extract_identifier_from_key("pm25_ch3") == "ch3"
    assert sensor_mapper._extract_identifier_from_key("tempinf") == "indoor"
    assert sensor_mapper._extract_identifier_from_key("tempf") == "outdoor"
    assert sensor_mapper._extract_identifier_from_key("baromrelin") == "relative"
    assert sensor_mapper._extract_identifier_from_key("baromabsin") == "absolute"


def test_get_mapping_stats(sensor_mapper: SensorMapper, mock_sensor_mappings):
    """Test getting mapping statistics."""
    sensor_mapper.update_mapping(mock_sensor_mappings)

    stats = sensor_mapper.get_mapping_stats()
    assert stats["total_sensors"] == 4
    assert stats["mapped_keys"] > 0
    assert stats["sensor_types"] >= 3  # WH51, WH41, WH31


def test_get_all_hardware_ids(sensor_mapper: SensorMapper, mock_sensor_mappings):
    """Test getting all hardware IDs."""
    sensor_mapper.update_mapping(mock_sensor_mappings)

    hardware_ids = sensor_mapper.get_all_hardware_ids()
    assert "D8174" in hardware_ids
    assert "D8648" in hardware_ids
    assert "EF891" in hardware_ids
    assert "A7C42" in hardware_ids
    assert len(hardware_ids) == 4


def test_empty_mapping(sensor_mapper: SensorMapper):
    """Test behavior with empty mapping."""
    sensor_mapper.update_mapping([])

    assert sensor_mapper.get_hardware_id("soilmoisture1") is None
    assert sensor_mapper.get_sensor_info("D8174") is None
    assert len(sensor_mapper.get_all_hardware_ids()) == 0

    stats = sensor_mapper.get_mapping_stats()
    assert stats["total_sensors"] == 0
    assert stats["mapped_keys"] == 0


def test_invalid_sensor_data(sensor_mapper: SensorMapper):
    """Test handling invalid sensor data."""
    invalid_mappings = [
        {"id": "", "type": "WH51", "channel": "1"},  # Empty ID
        {"type": "WH51", "channel": "1"},  # Missing ID
        {"id": "D8174"},  # Missing type and channel
    ]

    sensor_mapper.update_mapping(invalid_mappings)

    # Should handle gracefully without crashing
    stats = sensor_mapper.get_mapping_stats()
    assert stats["total_sensors"] >= 0


def test_placeholder_hardware_ids_filtered(sensor_mapper: SensorMapper):
    """Test that FFFFFFFF and FFFFFFFE placeholder IDs are filtered out.

    Page 2 of sensors_info lists unconnected sensor slots with FFFFFFFF/FFFFFFFE.
    These should not pollute the hardware mapping.
    """
    mappings = [
        {
            "id": "4108",
            "img": "wh51",
            "name": "Soil moisture CH1",
            "batt": "1",
            "signal": "4",
        },
        {
            "id": "FFFFFFFF",
            "img": "wh51",
            "name": "Soil moisture CH2",
            "batt": "1",
            "signal": "4",
        },
        {
            "id": "FFFFFFFE",
            "img": "wh51",
            "name": "Soil moisture CH3",
            "batt": "1",
            "signal": "4",
        },
    ]

    sensor_mapper.update_mapping(mappings)

    # Only the real sensor should be mapped
    assert sensor_mapper.get_hardware_id("soilmoisture1") == "4108"
    assert sensor_mapper.get_hardware_id("soiltemp1") == "4108"
    assert sensor_mapper.get_hardware_id("soilec1") == "4108"
    assert sensor_mapper.get_sensor_info("4108") is not None

    # Placeholder IDs should be filtered out entirely
    assert sensor_mapper.get_sensor_info("FFFFFFFF") is None
    assert sensor_mapper.get_sensor_info("FFFFFFFE") is None
    assert sensor_mapper.get_hardware_id("soilmoisture2") is None
    assert sensor_mapper.get_hardware_id("soilmoisture3") is None

    # Only 1 real sensor in the mapping
    assert len(sensor_mapper.get_all_hardware_ids()) == 1


def test_wh80_sensor_mapping():
    """Test WH80/WS80 wind/solar station sensor mapping (issue #23)."""
    mapper = SensorMapper()

    ws80_sensors = [
        {
            "id": "A1B2C3",
            "img": "wh80",
            "name": "Temp & Humidity & Solar & Wind",
            "batt": "0",
            "signal": "4",
        }
    ]

    mapper.update_mapping(ws80_sensors)

    # Wind hex IDs must be mapped (these were broken before the fix)
    assert mapper.get_hardware_id("0x0A") == "A1B2C3"  # Wind Direction
    assert mapper.get_hardware_id("0x0B") == "A1B2C3"  # Wind Speed
    assert mapper.get_hardware_id("0x0C") == "A1B2C3"  # Wind Gust
    assert mapper.get_hardware_id("0x6D") == "A1B2C3"  # Wind Direction Avg

    # Other WS80 sensors
    assert mapper.get_hardware_id("0x02") == "A1B2C3"  # Temperature
    assert mapper.get_hardware_id("0x07") == "A1B2C3"  # Humidity
    assert mapper.get_hardware_id("0x15") == "A1B2C3"  # Solar Radiation
    assert mapper.get_hardware_id("0x17") == "A1B2C3"  # UV Index
    assert mapper.get_hardware_id("wh80batt") == "A1B2C3"  # Battery

    # WS80 must NOT map rain hex IDs
    assert mapper.get_hardware_id("0x0D") != "A1B2C3"  # No rain event
    assert mapper.get_hardware_id("0x0E") != "A1B2C3"  # No rain rate

    sensor_info = mapper.get_sensor_info("A1B2C3")
    assert sensor_info is not None
    assert sensor_info["sensor_type"] == "WH80"


def test_wh80_name_string_detection():
    """Test that WS80 is detected by its name string (issue #23 fallback)."""
    mapper = SensorMapper()

    # Some gateways may report with a slightly different img field
    ws80_sensors = [
        {
            "id": "DEADBE",
            "img": "ws80",
            "name": "Temp & Humidity & Solar & Wind",
            "batt": "0",
            "signal": "4",
        }
    ]

    mapper.update_mapping(ws80_sensors)
    assert mapper.get_hardware_id("0x0B") == "DEADBE"
    assert mapper.get_hardware_id("0x0A") == "DEADBE"


def test_wh90_still_maps_rain_after_wh80_addition():
    """Ensure WH90 (which includes rain) is not broken by the WH80 elif addition."""
    mapper = SensorMapper()

    wh90_sensors = [
        {
            "id": "FF1234",
            "img": "wh90",
            "name": "Temp & Humidity & Solar & Wind & Rain",
            "batt": "0",
            "signal": "4",
        }
    ]

    mapper.update_mapping(wh90_sensors)
    assert mapper.get_hardware_id("0x0D") == "FF1234"  # Rain Event
    assert mapper.get_hardware_id("0x0E") == "FF1234"  # Rain Rate
    assert mapper.get_hardware_id("0x0B") == "FF1234"  # Wind Speed
    assert mapper.get_hardware_id("wh90batt") == "FF1234"


def test_wh69_sensor_mapping():
    """Test WH69 7-in-1 weather station sensor mapping."""
    mapper = SensorMapper()

    # WH69 sensor data based on user issue #3
    wh69_sensors = [
        {
            "id": "BB",
            "img": "wh69",
            "name": "Temp & Humidity & Solar & Wind & Rain",
            "batt": "0",
            "signal": "4",
        }
    ]

    mapper.update_mapping(wh69_sensors)

    # Check hardware ID mapping
    assert mapper.get_hardware_id("0x02") == "BB"  # Temperature
    assert mapper.get_hardware_id("0x07") == "BB"  # Humidity
    assert mapper.get_hardware_id("0x0B") == "BB"  # Wind speed
    assert mapper.get_hardware_id("0x15") == "BB"  # Solar radiation
    assert mapper.get_hardware_id("0x17") == "BB"  # UV index
    assert mapper.get_hardware_id("wh69batt") == "BB"  # Battery

    # Check sensor info
    sensor_info = mapper.get_sensor_info("BB")
    assert sensor_info is not None
    assert sensor_info["sensor_type"] == "WH69"
    assert sensor_info["hardware_id"] == "BB"

    # Test entity ID generation for WH69 hex sensors
    entity_id, friendly_name = mapper.generate_entity_id("0x02", "BB")
    assert "bb" in entity_id.lower()
    assert friendly_name == "Outdoor Temperature"


def test_wh65_wh90_conflict_prefers_stronger_signal():
    """When a stale WH65/WH69 slot and an active WH90 share common_list hex IDs,
    the mapping must go to the sensor with the stronger signal regardless of
    iteration order — otherwise live data leaks onto a phantom device.

    Reproduces issue #155: after v1.6.17 enabled multi-page sensor fetching,
    a stale WH65 slot left over from a previously paired weather station was
    pulled in alongside the active WH90, splitting WH90's entities across two
    devices.
    """
    # Stale WH65 slot first (signal=0 because it stopped transmitting),
    # active WH90 second.
    stale_first = [
        {
            "id": "EA1234",
            "img": "wh69",  # WH65 reports img=wh69
            "name": "Temp & Humidity & Solar & Wind & Rain",
            "batt": "0",
            "signal": "0",
        },
        {
            "id": "FF9988",
            "img": "wh90",
            "name": "Temp & Humidity & Solar & Wind & Rain",
            "batt": "0",
            "signal": "4",
        },
    ]
    mapper = SensorMapper()
    mapper.update_mapping(stale_first)
    for shared_key in ("0x02", "0x07", "0x0B", "0x15", "0x17", "0x0D", "0x13"):
        assert mapper.get_hardware_id(shared_key) == "FF9988"
    # Each device's unique battery key still resolves to its own hardware ID.
    assert mapper.get_hardware_id("wh69batt") == "EA1234"
    assert mapper.get_hardware_id("wh90batt") == "FF9988"

    # Reverse order — active WH90 first, stale WH65 last. The dict-overwrite
    # default would let the stale slot win; the signal-priority guard keeps
    # the active sensor.
    stale_last = [stale_first[1], stale_first[0]]
    mapper = SensorMapper()
    mapper.update_mapping(stale_last)
    for shared_key in ("0x02", "0x07", "0x0B", "0x15", "0x17", "0x0D", "0x13"):
        assert mapper.get_hardware_id(shared_key) == "FF9988"
    assert mapper.get_hardware_id("wh69batt") == "EA1234"
    assert mapper.get_hardware_id("wh90batt") == "FF9988"


def test_conflict_with_equal_signals_higher_priority_wins():
    """When two sensors claim the same key with equal signal strength, the
    higher-priority sensor wins per Ecowitt's documented order (issue #203).
    WH90 (priority 3) beats WH69 (priority 1) regardless of iteration order,
    eliminating the flip-flop that triggered unit-change repair notifications
    in Home Assistant (issue #192).
    """
    sensors = [
        {
            "id": "AAA111",
            "img": "wh69",
            "name": "Temp & Humidity & Solar & Wind & Rain",
            "batt": "0",
            "signal": "3",
        },
        {
            "id": "BBB222",
            "img": "wh90",
            "name": "Temp & Humidity & Solar & Wind & Rain",
            "batt": "0",
            "signal": "3",
        },
    ]
    mapper = SensorMapper()
    mapper.update_mapping(sensors)
    assert mapper.get_hardware_id("0x02") == "BBB222"

    # Reversed order: WH90 still wins because priority overrides iteration order.
    mapper2 = SensorMapper()
    mapper2.update_mapping(list(reversed(sensors)))
    assert mapper2.get_hardware_id("0x02") == "BBB222"


def test_conflict_with_equal_signal_wn32_beats_wh90():
    """WH26/WN32 (priority 4) beats WH90/WS90 (priority 3) at equal signal per
    Ecowitt's documented sensor priority order for outdoor measurements (issue #203).
    The result is deterministic regardless of which sensor appears first in the
    get_sensors_info response.
    """
    wh90 = {
        "id": "6530",
        "img": "wh90",
        "name": "Temp & Humidity & Solar & Wind & Rain",
        "batt": "0",
        "signal": "4",
    }
    wh32 = {
        "id": "A9",
        "img": "wh26",
        "name": "Outdoor T&H",
        "batt": "0",
        "signal": "4",
    }

    # WH90 appears first — WN32/WH26 should still win on priority.
    mapper = SensorMapper()
    mapper.update_mapping([wh90, wh32])
    assert mapper.get_hardware_id("0x02") == "A9"
    assert mapper.get_hardware_id("0x07") == "A9"
    assert mapper.get_hardware_id("0x03") == "A9"

    # Reversed order — same result.
    mapper2 = SensorMapper()
    mapper2.update_mapping([wh32, wh90])
    assert mapper2.get_hardware_id("0x02") == "A9"

    # Second poll with reversed order: priority still determines winner.
    mapper.update_mapping([wh32, wh90])
    assert mapper.get_hardware_id("0x02") == "A9"
    assert mapper.get_hardware_id("0x07") == "A9"
    assert mapper.get_hardware_id("0x03") == "A9"

    # If the WN32 drops out entirely, WH90 takes over.
    mapper.update_mapping([wh90])
    assert mapper.get_hardware_id("0x02") == "6530"


def test_sensor_priority_dead_high_priority_does_not_block_lower():
    """A higher-priority sensor with signal=0 must not block a lower-priority but
    active sensor from claiming shared keys — signal strength always beats priority.
    """
    mapper = SensorMapper()
    mapper.update_mapping(
        [
            {
                "id": "DEAD01",
                "img": "wh26",  # priority=4 but signal=0
                "name": "Outdoor T&H",
                "batt": "0",
                "signal": "0",
            },
            {
                "id": "LIVE02",
                "img": "wh90",  # priority=3 but signal=4
                "name": "Temp & Humidity & Solar & Wind & Rain",
                "batt": "0",
                "signal": "4",
            },
        ]
    )
    assert mapper.get_hardware_id("0x02") == "LIVE02"
    assert mapper.get_hardware_id("0x07") == "LIVE02"


def test_sensor_priority_equal_priority_stable_tiebreak():
    """Two sensors with identical priority use the stable tie-break (previous poll
    owner keeps the key) rather than flipping on every poll (issue #197 pattern).
    """
    sensor_a = {
        "id": "AAAA",
        "img": "wh90",
        "name": "Temp & Humidity & Solar & Wind & Rain",
        "batt": "0",
        "signal": "4",
    }
    sensor_b = {
        "id": "BBBB",
        "img": "wh90",
        "name": "Temp & Humidity & Solar & Wind & Rain",
        "batt": "0",
        "signal": "4",
    }

    mapper = SensorMapper()
    mapper.update_mapping([sensor_a, sensor_b])
    first_winner = mapper.get_hardware_id("0x02")

    # Second poll with reversed order — previous winner keeps the key.
    mapper.update_mapping([sensor_b, sensor_a])
    assert mapper.get_hardware_id("0x02") == first_winner


def test_conflict_with_unparseable_signal_does_not_crash():
    """A non-numeric signal field must not abort the mapping update — the
    sensor is still registered and competes with signal=-1 (lowest priority).
    """
    mapper = SensorMapper()
    mapper.update_mapping(
        [
            {
                "id": "GOOD01",
                "img": "wh90",
                "name": "Temp & Humidity & Solar & Wind & Rain",
                "batt": "0",
                "signal": "4",
            },
            {
                "id": "BAD002",
                "img": "wh69",
                "name": "Temp & Humidity & Solar & Wind & Rain",
                "batt": "0",
                "signal": "--",
            },
        ]
    )
    assert mapper.get_hardware_id("0x02") == "GOOD01"
    # The malformed-signal sensor still gets registered in sensor_info.
    assert mapper.get_sensor_info("BAD002") is not None


def test_wh54_generates_lds_keys():
    """WH54 sensor type produces lds_*_ch{N} keys for the channel (issue #164)."""
    mapper = SensorMapper()
    keys = mapper._generate_live_data_keys("WH54", "2")
    assert "lds_air_ch2" in keys
    assert "lds_depth_ch2" in keys
    assert "lds_voltage_ch2" in keys
    assert "lds_batt2" in keys
    assert "lds_level_ch2" in keys
    assert "lds_total_heat_ch2" in keys


def test_wh54_alias_lds():
    """The 'lds' sensor_type alias maps to the same WH54 keys including diagnostics."""
    mapper = SensorMapper()
    keys = mapper._generate_live_data_keys("lds", "1")
    assert "lds_depth_ch1" in keys
    assert "lds_level_ch1" in keys
    assert "lds_total_heat_ch1" in keys


def test_wh65_uses_wh69_key_list():
    """WH65 with img='wh65' (some firmware variants) maps to the same key list as WH69."""
    mapper = SensorMapper()
    keys_wh65 = mapper._generate_live_data_keys("WH65", "")
    keys_wh69 = mapper._generate_live_data_keys("WH69", "")
    assert keys_wh65 == keys_wh69
    assert "0x07" in keys_wh65  # Outdoor humidity
    assert "0x02" in keys_wh65  # Outdoor temperature
    assert "wh69batt" in keys_wh65  # Battery


def test_wh65_img_wh65_sensor_mapping():
    """WH65 reporting img='wh65' should register the same keys as img='wh69' (issue #187)."""
    mapper = SensorMapper()
    mapper.update_mapping(
        [
            {
                "id": "AB1234",
                "img": "wh65",
                "name": "Temp & Humidity & Solar & Wind & Rain",
                "batt": "0",
                "signal": "4",
            }
        ]
    )
    assert mapper.get_hardware_id("0x02") == "AB1234"
    assert mapper.get_hardware_id("0x07") == "AB1234"
    assert mapper.get_hardware_id("wh69batt") == "AB1234"


def test_wh69_includes_decimal_id_3_and_5():
    """WH69 weather station includes decimal IDs '3' (Feels Like) and '5' (VPD)."""
    mapper = SensorMapper()
    keys = mapper._generate_live_data_keys("WH69", "")
    assert "3" in keys
    assert "5" in keys


def test_wh90_includes_decimal_id_3_and_5():
    """WH90 outdoor station includes decimal IDs '3' and '5' (issue #173)."""
    mapper = SensorMapper()
    keys = mapper._generate_live_data_keys("WH90", "")
    assert "3" in keys
    assert "5" in keys


def test_ws90_includes_decimal_id_3_and_5():
    """WS90 outdoor station includes decimal IDs '3' and '5'."""
    mapper = SensorMapper()
    keys = mapper._generate_live_data_keys("WS90", "")
    assert "3" in keys
    assert "5" in keys


def test_piezo_devices_include_hourly_rain():
    """WH90, WS90, and WS85 include 0x7D (hourly rain) from piezoRain block (issue #205)."""
    mapper = SensorMapper()
    for sensor_type in ("WH90", "WS90", "wh85"):
        keys = mapper._generate_live_data_keys(sensor_type, "")
        assert "0x7D" in keys, f"{sensor_type} should include 0x7D (hourly rain)"


def test_wh80_includes_decimal_id_3_and_5():
    """WH80 wind/solar station includes decimal IDs '3' and '5'."""
    mapper = SensorMapper()
    keys = mapper._generate_live_data_keys("WH80", "")
    assert "3" in keys
    assert "5" in keys


def test_decimal_id_entity_id_generation():
    """Decimal IDs generate proper entity IDs and friendly names."""
    mapper = SensorMapper()
    eid_3, name_3 = mapper.generate_entity_id("3", "ABC123")
    assert eid_3 == "sensor.ecowitt_feels_like_temp_abc123"
    assert name_3 == "Feels Like Temperature"

    eid_5, name_5 = mapper.generate_entity_id("5", "ABC123")
    assert eid_5 == "sensor.ecowitt_vpd_abc123"
    assert name_5 == "Vapor Pressure Deficit"


def test_wh41_includes_aqi_keys():
    """WH41 PM2.5 sensor includes the new AQI keys (issue #158)."""
    mapper = SensorMapper()
    keys = mapper._generate_live_data_keys("WH41", "1")
    assert "pm25_aqi_realtime_ch1" in keys
    assert "pm25_aqi_24h_ch1" in keys


def test_pm25_aqi_entity_id_generation():
    """PM2.5 AQI keys generate distinct entity IDs (no collision with concentration)."""
    mapper = SensorMapper()
    eid_real, _ = mapper.generate_entity_id("pm25_aqi_realtime_ch1", "EF891")
    eid_24h, _ = mapper.generate_entity_id("pm25_aqi_24h_ch1", "EF891")
    eid_pm25, _ = mapper.generate_entity_id("pm25_ch1", "EF891")
    assert eid_real == "sensor.ecowitt_pm25_aqi_realtime_ef891"
    assert eid_24h == "sensor.ecowitt_pm25_aqi_24h_ef891"
    assert eid_pm25 == "sensor.ecowitt_pm25_ef891"
    assert len({eid_real, eid_24h, eid_pm25}) == 3


def test_duplicate_hardware_id_creates_channel_specific_unique_ids():
    """Two WN31 sensors on different channels that share the same hardware ID
    must each get a distinct unique_id so both appear as separate HA devices
    and entities (issue #211).

    Without the fix, _sensor_info[hardware_id] is overwritten by the second
    channel, and both channels end up with the same entity ID — only one
    appears in HA.
    """
    mapper = SensorMapper()
    mapper.update_mapping(
        [
            {
                "id": "B8",
                "img": "wh31",
                "name": "Temp & Humidity CH3",
                "type": "8",  # WH31 CH3: type - 5 = 3
                "batt": "0",
                "signal": "4",
            },
            {
                "id": "B8",  # Same hardware ID as CH3
                "img": "wh31",
                "name": "Temp & Humidity CH5",
                "type": "10",  # WH31 CH5: type - 5 = 5
                "batt": "0",
                "signal": "3",
            },
        ]
    )

    # Both channels must have distinct unique_ids
    uid_ch3 = mapper.get_hardware_id("temp3f")
    uid_ch5 = mapper.get_hardware_id("temp5f")
    assert uid_ch3 == "B8_ch3"
    assert uid_ch5 == "B8_ch5"
    assert uid_ch3 != uid_ch5

    # Both channels must have their own sensor_info entries
    info_ch3 = mapper.get_sensor_info("B8_ch3")
    info_ch5 = mapper.get_sensor_info("B8_ch5")
    assert info_ch3 is not None
    assert info_ch5 is not None
    assert info_ch3["channel"] == "3"
    assert info_ch5["channel"] == "5"
    # The original hardware_id is preserved inside the entry
    assert info_ch3["hardware_id"] == "B8"
    assert info_ch5["hardware_id"] == "B8"

    # get_all_hardware_ids returns both composite IDs
    all_ids = mapper.get_all_hardware_ids()
    assert "B8_ch3" in all_ids
    assert "B8_ch5" in all_ids
    assert "B8" not in all_ids  # plain ID must NOT exist as a key

    # Entity IDs are distinct
    eid_ch3, _ = mapper.generate_entity_id("temp3f", uid_ch3)
    eid_ch5, _ = mapper.generate_entity_id("temp5f", uid_ch5)
    assert eid_ch3 == "sensor.ecowitt_temperature_b8_ch3"
    assert eid_ch5 == "sensor.ecowitt_temperature_b8_ch5"
    assert eid_ch3 != eid_ch5

    # Humidity and battery keys are also routed to the correct channel
    assert mapper.get_hardware_id("humidity3") == "B8_ch3"
    assert mapper.get_hardware_id("humidity5") == "B8_ch5"
    assert mapper.get_hardware_id("batt3") == "B8_ch3"
    assert mapper.get_hardware_id("batt5") == "B8_ch5"


def test_duplicate_hardware_id_channel_extracted_from_type():
    """Duplicate-ID detection works when the channel comes from the type enum
    (custom sensor name without 'CH{n}' pattern, e.g. on GW3000A).
    """
    mapper = SensorMapper()
    mapper.update_mapping(
        [
            {
                "id": "FF",
                "img": "wh31",
                "name": "Bedroom",  # custom name, no CH{n}
                "type": "8",  # WH31 CH3
                "batt": "0",
                "signal": "4",
            },
            {
                "id": "FF",  # Same ID
                "img": "wh31",
                "name": "Kitchen",  # custom name, no CH{n}
                "type": "10",  # WH31 CH5
                "batt": "0",
                "signal": "4",
            },
        ]
    )

    assert mapper.get_hardware_id("temp3f") == "FF_ch3"
    assert mapper.get_hardware_id("temp5f") == "FF_ch5"
    info3 = mapper.get_sensor_info("FF_ch3")
    info5 = mapper.get_sensor_info("FF_ch5")
    assert info3 is not None and info3["channel"] == "3"
    assert info5 is not None and info5["channel"] == "5"


def test_non_duplicate_hardware_id_unchanged():
    """Normal sensors (no duplicate hardware ID) continue to use the plain
    hardware_id as their unique_id — no regression.
    """
    mapper = SensorMapper()
    mapper.update_mapping(
        [
            {
                "id": "A7C42",
                "img": "wh31",
                "name": "Temp & Humidity CH1",
                "type": "6",
                "batt": "0",
                "signal": "4",
            },
            {
                "id": "B3D99",
                "img": "wh31",
                "name": "Temp & Humidity CH2",
                "type": "7",
                "batt": "0",
                "signal": "4",
            },
        ]
    )

    # Plain hardware_ids — no channel suffix
    assert mapper.get_hardware_id("temp1f") == "A7C42"
    assert mapper.get_hardware_id("temp2f") == "B3D99"
    assert mapper.get_sensor_info("A7C42") is not None
    assert mapper.get_sensor_info("B3D99") is not None
