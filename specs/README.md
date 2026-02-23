# Ecowitt Local — Issue Specs

Kiro-style specs for open GitHub issues. Each spec has: requirements, design, tasks, and open questions.

## Status Overview

| Spec | Issue(s) | Title | Priority | Status |
|------|----------|-------|----------|--------|
| [004](004-wind-rain-hex-id-mapping.md) | #22, #23 | Wind/rain sensors unavailable (missing hardware_id mapping) | HIGH | ✅ Likely fixed — GW1100 data received, all hex IDs already supported; awaiting user confirmation on v1.5.25 |
| [011](011-ws85-wind-sensors.md) | #20 | WS85 wind sensors missing | MEDIUM | 🔴 Open — awaiting user data |
| [013](013-0x7c-24hour-rain-mislabeled.md) | #5 | 0x7C rain entity mislabeled "Daily Rain" (is 24-Hour Rain) | HIGH | ✅ Fixed in v1.5.26 — renamed to "24-Hour Rain", entity_id changed |
| [014](014-wh31-entities-under-gateway-device.md) | #19 | WH31 entities under gateway device, WH31 device empty | MEDIUM | 🔴 Open — awaiting `get_sensors_info` from affected user |
| [015](015-wh31-battery-binary.md) | #19 | WH31/WH69 battery binary conversion wrong | MEDIUM | ✅ Fixed in v1.5.26 — binary 0=100%, 1=10% for ch_aisle |
| [016](016-solar-lux-entity.md) | #84 | Solar illuminance (lux) entity missing | LOW | 🔴 Open — feature request, likely Option C (document gateway setting) |

## Waiting On

- **Spec 004 (GW1100)** — awaiting user confirmation that v1.5.25 resolves their issues
- **Spec 011 (WS85)** — need `get_sensors_info` data showing WS85 device type string
- **Spec 014** — need `get_sensors_info` from @AnHardt to confirm WH31 hardware_id
- **Spec 016** — need to clarify with user if gateway lux mode solves it

## Notes

- No physical hardware: all fixes are based on user-provided JSON dumps and logs. Mock data testing is the only validation path before user confirmation.
- Images in GitHub issues can be downloaded with `curl -sL <url> -o /tmp/img.png` and viewed with the Read tool.
