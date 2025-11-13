# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

- **1.5.5** - Home Assistant 2025.11 compatibility fix
- **1.5.4** - Test improvements
- **1.5.3** - Bug fixes
- **1.5.2** - Bug fixes
- **1.5.1** - Bug fixes
- **1.5.0** - Feature release
- **1.4.9** - Bug fixes
- **1.4.8** - WH90 support

For detailed information about each release, visit the [Releases page](https://github.com/alexlenk/ecowitt_local/releases).
