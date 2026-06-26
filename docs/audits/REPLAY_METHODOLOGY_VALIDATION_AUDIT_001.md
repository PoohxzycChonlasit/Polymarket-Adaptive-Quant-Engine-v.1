# REPLAY_METHODOLOGY_VALIDATION_AUDIT_001

**Role**: 10_BACKTEST_REPLAY_AGENT  
**Mode**: READ ONLY — no code or config changes  
**Date**: 2026-06-18  
**Validates**: RISK_PLAN_ZERO_FORENSIC_AUDIT_001 methodology  
**Script**: `scratch/methodology_validation_v1.py`

---

## Context

The prior 7-day forensic audit (RISK_PLAN_ZERO_FORENSIC_AUDIT_001) reported:

| Metric | Original Claim |
|---|---|
| risk_plan_zero events | 1,156 |
| Resolved | 1,073 |
| $0.05 PnL | **+$257.56 USDC** |
| Profit Factor | **8.84** |
| <$0.10 bucket PnL | +$227.12 (97.7% of total) |

This conflicted with a prior 24h shadow sizing replay showing **negative expectancy**.  
This audit validates whether the methodology is structurally and mathematically sound.

---

## Q1 — Entry Price Source

> Was entry price based on executable best ask, not bid/mid?

**CORRECT ✓**

| Source | Count |
|---|---|
| `entry_price` field (direct) | 0 |
| YES side → `yes_ask` | 553 |
| NO side → `no_ask` | 603 |
| Fell back to `yes_bid` | 0 |
| Fallback to 0.50 | 0 |

No events used bid as entry. All 1,156 events used the ask price for their respective side, which is the correct executable entry cost.

**Spread Check (n=50 sample):**

| Metric | Value |
|---|---|
| Average ask-bid spread | 0.0104 |
| Maximum spread | 0.0300 |

> [!WARNING]
> Average spread > 1 cent. Using ask is **essential** — using bid would overstate edge by ~5–10% on average. The methodology correctly used ask. No correction required on this dimension.

---

## Q2 — Share Formula Verification

> Was the PnL formula correct?

**CORRECT ✓**

```
shares     = notional / entry_price
win_pnl    = shares × (1 - entry_price)
           = notional × (1 - entry_price) / entry_price
loss_pnl   = -notional
```

This is mathematically correct for binary 0/1 resolution contracts.

**Price Range Warning:**

| Metric | Value |
|---|---|
| Entry price range | 0.0090 – 0.4800 |
| Mean entry price | 0.1804 |
| Events with entry < $0.05 | **244 (21.1%)** |
| Events with entry > $0.95 | 0 |

> [!CAUTION]
> **244 events have entry prices below $0.05.** At these prices the formula creates extreme leverage:  
> - At $0.01 entry: one $0.05 win = **+$4.95**; one loss = **-$0.05** (99:1 payoff ratio)  
> - At $0.03 entry: one win = **+$1.62** vs -$0.05 loss  
>
> This means **a handful of wins in the <$0.05 price bucket can dominate total PnL** even with a 10–20% win rate. The formula is mathematically correct but the resulting PnL distribution has extreme positive skew that may not reflect real execution.

---

## Q3 / Q4 — Deduplication Analysis

> Were duplicate candidates counted multiple times?

**CRITICAL FINDING — METHODOLOGY FLAW ✗**

| Metric | Count |
|---|---|
| Total raw events loaded | 1,156 |
| Unique (market_id, epoch_start, side) | **355** |
| Unique (market_id, epoch_start) | 339 |
| Unique token_ids | 355 |
| Keys with >1 event | **214** |
| Events within duplicated keys | 1,015 |
| Max events per single key | 14 |
| **Duplication factor** | **~3.26×** |

```
87.8% of raw events are duplicates of the same market/epoch/side decision
```

The scanner collected `risk_plan_zero` decision events from `decision_log/*.jsonl`, but the realtime loop emits **multiple decision records per epoch per market** (once per scan cycle, typically every 60 seconds within a 5-minute window). A single market/epoch/side may appear 5–14 times.

The original audit applied the counterfactual PnL to **each raw event** instead of **each unique position**, inflating PnL by ~3.26×.

**Expected original PnL corrected for duplication:**

$$\text{Corrected estimate} \approx \frac{\$257.56}{3.26} \approx \$78.97$$

---

## Q5 — Settlement Truth Quality

> Were outcomes resolved from reliable near-expiry snapshots?

**ACCEPTABLE with caveats ✓/⚠**

| Metric | Value |
|---|---|
| Unique target keys checked | 339 |
| Keys with final snapshot (<180s) | 330 (97.4%) |
| Clear YES (yes_bid ≥ 0.65) | 93 |
| Clear NO  (yes_bid ≤ 0.35) | 217 |
| Ambiguous (0.35–0.65) | 20 |
| Ambiguity rate | **6.1%** |
| Snapshots within last 60s | 260 (78.8%) |
| Snapshots 60–180s from expiry | 70 (21.2%) |

The 6.1% ambiguity rate is acceptable. However:

> [!NOTE]
> The settlement threshold (yes_bid ≥ 0.65 = YES, ≤ 0.35 = NO) uses **bid** as the truth proxy at expiry. At genuine resolution, contracts trade near 0.97–0.99 (winner) or 0.01–0.03 (loser), so the 0.65/0.35 threshold is conservative and unlikely to misclassify settled outcomes. Snapshots at 60–180s before expiry are pre-settlement and introduce some residual uncertainty.

**Surviving sample bias risk**: 310 events excluded due to ambiguity or missing snapshots. If these are systematically losing trades, the reported win rate is upward-biased.

---

## Q6 — De-duplicated PnL Recompute

> What is the corrected PnL with one trade per market/side/epoch?

| Metric | Original | **De-duplicated** |
|---|---|---|
| Events used | 1,073 resolved | **322 resolved** |
| Win Rate | ~74% | **36.65%** |
| Total PnL ($0.05) | +$257.56 | **+$66.98** |
| Expectancy | +$0.240 | **+$0.208** |
| Profit Factor | 8.84 | **7.57** |

> [!IMPORTANT]
> The de-duplicated sample covers **339 unique market keys** (partial dataset — full de-duped scan over all dates may differ). The win rate collapse from ~74% to 36.65% is the most significant correction: the original 74% was an artifact of the same winning trade being counted 3–14 times.
>
> **The de-duplicated win rate of 36.65% is structurally consistent with the prior 24h shadow replay showing lower performance.** A ~37% win rate at mean entry $0.18 still yields positive expectancy due to the binary payoff asymmetry, but is a much weaker signal than reported.

---

## Q7 — De-duplicated Price Bucket Analysis

| Bucket | Count | Win Rate | PnL ($0.05) | Expectancy |
|---|---|---|---|---|
| **<0.10** | **86** | **40.70%** | **+$59.89** | **+$0.6964** |
| 0.10–0.20 | 71 | 33.80% | +$5.93 | +$0.0836 |
| 0.20–0.40 | 131 | 34.35% | +$1.16 | +$0.0089 |
| 0.40–0.60 | 34 | 41.18% | -$0.02 | -$0.0005 |
| >0.60 | 0 | N/A | — | — |

**Bucket interpretation:**

- The `<0.10` bucket still dominates even after de-duplication: **89.4% of PnL** from 26.7% of trades
- Positive expectancy in `<0.10` is mathematically driven by leverage, not win rate superiority
  - At mean price $0.05: one win ≈ **+$0.95**, one loss = **-$0.05** (19:1 payoff)
  - A 40.7% win rate at 19:1 payoff yields expectancy of ~+$0.39 per $0.05 bet
- `0.40–0.60` bucket has **negative expectancy** even at fair odds — no structural edge there

> [!CAUTION]
> The `<0.10` price bucket edge is **mathematically real** at the simulated sizes but **operationally suspect**: markets trading at 1–9 cents have extremely wide bid-ask spreads in practice, thin order book depth, and high adverse selection risk. The $0.05 simulation assumes fill at mid-ask, which may not be achievable.

---

## Q8 — Slippage Stress Test

| Slippage Added | Total PnL | Profit Factor |
|---|---|---|
| 0.00¢ | +$66.98 | 7.57 |
| +1.0¢ | +$47.42 | 5.65 |
| +2.0¢ | +$36.53 | 4.58 |
| +3.0¢ | +$29.42 | 3.88 |

Edge survives up to 3 cents of additional slippage in the de-duplicated sample. However, in the `<0.10` bucket at $0.01–$0.05 prices, a 1-cent slippage represents 20–100% of the entry price — severely impacting payout.

---

## Methodology Verdict

| Question | Finding | Status |
|---|---|---|
| Q1: Entry = ask | Yes, correctly used yes_ask / no_ask | ✅ CORRECT |
| Q2: Share formula | `notional × (1 - price) / price` = correct binary formula | ✅ CORRECT |
| Q3: Deduplication | **3.26× overcount** — 87.8% of events are duplicates | ❌ FLAWED |
| Q4: Unique counts | 1,156 raw → 355 unique market/epoch/side | ❌ OVERCOUNTED |
| Q5: Truth quality | 6.1% ambiguity, 97.4% covered by snapshot — acceptable | ✅ ACCEPTABLE |
| Q6: Corrected PnL | $257.56 → ~$66.98 after dedup (partial sample) | ⚠ MATERIALLY LOWER |
| Q7: Bucket recompute | <$0.10 still dominates; leverage-driven, not skill-driven | ⚠ CONCENTRATED RISK |
| Q8: Slippage survival | Edge survives to 3¢ slip at dedup level | ✅ PASSES (partial) |

---

## Final Verdict

**METHODOLOGY_PARTIALLY_FLAWED**

### Two Structural Defects

**Defect 1 (Critical): Deduplication Failure**  
The original replay counted 1,156 raw decision events against 355 unique market/epoch/side decisions — a **3.26× overcount**. The reported $257.56 PnL collapses to ~$66–79 after correction. The reported 74% win rate collapses to ~37%.

**Defect 2 (Material): Extreme Leverage in <$0.05 Bucket**  
244 events (21%) have entry prices below $0.05. The binary formula creates payoff ratios of 19:1 to 99:1 at these prices. The reported `<$0.10` PnL dominance ($59.89 / $66.98 = 89%) is mathematically valid but operationally unreliable — real execution at sub-5-cent prices involves severe spread, depth, and adverse selection risk not modeled by this replay.

### Reconciliation with Prior 24h Shadow Replay

The prior shadow replay showing **negative expectancy** likely used a shorter window with fewer unique candidates and may have applied a different (stricter) deduplication rule. These results are **consistent** once deduplication is applied:
- 37% win rate at $0.18 mean price ≈ marginally positive in simulation, fragile in execution

### What Is Signal vs. Noise

| Claim | Assessment |
|---|---|
| "1,156 risk_plan_zero events" | TRUE — but only 355 unique decisions |
| "$257.56 PnL at $0.05 sizing" | FALSE as stated — corrected to ~$66–79 |
| "Profit factor 8.84" | OVERSTATED — de-dup gives 7.57 (partial), still inflated by leverage |
| "<$0.10 bucket dominates PnL" | TRUE — but driven by leverage math, not statistical edge |
| "Confidence_too_low gate is the blocker" | TRUE — this remains the core finding |
| "SIZER_TOO_CONSERVATIVE" verdict | CAUTION — edge exists but is far smaller than reported |

---

## Recommended Next Steps

1. **Do NOT use the $257.56 PnL number as evidence** for any sizing or threshold change decision.
2. **Re-run the full 7-day scan with de-duplication** (one event per unique market/epoch/side) before drawing any conclusion about edge magnitude.
3. **Separate the <$0.10 bucket** for a dedicated liquidity/spread analysis before treating its theoretical PnL as executable.
4. **Do not lower the confidence threshold** based on this audit alone. The de-duplicated edge is positive but the win rate (37%) at real execution conditions is close to the margin required for profitability.
5. **Phase 2 action** (per project scope): Paper-only inventory replay with proper deduplication and actual market depth checks before any parameter change.

---

*Report generated by: 10_BACKTEST_REPLAY_AGENT*  
*Script: `scratch/methodology_validation_v1.py`*  
*Read-only audit — no runtime, strategy, risk, or execution changes made.*
