# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.18] - 2026-05-01

### Fixed
- **Phantom WH69 device showing WH90 entities after v1.6.17**: When a stale WH65/WH69 sensor slot from a previously paired weather station coexisted with an active WH90, both claimed the same `common_list` hex IDs (`0x02`, `0x07`, `0x0B`, `0x15`, `0x17`, `0x0D`–`0x13`). The dict-overwrite "last wins" picked an arbitrary owner depending on iteration order, splitting WH90's entities across two devices: a phantom WH69 with the temperature/humidity/wind/solar entities, and the real WH90 with only the rain entities. v1.6.17's multi-page `get_sensors_info` sweep made this newly visible because the stale WH65 slot lived on a higher page that the previous two-page sweep skipped. The mapper now prefers the entry with the stronger signal when two sensor types share live-data keys, so the active sensor wins and the stale slot stops claiming entities. (issue #155)

## [1.6.17] - 2026-04-28

### Fixed
- **Sensors disappear after gateway firmware update (GW2000A V3.3.1, GW1100B V2.4.5+)**: Newer firmware moved paired sensors to higher pages of `/get_sensors_info` and advertises the page count via `sensorid_page` in `/get_version`. The integration was hardcoded to read only pages 1–2, so paired WH51 / WH34S / WH26 / WN32 sensors became unmapped — entities fell back to channel-based naming on the gateway device, and the `wh26batt` battery never appeared. The API client now reads `sensorid_page` from `/get_version` and iterates every advertised page (with a sane fallback to the legacy two-page sweep when the field is missing or invalid). Diagnosis and proposed fix by @briansperling. (issues #146, #148, #151)
- **WH57 lightning timestamp displayed with a UTC offset**: `Last Lightning` interpreted the gateway's naive ISO-8601 timestamp as UTC, so users in non-UTC timezones saw the strike time skewed by their UTC offset (e.g. a 20:32 strike showed as 21:32 in CET). The gateway reports times in its local clock, which matches Home Assistant's configured timezone, so naive timestamps are now attached to HA's local timezone. (issue #153)

## [1.6.16] - 2026-04-27

### Fixed
- **WH55 leak sensor logged Home Assistant warning about invalid unit**: After v1.6.15 added support for the WH55 leak channels, each entity logged `Entity sensor.ecowitt_leak_… is using native unit of measurement 'None' which is not a valid unit for the device class ('moisture')`. The leak sensor reports a binary `0`/`1` state, not a percentage, so the `moisture` device class (which requires `%`) was inappropriate. The device class has been removed; the entity still reports `0`/`1` and keeps its `mdi:water-alert` icon. (issue #149)

## [1.6.15] - 2026-04-26

### Fixed
- **WH55 leak sensor created device but no entities**: Some gateways (e.g. GW1200B firmware 1.4.6) report WH55 leak channels only via the `ch_leak` array in `get_livedata_info` and never list them in `get_sensors_info`. Without an explicit handler the channels were silently ignored, so the wh55 device existed in Home Assistant but had zero entities. The coordinator now parses `ch_leak`, mapping each channel's `status` → `leak_ch{N}` (`0` = Normal, `1` = leak detected) and `battery` → `leakbatt{N}` (converted from the 0–5 scale to percentage). (issue #149)

## [1.6.14] - 2026-04-20

### Fixed
- **Rain entities rounded to whole numbers**: Precipitation entities (rain event, rain rate, 24-hour/daily/weekly/monthly/yearly rain) had no `suggested_display_precision`, so Home Assistant displayed `0.2 mm` as `0 mm` and hid small rainfall totals that were visible in the Ecowitt app. mm-unit rain entities now display 1 decimal place and inch-unit rain entities display 2 decimal places. Underlying state values are unchanged. (issue #145)

## [1.6.13] - 2026-04-07

### Fixed
- **WH35 leaf wetness sensor shows no values**: The `ch_leaf` array in `get_livedata_info` was not being processed, so leaf wetness and battery entities were created but always empty. The coordinator now reads `ch_leaf` and maps `humidity` → `leafwetness_ch{N}` and `battery` → `leaf_batt{N}` (converted from the 0–5 scale to percentage). (issue #141)

## [1.6.12] - 2026-03-28

### Fixed
- **WH40 rain data attributed to WH90**: When both a tipping-bucket rain sensor (WH40 or WH69) and a piezoelectric rain sensor (WH90, WS90, or WS85) are registered simultaneously, they share the same rain hex IDs (`0x0D`–`0x13`), causing all rain entities to appear under whichever device registered last. Rain data from the `rain` array is now explicitly forced to the tipping-bucket device, and piezoRain data to the piezoelectric device, regardless of key registration order. (issue #137)

## [1.6.11] - 2026-03-24

### Fixed
- **Invalid binary sensor entity ID**: The `srain_piezo` binary sensor (and any future binary sensors) had an invalid entity ID of the form `binary_sensor.sensor.ecowitt_…` due to a double domain prefix. This will become a hard failure in HA 2027.2.0. Entity IDs are now correctly formed as `binary_sensor.ecowitt_…`. (PR #135 by @Juror2372)

## [1.6.10] - 2026-03-22

### Fixed
- **Duplicate "Unknown" gateway device after upgrade**: Users who upgraded from a version prior to v1.6.8 (where the gateway ID fallback was introduced) were left with a ghost device labelled "Unknown" alongside the correctly-named gateway device. On next startup the integration now automatically moves all entities from the stale "unknown" device to the real gateway device and removes the ghost. (issue #132)

## [1.6.9] - 2026-03-22

### Added
- **Soil moisture AD (raw analog-to-digital) sensors**: `soilad1`–`soilad16` entities are now available for WH51/WH52 soil moisture sensors via the `/get_cli_soilad` endpoint. These are disabled by default and expose the raw ADC reading (typically ~70 for dry, ~500 for wet), enabling custom calibration curves in Home Assistant. (PR #130 by @elderapo)

## [1.6.8] - 2026-03-19

### Added
- **WS85 wind & rain sensor support**: The WS85 (`wh85` image, "Wind & Rain") is now a fully supported device with wind, rain, battery percentage, battery voltage, and capacitor voltage entities. (issue #20)

### Fixed
- **WS90/WH90/WS85 voltage sensors now in Diagnostic section**: The battery voltage and capacitor voltage entities for WS90, WH90, and WS85 are now shown in the Diagnostic section alongside the battery percentage. Previously they appeared in the main Sensors section. (issue #119)
- **WS90/WH90/WS85 voltage display precision**: Battery voltage now defaults to 2 decimal places; capacitor voltage defaults to 1 decimal place. (issue #119)
- **WH80/WS80 battery entity missing**: The WH80/WS80 outdoor weather station battery level is now created from the sensors_info `batt` field. Previously it was only created if the gateway emitted `wh80batt` in livedata (which most firmware versions don't do). (issue #125)
- **WN38 battery entity missing**: Same fix — WN38 battery is now created from sensors_info for firmware that doesn't emit it in livedata. (issue #113, #125)
- **Gateway ID showing "unknown" for GW3000B**: Some gateways (GW3000B, and potentially others) don't include a `stationtype` field in `/get_version`. The gateway ID now falls back to the model name extracted from the firmware version string instead of "unknown". (issue #117)

## [1.6.7] - 2026-03-18

### Fixed
- **Wind direction long-term statistics**: Added `state_class: measurement_angle` to wind direction sensors (`winddir`, `winddir_avg10m`) so Home Assistant can record them in long-term statistics correctly. (issue #126)
- **Signal strength missing for single-channel sensors**: WH26, WH40, WH57, WH80, and WN38 sensors were not getting a Signal Strength diagnostic entity because the integration incorrectly required a channel number. Fixed so all paired sensors now show signal strength. (issues #122, #125)
- **WH40 battery percentage wrong**: The WH40 rain gauge uses a 0–5 bar battery scale. The integration was treating it as binary (0/1) encoding, showing 10% when it should show 20–100%. Now correctly converts bar values to percentage (each bar = 20%). (issue #125)
- **Decimal sensor IDs getting ugly entity names**: Sensors with decimal IDs like `3` (feels-like temperature) and `5` (VPD) were generating entity IDs like `sensor_ch3` instead of `feels_like_temp_…`. Fixed with explicit ID-to-name mapping. (issue #121)

## [1.6.6] - 2026-03-15

### Added
- **WS90/WH90 capacitor and battery voltage sensors**: The WS90/WH90 reports a capacitor voltage (`ws90cap_volt`) and a precise battery voltage (`voltage`) alongside the existing battery percentage. Both are now exposed as sensor entities — `WS90 Capacitor Voltage` and `WS90 Battery Voltage` — allowing you to track capacitor charge level and exact battery voltage rather than just the 0–100% bar reading. (issue #119)

## [1.6.5] - 2026-03-15

### Fixed
- **WH26/WN32 dew point entity missing**: Added dew point (`0x03`) to the WH26/WN32 sensor mapping so a Dewpoint Temperature entity is now created alongside temperature and humidity. (issue #104)
- **WH26/WN32 battery entity missing**: The WH26/WN32 gateway firmware embeds the battery level inside the dew point (`0x03`) common_list item rather than sending a separate `wh26batt` key. The coordinator now extracts this embedded battery value and creates the battery entity. Uses binary encoding: `0` = 100% (full), non-`0` = 10% (low). (issue #104)
- **Gateway device showing "Unknown" model**: Some gateways return the firmware version string with a `"Version: "` prefix (e.g. `"Version: GW1100A_V2.4.3"`), which broke the model name extraction. The extractor now searches for the `GW…` model name anywhere in the version string rather than assuming it starts at position 0. (issue #117)

### Changed
- Updated README to better explain the stable hardware-ID entity system as the primary motivation for this integration, and to include a comparison table with both the built-in HA Ecowitt integration and Ecowitt's official `ha-ecowitt-iot` integration.

## [1.6.4] - 2026-03-14

### Added
- **WN38 Black Globe Thermometer support**: The WN38 now creates two sensor entities: Black Globe Temperature (`0xA1`) and WBGT — Wet Bulb Globe Temperature (`0xA2`). Both appear on the gateway device (current firmware reports no hardware ID for WN38). (issue #113)

### Fixed
- **WH26/WN32 outdoor T&H sensor entities missing**: The WH26/WN32 was incorrectly mapped to indoor sensor keys (`tempinf`, `humidityin`). Fixed to use the correct outdoor hex ID keys (`0x02`, `0x07`) so the sensor's hardware ID is linked to temperature and humidity entities and they appear under their own device. (issue #104)
- **srain_piezo exposed as binary sensor**: The piezo rain state sensor (`srain_piezo`) is now created as a `moisture` binary sensor (on = raining, off = dry) instead of a numeric 0/1 sensor entity. (issue #110)

## [1.6.3] - 2026-03-08

### Added
- **WH46D PM1.0 and PM4.0 sensor support**: The WH46D air quality sensor provides PM1.0 and PM4.0 readings in addition to PM2.5, PM10, CO2, temperature, and humidity. These values were present in the `co2` live data array but not processed. Four new entities are now created: PM1.0, PM1.0 24h Avg, PM4.0, and PM4.0 24h Avg. The WH46D is detected as `wh45` type by the gateway; the integration now handles both WH45 and WH46D from the same `co2` array — WH45 sensors simply won't have PM1/PM4 data so no extra entities appear. (issue #108)

## [1.6.2] - 2026-03-06

### Fixed
- **WH52 soil temperature and conductivity entities appear on gateway instead of WH52 device**: The GW3000 gateway reports the WH52 as `wh51` in `get_sensors_info`, so the hardware ID mapping only included `soilmoisture` and `soilbatt` keys for WH51. The `soiltemp` and `soilec` keys from the `ch_ec` live data array had no hardware ID mapping and fell through to the gateway device. Fixed by including `soiltemp{ch}` and `soilec{ch}` in the WH51 key list — if the connected sensor is a real WH51 (no EC data), these extra keys simply won't exist in live data and no extra entities are created. (issue #103)

## [1.6.1] - 2026-03-06

### Fixed
- **Unconnected sensor slots pollute hardware mapping**: The gateway's `get_sensors_info` page 2 lists all possible sensor channel slots, including unconnected ones with placeholder hardware IDs (`FFFFFFFF` / `FFFFFFFE`). These were previously processed and added to the mapping, potentially overwriting valid hardware IDs for connected sensors (e.g. WH51 CH1 with real ID `4108` could be shadowed by CH2–16 all mapped to `FFFFFFFF`). Placeholder IDs are now filtered out during sensor mapping, ensuring only physically connected sensors appear as devices.

## [1.6.0] - 2026-03-06

### Added
- **WH52 soil sensor support**: The WH52 (enhanced soil sensor with electrical conductivity) now creates entities for soil moisture, soil temperature, and soil electrical conductivity (EC in µS/cm) from the `ch_ec` data array. Battery is mapped using the same 0–5 bar scale as WH51. (issue #103)

## [1.5.36] - 2026-03-01

### Fixed
- **WH45 air quality sensor creates no entities**: The WH45 (CO2 + PM2.5 + PM10 + temperature/humidity combo sensor) was completely missing from the local polling integration. The gateway returns its data in a `co2` JSON array, which was never processed. The coordinator now extracts all WH45 readings from the `co2` array and maps them to the expected sensor keys (`pm25_co2`, `pm10_co2`, `co2`, `co2_24h`, `humi_co2`, `tf_co2`/`tf_co2c`, and battery). Battery level 6 (DC power) is correctly capped at 100%. (issue #96)

## [1.5.35] - 2026-02-28

### Fixed
- **WH69 rain sensor battery linked to wrong device**: When a WH69 weather station is used as the rain sensor, its battery entity was being assigned to the WH40 rain gauge device instead of the WH69 device. The integration now detects whether a WH69 is registered and uses the correct `wh69batt` key (linking battery to the WH69 device) rather than always defaulting to `wh40batt`. This is the same device-aware battery association pattern used for WS90/WH90 battery in v1.5.32.

## [1.5.34] - 2026-02-28

### Fixed
- **WH40/WH69 rain sensor battery shows 0% when battery is new**: The `0x13` (Yearly Rain) item in the `rain` array carries the rain sensor's battery level. The integration was treating it as a 0–5 scale (`× 20`), causing a new battery to show 0%. Confirmed by @mjb1416 (GW1200A + WH69, issue #95): `"battery": "0"` with a new battery. The encoding is binary — `"0"` = full (100%), `"1"` = low (10%) — matching the same encoding already used for the `ch_aisle` battery (fixed in v1.5.28). Updated to use correct binary conversion.

## [1.5.33] - 2026-02-28

### Fixed
- **`0x10` rain entity mislabeled as "Hourly Rain" (is Daily Rain)**: The `0x10` hex ID in Ecowitt's local API contains a midnight-reset **daily** rain total, not hourly rain. The integration was displaying it as "Hourly Rain" since v1.5.21. User @nmaster2042 confirmed this via history chart (value accumulates all day, resets at midnight) and comparison with the Ecowitt app (HA showed 7mm, Ecowitt "Hourly" showed 1.1mm, "Daily" showed 7mm). The Ecowitt app's "Hourly" value is not available in the local polling API. Fixed by renaming `0x10` to "Daily Rain" throughout. **⚠️ Breaking change:** Entity ID changes from `sensor.ecowitt_hourly_rain_XXXX` → `sensor.ecowitt_daily_rain_XXXX` — update any automations or dashboards referencing `hourly_rain`.

## [1.5.32] - 2026-02-26

### Fixed
- **WS90 battery entity appears under Gateway instead of WS90 device**: The `piezoRain` battery extraction always used the key `wh90batt`, so WS90 users' battery entity was assigned no hardware ID and fell to the gateway device. Fixed by checking which battery key (`ws90batt` or `wh90batt`) is registered in the sensor mapper and using the correct one. WH90 users are unaffected.

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
