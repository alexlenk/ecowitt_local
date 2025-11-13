# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Ecowitt weather stations that uses local web interface polling instead of webhooks. The integration creates stable entity IDs based on hardware IDs and organizes sensors into individual devices for better management.

## ⚠️ CRITICAL: Entity Creation Pipeline Issues

**IMPORTANT**: This codebase has ongoing entity creation failures despite proper device detection. The primary issues are incomplete entity sets and mapping pipeline failures, not architectural violations. Focus on debugging the entity creation flow rather than mapping logic.

## Development Commands

### Testing
```bash
# Run all tests with coverage
PYTHONPATH="$PWD" python -m pytest tests/ -v

# Run specific test files
PYTHONPATH="$PWD" python -m pytest tests/test_sensor.py -v
PYTHONPATH="$PWD" python -m pytest tests/test_config_flow.py -v
PYTHONPATH="$PWD" python -m pytest tests/test_init.py -v

# Run tests with coverage report
PYTHONPATH="$PWD" python -m pytest tests/ --cov=custom_components/ecowitt_local --cov-report=term-missing
```

### Code Quality
```bash
# Type checking
mypy custom_components/ecowitt_local/

# Linting
flake8 custom_components/ecowitt_local/

# Code formatting
black custom_components/ecowitt_local/
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

Test coverage is maintained at 89% with 96+ automated tests covering device discovery, entity creation, hardware ID mapping, and edge cases.

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

# 🏗️ Actual Architecture (Evidence-Based)

## How Hex ID System Really Works

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
- Full test suite (225+ tests)
- Coverage reporting (must maintain >89%)  
- Multiple Python versions (3.11, 3.12)
- Code quality checks

**If CI fails, the implementation is WRONG and must be fixed.**

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

## Device Addition Checklist (Evidence-Based)

### For New Hex ID Devices (WH77, etc.)
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

3. **Tag and Release** (Automated)
   - GitHub Actions creates git tag (e.g., `v1.5.5`)
   - Creates GitHub Release with CHANGELOG content
   - HACS automatically detects new release

## Version Numbering

Follow Semantic Versioning (SemVer):
- **Major** (1.x.x): Breaking changes
- **Minor** (x.1.x): New features, backward compatible
- **Patch** (x.x.1): Bug fixes, backward compatible

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

HACS automatically detects new releases from GitHub releases. Ensure:
- Git tags follow `vX.Y.Z` format
- GitHub Release is created (not just a tag)
- `hacs.json` is valid
- Version in `manifest.json` matches tag

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
