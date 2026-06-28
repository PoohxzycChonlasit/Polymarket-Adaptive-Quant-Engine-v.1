# REPOSITORY_HEALTH_CHECK_001

**Status:** ACTIVE  
**Date:** 2026-06-28  
**Purpose:** Mandatory pre-implementation git health check protocol for AI agents.

---

## Why This Exists

On 2026-06-28, the local branch was 177 commits ahead of origin/main after multiple AI sessions. GitHub was not current, meaning any parallel AI agent using the remote would start from stale state. This protocol prevents implementation on stale state.

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

## Stop Conditions

**STOP and report to operator if:**

1. `behind N commits` — remote has work that local does not. Pull before continuing.
2. `diverged` — local and remote have different commits. Manual reconciliation required.
3. `ahead N > 20` — many unpushed commits. Push before starting new work.
4. Dirty tree with modified tracked files that you did not create this session.
5. Merge conflicts in any file.
6. `git diff --check` reports whitespace errors in implementation files.

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

## Governance Integration

This protocol integrates with [AI_RESOURCE_GOVERNANCE_001.md](AI_RESOURCE_GOVERNANCE_001.md).

Repository health check must pass before:
- Running full-repo pytest
- Running full historical canonical builder
- Running backtest grid on new data
- Starting any Class 6+ implementation task
