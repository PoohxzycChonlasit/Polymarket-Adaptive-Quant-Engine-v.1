# REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_PLAN_001

## Verdict

PLAN_READY_FOR_EXECUTION

This is a design-only dependency move plan. No tool files, tests, runtime code, builders, backtests, paper runtime, live runtime, strategy, sizing, risk, execution, dashboard, Telegram, or `.env` files were modified.

## Preflight

| Check | Result |
| --- | --- |
| `git status --short` | clean at task start |
| `git branch -vv` | `main` tracking `origin/main` at `0a9a2ea` |
| Active workflow state read | yes |
| Active loop memory pointer | `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json` |
| AI repository bootstrap read | yes |
| Pytest run | no, out of scope for design task |
| Builders/backtests run | no, out of scope for design task |

## Dependency Map

Current source search:

```text
rg -n "from tools\.cross_run_lifecycle_truth|import tools\.cross_run_lifecycle_truth|tools\.cross_run_lifecycle_truth" tools tests polymarket -g "*.py"
```

| File | Current role | Reference type | Finding | Risk |
| --- | --- | --- | --- | --- |
| `tools/cross_run_lifecycle_truth.py` | Cross-run lifecycle truth report builder and CLI | implementation | Defines `build_cross_run_lifecycle_truth`, `write_cross_run_lifecycle_truth`, and CLI `main`. | MEDIUM_IMPORT_RISK |
| `tools/lifecycle_truth_backfill.py` | Lifecycle truth backfill report builder and CLI | direct import | Imports `DEFAULT_MEMORY_INDEX_DIR`, `build_cross_run_lifecycle_truth`, and `write_cross_run_lifecycle_truth` from `tools.cross_run_lifecycle_truth`. | MEDIUM_IMPORT_RISK |
| `tests/test_cross_run_lifecycle_truth.py` | Targeted test | direct import | Imports from `tools.cross_run_lifecycle_truth`; must update with the move. | LOW_PATH_RISK |
| `tests/test_lifecycle_truth_backfill.py` | Targeted test | direct import | Imports from `tools.lifecycle_truth_backfill`; must update if the backfill moves. | LOW_PATH_RISK |
| `tools/research_state_writer.py` | Research state index writer | filename prefix only | Searches for output files with prefix `cross_run_lifecycle_truth_`; no Python import of the module. No import update needed. | NO_IMPORT_RISK |
| `tests/test_research_state_writer.py` | Targeted research state test | fixture filename only | Creates a `cross_run_lifecycle_truth_*.json` fixture; no import update needed. | NO_IMPORT_RISK |
| `polymarket/` | Runtime trading package | none found | No runtime imports found. | NO_RUNTIME_RISK |

Historical docs and prior reports mention the old root paths. Those can remain as historical records unless they are active command examples or index entries. Current `FILE_INDEX.md`, `DOCUMENTATION_MAP.md`, and `README.md` did not show active references in the targeted search.

## Options Considered

| Option | Decision | Reason |
| --- | --- | --- |
| Move `cross_run_lifecycle_truth.py` alone and update imports | rejected | Leaves `lifecycle_truth_backfill.py` as a root-level replay tool importing a shadow module; the dependency remains split across old/new structure. |
| Move `cross_run_lifecycle_truth.py` plus `lifecycle_truth_backfill.py` together | selected | Keeps the implementation and direct importer migration cohesive, with clear targeted tests and no runtime imports. |
| Create wrapper at old path and move implementation | rejected | Preserves a stale root import surface and adds maintenance debt for a repository cleanup task. |
| Defer until broader lifecycle truth tool batch | rejected for now | Dependency surface is small enough for a controlled atomic execution task. |

## Selected Option

Move `cross_run_lifecycle_truth.py` and `lifecycle_truth_backfill.py` together in the next execution task.

This aligns with the target structure:

| Current path | Target path | Category |
| --- | --- | --- |
| `tools/cross_run_lifecycle_truth.py` | `tools/shadow/cross_run_lifecycle_truth.py` | shadow/cross-run analysis |
| `tools/lifecycle_truth_backfill.py` | `tools/replay/lifecycle_truth_backfill.py` | replay/lifecycle truth tooling |

## Reference Update Plan

Update only the direct imports and active references required by the move:

| File | Required update |
| --- | --- |
| `tools/replay/lifecycle_truth_backfill.py` | Change `from tools.cross_run_lifecycle_truth import (...)` to `from tools.shadow.cross_run_lifecycle_truth import (...)`. |
| `tests/test_cross_run_lifecycle_truth.py` | Change import to `from tools.shadow.cross_run_lifecycle_truth import (...)`. |
| `tests/test_lifecycle_truth_backfill.py` | Change import to `from tools.replay.lifecycle_truth_backfill import (...)`. |
| `FILE_INDEX.md` | Update only if active path entries for either tool are present at execution time. |
| `docs/operations/ACTIVE_WORKFLOW_STATE_001.json` | Update task/status notes for the execution task. |
| `docs/operations/TASK_QUEUE_001.json` | Mark the plan done and queue the execution task. |
| Active loop memory | Append execution outcome in the active loop memory file. |

Do not update historical reports, old graph query evidence, or prior task reports unless they contain active command examples that would mislead future operators.

## Validation Plan For Execution Task

Do not run full pytest. Do not run builders or backtests.

Run these focused checks after the future move:

```powershell
rg "tools\.cross_run_lifecycle_truth|tools\.lifecycle_truth_backfill" tools tests polymarket -g "*.py"
rg "tools/cross_run_lifecycle_truth.py|tools/lifecycle_truth_backfill.py" README.md FILE_INDEX.md DOCUMENTATION_MAP.md docs/operations docs/architecture docs/reports
.venv\Scripts\python.exe -m py_compile tools\shadow\cross_run_lifecycle_truth.py tools\replay\lifecycle_truth_backfill.py
.venv\Scripts\python.exe -m pytest tests\test_cross_run_lifecycle_truth.py tests\test_lifecycle_truth_backfill.py tests\test_research_state_writer.py -q
.venv\Scripts\python.exe -m json.tool docs\operations\ACTIVE_WORKFLOW_STATE_001.json
.venv\Scripts\python.exe -m json.tool docs\operations\TASK_QUEUE_001.json
.venv\Scripts\python.exe -m json.tool docs\operations\loop_memory\LOOP_MEMORY_20260628_001.json
git diff --check
git status --short
```

Expected reference-validation result:

- No active Python imports of `tools.cross_run_lifecycle_truth`.
- No active Python imports of `tools.lifecycle_truth_backfill`.
- Remaining old path mentions, if any, are historical docs or prior reports.
- No `polymarket/` references to either moved tool.

## Rollback Plan

If validation fails during the future execution task:

1. Move files back with `git mv`:
   - `tools/shadow/cross_run_lifecycle_truth.py` -> `tools/cross_run_lifecycle_truth.py`
   - `tools/replay/lifecycle_truth_backfill.py` -> `tools/lifecycle_truth_backfill.py`
2. Revert the targeted imports in tests and the backfill tool.
3. Revert active docs/index path updates made in the execution task.
4. Rerun py_compile on the restored root files.
5. Rerun the targeted pytest command.
6. Do not use `git reset --hard` without explicit operator approval.

## Final Recommendation

Proceed with:

```text
REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_001
```

as a Class 6 atomic tools migration with the paired move above.
