# REPOSITORY_PHASE1B_TOOLS_LOW_PATH_RISK_MOVE_PLAN_001

## Final Verdict

FINAL_VERDICT: DESIGN_COMPLETE_MOVE_NOT_STARTED

Phase 1B should use a small outcome-truth batch: the three provisional free-source outcome tools. Do not move the full outcome-truth group yet.

No files were moved. No pytest, builders, backtests, paper runtime, or live runtime commands were run.

## Preflight

| Check | Result |
|---|---|
| `git status --short` | Clean at preflight. |
| `git branch -vv` | `main 6a33fec [origin/main: ahead 3] refactor: move no-risk probe tool into probes folder` |
| `git log -n 3 --oneline` | `6a33fec`, `c5fc3aa`, `00af48b` |
| Full pytest | Not run by design-only scope. |
| Builders/backtests | Not run by design-only scope. |

## Source Docs Reviewed

- `docs/reports/REPOSITORY_PHASE1_TOOLS_AUDIT_REORGANIZATION_001.md`
- `docs/architecture/TOOLS_STRUCTURE_TARGET_001.md`
- `DOCUMENTATION_MAP.md`
- `docs/PROJECT_CLEANUP_REPORT.md`

## Selected Batch

SELECTED_BATCH: `outcome_truth/provisional_free_source_trio`

Reason:

- All three files were classified `LOW_PATH_RISK`.
- They have no active ops references.
- They have no docs command examples outside historical/structure docs.
- They have direct targeted tests that can be updated and run without full pytest.
- They are cohesive: provisional outcome classification, join, and readiness.
- They avoid the larger official-resolution/outcome-truth group, which has more internal ownership and should move later.

## Move List

| Current path | Proposed path | Category | Risk | Test refs | Docs refs | Ops refs | Import refs | CLI command examples |
|---|---|---|---|---:|---:|---:|---:|---|
| `tools/free_outcome_truth_provisional.py` | `tools/outcome_truth/free_outcome_truth_provisional.py` | outcome_truth | LOW_PATH_RISK | 2 active refs in one test file | Historical/structure only | 0 | 1 test import | No active examples found |
| `tools/free_outcome_truth_provisional_join.py` | `tools/outcome_truth/free_outcome_truth_provisional_join.py` | outcome_truth | LOW_PATH_RISK | 1 active ref in one test file | Historical/structure only | 0 | 1 test import | No active examples found |
| `tools/free_outcome_truth_provisional_readiness.py` | `tools/outcome_truth/free_outcome_truth_provisional_readiness.py` | outcome_truth | LOW_PATH_RISK | 2 active refs in one test file | Historical/structure only | 0 | 1 test import | No active examples found |

## Reference Update Plan

### Tests To Update

| Test file | Current reference | New reference |
|---|---|---|
| `tests/test_free_outcome_truth_provisional.py` | `from tools.free_outcome_truth_provisional import ...` | `from tools.outcome_truth.free_outcome_truth_provisional import ...` |
| `tests/test_free_outcome_truth_provisional.py` | `Path("tools/free_outcome_truth_provisional.py")` | `Path("tools/outcome_truth/free_outcome_truth_provisional.py")` |
| `tests/test_free_outcome_truth_provisional_join.py` | `from tools.free_outcome_truth_provisional_join import ...` | `from tools.outcome_truth.free_outcome_truth_provisional_join import ...` |
| `tests/test_free_outcome_truth_provisional_readiness.py` | `from tools.free_outcome_truth_provisional_readiness import ...` | `from tools.outcome_truth.free_outcome_truth_provisional_readiness import ...` |
| `tests/test_free_outcome_truth_provisional_readiness.py` | `Path("tools/free_outcome_truth_provisional_readiness.py")` | `Path("tools/outcome_truth/free_outcome_truth_provisional_readiness.py")` |

### Docs To Treat As Historical

Do not rewrite historical audit records during the move phase unless they are active operator instructions:

- `docs/reports/REPOSITORY_PHASE1_TOOLS_AUDIT_REORGANIZATION_001.md`
- `docs/reports/REPOSITORY_FOLDER_REORGANIZATION_AUDIT_001.md`
- `docs/architecture/REPOSITORY_STRUCTURE_TARGET_001.md`

### Ops References

No active references were found in:

- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- root entrypoint docs checked by the plan scan

The execution task should update ops only to mark task state/report metadata, not because these tools are active ops dependencies.

### Import References

Only tests import these modules:

- `tests/test_free_outcome_truth_provisional.py`
- `tests/test_free_outcome_truth_provisional_join.py`
- `tests/test_free_outcome_truth_provisional_readiness.py`

No imports from runtime, `polymarket/`, `utils/`, dashboard, Telegram, or config were found.

### CLI Command Examples

No active CLI command examples were found for these three scripts. They expose `argparse` entrypoints, so manual invocation after move should use:

```powershell
python tools\outcome_truth\free_outcome_truth_provisional.py --evidence-path <path> --output-dir <dir>
python tools\outcome_truth\free_outcome_truth_provisional_join.py --population-manifest <path> --provisional-outcomes <path> --output-dir <dir>
python tools\outcome_truth\free_outcome_truth_provisional_readiness.py --joined-outcomes <path> --output-dir <dir>
```

Package invocation, if used, should be:

```powershell
python -m tools.outcome_truth.free_outcome_truth_provisional --evidence-path <path> --output-dir <dir>
python -m tools.outcome_truth.free_outcome_truth_provisional_join --population-manifest <path> --provisional-outcomes <path> --output-dir <dir>
python -m tools.outcome_truth.free_outcome_truth_provisional_readiness --joined-outcomes <path> --output-dir <dir>
```

## Execution Plan For Next Task

Recommended next task: `REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001`

Allowed execution-phase changes:

- Create `tools/outcome_truth/`
- Move the three selected scripts into `tools/outcome_truth/`
- Update only the three targeted test files listed above
- Write execution report under `docs/reports/`
- Update docs/operations state, queue, and loop memory

Forbidden execution-phase changes:

- No runtime code
- No strategy, sizing, risk, execution, order submission, live/paper behavior
- No dashboard or Telegram changes
- No `.env` changes
- No broad documentation rewrite
- No full outcome-truth category move

## Validation Plan

Run after the move:

```powershell
rg "tools/free_outcome_truth_provisional.py|tools\.free_outcome_truth_provisional|free_outcome_truth_provisional" .
rg "tools/free_outcome_truth_provisional_join.py|tools\.free_outcome_truth_provisional_join|free_outcome_truth_provisional_join" .
rg "tools/free_outcome_truth_provisional_readiness.py|tools\.free_outcome_truth_provisional_readiness|free_outcome_truth_provisional_readiness" .
```

Expected:

- No active old path references in tests.
- No old module imports in tests.
- Remaining hits are historical docs/structure records, report filenames, schema constants, or new `tools.outcome_truth.*` references.

Compile moved files only:

```powershell
.venv\Scripts\python.exe -m py_compile tools\outcome_truth\free_outcome_truth_provisional.py
.venv\Scripts\python.exe -m py_compile tools\outcome_truth\free_outcome_truth_provisional_join.py
.venv\Scripts\python.exe -m py_compile tools\outcome_truth\free_outcome_truth_provisional_readiness.py
```

Targeted tests only because imports change:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_free_outcome_truth_provisional.py tests\test_free_outcome_truth_provisional_join.py tests\test_free_outcome_truth_provisional_readiness.py -q
```

Also validate:

```powershell
git diff --name-status
git status --short
.venv\Scripts\python.exe -m json.tool docs\operations\ACTIVE_WORKFLOW_STATE_001.json
.venv\Scripts\python.exe -m json.tool docs\operations\TASK_QUEUE_001.json
.venv\Scripts\python.exe -m json.tool docs\operations\loop_memory\LOOP_MEMORY_20260628_001.json
```

Do not run:

- Full pytest
- Builders
- Backtests
- Paper runtime
- Live runtime

## Rollback Plan

If validation fails due to path/import issues:

```powershell
git mv tools\outcome_truth\free_outcome_truth_provisional.py tools\free_outcome_truth_provisional.py
git mv tools\outcome_truth\free_outcome_truth_provisional_join.py tools\free_outcome_truth_provisional_join.py
git mv tools\outcome_truth\free_outcome_truth_provisional_readiness.py tools\free_outcome_truth_provisional_readiness.py
```

Then revert the three test import/path updates and rerun:

```powershell
.venv\Scripts\python.exe -m py_compile tools\free_outcome_truth_provisional.py
.venv\Scripts\python.exe -m py_compile tools\free_outcome_truth_provisional_join.py
.venv\Scripts\python.exe -m py_compile tools\free_outcome_truth_provisional_readiness.py
.venv\Scripts\python.exe -m pytest tests\test_free_outcome_truth_provisional.py tests\test_free_outcome_truth_provisional_join.py tests\test_free_outcome_truth_provisional_readiness.py -q
```

If the failure is from unrelated historical docs references, do not roll back; document why the reference is historical.

## Final Recommendation

Proceed with `REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001` as a Class 6 low-risk refactor. Keep it to exactly three files plus their targeted tests and docs/operations/reporting artifacts.

## TASK_OUTPUT_CONTRACT

### Task Identity
- Task name: REPOSITORY_PHASE1B_TOOLS_LOW_PATH_RISK_MOVE_PLAN_001
- Task class: 2
- Agent roles used: PRIMARY=24_REPOSITORY_LIBRARIAN_AGENT SUPPORTING=07_TEST_CI_AGENT

### Files Changed
- `docs/reports/REPOSITORY_PHASE1B_TOOLS_LOW_PATH_RISK_MOVE_PLAN_001.md` - design-only move plan.
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json` - workflow state update.
- `docs/operations/TASK_QUEUE_001.json` - plan task completion and next task queue entry.
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json` - loop memory entry.

### Files Read (Not Changed)
- `docs/reports/REPOSITORY_PHASE1_TOOLS_AUDIT_REORGANIZATION_001.md` - source move matrix and risk classification.
- `docs/architecture/TOOLS_STRUCTURE_TARGET_001.md` - target tools structure and phased migration rules.
- `DOCUMENTATION_MAP.md` - docs routing and structure context.
- `docs/PROJECT_CLEANUP_REPORT.md` - cleanup policy context.
- `tools/free_outcome_truth_provisional.py` - import and CLI surface inspection.
- `tools/free_outcome_truth_provisional_join.py` - import and CLI surface inspection.
- `tools/free_outcome_truth_provisional_readiness.py` - import and CLI surface inspection.
- `tests/test_free_outcome_truth_provisional.py` - active references.
- `tests/test_free_outcome_truth_provisional_join.py` - active references.
- `tests/test_free_outcome_truth_provisional_readiness.py` - active references.

### Tests Run
- Command: NOT_REQUIRED by design-only scope; no pytest, builders, or backtests were run.
- Result: NOT_REQUIRED
- Pre-existing failures: NONE OBSERVED

### Evidence
- [Grade A] `git status --short` was clean at preflight.
- [Grade A] `git branch -vv` showed `main 6a33fec [origin/main: ahead 3]`.
- [Grade B] Audit docs classify the selected scripts as `LOW_PATH_RISK`.
- [Grade B] Source and search inspection found only targeted tests import these modules.
- [Grade D] Plan aligns with target structure and docs routing policy.

### Remaining Uncertainty
- Historical docs may intentionally retain old paths. The execution task must classify remaining `rg` hits instead of blindly rewriting historical records.

### Commits Made
- NONE

### Active Question Status
- OPEN: LOW_PRICE_TRUTH_RESOLUTION_001; unchanged.

### Batch 2 Authorization
- NOT AUTHORIZED

### Recommended Next Task
- REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001
