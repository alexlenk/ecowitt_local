# Spec 009: WS90 / GW2000 / GW3000 — Incomplete or Unavailable Entities

**GitHub Issues:** #5, #40, #15, #41 (partial)
**Status:** 🟡 Partial — most issues fixed through v1.5.21; entity-ID mismatch being fixed in v1.5.23
**Priority:** HIGH — affects many users with GW2000/GW3000 + WS90/WH90 combination

---

## Background

Users with GW2000 or GW3000 gateways + WS90/WH90 outdoor sensor consistently report:
- WS90/WH90 device created but most entities show "unavailable" or are never created
- Gateway device only shows a small subset of expected entities (9 instead of 20+)
- Some gateway sensors incorrectly show values like 160°F instead of ~74°F
- Sensors populate at startup/reload but then freeze (stop updating)

Representative reports:
- **@timnis (GW2000 + WS90):** "9 entities each even with 'Include Inactive Sensors'" — both gateway and WS90 severely truncated
- **@nicokars (GW3000):** Same — confirmed with screenshot
- **@darrendavid:** "My gateway temp is showing as over 160 degrees when the web UI reads 74.1F"
- **@nmaster2042 (GW2000 + WH90):** "Sensors populate at start but freeze — wind, UV, radiation stuck. Only humidity and dewpoint update."

---

## Known Live Data Structure (GW2000 + WH90, FW 3.2.9)

From user-provided `get_livedata_info` (@nmaster2042, GW2000 FW 3.2.9):

```json
{
  "common_list": [
    {"id": "0x02", "val": "9.1",  "unit": "C"},
    {"id": "0x07", "val": "94%"},
    {"id": "4",    "val": "7.4",  "unit": "C"},   ← apparent temperature
    {"id": "5",    "val": "0.069 kPa"},            ← vapor pressure deficit
    {"id": "0x03", "val": "8.2",  "unit": "C"},
    {"id": "0x0B", "val": "1.7 m/s"},
    {"id": "0x0C", "val": "2.7 m/s"},
    {"id": "0x19", "val": "6.0 m/s"},
    {"id": "0x15", "val": "0.00 W/m2"},
    {"id": "0x17", "val": "0"},
    {"id": "0x0A", "val": "351"},
    {"id": "0x6D", "val": "21"}
  ],
  "piezoRain": [
    {"id": "srain_piezo", "val": "0"},
    {"id": "0x0D", "val": "2.4 mm"},
    {"id": "0x0E", "val": "0.0 mm/Hr"},
    {"id": "0x7C", "val": "2.8 mm"},
    {"id": "0x10", "val": "1.0 mm"},
    {"id": "0x11", "val": "61.1 mm"},
    {"id": "0x12", "val": "136.7 mm"},
    {"id": "0x13", "val": "244.8 mm", "battery": "5", "voltage": "3.04", "ws90cap_volt": "4.2", "ws90_ver": "115"}
  ],
  "wh25": [{"intemp": "15.5", "unit": "C", "inhumi": "63%", "abs": "1012.4 hPa", "rel": "1012.4 hPa"}],
  "debug": [{"heap": "134032", "runtime": "79710", "usr_interval": "60", "is_cnip": false}]
}
```

Note: GW2000 FW 3.2.9 sends hex IDs with embedded units (`"1.7 m/s"`, `"94%"`) but also sends `"unit"` for temperature IDs. Humidity comes as `"94%"` (no space).

From `get_sensors_info` (@nmaster2042):
- WH90 hardware ID `4094A8` IS returned (only visible on page 1, @nmaster2042 initially confused by page 1 vs page 2 split)
- `{"img": "wh90", "type": "48", "name": "Temp & Humidity & Solar & Wind & Rain", "id": "4094A8", "batt": "5", "signal": "4"}`

From `get_sensors_info` (older data, @Rakkzi, GW2000 + WS90):
```json
[{"img": "wh90", "type": "48", "name": "Temp & Humidity & Solar & Wind & Rain", "id": "A238", "batt": "3"}]
```

---

## Root Cause Analysis

### ✅ Issue 1 (FIXED v1.5.x): `"89%"` / `"94%"` — percent sign without space

The humidity key `0x07` sends `"89%"` or `"94%"` (no space before `%`). Fixed in coordinator `_process_live_data` unit extraction via regex.

### ✅ Issue 4 (FIXED v1.5.19): `wh25` indoor temperature wrong unit

The `wh25` block sends `"unit": "F"` or `"unit": "C"`. Fixed by passing the `unit` field through the sensor item dict.

### 🔴 Issue 5 (CONFIRMED — fixed in v1.5.23): Entity ID format mismatch → sensors freeze

**Confirmed by @nmaster2042's debug log (2026-02-21).**

When the `hex_to_name` mapping was added to `_extract_sensor_type_from_key`, entity IDs changed format:
- **Old format (entity registry):** `sensor.ecowitt_0x0b_4094a8`
- **New format (coordinator data):** `sensor.ecowitt_wind_speed_4094a8`

Users who had entities registered under the old format keep those entity IDs in their HA entity registry (HA matches by `unique_id` and preserves the registered entity ID). When `_handle_coordinator_update` calls `get_sensor_data(self.entity_id)`:
1. Direct lookup `sensors_dict.get("sensor.ecowitt_0x0b_4094a8")` fails (data is at `"sensor.ecowitt_wind_speed_4094a8"`)
2. The fallback iterates and finds the FIRST sensor with `hardware_id="4094A8"` and a key starting with `"0x"` → **always returns outdoor_temp (`0x02`) data**
3. HA receives wind_speed entity with device_class=temperature / unit=°C → rejects state update
4. Entity value stays frozen at the initial startup value forever

Debug log evidence (repeats every coordinator cycle):
```
Found sensor by hardware_id match: sensor.ecowitt_0x0b_4094a8 -> sensor.ecowitt_outdoor_temp_4094a8
Found sensor by hardware_id match: sensor.ecowitt_0x0c_4094a8 -> sensor.ecowitt_outdoor_temp_4094a8
Found sensor by hardware_id match: sensor.ecowitt_0x0a_4094a8 -> sensor.ecowitt_outdoor_temp_4094a8
Found sensor by hardware_id match: sensor.ecowitt_0x6d_4094a8 -> sensor.ecowitt_outdoor_temp_4094a8
Found sensor by hardware_id match: sensor.ecowitt_0x0d_4094a8 -> sensor.ecowitt_outdoor_temp_4094a8
Found sensor by hardware_id match: sensor.ecowitt_0x0e_4094a8 -> sensor.ecowitt_outdoor_temp_4094a8
Found sensor by hardware_id match: sensor.ecowitt_0x7c_4094a8 -> sensor.ecowitt_outdoor_temp_4094a8
```

Affected sensors (old-format entity IDs in registry): wind speed, wind gust, wind direction, wind direction avg, rain event, rain rate, daily rain + rain amounts.

Not affected (new-format entity IDs, working): outdoor temp, outdoor humidity, dewpoint, solar radiation, UV index, weekly/monthly/yearly rain.

**Fix:** Change `_handle_coordinator_update`, `available`, and `extra_state_attributes` in `sensor.py` to use `get_sensor_data_by_key(sensor_key, hardware_id)` as the primary lookup. This is stable regardless of entity_id format — finds the sensor by its immutable sensor_key + hardware_id combination.

### ℹ️ Issue 6 (MINOR): Sensor "4" (apparent temperature) missing from GATEWAY_SENSORS / SENSOR_TYPES

`common_list` contains `{"id": "4", "val": "7.4", "unit": "C"}` — the gateway's calculated apparent temperature. Key "4" is not in `GATEWAY_SENSORS` or `SENSOR_TYPES`:
- No hardware_id mapping → appears under gateway device ✓ (correct, it's gateway-calculated)
- No SENSOR_TYPES entry → entity_id = `sensor.ecowitt_sensor_ch4` with no device_class or name

Fix: add "4" to `GATEWAY_SENSORS` and `SENSOR_TYPES` as "Apparent Temperature".

### ℹ️ Issue 7 (MINOR): `ws90batt` key in coordinator vs `wh90batt` in sensor_mapper

Coordinator emits key `ws90batt` from `piezoRain` battery data, but sensor_mapper registers `wh90batt` for WH90. Both are defined in `BATTERY_SENSORS`, but the key mismatch means WH90 battery gets `hardware_id=None` and appears under the gateway device.

Fix: change coordinator to emit `wh90batt` instead of `ws90batt`.

---

## Requirements

- [x] **REQ-009-1:** `"89%"` and similar no-space percent/unit suffixes must parse to a numeric value — DONE
- [x] **REQ-009-4:** `wh25` indoor temperature must not double-convert for Celsius gateways — DONE v1.5.19
- [ ] **REQ-009-5:** WH90/WS90 hex-ID sensors must update every coordinator cycle (not freeze after startup)
- [ ] **REQ-009-6:** Sensor "4" (apparent temperature) must appear with correct name and device class
- [ ] **REQ-009-7:** WH90 battery entity must appear under the WH90 device (not the gateway)

---

## Design

### Fix 1 (Critical): Entity lookup by sensor_key + hardware_id

In `sensor.py`, replace direct `entity_id` lookups with `get_sensor_data_by_key`:

```python
@callback
def _handle_coordinator_update(self) -> None:
    # Primary: look up by sensor_key + hardware_id (stable across entity_id format changes)
    sensor_info = self.coordinator.get_sensor_data_by_key(self._sensor_key, self._hardware_id)
    if sensor_info is None:
        sensor_info = self.coordinator.get_sensor_data(self.entity_id)
    if sensor_info:
        self._update_attributes(sensor_info)
    self.async_write_ha_state()
```

Same change in `available` and `extra_state_attributes`. This is backward-compatible — existing entity IDs preserved, they just now correctly find their data.

### Fix 2 (Minor): Add sensor "4" to const.py

```python
# GATEWAY_SENSORS set:
"4",   # Apparent temperature (gateway sensor)

# SENSOR_TYPES dict:
"4": {
    "name": "Apparent Temperature",
    "unit": "°C",
    "device_class": "temperature",
    "state_class": "measurement",
},
```

### Fix 3 (Minor): Fix battery key in coordinator.py

```python
# In piezoRain processing:
battery_key = "wh90batt"  # was "ws90batt" — use same key as sensor_mapper
```

### Files to Change
- [sensor.py](../custom_components/ecowitt_local/sensor.py) — `_handle_coordinator_update`, `available`, `extra_state_attributes`
- [const.py](../custom_components/ecowitt_local/const.py) — add "4" to GATEWAY_SENSORS and SENSOR_TYPES
- [coordinator.py](../custom_components/ecowitt_local/coordinator.py) — change `ws90batt` to `wh90batt`

---

## Tasks

- [x] **TASK-009-1:** Confirm `"89%"` is the exact string in `common_list` for 0x07 — confirmed
- [x] **TASK-009-2:** Fix `_convert_sensor_value` to handle no-space percent suffix — DONE
- [x] **TASK-009-4:** Verify `wh25` processing applies gateway unit setting — DONE v1.5.19
- [x] **TASK-009-6:** Get updated debug logs from GW2000+WH90 user after v1.5.21 — received from @nmaster2042
- [ ] **TASK-009-7:** Fix entity lookup order in sensor.py to use sensor_key+hardware_id primary
- [ ] **TASK-009-8:** Add sensor "4" (apparent temperature) to const.py
- [ ] **TASK-009-9:** Fix ws90batt → wh90batt key in coordinator.py piezoRain processing
- [ ] **TASK-009-10:** Add/update tests for entity lookup fix
- [ ] **TASK-009-11:** Release v1.5.23

---

## Open Questions

- **User action required after fix:** Existing entity IDs (`sensor.ecowitt_0x0b_4094a8` etc.) will persist in the registry — they will START updating correctly after the fix. No migration needed. Users do NOT need to re-add the integration.
- **Multiple outdoor sensors sharing hex keys:** The architectural limitation (flat `_hardware_mapping` dict) remains if GW2000 has both WS90 and WH69. This is an edge case not yet reported and is out of scope for this fix.
