# Spec 006: WH34 Pool Temperature Sensor — No Entities Created

**GitHub Issue:** #16
**Status:** ✅ Fixed in v1.5.15
**Priority:** MEDIUM — `ch_temp` array not processed by entity pipeline

---

## Background

The WH34 is a wired temperature probe sensor (8 channels). It is detected by the gateway, a device is created in HA, but **zero entities are created**.

**Hardware:** WH34 CH1 (pool temp), connected via GW1200B
**Integration:** v1.5.4, **HA:** 2025.10.2

From `get_sensors_info`:
```json
{"img": "wh31", "type": "6-13", "name": "Temp & Humidity CH1-6", "id": "6D/C1/79/8C/7/5E"}
```
(WH34 is distinct from WH31 but may share sensor registration in some gateway versions)

From `get_livedata_info`:
```json
"ch_temp": [
  {"channel": "1", "name": "", "temp": "69.3", "unit": "F", "battery": "5", "voltage": "1.52"}
]
```

The WH34 data appears in a **`ch_temp`** array — a separate data structure from `common_list` and `ch_aisle`.

---

## Root Cause

The coordinator's `_process_live_data()` method handles:
- ✅ `common_list` — gateway sensors and hex-ID sensors
- ✅ `ch_aisle` — WH31 temperature/humidity sensors (lines 241-276)
- ✅ `ch_soil` — WH51 soil moisture sensors
- ❌ **`ch_temp` — NOT PROCESSED** — WH34 pool temperature sensors

No code in coordinator.py reads the `ch_temp` array. The data is silently ignored.

### `const.py` — Partial definitions exist

```python
# Add temperature-only sensors (WH34) — lines 420-430
SENSOR_TYPES.update(_generate_channel_sensors(
    "tf_ch", "Soil Temperature CH{ch}",
    {"unit": "°F", "device_class": "temperature"}, 8
))
```

`tf_ch1` through `tf_ch8` exist in SENSOR_TYPES. However:
1. The key prefix is `tf_ch` (correct Ecowitt naming) but the coordinator must use this when processing `ch_temp`
2. The name says "Soil Temperature" but WH34 is a pool temperature sensor — name should be "Temperature CH{n}"
3. Battery key `tf_batt{n}` is in BATTERY_SENSORS — good, can be reused

### Sensor mapping for WH34

WH34 appears in `get_sensors_info` with type strings like `"Temp CH1"` through `"Temp CH8"` or similar. The sensor_mapper.py may not map these to a hardware_id — needs verification.

---

## Requirements

- [x] **REQ-006-1:** WH34 temperature entities must be created for each active channel — **fixed v1.5.15**
- [x] **REQ-006-2:** WH34 battery entities must be created — **fixed v1.5.15**
- [x] **REQ-006-3:** Entity unit must match the gateway's configured unit — **fixed v1.5.15** (reuses `_gateway_temp_unit`)
- [x] **REQ-006-4:** WH34 device already created by sensor_mapper; entities now populate via `ch_temp` — **fixed v1.5.15**

---

## Design

### Step 1: Process `ch_temp` in coordinator (analogous to `ch_aisle`)

Add `ch_temp` processing block to `_process_live_data()`:

```python
# coordinator.py — after ch_aisle block
ch_temp = raw_data.get("ch_temp", [])
if ch_temp:
    _LOGGER.debug("Found ch_temp data with %d items", len(ch_temp))
    for item in ch_temp:
        if isinstance(item, dict):
            channel = item.get("channel")
            temp = item.get("temp")
            battery = item.get("battery")

            if channel:
                if temp and temp != "None":
                    temp_key = f"tf_ch{channel}"  # matches SENSOR_TYPES key
                    # Use gateway unit setting (same fix as spec 003)
                    actual_unit = self._gateway_temp_unit  # "°C" or "°F"
                    all_sensor_items.append({"id": temp_key, "val": temp, "unit": actual_unit})

                if battery and battery != "None":
                    battery_key = f"tf_batt{channel}"  # already in BATTERY_SENSORS
                    battery_pct = str(int(battery) * 20) if str(battery).isdigit() else battery
                    all_sensor_items.append({"id": battery_key, "val": battery_pct})
```

### Step 2: WH34 sensor type detection in sensor_mapper.py

The WH34 hardware_id needs to be mapped so entities are assigned to the correct device. Check what `get_sensors_info` returns for WH34.

From issue #16's `get_sensors_info` dump, WH34 doesn't appear explicitly — the `ch_temp` data may be associated with existing sensor entries, OR WH34 may need its own sensor_mapper block.

**⚠️ Open:** Need WH34-specific `get_sensors_info` entry to know device type string and hardware_id.

### Step 3: Fix sensor name in const.py

```python
# Change "Soil Temperature" to "Temperature" for tf_ch sensors (WH34 is not soil)
_generate_channel_sensors(
    "tf_ch", "Temperature CH{ch}",  # was "Soil Temperature CH{ch}"
    {"unit": "°F", "device_class": "temperature"}, 8
)
```

**⚠️ Breaking change:** Changing the sensor name changes entity friendly names for existing users. Consider keeping old name or adding a migration.

### Files to Change
- [coordinator.py](../custom_components/ecowitt_local/coordinator.py) — add `ch_temp` processing block
- [sensor_mapper.py](../custom_components/ecowitt_local/sensor_mapper.py) — add WH34 device type detection (if needed)
- [const.py](../custom_components/ecowitt_local/const.py) — fix sensor name (optional, potentially breaking)

---

## Tasks

- [x] **TASK-006-1:** WH34 sensor_mapper block already existed (lines 286-293) — detects `wh34` or `temp_only` img values
- [x] **TASK-006-2:** Add `ch_temp` processing block to coordinator.py — done in v1.5.15 (follows ch_aisle pattern exactly)
- [x] **TASK-006-3:** WH34 sensor type detection already present in sensor_mapper.py — no changes needed
- [x] **TASK-006-4:** Renamed "Soil Temperature CH{n}" → "Temperature CH{n}" in const.py — not a breaking change (no prior entities existed)
- [x] **TASK-006-5:** `_gateway_temp_unit` applied to `ch_temp` processing — done in v1.5.15
- [x] **TASK-006-6:** 3 tests added for `ch_temp` processing (basic, Celsius gateway, empty handling)
- [x] **TASK-006-7:** Release v1.5.15 and comment on issue #16

---

## Open Questions / Blockers

- **AWAITING USER DATA:** Asked in issue #16 comment for the WH34-specific `get_sensors_info` entry (`img`, `type`, `name`, `id` fields). Needed to confirm sensor_mapper.py device type detection string.
- **OPEN:** Is `tf_batt{n}` the right battery key? Issue #16 shows `"battery": "5"` in ch_temp — need to verify the battery scale (5 × 20 = 100%? or different?).
- **RESOLVED FROM IMAGES (issue #16):**
  - **Image 1 (Ecowitt web UI Live Data):** Shows WH31 sensors CH1–CH6 all in Fahrenheit. At the bottom, "CH1 Temperature: 69.3°F" is visible — this is the WH34 pool sensor being reported by the gateway correctly.
  - **Image 2 (HA device list):** Device "Ecowitt Sensor 44D3" appears with model `wh34`, manufacturer `Ecowitt`, under the Ecowitt Local integration. **No battery icon is shown** (unlike WH31 sensors which all show 0% battery). WH31 devices (5E, 6D, 7, 8C, C1, 79) all have battery readings. Gateway "Family Room" (GW1200B) and WH26 also present.
  - **Images 3–7 (HA entity lists per device):** Every WH31 device has exactly 7 entities: Channel, Battery, Humidity, Temperature, Online, Hardware ID, Signal Strength. The "Family Room" gateway device has 10 entities (Absolute Pressure, Dewpoint Temperature, Humidity Outdoor/Indoor, Temperature Outdoor/Indoor, Online, Feels Like Temperature, Relative Pressure, Vapor Pressure Deficit). **No entity list screenshot shows any entity under "Ecowitt Sensor 44D3" (wh34)** — confirming zero entities are created for the WH34.
  - **Key finding:** The WH34 hardware ID is `44D3` (from device name "Ecowitt Sensor 44D3"). This matches the `get_sensors_info` entry that would show `"id": "44D3"` for a `wh34` type sensor. The device is created but no entities populate because `ch_temp` data processing is not implemented.
- **RESOLVED FROM COMMENT IMAGE (issue #16, @chrisgillings):** Second user confirms multiple devices affected. Device list shows:
  - "Ecowitt Temp Lead CH1" and "Ecowitt Temp Lead CH3" — model `wh34`, no entity count → confirms WH34 naming pattern and multi-channel support needed
  - "Ecowitt Lightning Sensor EA2A" — model `wh57`, no entities
  - "Ecowitt Rain Sensor 1C2ED" — model `wh40`, no entities
  - "Ecowitt Temp/Humidity Sensor Pergola" — model `wh26`, no entities
  - WH31 sensors correctly showing 7 entities each
  - **Additional issue:** WH26, WH40, WH57 also lack entities — separate bugs, not addressed in this spec.
- **DEPENDENCY RESOLVED:** Spec 003 (`_gateway_temp_unit`) is now implemented in v1.5.14. `ch_temp` processing can reuse `self._gateway_temp_unit` directly.
