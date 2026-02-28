# Ecowitt Local — Issue Specs

Kiro-style specs for open GitHub issues. Each spec has: requirements, design, tasks, and open questions.

## Status Overview

| Spec | Issue(s) | Title | Priority | Status |
|------|----------|-------|----------|--------|
| [004](004-wind-rain-hex-id-mapping.md) | #22, #23 | Wind/rain sensors unavailable (missing hardware_id mapping) | HIGH | ✅ Partially fixed — WS80 (#23) fixed v1.5.15; GW1100 (#22) open — awaiting user data |
| [011](011-ws85-wind-sensors.md) | #20 | WS85 wind sensors missing | MEDIUM | 🔴 Open — awaiting user data |

## Waiting On

- **Spec 004 (GW1100)** — awaiting user data (`get_sensors_info` + `get_livedata_info` JSON from a GW1100 user)
- **Spec 011 (WS85)** — need `get_sensors_info` data showing WS85 device type string

## Notes

- No physical hardware: all fixes are based on user-provided JSON dumps and logs. Mock data testing is the only validation path before user confirmation.
- Images in GitHub issues can be downloaded with `curl -sL <url> -o /tmp/img.png` and viewed with the Read tool.
