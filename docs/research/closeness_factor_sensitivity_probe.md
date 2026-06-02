# Closeness Factor Sensitivity Probe
# Polymarket-Adaptive-Quant-Engine-v.1

**Audit Date:** 2026-06-02  
**Mode:** READ_ONLY — no code changes, no runtime mutation  
**Source run:** `20260527T110608Z_26764_9d379e2c` (2026-05-27, 12-hour session)  
**Prior audit:** `docs/research/delta_extreme_deep_dive_audit.md`  
**Formula studied:** `closeness_factor = clamp(0.006 / max(distance_pct, MIN_CLAMP), 0.25, 4.0)`  
**Thresholds probed:** MIN_CLAMP ∈ {0.0003 (current), 0.0005, 0.001, 0.002}

---

## Executive Outputs

```
current_state:
  mechanism_b_rows:             3326   (true-extreme, delta_multiplier=0.2)
  currently_extreme_count:      3326   (100.0%)
  rows_with_ev_gt0_conf_ok:     1457   (43.8% of Mechanism B)
  rows_blocked_by_closeness:    3119   (93.7% — closeness_factor=4.0)

sensitivity_table:
  MIN_CLAMP  EXTREME    UNBLOCKED  MEANINGFUL_UNBLOCKED
  0.0003     3326(100%) 0    (0%)  0
  0.0005     3326(100%) 0    (0%)  0
  0.001      3326(100%) 0    (0%)  0
  0.002      1446( 43%) 1880 (57%) 521  (16%)

  NOTE: 0.0003 / 0.0005 / 0.001 are FUNCTIONALLY IDENTICAL.
  All three produce closeness_factor=4.0 for 93.7% of rows.
  Only 0.002 breaks the outer-clamp dominance.

top_candidate_threshold: 0.002
  - Only threshold that produces any unblocking
  - Reduces closeness_factor from 4.0 to 3.0 for oracle within 0.2% of PTB
  - 1,880 rows exit EXTREME (enter HIGH regime)
  - 521 rows are "meaningful": EV>0 AND confidence>=0.54

risk_notes:
  (1) 0.002 moves all 1,880 unblocked rows to HIGH (score 3.0-4.0),
      not LOW or NORMAL. At HIGH, delta_multiplier=0.5 (2.5x larger
      position than current EXTREME multiplier=0.2).
  (2) 60% of meaningful unblocked rows have score 3.5-4.0 — a small
      change in velocity or liquidity would push them back to EXTREME.
  (3) These rows have oracle within 0.2% of PTB: genuine near-PTB risk
      that delta_extreme was designed to block.
  (4) 0.0003/0.0005/0.001 provide no practical benefit over the current
      formula for any typical oracle distance.

recommended_next_audit:
  outer_clamp_probe — study the effect of lowering the outer upper clamp
  from 4.0 to 3.5, 3.0, or 2.5, which would affect closeness behavior
  across ALL distance ranges (not just near-zero), and quantify the
  resulting entry window expansion per 5-minute cycle.
```

---

## 1. Why 0.0003 / 0.0005 / 0.001 Are Identical

### The formula

```python
closeness_factor = clamp(0.006 / max(distance_pct, MIN_CLAMP), 0.25, 4.0)
```

There are two clamps here:
- **Inner:** `max(distance_pct, MIN_CLAMP)` — prevents division by zero
- **Outer:** `clamp(..., 0.25, 4.0)` — caps the result between 0.25 and 4.0

The outer upper cap of **4.0** dominates whenever:
```
0.006 / max(distance_pct, MIN_CLAMP) >= 4.0
→ max(distance_pct, MIN_CLAMP) <= 0.0015
```

This is satisfied when **distance_pct ≤ 0.0015** (0.15% of PTB), which covers all oracle prices within $104 of PTB for BTC or $3 of PTB for ETH.

### Actual distribution in the data

| distance_pct range | Rows | % | Effect |
|---|---:|---:|---|
| < 0.0001 | 427 | 12.8% | cf=4.0 at all clamps |
| 0.0001–0.0003 | 725 | 21.8% | cf=4.0 at all clamps |
| 0.0003–0.0005 | 594 | 17.9% | cf=4.0 at all clamps |
| 0.0005–0.001 | 966 | 29.0% | cf=4.0 at all clamps |
| 0.001–0.0015 | 406 | 12.2% | cf=4.0 for clamps ≤ 0.001; varies for 0.002 |
| 0.0015–0.002 | 142 | 4.3% | cf < 4.0 for all clamps; cf forced to 3.0 by 0.002 |
| 0.002–0.003 | 55 | 1.7% | cf = 0.006/distance (2.0–3.0 range) |
| > 0.003 | 11 | 0.3% | cf < 2.0 |

**93.7% of Mechanism B rows have distance_pct < 0.0015** — all firmly inside the outer-clamp dominance zone.

For these 93.7%:

| MIN_CLAMP | closeness_factor=4.0 |
|---|---|
| 0.0003 | 3,118/3,118 (100%) |
| 0.0005 | 3,118/3,118 (100%) |
| 0.001 | 3,118/3,118 (100%) |
| **0.002** | **0/3,118 (0%)** ← reduces to 3.0 |

**Conclusion: Changing MIN_CLAMP from 0.0003 to 0.0005 or 0.001 produces zero change for 93.7% of rows. The outer 4.0 clamp absorbs all of them. Only MIN_CLAMP=0.002 (> 0.0015) breaks this dominance.**

### Why MIN_CLAMP=0.002 works differently

When MIN_CLAMP=0.002 > 0.0015:
```
closeness_factor = clamp(0.006 / max(distance_pct, 0.002), 0.25, 4.0)
```
For distance_pct < 0.002 (typical near-PTB case):
```
closeness_factor = 0.006 / 0.002 = 3.0   (below outer cap of 4.0)
```

This reduces closeness from 4.0 → 3.0 for all rows where oracle is within 0.2% of PTB ($139 for BTC). A 25% reduction in the dominant formula component.

---

## 2. EXTREME Threshold under Each Scenario

With closeness_factor=cf, using minimal conditions (volatility≈0, velocity=0, spread=0.01, normal liquidity, qual_f=1.0):

```
delta_score = cf × sqrt(300/t) × 0.755 × 1.0 × 1.0

EXTREME when delta_score > 4.0:
  cf × sqrt(300/t) × 0.755 > 4.0
  sqrt(300/t) > 4.0 / (cf × 0.755)
  t < 300 / [4.0 / (cf × 0.755)]²
```

| MIN_CLAMP | Effective cf (near-PTB) | EXTREME when t < (normal liq) | EXTREME when t < (thin liq, qf=1.20) |
|---|---|---|---|
| 0.0003 | 4.0 | **171 seconds** | **246 seconds** |
| 0.0005 | 4.0 | **171 seconds** | **246 seconds** |
| 0.001 | 4.0 | **171 seconds** | **246 seconds** |
| **0.002** | **3.0** | **96 seconds** | **138 seconds** |

With MIN_CLAMP=0.002 and normal liquidity, EXTREME only triggers when **time_remaining < 96 seconds** — essentially collapsing to the timing gate zone (≤90s). With thin liquidity, it extends to 138 seconds.

**The tradeable window expands:**

| Scenario | Available entry window per 5-min cycle |
|---|---|
| Current (all clamps ≤ 0.001) | **129 seconds** (normal liq) or **54 seconds** (thin liq) |
| MIN_CLAMP=0.002 | **204 seconds** (normal liq) or **162 seconds** (thin liq) |
| Gain at 0.002 | +75 seconds (normal liq) or +108 seconds (thin liq) |

---

## 3. Sensitivity Table — Full Results

### Reconstruction validation

All 3,326 Mechanism B rows reconstructed as EXTREME under current formula (clamp=0.0003): ✓ 100% match.

### Results by threshold

| Metric | 0.0003 | 0.0005 | 0.001 | **0.002** |
|---|---|---|---|---|
| Still EXTREME | 3,326 | 3,326 | 3,326 | **1,446** |
| EXTREME % | 100.0% | 100.0% | 100.0% | **43.5%** |
| Unblocked | 0 | 0 | 0 | **1,880** |
| Unblocked % | 0% | 0% | 0% | **56.5%** |
| Unblocked EV>0, conf≥0.54 | 0 | 0 | 0 | **521** |
| Meaningful unblocked % | 0% | 0% | 0% | **15.7%** |

---

## 4. Profile of Unblocked Rows under MIN_CLAMP=0.002

### All 1,880 unblocked rows

| Metric | Value |
|---|---|
| Regime under 0.002 | **ALL HIGH** (100%) |
| New regime range | Score 2.0–4.0 (all in HIGH band) |
| ev > 0 | 521 (27.7%) |
| ev = 0 | 1,359 (72.3%) |
| conf ≥ 0.54 | 622 (33.1%) |
| conf < 0.54 (still fail conf gate) | 1,258 (66.9%) |
| EV>0 AND conf≥0.54 (meaningful) | **521 (27.7%)** |
| Asset | ETH 53.8%, BTC 46.2% |
| Lifecycle ACTIVE_INV_TRADING | 1,790 (95.2%) |
| Lifecycle OPENING_SCAN | 90 (4.8%) |
| Thin liquidity (<100 USDC) | 995 (52.9%) |
| Median liquidity | 87.8 USDC |
| Mean seconds remaining | 184 |
| Time bucket mid_window | 1,273 (67.7%) |
| Time bucket late_window | 407 (21.6%) |
| Time bucket early_window | 200 (10.6%) |

**72.3% of unblocked rows would still fail** at the EV gate (ev=0) or confidence gate (conf<0.54). The delta_extreme removal for these rows changes their block reason but not their outcome.

### The 521 Meaningful Unblocked Rows

These are rows that passed both confidence (≥0.54) and EV (>0) gates AND would exit EXTREME under MIN_CLAMP=0.002. They represent the outer bound of recoverable missed opportunity.

| Metric | Value |
|---|---|
| Count | 521 |
| As % of all Mechanism B | 15.7% |
| New delta score (mean) | **3.578** |
| New delta score (min) | 3.004 |
| New delta score (max) | 3.998 |
| Score in 3.0–3.5 (HIGH) | 208 (39.9%) |
| Score in 3.5–4.0 (HIGH, near-boundary) | 313 (60.1%) |
| EV mean | 0.2210 |
| EV max | 0.4073 |
| EV in 0.20–0.30 range | 195 (37.4%) |
| EV in 0.30–0.40 range | 121 (23.2%) |
| Confidence mean | 0.6343 |
| Confidence min | 0.5402 |
| Asset BTC | 414 (79.5%) |
| Asset ETH | 107 (20.5%) |
| Thin liquidity (<100 USDC) | 104 (20.0%) |
| Median liquidity | **319.7 USDC** |
| Mean liquidity | 488.9 USDC |
| Lifecycle ACTIVE_INV_TRADING | 512 (98.3%) |
| Mean seconds remaining | 164 |
| Time bucket mid_window | 290 (55.7%) |
| Time bucket late_window | 209 (40.1%) |

**Notable observations:**

1. **BTC-heavy (79.5%)**: The meaningful unblocked rows are disproportionately BTC. BTC's better orderbook depth (median 319.7 vs 87.8 USDC for all unblocked) keeps `quality_factor` lower, reducing delta_score below the 4.0 EXTREME threshold at clamp=0.002.

2. **Score concentration at 3.5–4.0**: 60.1% of the 521 meaningful rows have score in the 3.5–4.0 band. They are within 0.5 units of the EXTREME boundary. A slight increase in velocity, volatility, or thin-liquidity event would push them back to EXTREME under any formula.

3. **Good liquidity**: Median 319.7 USDC (vs 87.8 USDC for all unblocked, vs 76.4 USDC for all true-extreme). The meaningful unblocked rows have substantially better orderbook depth.

4. **Real EV**: Mean EV = 0.2210 — consistent with the wider pool. These are binary tokens priced at 0.02–0.10 USDC where model probability implies significant edge.

---

## 5. Why 1,446 Rows Remain EXTREME under 0.002

The 1,446 rows that remain EXTREME after raising MIN_CLAMP to 0.002 are blocked by either:
- **Time_remaining < ~138s with thin liquidity** (quality_factor=1.20 amplifies score above 4.0 even at cf=3.0)
- **Actual distance_pct > 0.002** (6.3% of rows — these are not affected by changing MIN_CLAMP)

Profile vs unblocked group:

| Metric | Unblocked (1,880) | Still-EXTREME (1,446) |
|---|---|---|
| Mean secs remaining | 184 | **137** (shorter) |
| Median liquidity | 87.8 USDC | **66.2 USDC** (thinner) |
| Thin liq (<100 USDC) | 52.9% | **62.6%** (more thin) |
| Time bucket late_window | 21.6% | **74.3%** (more late) |
| EV>0, conf≥0.54 | 27.7% | 34.5% |

The still-EXTREME rows are distinguished by shorter time remaining and thinner liquidity — exactly the conditions that amplify delta_score above 4.0 even with cf=3.0.

**Arithmetic example for still-EXTREME:**
At secs=120, thin liq (qf=1.20), cf=3.0:
```
delta_score = 3.0 × sqrt(300/120) × 0.755 × 1.0 × 1.20
            = 3.0 × 1.581 × 0.755 × 1.20 = 4.31  → EXTREME
```
Remains EXTREME even under clamp=0.002.

---

## 6. EV and Confidence Distributions across Thresholds

Since 0.0003/0.0005/0.001 are identical, the comparison is: current vs 0.002.

### Under current (0.0003)

```
EV>0, conf>=0.54 blocked by delta_extreme:  1457 rows  (43.8% of Mechanism B)
  EV: mean=0.2507  max=0.5340
  conf: mean=0.6442  min=0.5402

Of these 1,457:
  Released at 0.002:  521 (35.8%)  — would exit EXTREME
  Still blocked at 0.002: 936 (64.2%) — would remain EXTREME
```

### Confidence at meaningful unblocked vs still-blocked

| Group | n | Conf mean | Conf min |
|---|---|---|---|
| Meaningful unblocked (0.002) | 521 | 0.6343 | 0.5402 |
| EV>0, conf≥0.54, still EXTREME | 936 | 0.6484 | 0.5401 |

Confidence distributions are nearly identical between released and still-blocked. Confidence is not the discriminating factor.

---

## 7. Risk Notes

### Risk 1 — Borderline HIGH scores

60.1% of the 521 meaningful unblocked rows have score 3.5–4.0 under clamp=0.002. They are very close to the EXTREME boundary. Under any of the following conditions, they would return to EXTREME:

- Orderbook thins slightly (total bid+ask drops below 100 USDC → `quality_factor` jumps from 1.0 to 1.20)
- Oracle velocity increases (even a 0.001/unit velocity → `velocity_factor` = 1.25 → score × 1.25)
- Time remaining decreases by ~15 seconds

**These rows are structurally fragile under clamp=0.002.** A dynamic market condition could make clamp=0.002 unstable.

### Risk 2 — Genuine near-PTB risk

All 521 meaningful rows have oracle price within **0.20% of PTB** (within $139 for BTC at $69K, within $4 for ETH). In a binary market ("will BTC close above $69,489?"), being $139 below the target at 164 seconds remaining represents genuine high uncertainty. `delta_extreme` was originally calibrated to flag this uncertainty as entry-blocking. Relaxing it via clamp=0.002 allows entry at these uncertain moments.

### Risk 3 — Position sizing amplification

Under HIGH regime (clamp=0.002), `delta_multiplier = 0.5` vs current EXTREME `delta_multiplier = 0.2`. An allowed entry would use **2.5× the position size** currently allocated to EXTREME conditions. For a micro-survival bankroll ($10), even at HIGH regime:
- Current EXTREME: risk × 0.2 = $0.05 × 0.2 = $0.01 per trade
- Under HIGH: risk × 0.5 = $0.05 × 0.5 = $0.025 per trade

Larger, but still very small. The risk_plan_zero gate remains active and would catch any sizing that falls below the $0.05 minimum.

### Risk 4 — Outcome uncertainty for near-PTB binary markets

**This is the most important risk.** The delta engine's closeness_factor was designed to reflect that near-PTB markets are genuinely uncertain. The EV estimate (mean 0.2210) is based on the probability model output, not realized outcomes. For binary markets where oracle is within 0.2% of PTB:
- The outcome is nearly 50/50 (slight model edge)
- The probability model's edge at this close a distance has not been validated via OOS testing
- `delta_extreme` is partly a data-quality guard: when oracle is extremely close to PTB, the probability model's edge estimate is most noise-sensitive

**No outcome validation has been performed on these near-PTB entries.** The EV figures are advisory only.

### Risk 5 — Residual gate exposure

Even if delta_extreme is removed for these 521 rows, they must still pass:
- **risk_plan_zero** (~1.7% of run rows): ~9 additional blocks
- **frequency_cooldown** (~0.4%): ~2 additional blocks
- **max_active_positions_per_market**: no change expected (most are fresh evaluations)

Net potential additional entries from 521: approximately **510 additional entry evaluations** per 12-hour session would reach position sizing under clamp=0.002. Whether they result in fills depends on orderbook execution.

### Risk 6 — Interaction with DEFENSIVE risk mode

The live session summary showed `risk_mode=DEFENSIVE` with `confidence_below_defensive` as the second-largest skip reason. In DEFENSIVE mode, the confidence threshold is raised above the base 0.54 floor. Of the 521 meaningful rows (conf mean=0.6343), some may still fail the raised defensive confidence threshold even if delta_extreme is cleared.

---

## 8. Recommended Next Audit

```
recommended_next_audit: outer_clamp_probe

CONTEXT:
  The current probe reveals that changing MIN_CLAMP from 0.0003 to anything
  <= 0.001 provides zero benefit. Only 0.002 matters. But the 0.002 change
  moves ALL unblocked rows into the 3.0-4.0 HIGH band, concentrating them
  near the EXTREME boundary and leaving 62.6% of still-EXTREME rows blocked
  by thin-liquidity amplification.

  A complementary approach: lower the OUTER upper clamp (currently 4.0).
  This would reduce the EXTREME ceiling uniformly for ALL rows, not just
  near-zero-distance ones. It would also affect the scoring of rows with
  non-trivial distances.

SPECIFIC PROBE:
  Name: outer_clamp_sensitivity_probe
  Study outer clamp values: 4.0 (current), 3.5, 3.0, 2.5
  Formula: clamp(0.006 / max(distance_pct, 0.0003), 0.25, OUTER_CLAMP)

  Questions:
  1. How many rows exit EXTREME at each outer-clamp reduction?
  2. What regime do they enter (HIGH vs NORMAL)?
  3. Does reducing outer clamp to 3.0 produce similar unblocking as
     raising MIN_CLAMP to 0.002, or broader effects?
  4. What combination (e.g., outer_clamp=3.5 + thin_liq_gate_separate)
     would cleanly separate the liquidity-amplification problem?

SAFETY:
  Read-only probe. No code change. No deployment.
  Operator review required before any parameter change.
  No EV figures in this probe constitute approval to trade.
```

---

## Appendix A — Formula Equivalence Proof

For the three equivalent clamp values (0.0003, 0.0005, 0.001):

The outer 4.0 clamp dominates whenever `0.006 / max(dist, mc) ≥ 4.0`, i.e., when `max(dist, mc) ≤ 0.0015`. For 93.7% of rows where `dist < 0.0015`:

```
max(dist, 0.0003) ≤ 0.0015  → outer clamp fires → cf=4.0
max(dist, 0.0005) ≤ 0.0015  → outer clamp fires → cf=4.0
max(dist, 0.001)  ≤ 0.0015  → outer clamp fires → cf=4.0
```

(Because dist=0.0006 < 0.001 → max(0.0006, 0.001)=0.001 ≤ 0.0015 → 0.006/0.001=6.0 ≥ 4.0 → outer clamp fires → cf=4.0)

Only when `mc > 0.0015` does the min_clamp override the outer-clamp regime:
```
max(dist, 0.002)  = 0.002 > 0.0015  → outer clamp does NOT fire → cf = 0.006/0.002 = 3.0
```

The transition point is exactly `mc = 0.0015`. Any MIN_CLAMP ≤ 0.0015 produces identical behaviour.

---

## Appendix B — Full Sensitivity at clamp=0.002

| Category | Unblocked (0.002) | Still-EXTREME (0.002) |
|---|---|---|
| **Total rows** | **1,880** | **1,446** |
| EV=0 | 1,359 (72.3%) | 947 (65.5%) |
| EV>0 | 521 (27.7%) | 499 (34.5%) |
| conf≥0.54 | 622 (33.1%) | 562 (38.9%) |
| EV>0 AND conf≥0.54 | **521 (27.7%)** | **499 (34.5%)** |
| BTC | 868 (46.2%) | 597 (41.3%) |
| ETH | 1,012 (53.8%) | 849 (58.7%) |
| ACTIVE_INV_TRADING | 1,790 (95.2%) | 1,420 (98.2%) |
| OPENING_SCAN | 90 (4.8%) | 26 (1.8%) |
| Thin liq (<100) | 995 (52.9%) | 905 (62.6%) |
| Late_window | 407 (21.6%) | 1,075 (74.3%) |
| Mid_window | 1,273 (67.7%) | 307 (21.2%) |
| Mean secs remaining | 184 | 137 |
| New regime | HIGH (100%) | EXTREME (100%) |
