# CAPACITY_THROTTLE_ENGINE_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document formalizes the capacity throttling logic, trade frequency windows, and micro-pause constraints for the Polymarket Crypto 5M Quant Engine.

---

## 1. Capacity Throttling and Share Limits

To prevent capital erosion, the engine implements dynamic capacity throttles across active slots and share counts.

### A. Throttle Parameters by Runtime State

| State | Max Slots | Sizing Cap per Order | Trade Frequency Cap | Micro-Pause Duration | Cointegration Cap |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`AGGRESSIVE`** | 5 | 3.0% notional | 10 trades / hour | 5 seconds | No cap |
| **`NORMAL`** | 3–4 | 2.66% notional | 6 trades / hour | 10 seconds | $\rho \le 0.85$ (Scale size) |
| **`DEFENSIVE`** | 2 | 1.50% notional | 3 trades / hour | 30 seconds | $\rho \le 0.75$ (Scale size) |
| **`SURVIVAL`** | 1* | MEF notional | 1 trade / hour | 60 seconds | $\rho \le 0.50$ (Hard Veto) |
| **`RECOVERY`** | 2 | 1.00% notional | 3 trades / hour | 30 seconds | $\rho \le 0.75$ (Scale size) |

$$\text{*Note: } \text{Survival allows an optional 2nd slot exception under excellent microstructure conditions.}$$

---

## 2. Micro-Pauses and Throttle Windows

To stabilize execution and avoid adverse selection, the engine enforces micro-pauses and frequency limits:

### A. The Micro-Pause
- **Behavior**: Instantly after an order fill (entry or exit), the engine executes a **Micro-Pause** (e.g. 30 seconds in Defensive, 60 seconds in Survival).
- **Rule**: During the micro-pause, the loop **continues scanning, tracking, and ranking candidates** but blocks new order submissions. This allows local orderbook queues to clear, L1 liquidity to replenish, and spread volatility to normalize.

### B. The Throttle Window
- **Behavior**: Tracks trades executed within a rolling 60-minute window.
- **Rule**: If trades executed exceed the Trade Frequency Cap (e.g. 3 trades/hour in Defensive), the engine throttles entries. No new positions are opened until older trades roll off the window, ensuring capital is not over-allocated during high-volatility regimes.

---

## 3. Survival Mode 2nd Slot Exception

By default, Survival Mode restricts capacity to **1 active slot** to lock down correlation risk. However, the capacity throttle engine permits an optional **2nd active slot** strictly if the following six conditions are met:

1. **Composite ETS $\ge 0.90$** (optimal execution environment).
2. **L1 Touch Depth $> 200\text{x}$** target order size (guaranteeing zero slippage).
3. **Spread $\le 1.0\%$** of contract mid-price.
4. **Quote Age $\Delta t < 1.0\text{ second}$** (preventing stale quote risk).
5. **Correlation Coefficient $\rho < 0.30$** (ensuring near-perfect independence).
6. **Drawdown is stabilizing** (no losses in the last 10 cycles, upward equity slope).
7. **Strict MEF Sizing** (both slots remain locked to the Market Executable Floor).

If any condition degrades, the exception slot is revoked, and the capacity throttle instantly demotes capacity back to 1 slot.
