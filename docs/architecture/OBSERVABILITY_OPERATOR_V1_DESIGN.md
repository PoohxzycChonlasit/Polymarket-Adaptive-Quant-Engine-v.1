# DESIGN SPECIFICATION — OBSERVABILITY_OPERATOR_V1

This document outlines the detailed design of the 24/7 operator visibility improvements.

---

## Phase 1: Entry Funnel Panel

### Objective
Provide a real-time terminal UI panel displaying the progression of candidate markets through the analysis pipeline, identifying where candidates are rejected and the top bottleneck.

### Data Model
Track the following counters in `PaperSessionStats` (defined in [polymarket/trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py)):
- `funnel_candidates`: Increment at the start of market analysis.
- `funnel_orderbook_ready`: Increment if the market feed is valid, token mapping is resolved, the orderbook is successfully retrieved with valid bids/asks, and cutoff checks pass.
- `funnel_confidence_pass`: Increment if the candidate has a calculated confidence $\ge 0.54$ and did not fail model checks.
- `funnel_ev_pass`: Increment if the candidate has positive/approved EV.
- `funnel_delta_pass`: Increment if the candidate has a safe volatility/trend regime (not extreme).
- `funnel_risk_size_pass`: Increment if the risk engine computed a non-zero position size.
- `funnel_trade_open`: Increment when a trade/order is successfully submitted and simulated.

### Pipeline Instrumentation
In `_analyze_market_quant()`, we track the pipeline progression:
1. `Candidates`: Incremented immediately on entry.
2. `Orderbook Ready`: Determined if the analysis reaches the signal generation step (past feed/orderbook validation).
3. `Confidence Pass`: Evaluated as `confidence >= 0.54` and not `probability.skipped`.
4. `EV Pass`: Evaluated as `ev_result and ev_result.approved and scan.decision == OpportunityDecision.BEST_TRADE`.
5. `Delta Pass`: Evaluated as `delta.delta_regime != DeltaRegime.EXTREME and delta.delta_multiplier > 0`.
6. `Risk Size Pass`: Evaluated as `risk_plan.position_size > 0`.
7. `Trade Open`: Evaluated when `outcome.skipped` is `False`.

At the exit of `_analyze_market_quant()`, we update the corresponding counters sequentially.

### Panel Display
Add a new panel method `_entry_funnel_panel(self, spec)` in [utils/display.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/display.py). The panel displays the raw counts, conversion percentage relative to `Candidates`, and the most common skip reason as the `Top Bottleneck`.

---

## Phase 2: Defensive Mode Explanation

### Objective
Replace the static `Mode: DEFENSIVE` and `Mode: MICRO_RECOVERY` labels with an interactive block explaining why the mode was entered and the exit release criteria.

### Data Flow
1. Expose `consecutive_losses` and the current risk mode `reason` inside the portfolio state payload returned by `dashboard_portfolio_state()` in `polymarket/trader.py`.
2. In [utils/display.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/display.py)'s `_risk_panel`, check the active mode:
   - If `DEFENSIVE`:
     - **Reason**: `loss_streak=2` (if consecutive losses $\ge 2$) or `drawdown_ge_2pct` (if drawdown $\ge 0.02$).
     - **Exit**: `1 win OR drawdown < 2%`.
   - If `MICRO_RECOVERY`:
     - **Reason**: `loss_streak=3` (if consecutive losses $\ge 3$) or `drawdown_ge_4pct` (if drawdown $\ge 0.04$).
     - **Exit**: `1 win OR drawdown < 4%`.

---

## Phase 3: Shadow Panel Cleanup

### Objective
Restructure the stop loss/signal shadow monitoring panel to separate session (daily) and lifetime statistics, providing a clear breakdown of shadow reject reasons while removing ambiguous counters.

### Restructured Schema
The panel will display:
- **Session (Daily)**: Shadow Events, Would Reject, and Reject Rate.
- **Lifetime**: Cumulative Shadow Events, Would Reject, and Reject Rate.
- **Reason Breakdown**: EV Cap, YES Floor, and Both.

### Metrics Retrieval
- **Session**: Retained in memory inside [polymarket/trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) via `self._baseline_accepted`, `self._shadow_would_reject`, `self._ev_cap_shadow_rejects`, `self._yes_floor_shadow_rejects`, and `self._both_shadow_rejects`. At startup, these values are populated from the daily `{today_str}.jsonl` to survive restarts.
- **Lifetime**: Dynamically scanned from `runtime/quant_data/signal_filter_shadow/*.jsonl` log files on load.

---

## Phase 4: System Health Score

### Objective
Track and display the statuses of the core system daemons and calculate a composite health score from 0 to 100.

### Components Evaluated
1. **Ownership**: `OK` if `runtime_owner` matches current process, else `FAIL` (deduction: -40).
2. **Heartbeat**: `OK` if the last heartbeat attempt succeeded, else `WARN` (deduction: -15) or `FAIL` (deduction: -30).
3. **Telegram**: `OK` if configured with bot tokens, `WARN` if recent send failures exist, else `FAIL` (deduction: -20).
4. **JSONL**: `OK` if writing decision events successfully, else `WARN` (deduction: -15) or `FAIL` (deduction: -30).
5. **Orderbook**: `OK` if CLOB status is OK, else `WARN` (deduction: -20) or `FAIL` (deduction: -40).
6. **Decision Logs**: `OK` if decision log writes are succeeding.

---

## Phase 5: Telegram Alive V2

### Objective
Extend the hourly `ALIVE` Telegram alert to include runtime metadata, decision stats, blocker reasons, risk mode, and health scores.

### Message Template
```text
ALIVE | {mode}

Up:{uptime}
Run:{run_id}

Cycle:{cycles}
Open:{open}
Closed:{closed}

Decisions:{decisions}
Trades:{trades}

TopBlocker:{top_blocker}

Mode:{risk_mode}

Health:{health}/100
```
This template preserves compatibility with existing parsing code by using the same line headers where appropriate.
