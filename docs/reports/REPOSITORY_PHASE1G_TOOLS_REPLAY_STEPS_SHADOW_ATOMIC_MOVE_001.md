# REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001

## Final Verdict

MERGE_OK_ATOMIC_TOOLS_MOVE

The remaining semantic replay-step shadow tools were moved into `tools/shadow/` in one atomic batch. The batch updated targeted tests and `tools/multi_session_runner.py` module strings only. No runtime trading behavior changed.

## Discovery Summary

| Candidate | Current state before move | Target | References | Risk | Decision |
|---|---|---|---|---|---|
| `semantic_c_shadow_fill_replay.py` | root-level tool | `tools/shadow/` | targeted test + `multi_session_runner.py` module string | MEDIUM_PATH_RISK | MOVED |
| `semantic_c_shadow_pnl_truth.py` | root-level tool | `tools/shadow/` | targeted test + `multi_session_runner.py` module string | MEDIUM_PATH_RISK | MOVED |
| `semantic_c_inventory_continuity_replay.py` | root-level tool | `tools/shadow/` | targeted test + `multi_session_runner.py` module string | MEDIUM_PATH_RISK | MOVED |
| `cross_run_lifecycle_truth.py` | root-level tool | future target TBD | imported by `tools/lifecycle_truth_backfill.py` and targeted test | MEDIUM_IMPORT_RISK | DEFERRED |

Already moved before this task:

- `tools/shadow/semantic_c_bounded_reload_replay.py`
- `tools/shadow/semantic_c_shadow_observability_report.py`
- `tools/shadow/cross_run_ev_blindness.py`
- `tools/shadow/shadow_filter_evaluator.py`

## Files Moved

| Old path | New path |
|---|---|
| `tools/semantic_c_shadow_fill_replay.py` | `tools/shadow/semantic_c_shadow_fill_replay.py` |
| `tools/semantic_c_shadow_pnl_truth.py` | `tools/shadow/semantic_c_shadow_pnl_truth.py` |
| `tools/semantic_c_inventory_continuity_replay.py` | `tools/shadow/semantic_c_inventory_continuity_replay.py` |

## Files Deferred

| File | Reason |
|---|---|
| `tools/cross_run_lifecycle_truth.py` | Imported by `tools/lifecycle_truth_backfill.py`; should move in a dedicated cross-run/lifecycle batch with its importer and targeted tests. |

## Tests Updated

| Test file | Update |
|---|---|
| `tests/test_semantic_c_shadow_fill_replay.py` | Import path changed to `tools.shadow.semantic_c_shadow_fill_replay`. |
| `tests/test_semantic_c_shadow_pnl_truth.py` | Import path changed to `tools.shadow.semantic_c_shadow_pnl_truth`. |
| `tests/test_semantic_c_inventory_continuity_replay.py` | Import path changed to `tools.shadow.semantic_c_inventory_continuity_replay`. |
| `tests/test_multi_session_runner.py` | Expected module strings changed to `tools.shadow.*`. |

## Tool Updates

- `tools/multi_session_runner.py` REPLAY_STEPS module strings now point to `tools.shadow.*` for the three moved semantic replay-step tools.
- CLI examples inside the moved modules were updated to `python -m tools.shadow...`.

## Reference Validation

Old active Python module path scan:

```powershell
rg -n "tools\.semantic_c_shadow_fill_replay|tools\.semantic_c_shadow_pnl_truth|tools\.semantic_c_inventory_continuity_replay" -g "*.py"
```

Result: no active Python hits after import and runner updates.

Old file path scan:

```powershell
rg -n "tools/semantic_c_shadow_fill_replay\.py|tools/semantic_c_shadow_pnl_truth\.py|tools/semantic_c_inventory_continuity_replay\.py" .
```

Remaining hits are docs/ops/history/index references, including `FILE_INDEX.md`, prior reports, the graph query, and the execution contract. No active Python import path remains stale.

Deferred cross-run scan:

```powershell
rg -n "tools\.cross_run_lifecycle_truth|from tools import cross_run_lifecycle_truth|import tools\.cross_run_lifecycle_truth" -g "*.py" tools tests polymarket
```

Result:

- `tests/test_cross_run_lifecycle_truth.py`
- `tools/lifecycle_truth_backfill.py`

No `polymarket/` runtime import was found.

## Validation

| Check | Result |
|---|---|
| Preflight worktree | Clean on `main` before ops pointer repair |
| AIROS bootstrap | Clean after registering the operator-authorized atomic task in TASK_QUEUE |
| Graph query | DEGRADED because current task/HEAD are not in graph snapshot; fallback `rg` completed |
| py_compile | PASS for 3 moved files |
| Targeted pytest | PASS: 239 passed |
| Full pytest | Not run, out of scope |
| Builders/backtests | Not run, out of scope |
| Paper/live runtime | Not run, out of scope |

Targeted pytest command:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_semantic_c_shadow_fill_replay.py tests\test_semantic_c_shadow_pnl_truth.py tests\test_semantic_c_inventory_continuity_replay.py tests\test_multi_session_runner.py -q
```

## Boundary State

- No `polymarket/` files modified.
- No strategy, sizing, risk, execution, order submission, dashboard, Telegram, `.env`, paper/live behavior, builders, or backtests modified.
- `cross_run_lifecycle_truth.py` remains root-level and deferred to avoid mixing a cross-tool importer move into this replay-step batch.

## Next Task

REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_PLAN_001

Plan the move for `cross_run_lifecycle_truth.py` together with `lifecycle_truth_backfill.py` and their targeted tests.
