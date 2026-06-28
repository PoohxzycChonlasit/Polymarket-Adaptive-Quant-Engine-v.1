# AI_LOOP_BOUNDARY_GOVERNANCE_001

**Status:** ACTIVE  
**Date:** 2026-06-28  
**Purpose:** Prevent AI loop drift where a completed task leaves dirty outputs and the next implementation task starts before those outputs are committed or explicitly classified.

---

## Why This Exists

Recent repository organization tasks repeatedly hit this avoidable sequence:

```text
DESIGN_TASK_DONE_UNCOMMITTED
->
IMPLEMENTATION_TASK_STARTED
->
DIRTY_TREE_STOP
```

The existing governance correctly told agents to stop on a dirty tree, but it did not clearly require closing the previous task boundary first. This document makes task transitions explicit.

AIROS integration:

- `docs/operations/AI_REPO_BOOTSTRAP_001.md` uses this document when deciding whether a new task can start.
- `docs/architecture/AI_REPOSITORY_OPERATING_SYSTEM_V1_001.md` treats task boundary state as part of the Repository Kernel.
- `docs/operations/AI_REPOSITORY_KERNEL_SCHEMA_001.md` defines `repo_health.json.boundary_state`.
- `docs/operations/AI_TASK_TEMPLATE_LIBRARY_001.md` includes commit-boundary and dirty-tree templates.

---

## Task Boundary Rule

Every task must end in exactly one boundary state:

| Boundary state | Meaning | Required final action |
|---|---|---|
| `COMMITTED` | Task produced changes and they were committed. | Report commit hash and clean/dirty status after commit. |
| `CLEAN_NO_CHANGES` | Task produced no file changes. | Report clean worktree and that the next task can start immediately. |
| `BLOCKED_NEEDS_OPERATOR_DECISION` | Task cannot safely commit or discard current changes. | Report blocker, dirty files, and the exact operator decision needed. |

No task may end with completed outputs left dirty while recommending the next implementation task.

---

## Transition Rule

Before starting any new task, run:

```bash
git status --short
git branch -vv
```

If the worktree is dirty:

1. Identify whether the dirty files are outputs from the previous completed task.
2. Compare the dirty files with the previous task's allowed outputs and final report.
3. If the dirty files match previous task allowed outputs, the next task must be:

```text
COMMIT_PREVIOUS_TASK_OUTPUTS_001
```

or a task-specific equivalent such as:

```text
COMMIT_PHASE1B_TOOLS_MOVE_PLAN_DOCS_001
```

4. Do not start the next implementation, refactor, tooling, test, builder, paper, or live task until the previous outputs are committed or the operator explicitly chooses another boundary action.

---

## Forbidden Pattern

This pattern is forbidden:

```text
DESIGN_TASK_DONE_UNCOMMITTED
->
IMPLEMENTATION_TASK_STARTED
->
DIRTY_TREE_STOP
```

Instead, use:

```text
DESIGN_TASK_DONE
->
COMMIT_PREVIOUS_TASK_OUTPUTS_001
->
IMPLEMENTATION_TASK_STARTED
```

or:

```text
DESIGN_TASK_DONE
->
CLEAN_NO_CHANGES
->
IMPLEMENTATION_TASK_STARTED
```

---

## Clean Handoff Contract

Every final task output must include:

| Field | Required content |
|---|---|
| Worktree status | `clean`, or dirty file list from `git status --short`. |
| Commit status | `COMMITTED <sha>`, `CLEAN_NO_CHANGES`, or `NOT_COMMITTED`. |
| Boundary state | One of `COMMITTED`, `CLEAN_NO_CHANGES`, `BLOCKED_NEEDS_OPERATOR_DECISION`. |
| Next task can start immediately | `YES` or `NO`. |
| If not, exact commit task name | Example: `COMMIT_PREVIOUS_TASK_OUTPUTS_001`. |

The mandatory project `TASK_OUTPUT_CONTRACT` should repeat the same boundary facts under `Evidence`, `Commits Made`, and `Recommended Next Task`.

---

## Dirty Tree Classification

When `git status --short` is not clean, classify the dirty tree before deciding the next action.

| Classification | Definition | Required action |
|---|---|---|
| `DIRTY_PREVIOUS_TASK_OUTPUTS` | Dirty files match the previous completed task's allowed outputs and report/ops metadata. | Create or run `COMMIT_PREVIOUS_TASK_OUTPUTS_001`; do not start implementation. |
| `DIRTY_OPERATOR_WORK` | Dirty files appear to be user/operator work, unrelated to the AI task, or explicitly provided by the operator. | Stop and ask whether to preserve, commit, ignore, or branch around them. |
| `DIRTY_UNKNOWN` | Dirty files cannot be confidently attributed to previous task outputs or operator work. | Stop; report file list and ask for operator decision. |

---

## Commit Task Template

When the transition rule requires a commit task, use a narrow scope:

```text
TASK: COMMIT_PREVIOUS_TASK_OUTPUTS_001
TASK_CLASS: 3 DOCS / REPOSITORY HYGIENE

Objective:
Commit completed outputs from the previous task before starting the next implementation task.

Required:
1. Run git status --short.
2. Run git diff --name-only.
3. Confirm dirty files are only previous task allowed outputs.
4. Validate JSON files if docs/operations/*.json changed.
5. Stage only those files.
6. Commit with a descriptive message.
7. Do not push unless operator asks.
```

Task-specific names are preferred when they are clearer, for example `COMMIT_PHASE1B_TOOLS_MOVE_PLAN_DOCS_001`.

---

## Commit Cohesion Rule (Single-Commit Task Completion)

For all implementation/refactor tasks (Class 4, 5, 6, 7, 8), the following related artifacts must be staged and committed together in a single cohesive commit, rather than split across separate implementation and state-only commits:
- code modifications or file moves
- targeted test updates
- final task execution report
- `ACTIVE_WORKFLOW_STATE` JSON update
- `TASK_QUEUE` JSON update
- loop memory JSON update
- execution contract and graph query artifacts

### Avoid Pattern
Split commits such as:
1. `refactor: move tools` (commit 1)
2. `docs: update workflow state for completion` (commit 2)

### Allowed Exceptions
Separation is allowed only if:
1. The combined commit size or file count exceeds standard execution limits.
2. The user/operator explicitly requests separate commits.
3. The platform or environment encounters an error during the staging of specific files.
In all exception cases, the reason for splitting the commit must be explicitly documented in the final task execution report.

---

## Loop Memory Active File Governance

To prevent fragmented operational memory and cross-AI loop drift, all agents must adhere to these active-file workflow rules:
1. **Never Hardcode filenames**: Never hardcode loop memory filenames (e.g. `LOOP_MEMORY_YYYYMMDD_001.json`) in prompts, scripts, or task executions.
2. **Retrieve Pointer**: Always retrieve the `active_loop_memory_file` path directly from the `workflow_governance` block of `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`.
3. **Pointer Missing Safety Stop**: If the `active_loop_memory_file` pointer is missing, classify the condition as `LOOP_MEMORY_POINTER_MISSING`, STOP, and ask the operator to repair.
4. **Pointer Precedence**: If the pointer file date differs from the current local date but the pointer path is explicit, continue using the pointer file as the active log file unless the operator explicitly requests a rollover.
5. **Rollover Procedure**: If the operator says "new day" or requests a rollover:
   - Create the next dated loop memory file matching the current date.
   - Initialize it with a valid empty JSON list structure (`[]`).
   - Update the `active_loop_memory_file` pointer and update `last_loop_memory_rollover_utc` in `ACTIVE_WORKFLOW_STATE_001.json`.
   - Document the rollover in the next task report.

---

## Non-Goals

- This document does not authorize runtime, strategy, sizing, risk, execution, dashboard, Telegram, `.env`, paper, or live changes.
- This document does not require pushing after every local commit unless a separate task or operator instruction asks for it.
- This document does not override operator instructions to intentionally leave a tree dirty.

---

## Batch Reorganization Transition Rules

1. **Stop Micro-Move Splits:** Do not split low/medium repository cleanup tasks into separate plan-only and move-only tasks unless risk requires it (e.g. `PLAN_REQUIRED` or `DO_NOT_MOVE` levels under `BATCH_MIGRATION_RISK_MODEL_001.md`).
2. **Prefer Atomic Batch Execution:** Always prefer atomic batch execution when the blast radius score is bounded (score $\le 6$, mapping to `SAFE_ATOMIC` or `MEDIUM_ATOMIC`).
3. **Plan-Only Exception Criteria:** Plan-only phases are required only for batches involving runtime imports, unclear dependency graphs, missing test coverage, files on the execution/risk/sizing paths, or when explicitly requested by the operator.
