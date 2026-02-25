# Spec 017: battery_level Attribute Shows Raw Bar Value (Issue #90)

**GitHub Issues:** #90
**Status:** FIXED — v1.5.30
**Priority:** HIGH — affects Battery State Card and HA battery dashboard for all WH90 users

---

## Background

Battery State Card (a HACS card) and the HA battery dashboard read the `battery_level`
attribute from sensor entities to display battery percentages. The WH90 battery was showing
5% (full charge) instead of 100%.

---

## Root Cause

The gateway's `/get_sensors_info` API returns a raw battery bar value on a 0–5 scale
(e.g., `"battery": "5"` for full charge). This value was stored in `sensor_details`
in `coordinator.py` and spread (`**sensor_details`) into **every entity's attributes** on
the device — not just the battery entity.

`sensor.py`'s `extra_state_attributes` then read `attributes.get("battery")` and exported
it as `ATTR_BATTERY_LEVEL` (= `"battery_level"`). Battery State Card read
`battery_level = 5.0` and displayed 5%.

```
get_sensors_info → "battery": "5"   ← raw 0-5 bar, NOT a percentage
    ↓ sensor_details spread to ALL entity attributes
    ↓
ATTR_BATTERY_LEVEL = float("5") = 5.0  ← misread as 5%
    ↓
Battery State Card: "WH90 Battery: 5%"  ← WRONG
```

---

## Fix

1. **`coordinator.py`**: Remove `"battery": hardware_info.get("battery")` from
   `sensor_details`. The raw bar value is not a percentage and must not be exposed.

2. **`sensor.py`** `extra_state_attributes`: Replace the old attribute-based logic with
   entity-state-based logic, restricted to battery-category entities:

   ```python
   # OLD (wrong — sets battery_level = raw bar on ALL entities):
   if attributes.get("battery"):
       extra_attrs[ATTR_BATTERY_LEVEL] = float(attributes["battery"])

   # NEW (correct — only on battery entities, from entity state = real percentage):
   if self._category == "battery" and self._attr_native_value is not None:
       try:
           extra_attrs[ATTR_BATTERY_LEVEL] = float(self._attr_native_value)
       except (ValueError, TypeError):
           pass
   ```

The battery entity state (e.g., `wh90batt`) is already correctly converted to a
percentage by the coordinator (e.g., `5 * 20 = 100%`).

---

## Tasks

- [x] **TASK-017-1:** Remove `"battery"` from `sensor_details` in `coordinator.py`
- [x] **TASK-017-2:** Fix `ATTR_BATTERY_LEVEL` logic in `sensor.py`
- [x] **TASK-017-3:** Update tests (`test_extra_state_attributes_hardware`,
  `test_icon_battery_levels`, add `test_extra_state_attributes_battery_entity_invalid_state`)
- [x] **TASK-017-4:** Comment on issue #90 with fix details
- [ ] **TASK-017-5:** Confirm fix with user

---

## Fixed in: v1.5.30
