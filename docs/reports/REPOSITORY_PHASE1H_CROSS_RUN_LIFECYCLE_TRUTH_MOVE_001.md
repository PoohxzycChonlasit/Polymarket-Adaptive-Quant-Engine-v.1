# REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_001

## Verdict

MIGRATION_PASS

Executed the approved paired move for cross-run lifecycle truth and lifecycle truth backfill tooling. No runtime trading code, `polymarket/`, strategy, sizing, risk, execution, live/paper behavior, dashboard, Telegram, `.env`, builders, backtests, paper runtime, or live runtime changed.

## Files Moved

| Old path | New path |
| --- | --- |
| `tools/cross_run_lifecycle_truth.py` | `tools/shadow/cross_run_lifecycle_truth.py` |
| `tools/lifecycle_truth_backfill.py` | `tools/replay/lifecycle_truth_backfill.py` |

## Tests Updated

| File | Update |
| --- | --- |
| `tools/replay/lifecycle_truth_backfill.py` | Changed cross-run import to `tools.shadow.cross_run_lifecycle_truth`. |
| `tests/test_cross_run_lifecycle_truth.py` | Changed import to `tools.shadow.cross_run_lifecycle_truth`. |
| `tests/test_lifecycle_truth_backfill.py` | Changed import to `tools.replay.lifecycle_truth_backfill`. |

## Reference Validation

Commands:

```powershell
rg "tools\.cross_run_lifecycle_truth|tools/cross_run_lifecycle_truth.py" . -g "!*.md" -g "!*.json"
rg "tools\.lifecycle_truth_backfill|tools/lifecycle_truth_backfill.py" . -g "!*.md" -g "!*.json"
```

Result:

| Check | Status |
| --- | --- |
| Old cross-run module/path references in active non-doc/non-JSON files | none |
| Old backfill module/path references in active non-doc/non-JSON files | none |
| `polymarket/` references | none |

Historical markdown and ops references were left intact unless they represented active task state.

## Compile Status

```powershell
.venv\Scripts\python.exe -m py_compile tools\shadow\cross_run_lifecycle_truth.py tools\replay\lifecycle_truth_backfill.py
```

Status: PASS.

## Tests Run

```powershell
.venv\Scripts\python.exe -m pytest tests\test_cross_run_lifecycle_truth.py tests\test_lifecycle_truth_backfill.py -q
```

Status: PASS, `6 passed in 0.83s`.

## Validation Notes

- Full pytest was not run.
- Builders were not run.
- Backtests were not run.
- Paper/live runtime was not run.
- This was a path/import migration only.

## Remaining Dependency Note

`tools/replay/lifecycle_truth_backfill.py` still imports `tools.lifecycle_truth_tables`. That root tool also has additional importers (`candidate_path_observability.py`, `candidate_continuity.py`, `ev_field_coverage.py`, and targeted tests), so it should be handled by a separate dependency-aware plan rather than expanded into this atomic move.

## Next Recommendation

```text
REPOSITORY_PHASE1I_LIFECYCLE_TRUTH_TABLES_MOVE_PLAN_001
```

Design a safe migration plan for `tools/lifecycle_truth_tables.py` and direct importers before moving it.
