# OPTION_D_SHADOW_IMPLEMENTATION_SPEC_001: Shadow Telemetry & Observability Specification

**Task:** OPTION_D_SHADOW_IMPLEMENTATION_SPEC_001  
**Primary Role:** 02_CODE_ARCHITECT_AGENT  
**Supporting Roles:** 08_RESEARCH_QUANT_AGENT, 11_OBSERVABILITY_INCIDENT_AGENT  
**Mode:** DESIGN ONLY (No implementation, no code modifications, no strategy changes)  
**Date:** 2026-06-19  
**Status:** COMPLETE  

---

## 1. Telemetry Schema

To validate Option D prospectively without execution risk, the runtime engine must log a dedicated shadow schema for every active position. This schema will be written to `runtime/quant_data/stop_loss_shadow/*.jsonl` on every second scan.

### Field Definitions

| Field Name | Type | Source | Purpose |
|---|---|---|---|
| `position_id` | `string` | `Position.position_id` | Unique identifier for position tracking across logs. |
| `symbol` | `string` | `Position.symbol` | Asset ticker (e.g., "BTC", "ETH"). |
| `side` | `string` | `Position.side` | "YES" or "NO" prediction token. |
| `entry_ts` | `string` | `Position.entry_time` | ISO UTC timestamp of position open. |
| `hold_seconds` | `float` | `datetime.now() - entry_ts` | Current elapsed duration of the position in seconds. |
| `entry_price` | `float` | `Position.entry_price` | Purchase price (YES/NO ask at entry). |
| `entry_bid` | `float` | `ob.best_bid` at entry | YES bid at purchase time (captures entry spread). |
| `entry_mid` | `float` | `(entry_price + entry_bid)/2` | Mid-price baseline captured at entry. |
| `raw_bid` | `float` | `ob.best_bid` (current) | Current best bid price on orderbook. |
| `raw_ask` | `float` | `ob.best_ask` (current) | Current best ask price on orderbook. |
| `mid_price` | `float` | `(raw_bid + raw_ask)/2` | Current mid-price (returns bid if ask is 0). |
| `spread` | `float` | `raw_ask - raw_bid` | Current bid-ask spread width. |
| `bid_size` | `float` | `ob.bid_size` (current) | Available contract liquidity at current best bid. |
| `ask_size` | `float` | `ob.ask_size` (current) | Available contract liquidity at current best ask. |
| `delay_active` | `boolean` | `hold_seconds < 30.0` | Time suppression window state flag. |
| `delay_remaining`| `float` | `max(0.0, 30.0 - hold_seconds)`| Remaining seconds of time suppression. |
| `depth_gate_pass` | `boolean` | `bid_size >= 10.0 and ask_size >= 10.0`| True if orderbook depth is sufficient. |
| `three_sample_pass`| `boolean` | `consecutive_mid_breaches >= 3`| True if mid-price breach confirmed for 3 consecutive seconds. |
| `emergency_stop_trigger`| `boolean` | `unrealized_mid_pct <= -0.30` | True if mid-price loss exceeds 30% (bypasses delay). |
| `option_d_would_stop`| `boolean` | `three_sample_pass or emergency_stop_trigger` | True if Option D logic dictates exit. |
| `option_d_would_hold`| `boolean` | `not option_d_would_stop` | True if Option D logic dictates holding. |
| `actual_stop_triggered`| `boolean` | `trader.py` exit loop status | True if default stop-loss policy triggered exit. |
| `actual_exit_reason`| `string` | `trade_journal.exit_reason` | Actual exit event recorded (e.g., `stop_loss`, `expiry`). |
| `counterfactual_exit_reason`| `string` | Option D simulation logic | Would-be exit reason under Option D. |
| `unrealized_raw_bid_pct`| `float` | `(raw_bid - entry_price)/entry_price` | Unrealized PnL using raw bid price (default). |
| `unrealized_mid_pct`| `float` | `(mid_price - entry_mid)/entry_mid` | Unrealized PnL using mid-price. |

---

## 2. Event Lifecycle

The lifecycle trace tracks the states and transitions of Option D's evaluation loop:

```
[Position Open]
       ↓ (1) Log OPTION_D_SHADOW_OPEN
[Delay Window (0-30s)]
       ↓ (2) Log OPTION_D_SHADOW_SCAN (delay_active=True, would_stop=False)
       ↓ (3) If loss <= -30% → Bypasses to OPTION_D_SHADOW_TRIGGER (Emergency)
[Monitoring Window (>30s)]
       ↓ (4) Log OPTION_D_SHADOW_SCAN (delay_active=False)
       ↓ (5) If mid-price breach AND depth_gate_pass=True → Increment Counter
       ↓ (6) If Counter >= 3 → Transition to OPTION_D_SHADOW_TRIGGER (Normal)
[Position Close / Expiry]
       ↓ (7) Log OPTION_D_SHADOW_CLOSE (Reconcile actual vs. counterfactual)
```

### Telemetry Events

#### 1. `OPTION_D_SHADOW_OPEN`
* **Trigger:** Position successfully written to paper `position_tracker`.
* **Payload:** `position_id`, `symbol`, `side`, `entry_ts`, `entry_price`, `entry_bid`, `entry_mid`.

#### 2. `OPTION_D_SHADOW_SCAN`
* **Trigger:** Every 1-second interval execution scan.
* **Payload:** `position_id`, `hold_seconds`, `raw_bid`, `raw_ask`, `mid_price`, `spread`, `bid_size`, `ask_size`, `delay_active`, `depth_gate_pass`, `three_sample_pass`, `option_d_would_stop`.

#### 3. `OPTION_D_SHADOW_TRIGGER`
* **Trigger:** The exact second `option_d_would_stop` changes from `False` to `True`.
* **Payload:** `position_id`, `hold_seconds`, `trigger_type` (`NORMAL` vs. `EMERGENCY`), `mid_price`, `unrealized_mid_pct`.

#### 4. `OPTION_D_SHADOW_CLOSE`
* **Trigger:** Position is removed from `position_tracker` (due to actual stop-loss, take-profit, or expiry).
* **Payload:** `position_id`, `actual_exit_reason`, `actual_exit_price`, `actual_pnl`, `counterfactual_exit_reason`, `counterfactual_exit_price`, `counterfactual_pnl`, `saved_by_option_d` (`boolean`).

---

## 3. Metrics Layer

The metrics layer compiles the JSONL event streams to generate prospective performance indicators:

1. **False Stop Rate (FSR):**
   $$\text{FSR} = \frac{\text{Actual Stop-outs Saved by Option D that expired as Wins}}{\text{Total Actual Stop-outs Saved by Option D}}$$
   *Purpose:* Meaures the accuracy of Option D in suppressing noise without blocking true exits.

2. **Saved Trade Rate (STR):**
   $$\text{STR} = \frac{\text{Actual Stop-outs Saved by Option D}}{\text{Total Actual Stop-outs}}$$
   *Purpose:* Measures the percentage of premature liquidations prevented.

3. **Option D Trigger Rate (ODTR):**
   $$\text{ODTR} = \frac{\text{Option D Would-Stops}}{\text{Total Positions}}$$
   *Purpose:* Monitors stop frequency under the new policy compared to default.

4. **Counterfactual Profit Factor (CF_PF):**
   $$\text{CF\_PF} = \frac{\text{Gross Wins under Option D exits}}{\text{Gross Losses under Option D exits}}$$
   *Purpose:* The critical mathematical check for portfolio edge expansion.

5. **Counterfactual Expectancy (CF_Exp):**
   $$\text{CF\_Exp} = \frac{\text{Net PnL under Option D exits}}{\text{Total Trades}}$$
   *Purpose:* Quantifies expected USDC gain per unit trade.

6. **Drawdown Estimate Variance (DEV):**
   $$\text{DEV} = \text{Max Peak-to-Trough Drawdown (Option D)} - \text{Max Peak-to-Trough Drawdown (Default)}$$
   *Purpose:* Measures the capital volatility penalty of holding through intra-epoch swings.

---

## 4. Dashboard Layer

A dedicated terminal monitoring panel will extend the existing `utils/display.py` terminal interface to display active shadow metrics.

### Operator Dashboard Layout

```
================================================================================
                    POLYTRADE BOT - OPTION D SHADOW COCKPIT
================================================================================
[ACTIVE NO POSITIONS]
ID       Asset  Age(s) Entry_Mid  Curr_Mid  PnL(Mid)  Delay(s)  Depth   D_Action
--------------------------------------------------------------------------------
5c85c8f3 BTC    14s    0.4550     0.4600    +1.10%    Active-16  PASS   HOLD
d14d98bf ETH    45s    0.5050     0.4500    -10.89%   Expired    FAIL   HOLD (Gated)
3e1a7cac BTC    120s   0.3700     0.3200    -13.51%   Expired    PASS   STOP-Normal

[SHADOW METRICS LAYER]
Metric                       Default       Option D (Shadow)   Delta
--------------------------------------------------------------------------------
Trades Monitored             46            46                  0
Stop-loss Exits              32            12                  -20
Win Rate                     30.43%        68.42%              +37.99pp
Profit Factor                0.585         1.921               +1.336
Expectancy (per trade)       -0.0026 USDC  +0.0210 USDC        +0.0236 USDC
Max Consecutive Losses       6             3                   -3
Max Simulated Drawdown       -0.28 USDC    -0.12 USDC          +0.16 USDC

[OPTION D DIAGNOSTICS]
Saved Trade Count:    20 / 32 (62.5%)
False Stop Rate:      16 / 20 (80.0%)
Emergency Triggers:   0
Depth-Gated Samples:  42
================================================================================
```

---

## 5. Telegram Layer

Dedicated alert channels will format shadow data for mobile operations.

### OPTION_D_DAILY_SUMMARY

```
📊 POLYTRADE: OPTION D SHADOW DAILY REPORT
Date: 2026-06-19
----------------------------------
Positions Monitored:  8
Actual Stops Fired:   6
Option D Would-Stops: 2
Saved Trades:         4 (66.7% saved)

Performance Compare:
- Actual PnL:  -0.024 USDC (WR: 25.0%)
- Shadow PnL:  +0.068 USDC (WR: 75.0%)
- Expectancy:  +0.0085 USDC (Shadow) vs. -0.0030 USDC (Actual)

Diagnostic Flags:
- False Stops Saved:  3 (resolved WIN)
- Stalled Expiry Wins: 1 (resolved LOSS)
- Emergency Stops:    0
- Avg Hold Time:      240s (Shadow) vs. 15s (Actual)
```

### OPTION_D_ALERT

```
⚠️ POLYTRADE: OPTION D SHADOW SHIELD ALERT
Position: #3e1a7cac (ETH-NO)
----------------------------------
[STATUS]
Default Stop-Loss:  🚨 FIRED (raw_bid unrealized = -8.5%)
Option D Policy:     🛡️ SUPPRESSED (Mid-PnL = -5.1%, Depth = FAIL)

[METRICS]
Entry Price:        0.5200 (YES Ask)
Current Raw Bid:    0.4750 (YES Bid)
Current Mid-Price:  0.4935 (YES Mid)
Bid Size:           4.0 (Gating Active)

Action: Suppressing liquidation. Position maintained in shadow mode.
```

---

## 6. Validation Requirements

Before Option D can be promoted from `SHADOW_ONLY` to `PAPER_READY` (active execution), the collected shadow data must meet these thresholds:

1. **Sample Size Gate:**
   - Minimum of **150 unique trades** logged under the shadow schema.
   - At least **50 positions** must have triggered the default stop-loss policy (providing a comparative control group).

2. **Edge Improvement Gates:**
   - **Counterfactual Profit Factor (CF_PF):** $\ge 1.50$.
   - **Counterfactual Expectancy (CF_Exp):** $\ge +\$0.01\text{ USDC}$ per unit trade.
   - **Win Rate Calibration:** Shadow win rate on stopped-but-saved trades must be $\ge 50\%$.

3. **Risk Profile Gates:**
   - **Max Drawdown Deviation:** Drawdown under Option D exits must not exceed default drawdown by more than **$5.00$ USDC** (absolute portfolio value).
   - **Consecutive Loss Cap:** Maximum consecutive counterfactual losses $\le 5$.
   - **Emergency Stop Safety:** Emergency triggers must represent $\le 5\%$ of total positions (to ensure the -30% threshold does not cause panic liquidations on normal spread spikes).

---

## 7. Implementation Readiness

### Final Verdict: `READY_FOR_IMPLEMENTATION`

### Rationale
* The design contains a complete telemetry specification (Part 1), lifecycle trace logic (Part 2), analytics layer (Part 3), terminal display mockup (Part 4), and alert interfaces (Part 5).
* Retroactive logs confirm that all inputs (mid-prices, entry bid/ask orderbooks, and timestamps) are available within the active execution loops.
* Transitioning to implementation of the **shadow logger only** carries zero strategy risk and provides the required prospective telemetry to close out the remaining unknowns.
