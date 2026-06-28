# TRADER_REFACTOR_FIXTURE_BASELINE_REPAIR_001_CONTRACT_001

## Contract Metadata

| Field | Value |
| --- | --- |
| Contract id | `TRADER_REFACTOR_FIXTURE_BASELINE_REPAIR_001_CONTRACT_001` |
| Created at | 2026-06-29 |
| Bootstrap SHA | `46b6a12` |
| Bootstrap status | Clean worktree, `main` tracking `origin/main` |

## Task Identity

| Field | Value |
| --- | --- |
| Task id | `TRADER_REFACTOR_FIXTURE_BASELINE_REPAIR_001` |
| Task class | 5 |
| Description | Repair safe fixture/mock/setup failures from the remaining trader refactor baseline without changing production runtime behavior. |

## Allowed Files

- Failing test files under `tests/observability/` and `tests/polymarket/`
- `docs/reports/TRADER_REFACTOR_FIXTURE_BASELINE_REPAIR_001.md`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json`
- `docs/operations/execution_contracts/TRADER_REFACTOR_FIXTURE_BASELINE_REPAIR_001_CONTRACT_001.md`

## Forbidden Scope

- execution logic
- risk logic
- sizing logic
- strategy thresholds
- order submission
- wallet/balance behavior
- live/paper behavior
- `config/settings.py`
- `.env`

## Validation Plan

1. Re-run `tests/observability tests/polymarket` to capture the 12 remaining failures.
2. Classify each failure.
3. Apply only fixture/mock/test repairs.
4. Run exact repaired tests.
5. Run bounded broad subset again.
6. Validate changed Python/test files with `py_compile`.
7. Validate ops JSON and `git diff --check`.

## Verification Checklist

- [x] 12 baseline failures captured.
- [x] Failures classified.
- [x] Safe fixture/mock repairs applied only.
- [x] Exact repaired tests pass.
- [x] Broad bounded subset improves with no new failures.
- [x] Changed Python/test files compile.
- [x] Ops JSON validation passes.
- [x] `git diff --check` passes.
- [ ] Commit and push complete.
