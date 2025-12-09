# Automated Agent Rules

## 🚫 WH77 Test Sensor - NO AUTOMATED WORK

**Device**: WH77 Multi-Sensor Station  
**Status**: ✅ Fully implemented and tested  
**Restriction**: Automated agents must NOT work on WH77-related code or issues

**Rationale**:
- WH77 implementation serves as a reference pattern for other devices
- Changes could break test fixtures used for validation
- Implementation is stable and should remain unchanged
- Any WH77 issues require manual review by maintainers

**What automated agents should do**:
- ✅ Reference WH77 implementation as an example for similar devices
- ✅ Use WH77 test patterns for new device tests
- ❌ Do NOT modify WH77 device detection code
- ❌ Do NOT modify WH77 test fixtures
- ❌ Do NOT attempt to fix WH77-related issues without explicit maintainer approval

### Files to Avoid (WH77-related)
```
custom_components/ecowitt_local/sensor_mapper.py (lines 248-269)
custom_components/ecowitt_local/const.py (lines 489-492 - wh77batt)
tests/test_wh77_support.py (entire file)
tests/fixtures/test_wh77.py (entire file)
```

## ✅ Allowed Automated Work

### Device Support Additions
Automated agents MAY add support for new devices (not WH77) following documented patterns.

### Bug Fixes
Automated agents MAY fix bugs with clear definitions and reproducible symptoms.

### Documentation Updates
Automated agents MAY update documentation but not WH77 implementation examples without review.

## 🔍 Issue Handling Protocol

1. Check if issue involves WH77 → If yes, STOP and notify maintainer
2. Implement fix on `claude/**` branch
3. Wait for CI to pass
4. Comment on issue with fix details and request user testing
5. **NEVER close issues** - leave open for user confirmation

---

**Last Updated**: December 9, 2025
