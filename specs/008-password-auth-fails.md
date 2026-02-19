# Spec 008: Password Authentication Fails for GW2000 / GW3000

**GitHub Issue:** #43
**Status:** ✅ Fixed in v1.5.17
**Priority:** HIGH — any non-empty password prevents the integration from working at all

---

## Background

Users with GW2000 and GW3000 gateways report that the integration fails to connect whenever a password is entered. Removing the password (leaving it blank) allows the integration to connect and work normally.

From issue #43 comments:
- **@ShadowPeo (GW3000):** Any non-empty password fails; empty password works. Tested multiple passwords.
- **@Liozon (GW2000):** No password works; any password fails.
- **@Liozon (investigation):** *"The data endpoints (`/get_livedata_info`, `/get_sensors_info`, etc.) do NOT require authentication at all — only the WebUI does."*
- **@Pierre3dB:** Closing the Ecowitt app before connecting solved their issue (app was holding the connection — separate cause, not auth-related).

---

## Root Cause Analysis

### Empirically confirmed behaviour (GW1100A_V2.4.3)

Tested live against a GW1100A with password `test1234` set:

| Endpoint | No auth sent | Result |
|----------|-------------|--------|
| `GET /get_livedata_info` | — | **200 OK** — full data returned |
| `GET /get_sensors_info?page=1` | — | **200 OK** — full data returned |
| `GET /get_version` | — | **200 OK** — full data returned |
| `GET /get_units_info` | — | **200 OK** — full data returned |
| `POST /set_login_info` pwd=base64(test1234) | — | **500 Server Error** |

**The data endpoints are completely open** — the gateway password setting does not gate local API access at all.
**`/set_login_info` crashes the gateway with HTTP 500** for this firmware — it is not a valid API auth endpoint.

### What the code currently does

`get_live_data()` (line 213):
```python
async def get_live_data(self) -> Dict[str, Any]:
    if not self._authenticated and self._password:
        await self.authenticate()   # ← called only when password is set
    data = await self._make_request("/get_livedata_info")
```

`authenticate()` POSTs to `/set_login_info`. When the gateway returns 500, the code raises `ConnectionError("Authentication failed: HTTP 500")` and the data request never happens.

### The problem

The failure chain for users who enter any password:
1. Code calls `POST /set_login_info` with base64-encoded password
2. Gateway returns **500 Server Error**
3. `authenticate()` raises `ConnectionError`
4. Data request never executes
5. Integration fails to load

**The correct behaviour:** never call `/set_login_info`. The data endpoints require no authentication regardless of the gateway password setting.

---

## Requirements

- [ ] **REQ-008-1:** Integration must successfully connect and fetch data when a password is configured
- [ ] **REQ-008-2:** Password field must remain in config flow (some users may need it for future use cases or different firmware)
- [ ] **REQ-008-3:** No regression for passwordless setups

---

## Design

### Fix: Remove authentication call from data endpoint methods

The data endpoints don't need auth. Remove the `authenticate()` guard from `get_live_data()`, `get_sensor_mapping()`, `get_version()`, and `get_units()`:

```python
# BEFORE
async def get_live_data(self) -> Dict[str, Any]:
    if not self._authenticated and self._password:
        await self.authenticate()
    data = await self._make_request("/get_livedata_info")

# AFTER
async def get_live_data(self) -> Dict[str, Any]:
    data = await self._make_request("/get_livedata_info")
```

Apply the same change to `get_sensor_mapping()`, `get_version()`, `get_units()`.

The `authenticate()` method and `/set_login_info` call can remain in the codebase for potential future use (e.g., if a future firmware version adds real API auth), but must not be called automatically before data requests.

### Config flow impact

The password field in the config flow should remain but its behaviour changes:
- Password is stored in config entry
- It is **not** used for data endpoint authentication
- If Ecowitt ever adds real API authentication, the stored password is available

Alternatively: add a note in the config flow description that the password field is currently unused (the local data API requires no authentication).

### Files to Change
- [api.py](../custom_components/ecowitt_local/api.py) — remove `authenticate()` pre-call from all data methods
- [tests/test_api.py](../tests/test_api.py) — update auth tests to reflect new behavior

---

## Tasks

- [ ] **TASK-008-1:** Remove `authenticate()` pre-call from `get_live_data()`, `get_sensor_mapping()`, `get_version()`, `get_units()`
- [ ] **TASK-008-2:** Update tests to verify data endpoints work without calling `/set_login_info`
- [ ] **TASK-008-3:** Verify `test_connection()` still works (it already skips auth)
- [ ] **TASK-008-4:** Release and comment on issue #43

---

## Open Questions

- **Does any Ecowitt firmware require auth on data endpoints?** Confirmed no on GW1100A_V2.4.3. No user has ever reported a 401/403 from a data endpoint. The password field was implemented speculatively and has never been needed.
- **Should the password field be removed from config flow?** It is a no-op. Could be removed in a future major version to avoid user confusion. For now, keep it stored but unused.
- **Is `/set_login_info` ever valid?** Unknown. It may be a web UI session endpoint that only makes sense in a browser context (with CSRF tokens, redirects, etc.). It is not suitable for programmatic API use.
