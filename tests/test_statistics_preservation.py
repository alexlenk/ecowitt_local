"""Keep existing Recorder history and statistics when names switch to German."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import partial
from unittest.mock import patch

import pytest
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    get_metadata,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
    do_adhoc_statistics,
)

from custom_components.ecowitt_local.const import DOMAIN
from tests.test_entity_naming import _aisle, _set_gateway, _wh31
from tests.test_localization import _catalog


@pytest.fixture
def mock_recorder_before_hass(recorder_db_url):
    """Prepare SQLite before this project's automatic hass fixture is created."""


@pytest.mark.parametrize("language", ["de", "fr", "da", "it"])
@pytest.mark.parametrize("persistent_database", [True])
async def test_language_reload_preserves_history_and_long_term_statistics(
    recorder_mock,
    hass: HomeAssistant,
    mock_config_entry,
    mock_ecowitt_api,
    language,
):
    """A real SQLite database retains a renamed sensor's existing statistic ID."""
    # Recorder's fixture must initialize before hass; no recorder/database calls
    # are mocked. Only the weather gateway's network API is replaced.
    await hass.async_start()
    hass.config.language = "en"
    translated_temperature = _catalog(f"translations/{language}.json")["entity"][
        "sensor"
    ]["temperature"]["name"]
    mock_config_entry.add_to_hass(hass)
    devices = dr.async_get(hass)
    device = devices.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "D1E2F3")},
        name="Ecowitt Temperature/Humidity Sensor D1E2F3",
    )
    devices.async_update_device(device.id, name_by_user="Freezer")
    registry = er.async_get(hass)
    previous = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{DOMAIN}_D1E2F3_temp2f",
        suggested_object_id="freezer_probe",
        config_entry=mock_config_entry,
        device_id=device.id,
        original_name="Temperature",
    )
    entity_id = previous.entity_id
    assert entity_id == "sensor.freezer_probe"
    historical_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    async_import_statistics(
        hass,
        {
            "statistic_id": entity_id,
            "source": "recorder",
            "name": None,
            "unit_class": "temperature",
            "unit_of_measurement": "°C",
            "mean_type": StatisticMeanType.ARITHMETIC,
            "has_sum": False,
        },
        [
            {"start": historical_start, "mean": 20.0, "min": 19.0, "max": 21.0},
            {
                "start": historical_start + timedelta(hours=1),
                "mean": 21.0,
                "min": 20.0,
                "max": 22.0,
            },
        ],
    )
    await async_wait_recording_done(hass)

    async def stored_statistics():
        """Query the actual metadata row and hourly samples in SQLite."""
        metadata = await recorder_mock.async_add_executor_job(
            partial(get_metadata, hass, statistic_ids={entity_id})
        )
        rows = await recorder_mock.async_add_executor_job(
            statistics_during_period,
            hass,
            historical_start,
            historical_start + timedelta(hours=2),
            {entity_id},
            "hour",
            None,
            {"mean", "min", "max"},
        )
        return metadata, rows

    before = await stored_statistics()
    assert set(before[0]) == {entity_id}
    metadata_id, metadata = before[0][entity_id]
    assert isinstance(metadata_id, int)
    assert metadata["statistic_id"] == entity_id
    assert metadata["unit_of_measurement"] == "°C"
    assert [row["mean"] for row in before[1][entity_id]] == [20.0, 21.0]

    mock_ecowitt_api.get_units.return_value = {"temperature": "0"}
    _set_gateway(
        mock_ecowitt_api,
        [_wh31("D1E2F3", 2)],
        {"ch_aisle": [_aisle(2, "21.5")]},
    )
    history_start = dt_util.utcnow() - timedelta(seconds=1)
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
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_wait_recording_done(hass)
        english = hass.states.get(entity_id)
        assert english is not None
        assert english.attributes["friendly_name"] == "Freezer Temperature"
        numerical_properties = (
            english.state,
            english.attributes["unit_of_measurement"],
            english.attributes["state_class"],
            english.attributes["device_class"],
        )
        assert numerical_properties == ("21.5", "°C", "measurement", "temperature")
        assert await stored_statistics() == before

        hass.config.language = language
        assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        await async_wait_recording_done(hass)

    german = hass.states.get(entity_id)
    assert german is not None
    assert german.attributes["friendly_name"] == f"Freezer {translated_temperature}"
    assert (
        german.state,
        german.attributes["unit_of_measurement"],
        german.attributes["state_class"],
        german.attributes["device_class"],
    ) == numerical_properties
    upgraded = registry.async_get(entity_id)
    assert upgraded is not None
    assert (upgraded.id, upgraded.unique_id, upgraded.device_id) == (
        previous.id,
        previous.unique_id,
        previous.device_id,
    )
    assert registry.async_get("sensor.ecowitt_temperature_d1e2f3") is None
    assert devices.async_get(device.id).name_by_user == "Freezer"
    # The DB metadata primary key, statistic_id, unit, and both saved hourly
    # samples must all remain identical after the real integration reload.
    assert await stored_statistics() == before

    # Let HA's real sensor statistics compiler append a new sample after the
    # translation change. It must reuse the existing metadata row/series.
    statistics_start = dt_util.utcnow().replace(second=0, microsecond=0)
    statistics_start -= timedelta(minutes=statistics_start.minute % 5)
    do_adhoc_statistics(hass, start=statistics_start)
    await async_wait_recording_done(hass)
    current_statistics = await recorder_mock.async_add_executor_job(
        statistics_during_period,
        hass,
        statistics_start,
        statistics_start + timedelta(minutes=5),
        {entity_id},
        "5minute",
        None,
        {"mean", "min", "max"},
    )
    assert set(current_statistics) == {entity_id}
    assert len(current_statistics[entity_id]) == 1
    current_sample = current_statistics[entity_id][0]
    assert (
        current_sample["mean"],
        current_sample["min"],
        current_sample["max"],
    ) == pytest.approx((21.5, 21.5, 21.5))
    assert await stored_statistics() == before

    history = await recorder_mock.async_add_executor_job(
        partial(
            get_significant_states,
            hass,
            history_start,
            entity_ids=[entity_id],
            significant_changes_only=False,
        )
    )
    numeric_history = [state for state in history[entity_id] if state.state == "21.5"]
    assert {state.attributes["friendly_name"] for state in numeric_history} >= {
        "Freezer Temperature",
        f"Freezer {translated_temperature}",
    }
    assert all(state.entity_id == entity_id for state in numeric_history)
    assert all(
        state.attributes["unit_of_measurement"] == "°C"
        and state.attributes["state_class"] == "measurement"
        for state in numeric_history
    )
