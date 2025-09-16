# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Ecowitt weather stations that uses local web interface polling instead of webhooks. The integration creates stable entity IDs based on hardware IDs and organizes sensors into individual devices for better management.

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

# 🎯 **Issue Analysis Patterns & Solutions**

*The following patterns were learned through extensive issue analysis and bot development. These guide how to approach common problems in this integration.*

## Common Device Mapping Issues

### **Pattern: Device Type String Mismatch** 
- **Problem**: New weather stations report device type strings that don't match expected patterns
- **Example**: WH90 reports as `"Temp & Humidity & Solar & Wind & Rain"` instead of `"wh90"`
- **Solution**: Add device type string matching to `sensor_mapper.py` 
- **Files**: `custom_components/ecowitt_local/sensor_mapper.py`
- **Approach**: Extend existing `elif` conditions with `or "actual device string" in sensor_type.lower()`
- **Fixed in**: v1.4.8 (WH90 support)

### **Pattern: Hex ID Sensor Mapping**
- **Problem**: Weather stations using hex IDs (0x02, 0x07, etc.) not creating entities
- **Devices**: WH69, WS90, WH90, WH25
- **Solution**: Ensure device type detection uses existing hex ID system
- **Architecture**: All hex ID devices share the same sensor definitions in `const.py` (lines 276-350)
- **Key Principle**: **Reuse existing hex ID system - never duplicate definitions**

### **Pattern: Content-Type API Issues**
- **Problem**: Gateway returns JSON data with wrong HTTP content-type header
- **Devices**: GW3000, GW1200B  
- **Solution**: Implement fallback JSON parsing in `api.py`
- **Files**: `custom_components/ecowitt_local/api.py` (`_make_request` method)
- **Fixed in**: v1.4.4

### **Pattern: Embedded Unit Parsing**
- **Problem**: Sensor values contain units in the string (e.g., "29.40 inHg")
- **Devices**: GW2000, WS90
- **Solution**: Regex parsing in coordinator's `_convert_sensor_value` method
- **Files**: `custom_components/ecowitt_local/coordinator.py`
- **Fixed in**: v1.4.6

## Service Parameter Handling Issues

### **Pattern: Unhashable Type Errors**
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

# ❌ **Anti-Patterns (Critical - DO NOT DO)**

*These approaches have been tried and cause problems. Avoid them at all costs.*

## **DO NOT: Create Duplicate Hex ID Definitions**
- ❌ **Wrong**: Adding device-specific hex ID mappings to `const.py`
- ❌ **Wrong**: Creating separate `"0x02"` definitions for different devices  
- ✅ **Correct**: Use existing shared hex ID system (lines 276-350 in `const.py`)
- **Why**: Causes conflicts, breaks existing devices, violates architecture

## **DO NOT: Device-Specific Sensor Definitions**
- ❌ **Wrong**: Creating WH90-specific, WH69-specific sensor definitions
- ✅ **Correct**: Use shared sensor definitions, extend device type matching
- **Why**: Maintenance nightmare, naming inconsistency, architectural violation

## **DO NOT: Break Existing Device Compatibility**
- ❌ **Wrong**: Modifying existing WH69/WS90 mappings to "fix" WH90
- ✅ **Correct**: Extend patterns without changing existing ones
- **Why**: Regression in working devices is unacceptable

## **DO NOT: Inconsistent Entity Naming**
- ❌ **Wrong**: WH69 "Outdoor Temperature" vs WH90 "Temperature"  
- ✅ **Correct**: Use consistent naming from shared definitions
- **Why**: Confuses users, breaks entity recognition patterns

---

# 🏗️ **Architecture Principles**

## **Follow Existing Patterns**
When adding support for new devices, always:

1. **Study existing implementations** (WH69, WS90, WH68 patterns)
2. **Reuse existing systems** (hex ID mapping, battery definitions)
3. **Extend, don't replace** (add conditions, don't modify existing ones)
4. **Maintain consistency** (naming, structure, organization)

## **Hex ID System Architecture**
- **Single source of truth**: All hex IDs defined once in `const.py` (lines 276-350)
- **Shared definitions**: WH69, WS90, WH90 use same hex ID mappings
- **Device type detection**: Add new device type strings to `sensor_mapper.py`
- **Battery mapping**: Add device-specific battery keys (e.g., `"wh90batt"`)

## **Minimal, Surgical Changes**
- **Prefer single-line additions** over large modifications
- **Test compatibility** with existing devices
- **Validate against architecture** before implementing

## **Error Handling Patterns**
- **Defensive programming**: Always check parameter types
- **Graceful degradation**: Log errors but continue operation  
- **Type safety**: Handle both expected and unexpected parameter formats

---

# 🧪 **Testing & Validation Requirements**

## **Before Any Code Changes**
1. **Run full test suite**: `PYTHONPATH="$PWD" python -m pytest tests/ -v`
2. **Check coverage**: Maintain >89% coverage
3. **Validate architecture**: Ensure changes follow existing patterns

## **Device Addition Checklist**
- [ ] Device type string added to `sensor_mapper.py`
- [ ] Uses existing hex ID system (no new hex definitions)
- [ ] Battery mapping added if needed
- [ ] Maintains naming consistency
- [ ] All tests pass
- [ ] No regressions in existing devices

## **Service Changes**
- [ ] Handle both string and list parameters
- [ ] Defensive type checking implemented
- [ ] Service tests updated and passing
- [ ] Error scenarios covered

---

# 🏆 **Success Patterns**

## **Recent Successful Fixes**

### **WH90 Support (v1.4.8)**
- **Approach**: Added device type string matching
- **Code Change**: Single line addition to existing `elif` condition
- **Files Modified**: `sensor_mapper.py` (1 line changed)
- **Architecture**: Reused entire existing hex ID system
- **Result**: WH90 creates all expected entities without affecting WH69/WS90

### **Service Robustness (v1.4.9)**  
- **Approach**: Defensive parameter type checking
- **Code Changes**: Added type validation before device registry calls
- **Files Modified**: `__init__.py` service functions
- **Architecture**: Backward compatible parameter handling
- **Result**: Services work with both string and list device_id formats

## **Implementation Philosophy**

**"Extend existing patterns rather than creating new ones"**

This integration has a proven, stable architecture. New device support should:
- ✅ Follow established patterns
- ✅ Reuse existing systems  
- ✅ Maintain backward compatibility
- ✅ Require minimal code changes
- ✅ Pass all existing tests

**When in doubt, study how WH69/WS90 work and follow that exact pattern.**