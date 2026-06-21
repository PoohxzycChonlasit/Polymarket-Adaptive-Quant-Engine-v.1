# Root Markdown Files Reorganization Plan
**ID**: ROOT_MD_REORGANIZATION_PLAN_001  
**Status**: PLAN_ONLY_DRAFT  
**Final Verdict**: NEEDS_MANUAL_REVIEW  

---

## 1. Governance Keep List (ROOT_KEEP)
The following 8 files are marked as **ROOT_KEEP** and **must not be moved**. They serve as IDE customizations, developer entry points, indexes, or high-level maps.

| Filename | Reason to Retain |
| :--- | :--- |
| `README.md` | Standard entry point for any developer/contributor. |
| `AGENTS.md` | Auto-loaded customization rules file used by agentic IDE interfaces. |
| `PROJECT_RULES.md` | Core safety guidelines loaded automatically by agent agents. |
| `CURRENT_PROJECT_STATUS.md` | Critical runtime/reconciliation status log referenced at startup. |
| `CODEX_START_HERE.md` | Canonical starting point for developer session initiation. |
| `MASTER_AGENT_ROUTER.md` | Routing rules and instructions for selecting AI roles. |
| `FILE_INDEX.md` | Full repository map indexing files. |
| `DOCUMENTATION_MAP.md` | Logical mapping of project docs structure. |

---

## 2. Target Directories Definition
The files will be relocated into the following logical subdirectories:
* `docs/governance/`: Standards, instructions, and high-level manuals.
* `docs/architecture/`: Technical specifications, engine plans, and structural map files.
* `docs/audits/`: Forensic audits, code audits, and checkpoint audits.
* `docs/reports/`: Implementation reports, commit reports, and status summaries.
* `docs/evidence/`: Validation run logs, SQLite dry run results, and telemetries.
* `docs/research/`: Trading research plans and hypothesis ledgers.
* `docs/runtime/`: Active run configs, restart workflows, and deploy checklists.
* `docs/archive/root_md_legacy/`: Reserved directory for unclassified legacy files.

---

## 3. Conflict Detection
A search of the existing `docs/` folder was performed. The following conflicts were identified:
* [CONFLICT] Duplicate filename collision with existing file: docs\KNOWN_ISSUES.md
* [CONFLICT] Duplicate filename collision with existing file: docs\PROJECT_STRUCTURE.md

---

## 4. Reorganization Matrix
The following matrix maps every root markdown file to its proposed target path, indicating eligibility and batch assignment.

| Filename | Category | Target Path | Move Allowed | Batch | Reason / Retain Context |
| :--- | :---: | :--- | :---: | :---: | :--- |
| `AGENTS.md` | Governance | `docs/governance/AGENTS.md` | **no** | N/A | Core system file or IDE entry point; must remain at root. |
| `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md` | Architecture | `docs/architecture/BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `CHATGPT_PROJECT_START_PROMPT.md` | Governance | `docs/governance/CHATGPT_PROJECT_START_PROMPT.md` | **yes** | Batch 4 | Relocate to central Governance directory. |
| `CLAUDE.md` | Governance | `docs/governance/CLAUDE.md` | **yes** | Batch 4 | Relocate to central Governance directory. |
| `CODEX_START_HERE.md` | Governance | `docs/governance/CODEX_START_HERE.md` | **no** | N/A | Core system file or IDE entry point; must remain at root. |
| `CODEX_START_PROMPT.md` | Governance | `docs/governance/CODEX_START_PROMPT.md` | **yes** | Batch 4 | Relocate to central Governance directory. |
| `CURRENT_PROJECT_STATUS.md` | Report | `docs/reports/CURRENT_PROJECT_STATUS.md` | **no** | N/A | Core system file or IDE entry point; must remain at root. |
| `DECISION_LOG_SLIM_INDEX_BOUNDED_VALIDATION_001.md` | Evidence | `docs/evidence/DECISION_LOG_SLIM_INDEX_BOUNDED_VALIDATION_001.md` | **yes** | Batch 2 | Relocate to central Evidence directory. |
| `DECISION_LOG_SLIM_INDEX_COMMIT_REPORT_001.md` | Report | `docs/reports/DECISION_LOG_SLIM_INDEX_COMMIT_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `DECISION_LOG_SLIM_INDEX_DESIGN_001.md` | Architecture | `docs/architecture/DECISION_LOG_SLIM_INDEX_DESIGN_001.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `DECISION_LOG_SLIM_INDEX_FULL_BUILD_001.md` | Runtime | `docs/runtime/DECISION_LOG_SLIM_INDEX_FULL_BUILD_001.md` | **yes** | Batch 3 | Relocate to central Runtime directory. |
| `DECISION_LOG_SLIM_INDEX_IMPLEMENTATION_REPORT_001.md` | Report | `docs/reports/DECISION_LOG_SLIM_INDEX_IMPLEMENTATION_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `DECISION_LOG_SLIM_INDEX_INTEGRATION_AUDIT_001.md` | Audit | `docs/audits/DECISION_LOG_SLIM_INDEX_INTEGRATION_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `DECISION_LOG_SLIM_INDEX_INTEGRATION_COMMIT_REPORT_001.md` | Report | `docs/reports/DECISION_LOG_SLIM_INDEX_INTEGRATION_COMMIT_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `DECISION_LOG_SLIM_INDEX_INTEGRATION_IMPLEMENTATION_REPORT_001.md` | Report | `docs/reports/DECISION_LOG_SLIM_INDEX_INTEGRATION_IMPLEMENTATION_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `DECISION_LOG_SLIM_INDEX_INTEGRATION_PRE_COMMIT_AUDIT_001.md` | Audit | `docs/audits/DECISION_LOG_SLIM_INDEX_INTEGRATION_PRE_COMMIT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `DECISION_LOG_SLIM_INDEX_PRE_COMMIT_AUDIT_001.md` | Audit | `docs/audits/DECISION_LOG_SLIM_INDEX_PRE_COMMIT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `DELTA_EXTREME_CONFLICT_RESOLUTION_AUDIT_001.md` | Audit | `docs/audits/DELTA_EXTREME_CONFLICT_RESOLUTION_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `DELTA_EXTREME_EXECUTABLE_TRUTH_AUDIT_001.md` | Audit | `docs/audits/DELTA_EXTREME_EXECUTABLE_TRUTH_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `DELTA_EXTREME_GATE_FORENSIC_AUDIT.md` | Audit | `docs/audits/DELTA_EXTREME_GATE_FORENSIC_AUDIT.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `DELTA_EXTREME_SHADOW_OVERLAY_IMPLEMENTATION_PLAN_001.md` | Architecture | `docs/architecture/DELTA_EXTREME_SHADOW_OVERLAY_IMPLEMENTATION_PLAN_001.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `DELTA_EXTREME_SHADOW_OVERLAY_PHASE_A_COMMIT_REPORT.md` | Report | `docs/reports/DELTA_EXTREME_SHADOW_OVERLAY_PHASE_A_COMMIT_REPORT.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `DELTA_EXTREME_SHADOW_OVERLAY_PHASE_A_IMPLEMENTATION_001_REPORT.md` | Report | `docs/reports/DELTA_EXTREME_SHADOW_OVERLAY_PHASE_A_IMPLEMENTATION_001_REPORT.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `DELTA_EXTREME_SHADOW_OVERLAY_PHASE_A_PRE_COMMIT_AUDIT_001.md` | Audit | `docs/audits/DELTA_EXTREME_SHADOW_OVERLAY_PHASE_A_PRE_COMMIT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `DELTA_EXTREME_SHADOW_OVERLAY_SPEC_001.md` | Architecture | `docs/architecture/DELTA_EXTREME_SHADOW_OVERLAY_SPEC_001.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `DELTA_SHADOW_HOOKPOINT_AUDIT_001.md` | Audit | `docs/audits/DELTA_SHADOW_HOOKPOINT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `DELTA_SHADOW_PRE_IMPLEMENTATION_AUDIT_001.md` | Audit | `docs/audits/DELTA_SHADOW_PRE_IMPLEMENTATION_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `DOCUMENTATION_MAP.md` | Governance | `docs/governance/DOCUMENTATION_MAP.md` | **no** | N/A | Core system file or IDE entry point; must remain at root. |
| `DOC_TRUTH_RECONCILIATION_2026-05-14.md` | Governance | `docs/governance/DOC_TRUTH_RECONCILIATION_2026-05-14.md` | **yes** | Batch 4 | Relocate to central Governance directory. |
| `DUPLICATE_OPEN_FORENSIC_AUDIT_001.md` | Audit | `docs/audits/DUPLICATE_OPEN_FORENSIC_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `ENTRY_FUNNEL_ROOT_CAUSE_AUDIT_001.md` | Audit | `docs/audits/ENTRY_FUNNEL_ROOT_CAUSE_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `ENVIRONMENT_RECOVERY_REPORT_001.md` | Report | `docs/reports/ENVIRONMENT_RECOVERY_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `EVIDENCE_QUALITY_AUDIT.md` | Audit | `docs/audits/EVIDENCE_QUALITY_AUDIT.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `EXECUTION_DATASET_PURITY_AUDIT_001.md` | Audit | `docs/audits/EXECUTION_DATASET_PURITY_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `EXECUTION_FILTER_IMPACT_AUDIT_001.md` | Audit | `docs/audits/EXECUTION_FILTER_IMPACT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `EXECUTION_OFFLINE_SHADOW_FILTER_AUDIT_001.md` | Audit | `docs/audits/EXECUTION_OFFLINE_SHADOW_FILTER_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `EXECUTION_PAPER_RUNTIME_PHASE_A_COMMIT_REPORT_001.md` | Report | `docs/reports/EXECUTION_PAPER_RUNTIME_PHASE_A_COMMIT_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `EXECUTION_PAPER_RUNTIME_PHASE_A_DRY_RUN_VALIDATION_001.md` | Evidence | `docs/evidence/EXECUTION_PAPER_RUNTIME_PHASE_A_DRY_RUN_VALIDATION_001.md` | **yes** | Batch 2 | Relocate to central Evidence directory. |
| `EXECUTION_PAPER_RUNTIME_PHASE_A_IMPLEMENTATION_REPORT_001.md` | Report | `docs/reports/EXECUTION_PAPER_RUNTIME_PHASE_A_IMPLEMENTATION_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `EXECUTION_PAPER_RUNTIME_PHASE_A_PRE_COMMIT_AUDIT_001.md` | Audit | `docs/audits/EXECUTION_PAPER_RUNTIME_PHASE_A_PRE_COMMIT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `EXECUTION_PAPER_RUNTIME_PHASE_B_JOURNAL_WIRING_PLAN_001.md` | Architecture | `docs/architecture/EXECUTION_PAPER_RUNTIME_PHASE_B_JOURNAL_WIRING_PLAN_001.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `EXECUTION_PAPER_RUNTIME_PHASE_C_FULL_ELIGIBLE_REPLAY_COMPAT_001.md` | Evidence | `docs/evidence/EXECUTION_PAPER_RUNTIME_PHASE_C_FULL_ELIGIBLE_REPLAY_COMPAT_001.md` | **yes** | Batch 2 | Relocate to central Evidence directory. |
| `EXECUTION_PAPER_RUNTIME_PHASE_C_FULL_ELIGIBLE_REPLAY_COMPAT_RERUN_001.md` | Evidence | `docs/evidence/EXECUTION_PAPER_RUNTIME_PHASE_C_FULL_ELIGIBLE_REPLAY_COMPAT_RERUN_001.md` | **yes** | Batch 2 | Relocate to central Evidence directory. |
| `EXECUTION_SHADOW_FILTER_SPEC_001.md` | Architecture | `docs/architecture/EXECUTION_SHADOW_FILTER_SPEC_001.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `EXECUTION_SHADOW_TELEMETRY_IMPLEMENTATION_PLAN_001.md` | Architecture | `docs/architecture/EXECUTION_SHADOW_TELEMETRY_IMPLEMENTATION_PLAN_001.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `EXECUTION_SHADOW_TELEMETRY_OFFLINE_COMMIT_REPORT_001.md` | Report | `docs/reports/EXECUTION_SHADOW_TELEMETRY_OFFLINE_COMMIT_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `EXECUTION_SHADOW_TELEMETRY_OFFLINE_IMPLEMENTATION_REPORT_001.md` | Report | `docs/reports/EXECUTION_SHADOW_TELEMETRY_OFFLINE_IMPLEMENTATION_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `EXECUTION_SHADOW_TELEMETRY_OFFLINE_PRE_COMMIT_AUDIT_001.md` | Audit | `docs/audits/EXECUTION_SHADOW_TELEMETRY_OFFLINE_PRE_COMMIT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `EXECUTION_SIGNAL_CLUSTER_FORENSIC_AUDIT_001.md` | Audit | `docs/audits/EXECUTION_SIGNAL_CLUSTER_FORENSIC_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `EXECUTION_SIGNAL_FORENSIC_AUDIT_001.md` | Audit | `docs/audits/EXECUTION_SIGNAL_FORENSIC_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `FILE_INDEX.md` | Governance | `docs/governance/FILE_INDEX.md` | **no** | N/A | Core system file or IDE entry point; must remain at root. |
| `FORWARD_VALIDATION_PROTOCOL_AUDIT.md` | Audit | `docs/audits/FORWARD_VALIDATION_PROTOCOL_AUDIT.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `FULL_SQLITE_REAL_DATA_VALIDATION_001.md` | Evidence | `docs/evidence/FULL_SQLITE_REAL_DATA_VALIDATION_001.md` | **yes** | Batch 2 | Relocate to central Evidence directory. |
| `GITIGNORE_HYGIENE_COMMIT_REPORT_001.md` | Report | `docs/reports/GITIGNORE_HYGIENE_COMMIT_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `GIT_PROCESS_STORM_VENV_BACKUP_FIX_REPORT_001.md` | Report | `docs/reports/GIT_PROCESS_STORM_VENV_BACKUP_FIX_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `HISTORICAL_POSITION_IDENTITY_DESIGN_AUDIT_001.md` | Audit | `docs/audits/HISTORICAL_POSITION_IDENTITY_DESIGN_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `HISTORICAL_POSITION_IDENTITY_PATCH_COMMIT_REPORT_001.md` | Report | `docs/reports/HISTORICAL_POSITION_IDENTITY_PATCH_COMMIT_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `HISTORICAL_POSITION_IDENTITY_PATCH_IMPLEMENTATION_REPORT_001.md` | Report | `docs/reports/HISTORICAL_POSITION_IDENTITY_PATCH_IMPLEMENTATION_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `HISTORICAL_POSITION_IDENTITY_PATCH_PRE_COMMIT_AUDIT_001.md` | Audit | `docs/audits/HISTORICAL_POSITION_IDENTITY_PATCH_PRE_COMMIT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `HYPOTHESIS_LEDGER_RECONSTRUCTION.md` | Research | `docs/research/HYPOTHESIS_LEDGER_RECONSTRUCTION.md` | **yes** | Batch 3 | Relocate to central Research directory. |
| `INVENTORY_REPLAY_RESEARCH_PLAN.md` | Research | `docs/research/INVENTORY_REPLAY_RESEARCH_PLAN.md` | **yes** | Batch 3 | Relocate to central Research directory. |
| `JOINED_RECORDS_BUILDER_BOUNDED_REAL_DATA_VALIDATION_001.md` | Evidence | `docs/evidence/JOINED_RECORDS_BUILDER_BOUNDED_REAL_DATA_VALIDATION_001.md` | **yes** | Batch 2 | Relocate to central Evidence directory. |
| `JOINED_RECORDS_BUILDER_COMMIT_REPORT_001.md` | Report | `docs/reports/JOINED_RECORDS_BUILDER_COMMIT_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `JOINED_RECORDS_BUILDER_FULL_REAL_DATA_RERUN_001.md` | Evidence | `docs/evidence/JOINED_RECORDS_BUILDER_FULL_REAL_DATA_RERUN_001.md` | **yes** | Batch 2 | Relocate to central Evidence directory. |
| `JOINED_RECORDS_BUILDER_IMPLEMENTATION_REPORT_001.md` | Report | `docs/reports/JOINED_RECORDS_BUILDER_IMPLEMENTATION_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `JOINED_RECORDS_BUILDER_MEMORY_PATCH_COMMIT_REPORT_001.md` | Report | `docs/reports/JOINED_RECORDS_BUILDER_MEMORY_PATCH_COMMIT_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `JOINED_RECORDS_BUILDER_MEMORY_PATCH_IMPLEMENTATION_REPORT_001.md` | Report | `docs/reports/JOINED_RECORDS_BUILDER_MEMORY_PATCH_IMPLEMENTATION_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `JOINED_RECORDS_BUILDER_MEMORY_PATCH_PRE_COMMIT_AUDIT_001.md` | Audit | `docs/audits/JOINED_RECORDS_BUILDER_MEMORY_PATCH_PRE_COMMIT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `JOINED_RECORDS_BUILDER_PERFORMANCE_AUDIT_001.md` | Audit | `docs/audits/JOINED_RECORDS_BUILDER_PERFORMANCE_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `JOINED_RECORDS_BUILDER_PLAN_001.md` | Architecture | `docs/architecture/JOINED_RECORDS_BUILDER_PLAN_001.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `JOINED_RECORDS_BUILDER_POST_PATCH_BOUNDED_BENCHMARK_001.md` | Evidence | `docs/evidence/JOINED_RECORDS_BUILDER_POST_PATCH_BOUNDED_BENCHMARK_001.md` | **yes** | Batch 2 | Relocate to central Evidence directory. |
| `JOINED_RECORDS_BUILDER_PRE_COMMIT_AUDIT_001.md` | Audit | `docs/audits/JOINED_RECORDS_BUILDER_PRE_COMMIT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `JOINED_RECORDS_BUILDER_RUNTIME_BOTTLENECK_AUDIT_001.md` | Audit | `docs/audits/JOINED_RECORDS_BUILDER_RUNTIME_BOTTLENECK_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `JOINED_RECORDS_BUILDER_RUNTIME_PATCH_COMMIT_REPORT_001.md` | Report | `docs/reports/JOINED_RECORDS_BUILDER_RUNTIME_PATCH_COMMIT_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `JOINED_RECORDS_BUILDER_RUNTIME_PATCH_IMPLEMENTATION_REPORT_001.md` | Report | `docs/reports/JOINED_RECORDS_BUILDER_RUNTIME_PATCH_IMPLEMENTATION_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `JOINED_RECORDS_BUILDER_RUNTIME_PATCH_PRE_COMMIT_AUDIT_001.md` | Audit | `docs/audits/JOINED_RECORDS_BUILDER_RUNTIME_PATCH_PRE_COMMIT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `JOINED_RECORDS_REAL_DATA_AUDIT_001.md` | Audit | `docs/audits/JOINED_RECORDS_REAL_DATA_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `KNOWN_ISSUES.md` | Governance | `docs/governance/KNOWN_ISSUES.md` | **no** | N/A | Blocked by file collision / duplicate check. |
| `KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md` | Governance | `docs/governance/KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md` | **yes** | Batch 4 | Relocate to central Governance directory. |
| `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md` | Research | `docs/research/MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md` | **yes** | Batch 3 | Relocate to central Research directory. |
| `MASTER_AGENT_ROUTER.md` | Governance | `docs/governance/MASTER_AGENT_ROUTER.md` | **no** | N/A | Core system file or IDE entry point; must remain at root. |
| `MICRO_RECOVERY_COUNTERFACTUAL_AUDIT_001.md` | Audit | `docs/audits/MICRO_RECOVERY_COUNTERFACTUAL_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `MICRO_RECOVERY_LIVE_BLOCKING_AUDIT_001.md` | Audit | `docs/audits/MICRO_RECOVERY_LIVE_BLOCKING_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `MICRO_RECOVERY_TRAP_RESOLUTION_DESIGN_001.md` | Architecture | `docs/architecture/MICRO_RECOVERY_TRAP_RESOLUTION_DESIGN_001.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `N100_INTERPRETATION_MATRIX.md` | Governance | `docs/governance/N100_INTERPRETATION_MATRIX.md` | **yes** | Batch 4 | Relocate to central Governance directory. |
| `OPTION_D_COUNTERFACTUAL_AUDIT_001.md` | Audit | `docs/audits/OPTION_D_COUNTERFACTUAL_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `OPTION_D_RESTART_AFTER_MIGRATION_001_REPORT.md` | Report | `docs/reports/OPTION_D_RESTART_AFTER_MIGRATION_001_REPORT.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `OPTION_D_STOP_DISTRIBUTION_AUDIT_001.md` | Audit | `docs/audits/OPTION_D_STOP_DISTRIBUTION_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `PAPER_RUNTIME_STALE_OWNER_RECOVERY_AUDIT_001.md` | Audit | `docs/audits/PAPER_RUNTIME_STALE_OWNER_RECOVERY_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `PAPER_RUNTIME_STATE_AUDIT_001.md` | Audit | `docs/audits/PAPER_RUNTIME_STATE_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `PHASE_B_7DAY_EVIDENCE_COLLECTION_GOVERNANCE_001.md` | Governance | `docs/governance/PHASE_B_7DAY_EVIDENCE_COLLECTION_GOVERNANCE_001.md` | **yes** | Batch 4 | Relocate to central Governance directory. |
| `PHASE_B_DAILY_AUTOMATED_REPORT_IMPLEMENTATION_REPORT_001.md` | Report | `docs/reports/PHASE_B_DAILY_AUTOMATED_REPORT_IMPLEMENTATION_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `PHASE_B_DAILY_EVIDENCE_COLLECTOR_COMMIT_REPORT_001.md` | Report | `docs/reports/PHASE_B_DAILY_EVIDENCE_COLLECTOR_COMMIT_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `PHASE_B_DAILY_EVIDENCE_COLLECTOR_DESIGN_001.md` | Architecture | `docs/architecture/PHASE_B_DAILY_EVIDENCE_COLLECTOR_DESIGN_001.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `PHASE_B_DAILY_EVIDENCE_COLLECTOR_IMPLEMENTATION_REPORT_001.md` | Report | `docs/reports/PHASE_B_DAILY_EVIDENCE_COLLECTOR_IMPLEMENTATION_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `PHASE_B_DAILY_EVIDENCE_COLLECTOR_PRE_COMMIT_AUDIT_001.md` | Audit | `docs/audits/PHASE_B_DAILY_EVIDENCE_COLLECTOR_PRE_COMMIT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `PHASE_B_DAILY_EVIDENCE_COLLECTOR_REAL_DATA_VALIDATION_001.md` | Evidence | `docs/evidence/PHASE_B_DAILY_EVIDENCE_COLLECTOR_REAL_DATA_VALIDATION_001.md` | **yes** | Batch 2 | Relocate to central Evidence directory. |
| `PHASE_B_DAILY_SNAPSHOT_ARCHIVER_IMPLEMENTATION_REPORT_001.md` | Report | `docs/reports/PHASE_B_DAILY_SNAPSHOT_ARCHIVER_IMPLEMENTATION_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `PHASE_B_LIVE_RUNTIME_INSPECTION_001.md` | Runtime | `docs/runtime/PHASE_B_LIVE_RUNTIME_INSPECTION_001.md` | **yes** | Batch 3 | Relocate to central Runtime directory. |
| `PHASE_B_LIVE_RUNTIME_RESTART_AND_SMOKE_001.md` | Runtime | `docs/runtime/PHASE_B_LIVE_RUNTIME_RESTART_AND_SMOKE_001.md` | **yes** | Batch 3 | Relocate to central Runtime directory. |
| `PHASE_B_MIXED_SCHEMA_ROOT_CAUSE_AUDIT_001.md` | Audit | `docs/audits/PHASE_B_MIXED_SCHEMA_ROOT_CAUSE_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `PHASE_B_SCHEMA_ISOLATION_BOUNDED_VALIDATION_001.md` | Evidence | `docs/evidence/PHASE_B_SCHEMA_ISOLATION_BOUNDED_VALIDATION_001.md` | **yes** | Batch 2 | Relocate to central Evidence directory. |
| `PHASE_B_SCHEMA_ISOLATION_COMMIT_REPORT_001.md` | Report | `docs/reports/PHASE_B_SCHEMA_ISOLATION_COMMIT_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `PHASE_B_SCHEMA_ISOLATION_PATCH_IMPLEMENTATION_REPORT_001.md` | Report | `docs/reports/PHASE_B_SCHEMA_ISOLATION_PATCH_IMPLEMENTATION_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `PHASE_B_SCHEMA_ISOLATION_PATCH_PLAN_001.md` | Architecture | `docs/architecture/PHASE_B_SCHEMA_ISOLATION_PATCH_PLAN_001.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `PHASE_B_SCHEMA_ISOLATION_PATCH_PRE_COMMIT_AUDIT_001.md` | Audit | `docs/audits/PHASE_B_SCHEMA_ISOLATION_PATCH_PRE_COMMIT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `PROJECT_RULES.md` | Governance | `docs/governance/PROJECT_RULES.md` | **no** | N/A | Core system file or IDE entry point; must remain at root. |
| `PROJECT_STRUCTURE.md` | Governance | `docs/governance/PROJECT_STRUCTURE.md` | **no** | N/A | Blocked by file collision / duplicate check. |
| `QUANT_FUTURE_DECISION_ENGINE.md` | Architecture | `docs/architecture/QUANT_FUTURE_DECISION_ENGINE.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `QUANT_LIFECYCLE_INVENTORY_ENGINE.md` | Architecture | `docs/architecture/QUANT_LIFECYCLE_INVENTORY_ENGINE.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `QUANT_REGIME_PROBABILITY_ENGINE.md` | Architecture | `docs/architecture/QUANT_REGIME_PROBABILITY_ENGINE.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `README.md` | Governance | `docs/governance/README.md` | **no** | N/A | Core system file or IDE entry point; must remain at root. |
| `RISK_PLAN_ZERO_FORENSIC_AUDIT_001.md` | Audit | `docs/audits/RISK_PLAN_ZERO_FORENSIC_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `ROOT_MD_INVENTORY_001.md` | Unknown | `docs/archive/root_md_legacy/ROOT_MD_INVENTORY_001.md` | **yes** | N/A | Relocate to central Unknown directory. |
| `SELECTION_BIAS_AUDIT.md` | Audit | `docs/audits/SELECTION_BIAS_AUDIT.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `SHADOW_FLAG_INVENTORY_AUDIT_001.md` | Audit | `docs/audits/SHADOW_FLAG_INVENTORY_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `SHADOW_TELEMETRY_PHASE_B_BOUNDED_RUNTIME_VALIDATION_001.md` | Evidence | `docs/evidence/SHADOW_TELEMETRY_PHASE_B_BOUNDED_RUNTIME_VALIDATION_001.md` | **yes** | Batch 2 | Relocate to central Evidence directory. |
| `SHADOW_TELEMETRY_PHASE_B_BUILTIN_RECOVERY_ENABLE_001.md` | Runtime | `docs/runtime/SHADOW_TELEMETRY_PHASE_B_BUILTIN_RECOVERY_ENABLE_001.md` | **yes** | Batch 3 | Relocate to central Runtime directory. |
| `SHADOW_TELEMETRY_PHASE_B_COMMIT_REPORT_001.md` | Report | `docs/reports/SHADOW_TELEMETRY_PHASE_B_COMMIT_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `SHADOW_TELEMETRY_PHASE_B_CONTROLLED_ENABLE_001.md` | Runtime | `docs/runtime/SHADOW_TELEMETRY_PHASE_B_CONTROLLED_ENABLE_001.md` | **yes** | Batch 3 | Relocate to central Runtime directory. |
| `SHADOW_TELEMETRY_PHASE_B_DESIGN_001.md` | Architecture | `docs/architecture/SHADOW_TELEMETRY_PHASE_B_DESIGN_001.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `SHADOW_TELEMETRY_PHASE_B_ENABLE_READINESS_AUDIT_001.md` | Audit | `docs/audits/SHADOW_TELEMETRY_PHASE_B_ENABLE_READINESS_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `SHADOW_TELEMETRY_PHASE_B_IMPLEMENTATION_PLAN_001.md` | Architecture | `docs/architecture/SHADOW_TELEMETRY_PHASE_B_IMPLEMENTATION_PLAN_001.md` | **yes** | Batch 3 | Relocate to central Architecture directory. |
| `SHADOW_TELEMETRY_PHASE_B_IMPLEMENTATION_REPORT_001.md` | Report | `docs/reports/SHADOW_TELEMETRY_PHASE_B_IMPLEMENTATION_REPORT_001.md` | **yes** | Batch 1 | Relocate to central Report directory. |
| `SHADOW_TELEMETRY_PHASE_B_PRE_COMMIT_AUDIT_001.md` | Audit | `docs/audits/SHADOW_TELEMETRY_PHASE_B_PRE_COMMIT_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `SHADOW_TELEMETRY_PHASE_B_PRE_COMMIT_SCOPE_AUDIT_001.md` | Audit | `docs/audits/SHADOW_TELEMETRY_PHASE_B_PRE_COMMIT_SCOPE_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `SHADOW_TELEMETRY_PHASE_B_PRE_IMPLEMENTATION_AUDIT_001.md` | Audit | `docs/audits/SHADOW_TELEMETRY_PHASE_B_PRE_IMPLEMENTATION_AUDIT_001.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `SHADOW_TELEMETRY_PHASE_B_SMOKE_ENABLE_001.md` | Runtime | `docs/runtime/SHADOW_TELEMETRY_PHASE_B_SMOKE_ENABLE_001.md` | **yes** | Batch 3 | Relocate to central Runtime directory. |
| `SQLITE_BACKED_JOINED_BUILDER_BOUNDED_VALIDATION_001.md` | Evidence | `docs/evidence/SQLITE_BACKED_JOINED_BUILDER_BOUNDED_VALIDATION_001.md` | **yes** | Batch 2 | Relocate to central Evidence directory. |
| `VULTR_PAPER_RUN.md` | Runtime | `docs/runtime/VULTR_PAPER_RUN.md` | **yes** | Batch 3 | Relocate to central Runtime directory. |
| `overnight_maturity_check_2026-05-19.md` | Audit | `docs/audits/overnight_maturity_check_2026-05-19.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `repo_canonical_check_2026-05-19.md` | Audit | `docs/audits/repo_canonical_check_2026-05-19.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `research_cockpit_v2_gap_audit.md` | Audit | `docs/audits/research_cockpit_v2_gap_audit.md` | **yes** | Batch 1 | Relocate to central Audit directory. |
| `runtime_clean_validation_2026-05-19.md` | Evidence | `docs/evidence/runtime_clean_validation_2026-05-19.md` | **yes** | Batch 2 | Relocate to central Evidence directory. |
| `stop_loss_concentration_diagnosis_2026-05-19.md` | Audit | `docs/audits/stop_loss_concentration_diagnosis_2026-05-19.md` | **yes** | Batch 1 | Relocate to central Audit directory. |

---

## 5. Staged Migration Batches

Reorganizing 134 files at once can break documentation links and developer context. A 4-stage migration is recommended.

### Batch 1: Obvious Reports and Audits (78 files)
*Target: docs/reports/ and docs/audits/*  
*Rationale: Safe, historical status files that are rarely cross-linked dynamically by code or startup loops.*
* `DECISION_LOG_SLIM_INDEX_COMMIT_REPORT_001.md`
* `DECISION_LOG_SLIM_INDEX_IMPLEMENTATION_REPORT_001.md`
* `DECISION_LOG_SLIM_INDEX_INTEGRATION_AUDIT_001.md`
* `DECISION_LOG_SLIM_INDEX_INTEGRATION_COMMIT_REPORT_001.md`
* `DECISION_LOG_SLIM_INDEX_INTEGRATION_IMPLEMENTATION_REPORT_001.md`
* `DECISION_LOG_SLIM_INDEX_INTEGRATION_PRE_COMMIT_AUDIT_001.md`
* `DECISION_LOG_SLIM_INDEX_PRE_COMMIT_AUDIT_001.md`
* `DELTA_EXTREME_CONFLICT_RESOLUTION_AUDIT_001.md`
* `DELTA_EXTREME_EXECUTABLE_TRUTH_AUDIT_001.md`
* `DELTA_EXTREME_GATE_FORENSIC_AUDIT.md`
* `DELTA_EXTREME_SHADOW_OVERLAY_PHASE_A_COMMIT_REPORT.md`
* `DELTA_EXTREME_SHADOW_OVERLAY_PHASE_A_IMPLEMENTATION_001_REPORT.md`
* `DELTA_EXTREME_SHADOW_OVERLAY_PHASE_A_PRE_COMMIT_AUDIT_001.md`
* `DELTA_SHADOW_HOOKPOINT_AUDIT_001.md`
* `DELTA_SHADOW_PRE_IMPLEMENTATION_AUDIT_001.md`
* `DUPLICATE_OPEN_FORENSIC_AUDIT_001.md`
* `ENTRY_FUNNEL_ROOT_CAUSE_AUDIT_001.md`
* `ENVIRONMENT_RECOVERY_REPORT_001.md`
* `EVIDENCE_QUALITY_AUDIT.md`
* `EXECUTION_DATASET_PURITY_AUDIT_001.md`
* `EXECUTION_FILTER_IMPACT_AUDIT_001.md`
* `EXECUTION_OFFLINE_SHADOW_FILTER_AUDIT_001.md`
* `EXECUTION_PAPER_RUNTIME_PHASE_A_COMMIT_REPORT_001.md`
* `EXECUTION_PAPER_RUNTIME_PHASE_A_IMPLEMENTATION_REPORT_001.md`
* `EXECUTION_PAPER_RUNTIME_PHASE_A_PRE_COMMIT_AUDIT_001.md`
* `EXECUTION_SHADOW_TELEMETRY_OFFLINE_COMMIT_REPORT_001.md`
* `EXECUTION_SHADOW_TELEMETRY_OFFLINE_IMPLEMENTATION_REPORT_001.md`
* `EXECUTION_SHADOW_TELEMETRY_OFFLINE_PRE_COMMIT_AUDIT_001.md`
* `EXECUTION_SIGNAL_CLUSTER_FORENSIC_AUDIT_001.md`
* `EXECUTION_SIGNAL_FORENSIC_AUDIT_001.md`
* `FORWARD_VALIDATION_PROTOCOL_AUDIT.md`
* `GITIGNORE_HYGIENE_COMMIT_REPORT_001.md`
* `GIT_PROCESS_STORM_VENV_BACKUP_FIX_REPORT_001.md`
* `HISTORICAL_POSITION_IDENTITY_DESIGN_AUDIT_001.md`
* `HISTORICAL_POSITION_IDENTITY_PATCH_COMMIT_REPORT_001.md`
* `HISTORICAL_POSITION_IDENTITY_PATCH_IMPLEMENTATION_REPORT_001.md`
* `HISTORICAL_POSITION_IDENTITY_PATCH_PRE_COMMIT_AUDIT_001.md`
* `JOINED_RECORDS_BUILDER_COMMIT_REPORT_001.md`
* `JOINED_RECORDS_BUILDER_IMPLEMENTATION_REPORT_001.md`
* `JOINED_RECORDS_BUILDER_MEMORY_PATCH_COMMIT_REPORT_001.md`
* `JOINED_RECORDS_BUILDER_MEMORY_PATCH_IMPLEMENTATION_REPORT_001.md`
* `JOINED_RECORDS_BUILDER_MEMORY_PATCH_PRE_COMMIT_AUDIT_001.md`
* `JOINED_RECORDS_BUILDER_PERFORMANCE_AUDIT_001.md`
* `JOINED_RECORDS_BUILDER_PRE_COMMIT_AUDIT_001.md`
* `JOINED_RECORDS_BUILDER_RUNTIME_BOTTLENECK_AUDIT_001.md`
* `JOINED_RECORDS_BUILDER_RUNTIME_PATCH_COMMIT_REPORT_001.md`
* `JOINED_RECORDS_BUILDER_RUNTIME_PATCH_IMPLEMENTATION_REPORT_001.md`
* `JOINED_RECORDS_BUILDER_RUNTIME_PATCH_PRE_COMMIT_AUDIT_001.md`
* `JOINED_RECORDS_REAL_DATA_AUDIT_001.md`
* `MICRO_RECOVERY_COUNTERFACTUAL_AUDIT_001.md`
* `MICRO_RECOVERY_LIVE_BLOCKING_AUDIT_001.md`
* `OPTION_D_COUNTERFACTUAL_AUDIT_001.md`
* `OPTION_D_RESTART_AFTER_MIGRATION_001_REPORT.md`
* `OPTION_D_STOP_DISTRIBUTION_AUDIT_001.md`
* `PAPER_RUNTIME_STALE_OWNER_RECOVERY_AUDIT_001.md`
* `PAPER_RUNTIME_STATE_AUDIT_001.md`
* `PHASE_B_DAILY_AUTOMATED_REPORT_IMPLEMENTATION_REPORT_001.md`
* `PHASE_B_DAILY_EVIDENCE_COLLECTOR_COMMIT_REPORT_001.md`
* `PHASE_B_DAILY_EVIDENCE_COLLECTOR_IMPLEMENTATION_REPORT_001.md`
* `PHASE_B_DAILY_EVIDENCE_COLLECTOR_PRE_COMMIT_AUDIT_001.md`
* `PHASE_B_DAILY_SNAPSHOT_ARCHIVER_IMPLEMENTATION_REPORT_001.md`
* `PHASE_B_MIXED_SCHEMA_ROOT_CAUSE_AUDIT_001.md`
* `PHASE_B_SCHEMA_ISOLATION_COMMIT_REPORT_001.md`
* `PHASE_B_SCHEMA_ISOLATION_PATCH_IMPLEMENTATION_REPORT_001.md`
* `PHASE_B_SCHEMA_ISOLATION_PATCH_PRE_COMMIT_AUDIT_001.md`
* `RISK_PLAN_ZERO_FORENSIC_AUDIT_001.md`
* `SELECTION_BIAS_AUDIT.md`
* `SHADOW_FLAG_INVENTORY_AUDIT_001.md`
* `SHADOW_TELEMETRY_PHASE_B_COMMIT_REPORT_001.md`
* `SHADOW_TELEMETRY_PHASE_B_ENABLE_READINESS_AUDIT_001.md`
* `SHADOW_TELEMETRY_PHASE_B_IMPLEMENTATION_REPORT_001.md`
* `SHADOW_TELEMETRY_PHASE_B_PRE_COMMIT_AUDIT_001.md`
* `SHADOW_TELEMETRY_PHASE_B_PRE_COMMIT_SCOPE_AUDIT_001.md`
* `SHADOW_TELEMETRY_PHASE_B_PRE_IMPLEMENTATION_AUDIT_001.md`
* `overnight_maturity_check_2026-05-19.md`
* `repo_canonical_check_2026-05-19.md`
* `research_cockpit_v2_gap_audit.md`
* `stop_loss_concentration_diagnosis_2026-05-19.md`

### Batch 2: Evidence and Validations (13 files)
*Target: docs/evidence/*  
*Rationale: Validations and dry run logs. Safe to move as they are immutable evidence.*
* `DECISION_LOG_SLIM_INDEX_BOUNDED_VALIDATION_001.md`
* `EXECUTION_PAPER_RUNTIME_PHASE_A_DRY_RUN_VALIDATION_001.md`
* `EXECUTION_PAPER_RUNTIME_PHASE_C_FULL_ELIGIBLE_REPLAY_COMPAT_001.md`
* `EXECUTION_PAPER_RUNTIME_PHASE_C_FULL_ELIGIBLE_REPLAY_COMPAT_RERUN_001.md`
* `FULL_SQLITE_REAL_DATA_VALIDATION_001.md`
* `JOINED_RECORDS_BUILDER_BOUNDED_REAL_DATA_VALIDATION_001.md`
* `JOINED_RECORDS_BUILDER_FULL_REAL_DATA_RERUN_001.md`
* `JOINED_RECORDS_BUILDER_POST_PATCH_BOUNDED_BENCHMARK_001.md`
* `PHASE_B_DAILY_EVIDENCE_COLLECTOR_REAL_DATA_VALIDATION_001.md`
* `PHASE_B_SCHEMA_ISOLATION_BOUNDED_VALIDATION_001.md`
* `SHADOW_TELEMETRY_PHASE_B_BOUNDED_RUNTIME_VALIDATION_001.md`
* `SQLITE_BACKED_JOINED_BUILDER_BOUNDED_VALIDATION_001.md`
* `runtime_clean_validation_2026-05-19.md`

### Batch 3: Architecture, Research, and Runtimes (26 files)
*Target: docs/architecture/, docs/research/, and docs/runtime/*  
*Rationale: Replays and designs. Requires checking for cross-file links first.*
* `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md`
* `DECISION_LOG_SLIM_INDEX_DESIGN_001.md`
* `DECISION_LOG_SLIM_INDEX_FULL_BUILD_001.md`
* `DELTA_EXTREME_SHADOW_OVERLAY_IMPLEMENTATION_PLAN_001.md`
* `DELTA_EXTREME_SHADOW_OVERLAY_SPEC_001.md`
* `EXECUTION_PAPER_RUNTIME_PHASE_B_JOURNAL_WIRING_PLAN_001.md`
* `EXECUTION_SHADOW_FILTER_SPEC_001.md`
* `EXECUTION_SHADOW_TELEMETRY_IMPLEMENTATION_PLAN_001.md`
* `HYPOTHESIS_LEDGER_RECONSTRUCTION.md`
* `INVENTORY_REPLAY_RESEARCH_PLAN.md`
* `JOINED_RECORDS_BUILDER_PLAN_001.md`
* `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md`
* `MICRO_RECOVERY_TRAP_RESOLUTION_DESIGN_001.md`
* `PHASE_B_DAILY_EVIDENCE_COLLECTOR_DESIGN_001.md`
* `PHASE_B_LIVE_RUNTIME_INSPECTION_001.md`
* `PHASE_B_LIVE_RUNTIME_RESTART_AND_SMOKE_001.md`
* `PHASE_B_SCHEMA_ISOLATION_PATCH_PLAN_001.md`
* `QUANT_FUTURE_DECISION_ENGINE.md`
* `QUANT_LIFECYCLE_INVENTORY_ENGINE.md`
* `QUANT_REGIME_PROBABILITY_ENGINE.md`
* `SHADOW_TELEMETRY_PHASE_B_BUILTIN_RECOVERY_ENABLE_001.md`
* `SHADOW_TELEMETRY_PHASE_B_CONTROLLED_ENABLE_001.md`
* `SHADOW_TELEMETRY_PHASE_B_DESIGN_001.md`
* `SHADOW_TELEMETRY_PHASE_B_IMPLEMENTATION_PLAN_001.md`
* `SHADOW_TELEMETRY_PHASE_B_SMOKE_ENABLE_001.md`
* `VULTR_PAPER_RUN.md`

### Batch 4: Governance Docs (7 files)
*Target: docs/governance/*  
*Rationale: Key rules documents. Must be reviewed carefully to verify IDEs and route scripts do not expect them at the root.*
* `CHATGPT_PROJECT_START_PROMPT.md`
* `CLAUDE.md`
* `CODEX_START_PROMPT.md`
* `DOC_TRUTH_RECONCILIATION_2026-05-14.md`
* `KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md`
* `N100_INTERPRETATION_MATRIX.md`
* `PHASE_B_7DAY_EVIDENCE_COLLECTION_GOVERNANCE_001.md`

---

## 6. Final Verdict

Due to the massive scale of the reorganization (134 files total, with 126 planned relocations) and the risk of breaking internal link mappings, the verdict is:

```text
NEEDS_MANUAL_REVIEW
```

**Next Action for Operator**: Review this plan. If approved, migrations should be executed sequentially, batch-by-batch, updating the link references in `docs/DOCUMENTATION_MAP.md` and `FILE_INDEX.md` at each stage.
