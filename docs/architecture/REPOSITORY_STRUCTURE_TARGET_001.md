# REPOSITORY_STRUCTURE_TARGET_001

**Version:** 1.0  
**Date:** 2026-06-28  
**Status:** DESIGN — not yet implemented

Target repository structure after all 8 reorganization phases complete.

---

## Root Level (keep minimal)

```
./
├── main.py                         ← CLI entry point
├── check_balance.py                ← balance check utility
├── daily_report.py                 ← daily report utility
├── hft_paper_run.py                ← paper run script
├── register_api_keys.py            ← API key registration
├── generate_bypass.py              ← bypass utility
├── CLAUDE.md                       ← AI collaboration guide (required at root)
├── AGENTS.md                       ← AI agent governance (required at root)
├── PROJECT_RULES.md                ← Operator rules (required at root)
├── MASTER_AGENT_ROUTER.md          ← Task routing (required at root)
├── CODEX_START_HERE.md             ← Onboarding (required at root)
├── README.md                       ← Project README (required at root)
├── CURRENT_PROJECT_STATUS.md       ← Live status (required at root)
├── pytest.ini                      ← Test configuration
├── pyproject.toml / setup.py       ← Package config
├── .env / .env.example             ← Environment
└── requirements*.txt               ← Dependencies
```

**Removed from root:** All research plan .md, AI handoff .md, prompt .md, CHATGPT/CODEX prompt files.

---

## docs/ — Documentation

```
docs/
├── architecture/               ← Design specs (existing)
│   ├── MARKET_AVAILABILITY_ENGINE_001.md
│   ├── TRADER_MODULE_DECOMPOSITION_001.md
│   └── REPOSITORY_STRUCTURE_TARGET_001.md   ← this file
├── audits/                     ← Audit reports (existing)
├── operations/                 ← Ops state, task queue, loop memory (existing)
│   ├── AI_RESOURCE_GOVERNANCE_001.md
│   ├── REPOSITORY_HEALTH_CHECK_001.md
│   ├── ACTIVE_WORKFLOW_STATE_001.json
│   ├── TASK_QUEUE_001.json
│   ├── loop_memory/
│   ├── execution_contracts/
│   ├── graph_queries/
│   ├── memory/
│   └── skills/
├── reports/                    ← Task reports (existing)
└── research/                   ← NEW: research planning docs
    ├── BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md
    ├── INVENTORY_REPLAY_RESEARCH_PLAN.md
    ├── MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md
    ├── QUANT_FUTURE_DECISION_ENGINE.md
    ├── QUANT_LIFECYCLE_INVENTORY_ENGINE.md
    └── QUANT_REGIME_PROBABILITY_ENGINE.md
```

---

## tools/ — Offline Analysis Scripts

```
tools/
├── backtest_engine_v2/         ← ✓ DONE: BacktestEngineV2 package
│   ├── __init__.py
│   ├── engine.py
│   ├── policy.py
│   ├── equity.py
│   ├── metrics.py
│   ├── scenario.py
│   ├── comparison.py
│   ├── registry.py
│   └── exporter.py
│
├── flaos/                      ← ✓ DONE: FLAOS tooling
│   ├── bootstrap.py
│   ├── knowledge_graph.py
│   ├── log_governance.py
│   ├── memory_migrate.py
│   ├── memory_os.py
│   ├── runtime_session.py
│   ├── schemas.py
│   └── session_schema.py
│
├── canonical/                  ← Phase 2: canonical builders
│   ├── __init__.py
│   ├── canonical_trade_context_builder.py
│   ├── canonical_regime_export.py
│   └── canonical_trade_table_v1.py
│
├── replay/                     ← Phase 3: replay and lifecycle truth
│   ├── __init__.py
│   ├── replay_analyzer.py
│   ├── runtime_event_replay.py
│   ├── commitment_regime_replay.py
│   ├── convergence_regime_classification_replay.py
│   ├── exit_convergence_intelligence_replay.py
│   ├── lifecycle_profit_management_replay.py
│   ├── stabilization_survival_replay.py
│   ├── lifecycle_truth_backfill.py
│   └── lifecycle_truth_tables.py
│
├── probes/                     ← Phase 3: timing and admission probes
│   ├── __init__.py
│   ├── decision_cycle_timing_probe.py
│   ├── entry_budget_consumption_probe.py
│   ├── epoch_boundary_alignment_probe.py
│   ├── executable_state_persistence_probe.py
│   ├── market_readiness_admission_probe.py
│   ├── probability_semantics_calibration_probe.py
│   ├── silent_zone_selection_probe.py
│   ├── zero_size_risk_floor_probe.py
│   ├── event_driven_admission_simulation.py
│   ├── event_driven_fair_value_simulation.py
│   ├── lifecycle_latency_report.py
│   ├── lifecycle_timing_report.py
│   ├── candidate_continuity.py
│   ├── candidate_path_observability.py
│   └── discovery_harness_validation.py
│
├── phase_b/                    ← Phase 1: phase B pipeline
│   ├── __init__.py
│   ├── phase_b_daily_evidence_collector.py
│   ├── phase_b_daily_report.py
│   ├── phase_b_run_daily_pipeline.py
│   ├── phase_b_snapshot_archiver.py
│   ├── phase_b_snapshot_summary.py
│   └── phase_b_weekly_review_engine.py
│
├── outcome_truth/              ← Phase 1: resolution pipeline
│   ├── __init__.py
│   ├── free_outcome_truth_provisional.py
│   ├── free_outcome_truth_provisional_join.py
│   ├── free_outcome_truth_provisional_readiness.py
│   ├── official_resolution_acquire_pilot.py
│   ├── official_resolution_full_history_runner.py
│   ├── official_resolution_outcome_join.py
│   ├── official_resolution_rpc_client.py
│   ├── outcome_truth_graduation.py
│   ├── outcome_truth_population_manifest.py
│   └── outcome_truth_streaming_scan.py
│
├── research/                   ← Phase 3: research analysis
│   ├── __init__.py
│   ├── research_gap_analyzer.py
│   ├── research_memory_writer.py
│   ├── research_state_writer.py
│   ├── quant_intelligence_engine.py
│   ├── quant_data_quality.py
│   ├── edge_inventory_report.py
│   ├── no_entry_analyzer.py
│   └── no_entry_root_cause_report.py
│
├── audit/                      ← Phase 1: audit scripts
│   ├── __init__.py
│   ├── _audit_cs_btc.py
│   ├── _audit_decision_state.py
│   ├── _audit_w21_w22.py
│   ├── _delta_audit.py
│   ├── _delta_causal_verify.py
│   ├── _drift_audit.py
│   ├── _opp_capture_audit.py
│   ├── ev_field_coverage.py
│   ├── ev_field_coverage_audit.py
│   └── executable_truth_overlay.py
│
├── runtime/                    ← Phase 3: runtime support scripts
│   ├── __init__.py
│   ├── multi_session_runner.py
│   ├── session_runtime_evaluator.py
│   ├── runtime_storage_compressor.py
│   ├── dashboard_state_aggregator.py
│   ├── execution_paper_runtime.py
│   ├── paper_evaluation_report.py
│   ├── operator_summary.py
│   ├── offline_telegram_summary.py
│   ├── compact_run_summary.py
│   ├── joined_records_builder.py
│   └── decision_log_slim_index.py
│
└── shadow/                     ← Phase 2: shadow analysis
    ├── __init__.py
    ├── shadow_filter_evaluator.py
    ├── semantic_c_bounded_reload_replay.py
    ├── semantic_c_inventory_continuity_replay.py
    ├── semantic_c_shadow_fill_replay.py
    ├── semantic_c_shadow_observability_report.py
    ├── semantic_c_shadow_pnl_truth.py
    ├── cross_run_ev_blindness.py
    └── cross_run_lifecycle_truth.py
```

---

## tests/ — Test Suite

```
tests/
├── conftest.py                 ← Shared fixtures (existing)
│
├── execution/                  ← Phase 4: order submission, live flow
│   ├── conftest.py
│   ├── test_execution_paper_runtime.py
│   ├── test_execution_risk_controls.py
│   ├── test_execution_timestamp_phase1.py
│   ├── test_execution_timestamp_phase2.py
│   ├── test_execution_timestamp_phase3.py
│   ├── test_execution_timestamp_phase6.py
│   ├── test_live_allowance_preflight.py
│   ├── test_live_credential_and_allowance_readiness.py
│   ├── test_proxy_allowance_semantics.py
│   ├── test_live_fill_loop.py
│   └── test_live_reconciliation_timer.py
│
├── telemetry/                  ← Phase 4: observability and JSONL
│   ├── test_telemetry_backfill.py
│   ├── test_quant_event_logger.py
│   ├── test_orderbook_lineage_probe_v1.py
│   ├── test_entry_model_truth_envelope_v1.py
│   ├── test_entry_attribution_snapshot.py
│   ├── test_quote_lineage_phase4.py
│   └── test_quote_age_phase5.py
│
├── canonical/                  ← Phase 4: canonical context
│   ├── test_canonical_trade_context_builder.py
│   ├── test_canonical_regime_export.py
│   ├── test_canonical_trade_table_v1.py
│   └── test_backtest_engine_v2.py
│
├── replay/                     ← Phase 4: replay suite
│   ├── test_replay_analyzer.py
│   ├── test_commitment_regime_replay.py
│   ├── test_convergence_regime_classification_replay.py
│   ├── test_exit_convergence_intelligence_replay.py
│   ├── test_lifecycle_profit_management_replay.py
│   ├── test_lifecycle_truth_backfill.py
│   └── test_stabilization_survival_replay.py
│
├── policy/                     ← Phase 4: policy and scheduler
│   ├── test_shadow_policy.py
│   ├── test_market_availability_engine.py
│   └── test_risk_modes.py
│
├── shadow/                     ← Phase 4: shadow filters
│   ├── test_shadow_filters.py
│   ├── test_shadow_filter_evaluator.py
│   ├── test_option_d_shadow.py
│   ├── test_delta_shadow.py
│   ├── test_stop_loss_shadow.py
│   ├── test_semantic_c_bounded_reload_replay.py
│   ├── test_semantic_c_inventory_continuity_replay.py
│   ├── test_semantic_c_shadow_fill_replay.py
│   ├── test_semantic_c_shadow_observability_report.py
│   └── test_semantic_c_shadow_pnl_truth.py
│
├── bankroll/                   ← Phase 4: capital quality
│   ├── test_bankroll_rank_engine.py
│   ├── test_bankroll_tiers.py
│   └── test_size_sharp_engine.py
│
├── lifecycle/                  ← Phase 4: position lifecycle
│   ├── test_lifecycle_early_snapshot.py
│   ├── test_lifecycle_latency_report.py
│   ├── test_lifecycle_observability_completion.py
│   ├── test_lifecycle_timing_report.py
│   ├── test_lifecycle_truth_tables.py
│   ├── test_path_truth_checkpoints.py
│   ├── test_exit_agent.py
│   └── test_position_reconciliation.py
│
├── runtime/                    ← Phase 4: paper mode and trader
│   ├── test_paper_mode.py
│   ├── test_polymarket_trader.py
│   ├── test_runtime_loop_exception_observability.py
│   ├── test_runtime_ownership.py
│   ├── test_runtime_shutdown.py
│   ├── test_logging_resilience.py
│   └── test_scan_log_loading.py
│
├── market/                     ← Phase 4: market analysis
│   ├── test_delta_engine.py
│   ├── test_expected_value.py
│   ├── test_probability_model.py
│   ├── test_opportunity_scanner.py
│   ├── test_realtime_feed.py
│   └── test_regime_diagnostics.py
│
├── live/                       ← Phase 4: live mode
│   ├── test_live_telegram_visibility.py
│   ├── test_verify_mode.py
│   ├── test_polymarket_client_v2.py
│   └── test_ghost_position_sentinel.py
│
├── flaos/                      ← Phase 4: FLAOS tooling
│   ├── test_flaos_bootstrap_hardening.py
│   ├── test_flaos_bootstrap_memory_os.py
│   ├── test_flaos_knowledge_graph.py
│   ├── test_flaos_log_governance.py
│   ├── test_flaos_memory_os.py
│   └── test_flaos_runtime_session.py
│
├── outcome_truth/              ← Phase 4: resolution pipeline
│   ├── test_outcome_truth_graduation.py
│   ├── test_outcome_truth_patch.py
│   ├── test_outcome_truth_pipeline_integration.py
│   ├── test_outcome_truth_population_manifest.py
│   ├── test_outcome_truth_streaming_scan.py
│   ├── test_free_outcome_truth_provisional.py
│   ├── test_free_outcome_truth_provisional_join.py
│   └── test_free_outcome_truth_provisional_readiness.py
│
├── phase_b/                    ← Phase 4: phase B pipeline
│   ├── test_phase_b_daily_evidence_collector.py
│   ├── test_phase_b_run_daily_pipeline.py
│   └── test_phase_b_weekly_review_engine.py
│
└── probes/                     ← Phase 4: admission and timing probes
    ├── test_decision_cycle_timing_probe.py
    ├── test_entry_budget_consumption_probe.py
    ├── test_epoch_boundary_alignment_probe.py
    ├── test_executable_state_persistence_probe.py
    ├── test_market_readiness_admission_probe.py
    ├── test_market_readiness_timing.py
    ├── test_probability_semantics_calibration_probe.py
    └── test_zero_size_risk_floor_probe.py
```

---

## polymarket/ — Runtime Modules (after Trader Decomposition)

```
polymarket/
├── __init__.py
├── trader.py                   ← Core (reduced to ~5,000 lines post-decomposition)
├── client.py                   ← CLOB client (DO NOT MOVE)
├── gamma_fetcher.py            ← Market fetcher
├── market_feed.py              ← Market feed
├── oracle_price_feed.py        ← Oracle prices
├── opportunity_scanner.py      ← Scan
├── probability_model.py        ← Model
├── signal.py                   ← Signal
├── expected_value.py           ← EV
├── delta_engine.py             ← Delta
├── regime_diagnostics.py       ← Regime
├── order_manager.py            ← Order mgmt
├── order_intent.py             ← Intent guard
├── position_manager.py         ← Position
├── position_sizing.py          ← Sizing
├── risk_modes.py               ← Risk modes
├── market_availability_engine.py ← ✓ DONE
├── shadow_policy.py            ← ✓ DONE
├── bankroll_rank_engine.py     ← Stay (or move to analytics/)
├── size_sharp_engine.py        ← Stay (or move to analytics/)
├── bankroll_tiers.py           ← Stay
├── trade_frequency.py          ← Stay
├── virtual_ptb.py              ← Stay
│
├── orchestration/              ← ✓ Batch 3C (existing)
│   └── trader_observability.py
│
└── observability/              ← NEW (via Trader Decomposition Phases 1-6)
    ├── trader_size_sharp_observability.py
    ├── trader_decision_diagnostics.py
    ├── trader_orderbook_lineage.py
    ├── trader_market_readiness.py
    └── trader_lifecycle_observability.py
```
