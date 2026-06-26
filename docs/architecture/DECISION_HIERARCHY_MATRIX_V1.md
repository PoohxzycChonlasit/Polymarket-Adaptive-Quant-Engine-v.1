# DECISION_HIERARCHY_MATRIX_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document formalizes the conflict resolution rules and hierarchical execution logic of the Polymarket Crypto 5M Quant Engine. When multiple signals, risk modes, and execution filters fire simultaneously, this matrix determines which factor dominates.

---

## 1. The Priority Levels

The decision framework is structured into a strict four-tier hierarchy:

```
┌────────────────────────────────────────────────────────┐
│ LEVEL 1: SYSTEM INTEGRITY & HARD SAFETY (Vetoes All)  │
├────────────────────────────────────────────────────────┤
│ LEVEL 2: RISK-MODE & DYNAMIC CONTROLS (Overrides Size) │
├────────────────────────────────────────────────────────┤
│ LEVEL 3: MICROSTRUCTURE & EXECUTABLE TRUTH (Skips Cycle)│
├────────────────────────────────────────────────────────┤
│ LEVEL 4: SIGNAL & EXPECTANCY SIZING (Standard Path)    │
└────────────────────────────────────────────────────────┘
```

### Level 1: System Integrity & Hard Safety Gates (Vetoes All)
- **Rules**: Lockdown checks, Daily Drawdown limit, Reconciliation Mismatch, Multi-instance owner heartbeat failure.
- **Behavior**: Evaluated first. If any Level 1 check fails, the engine enters an immediate halt or hard block. No order intent is generated, outstanding orders are canceled, and an operator alert is triggered.

### Level 2: Risk-Mode & Dynamic Controls (Overrides Sizing)
- **Rules**: Active Risk Mode (`DEFENSIVE`, `MICRO_RECOVERY`), Loss Cluster Cooldown, Cointegrated Asset Correlation block.
- **Behavior**: Evaluated second. If a Level 2 condition is active, it overrides Level 4 sizing logic. For example, if a signal suggests a maximum Kelly size, but the system is in `DEFENSIVE` mode, the size is scaled down by 50% or capped to the Survival floor.

### Level 3: Microstructure & Executable Feasibility Gates (Skips Cycle)
- **Rules**: Bid-ask spread cap, L1 volume depth floor, Quote latency, time remaining cutoff.
- **Behavior**: Evaluated third. If a Level 3 check fails, the candidate is discarded for the current cycle (`skip_cycle`). This is a soft block that does not halt the engine but prevents trading into bad execution windows.

### Level 4: Signal, Expectancy, & Sizing Calculations (Standard Path)
- **Rules**: Model Probability, Fair Value, Expected Value (EV), Base Sizer.
- **Behavior**: Evaluated last. If all upper levels pass, the engine uses signal and Kelly/flat sizing parameters to compute the final order size.

---

## 2. Decision Hierarchy Matrix

| Priority | Decision Input / Factor | Evaluation Order | Override Behavior | Impact on Order Intent |
| :---: | :--- | :---: | :--- | :--- |
| **Level 1** | `SYSTEM_LOCKDOWN` | First | Overrides all layers. Immediate loop halt. | `ORDER_INTENT_BLOCKED` (Hard Block) |
| **Level 1** | `RECONCILIATION_GAP` | First | Overrides all layers. Immediate halt. | `ORDER_INTENT_BLOCKED` (Hard Block) |
| **Level 1** | `DAILY_DRAWDOWN_LIMIT` | First | Overrides all layers. Halts entries until reset. | `ORDER_INTENT_BLOCKED` (Hard Block) |
| **Level 2** | `LOSS_CLUSTER_PAUSE` | Second | Overrides Signal and Execution layers. | Skip Entry (30-min Cooldown) |
| **Level 2** | `COINTEGRATED_CORRELATION`| Second | Blocks BTC if ETH is active, or vice-versa. | Skip Entry (Avoid joint risk) |
| **Level 2** | `DEFENSIVE_MODE` | Second | Cuts Level 4 calculated size by 50%. | Approved at reduced size |
| **Level 2** | `SURVIVAL_MODE` | Second | Suspends Kelly; forces flat min notional. | Approved at min size |
| **Level 3** | `QUOTE_LATENCY_EXCEEDED`| Third | Overrides Signal Layer. | Skip Entry (Stale data check) |
| **Level 3** | `SPREAD_LIMIT_EXCEEDED` | Third | Overrides Signal Layer. | Skip Entry (Edge destruction) |
| **Level 3** | `LIQUIDITY_DEPTH_GAP` | Third | Overrides Sizing. | Skip Entry (Slippage check) |
| **Level 3** | `CYCLE_TIME_CUTOFF` | Third | Overrides Sizing. Blocks entry after 240s. | Skip Entry (Time decay gate) |
| **Level 4** | `EXPECTED_VALUE_FLOOR` | Fourth | Standard strategy trigger. | Base sizing calculation |

---

## 3. Override Case Studies

### Case Study A: High-Conviction Signal in Defensive Mode
- **Signal Input**: Model Probability = 0.68 for YES on BTC. Kelly Sizer suggests a $12.50 position.
- **Conflict**: The system is currently in `DEFENSIVE` mode due to a recent drawdown breach.
- **Resolution**: Level 2 overrides Level 4. The `DEFENSIVE_MODE` rule intercepts the sizer and cuts the position size by 50%, resulting in a final approved order intent of **$6.25**. The high directional confidence is overridden to protect capital.

### Case Study B: High EV Signal Near Cutoff
- **Signal Input**: Model Probability = 0.58, YES price is $0.50 (Theoretical EV = +0.08).
- **Conflict**: The cycle clock is at **242 seconds** elapsed (cutoff is 240s).
- **Resolution**: Level 3 overrides Level 4. The `CYCLE_TIME_CUTOFF` rule triggers a soft veto, discarding the trade. Although the theoretical EV is high, the time decay risk and lack of time to manage the position override the signal.

### Case Study C: Cointegrated Opportunities in Survival Mode
- **Signal Input**: Buy signals fire on both BTC YES and ETH YES.
- **Conflict**: The system is in `SURVIVAL_MODE`.
- **Resolution**: Level 2 overrides Level 4. The `COINTEGRATED_CORRELATION` rule permits filling only **1 slot** and blocks the second trade to avoid double exposure to cointegrated risk. The BTC trade is entered, and the ETH trade is instantly vetoed.
