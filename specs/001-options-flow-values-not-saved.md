# Spec 001: Options Flow — Values Not Saved After Edit

**GitHub Issues:** #50, #31
**Status:** Partially fixed (crash fixed in v1.5.11; save bug still open)
**Priority:** HIGH — all users on HA 2025.12+ are affected

---

## Background

Two layered bugs in `OptionsFlowHandler`:

1. **Crash (FIXED in v1.5.11):** `self.config_entry = config_entry` in `__init__` raised `AttributeError` because `config_entry` is a read-only property on the `OptionsFlow` base class since HA 2025.12. Fixed by removing the `__init__` entirely and returning `OptionsFlowHandler()` with no arguments.

2. **Values not saved (OPEN):** After the crash fix, the options form opens, but submitted values may not persist correctly. The handler reads current values from `self.config_entry.data` only, ignoring `self.config_entry.options`. If the user previously saved options, those values live in `.options` and `.data` has the original setup values. The form shows stale defaults.

---

## Requirements

- [ ] **REQ-001-1:** Options form must open without errors on HA 2025.12+
- [ ] **REQ-001-2:** Options form must show the **current effective values** — checking `.options` first, falling back to `.data`, then to defaults
- [ ] **REQ-001-3:** When the user clicks Submit, the new values must be saved and take effect on the next coordinator refresh cycle
- [ ] **REQ-001-4:** The coordinator must reload when options change (HA handles this via `async_reload_entry` triggered by options update)

---

## Design

### Current Broken Flow (before v1.5.11)

```
async_get_options_flow(config_entry)
  → OptionsFlowHandler(config_entry)   # CRASHES: read-only property
```

### Fixed Flow (v1.5.11+)

```
async_get_options_flow(config_entry)
  → OptionsFlowHandler()               # OK: base class provides self.config_entry

async_step_init():
  reads from self.config_entry.data    # BUG: ignores .options
  shows form with stale values
  on submit: async_create_entry(data=user_input)  # saves to .options
```

### Correct Flow

```python
def _get_option(self, key, default):
    """Read from options first, fall back to data, then default."""
    return self.config_entry.options.get(
        key, self.config_entry.data.get(key, default)
    )

async def async_step_init(self, user_input=None):
    if user_input is not None:
        return self.async_create_entry(title="", data=user_input)

    options_schema = vol.Schema({
        vol.Optional(CONF_SCAN_INTERVAL,
            default=self._get_option(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        ): vol.All(int, vol.Range(min=30, max=300)),
        ...
    })
```

### File to Change
- [config_flow.py](../custom_components/ecowitt_local/config_flow.py) — `OptionsFlowHandler.async_step_init`

---

## Tasks

- [ ] **TASK-001-1:** Add `_get_option()` helper to `OptionsFlowHandler` that reads `.options` → `.data` → default
- [ ] **TASK-001-2:** Replace the three `self.config_entry.data.get(...)` calls with `self._get_option(...)` calls
- [ ] **TASK-001-3:** Verify `async_create_entry(title="", data=user_input)` is correct (it saves to `.options`)
- [ ] **TASK-001-4:** Add/update test in `test_config_flow.py` to verify options are read from `.options` on second open
- [ ] **TASK-001-5:** Release and comment on issues #50 and #31

---

## Open Questions / Blockers

- None. Fix is well-understood and small.
