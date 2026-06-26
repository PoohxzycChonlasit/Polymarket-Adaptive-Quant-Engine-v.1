# CAPACITY_ALLOCATION_ENGINE_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document specifies the slot allocation, correlation management, and capital partitioning rules for the Polymarket Crypto 5M Quant Engine. It translates the **Capacity First, Size Second** directive into actionable portfolio allocation rules.

---

## 1. Slot Allocation and Partitioning Logic

To distribute risk across independent trades and prevent single-order concentration, the engine partitions capital dynamically across concurrent execution slots.

### A. Slot Count Rules by Tier and Risk State
The number of active concurrent slots ($N_{\text{slots}}$) is determined by the bankroll tier and scaled down in degraded risk states:

| Bankroll Tier | Normal Mode Slots | Defensive Mode Slots | Survival Mode Slots | Max Portfolio Exposure |
| :--- | :---: | :---: | :---: | :---: |
| **`T0_MICRO_SEED`** | 1 | 1 | 1 | 10.0% |
| **`T1_MICRO_BUILD`** | 2 | 1 | 1 | 10.0% |
| **`T2_MICRO_SURVIVAL`** | 2 | 1 | 1 | 9.0% |
| **`T3_BASE_BUILD`** | 3 | 2 | 1 | 8.0% |
| **`T4_BASE_STABLE`** | 4 | 2 | 1 | 7.0% |
| **`T5_SMALL_GROWTH`** | 5 | 3 | 1 | 6.0% |

### B. Capital Partitioning Formula
Rather than allocating a large fraction of the bankroll to a single contract, the engine divides the total portfolio exposure budget equally among the active slots:
$$\text{Max USDC Per Slot} = \frac{\text{Bankroll} \times \text{Max Portfolio Exposure \%}}{N_{\text{slots}}}$$
- **Example (T3 Normal)**: Bankroll = $100, Max Portfolio Exposure = 8.0%, $N_{\text{slots}} = 3$:
  $$\text{Max USDC Per Slot} = \frac{\$100 \times 8.0\%}{3} \approx \mathbf{\$2.66}$$
  This ensures that if the sizer is triggered on 3 assets (e.g. BTC, ETH, and a proxy), the exposure is capped at $2.66 per trade rather than putting a single $8.00 bet on one contract.
- **Sizing Precedence**:
  $$\text{Position Size} = \min\left(\text{Adjusted Kelly Sizing}, \text{Max USDC Per Slot}\right)$$

---

## 2. Correlation and Joint Risk Overrides

Because BTC and ETH binary prediction markets are highly cointegrated, simultaneous entries represent correlated exposure. The engine implements a **Correlation Gate** to regulate slot allocation:

```
Candidate Ingested (e.g. ETH YES)
        │
        ▼
Is there an active slot filled? (e.g. BTC YES)
        ├──► NO  ──► Enter Trade (Normal Sizing)
        └──► YES ──► Calculate rolling 30-min correlation (ρ)
                       │
                       ├─► Normal Mode: If ρ >= 0.85 ──► Scale down size by (1 - ρ²)
                       ├─► Defensive Mode: If ρ >= 0.75 ──► Scale down size by (1 - ρ²)
                       └─► Survival Mode: If ρ >= 0.50 ──► Hard Veto (Reject ETH)
```

1. **The Correlation Gate**:
   Before approving a new entry, the engine calculates the rolling 30-minute correlation coefficient ($\rho$) of price changes between the candidate asset and all currently active positions.
2. **Survival Mode Correlation Block**:
   In **Survival Mode**, the correlation cap is set to a strict **$\rho_{\text{cap}} = 0.50$**. If the correlation exceeds 0.50, the second trade is **completely vetoed** (no correlated exposure allowed). This prevents joint loss events.
3. **Defensive/Normal Scaling**:
   If the correlation cap is cleared but remains elevated, the second trade size is scaled down using the correlation multiplier:
   $$M_{\text{correlation}} = 1.0 - \rho^2$$

---

## 3. Slot Recycling & Collateral Lockup

- **Collateral Lockup**: Collateral is locked on-chain from the time of order fill until oracle settlement (T=300s). Locked capital cannot be reused for new entries within the same cycle.
- **Deactivation Cutoff (T=240s)**: At 240 seconds, all empty slots are deactivated. No new entry intents are allowed, and active slots are held strictly for exit management.
- **Post-Settlement Release**: Upon receipt of the oracle resolution payload, the position is marked as closed, and the slot is instantly released back to the available pool for the next cycle.
