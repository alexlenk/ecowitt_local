# Ecowitt Local — Issue Specs

Kiro-style specs for open GitHub issues. Each spec has: requirements, design, tasks, and open questions.

## Status Overview

| Spec | Issue(s) | Title | Priority | Status |
|------|----------|-------|----------|--------|
| [004](004-wind-rain-hex-id-mapping.md) | #22, #23 | Wind/rain sensors unavailable (missing hardware_id mapping) | HIGH | ✅ Partially fixed — WS80 (#23) fixed v1.5.15; GW1100 (#22) open — awaiting user data |
| [011](011-ws85-wind-sensors.md) | #20 | WS85 wind sensors missing | MEDIUM | 🔴 Open — awaiting user data |
| [013](013-0x7c-24hour-rain-mislabeled.md) | #5 | 0x7C rain entity mislabeled "Daily Rain" (is 24-Hour Rain) | HIGH | ✅ Fixed in v1.5.26 — renamed to "24-Hour Rain", entity_id changed |
| [014](014-wh31-entities-under-gateway-device.md) | #19 | WH31 entities under gateway device, WH31 device empty | MEDIUM | ✅ Likely fixed — user confirmed WH31 shows correctly (v1.5.x) |
| [015](015-wh31-battery-binary.md) | #19 | WH31/WH69 battery binary conversion wrong | MEDIUM | ✅ Fixed in v1.5.28 — binary 0→100%, 1→10% for ch_aisle |
| [016](016-solar-lux-entity.md) | #84 | Solar illuminance (lux) entity missing | LOW | ✅ Fixed in v1.5.29 — computed lux entity (W/m² × 126.7) |
| [017](017-battery-level-attribute-bug.md) | #90 | battery_level attribute shows raw bar value | HIGH | ✅ Fixed in v1.5.30 — user confirmed; issue #90 closed |
| [018](018-wh57-lightning-strikes-missing.md) | #19 | WH57 lightning strikes and timestamp entities missing | HIGH | ✅ Fixed in v1.5.31 — entity_id collision resolved |
| [019](019-0x10-daily-rain-mislabeled.md) | #5 | 0x10 rain entity mislabeled "Hourly Rain" (is Daily Rain) | MEDIUM | ✅ Fixed in v1.5.33 — renamed to "Daily Rain", entity_id changed |

## Waiting On

- **Spec 004 (GW1100)** — awaiting user data (`get_sensors_info` + `get_livedata_info` JSON from a GW1100 user)
- **Spec 011 (WS85)** — need `get_sensors_info` data showing WS85 device type string
- **Spec 015** — need user data to confirm if `0x13` rain battery and WH34 `ch_temp` battery use binary encoding

## Notes

- No physical hardware: all fixes are based on user-provided JSON dumps and logs. Mock data testing is the only validation path before user confirmation.
- Images in GitHub issues can be downloaded with `curl -sL <url> -o /tmp/img.png` and viewed with the Read tool.
