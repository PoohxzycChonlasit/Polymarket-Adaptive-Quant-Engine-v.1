# GHOST_POSITION_SENTINEL_ISOLATION_001

**Task:** GHOST_POSITION_SENTINEL_ISOLATION_001  
**Mode:** VERIFICATION ONLY — no code changes  
**Date:** 2026-06-26  
**Scope:** Isolate and classify Ghost Position Sentinel uncommitted work

---

## 1. polymarket/trader.py Status

**CLEAN — no uncommitted changes.**  
`git diff -- polymarket/trader.py` produced no output.  
Sentinel-related code in trader.py was committed in a prior session and is part of HEAD.

---

## 2. Files Belonging to Ghost Position Sentinel

### 2a. COMMITTED (already in HEAD)

| File | Evidence | What it provides |
|---|---|---|
| `polymarket/trader.py` | Line 599: `def run_ghost_position_sentinel(...)` | Sentinel orchestrator method; calls `self.tracker.set_runtime_session_id()` and `self.tracker.run_sentinel_checks()` |
| `polymarket/trader.py` | Line 630–639 | Reads ownership file, builds emit callback, calls tracker sentinel |
| `utils/quant_event_logger.py` | Line 77, 96, 114, 184–185 | `ghost_position_detected` event category wired in — file path, schema version `ghost_position_detected_v1`, priority CRITICAL, `log_ghost_position_detected()` method |

### 2b. UNCOMMITTED (dirty working tree)

| File | What it provides |
|---|---|
| `config/settings.py` | 3 sentinel settings: `ghost_position_max_age: int = 3600`, `ghost_position_quarantine_enabled: bool = True`, `ghost_position_allow_manual_restore: bool = False`; `ghost_position_max_age` added to `validate_positive_int` tuple |
| `utils/position_tracker.py` | `set_runtime_session_id()` method; `runtime_session_id` attribute; metadata injection (`runtime_session_id`, `owner_pid`) in `open_position()`; ghost filtering in `open_positions()` and `closed_positions()`; new `ghost_positions()` method; entire `run_sentinel_checks()` (~156 lines, 8 detection criteria) |

---

## 3. Files NOT Belonging to Ghost Position Sentinel

| File | Why not Sentinel |
|---|---|
| `tools/execution_paper_runtime.py` | Two changes: (1) early-reject empty `condition_id` on close events, (2) richer `ReconciliationError` message with file/line. Both are tool-side bug fixes for orphan-close replay, not sentinel logic. Could be committed separately or together. |
| `AGENTS.md` | Documentation update — not code |
| `CURRENT_PROJECT_STATUS.md` | Documentation update — not code |
| `PROJECT_RULES.md` | Documentation update — not code |
| `dashboard/*` (6 files) | Dashboard React work — unrelated |
| `runtime/research_exports/*` | Data files — not code |
| `tests/test_dashboard_state_aggregator.py` | Dashboard test — unrelated |
| `tools/dashboard_state_aggregator.py` | Dashboard tool — unrelated |

---

## 4. Dirty File Classification

| File | Status | Sentinel? | Notes |
|---|---|---|---|
| `config/settings.py` | M | YES | Sentinel settings block |
| `utils/position_tracker.py` | M | YES | Core sentinel implementation |
| `tools/execution_paper_runtime.py` | M | NO | Tool bug fixes (bundleable) |
| `AGENTS.md` | M | UNKNOWN | Not inspected — doc update |
| `CURRENT_PROJECT_STATUS.md` | M | UNKNOWN | Not inspected — doc update |
| `PROJECT_RULES.md` | M | UNKNOWN | Not inspected — doc update |
| `dashboard/*` | M | NO | Dashboard work |
| `runtime/research_exports/*` | M | NO | Data files |
| `tests/test_dashboard_state_aggregator.py` | M | NO | Dashboard test |
| `tools/dashboard_state_aggregator.py` | M | NO | Dashboard tool |
| `polymarket/trader.py` | CLEAN | N/A | Committed; sentinel method in HEAD |

---

## 5. Source Evidence

### Settings wiring (config/settings.py diff)

```python
# Added in uncommitted changes:
ghost_position_max_age: int = 3600
ghost_position_quarantine_enabled: bool = True
ghost_position_allow_manual_restore: bool = False  # ← DEFINED BUT NEVER CONSUMED (see §8)

# Added to validate_positive_int tuple:
"ghost_position_max_age",
```

### position_tracker.py — new methods added

```python
# New attribute + method (set_runtime_session_id):
self.runtime_session_id = ""
def set_runtime_session_id(self, session_id: str) -> None:
    self.runtime_session_id = session_id

# Modified open_position() — paper metadata injection:
meta = dict(metadata or {})
if self.settings.paper_trading:
    if getattr(self, "runtime_session_id", None):
        meta.setdefault("runtime_session_id", self.runtime_session_id)
    meta.setdefault("owner_pid", os.getpid())

# Modified open_positions() — ghost filter:
return [p for p in self._positions.values()
        if p.status == "open" and p.status != "ghost"
        and not (p.metadata or {}).get("quarantined") is True]

# Modified closed_positions() — ghost filter:
return [p for p in self._positions.values()
        if p.status != "open" and p.status != "ghost"
        and not (p.metadata or {}).get("quarantined") is True]

# New method:
def ghost_positions(self) -> list[Position]: ...

# New method (156 lines):
def run_sentinel_checks(self, current_run_id, active_owner, telemetry_emit) -> None:
    # 8 detection criteria:
    # 1. OWNER_MISSING (no runtime_session_id)
    # 2. SESSION_MISMATCH (session_id != current_run_id)
    # 3. UNKNOWN_LIFECYCLE (lifecycle_phase missing or UNKNOWN)
    # 4. OWNER_RUNTIME_MISMATCH (entry_time < owner start_utc)
    # 5. OWNER_RUNTIME_MISMATCH (pos session_id != owner run_id)
    # 6. OWNER_MISSING (active_owner absent or status != active)
    # 7. STALE_POSITION (age > ghost_position_max_age)
    # 8. PID_DEAD (owner_pid no longer alive)
    # → quarantine: pos.status = "ghost", metadata["quarantined"] = True
    # → emit log_ghost_position_detected + log_system_health
```

### trader.py committed sentinel orchestrator (lines 599–639)

```python
def run_ghost_position_sentinel(self, runtime_owner: Any | None = None) -> None:
    """Sentinel to scan and quarantine ghost paper positions on startup."""
    if not self.settings.paper_trading:
        return
    run_id = getattr(self.quant_events, "run_id", "") or ""
    # ... reads ownership file ...
    self.tracker.set_runtime_session_id(run_id)   # calls uncommitted method
    def emit_cb(event_method, payload): self._emit_quant_event(event_method, payload)
    self.tracker.run_sentinel_checks(              # calls uncommitted method
        current_run_id=run_id,
        active_owner=owner_dict,
        telemetry_emit=emit_cb,
    )
```

**`run_ghost_position_sentinel()` has no call site in main.py** — the method is defined and committed but never invoked. The AttributeError from the committed-but-uncompleted dependency would only trigger if explicitly called.

### quant_event_logger.py committed event (already in HEAD)

```python
# Line 77: "ghost_position_detected": "system_health"  ← JSONL file mapping
# Line 96: "ghost_position_detected": "ghost_position_detected_v1"  ← schema version
# Line 114: "ghost_position_detected": "CRITICAL"  ← priority
# Line 184: def log_ghost_position_detected(self, payload) → bool  ← method
```

---

## 6. Are Sentinel Settings Wired Correctly?

**YES, with one exception.**

- `ghost_position_max_age`: referenced in `run_sentinel_checks()` (position_tracker.py:706) via `getattr(self.settings, "ghost_position_max_age", 3600)` — correctly uses getattr fallback. Also added to `validate_positive_int` validator. **WIRED.**
- `ghost_position_quarantine_enabled`: referenced in `run_sentinel_checks()` (position_tracker.py:707) via `getattr(...)`. **WIRED.**
- `ghost_position_allow_manual_restore`: defined in settings.py but **NEVER REFERENCED** anywhere in the codebase (grep across all `.py` files returns only the definition line). This is a dead/planned field with no consumer. **NOT WIRED.**

---

## 7. Are Sentinel Routines Isolated in position_tracker.py?

**YES — well-isolated.**  
`run_sentinel_checks()` is a standalone method on `PositionTracker`. It takes all external dependencies (current_run_id, active_owner, telemetry_emit) as explicit parameters. The only internal import is `from utils.runtime_ownership import _default_process_checker` (lazy, inside a try/except) for PID liveness checks. No cross-layer calls at import time.

The ghost filtering in `open_positions()` / `closed_positions()` is self-contained — filters on `pos.status == "ghost"` and `pos.metadata.get("quarantined")`.

---

## 8. Does tools/execution_paper_runtime.py Depend on Sentinel?

**NO.** The two changes in `execution_paper_runtime.py` are:

1. **Empty condition_id guard** (line 821): Rejects close events with empty `condition_id` before processing. This is a general data quality fix, not sentinel-specific.
2. **Richer ReconciliationError message** (line 913): Adds `source_file:line_idx payload=...` to orphan_close errors. General debuggability improvement.

Neither references `ghost_position`, `sentinel`, `run_sentinel_checks`, or any sentinel concept. These changes can be committed with or without the sentinel commit.

---

## 9. Test Coverage Evidence

### Existing tests (not covering Sentinel)

| Test file | Covers |
|---|---|
| `tests/test_position_tracker.py` | 19 tests covering: risk gate, open_position tracking, close_position PnL, stop-loss/take-profit, save/load state |
| `tests/test_position_reconciliation.py` | 8 tests covering: flat/directional/hedged/live-cycle reconciliation states |
| `tests/test_position_manager.py` | Exists (not scanned in detail) |

### Ghost Sentinel test coverage

**ZERO.** Grep across all `tests/*.py` for `ghost_position`, `sentinel`, `run_sentinel_checks`, `ghost_positions`, `set_runtime_session_id` returns **no matches** (only `test_drift_audit.py` hit was an unrelated string literal).

### Risk: existing tests may surface regression

The modification to `open_positions()` changes the return contract — ghost/quarantined positions are now filtered out. Existing `test_position_tracker.py` tests that open positions and call `open_positions()` will continue to pass because they don't set `status = "ghost"` or `metadata["quarantined"] = True`. However, any test that relies on getting back ALL positions (including manually-set ghost/quarantined ones) would fail. No such test currently exists, so existing tests should remain green.

---

## 10. Is This Work Complete Enough to Commit?

**Structurally: YES. Tests: NO.**

The implementation is technically coherent:
- Settings block → position_tracker → trader orchestrator → event logger event handler is a complete wiring chain
- `run_sentinel_checks()` implements 8 detection criteria with quarantine and telemetry emission
- The only missing call site is in `main.py` (sentinel not yet wired into startup sequence), which is expected for a staged implementation

**Blockers:**
1. **No tests for any Sentinel behavior** — 8 detection criteria, quarantine state, ghost_positions() filter, set_runtime_session_id(), modified open_positions()/closed_positions() — zero coverage
2. **`ghost_position_allow_manual_restore` is a dead setting** — defined but never consumed. Either wire it or remove it before commit
3. **`run_ghost_position_sentinel()` has no call site in main.py** — the sentinel exists but is never invoked at startup. Whether this is by design (staged: implement first, wire to startup separately) or an oversight must be confirmed

---

## 11. Commit Readiness Verdict

## FINAL VERDICT: `NOT_READY_MISSING_TESTS`

**Reason:** The Sentinel implementation is self-contained and structurally sound, but has **zero test coverage** for any of its behavior. The 8 detection criteria (`OWNER_MISSING`, `SESSION_MISMATCH`, `UNKNOWN_LIFECYCLE`, `OWNER_RUNTIME_MISMATCH`, `STALE_POSITION`, `PID_DEAD`) are all untested. Quarantine state (`pos.status = "ghost"`, `metadata["quarantined"]`) is untested. The `ghost_positions()` filter is untested. There is also one unused setting (`ghost_position_allow_manual_restore`) with no consumer anywhere.

**NOT mixed with other work** — the Sentinel changes in settings.py and position_tracker.py are clean and exclusively Sentinel. The tool changes in execution_paper_runtime.py are NOT Sentinel and can be committed as a separate bugfix if desired.

---

## 12. Recommended Test Suite Before Commit

Tests that must pass (already exist, should remain green after changes):

```bash
python -m pytest tests/test_position_tracker.py -q
python -m pytest tests/test_position_reconciliation.py -q
python -m pytest tests/test_config_validation.py -q
```

Tests that **must be written** before commit:

| Test | Covers |
|---|---|
| `test_sentinel_owner_missing` | Position with no `runtime_session_id` → quarantined with `OWNER_MISSING` |
| `test_sentinel_session_mismatch` | Position with different `runtime_session_id` → quarantined with `SESSION_MISMATCH` |
| `test_sentinel_stale_position` | Position age > `ghost_position_max_age` → quarantined with `STALE_POSITION` |
| `test_sentinel_clean_position` | Current session, valid lifecycle → NOT quarantined |
| `test_sentinel_quarantine_disabled` | `ghost_position_quarantine_enabled=False` → ghost detected but not quarantined |
| `test_ghost_positions_filter` | Quarantined position excluded from `open_positions()`, included in `ghost_positions()` |
| `test_set_runtime_session_id` | `set_runtime_session_id()` populates `runtime_session_id` on tracker |
| `test_open_position_metadata_injection` | Paper mode injects `runtime_session_id` and `owner_pid` into position metadata |

Recommended new test file: `tests/test_ghost_position_sentinel.py`

---

## 13. Recommended Next Command Sequence

```bash
# Step 1: Confirm existing tests still green after position_tracker changes
python -m pytest tests/test_position_tracker.py -q
python -m pytest tests/test_position_reconciliation.py -q

# Step 2: Write tests/test_ghost_position_sentinel.py covering the 8 items above

# Step 3: Run new sentinel tests
python -m pytest tests/test_ghost_position_sentinel.py -v

# Step 4: Resolve ghost_position_allow_manual_restore — either wire it or remove it from settings.py

# Step 5 (optional, separate commit): Commit tools/execution_paper_runtime.py changes
#   git add tools/execution_paper_runtime.py
#   git commit -m "tools: improve orphan_close error message and missing condition_id guard"

# Step 6: Commit Sentinel when tests pass
#   git add config/settings.py utils/position_tracker.py
#   git commit -m "runtime: implement ghost position sentinel with quarantine and telemetry"
```

**Do NOT commit yet. Do NOT stash. Write sentinel tests first.**
