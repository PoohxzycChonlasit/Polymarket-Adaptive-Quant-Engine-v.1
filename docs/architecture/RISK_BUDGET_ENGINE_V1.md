# RISK_BUDGET_ENGINE_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document specifies the design for the dynamic risk budgeting engine of the Polymarket Crypto 5M Quant Engine. It translates session-level cash equity and drawdown bounds into trade-level risk budgets.

---

## 1. Usable Risk Capital (URC) Formulation

To guarantee that the engine never breaches session drawdown limits or falls below the hard balance floor, the sizer computes the **Usable Risk Capital (URC)** at the start of each cycle:

$$URC = \max\left(0.0, \min\left(\text{Cash Equity} - \text{Floor Balance}, \text{Daily Limit} - \text{Session Drawdown}\right)\right)$$

Where:
- **Cash Equity**: Current account balance excluding active contract margin.
- **Floor Balance**: Hard limit set at **$5.00**.
- **Daily Limit**: 10% of start-of-day bankroll balance.
- **Session Drawdown**: Cumulative dollar losses realized in the current UTC session.
- **Rule**: The total notional cost of any active trades plus the proposed entry candidate must not exceed $URC$. If $URC = 0.0$, the engine is blocked from entering any new positions.

---

## 2. Dynamic Sizing Risk Budget Tables

The engine assigns risk budgets dynamically based on bankroll tiers. This implements the **Capacity First, Size Second** principle by tapering down slot-level risk as the portfolio diversifies:

| Bankroll Tier | Base Bankroll | Max Portfolio Exposure | Concurrent Slots ($N_{\text{slots}}$) | Max Slot Risk Budget (USDC) | Sizing Suffix |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`T0_MICRO_SEED`** | $10 | 10.0% | 1 | $1.00 (10% of bankroll) | Flat MEF |
| **`T1_MICRO_BUILD`** | $25 | 10.0% | 2 | $1.25 (5.0% of bankroll) | Flat MEF |
| **`T2_MICRO_SURVIVAL`**| $50 | 9.0% | 2 | $2.25 (4.5% of bankroll) | Flat MEF |
| **`T3_BASE_BUILD`** | $100 | 8.0% | 3 | $2.66 (2.66% of bankroll) | Standard Kelly|
| **`T4_BASE_STABLE`** | $250 | 7.0% | 4 | $4.37 (1.75% of bankroll) | Standard Kelly|
| **`T5_SMALL_GROWTH`** | $500 | 6.0% | 5 | $6.00 (1.20% of bankroll) | Standard Kelly|

---

## 3. Dynamic Budget Allocation Matrix

At the cycle level, the sizer adjusts budget allocation based on the active risk state:

### A. NORMAL STATE
- **Allocation**: 100% of standard slot risk budget.
- **Sizer Mode**: Kelly or Flat according to tier.

### B. DEFENSIVE STATE
- **Allocation**: 50% of standard slot risk budget.
- **Slot Count**: Capped at $N_{\text{slots}} - 1$.
- **Sizer Override**: Restricts Kelly fraction to 0.10.

### C. SURVIVAL STATE (Micro Recovery)
- **Allocation**: Suspends Kelly. Restricts sizing to the absolute **Market Executable Floor (MEF)**.
- **Slot Count**: Defaults to **1 active slot**.
- **Exception Slot**: Permits an optional **2nd active slot** *only* if the recovery engine's strict criteria are met.
- **Budget Restriction**:
  $$\text{Max Slot Budget} = \text{MEF notional}$$
