# COMPRESSION Regime Root Cause Audit

**Generated:** 2026-05-30  
**Scope:** Offline evidence only — no runtime authority  
**Data:** 147 COMPRESSION trades across 2026-05-20 → 2026-05-30 (trade_journal + decision_log join)  
**Status:** RESEARCH ONLY — no strategy, risk, or execution recommendations

---

## Governor Statement

This report answers two framing questions:

> Is ETH YES actually different? Or is BTC systematically failing?

**Honest answer at current evidence level: cannot statistically confirm either.**

The four-cell chi-square across BTC/ETH × NO/YES yields χ²=5.225 on 3 df, **p=0.154** — does not reject the null hypothesis that all four cells share the same underlying win rate. The apparent difference in outcomes is consistent with sampling variance at n=32–41 per cell.

What IS statistically confirmed (p<0.0001, z=−4.04) is the **overall COMPRESSION win rate of 33.3% being below 50%**. The cell-level narrative should be treated as hypothesis-generating only.

---

## 1. Data Summary

| Dimension | Value |
|-----------|-------|
| Total trade_close events | 1,081 |
| COMPRESSION-regime trades | **147** |
| Decision_log match rate | 147/147 (100%) |
| Observable period | 2026-05-20 → 2026-05-30 |
| Cells analyzed | BTC NO (n=40), BTC YES (n=34), ETH NO (n=41), ETH YES (n=32) |

---

## 2. Core Finding: COMPRESSION Is Not 50/50

| Metric | Value |
|--------|-------|
| COMPRESSION win rate | **33.3%** (49/147) |
| z-score vs 50% | −4.04 |
| One-sided p-value | **2.7 × 10⁻⁵** |
| Gross PnL | **−$0.108** |
| Avg PnL per trade | −$0.001 |

The 33.3% win rate is **highly significant** vs a 50% null (p<0.0001). COMPRESSION is a systematically losing regime for this trading system. This is the primary finding.

The 75% loss-cluster rate documented in earlier audits is a **mathematical consequence** of this 33.3% win rate:

```
P(≥3 consecutive losses | wr=0.333) per sequence ≈ 29.7%
With ~8-10 COMPRESSION bets per session → cluster probability >93%
```

---

## 3. Cell-Level Win Rates (Descriptive — Not Significant)

| Cell | n | W | L | **Win%** | Gross PnL |
|------|---|---|---|---------|-----------|
| ETH YES | 32 | 16 | 16 | **50.0%** | +$0.098 |
| BTC NO | 40 | 12 | 28 | 30.0% | −$0.010 |
| ETH NO | 41 | 12 | 29 | 29.3% | −$0.117 |
| BTC YES | 34 | 9 | 25 | **26.5%** | −$0.079 |

**Statistical caveat:** Four-cell chi-square χ²=5.225, p=0.154. These differences are **not statistically distinguishable** from sampling noise at current n. Required n=90 per cell for 80% power to detect 50% vs 30%.

ETH YES vs all others in a **post-hoc** comparison yields χ²=5.113, p=0.022 — nominally significant but post-hoc and not pre-specified. BTC vs ETH yields χ²=1.646, p=0.196 — not significant.

**Classification: WEAK SIGNAL (pending n≥90 per cell for pre-specified test)**

---

## 4. Field-Level Comparison (Medians Used for Outlier Robustness)

| Field | BTC NO | BTC YES | ETH NO | ETH YES |
|-------|--------|---------|--------|---------|
| **Win rate** | 30.0% | 26.5% | 29.3% | **50.0%** |
| **Avg confidence** | 0.679 | 0.646 | 0.567 | **0.554** |
| **Avg EV** | 0.137 | 0.117 | 0.126 | 0.120 |
| **Avg `true_probability`** | 0.639 | 0.637 | 0.652 | 0.656 |
| **Secs remaining (median)** | 284s | 278s | 288s | 286s |
| **Spread (median)** | 0.010 | 0.010 | 0.010 | 0.010 |
| **ob_snap_age (median)** | 281ms | 242ms | 265ms | 250ms |
| **exec_age (median)** | 281ms | 242ms | 265ms | 250ms |
| **best_bid_size (median)** | 144 | 96 | 31 | 26 |
| **best_ask_size (median)** | 119 | 82 | 35 | 26 |
| **depth_oscillation (mean)** | 0.875 | 0.882 | 0.122 | 0.188 |
| **spread_oscillation (mean)** | 4.65 | 4.65 | 2.66 | 3.25 |
| **liq_depth dominant** | ACCEPTABLE | ACCEPTABLE | **THIN** | **THIN** |
| **ob_state: empty_book %** | 50% | **62%** | 49% | 34% |
| **ob_state: ready %** | 40% | 18% | 44% | **63%** |

### Observations from field data (all hypothesis-level):

**Spread:** Uniform at 0.010 across all cells. Spread is not a differentiator.

**Entry timing (secs remaining):** Nearly identical (275–288s). All cells enter early in the 5-minute epoch (first 12–25 seconds). Not a differentiator.

**True probability:** 0.637–0.656 across all four cells — the model assigns essentially the same probability regardless of asset or side. See §5 for the significance of this.

**Liquidity depth:** ETH cells are THIN-dominant (84–88%); BTC cells are ACCEPTABLE-dominant (76–90%). ETH books are 3–6× shallower than BTC by dollar depth. Despite this (or because of it), ETH YES performs comparably or better — shallower book is not causing losses.

**Orderbook oscillation:** BTC shows 4–7× more depth oscillation (0.875/0.882) than ETH (0.122/0.188). High oscillation means orders are appearing and disappearing rapidly during the evaluation window, making any cached book state less reliable. BTC YES has the highest oscillation and worst outcomes — possible contributor, unconfirmed.

**ob_state "empty_book" %:** BTC YES has the highest empty_book rate at decision time (62%). ETH YES has the lowest (34%). An empty book means the model is evaluating against no live orders — the EV/confidence calculation is based on stale or absent data. The ob_state distribution is directionally consistent with the win rate ordering (ETH YES cleanest book, BTC YES dirtiest book).

**ob_snap_age:** Medians are similar (242–281ms across cells). The mean for BTC YES is inflated to 586ms due to extreme outliers (max=10,641ms), but the median is 242ms. The outliers warrant attention but do not establish a causal pattern at these n values.

---

## 5. Model Calibration: The Robust Finding

This is the most statistically solid finding from the audit and does not depend on cell-level significance.

### 5a. True Probability vs Actual Outcome

| Cell | `true_p` (model) | Actual win rate | Calibration gap |
|------|-----------------|-----------------|-----------------|
| ETH YES | 0.656 | 0.500 | **−0.156** |
| BTC NO | 0.639 | 0.300 | −0.339 |
| ETH NO | 0.652 | 0.293 | −0.359 |
| BTC YES | 0.637 | 0.265 | **−0.372** |

The model assigns ~64% win probability to all four cells simultaneously, yet outcomes range from 26.5% to 50.0%. **The model cannot distinguish the cells from each other.** This 14–37 point calibration gap is the structural cause of the 33.3% overall COMPRESSION win rate.

### 5b. Win vs Loss True Probability Separation

| Cell | `true_p` (wins) | `true_p` (losses) | Separation |
|------|----------------|-------------------|-----------|
| BTC NO | 0.636 | 0.640 | −0.004 |
| BTC YES | 0.630 | 0.640 | −0.010 |
| ETH NO | 0.658 | 0.649 | +0.009 |
| ETH YES | 0.654 | 0.658 | −0.004 |

**The model's `true_probability` output separates winning from losing trades by ≤0.010 in all cells.** Effective within-cell discriminating power: zero. The model cannot tell a winning COMPRESSION trade from a losing one.

### 5c. Confidence vs Outcome (Inverse Relationship)

| Confidence band | n | Win% |
|----------------|---|------|
| < 0.65 | 99 | **37.4%** |
| 0.65–0.70 | 3 | 33.3% |
| 0.70–0.75 | 30 | **26.7%** |
| > 0.75 | 15 | **20.0%** |

**Classification: VERIFIED (n=147, monotonic across all bands)**

Higher model confidence in COMPRESSION correlates with worse outcomes. The model's highest-confidence COMPRESSION signals perform at a 20% win rate. This inverse relationship is observed across all four EV bands for NO-side and is directionally consistent for YES-side.

The inverse confidence–outcome relationship and the near-zero `true_p` discriminating power are consistent with a single underlying cause: **the probability model has not learned that COMPRESSION is a low-signal regime, and its outputs in COMPRESSION are not predictive of actual binary market resolutions.**

---

## 6. Why COMPRESSION Win Rate Is ~33%, Not ~50%

Based on the aggregate evidence (not any single statistically confirmed cell-level finding), the most plausible structural cause is:

### Primary: Systematic model miscalibration in COMPRESSION

The model generates probability and confidence estimates for COMPRESSION markets using the same signal pipeline as non-COMPRESSION markets. However:

1. COMPRESSION markets have near-50/50 resolution probability (neither YES nor NO has a systematic edge)
2. The model's signals (RSI, EMA gap, momentum, VPIN, etc.) all capture short-term directional movement
3. In COMPRESSION, these signals are noisy and oscillating — they briefly "see" a NO or YES edge that evaporates before resolution
4. The model assigns 63–66% win probability, but actual resolution is ~33% (for cells with confirmed biases) to 50% (ETH YES)
5. Higher confidence signals in COMPRESSION indicate stronger apparent signal in the noise — but noise has no predictive value

### Secondary (hypothesis): BTC orderbook instability in COMPRESSION

BTC shows 4–7× more depth oscillation than ETH in COMPRESSION (0.875 vs 0.122). This means:
- The best bid/ask sizes are changing rapidly during evaluation
- The EV calculation is based on a snapshot of an unstable book
- The fill at "entry price" may not match the evaluation price

BTC YES additionally shows the highest empty_book rate (62%) — decisions made against no live orderbook. This is directionally consistent with BTC YES's worse outcomes, but not statistically confirmed at current n.

### Why ETH YES performs at ~50% (hypothesis, not confirmed)

ETH YES has the combination of:
- Cleanest orderbook (63% "ready" state)
- Lowest depth oscillation (0.188)
- Lowest confidence (0.554 — fewer signals triggering through the noise filter)
- Shallowest book (27 USD depth) but most stable

If the model's confidence threshold acts as a noise filter, lower confidence on ETH YES means only the clearest signals pass — and those may correlate better with actual resolution even in COMPRESSION. This is plausible but unconfirmed.

---

## 7. What Each Regime Comparison Shows

| Regime × Side | n | Win% |
|--------------|---|------|
| **COMPRESSION NO** | 81 | **29.6%** |
| SIDEWAY NO | 61 | 41.0% |
| TREND_UP NO | 41 | 34.1% |
| TREND_DOWN NO | 37 | 43.2% |
| **COMPRESSION YES** | 66 | **37.9%** |
| TREND_UP YES | 25 | 44.0% |
| TREND_DOWN YES | 38 | 44.7% |
| SIDEWAY YES | 36 | 36.1% |

COMPRESSION NO is the worst-performing regime×side across all observed combinations. Every other regime's NO-side beats COMPRESSION NO by 4.5–13.6 points. COMPRESSION YES is near the bottom of YES-side performance.

---

## 8. Path Truth Evidence

| Metric | All trades |
|--------|-----------|
| Total path_truth checkpoints | 280 |
| `adverse_from_entry=True` | 154 (55%) |
| `favorable_from_entry=True` | 114 (41%) |

55% of held positions move adversely from entry — consistent with the 33% win rate (positions that move adversely tend to close at loss). Regime-specific path_truth join is not yet complete; this is aggregate.

---

## 9. Summary of Findings with Classifications

| Finding | Classification | Basis |
|---------|---------------|-------|
| COMPRESSION win rate = 33.3% (vs 50%) | **VERIFIED** | z=−4.04, p<0.0001, n=147 |
| Model `true_p` cannot discriminate W vs L (≤0.01 separation) | **VERIFIED** | n=147, all cells consistent |
| Higher confidence → worse outcomes in COMPRESSION | **VERIFIED** | Monotonic across 4 confidence bands |
| ETH YES outperforms rest | **WEAK SIGNAL** | χ²=5.1, p=0.022 but post-hoc; n=32 insufficient |
| BTC vs ETH win rate differs | **NOT SUPPORTED** | χ²=1.6, p=0.196 |
| All four cells share same underlying win rate | **CANNOT REJECT** | 4-cell χ²=5.2, p=0.154 |
| BTC orderbook more unstable (depth_osc 0.875 vs 0.122) | **OBSERVED** | Directional, unconfirmed causal link |
| BTC YES empty_book 62% vs ETH YES 34% | **OBSERVED** | Directional; causal link unconfirmed |
| COMPRESSION is worst-performing regime for NO-side | **OBSERVED** | Consistent across all other regimes |
| 75% cluster rate is mathematical output of 33% win rate | **VERIFIED** | Binomial calculation, not separate phenomenon |

---

## 10. Required Evidence to Advance Any Cell-Level Claim

| Target comparison | Current n | Required n | Additional needed |
|------------------|-----------|-----------|------------------|
| ETH YES 50% vs rest 29% | 32 vs 115 | **90 vs 90** | ~58 more ETH YES trades |
| BTC vs ETH overall | 74 vs 73 | ~70 per cell | Near threshold |
| BTC NO 30% vs 50% null | 40 | **90** | ~50 more BTC NO trades |
| BTC YES 26.5% vs 50% null | 34 | **90** | ~56 more BTC YES trades |

At the current entry rate (~10 COMPRESSION trades per session), reaching n=90 per cell requires approximately **5–6 weeks of additional data collection** before any cell-level claim can be statistically promoted.

---

## 11. Recommended Next Research Steps

1. **Primary:** Allow evidence accumulation to n=90 per cell. Do not change any thresholds, model weights, or entry logic based on current data.

2. **Regime calibration study:** Query the decision_log for `market_regime=COMPRESSION` across all non-trade events to understand: how frequently the bot evaluates (but skips) COMPRESSION markets, and what the confidence distribution looks like for skipped events vs executed events.

3. **Pre-register the ETH YES hypothesis:** Before the next audit, explicitly pre-register the test: "ETH YES COMPRESSION win rate > all-other-cells COMPRESSION win rate at p<0.05, two-sided." Apply this test once n≥90 per cell.

4. **BTC orderbook stability:** Correlate `depth_oscillation_count` and `ob_state` distribution with individual trade outcomes within BTC COMPRESSION. Currently n=40 (BTC NO) and n=34 (BTC YES) — not sufficient for cell-internal regression, but the trend should be tracked.

5. **Path truth regime join:** Join `path_truth` checkpoints to regime classification at entry. This gives post-entry price path data separated by regime, which would confirm or refute whether COMPRESSION produces systematically adverse price moves.

---

## Guardrails

- This report is offline evidence only and does not authorize runtime decisions, strategy changes, risk parameter changes, EV threshold changes, confidence threshold changes, entry logic changes, or model changes.
- All cell-level findings are classified as WEAK SIGNAL or OBSERVED pending n≥90 per cell.
- The only VERIFIED findings are regime-level (COMPRESSION ≠ 50%) and model calibration (true_p zero discriminating power).
- Do not use this report to suppress BTC trades, boost ETH YES priority, or apply regime-conditioned filters.
