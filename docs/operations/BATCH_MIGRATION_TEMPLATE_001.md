# BATCH_MIGRATION_TEMPLATE_001

**Status:** ACTIVE  
**Date:** 2026-06-28  
**Purpose:** Reusable templates for executing batch migrations.

---

## 1. Repository Tools Batch Migration Template

Use this template to structure a tools migration batch.

```text
TASK: <BATCH_MIGRATION_TASK_ID>
TASK_CLASS: 6 REFACTOR / BATCH MIGRATION

Objective:
Execute the migration of the <Batch Name> tools batch into tools/<target_folder>/.

Why:
Consolidate related scripts to clean up root tools and maintain modular structure.

Required preflight:
1. git status --short (must be clean)
2. git branch -vv (must be up to date with remote)
3. read docs/operations/ACTIVE_WORKFLOW_STATE_001.json
4. use active_loop_memory_file from ACTIVE_WORKFLOW_STATE

Graph Scan & Blast Radius:
| File | Proposed Path | Dependency Risk | Score |
|---|---|---|---|
| <file1.py> | tools/<folder>/<file1.py> | <risk description> | <score> |

Move List:
- git mv tools/<file1.py> tools/<folder>/<file1.py>

Import Update Rules:
- Replace "import tools.<module1>" with "import tools.<folder>.<module1>" in:
  - tests/test_<file1>.py

Validation:
1. .venv\Scripts\python.exe -m py_compile tools/<folder>/*.py
2. pytest tests/test_<file1>.py -q
3. python -m json.tool on active state, queue, and active loop memory.
4. git diff --check

Report & Commit:
- Create docs/reports/<BATCH_MIGRATION_TASK_ID>.md
- Stage and commit all files in a single cohesive commit:
  git commit -m "refactor(batch): move <Batch Name> tools"
- Push immediately to origin main.
```

---

## 2. Tests Batch Migration Template

Use this template when moving test suites to match the tools hierarchy.

```text
TASK: <TESTS_MIGRATION_TASK_ID>
TASK_CLASS: 6 REFACTOR / TESTS MIGRATION

Objective:
Align the tests folder structure with the tools folder reorganization by moving test files.

Required preflight:
- Git status clean
- Check remote alignment

Move List:
- git mv tests/test_<file1>.py tests/<folder>/test_<file1>.py

Validation:
- pytest tests/<folder>/test_<file1>.py -q
- Confirm test selection finds the relocated tests
- Git diff check

Commit:
- commit message: "refactor(batch): relocate <Batch Name> tests to tests/<folder>/"
- Push immediately.
```

---

## 3. Docs/Index Refresh Batch Template

Use this template to clean up stale documentation links.

```text
TASK: <DOCS_REFRESH_TASK_ID>
TASK_CLASS: 3 DOCS / REPOSITORY HYGIENE

Objective:
Update stale file path links in documentation and index files following a batch migration.

Required preflight:
- Git status clean

Files to update:
- FILE_INDEX.md
- DOCUMENTATION_MAP.md
- README.md

Verification:
- Run ripgrep to ensure no stale path strings remain.
- Git diff check

Commit:
- commit message: "docs(batch): update file index and markdown links for <Batch Name> moves"
- Push immediately.
```

---

## 4. Trader Observability Extraction Batch Template

Use this template when refactoring logging or metrics code.

```text
TASK: <OBSERVABILITY_EXTRACTION_TASK_ID>
TASK_CLASS: 5 OBSERVABILITY / REFACTOR

Objective:
Extract observability telemetry code out of core trader logic into a dedicated module.

Required preflight:
- Git status clean
- Validate schema contract in docs/operations/

Allowed Changes:
- Extract helper methods from polymarket/trader.py
- Add to utils/logger.py or polymarket/realtime_logger.py
- Targeted test updates

Validation:
- Compile changed files
- Targeted pytest
- Confirm no trading/risk state behavior is modified

Commit:
- commit message: "observability(batch): extract telemetry from trader core"
- Push immediately.
```
