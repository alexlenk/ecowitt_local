# Spec 007: `"rain"` Array Not Processed (Tipping-Bucket Rain Missing)

**GitHub Issues:** #59, #11 (rain portion)
**Status:** ✅ Fixed in v1.5.16
**Priority:** HIGH — rain sensors entirely absent for GW1200 + WS69 users; also explains missing rain in WH69 (issue #11)

---

## Background

### Issue #59 — GW1200 + WS69: no rain entities

Rain data from WS69 (tipping-bucket sensor) is missing when connected via the GW1200 gateway. The reporter identified the exact root cause: the GW1200 puts rain data in a top-level `"rain"` JSON array rather than `common_list`.

The reporter provided the two-line local workaround:
> Extend `_process_live_data` to also extract and append the `"rain"` array to `all_sensor_items`, just like `common_list`.

Rain hex IDs reported in the `"rain"` array:
```
0x0D  Rain Rate
0x0E  Event Rain
0x7C  Hourly Rain
0x10  Daily Rain
0x11  Weekly Rain
0x12  Monthly Rain
0x13  Total Rain
```

### Issue #11 (rain portion) — GW2000A + WH69

Issue #11's original report explicitly states: *"Rain data is in a `"rain"` array, also missing."* The same root cause applies — rain data for WH69 + GW2000A also lives in the `"rain"` array, not in `common_list`.

### Likely affected: GW1100 (issue #22 rain portion)

Spec 004 notes that GW1100 rain entities are entirely absent (unlike wind which at least creates unavailable entities). GW1100 may also put rain in a `"rain"` array. No GW1100 live data JSON has been provided yet to confirm.

---

## Root Cause

`_process_live_data()` in `coordinator.py` processes these data sections:
- ✅ `common_list` — gateway sensors and hex-ID sensors
- ✅ `piezoRain` — piezoelectric rain sensor (WS90/WH40)
- ✅ `ch_soil` — WH51 soil moisture sensors
- ✅ `ch_aisle` — WH31 temperature/humidity sensors
- ✅ `ch_temp` — WH34 pool temperature sensors (added v1.5.15)
- ❌ **`rain` — NOT PROCESSED** — tipping-bucket rain sensors (WS69, WH69, GW1100 integrated)

The `"rain"` array uses the **same item format as `common_list`** (`{"id": "0x0D", "val": "0.00 in"}`), so no structural conversion is needed — it can be extended directly.

All rain hex IDs (`0x0D`, `0x0E`, `0x7C`, `0x10`, `0x11`, `0x12`, `0x13`) are already defined in `SENSOR_TYPES` in `const.py` (lines 346–382). No `const.py` changes needed.

---

## Requirements

- [x] **REQ-007-1:** Rain entities from the `"rain"` array must be created and receive live values — **fixed v1.5.16**
- [x] **REQ-007-2:** Fix must not regress `piezoRain` (WS90/WH40) rain processing — **verified by tests**
- [x] **REQ-007-3:** Fix must not regress `common_list` processing for any existing device — **verified by tests**

---

## Design

### Fix: add `rain` array processing to `coordinator.py`

Insert after the `common_list` block (or alongside the other array extractions):

```python
# Extract rain data (tipping-bucket rain sensor readings — GW1200, GW2000A with WS69/WH69)
rain_list = raw_data.get("rain", [])
if rain_list:
    _LOGGER.debug("Found rain data with %d items", len(rain_list))
    all_sensor_items.extend(rain_list)
```

The `"rain"` array items have the same `{"id": ..., "val": ...}` format as `common_list`, so `extend` is all that is needed — no conversion or battery special-casing required (unlike `piezoRain`).

### Files to Change
- [coordinator.py](../custom_components/ecowitt_local/coordinator.py) — add `rain` array extraction block
- [tests/test_coordinator.py](../tests/test_coordinator.py) — add tests for `rain` array processing

---

## Tasks

- [x] **TASK-007-1:** Confirm `"rain"` array item format matches `common_list` — confirmed from issue #59 reporter description and hex IDs
- [x] **TASK-007-2:** Confirm all rain hex IDs already defined in `const.py` — yes, lines 346–382
- [x] **TASK-007-3:** Add `rain` array processing to `coordinator.py` — done in v1.5.16
- [x] **TASK-007-4:** Add tests: basic rain array, empty handling, no regression vs piezoRain — done in v1.5.16
- [x] **TASK-007-5:** Release v1.5.16 and comment on issues #59 and #11

---

## Open Questions

- **GW1100 (issue #22 rain):** Does GW1100 also put rain in a `"rain"` array? No live data JSON has been received from a GW1100 user. If yes, this fix resolves GW1100 rain too. Tracked in spec 004 TASK-004-5/006.
- **Battery in `"rain"` array:** The reporter did not mention battery data in the `"rain"` array items. `piezoRain` has battery on the last item; `"rain"` (tipping-bucket) typically has the battery reported separately in `common_list` or `ch_soil`-style entries. No special battery handling added.
