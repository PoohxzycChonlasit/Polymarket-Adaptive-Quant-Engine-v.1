# Delta Extreme Deep Dive Audit
# Polymarket-Adaptive-Quant-Engine-v.1

**Audit Date:** 2026-06-02  
**Mode:** READ_ONLY — no code changes, no runtime mutation  
**Source run:** `20260527T110608Z_26764_9d379e2c` (2026-05-27, 12-hour session)  
**Data file:** `runtime/quant_data/decision_log/2026-05-27.jsonl`  
**Prior context:** Previous root cause audit found delta_extreme = 869/1,400 (62.1%) in the 3-hour audit window; this audit expands to the full 12-hour run (7,706 decisions) for richer statistics

---

## Executive Outputs

```
total_delta_extreme_count:   4393   (full 12-hour session)
delta_extreme_share:         57.0%  (4393 / 7706 total decisions)

asset_split:
  ETH: 2381  (54.2%)
  BTC: 2012  (45.8%)

lifecycle_split:
  ACTIVE_INVENTORY_TRADING: 3846  (87.5%)
  PROFIT_MANAGEMENT:          431   (9.8%)
  OPENING_SCAN:               116   (2.6%)

hour_split (UTC):
  11h: 213 (4.8%)   16h: 389 (8.9%)   20h: 391 (8.9%)
  12h: 301 (6.9%)   17h: 341 (7.8%)   21h: 372 (8.5%)
  13h: 319 (7.3%)   18h: 374 (8.5%)   22h: 413 (9.4%)
  14h: 338 (7.7%)   19h: 366 (8.3%)   23h: 385 (8.8%)
  15h: 191 (4.3%)
  (no dominant session hour; fairly uniform across 12 hours)

time_remaining_distribution:
  1-30s:    0    (0.0%)   — absorbed by timing-gate (dm=0.0)
  31-60s:  431   (9.8%)   — timing-gate
  61-90s:  636  (14.5%)   — timing-gate
  91-120s: 714  (16.3%)
  121-180s:1503  (34.2%)  ← peak delta_extreme zone
  181-240s: 845  (19.2%)
  >240s:    264   (6.0%)   — early window

  mean=139.6s   median=136s   min=36s   max=296s

confidence_distribution:
  <0.40:      582  (13.2%)
  0.40-0.45:  742  (16.9%)
  0.45-0.50:  840  (19.1%)
  0.50-0.54:  587  (13.4%)   (below floor: 62.6% of all delta_extreme)
  0.54-0.60:  609  (13.9%)
  0.60-0.65:  336   (7.6%)
  0.65-0.70:  347   (7.9%)
  >=0.70:     350   (8.0%)
  mean=0.515   median=0.502

ev_distribution:
  ev_after_spread = 0.00:   2936  (66.8%)
  ev_after_spread != 0.00:  1457  (33.2%)
    non-zero EV: min=0.0367  max=0.5340  mean=0.2507
    all 1457 non-zero EV rows have confidence >= 0.54 (confirmed)

overlap_with_time_unsafe:
  292 candidates saw BOTH delta_extreme AND time_unsafe on same candidate_id
  (same candidate first blocked by delta_extreme mid-window, then time_unsafe at end)

overlap_with_empty_book:
  0 candidates — delta_extreme and empty_book are mutually exclusive paths
  (empty_book fires before delta assessment reaches the delta gate)

root_cause:
  TWO distinct mechanisms (see Section 3)

recommended_next_audit:
  closeness_factor_sensitivity_probe — measure the tradeable window
  duration per epoch under current closeness formula vs a relaxed clamp;
  quantify EV foregone from the 1,457 non-zero EV delta_extreme rows
```

---

## 1. The Two-Mechanism Split

`delta_extreme` is NOT a single condition. It fires from two completely independent code paths with different causes.

### Mechanism A — Timing Gate (24.3% of delta_extreme, 1,067 rows)

**Code path:** `delta_engine.estimate_micro_delta`, first branch:
```python
if time_remaining <= 90:
    return MicroDeltaResult(
        delta_score=10.0,
        delta_regime=DeltaRegime.EXTREME,
        delta_multiplier=0.0,    # ← hardcoded zero
        reason="entry_blocked_time_remaining_le_90s",
        new_entry_blocked=True,
    )
```

**Behaviour:** When fewer than 90 seconds remain in the 5-minute window, `delta_multiplier` is set to 0.0 and regime is forced EXTREME regardless of price, volatility, or confidence. This is a **hard safety gate**, not a price-risk assessment.

**Diagnostic signature:**
- `delta_multiplier = 0.0` (only Mechanism A produces this value)
- `seconds_remaining ≤ 90` (always for this path)
- `delta_score = 10.0` (hardcoded)

**Assessment:** Working as designed. This 90-second exclusion zone is a correct risk boundary. It should not be changed without operator approval and a full replay analysis on late-entry performance.

---

### Mechanism B — Structural Closeness Sensitivity (75.7% of delta_extreme, 3,326 rows)

**Code path:** `delta_engine.estimate_micro_delta`, main scoring branch:
```python
closeness_factor = clamp(0.006 / max(distance_pct, 0.0003), 0.25, 4.0)
delta_score = closeness_factor * time_factor * volatility_factor * velocity_factor * quality_factor
```

**Behaviour:** When oracle price is within 0.15% of PTB, `distance_pct < 0.0015`, causing `0.006 / distance_pct > 4.0` which is clamped to the maximum `closeness_factor = 4.0`. Combined with normal time_factor values, this drives `delta_score > 4.0` → EXTREME.

**Diagnostic signature:**
- `delta_multiplier = 0.2` (EXTREME path with non-zero multiplier)
- `delta_score = None` (not serialized to log — regime inferred from multiplier)
- `seconds_remaining` ranges from 91 to 296 — spans most of the window
- All `delta_regime = EXTREME` (confirmed 100% of Mechanism B rows)

---

## 2. Mechanism B Root Cause: Closeness Factor at Maximum

### How the formula fires

The `closeness_factor` denominator has a minimum clamp of **0.0003**:

```python
closeness_factor = clamp(0.006 / max(distance_pct, 0.0003), 0.25, 4.0)
```

This means: **any oracle price within 0.15% of PTB (`distance_pct < 0.0015`) gives `closeness_factor = 4.0` (maximum)**. The clamp floor 0.0003 prevents the denominator from being smaller than 0.0003.

Threshold: `0.006 / 4.0 = 0.0015` = 0.15% of PTB price.

In dollar terms:
- **BTC at $69,489:** oracle within **$104** of PTB → closeness_factor = 4.0
- **ETH at $1,978:** oracle within **$3.0** of PTB → closeness_factor = 4.0

### Frequency in practice

| Metric | Value |
|---|---|
| True-extreme rows with closeness_factor = 4.0 | 3,119 / 3,326 = **93.8%** |
| True-extreme rows with closeness_factor < 4.0 | 207 / 3,326 = 6.2% (sub-4 mean=3.21) |
| Distance from PTB (true-extreme, median) | 0.047% of PTB ($33 for BTC) |
| Distance from PTB (true-extreme, mean) | 0.060% of PTB ($42 for BTC) |

**93.8% of true-extreme blocks occur when oracle is within the 0.15% closeness threshold.**

### Why this produces EXTREME at mid-window

With `closeness_factor = 4.0` and assuming minimal conditions (near-zero velocity, near-zero volatility, spread=0.01):
- `volatility_factor ≈ 0.755` (minimum: clamp floor = 0.75)
- `velocity_factor = 1.0` (zero velocity)
- `quality_factor = 1.0` (normal liquidity, narrow spread)

The delta score formula becomes:

```
delta_score = 4.0 × sqrt(300 / time_remaining) × 0.755 × 1.0 × 1.0
```

**EXTREME threshold (score > 4.0) is reached when:**
```
4.0 × sqrt(300/t) × 0.755 > 4.0
sqrt(300/t) > 1.325
t < 171 seconds
```

→ **With normal liquidity: EXTREME triggers when time_remaining < 171 seconds (= elapsed ≥ 129 seconds into the 5-minute window).**

With **thin liquidity** (bid+ask < 100 USDC, `quality_factor = 1.20`, affects **57.1% of true-extreme rows**):
```
4.0 × sqrt(300/t) × 0.755 × 1.20 > 4.0
t < 246 seconds
```

→ **With thin liquidity: EXTREME triggers when time_remaining < 246 seconds (= elapsed ≥ 54 seconds into the window).**

### Effective tradeable window

| Condition | EXTREME threshold | Tradeable window |
|---|---|---|
| Normal liquidity (bid+ask ≥ 100 USDC) | time_remaining < 171s | First **129 seconds** of window |
| Thin liquidity (bid+ask < 100 USDC) | time_remaining < 246s | First **54 seconds** of window |
| Thin + timing gate | time_remaining < 246s OR ≤90s | ~54 seconds (net) |

**57.1% of true-extreme rows have thin liquidity.** The thin-liquidity case reduces the available entry window from 129 seconds to only ~54 seconds per 5-minute cycle.

---

## 3. True-Extreme Sub-Distribution

### Seconds remaining when EXTREME fires

```
Distribution of seconds_remaining at delta_extreme block (Mechanism B):

  91-120s:   475 (14.3%)  — near-timing zone
  121-170s:  1526 (45.9%) — main EXTREME zone (with normal liq)
  171-225s:  923 (27.8%)  — thin-liq EXTREME zone
  226-296s:  402 (12.1%)  — early window (velocity/extra-thin liq driving EXTREME)

Mean: 159 seconds    Min: 91    Max: 296
```

| Zone | Rows | % | Likely Driver |
|---|---:|---:|---|
| 91-170s remaining (normal EXTREME zone) | 2,001 | 60.2% | time_factor + closeness_factor ≥ 4.0 at normal liquidity |
| 171-225s remaining (thin-liq zone) | 923 | 27.8% | quality_factor=1.20 from thin liquidity pushes score above 4.0 |
| 226-296s remaining (early window) | 402 | 12.1% | Price velocity, extra-thin liquidity, or PROFIT_MANAGEMENT/OPENING_SCAN context |

### OPENING_SCAN delta_extreme (early window)

**116 blocks at mean 281 seconds remaining** (just 19 seconds into the 5-minute window).

Observed pattern in OPENING_SCAN samples:
- `distance_from_ptb_pct` = 0.016-0.094% (close to PTB, as expected at window start)
- `top_bid_depth + top_ask_depth` = 24-40 USDC (extremely thin at window open)
- `spread = 0.01` (normalized already)

At 285s remaining with thin liquidity: `delta_score = 4.0 × 1.026 × 0.75 × 1.0 × 1.20 = 3.69` (HIGH, not EXTREME). These OPENING_SCAN EXTREME cases likely involve non-zero price velocity pushing `velocity_factor > 1.0`, crossing the EXTREME threshold in the very first evaluation.

### ACTIVE_INVENTORY_TRADING dominance (87.5%)

The fact that 87.5% of delta_extreme blocks carry `lifecycle_phase = ACTIVE_INVENTORY_TRADING` is consistent with mid-window evaluation: the market is discovered and active, but between 91-296 seconds, the combined `closeness_factor × time_factor` product consistently exceeds EXTREME threshold for oracle prices near PTB.

---

## 4. Confidence Distribution Analysis

```
Below confidence floor (< 0.54):   2751 rows  (62.6% of all delta_extreme)
At or above floor (>= 0.54):       1642 rows  (37.4%)
```

### Why this breakdown matters for gate ordering

`trader.py` checks gates in this order (at the `skip_reason` assignment, line ~9078):
```python
elif delta.delta_regime == DeltaRegime.EXTREME or delta.delta_multiplier <= 0:
    skip_reason = "delta_extreme"
elif not quality_ok:
    skip_reason = f"risk_mode_{mode}:{quality_reason}"
elif not ev_result.approved:
    skip_reason = scored.skip_reason  # includes confidence_too_low
```

**The delta check fires BEFORE confidence and EV checks in this path.** So `delta_extreme` absorbs a portion of rows that would have failed at confidence anyway (62.6% below floor). The 37.4% with confidence ≥ 0.54 are genuine missed-opportunity blocks.

### The 1,457 non-zero EV rows

**1,457 delta_extreme rows (33.2%) have non-zero `ev_after_spread`**, all with confidence ≥ 0.54. These rows passed both confidence and EV gates before being blocked by delta.

| Metric | Value |
|---|---|
| Count | 1,457 |
| EV mean | 0.2507 (25.1% edge — very high) |
| EV max | 0.5340 |
| Confidence mean | 0.6442 |
| Confidence min | 0.5402 (just above floor) |
| delta_multiplier = 0.0 (timing-gate) | 437 rows |
| delta_multiplier = 0.2 (true-extreme) | 1,020 rows |
| Lifecycle: ACTIVE_INVENTORY_TRADING | 1,286 (88.3%) |
| Time remaining mean | 123 seconds |
| secs >= 171 (early-zone potential) | 231 rows (15.9%) |
| secs 91-170 (mid-EXTREME zone) | 789 rows (54.2%) |

**231 non-zero EV rows (15.9%) occur at secs ≥ 171** — the zone where standard-liquidity entry could theoretically proceed if the delta threshold were tuned. These represent the most tractable missed-opportunity candidates for further study.

---

## 5. EV Distribution

```
ev_after_spread_available = True:  4393 (100% of delta_extreme rows)
EV was calculated for all blocked rows.

ev = 0.00:       2936 rows (66.8%)
ev != 0.00:      1457 rows (33.2%)

Within non-zero EV:
  0.03 - 0.10:   244 rows  (16.8%)
  0.10 - 0.20:   187 rows  (12.8%)
  0.20 - 0.30:   312 rows  (21.4%)
  0.30 - 0.40:   321 rows  (22.0%)
  0.40 - 0.50:   274 rows  (18.8%)
  0.50+:         119 rows   (8.2%)
```

The high mean EV (0.2507) in the non-zero rows is expected: these are Polymarket binary markets where YES token is priced at 0.02-0.10¢ (deeply out-of-the-money), so `ev = p_yes - yes_ask` can be large when the model assigns moderate probability. These are NOT necessarily reliable edges — EV quality depends on model calibration.

**The zero-EV majority (66.8%)** reflects rows where the model assigned a 50/50 probability (confidence too low) or where the ask price exceeded model probability — both result in `evaluate_entry` returning `ev=0.0`.

---

## 6. Asset Split Analysis

```
All delta_extreme (4393):    ETH 54.2%  BTC 45.8%
Timing-gate (1067):          BTC 51.3%  ETH 48.7%
True-extreme (3326):         ETH 56.0%  BTC 44.0%
Non-zero EV (1457):          (not split in this analysis)
```

**ETH has higher true-extreme exposure** (56%) versus BTC (44%). Possible explanations:
- ETH's smaller absolute price ($1,978 vs $69,489) means the $3 closeness threshold is reached more easily (0.15% of ETH = $3.0 vs 0.15% of BTC = $104)
- ETH's orderbook tends to be thinner in USDC terms, increasing `quality_factor` contribution
- Both observations need further data to confirm

The timing-gate is roughly symmetric between assets (51/49), consistent with both markets sharing the same 5-minute window cycle.

---

## 7. Hour Distribution Analysis

```
Hour (UTC) | delta_extreme | delta_extreme/hr
  11h UTC  |      213      | low (session start)
  12-14h   |   301-338     | building
  15h UTC  |      191      | dip (likely run gap)
  16-23h   |   341-413     | sustained 8-9%/hr plateau
  peak: 22h UTC = 413 (9.4%)
```

No dominant session window for delta_extreme. The distribution reflects the continuous 12-hour evaluation cadence rather than any session-specific pattern. The 15h dip likely corresponds to a brief run interruption or lower market activity period.

**Implication:** delta_extreme is a structural feature of the oracle-near-PTB condition, not a session-timing artifact. Fixing it requires addressing the formula, not shifting session timing.

---

## 8. Spread and Liquidity

```
Spread distribution (true-extreme):
  spread = 0.01 (minimum):  3004 / 3326 = 90.3%
  spread = 0.02:              172 (5.2%)
  spread = 0.03:               62 (1.9%)
  spread ≥ 0.04:               88 (2.6%)

Liquidity (bid+ask top-of-book, true-extreme):
  median = 76.4 USDC
  mean   = 199.2 USDC
  bid+ask < 100 USDC (thin): 1,900 / 3,326 = 57.1%
```

**Spread is NOT the driver.** 90.3% of true-extreme rows have the minimum 0.01 spread — spread makes no contribution to `quality_factor` (threshold is ≥ 0.04).

**Thin liquidity IS a significant amplifier.** 57.1% of true-extreme rows have thin orderbooks (< 100 USDC total). This adds `quality_factor += 0.20` (→ 1.20), pushing the EXTREME threshold from 171s to 246s remaining — cutting the available entry window by 55 additional seconds.

---

## 9. Overlap with Other Block Reasons

| Overlap | Count | Interpretation |
|---|---|---|
| delta_extreme AND time_unsafe (same candidate_id) | 292 candidates | Candidate first seen mid-window → delta_extreme; not entered; seen again near close → time_unsafe |
| delta_extreme AND empty_book (same candidate_id) | 0 candidates | Mutually exclusive: empty_book fires before reaching the delta gate |
| delta_extreme AND risk_plan_zero (same candidate_id) | 44 candidates | Candidate passed delta in some cycles (when delta wasn't extreme) but then failed at sizing |
| delta_extreme AND confidence_too_low (same candidate_id) | 334 candidates | Candidate had low confidence in some evaluations, delta_extreme in others |

The 292 delta_extreme / time_unsafe overlap confirms the two-mechanism narrative: the same candidate is repeatedly evaluated, blocked by delta_extreme early in the window, and eventually blocked by time_unsafe when the 90s gate engages.

---

## 10. Root Cause Summary

```
root_cause: STRUCTURAL — closeness_factor formula produces EXTREME regime
            for all typical BTC/ETH 5-minute market conditions

Two-mechanism breakdown:
  Mechanism A (timing gate, 24.3%):
    Hard-coded block at time_remaining <= 90s.
    Working as designed. delta_multiplier=0.0.
    No change indicated.

  Mechanism B (closeness-driven, 75.7%):
    closeness_factor minimum clamp of 0.0003 means:
    - Any oracle within 0.15% of PTB -> closeness_factor = 4.0 (maximum)
    - For BTC: within $104; for ETH: within $3
    - 93.8% of Mechanism B rows are at this maximum
    - EXTREME threshold (delta_score > 4.0) reached at:
        normal liquidity: time_remaining < 171s (2:49 window remaining)
        thin liquidity (57.1% of rows): time_remaining < 246s (4:06 remaining)
    - Result: effective entry window is only 54-129 seconds per 5-minute cycle

Key compound finding:
  - 57.1% of true-extreme rows have thin liquidity (bid+ask < 100 USDC)
  - Thin liquidity both (a) amplifies delta_score via quality_factor += 0.20
    AND (b) reduces model confidence → confidence_too_low overlap
  - The oracle being near PTB (most common 5-min condition) + thin liquidity =
    EXTREME from the first 54 seconds of every window cycle

EV impact:
  - 1,457 non-zero EV rows (mean EV=0.2507) blocked by delta_extreme
  - All 1,457 have confidence >= 0.54 (passed the confidence gate)
  - 231 of these (15.9%) are in the early-window zone (secs >= 171)
    where entry logic could otherwise proceed
```

---

## 11. Recommended Next Audit

```
recommended_next_audit:
  NAME: closeness_factor_sensitivity_probe

  GOAL:
    Quantify how many additional entries become possible — and what their
    EV and outcome look like — under alternative closeness_factor formulas.

  SPECIFIC QUESTIONS:
    1. If the minimum clamp in _distance_pct is raised from 0.0003 to 0.001,
       how many mid-window rows exit EXTREME regime?
    2. What is the actual EV/outcome distribution of the 231 non-zero EV rows
       in the early-window zone (secs >= 171)?
    3. Does separating thin_liquidity blocking from closeness_factor
       (i.e., liquidity as a separate gate rather than quality_factor amplifier)
       improve entry frequency without increasing realized loss rate?
    4. What is the oracle distance from PTB distribution across ALL sessions
       (not just the source run) — is 0.15% threshold consistently too tight?

  METHOD:
    Read-only replay of the source run decision log using the existing
    tools/no_entry_root_cause_report.py, augmented with a closeness_factor
    counterfactual (mock delta engine with relaxed clamp).
    No live trading, no code deployment, operator review required before
    any parameter change.

  SAFETY:
    No runtime mutation.
    No code change from this audit.
    Operator approval required before any threshold adjustment.
```

---

## Appendix: Delta Engine Formula Reference

```python
# delta_engine.py — estimate_micro_delta()

# Hard gate (Mechanism A):
if time_remaining <= 90:
    return MicroDeltaResult(delta_score=10.0, regime=EXTREME, multiplier=0.0)

# Main score (Mechanism B):
distance_pct    = abs(window_delta_dollars) / ptb_price
closeness_factor = clamp(0.006 / max(distance_pct, 0.0003), 0.25, 4.0)
#                                              ↑ minimum clamp 0.0003
#                                               means any distance < 0.15%
#                                               gives closeness_factor = 4.0

time_factor      = clamp(sqrt(300.0 / max(time_remaining, 1)), 0.75, 2.0)
volatility_factor= clamp(0.75 + (volatility / 0.02), 0.75, 2.5)
velocity_factor  = clamp(1.0 + (velocity / 0.004), 1.0, 2.5)

quality_factor   = 1.0
if spread >= 0.08: quality_factor += 0.20   # spread contribution
elif spread >= 0.04: quality_factor += 0.10
if liquidity < 100: quality_factor += 0.20  # thin liquidity contribution
elif liquidity < 500: quality_factor += 0.10

delta_score = closeness_factor * time_factor * volatility_factor
            * velocity_factor * quality_factor

# EXTREME when delta_score > 4.0
# classify_delta_regime: <=1.0=LOW, <=2.0=NORMAL, <=4.0=HIGH, >4.0=EXTREME
```

**EXTREME threshold with closeness_factor=4.0 and minimum conditions:**
- time_remaining < 171s (normal liquidity)
- time_remaining < 246s (thin liquidity, quality_factor=1.20)
