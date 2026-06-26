# DYNAMIC_SHARE_MODEL_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document formalizes the Dynamic Share Model for the Polymarket Crypto 5M Quant Engine. It defines how position size in USDC is translated into integer share counts under contract price variations, and analyzes the capital usage implications for micro bankrolls.

---

## 1. Share Sizing and Quantization Formulas

Position size calculated in USDC must be converted to an integer share count for execution on the Polymarket CLOB:

$$\text{Raw Shares} = \frac{\text{Adjusted Position Size (USDC)}}{\text{Ask Price}}$$
$$\text{Quantized Shares} = \max\left(\text{round}(\text{Raw Shares}), \text{MEF}\right)$$

Where:
- **Ask Price** is the price of YES or NO contracts ($0.01$ to $0.99$).
- **MEF** (Market Executable Floor) is defined as:
  $$\text{MEF} = \max(\text{1 Share}, \lceil 0.05 / \text{Ask Price} \rceil)$$
  This guarantees that the order satisfies the CLOB minimum order value of **$0.05 USDC** at any price.

---

## 2. Capital Usage Matrix (USDC Cost)

The table below calculates the exact capital required (notional cost) for representative contract prices and share counts:

| Contract Price | 1 Share Cost | 5 Shares Cost | 10 Shares Cost | 20 Shares Cost | 50 Shares Cost |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **$0.10** | $0.10 | $0.50 | $1.00 | $2.00 | $5.00 |
| **$0.20** | $0.20 | $1.00 | $2.00 | $4.00 | $10.00 |
| **$0.40** | $0.40 | $2.00 | $4.00 | $8.00 | $20.00 |
| **$0.60** | $0.60 | $3.00 | $6.00 | $12.00 | $30.00 |
| **$0.80** | $0.80 | $4.00 | $8.00 | $16.00 | $40.00 |
| **$0.90** | $0.90 | $4.50 | $9.00 | $18.00 | $45.00 |

---

## 3. Micro-Tier Feasibility Audit ($10, $20, $50 Bankrolls)

Evaluating these capital costs against micro bankroll limits under a **10% daily drawdown limit** and a **$5.00 floor**:

### A. $10 Bankroll (T0_MICRO_SEED)
- **Constraints**: Usable capital = $5.00. Daily drawdown limit = **$1.00**. Max Slot Exposure = **10.0% ($1.00)**. Max concurrent slots = **1**.
- **Feasibility Map**:
  - **Prohibited Zone**: Any trade costing $> \$1.00$. All 50 shares, 20 shares, and 10 shares columns are completely blocked. 5 shares is blocked for all prices $\ge \$0.20$.
  - **Permitted Zone**:
    - **Cheap contracts ($0.10$)**: Can buy up to 10 shares ($1.00$ cost) while staying within the slot limit.
    - **Mid contracts ($0.20–$0.40$)**: Can buy up to 5 shares ($1.00$ cost at $0.20$) or 1–2 shares.
    - **Expensive contracts ($0.60–$0.90$)**: Strictly restricted to **1 share** (costs $0.60–$0.90). A 5-share purchase at $0.90$ costs $4.50$, which represents 45% of the bankroll and 450% of the daily drawdown budget, causing instant lockdown.
  - **Verdict**: Sizing must be highly price-sensitive. To trade expensive contracts, the sizer must strictly limit shares to 1.

### B. $20 Bankroll (T0_MICRO_SEED)
- **Constraints**: Usable capital = $15.00. Daily drawdown limit = **$2.00**. Max Slot Exposure = **10.0% ($2.00)**. Max slots = **1**.
- **Feasibility Map**:
  - **Prohibited Zone**: Trades costing $> \$2.00$. 50 shares is entirely blocked. 20 shares is blocked for prices $\ge \$0.20$. 10 shares is blocked for prices $\ge \$0.40$. 5 shares is blocked for prices $\ge \$0.60$.
  - **Permitted Zone**: Can trade 10 shares at $0.10$ ($1.00$) or $0.20$ ($2.00$). Can trade 5 shares at $0.40$ ($2.00$). For expensive contracts ($0.80–$0.90$), restricted to 1–2 shares.

### C. $50 Bankroll (T2_MICRO_SURVIVAL)
- **Constraints**: Usable capital = $45.00. Daily drawdown limit = **$5.00**. Max Slot Exposure = **4.5% ($2.25)**. Max slots = **2**.
- **Feasibility Map**:
  - **Prohibited Zone**: Sizing per order is capped by the slot limit of **$2.25**. 50 shares is blocked at all prices (min cost $5.00$). 20 shares is blocked for prices $\ge \$0.20$. 10 shares is blocked for prices $\ge \$0.40$.
  - **Permitted Zone**: Can trade 20 shares at $0.10$ ($2.00$). Can trade 10 shares at $0.20$ ($2.00$). Can trade 5 shares at $0.40$ ($2.00$). Restricted to 1–2 shares for expensive contracts ($0.60–$0.90$).
