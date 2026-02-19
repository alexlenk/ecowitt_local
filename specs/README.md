# Ecowitt Local — Issue Specs

Kiro-style specs for open GitHub issues. Each spec has: requirements, design, tasks, and open questions.

## Status Overview

| Spec | Issue(s) | Title | Priority | Status |
|------|----------|-------|----------|--------|
| [001](001-options-flow-values-not-saved.md) | #50, #31 | Options flow values not saved after edit | HIGH | ✅ Fixed in v1.5.12 |
| [002](002-rain-sensor-state-class.md) | #32, #45 | Rain entities missing `state_class` | HIGH | ✅ Fixed in v1.5.13 |
| [003](003-temperature-double-conversion.md) | #19, #13 | Temperature double-conversion for Celsius gateways | HIGH | ✅ Fixed in v1.5.14 |
| [004](004-wind-rain-hex-id-mapping.md) | #22, #23 | Wind/rain sensors unavailable (missing hardware_id mapping) | HIGH | ⚠️ Partial — WS80/WH80 fixed in v1.5.15; GW1100 still awaiting user data |
| [006](006-wh34-pool-temperature.md) | #16 | WH34 pool temperature — no entities | MEDIUM | ✅ Fixed in v1.5.15 |
| [007](007-rain-array-not-processed.md) | #59, #11 | `"rain"` array (tipping-bucket) not processed | HIGH | ✅ Fixed in v1.5.16 |
| [008](008-password-auth-fails.md) | #43 | Password authentication fails (GW2000/GW3000) | HIGH | ✅ Fixed in v1.5.17 |
| [009](009-ws90-gw2000-incomplete-entities.md) | #5, #40, #15 | WS90/GW2000 incomplete or unavailable entities | HIGH | 🔴 Open — multiple root causes identified |
| [010](010-wh69-embedded-unit-strings.md) | #41 | WH69 unit strings ("knots", "W/m2") cause unavailable entities | MEDIUM | ✅ Fixed in v1.5.18 |
| [011](011-ws85-wind-sensors.md) | #20 | WS85 wind sensors missing | MEDIUM | 🔴 Open — awaiting user data |

## Recommended Implementation Order

1. **Spec 009 (WS90/GW2000)** — multiple root causes; fix `"89%"` parsing first, then investigate hardware_id mapping conflict
4. **Spec 011 (WS85)** — awaiting `get_sensors_info` data from user
5. **Spec 004 (GW1100 part)** — awaiting `get_sensors_info` + `get_livedata_info` JSON from a GW1100 user

## Limitations / Notes

- **Images viewable:** GitHub issue images can be downloaded with `curl -sL <url> -o /tmp/img.png` and read with the Read tool. Specs 003, 004, 006 have been updated with image findings.
- **No physical hardware:** All fixes are based on user-provided JSON dumps and logs. Mock data testing is the only validation path before user confirmation.
- **Sensor rename in v1.5.15:** `tf_ch` sensors renamed from "Soil Temperature CH{n}" to "Temperature CH{n}". Not a breaking change since no WH34 users had working entities before this release.
