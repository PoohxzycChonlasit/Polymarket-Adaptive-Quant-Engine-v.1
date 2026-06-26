# BANKROLL_PROMOTION_SYSTEM_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document formalizes the rules, gates, and hysteresis buffers governing capital promotions and demotions for tiers, trade capacities (slots), and share sizes in the Polymarket Crypto 5M Quant Engine.

---

## 1. Sizing Promotion Gates (Upgrade Rules)

Promotion check is executed strictly at **00:00 UTC** (no intraday compounding) and is blocked unless all five gates are cleared:

```
                  ┌─────────────────────────────────────────┐
                  │            PROMOTION GATES              │
                  ├──────────────┬──────────────┬───────────┤
                  │ COMPOSTION   │ PERFORMANCE  │ SAFETY    │
                  ├──────────────┼──────────────┼───────────┤
                  │ - Hysteresis │ - Win Rate   │ - ActiveQ │
                  │ - Balance    │ - 50 Trades  │ - DD = 0% │
                  └──────────────┴──────────────┴───────────┘
```

1. **Hysteresis & Compounding Gate**:
   - Cash equity must exceed the upper tier boundary (e.g. $50.00 for T1).
   - Once promoted, the engine applies a **5% hysteresis buffer** to prevent rapid thrashing. For example, if promoted to T2, the engine will not demote back to T1 unless cash equity falls below **$47.50** ($50.00 - 5%).
2. **Performance Win Rate Gate**:
   - The strategy's rolling 50 resolved trades must demonstrate a win rate ($WR$) exceeding the price-dependent breakeven gate:
     $$WR \ge \text{Average Fill Price} + 0.02 \text{ (friction buffer)}$$
   - This ensures sizing only scales up when the strategy is statistically profitable in real execution.
3. **Active Question Lock**:
   - Sizing changes are completely blocked as long as any critical research question (e.g., `LOW_PRICE_TRUTH_RESOLUTION_001` in `docs/research/ACTIVE_QUESTION.md`) remains open in the registry.
4. **Drawdown Reset Gate**:
   - Sizing cannot increase if the current daily drawdown is $>0\%$. Daily statistics must reset and clear at 00:00 UTC before risk configuration changes can be applied.

---

## 2. Capacity vs. Sizing Promotion Sequence

Promotions are coordinated strictly to prioritize **Capacity (Slots) first, Sizing second**:

```
[Tier Upgrade Cleared] ──► [Step 1: Promote Slot Capacity] ──► [Step 2: Sizing Cap Promoted]
                               (Instant on upgrade)          (Only after 50-trade win rate check)
```

1. **Step 1: Capacity Promotion**:
   - Upon clearing the promotion gates, the engine immediately increases the maximum concurrent slot capacity (e.g., expanding from 2 slots to 3 slots in T3). This allows the system to capture more independent, uncorrelated opportunities.
2. **Step 2: Share Size Promotion**:
   - The maximum notional cap per order remains restricted to the previous tier's limit until the bot executes at least **50 resolved trades** in the new tier and satisfies the win rate gate. Once cleared, the individual order cap is promoted to the new tier's maximum.

---

## 3. Sizing Demotion Gates (Downgrade Rules)

Unlike promotions, which are gated and slow, **demotions are real-time, immediate, and aggressive** to preserve capital:

- **Tier Demotion**:
  - *Trigger*: Cash equity falls below the tier lower boundary minus the 5% hysteresis buffer.
  - *Action*: Instantly demotes the bankroll tier, shrinks the max portfolio exposure budget, and scales down sizing limits.
- **Capacity Demotion**:
  - *Trigger*: Risk state shifts to `DEFENSIVE` or `SURVIVAL`.
  - *Action*: Slots are immediately reduced by 1 (Defensive) or locked to 1 (Survival, except for the ETS/liquidity exception slot).
- **Share Size Demotion**:
  - *Trigger*: Loss cluster (3 consecutive losses) or daily drawdown $>5\%$.
  - *Action*: Immediately applies a 50% multiplier ($M_{\text{state}} = 0.50$) to sizer outputs.
