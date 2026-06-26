# CAPACITY_SCALING_MODEL_V1
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-24**  

This document outlines the Capacity Scaling Model for concurrent positions and slot allocation in Polymarket 5-minute prediction markets.

---

## 1. Concurrent Slot Allocation limits

To prevent daily drawdown breaches, the system restricts the number of simultaneous active trades (slots) based on the bankroll tier:

| Tier | Bankroll Range | Max Concurrent Slots | Max Exposure Per Slot | Max Portfolio Exposure | Sizing Risk Mode |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **T0_MICRO_SEED** | $10 - $25 | **1** | 10.0% | 10.0% | Survival |
| **T1_MICRO_BUILD** | $25 - $50 | **1 - 2** | 5.0% | 10.0% | Survival |
| **T2_MICRO_SURVIVAL** | $50 - $100 | **2** | 4.5% | 9.0% | Survival |
| **T3_BASE_BUILD** | $100 - $250 | **2 - 3** | 4.0% | 8.0% | Kelly |
| **T4_BASE_STABLE** | $250 - $500 | **3 - 4** | 3.5% | 7.0% | Kelly |
| **T5_SMALL_GROWTH** | $500 - $1,000 | **4 - 5** | 3.0% | 6.0% | Kelly |

---

## 2. Key Scaling Questions Answered

### Q1: How many simultaneous positions are realistic?
* **For Micro Family ($10 - $100)**: **1 to 2 positions** is the absolute limit.
  - *Risk Constraint*: If a Micro Build account has a $25 balance and opens two $1.25 positions (5% each), a simultaneous loss on both results in a **10% loss**, instantly triggering the hard daily drawdown lockdown!
  - *Correlation Risk*: BTC and ETH binary prediction markets are highly correlated. Running more than 2 slots in the same 5-minute cycle exposes the system to a high joint loss probability, destroying the bankroll.
* **For Standard Family ($100 - $1000)**: **2 to 5 positions** are realistic.
  - *Expectancy Preservation*: Sizing is much smaller (2% - 4% of bankroll), so a simultaneous loss on 3 positions results in a 6% loss, which is well below the 10% daily limit.
  - *Microstructure Liquidity*: As size increases, orderbook depth must be partitioned. Dividing capital across 3-5 concurrent positions minimizes price slippage.

### Q2: When should slot count increase?
Slot count must only increase when the active risk budget can fully absorb the concurrent slot risk without violating daily drawdown bounds:
$$\text{Max Concurrent Slots} \times \text{Tier Max Risk \%} < \frac{\text{Daily Drawdown Limit}}{2}$$
This ensures a **2x safety cushion** against simultaneous losses. 
For example, to transition to **3 slots** under a **10% daily drawdown limit**, the individual slot risk must be capped at:
$$\text{Max Risk Per Slot} < \frac{10\%}{2 \times 3} = 1.66\%$$
If the sizer’s base risk exceeds 1.66%, the slot count must remain capped at 2.

---

## 3. Opportunity Decay vs. Capital Lockup

In 5-minute prediction markets, the system faces a critical tradeoff between capital lockup and opportunity half-life:

```
Cycle Start (T=0s) ──────────────► T=35s ──────────────────► T=240s ──────────────► T=300s (Expiry)
       │                           │                          │
       ▼                           ▼                          ▼
   [Warmup]                 [Active Trading]               [Cutoff]
- Spreads wide.             - Best liquidity.              - Fast price action.
- Books empty.              - Spreads normalized.          - High directional decay.
- Slots reserved.           - Fills complete.              - Slots locked / exit-only.
```

- **Capital Lockup**: Entering a position locks up collateral until settlement (at T=300s). Once a slot is filled, that capital cannot be recycled into newer, higher-EV opportunities that might form later in the cycle.
- **Opportunity Decay**: Fills near the cutoff (T=240s) have an extremely short window to resolve, leading to decay in fill probability and higher adverse selection.
- **Dynamic Slot Re-allocation**: 
  - The system reserves slots in the early active window (35-120s) for high-confidence candidates.
  - If slots remain empty by T=180s, the sizer dynamically relaxes sizer thresholds to allow lower-confidence, high-edge recovery trades to fill the remaining capacity.
  - At T=240s, all empty slots are deactivated, and the system moves to profit management and exit closeouts.
