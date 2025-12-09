# Issue Resolution Patterns for Ecowitt Local Integration

## Known Issue Patterns and Solutions

### Issue Pattern 1: Device Type String Mismatch

**Symptoms**:
- Device detected but creates zero entities
- Device appears in Home Assistant with correct name
- No sensors appear in entity list

**Root Cause**: Device reports type string that doesn't match expected identifier
- Example: WH90 reports "Temp & Humidity & Solar & Wind & Rain" instead of "wh90"
- Example: WH77 reports "Multi-Sensor Station" instead of "wh77"

**Solution**:
Add device type string matching to `sensor_mapper.py`:
```python
elif sensor_type.lower() in ("deviceid", "weather_station_deviceid") or "actual device string" in sensor_type.lower():
```

**Evidence**: Fixed in v1.4.8 for WH90 (commit 15ec621)
**Files**: `custom_components/ecowitt_local/sensor_mapper.py`

---

### Issue Pattern 2: Incomplete Entity Creation

**Symptoms**:
- Device detected correctly
- Some entities created but not all expected ones
- Example: WH69 creates 7 entities instead of 12

**Root Cause**: Entity creation pipeline failure in coordinator or sensor setup
**NOT the problem**: Device type detection (usually works correctly)

**Investigation Areas**:
1. Hardware ID mapping in `sensor_mapper.py`
2. Entity ID generation in `sensor_mapper.py:318-359`
3. Sensor data processing in `coordinator.py:220-310`
4. Entity creation in `sensor.py:77-88`

**Debug Points**:
```python
# Check hardware ID mapping
hardware_id = self.sensor_mapper.get_hardware_id(sensor_key)
_LOGGER.debug("Hardware ID lookup for %s: %s", sensor_key, hardware_id)

# Verify entity ID generation
entity_id, friendly_name = self.sensor_mapper.generate_entity_id(sensor_key, hardware_id)
_LOGGER.debug("Generated entity: %s -> %s", sensor_key, entity_id)

# Check sensor data inclusion
if not sensor_value and not self._include_inactive:
    _LOGGER.debug("Skipping sensor %s (inactive)", sensor_key)
```

**Status**: Known issue requiring pipeline debugging, not device detection fixes

---

### Issue Pattern 3: Content-Type API Problems

**Symptoms**:
- Gateway communication fails
- JSON parsing errors
- HTTP content-type header mismatches

**Root Cause**: Gateway returns JSON with wrong content-type header
**Affected Devices**: GW3000, GW1200B

**Solution**: Implement fallback JSON parsing in `api.py`
```python
# In _make_request method
try:
    return await response.json()
except ContentTypeError:
    # Fallback for gateways with incorrect content-type
    text = await response.text()
    return json.loads(text)
```

**Evidence**: Fixed in v1.4.4
**Files**: `custom_components/ecowitt_local/api.py`

---

### Issue Pattern 4: Embedded Unit Parsing

**Symptoms**:
- Sensor values include units in string format
- Example: "29.40 inHg" instead of just "29.40"
- Type conversion errors or incorrect values

**Root Cause**: Gateway includes units in value strings
**Affected Devices**: GW2000, WS90

**Solution**: Regex parsing in `coordinator.py`
```python
def _convert_sensor_value(self, value: str) -> float:
    """Extract numeric value from string with embedded units."""
    # Regex to extract number from "29.40 inHg"
    match = re.search(r'(-?\d+\.?\d*)', value)
    return float(match.group(1)) if match else 0.0
```

**Evidence**: Fixed in v1.4.6
**Files**: `custom_components/ecowitt_local/coordinator.py`

---

### Issue Pattern 5: Service Parameter Type Errors

**Symptoms**:
- `TypeError: unhashable type: 'list'` in service calls
- Service call crashes when device_id parameter provided
- Home Assistant automation failures

**Root Cause**: Home Assistant passes device_id as list instead of string
**Affected Services**: refresh_mapping, update_data

**Solution**: Defensive type checking in service handlers
```python
# In __init__.py service functions
if isinstance(device_id, list):
    device_id = device_id[0] if device_id else None
device = device_registry.async_get(device_id) if device_id else None
```

**Evidence**: Fixed in v1.4.9
**Files**: `custom_components/ecowitt_local/__init__.py`

---

### Issue Pattern 6: Home Assistant Breaking Changes

**Symptoms**:
- hassfest validation errors in CI
- Service definition errors after HA updates
- Integration fails to load after HA upgrade

**Example**: HA 2025.11 removed device filters from target selectors

**Solution**: Update `services.yaml` to match new HA requirements
```yaml
# BEFORE (deprecated):
target:
  device:
    filter:
      integration: ecowitt_local

# AFTER (HA 2025.11+):
target:
  device:
    integration: ecowitt_local
```

**Evidence**: Fixed in v1.5.5
**Files**: `custom_components/ecowitt_local/services.yaml`

---

## Resolution Workflow

### Step 1: Pattern Recognition
- Identify which issue pattern matches the reported problem
- Check if similar issues were previously solved
- Reference CLAUDE.md for known patterns

### Step 2: Minimal Implementation
- Use single-line changes when possible
- Extend existing patterns rather than creating new ones
- Follow successful examples (e.g., WH90 fix)

### Step 3: Testing and Validation
- Run full test suite (`pytest tests/ -v`)
- Verify no regressions in existing functionality
- Check CI passes on `claude/**` branch
- Test against real device data if available

### Step 4: Release and User Validation
- Update version in `manifest.json`
- Add CHANGELOG entry with clear description
- Create release and push to main
- Comment on issue requesting user testing
- **DO NOT close issue** until user confirms fix

### Step 5: Learning and Documentation
- Document successful pattern in CLAUDE.md
- Update Kiro steering files if new pattern discovered
- Share knowledge for future similar issues

---

## Quick Reference: File Locations

### Device Support
- Device type detection: `sensor_mapper.py:89-316`
- Hex ID mapping: `sensor_mapper.py:184-247`
- Hex ID metadata: `const.py:287-372`
- Battery mapping: `const.py:451-493`

### Entity Creation
- Hardware ID mapping: `sensor_mapper.py:318-327`
- Entity ID generation: `sensor_mapper.py:340-381`
- Data processing: `coordinator.py:220-310`
- Entity setup: `sensor.py:77-88`

### API and Services
- API client: `api.py`
- Service handlers: `__init__.py`
- Service definitions: `services.yaml`

### Configuration
- Config flow: `config_flow.py`
- Integration setup: `__init__.py:23-100`
- Constants: `const.py`