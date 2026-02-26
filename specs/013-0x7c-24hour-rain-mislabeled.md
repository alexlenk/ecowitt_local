# Spec 013: 0x7C Rain Entity Mislabeled as "Daily Rain"

**GitHub Issues:** #5
**Status:** ✅ FIXED — v1.5.26
**Priority:** HIGH — all WH90/WH69/WS90 users see wrong rain values

---

## Background

The `0x7C` hex ID rain sensor is labeled "Daily Rain" in the integration, but it
actually contains **rolling 24-hour rain** (not calendar daily reset at midnight).

### Confirmed Evidence (issue #5, @nmaster2042)

| Source | Value | Label |
|--------|-------|-------|
| HA integration | 13 mm | "Daily Rain" |
| Ecowitt web "24 Hours" | 12.8 mm | 24-hour rolling rain ✓ |
| Ecowitt web "Daily" | 0.2 mm | Calendar daily (midnight reset) |

The integration's "Daily Rain" matches Ecowitt's "24 Hours" — confirming `0x7C` is
rolling 24h rain. The actual calendar daily rain (0.2 mm) has no entity in the integration.

---

## Root Cause

In `const.py`:
```python
"0x7C": {
    "name": "Daily Rain",   # ← WRONG
    ...
}
```

The Ecowitt gateway reports two distinct rain accumulations:
- `0x7C` — 24-hour rolling window (last 24h regardless of midnight)
- Calendar daily — resets at midnight (hex ID unknown; may not be in `common_list`/`rain` array, or may use a different ID per sensor type)

---

## Requirements

- [ ] **REQ-013-1:** `0x7C` must be labeled "24-Hour Rain" with entity_id slug `24h_rain`
- [ ] **REQ-013-2:** No regression for users who have automations referencing `daily_rain` entity IDs — document breaking change in CHANGELOG
- [ ] **REQ-013-3:** Investigate whether a separate calendar daily rain hex ID exists and can be added

---

## Design

### Fix 1: Rename 0x7C (confirmed, implement now)

In `const.py`:
```python
"0x7C": {
    "name": "24-Hour Rain",
    "unit": "mm",
    "device_class": "precipitation",
    "state_class": "total_increasing",
}
```

Note: entity_id will change from `sensor.ecowitt_daily_rain_XXXX` → `sensor.ecowitt_24h_rain_XXXX`.
This is a breaking change — document in CHANGELOG.

### Fix 2: Calendar daily rain (investigation needed)

The GW2000/WH90 rain array observed in the wild:
```
0x0D = Rain Event
0x0E = Rain Rate
0x7C = 24-Hour Rain (rolling)
0x10 = Hourly Rain
0x11 = Weekly Rain
0x12 = Monthly Rain
0x13 = Yearly Rain
```

No calendar "Daily Rain" (midnight reset) appears in the WH90 rain array. Ecowitt may
compute this in their app only, or it may be in a hex ID not yet observed.

**⚠️ Open question:** Is there a separate daily rain hex ID, or is Ecowitt's "Daily"
a client-side calculation? Need data from a user who resets at midnight to observe.

---

## Tasks

- [x] **TASK-013-1:** Rename `0x7C` in `const.py` from "Daily Rain" to "24-Hour Rain" — done in v1.5.26
- [x] **TASK-013-2:** Update entity_id slug comment in sensor_mapper `hex_to_name` — done in v1.5.26
- [x] **TASK-013-3:** Document entity_id change in CHANGELOG — done in v1.5.26
- [x] **TASK-013-4:** Update tests that reference `daily_rain` entity IDs — done in v1.5.26
- [x] **TASK-013-5:** Ask users to confirm if calendar daily rain should be a separate entity — asked; no separate hex ID found

---

## Open Questions

- **UNRESOLVED:** No calendar daily rain hex ID has been identified in any user's `get_livedata_info`. Ecowitt likely computes this client-side only. No action needed unless a user provides data showing a separate hex ID.
- **CONFIRMED:** `0x7C` is 24-hour rolling rain across all observed sensor types (WH90, WH69, WS90).
