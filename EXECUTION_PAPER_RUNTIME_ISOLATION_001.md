# EXECUTION_PAPER_RUNTIME_ISOLATION_001

**Task:** EXECUTION_PAPER_RUNTIME_ISOLATION_001  
**Mode:** VERIFICATION ONLY — no code changes  
**Date:** 2026-06-26  
**Scope:** Isolate and classify the uncommitted change in `tools/execution_paper_runtime.py`

---

## 1. Final Verdict

## `READY_TO_COMMIT_TOOL_FIX`

The change is a 5-line, two-fix defensive patch to an offline replay tool. It has zero relationship to Ghost Position Sentinel, dashboard work, or runtime execution. Both changes are already covered by existing tests (39/39 pass). Safe to commit independently.

---

## 2. Diff Summary

```
tools/execution_paper_runtime.py | 5 ++++-
1 file changed, 4 insertions(+), 1 deletion(-)
```

**Full diff:**

```diff
@@ -818,6 +818,9 @@ def run_replay(
                         elif is_close:
+                        if condition_id == "":
+                            trigger_reject("missing_condition_id")
+                            continue
                         exit_price = payload.get("exit_price")

@@ -910,7 +913,7 @@ def run_replay(
                         if not open_pos:
-                            raise ReconciliationError("orphan_close")
+                            raise ReconciliationError(f"orphan_close at {source_file}:{line_idx} payload={payload}")
```

### Fix 1 — Empty `condition_id` guard (lines 821–823, +3 lines)

On close events, if `condition_id == ""`, the replay now calls `trigger_reject("missing_condition_id")` and `continue`s to the next event. Without this guard, a close event with an empty `condition_id` would proceed into the reconciliation path and eventually fail with an ambiguous error.

**Behavior change:** Early reject with explicit `reject_reason="missing_condition_id"` instead of falling through to a later failure. Emits an `execution_paper_reject` event to the journal.

### Fix 2 — Richer orphan_close error message (line 913, 1 line changed)

```python
# Before:
raise ReconciliationError("orphan_close")

# After:
raise ReconciliationError(f"orphan_close at {source_file}:{line_idx} payload={payload}")
```

**Behavior change:** None — still raises `ReconciliationError`. Only the error message is richer, adding file name, line index, and payload for debuggability.

---

## 3. Q1 — What exactly changed?

Two independent defensive fixes inside `run_replay()`:

| Fix | Location | What | Why |
|---|---|---|---|
| 1 | Line 821–823 | Early-reject close events with `condition_id == ""` | Prevents ambiguous downstream failure on malformed JSONL close events |
| 2 | Line 913 | Add `source_file:line_idx payload=...` to `ReconciliationError` message | Makes orphan_close errors debuggable — previously the error had no context about which file/line caused it |

---

## 4. Q2 — Is the change runtime-affecting or offline-tool-only?

**Offline-tool-only.** `tools/execution_paper_runtime.py` is never imported by any runtime module.

**Evidence — reference scan across all `.py` files:**

```
tools\execution_paper_runtime.py   → self-references (event type strings)
tests\test_execution_paper_runtime.py → 25 import lines (test file only)
```

No file in `polymarket/`, `utils/`, `config/`, `main.py`, or any other runtime module imports `execution_paper_runtime`. This is consistent with the CLAUDE.md constraint:

> "Offline tools are evidence only. Replay outputs and analyzer reports must not be wired into automatic runtime decisions."

Both fixes are in `run_replay()` — a function called only by the CLI entry point or directly in tests. No path exists from runtime execution to this code.

---

## 5. Q3 — Is it related to Ghost Position Sentinel?

**No.**

**Evidence — grep for sentinel concepts inside `tools/execution_paper_runtime.py`:**

```
pattern: ghost_position|sentinel|dashboard_state|aggregator
result: No matches found
```

The sentinel commit (`701fee67`) staged `config/settings.py` and `utils/position_tracker.py`. `execution_paper_runtime.py` was not part of that commit and shares no code with sentinel. The GHOST_POSITION_SENTINEL_ISOLATION_001.md audit explicitly classified execution_paper_runtime.py changes as "NOT Sentinel — tool bug fixes."

---

## 6. Q4 — Is it related to dashboard state aggregator?

**No.**

The grep for `dashboard_state|aggregator` inside `tools/execution_paper_runtime.py` returned zero matches. The dashboard-related dirty files (`tools/dashboard_state_aggregator.py`, `tests/test_dashboard_state_aggregator.py`, `dashboard/*`) are separate and have no connection to replay functionality.

---

## 7. Q5 — Is it safe to commit independently?

**Yes.**

- The two fixes are self-contained within `run_replay()` — no interface changes, no new public API.
- No other module imports this file.
- Fix 1 (`missing_condition_id`) is already tested at `test_execution_paper_runtime.py:366`.
- Fix 2 (richer `ReconciliationError` message) is covered by two existing tests at lines 174 and 497, both using `pytest.raises(ReconciliationError, match="orphan_close")`. The `match` argument is a regex pattern — `"orphan_close"` matches as a substring of the new richer message `"orphan_close at {source_file}:{line_idx} payload={...}"`. Both tests continue to pass.
- 39/39 tests pass.

---

## 8. Q6 — What tests cover this file?

**`tests/test_execution_paper_runtime.py`** — 39 tests.

Tests that directly cover the two changed behaviors:

| Test | Line | Changed behavior covered |
|---|---|---|
| Unnamed test containing `assert rows[0]["reject_reason"] == "missing_condition_id"` | ~366 | Fix 1: empty condition_id early-reject |
| `test_reconciliation_orphan_close_fails()` | 166–175 | Fix 2: ReconciliationError still raised with `orphan_close` prefix |
| Second `pytest.raises(ReconciliationError, match="orphan_close")` | 497 | Fix 2: same validation, different JSONL fixture |

---

## 9. Q7 — What tests should run before commit?

Minimum (already verified passing):

```bash
python -m pytest tests/test_execution_paper_runtime.py -q
# 39 passed in 2.18s
```

Optional regression (unrelated to this file, but clean):

```bash
python -m pytest tests/ -q --ignore=tests/test_dashboard_state_aggregator.py
```

---

## 10. Q8 — Does it block Batch 1?

**No.** This change touches only one file: `tools/execution_paper_runtime.py`. Batch 1 involves repository organisation and documentation moves. There is no dependency between this tool fix and Batch 1 work.

---

## 11. Ownership Classification

| Attribute | Value |
|---|---|
| File type | Offline analysis tool |
| Runtime dependency | None — not imported by any runtime module |
| Sentinel relationship | None |
| Dashboard relationship | None |
| Risk level | LOW |
| Diff size | 5 lines changed (4 insertions, 1 deletion) |
| Test coverage | FULL — both behaviors already covered by 39-test suite |
| Commit independence | YES — no other dirty file depends on this |

---

## 12. Recommended Action

**Commit independently as a tool bugfix:**

```bash
git add tools/execution_paper_runtime.py
git commit -m "tools: guard orphan_close on empty condition_id and improve error message"
```

Also include `EXECUTION_PAPER_RUNTIME_ISOLATION_001.md` in the same commit as documentation:

```bash
git add tools/execution_paper_runtime.py EXECUTION_PAPER_RUNTIME_ISOLATION_001.md
git commit -m "tools: guard orphan_close on empty condition_id and improve error message"
```

**Required pre-commit check:**

```bash
python -m pytest tests/test_execution_paper_runtime.py -q
```

Expected: 39 passed.
