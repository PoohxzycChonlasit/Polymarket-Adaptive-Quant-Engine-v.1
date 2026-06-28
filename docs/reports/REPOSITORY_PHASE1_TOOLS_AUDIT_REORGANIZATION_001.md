# REPOSITORY_PHASE1_TOOLS_AUDIT_REORGANIZATION_001

## Final Verdict

FINAL_VERDICT: DESIGN_COMPLETE_MOVE_NOT_STARTED

This task audited `tools/` and produced a phased migration design. No tool files were moved or edited. No tests, builders, backtests, or runtime commands were run.

## Preflight

| Check | Result |
|---|---|
| `git status --short` | Clean at preflight. |
| `git branch -vv` | `main` tracking `origin/main`, ahead by one local docs commit. |
| Latest HEAD | `00af48b docs: clean repository root markdown organization`. |
| Root handoff | None in root after Phase 0 cleanup. |
| Pytest/builders/backtests | Not run by scope. |

## Tools Inventory

Observed:

- `tools/*.py`: 81 root-level Python scripts.
- Existing source subdirectories:
  - `tools/backtest_engine_v2/`
  - `tools/flaos/`
- Generated/non-source subdirectory:
  - `tools/__pycache__/`

Category counts:

| Category | Count |
|---|---:|
| `tools/probes/` | 15 |
| `tools/runtime/` | 11 |
| `tools/audit/` | 10 |
| `tools/outcome_truth/` | 10 |
| `tools/replay/` | 9 |
| `tools/research/` | 8 |
| `tools/shadow/` | 8 |
| `tools/phase_b/` | 6 |
| `tools/canonical/` | 3 |
| `tools/unknown_needs_review/` or keep root | 1 |

Reference findings:

- 74/81 root scripts look like CLI entrypoints.
- 73/81 have direct test references.
- 69/81 have docs references.
- 4 have direct active ops references: `canonical_trade_context_builder.py`, `canonical_trade_table_v1.py`, `quant_intelligence_engine.py`, `replay_analyzer.py`.

## Target Tools Structure

See `docs/architecture/TOOLS_STRUCTURE_TARGET_001.md`.

## Move Matrix

| Current path | Proposed path | Category | Risk | Reference summary |
|---|---|---|---|---|
| `tools/_audit_cs_btc.py` | `tools/audit/_audit_cs_btc.py` | audit | LOW_PATH_RISK | tests 0, docs 6, ops no, cli no |
| `tools/_audit_decision_state.py` | `tools/audit/_audit_decision_state.py` | audit | LOW_PATH_RISK | tests 0, docs 6, ops no, cli no |
| `tools/_audit_w21_w22.py` | `tools/audit/_audit_w21_w22.py` | audit | LOW_PATH_RISK | tests 0, docs 8, ops no, cli no |
| `tools/_delta_audit.py` | `tools/audit/_delta_audit.py` | audit | LOW_PATH_RISK | tests 0, docs 9, ops no, cli no |
| `tools/_delta_causal_verify.py` | `tools/audit/_delta_causal_verify.py` | audit | LOW_PATH_RISK | tests 0, docs 7, ops no, cli no |
| `tools/_drift_audit.py` | `tools/audit/_drift_audit.py` | audit | LOW_PATH_RISK | tests 1, docs 17, ops no, cli yes |
| `tools/_opp_capture_audit.py` | `tools/audit/_opp_capture_audit.py` | audit | LOW_PATH_RISK | tests 0, docs 8, ops no, cli no |
| `tools/candidate_continuity.py` | `tools/probes/candidate_continuity.py` | probes | LOW_PATH_RISK | tests 1, docs 2, ops no, cli yes |
| `tools/candidate_path_observability.py` | `tools/probes/candidate_path_observability.py` | probes | LOW_PATH_RISK | tests 1, docs 4, ops no, cli yes |
| `tools/canonical_regime_export.py` | `tools/canonical/canonical_regime_export.py` | canonical | LOW_PATH_RISK | tests 1, docs 6, ops no, cli yes |
| `tools/canonical_trade_context_builder.py` | `tools/canonical/canonical_trade_context_builder.py` | canonical | MEDIUM_IMPORT_RISK | tests 3, docs 18, ops yes, cli yes |
| `tools/canonical_trade_table_v1.py` | `tools/canonical/canonical_trade_table_v1.py` | canonical | MEDIUM_IMPORT_RISK | tests 1, docs 11, ops yes, cli yes |
| `tools/commitment_regime_replay.py` | `tools/replay/commitment_regime_replay.py` | replay | LOW_PATH_RISK | tests 2, docs 2, ops no, cli yes |
| `tools/compact_run_summary.py` | `tools/runtime/compact_run_summary.py` | runtime | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/convergence_regime_classification_replay.py` | `tools/replay/convergence_regime_classification_replay.py` | replay | LOW_PATH_RISK | tests 2, docs 1, ops no, cli yes |
| `tools/cross_run_ev_blindness.py` | `tools/shadow/cross_run_ev_blindness.py` | shadow | LOW_PATH_RISK | tests 1, docs 4, ops no, cli yes |
| `tools/cross_run_lifecycle_truth.py` | `tools/shadow/cross_run_lifecycle_truth.py` | shadow | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/dashboard_state_aggregator.py` | `tools/runtime/dashboard_state_aggregator.py` | runtime | LOW_PATH_RISK | tests 1, docs 57, ops no, cli yes |
| `tools/decision_cycle_timing_probe.py` | `tools/probes/decision_cycle_timing_probe.py` | probes | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/decision_log_slim_index.py` | `tools/runtime/decision_log_slim_index.py` | runtime | LOW_PATH_RISK | tests 1, docs 10, ops no, cli yes |
| `tools/discovery_harness_validation.py` | `tools/probes/discovery_harness_validation.py` | probes | LOW_PATH_RISK | tests 1, docs 0, ops no, cli yes |
| `tools/edge_inventory_report.py` | `tools/research/edge_inventory_report.py` | research | LOW_PATH_RISK | tests 1, docs 5, ops no, cli yes |
| `tools/entry_budget_consumption_probe.py` | `tools/probes/entry_budget_consumption_probe.py` | probes | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/epoch_boundary_alignment_probe.py` | `tools/probes/epoch_boundary_alignment_probe.py` | probes | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/eth_yes_fc_os_command_center.py` | keep root pending review | unknown_needs_review | LOW_PATH_RISK | tests 1, docs 18, ops no, cli yes |
| `tools/ev_field_coverage.py` | `tools/audit/ev_field_coverage.py` | audit | LOW_PATH_RISK | tests 2, docs 5, ops no, cli yes |
| `tools/ev_field_coverage_audit.py` | `tools/audit/ev_field_coverage_audit.py` | audit | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/event_driven_admission_simulation.py` | `tools/probes/event_driven_admission_simulation.py` | probes | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/event_driven_fair_value_simulation.py` | `tools/probes/event_driven_fair_value_simulation.py` | probes | LOW_PATH_RISK | tests 1, docs 3, ops no, cli yes |
| `tools/executable_state_persistence_probe.py` | `tools/probes/executable_state_persistence_probe.py` | probes | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/executable_truth_overlay.py` | `tools/audit/executable_truth_overlay.py` | audit | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/execution_paper_runtime.py` | `tools/runtime/execution_paper_runtime.py` | runtime | LOW_PATH_RISK | tests 1, docs 44, ops no, cli yes |
| `tools/exit_convergence_intelligence_replay.py` | `tools/replay/exit_convergence_intelligence_replay.py` | replay | LOW_PATH_RISK | tests 2, docs 1, ops no, cli yes |
| `tools/free_outcome_truth_provisional.py` | `tools/outcome_truth/free_outcome_truth_provisional.py` | outcome_truth | LOW_PATH_RISK | tests 3, docs 0, ops no, cli yes |
| `tools/free_outcome_truth_provisional_join.py` | `tools/outcome_truth/free_outcome_truth_provisional_join.py` | outcome_truth | LOW_PATH_RISK | tests 1, docs 0, ops no, cli yes |
| `tools/free_outcome_truth_provisional_readiness.py` | `tools/outcome_truth/free_outcome_truth_provisional_readiness.py` | outcome_truth | LOW_PATH_RISK | tests 1, docs 0, ops no, cli yes |
| `tools/joined_records_builder.py` | `tools/runtime/joined_records_builder.py` | runtime | LOW_PATH_RISK | tests 1, docs 22, ops no, cli yes |
| `tools/lifecycle_latency_report.py` | `tools/probes/lifecycle_latency_report.py` | probes | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/lifecycle_profit_management_replay.py` | `tools/replay/lifecycle_profit_management_replay.py` | replay | LOW_PATH_RISK | tests 2, docs 3, ops no, cli yes |
| `tools/lifecycle_timing_report.py` | `tools/probes/lifecycle_timing_report.py` | probes | LOW_PATH_RISK | tests 1, docs 0, ops no, cli yes |
| `tools/lifecycle_truth_backfill.py` | `tools/replay/lifecycle_truth_backfill.py` | replay | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/lifecycle_truth_tables.py` | `tools/replay/lifecycle_truth_tables.py` | replay | LOW_PATH_RISK | tests 1, docs 3, ops no, cli yes |
| `tools/market_readiness_admission_probe.py` | `tools/probes/market_readiness_admission_probe.py` | probes | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/multi_session_runner.py` | `tools/runtime/multi_session_runner.py` | runtime | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/no_entry_analyzer.py` | `tools/research/no_entry_analyzer.py` | research | LOW_PATH_RISK | tests 2, docs 23, ops no, cli yes |
| `tools/no_entry_root_cause_report.py` | `tools/research/no_entry_root_cause_report.py` | research | LOW_PATH_RISK | tests 1, docs 2, ops no, cli yes |
| `tools/official_resolution_acquire_pilot.py` | `tools/outcome_truth/official_resolution_acquire_pilot.py` | outcome_truth | LOW_PATH_RISK | tests 2, docs 0, ops no, cli yes |
| `tools/official_resolution_full_history_runner.py` | `tools/outcome_truth/official_resolution_full_history_runner.py` | outcome_truth | LOW_PATH_RISK | tests 2, docs 1, ops no, cli yes |
| `tools/official_resolution_outcome_join.py` | `tools/outcome_truth/official_resolution_outcome_join.py` | outcome_truth | LOW_PATH_RISK | tests 2, docs 0, ops no, cli yes |
| `tools/official_resolution_rpc_client.py` | `tools/outcome_truth/official_resolution_rpc_client.py` | outcome_truth | LOW_PATH_RISK | tests 2, docs 0, ops no, cli no |
| `tools/offline_telegram_summary.py` | `tools/runtime/offline_telegram_summary.py` | runtime | LOW_PATH_RISK | tests 1, docs 5, ops no, cli yes |
| `tools/operator_summary.py` | `tools/runtime/operator_summary.py` | runtime | LOW_PATH_RISK | tests 0, docs 2, ops no, cli yes |
| `tools/outcome_truth_graduation.py` | `tools/outcome_truth/outcome_truth_graduation.py` | outcome_truth | LOW_PATH_RISK | tests 2, docs 0, ops no, cli yes |
| `tools/outcome_truth_population_manifest.py` | `tools/outcome_truth/outcome_truth_population_manifest.py` | outcome_truth | LOW_PATH_RISK | tests 2, docs 0, ops no, cli yes |
| `tools/outcome_truth_streaming_scan.py` | `tools/outcome_truth/outcome_truth_streaming_scan.py` | outcome_truth | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/paper_evaluation_report.py` | `tools/runtime/paper_evaluation_report.py` | runtime | LOW_PATH_RISK | tests 3, docs 15, ops no, cli yes |
| `tools/phase_b_daily_evidence_collector.py` | `tools/phase_b/phase_b_daily_evidence_collector.py` | phase_b | LOW_PATH_RISK | tests 1, docs 10, ops no, cli yes |
| `tools/phase_b_daily_report.py` | `tools/phase_b/phase_b_daily_report.py` | phase_b | LOW_PATH_RISK | tests 1, docs 10, ops no, cli yes |
| `tools/phase_b_run_daily_pipeline.py` | `tools/phase_b/phase_b_run_daily_pipeline.py` | phase_b | LOW_PATH_RISK | tests 1, docs 9, ops no, cli yes |
| `tools/phase_b_snapshot_archiver.py` | `tools/phase_b/phase_b_snapshot_archiver.py` | phase_b | LOW_PATH_RISK | tests 1, docs 9, ops no, cli yes |
| `tools/phase_b_snapshot_summary.py` | `tools/phase_b/phase_b_snapshot_summary.py` | phase_b | LOW_PATH_RISK | tests 1, docs 8, ops no, cli yes |
| `tools/phase_b_weekly_review_engine.py` | `tools/phase_b/phase_b_weekly_review_engine.py` | phase_b | LOW_PATH_RISK | tests 1, docs 11, ops no, cli yes |
| `tools/probability_semantics_calibration_probe.py` | `tools/probes/probability_semantics_calibration_probe.py` | probes | LOW_PATH_RISK | tests 1, docs 2, ops no, cli yes |
| `tools/quant_data_quality.py` | `tools/research/quant_data_quality.py` | research | LOW_PATH_RISK | tests 3, docs 23, ops no, cli yes |
| `tools/quant_intelligence_engine.py` | `tools/research/quant_intelligence_engine.py` | research | MEDIUM_IMPORT_RISK | tests 1, docs 5, ops yes, cli yes |
| `tools/replay_analyzer.py` | `tools/replay/replay_analyzer.py` | replay | MEDIUM_IMPORT_RISK | tests 4, docs 46, ops yes, cli yes |
| `tools/research_gap_analyzer.py` | `tools/research/research_gap_analyzer.py` | research | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |
| `tools/research_memory_writer.py` | `tools/research/research_memory_writer.py` | research | LOW_PATH_RISK | tests 1, docs 2, ops no, cli yes |
| `tools/research_state_writer.py` | `tools/research/research_state_writer.py` | research | LOW_PATH_RISK | tests 1, docs 2, ops no, cli yes |
| `tools/runtime_event_replay.py` | `tools/replay/runtime_event_replay.py` | replay | LOW_PATH_RISK | tests 1, docs 3, ops no, cli yes |
| `tools/runtime_storage_compressor.py` | `tools/runtime/runtime_storage_compressor.py` | runtime | LOW_PATH_RISK | tests 1, docs 10, ops no, cli yes |
| `tools/semantic_c_bounded_reload_replay.py` | `tools/shadow/semantic_c_bounded_reload_replay.py` | shadow | LOW_PATH_RISK | tests 1, docs 3, ops no, cli yes |
| `tools/semantic_c_inventory_continuity_replay.py` | `tools/shadow/semantic_c_inventory_continuity_replay.py` | shadow | LOW_PATH_RISK | tests 2, docs 2, ops no, cli yes |
| `tools/semantic_c_shadow_fill_replay.py` | `tools/shadow/semantic_c_shadow_fill_replay.py` | shadow | LOW_PATH_RISK | tests 2, docs 1, ops no, cli yes |
| `tools/semantic_c_shadow_observability_report.py` | `tools/shadow/semantic_c_shadow_observability_report.py` | shadow | LOW_PATH_RISK | tests 1, docs 0, ops no, cli yes |
| `tools/semantic_c_shadow_pnl_truth.py` | `tools/shadow/semantic_c_shadow_pnl_truth.py` | shadow | LOW_PATH_RISK | tests 2, docs 2, ops no, cli yes |
| `tools/session_runtime_evaluator.py` | `tools/runtime/session_runtime_evaluator.py` | runtime | LOW_PATH_RISK | tests 2, docs 30, ops no, cli yes |
| `tools/shadow_filter_evaluator.py` | `tools/shadow/shadow_filter_evaluator.py` | shadow | LOW_PATH_RISK | tests 1, docs 18, ops no, cli yes |
| `tools/silent_zone_selection_probe.py` | `tools/probes/silent_zone_selection_probe.py` | probes | NO_IMPORT_RISK | tests 0, docs 0, ops no, cli yes |
| `tools/stabilization_survival_replay.py` | `tools/replay/stabilization_survival_replay.py` | replay | LOW_PATH_RISK | tests 2, docs 2, ops no, cli yes |
| `tools/zero_size_risk_floor_probe.py` | `tools/probes/zero_size_risk_floor_probe.py` | probes | LOW_PATH_RISK | tests 1, docs 1, ops no, cli yes |

## Import Risk Table

| Risk | Count | Interpretation |
|---|---:|---|
| NO_IMPORT_RISK | 1 | Can move first without import/doc/test updates. |
| LOW_PATH_RISK | 76 | Move only with tests/docs command updates and `rg` old-path proof. |
| MEDIUM_IMPORT_RISK | 4 | Move only in coordinated batches with tests, docs, and ops metadata updates. |
| HIGH_RUNTIME_RISK | 0 | No direct runtime-trading importer found for root `tools/*.py` in this audit. |

## Do Not Move Yet

Must remain until a scoped move phase updates references in the same commit:

- `tools/canonical_trade_context_builder.py`
- `tools/canonical_trade_table_v1.py`
- `tools/replay_analyzer.py`
- `tools/quant_intelligence_engine.py`
- `tools/backtest_engine_v2/`
- `tools/flaos/`
- `tools/eth_yes_fc_os_command_center.py`
- `tools/execution_paper_runtime.py`
- `tools/dashboard_state_aggregator.py`
- Any script named directly in `ACTIVE_WORKFLOW_STATE_001.json` or `TASK_QUEUE_001.json`.

Root-level scripts that should remain temporarily for operator familiarity and command stability:

- `tools/quant_data_quality.py`
- `tools/replay_analyzer.py`
- `tools/no_entry_analyzer.py`
- `tools/session_runtime_evaluator.py`
- `tools/paper_evaluation_report.py`
- `tools/canonical_trade_context_builder.py`
- `tools/multi_session_runner.py`
- `tools/offline_telegram_summary.py`

## Phased Migration Plan

### Phase 1A - No-Import-Risk One-Off Probe

Move only:

- `tools/silent_zone_selection_probe.py` -> `tools/probes/silent_zone_selection_probe.py`

Validation:

- `git diff --name-status`
- `rg "tools/silent_zone_selection_probe.py|tools.silent_zone_selection_probe"`
- `python -m py_compile tools/probes/silent_zone_selection_probe.py`
- No pytest, no builders.

### Phase 1B - Research / Export / Outcome Truth

Move:

- `tools/outcome_truth/*.py` target group.
- `tools/phase_b/*.py` target group.
- Low-risk research scripts after doc/test references are patched.

Hold:

- `quant_intelligence_engine.py` until `TASK_QUEUE_001.json` references are updated.
- `quant_data_quality.py`, `no_entry_analyzer.py`, and common operator CLIs until command examples are updated.

Validation:

- `git diff --name-status`
- `rg` old path references for moved files.
- `python -m py_compile` moved scripts only.
- Targeted tests for moved imports only.
- No full pytest, no full builder.

### Phase 1C - Canonical / Replay Tools

Move:

- `canonical_regime_export.py`
- `canonical_trade_table_v1.py`
- `canonical_trade_context_builder.py`
- replay group scripts

Only proceed after updating tests/docs/ops references in the same phase.

Validation:

- `rg "tools/canonical_trade_context_builder.py|tools.canonical_trade_context_builder"`
- `rg "tools/replay_analyzer.py|tools.replay_analyzer"`
- `python -m py_compile` moved scripts only.
- Targeted tests such as `tests/test_canonical_trade_context_builder.py`, `tests/test_canonical_trade_table_v1.py`, and `tests/test_replay_analyzer.py`.
- No full builder.

### Phase 1D - Documentation Link and Command Refresh

Patch documentation command examples after each move phase:

- `README.md`
- `CLAUDE.md`
- `FILE_INDEX.md`
- `DOCUMENTATION_MAP.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/KNOWN_ISSUES.md`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- Relevant reports only when they are active operational docs, not historical records.

Validation:

- `rg "python tools/" docs README.md CLAUDE.md FILE_INDEX.md DOCUMENTATION_MAP.md`
- Ensure stale paths are either historical or updated.

## Recommended Next Task

NEXT_TASK: REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001

## TASK_OUTPUT_CONTRACT

### Task Identity
- Task name: REPOSITORY_PHASE1_TOOLS_AUDIT_REORGANIZATION_001
- Task class: 2
- Agent roles used: PRIMARY=02_CODE_ARCHITECT_AGENT SUPPORTING=07_TEST_CI_AGENT, 24_REPOSITORY_LIBRARIAN_AGENT behavior via router

### Files Changed
- `docs/architecture/TOOLS_STRUCTURE_TARGET_001.md` - target tools structure.
- `docs/reports/REPOSITORY_PHASE1_TOOLS_AUDIT_REORGANIZATION_001.md` - audit and phased plan.
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json` - task state update.
- `docs/operations/TASK_QUEUE_001.json` - task queue update.
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json` - loop memory entry.

### Files Read (Not Changed)
- `tools/*.py` inventory - classification.
- `tools/backtest_engine_v2/` and `tools/flaos/` - existing structured directories.
- `tests/`, `docs/`, and ops JSON references - import/path risk discovery.
- `docs/reports/REPOSITORY_FOLDER_REORGANIZATION_AUDIT_001.md` - prior structure plan.

### Tests Run
- Command: NOT_REQUIRED by design-only scope; no pytest, builders, or backtests were run.
- Result: NOT_REQUIRED
- Pre-existing failures: N/A

### Evidence
- [Grade A] `git status --short` was clean at preflight.
- [Grade A] `git branch -vv` showed `main` tracking `origin/main`, ahead by one local docs commit.
- [Grade B] Tool inventory and reference counts were produced from local filesystem and text search.
- [Grade D] Prior audit alignment confirmed target categories.

### Remaining Uncertainty
- Reference counts are conservative text-search counts. Historical docs may mention old commands intentionally and should be filtered during move phases.

### Commits Made
- NONE

### Active Question Status
- OPEN: LOW_PRICE_TRUTH_RESOLUTION_001

### Batch 2 Authorization
- NOT AUTHORIZED

### Recommended Next Task
- REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001
