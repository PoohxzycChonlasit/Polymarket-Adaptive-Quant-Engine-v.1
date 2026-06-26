# LOSS_CLUSTER_ENGINE_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document specifies the loss cluster detection, reduced aggression windows, and exponential backoff throttle constraints for the Polymarket Crypto 5M Quant Engine.

---

## 1. Loss Cluster Identification

A **Loss Cluster** is defined as a sequence of **3 consecutive realized losses** within the same market regime.

- **Tracking Mechanism**: The engine maintains a rolling queue of the last 10 resolved trades, storing:
  - Trade outcome (`WIN` or `LOSS`).
  - Realized PnL.
  - Market Regime Label at entry (e.g., `HIGH_VOLATILITY_TREND`, `LOW_VOLATILITY_COMPRESSION`).
- **Trigger**: If the last 3 resolved trades in the active regime are all `LOSS`, a loss cluster is declared. This indicates a potential regime mismatch where strategy parameters are out of sync with current market behavior.

---

## 2. The Reduced Aggression Window

Upon triggering a loss cluster, the engine immediately initiates a **Reduced Aggression Window**:

- **Scanning Status**: **Continues scanning and ranking uninterrupted**. The bot remains fully aware of market dynamics.
- **Sizer Adjustment**: Applies a **50% sizing cut** ($M_{\text{state}} = 0.50$) to all trade calculations.
- **Selectivity Elevators**:
  - The minimum EV threshold is raised from **0.02 to 0.05**.
  - The minimum ETS threshold is raised from **0.60 to 0.75**.
  - Spread caps are tightened to **$\le 2.0\%$** of mid-price.
  - Max slots are capped at **2 concurrent slots**.
- **Exit Condition**: The reduced aggression window is cleared only after the engine records **2 consecutive winning trades** in the active regime, or when the daily statistics reset at **00:00 UTC**.

---

## 3. Exponential Backoff Throttling

To prevent trading through sustained regime shocks while maintaining entry readiness, the engine applies an **Exponential Backoff Throttle Window**:

$$\text{Throttle Seconds} = 300 \times 2^{\text{consecutive losses} - 3} \text{ for losses } \ge 3$$
$$\text{Max Throttle} = 1800 \text{ seconds (30 minutes)}$$

| Consecutive Losses | Throttle Duration | Action on Ingestion / Scan | Sizer & Entry Rule |
| :---: | :---: | :--- | :--- |
| **3** | 300s (5 mins) | Continues scanning & ranking | Entry blocked unless **Elite Opportunity** |
| **4** | 600s (10 mins) | Continues scanning & ranking | Entry blocked unless **Elite Opportunity** |
| **5** | 1200s (20 mins) | Continues scanning & ranking | Entry blocked unless **Elite Opportunity** |
| **6+** | 1800s (30 mins cap) | Continues scanning & ranking | Entry blocked unless **Elite Opportunity** |

### A. The Elite Opportunity Exception Gate
During a throttle window, standard entries are blocked. However, because the engine continues scanning, it remains eligible to execute if a candidate satisfies the **Elite Opportunity Gate**:
1. **Composite ETS $\ge 0.90$** (optimal execution).
2. **EV $\ge 0.08$** (extreme theoretical edge).
3. **Spread $\le 1.0\%$** of mid-price (tight spread friction).
4. **Quote Age $\Delta t < 1.0\text{ second}$** (guaranteed fresh data).
5. **Sizing**: Locked to the 50% Defensive cap.

This allows the bot to exploit high-edge setups that present themselves during the throttle window, while shielding capital from ordinary noise.
