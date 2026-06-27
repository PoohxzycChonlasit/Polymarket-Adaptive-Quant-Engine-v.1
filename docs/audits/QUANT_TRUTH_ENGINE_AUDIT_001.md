# QUANT_TRUTH_ENGINE_AUDIT_001

> **TASK_CLASS: 1 - RESEARCH**
> **PRIMARY: 08_RESEARCH_QUANT_AGENT | SUPPORTING: 10_BACKTEST_REPLAY_AGENT, 25_DATA_STEWARD_AGENT**
> **Date: 2026-06-28 | Evidence Grade: B (source-code) + A (runtime observed)**

---

## FINAL_VERDICT

```
DATA_READINESS:    PARTIAL - 10 of 17 lifecycle fields present at open; 6+ missing at close
METRICS_READY:     PARTIAL - expectancy/winrate/profit_factor READY; Sharpe/Sortino/Kelly PARTIAL; slippage/adverse selection NOT READY
MISSING_FIELDS:    bankroll_tier+risk_mode at close; ev/fair_value at close; drawdown curve; slippage; loss/win streak
NEXT_TASK:         TELEMETRY_BACKFILL_FOR_QUANT_TRUTH_001
```

---

## 1. Runtime Data Inventory

### 1.1 Event Stream (runtime/event_stream/)

| File | Size | Date Coverage |
|---|---|---|
| runtime_events_2026-06-25_001.jsonl | 7.8 MB | 2026-06-25 |
| runtime_events_2026-06-26_001.jsonl | 129 MB | 2026-06-26 |
| runtime_events_2026-06-27_001.jsonl | 110 MB | 2026-06-27 |

Total: ~246 MB of high-frequency unified runtime stream (3 days only). Not the primary quant analysis source.

### 1.2 Quant Data Subdirectory (runtime/quant_data/)

**Total JSONL across all streams: ~28.6 GB** (30,718,405,294 bytes)

| Stream | Date Range | Files | Notes |
|---|---|---|---|
| decision_log/ | 2026-05-08 to 2026-06-27 | 49 | Primary: signal, EV, probability, skip reasons, bankroll tier |
| execution_log/ | 2026-05-08 to 2026-06-27 | 48 | Order submission, exit events |
| trade_journal/ | 2026-05-08 to 2026-06-27 | 47 | trade_open + trade_close with PnL |
| risk_log/ | 2026-05-08 to 2026-06-27 | 53 | Risk mode changes, sizing diagnostics |
| market_snapshots/ | 2026-05-08 to 2026-06-27 | 50 | Orderbook, spread, liquidity per cycle |
| path_truth/ | 2026-05-24 to 2026-06-27 | 33 | trade_path_checkpoint (MFE/MAE intra-trade) |
| signal_filter_shadow/ | 2026-06-17 to 2026-06-27 | 11 | Signal filter shadow (candidate rejection data) |
| system_health/ | 2026-05-08 to 2026-06-27 | 49 | Health probes, lockdowns, errors |
| orderbook_lineage/ | varies | multiple | Orderbook state transitions |

**Coverage: 51 calendar days** (2026-05-08 to 2026-06-27, with gaps 2026-06-03, 2026-05-15-16).

### 1.3 Aggregate Trade Counts (all-time, Grade A)

| Metric | Value |
|---|---|
| trade_open events (all-time) | 797 |
| trade_close events (all-time) | 2,148 |
| Real closed trades (non-test, with PnL) | 1,469 |
| Wins | 924 |
| Losses | 545 |
| Gross paper PnL | +$347.43 |
| Implied win rate (paper) | 62.9% |

> **Note**: trade_close > trade_open because many legacy/test positions were closed without matching opens.
> The paper_trade_replay_key join field exists for matching (see canonical_trade_table_v1.py).
> Exit reason=test accounts for 76/217 closes on 2026-06-26 - these are simulation exits, not real paper exits.
> True paper session win rate should filter by reason NOT IN ('test').

### 1.4 Event Schema Version

All events carry: schema_version: "1.0", packet_schema_version: "1.0", event_type, mode, run_id,
timestamp_utc, source_module. Schema is consistent. No schema drift detected in sampled files.

---

## 2. Trade Lifecycle Coverage

| Field | Present at Open | Present at Close | Source | Quality |
|---|---|---|---|---|
| signal | YES | YES | trade_open.signal_name | DIRECT |
| signal_reason | YES | YES | trade_open.signal_reason | DIRECT |
| strategy_signal | YES | YES | trade_open.strategy_signal_name | DIRECT |
| probability (p_yes/p_no) | YES | NO | trade_open.model_p_yes/no | MISSING at close |
| EV | YES | NO | trade_open.ev, ev_after_spread | MISSING at close; join required |
| fair_value | YES | NO | trade_open.fair_value | MISSING at close |
| entry_decision | YES | partial | trade_open.candidate_block_reason | join required at close |
| order_size | YES | YES | trade_open.size | DIRECT |
| entry_price | YES | YES | trade_open.entry_price | DIRECT |
| fill_status | YES | YES | trade_open.receipt | paper mode fills present |
| exit_reason | N/A | YES | trade_close.reason | DIRECT |
| exit_price | N/A | YES | trade_close.exit_price | DIRECT |
| realized_pnl | N/A | YES | trade_close.pnl/pnl_usdc | DIRECT |
| holding_time | N/A | YES | trade_close.hold_seconds | DIRECT |
| market_state (lifecycle_phase) | YES | partial | trade_open/close.lifecycle_phase | UNKNOWN in most closes |
| bankroll_tier | via join only | NO | risk_plan_zero_diagnostics in decision_log | MISSING in trade_close |
| risk_mode | via join only | NO | risk_log or nested decision_log field | MISSING in trade_close directly |
| exposure | YES | NO | trade_open.current_exposure | MISSING at close |

**Summary**: 10/17 fields directly available in trade_open. trade_close is missing: probability, EV,
fair_value, bankroll_tier, risk_mode, exposure, lifecycle_phase. These are joinable via position_id +
replay_chain_id but require cross-stream join (canonical_trade_table_v1.py).

---

## 3. Quant Metrics Feasibility

| Metric | Status | Reason |
|---|---|---|
| Win rate | READY | 1,469 closed trades; trade_result field present |
| Expectancy (avg PnL per trade) | READY | pnl_usdc present in all closes with trade_result |
| Gross profit / gross loss | READY | Sum of positive / negative PnL from trade_close |
| Profit factor | READY | gross_profit / abs(gross_loss) computable now |
| Max drawdown | PARTIAL | No pre-built equity curve; must reconstruct from trade_close sorted by timestamp |
| Recovery factor | PARTIAL | Depends on drawdown; constructible from equity reconstruction |
| Sharpe ratio | PARTIAL | Daily PnL computable per day; std of daily returns computable |
| Sortino ratio | PARTIAL | Downside deviation computable from daily PnL series |
| Kelly estimate | PARTIAL | Win rate + avg_W/avg_L computable; EV at close missing; needs join |
| EV accuracy | PARTIAL | EV at open available; actual outcome at close; join by position_id required |
| Slippage / fill quality | NOT READY | Paper trades use default entry_price=0.50. Effective fill vs orderbook mid not separately tracked |
| Adverse selection | NOT READY | Requires order submission time vs. fill vs. mark-to-market; absent in paper mode |
| Opportunity cost | NOT READY | signal_filter_shadow exists but outcome truth not joined to skipped signals |

### Computed Now from Sampled Data (Grade A)

```
Paper win rate (all-time):  62.9%  (924W / 545L on 1469 real closes)
Paper gross PnL:            +$347.43 (all modes combined)
Exit reasons (sample 2026-06-26):
  test: 76, forced_exit: 42, stop_loss: 28, take_profit_partial: 25,
  take_profit_full: 21, take_profit: 16, emergency_flatten: 4
```

---

## 4. Bankroll Rank Data Requirements

| Field | Available | Location | Quality |
|---|---|---|---|
| current bankroll | YES | decision_log.paper_available_balance | DIRECT per cycle |
| equity (cash + unrealized) | PARTIAL | decision_log.paper_virtual_cash + paper_open_position_value | DIRECT but unrealized approximate |
| realized PnL | PARTIAL | Sum of trade_close.pnl_usdc per session | Computable; no pre-built cumulative field |
| unrealized PnL | PARTIAL | path_truth.unrealized_pnl | PARTIAL - path_truth starts 2026-05-24 only |
| drawdown | MISSING | Not emitted directly | Must reconstruct from equity curve; no drawdown_pct event |
| loss streak | MISSING | Not emitted directly | Must compute from ordered trade_close sequence |
| win streak | MISSING | Not emitted directly | Same |
| volatility of equity curve | MISSING | Not emitted directly | Must build from daily equity series |
| capital survivability | MISSING | Not present | Requires floor + drawdown + streak combination |
| recovery state | PARTIAL | risk_log mentions MICRO_RECOVERY mode | Partial - state label in risk_plan_zero_diagnostics.risk_mode |
| growth state | MISSING | Not emitted directly | No growth_rate or growth_state event |

---

## 5. Size Sharp Data Requirements

| Field | Available | Location | Quality |
|---|---|---|---|
| EV | YES | trade_open.ev_after_spread / decision_log.ev_after_spread | DIRECT |
| probability edge | YES | trade_open.model_p_yes/no, true_probability | DIRECT |
| liquidity | YES | decision_log.liquidity_state, prob_model_liquidity_usd | DIRECT |
| spread | YES | decision_log.spread, spread_limit | DIRECT |
| orderbook depth | YES | trade_open.top_bid_depth, total_bid_depth_l1_l3 | DIRECT |
| fill probability | PARTIAL | Not emitted as a field; inferred from liquidity_state | PARTIAL |
| market regime | YES | decision_log.volatility_regime, trend_regime | DIRECT |
| volatility | YES | decision_log.realized_volatility, volatility_score | DIRECT |
| time remaining | YES | decision_log.seconds_remaining, seconds_until_close | DIRECT |
| current inventory | PARTIAL | trade_open.current_exposure | PARTIAL - at open only |
| bankroll rank | MISSING | Not emitted as a computed rank field | MISSING - tier exists but rank score does not |
| risk_mode | PARTIAL | risk_plan_zero_diagnostics.risk_mode in decision_log (nested) | PARTIAL - nested, not top-level |
| opportunity cost | MISSING | Not tracked | MISSING |

---

## 6. Replay / Backtest Readiness

### Tools Available (Grade B)

| Tool | File | Capability |
|---|---|---|
| replay_analyzer.py | tools/ (77 KB, 1694 lines) | Phase 2 lifecycle coverage, skip-reason analysis, spread/liquidity readiness |
| canonical_trade_table_v1.py | tools/ (62 KB, 1458 lines) | Cross-stream trade join via paper_trade_replay_key; CSV + summary |
| backtester_5m.py | polymarket/ (38 KB, 798 lines) | Historical backtest on Coinbase OHLCV; Sharpe, Sortino, max DD, profit factor |
| quant_data_quality.py | tools/ (23 KB, 560 lines) | Schema validation, phase2 coverage, replay continuity |
| compact_run_summary.py | tools/ (141 KB) | Cross-session summary |
| ev_field_coverage.py | tools/ (207 KB) | EV field coverage audit |
| session_runtime_evaluator.py | tools/ (195 KB) | Comprehensive session evaluation |

### Grouping Capability Assessment

| Grouping | Status | Path |
|---|---|---|
| PnL by signal type | READY | signal_name in trade_open; join to close via position_id |
| PnL by market state (lifecycle_phase) | PARTIAL | lifecycle_phase = UNKNOWN in most closes; use open's phase |
| PnL by EV bucket | PARTIAL | EV at open available; join required (not in close) |
| PnL by time remaining | PARTIAL | seconds_remaining_when_eligible present in some events |
| PnL by bankroll tier | PARTIAL | Tier in decision_log via risk_plan_zero_diagnostics; join required |
| PnL by sizing bucket | PARTIAL | size in close; tier in join |
| Decision vs counterfactual skip | NOT READY | signal_filter_shadow exists but outcome truth not joined |

### Backtester Limitations

backtester_5m.py uses Coinbase 5-min OHLCV + simulated slippage (0.3-1.5 cents) + 2% fee.
It does NOT replay the actual live probability model or actual orderbook bid/ask seen during paper sessions.
Useful for strategy research but NOT for validating live paper session truth.

---

## 7. Telemetry Backfill Needs

### Priority 1 - Required for Basic Quant Truth (Carry-Forward at Close)

| Field | Where to Add | Event |
|---|---|---|
| bankroll_tier_id | Carry-forward from entry context | trade_journal/trade_close |
| bankroll_tier_name | Carry-forward from entry context | trade_journal/trade_close |
| bankroll_family | Carry-forward from entry context | trade_journal/trade_close |
| risk_mode | Carry-forward from entry context | trade_journal/trade_close |
| ev_at_entry | Carry-forward ev_after_spread from open | trade_journal/trade_close |
| fair_value_at_entry | Carry-forward fair_value from open | trade_journal/trade_close |
| true_probability_at_entry | Carry-forward from open | trade_journal/trade_close |
| lifecycle_phase_at_entry | Carry-forward from open | trade_journal/trade_close |
| notional_size | Already in open; missing in close | trade_journal/trade_close |
| seconds_remaining_at_entry | Carry-forward seconds_remaining | trade_journal/trade_close |

### Priority 2 - Required for Bankroll Rank (New Event Type)

| Field | Where to Add | Event |
|---|---|---|
| cumulative_realized_pnl | Rolling sum after each close | New bankroll_update_v1 event |
| current_drawdown_pct | Session peak equity minus current equity | New bankroll_update_v1 event |
| loss_streak_count | Consecutive losses since last win | New bankroll_update_v1 event |
| win_streak_count | Consecutive wins since last loss | New bankroll_update_v1 event |
| equity_volatility_30d | Rolling std of daily equity | New bankroll_update_v1 event |
| recovery_state | GROWING / RECOVERING / STABLE | New bankroll_update_v1 event |

### Priority 3 - Required for Size Sharp

| Field | Where to Add | Event |
|---|---|---|
| fill_probability_estimate | Estimated from spread + depth | trade_open |
| effective_slippage_cents | Actual fill vs mid-price | trade_open (live mode) |
| opportunity_cost_usd | From skipped signals that resolved correctly | New opportunity_cost_v1 event |
| bankroll_rank_score | Composite score 0-100 | New bankroll_update_v1 event |

### Priority 4 - Required for Counterfactual Replay

| Field | Where to Add | Event |
|---|---|---|
| market_outcome | YES/NO resolved outcome | Join from official_resolution tools |
| counterfactual_decision | What bot would decide with perfect info | Offline computation tool |

---

## 8. Recommended Roadmap

### Verdict: TELEMETRY_BACKFILL_FOR_QUANT_TRUTH_001 First

**Rationale:**

1. The core trade data is rich. 797 trade_open events and 1,469 real closes spanning 51 days is a
   meaningful dataset for paper evaluation.

2. canonical_trade_table_v1.py already exists for cross-stream joining. The question is whether it
   can produce complete rows for Bankroll Rank / Size Sharp without backfill.

3. The critical gap is at trade_close: EV, probability, fair_value, bankroll_tier, and risk_mode are
   all absent. Every quant metric that needs these at exit-time must do a fragile join.
   paper_trade_replay_key matching has legacy coverage issues
   (entry_attribution_status: missing_legacy observed in sampled data).

4. Before implementing Bankroll Rank or Size Sharp in the runtime, the telemetry backfill ensures
   every future live trade is fully observable without fragile joins. This is the minimum viable
   data foundation for the Quant Truth Engine.

### Sequencing

```
STEP 1: TELEMETRY_BACKFILL_FOR_QUANT_TRUTH_001  (Class 5 - OBSERVABILITY)
   - Add Priority 1 fields to trade_close emission in trader.py
   - Narrowest possible change; does not alter strategy/risk/sizing logic
   - Add tests confirming fields are emitted in trade_close payload

STEP 2: BANKROLL_RANK_AND_SIZE_SHARP_IMPLEMENTATION_PLAN_001  (Class 2 - DESIGN)
   - Design Bankroll Rank score (0-100 composite) using now-complete telemetry
   - Design Size Sharp multiplier from EV + tier + regime + fill probability

STEP 3: BANKROLL_RANK_IMPLEMENTATION_001  (Class 7 - FEATURE)
   - Implement Bankroll Rank engine using Priority 2 fields
   - Paper validate with 5+ session evidence before any live use
```

---

## TASK_OUTPUT_CONTRACT

### Task Identity
- Task name: QUANT_TRUTH_ENGINE_AUDIT_001
- Task class: 1 (RESEARCH)
- Agent roles used: PRIMARY=08_RESEARCH_QUANT_AGENT SUPPORTING=10_BACKTEST_REPLAY_AGENT, 25_DATA_STEWARD_AGENT

### Files Changed
- docs/audits/QUANT_TRUTH_ENGINE_AUDIT_001.md - [NEW] this audit
- docs/reports/QUANT_TRUTH_ENGINE_AUDIT_001.md - [NEW] report (cross-reference)
- docs/operations/ACTIVE_WORKFLOW_STATE_001.json - updated
- docs/operations/TASK_QUEUE_001.json - updated
- docs/operations/loop_memory/LOOP_MEMORY_20260627_001.json - updated

### Files Read (Not Changed)
- runtime/quant_data/trade_journal/*.jsonl
- runtime/quant_data/decision_log/*.jsonl
- runtime/quant_data/execution_log/*.jsonl
- runtime/quant_data/path_truth/*.jsonl
- runtime/quant_data/signal_filter_shadow/*.jsonl
- runtime/event_stream/*.jsonl
- tools/replay_analyzer.py
- tools/quant_data_quality.py
- tools/canonical_trade_table_v1.py
- polymarket/backtester_5m.py
- polymarket/position_sizing.py
- utils/risk_manager.py

### Tests Run
- Command: NOT_REQUIRED (Class 1 research)
- Result: NOT_REQUIRED

### Evidence
- [Grade A] trade_open=797, trade_close=2148, real_closes=1469 wins=924 losses=545 PnL=+$347.43
- [Grade A] trade_close payload missing: true_probability, fair_value, ev, bankroll_tier_id, risk_mode
- [Grade A] decision_log contains bankroll_tier_id, bankroll_family, paper_available_balance per cycle
- [Grade B] canonical_trade_table_v1.py exists as cross-stream join tool
- [Grade B] replay_analyzer.py computes phase2 coverage, skip reasons, spread/liquidity readiness
- [Grade B] backtester_5m.py outputs Sharpe, Sortino, max_drawdown, profit_factor

### Remaining Uncertainty
- True paper session PnL (filtering reason=test) not computed here
- backtester_5m.py uses simplified signals; diverges from real paper session outcomes
- Legacy closes (pre-2026-05-24) may lack paper_trade_replay_key join field

### Commits Made
- NONE

### Active Question Status
- CLOSED: Data readiness for Quant Truth Engine assessed

### Batch 2 Authorization
- NOT AUTHORIZED

### Recommended Next Task
- TELEMETRY_BACKFILL_FOR_QUANT_TRUTH_001 (Class 5 - OBSERVABILITY)
