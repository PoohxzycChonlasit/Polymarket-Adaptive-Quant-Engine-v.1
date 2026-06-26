# RUNTIME_STATE_MACHINE_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document formalizes the State Transition Matrix and Loop Halt logic for the master runtime state machine of the Polymarket Crypto 5M Quant Engine.

---

## 1. State Transition Matrix

The table below defines the transition rules between the five runtime states:

| Current State | Next State | Trigger Condition | Real-Time Actions & Parameter Adjustments |
| :--- | :--- | :--- | :--- |
| **`AGGRESSIVE`** | `NORMAL` | Daily Drawdown $> 2.0\%$ | Restores standard slots (3–4) and Kelly sizing. |
| **`NORMAL`** | `AGGRESSIVE` | Session Win Rate $> 60\%$ (20 trades) AND Drawdown $= 0.0\%$ | Expands slots to 5; sets EV floor to $0.015. |
| **`NORMAL`** | `DEFENSIVE` | Daily Drawdown $\ge 5.0\%$ OR Consecutive Losses $\ge 3$ | Cuts sizer size by 50%, caps slots to 2, raises EV floor to $0.04. |
| **`DEFENSIVE`**| `SURVIVAL` | Daily Drawdown $\ge 8.0\%$ OR Account Balance $\le \$6.00$ | Restricts sizing to MEF, limits slots to 1, raises EV floor to $0.05. |
| **`DEFENSIVE`**| `RECOVERY` | Session Drawdown stabilizing (no losses in 10 cycles) | Enters Recovery. Restores slots to 2; keeps sizer capped. |
| **`SURVIVAL`** | `RECOVERY` | Account Balance $> \$6.00$ AND 20-trade Win Rate $\ge$ Breakeven | Enters Recovery. Restores slots to 2; keeps sizing capped. |
| **`RECOVERY`** | `NORMAL` | Rolling 50-trade Win Rate $\ge$ Breakeven AND Drawdown $= 0.0\%$ | Promotes to Normal. Restores standard base risk fractions. |
| **`RECOVERY`** | `SURVIVAL` | Any realized loss in Recovery mode | Re-demotes immediately to Survival state. |

---

## 2. Hard Stop Constraints (Permitted Loop Halts)

To maintain continuous 24/7 VPS execution, ordinary trading losses or drawdowns must **never** halt the loop. A loop halt (Hard Stop) is strictly limited to the following six operational safety triggers:

1. **Runtime Ownership Conflict**:
   - *Trigger*: Multi-instance detection where a separate PID writes to the active owner file, indicating a duplicate process run.
2. **Corrupted Data**:
   - *Trigger*: Structural database corruption or unreadable JSONL/CSV configuration logs that prevent state reconstruction.
3. **Stale / Broken Market Data**:
   - *Trigger*: Persistent WebSocket or REST API failures from Binance or Polymarket price feeds exceeding 10 consecutive connection attempts.
4. **Wallet / Allowance / Reconciliation Issue**:
   - *Trigger*: Wallet balance fetch failure, smart contract allowance missing/revoked, or a position reconciliation mismatch (e.g. unhedged token imbalance).
5. **Execution Safety Failure**:
   - *Trigger*: Multiple consecutive transaction signature rejections or CLOB order submission errors (suggesting API key compromise or network censorship).
   - *Action*: Loops are blocked to prevent transaction spam or key leakage.
6. **VPS Disk / Logging / System Failure**:
   - *Trigger*: VPS disk space falls below 100MB or write permission is locked, preventing fail-soft logs or JSONL events from persisting.
