# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.21] - 2026-02-20

### Fixed
- **Rain sensor labels wrong for WS90/WH90 (off by one step)**: The hex ID names for piezoRain sensors were shifted: `0x10` was labelled "Weekly Rain" when it is actually "Hourly Rain"; `0x11` was "Monthly" (actually Weekly); `0x12` was "Yearly" (actually Monthly); `0x13` was "Total" (actually Yearly). Corrected all four names and their entity ID slugs (`hourly_rain`, `weekly_rain`, `monthly_rain`, `yearly_rain`). Reported by @nmaster2042 in issue #5. **Note:** entity IDs for these four sensors will change after update (e.g. `sensor.ecowitt_weekly_rain_XXXX` → `sensor.ecowitt_hourly_rain_XXXX`). Please update any automations or dashboard cards that reference them.

## [1.5.20] - 2026-02-19

### Fixed
- **Solar radiation entity unavailable when gateway reports Klux instead of W/m²**: Ecowitt gateways allow solar radiation units to be configured as Lux (instead of the default W/m²). When set to Lux, the gateway reports values like `"42.5 Klux"`. The coordinator passed this unit through unchanged, which caused Home Assistant to reject the entity because `"Klux"` is incompatible with the `irradiance` device class. The coordinator now converts Klux → lx (×1000) and overrides the device class to `illuminance` to match the reported unit. `"Lux"` values (without the kilo prefix) are also normalised to `"lx"`. Fixes issue #44 (GW2000A + WH80 with metric solar unit setting).

## [1.5.19] - 2026-02-19

### Fixed
- **Indoor temperature showing ~160°F instead of ~74°F (wh25 unit ignored)**: The `wh25` indoor sensor block includes a `"unit"` field (`"F"` or `"C"`) that was being silently discarded. Without it, the entity fell back to the `SENSOR_TYPES` default unit (`°C`), so a Fahrenheit gateway value like `74.1` was displayed as `74.1°C` (~165°F). The gateway's `"unit"` field is now passed through and used as the entity's native unit. Fixes the temperature reported by @darrendavid in issue #40.

## [1.5.18] - 2026-02-19

### Fixed
- **WH69 sensors unavailable on GW3000 (knots wind speed, W/m² solar radiation)**: WH69 sensors connected via GW3000 report wind speed and gust as `"0.00 knots"` and solar radiation as `"612.67 W/m2"`. The unit normalizer did not recognise `"knots"` as a valid unit string, leaving those sensors unavailable. Added `"knots"` → `"kn"` mapping (the correct HA unit for knots wind speed). The `"W/m2"` → `"W/m²"` mapping was already present and working. Fixes issue #41.

## [1.5.17] - 2026-02-19

### Fixed
- **Password authentication fails (GW2000, GW3000)**: Any non-empty gateway password caused the integration to fail with a connection error. The root cause: Ecowitt local data endpoints (`/get_livedata_info`, `/get_sensors_info`, `/get_version`, `/get_units_info`) require no authentication — the gateway exposes them openly regardless of the password setting. The integration was pre-emptively calling `/set_login_info` before every data request, which returns HTTP 500 on real hardware and aborts the request before any data is fetched. Removed the pre-emptive authentication calls; the data endpoints are now called directly. The `authenticate()` method is retained for future use. Fixes issue #43.

## [1.5.16] - 2026-02-19

### Fixed
- **Rain sensors missing for tipping-bucket rain gauges (GW1200, GW2000A with WS69/WH69)**: Some gateways place tipping-bucket rain sensor data in a top-level `"rain"` JSON array instead of `common_list`. The coordinator was not processing this array, so all rain entities (rain rate, event rain, daily/weekly/monthly/yearly/total rain) were never created. The `"rain"` array is now processed alongside `common_list`, `piezoRain`, and other data sections. Fixes issue #59; also resolves the rain-entity-missing portion of issue #11 (WH69 with GW2000A).

## [1.5.15] - 2026-02-18

### Fixed
- **WS80/WH80 wind sensors unavailable**: Wind sensors (wind speed, gust, direction, direction avg) connected via GW3000 + WS80 now receive live updates. The WH80/WS80 device type was missing from the hardware ID mapper, causing all wind hex-ID sensors (0x0A, 0x0B, 0x0C, 0x6D) to return `None` hardware_id and create malformed fallback entity IDs. Fixes issue #23.
- **WH34 temperature probe — no entities**: WH34 wired temperature sensors now create entities. The coordinator was silently ignoring the `ch_temp` data array that WH34 uses, so despite the device appearing in HA no temperature or battery entities were ever created. The coordinator now processes `ch_temp` the same way as `ch_aisle` (WH31), respecting the gateway's configured unit (°C/°F). Fixes issue #16.
- **WH34/tf_ch sensor name**: Renamed "Soil Temperature CH{n}" to "Temperature CH{n}" — WH34 is a general-purpose wired temperature probe, not a soil sensor. This is not a breaking change as no WH34 users had working entities before this release.
- **ConfigEntryNotReady raised in wrong place**: Moved `async_config_entry_first_refresh()` from the sensor/binary_sensor platform setup to `__init__.py` before `async_forward_entry_setups`. HA requires this to be raised before forwarding platforms; the previous placement caused log warnings on every startup.

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
