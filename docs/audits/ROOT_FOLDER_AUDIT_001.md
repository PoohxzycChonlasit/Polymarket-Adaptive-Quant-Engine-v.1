# ROOT_FOLDER_AUDIT_001

**Task:** REPOSITORY_ORGANIZATION_AUDIT_001  
**Mode:** DISCOVERY ONLY  
**Date:** 2026-06-26  
**Scope:** Every item in the repository root directory

---

## Non-Markdown Root Files (13 files)

These are analyzed first because they have harder location dependencies.

| File | Size | Purpose | In Root? | Should Move? | Startup-Critical? |
|---|---|---|---|---|---|
| `main.py` | 63KB | Primary entry point | YES | NO — convention | YES |
| `.env` | 4.8KB | Runtime secrets/config | YES | NO — dotenv loads from CWD | SECURITY |
| `.env.backup.local` | 4.8KB | Env backup (sensitive!) | YES | SHOULD DELETE or secure | NO |
| `.env.example` | 2.4KB | Template for new devs | YES | NO — convention | NO |
| `.gitignore` | 821B | Git exclusion rules | YES | NO — git requires root | NO |
| `requirements.txt` | 356B | Pip dependencies | YES | NO — pip convention | YES |
| `pytest.ini` | 60B | Pytest config | YES | NO — pytest looks in root | YES |
| `task.md` | 863B | Current task note | YES | YES → delete or scratch/ | NO |
| `docs.zip` | 66KB | Archived docs snapshot | YES | YES → archive/ | NO |
| `check_balance.py` | 1.3KB | Wallet balance utility | YES | YES → scripts/ | NO |
| `daily_report.py` | 18.9KB | Daily reporting tool | YES | YES → scripts/ or tools/ | NO |
| `generate_bypass.py` | 1.4KB | Unknown bypass generator | YES | YES → scripts/ after review | NO |
| `hft_paper_run.py` | 22.3KB | HFT paper trading runner | YES | YES → hft/ or scripts/ | NO |
| `register_api_keys.py` | 1.7KB | API key registration | YES | YES → scripts/ | NO |

**Notes:**
- `.env.backup.local` contains live credentials. Should NOT be in git at all — verify .gitignore covers it.
- `generate_bypass.py` — name is ambiguous. Before moving, confirm it is not wired into any runtime or CI.
- `hft_paper_run.py` likely belongs alongside `hft/` folder content.

---

## AI Startup Context Files (10 files — must stay in root)

These files are explicitly referenced in CLAUDE.md's startup sequence or are auto-loaded by AI tooling.

| File | Size | Purpose | Must Stay? | Notes |
|---|---|---|---|---|
| `CLAUDE.md` | 4.9KB | Claude Code project instructions | YES — auto-loaded | The project AI contract |
| `AGENTS.md` | 19.6KB | Agent role definitions | YES — Claude SDK | Loaded by agent harness |
| `README.md` | 14.8KB | Public-facing documentation | YES — GitHub renders | Primary entry point |
| `CODEX_START_HERE.md` | 7.3KB | CLAUDE.md "read first" startup | YES — referenced in CLAUDE.md | Core AI onboarding |
| `PROJECT_RULES.md` | 6.1KB | Project constraints | YES — referenced in CLAUDE.md | |
| `CURRENT_PROJECT_STATUS.md` | 50.9KB | Live project state | YES — referenced in CLAUDE.md | 50KB is large; split candidate |
| `MASTER_AGENT_ROUTER.md` | 10.8KB | Agent task routing | YES — referenced in CLAUDE.md | |
| `CODEX_START_PROMPT.md` | 2.0KB | Codex AI prompt | RECOMMENDED stay | AI system prompt |
| `CHATGPT_PROJECT_START_PROMPT.md` | 1.5KB | ChatGPT context prompt | OPTIONAL | Could move to .codex/ |
| `FILE_INDEX.md` | 24.8KB | Repository file index | RECOMMENDED stay | Navigation reference |
| `DOCUMENTATION_MAP.md` | 11.7KB | Documentation map | RECOMMENDED stay | |

---

## Root Markdown Files — By Category

**Total root markdown files: 395**

The following analysis categorizes all 395 by pattern. Exact move targets are in `SAFE_MOVE_PLAN_001.md`.

---

### Category A — Architecture & Design Documents (~60 files)

These define system design, component specs, or architectural decisions. Canonical docs. Should move to `docs/architecture/` or `docs/design/`.

Examples:
- `ALWAYS_ACTIVE_ENGINE_V1_DESIGN_001.md`
- `ALWAYS_ACTIVE_RISK_MODEL_V1.md`
- `ANALYTICS_AUTHORITY_MATRIX_001.md`
- `ANALYTICS_CACHE_POLICY_001.md`
- `ANALYTICS_DEPENDENCY_BOUNDARY_001.md`
- `ANALYTICS_FAILSOFT_POLICY_001.md`
- `ANALYTICS_LOADER_V1_DESIGN_001.md`
- `ARCHITECTURE_FREEZE_DECISION_001.md`
- `ARCHITECTURE_FREEZE_REVIEW_001.md`
- `BANKROLL_ENGINE_V1_DESIGN_001.md`
- `BANKROLL_PROMOTION_SYSTEM_V1.md`
- `BANKROLL_TIER_FRAMEWORK_V1.md` (DUPLICATE — also in docs/)
- `BANKROLL_TIER_SYSTEM.md`
- `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md`
- `CANDIDATE_EVALUATION_PIPELINE_V1.md`
- `CAPACITY_ALLOCATION_ENGINE_V1.md`
- `CAPACITY_SCALING_MODEL_V1.md`
- `CAPACITY_THROTTLE_ENGINE_V1.md`
- `DECISION_FRAMEWORK_V1_DESIGN_001.md`
- `DECISION_GATE_HIERARCHY_V1.md`
- `DECISION_HIERARCHY_MATRIX_V1.md`
- `DECISION_LOG_SLIM_INDEX_DESIGN_001.md`
- `DECISION_RUNTIME_V1_DESIGN_001.md`
- `DYNAMIC_SHARE_MODEL_V1.md`
- `ENTRY_VETO_SYSTEM_V1.md`
- `EVENT_CATALOG_V1.md`
- `EVENT_CONSUMER_MATRIX_V1.md`
- `EVENT_DASHBOARD_STATE_MAP_V1.md`
- `EVENT_DROP_POLICY_V1.md`
- `EVENT_PRIORITY_MATRIX_V1.md`
- `EVENT_REPLAY_ARCHITECTURE_V1.md`
- `EVENT_SCHEMA_STANDARD_V1.md`
- `GO_NO_GO_ENGINE_V1.md`
- `LOSS_CLUSTER_ENGINE_V1.md`
- `ORDER_INTENT_GENERATION_V1.md`
- `POSITION_SIZING_ENGINE_V1_DESIGN_001.md`
- `POSITION_SIZING_MATRIX_V1.md`
- `QUANT_LIFECYCLE_INVENTORY_ENGINE.md`
- `RECOVERY_ENGINE_V1.md`
- `RISK_BUDGET_ENGINE_V1.md`
- `RUNTIME_EVENT_STREAM_V1.md`
- `RUNTIME_HEARTBEAT_SPEC_V1.md`
- `RUNTIME_STATE_MACHINE_V1.md`
- ...and ~15 more

---

### Category B — Research / Forensic Audit Documents (~90 files)

Active research findings from specific sessions. Primary source of truth for known issues. Move to `docs/research/` with appropriate subfolder.

Examples:
- `CLOB_EMPTY_RESPONSE_FORENSIC_AUDIT.md`
- `DEFENSIVE_CONFIDENCE_DISTRIBUTION_001.md`
- `DEFENSIVE_COUNTERFACTUAL_PASS_ANALYSIS_001.md`
- `DEFENSIVE_MODE_FORENSIC_VALIDATION_001.md`
- `DEFENSIVE_MODE_NEXT_ACTIONS_001.md`
- `DELTA_EXTREME_GATE_FORENSIC_AUDIT.md`
- `DIRECTIONAL_ASYMMETRY_RESOLUTION_001.md`
- `EXIT_EXECUTION_ROOT_CAUSE_AUDIT_001.md`
- `EXIT_FAILURE_DISTRIBUTION_001.md`
- `EXIT_LIFECYCLE_TRACE_001.md`
- `HOLD_TIME_COLLAPSE_FORENSIC_001.md`
- `MICRO_BANKROLL_EXECUTABILITY_ANALYSIS_001.md`
- `MICRO_RECOVERY_COUNTERFACTUAL_ANALYSIS_001.md` (THIS SESSION)
- `MICRO_RECOVERY_NEXT_ACTIONS_001.md` (THIS SESSION)
- `MICRO_RECOVERY_RISK_PLAN_ZERO_AUDIT_001.md` (THIS SESSION)
- `MICRO_RECOVERY_ZERO_PIPELINE_TRACE_001.md` (THIS SESSION)
- `NO_EV_EXIT_REASON_FORENSIC_AUDIT_001.md`
- `NO_SIDE_FAILURE_FORENSIC_AUDIT_001.md`
- `NO_TRADE_ROOT_CAUSE_AUDIT_001.md`
- `ORDERBOOK_ROOT_CAUSE_AUDIT_001.md`
- `RISK_PLAN_ZERO_DISTRIBUTION_001.md` (THIS SESSION)
- `RISK_PLAN_ZERO_FORENSIC_AUDIT_001.md`
- `RISK_MODE_TRANSITION_TIMELINE_001.md`
- `SIZING_MULTIPLIER_ROOT_CAUSE_AUDIT_001.md`
- ...and ~65 more

---

### Category C — Patch/Implementation/Commit Reports (~120 files)

Historical records of what was changed and when. Pure historical reference — not design docs. Move to `docs/reports/` or a dedicated `docs/patch_history/` folder.

Examples:
- `COLD_JSONL_COMPRESSION_DRY_RUN_COMMIT_REPORT_001.md`
- `COMPRESS_RESTORE_PATCH_COMMIT_REPORT_001.md`
- `DASHBOARD_API_V0_COMMIT_REPORT_001.md`
- `DASHBOARD_STATE_AGGREGATOR_COMMIT_REPORT_001.md`
- `MAIN_PY_DIRTY_AUDIT_REPORT.md`
- `OPTION_D_PHASE_A_COMMIT_REPORT.md`
- `PATCH_006B_RUNTIME_EVIDENCE_AUDIT.md`
- `PATCH_OBSERVABILITY_001_COMMIT_REPORT.md`
- `PATCH_STOP_002_COMMIT_REPORT.md`
- `PATCH_TG_HEARTBEAT_V2_COMMIT_REPORT.md`
- `REACT_DASHBOARD_V0_COMMIT_REPORT_001.md`
- `REGIME_ANALYTICS_V1_COMMIT_REPORT_001.md`
- `SCHEMA_SLIMMING_STAGE_1_COMMIT_REPORT_001.md`
- `SESSION_ANALYTICS_V1_COMMIT_REPORT_001.md`
- ...and ~105 more

---

### Category D — Previous Reorganization Artifacts (~8 files)

Files from a prior attempt to organize the root. Now meta-noise.

| File | Notes |
|---|---|
| `ROOT_MD_BATCH_1_MOVE_REPORT_001.md` | Documents first batch of moves |
| `ROOT_MD_BATCH_2_MOVE_REPORT_001.md` | Documents second batch of moves |
| `ROOT_MD_INVENTORY_001.md` | Prior inventory (23KB) — stale |
| `ROOT_MD_REORGANIZATION_PLAN_001.md` | Prior plan (35KB) — largely unexecuted |
| `CANONICAL_DOCUMENT_RECONCILIATION_001.md` | Prior reconciliation |
| `AUDIT_CLASSIFICATION_REVIEW.md` | Prior classification |
| `DOCS_LANDING_PAGES_REPORT_001.md` | Prior landing page review |
| `DOCUMENTATION_MAP_REFRESH_REPORT_001.md` | Prior map refresh |

**These are the clearest evidence that a prior reorganization was planned but not completed.** The ROOT_MD_REORGANIZATION_PLAN_001.md (35KB) likely contains the prior plan — it should be read before executing any moves to avoid re-deriving work.

---

### Category E — Navigation / Index Documents (5 files — keep in root or docs/)

| File | Size | Recommendation |
|---|---|---|
| `FILE_INDEX.md` | 24.8KB | Keep root — AI navigation |
| `DOCUMENTATION_MAP.md` | 11.7KB | Keep root — AI navigation |
| `PROJECT_STRUCTURE.md` | 671B | STUB — defer to docs/PROJECT_STRUCTURE.md |
| `KNOWN_ISSUES.md` | 267B | STUB — defer to docs/KNOWN_ISSUES.md |
| `PROJECT_DOCUMENT_INVENTORY_001.md` | 10.4KB | Move to docs/ |

---

### Category F — Governance / Compliance Documents (~15 files)

| File | Notes |
|---|---|
| `ARCHITECTURE_PRINCIPLE_COMPLIANCE_001.md` | Move to docs/architecture/ |
| `GOVERNANCE_BOOTSTRAP_001_DESIGN_PACKAGE.md` | Move to docs/architecture/ |
| `GOVERNANCE_BOOTSTRAP_001_PHASE1_IMPLEMENTATION_REPORT.md` | Move to docs/reports/ |
| `GOVERNANCE_V1_CLOSURE_AUDIT_001.md` | Move to docs/audits/ |
| `FINAL_SOURCE_OF_TRUTH_HIERARCHY_001.md` | Move to docs/architecture/ |
| `QUANT_KNOWLEDGE_GOVERNANCE_AUDIT_001.md` | Move to docs/audits/ |
| `ANALYTICS_RUNTIME_CONSUMPTION_MAP_001.md` | Move to docs/architecture/ |

---

### Category G — Miscellaneous Working Notes (~20 files)

Small documents that were working notes or temporary analyses. Many are stubs or outdated.

| File | Size | Notes |
|---|---|---|
| `task.md` | 863B | Temporary task note — delete or move to scratch/ |
| `implementation_plan.md` | 3.0KB | Generic — likely stale |
| `walkthrough.md` | 3.3KB | Unknown walkthrough |
| `KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md` | 16.2KB | Date-specific — docs/audits/ |
| `overnight_maturity_check_2026-05-19.md` | 10.5KB | Date-specific — docs/research/ |
| `repo_canonical_check_2026-05-19.md` | 7.8KB | Date-specific — docs/audits/ |
| `runtime_clean_validation_2026-05-19.md` | 4.7KB | Date-specific — docs/reports/ |
| `stop_loss_concentration_diagnosis_2026-05-19.md` | 11.3KB | Date-specific — docs/research/ |
| `decision_gate_audit_summary.md` | 2.7KB | Lower-case name — docs/audits/ |
| `orderbook_audit_summary.md` | 3.1KB | Lower-case name — docs/audits/ |
| `probability_ev_signal_naming_audit_001.md` | 5.2KB | Lower-case name — docs/audits/ |
| `no_signal_root_cause_audit_001.md` | 8.6KB | Lower-case name — docs/research/ |
| `dashboard_v2a_commit_report.md` | 894B | Lower-case name — docs/reports/ |
| `patch_006b_two_tier_runtime_attribution_plan.md` | 4.8KB | Lower-case name — docs/reports/ |
| `two_tier_signal_schema_patch_plan_001.md` | 6.0KB | Lower-case name — docs/reports/ |
| `VULTR_PAPER_RUN.md` | 1.7KB | Operations note |
| `INVENTORY_REPLAY_RESEARCH_PLAN.md` | 1.8KB | Plan doc — docs/research/ |
| `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md` | 1.4KB | Plan doc — docs/research/ |
| `REGISTRY_INDEX_INTEGRATION_PLAN.md` | 2.0KB | Plan doc |
| `HYPOTHESIS_LEDGER_RECONSTRUCTION.md` | 23.4KB | Research — docs/research/ |

---

## Root Folders Audit

| Folder | Assessment |
|---|---|
| `.claude/` | Correct location — AI tooling directory |
| `.codex/` | Correct location — Codex tooling directory |
| `api/` | Misplaced — single file belongs in dashboard/ |
| `archive/` | Correct location — but CLAUDE.md shouldn't be in archive if also in root |
| `config/` | Correct — settings.py should stay here |
| `crypto_scalper/` | Orphaned — separate legacy project, not part of PolyTrade engine |
| `dashboard/` | Correct — active dashboard |
| `docs/` | Correct — but needs internal cleanup |
| `hft/` | Orphaned — separate HFT engine project |
| `logs/` | Correct location — but needs subdirectory structure |
| `memory/` | Misplaced — should be in .claude/ or docs/ |
| `polymarket/` | Correct — core engine |
| `research/` | Partially overlaps with docs/research/ — needs clarification |
| `research_cockpit/` | Orphaned — abandoned React dashboard prototype |
| `runtime/` | Correct — runtime-generated data |
| `scratch/` | Valid but undefined boundary — needs .gitignore |
| `scripts/` | Correct — but only 3 files; several root scripts should move here |
| `tests/` | Correct — but .pyc contamination |
| `tools/` | Correct — but .pyc contamination |
| `utils/` | Correct — shared utilities |
| `web-dashboard/` | Orphaned — abandoned React dashboard prototype |
