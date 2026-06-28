# AI Task Template Library v1

## Purpose

Reusable task templates for AI agents working in this repository. Templates are docs-only contracts; they do not authorize scope beyond the user's task.

## Atomic Repository Move

```text
TASK: <TASK_ID>
TASK_CLASS: 6 REFACTOR / REPOSITORY ORGANIZATION

Objective:
Move exactly <N> files from <old paths> to <new paths>.

Allowed changes:
- listed old paths
- listed new paths
- targeted tests that import moved modules
- docs/reports/<TASK_ID>.md
- docs/operations state, queue, active loop memory

Required preflight:
- git status --short
- git branch -vv
- active_loop_memory_file from ACTIVE_WORKFLOW_STATE_001.json

Required validation:
- rg old paths/imports
- py_compile moved files only
- targeted pytest only if imports changed
- json.tool ops JSON and active loop memory
- git diff --check

Forbidden:
- full pytest
- builders/backtests
- paper/live runtime
- runtime trading files unless explicitly scoped
```

## Docs/Governance Task

```text
TASK: <TASK_ID>
TASK_CLASS: 3 DOCS / GOVERNANCE

Objective:
Update governance or documentation contracts.

Allowed changes:
- docs/operations/
- docs/reports/
- docs/architecture/ only if design docs are required

Validation:
- rg required terms
- json.tool modified ops JSON
- git diff --check
- no runtime/tool/test changes
```

## Class 6 Low-Risk Refactor

```text
TASK: <TASK_ID>
TASK_CLASS: 6 REFACTOR

Preconditions:
- clean tree
- graph query or documented fallback if graph target missing
- execution contract if required by current governance
- active loop memory pointer validated

Validation:
- compile changed Python files
- targeted tests for changed imports/behavior
- source guard proving forbidden runtime paths unchanged
- docs/report/ops updated in the same cohesive commit
```

## Design-Only Architecture Task

```text
TASK: <TASK_ID>
TASK_CLASS: 2 DESIGN

Scope:
Design only. Do not implement scripts, move files, change runtime behavior, or run heavy validation.

Required:
- preflight git status and branch
- read current architecture and ops state
- create docs/architecture design
- create docs/reports report
- update docs/operations state, queue, active loop memory

Validation:
- json.tool ops JSON and active loop memory
- git diff --check
- no pytest/builders/backtests
```

## Runtime Validation Task

```text
TASK: <TASK_ID>
TASK_CLASS: 0 HEALTH_CHECK or 5 OBSERVABILITY VALIDATION

Scope:
Validation only. No strategy/risk/execution changes.

Required:
- runtime operations preflight
- no live mode unless explicitly authorized
- capture command, duration, exit code, logs, JSONL evidence
- write report

Stop:
- dirty core runtime files
- live-risk flags
- missing operator approval
```

## Replay/Backtest Task

```text
TASK: <TASK_ID>
TASK_CLASS: 1 RESEARCH or 4 TOOLING

Scope:
Offline only.

Required:
- check active question and registries
- use compact research state first
- state data window and sample size
- write report

Validation:
- targeted script/test command
- no live/paper runtime
- no strategy promotion without separate task
```

## Paper Session Report

```text
TASK: <TASK_ID>
TASK_CLASS: 0 or 16-style PAPER EVALUATION

Required:
- runtime operations preflight
- run only paper mode
- record start/end time, run id, cycles, events, no-live-order proof
- evaluate logs with targeted offline tools if scoped
- write PASS/CAUTION/FAIL report
```

## Commit-Boundary Repair

```text
TASK: COMMIT_<PREVIOUS_TASK>_001
TASK_CLASS: 3 DOCS / REPOSITORY HYGIENE

Objective:
Commit completed previous task outputs before starting implementation.

Required:
- git status --short
- git diff --name-only
- confirm dirty files are only previous task allowed outputs
- validate JSON files if ops JSON changed
- stage only listed files
- commit
- do not push unless asked
```

## Dirty Tree Classification

```text
TASK: DIRTY_TREE_CLASSIFICATION_001
TASK_CLASS: 0 HEALTH_CHECK

Required:
- git status --short
- git diff --name-only
- compare dirty files to previous task allowed outputs
- classify as DIRTY_PREVIOUS_TASK_OUTPUTS, DIRTY_OPERATOR_WORK, or DIRTY_UNKNOWN
- recommend commit-boundary task or operator decision

No writes.
```

## Enterprise Atomic Batch Migration

```text
TASK: <BATCH_TASK_ID>
TASK_CLASS: 6 REFACTOR / BATCH MIGRATION

Objective:
Relocate multiple related candidate scripts into their target folders atomically.

Batch Rules:
- Stop micro-move rule: Batch files together rather than running plan/move splits.
- Max size: 12 files or 1,500 lines diff.
- Must use BATCH_MIGRATION_RISK_MODEL_001 to classify risk.

Required preflight:
- git status --short (must be clean)
- git branch -vv (must be up to date)
- active_loop_memory_file from ACTIVE_WORKFLOW_STATE

Allowed changes:
- Moves of listed files via git mv
- Targeted test import updates
- Docs index refresh (FILE_INDEX.md, etc.)
- docs/reports/<BATCH_TASK_ID>.md execution report
- ops state, queue, active loop memory updates

Validation:
- py_compile on all moved files
- targeted pytest on all affected test suites
- git diff --check
- json.tool validation on all modified ops JSONs

Commit/Push:
- Stage and commit all deliverables together in a single cohesive commit.
- Push immediately to origin main.
```
