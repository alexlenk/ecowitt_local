# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.31] - 2026-02-26

### Fixed
- **WH57 Lightning Strikes and Last Lightning entities missing**: All three lightning sensor keys (`lightning_num`, `lightning_time`, `lightning`) were generating the same entity ID (`sensor.ecowitt_lightning_*`) due to a substring collision in the entity ID generator. The coordinator added all three to its sensor list but only the distance entity survived — strikes and timestamp were silently overwritten. Fixed by adding specific patterns for `lightning_num` (`lightning_strikes`) and `lightning_time` (`last_lightning`) before the generic `lightning` pattern. The distance entity ID is unchanged (`sensor.ecowitt_lightning_*`). Reported by @chrisgillings in issue #19.
- **WH57 Last Lightning timestamp invalid in HA**: The gateway returns the last-strike datetime as a naive ISO 8601 string (`"2026-02-22T18:00:36"`) without timezone info. Home Assistant's `timestamp` device class requires a timezone-aware `datetime` object. Fixed by converting the string to a UTC-aware `datetime` in sensor entity setup.

## [1.5.30] - 2026-02-25

### Fixed
- **WH90 battery shown as 5% in Battery State Card**: The raw battery bar value (0–5 scale from the gateway's `get_sensors_info` API) was being spread into the attributes of every entity on a device, including non-battery entities. Battery State Card reads the `battery_level` attribute and interpreted the raw bar value (e.g. `5`) as 5%, showing a nearly-dead battery for a fully charged WH90. Fixed by removing the raw `battery` field from shared sensor details and instead setting `battery_level` only on dedicated battery entities, sourced from the entity's own state (which is already correctly converted to a percentage). Closes issue #90.

## [1.5.29] - 2026-02-24

### Added
- **Solar Illuminance (lux) entity**: Added a computed `sensor.ecowitt_solar_lux_*` entity alongside the existing solar radiation (`0x15`) entity. The gateway's local API always returns solar radiation in W/m² regardless of the unit setting in the gateway web UI, so illuminance is computed as `lux = W/m² × 126.7`. The entity uses device class `illuminance` and unit `lx`. Users who had their gateway set to "Lux" mode (which was already handled by the Klux conversion) will now also see this computed entity — both show the same value in that case. Closes issue #84.

## [1.5.28] - 2026-02-24

### Fixed
- **WH57 (lightning sensor) has no entities**: The coordinator was completely ignoring the `lightning` block in the gateway API response. Fixed by adding dedicated processing that extracts lightning distance, strike count, last-strike timestamp, and battery level from the `lightning` array and maps them to the WH57 device. Reported by @chrisgillings in issue #19.
- **WH40 (rain gauge) has no entities**: The sensor mapper was using plain metric key names (`rainratein`, `eventrainin`, etc.) which don't match what the gateway API actually sends — the `rain` array uses hex IDs (`0x0E`, `0x0D`, `0x7C`, `0x10`, `0x11`, `0x12`, `0x13`). Fixed by updating WH40 to use the correct hex ID keys. Reported by @chrisgillings in issue #19.
- **WH40 battery not shown**: The battery level embedded in the `0x13` (yearly rain) item of the `rain` array was silently discarded. Fixed by extracting it and creating the `wh40batt` entity.

## [1.5.27] - 2026-02-23

### Fixed
- **Unknown content-type JSON parsing**: Gateways that return JSON with an unrecognised `Content-Type` header (e.g. `application/octet-stream`) could silently fail. Fixed by passing `content_type=None` to skip the content-type check when the type is not `application/json`, `text/html`, or `text/plain`.
- **Leafwetness channel key duplication in const.py**: Removed a duplicate `elif base_key == "leafwetness_ch"` branch that was shadowed by the earlier `if "_ch" in base_key` check. No user-visible behaviour change.

### Changed
- **Test coverage raised to 100%**: Added targeted tests for all previously uncovered edge-case code paths (retry-after-401 success path, GW-prefix firmware model regex, migration hardware-id fallback from coordinator data, and reload-entry success path).
- **Updated codecov badge URL** in README to use the stable token-based link.

## [1.5.26] - 2026-02-23

### Fixed
- **WH31/WH69 battery always shows 0% even when battery is OK**: WH31 and WH69 sensors report battery as a binary flag — `0` means OK, `1` means weak — not a 0–5 bar scale. The previous code applied `value × 20` (designed for WH51 soil sensors), which mapped `0` → 0% and `1` → 20%. Both values were wrong. Fixed: binary `0` now displays 100% (OK) and binary `1` displays 10% (weak). Reported by @AnHardt in issue #19.
- **0x7C rain entity mislabeled "Daily Rain"**: The `0x7C` hex ID contains a rolling 24-hour rain total (not a midnight-reset calendar daily total). It was labeled "Daily Rain" which caused confusion when the value did not reset at midnight. Renamed to "24-Hour Rain". Entity IDs change from `sensor.ecowitt_daily_rain_XXXX` to `sensor.ecowitt_24h_rain_XXXX` — users with automations referencing the old entity ID will need to update them. Confirmed by @nmaster2042 in issue #5.

### Changed
- **⚠️ Breaking: `sensor.ecowitt_daily_rain_XXXX` entity renamed to `sensor.ecowitt_24h_rain_XXXX`**: If you have automations, scripts, or dashboards referencing `daily_rain` in the entity ID, update them to use `24h_rain` instead.

## [1.5.25] - 2026-02-22

### Fixed
- **WH31/WH34 temperature still wrong on GW3000A and GW1200C**: The v1.5.14 fix for Celsius temperature double-conversion was not working on newer gateway firmware. Newer firmware (GW3000A, GW1200C) returns the temperature unit setting under the key `"temperature"` in `/get_units_info`, while older firmware uses `"temp"`. The coordinator was only checking `"temp"`, so on newer gateways it silently fell back to assuming Fahrenheit and the double-conversion persisted. Fixed by checking `"temperature"` first and falling back to `"temp"`. Fixes issue #19.

## [1.5.24] - 2026-02-22

### Fixed
- **Signal strength entity causes HA validation error**: Signal strength sensors (reporting 0–100% converted from the gateway's 0–4 bar scale) were incorrectly using `device_class: signal_strength`, which Home Assistant requires to be in dB or dBm. This caused a log error on every HA startup: *"is using native unit of measurement '%' which is not a valid unit for the device class ('signal_strength')"*. Removed the device class; the sensor now reports a plain percentage with no device class, which is valid and suppresses the error. Reported by @mlohus93 in issue #13.

## [1.5.23] - 2026-02-22

### Fixed
- **WS90/WH90 sensors freeze after startup — wind, UV, radiation, rain stuck at initial value**: When the integration was updated in a prior version, entity IDs for hex-sensor types were renamed (e.g. `sensor.ecowitt_0x0b_4094a8` → `sensor.ecowitt_wind_speed_4094a8`). Home Assistant kept the old entity IDs in the entity registry for existing installations. On each coordinator refresh, the data lookup failed to find the old entity_id in the new-format sensor dict; the broken fallback then returned the wrong sensor's data (always outdoor temperature). Home Assistant rejected the resulting device-class/unit mismatch and left the entity frozen at its startup value. Fixed by switching the primary lookup to `sensor_key + hardware_id`, which is stable across entity_id format changes. All sensors now update on every coordinator refresh regardless of which entity_id format is stored in the registry. Reported by @nmaster2042 in issue #5.
- **WH90 battery entity appears under gateway device instead of WH90 device**: The battery value extracted from `piezoRain` was stored with key `ws90batt`, but the sensor mapper registered `wh90batt` for WH90. The key mismatch caused the battery entity to have no hardware ID and appear under the gateway device. Changed coordinator to use `wh90batt` to match the sensor mapper, so the battery is now correctly associated with the WH90 device.
- **Apparent temperature (sensor "4") appears with wrong name and no device class**: GW2000/GW3000 gateways report apparent temperature as common_list id `"4"` alongside outdoor sensors. This key was missing from `GATEWAY_SENSORS` and `SENSOR_TYPES`, so it appeared as an unnamed sensor with entity_id `sensor.ecowitt_sensor_ch4`. Added proper definition: "Apparent Temperature", device class temperature, state class measurement.

## [1.5.22] - 2026-02-21

### Fixed
- **WH41 PM2.5 air quality sensor has no entities**: The `ch_pm25` data section returned by Ecowitt gateways (GW3000, GW2000, etc.) was never processed by the coordinator, so WH41 sensors would appear as a device with zero entities. The coordinator now reads `ch_pm25` and creates `pm25_ch{N}` (real-time PM2.5), `pm25_avg_24h_ch{N}` (24-hour average), and `pm25batt{N}` (battery) entities for each channel. Both `"pm25"` (lowercase) and `"PM25"` / `"PM25_24HAQI"` (uppercase) field name variants from different firmware versions are handled. Fixes issue #68.
- **PM2.5 24h average entity_id collision with real-time entity**: The sensor type extractor was returning `pm25` for both `pm25_ch1` and `pm25_avg_24h_ch1`, causing both entities to share the entity_id `sensor.ecowitt_pm25_*` and overwrite each other. The 24h average now generates a distinct `sensor.ecowitt_pm25_24h_avg_*` entity_id.

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
