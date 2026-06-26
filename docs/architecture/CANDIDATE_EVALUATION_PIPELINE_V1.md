# CANDIDATE_EVALUATION_PIPELINE_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document specifies the Candidate Ingestion, Evaluation, and Ranking pipeline for the Polymarket Crypto 5M Quant Engine. The pipeline evaluates candidates by separating data into five distinct domains of "Truth."

---

## 1. Separation of the Five Truths

Every ingested candidate is evaluated by isolating and verifying five separate domains of truth before order intent generation:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CANDIDATE EVALUATION                          │
├──────────────┬──────────────┬──────────────┬──────────────┬────────────┤
│ SIGNAL TRUTH │ EXEC TRUTH   │  RISK TRUTH  │ BANKROLL TRU │ INV TRUTH  │
├──────────────┼──────────────┼──────────────┼──────────────┼────────────┤
│ - Model Prob │ - Bid/Ask    │ - Drawdown   │ - Tier ID    │ - Slots    │
│ - Fair Value │ - L1 Depth   │ - Risk Mode  │ - Cash Equit │ - Inv Caps │
│ - Mid-EV     │ - Quote Age  │ - Loss Clust │ - URC        │ - Release  │
└──────────────┴──────────────┴──────────────┴──────────────┴────────────┘
```

### A. Signal Truth (Idealized Edge)
- **Inputs**: Model Probability ($P_{\text{model}}$), Fair Value (FV), Expected Value at Mid-Market ($EV_{\text{mid}}$).
- **Evaluation**: Establishes whether a candidate possesses a theoretical strategy edge. If the raw signal win probability is below the floor, the candidate is instantly discarded.

### B. Executable Truth (Execution Feasibility)
- **Inputs**: Ask price, bid price, spread, L1 depth, quote age ($\Delta t$), cycle elapsed time.
- **Evaluation**: Computes how much edge remains after accounting for transaction spread costs, slippage, and latency. Translates these metrics into the composite **Executable Truth Score (ETS)**.

### C. Risk Truth (Portfolio Safety)
- **Inputs**: Daily drawdown %, active risk state, loss cluster state.
- **Evaluation**: Determines whether entering a trade is permitted under the portfolio's current risk state. If the state is in `DEFENSIVE` or `SURVIVAL`, it scales down sizing and caps slots.

### D. Bankroll Truth (Capital Constraints)
- **Inputs**: Cash equity, starting daily balance, floor balance ($5.00), hysteresis tier.
- **Evaluation**: Verifies if the account balance exceeds the hard floor and calculates the available **Usable Risk Capital (URC)**. If the proposed notional cost exceeds the URC, the candidate is rejected.

### E. Inventory Truth (Capacity Slots)
- **Inputs**: Active slots filled, cointegrated correlation ($\rho$), max inventory caps.
- **Evaluation**: Inspects portfolio capacity. If all slots are full, or if the candidate has high correlation with an active position, the trade is blocked to avoid joint risk.

---

## 2. Candidate Ranking Logic

If multiple candidate signals fire simultaneously in the same 5-minute cycle (e.g. both BTC and ETH YES signals are active), the pipeline ranks them to prioritize capital allocation.

1. **Calculate the Ranking Score**:
   Each candidate is scored using the product of its Executable EV and Executable Truth Score:
   $$\text{Ranking Score} = \text{Executable EV} \times ETS$$
   This prioritizes trades with a high theoretical edge *and* near-perfect execution environments.
2. **Rank and Sort**:
   Candidates are sorted in descending order of their Ranking Score.
3. **Slot Allocation**:
   - The highest-ranked candidate is allocated the first open slot.
   - Subsequent candidates are evaluated and allocated slots in order, subject to the **Capacity Allocation Engine** correlation cap. If a lower-ranked candidate exceeds the correlation cap (e.g. ETH correlation with BTC is $\ge 0.50$ in Survival Mode), it is vetoed.
