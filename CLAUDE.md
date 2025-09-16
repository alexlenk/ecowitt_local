# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Ecowitt weather stations that uses local web interface polling instead of webhooks. The integration creates stable entity IDs based on hardware IDs and organizes sensors into individual devices for better management.

## ⚠️ CRITICAL: Read Anti-Patterns Section Before Making Changes

**IMPORTANT**: This codebase has a specific architecture for handling hex ID sensors. Creating duplicate hex ID definitions is the #1 mistake. Always check the Anti-Patterns section below before implementing device support.

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

### Pattern: Hex ID Sensor Mapping
- **Problem**: Weather stations using hex IDs (0x02, 0x07, etc.) not creating entities
- **Devices**: WH69, WS90, WH90, and similar multi-sensor stations
- **Solution**: Ensure device type detection uses existing hex ID system
- **Architecture**: All hex ID devices share the same sensor definitions in `const.py` (lines 276-350)
- **Key Principle**: **Reuse existing hex ID system - never duplicate definitions**

---

# ❌ Anti-Patterns (CRITICAL - DO NOT DO)

*These approaches have been tried and cause problems. Avoid them at all costs.*

## DO NOT: Create Duplicate Hex ID Definitions
- ❌ **Wrong**: Adding device-specific hex ID mappings like:
  ```python
  keys.extend([
      "0x02",  # Temperature
      "0x07",  # Humidity
      ...
  ])
  ```
- ✅ **Correct**: Device should fall through to use existing common_list hex ID handling
- **Why**: Causes conflicts, breaks existing devices, violates architecture

## DO NOT: Device-Specific Sensor Lists
- ❌ **Wrong**: Creating WH90-specific, WH69-specific sensor definitions
- ✅ **Correct**: Add only device type detection, reuse existing hex ID system
- **Why**: Maintenance nightmare, naming inconsistency, architectural violation

## DO NOT: Break Existing Device Compatibility
- ❌ **Wrong**: Modifying existing WH69/WS90 conditions to "fix" new devices
- ✅ **Correct**: Extend patterns without changing existing ones
- **Why**: Regression in working devices is unacceptable

---

# 🏗️ Architecture Principles

## Hex ID System Architecture

The hex ID system is designed with **reusability** as the core principle:

1. **Single source of truth**: All hex IDs (0x02, 0x07, etc.) are defined ONCE in `const.py` (lines 276-350)
2. **Shared definitions**: WH69, WS90, WH90, and similar devices all use the SAME hex ID mappings
3. **Device type detection**: Only add device type string matching in `sensor_mapper.py`
4. **Automatic handling**: Once device type is detected, hex IDs in common_list are automatically processed

### How It Works:
```python
# In sensor_mapper.py - CORRECT approach for new hex ID device:
elif sensor_type.lower() in ("wh90", "weather_station_wh90") or "temp & humidity & solar & wind & rain" in sensor_type.lower():
    # Device uses hex IDs - no need to list them, they're handled automatically
    pass  # Falls through to common_list processing
```

## Minimal, Surgical Changes

- **Prefer single-line additions** over large modifications
- **Test compatibility** with existing devices
- **Validate against architecture** before implementing

---

# 🏆 Success Patterns

## Example: WH90 Support (v1.4.8)

**Problem**: WH90 not creating entities  
**Root Cause**: Device type string mismatch  
**Solution**: Single line addition to sensor_mapper.py

```python
# BEFORE: WH90 not detected
elif sensor_type.lower() in ("wh69", "weather_station_wh69"):
    # WH69 handling
    
# AFTER: WH90 works perfectly (ONE LINE ADDED)
elif sensor_type.lower() in ("wh90", "weather_station_wh90") or "temp & humidity & solar & wind & rain" in sensor_type.lower():
    # WH90 now detected, uses same hex ID system as WH69
```

**Key**: Added detection without duplicating any hex ID definitions

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

### Learning from Test Failures

Common test failure patterns and their meanings:

- **Duplicate entity errors**: Usually indicates hex ID duplication (follow anti-patterns)
- **Entity naming inconsistencies**: Indicates architectural violation
- **Coverage drops**: Missing test coverage for new code paths
- **Regression failures**: Changes broke existing device functionality

**Update implementation based on test feedback - tests reveal architectural violations.**

## Before Any Device Support Changes

1. **Understand the architecture**: Read the Anti-Patterns section
2. **Check existing patterns**: See how WH69/WS90 work  
3. **Plan minimal changes**: Single line additions preferred
4. **Commit and monitor**: Wait for CI results and fix any failures

## Device Addition Checklist
- [ ] Device type string added to `sensor_mapper.py` ONLY
- [ ] NO new hex ID definitions created
- [ ] Uses existing hex ID system from const.py
- [ ] Battery mapping added if needed (device-specific key only)
- [ ] **CI passes completely** (all tests, all Python versions)
- [ ] No regressions in existing devices
- [ ] Implementation follows minimal approach

---

# Implementation Philosophy

**"Extend existing patterns rather than creating new ones"**

When adding device support:
1. ✅ Add device type detection (1-2 lines maximum)
2. ✅ Reuse existing hex ID system entirely
3. ❌ Never create device-specific hex ID lists
4. ❌ Never duplicate existing definitions

**When in doubt**: Look at WH69/WS90 implementation and follow that EXACT pattern.

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