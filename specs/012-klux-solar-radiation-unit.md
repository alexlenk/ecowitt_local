# Spec 012: Solar Radiation Entity Unavailable — Klux/Lux Unit Setting

**GitHub Issue:** #44
**Status:** ✅ Fixed in v1.5.20
**Priority:** MEDIUM — affects users whose Ecowitt gateway is configured with Lux solar units

---

## Background

Ecowitt gateways allow the solar radiation measurement unit to be configured in the web UI.
The default is **W/m²** (watts per square metre), but users can select **Lux** or **Foot-candles**.

When set to **Lux**, the gateway reports values like `"0.00 Klux"` or `"42.5 Klux"` (kilolux)
for the `0x15` hex sensor key in `common_list`.

The coordinator extracted `"Klux"` as the embedded unit and overrode the entity's
`unit_of_measurement`, but the `device_class` remained `"irradiance"` (from `const.py`).
Home Assistant rejects `"Klux"` as incompatible with `irradiance` → entity unavailable.

Reported by **@hosch31** in issue #44 (GW2000A_V3.2.7 + WH80, metric/European unit settings).

---

## Live Data Evidence (issue #44)

From `get_livedata_info`:
```json
{"id": "0x15", "val": "0.00 Klux"}
```

`const.py` definition for `0x15`:
```python
"0x15": {"name": "Solar Radiation", "unit": "W/m²", "device_class": "irradiance"}
```

HA's `irradiance` device class only accepts `W/m²`. `"Klux"` is an illuminance unit
(`device_class: "illuminance"`, HA standard unit: `"lx"`).

---

## Root Cause

1. `_normalize_unit("Klux")` had no match → returned `"Klux"` unchanged
2. `unit = embedded_unit` → `unit = "Klux"`
3. `device_class` remained `"irradiance"` (not overridden by embedded unit)
4. HA: `"Klux"` + `device_class: irradiance` → incompatible → entity unavailable

---

## Fix (v1.5.20)

Three changes to `coordinator.py`:

### 1. `_normalize_unit()` — add Lux → lx

```python
elif unit_upper == "LUX":
    return "lx"
```

### 2. Main loop — convert Klux to lx (×1000)

```python
if embedded_unit and embedded_unit.upper() == "KLUX":
    try:
        sensor_value = str(float(sensor_value) * 1000)
        numeric_value = sensor_value
    except (ValueError, TypeError):
        pass
    embedded_unit = "lx"
```

### 3. Main loop — override device_class for illuminance units

```python
if unit == "lx" and device_class == "irradiance":
    device_class = "illuminance"
```

---

## Unit Conversion

| Gateway reports | Coordinator output | HA device_class |
|---|---|---|
| `"0.00 Klux"` | state=0.0, unit="lx" | illuminance |
| `"42.5 Klux"` | state=42500.0, unit="lx" | illuminance |
| `"500.0 W/m2"` | state=500.0, unit="W/m²" | irradiance (unchanged) |
| `"0.5 lux"` | state=0.5, unit="lx" | illuminance |

---

## Requirements

- [x] **REQ-012-1:** Solar radiation entity must not be unavailable when gateway reports `"Klux"`
- [x] **REQ-012-2:** Klux values must be converted to lx (×1000) so the numeric value is correct
- [x] **REQ-012-3:** `"Lux"` / `"lux"` unit strings normalise to `"lx"`
- [x] **REQ-012-4:** Existing W/m² solar radiation must be unaffected (regression)

---

## Tests Added

- `test_coordinator_klux_solar_radiation` — 42.5 Klux → state=42500.0, unit="lx", device_class="illuminance"
- `test_coordinator_klux_zero_value` — 0.00 Klux → state=0.0 (night-time)
- `test_coordinator_solar_wm2_unchanged` — 500 W/m2 → state=500.0, device_class="irradiance" (regression)
- Updated `test_coordinator_normalize_unit` — "lux"/"LUX"/"Lux" all map to "lx"
