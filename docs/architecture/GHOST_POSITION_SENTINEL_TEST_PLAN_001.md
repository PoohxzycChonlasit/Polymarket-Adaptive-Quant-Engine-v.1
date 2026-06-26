# GHOST_POSITION_SENTINEL_TEST_PLAN_001

**Task:** GHOST_POSITION_SENTINEL_TEST_PLAN_001  
**Mode:** TEST PLANNING ONLY — no code changes  
**Date:** 2026-06-26  
**Scope:** Produce a complete test plan for the uncommitted Ghost Position Sentinel before implementation

---

## 1. Source Behavior Summary

### 1a. Methods Added / Modified (all in `utils/position_tracker.py`)

| Method | Line | What It Does |
|---|---|---|
| `PositionTracker.__init__()` | 112 | Added `self.runtime_session_id = ""` attribute |
| `set_runtime_session_id(session_id)` | 114–115 | Stores session_id on tracker; called by trader orchestrator on startup |
| `open_position()` | 171–175 | In paper mode: injects `runtime_session_id` and `owner_pid` into position metadata via `meta.setdefault()` (does not overwrite caller-supplied values) |
| `open_positions()` | 353–358 | Excludes positions where `status == "ghost"` OR `metadata["quarantined"] is True` |
| `closed_positions()` | 360–365 | Excludes positions where `status == "ghost"` OR `metadata["quarantined"] is True` |
| `ghost_positions()` | 367–372 | Returns positions where `status == "ghost"` OR `metadata["quarantined"] is True` |
| `run_sentinel_checks(current_run_id, active_owner, telemetry_emit)` | 677–828 | Startup-only scan: runs 8 detection criteria against all open positions, quarantines ghosts |

### 1b. Settings Added (in `config/settings.py` lines 223–227)

| Setting | Type | Default | Consumed? |
|---|---|---|---|
| `ghost_position_max_age` | `int` | `3600` | YES — `run_sentinel_checks()` line 706 |
| `ghost_position_quarantine_enabled` | `bool` | `True` | YES — `run_sentinel_checks()` line 707 |
| `ghost_position_allow_manual_restore` | `bool` | `False` | **NO** — defined but never referenced |

`ghost_position_max_age` is also added to the `validate_positive_int` validator.

### 1c. Sentinel Detection Logic — Exact Cascade

`run_sentinel_checks()` acquires `self._lock` for its **entire body** including telemetry callback invocations. The first matching criterion sets `ghost_reason`; subsequent guarded checks are skipped.

```
Checks 1–2: if / elif (mutually exclusive, first wins):
  1. OWNER_MISSING          pos.metadata.get("runtime_session_id") is falsy
  2. SESSION_MISMATCH       pos_session_id != current_run_id

Checks 3–8: each guarded by `if not ghost_reason`:
  3. UNKNOWN_LIFECYCLE      metadata.get("lifecycle_phase") missing or == "UNKNOWN"
  4. OWNER_RUNTIME_MISMATCH entry_time < active_owner["started_utc"]
  5. OWNER_RUNTIME_MISMATCH pos_session_id != active_owner.get("run_id")
  6. OWNER_MISSING          not active_owner or active_owner.get("status") != "active"
  7. STALE_POSITION         age_seconds > ghost_position_max_age (strict >, not >=)
  8. PID_DEAD               owner_pid present AND _default_process_checker(pid) == False
```

On ghost detection, if `quarantine_enabled`:
- `pos.status = "ghost"`
- `pos.metadata["quarantined"] = True`
- `pos.metadata["ghost_reason"] = ghost_reason`
- `pos.metadata["ghost_detected_at"] = <ISO UTC>`
- Emits `log_ghost_position_detected` telemetry

Regardless of quarantine state, emits `log_system_health` at end of scan.

### 1d. Lock Scope Warning

`run_sentinel_checks()` holds `self._lock` while invoking the `telemetry_emit` callback. Any telemetry callback that re-enters the tracker (e.g. calls `tracker.open_positions()`) will deadlock. Tests must use mock callbacks that do not call back into the tracker.

### 1e. `open_positions()` Logic Note

```python
if p.status == "open" and p.status != "ghost" and not (p.metadata or {}).get("quarantined") is True
```

The second condition `p.status != "ghost"` is logically redundant when the first condition `p.status == "open"` is true (a position cannot simultaneously be `"open"` and `"ghost"`). Ghost exclusion is effectively carried by the `quarantined` metadata check. This means:
- A position manually set to `status = "ghost"` is excluded
- A position with `metadata["quarantined"] = True` but `status = "open"` is ALSO excluded

Tests must cover both exclusion paths independently.

---

## 2. Test Coverage Gap

From `GHOST_POSITION_SENTINEL_ISOLATION_001.md` — zero tests exist for any of the following:

| Behavior | Coverage |
|---|---|
| `set_runtime_session_id()` sets attribute | NONE |
| `open_position()` injects `runtime_session_id` metadata in paper mode | NONE |
| `open_position()` injects `owner_pid` metadata in paper mode | NONE |
| `open_position()` does NOT inject metadata in live mode | NONE |
| `open_positions()` excludes ghost positions | NONE |
| `open_positions()` excludes quarantined-metadata positions | NONE |
| `closed_positions()` excludes ghost positions | NONE |
| `ghost_positions()` returns quarantined positions | NONE |
| `ghost_positions()` excludes normal positions | NONE |
| `run_sentinel_checks()` — OWNER_MISSING (no session_id) | NONE |
| `run_sentinel_checks()` — SESSION_MISMATCH | NONE |
| `run_sentinel_checks()` — UNKNOWN_LIFECYCLE (missing) | NONE |
| `run_sentinel_checks()` — UNKNOWN_LIFECYCLE (explicit "UNKNOWN") | NONE |
| `run_sentinel_checks()` — OWNER_RUNTIME_MISMATCH (time) | NONE |
| `run_sentinel_checks()` — OWNER_RUNTIME_MISMATCH (run_id) | NONE |
| `run_sentinel_checks()` — OWNER_MISSING (no active_owner) | NONE |
| `run_sentinel_checks()` — STALE_POSITION | NONE |
| `run_sentinel_checks()` — PID_DEAD | NONE |
| `run_sentinel_checks()` — quarantine_enabled=True applies status/metadata | NONE |
| `run_sentinel_checks()` — quarantine_enabled=False logs but does not mutate | NONE |
| `run_sentinel_checks()` — no open positions exits early | NONE |
| `run_sentinel_checks()` — telemetry callback invoked with correct payload | NONE |
| `run_sentinel_checks()` — multiple ghosts quarantined independently | NONE |
| `run_sentinel_checks()` — clean position not quarantined | NONE |
| `run_sentinel_checks()` — stale boundary (age == max_age) NOT ghost | NONE |

---

## 3. Test Matrix

### Group S — `run_sentinel_checks()` detection criteria

| Test ID | Target Function | Scenario | Setup | Expected Result | Priority |
|---|---|---|---|---|---|
| S-01 | `run_sentinel_checks` | OWNER_MISSING: no session_id in metadata | Open pos with no `runtime_session_id` in metadata; current_run_id="run-A" | `pos.status == "ghost"`, `metadata["ghost_reason"] == "OWNER_MISSING"`, `metadata["quarantined"] is True` | P0 |
| S-02 | `run_sentinel_checks` | SESSION_MISMATCH: session_id differs | Open pos with `runtime_session_id="run-OLD"`; current_run_id="run-NEW" | `ghost_reason == "SESSION_MISMATCH"`, position quarantined | P0 |
| S-03 | `run_sentinel_checks` | UNKNOWN_LIFECYCLE: lifecycle_phase missing | Open pos with matching session, no `lifecycle_phase` key | `ghost_reason == "UNKNOWN_LIFECYCLE"`, position quarantined | P0 |
| S-04 | `run_sentinel_checks` | UNKNOWN_LIFECYCLE: lifecycle_phase="UNKNOWN" | Open pos with matching session, `lifecycle_phase="UNKNOWN"` | `ghost_reason == "UNKNOWN_LIFECYCLE"`, position quarantined | P0 |
| S-05 | `run_sentinel_checks` | OWNER_RUNTIME_MISMATCH: entry time before owner start | pos session matches, lifecycle valid; `active_owner["started_utc"]` is 1hr after position entry_time | `ghost_reason == "OWNER_RUNTIME_MISMATCH"`, position quarantined | P1 |
| S-06 | `run_sentinel_checks` | OWNER_RUNTIME_MISMATCH: run_id mismatch | pos session matches current_run_id but `active_owner["run_id"]` differs; entry time OK | `ghost_reason == "OWNER_RUNTIME_MISMATCH"`, position quarantined | P1 |
| S-07 | `run_sentinel_checks` | OWNER_MISSING: no active_owner | active_owner=None; pos has matching session, valid lifecycle | `ghost_reason == "OWNER_MISSING"`, position quarantined | P1 |
| S-08 | `run_sentinel_checks` | OWNER_MISSING: active_owner status != "active" | active_owner=`{"run_id": run_id, "status": "stopped"}`; pos otherwise clean | `ghost_reason == "OWNER_MISSING"`, position quarantined | P1 |
| S-09 | `run_sentinel_checks` | STALE_POSITION: age > max_age | Use `ghost_position_max_age=10`; open pos with entry_time 20 seconds ago; owner active, pid alive | `ghost_reason == "STALE_POSITION"`, position quarantined | P0 |
| S-10 | `run_sentinel_checks` | NOT stale at exact boundary | Use `ghost_position_max_age=3600`; age exactly 3600s | `ghost_reason` is NOT `"STALE_POSITION"` (strict `>` boundary) | P0 |
| S-11 | `run_sentinel_checks` | PID_DEAD: owner pid process not running | Provide `owner_pid` in metadata; mock `_default_process_checker` returns False | `ghost_reason == "PID_DEAD"`, position quarantined | P1 |
| S-12 | `run_sentinel_checks` | CLEAN: all criteria pass | Current session, valid lifecycle, fresh entry, active owner with matching run_id, live pid | Position NOT quarantined, `status == "open"`, `metadata.get("quarantined")` not True | P0 |
| S-13 | `run_sentinel_checks` | quarantine_enabled=False | Ghost detected (OWNER_MISSING); `ghost_position_quarantine_enabled=False` | `pos.status` remains `"open"`, metadata NOT mutated, telemetry NOT emitted for `log_ghost_position_detected`? Actually re-read: telemetry IS emitted even when quarantine disabled (line 793–809). Status NOT changed. | P0 |
| S-14 | `run_sentinel_checks` | no open positions | Tracker has no positions at all | Method returns without error; if telemetry provided, `log_system_health` emitted with `ghost_positions_found=0` | P0 |
| S-15 | `run_sentinel_checks` | multiple ghosts | 3 open positions: 2 OWNER_MISSING, 1 clean | 2 quarantined, 1 remains open; telemetry emitted twice for ghost, once for health | P1 |
| S-16 | `run_sentinel_checks` | telemetry payload fields | OWNER_MISSING ghost detected | `log_ghost_position_detected` callback called; payload contains `position_id`, `ghost_reason`, `quarantined`, `age_seconds`, `action_taken`, `telemetry_scope="sentinel"` | P1 |

**S-13 correction:** Re-reading lines 793–809 in `run_sentinel_checks()` — the `telemetry_emit("log_ghost_position_detected", payload)` block is inside `if ghost_reason:` but NOT inside the `if quarantine_enabled:` block. So telemetry IS emitted regardless of quarantine state. When quarantine is disabled: status unchanged, metadata unchanged, telemetry still fires.

### Group F — Filter methods

| Test ID | Target Function | Scenario | Expected Result | Priority |
|---|---|---|---|---|
| F-01 | `open_positions()` | Position manually set to `status="ghost"` | Excluded from result | P0 |
| F-02 | `open_positions()` | Position with `status="open"` and `metadata["quarantined"]=True` | Excluded from result (quarantine metadata exclusion path) | P0 |
| F-03 | `open_positions()` | Normal open position, no ghost markers | Included in result | P0 |
| F-04 | `closed_positions()` | Position with `status="ghost"` | Excluded from result | P1 |
| F-05 | `closed_positions()` | Position with `status="closed"` and `metadata["quarantined"]=True` | Excluded from result | P1 |
| F-06 | `ghost_positions()` | Position with `status="ghost"` | Included | P0 |
| F-07 | `ghost_positions()` | Position with `metadata["quarantined"]=True` but `status="open"` | Included (dual path) | P0 |
| F-08 | `ghost_positions()` | Normal open position | Excluded | P0 |

### Group M — Metadata injection and session wiring

| Test ID | Target Function | Scenario | Expected Result | Priority |
|---|---|---|---|---|
| M-01 | `set_runtime_session_id()` | Call with "run-xyz" | `tracker.runtime_session_id == "run-xyz"` | P0 |
| M-02 | `open_position()` (paper) | `runtime_session_id` set on tracker | `position.metadata["runtime_session_id"] == tracker.runtime_session_id` | P0 |
| M-03 | `open_position()` (paper) | `runtime_session_id` empty string (not set) | `metadata["runtime_session_id"]` NOT injected; `metadata["owner_pid"]` IS injected | P0 |
| M-04 | `open_position()` (live) | `paper_trading=False` | Neither `runtime_session_id` nor `owner_pid` injected into metadata | P0 |
| M-05 | `open_position()` (paper) | Caller-supplied metadata already has `runtime_session_id` | `meta.setdefault()` preserves caller value — NOT overwritten by tracker value | P1 |

---

## 4. Exact Test Files

### Primary: `tests/test_ghost_position_sentinel.py` (new file)

Owns all 25+ sentinel tests (Groups S, F, M above). This keeps sentinel concerns entirely isolated from existing test files.

### Existing files — do NOT modify

| File | Why unchanged |
|---|---|
| `tests/test_position_tracker.py` | Covers basic PositionTracker behavior (open, close, PnL, risk gate, save/load). The `open_positions()` filter change is backward-compatible — existing tests never set `status="ghost"` or `metadata["quarantined"]=True`, so they remain green |
| `tests/test_position_reconciliation.py` | Covers `reconcile_inventory()`. No sentinel dependency. Calls `open_positions()` internally — passes because sentinel changes don't affect positions without ghost markers |
| `tests/test_execution_risk_controls.py` | No sentinel dependency |
| `tests/test_polymarket_trader.py` | No sentinel dependency |

### Existing tests to run before and after as regression check

```bash
python -m pytest tests/test_position_tracker.py -q
python -m pytest tests/test_position_reconciliation.py -q
python -m pytest tests/test_config_validation.py -q
```

All three must pass with no changes to confirm `open_positions()` / `closed_positions()` modifications are backward-compatible.

---

## 5. Test File Structure (non-code skeleton)

`tests/test_ghost_position_sentinel.py` should be organized as three test classes:

```
class SentinelDetectionTests(unittest.TestCase):
    # Group S: S-01 through S-16

class SentinelFilterTests(unittest.TestCase):
    # Group F: F-01 through F-08

class SentinelMetadataTests(unittest.TestCase):
    # Group M: M-01 through M-05
```

### Required test helpers (to be implemented)

```python
def _settings(paper=True, max_age=3600, quarantine=True):
    """Return SimpleNamespace with sentinel settings."""
    return SimpleNamespace(
        paper_trading=paper,
        account_balance=100.0,
        max_open_positions=10,
        max_total_exposure=1.0,
        max_daily_drawdown=0.10,
        ghost_position_max_age=max_age,
        ghost_position_quarantine_enabled=quarantine,
    )

def _tracker(paper=True, max_age=3600, quarantine=True):
    """Return PositionTracker with sentinel settings."""
    return PositionTracker(settings=_settings(paper, max_age, quarantine))

def _open_with_meta(tracker, metadata):
    """Open a position with specific metadata."""
    return tracker.open_position(
        symbol="pm-5m-btc",
        source="polymarket",
        side="BUY",
        entry_price=0.50,
        size=5.0,
        stop_loss=0.40,
        take_profit=0.60,
        order_id="test-order",
        metadata=metadata,
    )

def _active_owner(run_id="run-A", started_utc=None):
    """Return a valid active_owner dict."""
    # started_utc defaults to 10 minutes ago
    return {
        "run_id": run_id,
        "status": "active",
        "started_utc": (started_utc or datetime.now(tz=UTC) - timedelta(minutes=10)).isoformat(),
    }
```

### How to simulate STALE_POSITION (S-09)

`Position.entry_time` is set at creation to `datetime.now(UTC)`. To simulate an old position without sleeping:
- Open a position normally
- Manually override `pos.entry_time` to a past ISO timestamp after opening:
  ```python
  pos.entry_time = (datetime.now(tz=UTC) - timedelta(seconds=max_age + 1)).isoformat().replace("+00:00", "Z")
  ```

### How to mock PID_DEAD (S-11)

```python
with patch("utils.runtime_ownership._default_process_checker", return_value=False):
    tracker.run_sentinel_checks(...)
```

---

## 6. Minimum Acceptance Criteria

Tests that MUST pass before sentinel can be committed:

| # | Test ID(s) | What It Proves |
|---|---|---|
| 1 | S-01 | Core quarantine path works for OWNER_MISSING |
| 2 | S-02 | SESSION_MISMATCH detected and quarantined |
| 3 | S-03 or S-04 | UNKNOWN_LIFECYCLE detected and quarantined |
| 4 | S-09 | STALE_POSITION detected using `ghost_position_max_age` setting |
| 5 | S-10 | Boundary condition: `age == max_age` is NOT a ghost (strict `>`) |
| 6 | S-12 | Clean position is never quarantined (no false positive) |
| 7 | S-13 | `quarantine_enabled=False` suppresses mutation, permits telemetry |
| 8 | S-14 | No-op with zero open positions |
| 9 | F-01 | `open_positions()` excludes ghost-status position |
| 10 | F-02 | `open_positions()` excludes quarantine-metadata position |
| 11 | F-06 | `ghost_positions()` returns quarantined positions |
| 12 | M-01 | `set_runtime_session_id()` stores value |
| 13 | M-02 | Paper mode injects `runtime_session_id` into position metadata |
| 14 | M-04 | Live mode does NOT inject sentinel metadata |

14 tests minimum. Full suite (25 tests) is recommended.

---

## 7. Decision on `ghost_position_allow_manual_restore`

**Decision: REMOVE from `config/settings.py` before committing sentinel.**

### Evidence

1. Defined at `config/settings.py:226`: `ghost_position_allow_manual_restore: bool = False`
2. Grep across all `.py` files in the project returns exactly one match — the definition line. No consumer exists.
3. It is NOT in the `validate_positive_int` validator (a bool setting cannot be validated there, which is correct, but reinforces that no validator references it).
4. The `run_sentinel_checks()` method does not read this setting anywhere.
5. No method exists to restore a quarantined position to normal state.

### Why it must be removed, not merely documented

- The setting implies a capability that does not exist. Operators who see `ghost_position_allow_manual_restore=False` in a config file may believe setting it to `True` enables something — it does not.
- Writing a test that asserts `ghost_position_allow_manual_restore` exists in settings is a test with no behavioral assertion. It would test the presence of dead config.
- The field defaults to `False`, which is the safe fallback, so removal has zero behavioral impact on the running system.
- When a manual restore implementation is added in a future phase, the setting can be re-added alongside the consuming code in the same commit.

### Removal scope

Remove exactly one line from `config/settings.py`:
```python
ghost_position_allow_manual_restore: bool = False  # ← delete this line
```

No other changes needed. The remaining two sentinel settings (`ghost_position_max_age`, `ghost_position_quarantine_enabled`) are correctly wired and remain.

This removal should be part of the sentinel commit (alongside `config/settings.py` and `utils/position_tracker.py`), not a separate commit.

---

## 8. Integration Points — `tools/execution_paper_runtime.py`

The sentinel has **no integration dependency** on `tools/execution_paper_runtime.py`. The two changes in that file (empty `condition_id` guard at line 821, richer `ReconciliationError` message at line 916) are independent tool-side bug fixes for replay analysis. No sentinel tests are needed in that area.

`execution_paper_runtime.py` may be committed as a separate bugfix before, after, or alongside the sentinel — the sequencing does not matter.

---

## 9. Risks and Notes for Test Implementer

1. **Lock scope**: `run_sentinel_checks()` holds `self._lock` during all telemetry callback invocations. Mock callbacks passed to tests MUST NOT call any `PositionTracker` method (would deadlock). Use a simple list-append mock: `events = []; emit = lambda m, p: events.append((m, p))`.

2. **entry_time manipulation**: To test STALE_POSITION without sleeping, directly mutate `pos.entry_time` after calling `open_position()`. The `entry_time` field is a plain string on the dataclass.

3. **`getattr` fallback**: `run_sentinel_checks()` reads `ghost_position_max_age` and `ghost_position_quarantine_enabled` via `getattr(..., default)`. Tests using `SimpleNamespace` for settings must explicitly include these fields or the fallback defaults (3600 / True) will be used silently.

4. **Check cascade**: Tests for criteria 4–8 must set up positions that pass checks 1–3 first (matching session ID, valid lifecycle, entry time after owner start). Otherwise an earlier criterion fires and the intended criterion is never reached.

5. **`closed_positions()` uses `status != "open"` not `status == "closed"`**: Tests for F-04 and F-05 should close a position first (call `tracker.close_position()`), then manually set ghost markers to confirm exclusion.

6. **`ghost_positions()` dual path**: F-06 tests `status="ghost"` path; F-07 must separately test a position with `status="open"` and `metadata["quarantined"]=True` — this is the path used immediately after `run_sentinel_checks()` runs (the sentinel sets BOTH, but the filter catches EITHER).

---

## 10. Final Verdict

## `REMOVE_UNUSED_SETTING_FIRST`

**Reason:** The sentinel implementation is structurally complete and the test plan is fully specified. However, `ghost_position_allow_manual_restore` is a dead setting with no consumer anywhere in the codebase. Before implementing tests, this setting must be removed from `config/settings.py` so that:

1. No test is written to assert the presence of config that does nothing
2. The committed settings block accurately reflects the real sentinel capability set
3. The commit (`config/settings.py` + `utils/position_tracker.py`) arrives as coherent, complete work with no misleading config fields

**Sequence:**
1. Remove `ghost_position_allow_manual_restore: bool = False` from `config/settings.py`
2. Implement `tests/test_ghost_position_sentinel.py` per this plan (Groups S, F, M — 25 tests, 14 minimum)
3. Run regression checks: `test_position_tracker.py`, `test_position_reconciliation.py`, `test_config_validation.py`
4. Run new sentinel tests: `python -m pytest tests/test_ghost_position_sentinel.py -v`
5. Commit: `git add config/settings.py utils/position_tracker.py tests/test_ghost_position_sentinel.py`
6. Optionally commit `tools/execution_paper_runtime.py` separately as a tool bugfix

**Commit is blocked only by:** (a) unused setting removal + (b) sentinel tests written and green.
