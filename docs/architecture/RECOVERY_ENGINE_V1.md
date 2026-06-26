# RECOVERY_ENGINE_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document formalizes the autonomic, self-healing recovery logic of the Polymarket Crypto 5M Quant Engine. It specifies how the engine transitions back to normal states after drawdowns and loss clusters without manual intervention, ensuring continuous 24/7 VPS operation.

---

## 1. Autonomic Recovery State Transitions

To prevent permanent halts, the recovery engine coordinates transitions back to normal modes using performance-based gates rather than strict UTC time resets:

```
                  ┌──────────────┐
                  │    NORMAL    │
                  └──────▲───────┘
                         │ (Realized Win Rate >= Breakeven Gate & DD = 0% at UTC)
                  ┌──────┴───────┐
                  │  DEFENSIVE   │
                  └──────▲───────┘
                         │ (Balance > $6.00 & 20-trade Win Rate >= Breakeven)
                  ┌──────┴───────┐
                  │   SURVIVAL   │
                  └──────────────┘
```

1. **Survival to Defensive Transition Gate**:
   - *Trigger*: Account cash equity recovers above **$6.00**, and the rolling 20-trade resolved win rate exceeds the price-dependent breakeven gate:
     $$WR \ge \text{Average Price} + 0.02$$
   - *Action*: Automatically promotes the risk state from `SURVIVAL` to `DEFENSIVE`. Suspends MEF limits, allowing 50% Kelly sizing.
2. **Defensive to Normal Transition Gate**:
   - *Trigger*: Session drawdown returns to **0.0%** (realized at UTC reset) AND the rolling 50-trade win rate exceeds the breakeven gate.
   - *Action*: Automatically promotes from `DEFENSIVE` to `NORMAL` mode. Restores standard base risk fractions and concurrent slot counts.

---

## 2. Survival Mode Capacity Expansion: The 2nd Slot Exception

By default, Survival Mode caps the concurrent slot capacity at **1 active slot** to prevent correlation exposure. However, to accelerate recovery under optimal execution conditions, the engine permits an optional **2nd active slot** strictly if all seven criteria are met:

1. **Excellent Executable Truth Score**:
   - The candidate's composite $ETS$ must be $\ge 0.90$.
2. **Excellent Liquidity**:
   - Immediate L1 touch depth must be $>200\text{x}$ the target order size, guaranteeing zero slippage.
3. **Tight Spread**:
   - The bid-ask spread must be $\le 1.0\%$ of the contract mid-price.
4. **Fresh Quotes**:
   - Quote age ($\Delta t$) must be $<1.0\text{ second}$.
5. **Low Correlation Risk**:
   - Cointegrated correlation between the active asset and the candidate must be $\rho < 0.30$.
6. **Stabilizing Drawdown**:
   - The engine must have recorded zero realized losses over the last 10 cycles, and the local equity slope must be positive.
7. **Strict MEF Sizing**:
   - The position size for **both** the active and the proposed slot must remain strictly locked to the Market Executable Floor:
     $$\text{Sizing} = \max(\text{1 Share}, \text{Market Min Order Size})$$

If any of these conditions fail, the exception is revoked, and slot capacity is instantly restricted to 1 active slot.

---

## 3. Dynamic Loss Cluster Exponential Backoff

To prevent trading into regime shocks (e.g. repeated trend reversals in range-bound markets), the engine replaces the static 30-minute pause with an **Exponential Backoff Pause** based on consecutive losses:

$$\text{Pause Seconds} = 300 \times 2^{\text{consecutive losses} - 3} \text{ for consecutive losses } \ge 3$$
$$\text{Max Pause} = 1800 \text{ seconds (30 minutes)}$$

| Consecutive Losses | Pause Duration | Cycle Impact | Rationale |
| :---: | :---: | :---: | :--- |
| **3** | 300 seconds (5 mins) | 1 cycle pause | Short pause to allow brief price spike to normalize. |
| **4** | 600 seconds (10 mins) | 2 cycles pause | Medium pause; filters out rapid double-reversal spikes. |
| **5** | 1200 seconds (20 mins) | 4 cycles pause | Long pause; allows high-volatility session block to expire. |
| **6+** | 1800 seconds (30 mins) | 6 cycles pause | Hard cap; protects capital during sustained regime shifts. |
