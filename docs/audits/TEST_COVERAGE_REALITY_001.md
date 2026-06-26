# TEST_COVERAGE_REALITY_001

**Task:** FULL_PROJECT_REALITY_AUDIT_001  
**Mode:** DISCOVERY ONLY — no code changes  
**Date:** 2026-06-26  
**Evidence basis:** Test file listing from `tests/test_*.py` glob (100+ files found) and module inventory. Test file contents not read individually — coverage is inferred from filename-to-module mapping only. NOT VERIFIED: which specific code paths are exercised by each test.

---

## Audit Method

Methodology: filename matching + spot-check of test imports from session transcript (`test_paper_mode.py`, `test_polymarket_trader.py`, `test_no_entry_analyzer.py` imports were verified from prior session). Full test body content was not read for all files. Findings below are based on:
1. Existence of a test file with a matching module name → COVERED (file level)
2. No test file with a matching name → UNKNOWN (may still be covered via integration tests)
3. Import verification where available from prior reads

---

## 1. Test Suite Overview

| Metric | Value |
|---|---|
| Total test files found | 100+ (tests/ glob truncated at 100 — exact count: 139 by prior PowerShell count) |
| Test framework | pytest (verified from `pytest.ini` in root, `pytest>=8,<9` in requirements.txt) |
| Test location | All in `tests/` directory |
| Test naming | `test_<module_or_feature>.py` pattern |

---

## 2. Coverage by Module Group

### 2.1 Pure Core Modules — WELL COVERED

| Module | Test File | Coverage Assessment |
|---|---|---|
| `polymarket/bankroll_tiers.py` | `test_bankroll_tiers.py` | COVERED |
| `polymarket/expected_value.py` | `test_expected_value.py` | COVERED |
| `polymarket/probability_model.py` | `test_probability_model.py` | COVERED |
| `polymarket/risk_modes.py` | `test_risk_modes.py` | COVERED |
| `polymarket/delta_engine.py` | `test_delta_engine.py` | COVERED |
| `polymarket/trade_frequency.py` | `test_trade_frequency.py` | COVERED |
| `polymarket/position_sizing.py` | included in `test_paper_mode.py` (verified) | COVERED via integration |
| `polymarket/lucky_shot.py` | `test_lucky_shot.py` | COVERED |
| `polymarket/trend_runner.py` | `test_trend_runner.py` | COVERED |
| `polymarket/regime_diagnostics.py` | `test_regime_diagnostics.py` | COVERED |
| `polymarket/order_intent.py` | NOT found directly (covered in `test_paper_mode.py`) | COVERED via integration |
| `polymarket/order_manager.py` | NOT found directly (covered in `test_paper_mode.py`) | COVERED via integration |

### 2.2 Trader and Paper Mode — COVERED WITH DEPTH

| Module | Test Files | Notes |
|---|---|---|
| `polymarket/trader.py` | `test_polymarket_trader.py`, `test_paper_mode.py` (108KB) | Heavy integration test |
| Paper session flow | `test_paper_mode.py` (largest test file at 108KB) | Full paper mode integration |
| Entry model truth | `test_entry_model_truth_envelope_v1.py` | Specific entry model test |
| Paper execution timestamp | `test_execution_timestamp_phase1.py`, `phase2`, `phase3`, `phase6` | Multi-phase timestamp tests |
| Quote age | `test_quote_age_phase5.py` | Phase 5 quote lineage |
| Quote lineage | `test_quote_lineage_phase4.py` | Phase 4 quote lineage |
| Path truth checkpoints | `test_path_truth_checkpoints.py` | Path truth checkpoint emission |

### 2.3 Position and Reconciliation — COVERED

| Module | Test File |
|---|---|
| `utils/position_tracker.py` | `test_position_tracker.py` |
| `polymarket/position_manager.py` | `test_position_manager.py` |
| `polymarket/arbitrage_executor.py` | `test_arbitrage_executor.py` |
| `utils/position_tracker.py` (reconciliation) | `test_position_reconciliation.py` |

### 2.4 Analytics Tools — WELL COVERED

| Tool | Test File |
|---|---|
| `tools/replay_analyzer.py` | `test_replay_analyzer.py` |
| `tools/quant_data_quality.py` | `test_quant_data_quality.py` |
| `tools/paper_evaluation_report.py` | `test_paper_evaluation_report.py` |
| `tools/session_runtime_evaluator.py` | `test_session_runtime_evaluator.py` |
| `tools/compact_run_summary.py` | `test_compact_run_summary.py` |
| `tools/ev_field_coverage.py` | `test_ev_field_coverage.py` |
| `tools/ev_field_coverage_audit.py` | `test_ev_field_coverage_audit.py` |
| `tools/candidate_continuity.py` | `test_candidate_continuity.py` |
| `tools/candidate_path_observability.py` | `test_candidate_path_observability.py` |
| `tools/cross_run_ev_blindness.py` | `test_cross_run_ev_blindness.py` |
| `tools/cross_run_lifecycle_truth.py` | `test_cross_run_lifecycle_truth.py` |
| `tools/lifecycle_truth_tables.py` | `test_lifecycle_truth_tables.py` |
| `tools/lifecycle_truth_backfill.py` | `test_lifecycle_truth_backfill.py` |
| `tools/lifecycle_profit_management_replay.py` | `test_lifecycle_profit_management_replay.py` |
| `tools/no_entry_analyzer.py` | `test_no_entry_analyzer.py` |
| `tools/offline_telegram_summary.py` | `test_offline_telegram_summary.py` |
| `tools/operator_summary.py` | `test_operator_summary.py` |
| `tools/research_gap_analyzer.py` | `test_research_gap_analyzer.py` |
| `tools/canonical_trade_table_v1.py` | `test_canonical_trade_table_v1.py` |
| `tools/canonical_regime_export.py` | `test_canonical_regime_export.py` |
| `tools/executable_truth_overlay.py` | `test_executable_truth_overlay.py` |
| `tools/execution_paper_runtime.py` | (inferred from session) | LIKELY COVERED |

### 2.5 Probe Tools — COVERED

| Probe | Test File |
|---|---|
| `tools/decision_cycle_timing_probe.py` | `test_decision_cycle_timing_probe.py` |
| `tools/epoch_boundary_alignment_probe.py` | `test_epoch_boundary_alignment_probe.py` |
| `tools/entry_budget_consumption_probe.py` | `test_entry_budget_consumption_probe.py` |
| `tools/executable_state_persistence_probe.py` | `test_executable_state_persistence_probe.py` |
| `tools/market_readiness_admission_probe.py` | `test_market_readiness_admission_probe.py` |
| `tools/zero_size_risk_floor_probe.py` | `test_zero_size_risk_floor_probe.py` |
| `tools/probability_semantics_calibration_probe.py` | `test_probability_semantics_calibration_probe.py` |

### 2.6 Replay Simulation Tools — COVERED

| Tool | Test File |
|---|---|
| `tools/commitment_regime_replay.py` | `test_commitment_regime_replay.py` |
| `tools/convergence_regime_classification_replay.py` | `test_convergence_regime_classification_replay.py` |
| `tools/exit_convergence_intelligence_replay.py` | `test_exit_convergence_intelligence_replay.py` |
| `tools/stabilization_survival_replay.py` | `test_stabilization_survival_replay.py` |
| `tools/semantic_c_*.py` (5 files) | `test_semantic_c_*.py` (5 files) | COVERED |
| `tools/event_driven_admission_simulation.py` | `test_event_driven_admission_simulation.py` | COVERED |
| `tools/event_driven_fair_value_simulation.py` | `test_event_driven_fair_value_simulation.py` | COVERED |

### 2.7 Configuration and Infrastructure — COVERED

| Module | Test File |
|---|---|
| `config/settings.py` (validation) | `test_config_validation.py` |
| `main.py` (verify mode) | `test_verify_mode.py` |
| `main.py` (runtime shutdown) | `test_runtime_shutdown.py` |
| `main.py` (loop exception) | `test_runtime_loop_exception_observability.py` |
| `utils/no_entry_diagnostics.py` | indirectly via `test_no_entry_root_cause_classifier.py` |
| CLOB empty response | `test_empty_orderbook_fail_soft.py` |
| Scan log loading | `test_scan_log_loading.py` |
| Stale feed kill switch | `test_stale_feed_kill_switch.py` |
| Logging resilience | `test_logging_resilience.py` |

---

## 3. Modules with NO Direct Test File Found

The following modules have no directly named test file. They may be covered by integration tests or may be genuinely untested.

| Module | Size | Coverage Status | Notes |
|---|---|---|---|
| `utils/display.py` | 217 KB | NOT DIRECTLY TESTED | No `test_display.py`. Largest untested module. |
| `utils/logger.py` | unknown | NOT DIRECTLY TESTED | No `test_logger.py`. Partially covered via `test_logging_resilience.py` |
| `utils/telegram_alerts.py` | unknown | NOT DIRECTLY TESTED | No `test_telegram_alerts.py` |
| `utils/telegram_reporter.py` | unknown | NOT DIRECTLY TESTED | No `test_telegram_reporter.py` |
| `utils/runtime_event_stream.py` | unknown | NOT DIRECTLY TESTED | No direct test; may be covered in paper mode tests |
| `utils/runtime_ownership.py` | unknown | NOT DIRECTLY TESTED | No direct test |
| `utils/rate_limiter.py` | unknown | NOT DIRECTLY TESTED | No direct test |
| `polymarket/market_feed.py` | unknown | NOT DIRECTLY TESTED | No `test_market_feed.py` |
| `polymarket/oracle_price_feed.py` | unknown | NOT DIRECTLY TESTED | No direct test |
| `polymarket/gamma_fetcher.py` | unknown | NOT DIRECTLY TESTED | No `test_gamma_fetcher.py` |
| `polymarket/virtual_ptb.py` | unknown | NOT DIRECTLY TESTED | No direct test |
| `polymarket/shadow_telemetry.py` | unknown | NOT DIRECTLY TESTED | No direct test |
| `polymarket/five_min_monitor.py` | unknown | NOT DIRECTLY TESTED | No direct test |
| `polymarket/price_to_beat_fetcher.py` | unknown | NOT DIRECTLY TESTED | No direct test |
| `dashboard/app.py` | 5 KB | PARTIALLY TESTED | `test_offline_quant_report_dashboard.py` exists |
| `api/dashboard_api.py` | unknown | PARTIALLY TESTED | `test_dashboard_api.py` likely exists |

---

## 4. Test Quality Observations

### 4.1 Integration vs Unit Tests

`test_paper_mode.py` (108,420 bytes) and `test_session_runtime_evaluator.py` (112,211 bytes) are very large test files. This suggests:
- Heavy integration test structure — tests span many modules together
- May mask gaps in unit coverage for individual components

### 4.2 Tests That Protect Runtime Behavior

From import verification (prior reads), tests that directly protect runtime-critical paths:

| Test | What It Protects |
|---|---|
| `test_risk_modes.py` | Risk mode thresholds (0.04/0.02 drawdown, 3/2 losses) — changes here would break risk controls |
| `test_bankroll_tiers.py` | Tier boundaries and Kelly fractions — changes here affect position sizing |
| `test_expected_value.py` | EV calculation math |
| `test_probability_model.py` | p_yes/p_no confidence scoring |
| `test_paper_mode.py` | Full paper mode integration including paper/live separation |
| `test_runtime_shutdown.py` | Clean shutdown of background threads and event streams |
| `test_stale_feed_kill_switch.py` | Data staleness protection |
| `test_empty_orderbook_fail_soft.py` | CLOB empty response handling |
| `test_path_truth_checkpoints.py` | Trade lifecycle observability |
| `test_entry_model_truth_envelope_v1.py` | Entry model validation |

### 4.3 Tests Likely Coupled to File Layout

The following test patterns suggest coupling to current file layout that would break on reorganization:

| Pattern | Risk |
|---|---|
| `from api.dashboard_api import create_app` | Would break if `api/` → `dashboard/` |
| `from crypto_scalper.live_runner import ...` | Would break if moved to `experiments/` |
| `monkeypatch.setitem(sys.modules, "crypto_scalper.live_runner", ...)` (`test_runtime_shutdown.py:83`) | Same |
| Any test importing `from hft.*` | Would break if moved to `experiments/` |

### 4.4 Stale Tests (Potential)

From test filenames with phase/version numbering:
- `test_execution_timestamp_phase1.py`, `phase2`, `phase3`, `phase6` — no phase4 or phase5 test; naming suggests versioned development. Phase 5 is a different test (`test_quote_age_phase5.py`). NOT VERIFIED whether earlier phases are superseded.

---

## 5. Test Coverage Summary

| Group | Modules | Coverage |
|---|---|---|
| Pure core modules (risk, sizing, EV, probability, tiers) | ~8 modules | HIGH |
| Trader and paper mode integration | trader.py, order_manager, order_intent | HIGH (integration) |
| Analytics tools | 40+ tools | HIGH |
| Probe tools | 7 tools | HIGH |
| Replay simulation tools | 12+ tools | HIGH |
| Infrastructure (config, logger, shutdown) | 5 modules | MEDIUM |
| Market data modules (market_feed, oracle, gamma) | 3 modules | LOW |
| Display and UI | display.py (217KB) | NONE |
| Event streaming | runtime_event_stream.py | LOW |
| Telegram alerting | telegram_alerts.py, telegram_reporter.py | NONE |
| Dashboard Python files | app.py, live_dashboard.py | LOW |

**Overall:** Tool suite and pure logic modules are well-tested. The runtime data ingestion path (WebSocket, market_feed, gamma_fetcher) and the terminal UI have low or no test coverage. This is typical for network-dependent and display modules but should be noted as a risk area for regression.
