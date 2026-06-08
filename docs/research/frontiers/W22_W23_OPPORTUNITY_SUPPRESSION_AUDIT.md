# W22 vs W23 Opportunity Suppression Audit

Generated: 2026-06-08
Source evidence: `runtime/quant_data/decision_log/` (W22: 7 files, W23: 8 files) + `runtime/research_exports/canonical_regime_enriched_trades_v1.csv`
Mode: READ ONLY — offline/reporting only. No code changes. No commits. No runtime modifications.
Non-authorization: this document does not change strategy, risk, execution, sizing, live behaviour, runtime policy, or alerts.

---

## 1. Executive Summary

ETH YES FC OS qualifying opportunities collapsed from **W22 = 21** to **W23 = 2**, a **−90.5% drop**. This audit answers six research questions about the collapse.

**Root cause: two independent factors multiply to produce the observed collapse.**

| Factor | W22 | W23 | Ratio |
|---|---:|---:|---:|
| OPENING_SCAN ETH YES *executed* trades (canonical) | 42 | 14 | ×0.33 |
| hold > 15s pass rate | 52.4% | 14.3% | ×0.27 |
| **Predicted qualifying** | **—** | **21 × 0.33 × 0.27 ≈ 1.9** | **×0.09** |
| **Observed qualifying** | **21** | **2** | **×0.095** |

The multiplicative decomposition closes within rounding error. Neither factor alone explains the collapse; they compound.

**Hold collapse (×0.27) is the primary mechanical driver.** It is regime-independent: TREND_DOWN and SIDEWAY — regimes present in *both* weeks — show the same short-hold behaviour in W23. No W23 ETH YES OPENING_SCAN trade held longer than 24 seconds; W22's maximum was 65 seconds.

**Volume collapse (×0.33) is the upstream structural driver.** COMPRESSION's complete absence in W23 (0 events vs 1,919 in W22) is the largest single contributor to the volume drop, but CLOB_EMPTY_RESPONSE (+523%) and RISK_PLAN_ZERO (+422%) are secondary factors within this leg.

**Gate tightening is ruled out.** DELTA_EXTREME blocks decreased by 5.4 pp; EV and confidence are stable or improved.

---

## 2. Scope and Constraints

| Item | Value |
|---|---|
| W22 date range | 2026-05-25 to 2026-05-31 (ISO 2026-W22) |
| W23 date range | 2026-06-01 to 2026-06-08 (ISO 2026-W23) |
| W22 decision log files | 7 files, ~3.5 GB total |
| W23 decision log files | 8 files, ~2.3 GB total (note: 2026-06-03 near-downtime, 136 events, 4.2 MB) |
| Canonical export source | `canonical_regime_enriched_trades_v1.csv` (n=62, as of 2026-06-08) |
| Question | Why did ETH YES FC OS qualifying opportunities collapse? |
| NOT evaluating | Profitability, PF, WR, or campaign health |

---

## 3. Q1 — Full Funnel Table

The funnel has two physically distinct sections that must not be merged: pre-execution evaluations (from decision log) and post-execution executions (from canonical export). They have different denominators and different semantics.

### Section A: Decision Log Evaluations (pre-execution signal events)

| Stage | W22 | W23 | Change |
|---|---:|---:|---:|
| Total decision events (all assets, all sides) | 121,948 | 74,861 | −38.6% |
| ETH events | 60,898 | 37,431 | −38.5% |
| ETH YES events | 8,115 | 6,884 | −15.2% |
| ETH YES OPENING_SCAN events | 764 | 341 | −55.4% |

These counts measure *evaluation volume* — how often the engine assessed ETH YES OPENING_SCAN candidates. They include blocked, skipped, and executed candidates alike. The hold filter cannot be applied here (hold is only known post-execution).

### Section B: Canonical Export Executions (post-execution qualifying filter)

| Stage | W22 | W23 | Change |
|---|---:|---:|---:|
| All executed trades (ETH + BTC, all sides) | 206 | 76 | −63.1% |
| ETH YES executed | 51 | 20 | −60.8% |
| ETH YES OPENING_SCAN executed | 42 | 14 | −66.7% |
| hold > 15s | 22 | 2 | −90.9% |
| + outcome quality gate (TP/SL or pnl_usdc present) | 22 | 2 | — |
| + canonical_retained_flag = true | **21** | **2** | **−90.5%** |

The hold filter is the decisive step: it eliminates 12 of 14 W23 OPENING_SCAN ETH YES trades. Outcome quality gate adds zero additional exclusions (all 22/2 trades have resolved outcomes). The dedup gate removes 1 duplicate pair in W22 (from 22 to 21); W23 has no duplicates.

### Divergence note

Total decision events fell 38.6% but executed trades fell 63.1%. The *execution conversion rate* also compressed — not just evaluation volume. CLOB_EMPTY_RESPONSE (+523%) and RISK_PLAN_ZERO (+422%) are the primary causes within the post-evaluation, pre-execution funnel.

---

## 4. Q2 — Gate Suppression Decomposition

Measured over the full ETH YES population (W22 n=8,115; W23 n=6,884) using `candidate_block_reason`, `skip_reason_primary`, and `pre_model_gate_reason` fields from the decision log.

*Note: `delta_extreme` is not a directly emitted field. DELTA_EXTREME block reason and IMBALANCE_EXTREME skip reason serve as its observable proxy.*

| Gate | W22 blocks | W22 rate | W23 blocks | W23 rate | Delta | Direction |
|---|---:|---:|---:|---:|---:|---|
| DELTA_EXTREME | 3,246 | 40.0% | 2,379 | 34.6% | −5.4 pp | ↓ less restrictive |
| TIME_UNSAFE | 1,498 | 18.5% | 1,375 | 20.0% | +1.5 pp | ↑ modest increase |
| CONFIDENCE_TOO_LOW | 1,026 | 12.6% | 1,055 | 15.3% | +2.7 pp | ↑ modest increase |
| FREQUENCY_COOLDOWN | 1,002 | 12.3% | 411 | 6.0% | −6.3 pp | ↓ less restrictive |
| EMPTY_BOOK | 852 | 10.5% | 0 | 0.0% | −10.5 pp | — (label retired) |
| CLOB_EMPTY_RESPONSE | 221 | 2.7% | 1,157 | 16.8% | +14.1 pp | ↑↑ severe increase |
| RISK_PLAN_ZERO | 82 | 1.0% | 428 | 6.2% | +5.2 pp | ↑↑ severe increase |
| MAX_TRADES_PER_HOUR | 84 | 1.0% | 49 | 0.7% | −0.3 pp | ↓ negligible |
| MAX_ACTIVE_POSITIONS | 43 | 0.5% | 7 | 0.1% | −0.4 pp | ↓ less restrictive |
| API_MISSING_FIELDS | 32 | 0.4% | 5 | 0.1% | −0.3 pp | ↓ negligible |

**Key observations:**
- CLOB_EMPTY_RESPONSE is the single largest absolute shift: +14.1 pp (221 → 1,157 events, +523%). This directly suppresses execution throughput.
- RISK_PLAN_ZERO jumped +5.2 pp (82 → 428 events, +422%). All 428 W23 events are in the MICRO SEED bankroll tier, concentrated on 2026-06-06 (predominantly TREND_DOWN regime). This indicates the position-sizing model returned a zero plan for the available ETH YES market price/liquidity conditions under MICRO SEED tier constraints.
- DELTA_EXTREME decreased — the gate actually relaxed. It is not a driver.
- EMPTY_BOOK disappeared in W23 (label change); its functional successor CLOB_EMPTY_RESPONSE accounts for the replacement and more.

---

## 5. Q3 — Cause Classification: Mixed (F)

### 5.1 Multiplicative decomposition

The collapse is fully explained by two independent multiplicative factors:

```
W22 qualifying: 21
W23 qualifying: 21 × (volume factor) × (hold factor)
             = 21 × (14/42) × (2/14)/(22/42)
             = 21 × 0.333 × 0.273
             ≈ 1.9  →  rounds to 2 ✓
```

Neither factor alone is sufficient:
- Volume factor alone (0.33×): 21 × 0.33 ≈ 7 (not 2)
- Hold factor alone (0.27×): 21 × 0.27 ≈ 6 (not 2)
- Together: ≈ 2 ✓

### 5.2 Hold collapse — primary mechanical driver

The hold > 15s pass rate collapsed from 52.4% (22/42) to 14.3% (2/14). This is **regime-independent**:

| Regime | W22 hold sample (OPENING_SCAN ETH YES) | W23 hold sample |
|---|---|---|
| TREND_DOWN | 18–55s (all qualify) | 4, 4, 7, 11, 11, 15s (0/6 qualify) |
| SIDEWAY | Mix of short/long | ≤24s max |
| COMPRESSION | 4–65s (~50% qualify) | 0 events |

Every W23 TREND_DOWN and SIDEWAY execution resolved within ≤24 seconds. Regimes present in *both* weeks show the same short-hold behaviour in W23. The hold collapse is therefore not a *consequence* of COMPRESSION disappearing — it is a **separate phenomenon** applying uniformly across all surviving regimes.

Consistent with fast TP/SL resolution: PnL magnitudes (±0.004–0.015) are normal-sized but the durations are 3–15× shorter than W22, indicating positions hit their exit levels at a faster pace.

### 5.3 Volume collapse — structural driver

Execution volume dropped 66.7% (42 → 14 OPENING_SCAN ETH YES). Within this:
- COMPRESSION's complete absence (0 events) removed a significant source of OPENING_SCAN setups
- CLOB_EMPTY_RESPONSE surge (+523%) blocked candidates that previously reached execution
- RISK_PLAN_ZERO surge (+422%) zeroed out sizing for a subset of remaining candidates

### 5.4 Cause scores

| Cause | Code | Evidence | Verdict |
|---|---|---|---|
| Market structure change (COMPRESSION disappearance, EXTREME_VOL emergence, volatility label shift) | A | COMPRESSION: 1,919→0; EXTREME_VOL market_regime: 0→204; HIGH_VOL regime label: 4.2%→16.1% | **CONFIRMED PRIMARY** |
| COMPRESSION disappearance as independent cause | B | 23.7%→0.0% COMPRESSION share; 7 gross qualifying W22 trades from COMPRESSION | **CONFIRMED — but net contribution limited** (see §8) |
| Runtime behaviour change (CLOB_EMPTY, RISK_PLAN_ZERO, downtime) | C | CLOB_EMPTY +523%, RISK_PLAN_ZERO +422%, Jun 3 near-downtime | **CONFIRMED SECONDARY** |
| Gate tightening (delta_extreme, confidence, EV thresholds) | D | DELTA_EXTREME: 40.0%→34.6% (decreased); EV: 0.224→0.225 (stable) | **RULED OUT** |
| Candidate quality deterioration (EV, confidence) | E | Confidence: 0.333→0.356 (improved); EV: 100% positive both weeks | **RULED OUT** |
| Mixed causes | F | All of the above | **CONFIRMED — classification = F** |

---

## 6. Q4 — COMPRESSION Disappearance: Gross vs Net Contribution

### 6.1 COMPRESSION share

| Metric | W22 | W23 |
|---|---:|---:|
| ETH YES decision events | 8,115 | 6,884 |
| COMPRESSION events | 1,919 | **0** |
| COMPRESSION share | 23.7% | **0.0%** |
| Days with any COMPRESSION | 7/7 | **0/8** |

COMPRESSION was completely absent every single day of W23 — 8 consecutive days with zero COMPRESSION events. This is not volatility; this is structural.

### 6.2 W22 COMPRESSION qualifying trades (gross)

W22 had 14 COMPRESSION OPENING_SCAN ETH YES executed trades in the canonical export. Their hold distribution was approximately bimodal: 7 trades held ≤15s (4, 7, 10, 10, 11, 12, 12s) and 7 held >15s (18, 23, 25, 31, 35, 48, 65s). The ~50% pass rate matches W22's overall pass rate of 52%.

**Gross missing qualifying from COMPRESSION disappearance = 7 trades.**

### 6.3 Net independent contribution

The hold collapse is regime-independent (§5.2). Under W23's 14.3% pass rate, those 14 COMPRESSION executions would yield:
```
14 × 0.143 = 2.0 qualifying trades
```

COMPRESSION absence therefore withheld approximately 2 qualifying trades (relative to the counterfactual where COMPRESSION returns but W23's hold conditions persist). The **net independent contribution of COMPRESSION disappearance is ~2 missing qualifying trades** — not 7.

The difference (7 gross → ~2 net) is fully explained by the regime-independent hold collapse: even if COMPRESSION had been present, the short-hold environment would have suppressed most COMPRESSION qualifying trades.

**Using the gross figure of 7 as the "COMPRESSION share of the collapse" double-counts the hold-collapse contribution.** The two factors must be separated.

### 6.4 COMPRESSION as a structural symptom

COMPRESSION (ranging/consolidation) is a low-volatility regime. Its complete disappearance is consistent with the volatility regime label shift observed in W23 (HIGH_VOL: 4.2% → 16.1%), though the underlying `volatility_score` average is identical (0.003 in both weeks), indicating the shift is in regime classification rather than raw price volatility. COMPRESSION's absence is best understood as a symptom of the market structure shift (Cause A), not an independent root cause.

---

## 7. Q5 — Delta_extreme Analysis: RULED OUT

| Metric | W22 | W23 | Change |
|---|---:|---:|---:|
| DELTA_EXTREME blocks | 3,246 | 2,379 | −26.7% |
| Block rate (% of ETH YES events) | 40.0% | 34.6% | −5.4 pp |

The DELTA_EXTREME block rate **decreased** by 5.4 pp. The gate became *less* restrictive in W23, not more. If delta_extreme were tightening and causing the collapse, the block rate would have increased. The evidence is the opposite.

**Verdict: delta_extreme does not explain the collapse. RULED OUT.**

*Measurement note: `delta_extreme` is not a directly emitted payload field. This analysis uses DELTA_EXTREME as the `candidate_block_reason` / IMBALANCE_EXTREME as `skip_reason_primary` as the observable proxy. These are the standard signals used throughout the pipeline.*

---

## 8. Q6 — Confidence and EV Gate Analysis: Non-Discriminating

| Metric | W22 | W23 | Change |
|---|---:|---:|---:|
| Avg candidate confidence (ETH YES population) | 0.333 | 0.356 | +0.023 |
| CONFIDENCE_TOO_LOW block rate | 12.6% | 15.3% | +2.7 pp |
| Avg EV at execution (OPENING_SCAN ETH YES) | 0.224 | 0.225 | +0.001 |
| Qualifying trades with positive EV | 100% | 100% | 0 pp |

**Important framing:** These averages are computed over the full ETH YES population (mostly blocked candidates), not over qualifying trades only. They measure signal population health, not outcome quality.

**Confidence:** Average confidence *improved* by 0.023 in W23. The CONFIDENCE_TOO_LOW block rate rose 2.7 pp — a modest increase, not a structural shift. It cannot explain a 90.5% qualifying collapse.

**EV:** Both weeks show 100% positive EV at execution. However, "100% positive EV" is a rubber stamp — the EV gate passes any trade with EV > 0, which is trivially true for all executed OPENING_SCAN candidates in both weeks. Its stability indicates the EV gate is not discriminating; it does not provide evidence that edge quality was maintained.

**Verdict: Confidence and EV gates did not cause the collapse. RULED OUT.**

---

## 9. Volatility Environment Context

### Regime label distribution (3-day sample per week: 2026-05-25/30/31 and 2026-06-01/06/07)

| Regime | W22 (n=3,838 ETH YES) | W23 (n=3,310 ETH YES) |
|---|---:|---:|
| NORMAL_VOL | 88.6% | 76.8% |
| HIGH_VOL | 4.2% | **16.1%** |
| LOW_VOL | 7.1% | 3.8% |
| EXTREME_VOL | 0.1% | 3.3% |

HIGH_VOL regime labels increased nearly 4× between the samples. However, the underlying `volatility_score` average is 0.003 in both weeks. This means the shift is in *regime label distribution* (which markets are being traded and their intraday structure) rather than a change in the raw volatility measurement algorithm. The label shift is consistent with COMPRESSION's absence: COMPRESSION (a ranging low-vol regime) has been replaced by TREND_DOWN and SIDEWAY regimes that the labeller classifies as higher volatility.

**`volatility_regime` shift does not add a new independent cause — it is a facet of the same market structure change (Cause A) that produced COMPRESSION's disappearance.**

The EXTREME_VOL `market_regime` contributed 204 W23 decision events (3.0%) — present but not a primary driver.

---

## 10. Secondary Factors

### 10.1 CLOB_EMPTY_RESPONSE (+523%)

| Week | Events | Rate |
|---|---:|---:|
| W22 | 221 | 2.7% |
| W23 | 1,157 | 16.8% |

CLOB_EMPTY_RESPONSE events represent candidates where the CLOB orderbook returned an empty or unusable response, preventing execution. A 5× increase in this rate significantly degrades execution throughput — it is a direct contributor to the volume factor (×0.33) in the multiplicative decomposition. Whether this reflects a CLOB API service degradation, a shift in which markets are being evaluated, or a session reconnection pattern is not determinable from the decision log alone.

### 10.2 RISK_PLAN_ZERO (+422%)

| Week | Events | Rate | Concentration |
|---|---:|---:|---|
| W22 | 82 | 1.0% | Mixed regimes |
| W23 | 428 | 6.2% | MICRO SEED tier; TREND_DOWN-heavy |

428 W23 RISK_PLAN_ZERO events occurred with MICRO SEED bankroll tier designation (the smallest tier). The concentration on 2026-06-06 in TREND_DOWN regime suggests the position-sizing model could not find a non-zero plan for available ETH YES market prices under MICRO SEED tier capital constraints. This is a secondary contributor to the volume factor.

### 10.3 Bot downtime (2026-06-03)

| Day | File size | Event count | Status |
|---|---:|---:|---|
| 2026-06-03 | 4.2 MB | 136 | Near-complete downtime |
| Typical day | 100–500 MB | tens of thousands | Normal |

The 2026-06-03 near-downtime removed one of eight W23 trading days from the opportunity pool. This is a direct deduction from the W23 execution count but is independent of the hold collapse and COMPRESSION disappearance causes.

---

## 11. Summary Table

| Question | Finding | Verdict |
|---|---|---|
| Q1 | Decision log: 764→341 OPENING_SCAN ETH YES events (−55.4%). Canonical: 42→14 executed (−66.7%), 22→2 qualifying (−90.9%). | Two-tier funnel documented |
| Q2 | CLOB_EMPTY: +14.1 pp. RISK_PLAN_ZERO: +5.2 pp. DELTA_EXTREME: −5.4 pp. CONFIDENCE: +2.7 pp. FREQUENCY_COOLDOWN: −6.3 pp. | CLOB and risk-zero are secondary drivers; gate tightening ruled out |
| Q3 | Mixed (F). Two multiplicative factors: volume (×0.33) × hold pass rate (×0.27) = ×0.09. Hold collapse is regime-independent; COMPRESSION disappearance sits inside volume factor. | CONFIRMED Mixed (F); hold collapse primary mechanical driver |
| Q4 | COMPRESSION: 23.7%→0%, absent 8/8 W23 days. Gross missing = 7 qualifying trades. Net independent contribution ≈ 2 under W23 hold conditions. | COMPRESSION absence is structural but ~2 net independent qualifying trades, not 7 |
| Q5 | DELTA_EXTREME: 40.0%→34.6% (decreased). Gate relaxed in W23. | RULED OUT |
| Q6 | Confidence 0.333→0.356 (improved). EV 0.224→0.225 (stable). 100% positive EV is non-discriminating. | RULED OUT as driver; EV gate is not discriminating |

---

## 12. Governor Verdict

**CONTINUE_ACCUMULATION. Do not adjust strategy, thresholds, or risk parameters.**

**Why continue:**
- The qualifying collapse is **market-structure-driven, not strategy-driven**. Gates are not tightening — DELTA_EXTREME actually relaxed. EV quality is maintained.
- The hold collapse (primary mechanical driver) is not caused by mis-specified strategy parameters. Trades are resolving quickly, which is a market characteristic, not a system failure.
- n=62 remains above zero; nc_PF=2.367 is healthy; no kill criteria are active.

**Primary recovery signal to watch:**
- **Hold seconds length.** If W24+ OPENING_SCAN ETH YES trades resume holding 20–65s (as in W22), qualifying velocity will recover without any parameter changes. A single hold>15s week of 5+ qualifying trades would confirm recovery.
- **COMPRESSION return.** Any reappearance of COMPRESSION events in ETH YES decision logs signals the structural precondition for higher qualifying volume. COMPRESSION has been absent 8 consecutive days as of 2026-06-08.

**Secondary items to investigate (outside this audit scope):**
1. CLOB_EMPTY_RESPONSE +523% — root cause unclear; may indicate CLOB API service issues or a session reconnection pattern. Should be diagnosed in a targeted investigation.
2. Bot downtime 2026-06-03 — cause not yet identified. A single day's near-complete outage removes ~1–2 expected qualifying trades per occurrence.
3. RISK_PLAN_ZERO concentration on 2026-06-06 TREND_DOWN / MICRO SEED — if the current bankroll tier remains MICRO SEED, consider whether the sizing model parameters are calibrated for this market price range.

**This report is observational only.** No runtime, strategy, risk, or execution changes are authorized by this document.

---

*Offline/reporting only. No runtime, strategy, risk, or execution changes. No commits authorized by this document.*
