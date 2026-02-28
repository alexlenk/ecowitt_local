# Spec 019: 0x10 Rain Entity Mislabeled as "Hourly Rain" (is Daily Rain)

**GitHub Issues:** #5
**Status:** ✅ FIXED — v1.5.33
**Priority:** MEDIUM — mislabeled entity, values are correct but confusing

---

## Background

User @nmaster2042 (GW2000 + WS90) reported that "Hourly Rain" in the integration
shows the wrong value: HA shows 7mm while the Ecowitt app shows Hourly = 1.1mm.
The history chart shows the entity accumulating all day and resetting at midnight
— that is **daily** behavior, not hourly.

---

## Root Cause

The `0x10` hex ID in Ecowitt's local API (`/get_livedata_info`) is the **midnight-reset
daily rain total**, not the hourly rain. The standard rain hex ID sequence is:

| Hex ID | Correct Name   | What our code said (wrong) |
|--------|---------------|---------------------------|
| `0x0D` | Rain Event    | Rain Event ✅              |
| `0x0E` | Rain Rate     | Rain Rate ✅               |
| `0x0F` | Hourly Rain   | (not in local API for WS90) |
| `0x10` | **Daily Rain** | **Hourly Rain** ❌         |
| `0x11` | Weekly Rain   | Weekly Rain ✅             |
| `0x12` | Monthly Rain  | Monthly Rain ✅            |
| `0x13` | Yearly Rain   | Yearly Rain ✅             |
| `0x7C` | 24-Hour Rain  | 24-Hour Rain ✅            |

The v1.5.21 "Rain Hex ID Names" fix renamed `0x10` from "Weekly" → "Hourly" when it
should have been "Daily". The shift was off by one step.

### The Ecowitt App's "Hourly" Value

The Ecowitt cloud app shows a separate "Hourly" value (e.g. 1.1mm) that is NOT
present in the local polling API (`/get_livedata_info`). The piezoRain section for
WS90 has no `0x0F` entry. Ecowitt's "Hourly" is either computed client-side or
only available via the cloud/push protocol. It cannot be exposed by this integration.

### Evidence

From @nmaster2042's screenshot taken at 20:43:
- HA "Hourly Rain" = 7mm
- Ecowitt app "Hourly" = 1.1mm, "Daily" = 7.0mm, "24 Hours" = 7.0mm

HA history chart for the entity: value builds from 0 to ~11mm over Feb 27, resets
to 0 at midnight Feb 28 → **daily behavior confirmed**.

---

## Fix

Rename `0x10` from "Hourly Rain" → "Daily Rain" in `const.py` and update the
`type_mappings` dict in `sensor_mapper.py` from `"hourly_rain"` → `"daily_rain"`.

**⚠️ Breaking change:** Entity ID changes from
`sensor.ecowitt_hourly_rain_XXXX` → `sensor.ecowitt_daily_rain_XXXX`.
Update automations and dashboards that reference `hourly_rain`.

Note: `daily_rain` slug was previously used for `0x7C` (renamed to `24h_rain` in
v1.5.26), so it is now free to use for `0x10`.

---

## Tasks

- [x] **TASK-019-1:** Rename `0x10` in `const.py` from "Hourly Rain" to "Daily Rain"
- [x] **TASK-019-2:** Update `type_mappings` in `sensor_mapper.py` (`hourly_rain` → `daily_rain`)
- [x] **TASK-019-3:** Update all `# Hourly rain` comments in `sensor_mapper.py` hex ID lists
- [x] **TASK-019-4:** Update tests referencing `hourly_rain` → `daily_rain`
- [x] **TASK-019-5:** Release v1.5.33

---

## Open Questions

- **UNRESOLVED:** Does `0x0F` appear in live data for non-piezo rain sensors (WH40, WH65)?
  If so, it could be named "Hourly Rain" for those devices. No user has provided live data
  showing `0x0F` in their payload. Do not add speculatively.
