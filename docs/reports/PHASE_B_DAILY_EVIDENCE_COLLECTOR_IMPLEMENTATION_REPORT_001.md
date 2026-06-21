# Implementation Report: Phase B Daily Evidence Collector
**ID**: PHASE_B_DAILY_EVIDENCE_COLLECTOR_IMPLEMENTATION_REPORT_001  
**Status**: DAILY_EVIDENCE_COLLECTOR_IMPLEMENTED  

## 1. Files Created
* [tools/phase_b_daily_evidence_collector.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/phase_b_daily_evidence_collector.py): Main command-line offline metrics collector.
* [tests/test_phase_b_daily_evidence_collector.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tests/test_phase_b_daily_evidence_collector.py): Pytest file validating the collector logic.

## 2. Metrics Implemented
For each active shadow filter, the collector calculates:
* `candidates_seen`: Total shadow telemetry rows.
* `candidates_passed`: Count where `shadow_pass == True`.
* `candidates_rejected`: Count where `shadow_pass == False`.
* `pass_rate`: `candidates_passed / candidates_seen`.
* `closed_candidates_seen`: Joined closed trade count.
* `join_coverage_pct`: percentage of closed trades successfully joined to a shadow event.
* `realized_pnl`: Sum of closed joined trade PnLs that passed the filter.
* `rejected_pnl`: Sum of closed joined trade PnLs that were rejected/blocked by the filter.
* `baseline_pnl`: Sum of realized + rejected joined closed PnLs.
* `delta_vs_baseline`: `realized_pnl - baseline_pnl` (the financial benefit/penalty of the filter).
* `profit_factor`: Gross profit / abs(gross loss) of passed trades (with handling for `"INF"`, `"UNDEFINED"`, and `"UNDERPOWERED"` when passed trades count < 10).
* `winrate`: Winning passed trades / non-flat passed trades.
* `max_drawdown`: Peak-to-trough max drawdown of cumulative passed trade PnL.
* `baseline_max_drawdown`: Peak-to-trough max drawdown of cumulative baseline trade PnL.
* `top_reject_reason`: Most common reason for rejection in shadow telemetry.
* `schema_complete_rows`: Count of telemetry rows matching the expected schema.
* `schema_incomplete_rows`: Count of telemetry rows violating schema completeness.
* `exception_count`: Telemetry exceptions detected.
* `status`: Assigned governance state.

## 3. Join Strategy Implemented
* **Primary Join**: Uses `(run_id, candidate_instance_id)` from shadow log payload matching trade close journals.
* **Fallback Join**: Uses `paper_trade_replay_key` when the primary key is missing or mismatched.
* **Coverage Tracking**: Unmatched trades do not join and decrease `join_coverage_pct`, ensuring any data gaps are immediately visible.

## 4. Governance States Implemented
* `NOT_READY`: Assigned if days observed < 3, closed joined trades < 20, join coverage < 95%, schema completeness < 100%, or exception count > 0.
* `WATCHLIST`: Assigned when minimum requirements are met, delta vs baseline > 0, profit factor >= 1.0, and drawdown <= baseline drawdown * 1.10.
* `CANDIDATE`: Assigned when days observed >= 5, closed joined trades >= 35, join coverage >= 97%, PF >= filter-specific threshold (1.00 for `block_btc_shadow`, 1.15 for `block_normal_vol_shadow`, 1.10 for `combined_broad_shadow`, 1.25 for `combined_conservative_shadow`), winrate within 5% of baseline, max drawdown <= baseline, and rejected PnL <= 0.
* `PROMOTION_REVIEW`: Assigned when candidate conditions are met, days observed >= 7, closed joined trades >= 50, join coverage >= 98%, rejected PnL < 0, winrate >= baseline, and PF >= filter-specific promotion threshold.
