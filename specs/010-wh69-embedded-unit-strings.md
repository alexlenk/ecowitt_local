# Spec 010: WH69 Sensor Values Unavailable (Embedded Unit Strings)

**GitHub Issue:** #41
**Status:** ✅ Fixed in v1.5.18
**Priority:** MEDIUM — affects WH69 users on GW3000; most values unavailable

---

## Background

WH69 users with GW3000 report that nearly all WH69 sensor entities are created but show "unavailable". UV Index is the only value that works. The root cause was identified by user @riclamont in issue #41:

> *"Root cause: WH69 sensor values include units in the value string (e.g. `"0.00 knots"`, `"612.67 W/m2"`), but the integration doesn't parse embedded units for these sensors. Only UV Index works."*

UV Index (`0x17`) works because it sends a bare numeric value (`"0"`), while all other WH69 sensors send values with embedded unit strings that vary by gateway unit setting.

**Hardware:** WH69 connected via GW3000 (same issue likely on GW2000A)
**Integration version when reported:** v1.5.x

---

## Known Data

From @riclamont's report, WH69 values in `common_list`:

| Hex ID | Sensor | Value example | Issue |
|--------|--------|---------------|-------|
| `0x0B` | Wind Speed | `"0.00 knots"` | Unit not stripped |
| `0x0C` | Wind Gust | `"0.00 knots"` | Unit not stripped |
| `0x0A` | Wind Direction | `"133"` | Works (bare numeric) |
| `0x15` | Solar Radiation | `"612.67 W/m2"` | Unit not stripped |
| `0x17` | UV Index | `"0"` | Works (bare numeric) |

**Note:** Other gateways (GW2000A with WH69) send `"1.34 mph"` for wind, which IS handled by the existing embedded-unit extractor. The GW3000 sends `"knots"` instead of `"mph"` for WH69 wind speed.

---

## Root Cause

The coordinator's `_convert_sensor_value` (or embedded unit extraction) handles these known unit strings:
- `mph`, `km/h`, `m/s` — wind speed
- `in`, `mm` — rain
- `in/Hr`, `mm/Hr` — rain rate
- `W/m2` — solar radiation (space-separated: `"612.67 W/m2"`)
- `inHg`, `hPa` — pressure

The issue is **`"knots"`**: wind speed in knots is a valid gateway unit setting that the GW3000 can output. The embedded-unit extractor may not recognize `"knots"` as a unit, or the unit normalization doesn't map `"knots"` to the expected HA unit (`km/h` or `m/s`).

**For `"612.67 W/m2"`**: This has a space before the unit, so the regex should split it correctly. It's possible the unit `W/m2` is being normalized to something HA rejects for the `solar_radiation` device class (which expects `W/m²`). The Unicode superscript `²` vs ASCII `2` may cause a mismatch.

---

## Requirements

- [ ] **REQ-010-1:** Wind speed/gust values in `"knots"` format must parse to a numeric value and use correct HA unit
- [ ] **REQ-010-2:** Solar radiation `"W/m2"` must normalize to `W/m²` (or `W/m2` if HA accepts both)
- [ ] **REQ-010-3:** All WH69 sensors on GW3000 must show live values, not "unavailable"

---

## Design

### Fix 1: Add `"knots"` to unit normalization

In the coordinator's unit normalization map, add:
```python
"knots": "kn",   # or convert to km/h/m/s and set appropriate unit
```
The HA `wind_speed` device class accepts `km/h`, `m/s`, `mph`, `kn` (knots). `"kn"` is the correct HA unit for knots.

### Fix 2: Verify `W/m2` → `W/m²` normalization

Check the unit normalization in `coordinator.py`. If `"W/m2"` is not being normalized to `"W/m²"`, add it to the normalization map. HA's `irradiance` device class requires `W/m²`.

### Files to Change
- [coordinator.py](../custom_components/ecowitt_local/coordinator.py) — unit normalization in `_convert_sensor_value` or `_normalize_unit`

---

## Tasks

- [ ] **TASK-010-1:** Locate the unit normalization map in `coordinator.py` and confirm whether `"knots"` is present
- [ ] **TASK-010-2:** Add `"knots"` → `"kn"` to unit normalization
- [ ] **TASK-010-3:** Confirm `"W/m2"` → `"W/m²"` normalization is correct
- [ ] **TASK-010-4:** Add tests for `"0.00 knots"` and `"612.67 W/m2"` value parsing
- [ ] **TASK-010-5:** Request confirmation from @riclamont after fix

---

## Open Questions

- **Does GW2000A with WH69 also report knots?** Or is this GW3000-specific? The GW3000 unit setting may default to metric/SI while GW2000A defaults to imperial (mph). Needs clarification.
- **Are there other unit strings from GW3000 that aren't handled?** e.g. `"°C"` vs `"°F"` in `common_list` items, `"hPa"` vs `"inHg"` — likely already handled but worth checking with a complete GW3000 live data dump.
- **Is `W/m²` actually needed or does HA accept `W/m2`?** Check HA's unit registry for solar radiation. Some versions are lenient about the superscript.
