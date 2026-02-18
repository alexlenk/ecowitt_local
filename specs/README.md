# Ecowitt Local — Issue Specs

Kiro-style specs for open GitHub issues. Each spec has: requirements, design, tasks, and open questions.

## Status Overview

| Spec | Issue(s) | Title | Priority | Status |
|------|----------|-------|----------|--------|
| [001](001-options-flow-values-not-saved.md) | #50, #31 | Options flow values not saved after edit | HIGH | ✅ Fixed in v1.5.12 |
| [002](002-rain-sensor-state-class.md) | #32, #45 | Rain entities missing `state_class` | HIGH | ✅ Fixed in v1.5.13 |
| [003](003-temperature-double-conversion.md) | #19, #13 | Temperature double-conversion for Celsius gateways | HIGH | Open — approach chosen, needs impl |
| [004](004-wind-rain-hex-id-mapping.md) | #22, #23 | Wind/rain sensors unavailable (missing hardware_id mapping) | HIGH | Open — WS80 fix designed; GW1100 needs data |
| [005](005-wh77-multi-sensor-station.md) | #12 | WH77 Multi-Sensor Station — no entities | MEDIUM | Open — fix is clear, ready to implement |
| [006](006-wh34-pool-temperature.md) | #16 | WH34 pool temperature — no entities | MEDIUM | Open — needs WH34 sensor_info data |

## Recommended Implementation Order

1. **Spec 001** — 30 min, no blockers, all users on HA 2025.12+ affected
2. **Spec 005** — 1 hr, no blockers, identical to WH90 fix pattern
3. **Spec 002** — 2 hrs, trace coordinator first then fix sensor.py
4. **Spec 003** — 3 hrs, complex unit handling, dependency for Spec 006
5. **Spec 004** — 2 hrs for WS80, blocked for GW1100 pending user data
6. **Spec 006** — 2 hrs, depends on Spec 003 for unit handling

## Limitations / Notes

- **Images viewable:** GitHub issue images can be downloaded with `curl -sL <url> -o /tmp/img.png` and read with the Read tool. Specs 003, 004, 006 have been updated with image findings.
- **No physical hardware:** All fixes are based on user-provided JSON dumps and logs. Mock data testing is the only validation path before user confirmation.
- **Breaking changes:** Spec 003 (temp keys) and Spec 006 (sensor rename) may change entity IDs for existing users — requires migration consideration.
