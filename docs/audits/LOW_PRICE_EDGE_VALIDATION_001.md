# LOW_PRICE_EDGE_VALIDATION_001

**Role**: 10_BACKTEST_REPLAY_AGENT + 08_RESEARCH_QUANT_AGENT  
**Mode**: READ ONLY — no code, config, strategy, or execution changes  
**Date**: 2026-06-18  
**Script**: `scratch/low_price_edge_validation_v1.py`  
**Source data**: 7-day decision_log + market_snapshots (2026-06-12 → 2026-06-18)

---

## Objective

Determine whether the apparent profitability of low-price contracts (< $0.10 ask) is a real executable edge or a replay artifact caused by:
- duplicate counting
- settlement approximation
- extreme payout asymmetry
- non-executable fills

---

## Q1 — Deduplication

| Metric | Value |
|---|---|
| raw_events | 1,156 |
| unique_events | **355** |
| duplication_factor | **3.26×** |
| keys_with_dups | 214 |
| max_dups_per_key | 14 |
| median_dups_per_key | 2 |

**Finding**: 87.8% of raw events are duplicates. The realtime loop emits a new decision record every scan cycle (~60s) for the same market/epoch/side while it remains in scope. All downstream PnL numbers in this report use the **355 unique events only**.

---

## Q2 — Price Bucket Distribution (unique events)

| Bucket | Count | % Total | Avg Confidence | Avg EV |
|---|---|---|---|---|
| **<0.05** | **60** | **16.9%** | **0.7863** | **0.2695** |
| 0.05–0.10 | 27 | 7.6% | 0.7060 | 0.2541 |
| 0.10–0.20 | 77 | 21.7% | 0.6782 | 0.2283 |
| 0.20–0.40 | 151 | 42.5% | 0.6042 | 0.1359 |
| >0.40 | 40 | 11.3% | 0.5511 | 0.0694 |

**Key observations:**
- The `<$0.05` bucket has the **highest average confidence (0.786)** and **highest average EV (0.270)** of any bucket — the model is most convicted on the cheapest contracts
- The `0.20–0.40` bucket is the largest by count (42.5%) but carries the lowest conviction per event
- High confidence and EV in low-price events is consistent with strong implied edge — but also consistent with low-price contracts being near-certain losers that the model over-rates

---

## Q3 — Replay Profitability (unique events only)

**Resolved trades**: 322 / 355 (90.7%)  
**Wins**: 118 | **Losses**: 204 | **Win Rate**: **36.65%**

| Notional | Total PnL | Expectancy | Profit Factor |
|---|---|---|---|
| $0.05 | **+$66.98** | +$0.2080/trade | **7.57** |
| $0.10 | **+$133.95** | +$0.4160/trade | **7.57** |

> [!IMPORTANT]
> After correcting the 3.26× duplication error, PnL drops from the original claimed $257.56 to **$66.98** — a **75% reduction**. The profit factor (7.57) remains high, but this is explained by payout asymmetry in the `<$0.05` bucket, not skill-based edge across all candidates.

---

## Q4 — Execution Realism

**Classification criteria:**
- `NON_EXECUTABLE`: entry_price < $0.03, OR spread > 5¢, OR liquidity < $5
- `QUESTIONABLE`: spread > 2¢, OR liquidity < $50, OR seconds_remaining < 30s
- `EXECUTABLE`: all other cases

| Classification | Count | % of Unique |
|---|---|---|
| EXECUTABLE | 324 | 91.3% |
| QUESTIONABLE | 6 | 1.7% |
| NON_EXECUTABLE | **25** | **7.0%** |

**Market microstructure data availability:**

| Field | Available | Avg | Max |
|---|---|---|---|
| Spread | 355/355 (100%) | 0.0102 | 0.0300 |
| Liquidity | 355/355 (100%) | $1,135.37 | — |
| Seconds remaining | 355/355 (100%) | 227.2s | — |

**Per-bucket execution breakdown:**

| Bucket | Count | NON_EXEC | QUEST | EXEC |
|---|---|---|---|---|
| **<0.05** | **60** | **25 (41.7%)** | 0 | **35 (58.3%)** |
| 0.05–0.10 | 27 | 0 | 0 | 27 (100%) |
| 0.10–0.20 | 77 | 0 | 3 | 74 (96.1%) |
| 0.20–0.40 | 151 | 0 | 3 | 148 (98.0%) |
| >0.40 | 40 | 0 | 0 | 40 (100%) |

> [!CAUTION]
> **ALL 25 NON_EXECUTABLE events fall in the `<$0.05` bucket.** These are contracts priced below $0.03 — they have spreads that represent 34–100% of the entry price. The `<$0.05` bucket, which drives 85.1% of total replay PnL, is **41.7% non-executable at the simulation entry price**.

---

## Q5 — Settlement Quality

| Metric | Value |
|---|---|
| unique_events | 355 |
| resolved_events | **322** |
| ambiguous_events | 24 |
| missing_truth (no snapshot) | 0 |
| missing_truth (too early, >180s) | 9 |
| **resolution_rate** | **90.7%** |

**Settlement snapshot timing:**

| Proximity to expiry | Count | % |
|---|---|---|
| <60s before expiry | 260 | **78.8%** |
| 60–120s before expiry | 68 | 20.6% |
| 120–180s before expiry | 2 | 0.6% |

**Settlement methodology:**
```
Proxy truth = yes_bid at nearest snapshot to expiry (< 180s window)
YES  ← yes_bid >= 0.65
NO   ← yes_bid <= 0.35
AMBIGUOUS ← 0.35 < yes_bid < 0.65 (excluded from replay)
```

**Assessment**: Settlement quality is **acceptable**. 78.8% of resolutions are from snapshots within the final 60 seconds, where binary outcomes are almost certain. The 6.1% ambiguity exclusion rate (24 events) is manageable and unlikely to introduce systematic bias.

---

## Q6 — Low-Price Profit Concentration

**Total de-duplicated PnL ($0.05 notional): $66.98**

| Bucket | Count | PnL | % of Total PnL | Win Rate |
|---|---|---|---|---|
| **<0.05** | **60** | **+$57.00** | **85.1%** | **48.33%** |
| 0.05–0.10 | 26 | +$2.89 | 4.3% | 23.08% |
| 0.10–0.20 | 71 | +$5.93 | 8.9% | 33.80% |
| 0.20–0.40 | 131 | +$1.16 | 1.7% | 34.35% |
| >0.40 | 34 | −$0.02 | −0.0% | 41.18% |

**Cumulative PnL concentration:**

| Threshold | PnL | % of Total |
|---|---|---|
| Contracts < $0.05 | $57.00 | **85.1%** |
| Contracts < $0.10 | $59.89 | **89.4%** |
| Contracts < $0.20 | $65.83 | **98.3%** |

**Leverage diagnostic for the `<$0.05` bucket:**

| Metric | Value |
|---|---|
| Events in bucket | 60 |
| Avg entry price | $0.0280 |
| Avg win pnl @ $0.05 notional | **$1.7357** |
| Avg loss | −$0.05 |
| Implied payoff ratio | **34.7 : 1** |
| Breakeven win rate required | **2.80%** |

> [!WARNING]
> The `<$0.05` bucket wins at 48.33% — **17× above the breakeven win rate of 2.80%**. This is why the profit factor is 7.57. The math is technically correct, but the profitability here is a function of **extreme payout leverage**, not of superior signal quality. Any positive win rate above ~3% at a $0.028 avg price will show dramatic PnL. This is the dominant structural concern.

**The `0.05–0.10` sub-bucket is the critical canary**: it shows only **23.08% win rate** and **$2.89 PnL** across 26 trades — dramatically weaker than the `<$0.05` bucket. This collapse in performance at slightly higher prices is inconsistent with a generalizable edge and suggests the `<$0.05` profitability may be partially driven by selection bias or favorable settlement timing.

---

## Q7 — Slippage Stress Test

**Overall (all 322 resolved unique trades, $0.05 notional):**

| Slippage | Total PnL | Profit Factor | Sign |
|---|---|---|---|
| 0¢ | +$66.98 | 7.57 | POSITIVE |
| +1¢ | +$47.42 | 5.65 | POSITIVE |
| +2¢ | +$36.53 | 4.58 | POSITIVE |
| +3¢ | +$29.42 | 3.88 | POSITIVE |

**Per-bucket slippage survival ($0.05 notional):**

| Bucket | 0¢ PnL | +1¢ PnL | +3¢ PnL | Survives 3¢? |
|---|---|---|---|---|
| **<0.05** | **+$57.00** | **+$39.00** | **+$23.43** | **YES** |
| 0.05–0.10 | +$2.89 | +$2.36 | +$1.62 | YES |
| 0.10–0.20 | +$5.93 | +$5.22 | +$4.08 | YES |
| 0.20–0.40 | +$1.16 | +$0.90 | +$0.42 | YES |
| >0.40 | −$0.02 | −$0.06 | −$0.13 | NO |

**Interpretation**: The `<$0.05` bucket survives 3¢ slippage **because the payoff ratio (34.7:1) is so extreme** that slippage barely matters. At $0.028 avg entry price, adding 3¢ of slippage brings the effective entry to $0.058 — still a 16:1 payoff. **Slippage survivability here is a function of leverage, not signal quality.** The `>0.40` bucket correctly fails at 3¢ slippage as expected for fair-odds contracts.

---

## Q8 — Final Classification

**Scoring dimensions:**

| Dimension | Value | Assessment |
|---|---|---|
| De-dup PnL positive | True | ✅ |
| Profit factor (0¢ slip) | 7.57 | ✅ |
| Profit factor (3¢ slip) | 3.88 | ✅ |
| Survives 3¢ slippage | True | ✅ |
| Win rate (de-duped) | 36.65% | ⚠ Below 50% |
| PnL concentrated <$0.10 | 89.4% | ❌ Extreme concentration |
| 41.7% of <$0.05 bucket NON_EXECUTABLE | True | ❌ Execution concern |
| Edge driven by leverage ≠ skill | True | ❌ Structural concern |
| 0.05–0.10 bucket WR collapse (23%) | True | ❌ Generalization concern |

---

## VERDICT

```
EDGE_WEAK
```

### Rationale

The mathematical edge is **technically present** after deduplication and slippage stress testing. The profit factor of 7.57 survives 3 cents of slippage. However:

1. **85.1% of PnL comes from the `<$0.05` bucket** — a price regime where the breakeven win rate is 2.80%. Any strategy with random entry and 3% actual win rate would show a positive profit factor here.

2. **41.7% of `<$0.05` events are classified NON_EXECUTABLE** (entry price < $0.03). The $57.00 PnL driving the overall result includes a significant share of fills that cannot be realized at the simulated price.

3. **The `0.05–0.10` bucket collapses** from 48% WR (`<$0.05`) to 23% WR — well below breakeven for that price tier. If the edge were generalizable, this bucket should perform near or above the `<$0.05` level. The 23% WR is consistent with **adverse selection** at marginally higher prices, not genuine edge.

4. **The payoff structure masks signal quality.** With 34:1 payoff leverage, even a 10% real win rate generates a positive profit factor. The replay cannot distinguish between "strong signal" and "lucky leverage." 

5. **The deduplication correction alone eliminated $190.58 of reported PnL** (from $257.56 to $66.98). The original forensic audit verdict of `SIZER_TOO_CONSERVATIVE` was based on materially overstated evidence.

---

## RECOMMENDED_ACTION

```
INVESTIGATE_EXECUTION_REALISM
```

### What this means

Before any confidence threshold change, sizer parameter adjustment, or low-price tier implementation:

1. **Verify fill rates at sub-$0.05 prices**: Pull actual executed trade log entries from `trade_journal` or `edge_inventory` to determine if any real fills have occurred at prices below $0.05. Count fills vs. attempts.

2. **Quantify the non-executable fraction impact**: Remove the 25 NON_EXECUTABLE `<$0.05` events from the replay and recompute. If PnL drops significantly, the edge is not yet operationally supportable.

3. **Measure real spread at sub-$0.05 prices**: The avg spread of 1.02¢ may understate true execution cost. At $0.028 entry, 1¢ spread = 35.7% of entry price. Confirm what the CLOB actually shows at time of entry.

4. **Run a separate sub-bucket test**: Isolate `$0.03–$0.05` (executable sub-range within <$0.05) and `$0.05–$0.10` and evaluate independently with the same deduplication. If the `$0.05–$0.10` bucket recovers from 23% WR in a longer sample, that changes the picture.

### What this does NOT authorize

- No confidence threshold change
- No sizer parameter change
- No new price tier implementation
- No execution behavior modification
- All investigation is paper/offline only

---

## Final Confirmation

| Item | Status |
|---|---|
| Runtime changed | No |
| Strategy changed | No |
| EV changed | No |
| Risk changed | No |
| Execution changed | No |
| Live trading changed | No |
| Files modified | 0 |

---

*Report generated by: 10_BACKTEST_REPLAY_AGENT + 08_RESEARCH_QUANT_AGENT*  
*Script: `scratch/low_price_edge_validation_v1.py`*  
*Read-only audit — evidence only.*
