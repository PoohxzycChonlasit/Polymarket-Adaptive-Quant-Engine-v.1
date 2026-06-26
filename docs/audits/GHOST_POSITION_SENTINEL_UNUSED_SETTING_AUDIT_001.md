# GHOST_POSITION_SENTINEL_UNUSED_SETTING_AUDIT_001

**Task:** GHOST_POSITION_SENTINEL_UNUSED_SETTING_AUDIT_001  
**Mode:** VERIFICATION ONLY — no code changes  
**Date:** 2026-06-26  
**Scope:** Verify whether `ghost_position_allow_manual_restore` is truly unused and safe to remove

---

## 1. Verdict

## CONFIRMED_SAFE_TO_REMOVE

`ghost_position_allow_manual_restore` has exactly one occurrence in all `.py` files in the repository: its definition line at `config/settings.py:226`. No code in the project reads, checks, passes, or branches on this setting.

---

## 2. Check 1 — Direct Symbol Search

**Query:** All `.py` files for `ghost_position_allow_manual_restore`

```
config\settings.py:226:    ghost_position_allow_manual_restore: bool = False
```

**Result: 1 match — definition only.**

No other file (not `utils/position_tracker.py`, not `polymarket/trader.py`, not `tests/`, not `tools/`, not `main.py`) contains this string.

---

## 3. Check 2 — All `ghost_position_` References in Source

**Query:** All `.py` files for `ghost_position_`

Full match list (project source only):

| File | Line | Symbol | Type |
|---|---|---|---|
| `utils/quant_event_logger.py` | 77 | `ghost_position_detected` | Event category key |
| `utils/quant_event_logger.py` | 96 | `ghost_position_detected` | Schema version key |
| `utils/quant_event_logger.py` | 114 | `ghost_position_detected` | Priority key |
| `utils/quant_event_logger.py` | 184–185 | `log_ghost_position_detected()` | Telemetry method |
| `utils/position_tracker.py` | 695 | `ghost_position_sentinel_startup` | Event name string literal |
| `utils/position_tracker.py` | 706 | `ghost_position_max_age` | Setting read via `getattr` |
| `utils/position_tracker.py` | 707 | `ghost_position_quarantine_enabled` | Setting read via `getattr` |
| `utils/position_tracker.py` | 754 | `ghost_position_max_age` | Comment referencing setting |
| `utils/position_tracker.py` | 807 | `log_ghost_position_detected` | Telemetry callback call |
| `utils/position_tracker.py` | 821 | `ghost_position_sentinel_startup` | Event name string literal |
| `polymarket/trader.py` | 599 | `run_ghost_position_sentinel` | Method definition |
| `config/settings.py` | 224 | `ghost_position_max_age` | Setting definition |
| `config/settings.py` | 225 | `ghost_position_quarantine_enabled` | Setting definition |
| `config/settings.py` | 226 | `ghost_position_allow_manual_restore` | Setting definition |
| `config/settings.py` | 419 | `ghost_position_max_age` | Validator tuple entry |

**Findings:**

- `ghost_position_max_age` — appears at `position_tracker.py:706` (consumed). **WIRED.**
- `ghost_position_quarantine_enabled` — appears at `position_tracker.py:707` (consumed). **WIRED.**
- `ghost_position_allow_manual_restore` — appears only at `config/settings.py:226` (definition). **ZERO CONSUMERS.**

No occurrence of `ghost_position_allow_manual_restore` in any file other than its own definition line.

---

## 4. Check 3 — Dynamic Settings Enumeration

**Query:** All `.py` files for patterns that might dynamically access all settings fields without naming them:  
`model_dump | .dict() | getattr(.*settings | settings.__dict__ | vars(.*settings`

**Scope:** Project source files only (`.venv_BROKEN` library hits excluded as they are third-party code that does not touch `AppSettings`).

All project-owned hits:

| File | Pattern | What it does |
|---|---|---|
| `utils/telegram_alerts.py:39,41,866,894,895` | `getattr(settings, "telegram_*", default)` | Named field lookups only |
| `utils/quant_event_logger.py:136–143` | `getattr(settings, "quant_*", default)` | Named field lookups only |
| `utils/position_tracker.py:706–707` | `getattr(self.settings, "ghost_position_max_age", ...)` | Named field lookup |
| `utils/logger.py:333` | `getattr(settings, "telegram_enabled", ...)` | Named field lookup |
| `utils/config_validator.py:296` | `getattr(settings, "quant_data_enabled", ...)` | Named field lookup |
| `tests/test_shadow_filters.py:67` | `getattr(self._real_settings, name)` | Proxy forwarding — `name` must be supplied by caller, not self-discovered |
| `polymarket/trader.py:452,642,645,...` | `getattr(self.settings, "field_name", default)` | All named field lookups |
| `polymarket/client.py:342,430,...` | `getattr(self.settings, "field_name", default)` | All named field lookups |
| `main.py:363,364,369,370` | `getattr(settings, "field_name", default)` | All named field lookups |

**Findings:**

No project code calls `settings.model_dump()`, `settings.dict()`, `vars(settings)`, or `settings.__dict__` in a way that would enumerate every field on `AppSettings`. Every settings access pattern in the project names its target field explicitly. There is no dynamic discovery path that would silently consume `ghost_position_allow_manual_restore`.

The `tests/test_shadow_filters.py:67` `getattr(self._real_settings, name)` is a proxy that forwards named attribute access — callers must supply a specific attribute name. It is not a wildcard enumerator.

---

## 5. Markdown References

The string `ghost_position_allow_manual_restore` also appears in:

| File | Context |
|---|---|
| `GHOST_POSITION_SENTINEL_TEST_PLAN_001.md` | Documenting the removal decision |
| `GHOST_POSITION_SENTINEL_ISOLATION_001.md` | Prior audit noting the dead setting |
| `WORKING_TREE_CLEANUP_PLAN_001.md` | Earlier working tree audit |
| `WORKING_TREE_INTEGRITY_AUDIT_001.md` | Git diff snapshot |

All markdown references are documentation artifacts, not operational code. Removing the setting from `config/settings.py` does not require modifying these files (they describe historical state or planning decisions).

---

## 6. Summary Table

| Check | Question | Answer |
|---|---|---|
| Direct symbol search (`.py`) | Does any `.py` file reference `ghost_position_allow_manual_restore` other than its definition? | NO — 1 match total: definition only |
| `run_sentinel_checks()` | Does the sentinel implementation read this setting? | NO — reads `ghost_position_max_age` and `ghost_position_quarantine_enabled` only |
| `getattr` enumeration | Is there any getattr call that could silently reach this setting without naming it? | NO — all getattr calls in project code name the target field explicitly |
| `model_dump` / `dict()` | Does any code serialize all settings fields to a dict/JSON, potentially transmitting this setting? | NO — no `settings.model_dump()` or `settings.dict()` in project source |
| `vars()` / `__dict__` | Does any code iterate the settings namespace? | NO |
| Test coverage | Is there a test that asserts `ghost_position_allow_manual_restore` exists or has a value? | NO |
| Markdown references | Are markdown references operational? | NO — documentation only |

---

## 7. Exact Removal Scope

When the removal task is assigned, exactly one line must be deleted from `config/settings.py`:

```python
# Line 226 — delete this line:
ghost_position_allow_manual_restore: bool = False
```

No other file requires a change. The remaining two sentinel settings stay untouched:

```python
ghost_position_max_age: int = 3600             # keep — consumed at position_tracker.py:706
ghost_position_quarantine_enabled: bool = True  # keep — consumed at position_tracker.py:707
```

After removal, run:

```bash
python -m pytest tests/test_config_validation.py -q
```

to confirm the settings model loads cleanly and no validator references the removed field. (The `validate_positive_int` tuple at `config/settings.py:419` does not include `ghost_position_allow_manual_restore` — only `ghost_position_max_age` — so no validator cleanup is needed.)

---

## 8. Audit Trail

Commands run (read-only):

1. `Grep(pattern="ghost_position_allow_manual_restore", glob="*.py")` — 1 match
2. `Grep(pattern="ghost_position_", glob="*.py")` — full enumeration of all sentinel-prefixed symbols
3. `Grep(pattern="model_dump|\\.dict\\(\\)|getattr\\(.*settings|settings\\.__dict__|vars\\(.*settings", glob="*.py")` — full enumeration of dynamic settings access patterns

No files modified. No stash. No commit.
