# Spec 004: Wind / Rain Sensors Unavailable (Missing hardware_id Mapping)

**GitHub Issues:** #22, #23
**Status:** ✅ Likely fixed — GW1100 live data received (Feb 2026); all hex IDs already supported; awaiting user confirmation on v1.5.25
**Priority:** HIGH — GW1100 wind/rain still broken; WS80 wind sensors now resolved

---

## Background

### Issue #23 — WS80 wind sensors (GW3000B)

Wind hex IDs from the WS80 (`0x0A`, `0x0B`, `0x0C`, `0x6D`) appear in `common_list` and are logged, but entities remain permanently **unavailable**. Debug log:

```
Sensor item: id=0x0A, val=86
Sensor item: id=0x0B, val=2.46 mph
Sensor item: id=0x0C, val=2.91 mph
Sensor item: id=0x6D, val=83
Hardware ID lookup for 0x0B: None       ← root cause
Processing sensor: key=0x0B, value=2.46, hardware_id=None,
  entity_id=sensor.ecowitt_0x0B_0x0b   ← malformed fallback entity ID
```

All other WS80 sensors (temperature, humidity, solar, UV, pressure, lightning) work correctly — they use a named hardware_id mapping. Only wind hex-ID sensors are broken.

**Gateway:** GW3000B fw 1.1.3, **Outdoor unit:** WS80, **HA:** 2025.10.x, **Integration:** v1.5.4

### Issue #22 — GW1100 wind and rain entities

Temperature and soil moisture work, but:
- Rain: **no entities created at all**
- Wind: entities exist but are **permanently unavailable**

---

## Root Cause Analysis

### How the hardware_id mapping works

`sensor_mapper.py` builds `_hardware_mapping`: `{hex_key → hardware_id}`.

This mapping is populated in `_update_sensor_mapping()` when a device of a known type is detected:

```python
elif sensor_type.lower() in ("wh69", ...):
    keys.extend(["0x0B", "0x0C", "0x0A", "0x6D", ...])
    for key in keys:
        self._hardware_mapping[key] = hardware_id  # links hex key → device hardware_id
```

**The bug:** If the WS80 (or GW1100's integrated station) presents under a device type string that isn't in the `elif` chain, no mapping is created, and `get_hardware_id("0x0B")` returns `None`.

### WS80 device type string

From the Ecowitt sensor mapping API, WS80 is likely reported as one of:
- `"wh80"` (from img field: `"img": "wh80"`)
- `"Temp & Humidity & Solar & Wind"` (from name field: `type 2`)

Looking at issue #16's `get_sensors_info` dump:
```json
{"img": "wh80", "type": "2", "name": "Temp & Humidity & Solar & Wind", "id": "FFFFFFFF"}
```
The `id` is `"FFFFFFFF"` (invalid/unconnected slot) in that user's case. For a connected WS80 it would be a real hardware ID.

**Root cause confirmed:** `sensor_mapper.py` has no `elif` clause for `"wh80"` or `"Temp & Humidity & Solar & Wind"`.

### GW1100 — different scenario

GW1100 has an integrated weather station (no separate sensor mapping entry). Its wind/rain sensors (`windspeedmph`, `windgustmph`, `winddir`, `rainratein`, etc.) appear in `common_list` as named keys, not hex keys. These map via `SENSOR_TYPES` directly. The issue may be:
1. These sensors have a hardware_id of `None` because the GW1100 gateway itself doesn't have a sensor mapping entry for its integrated station
2. OR the coordinator skips them for another reason

**⚠️ Needs investigation:** Full live data and sensor mapping JSON from a GW1100 user needed.

---

## Requirements

- [x] **REQ-004-1:** WS80 wind sensors (0x0A, 0x0B, 0x0C, 0x6D) connected via GW3000 must receive live updates — **fixed v1.5.15**
- [x] **REQ-004-2:** WS80 entities must have correct `device_class`, units, and be assigned to the WS80 device — **fixed v1.5.15**
- [ ] **REQ-004-3:** GW1100 wind and rain entities must become available with live values — **still open**
- [x] **REQ-004-4:** No regression for WH69/WS90/WH90 which use the same hex keys — **verified by tests**

---

## Design

### Fix for WS80 (Issue #23)

Add WS80 device type detection to `sensor_mapper.py`:

```python
elif sensor_type.lower() in ("wh80", "ws80") or "temp & humidity & solar & wind" in sensor_type.lower():
    keys.extend([
        "0x02",   # Temperature
        "0x07",   # Humidity
        "0x0B",   # Wind Speed
        "0x0C",   # Wind Gust
        "0x0A",   # Wind Direction
        "0x6D",   # Wind Direction Avg
        "0x15",   # Solar Radiation
        "0x17",   # UV Index
        "0x03",   # Dewpoint
        "wh80batt",  # Battery (if applicable)
    ])
```

All hex IDs above are already defined in `SENSOR_TYPES` in `const.py` — no const.py changes needed.

**⚠️ Open:** WS80 does NOT have rain sensors (it's a wind/solar station). GW3000 may report rain separately. Verify which hex IDs WS80 actually reports.

### Fix for GW1100 (Issue #22)

**Needs more data.** Request from GW1100 users:
1. Full JSON from `http://[gateway_ip]/get_sensors_info?page=1`
2. Full JSON from `http://[gateway_ip]/get_livedata_info`

Hypothesis: GW1100 has a built-in rain sensor that reports wind/rain as `windspeedmph`, `rainratein` (named keys) in `common_list`. These go through the named-sensor path, which doesn't require hex ID mapping. If entities are "unavailable", the hardware_id is `None`, meaning the coordinator is not assigning them to a device.

Check if GW1100's integrated sensor type appears in `get_sensors_info` with a valid hardware_id.

### Files to Change
- [sensor_mapper.py](../custom_components/ecowitt_local/sensor_mapper.py) — add WS80/WH80 device type detection
- [const.py](../custom_components/ecowitt_local/const.py) — add `wh80batt` to `BATTERY_SENSORS` if WS80 has battery reporting

---

## Tasks

- [x] **TASK-004-1:** Confirm WS80 device type string — `img: "wh80"`, `name: "Temp & Humidity & Solar & Wind"` confirmed from issue evidence
- [x] **TASK-004-2:** WS80 reports temp/humidity/wind/solar — no rain (confirmed: WS80 is wind/solar only)
- [x] **TASK-004-3:** Add WS80/WH80 device type detection to `sensor_mapper.py` — done in v1.5.15
- [x] **TASK-004-4:** Add `wh80batt` to `BATTERY_SENSORS` in `const.py` — done in v1.5.15
- [ ] **TASK-004-5:** Request GW1100 live data from issue #22 reporters — comment posted, no JSON received yet
- [ ] **TASK-004-6:** Implement GW1100 fix once data is available
- [x] **TASK-004-7:** Add tests for WS80 device type detection — 3 tests added in v1.5.15
- [x] **TASK-004-8:** Release and comment on issues #22 and #23 — v1.5.15

---

## Open Questions / Blockers

- **AWAITING USER DATA (issue #23):** Posted comment asking for: (1) real hardware `id` for connected WS80 (not `FFFFFFFF`), (2) confirmation of `img`/`name` fields, (3) whether WS80 reports battery. Design is ready; just need to confirm the device type string before releasing.
- **AWAITING USER DATA (issue #22):** Posted comment asking for full `get_sensors_info?page=1` and `get_livedata_info` JSON from a GW1100 user. No JSON has been provided yet despite multiple reporters.
- **DESIGN READY FOR WS80:** Fix is `elif sensor_type.lower() in ("wh80", "ws80") or "temp & humidity & solar & wind" in sensor_type.lower()` in sensor_mapper.py. Can implement without waiting for data since the `name` field from existing evidence matches. Battery key `wh80batt` needs confirmation.
- **RESOLVED FROM IMAGES:**
  - **Issue #22, img1 (GW1100A device page):** Firmware `GW1100A_V2.3.2`. Only 5 entities exist under the gateway device: Absolute Pressure, Feels Like Temperature, Indoor Humidity, Indoor Temperature, Relative Pressure. No wind or rain entities at all.
  - **Issue #22, img2 (wh69 device page):** The WH69 (model `wh69`, "Connected via Ecowitt Gateway") has UV Index working with a value (1 UV Index), but **Wind Direction, Wind Gust, and Wind Speed are all "Unavailable"**. This confirms wind keys are parsed but lack hardware_id mapping.
  - **Issue #22, img3 (original Ecowitt integration — 26 entities for same GW1100A):** The garbled1/homeassistant_ecowitt integration correctly creates: Absolute Pressure, Daily Rain, Dewpoint, Event Rain, Feels Like Temperature, Hourly Rain, Humidity, Indoor Dewpoint, Indoor Humidity, Indoor Temperature, Max Daily Gust, Monthly Rain, Outdoor Temperature, Rain Rate, Relative Pressure, Solar Lux, Solar Radiation, Total Rain, UV Index, Weekly Rain, Wind Chill, Wind Direction, Wind Gust, Wind Speed, Windchill, Yearly Rain + WH65 Battery (diagnostic). This is the full expected entity set for a GW1100A user.
  - **Issue #23, img1 (WS80 device page, Dutch UI):** Four wind sensors all shown as "Niet beschikbaar" (Unavailable): Wind Direction, Wind Direction Avg, Wind Gust, Wind Speed. The entities exist but receive no state updates due to missing hardware_id mapping. Matches exactly the log excerpt in the issue text (hardware_id=None for 0x0A/0x0B/0x0C/0x6D).
  - **Key finding from img3:** GW1100 users expect **rain sensors** (0x0D–0x14) in addition to wind sensors. The rain entities are completely absent (not even created as unavailable), unlike wind which at least creates unavailable entities. This suggests rain keys also lack hardware_id mapping AND entity creation for the GW1100.
