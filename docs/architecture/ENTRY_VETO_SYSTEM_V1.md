# ENTRY_VETO_SYSTEM_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document defines the formal Veto and Penalty taxonomy for the Polymarket Crypto 5M Quant Engine. The veto system separates non-negotiable safety blockers (**Hard Vetoes**) from execution and pricing adjustments (**Soft Penalties**).

---

## 1. Hard Vetoes (System Safety Blocks)

Hard Vetoes represent absolute boundaries. If any Hard Veto is triggered, the engine blocks the order intent (`ORDER_INTENT_BLOCKED`) and, where applicable, halts the cycle loop.

```
                  ┌─────────────────────────────────────┐
                  │            HARD VETOES              │
                  ├───────────────────┬─────────────────┤
                  │  CRITICAL HALTS   │ SESSION BLOCKS  │
                  ├───────────────────┼─────────────────┤
                  │ - LOCKDOWN        │ - DAILY LOSS    │
                  │ - RECONCILIATION  │ - PORTFOLIO FULL│
                  │ - HEARTBEAT FAIL  │                 │
                  └───────────────────┴─────────────────┘
```

### A. Critical Halts (Loop Suspended, Requires Operator Intervention)
1. **`VETO_LOCKDOWN`**:
   - *Trigger*: Cumulative daily drawdown exceeds 10%, bankroll balance falls below the **$5.00** floor, or an unhandled critical exception escapes the main loop.
   - *Action*: Instantly kills WebSocket price feeds, cancels all open orders, locks the sizer, and issues a critical alert.
   - *Reset Mechanism*: Requires manual operator intervention via an explicit restart and validation command.
2. **`VETO_RECONCILIATION_GAP`**:
   - *Trigger*: A mismatch is detected between tracked in-memory position inventory and real-time CLOB token balances (e.g. holding YES tokens but having zero tracked positions in the local database).
   - *Action*: Prevents any new entry buys. Exits are allowed only under manual routing.
   - *Reset Mechanism*: Automatically resolves if a subsequent reconciliation sweep confirms balance alignment, or requires manual reconciliation via script.
3. **`VETO_HEARTBEAT_FAILURE`**:
   - *Trigger*: Multi-instance detection where another PID writes to the owner file, or when the database lock fails.
   - *Action*: Engine immediately terminates with return code `0` to prevent duplicate trading.

### B. Session Blocks (Resets Automatically on Time or State)
1. **`VETO_DAILY_DRAWDOWN`**:
   - *Trigger*: Current session losses exceed the configured daily limit (e.g. 5% in Defensive, 10% in Normal).
   - *Action*: Blocks all new entries. Exits and profit management cycles continue.
   - *Reset Mechanism*: Automatically resets at **00:00 UTC**.
2. **`VETO_PORTFOLIO_FULL`**:
   - *Trigger*: All available concurrent slot count allocations are filled (e.g. 1 slot in Survival, 3 slots in T3).
   - *Action*: Rejects new entry signals.
   - *Reset Mechanism*: Automatically clears when an active position is resolved or exited.

---

## 2. Soft Penalties (Execution & Pricing Adjustments)

Soft Penalties do not halt the system. Instead, they dynamically scale down sizer weights or adjust probability thresholds to reflect imperfect market conditions.

### A. Sizer Multipliers (Capital Adjustments)
1. **Spread Penalty Multiplier ($M_{\text{spread}}$)**:
   Designed to scale down position size as the bid-ask spread widens towards the maximum limit:
   $$M_{\text{spread}} = \max\left(0, 1 - \frac{\text{Spread}}{\text{Max Allowed Spread}}\right)$$
   - *Example*: If max allowed spread is $0.05, a spread of $0.02 yields $M_{\text{spread}} = 0.60$ (reducing size by 40%).
2. **Liquidity Depth Multiplier ($M_{\text{depth}}$)**:
   Reduces execution size if immediate L1 book volume is insufficient to absorb the order without price degradation:
   $$M_{\text{depth}} = \min\left(1.0, \frac{\text{L1 Book Depth}}{\text{Target Size} \times 15}\right)$$

### B. Adaptive Sizer Threshold Adjustments
1. **Confidence Penalty ($M_{\text{confidence}}$)**:
   If model directional confidence approaches the configured floor (e.g. 0.54 in Normal), the position size is penalized:
   $$M_{\text{confidence}} = \max\left(0.1, \frac{\text{Confidence} - \text{Floor}}{1.0 - \text{Floor}}\right)$$
2. **Correlation Cointegration Scaler ($M_{\text{correlation}}$)**:
   If the engine detects that the candidate is highly correlated with an active position (e.g., entering ETH when a BTC trade is open), it applies a correlation scale:
   $$M_{\text{correlation}} = 1.0 - \rho^2$$
   where $\rho$ is the historical rolling 30-minute correlation coefficient between BTC and ETH. If $\rho = 0.70$, the position size of the second asset is cut by **49%** ($1 - 0.49 = 0.51$).

---

## 3. Threshold Calibration Matrix

The table below defines the veto and penalty thresholds across the different risk states:

| Risk State | Max Spread | Max Quote Age | Min L1 Depth | Cointegration Correlation Cap ($\rho$) | Max Slots | Sizer Multiplier Cap |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`NORMAL`** | $0.05 | 5.0 seconds | 10x order size | No cap (standard Kelly) | Tier Limit | 1.00 (No penalty) |
| **`DEFENSIVE`** | $0.03 | 3.0 seconds | 25x order size | $\rho \le 0.75$ | Tier Limit - 1 | 0.50 max cap |
| **`SURVIVAL`** | **$0.015** | **1.5 seconds** | **100x order size** | **$\rho \le 0.50$ (Hard Veto)** | **1 slot** | **Min notional floor** |
