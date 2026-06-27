# RUNTIME_LOG_GOVERNANCE_POLICY_CORRECTION_001

**Date:** 2026-06-27 · **Tier:** LOOP Class 4 · **Repairs:** 0

## Policy Mismatch Summary

The original `N>5` rotated backup policy produced **0 DELETE candidates** because all log files use `backupCount=5` (N max=5). The 1.6 GB comes from **299 old session log groups** from PIDs that are no longer running — some from May 2026 (50 days old).

**Corrected policy:** Parse session timestamp and PID from filename `polytrade_bot_YYYYMMDD_HHMMSS_PID.log[.N]`. Delete all files in a session group if age > 7 days AND PID is not running.

---

## Code Changes

| File | Changes |
|------|---------|
| `tools/flaos/log_governance.py` | +`import re`, `+import datetime`; +`SESSION_LOG_RETENTION_DAYS=7`; +`_SESSION_LOG_RE` regex; +`_parse_session_log_name()`; +`_get_running_pids()`; +`collect_old_session_log_groups()`; updated `cmd_inspect/plan/dry_run/execute` |
| `tests/test_flaos_log_governance.py` | +9 new tests for parsing, collection, metadata, integration |

---

## Test Results

**28/28 pass** (was 18, now 28 — 10 new tests added).

| New tests | What verified |
|-----------|-------------|
| `test_parse_base/rotated_log_filename` | Correct metadata extraction |
| `test_malformed_filename_returns_none` | Safe ignore of non-matching names |
| `test_old_non_running_session_is_delete_candidate` | Core policy |
| `test_recent_session_is_kept` | Age boundary |
| `test_running_pid_session_is_kept` | PID guard |
| `test_action_metadata_includes_session_fields` | Required metadata fields |
| `test_plan_includes_session_group_candidates` | Integration |
| `test_dry_run_with_session_groups_does_not_mutate` | Safety |
| `test_hard_cap_respected_with_session_groups` | Cap still enforced |

---

## Real Plan/Dry-Run Summary

```
plan:
  total_actions: 862 (capped at 800)
  estimated_reclaim_mb: 1,423.6
  unique_sessions: 232 (age 11–50 days)
  action types: DELETE:old_session_group (800 within cap)

dry-run:
  mode: DRY_RUN
  session_guard: PASS
  total_actions: 800
  status: all DRY_RUN (0 mutations)
  JSONL DELETE actions: 0
```

---

## Safety Confirmation

| Check | Result |
|-------|--------|
| JSONL never DELETEd | 0 JSONL DELETE actions ✓ |
| Hard cap ≤ 800 | 800 ✓ |
| Dry-run = 0 mutations | Confirmed ✓ |
| Session guard | PASS ✓ |
| Session metadata in all actions | session_key, pid, age_days, session_date ✓ |
| No execute --confirm run | Confirmed — dry-run only ✓ |

---

## Next Recommendation

**`RUNTIME_LOG_GOVERNANCE_CORRECTED_DRY_RUN_REVIEW_001`** — GATE tier Class 2.

Human review of the 800 DELETE action plan (1.4 GB) before execution. Confirm:
- Sessions targeted are 11–50 days old (May–June 2026)
- 232 unique session keys (232 trading sessions from completed runs)
- All targeted PIDs have exited
- No critical logs would be lost

After review, authorize `execute --confirm` to reclaim ~1.4 GB.

## Final Verdict

```
RUNTIME_LOG_GOVERNANCE_POLICY_CORRECTION_COMMITTED
```
