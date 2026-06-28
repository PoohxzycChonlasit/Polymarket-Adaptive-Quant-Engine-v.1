# REPOSITORY_HEALTH_CHECK_001

**Status:** ACTIVE  
**Date:** 2026-06-28  
**Purpose:** Mandatory pre-implementation git health check protocol for AI agents.

---

## Why This Exists

On 2026-06-28, the local branch was 177 commits ahead of origin/main after multiple AI sessions. GitHub was not current, meaning any parallel AI agent using the remote would start from stale state. This protocol prevents implementation on stale state.

AIROS integration:

- `docs/operations/AI_REPO_BOOTSTRAP_001.md` starts with this health check.
- `docs/architecture/AI_REPOSITORY_OPERATING_SYSTEM_V1_001.md` defines the Health Dashboard layer.
- `docs/operations/AI_REPOSITORY_KERNEL_SCHEMA_001.md` defines `repo_health.json`.
- `docs/operations/AI_TASK_TEMPLATE_LIBRARY_001.md` includes dirty-tree and commit-boundary templates.

---

## Mandatory Commands Before Any Implementation

Run ALL of the following before writing any code, modifying any file, or starting any builder/backtest:

```bash
# 1. Check working tree state
git status

# 2. Fetch remote state (no merge — read only)
git fetch origin

# 3. Check ahead/behind
git branch -vv

# 4. Check recent local commits
git log --oneline -5

# 5. Check for whitespace/conflict markers
git diff --check
```

---

## Decision Tree

```
git status
├── dirty (modified or staged files)
│   ├── Ask operator: commit / stash / leave?
│   └── DO NOT push until operator decides
└── clean (only untracked allowed)
    └── git branch -vv
        ├── ahead N → push before starting new work
        │   └── git push origin main
        ├── behind N → STOP — pull and reconcile first
        ├── diverged → STOP — reconcile with operator
        └── up to date → proceed with implementation
```

---

## Dirty Tree Classification

Classify a dirty tree before starting any new task.

| Classification | How to identify | Required action |
|---|---|---|
| `DIRTY_PREVIOUS_TASK_OUTPUTS` | Dirty files match the previous completed task's allowed outputs, such as docs/reports and docs/operations metadata from a finished design/report task. | Do not start the next implementation task. Run a commit-boundary task such as `COMMIT_PREVIOUS_TASK_OUTPUTS_001` or a task-specific commit task. |
| `DIRTY_OPERATOR_WORK` | Dirty files appear unrelated to the previous AI task, were modified by the operator, or include files outside the previous task's allowed scope. | Stop and ask the operator whether to preserve, commit, ignore, branch around, or otherwise handle the work. |
| `DIRTY_UNKNOWN` | The source of dirty files cannot be confidently identified. | Stop, report `git status --short` and `git diff --name-only`, and ask for operator classification. |

Forbidden transition:

```text
DESIGN_TASK_DONE_UNCOMMITTED
->
IMPLEMENTATION_TASK_STARTED
->
DIRTY_TREE_STOP
```

Required transition:

```text
DIRTY_PREVIOUS_TASK_OUTPUTS
->
COMMIT_PREVIOUS_TASK_OUTPUTS_001
->
next implementation task
```

See [AI_LOOP_BOUNDARY_GOVERNANCE_001.md](AI_LOOP_BOUNDARY_GOVERNANCE_001.md) for the full task boundary contract.

---

## Stop Conditions

**STOP and report to operator if:**

1. `behind N commits` — remote has work that local does not. Pull before continuing.
2. `diverged` — local and remote have different commits. Manual reconciliation required.
3. `ahead N > 20` — many unpushed commits. Push before starting new work.
4. Dirty tree with modified tracked files that you did not create this session.
5. Merge conflicts in any file.
6. `git diff --check` reports whitespace errors in implementation files.
7. Previous task outputs are complete but uncommitted and the requested next task is implementation/refactor/tooling.

---

## Before Starting New Work

```bash
# Required sequence — run in this order
git status                 # must be clean or approved dirty
git fetch origin
git branch -vv             # must be "up to date" or "ahead N" (not behind, not diverged)
git log --oneline -5       # confirm HEAD is expected commit
```

**If branch is ahead of origin**: push before starting new work when the tree is clean.

**Never assume GitHub is current.** The remote may be stale from previous sessions.

**If the tree is dirty from previous completed task outputs**: do not ask for a broad commit/stash choice. The next task should be a narrow commit-boundary task that validates and commits those outputs.

---

## After Each Implementation Phase

After completing a logical unit of work (a task, a feature, a bugfix):

```bash
git status                         # verify only expected files changed
git diff --stat HEAD               # review what changed
git add <specific files>           # stage only relevant files
git commit -m "descriptive msg"    # commit with clear message
git push origin main               # push to keep remote current
git branch -vv                     # verify up to date
```

---

## Quick Reference Card

| Command | Purpose | When to run |
|---|---|---|
| `git status` | Working tree state | Always — first command |
| `git fetch origin` | Refresh remote refs | Before any push/check |
| `git branch -vv` | Ahead/behind/diverged | Before starting work |
| `git log --oneline -5` | Recent commits | Confirm HEAD |
| `git diff --check` | Whitespace/conflict check | Before committing |
| `git push origin main` | Sync to remote | After clean commits |

---

## Loop Memory Health Validation

Before executing any commit or task completion state update, the active loop memory file must pass these checks:
1. **Pointer Existence**: The `active_loop_memory_file` key must be defined in `ACTIVE_WORKFLOW_STATE_001.json`.
2. **File Existence**: The referenced active loop memory file must exist on disk under `docs/operations/loop_memory/`.
3. **JSON Validity**: The file must be syntactically valid JSON. Verify using:
   ```bash
   python -m json.tool <active_loop_memory_file>
   ```
4. **No Side-channel Appends**: No task loop memory entry may be written to any file other than the designated active loop memory file.
5. **Entry Alignment**: The date of the latest task entry in the active file must match the current local system date, or be explicitly authorized by the operator.

---

## Governance Integration

This protocol integrates with [AI_RESOURCE_GOVERNANCE_001.md](AI_RESOURCE_GOVERNANCE_001.md).

Repository health check must pass before:
- Running full-repo pytest
- Running full historical canonical builder
- Running backtest grid on new data
- Starting any Class 6+ implementation task

It also integrates with [AI_LOOP_BOUNDARY_GOVERNANCE_001.md](AI_LOOP_BOUNDARY_GOVERNANCE_001.md), which defines the required final task boundary states and clean handoff contract.
