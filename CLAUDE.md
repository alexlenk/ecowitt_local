# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Ecowitt weather stations that uses local web interface polling instead of webhooks. The integration creates stable entity IDs based on hardware IDs and organizes sensors into individual devices for better management.

## ⚠️ CRITICAL: Entity Creation Pipeline Issues

**IMPORTANT**: This codebase has ongoing entity creation failures despite proper device detection. The primary issues are incomplete entity sets and mapping pipeline failures, not architectural violations. Focus on debugging the entity creation flow rather than mapping logic.

## Development Commands

### Local environment
The project uses a virtualenv at `.venv/` in the project root.
- **Python**: Homebrew Python 3.14 at `/opt/homebrew/bin/python3`
- **Create venv**: `python3 -m venv .venv && .venv/bin/pip install -r requirements_test.txt`

### Testing
```bash
# Run all tests with coverage (ALWAYS use .venv, not system python)
PYTHONPATH="$PWD" .venv/bin/pytest tests/ -v

# Run with coverage report
PYTHONPATH="$PWD" .venv/bin/pytest tests/ --cov=custom_components/ecowitt_local --cov-report=term-missing
```

**Coverage must be 100%.** If coverage drops, add tests before committing.

### ⚠️ Mandatory pre-commit checklist

Run ALL of these before every commit. CI will fail if any step is skipped.

```bash
# 1. Format
black custom_components/ecowitt_local/ tests/

# 2. Sort imports
isort custom_components/ecowitt_local/ tests/

# 3. Type check (must show "Success: no issues found")
mypy custom_components/ecowitt_local/ --follow-imports=silent --ignore-missing-imports

# 4. Full test suite with coverage (must be 100%)
PYTHONPATH="$PWD" .venv/bin/pytest tests/ --cov=custom_components/ecowitt_local --cov-report=term-missing
```

### Development Dependencies
Install test requirements: `pip install -r requirements_test.txt`

## Architecture Overview

### Core Components

**Integration Entry Point** (`__init__.py:23`): Sets up coordinator, device registry, platforms, and services in a specific order to ensure proper entity-device relationships.

**Data Coordinator** (`coordinator.py`): Manages two separate polling intervals:
- Live data polling (60s default) for sensor readings
- Sensor mapping polling (600s default) for hardware ID discovery

**API Client** (`api.py`): Handles authentication and communication with Ecowitt gateway web interface. Supports both authenticated and non-authenticated gateways.

**Sensor Mapping** (`sensor_mapper.py`): Critical component that maps raw sensor data keys to hardware IDs and device information. This enables stable entity IDs and proper device organization.

### Entity Organization

The integration creates individual Home Assistant devices for each physical sensor rather than grouping everything under the gateway. Each device contains:
- Primary sensor entities (temperature, humidity, etc.)
- Diagnostic entities (battery, signal strength, online status)

### Hardware ID Strategy

Entity IDs are based on hardware IDs extracted from the gateway's sensor mapping, ensuring stability across battery changes and reconnections:
- `sensor.ecowitt_soil_moisture_d8174` (hardware ID: D8174)
- `sensor.ecowitt_temperature_a1b2c3` (hardware ID: A1B2C3)

## Key Integration Points

### Device Registry Setup
Device creation happens in `__init__.py:40` before platform setup to ensure entities find their proper parent devices.

### Migration System
The integration includes migration logic in `__init__.py` to handle updates from older versions and reassign entities to correct devices.

### Error Handling
Authentication errors trigger re-authentication. API failures are logged but don't crash the integration, allowing recovery on next update cycle.

## Testing Strategy

The codebase uses comprehensive mock data testing for device types not physically available, validated against the `aioecowitt` library's sensor mappings. Physical testing is done with WH51 soil moisture sensors.

Test coverage is maintained at **100%** with 330+ automated tests covering device discovery, entity creation, hardware ID mapping, and edge cases.

## Configuration

The integration uses Home Assistant's config flow with these key options:
- Host IP address (required)
- Password (optional, for protected gateways)
- Live data polling interval (30-300s)
- Sensor mapping interval (300-3600s)
- Include inactive sensors flag

---

# 🎯 Issue Analysis Patterns & Solutions

*The following patterns were learned through extensive issue analysis. These guide how to approach common problems in this integration.*

## Common Device Mapping Issues

### Pattern: Device Type String Mismatch
- **Problem**: New weather stations report device type strings that don't match expected patterns
- **Example**: WH90 reports as `"Temp & Humidity & Solar & Wind & Rain"` instead of `"wh90"`
- **Solution**: Add device type string matching to `sensor_mapper.py` 
- **Files**: `custom_components/ecowitt_local/sensor_mapper.py`
- **Approach**: Extend existing `elif` conditions with `or "actual device string" in sensor_type.lower()`
- **Fixed in**: v1.4.8 (WH90 support)

### Pattern: Incomplete Entity Creation
- **Problem**: Devices detected correctly but creating incomplete entity sets (e.g., WH69 shows 7 entities instead of 12)
- **Devices**: WH69, WH77, GW2000A combinations, WH31 sensors
- **Root Cause**: Entity creation pipeline failures in coordinator.py or sensor.py
- **Evidence**: Issue #11 shows WH69 with partial entities despite proper device detection
- **Solution Focus**: Debug entity creation flow, not device type detection

---

# 🔍 Real Issues & Evidence-Based Analysis

*Based on actual user reports and codebase analysis.*

## Current Architecture Reality

### Hex ID System Implementation
- **Location**: Hex IDs explicitly defined in `sensor_mapper.py` (lines 184-247) for WH69, WS90, WH90
- **Purpose**: Maps device types to specific hex ID lists for entity creation
- **const.py Role**: Contains sensor metadata (names, units, device classes) for hex IDs
- **No Fallthrough**: No automatic common_list processing - explicit mapping required

### Evidence from Issues
1. **Issue #11**: WH69 only creates 7 entities instead of 12 despite explicit hex ID mapping
2. **Issue #6**: WH90 fixed with single-line device type detection (commit 15ec621)
3. **Multiple Reports**: Entity creation failures across different device combinations

## Proven Successful Patterns

### ✅ Minimal Device Type Detection (WH90 Success)
```python
# Single line fix that resolved Issue #6:
elif sensor_type.lower() in ("wh90", "weather_station_wh90") or "temp & humidity & solar & wind & rain" in sensor_type.lower():
```
**Why it worked**: Used existing hex ID infrastructure without modification

### ✅ Device-Specific Hex ID Lists (Current Working System)
- WH69, WS90, WH90 all have explicit hex ID lists in sensor_mapper.py
- This is the PRIMARY mechanism for hex ID device support
- Reuses sensor definitions from const.py for metadata

## ⚠️ Actual Problems to Avoid

### DO NOT: Assume Current System Works Perfectly
- **Reality**: Multiple users report incomplete entity creation
- **Evidence**: WH69 users getting 7 entities instead of 12
- **Focus**: Debug entity creation pipeline, not device detection

### DO NOT: Over-Engineer Solutions
- **Success Pattern**: WH90 fixed with 1-line change
- **Approach**: Minimal modifications that reuse existing infrastructure
- **Test**: Validate against actual user reports

---

# 📜 Ecowitt HTTP API Spec — Authoritative Reference

**Always cross-check sensor questions against the official spec, not just the codebase.** The spec is the source of truth for what fields the gateway *can* emit.

> ⚠️ **Spec ≠ confirmed gateway behavior.** The spec describes the protocol surface; it does NOT guarantee that any specific firmware on any specific gateway model actually emits a given field today. The ✅/❌ markers below reflect *code coverage*, not *user-reported bugs*. Before "fixing" a ❌ entry, confirm the gateway in the user's hands actually sends that field — request a `get_livedata_info` JSON dump or wait for a user report. The issues filed in 2026-05 against the V1.0.6 spec audit (#158–#174) are mostly **spec-derived findings awaiting field verification**, not actively-hit user bugs (with the exception of #158, #164, #173, #174 which are confirmed by code analysis alone).

## Spec Document

- **Current version**: V1.0.6 (2026-01-09) — *check the URL pattern for newer versions*
- **URL**: https://oss.ecowitt.net/uploads/20260114/HTTP%20API%20interface%20Protocol%20(Generic)-(V1.0.6-2026-1-14)%20.pdf
- **How to read it**: WebFetch returns garbled binary for this PDF. Save the file and run:
  ```bash
  pdftotext -layout /path/to/spec.pdf /tmp/spec.txt
  ```

## Spec Changelog (lifelong)

| Version | Date | Notable additions |
|---------|------|------------------|
| V1.0.3 | 2024-12-18 | `ch_lds` and `debug` blocks added to `get_livedata_info`; `Get_cli_lds`/`Set_cli_lds` API; MQTT support |
| V1.0.4 | 2025-04-14 | New CO2-block fields: `PM10`, `PM1`, `PM4` and their `_RealAQI`/`_24HAQI`/`_24H` variants; `CO2_24H`; `level` and `total_heat` for LDS |
| V1.0.5 | 2025-10-08 | `eWN20_SENSOR` (type 70) and `eWN38_SENSOR` (type 71, BGT) added to `get_sensors_info` |
| V1.0.6 | 2026-01-09 | `get_livedata_info` adds **VPD**, **BGT** (`0xA1`), **WBGT** (`0xA2`), and multi-channel EC (`ch_ec`) |

## `get_livedata_info` Block Layout

The endpoint can return up to 14 top-level blocks. Each is processed independently in `coordinator.py`:

| Block | Sensor | Status |
|-------|--------|--------|
| `common_list` | Outdoor weather (hex IDs) | ✅ processed |
| `rain` | WH40/WH69 tipping bucket | ✅ processed |
| `piezoRain` | WS90/WH90/WS85 piezo rain | ✅ processed |
| `wh25` | Indoor T/H/pressure | ✅ processed |
| `lightning` | WH57 lightning | ✅ processed |
| `co2` | WH45/WH46D combo | ✅ processed |
| `ch_pm25` | WH41 PM2.5 channels | ✅ processed |
| `ch_leak` | WH55 leak channels | ✅ processed |
| `ch_aisle` | WH31 T/H channels | ✅ processed |
| `ch_soil` | WH51 soil moisture channels | ✅ processed |
| `ch_temp` | WH34 temp-only channels | ✅ processed |
| `ch_leaf` | WH35 leaf wetness channels | ✅ processed |
| `ch_lds` | WH54 liquid depth channels | ❌ NOT processed (issue #164) |
| `ch_ec` | WH52 soil EC channels | ✅ processed (vendor) |
| `debug` | heap, runtime, usr_interval | ❌ not exposed (low priority) |

## Complete `common_list` Hex-ID Catalog

| Hex ID | Spec field | Unit | Status |
|--------|-----------|------|--------|
| `0x01` | ITEM_INTEMP — Indoor Temp | °C | ❌ via common_list (issue #172) |
| `0x02` | ITEM_OUTTEMP — Outdoor Temp | °C | ✅ |
| `0x03` | ITEM_DEWPOINT — Dew Point | °C | ✅ |
| `0x04` | ITEM_WINDCHILL — Wind Chill | °C | ❌ (issue #170) |
| `0x05` | ITEM_HEATINDEX — Heat Index | °C | ❌ (issue #171) |
| `0x06` | ITEM_INHUMI — Indoor Humidity | % | ❌ via common_list (issue #172) |
| `0x07` | ITEM_OUTHUMI — Outdoor Humidity | % | ✅ |
| `0x08` | ITEM_ABSBARO — Absolute Pressure | hPa | ❌ via common_list (issue #172) |
| `0x09` | ITEM_RELBARO — Relative Pressure | hPa | ❌ via common_list (issue #172) |
| `0x0A` | ITEM_WINDDIRECTION | ° | ✅ |
| `0x0B` | ITEM_WINDSPEED | m/s | ✅ |
| `0x0C` | ITEM_GUSTSPEED | m/s | ✅ |
| `0x0D` | ITEM_RAINEVENT | mm | ✅ |
| `0x0E` | ITEM_RAINRATE | mm/h | ✅ |
| `0x0F` | ITEM_RAIN_GAIN — calibration multiplier | — | ⚠️ silently skipped (issue #168) |
| `0x10` | ITEM_RAINDAY — **Daily Rain** (NOT Hourly) | mm | ✅ |
| `0x11` | ITEM_RAINWEEK — Weekly Rain | mm | ✅ |
| `0x12` | ITEM_RAINMONTH — Monthly Rain | mm | ✅ |
| `0x13` | ITEM_RAINYEAR — Yearly Rain | mm | ✅ |
| `0x14` | ITEM_RAINTOTALS — All-time cumulative | mm | ❌ (issue #161) |
| `0x15` | ITEM_LIGHT — Solar Radiation | W/m² | ✅ |
| `0x16` | ITEM_UV — UV irradiance | uW/m² | ❌ (issue #160) |
| `0x17` | ITEM_UVI — UV Index | 0–15 | ✅ |
| `0x18` | ITEM_TIME — Date/time | — | ⚠️ not a sensor |
| `0x19` | ITEM_DAYLWINDMAX — Daily max gust | m/s | ✅ |
| `0xA1` | BGT — Black Globe Temp | °C | ✅ |
| `0xA2` | WBGT — Wet Bulb Globe Temp | °C | ✅ |
| `0x6D` | Wind Direction Avg (vendor, NOT in spec) | ° | ✅ — observed on WS80/GW3000 |
| `0x7C` | 24-Hour Rain (vendor, NOT in spec) | mm | ✅ — observed on WS90 |

### Decimal-string IDs in `common_list` (NOT hex)

| ID | Meaning | Status |
|----|---------|--------|
| `"3"` | Feel Like (decimal 3, ≠ `"0x03"` Dew Point) | ⚠️ partial implementation (issue #173) |
| `"4"` | Unknown — `SENSOR_TYPES` has it as "Apparent Temperature" but not in spec | ⚠️ dead code (issue #173) |
| `"5"` | VPD (decimal 5, ≠ `"0x05"` Heat Index) — added v1.0.6 | ⚠️ partial implementation (issues #162, #173) |

> **CRITICAL**: `"3"` and `"0x03"` are different keys in the JSON response. Same numeric value, different sensors. Treat them as distinct strings throughout.

## Battery Encoding by Sensor (per `get_sensors_info` enum)

The spec defines **three encoding schemes**. Real-world livedata behavior may differ from spec text — see [issue #174](https://github.com/alexlenk/ecowitt_local/issues/174).

| Encoding | Sensors | Conversion |
|----------|---------|-----------|
| **Binary** (0=normal, 1=low) | WH65, WH25, WH26, WH31 (`ch_aisle`), WH51 (`ch_soil`) | `0→100%, 1→10%` |
| **0–5 bar level** | WH41 (`ch_pm25`), WH57 (`lightning`), WH55 (`ch_leak`), WH45 (`co2`) | `val × 20%` |
| **Voltage** (`val × 0.02V`; low ≤ 1.2V) | WH68, WH80, WH40 (`rain`), WH34 (`ch_temp`), WH35 (`ch_leaf`), WH54 (`ch_lds`), WH85, WH90 (`piezoRain`) | spec: voltage; observed: gateway often normalizes to 0–5 bars |

**`get_sensors_info`** always returns `batt` as 0–5 bars regardless of underlying encoding. **`get_livedata_info`** behavior is firmware-dependent and inconsistent — issue #138 (closed unresolved) hinted at this.

## Sensor Enum (`get_sensors_info` types)

```
0   WH65          26  WH57 (Lightning)        49  WH85 (Wind & Rain)
1   WH68          27-30  WH55_CH1-4           58-65  WH51_CH9-16
2   WH80          31-38  WH34_CH1-8           66-69  WH54_CH1-4 (LDS)
3   WH40          39  WH45 (CO2/PM combo)     70  WN20 (NEW v1.0.5, unsupported)
4   WH25          40-47  WH35_CH1-8           71  WN38 (BGT, supported as 0xA1)
5   WH26          48  WH90
6-13   WH31_CH1-8
14-21  WH51_CH1-8
22-25  WH41_CH1-4
```

WH65 and WH69 share `img: "wh69"` and name `"Temp & Humidity & Solar & Wind & Rain"` (same as WH90). Disambiguate by `type` and `id`.

## Adding Support for a New Sensor — 4-Place Update Pattern

When a new sensor type is added, **all four locations** must be updated or the entity won't appear correctly:

1. **`sensor_mapper.py` — name mapping**
   - For hex IDs: add to `hex_to_name` dict (~line 550)
   - For decimal-string IDs: add to `decimal_id_names` dict (~line 540)

2. **`sensor_mapper.py` — device key list** in `_generate_live_data_keys` (~line 136+)
   - Add the key to every device type that emits this field
   - Without this, `get_hardware_id()` returns `None` → **orphan entity** (entity created but no parent device — same shape as issue #173)

3. **`const.py` — `SENSOR_TYPES`** entry with `name`, `unit`, `device_class`
   - For batteries: add to `BATTERY_SENSORS` instead
   - For binary: add to `BINARY_SENSORS`

4. **`coordinator.py`** — only if the sensor lives in a **non-`common_list` block** (e.g. `ch_lds`, `co2`, `ch_pm25`). `common_list` items flow through automatically once steps 1–3 are done.

If `get_sensors_info` registers a device but no entity is ever produced for it, that's a **phantom device** — same shape as the v1.6.18 phantom WH69 fix and issue #164 (WH54). Always check both ends of the pipeline (`get_sensors_info` device registration AND `get_livedata_info` block parsing).

---

### Two-Part Architecture
1. **sensor_mapper.py**: Device-specific hex ID mapping lists (lines 184-247)
   - Maps device types to hex ID keys they should handle
   - **Required** for entity creation - no automatic fallthrough exists

2. **const.py**: Hex ID sensor metadata (lines 276-360) 
   - Defines what each hex ID represents (name, unit, device_class)
   - **Shared** across all hex ID devices for consistency

### Actual Implementation Pattern
```python
# In sensor_mapper.py - How hex ID devices are ACTUALLY implemented:
elif sensor_type.lower() in ("wh69", "weather_station_wh69"):
    keys.extend([
        "0x02",  # Temperature - explicit mapping required
        "0x07",  # Humidity
        "0x0B",  # Wind speed
        # ... full hex ID list
        "wh69batt",  # Battery
    ])
```

### Why This Architecture Exists
- **common_list data format**: `{"id": "hardware_id", "val": "value", "ch": "0x02"}`
- **Mapping requirement**: Must know which hex IDs belong to which device type
- **Entity creation**: coordinator.py needs explicit mapping to create entities

## Minimal, Surgical Changes

- **Prefer single-line additions** over large modifications
- **Test compatibility** with existing devices
- **Validate against architecture** before implementing

---

# 🏆 Success Patterns

## Example: WH90 Support (v1.4.8) - Actual Implementation

**Problem**: WH90 not creating entities  
**Root Cause**: Device type string mismatch  
**Solution**: Single line addition to EXISTING hex ID device block

```python
# BEFORE: WH90 not detected
elif sensor_type.lower() in ("wh90", "weather_station_wh90"):
    keys.extend([...])  # Had hex ID list but wrong device type detection
    
# AFTER: WH90 works perfectly (ONE LINE ADDED)
elif sensor_type.lower() in ("wh90", "weather_station_wh90") or "temp & humidity & solar & wind & rain" in sensor_type.lower():
    keys.extend([...])  # Same hex ID list, better device type detection
```

**Key**: Fixed device type detection string matching, reused existing hex ID infrastructure

**Evidence**: Commit 15ec621 shows the actual minimal change that worked

---

# 🧪 Testing & Validation Requirements

## CRITICAL: CI Monitoring and Learning

**MANDATORY PROCESS**: After implementing any changes, the bot MUST:

1. **Monitor CI Results**: Wait for GitHub Actions CI to complete on the created branch
2. **Analyze Failures**: If CI fails, analyze the test failures and error messages
3. **Fix Issues**: Update the implementation to address any test failures
4. **Learn from Failures**: Update approach based on what the tests reveal
5. **Iterate Until Success**: Continue fixing until all tests pass

### CI Workflow Monitoring

The CI runs on `claude/**` branches and includes:
- Full test suite (330+ tests)
- Coverage reporting (must maintain **100%**)
- Multiple Python versions (3.12, 3.13)
- black, isort, flake8, mypy checks
- hassfest and HACS validation

**If CI fails, the implementation is WRONG and must be fixed before doing anything else.**

To check CI status after pushing:
```bash
gh run list --branch <branch-name> --limit 5
gh run view <run-id> --log-failed   # if failed
```

### Learning from Test Failures & User Reports

Common failure patterns and their meanings:

- **Incomplete entity creation**: Device detected but missing entities (WH69: 7 instead of 12)
- **Entity naming inconsistencies**: Check sensor metadata in const.py
- **Coverage drops**: Missing test coverage for new code paths
- **Regression failures**: Changes broke existing device functionality
- **User reports of "no entities"**: Usually device type detection issues

**Update implementation based on**:
- Test feedback for code quality
- User issue reports for real-world functionality
- Actual commit history showing what worked (WH90 fix)

## Issue Management Protocol

**CRITICAL**: When fixing GitHub issues, follow this exact protocol:

### Reading Issues

Always read the full issue body **and all comments**. If an issue contains screenshots or images, always download and view them — they often contain critical data (entity lists, livedata JSON, error messages) not present in the text.

```bash
# Download and view an image from a GitHub issue
curl -sL "<image-url>" -o /tmp/issue_image.png
# Then use the Read tool to view it
```

### After Implementing a Fix:
1. **Create release** with the fix
2. **Comment on the issue** explaining the fix and requesting user testing
3. **DO NOT close the issue** - leave it open for user confirmation
4. **Wait for user feedback** confirming the fix works
5. **Only close issues** after users confirm the fix resolved their problem

### Comment Template:
```markdown
## 🎯 Fix Available - Please Test

Hi! I've just released **vX.X.X** which should fix [describe the issue].

### What was fixed:
- [Detailed explanation of the changes]

### Please test:
1. **Update to vX.X.X** (available now)
2. **Test the specific functionality** that was failing
3. **Report back** if the issue persists after this update

### Expected behavior:
- [What should work now]

Let me know how it works for you. 🚀
```

**Never close issues prematurely** - user confirmation is required for all fixes.

## Before Any Device Support Changes

1. **Understand the architecture**: Read the Anti-Patterns section
2. **Check existing patterns**: See how WH69/WS90 work  
3. **Plan minimal changes**: Single line additions preferred
4. **Commit and monitor**: Wait for CI results and fix any failures

## Devices — Do NOT Implement

- **WH77**: This is a testing/internal sensor. Do not add support for it under any circumstances, even if a user requests it.

## Device Addition Checklist (Evidence-Based)

### For New Hex ID Devices
- [ ] Add device type detection to `sensor_mapper.py`
- [ ] Add hex ID list for the device (follow WH69/WS90/WH90 pattern)
- [ ] Reuse existing hex ID definitions from const.py (DO NOT duplicate metadata)
- [ ] Add battery mapping to const.py if device has battery sensor
- [ ] **Debug entity creation pipeline** if entities still missing
- [ ] **CI passes completely** (all tests, all Python versions)
- [ ] **Validate against user reports** - check for incomplete entity sets

### For Entity Creation Issues
- [ ] Focus on coordinator.py entity processing logic
- [ ] Check sensor.py entity creation flow
- [ ] Verify hardware ID mapping is working correctly
- [ ] Test with actual device data structures

---

# Implementation Philosophy

**"Extend existing patterns rather than creating new ones"**

When adding device support:
1. ✅ Add device type detection with proper string matching
2. ✅ Add device-specific hex ID lists (follow existing WH69/WS90/WH90 pattern)
3. ✅ Reuse hex ID metadata from const.py (names, units, device classes)
4. ❌ Never duplicate hex ID metadata definitions in const.py
5. ✅ Focus on debugging entity creation pipeline for missing entities

**When in doubt**: 
- Look at WH69/WS90/WH90 implementation in sensor_mapper.py (lines 182-247)
- Follow the proven pattern that actually exists in the codebase
- Test against real user reports, not theoretical architecture

---

# 🧠 Memory and Learning Requirements

## Update Memory with Learnings

After each implementation attempt, the bot MUST update its memory with:

### What Worked
- Successful patterns that passed CI
- Minimal changes that achieved the goal
- Architectural approaches that maintained compatibility

### What Failed  
- Approaches that caused test failures
- Anti-patterns that violated architecture
- Complex solutions that created problems

### Key Learnings
- Why the existing architecture exists
- How hex ID system reusability works
- Importance of minimal, surgical changes

## Apply Learnings to Future Issues

Use accumulated knowledge to:
- **Recognize similar patterns** in future issues
- **Avoid repeating mistakes** that caused test failures  
- **Default to proven approaches** that have worked before
- **Respect architectural boundaries** learned through testing

**Memory should compound - each successful fix should make future fixes better and more architecturally sound.**

---

# 🚨 Critical Entity Creation Issues

*Based on issue analysis and codebase investigation.*

## Known Entity Creation Failures

### Issue #11: WH69 Incomplete Entity Set
- **Symptom**: WH69 creates only 7 entities instead of expected 12
- **Status**: Device detected correctly, mapping exists, but entity creation incomplete
- **Root Cause**: Unknown - entity creation pipeline failure
- **Files to Investigate**: `coordinator.py:_process_live_data()`, `sensor.py:async_setup_entry()`

### WH77 "Multi-Sensor Station" Support Missing
- **Problem**: Device type "Multi-Sensor Station" not detected
- **Expected**: Should use hex ID system like WH69/WS90/WH90
- **Solution**: Add device type detection in sensor_mapper.py
- **Missing**: wh77batt battery mapping in const.py

### GW2000A Gateway Issues
- **Symptoms**: Unnamed sensors appearing as "Sensor 3", "Sensor 5" 
- **Problem**: Gateway-level sensor mapping or entity naming issues
- **Investigation**: Check gateway device creation and sensor naming logic

## Entity Creation Pipeline Debug Points

### 1. Hardware ID Mapping (sensor_mapper.py)
```python
# Check if hardware ID mapping is working:
hardware_id = self.sensor_mapper.get_hardware_id(sensor_key)
_LOGGER.debug("Hardware ID lookup for %s: %s", sensor_key, hardware_id)
```

### 2. Entity ID Generation (sensor_mapper.py:318-359)
```python
# Verify entity ID generation:
entity_id, friendly_name = self.sensor_mapper.generate_entity_id(sensor_key, hardware_id)
_LOGGER.debug("Generated entity: %s -> %s", sensor_key, entity_id)
```

### 3. Sensor Data Processing (coordinator.py:220-310)
```python
# Check sensor data inclusion:
if not sensor_value and not self._include_inactive:
    _LOGGER.debug("Skipping sensor %s (inactive)", sensor_key)
```

### 4. Entity Creation (sensor.py:77-88)
```python
# Verify entity creation:
for entity_id, sensor_info in sensor_data.items():
    category = sensor_info.get("category")
    if category in ("sensor", "battery", "system", "diagnostic"):
        _LOGGER.debug("Creating entity: %s (%s)", entity_id, category)
```

---

# 📋 Additional Patterns

## API and Data Handling Issues

### Pattern: Content-Type API Issues
- **Problem**: Gateway returns JSON data with wrong HTTP content-type header
- **Devices**: GW3000, GW1200B  
- **Solution**: Implement fallback JSON parsing in `api.py`
- **Files**: `custom_components/ecowitt_local/api.py` (`_make_request` method)
- **Fixed in**: v1.4.4

### Pattern: Embedded Unit Parsing
- **Problem**: Sensor values contain units in the string (e.g., "29.40 inHg")
- **Devices**: GW2000, WS90
- **Solution**: Regex parsing in coordinator's `_convert_sensor_value` method
- **Files**: `custom_components/ecowitt_local/coordinator.py`
- **Fixed in**: v1.4.6

## Service Parameter Handling Issues

### Pattern: Unhashable Type Errors
- **Problem**: `TypeError: unhashable type: 'list'` in service calls
- **Root Cause**: Home Assistant passes device_id as list instead of string
- **Solution**: Defensive type checking before using device_id
- **Files**: `custom_components/ecowitt_local/__init__.py` (service functions)
- **Code Pattern**:
```python
if isinstance(device_id, list):
    device_id = device_id[0] if device_id else None
device = device_registry.async_get(device_id) if device_id else None
```
- **Fixed in**: v1.4.9
---

# 🚀 Release Process

## Overview

This project uses automated GitHub Actions for releases. Claude Code bots work on `claude/**` branches, and the release process is handled via automation.

## Release Workflow

### 1. Development on Claude Branches
- All Claude Code work happens on branches matching `claude/**` pattern
- CI runs automatically on `claude/**` branches
- All tests must pass before merging

### 2. Automated Release Process

**When ready to release:**

1. **Create Release PR** (Automated via GitHub Actions)
   - Bot creates changes on `claude/release-*` branch
   - Updates `manifest.json` version
   - Updates `CHANGELOG.md` with release notes
   - Pushes to remote
   - GitHub Actions automatically creates PR to main

2. **PR Review and Merge** (Automated)
   - CI tests run on PR
   - Once tests pass, GitHub Actions auto-merges PR
   - Main branch updated with release

3. **Tag and Release** (Automated via `auto-release.yml`)
   - Triggers automatically when code merges to `main` branch
   - GitHub Actions creates annotated git tag (e.g., `v1.5.5`)
   - Pushes tag to GitHub: `git push origin v1.5.5`
   - Creates GitHub Release with CHANGELOG content
   - **CRITICAL**: Tag creation is REQUIRED for HACS integration
   - HACS automatically detects new release from git tags

## GitHub Actions Workflows

The release automation consists of three workflows:

### 1. `auto-pr.yml` - Automatic PR Creation
- **Trigger**: When CI completes on `claude/**` branches
- **Actions**:
  - Checks if version changed compared to main
  - Extracts CHANGELOG notes for the version
  - Creates PR to main branch with `release` label
  - Skips if version unchanged or PR already exists

### 2. `auto-merge.yml` - Automatic PR Merging
- **Trigger**: When PR is opened/updated on main branch
- **Conditions**: Only runs for `claude/**` branches with `release` label
- **Actions**:
  - Waits for all CI checks to pass
  - Automatically merges PR
  - Deletes source branch
- **Note**: Currently configured but can be manual

### Release notes in HACS / Home Assistant

HACS shows the **GitHub Release body** to users when an update is available. The auto-release workflow extracts that body from `CHANGELOG.md` using an awk state-machine that finds `## [VERSION]` and prints lines until the next `## [` header.

If a release ever shows the generic fallback ("This release includes updates and improvements...") instead of the actual changelog entries, it means the awk extraction silently returned empty. Fix the workflow's awk script — do **not** edit the GitHub release body manually, because HACS caches it and the next release will regress.

The original range-expression form (`/start/,/end/`) was buggy: because the start line `## [VERSION]` also matches the end pattern `^## \[`, the range activated and deactivated on the same line and nothing got printed. The state-machine form in `auto-release.yml` is the correct shape — keep it.

### 3. `auto-release.yml` - Git Tag & GitHub Release Creation
- **Trigger**: Push to `main` branch (after merge)
- **Actions**:
  1. Extracts version from `manifest.json`
  2. Checks if tag already exists (prevents duplicates)
  3. Creates annotated git tag: `git tag -a "v$VERSION"`
  4. Pushes tag to GitHub: `git push origin "v$VERSION"`
  5. Creates GitHub Release with CHANGELOG content
  6. **Result**: HACS detects new version and notifies users

**CRITICAL**: The tag creation in step 3 is what makes HACS work. Without the tag, HACS cannot detect the release.

## Branch Naming

**CRITICAL**: The branch name must always match the version being released.

```
claude/release-v1.6.8   ← branch name
"version": "1.6.8"      ← manifest.json version
## [1.6.8] - ...        ← CHANGELOG entry
```

Never reuse an old branch name for a new release. If you are releasing v1.6.9, the branch must be `claude/release-v1.6.9` even if the previous work was on `claude/release-v1.6.8`.

## Version Bump Checklist

When changing the version in `manifest.json`, **always** also update:

1. `custom_components/ecowitt_local/manifest.json` — the version number
2. `CHANGELOG.md` — new section with release notes
3. `hacs.json` → `homeassistant` field — only if minimum HA version requirements changed
4. `README.md` → HA version badge — only if `hacs.json` homeassistant version changed

## Version Numbering

Follow Semantic Versioning (SemVer):
- **Major** (1.x.x): Breaking changes
- **Minor** (x.1.x): New features, backward compatible
- **Patch** (x.x.1): Bug fixes, backward compatible

### Planned: v1.7.0 after V1.0.6 spec-audit issues land

Once the V1.0.6 spec-audit bugs (#158–#174) are fixed, **bump the next release to v1.7.0** (minor), not another patch in the v1.6.x line. Rationale:
- Several of those changes add new entities (Wind Chill, Heat Index, VPD, WH54 LDS, AQI fields, etc.) — that's new functionality, which calls for a minor bump.
- A few correct existing entity values (battery percentages, AQI/concentration unit fix). Those are fixes, but bundled with the new-feature changes the cumulative impact is meaningfully larger than a typical patch.
- A minor bump gives the release notes a clean header for the README/changelog audit pass.

Save v2.0.0 for an actual breaking change (e.g. removing a long-deprecated entity, restructuring config flow). Don't burn the major bump on a spec-coverage cleanup.

Don't bump to v1.7.0 mid-stream — wait until enough of the spec-audit bugs are landed that the cumulative change warrants the minor-version signal.

### Batch size: max 5–7 issues per agent run

When fixing the spec-audit backlog (#158–#174) or any large issue batch, **do not attempt more than 5–7 issues in a single agent session**. Reasons:
- Each fix needs CHANGELOG entry, version bump, branch creation, CI wait, PR merge — context grows fast.
- Overnight runs that try to power through 10+ issues consistently degrade in quality late in the run: shortcuts on tests, skimped CHANGELOG entries, missed cross-cutting checks.
- A failed CI on issue #11 of a 15-issue batch wastes the entire run; smaller batches fail more recoverably.

Pick 5–7 thematically related issues per run (e.g. "all common_list hex-ID drops" or "all name-string fallbacks"), land them as one minor release, then start a fresh session for the next batch.

## CHANGELOG Format

Use [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [1.5.5] - 2025-11-13

### Fixed
- Description of fix

### Added
- Description of new feature

### Changed
- Description of change

### Deprecated
- Description of deprecation
```

## Manual Release Process (Fallback)

If GitHub Actions are unavailable:

```bash
# 1. Update version in manifest.json
# Edit: custom_components/ecowitt_local/manifest.json
"version": "1.5.5"

# 2. Update CHANGELOG.md with release notes

# 3. Commit and push to claude branch
git add custom_components/ecowitt_local/manifest.json CHANGELOG.md
git commit -m "Release v1.5.5 - <description>"
git push origin claude/release-v1.5.5

# 4. Wait for CI to pass

# 5. Merge to main (requires permissions)
git checkout main
git merge claude/release-v1.5.5 --no-ff
git push origin main

# 6. Create and push tag
git tag -a v1.5.5 -m "Release v1.5.5"
git push origin v1.5.5

# 7. Create GitHub Release
gh release create v1.5.5 \
  --title "v1.5.5 - <title>" \
  --notes-file CHANGELOG.md \
  --latest
```

## Release Checklist

- [ ] All CI tests passing
- [ ] Version bumped in `manifest.json`
- [ ] CHANGELOG.md updated with release notes
- [ ] Breaking changes documented if any
- [ ] GitHub Release created with tag
- [ ] HACS validation passing

## HACS Integration

**CRITICAL**: HACS (Home Assistant Community Store) detects new versions via **git tags** on GitHub.

### How HACS Release Detection Works

1. **Git Tag Required**: HACS monitors GitHub repository for new tags matching `vX.Y.Z` format
   - Example: `v1.5.7` at https://github.com/alexlenk/ecowitt_local/tree/refs/tags/v1.5.7
   - Tags are created automatically by `auto-release.yml` workflow
   - Without tags, HACS cannot detect new releases

2. **Tag Format**: Must follow semantic versioning with `v` prefix
   - ✅ Correct: `v1.5.7`, `v2.0.0`, `v1.4.8`
   - ❌ Incorrect: `1.5.7`, `version-1.5.7`, `release-1.5.7`

3. **Automated Tagging**: The `auto-release.yml` workflow handles this automatically:
   ```yaml
   # Creates annotated tag
   git tag -a "v$VERSION" -m "Release v$VERSION"
   # Pushes to GitHub
   git push origin "v$VERSION"
   ```

4. **GitHub Release**: Created alongside the tag with CHANGELOG content
   - Provides human-readable release notes
   - Links to the git tag
   - HACS users see these notes when updating

### Verification

After a release, verify HACS integration:
```bash
# Check tags exist
git tag -l | grep v1.5.7

# View tag details
git show v1.5.7 --no-patch

# Verify tag is pushed to GitHub
# Visit: https://github.com/alexlenk/ecowitt_local/tags
```

### Requirements for HACS
- Git tags follow `vX.Y.Z` format (automated by workflow)
- GitHub Release created (not just a tag) - automated by workflow
- `hacs.json` is valid - validated by HACS Action in CI
- Version in `manifest.json` matches tag - enforced by automation

## Home Assistant Compatibility

When Home Assistant introduces breaking changes:
- Document in CHANGELOG under `### Fixed` or `### Changed`
- Update `homeassistant` minimum version in `hacs.json` if needed
- Test against latest HA version before release

## Common Release Issues

### services.yaml Validation Errors
- Run `hassfest` validation in CI before release
- Home Assistant breaking changes may require service definition updates
- Example: HA 2025.11 removed device filters from target selectors

### CI Failures
- All tests must pass before merging to main
- Fix test failures on claude branch before creating release PR
- Revert problematic changes if needed

### Version Conflicts
- Always increment version number
- Never reuse version numbers
- Check existing tags: `git tag -l`
