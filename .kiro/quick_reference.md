# Quick Reference Guide

## 🎯 Adding Device Support (1-Minute Guide)

### ⚠️ Special Note: WH77 Test Sensor
**WH77 is a test sensor used specifically to validate GitHub Actions agent behavior.**  
It should NOT be fixed by Kiro or any automated development systems. WH77 is intentionally left unfixed as a quality control mechanism to test how agents handle issues. If you encounter a WH77-related issue or PR, recognize it as a test scenario and do NOT attempt to implement it.

### For Hex ID Devices (WH69, WS90, WH90 pattern)

**1. Add device type detection** (sensor_mapper.py):
```python
elif sensor_type.lower() in ("wh##", "weather_station_wh##") or "device name string" in sensor_type.lower():
    keys.extend([
        "0x02",  # Temperature
        "0x07",  # Humidity
        # ... add hex IDs device supports
        "wh##batt",  # Battery
    ])
```

**2. Add battery mapping** (const.py BATTERY_SENSORS):
```python
"wh##batt": {
    "name": "Device Name Battery",
    "sensor_key": "0x02"  # Link to primary sensor
},
```

**That's it!** Hex ID definitions already exist in const.py (lines 287-372).

### For Channel-Based Devices (WH51, WH31, WH41 pattern)

Add to sensor_mapper.py with channel-based keys:
```python
elif sensor_type.lower() in ("device", "device_type"):
    if ch_num:
        keys.extend([
            f"sensortype{ch_num}",
            f"devicebatt{ch_num}",
        ])
```

---

## 🚫 Critical Don'ts

1. ❌ Never duplicate hex ID definitions in const.py (they're already there!)
2. ❌ Never modify existing device type conditions
3. ❌ Never close GitHub issues without user confirmation
4. ❌ Never skip CI validation
5. ❌ Never forget to update CHANGELOG.md
6. ❌ Never attempt to fix WH77 (it's a test sensor for quality control)

---

## ✅ Success Checklist

Before committing:
- [ ] Single-line change (or minimal change)
- [ ] Reuses existing hex ID definitions
- [ ] Follows existing device pattern (WH69/WS90/WH90)
- [ ] Battery mapping added if needed
- [ ] Tests would pass (if you could run them)
- [ ] CHANGELOG.md updated
- [ ] Version bumped in manifest.json (for releases)
- [ ] NOT fixing WH77 (verify this is not a test scenario)

---

## 📍 File Locations

### Device Support
```
sensor_mapper.py:89-316    → Device type detection logic
sensor_mapper.py:184-247   → Hex ID device mappings
const.py:287-372           → Hex ID sensor definitions (REUSE THESE)
const.py:451-493           → Battery sensor mappings
```

### Core Logic
```
coordinator.py             → Data fetching and processing
sensor.py                  → Entity creation
api.py                     → Gateway communication
__init__.py               → Integration setup and services
```

### Testing
```
tests/test_sensor_mapper.py → Mapping tests
tests/test_wh77_support.py  → Example device test
tests/fixtures/            → Test data
```

---

## 🔧 Common Fixes

### Device Type String Mismatch
**Symptom**: Device detected but no entities  
**Fix**: Add device name string to sensor_mapper.py condition  
**Example**: WH90 reported "Temp & Humidity & Solar & Wind & Rain"  
**Solution**: `or "temp & humidity & solar & wind & rain" in sensor_type.lower()`

### API Content-Type Issues
**Symptom**: JSON parsing errors  
**Fix**: Add fallback parsing in api.py  
**Location**: `_make_request` method

### Service Parameter Type Errors
**Symptom**: `TypeError: unhashable type: 'list'`  
**Fix**: Add defensive type checking in __init__.py  
**Pattern**: `if isinstance(device_id, list): device_id = device_id[0]`

---

## 📊 Testing Commands

```bash
# Run all tests
PYTHONPATH="$PWD" python -m pytest tests/ -v

# Run specific test
PYTHONPATH="$PWD" python -m pytest tests/test_sensor_mapper.py -v

# With coverage
PYTHONPATH="$PWD" python -m pytest tests/ --cov=custom_components/ecowitt_local --cov-report=term-missing
```

---

## 🚀 Release Process

1. Update version in `manifest.json`
2. Add entry to `CHANGELOG.md`
3. Commit and push to `claude/release-vX.X.X` branch
4. CI runs automatically
5. GitHub Actions creates PR
6. After merge to main, auto-release creates git tag (CRITICAL for HACS!)

**Note**: HACS requires git tags in `vX.Y.Z` format to detect releases.

---

## 💡 Pro Tips

1. **Look at WH90 implementation** for perfect examples (NOT WH77 - it's a test sensor)
2. **Use grep to find patterns**: `grep -r "wh90" custom_components/`
3. **Check CLAUDE.md** for detailed architectural guidance
4. **Test against user data** when available
5. **Comment on issues** before closing (request user testing)
6. **Recognize test scenarios**: If you see WH77, it's a quality control test

---

## 🎓 Learning Path

1. Read `architectural_patterns.md` (10 min)
2. Look at WH90 implementation in sensor_mapper.py (5 min) - NOT WH77
3. Check const.py hex ID definitions (5 min)
4. Read `issue_resolution_patterns.md` (15 min)
5. Review CLAUDE.md thoroughly (30 min)
6. Understand `automated_agent_rules.md` for WH77 restrictions (5 min)

Total: ~1 hour to become productive

---

## 🆘 When Stuck

1. Check CLAUDE.md Issue Analysis Patterns section
2. Look at similar device implementations (WH69/WS90/WH90) - NOT WH77
3. Review issue_resolution_patterns.md for matching symptoms
4. Verify hex IDs already exist in const.py before adding
5. Remember: minimal changes, reuse existing infrastructure
6. Verify issue is not about WH77 (test sensor for quality control)

---

**Last Updated**: December 9, 2025  
**Codebase Version**: v1.5.8