# Spec 016: Solar Illuminance (Lux) Entity Missing

**GitHub Issues:** #84
**Status:** IMPLEMENTING — Option A (computed lux entity)
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

### Confirmed: Gateway Lux Mode Does NOT Change Local API Response

User @dMopp confirmed (issue #84) that even after switching the gateway UI to
"Lux" mode, the local API still returns `"val": "21.35 W/m2"`. The gateway
setting only affects the cloud/push protocol, not the local HTTP API.

This means **Option B/C (use gateway setting) does not work**. The local API
always returns W/m² regardless of the unit setting.

---

## Requirements

- [x] **REQ-016-1:** When the gateway reports `0x15` in W/m², expose a computed
  illuminance entity in lux (`≈ value × 126.7 lx`)
- [x] **REQ-016-2:** No double-entity for users whose gateway is already reporting
  in lux (Klux case, handled by v1.5.20) — lux entity is only added when unit is W/m²

---

## Design Decision: Option A — Computed Lux Entity

**Why not Option B/C:** The gateway's local API (`/get_livedata_info`) returns W/m²
regardless of the unit setting in the gateway web UI. Telling users to "switch to
Lux mode" does not change the local API response.

**Why Option A works:**
- The conversion factor `1 W/m² ≈ 126.7 lux` is standard for sunlight
- The same approximation is used by the webhook-based Ecowitt integration
- It provides a directly comparable `solar_lux` entity for users migrating from
  webhook to local polling

**Implementation:**
```python
# In coordinator.py processing loop, after creating 0x15 entity:
if sensor_key == "0x15" and unit == "W/m²":
    try:
        lux_val = round(float(sensor_value) * 126.7, 1)
        # Create solar_lux entity with same hardware_id
        ...
    except (ValueError, TypeError):
        pass
```

The entity only appears when the unit is W/m². If the gateway ever starts
sending lux directly (unit = "lx"), the existing entity handles it and no
duplicate lux entity is created.

---

## Tasks

- [x] **TASK-016-1:** Confirm gateway behavior with user (gateway sends W/m² always)
- [x] **TASK-016-2:** Implement computed lux entity in coordinator.py
- [x] **TASK-016-3:** Add `solar_lux` to SENSOR_TYPES in const.py
- [x] **TASK-016-4:** Add `solar_lux` type mapping in sensor_mapper.py
- [ ] **TASK-016-5:** Comment on issue #84 with fix details

---

## Implementation Notes

- Entity key: `solar_lux`
- Entity ID format: `sensor.ecowitt_solar_lux_{hardware_id}` (e.g. `sensor.ecowitt_solar_lux_4094a8`)
- Unit: `lx`
- Device class: `illuminance`
- State class: `measurement`
- Same hardware_id as the `0x15` solar radiation entity → appears on the same device
- Conversion: `lux = round(float(w_per_m2) * 126.7, 1)`
- Only created when `sensor_key == "0x15"` and `unit == "W/m²"`
- Fixed in: **v1.5.29**
