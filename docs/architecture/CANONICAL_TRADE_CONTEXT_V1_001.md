# Canonical Trade Context v1 Specification

> **TASK_CLASS: 2 — DESIGN / ARCHITECTURE**
> **PRIMARY: 02_CODE_ARCHITECT_AGENT | SUPPORTING: 08_RESEARCH_QUANT_AGENT, 25_DATA_STEWARD_AGENT**
> **Date: 2026-06-28 | Evidence Grade: B (source-code verified) + D (docs aligned)**

---

## 1. Objective and Scope

The **Canonical Trade Context v1** defines the unified, single source of truth for a trade transaction within the Polymarket adaptive quant runtime. 

Currently, evaluating strategy performance, calibrating sizing metrics, or running backtests requires joining several high-frequency JSONL log streams (`trade_journal`, `decision_log`, `execution_log`, `risk_log`, `path_truth`). These joins are complex, fragile, and contain coverage gaps (such as legacy events missing the `paper_trade_replay_key` join field).

Establishing a canonical trade context schema is a prerequisite to implementing **Bankroll Rank** and **Size Sharp** sizing engines. Sizing calculations must base their risk adjustments on exact historical win rates, volatility, and drawdowns within specific bankroll tiers. Without a standardized trade schema, the telemetry remains too fragmented to safely calibrate live risk bounds.

---

## 2. Current Data Reality

### 2.1 Available Telemetry Sources
- **`trade_journal/trade_open`**: Captures trade start, basic sizing (`size`, `notional_size`), entry price, signal name, and `entry_model_truth_envelope_v1` (containing probability, fair value, and EV if calculated).
- **`trade_journal/trade_close`**: Captures exit pricing, realized PnL, holding time, exit reason, and `trade_result`. However, it lacks entry-time context (EV, probability, bankroll tier, risk mode).
- **`decision_log/decision`**: Logged every cycle. Contains market orderbook state, signals, volatility/trend regimes, and `risk_plan_zero_diagnostics` (which holds bankroll tier and mode details).
- **`execution_log/execution`**: Records order intents, exchange response, submissions, and execution-level errors.
- **`path_truth/trade_path_checkpoint`**: Records mark-to-market valuations and max adverse/favorable excursions (MAE/MFE) intra-trade.
- **`risk_log/risk_event`**: Records transitions in risk mode (e.g., normal to lockdown).

### 2.2 Join Keys
- **Primary Join Key**: `(run_id, paper_trade_replay_key)` where `paper_trade_replay_key` is constructed as:
  `condition_id | epoch_start_ts | ticker | outcome | token_id`
- **Fallback Join Key**: `(run_id, position_id)` or `(run_id, candidate_id)`.

### 2.3 Fragility & Gaps
1. **Missing Fields at Exit**: `trade_close` events are emitted without carrying forward the entry-time bankroll tier, EV, probability, or lifecycle phase.
2. **Missing Realized/Unrealized PnL Curves**: No single log tracks cumulative drawdown or rolling realized/unrealized equity curves.
3. **Legacy Gaps**: Pre-May 2026 logs contain empty or incomplete `paper_trade_replay_key` fields, returning `entry_attribution_status = "missing_legacy"`.

---

## 3. Canonical Trade Context Schema

The Canonical Trade Context is represented as a single flat dictionary structure. 

### A. Identity
- **`trade_id`** (str): Canonical unique identifier of the joined trade, derived from `sha1(run_id | paper_trade_replay_key)`.
- **`position_id`** (str): Local position identifier generated at order intent.
- **`market_id`** (str): CLOB market identifier (e.g., `pm-5m-btc`).
- **`asset_id`** (str): Asset category (e.g., `BTC`, `ETH`).
- **`ticker`** (str): Human-readable asset name.
- **`market_slug`** (str): Polymarket URL slug.
- **`outcome`** (str): Selected outcome side (`YES` or `NO`).
- **`side`** (str): Order action (`BUY` or `SELL`).
- **`source_event_ids`** (dict): Map of source events (`decision_id`, `execution_id`, `open_log_id`, `close_log_id`).
- **`replay_key`** (str): Factual `paper_trade_replay_key` used for cross-stream joining.

### B. Entry Decision Context
- **`signal_name`** (str): Target signal strategy name (e.g., `PROBABILITY_EV_EDGE`).
- **`probability`** (float): Implied probability from the model at decision time.
- **`fair_value`** (float): Estimated fair value of the contract ($0.00–$1.00).
- **`ev`** (float): Expected value calculated at decision time.
- **`ev_after_spread`** (float): Expected value adjusted for bid-ask spread.
- **`decision_score`** (float): Composite strategy signal score.
- **`reason_codes`** (list[str]): List of signal/strategy trigger reason strings.
- **`blockers`** (list[str]): Active execution or safety blockers resolved during the cycle.
- **`market_state`** (str): State label from the Market State Classifier (e.g., `TREND_CONTINUATION`).
- **`lifecycle_phase`** (str): Loop runtime phase at entry (e.g., `OPENING_SCAN`).
- **`seconds_remaining`** (int): Time remaining in the 5-minute epoch.
- **`quote_age_ms`** (int): Age of orderbook data in milliseconds at decision.

### C. Execution Context
- **`intended_price`** (float): Limit price chosen by the pricing engine.
- **`intended_size`** (float): Shares requested.
- **`intended_notional`** (float): USDC cost requested (`size * price`).
- **`order_type`** (str): Order type (`GTC`, `IOC`, `FOK`).
- **`order_id`** (str): Exchange order ID returned on submission.
- **`submitted_at`** (str): Timestamp of submission to CLOB.
- **`fill_status`** (str): Status of order fill (`filled`, `partial`, `timeout_cancelled`).
- **`filled_size`** (float): Actual filled shares.
- **`fill_price`** (float): Weighted average fill price per share.
- **`slippage`** (float): Difference between fill price and intended price.
- **`timeout_status`** (bool): True if order timed out and was cancelled.

### D. Capital / Risk Context
- **`bankroll`** (float): Total cash balance of the wallet at entry.
- **`equity`** (float): Cash balance plus open position value.
- **`realized_pnl_before`** (float): Cumulative realized PnL prior to this trade.
- **`unrealized_pnl_before`** (float): Portfolio unrealized PnL at entry time.
- **`bankroll_tier_id`** (str): Tier designation (e.g., `T0_MICRO_SEED`).
- **`bankroll_rank`** (float): Computed bankroll health score (0–100).
- **`risk_mode`** (str): Operating risk level (`NORMAL`, `MICRO_RECOVERY`, `LOCKDOWN`).
- **`risk_budget`** (float): Max dollar allocation allowed for the current cycle.
- **`max_order_usd`** (float): Safety ceiling limit for a single order.
- **`max_daily_loss_usd`** (float): Safety limit for cumulative daily loss.
- **`max_open_exposure_usd`** (float): Safety limit for overall open exposure.
- **`current_exposure`** (float): Open portfolio exposure immediately prior to entry.
- **`target_exposure`** (float): Sizer-recommended exposure for this trade.

### E. Inventory Context
- **`inventory_state`** (str): Inventory designation (`FLAT`, `DIRECTIONAL_YES`, `DIRECTIONAL_NO`).
- **`open_position_count`** (int): Count of active positions before this trade.
- **`market_exposure_before`** (float): Open exposure in this specific market prior to trade.
- **`market_exposure_after`** (float): Open exposure in this specific market after fill.
- **`position_lifecycle_state`** (str): Action status (`STARTER`, `RELOAD`, `UNLOAD`, `FINAL_DERISK`).

### F. Exit / Outcome Context
- **`exit_reason`** (str): Reason for closing the trade (`stop_loss`, `take_profit`, `forced_exit`, etc.).
- **`exit_price`** (float): Fill price obtained at exit.
- **`exit_timestamp`** (str): ISO timestamp of exit fill.
- **`hold_seconds`** (int): Duration of the trade in seconds.
- **`realized_pnl`** (float): Net dollar PnL after transaction fees.
- **`expected_pnl_at_entry`** (float): Forecasted PnL from EV math.
- **`pnl_pct`** (float): Net PnL as a percentage of entry cost.
- **`trade_result`** (str): Trade outcome label (`WIN`, `LOSS`, `TP`, `SL`).
- **`resolved_outcome`** (str): Factual market settlement resolution (`YES` or `NO`).

### G. Replay / Backtest Context
- **`replay_version`** (str): Version of builder mapping utilized.
- **`data_quality_grade`** (str): Data completeness score (`A`, `B`, `C`, `D`, `E`).
- **`missing_fields`** (list[str]): List of fields unable to be resolved.
- **`source_streams`** (list[str]): List of log folders joined to construct this context.
- **`join_confidence`** (str): Quality of join matches (`DIRECT`, `PROXY_ONLY`, `INSUFFICIENT`).
- **`counterfactual_available`** (bool): True if parallel shadow pricing exists for comparison.

---

## 4. Field Source Map

| Field Group | Field Name | Primary Telemetry Source | Computed / Joined | Status Today |
|---|---|---|---|---|
| **Identity** | `trade_id` | N/A | `sha1(run_id \| replay_key)` | Computed |
| | `position_id` | `trade_open`, `trade_close` | Direct | ✅ Present |
| | `market_slug` | `trade_open`, `decision` | Direct / Joined | ✅ Present |
| | `replay_key` | `trade_open`, `trade_close` | Direct | ✅ Present |
| **Entry Decision**| `ev_after_spread` | `trade_open` | Carry-forward at close | ❌ Missing at close |
| | `true_probability` | `trade_open` | Carry-forward at close | ❌ Missing at close |
| | `fair_value` | `trade_open` | Carry-forward at close | ❌ Missing at close |
| | `market_state` | `decision` | Joined | ❌ Missing at close |
| | `lifecycle_phase` | `trade_open` | Carry-forward at close | ❌ Missing at close |
| | `seconds_remaining`| `decision` | Joined | ❌ Missing at close |
| **Execution** | `fill_price` | `trade_open`, `trade_close` | Direct | ✅ Present |
| | `slippage` | `execution` | Joined | ❌ Missing today |
| **Capital/Risk** | `bankroll_tier_id` | `decision` (`risk_plan_zero_diagnostics`) | Joined | ❌ Missing at close |
| | `bankroll_rank` | N/A | Computed (not in logs) | ❌ Missing today |
| | `risk_mode` | `risk_log` | Joined | ❌ Missing at close |
| | `current_exposure` | `trade_open` | Carry-forward at close | ❌ Missing at close |
| **Inventory** | `position_lifecycle_state`| `decision` | Joined | ❌ Missing today |
| **Exit/Outcome** | `exit_reason` | `trade_close` | Direct | ✅ Present |
| | `realized_pnl` | `trade_close` | Direct | ✅ Present |
| | `resolved_outcome` | `trade_close` | Direct | ✅ Present |
| **Replay/Backtest**| `data_quality_grade`| N/A | Computed (offline tool) | ✅ Present |

---

## 5. Required Runtime Backfill

To avoid high-overhead cross-stream joining during live execution and simplify offline metrics tracking, the runtime (`polymarket/trader.py`) must be updated to carry forward entry-time data within the position instance:

1. **Carry-Forward inside Position Metadata**:
   When a position is initialized in `PositionTracker`, the sizer's execution context must be saved into the position's `metadata` dictionary. This includes:
   - `true_probability`, `fair_value`, `ev_after_spread`
   - `bankroll_tier_id`, `bankroll_tier_name`, `bankroll_family`
   - `risk_mode`
   - `lifecycle_phase`
   - `seconds_remaining_at_entry`
   - `notional_size`

2. **Log Emission on Close**:
   `_emit_trade_closed_event()` must unpack these metadata fields and serialize them directly into the `trade_close` payload. This guarantees that `trade_close` contains all data necessary to compute expectancy, win rate by tier, and EV decay without joining.

3. **Where to build the context**:
   - **Offline-built first**: An offline builder tool (`tools/canonical_trade_builder.py`) should be created to process existing history and construct Canonical Trade Contexts from the 28.6 GB historical log repository.
   - **Runtime-built second**: Once verified offline, the `trader.py` event logger should emit the canonical flat dictionary block directly when generating `trade_close` events.

---

## 6. Replay / Backtest Integration

- **`replay_analyzer.py`**:
  Instead of parsing separate streams and estimating proxy coverage, the analyzer will ingest a single CSV/JSON database of Canonical Trade Contexts. This enables one-line grouping of win rates, profit factors, and holding times by market regime, sizer tier, and signal type.
- **`canonical_trade_table_v1.py`**:
  This tool will serve as the core compiler, compiling historical JSONL logs into a clean, queryable tabular database of Canonical Trade Contexts for researchers.

---

## 7. Bankroll Rank Support

Bankroll Rank measures wallet health to scale sizer risk dynamically. The Canonical Trade Context supports this by tracking:
- **Drawdown History**: Sequential PnL allows computing drawdown curves.
- **Streak Volatility**: Tracking wins/losses sequentially supports sizing adjustments for cluster losses.
- **Survivability Bounds**: Correlating `bankroll_tier_id` with PnL stability verifies if a tier is under-funded.

---

## 8. Size Sharp Support

Size Sharp determines the optimal execution size based on microstructural constraints:
- **Spread & Liquidity**: Correlating `ev_after_spread` with `slippage` reveals the optimal depth absorption.
- **Time Expiry Decay**: Correlating `seconds_remaining` with win rates validates if late entries suffer adverse selection.
- **Probability Calibration**: Comparing `true_probability` with `resolved_outcome` builds the calibration curve for Kelly inputs.

---

## 9. Dashboard / Telegram Support

 Surfacing these metrics provides the operator with clean visibility:
- **Telegram Entry Alert**: Surfacing `market_state` (e.g. `MEAN_REVERSION`), `true_probability`, and `bankroll_tier_id` explains sizer decisions instantly.
- **Dashboard UI**: Displays current open exposure relative to `max_open_exposure_usd` and real-time sizer scaling multipliers.

---

## 10. Migration Strategy

1. **v1 offline builder from existing JSONL**: Build `tools/canonical_trade_builder.py` to aggregate existing decision and journal logs into `completed_trades_v1.csv` / `completed_trades_v1.json`.
2. **v2 runtime emit canonical context**: Update `trader.py` and `position_tracker.py` to cache sizer state and carry-forward the `entry_model_truth_envelope_v1` inside metadata, producing self-contained close events.
3. **v3 dashboard uses canonical context**: Re-route dashboard state aggregator to read completed trades directly from self-contained closes.
4. **v4 Bankroll Rank + Size Sharp consume canonical context**: Implement adaptive sizers powered by the self-contained database.

---

## 11. Risks and Failure Modes

- **Stale Copied Context**: If a position remains open across cycles, its entry-time metadata must remain immutable. Re-evaluation at mid-points (e.g., reloads) must create linked sub-contexts.
- **Incorrect Join Keys**: Legacy data lacks `paper_trade_replay_key`. The builder must implement fallback joining using `condition_id` + `timestamp` window matching.
- **Partial Fills**: If a trade is partially filled, `notional_size` must reflect actual filled value, not intended size.
- **Execution Event without Position Event**: Order submissions that fail to execute must be logged as counterfactual skips to prevent trade PnL distortion.
- **Live/Paper Schema Drift**: Schema structure changes must increment `schema_version`.

---

## 12. Verification Plan

### 12.1 Schema Validation
A JSON Schema validation script (`tests/test_canonical_schema.py`) will run against compiled canonical contexts to ensure no required fields (such as `trade_id`, `pnl`, or `bankroll_tier_id`) are null.

### 12.2 Open-Close Join Verification
A verification test will confirm that `win_rate * n_trades` exactly matches the total number of wins in the raw log, ensuring no trades are duplicated or omitted during compilation.

---

## 13. Recommended Next Task

### Chosen Path: CANONICAL_TRADE_CONTEXT_OFFLINE_BUILDER_001

Building the offline compiler first allows us to test the schema definition against 51 days of historical data, resolve join gaps, and confirm metrics generation *before* making any changes to runtime code.
