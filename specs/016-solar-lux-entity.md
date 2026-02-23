# Spec 016: Solar Illuminance (Lux) Entity Missing

**GitHub Issues:** #84
**Status:** OPEN
**Priority:** LOW — feature request, original Ecowitt integration supports it

---

## Background

The original Ecowitt webhook integration exposes a `solar_lux` entity showing
outdoor illuminance in lux (lx). This integration currently only exposes Solar
Radiation in W/m² (`0x15`). Users coming from the webhook integration notice
the lux entity is missing.

### Request (@user, GW1100A with WH69)

> "The original ecowitt integration is showing the solar_lux entity, which
> represents the actual illuminance outside, can you add that, please?"

---

## Background on Solar Units

Ecowitt gateways can be configured to report solar data in either:
- **W/m²** (irradiance) — used for solar radiation measurement
- **Lux** (illuminance) — used for light level measurement

The relationship: `1 W/m² ≈ 126.7 lux` (for sunlight, approximately).

The integration already handles the case where the gateway sends **Klux**
(fixed in v1.5.20): it converts Klux → lx when the gateway reports in lux units.
So when the gateway is set to lux, the `0x15` entity already shows lux values.

### What the original integration does

The webhook-based Ecowitt integration receives both `solarradiation` (W/m²) and
`solarradiation_lux` (lx) as separate keys in the push data. Local polling via
`get_livedata_info` only exposes `0x15` — there is no separate lux key in the
live data API.

---

## Root Cause

The gateway's `/get_livedata_info` only exposes one solar sensor (`0x15`), and its
unit (W/m² vs lux) depends on the gateway unit setting. There is no separate lux
key in the local API — unlike the webhook protocol which sends both.

---

## Requirements

- [ ] **REQ-016-1:** When the gateway reports `0x15` in W/m², expose a computed
  illuminance entity in lux (`≈ value × 126.7 lx`) **OR** document that lux is not
  available via local polling
- [ ] **REQ-016-2:** No double-entity for users whose gateway is already reporting
  in lux (Klux case, handled by v1.5.20)

---

## Design Options

### Option A: Computed lux entity (coordinator calculates it)
Add a second entity `sensor.ecowitt_solar_lux_XXXX` computed from `0x15` W/m²:
```python
# In coordinator, after processing 0x15:
if unit == "W/m²":
    lux_value = float(value) * 126.7
    all_sensor_items.append({"id": "solar_lux", "val": str(lux_value)})
```
**Risk:** Approximate conversion, not a direct sensor reading. May confuse users.

### Option B: Let gateway unit setting control
Document that users should set their gateway to report solar in "Lux" mode —
the `0x15` entity will then show lux (handled by existing Klux fix). Only one
solar entity regardless of unit.

### Option C: No change, document limitation
The local API doesn't expose a separate lux key. Users who want lux should
configure their gateway to "Lux" mode (then `0x15` shows lux). Document this.

**Recommended: Option C** — computing lux from W/m² is an approximation (the
conversion factor varies with spectrum), and the original integration gets
separate values from Ecowitt's cloud, which we don't have in local polling.

---

## Tasks

- [ ] **TASK-016-1:** Confirm with the user whether their gateway has a "Lux" unit
  setting that would make `0x15` report in lux directly
- [ ] **TASK-016-2:** If Option A is chosen, implement computed lux entity
- [ ] **TASK-016-3:** Document the solar unit behavior in README
- [ ] **TASK-016-4:** Comment on issue #84

---

## Open Questions

- **OPEN:** Does the user's GW1100A support lux mode in unit settings? If so,
  Option C (just configure the gateway) is the answer.
- **OPEN:** Is the approximate W/m² → lux conversion acceptable to users?
