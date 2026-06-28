# TRADER_REFACTOR_TEST_PATH_FIX_001_CONTRACT_001

## Contract Metadata

| Field | Value |
| --- | --- |
| Contract id | `TRADER_REFACTOR_TEST_PATH_FIX_001_CONTRACT_001` |
| Created at | 2026-06-29 |
| Bootstrap SHA | `658fd41` |
| Bootstrap status | Clean worktree, `main` tracking `origin/main` |

## Task Identity

| Field | Value |
| --- | --- |
| Task id | `TRADER_REFACTOR_TEST_PATH_FIX_001` |
| Task class | 5 |
| Description | Fix three deterministic AST/source-path test failures from the trader refactor baseline. |

## Allowed Files

- `tests/observability/test_candidate_instance_shadow_propagation.py`
- `tests/polymarket/test_signal_identity.py`
- `tests/polymarket/test_signal_identity_propagation.py`
- `docs/reports/TRADER_REFACTOR_TEST_PATH_FIX_001.md`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json`
- `docs/operations/execution_contracts/TRADER_REFACTOR_TEST_PATH_FIX_001_CONTRACT_001.md`

## Forbidden Scope

- `polymarket/trader.py`
- runtime behavior
- strategy
- sizing
- risk
- execution
- wallet/balance
- live/paper behavior
- `config/settings.py`
- `.env`

## Failure Targets

| Test | Root cause |
| --- | --- |
| `tests/observability/test_candidate_instance_shadow_propagation.py::test_active_candidate_identity_is_copied_to_quant_detail_with_shadow_names_only` | `TRADER_PATH` points under `tests/polymarket/trader.py`. |
| `tests/polymarket/test_signal_identity.py::test_every_signal_result_producer_declares_canonical_identity_metadata` | `SIGNAL_PATH` points under `tests/polymarket/signal.py`. |
| `tests/polymarket/test_signal_identity_propagation.py::test_active_analysis_handoff_copies_signal_identity_into_quant_detail` | `TRADER_PATH` points under `tests/polymarket/trader.py`. |

## Validation Plan

1. Run exact failing tests before edits.
2. Update only the path constants to derive source files from imported module `__file__`.
3. Run exact failing tests after edits.
4. Run bounded broad subset:
   - `.venv\Scripts\python.exe -m pytest tests\observability tests\polymarket -q --tb=short -ra`
5. Validate ops JSON and `git diff --check`.

## Verification Checklist

- [x] Exact three target tests reproduced.
- [x] Test-only path fix applied.
- [x] Exact three target tests pass.
- [x] Broad bounded subset has three fewer failures and no new failures.
- [x] Ops JSON validation passes.
- [x] `git diff --check` passes.
- [ ] Commit and push complete.
