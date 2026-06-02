# Thin Liquidity Gate Separation Audit
# Polymarket-Adaptive-Quant-Engine-v.1

**Audit Date:** 2026-06-02
**Mode:** READ_ONLY — no code changes, no runtime mutation
**Source run:** `20260527T110608Z_26764_9d379e2c` (2026-05-27, 12-hour session)
**Prior audits:** delta_extreme_deep_dive_audit.md | closeness_factor_sensitivity_probe.md | outer_clamp_sensitivity_probe.md
**Formula studied:** Separation of thin-liquidity from `quality_factor` in `estimate_micro_delta`
**Current formula:** `quality_factor += 0.20 if liq < 100 USDC` (embedded)
**Proposed separation:** Remove liq from `quality_factor`; add standalone `liq >= threshold` admission gate

---

## Executive Outputs

```
thin_liquidity_thresholds_tested:  [50, 75, 100, 150, 200, 300] USDC (L1 top-of-book)

thin_liquidity_row_count:   1900  (liq < 100 USDC, L1 bid+ask combined)
thin_liquidity_share:       57.1% of Mechanism B rows (3,326 total)

Liquidity baseline:
  min=0.2 USDC  max=8227.7 USDC  mean=199.2  median=76.4 USDC

Thin-liq-only EXTREME rows at OC=4.0 (current):
  count: 721 (21.7% of Mechanism B)
  These rows are EXTREME SOLELY because thin-liq contribution
  pushed quality_factor from 1.0 to 1.20.
  median liq=39.2 USDC  mean secs=211  80.9% actually liq<100

oc35_rows_after_liquidity_gate:   (separated formula, OC=3.5)
  liq>=0   (no gate): 376 meaningful
  liq>=50:            301 meaningful
  liq>=75:            268 meaningful
  liq>=100:           245 meaningful  <-- RECOMMENDED
  liq>=150:           211 meaningful
  liq>=200:           185 meaningful
  liq>=300:           140 meaningful

oc30_rows_after_liquidity_gate:   (separated formula, OC=3.0)
  liq>=0   (no gate): 732 meaningful
  liq>=50:            619 meaningful
  liq>=75:            565 meaningful
  liq>=100:           523 meaningful  (near-identical to embedded OC=3.0 = 521)
  liq>=150:           455 meaningful
  liq>=200:           393 meaningful
  liq>=300:           321 meaningful

oc25_rows_after_liquidity_gate:   (separated formula, OC=2.5)
  liq>=0   (no gate): 922 meaningful
  liq>=50:            791 meaningful
  liq>=75:            723 meaningful
  liq>=100:           676 meaningful
  liq>=150:           593 meaningful
  liq>=200:           517 meaningful
  liq>=300:           415 meaningful

ev_distribution_after_gate:       (OC=3.5 + separated + liq>=100, n=245)
  <0.10:  34 (13.9%)
  0.10-0.15: 34 (13.9%)
  0.15-0.20: 31 (12.7%)
  0.20-0.30: 103 (42.0%)  <- dominant bucket
  0.30-0.40: 43 (17.6%)
  mean=0.2164  max=0.3621

confidence_distribution_after_gate:  (OC=3.5 + separated + liq>=100)
  0.54-0.60: 79 (32.2%)
  0.60-0.65: 67 (27.3%)
  0.65-0.70: 58 (23.7%)
  >=0.70:    41 (16.7%)
  mean=0.6357  min=0.5402  max=0.7582

time_remaining_distribution_after_gate:  (OC=3.5 + separated + liq>=100)
  91-120s:  0    (0.0%)
  121-150s: 70  (28.6%)
  151-180s: 120 (49.0%)
  181-240s: 46  (18.8%)
  >240s:     9   (3.7%)
  mean=170s  min=131s  max=279s

recommended_liquidity_threshold: 100 USDC (L1 top-of-book bid+ask combined)
  Rationale: matches existing formula boundary; cleanly separates
  thin (median 33.8 USDC) from adequate orderbooks; works with
  $5-$10 micro-survival entry sizes

recommended_next_audit:
  liquidity_gate_outcome_validation — for the 117 rows unique to the
  separated approach, verify whether path_truth checkpoints exist for
  any comparable entries to establish whether these higher-liquidity
  OC=3.5 entries produce better outcomes than the thin-liq rows they replace
```

---

## 1. Current Formula: Thin Liquidity Embedded in Quality Factor

### How it works today

```python
# estimate_micro_delta() — quality_factor computation
quality_factor = 1.0
if spread >= 0.08:    quality_factor += 0.20   # wide spread penalty
elif spread >= 0.04:  quality_factor += 0.10
if liquidity < 100.0: quality_factor += 0.20   # thin liquidity embedded here
elif liquidity < 500.0: quality_factor += 0.10  # medium liquidity embedded here

delta_score = closeness_factor * time_factor * vol_factor * vel_factor * quality_factor
```

Thin liquidity (`liq < 100 USDC`) adds 0.20 to `quality_factor`, which multiplies directly into `delta_score`. This means thin orderbooks amplify the delta score by 20%, pushing borderline cases from HIGH into EXTREME.

### Why the embedding is problematic

The quality_factor is designed to capture "market quality risk" — but by multiplying it into delta_score, thin liquidity acts like a **price-risk amplifier** rather than an **execution gating condition**. The result:

- A row with closeness=4.0, time_factor=1.2, vol=0.755, vel=1.0 and **normal liq (qf=1.0)**:
  `score = 4.0 × 1.2 × 0.755 = 3.62` → **HIGH** (would be admissible)

- The **same row** with thin liq (qf=1.20):
  `score = 4.0 × 1.2 × 0.755 × 1.20 = 4.34` → **EXTREME** (blocked)

The thin-liquidity embedding is turning **execution risk into price-risk EXTREME classification**, blocking entries that have perfectly normal price dynamics.

---

## 2. Thin Liquidity Baseline

| Threshold | Rows below | % of Mechanism B | Interpretation |
|---|---:|---:|---|
| liq < 50 USDC | 1,286 | 38.7% | Extremely thin — $50 total depth |
| liq < 75 USDC | 1,647 | 49.5% | Very thin |
| liq < 100 USDC | 1,900 | 57.1% | Current formula thin boundary |
| liq < 150 USDC | 2,230 | 67.0% | Still thin for $10 entries |
| liq < 200 USDC | 2,439 | 73.3% | Moderate depth |
| liq < 300 USDC | 2,702 | 81.2% | Adequate for small entries |

**Median L1 depth: 76.4 USDC** — more than half of all Mechanism B evaluations occur when bid+ask depth is below the existing formula's thin threshold of 100 USDC. This reflects the Polymarket 5-minute market structure: orderbooks open thin and deepen as the window progresses toward close.

---

## 3. Thin-Liq-Only EXTREME Rows (OC=4.0 Baseline)

With the current outer clamp at 4.0, **721 rows (21.7%) are EXTREME solely because thin-liquidity amplification pushed their score above 4.0**. Without the thin-liq quality_factor contribution, these same rows would score ≤ 4.0.

| Metric | Thin-liq-only EXTREME group (721 rows) |
|---|---|
| Count | 721 (21.7% of Mechanism B) |
| Liq median | 39.2 USDC |
| Liq actually < 100 USDC | 583 (80.9%) |
| Liq 100–500 USDC (medium) | 138 (19.1%) |
| Seconds remaining mean | 211 |
| Seconds remaining min/max | 99 / 296 |

**80.9% of these rows are genuinely thin (< 100 USDC)**. The remaining 19.1% have medium liquidity (100–500 USDC, contributing +0.10 to qf) but were still pushed to EXTREME by that contribution.

**Key finding:** The majority of thin-liq-only EXTREME rows have very thin books (median 39.2 USDC) with mean secs=211 — **mid-window evaluations where the market is active but thin**. These are reasonable candidates to block via a standalone liquidity gate rather than via delta_score amplification.

---

## 4. The Proposed Separation

### Separated approach definition

**Step 1 — Remove liquidity from quality_factor:**
```python
quality_factor_separated = 1.0
if spread >= 0.08:   quality_factor_separated += 0.20   # keep spread
elif spread >= 0.04: quality_factor_separated += 0.10
# liquidity contribution REMOVED
delta_score_separated = closeness_factor * time_factor * vol_factor
                       * vel_factor * quality_factor_separated
```

**Step 2 — Standalone liquidity admission gate:**
```python
liquidity_ok = (top_bid_depth + top_ask_depth) >= LIQUIDITY_THRESHOLD
# Block entry if not liquidity_ok — regardless of delta score
```

### EXTREME threshold shift

Removing liq from quality_factor changes the EXTREME threshold (with closeness=OUTER_CLAMP):

| Formula | EXTREME when (normal spread) | EXTREME when (wide spread) |
|---|---|---|
| Current (embedded, liq thin, qf=1.20) | t < 246s (at OC=4.0) | t < 206s |
| Separated (no liq in qf, qf=1.0) | t < 171s (at OC=4.0) | t < 145s |
| Separated at OC=3.5 | t < 131s | t < 110s |
| Separated at OC=3.0 | t < 96s | t < 80s |

For thin-liq markets at OC=4.0:
- **Current:** EXTREME zone starts at 246s remaining (after only 54s of each window)
- **Separated:** EXTREME zone starts at 171s remaining (after 129s of each window)
- **Gain:** 75 additional seconds of potential entry window per cycle for thin-liq markets

---

## 5. Full Compound Sensitivity Table

Meaningful rows = **exits EXTREME (separated) AND liq >= threshold AND EV > 0 AND conf >= 0.54**

| OC \ liq gate | no gate | >=50 | >=75 | >=100 | >=150 | >=200 | >=300 |
|---|---|---|---|---|---|---|---|
| **4.0** | 70 | 32 | 17 | **11** | 6 | 3 | 2 |
| **3.5** | 376 | 301 | 268 | **245** | 211 | 185 | 140 |
| **3.0** | 732 | 619 | 565 | **523** | 455 | 393 | 321 |
| **2.5** | 922 | 791 | 723 | **676** | 593 | 517 | 415 |

**For comparison — embedded formula (prior probe):**

| OC | Meaningful (embedded, no separate liq gate) |
|---|---|
| 4.0 | 0 |
| 3.5 | 159 |
| 3.0 | 521 |
| 2.5 | 854 |

### Key comparison: OC=3.5

| Approach | Meaningful rows | Min secs | Median liq | Mean EV |
|---|---|---|---|---|
| Embedded OC=3.5 (prior probe) | 159 | 134 | 417.8 USDC | 0.208 |
| **Separated OC=3.5 + liq>=100** | **245** | **131** | **346.3 USDC** | **0.216** |
| Delta | +86 (+54%) | -3s | -72 USDC | +0.008 |

The separation at OC=3.5 with liq≥100 yields **54% more meaningful rows** than the embedded formula, with comparable timing safety (min secs=131 vs 134) and slightly lower median liquidity (346 vs 418 USDC).

### Key comparison: OC=3.0

| Approach | Meaningful rows |
|---|---|
| Embedded OC=3.0 | 521 |
| Separated OC=3.0 + liq>=100 | 523 |

**Near-identical results at OC=3.0.** The separation adds minimal value at this level because OC=3.0 already does the heavy lifting: it reduces closeness from 4.0 to 3.0, which on its own collapses most EXTREME blocks. The thin-liq contribution (+0.20 to qf) is less able to push sub-4.0 scores over 4.0 when the closeness is already capped at 3.0.

---

## 6. The Row Exchange at OC=3.5

The separation at OC=3.5 trades quality:

### Lost (31 rows): in embedded OC=3.5, blocked by liq>=100 gate

These rows were passing under the embedded formula (score_embedded ≤ 4.0) but would be blocked by a standalone liq>=100 gate:

| Metric | Value |
|---|---|
| Count | 31 (all ETH) |
| Liquidity | ALL < 100 USDC; median 33.8 USDC, mean 35.3 USDC |
| EV mean | **0.1514** (lowest of any group) |
| Confidence mean | 0.5723 |
| Seconds remaining mean | 214 (mid-window) |
| Asset | ETH 100%, BTC 0% |
| Time bucket | mid_window 87%, early_window 13% |

**These 31 rows represent the worst trade of the embedded formula:** thin-liquidity ETH entries with low EV that were admitted through the embedded formula because the thin-liq quality_factor amplification happened to keep their scores below 4.0 at OC=3.5.

### Gained (117 rows): in separated+liq>=100, not in embedded OC=3.5

These rows were blocked under the embedded formula (score_embedded > 4.0) but exit EXTREME under the separated formula and pass liq≥100:

| Metric | Value |
|---|---|
| Count | 117 |
| Liquidity | ALL >= 100 USDC; median 243.6 USDC, mean 273.0 USDC |
| EV mean | **0.2105** (39% higher than lost rows) |
| Confidence mean | 0.6308 |
| Seconds remaining mean | 167 (mid-window) |
| Asset | BTC 88.0%, ETH 12.0% |
| Time bucket | mid_window 56%, late_window 39% |
| Score under separated formula | 3.637–3.999, mean 3.813 |

**Why these rows were blocked under the embedded formula:** They have liquidity in the 100–500 USDC range, contributing +0.10 to `quality_factor`. This pushed their embedded score from ~3.7–3.8 (HIGH) to ~4.1–4.2 (EXTREME). Under the separated formula, qf returns to 1.0 (spread-only) and their score drops back to 3.7–3.8 → HIGH.

**The embedded formula incorrectly penalised medium-liquidity (100–500 USDC) rows** by treating them similarly to thin-liquidity rows. The separation correctly distinguishes them.

---

## 7. Recommended Scenario: OC=3.5 + Separated + liq>=100

### Full profile (245 meaningful rows)

| Metric | Value |
|---|---|
| **Count** | **245** |
| **EV mean** | **0.2164** |
| EV max | 0.3621 |
| EV 0.20–0.30 | 103/245 (42.0%) — dominant bucket |
| Confidence mean | 0.6357 |
| Confidence 0.54–0.60 | 79 (32.2%) |
| Confidence >=0.70 | 41 (16.7%) |
| Secs remaining mean | **170** |
| Secs remaining min | **131** (41s above timing gate) |
| Secs remaining max | 279 |
| 121–150s | 70 (28.6%) |
| 151–180s | 120 (49.0%) — majority |
| 181–240s | 46 (18.8%) |
| Liquidity median | **346.3 USDC** |
| Liquidity mean | 454.0 USDC |
| Thin (<100 USDC) | **0 (blocked by gate)** |
| Liq 100–200 USDC | 60 (24.5%) |
| Asset BTC | 221 (90.2%) |
| Asset ETH | 24 (9.8%) |
| Lifecycle ACTIVE_INV_TRADING | 241 (98.4%) |
| Score range (separated OC=3.5) | 3.186–3.999, mean 3.737 |
| Score 3.5–3.8 | 143 (58.4%) |
| Score 3.8–4.0 | 96 (39.2%) |

### Comparison to all prior "best" candidates

| Approach | Meaningful | Min secs | Median liq | Mean EV | Thin liq |
|---|---|---|---|---|---|
| Embedded OC=3.5 (Batch A) | 159 | 134 | 418 USDC | 0.208 | 19.5% |
| **Sep OC=3.5 + liq>=100** | **245** | **131** | **346 USDC** | **0.216** | **0%** |
| Embedded OC=3.0 | 521 | 99 | 320 USDC | 0.221 | 20.0% |
| Sep OC=3.0 + liq>=100 | 523 | similar | similar | similar | lower |

The recommended scenario produces **86 more meaningful rows** than the embedded OC=3.5 benchmark, with comparable timing safety and zero thin-liquidity rows admitted. The slight decrease in median liquidity (346 vs 418 USDC) is a reasonable trade for the 54% yield improvement.

---

## 8. Why liq>=100 USDC Is the Recommended Threshold

### Threshold analysis for OC=3.5 + separated

| liq threshold | Meaningful rows | Rows lost vs no-gate | % lost |
|---|---|---|---|
| no gate | 376 | — | — |
| >=50 USDC | 301 | 75 | 20.0% |
| >=75 USDC | 268 | 33 | 8.8% |
| **>=100 USDC** | **245** | **56** | **14.9%** |
| >=150 USDC | 211 | 34 | 13.9% |
| >=200 USDC | 185 | 26 | 12.4% |
| >=300 USDC | 140 | 45 | 24.3% |

### Rationale for 100 USDC

**1. Formula alignment.** The existing formula already uses 100 USDC as the thin-liquidity boundary (`if liq < 100: qf += 0.20`). A standalone gate at 100 USDC is a natural translation of the same threshold into explicit gate form.

**2. Execution adequacy.** For a $5–$10 entry (typical micro-survival position at 0.25% × $10 = $0.025, rescued to min $0.05 by micro-survival path):
- 100 USDC L1 depth is sufficient for $0.05–$0.10 fills at normal market conditions
- The min_fillable_size_usd field in decision logs typically shows $50–$70 minimum fill threshold, well covered by 100 USDC depth

**3. Quality step at 100 USDC.** The rows blocked between no-gate and >=100 (131 rows) are genuinely thin. These were the 'lost group' in the embedded formula: thin-liq rows being incorrectly processed due to formula interaction.

**4. No over-restriction.** Thresholds ≥ 150 USDC begin cutting into otherwise-healthy entries. The 34 rows lost between >=100 and >=150 have adequate liquidity (100–150 USDC) that should be sufficient for the position sizes involved.

---

## 9. Risk Notes

### Risk 1 — Min secs=131 is 41 seconds above timing gate

The recommended scenario (OC=3.5 + sep + liq>=100) has a minimum time_remaining of 131 seconds. This provides only a 41-second buffer above the 90s hard timing gate. In the worst case, a candidate entering at 131s with a delayed evaluation or adverse fill could be caught by the exit sequence. The mean (170s) is healthier, but the min warrants monitoring.

### Risk 2 — Score concentration at 3.5–4.0 (HIGH)

97.6% of the 245 rows have separated scores between 3.5 and 4.0 — just below the EXTREME threshold. These rows are structurally fragile: any increase in volatility, velocity, or spread during evaluation could shift their score to EXTREME. **Under real runtime conditions, borderline rows may oscillate in and out of EXTREME classification** cycle-to-cycle.

### Risk 3 — The 117 gained rows are "newly visible," not validated

The 117 rows unique to the separated approach (in sep+liq>=100, not in embedded OC=3.5) have never been tested or observed under live entry conditions. Their mean EV of 0.211 and median liq of 243.6 USDC are promising, but:
- No path_truth checkpoints exist for these specific rows
- No replay evidence exists for entries under separated-formula conditions
- Confidence is model-derived, not validated against OOS data

### Risk 4 — Quality factor still includes spread

The separated formula retains spread in quality_factor (+0.20 for spread ≥ 0.08). Rows with wide spreads still have elevated delta scores. Spread is a legitimate risk amplifier for new entries and its retention in quality_factor is appropriate. But it means the separation is **partial**: the formula becomes `delta_score = closeness × time × vol × vel × spread_qf_only`, making spread-affected rows harder to compare across scenarios.

### Risk 5 — OC=3.0 + separated is indistinguishable from embedded OC=3.0

Separated OC=3.0 + liq>=100 = 523 rows. Embedded OC=3.0 = 521 rows. The two approaches converge at this outer clamp level. If the operator's goal is to adopt the separated approach for OC=3.0, the result is nearly identical to simply using embedded OC=3.0 with a post-hoc liquidity filter. This removes one justification for the separation complexity at OC=3.0.

### Risk 6 — L1 depth may not reflect fill depth

The liquidity gate uses L1 top-of-book depth (`top_bid_depth + top_ask_depth`). For larger entries, L2/L3 depth is more relevant. However, for micro-survival entry sizes ($0.05–$0.25), L1 is the operative fill depth. The `total_bid_depth_l1_l3` field is available if a multi-level depth gate is needed.

---

## 10. Recommended Liquidity Threshold and Next Audit

### Recommended threshold

```
recommended_liquidity_threshold: 100 USDC (L1 top-of-book, bid+ask combined)

Applied as a standalone pre-entry gate, separate from delta_score:
  liquidity_ok = (top_bid_depth + top_ask_depth) >= 100 USDC
  if not liquidity_ok: skip (reason: "liquidity_below_gate")
```

This threshold:
- Matches the existing formula classification boundary
- Admits 245 meaningful rows at OC=3.5 (vs 159 embedded)
- Blocks all 31 thin-liq ETH rows that embedded OC=3.5 was incorrectly admitting
- Captures 117 medium-liquidity BTC rows that embedded OC=3.5 was incorrectly blocking

### Recommended next audit

```
recommended_next_audit: liquidity_gate_outcome_validation

GOAL:
  Validate whether the 117 rows uniquely admitted by the separated approach
  (OC=3.5 + separated + liq>=100, not in embedded OC=3.5) represent genuine
  improvement or introduce new risks.

SPECIFIC QUESTIONS:
  1. For any historical entries logged in path_truth near the profile of
     these 117 rows (BTC, mid-window, liq 100-300 USDC, secs 131-180),
     what were the observed outcomes (favorable vs adverse from entry)?
  2. Do the 117 rows have significantly better realized outcomes than the
     31 thin-liq ETH rows they replace? (requires path_truth checkpoint data)
  3. Is the 100 USDC L1 gate sufficient for actual fill quality, or does
     L3 depth need to be incorporated (total_bid_depth_l1_l3)?
  4. What is the min_fillable_size_usd distribution for the 117 rows
     vs the 31 lost rows?

METHOD:
  Read-only join of decision log and path_truth checkpoints.
  No replay execution. No live order placement.
  Operator review required before any formula modification.

SAFETY:
  Read-only. No code change. No parameter change.
  No outcome conclusions from this probe authorize trading.
```

---

## Appendix A — Separation Comparison Table

| Feature | Embedded formula | Separated formula |
|---|---|---|
| Thin-liq effect | Multiplies delta_score by 1.20 | No effect on delta_score |
| Medium-liq effect | Multiplies delta_score by 1.10 | No effect on delta_score |
| Spread effect | Multiplies delta_score by 1.10–1.20 | Same — retained |
| Thin-liq blocking mechanism | EXTREME delta classification | Explicit admission gate |
| Blocking reason in log | `delta_extreme` | New: `liquidity_below_gate` |
| Borderline thin rows | Some admitted (score ≤ 4.0 despite thin liq) | All blocked at gate |
| Medium-liq rows | Some blocked (score > 4.0 due to +0.10) | Admitted (score drops below 4.0) |
| OC=3.5 meaningful rows | 159 | 245 (+54%) |
| OC=3.0 meaningful rows | 521 | 523 (+0.4%) |
| Row quality trade (OC=3.5) | 31 thin-liq ETH (mean EV 0.151) | 117 medium-liq BTC (mean EV 0.211) |

---

## Appendix B — Liquidity Distribution of Key Groups

| Group | n | Median | Mean | <100 | 100-200 | 200-500 | >500 |
|---|---|---|---|---|---|---|---|
| All Mechanism B | 3326 | 76.4 | 199.2 | 57.1% | 9.4% | 13.6% | 19.9% |
| Thin-liq-only EXTREME (OC=4.0) | 721 | 39.2 | 73.1 | 80.9% | 11.8% | 5.0% | 2.4% |
| Embedded OC=3.5 meaningful | 159 | 417.8 | 505.5 | 19.5% | 7.5% | 18.2% | 54.7% |
| Separated OC=3.5 + liq>=100 | 245 | 346.3 | 454.0 | 0% | 24.5% | 28.6% | 46.9% |
| Lost (in emb, not sep) | 31 | 33.8 | 35.3 | 100% | 0% | 0% | 0% |
| Gained (in sep, not emb) | 117 | 243.6 | 273.0 | 0% | 45.3% | 36.8% | 17.9% |
