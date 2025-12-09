# Architectural Patterns for Ecowitt Local Integration

## Device Support Patterns

### Pattern: Device Type String Mismatch
**Problem**: New weather stations report device type strings that don't match expected patterns
**Example**: WH90 reports as `"Temp & Humidity & Solar & Wind & Rain"` instead of `"wh90"`
**Solution**: Add device type string matching to `sensor_mapper.py`
**Implementation**: Extend existing `elif` conditions with `or "actual device string" in sensor_type.lower()`

### Pattern: Hex ID System Usage
**Description**: For complex weather stations (WH69, WS90, WH90, WH77), use hex ID mapping system
**Location**: `sensor_mapper.py` lines 184-247 for device-specific hex ID lists
**Metadata**: `const.py` lines 287-372 for hex ID sensor definitions
**Key Principle**: Reuse existing hex ID definitions, never duplicate metadata

### Pattern: Battery Mapping
**Location**: `const.py` BATTERY_SENSORS section (lines 451-493)
**Format**: `"devicebatt": {"name": "Device Battery", "sensor_key": "primary_sensor_key"}`
**Linking**: Battery sensors link to primary sensor key for device association

## Entity Creation Architecture

### Hardware ID Strategy
- Entity IDs are based on hardware IDs: `sensor.ecowitt_sensor_type_hardwareid`
- Hardware IDs extracted from gateway's sensor mapping ensure stability
- Migration system handles updates and reassigns entities to correct devices

### Device Organization
- Individual devices for each physical sensor (not grouped under gateway)
- Each device contains primary + diagnostic entities (battery, signal, online status)
- Device registry setup happens before platform setup in `__init__.py:40`

### Two-Part Hex ID Architecture
1. **sensor_mapper.py**: Device-specific hex ID mapping lists (required for entity creation)
2. **const.py**: Hex ID sensor metadata (shared across all hex ID devices)

## Implementation Philosophy

**"Extend existing patterns rather than creating new ones"**

### Successful Pattern: Single-Line Device Type Fixes
```python
# WH90 success example - single line addition:
elif sensor_type.lower() in ("wh90", "weather_station_wh90") or "temp & humidity & solar & wind & rain" in sensor_type.lower():
```

### Anti-Patterns to Avoid
- ❌ Duplicating hex ID metadata definitions in const.py
- ❌ Creating device-specific sensor mappings when hex ID system exists
- ❌ Modifying existing device type conditions
- ❌ Large multi-file changes for simple device support

## Error Handling Patterns

### API Resilience
- Authentication errors trigger re-authentication
- API failures logged but don't crash integration
- Content-Type fallback JSON parsing for misbehaving gateways

### Service Parameter Safety
```python
# Defensive programming for Home Assistant parameter handling
if isinstance(device_id, list):
    device_id = device_id[0] if device_id else None
```

## Testing Requirements

### Mandatory CI Monitoring
- All changes must pass complete CI suite (225+ tests)
- Maintain >89% test coverage
- Support multiple Python versions (3.11, 3.12)
- Monitor CI on `claude/**` branches and fix failures before merging

### Architecture Validation
- Test device detection without modifying existing patterns
- Validate hex ID reuse (no new definitions)
- Verify entity naming consistency
- Check for regressions in existing device functionality