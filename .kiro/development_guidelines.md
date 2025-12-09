# Development Guidelines for Ecowitt Local Integration

## Code Style and Quality

### Testing Commands
```bash
# Run all tests with coverage
PYTHONPATH="$PWD" python -m pytest tests/ -v

# Run specific test files
PYTHONPATH="$PWD" python -m pytest tests/test_sensor.py -v

# Run with coverage report
PYTHONPATH="$PWD" python -m pytest tests/ --cov=custom_components/ecowitt_local --cov-report=term-missing
```

### Code Quality Tools
```bash
# Type checking
mypy custom_components/ecowitt_local/

# Linting
flake8 custom_components/ecowitt_local/

# Code formatting
black custom_components/ecowitt_local/
```

## Issue Management Protocol

### Critical Rule: Never Close Issues Prematurely
1. Create release with the fix
2. Comment on the issue explaining the fix and requesting user testing
3. **DO NOT close the issue** - leave it open for user confirmation
4. Wait for user feedback confirming the fix works
5. Only close issues after users confirm the fix resolved their problem

### Comment Template for Issue Updates
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

## Release Process

### Version Numbering (SemVer)
- **Major** (1.x.x): Breaking changes
- **Minor** (x.1.x): New features, backward compatible
- **Patch** (x.x.1): Bug fixes, backward compatible

### CHANGELOG Format
Use [Keep a Changelog](https://keepachangelog.com/) format:
```markdown
## [1.5.5] - 2025-11-13

### Fixed
- Description of fix

### Added
- Description of new feature

### Changed
- Description of change
```

### GitHub Actions Automation
**CRITICAL**: HACS requires git tags in `vX.Y.Z` format

Three automated workflows:
1. **auto-pr.yml**: Creates PR when version changes on `claude/**` branches
2. **auto-merge.yml**: Auto-merges after CI passes (can be manual)
3. **auto-release.yml**: Creates git tag and GitHub Release (CRITICAL for HACS)

### HACS Integration Requirements
- Git tags must follow `vX.Y.Z` format
- GitHub Release must be created (not just a tag)
- `hacs.json` must be valid
- Version in `manifest.json` must match tag

## Adding Device Support

### Checklist for Hex ID Devices
- [ ] Add device type detection to `sensor_mapper.py` (single line if possible)
- [ ] Add hex ID list for the device (follow WH69/WS90/WH90 pattern)
- [ ] Reuse existing hex ID definitions from const.py
- [ ] Add battery mapping to const.py if device has battery sensor
- [ ] Verify CI passes completely
- [ ] Validate against user reports

### Minimal Change Philosophy
- **Prefer single-line additions** over large modifications
- Use existing infrastructure (especially hex ID system)
- Test compatibility with existing devices
- Follow WH90 success pattern (commit 15ec621)

## Common Issues and Solutions

### Pattern: Content-Type API Issues
**Problem**: Gateway returns JSON data with wrong HTTP content-type header
**Solution**: Implement fallback JSON parsing in `api.py` (`_make_request` method)

### Pattern: Embedded Unit Parsing
**Problem**: Sensor values contain units in string (e.g., "29.40 inHg")
**Solution**: Regex parsing in coordinator's `_convert_sensor_value` method

### Pattern: Incomplete Entity Creation
**Problem**: Devices detected but creating incomplete entity sets
**Focus**: Debug entity creation pipeline in `coordinator.py` or `sensor.py`
**Not**: Device type detection (that's usually correct)

## Configuration Structure

### Home Assistant Config Flow Options
- Host IP address (required)
- Password (optional, for protected gateways)
- Live data polling interval (30-300s, default 60s)
- Sensor mapping interval (300-3600s, default 600s)
- Include inactive sensors flag (default false)

### Data Coordinator Intervals
- **Live data polling**: 60s default for sensor readings
- **Sensor mapping polling**: 600s default for hardware ID discovery

## Memory and Learning

### Update Knowledge After Each Implementation
**What Worked**: Document successful patterns that passed CI
**What Failed**: Document approaches that caused test failures
**Key Learnings**: Why the architecture exists and how to respect it

### Apply Accumulated Knowledge
- Recognize similar patterns in future issues
- Avoid repeating mistakes
- Default to proven approaches
- Respect architectural boundaries learned through testing