# Spec 003: Temperature Double-Conversion (WH31 / ch_aisle Sensors)

**GitHub Issues:** #19, #13
**Status:** OPEN
**Priority:** HIGH — all Celsius users with WH31/WH26 get wrong temperature readings

---

## Background

Users who configure their Ecowitt gateway in **Celsius** mode report that WH31 (and related) temperature sensors display incorrect values in Home Assistant. The displayed value is the result of HA applying a °F→°C conversion to a value that is **already in Celsius**.

### Confirmed Evidence (issue #19)

Gateway shows correct Celsius values. HA displays the F→C conversion of the same number:

| Ch | Gateway °C | HA displays (°C) | Verification: (Gateway_val − 32) × 5/9 |
|----|-----------|-------------------|----------------------------------------|
| 1  | 22.2      | −5.5              | (22.2 − 32) × 5/9 = **−5.44** ✓       |
| 2  | 22.2      | −5.4              | matches ✓                               |
| 4  | 21.1      | −6.9              | (21.1 − 32) × 5/9 = **−6.06**...       |

The pattern confirms HA is treating the Celsius value as Fahrenheit and converting it.

### Related: GW1200B internal sensors (#13)

Same conversion error observed for `common_list` items `"3"` (Feels Like) and `"5"` reported by user `robert6520-sys`.

---

## Root Cause Analysis

### Data Flow for `ch_aisle` (WH31 sensors)

**Step 1 — Gateway API response** (`get_livedata_info`):
```json
"ch_aisle": [{"channel": "1", "temp": "22.2", "unit": "F", "humidity": "44%"}]
```
When the gateway is set to Celsius, `"temp": "22.2"` is in **Celsius**, but `"unit": "F"` remains `"F"` (Ecowitt firmware bug: unit field doesn't reflect gateway unit setting for ch_aisle).

**Step 2 — coordinator.py lines 256-259:**
```python
temp_key = f"temp{channel}f"  # e.g., "temp1f"
all_sensor_items.append({"id": temp_key, "val": temp})  # unit is DROPPED
```
The "unit" from the ch_aisle item is discarded. The sensor is given the key `temp1f`.

**Step 3 — SENSOR_TYPES in const.py:**
```python
"temp1f": {"name": "Temperature CH1", "unit": "°F", "device_class": "temperature"}
```
The entity inherits `unit = "°F"` from SENSOR_TYPES.

**Step 4 — Home Assistant unit conversion:**
HA's sensor framework sees a sensor claiming `native_unit = "°F"` with value `22.2`. If the user's HA is configured for metric (°C), HA auto-converts: `(22.2 − 32) × 5/9 = −5.44°C`. **Wrong.**

### Why it's hard to fix

The Ecowitt gateway always reports `"unit": "F"` in `ch_aisle` even in Celsius mode. We cannot trust the `unit` field. We need to detect the gateway's configured unit from the `/get_units_info` API endpoint.

The coordinator already fetches units via `api.get_units()`. The response includes a `temp` key: `"0"` = Celsius, `"1"` = Fahrenheit.

---

## Requirements

- [ ] **REQ-003-1:** WH31 temperatures must display correctly whether the gateway is configured in Celsius or Fahrenheit
- [ ] **REQ-003-2:** The coordinator must use the gateway's configured unit setting (from `/get_units_info`) to determine the actual temperature unit for `ch_aisle` data
- [ ] **REQ-003-3:** No regression for Fahrenheit-configured gateways
- [ ] **REQ-003-4:** Similar fix must apply to any other sensor array that has the same unit reporting bug

---

## Design

### Approach A: Use gateway unit setting from `/get_units_info`

The coordinator already stores units data. Use it when processing `ch_aisle`:

```python
# coordinator.py — in __init__ or async_setup:
self._gateway_temp_unit = "°C"  # or "°F", loaded from get_units_info

# In _process_live_data:
for item in ch_aisle:
    channel = item.get("channel")
    temp = item.get("temp")
    # Don't trust item["unit"] — use gateway setting instead
    actual_unit = self._gateway_temp_unit  # "°C" or "°F"

    if actual_unit == "°C":
        temp_key = f"temp{channel}c"  # needs new const.py entry, OR
        # Alternative: store temp1f key but override unit in the sensor dict
    else:
        temp_key = f"temp{channel}f"

    all_sensor_items.append({"id": temp_key, "val": temp, "unit": actual_unit})
```

**Problem:** `temp{n}c` keys don't exist in SENSOR_TYPES. Would require adding 8 new sensor definitions.

### Approach B: Always use `temp{n}f` key but set unit correctly from gateway setting

Keep existing `temp{n}f` key (for entity ID stability) but override the native unit based on the gateway setting:

```python
# In sensor data dict sent to entity:
all_sensor_items.append({
    "id": temp_key,
    "val": temp,
    "unit": self._gateway_temp_unit  # overrides SENSOR_TYPES unit
})
```

The entity reads `unit` from sensor_info and uses it as `native_unit_of_measurement`. HA then handles conversion correctly.

**⚠️ Risk:** Entity IDs stay as `temp1f` but they'd be reporting Celsius — misleading name.

### Approach C (Recommended): Fix at the key level — use `temp{n}c` for Celsius

1. Add `temp1c` through `temp8c` to `SENSOR_TYPES` with `"unit": "°C"`
2. When gateway is Celsius: create `temp{n}c` key
3. When gateway is Fahrenheit: create `temp{n}f` key (existing behavior)

**Problem:** Entity IDs will change for existing Celsius users (breaking change). Mitigation: migration step.

### Approach D (Simplest short-term): Read units_info and pass unit with ch_aisle items

```python
# coordinator.py _process_live_data:
gateway_unit = self._units_data.get("temp", "1")  # "0"=C, "1"=F
ch_unit = "°C" if gateway_unit == "0" else "°F"

for item in ch_aisle:
    temp_key = f"temp{channel}f"  # keep existing key for entity ID stability
    all_sensor_items.append({
        "id": temp_key,
        "val": temp,
        "unit": ch_unit  # pass actual unit, entity uses this instead of SENSOR_TYPES
    })
```

Then in `sensor.py`, when `sensor_info` has a `"unit"` key, use it as `native_unit_of_measurement` instead of (or in addition to) the SENSOR_TYPES lookup.

**⚠️ Open question:** Does the entity currently use `sensor_info["unit"]` or SENSOR_TYPES? Need to trace this.

### Files to Change
- [coordinator.py](../custom_components/ecowitt_local/coordinator.py) — `_process_live_data`, `ch_aisle` block
- [sensor.py](../custom_components/ecowitt_local/sensor.py) — unit resolution (if needed)
- [const.py](../custom_components/ecowitt_local/const.py) — add `temp{n}c` definitions (if Approach C)

---

## Tasks

- [ ] **TASK-003-1:** Trace how `_units_data` (from `get_units_info`) is stored and accessed in coordinator
- [ ] **TASK-003-2:** Determine which approach to use (recommend D for minimal change, C for correctness)
- [ ] **TASK-003-3:** Implement fix in coordinator `ch_aisle` processing block
- [ ] **TASK-003-4:** Verify `sensor.py` uses the correct unit from sensor_info
- [ ] **TASK-003-5:** Test with mock data simulating Celsius gateway (temp="22.2", gateway_unit="0")
- [ ] **TASK-003-6:** Test no regression for Fahrenheit gateway (existing behavior)
- [ ] **TASK-003-7:** Release and comment on issues #19 and #13

---

## Open Questions / Blockers

- **OPEN:** Does the entity read `native_unit_of_measurement` from sensor_info or exclusively from SENSOR_TYPES? Must check `sensor.py` `_update_attributes()`.
- **OPEN:** Contributor `kobius77` linked commit `c8182528` — need to read that commit to understand proposed fix before implementing.
- **OPEN:** Similar issue may affect `common_list` sensors "3" and "5" for GW1200B (issue #13). Are those also affected by the same gateway unit setting?
- **RESOLVED FROM IMAGE (issue #19):**
  - **Image 1 (Ecowitt Live Data page):** Shows 4 WH31 sensors all displaying correct Celsius values on the gateway web UI: Study 21.9°C, Bedroom 22.0°C, Office 23.4°C, Workshop 20.9°C — confirming the gateway is genuinely in Celsius mode.
  - **Image 2 (HA entity detail):** "Temperature CH1" shows **-5.6°C** as the entity value, with **Raw value: 21.9** visible in attributes. Attributes also show: `Sensor key: temp1f`, `Hardware ID: 8E`, `Channel: 1`, `Device model: wh31`, `Battery level: 0%`, `Signal strength: 4`. The math confirms the bug: (21.9 − 32) × 5/9 = **−5.6°C** — the raw Celsius value 21.9 is being treated as Fahrenheit and converted, producing a wrong negative result.
  - **Conclusion:** The `temp1f` key suffix and/or the `"unit": "F"` field in `ch_aisle` data causes the coordinator to apply an F→C conversion to a value that is already in Celsius.
