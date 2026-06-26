# ROOT_MD_TRACKED_BATCH_T2_001

**Date:** 2026-06-26  
**Role:** 24_REPOSITORY_LIBRARIAN_AGENT  
**Task Class:** 3 (DOCS_HOUSEKEEPING) — git mv only, no commit  
**Baseline:** `95c35ab` docs: batch T1 move tracked architecture docs

---

## Summary

Moved 36 tracked root audit/evidence/review/validation/trace files to `docs/audits/` using `git mv`. All 36 staged as `R100` renames — pure file moves, full git history preserved. No commit made.

---

## Source → Destination Table (36 files)

All staged as `R100` (pure rename, 100% content similarity).

| # | Source (root) |
|---|---------------|
| 1 | `CANDIDATE_FUNNEL_EVIDENCE_001.md` |
| 2 | `CANDIDATE_LIFECYCLE_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md` |
| 3 | `CANDIDATE_PIPELINE_RUNTIME_VALIDATION_001.md` |
| 4 | `COLD_JSONL_COMPRESSION_TOOL_DRY_RUN_PRE_COMMIT_AUDIT_001.md` |
| 5 | `COMPRESS_RESTORE_PRE_COMMIT_AUDIT_001.md` |
| 6 | `DASHBOARD_API_V0_PRE_COMMIT_AUDIT_001.md` |
| 7 | `DASHBOARD_STATE_AGGREGATOR_PRE_COMMIT_AUDIT_001.md` |
| 8 | `DOC_TRUTH_RECONCILIATION_2026-05-14.md` |
| 9 | `EXECUTION_PAPER_RUNTIME_ISOLATION_001.md` |
| 10 | `EXIT_EXECUTION_ROOT_CAUSE_AUDIT_001.md` |
| 11 | `EXIT_FAILURE_DISTRIBUTION_001.md` |
| 12 | `EXIT_LIFECYCLE_TRACE_001.md` |
| 13 | `FIRST_BLOCKING_GATE_DISTRIBUTION_001.md` |
| 14 | `GHOST_POSITION_UNUSED_SETTING_AUDIT_001.md` |
| 15 | `ONE_FILE_COMPRESSION_VALIDATION_001.md` |
| 16 | `PHASE_B_DAILY_PIPELINE_MANUAL_RUNNER_PRE_COMMIT_AUDIT_001.md` |
| 17 | `PHASE_B_DAILY_PIPELINE_OPERATOR_ACCEPTANCE_AUDIT_001.md` |
| 18 | `PHASE_B_LIVE_RUNTIME_INSPECTION_001.md` |
| 19 | `PHASE_B_WEEKLY_REVIEW_ENGINE_PRE_COMMIT_AUDIT_001.md` |
| 20 | `POSITION_SIZING_HOTFIX_EVIDENCE_SUMMARY_001.md` |
| 21 | `POSITION_SIZING_HOTFIX_RUNTIME_VALIDATION_001.md` |
| 22 | `QUANT_TERMINAL_UI_V3_BLOOMBERG_PRE_COMMIT_AUDIT_001.md` |
| 23 | `REACT_DASHBOARD_ARCHITECTURE_REFACTOR_V1_PRE_COMMIT_AUDIT_001.md` |
| 24 | `REACT_DASHBOARD_ROUTER_V1_PRE_COMMIT_AUDIT_001.md` |
| 25 | `REACT_DASHBOARD_V0_PRE_COMMIT_AUDIT_001.md` |
| 26 | `README_REFRESH_AUDIT_001.md` |
| 27 | `REGIME_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md` |
| 28 | `REPLAY_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md` |
| 29 | `RESEARCH_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md` |
| 30 | `SCHEMA_SLIMMING_STAGE_2_PRE_COMMIT_AUDIT_001.md` |
| 31 | `SCHEMA_SLIMMING_STAGE_2_SCRATCH_VALIDATION_001.md` |
| 32 | `SESSION_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md` |
| 33 | `SMALL_BATCH_COMPRESSION_VALIDATION_001.md` |
| 34 | `WEEKLY_REVIEW_ENGINE_SOURCE_OF_TRUTH_AUDIT_001.md` |
| 35 | `WEEKLY_REVIEW_ENGINE_SOURCE_OF_TRUTH_PATCH_PRE_COMMIT_AUDIT_001.md` |
| 36 | `WEEKLY_REVIEW_ENGINE_SOURCE_OF_TRUTH_REAUDIT_001.md` |

All destinations: `docs/audits/<filename>`

---

## Staged Rename Verification

| Check | Result |
|-------|--------|
| `git diff --cached --name-status \| wc -l` | **36** ✓ |
| Non-R100 entries | **0** (grep returned nothing) ✓ |
| Destinations outside `docs/audits/` | **0** (grep returned nothing) ✓ |

---

## Scope Verification

| Check | Result |
|-------|--------|
| Python files staged | NONE ✓ |
| Dashboard files staged | NONE ✓ |
| Runtime export files staged | NONE ✓ |
| Architecture/report/research docs staged | NONE ✓ |
| Root entrypoints moved | NONE ✓ |
| Batch 2 started | NO ✓ |
| Commits made | NONE ✓ |

---

## Remaining Tracked-Root Move Batches

| Batch | Destination | Files | Status |
|-------|-------------|-------|--------|
| T1 | `docs/architecture/` | 22 | COMMITTED ✓ `95c35ab` |
| T2 | `docs/audits/` | 36 | **STAGED — uncommitted** |
| T3 | `docs/reports/` part 1 | ~25 | After T2 commit |
| T4 | `docs/reports/` part 2 + research | ~24+2 | After T3 |

---

## Final Verdict

```
ROOT_MD_T2_READY_TO_COMMIT
```

**Summary:** 36 tracked root audit files staged as `R100` renames to `docs/audits/`. All 36 entries verified as R100. Zero files outside scope. Git rename history preserved for all 36 files. Ready to commit as a single Type C batch.
