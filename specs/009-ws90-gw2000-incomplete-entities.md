# Spec 009: WS90 / GW2000 / GW3000 — Incomplete or Unavailable Entities

**GitHub Issues:** #5, #40, #15, #41 (partial)
**Status:** 🟡 Partial — wh25 temperature unit fixed in v1.5.19; hardware_id mapping conflict still open
**Priority:** HIGH — affects many users with GW2000/GW3000 + WS90 combination

---

## Background

Users with GW2000 or GW3000 gateways + WS90 outdoor sensor consistently report:
- WS90 device created but most entities show "unavailable" or are never created
- Gateway device only shows a small subset of expected entities (9 instead of 20+)
- Some gateway sensors incorrectly show values like 160°F instead of ~74°F

Representative reports:
- **@timnis (GW2000 + WS90):** "9 entities each even with 'Include Inactive Sensors'" — both gateway and WS90 severely truncated
- **@nicokars (GW3000):** Same — confirmed with screenshot
- **@darrendavid:** "My gateway temp is showing as over 160 degrees when the web UI reads 74.1F"
- Multiple users in #40 confirm across GW2000/GW3000 variants

---

## Known Live Data Structure (GW2000 + WS90)

From user-provided `get_livedata_info` (issue #5, user @Rakkzi):

```json
{
  "common_list": [
    {"id": "0x02", "val": "66.0", "unit": "F"},
    {"id": "0x07", "val": "89%"},           ← percent sign embedded, no space
    {"id": "3",    "val": "66.0", "unit": "F"},
    {"id": "5",    "val": "0.071 inHg"},    ← embedded unit with space
    {"id": "0x03", "val": "62.8", "unit": "F"},
    {"id": "0x0B", "val": "1.34 mph"},
    {"id": "0x0C", "val": "1.57 mph"},
    {"id": "0x19", "val": "7.38 mph"},
    {"id": "0x15", "val": "0.00 W/m2"},
    {"id": "0x17", "val": "0"},
    {"id": "0x0A", "val": "133"},
    {"id": "0x6D", "val": "130"}
  ],
  "piezoRain": [
    {"id": "srain_piezo", "val": "0"},
    {"id": "0x0D", "val": "0.00 in"},
    {"id": "0x0E", "val": "0.00 in/Hr"},
    {"id": "0x7C", "val": "0.00 in"},
    {"id": "0x10", "val": "0.00 in"},
    {"id": "0x11", "val": "0.00 in"},
    {"id": "0x12", "val": "2.36 in"},
    {"id": "0x13", "val": "10.15 in", "battery": "3", "voltage": "2.62", "ws90cap_volt": "5.3", "ws90_ver": "153"}
  ],
  "wh25": [{"intemp": "80.6", "unit": "F", "inhumi": "35%", "abs": "29.38 inHg", "rel": "30.03 inHg"}]
}
```

From `get_sensors_info`:
```json
[
  {"img": "wh90", "type": "48", "name": "Temp & Humidity & Solar & Wind & Rain", "id": "A238", "batt": "3", "rssi": "-69", "signal": "4"}
]
```
WS90 has hardware ID `A238` and is in `common_list` + `piezoRain`.

---

## Root Cause Analysis

### Issue 1: `"89%"` — percent sign without space breaks value parsing

The humidity key `0x07` sends `"89%"` (no space before `%`). The coordinator's embedded-unit extractor uses a regex that expects a space before the unit (e.g. `"89 %"` or `"1.34 mph"`). Without a space, `"89%"` is not split — the raw string is passed to HA, causing a `ValueError` when HA tries to cast it to float.

**Fix:** Extend `_convert_sensor_value` to also strip trailing `%` (and handle other no-space unit suffixes).

### Issue 2: WS90 hardware_id not associated with `common_list` hex keys

The sensor mapper maps hex keys (`0x02`, `0x07`, etc.) to a hardware ID only when a known device type is detected in `get_sensors_info`. For WS90 (`wh90`), the hex key → hardware ID mapping IS present (added in v1.4.8). However, there may be a conflict: if multiple sensors share the same hex key (e.g. both WS90 and WH80 use `0x07`), only the last mapping survives in `_hardware_mapping`. The WS90's hardware ID may be overwritten by another device, causing `get_hardware_id("0x07")` to return the wrong ID or `None`.

**Investigation needed:** Check whether `_hardware_mapping` correctly maps `0x07` → `A238` for a GW2000 + WS90 setup.

### Issue 3: `piezoRain` → WS90 device association

`piezoRain` items (battery, wind rain values) are appended to `all_sensor_items` by the coordinator, but the hardware_id used when creating those entities comes from `get_hardware_id(sensor_id)`. For `"0x13"` (total rain), the hardware_id lookup must return `A238` for the WS90. This only works if `0x13` is mapped to the WS90's hardware ID in `_hardware_mapping` — which requires the WS90 device type detection to have run successfully.

### Issue 4: `wh25` indoor data — wrong temperature values

The `wh25` block sends `"intemp": "80.6"` with `"unit": "F"`. The coordinator processes this as `tempinf` (indoor temperature Fahrenheit). If the gateway is configured in Celsius but reports `wh25` in Fahrenheit (same issue as `ch_aisle` in spec 003), the value could be double-converted. **But** the `wh25` unit field is explicit — needs to verify whether the spec 003 fix also covers `wh25` data.

The 160°F report is likely a double-conversion: Celsius value being treated as Fahrenheit and converted again.

---

## Requirements

- [ ] **REQ-009-1:** `"89%"` and similar no-space percent/unit suffixes must parse to a numeric value
- [ ] **REQ-009-2:** WS90 hex-ID sensors in `common_list` must map to the WS90 hardware ID (`A238`)
- [ ] **REQ-009-3:** `piezoRain` sensors must be associated to the WS90 device
- [ ] **REQ-009-4:** `wh25` indoor temperature must not double-convert for Celsius gateways

---

## Design

### Fix 1: Strip no-space unit suffixes in `_convert_sensor_value`

```python
# In coordinator.py _convert_sensor_value or unit extraction
# Handle "89%" → 89 with unit "%"
if value.endswith("%") and not value.endswith(" %"):
    return float(value[:-1]), "%"
```

### Fix 2: Hardware ID mapping conflict

Check `sensor_mapper.py` — when multiple devices share a hex key, `_hardware_mapping[key]` is overwritten. Need to track hex key → hardware ID per-device rather than a flat map.

**⚠️ Architectural issue:** The current flat `_hardware_mapping` dict can only hold one hardware ID per hex key. For GW2000 setups with multiple outdoor sensors (WS90 + WH69), they share hex keys. Only the last device processed will have its hardware ID survive.

### Fix 3: `wh25` unit handling

Check if `wh25` processing in coordinator applies the spec 003 `_gateway_temp_unit` fix. If `wh25` still uses the hardcoded `tempinf` key (which assumes Fahrenheit), Celsius gateways will double-convert.

### Files to investigate
- [coordinator.py](../custom_components/ecowitt_local/coordinator.py) — `_convert_sensor_value`, `wh25` processing block
- [sensor_mapper.py](../custom_components/ecowitt_local/sensor_mapper.py) — `_hardware_mapping` flat dict architecture

---

## Tasks

- [ ] **TASK-009-1:** Confirm `"89%"` is the exact string in `common_list` for 0x07 (humidity) — confirmed from issue #5 data
- [ ] **TASK-009-2:** Fix `_convert_sensor_value` to handle no-space percent suffix
- [ ] **TASK-009-3:** Investigate `_hardware_mapping` conflict for multi-sensor GW2000 setups
- [ ] **TASK-009-4:** Verify `wh25` processing applies gateway unit setting (or fix if not)
- [ ] **TASK-009-5:** Add tests for `"89%"` value parsing
- [ ] **TASK-009-6:** Request updated debug logs from GW2000+WS90 user after v1.5.16 to confirm which issues remain

---

## Open Questions / Blockers

- **Multi-sensor hex key conflict:** If GW2000 has both WS90 and WH69, both register `0x07` in `_hardware_mapping`. Whichever runs last in `_update_sensor_mapping()` wins. No fix exists yet — architectural change needed.
- **Which entities are still missing after v1.5.16?** The `piezoRain` fix (v1.5.4), WS90 device type detection (v1.4.8), and `rain` array fix (v1.5.16) have all been applied. Users need to re-test with v1.5.16 and report exactly which entities are missing.
- **wh25 double-conversion:** Spec 003 fixed `ch_aisle` but did it also fix `wh25`? Check `wh25` processing in coordinator — it hardcodes `tempinf` without a unit override.
