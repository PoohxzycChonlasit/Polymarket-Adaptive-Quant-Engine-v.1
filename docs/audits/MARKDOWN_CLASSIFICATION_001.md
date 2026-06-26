# MARKDOWN_CLASSIFICATION_001

**Task:** REPOSITORY_ORGANIZATION_AUDIT_001  
**Mode:** DISCOVERY ONLY  
**Date:** 2026-06-26  
**Scope:** All 1,003 markdown files in the repository

---

## Overview

| Location | MD Count | Notes |
|---|---|---|
| Root directory | 395 | Primary tech debt |
| docs/ (all subdirs) | 499 | Organized but mixed quality |
| docs/research/ | 352 | Largest subfolder — 149 at root level |
| runtime/ | ~15 | Research state, reports |
| research/ | 8 | Session notes |
| scratch/ | 6 | Scratch notes |
| archive/ | 10 | Archived docs |
| tests/ | 0 | Correct |
| polymarket/ | 0 | Correct |
| utils/ | 0 | Correct |
| config/ | 0 | Correct |
| tools/ | 0 | Correct |
| dashboard/ | 0 | Correct |
| hft/ | 0 | Correct |
| crypto_scalper/ | 0 | Correct |
| .codex/ | 12 | AI context docs |

---

## Root Markdown — Full Classification Table

The following classifies every significant root markdown file. Files with `*` are from the current session (2026-06-26).

### Class 1: AI Startup Context (Must Stay Root)

| File | Classification | Move? |
|---|---|---|
| CLAUDE.md | AI startup — project contract | NO |
| AGENTS.md | AI startup — agent registry | NO |
| CODEX_START_HERE.md | AI startup — read sequence | NO |
| CODEX_START_PROMPT.md | AI startup — system prompt | NO |
| MASTER_AGENT_ROUTER.md | AI startup — task routing | NO |
| PROJECT_RULES.md | AI startup — constraints | NO |
| CURRENT_PROJECT_STATUS.md | AI startup — live status | NO |
| README.md | Public documentation | NO |
| FILE_INDEX.md | Navigation index | NO (or docs/) |
| DOCUMENTATION_MAP.md | Navigation map | NO (or docs/) |

**Count: 10 files — stay in root**

---

### Class 2: Active Architecture / Design Documents

These represent canonical design decisions that are still load-bearing for the system.

| File | Target |
|---|---|
| ALWAYS_ACTIVE_ENGINE_V1_DESIGN_001.md | docs/architecture/ |
| ALWAYS_ACTIVE_RISK_MODEL_V1.md | docs/architecture/ |
| ANALYTICS_AUTHORITY_MATRIX_001.md | docs/architecture/ |
| ANALYTICS_CACHE_POLICY_001.md | docs/architecture/ |
| ANALYTICS_DEPENDENCY_BOUNDARY_001.md | docs/architecture/ |
| ANALYTICS_FAILSOFT_POLICY_001.md | docs/architecture/ |
| ANALYTICS_LOADER_V1_DESIGN_001.md | docs/architecture/ |
| ARCHITECTURE_FREEZE_DECISION_001.md | docs/architecture/ |
| ARCHITECTURE_FREEZE_REVIEW_001.md | docs/architecture/ |
| ARCHITECTURE_PRINCIPLE_COMPLIANCE_001.md | docs/architecture/ |
| BANKROLL_ENGINE_V1_DESIGN_001.md | docs/architecture/ |
| BANKROLL_PROMOTION_SYSTEM_V1.md | docs/architecture/ |
| BANKROLL_TIER_FRAMEWORK_V1.md | docs/architecture/ (DUPLICATE — resolve) |
| BANKROLL_TIER_RUNTIME_MAP_001.md | docs/architecture/ |
| BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md | docs/architecture/ |
| CANDIDATE_EVALUATION_PIPELINE_V1.md | docs/architecture/ |
| CAPACITY_ALLOCATION_ENGINE_V1.md | docs/architecture/ |
| CAPACITY_SCALING_MODEL_V1.md | docs/architecture/ |
| CAPACITY_THROTTLE_ENGINE_V1.md | docs/architecture/ |
| DECISION_FRAMEWORK_V1_DESIGN_001.md | docs/architecture/ |
| DECISION_GATE_HIERARCHY_V1.md | docs/architecture/ |
| DECISION_HIERARCHY_MATRIX_V1.md | docs/architecture/ |
| DECISION_LOG_SLIM_INDEX_DESIGN_001.md | docs/architecture/ |
| DECISION_RUNTIME_V1_DESIGN_001.md | docs/architecture/ |
| DYNAMIC_SHARE_MODEL_V1.md | docs/architecture/ |
| ENTRY_VETO_SYSTEM_V1.md | docs/architecture/ |
| EVENT_CATALOG_V1.md | docs/architecture/ |
| EVENT_CONSUMER_MATRIX_V1.md | docs/architecture/ |
| EVENT_DASHBOARD_STATE_MAP_V1.md | docs/architecture/ |
| EVENT_DROP_POLICY_V1.md | docs/architecture/ |
| EVENT_PRIORITY_MATRIX_V1.md | docs/architecture/ |
| EVENT_REPLAY_ARCHITECTURE_V1.md | docs/architecture/ |
| EVENT_SCHEMA_STANDARD_V1.md | docs/architecture/ |
| FINAL_SOURCE_OF_TRUTH_HIERARCHY_001.md | docs/architecture/ |
| GO_NO_GO_ENGINE_V1.md | docs/architecture/ |
| GOVERNANCE_BOOTSTRAP_001_DESIGN_PACKAGE.md | docs/architecture/ |
| GOVERNANCE_BOOTSTRAP_001_REFINED.md | docs/architecture/ |
| LOSS_CLUSTER_ENGINE_V1.md | docs/architecture/ |
| MAE_MFE_ANALYTICS_V1_DESIGN_001.md | docs/architecture/ |
| OBSERVABILITY_OPERATOR_V1_DESIGN.md | docs/architecture/ |
| ORDER_INTENT_GENERATION_V1.md | docs/architecture/ |
| POSITION_SIZING_ENGINE_V1_DESIGN_001.md | docs/architecture/ |
| POSITION_SIZING_MATRIX_V1.md | docs/architecture/ |
| PROJECT_OS_V1_DESIGN.md | docs/architecture/ |
| PROJECT_OS_V1_IMPLEMENTATION_ROADMAP.md | docs/architecture/ |
| QUANT_LIFECYCLE_INVENTORY_ENGINE.md | docs/architecture/ |
| RECOVERY_ENGINE_V1.md | docs/architecture/ |
| RISK_BUDGET_ENGINE_V1.md | docs/architecture/ |
| RUNTIME_EVENT_STREAM_V1.md | docs/architecture/ |
| RUNTIME_HEARTBEAT_SPEC_V1.md | docs/architecture/ |
| RUNTIME_STATE_MACHINE_V1.md | docs/architecture/ |
| RUNTIME_24_7_SELF_RECOVERY_HARDENING_DESIGN.md | docs/architecture/ |
| STORAGE_ARCHITECTURE_AUDIT_001.md | docs/architecture/ |
| STORAGE_ARCHITECTURE_ACTION_PLAN_001.md | docs/architecture/ |

**Count: ~54 files**

---

### Class 3: Active Research / Forensic Audit Documents

Findings from live sessions. Primary source for diagnosis.

| File | Subfolder Target | Session |
|---|---|---|
| ALWAYS_ACTIVE_IMPLEMENTATION_GAP_001.md | docs/research/runtime_health/ | |
| ALWAYS_ACTIVE_RUNTIME_GAP_AUDIT_001.md | docs/research/runtime_health/ | |
| CANDIDATE_FUNNEL_EVIDENCE_001.md | docs/research/session_edge/ | |
| CANDIDATE_PIPELINE_NEXT_ACTIONS_001.md | docs/research/session_edge/ | |
| CANDIDATE_PIPELINE_RUNTIME_VALIDATION_001.md | docs/research/session_edge/ | |
| CLOB_EMPTY_RESPONSE_FORENSIC_AUDIT.md | docs/research/runtime_health/ | |
| DEFENSIVE_CONFIDENCE_DISTRIBUTION_001.md | docs/research/session_edge/ | 2026-06-25 |
| DEFENSIVE_COUNTERFACTUAL_PASS_ANALYSIS_001.md | docs/research/session_edge/ | 2026-06-25 |
| DEFENSIVE_MODE_FORENSIC_VALIDATION_001.md | docs/research/session_edge/ | 2026-06-25 |
| DEFENSIVE_MODE_NEXT_ACTIONS_001.md | docs/research/session_edge/ | 2026-06-25 |
| DELTA_EXTREME_GATE_FORENSIC_AUDIT.md | docs/research/session_edge/ | |
| DIRECTIONAL_ASYMMETRY_RESOLUTION_001.md | docs/research/session_edge/ | |
| EDGE_INVENTORY_REPORT_V1_30_TRADE_EXPLORATORY_AUDIT.md | docs/research/performance/ | |
| EDGE_INVENTORY_REPORT_V1_30_TRADE_TARGET_AUDIT.md | docs/research/performance/ | |
| EVIDENCE_QUALITY_AUDIT.md | docs/audits/ | |
| EXECUTABLE_REALITY_AUDIT_001.md | docs/research/executable_truth/ | |
| EXECUTABLE_REALITY_AUDIT_V1.md | docs/research/executable_truth/ | |
| EXECUTABLE_REALITY_REVIEW_001.md | docs/research/executable_truth/ | |
| EXECUTABLE_TRUTH_RESOLUTION_001.md | docs/research/executable_truth/ | |
| EXECUTABLE_TRUTH_SCORE_V1.md | docs/research/executable_truth/ | |
| EXIT_EXECUTION_ROOT_CAUSE_AUDIT_001.md | docs/research/session_edge/ | |
| EXIT_FAILURE_DISTRIBUTION_001.md | docs/research/session_edge/ | |
| EXIT_LIFECYCLE_TRACE_001.md | docs/research/session_edge/ | |
| FIRST_BLOCKING_GATE_DISTRIBUTION_001.md | docs/research/session_edge/ | |
| FORWARD_VALIDATION_PROTOCOL_AUDIT.md | docs/audits/ | |
| HOLD_TIME_COLLAPSE_FORENSIC_001.md | docs/research/session_edge/ | |
| HYPOTHESIS_LEDGER_RECONSTRUCTION.md | docs/research/discovery/ | |
| IMPLEMENTATION_BLOCKER_REGISTRY_001.md | docs/research/ | |
| LOW_PRICE_EDGE_VALIDATION_001.md | docs/research/session_edge/ | |
| LOW_PRICE_TRUTH_RESOLUTION_DISCOVERY_001.md | docs/research/discovery/ | |
| MICRO_BANKROLL_EXECUTABILITY_ANALYSIS_001.md | docs/research/session_edge/ | 2026-06-25 |
| MICRO_RECOVERY_COUNTERFACTUAL_ANALYSIS_001.md | docs/research/session_edge/ | 2026-06-26* |
| MICRO_RECOVERY_NEXT_ACTIONS_001.md | docs/research/session_edge/ | 2026-06-26* |
| MICRO_RECOVERY_RISK_PLAN_ZERO_AUDIT_001.md | docs/research/session_edge/ | 2026-06-26* |
| MICRO_RECOVERY_TRAP_RESOLUTION_DESIGN_001.md | docs/research/session_edge/ | 2026-06-25 |
| MICRO_RECOVERY_ZERO_PIPELINE_TRACE_001.md | docs/research/session_edge/ | 2026-06-26* |
| MULTI_DAY_SIGNAL_FILTER_VALIDATION.md | docs/research/performance/ | |
| MULTIPLIER_INTERACTION_ANALYSIS_001.md | docs/research/session_edge/ | |
| MULTIPLIER_SENSITIVITY_ANALYSIS_001.md | docs/research/session_edge/ | |
| N100_INTERPRETATION_MATRIX.md | docs/research/ | |
| NEAR_MISS_ANALYSIS_001.md | docs/research/session_edge/ | |
| NO_EV_EXIT_REASON_FORENSIC_AUDIT_001.md | docs/research/session_edge/ | |
| NO_SIDE_FAILURE_FORENSIC_AUDIT_001.md | docs/research/session_edge/ | |
| NO_TRADE_AFTER_ENTRY_DISTRIBUTION_001.md | docs/research/session_edge/ | |
| NO_TRADE_NEXT_ACTION_PLAN_001.md | docs/research/session_edge/ | |
| NO_TRADE_PIPELINE_STAGE_MAP_001.md | docs/research/session_edge/ | |
| NO_TRADE_REJECT_REASON_DISTRIBUTION_001.md | docs/research/session_edge/ | |
| NO_TRADE_ROOT_CAUSE_AUDIT_001.md | docs/research/session_edge/ | |
| ORDERBOOK_CACHE_AUDIT_001.md | docs/research/runtime_health/ | |
| ORDERBOOK_FAILURE_TREE_001.md | docs/research/runtime_health/ | |
| ORDERBOOK_HTTP_ANALYSIS_001.md | docs/research/runtime_health/ | |
| ORDERBOOK_MARKET_BREAKDOWN_001.md | docs/research/runtime_health/ | |
| ORDERBOOK_RATE_LIMIT_ANALYSIS_001.md | docs/research/runtime_health/ | |
| ORDERBOOK_ROOT_CAUSE_AUDIT_001.md | docs/research/runtime_health/ | |
| ORDERBOOK_TIMELINE_ANALYSIS_001.md | docs/research/runtime_health/ | |
| POST_30_TRADE_EV_EDGE_FORENSIC_AUDIT_001.md | docs/research/performance/ | |
| POST_TRADE_STARVATION_FUNNEL_001.md | docs/research/session_edge/ | |
| PROBABILITY_EV_EDGE_FORENSIC_AUDIT_001.md | docs/research/session_edge/ | |
| QUANT_CORE_ARCHITECTURE_CONSISTENCY_AUDIT_001.md | docs/audits/ | |
| QUANT_CORE_CONTRADICTION_REGISTRY_001.md | docs/audits/ | |
| QUANT_CORE_IMPLEMENTATION_SEQUENCE_001.md | docs/audits/ | |
| QUANT_CORE_SOURCE_OF_TRUTH_MAP_001.md | docs/audits/ | |
| QUANT_KNOWLEDGE_GOVERNANCE_AUDIT_001.md | docs/audits/ | |
| QUANT_KNOWLEDGE_REFRESH_PLAN_001.md | docs/research/ | |
| REPLAY_METHODOLOGY_VALIDATION_AUDIT_001.md | docs/research/performance/ | |
| RISK_MODE_TRANSITION_TIMELINE_001.md | docs/research/session_edge/ | 2026-06-25 |
| RISK_PLAN_ZERO_DISTRIBUTION_001.md | docs/research/session_edge/ | 2026-06-26* |
| RISK_PLAN_ZERO_FORENSIC_AUDIT_001.md | docs/research/session_edge/ | |
| SCHEMA_SLIMMING_FEASIBILITY_AUDIT_001.md | docs/audits/ | |
| SELECTION_BIAS_AUDIT.md | docs/audits/ | |
| SHADOW_SIZING_REPLAY_AUDIT_001.md | docs/research/session_edge/ | |
| SIGNAL_FILTER_COUNTERFACTUAL_REPLAY_001.md | docs/research/session_edge/ | |
| SIGNAL_FILTER_PARAMETER_SWEEP_001.md | docs/research/session_edge/ | |
| SIGNAL_QUALITY_RESOLUTION_001.md | docs/research/session_edge/ | |
| SIZING_MULTIPLIER_ROOT_CAUSE_AUDIT_001.md | docs/research/session_edge/ | |
| SIZING_MULTIPLIER_WATERFALL_001.md | docs/research/session_edge/ | |
| SIZING_MULTIPLIER_WATERFALL_V2_001.md | docs/research/session_edge/ | |
| STOP_LOSS_COMPARATOR_EVIDENCE_AUDIT_001.md | docs/research/session_edge/ | |
| STOP_LOSS_COUNTERFACTUAL_AUDIT_001.md | docs/research/session_edge/ | |
| STOP_LOSS_MECHANICS_VALIDATION_001.md | docs/research/session_edge/ | |
| STOP_LOSS_REDESIGN_OPTIONS_001.md | docs/research/session_edge/ | |
| STOP_LOSS_ROOT_CAUSE_RESOLUTION_001.md | docs/research/session_edge/ | |
| STOP_LOSS_SHADOW_RUNTIME_EVIDENCE_AUDIT_001.md | docs/research/session_edge/ | |
| SUB_5C_EXECUTION_REALITY_AUDIT.md | docs/research/session_edge/ | |
| YES_EV_FAILURE_FORENSIC_AUDIT.md | docs/research/session_edge/ | |

**Count: ~80 files**

---

### Class 4: Patch / Implementation / Commit Report History (~120 files)

Historical records. Move to `docs/reports/` organized by year-month or by system area.

Key pattern groups:
- `*_COMMIT_REPORT*.md` — commit records
- `*_IMPLEMENTATION_REPORT*.md` — implementation summaries
- `*_PRE_COMMIT_AUDIT*.md` — pre-commit checklists
- `PATCH_*_COMMIT_REPORT*.md` — patch commit records
- `PATCH_*_IMPLEMENTATION_REPORT*.md` — patch implementation records

Examples:
- `CANDIDATE_LIFECYCLE_ANALYTICS_V1_COMMIT_REPORT_001.md`
- `CANDIDATE_LIFECYCLE_ANALYTICS_V1_IMPLEMENTATION_REPORT_001.md`
- `COLD_JSONL_COMPRESSION_DRY_RUN_COMMIT_REPORT_001.md`
- `COMPRESS_RESTORE_PATCH_COMMIT_REPORT_001.md`
- `DASHBOARD_API_V0_COMMIT_REPORT_001.md`
- `OPTION_D_PHASE_A_COMMIT_REPORT.md`
- `PATCH_OBSERVABILITY_001_COMMIT_REPORT.md`
- `REACT_DASHBOARD_V0_COMMIT_REPORT_001.md`
- `REGIME_ANALYTICS_V1_COMMIT_REPORT_001.md`
- `SCHEMA_SLIMMING_STAGE_1_COMMIT_REPORT_001.md`
- `SESSION_ANALYTICS_V1_COMMIT_REPORT_001.md`

**All move to `docs/reports/`.**

---

### Class 5: Duplicate Documents

| Root File (small/stub) | docs/ File (larger/canonical) | Action |
|---|---|---|
| `KNOWN_ISSUES.md` (267B) | `docs/KNOWN_ISSUES.md` (18.7KB) | Root is stub — remove after confirming docs/ is current |
| `PROJECT_STRUCTURE.md` (671B) | `docs/PROJECT_STRUCTURE.md` (13.4KB) | Root is stub — remove after confirming docs/ is current |
| `BANKROLL_TIER_FRAMEWORK_V1.md` (4.5KB) | `docs/BANKROLL_TIER_FRAMEWORK_V1.md` (same) | Verify which is canonical, keep one |
| `CLAUDE.md` (active, 4.9KB) | `archive/CLAUDE.md` (older, 1.9KB) | Root is active; archive copy is intentionally archived |
| `PROJECT_CENSUS_AUDIT_001.md` (15.8KB) | — | Check if superseded by this audit |

---

### Class 6: Date-Specific Working Notes

These are named with dates and are historical records of specific sessions.

| File | Date | Move Target |
|---|---|---|
| `overnight_maturity_check_2026-05-19.md` | 2026-05-19 | docs/research/sessions/ |
| `repo_canonical_check_2026-05-19.md` | 2026-05-19 | docs/audits/ |
| `runtime_clean_validation_2026-05-19.md` | 2026-05-19 | docs/reports/ |
| `stop_loss_concentration_diagnosis_2026-05-19.md` | 2026-05-19 | docs/research/session_edge/ |
| `KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md` | 2026-05-14 | docs/audits/ |
| `DOC_TRUTH_RECONCILIATION_2026-05-14.md` | 2026-05-14 | docs/audits/ |

---

### Class 7: Observability / Operational Plans (~25 files)

Plans for feature implementation. Primarily in root because they were created during work sessions.

| File | Target |
|---|---|
| COLD_JSONL_COMPRESSION_REAL_IMPLEMENTATION_PLAN_001.md | docs/design/ |
| COLD_JSONL_COMPRESSION_TOOL_DESIGN_001.md | docs/design/ |
| DASHBOARD_DISCOVERY_AUDIT_001.md | docs/audits/ |
| DASHBOARD_STATE_DESIGN_001.md | docs/design/ |
| DELTA_EXTREME_SHADOW_OVERLAY_IMPLEMENTATION_PLAN_001.md | docs/design/ |
| DELTA_EXTREME_SHADOW_OVERLAY_SPEC_001.md | docs/design/ |
| EXECUTION_PAPER_RUNTIME_PHASE_B_JOURNAL_WIRING_PLAN_001.md | docs/design/ |
| EXECUTION_SHADOW_FILTER_SPEC_001.md | docs/design/ |
| EXECUTION_SHADOW_TELEMETRY_IMPLEMENTATION_PLAN_001.md | docs/design/ |
| EXIT_IMPLEMENTATION_PLAN_001.md | docs/design/ |
| OPTION_D_SHADOW_IMPLEMENTATION_PLAN_001.md | docs/design/ |
| OPTION_D_SHADOW_IMPLEMENTATION_SPEC_001.md | docs/design/ |
| PAPER_STOP_FAILSAFE_AUDIT_001.md | docs/audits/ |
| PATCH_SIGNAL_001_EV_CAP_YES_PROB_FLOOR_DESIGN.md | docs/design/ |
| POSITION_SIZING_HOTFIX_NEXT_ACTIONS_001.md | docs/research/session_edge/ |
| RUNTIME_STORAGE_POLICY_DESIGN_001.md | docs/design/ |
| SCHEMA_SLIMMING_IMPLEMENTATION_PLAN_001.md | docs/design/ |
| SHADOW_TELEMETRY_PHASE_B_DESIGN_001.md | docs/design/ |
| SHADOW_TELEMETRY_PHASE_B_IMPLEMENTATION_PLAN_001.md | docs/design/ |
| STOP_LOSS_POLICY_FIX_PLAN_001.md | docs/design/ |
| STOP_LOSS_SHADOW_COMPARATOR_PLAN_001.md | docs/design/ |
| STOP_LOSS_SHADOW_POLICY_PLAN_001.md | docs/design/ |

---

### Class 8: Docs Within docs/ — Needing Classification

The `docs/research/` root has **149 files** that are not in subdirectories. These need to be classified into the existing subfolders:
- `docs/research/campaigns/`
- `docs/research/candidate_graveyard/`
- `docs/research/discovery/`
- `docs/research/executable_truth/`
- `docs/research/frontiers/`
- `docs/research/path_truth/`
- `docs/research/performance/`
- `docs/research/runtime_health/`
- `docs/research/session_edge/`
- `docs/research/sessions/`
- `docs/research/watchlists/`

This is a secondary cleanup that can follow root cleanup.

---

## Duplicate Summary

| Duplicate Type | Count | Action |
|---|---|---|
| Root stub vs docs/ canonical | 3 | Remove root stub after verification |
| Same content both locations | 1 (BANKROLL_TIER_FRAMEWORK_V1) | Verify canonical, delete one |
| Archive copy vs active root | 1 (CLAUDE.md) | Archive is intentional |
| Superseded by newer doc | ~30 (estimated) | Review individually |

---

## Files That Are Candidates for Deletion (Not Move)

| File | Reason |
|---|---|
| `task.md` (863B) | Temporary task note from a prior session |
| `KNOWN_ISSUES.md` (267B) | Stub — docs/ has the real one (18.7KB) |
| `PROJECT_STRUCTURE.md` (671B) | Stub — docs/ has the real one (13.4KB) |
| `docs.zip` | Snapshot of docs at a point in time — check if still useful |
| `.env.backup.local` | Sensitive credential backup in repo root |
| `ROOT_MD_INVENTORY_001.md` | Superseded by this audit |
| `ROOT_MD_REORGANIZATION_PLAN_001.md` | Superseded by SAFE_MOVE_PLAN_001.md |
| `ROOT_MD_BATCH_1_MOVE_REPORT_001.md` | Historical record of partial cleanup |
| `ROOT_MD_BATCH_2_MOVE_REPORT_001.md` | Historical record of partial cleanup |
