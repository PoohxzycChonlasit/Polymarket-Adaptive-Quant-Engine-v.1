# ROOT_MD_FINAL_INVENTORY_001

**Date:** 2026-06-26  
**Role:** 24_REPOSITORY_LIBRARIAN_AGENT  
**Task Class:** 0 (DISCOVERY ONLY) — no moves, no commits  
**Baseline:** `fdf1e73` docs: batch R7 route remaining markdown documents

---

## 1. Summary Counts

| Metric | Count |
|--------|-------|
| Tracked root `.md` files | **128** |
| Untracked root `.md` files | **2** |
| Modified tracked root `.md` | **1** (`CURRENT_PROJECT_STATUS.md`) |
| **Total root `.md` files** | **130** |

### Classification Totals

| Category | Tracked | Untracked | Total |
|----------|---------|-----------|-------|
| KEEP_ROOT_ENTRYPOINT | 20 | 0 | **20** |
| MOVE_TO_DOCS_ARCHITECTURE | 22 | 0 | **22** |
| MOVE_TO_DOCS_AUDITS | 36 | 0 | **36** |
| MOVE_TO_DOCS_REPORTS | 48 | 1 | **49** |
| MOVE_TO_DOCS_RESEARCH | 2 | 0 | **2** |
| DUPLICATE_DO_NOT_STAGE | 0 | 1 | **1** |
| **Total** | **128** | **2** | **130** |

---

## 2. KEEP_ROOT_ENTRYPOINT (20 files — do not move)

All tracked clean unless noted.

| File | Git State | Reason |
|------|-----------|--------|
| `README.md` | tracked clean | User-facing entrypoint |
| `AGENTS.md` | tracked clean | Auto-loaded AI governance |
| `PROJECT_RULES.md` | tracked clean | Auto-loaded AI governance |
| `MASTER_AGENT_ROUTER.md` | tracked clean | Auto-loaded AI routing |
| `CURRENT_PROJECT_STATUS.md` | **tracked modified** | Single source of truth (needs update after session) |
| `CODEX_START_HERE.md` | tracked clean | Session startup |
| `FILE_INDEX.md` | tracked clean | Quick file map |
| `DOCUMENTATION_MAP.md` | tracked clean | Docs navigation |
| `CLAUDE.md` | tracked clean | Claude Code instructions |
| `CODEX_START_PROMPT.md` | tracked clean | Reusable prompt |
| `CHATGPT_PROJECT_START_PROMPT.md` | tracked clean | Reusable prompt |
| `PROJECT_STRUCTURE.md` | tracked clean | Architecture pointer |
| `KNOWN_ISSUES.md` | tracked clean | Active issues |
| `QUANT_FUTURE_DECISION_ENGINE.md` | tracked clean | Decision framework |
| `QUANT_LIFECYCLE_INVENTORY_ENGINE.md` | tracked clean | Active phase design |
| `QUANT_REGIME_PROBABILITY_ENGINE.md` | tracked clean | Active phase design |
| `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md` | tracked clean | Active phase design |
| `INVENTORY_REPLAY_RESEARCH_PLAN.md` | tracked clean | Active phase plan |
| `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md` | tracked clean | Active phase plan |
| `VULTR_PAPER_RUN.md` | tracked clean | Operations reference |

---

## 3. MOVE_TO_DOCS_ARCHITECTURE (22 files)

All tracked clean. Routing basis: DESIGN ONLY / PLAN / SPEC / TAXONOMY / V1 system definitions.

| File | Confidence | Reason |
|------|-----------|--------|
| `CANDIDATE_LIFECYCLE_ANALYTICS_V1_DESIGN_001.md` | HIGH | `_DESIGN_` |
| `EVENT_CATALOG_V1.md` | HIGH | Event catalog design |
| `EVENT_CONSUMER_MATRIX_V1.md` | HIGH | Event system design matrix |
| `EVENT_DASHBOARD_STATE_MAP_V1.md` | HIGH | State map design |
| `EVENT_DROP_POLICY_V1.md` | HIGH | Policy design |
| `EVENT_PRIORITY_MATRIX_V1.md` | HIGH | Priority design |
| `EVENT_REPLAY_ARCHITECTURE_V1.md` | HIGH | Architecture design |
| `EVENT_SCHEMA_STANDARD_V1.md` | HIGH | Schema standard design |
| `EXIT_IMPLEMENTATION_PLAN_001.md` | HIGH | Forward-looking design plan |
| `PHASE_B_7DAY_EVIDENCE_COLLECTION_GOVERNANCE_001.md` | HIGH | Governance design (READY_FOR_EVIDENCE_COLLECTION verdict = design artifact) |
| `PHASE_B_DAILY_EVIDENCE_COLLECTOR_DESIGN_001.md` | HIGH | `_DESIGN_` |
| `PHASE_B_DAILY_PIPELINE_MANUAL_RUNNER_PLAN_001.md` | HIGH | Forward design plan |
| `PHASE_B_SCHEMA_ISOLATION_PATCH_PLAN_001.md` | HIGH | Forward design plan |
| `REGIME_ANALYTICS_V1_DESIGN_001.md` | HIGH | `_DESIGN_` |
| `REPLAY_ANALYTICS_V1_DESIGN_001.md` | HIGH | `_DESIGN_` |
| `RUNTIME_EVENT_STREAM_IMPLEMENTATION_PLAN_V2.md` | HIGH | Forward design plan |
| `RUNTIME_EVENT_STREAM_V1.md` | HIGH | V1 event stream design |
| `RUNTIME_EVENT_TAXONOMY_V1.md` | HIGH | Taxonomy design |
| `RUNTIME_HEARTBEAT_SPEC_V1.md` | HIGH | Spec design |
| `SESSION_ANALYTICS_V1_DESIGN_001.md` | HIGH | `_DESIGN_` |
| `SHADOW_TELEMETRY_PHASE_B_DESIGN_001.md` | HIGH | `_DESIGN_` |
| `SHADOW_TELEMETRY_PHASE_B_IMPLEMENTATION_PLAN_001.md` | HIGH | Forward design plan |

---

## 4. MOVE_TO_DOCS_AUDITS (36 files)

All tracked clean. Routing basis: AUDIT / PRE_COMMIT_AUDIT / EVIDENCE / DISTRIBUTION / TRACE / VALIDATION / ISOLATION / RECONCILIATION / INSPECTION.

| File | Confidence | Reason |
|------|-----------|--------|
| `CANDIDATE_FUNNEL_EVIDENCE_001.md` | HIGH | Evidence source validation |
| `CANDIDATE_LIFECYCLE_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `CANDIDATE_PIPELINE_RUNTIME_VALIDATION_001.md` | HIGH | Runtime validation audit |
| `COLD_JSONL_COMPRESSION_TOOL_DRY_RUN_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `COMPRESS_RESTORE_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `DASHBOARD_API_V0_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `DASHBOARD_STATE_AGGREGATOR_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `DOC_TRUTH_RECONCILIATION_2026-05-14.md` | HIGH | Documentation reconciliation audit |
| `EXECUTION_PAPER_RUNTIME_ISOLATION_001.md` | HIGH | VERIFICATION ONLY — isolation audit |
| `EXIT_EXECUTION_ROOT_CAUSE_AUDIT_001.md` | HIGH | Root cause audit |
| `EXIT_FAILURE_DISTRIBUTION_001.md` | HIGH | Failure distribution analysis |
| `EXIT_LIFECYCLE_TRACE_001.md` | HIGH | Lifecycle trace |
| `FIRST_BLOCKING_GATE_DISTRIBUTION_001.md` | HIGH | Gate distribution analysis |
| `GHOST_POSITION_UNUSED_SETTING_AUDIT_001.md` | HIGH | Audit |
| `ONE_FILE_COMPRESSION_VALIDATION_001.md` | HIGH | Validation audit |
| `PHASE_B_DAILY_PIPELINE_MANUAL_RUNNER_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `PHASE_B_DAILY_PIPELINE_OPERATOR_ACCEPTANCE_AUDIT_001.md` | HIGH | Acceptance audit |
| `PHASE_B_LIVE_RUNTIME_INSPECTION_001.md` | HIGH | Runtime inspection (PHASE_B_NOT_ACTIVE verdict) |
| `PHASE_B_WEEKLY_REVIEW_ENGINE_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `POSITION_SIZING_HOTFIX_EVIDENCE_SUMMARY_001.md` | HIGH | Evidence summary audit |
| `POSITION_SIZING_HOTFIX_RUNTIME_VALIDATION_001.md` | HIGH | Runtime validation audit |
| `QUANT_TERMINAL_UI_V3_BLOOMBERG_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `REACT_DASHBOARD_ARCHITECTURE_REFACTOR_V1_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `REACT_DASHBOARD_ROUTER_V1_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `REACT_DASHBOARD_V0_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `README_REFRESH_AUDIT_001.md` | HIGH | Audit |
| `REGIME_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `REPLAY_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `RESEARCH_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `SCHEMA_SLIMMING_STAGE_2_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `SCHEMA_SLIMMING_STAGE_2_SCRATCH_VALIDATION_001.md` | HIGH | Validation audit |
| `SESSION_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `SMALL_BATCH_COMPRESSION_VALIDATION_001.md` | HIGH | Validation audit |
| `WEEKLY_REVIEW_ENGINE_SOURCE_OF_TRUTH_AUDIT_001.md` | HIGH | Audit |
| `WEEKLY_REVIEW_ENGINE_SOURCE_OF_TRUTH_PATCH_PRE_COMMIT_AUDIT_001.md` | HIGH | Pre-commit audit |
| `WEEKLY_REVIEW_ENGINE_SOURCE_OF_TRUTH_REAUDIT_001.md` | HIGH | Re-audit |

---

## 5. MOVE_TO_DOCS_REPORTS (49 files = 48 tracked + 1 untracked)

Routing basis: COMMIT_REPORT / IMPLEMENTATION_REPORT / BATCH_REPORT / SCOPE_REVIEW / RESTART_RECORD / NEXT_ACTIONS / OPERATIONAL_RECORD.

| File | Git State | Confidence | Reason |
|------|-----------|-----------|--------|
| `AGENT_OS_DOCS_BATCH_1_REPORT.md` | tracked clean | HIGH | Batch report (committed 65711bc) |
| `BATCH_001_SCOPE_REVIEW_001.md` | tracked clean | HIGH | REVIEW ONLY — scope review record (committed e76581fb) |
| `BATCH_001_SPLIT_COMMIT_PLAN_001.md` | tracked clean | HIGH | Commit plan record (committed e76581fb) |
| `CANDIDATE_LIFECYCLE_ANALYTICS_V1_IMPLEMENTATION_REPORT_001.md` | tracked clean | HIGH | Implementation report |
| `CANDIDATE_PIPELINE_NEXT_ACTIONS_001.md` | tracked clean | HIGH | Next-actions operational record |
| `COLD_JSONL_COMPRESSION_DRY_RUN_COMMIT_REPORT_001.md` | tracked clean | HIGH | Commit report |
| `COLD_JSONL_COMPRESSION_TOOL_DRY_RUN_IMPLEMENTATION_REPORT_001.md` | tracked clean | HIGH | Implementation report |
| `COMPRESS_RESTORE_PATCH_COMMIT_REPORT_001.md` | tracked clean | HIGH | Commit report |
| `COMPRESS_RESTORE_PATCH_REPORT_001.md` | tracked clean | HIGH | Patch report |
| `DASHBOARD_API_V0_IMPLEMENTATION_REPORT_001.md` | tracked clean | HIGH | Implementation report |
| `DASHBOARD_STATE_AGGREGATOR_IMPLEMENTATION_REPORT_001.md` | tracked clean | HIGH | Implementation report |
| `DOCS_LANDING_PAGES_REPORT_001.md` | tracked clean | HIGH | Report |
| `DOCUMENTATION_MAP_REFRESH_REPORT_001.md` | tracked clean | HIGH | Report |
| `FILE_INDEX_REFRESH_REPORT_001.md` | tracked clean | HIGH | Report |
| `GHOST_POSITION_SENTINEL_TEST_IMPLEMENTATION_001.md` | tracked clean | HIGH | CONTROLLED TEST IMPLEMENTATION record |
| `IMPLEMENTATION_REPORT_POSITION_SIZING_V1.md` | tracked clean | HIGH | Implementation report |
| `KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md` | tracked clean | HIGH | Dated snapshot (historical, not active issues list) |
| `PHASE_B_DAILY_PIPELINE_MANUAL_RUNNER_IMPLEMENTATION_REPORT_001.md` | tracked clean | HIGH | Implementation report |
| `PHASE_B_LIVE_RUNTIME_RESTART_AND_SMOKE_001.md` | tracked clean | HIGH | Restart operational record |
| `PHASE_B_WEEKLY_REVIEW_ENGINE_IMPLEMENTATION_REPORT_001.md` | tracked clean | HIGH | Implementation report |
| `POSITION_SIZING_HOTFIX_NEXT_ACTIONS_001.md` | tracked clean | HIGH | Next-actions operational record |
| `QUANT_TERMINAL_UI_V3_BLOOMBERG_REPORT_001.md` | tracked clean | HIGH | Report |
| `QUANT_TERMINAL_UI_V3_VISUAL_VALIDATION_REPORT_001.md` | tracked clean | HIGH | Validation report |
| `REACT_DASHBOARD_ARCHITECTURE_REFACTOR_V1_REPORT_001.md` | tracked clean | HIGH | Report |
| `REACT_DASHBOARD_ROUTER_V1_IMPLEMENTATION_REPORT_001.md` | tracked clean | HIGH | Implementation report |
| `REACT_DASHBOARD_V0_COMMIT_REPORT_001.md` | tracked clean | HIGH | Commit report |
| `REACT_DASHBOARD_V0_IMPLEMENTATION_REPORT_001.md` | tracked clean | HIGH | Implementation report |
| `README_REFRESH_REPORT_001.md` | tracked clean | HIGH | Report |
| `REGIME_ANALYTICS_V1_IMPLEMENTATION_REPORT_001.md` | tracked clean | HIGH | Implementation report |
| `REPLAY_ANALYTICS_V1_IMPLEMENTATION_REPORT_001.md` | tracked clean | HIGH | Implementation report |
| `RESEARCH_ANALYTICS_V1_IMPLEMENTATION_REPORT_001.md` | tracked clean | HIGH | Implementation report |
| `ROOT_FOLDER_TRIAGE_001.md` | tracked clean | HIGH | Librarian triage report |
| `ROOT_MD_BATCH_R1_001.md` | tracked clean | HIGH | Librarian batch report |
| `ROOT_MD_BATCH_R2_001.md` | tracked clean | HIGH | Librarian batch report |
| `ROOT_MD_BATCH_R4_001.md` | tracked clean | HIGH | Librarian batch report |
| `ROOT_MD_BATCH_R7_001.md` | tracked clean | HIGH | Librarian batch report |
| `ROOT_MD_INVENTORY_001.md` | tracked clean | HIGH | Inventory report |
| `ROOT_MD_PILOT_MOVE_001.md` | tracked clean | HIGH | Pilot move report |
| `ROOT_MD_REORGANIZATION_PLAN_001.md` | tracked clean | HIGH | Root reorganization operational plan |
| `RUNTIME_EVENT_STREAM_DESIGN_REPORT_001.md` | tracked clean | HIGH | Design report |
| `RUNTIME_EVENT_STREAM_IMPLEMENTATION_REPORT_001.md` | tracked clean | HIGH | Implementation report |
| `SCHEMA_SLIMMING_STAGE_2_FEATURE_FLAG_PATCH_REPORT_001.md` | tracked clean | HIGH | Patch report |
| `SESSION_ANALYTICS_V1_IMPLEMENTATION_REPORT_001.md` | tracked clean | HIGH | Implementation report |
| `SHADOW_TELEMETRY_PHASE_B_BUILTIN_RECOVERY_ENABLE_001.md` | tracked clean | HIGH | PHASE_B_ENABLE_FAILED operational record |
| `SHADOW_TELEMETRY_PHASE_B_CONTROLLED_ENABLE_001.md` | tracked clean | HIGH | Enable operational record |
| `SHADOW_TELEMETRY_PHASE_B_SMOKE_ENABLE_001.md` | tracked clean | HIGH | Smoke enable operational record |
| `TRADER_REFACTOR_BATCH_001_REPORT.md` | tracked clean | HIGH | Batch report (committed e76581fb) |
| `WEEKLY_REVIEW_ENGINE_SOURCE_OF_TRUTH_PATCH_REPORT_001.md` | tracked clean | HIGH | Patch report |
| `ROOT_MD_BATCH_R7_COMMIT_REPORT_001.md` | **untracked** | HIGH | This session's commit report |

---

## 6. MOVE_TO_DOCS_RESEARCH (2 files)

| File | Git State | Confidence | Reason |
|------|-----------|-----------|--------|
| `HYPOTHESIS_LEDGER_RECONSTRUCTION.md` | tracked clean | HIGH | `Mode: READ ONLY`, Role: Quant Research Historian — research record |
| `N100_INTERPRETATION_MATRIX.md` | tracked clean | HIGH | `Mode: READ ONLY`, Role: Quant Research Governor — N=100 interpretation matrix |

---

## 7. DUPLICATE_DO_NOT_STAGE (1 file)

| File | Git State | Confidence | Action |
|------|-----------|-----------|--------|
| `RESEARCH_AUTHORITY_MAP_V2.md` | untracked | HIGH | Byte-for-byte identical to committed `docs/research/RESEARCH_AUTHORITY_MAP_V2.md` (verified by `diff` in R7). Safe to `rm`. |

---

## 8. Risk Notes

**Risk 1 — CURRENT_PROJECT_STATUS.md is modified** (tracked dirty): Content is stale — it was last substantively updated 2026-06-20 and does not yet reflect: Trader Refactor Batch 1, paper validation, architecture plan, Agent OS, or root markdown cleanup. This should be updated in a separate CLASS 3 docs task before Batch 2 planning.

**Risk 2 — Tracked file moves require `git mv`**: All 108 move-candidate files (22 arch + 36 audit + 48 reports + 2 research) are TRACKED files. Moving them requires `git mv source dest` (not `mv`), otherwise git sees a delete + new file rather than a rename, breaking git history for those files.

**Risk 3 — KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md**: Classified as MOVE_TO_DOCS_REPORTS since it's a dated historical snapshot, not the live `KNOWN_ISSUES.md`. Confidence HIGH.

**Risk 4 — Large move batch**: 108 tracked files to move using `git mv`. Recommend splitting into 3–4 batches by destination to keep commits manageable and verifiable.

---

## 9. Recommended Next Move Batches

Since all move candidates are TRACKED files, `git mv` is required. The moves will be staged automatically.

### Batch T1 — Architecture (22 files)
```bash
git mv CANDIDATE_LIFECYCLE_ANALYTICS_V1_DESIGN_001.md docs/architecture/
git mv EVENT_CATALOG_V1.md docs/architecture/
# ... (20 more)
```
Commit: `docs: batch T1 move tracked architecture docs`

### Batch T2 — Audits (36 files)
```bash
git mv CANDIDATE_FUNNEL_EVIDENCE_001.md docs/audits/
git mv CANDIDATE_LIFECYCLE_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md docs/audits/
# ... (34 more)
```
Commit: `docs: batch T2 move tracked audit docs`

### Batch T3 — Reports part 1 (25 files)
Move first half of the 49 report candidates.

### Batch T4 — Reports part 2 + Research (25 + 2 files)
Move second half of reports + 2 research files.

### Housekeeping
- `rm RESEARCH_AUTHORITY_MAP_V2.md` (duplicate delete, can include in any commit)
- `git add ROOT_MD_BATCH_R7_COMMIT_REPORT_001.md docs/reports/ROOT_MD_BATCH_R7_COMMIT_REPORT_001.md` after moving

---

## 10. Final Verdict

```
READY_FOR_TRACKED_ROOT_DOC_MOVE_PLAN
```

**Summary:** 130 root `.md` files classified. 20 are designated entrypoints (keep in root). 108 tracked files are clear move candidates — all HIGH confidence — routing to `docs/architecture/` (22), `docs/audits/` (36), `docs/reports/` (48), `docs/research/` (2). 1 untracked `ROOT_MD_BATCH_R7_COMMIT_REPORT_001.md` goes to `docs/reports/`. 1 duplicate (`RESEARCH_AUTHORITY_MAP_V2.md`) to delete. Zero files require manual review.

**Key difference from prior batches:** All move candidates are TRACKED files — `git mv` required, not `mv`. This produces clean rename tracking in git history.
