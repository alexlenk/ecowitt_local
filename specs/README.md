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

## Recommended Implementation Order

1. **Spec 004 (GW1100 part)** — awaiting `get_sensors_info` + `get_livedata_info` JSON from a GW1100 user

## Limitations / Notes

- **Images viewable:** GitHub issue images can be downloaded with `curl -sL <url> -o /tmp/img.png` and read with the Read tool. Specs 003, 004, 006 have been updated with image findings.
- **No physical hardware:** All fixes are based on user-provided JSON dumps and logs. Mock data testing is the only validation path before user confirmation.
- **Sensor rename in v1.5.15:** `tf_ch` sensors renamed from "Soil Temperature CH{n}" to "Temperature CH{n}". Not a breaking change since no WH34 users had working entities before this release.
