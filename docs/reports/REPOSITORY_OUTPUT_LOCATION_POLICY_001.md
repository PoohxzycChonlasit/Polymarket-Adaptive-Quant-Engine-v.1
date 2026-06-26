# REPOSITORY_OUTPUT_LOCATION_POLICY_001

**Date:** 2026-06-26  
**Role:** 24_REPOSITORY_LIBRARIAN_AGENT  
**Task Class:** 3 (DOCS_HOUSEKEEPING)  
**Document type:** Report  
**Destination:** `docs/reports/` ← this file is here, not in root  
**HEAD:** `1ba8499`

---

## Summary

Added Repository Output Location Policy to three governance documents. Moved 11 root `.md` files (1 tracked, 10 untracked) to correct `docs/` destinations. Root tracked `.md` is now exactly the 20 designated entrypoints — zero session artifacts.

---

## Rules Added

### PROJECT_RULES.md — New section: Repository Output Location Policy

Added immediately before the `# Session Handoff Rule` section. Content:
- Routing table: 5 document types → 5 `docs/` destinations
- `WRONG` / `RIGHT` examples for 3 common violations
- Full list of 21 designated root entrypoints
- Violation definition and Librarian trigger condition

### AGENTS.md — New section: Repository Output Location Policy

Added immediately before `## Mandatory Task Output Contract`. Content:
- Pre-write declaration format (`DOCUMENT_TYPE` / `DESTINATION` / `REASON`)
- Compact routing table
- Policy violation definition and Role 24 trigger

### MASTER_AGENT_ROUTER.md — New section: Repository Output Location Rule

Added immediately before `## Documentation Cleanup Trigger`. Content:
- Pre-write destination declaration requirement
- Role 24 invocation rule for any task creating/moving `.md` files
- Quick routing guide (4 lines)
- Violation consequence (task output contract incomplete until routed)

---

## Files Edited

| File | Lines Added |
|------|-------------|
| `PROJECT_RULES.md` | +39 |
| `AGENTS.md` | +25 |
| `MASTER_AGENT_ROUTER.md` | +16 |
| **Total** | **+80** |

---

## Files Moved

### Tracked (git mv → R100 rename)

| Source | Destination |
|--------|------------|
| `ROOT_MD_TRACKED_BATCH_T5_001.md` | `docs/reports/ROOT_MD_TRACKED_BATCH_T5_001.md` |

### Untracked (mv → correct docs path)

| Source | Destination | Category |
|--------|------------|----------|
| `BATCH_2_GATE_CHECK_001.md` | `docs/audits/BATCH_2_GATE_CHECK_001.md` | Gate check / audit |
| `DASHBOARD_DIRTY_BATCH_ISOLATION_001.md` | `docs/audits/DASHBOARD_DIRTY_BATCH_ISOLATION_001.md` | Audit/verification |
| `CURRENT_PROJECT_STATUS_SYNC_001.md` | `docs/reports/CURRENT_PROJECT_STATUS_SYNC_001.md` | Status sync report |
| `ROOT_MD_BATCH_R7_COMMIT_REPORT_001.md` | `docs/reports/ROOT_MD_BATCH_R7_COMMIT_REPORT_001.md` | Commit report |
| `ROOT_MD_FINAL_INVENTORY_COMMIT_REPORT_001.md` | `docs/reports/ROOT_MD_FINAL_INVENTORY_COMMIT_REPORT_001.md` | Commit report |
| `ROOT_MD_TRACKED_BATCH_T1_COMMIT_REPORT_001.md` | `docs/reports/ROOT_MD_TRACKED_BATCH_T1_COMMIT_REPORT_001.md` | Commit report |
| `ROOT_MD_TRACKED_BATCH_T2_COMMIT_REPORT_001.md` | `docs/reports/ROOT_MD_TRACKED_BATCH_T2_COMMIT_REPORT_001.md` | Commit report |
| `ROOT_MD_TRACKED_BATCH_T3_COMMIT_REPORT_001.md` | `docs/reports/ROOT_MD_TRACKED_BATCH_T3_COMMIT_REPORT_001.md` | Commit report |
| `ROOT_MD_TRACKED_BATCH_T4_COMMIT_REPORT_001.md` | `docs/reports/ROOT_MD_TRACKED_BATCH_T4_COMMIT_REPORT_001.md` | Commit report |
| `ROOT_MD_TRACKED_BATCH_T5_COMMIT_REPORT_001.md` | `docs/reports/ROOT_MD_TRACKED_BATCH_T5_COMMIT_REPORT_001.md` | Commit report |

**Total moved: 11 files** (1 tracked R100 + 10 untracked)

---

## Root Markdown Remaining

After all moves, `git ls-files "*.md" | grep -v "/"` returns exactly:

```
AGENTS.md
BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md
CHATGPT_PROJECT_START_PROMPT.md
CLAUDE.md
CODEX_START_HERE.md
CODEX_START_PROMPT.md
CURRENT_PROJECT_STATUS.md
DOCUMENTATION_MAP.md
FILE_INDEX.md
INVENTORY_REPLAY_RESEARCH_PLAN.md
KNOWN_ISSUES.md
MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md
MASTER_AGENT_ROUTER.md
PROJECT_RULES.md
PROJECT_STRUCTURE.md
QUANT_FUTURE_DECISION_ENGINE.md
QUANT_LIFECYCLE_INVENTORY_ENGINE.md
QUANT_REGIME_PROBABILITY_ENGINE.md
README.md
VULTR_PAPER_RUN.md
```

**20 files — exactly the designated entrypoints. Zero untracked root `.md`. Root is clean.**

---

## Verification Results

| Check | Result |
|-------|--------|
| Governance docs changed | AGENTS.md +25, PROJECT_RULES.md +39, MASTER_AGENT_ROUTER.md +16 |
| Python files changed | NONE ✓ |
| Dashboard files changed | NONE ✓ |
| Runtime exports changed | NONE ✓ |
| Root entrypoints moved | NONE ✓ |
| Non-entrypoint `.md` in root tracked | **0** ✓ |
| Non-entrypoint `.md` in root untracked | **0** ✓ |
| Staged: | R100 `ROOT_MD_TRACKED_BATCH_T5_001.md → docs/reports/` |
| Batch 2 started | NO ✓ |

---

## Commit Plan (after verification)

All changes should be committed in a single TYPE C commit (governance docs + tracked rename + untracked additions to docs/):

```bash
git add AGENTS.md PROJECT_RULES.md MASTER_AGENT_ROUTER.md \
        docs/audits/BATCH_2_GATE_CHECK_001.md \
        docs/audits/DASHBOARD_DIRTY_BATCH_ISOLATION_001.md \
        docs/reports/CURRENT_PROJECT_STATUS_SYNC_001.md \
        docs/reports/ROOT_MD_BATCH_R7_COMMIT_REPORT_001.md \
        docs/reports/ROOT_MD_FINAL_INVENTORY_COMMIT_REPORT_001.md \
        docs/reports/ROOT_MD_TRACKED_BATCH_T1_COMMIT_REPORT_001.md \
        docs/reports/ROOT_MD_TRACKED_BATCH_T2_COMMIT_REPORT_001.md \
        docs/reports/ROOT_MD_TRACKED_BATCH_T3_COMMIT_REPORT_001.md \
        docs/reports/ROOT_MD_TRACKED_BATCH_T4_COMMIT_REPORT_001.md \
        docs/reports/ROOT_MD_TRACKED_BATCH_T5_COMMIT_REPORT_001.md \
        docs/reports/REPOSITORY_OUTPUT_LOCATION_POLICY_001.md

git commit -m "docs: add output location policy and route session reports"
```

Note: `ROOT_MD_TRACKED_BATCH_T5_001.md → docs/reports/` is already staged as R100 from `git mv`.

---

## Final Verdict

```
OUTPUT_POLICY_READY_TO_COMMIT
```

**Summary:** Repository output location policy added to all three governance documents (+80 lines total). 11 root session reports moved to correct `docs/` destinations. Root tracked `.md` is now exactly the 20 designated entrypoints. No Python, dashboard, or runtime files touched. Ready to commit as a single TYPE C batch.
