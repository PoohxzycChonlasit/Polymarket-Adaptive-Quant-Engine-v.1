# POSITION_SIZING_MATRIX_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document defines the multi-dimensional position sizing lookup matrix for the Polymarket Crypto 5M Quant Engine. It cross-references Bankroll Tiers, Active Risk States, and Executable Truth Scores (ETS) to output the finalized sizing policies.

---

## 1. Master Position Sizing Matrix

The table below maps sizing behaviors and caps across bankroll tiers and risk states:

| Bankroll Tier | Sizer Mode | Normal Risk Mode Sizing | Defensive Risk Mode Sizing | Survival Risk Mode Sizing | ETS Scaling Behavior |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`T0_MICRO_SEED`**<br>($10–$25) | **Survival** | Flat $\text{MEF}^*$ ($0.05–$0.50 notional) | Flat $\text{MEF}^*$ ($0.05–$0.25 notional) | Hard block / Veto | Threshold Veto ($ETS < 0.85$) |
| **`T1_MICRO_BUILD`**<br>($25–$50) | **Survival** | Flat $\text{MEF}^*$ ($0.05–$0.50 notional) | Flat $\text{MEF}^*$ ($0.05–$0.25 notional) | Hard block / Veto | Threshold Veto ($ETS < 0.85$) |
| **`T2_MICRO_SURVIVAL`**<br>($50–$100) | **Survival** | Flat $0.25 notional | Flat $\text{MEF}^*$ ($0.05–$0.15 notional) | Flat $\text{MEF}^*$ ($0.05–$0.10 notional) | Threshold Veto ($ETS < 0.85$) |
| **`T3_BASE_BUILD`**<br>($100–$250) | **Kelly** | 0.20 Kelly Sizer<br>(Capped at 4% / slot) | 0.10 Kelly Sizer<br>(Capped at 2% / slot) | Capped at Flat $0.50 | Linear Scaling ($Base \times ETS$) |
| **`T4_BASE_STABLE`**<br>($250–$500) | **Kelly** | 0.20 Kelly Sizer<br>(Capped at 3.5% / slot) | 0.10 Kelly Sizer<br>(Capped at 1.75% / slot) | Capped at Flat $1.00 | Linear Scaling ($Base \times ETS$) |
| **`T5_SMALL_GROWTH`**<br>($500–$1,000) | **Kelly** | 0.20 Kelly Sizer<br>(Capped at 3.0% / slot) | 0.10 Kelly Sizer<br>(Capped at 1.5% / slot) | Capped at Flat $2.00 | Linear Scaling ($Base \times ETS$) |

$$\text{*Note: } \text{MEF} = \text{Market Executable Floor} = \max(\text{1 Share}, \text{Market Min Order Size})$$

---

## 2. Matrix Execution Rules

### A. The Market Executable Floor (MEF) Sizing Limit
In micro-tiers (`T0`–`T2`), theoretical Kelly calculations frequently output fractions of cents, which are rejected by the Polymarket CLOB. The engine bypasses Kelly and applies the **MEF** rule:
- **Contract Price $\ge \$0.05$**: 1 share represents $\ge \$0.05$ notional, which satisfies the CLOB minimum order value. Sizing is set to **1 share**.
- **Contract Price $<\$0.05$**: 1 share costs less than the CLOB limit. The engine computes the minimum number of shares needed to exceed $0.05:
  $$\text{Shares} = \lceil 0.05 / \text{Price} \rceil$$
  Sizing is set to this calculated share count (e.g. 3 shares for a $0.02 contract).
- **Rule**:
  $$\text{MEF Size (USDC)} = \max(\text{1 Share}, \text{Market Min Order Size})$$

### B. Defensive Mode Transition Override
- When daily drawdown crosses **5%**, the engine switches to `DEFENSIVE` mode.
- The sizer instantly halts Kelly calculations for the current session, restricts the sizer to **0.10 Kelly fraction** (50% of Normal), and caps the max risk exposure per slot.
- Daily statistics must reset at **00:00 UTC** before normal sizer limits can be restored.

### C. ETS Scaling Interaction
- If $ETS < 0.60$ (in Normal) or $ETS < 0.85$ (in Survival/Micro), the matrix outputs `REJECT` (Skip Cycle).
- If it passes the veto check, the base size from the matrix is scaled by the $ETS$ score:
  $$\text{Final Sizing} = \text{Matrix Sizing} \times ETS$$
- For example, if T3 Normal size is calculated as $4.00, and $ETS = 0.75$ (due to a $0.02 spread and quote age latency), the final position size is scaled to **$3.00**.
