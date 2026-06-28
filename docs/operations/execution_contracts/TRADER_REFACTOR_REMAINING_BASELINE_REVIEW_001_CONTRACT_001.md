# TRADER_REFACTOR_REMAINING_BASELINE_REVIEW_001_CONTRACT_001

## Contract Metadata

| Field | Value |
| --- | --- |
| Contract id | `TRADER_REFACTOR_REMAINING_BASELINE_REVIEW_001_CONTRACT_001` |
| Created at | 2026-06-29 |
| Bootstrap SHA | `cbcef4d` |
| Bootstrap status | Clean worktree, `main` tracking `origin/main` |

## Task Identity

| Field | Value |
| --- | --- |
| Task id | `TRADER_REFACTOR_REMAINING_BASELINE_REVIEW_001` |
| Task class | 5 |
| Description | Review and repair the final two remaining bounded trader refactor baseline failures with strict runtime safety boundaries. |

## Allowed Files

- `tests/observability/test_candidate_instance_shadow_propagation.py`
- `tests/polymarket/test_stale_feed_kill_switch.py`
- `polymarket/observability/trader_decision_diagnostics.py` for observability-only identity propagation repair
- `polymarket/trader.py` only if a proven production guard/initialization fix is required and non-execution/non-risk/non-sizing semantics are preserved
- AIROS repository registry files only if production/module code changes
- `docs/reports/TRADER_REFACTOR_REMAINING_BASELINE_REVIEW_001.md`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json`
- `docs/operations/execution_contracts/TRADER_REFACTOR_REMAINING_BASELINE_REVIEW_001_CONTRACT_001.md`

## Forbidden Scope

- order submission semantics
- risk logic
- sizing logic
- strategy thresholds
- wallet/balance behavior
- live execution behavior
- `config/settings.py`
- `.env`
- paper/live runtime launch
- full pytest

## Validation Plan

1. Reproduce the exact two failing tests.
2. Classify each failure.
3. Trace root cause before patching.
4. Apply only safe fixture/observability/guard repairs.
5. Run exact repaired tests.
6. Run bounded subset `tests/observability tests/polymarket`.
7. If production code changes, run `py_compile polymarket\trader.py` and refresh AIROS registries.
8. Validate changed Python/test files, ops JSON, active loop memory, and `git diff --check`.

## Verification Checklist

- [x] Exact two failures reproduced.
- [x] Candidate identity root cause classified.
- [x] `selected_token_id` root cause classified.
- [x] Safe scoped repairs applied only.
- [x] Exact repaired tests pass.
- [x] Bounded subset has no new failures.
- [x] Changed Python files compile.
- [x] AIROS registries refreshed if production code changed.
- [x] Ops JSON validation passes.
- [x] Active loop memory validation passes.
- [x] `git diff --check` passes.
- [ ] Commit and push complete.
