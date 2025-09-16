# 🤖 **Official Claude Code Bot Test Plan**

## **Overview**

This document defines the comprehensive testing strategy for validating the official Claude Code GitHub Actions implementation. The test validates that the bot can handle real-world device support requests following our documented patterns and architecture.

---

## **🎯 Test Scenario: WH77 Multi-Sensor Station Support**

### **Test Description**
Simulate a realistic user request for adding support for a fictional "WH77 Multi-Sensor Station" that exhibits the same patterns as our successfully resolved WH90 issue (device type string mismatch).

### **Why WH77 Test is Perfect**
- **Realistic**: Based on actual WH90 pattern we've solved
- **Safe**: Fictional device won't impact real users
- **Comprehensive**: Tests all our learned patterns
- **Measurable**: Clear pass/fail criteria
- **Repeatable**: Can be run multiple times

---

## **📋 Test Setup Requirements**

### **Test Fixtures** 
Create realistic test data in `tests/fixtures/test_wh77.py`:

```python
"""Test fixtures for WH77 Multi-Sensor Station testing."""

WH77_SENSOR_MAPPING = {
    "id": "C234", 
    "img": "wh77",
    "name": "Multi-Sensor Station",  # Key: Different from device img
    "type": "52",
    "batt": "3", 
    "signal": "-65"
}

WH77_LIVE_DATA = {
    "common_list": [
        {"id": "C234", "val": "23.5", "ch": "0x02"},  # Temperature
        {"id": "C234", "val": "65", "ch": "0x07"},    # Humidity
        {"id": "C234", "val": "12.5", "ch": "0x0B"},  # Wind Speed
        {"id": "C234", "val": "8.2", "ch": "0x0C"},   # Wind Gust
        {"id": "C234", "val": "180", "ch": "0x0A"},   # Wind Direction
        {"id": "C234", "val": "450", "ch": "0x15"},   # Solar Radiation
        {"id": "C234", "val": "5", "ch": "0x17"},     # UV Index
    ]
}

WH77_BATTERY_MAPPING = {
    "wh77batt": {
        "name": "WH77 Multi-Sensor Station Battery",
        "sensor_key": "0x02"
    }
}
```

### **Validation Test Case**
Create test in `tests/test_wh77_support.py`:

```python
"""Test case for WH77 Multi-Sensor Station support."""

def test_wh77_sensor_mapping():
    """Test that WH77 follows the correct architectural pattern."""
    # Test that device type "Multi-Sensor Station" maps to hex IDs
    # Test that existing hex ID definitions are reused
    # Test that no duplicate definitions are created
    pass

def test_wh77_entities_created():
    """Test that WH77 creates expected entities.""" 
    # Test temperature, humidity, wind, solar, UV, battery entities
    # Test consistent entity naming with existing devices
    pass
```

---

## **🎯 GitHub Issue Template**

### **Issue Title**: `WH77 Multi-Sensor Station not creating entities`

### **Issue Body**:
```markdown
## WH77 Multi-Sensor Station Not Creating Entities

**Hardware Setup:**
- Gateway: GW2000A  
- Sensor: WH77 Multi-Sensor Station
- Hardware ID: C234
- Firmware: Latest

**Problem:**
The WH77 sensor is detected by the integration and shows as a device, but **creates zero entities**. The device appears in Home Assistant as "Multi-Sensor Station" but has no temperature, humidity, wind, or battery sensors.

**Current Behavior:**
- ✅ Device detected (shows as "Multi-Sensor Station") 
- ❌ No entities created (0 entities)
- ❌ No sensors appear in entity list

**Expected Behavior:**
Should create entities for temperature, humidity, wind speed, wind direction, solar radiation, UV index, and battery status, similar to other weather stations like WH69 and WH90.

**Diagnostic Data:**

<details>
<summary>Sensor Mapping JSON</summary>

```json
{
  "id": "C234",
  "img": "wh77", 
  "name": "Multi-Sensor Station",
  "type": "52",
  "batt": "3",
  "signal": "-65"
}
```
</details>

<details>
<summary>Live Data JSON</summary>

```json
{
  "common_list": [
    {"id": "C234", "val": "23.5", "ch": "0x02"},
    {"id": "C234", "val": "65", "ch": "0x07"},
    {"id": "C234", "val": "12.5", "ch": "0x0B"},
    {"id": "C234", "val": "8.2", "ch": "0x0C"},
    {"id": "C234", "val": "180", "ch": "0x0A"},
    {"id": "C234", "val": "450", "ch": "0x15"},
    {"id": "C234", "val": "5", "ch": "0x17"}
  ]
}
```
</details>

**Version:** v1.4.9
**Home Assistant:** 2024.12.x

This looks very similar to the WH90 issue that was recently fixed. The device type string seems to be "Multi-Sensor Station" instead of "wh77".

@claude Can you help implement support for the WH77 Multi-Sensor Station?
```

---

## **✅ Acceptance Criteria**

### **Primary Success Criteria**

#### **1. Pattern Recognition** ✅
- [ ] Bot identifies this as device type string mismatch pattern
- [ ] Bot references similar WH90 fix (v1.4.8) 
- [ ] Bot understands root cause is sensor_mapper.py device type detection

#### **2. Architectural Compliance** ✅  
- [ ] Bot proposes single-line addition to `sensor_mapper.py`
- [ ] Bot extends existing `elif` condition (doesn't create new one)
- [ ] Bot reuses existing hex ID system entirely
- [ ] Bot mentions using existing battery mapping system

#### **3. Anti-Pattern Avoidance** ✅
- [ ] Bot does NOT propose creating new hex ID definitions in `const.py`
- [ ] Bot does NOT propose device-specific sensor mappings
- [ ] Bot does NOT modify existing WH69/WS90/WH90 conditions
- [ ] Bot does NOT create inconsistent entity naming

#### **4. Implementation Quality** ✅
- [ ] Proposed code change is minimal (1 line addition)
- [ ] Code follows exact pattern: `or "multi-sensor station" in sensor_type.lower()`
- [ ] Solution reuses existing hex ID definitions (lines 276-350 in const.py)
- [ ] Maintains consistent entity naming with other devices

#### **5. Testing & Validation** ✅
- [ ] Bot mentions running test suite requirement
- [ ] Bot verifies compatibility with existing devices  
- [ ] Bot ensures no regressions in WH69/WS90/WH90 functionality
- [ ] Bot validates against architectural principles

### **Code Quality Requirements**

#### **Expected Implementation**:
```python
# In custom_components/ecowitt_local/sensor_mapper.py
elif sensor_type.lower() in ("wh77", "weather_station_wh77") or "multi-sensor station" in sensor_type.lower():
    # WH77 Multi-Sensor Station (similar to WH69/WS90/WH90, uses hex IDs in common_list)
    keys.extend([
        "0x02",  # Temperature
        "0x03",  # Temperature (alternate)
        "0x07",  # Humidity
        "0x0B",  # Wind speed
        "0x0C",  # Wind gust
        "0x19",  # Max daily gust
        "0x0A",  # Wind direction
        "0x6D",  # Wind direction 10min avg
        "0x15",  # Solar radiation
        "0x17",  # UV index
        "wh77batt",  # Battery level
    ])
```

#### **Battery Mapping Addition** (if proposed):
```python
# In custom_components/ecowitt_local/const.py (battery sensors section)
"wh77batt": {
    "name": "WH77 Multi-Sensor Station Battery", 
    "sensor_key": "0x02"
},
```

### **Failure Criteria (Auto-Fail)**

#### **Immediate Failures** ❌
- Bot creates duplicate hex ID definitions (e.g., new "0x02" definition)
- Bot modifies existing device type conditions  
- Bot proposes device-specific const.py sensor definitions
- Bot suggests breaking changes to existing architecture
- Bot creates inconsistent entity naming patterns

#### **Architecture Violations** ❌ 
- Large multi-file changes instead of minimal addition
- New architecture patterns instead of extending existing ones
- Complex solutions when simple one-line fix is correct
- Testing requirements not mentioned or followed

---

## **🧪 Testing Procedure**

### **Phase 1: Pre-Test Setup**
1. Create `bot-development` branch from `main`
2. Add WH77 test fixtures to branch
3. Install official Claude Code GitHub Actions
4. Configure CLAUDE.md with our documented patterns
5. Verify all tests pass on clean branch

### **Phase 2: Bot Interaction**
1. Create GitHub issue with WH77 scenario
2. Tag `@claude` with clear request for support
3. Monitor bot analysis and proposed solution
4. Evaluate against acceptance criteria
5. Check for any immediate failure conditions

### **Phase 3: Code Review** 
1. Review generated PR against quality requirements
2. Validate architectural compliance
3. Run full test suite (`PYTHONPATH="$PWD" python -m pytest tests/ -v`)
4. Check for regressions in existing functionality
5. Verify entity naming consistency

### **Phase 4: Integration Testing**
1. Test with realistic WH77 data scenarios
2. Validate entity creation and naming
3. Check device organization and relationships
4. Verify battery status and diagnostic entities
5. Confirm no impact on existing devices

---

## **📊 Success Metrics**

### **Quantitative Metrics**
- **Code Quality**: Single-line change (±2 lines acceptable)
- **Test Coverage**: Maintain >89% coverage
- **Test Results**: All 218+ tests pass
- **Architecture**: Zero existing pattern modifications
- **Consistency**: 100% entity naming compliance

### **Qualitative Metrics**
- **Pattern Recognition**: Bot identifies correct issue pattern
- **Solution Quality**: Minimal, surgical fix proposed
- **Documentation**: Bot references our CLAUDE.md patterns
- **Communication**: Clear explanation of fix rationale
- **Safety**: Zero risk to existing device functionality

---

## **🔄 Iteration Strategy**

### **If Initial Test Fails**
1. **Analyze failure mode** against criteria
2. **Update CLAUDE.md** with additional guidance if needed
3. **Refine acceptance criteria** based on lessons learned
4. **Retry with improved documentation**
5. **Document learnings** for future iterations

### **If Test Succeeds**
1. **Merge WH77 support** to main after validation
2. **Document successful patterns** in CLAUDE.md
3. **Create additional test scenarios** for edge cases
4. **Enable bot for production** use on real issues
5. **Monitor performance** and refine as needed

---

## **🚀 Future Test Scenarios**

After WH77 succeeds, test these scenarios:

### **Test 2: Service Robustness** 
- Parameter handling edge cases
- Defensive programming patterns

### **Test 3: API Issues**
- Content-type mismatch scenarios  
- Gateway compatibility patterns

### **Test 4: Complex Multi-Pattern**
- Issues requiring multiple pattern applications
- Comprehensive architecture understanding

---

## **📋 Test Execution Checklist**

### **Pre-Execution**
- [ ] bot-development branch created
- [ ] WH77 test fixtures implemented  
- [ ] Official Claude Code installed and configured
- [ ] CLAUDE.md enhanced with all patterns
- [ ] Baseline tests passing

### **During Execution**
- [ ] GitHub issue created with WH77 scenario
- [ ] @claude tagged with clear request
- [ ] Bot response analyzed against acceptance criteria
- [ ] Code quality evaluated against requirements
- [ ] Failure criteria checked for violations

### **Post-Execution**  
- [ ] Generated code reviewed and tested
- [ ] Full test suite executed and passing
- [ ] Integration testing completed
- [ ] Results documented and analyzed
- [ ] Lessons learned captured for iteration

---

**This test plan ensures the official Claude Code will be as intelligent as our custom bot should have been, but actually working for reliable code generation.**