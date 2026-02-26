# Spec 018: WH57 Lightning Strikes and Timestamp Entities Missing

**GitHub Issue:** #19 (WH31 Celsius raw value is converting to Fahrenheit)
**Status:** ✅ FIXED — v1.5.31
**Priority:** HIGH — strikes count and last-lightning timestamp never appear as entities

---

## Background

User reports WH57 lightning sensor is connected and working (distance entity visible, battery entity
visible), but the **Lightning Strikes** (count) and **Last Lightning** (timestamp) entities never
appear in Home Assistant — even after storms with non-zero strike counts.

> *WH57 JSON: `{"distance": "8 km", "date": "2026-02-26T20:40:36", "count": "7", "battery": "5"}`*
> *"The count entity has not appeared in HA."*

Screenshot confirms: only **Lightning Distance** and **Lightning Sensor Battery** are visible.

---

## Root Cause

### Entity ID Collision in `_extract_sensor_type_from_key`

`sensor_mapper.py:_extract_sensor_type_from_key()` uses substring matching against the sensor key
to derive a human-readable type name for the entity_id. The `type_mappings` dict contains:

```python
"lightning": "lightning",
```

All three lightning sensor keys contain the substring `"lightning"`:
- `"lightning_num"` → matches `"lightning"` → `sensor_type_name = "lightning"`
- `"lightning_time"` → matches `"lightning"` → `sensor_type_name = "lightning"`
- `"lightning"` → matches `"lightning"` → `sensor_type_name = "lightning"`

All three therefore generate **the same entity_id**:
```
sensor.ecowitt_lightning_{hardware_id}
```

The coordinator processes items in this order:
1. `{"id": "lightning_num", ...}` → writes `sensors_data["sensor.ecowitt_lightning_{hw}"]`
2. `{"id": "lightning_time", ...}` → **overwrites** the same key
3. `{"id": "lightning", ...}` → **overwrites** again

Result: only the **distance** entity survives (it's processed last). Strikes and timestamp are
silently discarded.

### Secondary: `lightning_time` datetime handling

The gateway returns `"date": "2026-02-22T18:00:18"` — a naive ISO 8601 string (no timezone).
HA's `SensorDeviceClass.TIMESTAMP` requires a timezone-aware `datetime` object. The coordinator
returns this as a raw string; sensor.py must convert it before assigning to `native_value`.

---

## Requirements

- **REQ-018-1:** `lightning_num` entity must have a unique entity_id (e.g., `sensor.ecowitt_lightning_strikes_{hw}`)
- **REQ-018-2:** `lightning_time` entity must have a unique entity_id (e.g., `sensor.ecowitt_last_lightning_{hw}`)
- **REQ-018-3:** `lightning` distance entity must keep its existing entity_id `sensor.ecowitt_lightning_{hw}` (no breaking change)
- **REQ-018-4:** `lightning_time` native_value must be a timezone-aware `datetime` object
- **REQ-018-5:** No regression for distance or battery entities

---

## Design

### Fix 1: `sensor_mapper.py` — add specific patterns before generic `"lightning"`

In `_extract_sensor_type_from_key()`, add the more-specific substrings before `"lightning"`:

```python
type_mappings = {
    ...
    "lightning_num": "lightning_strikes",     # Must precede "lightning"
    "lightning_time": "last_lightning",       # Must precede "lightning"
    "lightning_mi": "lightning_distance_mi",  # Must precede "lightning"
    "lightning": "lightning",                 # km distance — entity_id preserved
    ...
}
```

Resulting entity_ids:
- `lightning_num` → `sensor.ecowitt_lightning_strikes_{hw}` (NEW — was never created before)
- `lightning_time` → `sensor.ecowitt_last_lightning_{hw}` (NEW — was never created before)
- `lightning` → `sensor.ecowitt_lightning_{hw}` (UNCHANGED — existing users unaffected)
- `wh57batt` → `sensor.ecowitt_lightning_battery_{hw}` (UNCHANGED)

### Fix 2: `sensor.py` — convert naive datetime string for timestamp sensors

In `_update_attributes()`, after setting `self._attr_native_value`, add:

```python
if device_class_str == "timestamp" and isinstance(self._attr_native_value, str):
    from datetime import timezone as tz
    try:
        dt = datetime.fromisoformat(self._attr_native_value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.utc)
        self._attr_native_value = dt
    except (ValueError, TypeError):
        self._attr_native_value = None
```

---

## Files to Change

- [sensor_mapper.py](../custom_components/ecowitt_local/sensor_mapper.py) — fix `_extract_sensor_type_from_key`
- [sensor.py](../custom_components/ecowitt_local/sensor.py) — fix timestamp handling
- [tests/test_weather_devices.py](../tests/test_weather_devices.py) — update WH57 entity_id assertions

---

## Tasks

- [x] **TASK-018-1:** Root cause identified (entity_id collision)
- [x] **TASK-018-2:** Fix `_extract_sensor_type_from_key` in `sensor_mapper.py`
- [x] **TASK-018-3:** Fix timestamp handling in `sensor.py`
- [x] **TASK-018-4:** Update tests to assert new, correct entity_ids
- [x] **TASK-018-5:** Release
