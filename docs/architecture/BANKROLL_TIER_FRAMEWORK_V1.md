# BANKROLL_TIER_FRAMEWORK_V1
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-24**  

This framework formalizes the bankroll tier transitions, sizing rules, and hysteresis protections for capital scaling from $10 to $1000 in Polymarket 5-minute prediction markets.

---

## 1. Bankroll Tier Progression ($10 to $1000)

| Tier | Bankroll Range | Base Risk % | Max Trades/Hour | Min Bet (USD) | Max Bet (USD) | Sizer Mode | Target Asset |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **T0_MICRO_SEED** | $10 - $25 | 3% - 5% | 2 - 4 | $0.05 | $1.25 | Survival (Manual) | Cheap only (<$0.15) |
| **T1_MICRO_BUILD** | $25 - $50 | 4% - 6% | 3 - 5 | $0.05 | $3.00 | Survival (Manual) | Cheap / Mid |
| **T2_MICRO_SURVIVAL** | $50 - $100 | 4% - 5% | 4 - 6 | $0.05 | $5.00 | Survival (Manual) | Cheap / Mid |
| **T3_BASE_BUILD** | $100 - $250 | 3% - 4% | 5 - 8 | $0.50 | $10.00 | Standard (Kelly) | All |
| **T4_BASE_STABLE** | $250 - $500 | 2.5% - 3.5% | 6 - 8 | $0.75 | $17.50 | Standard (Kelly) | All |
| **T5_SMALL_GROWTH** | $500 - $1,000 | 2% - 3% | 6 - 10 | $1.00 | $30.00 | Standard (Kelly) | All |

---

## 2. Key Sizing Questions Answered

### Q1: What is the realistic minimum share size by bankroll tier?
On the Polymarket CLOB, the absolute minimum order value is **$0.05 USDC**. This creates a physical constraint on the minimum share size depending on the contract price:
- **For $0.50 contracts (YES/NO)**: 1 share costs $0.50. The minimum fill size is **1 share** ($0.50 notional).
- **For low-priced contracts ($0.02)**: 1 share costs $0.02. To meet the $0.05 minimum order value, the minimum fill size is **3 shares** ($0.06 notional).
- **Dynamic Sizing Rule**: The sizer implements a dynamic minimum share floor based on edge (opportunity size):
  $$\text{Dynamic Min Shares} = \text{round}(1.0 + (\text{min}(\text{edge} / 0.15, 1.0) \times 4.0))$$
  This yields **1 to 5 shares** as the physical transaction floor.

### Q2: How do bankroll tiers evolve from $10 to $1000?
* **Micro Family ($10 - $100)**:
  - Sizing is in **survival mode**. Because bankrolls are tiny, standard fractional Kelly sizing ($10 \times 1\% \times 0.20 = \$0.02$) returns sizes below the CLOB order limit ($0.05).
  - Therefore, the system bypasses Kelly sizing and forces a flat **$0.05 to $0.10 micro-bet** (T0/T1) or **$0.25 bet** (T2).
  - Risk profiles are extremely defensive. Sizing does not scale with model confidence, and trades are restricted to high-edge opportunities to prevent rapid depletion of the tiny capital base.
* **Standard Family ($100 - $1000)**:
  - Sizing transitions to **standard fractional Kelly mode** with smooth interpolation.
  - The base risk taper automatically reduces the risk percentage as the bankroll grows within a tier, preventing sizing jumps at boundaries:
    $$\text{Base Risk} = \text{Max Risk} - (\text{Max Risk} - \text{Min Risk}) \times \text{Progress}$$
  - Sizer multipliers (confidence, EV, drawdown, spread, and liquidity) actively scale down the position size, keeping capital exposure safe.

### Q3: When should size increase?
Position size must only increase when the account balance crosses a tier boundary and satisfies the **upgrade gate**:
1. **Compounding Gate**: Balance must exceed the upper tier boundary.
2. **Hysteresis Lock**: A **5% buffer** is applied to downgrades to prevent "thrashing" (repeatedly upgrading and downgrading due to small PnL fluctuations). For example, to upgrade from T1 ($25-$50) to T2 ($50-$100), the balance must cross **$50.00**. Once in T2, the system will not downgrade back to T1 unless the balance falls below **$47.50** ($50.00 - 5%).
3. **No Intraday Compounding**: Sizing scales at the start of a session or cycle based on cash equity, not dynamically within the 5-minute loop.

---

## 3. Dynamic Parameter Adjustments by Tier

* **Confidence Floors**:
  - **T0-T2 (Micro)**: Floor is relaxed to **0.40** (or 0.38 in recovery mode) because micro sizers trade low-price asymmetry where high directional confidence is not required.
  - **T3-T5 (Standard)**: Floor is tightened to **0.54** to filter out marginal $0.50 trades that lack payoff leverage.
* **Max Market Exposure**:
  - T0-T2 capped at **10%** of bankroll.
  - T3-T5 tapers from **8%** down to **6%** of bankroll.
* **Stop Loss Levels**:
  - T0-T2 uses tight stop-loss percentages (**85% - 90%** of entry cost) to protect cash reserves.
  - T3-T5 uses standard stop-loss (**75% - 80%** of entry cost) to allow the position to breathe.
