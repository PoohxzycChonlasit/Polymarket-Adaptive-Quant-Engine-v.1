# Outer Clamp Sensitivity Probe
# Polymarket-Adaptive-Quant-Engine-v.1

**Audit Date:** 2026-06-02
**Mode:** READ_ONLY — no code changes, no runtime mutation
**Source run:** `20260527T110608Z_26764_9d379e2c` (2026-05-27, 12-hour session)
**Prior audits:** delta_extreme_deep_dive_audit.md | closeness_factor_sensitivity_probe.md
**Formula studied:** `closeness_factor = clamp(0.006 / max(distance_pct, 0.0003), 0.25, OUTER_CLAMP)`
**Thresholds probed:** OUTER_CLAMP in {4.0 (current), 3.5, 3.0, 2.5}
**MIN_CLAMP held constant:** 0.0003

---

## Executive Outputs

```
current_state:
  mechanism_b_rows:          3326   (delta_multiplier=0.2, time_remaining > 90s)
  currently_extreme:         3326   (100.0%)
  ev_gt0_conf_ok_blocked:    1457   (43.8% of Mechanism B)
  closeness_at_max_4.0:      3119   (93.7% of rows have dist_pct < 0.0015)

sensitivity_table:
  OUTER_CLAMP  EXTREME       HIGH          NORMAL/LOW    UNBLOCKED    MEANINGFUL
  4.0          3326 (100%)   0    (0%)     0             0            0
  3.5          2605 ( 78%)   721  (22%)    0             721          159
  3.0          1446 ( 44%)   1880 ( 57%)   0             1880         521
  2.5           486 ( 15%)   2840 ( 85%)   0             2840         854

  KEY FINDING: OC=3.0 is mathematically IDENTICAL to MIN_CLAMP=0.002 (prior probe).
  Confirmed 100% match across all 3,326 rows.
  All unblocked rows under ANY tested outer clamp land in HIGH — never NORMAL or LOW.

  Incremental structure (meaningful rows are strict subsets):
    Batch A (OC<=3.5):            159 rows   -- highest quality, best liquidity
    Batch B (OC<=3.0, not 3.5):  +362 rows   -- moderate quality
    Batch C (OC<=2.5, not 3.0):  +333 rows   -- lowest quality, near timing gate
    Total at OC=2.5:              854 rows

best_candidate_outer_clamp: 3.5
  Rationale: releases only 159 high-quality rows (best liquidity, purely mid-window,
  lowest thin-liq rate at 19.5%) while exposing the least near-expiry risk.
  OC=3.0 is broader (521 rows) but equivalent to MIN_CLAMP=0.002.
  OC=2.5 is aggressive and unblocks rows with mean secs_remaining=131
  (competing with the 90s timing gate).

risk_notes:
  (1) No outer clamp produces NORMAL or LOW regime. All unblocked rows
      enter HIGH (delta_multiplier=0.5), not the safer 0.8 or 1.0 multipliers.
  (2) EV INCREASES as outer clamp decreases (Batch C mean EV=0.246 vs
      Batch A mean EV=0.208). High-EV rows are also the riskiest (near expiry,
      near PTB). EV quality has not been validated by OOS or replay.
  (3) Batch C (OC=2.5 incremental): mean secs=131, 30% thin liquidity.
      These rows are genuinely borderline. A 40s adverse move on BTC
      would expire the window before position management is possible.
  (4) OC=3.0 == MIN_CLAMP=0.002. Both probes converge on the same 521
      meaningful rows. Running both confirms they are the same candidates.
  (5) Tradeable window expands significantly but ALL entry candidates remain
      in the HIGH risk band, not the moderate or safe bands.

recommended_next_audit:
  thin_liquidity_gate_separation — investigate whether a separate liquidity
  admission gate (rejecting entries when bid+ask < threshold) would be more
  targeted than outer-clamp relaxation, given that thin liquidity is the
  primary amplifier causing EXTREME in the first 54 seconds of each window.
```

---

## 1. Mathematical Equivalence: OC=3.0 Equals MIN_CLAMP=0.002

Before analysing outcomes, a key structural finding: **OUTER_CLAMP=3.0 and MIN_CLAMP=0.002 are mathematically identical for all distances in this dataset**.

### Why they are the same

The threshold where `closeness_factor` equals exactly 3.0 is:
```
0.006 / distance_pct = 3.0   →   distance_pct = 0.002
```

For any `distance_pct < 0.002`:
- With `OUTER_CLAMP=3.0`: `0.006/max(dist, 0.0003)` exceeds 3.0, outer clamp fires → `cf = 3.0`
- With `MIN_CLAMP=0.002`: `0.006/max(dist, 0.002) = 0.006/0.002 = 3.0` → same result

For `distance_pct >= 0.002` (only 2% of rows):
- Both formulas reduce to `0.006/dist` — same result

**Verified: 3,326/3,326 rows produce identical scores.** The two prior probes converge on the same 521 meaningful rows.

This equivalence means the prior `closeness_factor_sensitivity_probe.md` findings fully apply to OC=3.0 without repeating analysis. The present probe focuses on what OC=3.5 and OC=2.5 add incrementally.

---

## 2. EXTREME Threshold Shift per Outer Clamp

With minimal field conditions (vol_f=0.755, vel_f=1.0) and `closeness_factor = OUTER_CLAMP` (the dominant case for 93.7% of rows), EXTREME fires when:

```
OUTER_CLAMP × sqrt(300/t) × 0.755 × qual_f > 4.0
```

| OUTER_CLAMP | EXTREME when (normal liq, qf=1.0) | EXTREME when (thin liq, qf=1.20) | Tradeable window (normal) | Tradeable window (thin) |
|---|---|---|---|---|
| **4.0 (current)** | **t < 171s** | **t < 246s** | **129s** | **54s** |
| **3.5** | **t < 131s** | **t < 189s** | **169s** | **111s** |
| **3.0** | **t < 96s** | **t < 139s** | **204s** | **161s** |
| **2.5** | **t < 67s** | **t < 96s** | **233s** | **204s** |

**Key takeaway per threshold:**

- **OC=3.5:** EXTREME at t<131s (normal liq) / t<189s (thin). Opens 40 additional seconds of normal-liquidity entry vs current. Thin-liquidity window expands from 54s to 111s.
- **OC=3.0:** EXTREME approaches the timing-gate boundary for normal liquidity (t<96s ≈ 90s hard gate). Thin-liquidity still blocks at t<139s.
- **OC=2.5:** Normal-liq EXTREME collapses to t<67s (below the 90s timing gate). Thin-liq just reaches t<96s. Mechanism B EXTREME essentially disappears for normal-liquidity markets.

---

## 3. Sensitivity Table — Full Results

### Reconstruction validation

All 3,326 rows reconstruct to EXTREME under OUTER_CLAMP=4.0: 100% match. ✓

### Results

| OUTER_CLAMP | EXTREME | HIGH | NORMAL/LOW | Unblocked | Meaningful (EV>0, conf>=0.54) |
|---|---|---|---|---|---|
| 4.0 | 3326 (100.0%) | 0 (0.0%) | 0 (0.0%) | 0 | 0 |
| 3.5 | 2605 (78.3%) | 721 (21.7%) | 0 (0.0%) | 721 | **159** |
| 3.0 | 1446 (43.5%) | 1880 (56.5%) | 0 (0.0%) | 1880 | **521** |
| 2.5 | 486 (14.6%) | 2840 (85.4%) | 0 (0.0%) | 2840 | **854** |

**Why NORMAL/LOW = 0 at every threshold:**

Even at OC=2.5 and closeness=2.5, the minimum achievable score requires secs_remaining close to 300 AND very low quality_factor. In the actual data, even the earliest-window evaluations carry thin liquidity (quality_factor=1.20), keeping scores above 2.0. Computed minimum at OC=2.5, secs=285, thin-liq:
```
2.5 × sqrt(300/285) × 0.755 × 1.0 × 1.20 = 2.5 × 1.026 × 0.755 × 1.20 = 2.31  → HIGH
```
The practical floor of HIGH regime prevents any NORMAL or LOW outcomes for this dataset.

---

## 4. Incremental Batch Structure

The meaningful rows form a strict subset chain: **A ⊆ (A+B) ⊆ (A+B+C)**

```
Verified:
  OC=3.5 meaningful (159) ⊂ OC=3.0 meaningful (521): 100.0%
  OC=3.0 meaningful (521) ⊂ OC=2.5 meaningful (854): 100.0%
```

Incremental batches:

| Batch | Released at | Rows | Description |
|---|---|---|---|
| A | OC=3.5 | 159 | First released — highest score headroom, best liquidity |
| B | OC=3.0 (not 3.5) | 362 | Second tier — moderate liquidity, more late-window |
| C | OC=2.5 (not 3.0) | 333 | Third tier — thinnest liquidity, nearest timing gate |

### Batch A — Released at OC=3.5 (159 rows)

The batch with the most margin to EXTREME, best orderbook quality, and most conservative timing.

| Metric | Value |
|---|---|
| EV mean | 0.2081 |
| EV max | 0.3621 |
| Confidence mean | 0.6269 |
| Confidence min | 0.5402 |
| Seconds remaining mean | 180 |
| Seconds remaining min | **134** |
| Median liquidity | **417.8 USDC** |
| Thin liquidity (<100 USDC) | 31 (19.5%) |
| Asset BTC | 118 (74.2%) |
| Asset ETH | 41 (25.8%) |
| Time bucket mid_window | 127 (79.9%) |
| Time bucket late_window | 24 (15.1%) |
| Lifecycle ACTIVE_INV_TRADING | 157 (98.7%) |
| Score range (at OC=3.5) | 3.505–3.999 (mean 3.813) |

**Profile:** Batch A is the cleanest subset. Minimum secs=134 keeps all rows safely above the 90s timing gate. Median liquidity of 418 USDC signals healthy orderbooks. 80% are mid-window evaluations. BTC dominates (74.2%).

### Batch B — Released at OC=3.0, not 3.5 (362 rows)

The incremental batch that OC=3.0 adds over OC=3.5.

| Metric | Value |
|---|---|
| EV mean | 0.2267 |
| EV max | 0.4073 |
| Confidence mean | 0.6376 |
| Seconds remaining mean | 156 |
| Seconds remaining min | **99** |
| Median liquidity | **291.8 USDC** |
| Thin liquidity (<100 USDC) | 73 (20.2%) |
| Asset BTC | 296 (81.8%) |
| Time bucket late_window | 185 (51.1%) |
| Time bucket mid_window | 163 (45.0%) |
| Score range (at OC=3.0) | 3.0–3.5 (by definition — below Batch A threshold) |

**Profile:** Good liquidity, slightly higher EV, but approaching later in the window. Min secs=99 is only 9 seconds above the hard 90s timing gate. Late_window rows now represent majority (51%). BTC dominance increases further (81.8%).

### Batch C — Released at OC=2.5, not 3.0 (333 rows)

The riskiest incremental batch — rows released only at the most aggressive clamp.

| Metric | Value |
|---|---|
| EV mean | **0.2464** (highest of any batch) |
| EV max | **0.4980** |
| Confidence mean | 0.6387 |
| Seconds remaining mean | **131** |
| Seconds remaining min | **91** (1 second above timing gate!) |
| Median liquidity | **232.5 USDC** |
| Thin liquidity (<100 USDC) | 100 (30.0%) |
| Asset BTC | 238 (71.5%) |
| Time bucket late_window | 262 (78.7%) |
| Time bucket mid_window | 56 (16.8%) |

**Profile:** Highest EV but also highest risk. Min secs=91 is one second above the 90s hard safety gate. Late_window rows account for 78.7%. Thin liquidity rate doubles vs Batch A (30% vs 19.5%). Mean secs=131 leaves only ~40 seconds of window before the timing gate engages.

---

## 5. EV Distribution Across Scenarios

```
Batch A (OC=3.5):              159 rows
  <0.10:  21 (13.2%)
  0.10-0.20: 55 (34.6%)
  0.20-0.30: 59 (37.1%)
  0.30-0.40: 24 (15.1%)
  mean=0.2081  max=0.3621

Batch A+B (OC=3.0):            521 rows
  <0.10:  75 (14.4%)
  0.10-0.20: 129 (24.8%)
  0.20-0.30: 195 (37.4%)
  0.30-0.40: 121 (23.2%)
  >=0.40:   1  (0.2%)
  mean=0.2210  max=0.4073

Batch A+B+C (OC=2.5):          854 rows
  <0.10: 102 (11.9%)
  0.10-0.20: 198 (23.2%)
  0.20-0.30: 328 (38.4%)
  0.30-0.40: 219 (25.6%)
  >=0.40:   7  (0.8%)
  mean=0.2309  max=0.4980
```

**EV increases as outer clamp decreases.** This is a structurally expected pattern: near-expiry binary tokens priced at 0.02–0.05 USDC with model probability 0.25–0.55 produce large arithmetic EVs. But "large EV" in this context reflects deep OTM binary pricing, not validated edge. The highest-EV rows (max=0.498) are those closest to expiry with the most uncertain outcomes.

---

## 6. Confidence Distribution

Confidence is nearly identical across all three unblocking scenarios. This is expected: confidence depends on model output, not on the delta formula.

| Scenario | Conf mean | Conf min | Conf max |
|---|---|---|---|
| OC=3.5 (159) | 0.6269 | 0.5402 | 0.7855 |
| OC=3.0 (521) | 0.6343 | 0.5402 | 0.7855 |
| OC=2.5 (854) | 0.6360 | 0.5402 | 0.8800 |

Confidence is not a discriminating factor between the three unblocking scenarios. The floor (0.5402) and mean (~0.635) are stable across all batches.

---

## 7. Liquidity Distribution

Liquidity shows the clearest degradation as outer clamp relaxes.

| Batch | Thin (<100) | Median | Mean |
|---|---|---|---|
| A only (OC=3.5, 159) | 19.5% | 417.8 USDC | 505.5 USDC |
| A+B (OC=3.0, 521) | 20.0% | 319.7 USDC | 488.9 USDC |
| A+B+C (OC=2.5, 854) | 23.9% | 283.3 USDC | 459.5 USDC |
| Still-EXTREME (OC=2.5, 486) | 57.4% | 60.5 USDC | ~150 USDC |

The still-EXTREME group at OC=2.5 has dramatically thinner liquidity (57.4% thin, median 60 USDC). Thin liquidity is the dominant factor keeping the 486 remaining rows in EXTREME even at OC=2.5.

**Conclusion: liquidity quality drives what stays EXTREME.** Rows with good liquidity are released first (Batch A), rows with moderate liquidity released next (Batch B), rows with thinner liquidity in Batch C. The hardest-to-unblock rows are those with the thinnest books.

---

## 8. Time Remaining Distribution

Time remaining shifts later as outer clamp decreases.

```
Time bucket breakdown (meaningful unblocked):

                    OC=3.5 (159)    OC=3.0 (521)    OC=2.5 (854)
  early_window        8  ( 5.0%)    22  ( 4.2%)    37  ( 4.3%)
  mid_window         127 (79.9%)   290 (55.7%)   346 (40.5%)
  late_window         24 (15.1%)   209 (40.1%)   471 (55.1%)

Seconds remaining:
                    OC=3.5      OC=3.0      OC=2.5
  mean               180         164         151
  min                134          99          91
  max                277         292         292
```

At OC=3.5, 80% of meaningful rows are mid-window (more than 120–180 seconds from close). At OC=2.5, the late_window bucket becomes the majority (55%), with minimum secs=91 edging against the timing gate.

---

## 9. BTC/ETH Split

BTC dominates across all outer clamp scenarios, increasingly so for the incremental batches.

| Scenario | BTC | ETH | BTC % |
|---|---|---|---|
| All Mechanism B (3326) | 1465 | 1861 | 44.0% |
| OC=3.5 meaningful (159) | 118 | 41 | **74.2%** |
| OC=3.0 meaningful (521) | 414 | 107 | **79.5%** |
| OC=2.5 meaningful (854) | 652 | 202 | **76.3%** |

BTC represents 74–80% of all meaningful unblocked rows despite being only 44% of all Mechanism B rows. This reflects BTC's typically better orderbook depth (keeping quality_factor lower, allowing scores to stay below 4.0 threshold even at reduced outer clamps).

---

## 10. Overlap with Previous MIN_CLAMP=0.002 Probe (521 rows)

Since OC=3.0 is identical to MIN_CLAMP=0.002:

- The 521 meaningful rows from the closeness_factor_sensitivity_probe.md are **the same 521 rows** found here at OC=3.0.
- Overlap = 521/521 = 100%.
- No new rows are identified by the OC=3.0 scenario. The two probes are redundant.

**The OC=3.5 scenario (159 rows) is the only genuinely new finding** — rows that were not identifiable from the MIN_CLAMP probe because MIN_CLAMP changes below 0.002 have no effect.

---

## 11. Risk Notes

### Risk 1 — No path to NORMAL or LOW (all unblocking stays HIGH)

Across all four outer clamp values tested, zero rows reach NORMAL (score ≤ 2.0) or LOW (score ≤ 1.0). Every unblocked row remains in HIGH (2.0 < score ≤ 4.0), meaning `delta_multiplier = 0.5` in all cases. Position sizing would be halved vs a LOW/NORMAL entry. **There is no outer clamp value that makes a Mechanism B entry "safe" in the classical sense.**

### Risk 2 — Batch C is genuinely near-expiry

Batch C (OC=2.5 incremental, 333 rows) has min secs=91 — one second above the hard timing gate. Mean secs=131 leaves ~40 seconds of execution window. In a binary Polymarket 5-minute market:
- At 131s remaining, BTC needs to hold its oracle position for only 131 more seconds to resolve.
- If the entry is on the wrong side of a late momentum move, there is limited time to exit or manage.
- These are not the same risk profile as early-window entries (Batch A at mean secs=180).

### Risk 3 — EV inversion: highest EV = highest risk

EV increases as outer clamp decreases (Batch A mean 0.208 → Batch C mean 0.246). This is arithmetically expected: deep out-of-the-money binary tokens near expiry have large EV when model probability exceeds token price. But these are also the moments of greatest uncertainty. **High EV in this context is a warning signal, not a quality signal.** The model has not been validated for edge at oracle-near-PTB conditions.

### Risk 4 — Thin liquidity doubles in Batch C

Thin liquidity rate: Batch A 19.5% → Batch B 20.2% → Batch C 30.0%. At OC=2.5, nearly 1 in 3 meaningful unblocked rows has a bid+ask depth below 100 USDC. Thin books increase slippage risk and make the min_fillable_size constraint more binding.

### Risk 5 — delta_multiplier jump from 0.2 to 0.5

Current EXTREME rows have `delta_multiplier = 0.2` (20% of normal position size). Unblocked HIGH rows would use `delta_multiplier = 0.5` (50% of normal). For the micro-survival bankroll (~$10):
- Current (EXTREME): 0.25% × $10 × 0.2 = $0.005 effective risk
- Under HIGH: 0.25% × $10 × 0.5 = $0.0125 effective risk

Still small absolute amounts, but a 2.5× increase in risk per entry. The risk_plan_zero gate remains active and would block any sizing below $0.05 minimum.

### Risk 6 — OC=3.5 is conservative but not risk-free

Batch A (OC=3.5) is the best-quality batch — median liq 418 USDC, mean secs 180, 80% mid-window — but still requires 159 entries into markets where oracle is within 0.15% of PTB. The near-PTB uncertainty that motivated the original delta_extreme block has not changed; only the formula tolerance has shifted.

---

## 12. Best Candidate Outer Clamp

### OC=3.5 — Recommended for initial study

**Why:** Batch A (159 rows) has the strongest risk/quality profile of any incremental batch:
- Mean secs=180 (safely above timing gate with 90s buffer)
- Median liquidity=418 USDC (3x better than all-meaningful at OC=2.5)
- 19.5% thin (vs 30% at OC=2.5)
- 80% mid-window (cleanest timing profile)
- BTC 74% (more liquid asset)
- Min secs=134 (44s above timing gate)

The 159-row yield is much smaller than OC=3.0 (521) or OC=2.5 (854), but the quality concentration is highest. An OC=3.5 pilot study is the most defensible first step.

### OC=3.0 — Equivalent to MIN_CLAMP=0.002, broader yield

If the 159 rows at OC=3.5 prove acceptable in a controlled test, OC=3.0 adds 362 more rows (Batch B). Batch B has slightly lower liquidity (median 292 USDC) and more late-window exposure (51%). Min secs=99 is tighter but still above the timing gate. Both MIN_CLAMP=0.002 and OC=3.0 produce the same 521 meaningful rows — confirmed convergent.

### OC=2.5 — Aggressive, not recommended without validation

Batch C (333 incremental rows) introduces min secs=91, 30% thin liquidity, and 79% late-window composition. Without replay validation of these specific characteristics, OC=2.5 could degrade PnL by accepting entries at the worst moments of each window cycle.

### Summary recommendation

```
best_candidate_outer_clamp: 3.5

Conservative order of evaluation:
  Step 1: Validate 159-row Batch A (OC=3.5) via bounded replay
  Step 2: If Step 1 validates, extend to 521-row Batch A+B (OC=3.0)
  Step 3: If Step 2 validates, consider Batch C (OC=2.5 incremental)

Each step requires operator approval and bounded replay analysis.
No step should auto-advance. No code changes from this probe.
```

---

## 13. Recommended Next Audit

```
recommended_next_audit: thin_liquidity_gate_separation

CONTEXT:
  Both probes (min-clamp and outer-clamp) show that thin liquidity
  (bid+ask < 100 USDC) is the dominant amplifier of EXTREME regime:
  - It extends EXTREME from t<171s to t<246s per window cycle
  - It keeps 57.4% of the still-EXTREME rows blocked even at OC=2.5
  - It accounts for 30% of the riskiest (Batch C) unblocked rows

  Current formula: thin liquidity contributes +0.20 to quality_factor,
  which multiplies directly into delta_score. This COMBINES a liquidity
  assessment with a price-distance assessment in one multiplicative term.

PROBE GOAL:
  Determine whether separating thin-liquidity into its own gate
  (a pre-delta liquidity filter) would be more precise than adjusting
  the outer clamp.

  Specific questions:
  1. How many mid-window rows are EXTREME SOLELY because thin
     liquidity pushed quality_factor to 1.20?
  2. If a standalone liquidity gate (min_liquidity = 100 USDC for new
     entries) replaced the quality_factor contribution, how many rows
     would be released vs blocked?
  3. Does the thin-liquidity gate produce a cleaner risk profile than
     outer_clamp relaxation (i.e., does it avoid releasing late-window
     and near-expiry rows)?

METHOD:
  Read-only simulation on the decision log using reconstructed
  delta_score with quality_factor capped at 1.0 (removing thin-liq
  contribution), then counting which rows exit EXTREME.
  Compare results to Batch A and Batch B quality profiles.

SAFETY:
  Read-only probe. No code change. No deployment.
  Operator review required before any parameter change.
```

---

## Appendix A — Score Bands under Each Outer Clamp

Score distributions for all meaningful unblocked rows (not just incremental):

```
OC=3.5 (159 meaningful):
  3.5-3.8 HIGH:  61 (38.4%)
  3.8-4.0 HIGH:  98 (61.6%)
  mean=3.813   min=3.505   max=3.999

OC=3.0 (521 meaningful):
  3.0-3.5 HIGH: 208 (39.9%)
  3.5-3.8 HIGH: 183 (35.1%)
  3.8-4.0 HIGH: 130 (25.0%)
  mean=3.578   min=3.004   max=3.998

OC=2.5 (854 meaningful):
  2.5-3.0 HIGH: 266 (31.1%)
  3.0-3.5 HIGH: 377 (44.1%)
  3.5-3.8 HIGH: 148 (17.3%)
  3.8-4.0 HIGH:  63  (7.4%)
  mean=3.227   min=2.503   max=3.988
```

Score concentration moves further from the EXTREME boundary as outer clamp decreases. OC=3.5 rows are all 3.5–4.0 (near boundary). OC=2.5 rows spread down to 2.5, providing more margin to EXTREME re-entry.

---

## Appendix B — Closeness Factor Behaviour by Distance Range

How closeness_factor changes under each outer clamp for representative distance values:

| dist_pct | Current (OC=4.0) | OC=3.5 | OC=3.0 | OC=2.5 |
|---|---|---|---|---|
| 0.0001 (0.01% of PTB) | 4.0 | 3.5 | 3.0 | 2.5 |
| 0.0003 (0.03%) | 4.0 | 3.5 | 3.0 | 2.5 |
| 0.0006 (0.06%, median) | 4.0 | 3.5 | 3.0 | 2.5 |
| 0.0010 (0.10%) | 4.0 | 3.5 | 3.0 | 2.5 |
| 0.0015 (0.15%, threshold) | 4.0 | 3.5 | 3.0 | 2.5 |
| 0.0017 (0.17%) | 3.53 | 3.5 | 3.0 | 2.5 |
| 0.0020 (0.20%) | 3.0 | 3.0 | 3.0 | 2.5 |
| 0.0024 (0.24%) | 2.5 | 2.5 | 2.5 | 2.5 |
| 0.0030 (0.30%) | 2.0 | 2.0 | 2.0 | 2.0 |
| 0.0060 (0.60%) | 1.0 | 1.0 | 1.0 | 1.0 |

For distances above 0.002, all outer clamps produce the same result (actual 0.006/dist value, no clamping). The outer clamp only matters for distances below 0.006/OC.

The 93.7% of rows with dist_pct < 0.0015 all get closeness = OC exactly, regardless of their specific distance. The outer clamp fully controls closeness for this dominant majority.
