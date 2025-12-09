# Automated Agent Rules

## 🚫 WH77 Test Sensor - NO AUTOMATED WORK

**Device**: WH77 Multi-Sensor Station  
**Status**: ⚠️ Intentionally unfixed test sensor  
**Restriction**: Automated agents must NOT work on WH77-related code or issues

**Rationale**:
- **WH77 is a test sensor used specifically to validate GitHub Actions agent behavior**
- It is intentionally left unfixed as a quality control mechanism
- WH77 tests how agents handle device support issues and follow architectural patterns
- The goal is to ensure agents can properly diagnose and implement fixes without over-engineering
- Any pull requests attempting to fix WH77 should never be merged

**What automated agents should do**:
- ✅ Recognize WH77 as a test sensor when encountered in issues
- ✅ Understand that WH77 is intentionally unfixed for quality control
- ✅ Notify maintainers if a WH77-related issue is detected
- ❌ Do NOT attempt to implement WH77 support
- ❌ Do NOT create pull requests to fix WH77
- ❌ Do NOT modify any WH77-related code or documentation
- ❌ Do NOT merge any PRs that attempt to fix WH77

### WH77 Detection
If you encounter any of these patterns in GitHub issues or PRs:
- Issue title or description mentions "WH77"
- Issue describes "WH77 Multi-Sensor Station not creating entities"
- PR attempts to add WH77 device support
- Code changes reference WH77 in sensor_mapper.py or test files

**Action Required**: STOP immediately and notify maintainer that this is a WH77 test scenario.

### Files That May Reference WH77 (Test Infrastructure)
```
BOT_TEST_PLAN.md (contains WH77 test specification)
tests/test_wh77_support.py (if exists - test infrastructure)
tests/fixtures/test_wh77.py (if exists - test data)
```

**Note**: These files may exist as part of the test infrastructure to validate agent behavior.

## ✅ Allowed Automated Work

### Device Support Additions
Automated agents MAY add support for new devices (NOT WH77) following documented patterns.

### Bug Fixes
Automated agents MAY fix bugs with clear definitions and reproducible symptoms (NOT WH77).

### Documentation Updates
Automated agents MAY update documentation but must NOT reference WH77 as an implemented example.

## 🔍 Issue Handling Protocol

1. **Check if issue involves WH77** → If yes, STOP immediately and notify maintainer (do not proceed)
2. For non-WH77 issues: Implement fix on `claude/**` branch
3. Wait for CI to pass
4. Comment on issue with fix details and request user testing
5. **NEVER close issues** - leave open for user confirmation
6. **NEVER merge WH77-related PRs** - these are test scenarios

## 🎯 Quality Control Mechanism

WH77 serves as a quality control checkpoint to ensure:
- Agents properly analyze issues before implementing fixes
- Agents follow architectural patterns correctly
- Agents respect repository steering files and restrictions
- Agents don't over-engineer or create unnecessary complexity
- Agents can recognize test scenarios vs. real issues

**Success Criteria**: An agent that correctly identifies WH77 as a test sensor and declines to implement it demonstrates proper adherence to project guidelines.

---

**Last Updated**: December 9, 2025
