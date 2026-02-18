# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.14] - 2026-02-18

### Fixed
- **WH31/ch_aisle temperature double-conversion for Celsius gateways**: Ecowitt firmware always reports `"unit": "F"` in `ch_aisle` data even when the gateway is configured in Celsius mode, causing HA to apply an erroneous °F→°C conversion to values that are already in Celsius (e.g. 22.2°C displayed as −5.5°C). The coordinator now fetches the gateway's actual unit setting from `/get_units_info` and uses it when processing `ch_aisle` temperature sensors. Fixes issues #19, #13.

## [1.5.13] - 2026-02-18

### Fixed
- **Rain sensor state_class missing**: Rain entities now correctly expose `state_class` (`measurement` for rain rate, `total` for event rain, `total_increasing` for accumulated rain). Previously all `precipitation` device-class sensors were forced to `measurement`, causing HA long-term statistics warnings after HA 2025.12. Fixes issues #32, #45.

## [1.5.12] - 2026-02-18

### Fixed
- **Options flow values not saved**: After editing options (scan interval, mapping interval, include inactive), reopening the options form now shows the previously saved values instead of reverting to the original setup values. Fixes issues #50, #31.

## [1.5.11] - 2026-02-18

### Fixed
- **HA 2026.x compatibility**: Update deprecated `hass.helpers.entity_registry` API calls to use `homeassistant.helpers.entity_registry` module directly
- **HA 2026.x compatibility**: Replace direct `config_entry.minor_version` assignment (now read-only) with `hass.config_entries.async_update_entry()`
- **HA 2026.x compatibility**: Remove `config_entry` parameter from `OptionsFlowHandler.__init__` (base class now provides it automatically)

## [1.5.10] - 2026-02-18

### Fixed
- **Inactive sensor filtering**: Also exclude sensors with IDs `FFFFFFFE` and `00000000` (not only `FFFFFFFF`) to correctly filter all unconnected sensors (contributed by @rvecchiato, fixes #48)
- **Entity ID casing**: Normalize sensor type names to lowercase for consistent entity ID generation

## [1.5.8] - 2025-11-13

### Documentation
- **HACS Integration**: Added comprehensive documentation about HACS tag requirements
  - Detailed explanation of how HACS detects releases via git tags
  - Tag format requirements (vX.Y.Z) with examples
  - Verification steps for validating HACS integration
  - Complete workflow descriptions for all three automation workflows

### Changed
- **Release Documentation**: Enhanced CLAUDE.md with explicit HACS tagging process
  - Documents that auto-release.yml creates annotated git tags automatically
  - Clarifies that tags are CRITICAL for HACS to detect new versions
  - Added verification commands for post-release validation

## [1.5.7] - 2025-11-13

### Fixed
- **CHANGELOG Extraction**: Fixed auto-release workflow to properly extract release notes from CHANGELOG.md
  - Improved awk pattern matching for version sections
  - GitHub releases now include full CHANGELOG content instead of generic message

### Changed
- **Testing**: Full automation test with end-to-end workflow validation

## [1.5.6] - 2025-11-13

### Added
- **Automated Release Process**: Complete GitHub Actions automation for releases
  - Auto-PR creation when pushing to `claude/**` branches with version bumps
  - Auto-merge after all CI checks pass
  - Auto-release creation with git tags and GitHub releases
  - Version change detection to prevent unnecessary release PRs
- **Release Documentation**: Comprehensive documentation in CLAUDE.md and .github/workflows/README.md
- **README Update**: Added Automated Releases section in Contributing guide

### Technical Details
- Three new GitHub Actions workflows: auto-pr.yml, auto-merge.yml, auto-release.yml
- Smart version detection compares branch version with main to trigger releases
- CHANGELOG-based release notes extraction
- Proper check name matching for CI validation

## [1.5.5] - 2025-11-13

### Fixed
- **Home Assistant 2025.11 Compatibility**: Fixed `services.yaml` validation error by removing device filters from target selectors
  - Home Assistant 2025.11 introduced a breaking change that removed support for device filters in target selectors
  - Updated service definitions to use simplified target format without device filters
  - Service handlers in Python already validate device membership, so no functionality is lost
  - Fixes hassfest validation error: "Services do not support device filters on target, use a device selector instead"

### Technical Details
- Simplified `refresh_mapping` and `update_data` service target selectors to basic format
- Removed deprecated device filter syntax that was causing CI failures
- All GitHub Actions tests now passing (CI, hassfest, HACS validation)

## [1.5.4] - 2025-10-07

### Fixed
- Enhanced piezoRain test with flexible battery value validation

## [1.5.3] - Previous Release

See [GitHub Releases](https://github.com/alexlenk/ecowitt_local/releases) for earlier versions.

---

## Version History

- **1.5.7** - CHANGELOG extraction fix and automation testing
- **1.5.6** - Automated release process
- **1.5.5** - Home Assistant 2025.11 compatibility fix
- **1.5.4** - Test improvements
- **1.5.3** - Bug fixes
- **1.5.2** - Bug fixes
- **1.5.1** - Bug fixes
- **1.5.0** - Feature release
- **1.4.9** - Bug fixes
- **1.4.8** - WH90 support

For detailed information about each release, visit the [Releases page](https://github.com/alexlenk/ecowitt_local/releases).
