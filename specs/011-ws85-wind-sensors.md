# Spec 011: WS85 Wind Sensors Missing

**GitHub Issue:** #20
**Status:** 🔴 Open — root cause likely same as WS80 (fixed in v1.5.15); needs user data to confirm
**Priority:** MEDIUM — rain works, only wind entities missing

---

## Background

User reports WS85 connected to a gateway: rain data appears correctly but wind data is missing. No wind entities created.

> *"User added WS85 and sees rain data but not wind data. Asks about plans for WS85 support."*

No `get_sensors_info` or `get_livedata_info` data has been provided. Zero comments on the issue.

---

## Known Facts About WS85

The WS85 is Ecowitt's solar-powered wind + rain sensor (similar to WS80 but with a tipping-bucket rain gauge added). Key differences vs WS80:
- **WS80:** Wind + Solar only — no rain
- **WS85:** Wind + Solar + Rain (tipping bucket)

Since rain works but wind doesn't, the WS85's rain data likely arrives via `common_list` (named keys like `rainratein`) or the `"rain"` array, while wind data arrives via hex keys (`0x0A`, `0x0B`, `0x0C`, `0x6D`) that need a hardware ID mapping — exactly the same pattern as WS80 before the v1.5.15 fix.

---

## Root Cause Hypothesis

**Same as WS80 (fixed in v1.5.15):** `sensor_mapper.py` has no `elif` clause for the WS85 device type string. The WS85 likely reports as:
- `"img": "ws85"` — inferred from Ecowitt naming convention
- `"name"`: possibly `"Wind & Rain & Solar"` or similar

Without a matching `elif` in `sensor_mapper.py`, the hex keys `0x0A`, `0x0B`, `0x0C`, `0x6D` are never mapped to the WS85 hardware ID, so `get_hardware_id()` returns `None` and wind entities stay permanently unavailable.

The fix for WS80 was:
```python
elif sensor_type.lower() in ("wh80", "ws80") or "temp & humidity & solar & wind" in sensor_type.lower():
    keys.extend(["0x0B", "0x0C", "0x0A", "0x6D", ...])
```

An equivalent block is needed for WS85.

---

## Requirements

- [ ] **REQ-011-1:** WS85 wind sensors (speed, gust, direction, direction avg) must receive live values
- [ ] **REQ-011-2:** WS85 solar radiation and UV sensors must also work
- [ ] **REQ-011-3:** WS85 rain sensors must continue working (already working — no regression)
- [ ] **REQ-011-4:** No regression for WS80/WH80

---

## Design

### Step 1: Confirm WS85 device type string from `get_sensors_info`

Need from a WS85 user:
```
GET http://[gateway_ip]/get_sensors_info?page=1
```
Looking for the `img`, `type`, and `name` fields for the WS85 entry.

Hypothesis (based on Ecowitt naming convention):
```json
{"img": "ws85", "type": "X", "name": "Wind & Rain", "id": "XXXXXX"}
```

### Step 2: Add WS85 device type detection to `sensor_mapper.py`

Following the WS80 pattern exactly:
```python
elif sensor_type.lower() in ("ws85",) or "wind & rain" in sensor_type.lower():
    keys.extend([
        "0x02",   # Temperature (if WS85 has temp sensor)
        "0x0B",   # Wind Speed
        "0x0C",   # Wind Gust
        "0x19",   # Max Daily Gust
        "0x0A",   # Wind Direction
        "0x6D",   # Wind Direction Avg
        "0x15",   # Solar Radiation
        "0x17",   # UV Index
        "0x0D",   # Rain Event (if tipping bucket)
        "0x0E",   # Rain Rate
        "0x7C",   # Daily Rain
        "0x10",   # Weekly Rain
        "0x11",   # Monthly Rain
        "0x12",   # Yearly Rain
        "0x13",   # Total Rain
        "ws85batt",  # Battery
    ])
```

**⚠️ Caution with `name` string matching:** The `"wind & rain"` string match could accidentally catch unintended devices. Prefer exact `img` field matching once confirmed.

### Step 3: Add battery definition to `const.py`

```python
"ws85batt": {"name": "WS85 Battery", "unit": "%", "device_class": "battery"}
```

### Files to Change
- [sensor_mapper.py](../custom_components/ecowitt_local/sensor_mapper.py) — add WS85 device type detection
- [const.py](../custom_components/ecowitt_local/const.py) — add `ws85batt` to `BATTERY_SENSORS`

---

## Tasks

- [ ] **TASK-011-1:** Request `get_sensors_info` and `get_livedata_info` from @ostsee-segler (issue reporter)
- [ ] **TASK-011-2:** Confirm WS85 `img`, `name`, `type` fields from sensor mapping
- [ ] **TASK-011-3:** Confirm which hex keys WS85 uses for wind (same as WS80? Does it also have temp/humidity?)
- [ ] **TASK-011-4:** Add WS85 device type detection to `sensor_mapper.py`
- [ ] **TASK-011-5:** Add `ws85batt` to `BATTERY_SENSORS` in `const.py`
- [ ] **TASK-011-6:** Add tests and release

---

## Open Questions / Blockers

- **AWAITING USER DATA:** No `get_sensors_info` or `get_livedata_info` JSON has been provided. The fix design is ready (same pattern as WS80) but the exact `img`/`name` string from `get_sensors_info` must be confirmed before implementing to avoid matching wrong devices.
- **Does WS85 have temperature/humidity?** WS80 has temp + humidity. WS85 may or may not — needs confirmation from the sensor mapping data.
- **Rain data path:** If WS85 rain data comes via the `"rain"` array (like WS69), the v1.5.16 fix already handles it. If it comes via `common_list` with named keys (`rainratein` etc.), it works independently of hex ID mapping.
