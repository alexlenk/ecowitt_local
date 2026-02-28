# Spec 015: WH31/WH69 Battery Reports Binary (0=OK / 1=Weak) Not 0–4 Scale

**GitHub Issues:** #19 (comment by @AnHardt)
**Status:** ✅ FIXED — v1.5.28 (binary conversion 0→100%, 1→10% implemented in coordinator ch_aisle processing)
**Priority:** MEDIUM — battery always shows 0% or 20%, never reflects actual level

---

## Background

The integration converts battery values using `int(battery) * 20` (treating 0–5
as bars → percentage). WH31 and WH69 sensors in `ch_aisle` report battery as a
**binary flag**: `"0"` = battery OK, `"1"` = battery weak/low.

The `0x13` rain hex ID also carries a battery field:
```json
{"id": "0x13", "val": "45.2 mm", "battery": "0"}
```
Same binary format.

### Confirmed Evidence (@AnHardt, GW1100A_V2.4.4)

> "WH31 and WS69 do report no battery level, just a binary if the battery is
> good or bad. Where 0 means Battery OK and 1 means Battery weak."

```json
"ch_aisle": [{"channel": "1", "battery": "0", "temp": "20.0", "unit": "C", ...}]
```

With `int("0") * 20 = 0%` → battery entity always shows 0% even when battery is fine.

---

## Root Cause

In `coordinator.py` ch_aisle processing:
```python
battery_pct = str(int(battery) * 20) if battery.isdigit() else battery
```

This converts `"0"` → `"0%"` and `"1"` → `"20%"`. Both values are wrong:
- `"0"` should mean 100% (battery OK)
- `"1"` should mean 0–20% (battery weak/low)

This same `* 20` logic was designed for WH51 soil moisture sensors which use a
0–5 scale. WH31/WH69 ch_aisle battery uses a different binary encoding.

---

## Requirements

- [x] **REQ-015-1:** WH31/WH69 ch_aisle battery `"0"` must display as battery OK (100%) — fixed v1.5.28
- [x] **REQ-015-2:** WH31/WH69 ch_aisle battery `"1"` must display as battery Low (10% or similar) — fixed v1.5.28
- [x] **REQ-015-3:** No regression for WH51 soil sensors which correctly use `* 20` scale — verified
- [x] **REQ-015-4:** Same fix applies to `0x13` rain battery field if it uses binary encoding — confirmed by @mjb1416 (issue #95, GW1200A + WH69): `"0"` with new battery → fixed v1.5.34

---

## Design

### Detect binary vs scale battery

In coordinator `ch_aisle` processing, apply binary conversion:
```python
battery = item.get("battery", "")
if battery and battery != "None":
    battery_key = f"batt{channel}"
    # ch_aisle battery is binary: "0"=OK(100%), "1"=weak(10%)
    if battery == "0":
        battery_pct = "100"
    elif battery == "1":
        battery_pct = "10"
    else:
        battery_pct = str(int(battery) * 20) if battery.isdigit() else battery
    all_sensor_items.append({"id": battery_key, "val": battery_pct})
```

Same fix for `0x13` rain battery in piezoRain/rain array processing.

### Alternative: binary sensor

Since the value is truly binary, a `BinarySensorEntity` with `device_class: battery`
(True = low) would be more semantically correct than a percentage sensor. However,
this would be an architectural change (adding a binary sensor to the battery pipeline).
Simpler to keep as a numeric sensor with 100%/10% mapping for now.

---

## Tasks

- [x] **TASK-015-1:** Fix ch_aisle battery processing: `"0"` → `"100"`, `"1"` → `"10"` — done in v1.5.28
- [x] **TASK-015-2:** Fix `0x13` rain battery — confirmed binary by @mjb1416 (issue #95); fixed v1.5.34
- [ ] **TASK-015-3:** Check if WH34 `ch_temp` battery uses same binary format — unconfirmed; needs user data
- [x] **TASK-015-4:** Update/add tests for binary battery conversion — done in v1.5.28
- [x] **TASK-015-5:** Release and comment on issue #19 — released v1.5.28

---

## Open Questions

- **OPEN:** Does `ch_temp` (WH34) use the same binary battery format? No WH34 user data received.
- **RESOLVED:** `0x13` rain battery IS binary — @mjb1416 (GW1200A + WH69, issue #95) confirmed `"battery": "0"` with a new battery. Fixed in v1.5.34.
