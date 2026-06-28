# AIROS Migration Analyzer and Patch Planner

**Task:** `AIROS_MIGRATION_ANALYZER_AND_PATCH_PLANNER_001`  
**Task Class:** 4 TOOLING  
**Date:** 2026-06-28  
**Status:** ✅ PASS

---

## Summary

Implemented `tools/airos/migration_analyzer.py` — a pre-move intelligence scanner that reads `batch_candidates.json` and produces `migration_patch_plan.json` identifying every rewriting and patching requirement before any file is relocated.

Also upgraded `tools/airos/atomic_batch_executor.py` with:
- **Pattern 4**: monkeypatch/mock string literal rewriting (`"tools.x.func"` → `"tools.newloc.x.func"`)
- **Pattern 5**: `importlib.import_module("tools.x")` string rewriting

These were the **root cause of all prior executor failures** on `REPOSITORY_PHASE1_OUTCOME_TRUTH_BATCH_001`.

---

## Root Cause Diagnosed

`tests/test_official_resolution_full_history_runner.py` contains:

```python
monkeypatch.setattr(
    "tools.official_resolution_acquire_pilot.build_pilot_package", build_pilot_package
)
```

After `official_resolution_acquire_pilot.py` was moved to `tools/outcome_truth/`, the string literal `"tools.official_resolution_acquire_pilot.build_pilot_package"` still referenced the old (non-existent) module path. The executor was rewriting regular `import` and `from ... import` statements but **not quoted string literals** used by pytest's monkeypatch.

---

## Files Created / Modified

| File | Action |
|---|---|
| `tools/airos/migration_analyzer.py` | **NEW** — pre-move pattern scanner |
| `tests/test_airos_migration_analyzer.py` | **NEW** — 14 tests, all pass |
| `tools/airos/atomic_batch_executor.py` | **MODIFIED** — added Pattern 4 + 5 to rewriter, `__init__.py` auto-creation |
| `docs/operations/repository/migration_patch_plan.json` | **GENERATED** — live analysis output |

---

## Detected Patterns (7 types)

| Pattern | Description |
|---|---|
| `import_statements` | `import tools.x` / `from tools.x import y` / `from tools import x` |
| `monkeypatch_strings` | `"tools.x.func"` / `'tools.x.func'` in setattr/patch calls |
| `path_literals` | `Path("tools/x.py")` / `Path('tools/x.py')` |
| `repo_path_builds` | `_REPO / "tools" / "x.py"` style chain builds |
| `ast_source_readers` | `ast.parse(Path(...).read_text(...))` near target basename |
| `importlib_strings` | `importlib.import_module("tools.x")` |
| `init_files_required` | Target package dirs missing `__init__.py` |

---

## Live Analysis — OUTCOME_TRUTH_BATCH_001

```
Batch:                REPOSITORY_PHASE1_OUTCOME_TRUTH_BATCH_001
Risk level:           MEDIUM_ATOMIC
Files to move:        6
Affected files:       10
Monkeypatch rewrites: 4      ← ROOT CAUSE FOUND
Path literal rewrites:0      ← already fixed via __file__
Dynamic import fixes: 0
__init__.py required: 1      ← ROOT CAUSE FOUND
Unresolved patterns:  0
```

### Recommendations
- Rewrite 4 monkeypatch string literals before or during move ✅ (executor now handles this)
- Create `__init__.py` in `tools/outcome_truth/` ✅ (executor now auto-creates)

---

## Tests

```
tests/test_airos_migration_analyzer.py  14/14 passed
tests/test_airos_atomic_batch_executor.py  3/3 passed
```

---

## Patch Plan Schema

```json
{
  "schema_version": "migration_patch_plan_v1",
  "generated_at_utc": "...",
  "batch_id": "...",
  "risk_level": "...",
  "approval_required": false,
  "source_paths": [...],
  "target_paths": [...],
  "module_rewrite_map": {...},
  "file_path_rewrite_map": {...},
  "affected_files": {...},
  "test_files": [...],
  "monkeypatch_rewrites": [...],
  "path_literal_rewrites": [...],
  "dynamic_import_rewrites": [...],
  "init_files_required": [...],
  "pre_move_patch_recommendations": [...],
  "post_move_validation_commands": [...],
  "unresolved_patterns": [...]
}
```

---

## Safety Check

- No polymarket/, config/, strategy, sizing, risk, execution, live/paper behavior, dashboard, Telegram, .env touched
- All changes: offline tooling only
- Evidence grade: C (tests verified)

---

## TASK_OUTPUT_CONTRACT

### Task Identity
- Task name: AIROS_MIGRATION_ANALYZER_AND_PATCH_PLANNER_001
- Task class: 4 TOOLING
- Agent roles used: PRIMARY=04_TOOLING SUPPORTING=07_TEST_CI_AGENT

### Files Changed
- `tools/airos/migration_analyzer.py` — NEW: pre-move pattern scanner
- `tests/test_airos_migration_analyzer.py` — NEW: 14 tests
- `tools/airos/atomic_batch_executor.py` — MODIFIED: Pattern 4+5 added to rewriter, __init__.py auto-creation
- `docs/operations/repository/migration_patch_plan.json` — GENERATED: live patch plan
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json` — updated task state
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json` — new entry appended

### Tests Run
- Command: `.venv\Scripts\python.exe -m pytest tests\test_airos_migration_analyzer.py -q`
- Result: PASS 14/14
- Pre-existing failures: NONE

### Evidence
- [Grade C] 14/14 tests pass in `test_airos_migration_analyzer.py`
- [Grade C] 3/3 tests pass in `test_airos_atomic_batch_executor.py`
- [Grade B] Live analyzer run on actual `batch_candidates.json` found exactly 4 monkeypatch rewrites + 1 init file required
- [Grade B] Pattern 4+5 confirmed in executor source code

### Remaining Uncertainty
- The OUTCOME_TRUTH batch has not yet been re-executed with the upgraded executor — that is the next task

### Commits Made
- NONE yet (pending commit in this response)

### Active Question Status
- OPEN: LOW_PRICE_TRUTH_RESOLUTION_001

### Batch 2 Authorization
- NOT AUTHORIZED

### Recommended Next Task
- `RUN_OUTCOME_TRUTH_BATCH_WITH_ANALYZER_GUIDED_EXECUTION` (Class 6) — re-execute the OUTCOME_TRUTH batch with upgraded executor
