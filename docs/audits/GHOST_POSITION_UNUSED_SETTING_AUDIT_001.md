# GHOST_POSITION_UNUSED_SETTING_AUDIT_001

**Task:** GHOST_POSITION_SENTINEL_UNUSED_SETTING_AUDIT_001  
**Mode:** VERIFICATION ONLY — no code changes  
**Date:** 2026-06-26  
**Scope:** Verify whether `ghost_position_allow_manual_restore` is truly unused and safe to remove

---

## 1. Final Verdict

## `SAFE_TO_REMOVE`

`ghost_position_allow_manual_restore` has exactly one occurrence in all `.py` files: its definition at `config/settings.py:226`. No other file reads, checks, passes, or branches on it.

---

## 2. Q1 — Where is it defined?

**`config/settings.py:226`**

```python
# ── Ghost Position Sentinel ──────────────────────────────────────────────
ghost_position_max_age: int = 3600             # line 224
ghost_position_quarantine_enabled: bool = True  # line 225
ghost_position_allow_manual_restore: bool = False   # line 226  ← subject
```

`ghost_position_allow_manual_restore` is NOT added to `validate_positive_int` (that tuple at line 419 includes only `ghost_position_max_age`). It has no validator, no alias, no default-override.

---

## 3. Q2 — Is it referenced outside `config/settings.py`?

**No.**

**Evidence — grep across all `.py` files:**

```
config\settings.py:226:    ghost_position_allow_manual_restore: bool = False
```

One match total. No other `.py` file in the project contains this string.

---

## 4. Q3 — Is it consumed dynamically?

**No.**

### `getattr` pattern scan

All `getattr(settings, ...)` calls in project source name their target field explicitly:

| File | Pattern example |
|---|---|
| `utils/position_tracker.py:706–707` | `getattr(self.settings, "ghost_position_max_age", 3600)` |
| `utils/position_tracker.py:706–707` | `getattr(self.settings, "ghost_position_quarantine_enabled", True)` |
| `polymarket/trader.py` (many) | `getattr(self.settings, "specific_field_name", default)` |
| `utils/telegram_alerts.py` | `getattr(settings, "telegram_*", default)` |

Neither `position_tracker.py` nor any other file contains `getattr(..., "ghost_position_allow_manual_restore", ...)`.

### `model_dump` / `dict()` scan

No project code calls `settings.model_dump()`, `settings.dict()`, `vars(settings)`, or `settings.__dict__` in a way that would enumerate all fields on `AppSettings`. All `model_dump`/`dict()` hits are in `.venv_BROKEN` (third-party library code that does not interact with `AppSettings`).

### `test_shadow_filters.py:67` proxy

```python
return getattr(self._real_settings, name)
```

This forwards named attribute access — the caller must supply a specific `name`. It is not an enumerator and will not auto-discover `ghost_position_allow_manual_restore` unless explicitly called with that string, which no test does.

---

## 5. Q4 — Is it required by tests?

**No.**

No file under `tests/` references `ghost_position_allow_manual_restore`:

```
# grep result across tests/*.py for "ghost_position_allow_manual_restore"
# → 0 matches
```

The existing test suite (`test_position_tracker.py`, `test_position_reconciliation.py`, `test_config_validation.py`, `test_execution_risk_controls.py`, `test_polymarket_trader.py`) does not assert its presence, value, or behavior.

---

## 6. Q5 — Is it documented as future behavior?

**Only in documentation artifacts — not in source code comments or docstrings.**

| File | Context |
|---|---|
| `GHOST_POSITION_SENTINEL_TEST_PLAN_001.md` | Documents it as "dead config, remove before commit" |
| `GHOST_POSITION_SENTINEL_ISOLATION_001.md` | Labels it "DEFINED BUT NEVER CONSUMED" |
| `WORKING_TREE_INTEGRITY_AUDIT_001.md` | Shows it in a git diff snapshot |
| `WORKING_TREE_CLEANUP_PLAN_001.md` | Lists it as a known sentinel setting |

No source file (`position_tracker.py`, `trader.py`, `main.py`, any other `.py`) contains a comment referencing `ghost_position_allow_manual_restore` as planned or future behavior. Its definition line has no inline comment indicating intent.

---

## 7. Q6 — Does removing it affect Sentinel behavior?

**No.**

The sentinel behavior chain is:

```
config/settings.py → position_tracker.run_sentinel_checks() → quarantine + telemetry
```

`run_sentinel_checks()` reads exactly two settings:
- `ghost_position_max_age` at line 706 via `getattr(..., 3600)`
- `ghost_position_quarantine_enabled` at line 707 via `getattr(..., True)`

Neither of these is affected by removing `ghost_position_allow_manual_restore`. The sentinel's 8 detection criteria, quarantine state transitions, telemetry emission, and startup orchestration are all independent of this setting.

---

## 8. Q7 — Should it be removed, documented, or implemented?

**Removed.**

Arguments for each option:

| Option | Assessment |
|---|---|
| **REMOVE** | Setting implies a non-existent capability. Operators who see `ghost_position_allow_manual_restore=False` may believe toggling it to `True` enables something — it does not. Retaining it is actively misleading. |
| **DOCUMENT** | Inline comments or docstrings saying "future feature" are acceptable only if implementation is imminent. No implementation plan exists. Documenting a permanently inert setting wastes operator attention. |
| **IMPLEMENT NOW** | No consuming code exists. Implementing manual restore requires adding: (a) restore method to `PositionTracker`, (b) auth check, (c) audit log event, (d) CLI or API entry point, (e) tests. This is a separate feature scope, not part of the current sentinel commit. |

**Decision: REMOVE.** When a manual restore feature is implemented, the setting can be re-added in the same commit as the consuming code.

---

## 9. Risk Assessment

| Risk | Likelihood | Severity | Notes |
|---|---|---|---|
| Removal breaks a running consumer | **NONE** | N/A | Zero references in source — no running path reaches this field |
| Removal breaks a test | **NONE** | N/A | No test asserts its presence or value |
| Removal breaks import chain | **NONE** | N/A | Pydantic `BaseSettings` — removing a field does not break other field definitions |
| `.env` file sets `GHOST_POSITION_ALLOW_MANUAL_RESTORE=true` at runtime | **LOW** | **LOW** | Even if set, Pydantic ignores env vars for unknown fields (extra fields are ignored by default in BaseSettings). No behavior change. Operator is informed by settings.py source. |
| Config serialization includes the field | **NONE** | N/A | No code serializes all settings fields |

**No credible risk path exists for this removal.**

---

## 10. Exact Removal Scope

One line from `config/settings.py`:

```python
ghost_position_allow_manual_restore: bool = False  # ← delete only this line
```

No other file requires a change. The `validate_positive_int` tuple at line 419 does not include this setting, so no validator cleanup is needed.

---

## 11. Source Evidence Summary

| Evidence type | Result |
|---|---|
| `.py` search for `ghost_position_allow_manual_restore` | 1 match: definition only at `config/settings.py:226` |
| `run_sentinel_checks()` reads this setting? | NO — reads `ghost_position_max_age` and `ghost_position_quarantine_enabled` only |
| Any `getattr` call for this field? | NO |
| Any `model_dump` / `dict()` on `AppSettings`? | NO |
| Any test asserting this field? | NO |
| Any source comment marking it "future"? | NO |
| Risk of breakage on removal? | NONE |
