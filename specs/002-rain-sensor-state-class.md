# Spec 002: Rain Entities Missing `state_class`

**GitHub Issues:** #32, #45
**Status:** OPEN
**Priority:** HIGH — affects all users with rain sensors, all gateway models

---

## Background

After HA 2025.12, all rain sensor entities lost their `state_class` and HA warns:

> "We have generated statistics for 'GW1200A Event Rain' (sensor.gw1200a_event_rain) in the past,
> but it no longer has a state class, therefore, we cannot track long term statistics for it anymore."

Affected sensors confirmed across: GW1200A, GW1000_Pro, WS2900, GW2000B, HP2564.
Affected entity IDs: event rain, rain rate, hourly rain, daily rain, weekly rain, monthly rain, yearly rain.

---

## Root Cause Analysis

### `const.py` — Correct definitions (not the bug)

`const.py` has correct `state_class` values:
```python
"rainratein":   {"state_class": "measurement", "device_class": "precipitation_intensity"}
"eventrainin":  {"state_class": "total", "device_class": "precipitation"}
"hourlyrainin": {"state_class": "total_increasing", "device_class": "precipitation"}
"dailyrainin":  {"state_class": "total_increasing", "device_class": "precipitation"}
# ... etc
```

### `sensor.py` — The Bug

`sensor.py:142-159` sets `state_class` via hardcoded logic that **ignores** `const.py`:

```python
# sensor.py lines 142-159 (THE BUG)
if isinstance(self._attr_native_value, (int, float)):
    if self._category == "battery":
        self._attr_state_class = SensorStateClass.MEASUREMENT
    elif device_class_str in ("temperature", "humidity", "pressure", "wind_speed",
                               "precipitation",  # ← WRONG: sets MEASUREMENT for ALL precipitation
                               "precipitation_intensity", ...):
        self._attr_state_class = SensorStateClass.MEASUREMENT  # ← OVERRIDES correct total_increasing
    elif "total" in self._sensor_key or "yearly" in self._sensor_key:
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
```

This code:
1. Sets `MEASUREMENT` for ALL `precipitation` device class sensors — overriding the correct `total_increasing` for accumulated rain
2. Only catches `total` or `yearly` in the key as a fallback, missing `hourly`, `monthly`, `weekly`, `event`
3. Ignores the `state_class` field already defined in `SENSOR_TYPES`

### Why it worked before HA 2025.12

HA became stricter about `state_class` validation in 2025.12, surfacing the bug that was always there.

---

## Requirements

- [ ] **REQ-002-1:** All rain sensor entities must expose the correct `state_class` matching `SENSOR_TYPES` definitions
- [ ] **REQ-002-2:** `state_class` logic must be driven by data in `SENSOR_TYPES`, not hardcoded by device_class
- [ ] **REQ-002-3:** No regression for non-rain sensors (temperature, humidity, etc.) which correctly use `MEASUREMENT`

---

## Design

### Fix: Read `state_class` from sensor_info, fall back to device_class logic

The sensor entity receives `sensor_info` from the coordinator, which includes metadata from `SENSOR_TYPES`. The fix reads `state_class` from sensor_info first:

```python
# In sensor.py _update_attributes():

# Read state_class from SENSOR_TYPES metadata (comes via sensor_info)
state_class_str = sensor_info.get("state_class")
if state_class_str:
    try:
        self._attr_state_class = SensorStateClass(state_class_str)
    except ValueError:
        self._attr_state_class = None
elif isinstance(self._attr_native_value, (int, float)):
    # Fallback: derive from device_class (only for sensors without explicit state_class)
    if self._category == "battery":
        self._attr_state_class = SensorStateClass.MEASUREMENT
    elif device_class_str in ("temperature", "humidity", "pressure",
                               "wind_speed", "precipitation_intensity",
                               "irradiance", "pm25", "moisture"):
        self._attr_state_class = SensorStateClass.MEASUREMENT
    # precipitation without explicit state_class: no state_class (safer)
```

### Does coordinator pass `state_class` to sensor_info?

Need to verify coordinator's `_process_live_data()` includes `state_class` when assembling sensor dicts from `SENSOR_TYPES`. If not, the coordinator must be updated to include it.

**⚠️ Open Investigation Needed:** Trace coordinator.py to confirm how sensor metadata (name, unit, device_class, state_class) flows into the sensor_info dict returned by `get_sensor_data()`.

### Files to Change
- [sensor.py](../custom_components/ecowitt_local/sensor.py) — `_update_attributes()` state_class logic
- [coordinator.py](../custom_components/ecowitt_local/coordinator.py) — ensure `state_class` is included in sensor data dict (if missing)

---

## Tasks

- [ ] **TASK-002-1:** Trace how sensor metadata flows from `SENSOR_TYPES` → coordinator → sensor entity
- [ ] **TASK-002-2:** Fix `sensor.py` to read `state_class` from sensor_info before falling back to device_class logic
- [ ] **TASK-002-3:** Ensure coordinator includes `state_class` in sensor data dicts
- [ ] **TASK-002-4:** Update tests to assert correct `state_class` on rain entities (MEASUREMENT for rain rate, TOTAL_INCREASING for accumulated rain)
- [ ] **TASK-002-5:** Release and comment on issues #32 and #45

---

## Open Questions / Blockers

- **OPEN:** Does coordinator.py currently pass `state_class` through in the sensor data dict? Must trace before implementing.
- **OPEN:** HA stats database already has entries with wrong `state_class`. After fix, HA will ask users to either delete old stats or accept the new class. Should we document a migration note?
