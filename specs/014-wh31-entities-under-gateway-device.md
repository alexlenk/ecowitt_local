# Spec 014: WH31 Entities Appear Under Gateway Device, WH31 Device Empty

**GitHub Issues:** #19 (comment by @AnHardt)
**Status:** ✅ Likely FIXED — @chrisgillings (issue #19, 2026-02-26) confirms WH31 device shows correctly as "wh31 by Ecowitt" with Temperature and Humidity entities under it
**Priority:** MEDIUM — WH31 temperature/humidity entities work but are under wrong device

---

## Background

When a WH31 sensor is paired, the integration creates a WH31 device in HA (from
`get_sensors_info`), but the temperature and humidity entities appear under the
**Gateway device** instead of the WH31 device. The WH31 device shows as empty.

### Confirmed Evidence (@AnHardt, GW1100A_V2.4.4)

> "A empty device WH31 is generated in HA. The indoor sensors values are reported
> in the gateway's device."

---

## Root Cause Analysis

### How `get_sensors_info` creates devices

The sensor_mapper sees:
```json
{"img": "wh31", "type": "6", "name": "Temp & Humidity CH1", "id": "6D", ...}
```
→ Creates hardware_id mapping for WH31 CH1 (`"6D"`)
→ HA device created for hardware_id `"6D"`

### How `ch_aisle` entities are assigned

In `sensor_mapper._generate_live_data_keys("wh31", "1")`:
```python
keys = ["temp1f", "humidity1", "batt1"]
```
So `_hardware_mapping["temp1f"] = "6D"` should be set.

### Possible failure points

1. **Channel extraction mismatch:** `get_sensors_info` name `"Temp & Humidity CH1"` →
   `_extract_channel_from_name()` extracts `"1"`. But the live data key is `"temp1f"`.
   If the channel is extracted as `"1"` and key generated as `"temp1f"`, this should work.

2. **FFFFFFFF id:** If the WH31 shows `"id": "FFFFFFFF"` in `get_sensors_info`
   (not yet paired/synced), then `_hardware_mapping["temp1f"] = "FFFFFFFF"`. A device
   is created for FFFFFFFF but temp1f entity gets hardware_id FFFFFFFF — may not
   match what coordinator expects.

3. **Battery key mismatch:** Coordinator may create key `battch1` or `battery1` but
   sensor_mapper generates `batt1` — entity ends up without hardware_id.

**⚠️ Investigation needed:** Need @AnHardt's `get_sensors_info` output to confirm
which failure point applies.

---

## Requirements

- [ ] **REQ-014-1:** WH31 temperature and humidity entities must appear under the
  WH31 device (not the gateway device)
- [ ] **REQ-014-2:** WH31 device must not appear empty in HA
- [ ] **REQ-014-3:** No regression for other sensor types that use channel-based keys

---

## Design (pending investigation)

Once root cause is confirmed, fix is likely one of:

**A) Channel extraction bug:** Fix `_extract_channel_from_name` to correctly parse
WH31 name format → correct channel → correct `temp{n}f` key generated

**B) FFFFFFFF handling:** Skip hardware_id assignment for FFFFFFFF sensors (treat
as no hardware_id), so entities fall to gateway device without an empty orphan device

**C) Battery key:** Align coordinator's ch_aisle battery key with sensor_mapper's
expected `batt{n}` key

---

## Tasks

- [ ] **TASK-014-1:** Get `get_sensors_info` output from an affected user (WH31 with id != FFFFFFFF)
- [ ] **TASK-014-2:** Add debug logging to trace `temp1f` → hardware_id lookup path
- [ ] **TASK-014-3:** Implement fix based on root cause found
- [ ] **TASK-014-4:** Test WH31 entities appear under correct device

---

## Open Questions

- **OPEN:** Is the WH31 id "FFFFFFFF" or a real id in @AnHardt's `get_sensors_info`?
- **OPEN:** Does coordinator create `batt1` or some other key for ch_aisle battery?
