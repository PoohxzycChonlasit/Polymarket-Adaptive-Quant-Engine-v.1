# ROOT_MD_PILOT_MOVE_001

**Date:** 2026-06-26  
**Role:** 24_REPOSITORY_LIBRARIAN_AGENT  
**Task Class:** 3 (DOCS_HOUSEKEEPING) — pilot file move, no commit  
**Baseline commit:** `1e134fc` docs: add root folder triage report

---

## Pre-Move Verification

| Check | Result |
|-------|--------|
| HEAD | `1e134fc` ✓ |
| Branch | `main` ✓ |
| `docs/reports/` exists | YES (31 files before move) ✓ |
| `docs/architecture/` exists | YES (1 file before move) ✓ |
| All 8 source files tracked by git | NO — all 8 were untracked (`??`) |
| All 8 source files exist in root | YES — all confirmed ✓ |

**Note on `git mv`:** The task specified `git mv` where possible. All 8 files were untracked (`git ls-files` returned empty for all). `git mv` requires a tracked file to operate; it raises an error on untracked files. Regular `mv` was used instead, which is the correct tool for untracked files. The result is identical at commit time: both produce new files at the destination path.

---

## Source → Destination Table

| Source (root) | Destination | Status |
|--------------|-------------|--------|
| `PROJECT_HEALTH_CHECK_001.md` | `docs/reports/PROJECT_HEALTH_CHECK_001.md` | MOVED ✓ |
| `RUNTIME_ENVIRONMENT_ACTIVATION_CHECK_001.md` | `docs/reports/RUNTIME_ENVIRONMENT_ACTIVATION_CHECK_001.md` | MOVED ✓ |
| `VENV_REBUILD_DESKTOP_001.md` | `docs/reports/VENV_REBUILD_DESKTOP_001.md` | MOVED ✓ |
| `RUNTIME_SHORT_PAPER_VALIDATION_001.md` | `docs/reports/RUNTIME_SHORT_PAPER_VALIDATION_001.md` | MOVED ✓ |
| `AGENT_OS_DOCS_BATCH_1_COMMIT_REPORT_001.md` | `docs/reports/AGENT_OS_DOCS_BATCH_1_COMMIT_REPORT_001.md` | MOVED ✓ |
| `ROOT_FOLDER_TRIAGE_COMMIT_REPORT_001.md` | `docs/reports/ROOT_FOLDER_TRIAGE_COMMIT_REPORT_001.md` | MOVED ✓ |
| `QUANT_ARCHITECTURE_MASTER_PLAN_001.md` | `docs/architecture/QUANT_ARCHITECTURE_MASTER_PLAN_001.md` | MOVED ✓ |
| `AI_AGENT_OPERATING_SYSTEM_DESIGN_001.md` | `docs/architecture/AI_AGENT_OPERATING_SYSTEM_DESIGN_001.md` | MOVED ✓ |

**Total moved: 8 / 8**

---

## Post-Move Verification

### Source files gone from root

```
GONE_FROM_ROOT: PROJECT_HEALTH_CHECK_001.md
GONE_FROM_ROOT: RUNTIME_ENVIRONMENT_ACTIVATION_CHECK_001.md
GONE_FROM_ROOT: VENV_REBUILD_DESKTOP_001.md
GONE_FROM_ROOT: RUNTIME_SHORT_PAPER_VALIDATION_001.md
GONE_FROM_ROOT: AGENT_OS_DOCS_BATCH_1_COMMIT_REPORT_001.md
GONE_FROM_ROOT: ROOT_FOLDER_TRIAGE_COMMIT_REPORT_001.md
GONE_FROM_ROOT: QUANT_ARCHITECTURE_MASTER_PLAN_001.md
GONE_FROM_ROOT: AI_AGENT_OPERATING_SYSTEM_DESIGN_001.md
```

All 8 source files absent from root. ✓

### Destination files appear at correct paths

```
?? docs/architecture/AI_AGENT_OPERATING_SYSTEM_DESIGN_001.md
?? docs/architecture/QUANT_ARCHITECTURE_MASTER_PLAN_001.md
?? docs/reports/AGENT_OS_DOCS_BATCH_1_COMMIT_REPORT_001.md
?? docs/reports/PROJECT_HEALTH_CHECK_001.md
?? docs/reports/ROOT_FOLDER_TRIAGE_COMMIT_REPORT_001.md
?? docs/reports/RUNTIME_ENVIRONMENT_ACTIVATION_CHECK_001.md
?? docs/reports/RUNTIME_SHORT_PAPER_VALIDATION_001.md
?? docs/reports/VENV_REBUILD_DESKTOP_001.md
```

All 8 files visible as untracked at their new destinations. ✓

### Tracked dirty set unchanged

```
M CURRENT_PROJECT_STATUS.md
M dashboard/package-lock.json
M dashboard/package.json
M dashboard/src/pages/overview/OverviewPage.test.tsx
M dashboard/src/pages/overview/OverviewPage.tsx
M dashboard/src/pages/research/ResearchPage.tsx
M dashboard/src/styles/styles.css
M dashboard/src/types/dashboard.ts
M dashboard/vite.config.ts
M docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md
M runtime/research_exports/canonical_regime_enriched_trades_v1.csv
M runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json
M runtime/research_exports/canonical_regime_enriched_trades_v1_summary.md
M tests/test_dashboard_state_aggregator.py
M tools/dashboard_state_aggregator.py
```

Identical to pre-task state. No tracked files disturbed. ✓

---

## Scope Violation Checks

| Check | Result |
|-------|--------|
| Python files moved | NONE |
| Dashboard files moved | NONE |
| Runtime exports moved | NONE |
| Root entrypoints moved | NONE (AGENTS.md, PROJECT_RULES.md, README.md, etc. untouched) |
| Files outside the 8-file allowed list moved | NONE |
| Batch 2 started | NO |
| Commits made | NONE |

---

## Confirmation No Code Files Touched

- [A] `git status --short | grep -v "^??"` shows identical tracked dirty set before and after moves
- [A] None of the 8 moved files are Python, TypeScript, JSON, or any non-markdown type
- [A] `docs/reports/` and `docs/architecture/` contain only `.md` files from this task

---

## Workflow Note: `git mv` vs `mv` for Untracked Files

For the full 322-file cleanup batches (R1–R7), the same pattern applies: most root files are untracked, so `mv` is the correct tool. The commit workflow is:

```bash
# Move untracked files with mv
mv SOURCE.md docs/DESTINATION/

# Then stage at the new path
git add docs/DESTINATION/SOURCE.md

# Commit
git commit -m "docs: move [category] docs to docs/[destination]/"
```

For any files that **are** tracked in root (from the 122 tracked root `.md` files), `git mv` would be used and the staging is automatic. This distinction is important for future batches.

---

## Recommendation for Commit

The pilot move is clean and complete. Committing these 8 files is safe. Suggested commit:

```bash
git add docs/reports/PROJECT_HEALTH_CHECK_001.md \
        docs/reports/RUNTIME_ENVIRONMENT_ACTIVATION_CHECK_001.md \
        docs/reports/VENV_REBUILD_DESKTOP_001.md \
        docs/reports/RUNTIME_SHORT_PAPER_VALIDATION_001.md \
        docs/reports/AGENT_OS_DOCS_BATCH_1_COMMIT_REPORT_001.md \
        docs/reports/ROOT_FOLDER_TRIAGE_COMMIT_REPORT_001.md \
        docs/architecture/QUANT_ARCHITECTURE_MASTER_PLAN_001.md \
        docs/architecture/AI_AGENT_OPERATING_SYSTEM_DESIGN_001.md

git commit -m "docs: route session reports and architecture plans to docs/"
```

This commit should also include `ROOT_MD_PILOT_MOVE_001.md` (this report) staged from root, or this report should be moved to `docs/reports/` before staging.

---

## Final Verdict

```
PILOT_MOVE_READY_TO_COMMIT
```

**Summary:** All 8 files successfully moved from root to their target subdirectories. Source files are gone from root. Destination files are present at correct paths. No tracked files, code files, dashboard files, or runtime exports were disturbed. No root entrypoints were moved. Batch 2 was not started. No commits were made.

The pilot confirms that the full 322-file cleanup batches (R1–R7) can proceed safely using the same `mv` + `git add` + `git commit` workflow.
