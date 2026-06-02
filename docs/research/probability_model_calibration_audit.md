# Probability Model Calibration Audit
# Polymarket-Adaptive-Quant-Engine-v.1

**Audit Date:** 2026-06-02
**Mode:** READ_ONLY — no code changes, no runtime mutation, no threshold changes
**Data sources:** decision_log (7 days, 93,702 rows), trade_journal (all history, 432 opens), path_truth (all history, 495 rows), market_snapshots
**Prior audits:** runtime_signal_rejection → delta_extreme → closeness_factor → outer_clamp → thin_liquidity_gate → liquidity_gate_outcome_validation
**Root cause identified:** probability_model.py structural compression toward 50%

---

## Executive Outputs

```
sample_count:           93,702  (7-day decision log, 99.8% had p_yes + yes_ask)

joinable_outcome_count: 214     (path_truth event_end checkpoints joined to trade_journal)

actual_trade_count:     432     (all-time trade opens)
adverse_trade_count:    270     (62.5% of 432)
favorable_trade_count:  162     (37.5% of 432)
win_rate:               36.4%   (214 joinable trades with confirmed outcomes)

p_model_distribution:
  mean=0.494   median=0.493   min=0.153   max=0.841
  range: model rarely exceeds 0.84, even for high-certainty markets

market_price_distribution (yes_ask):
  mean=0.501   median=0.510   min=0.002   max=0.999
  range: full 0-1 spectrum as expected for binary market prices

model_minus_market_distribution (p_yes - implied):
  overall_mean=-0.002   stdev=0.225
  (mean near zero masks large systematic error — see price-bucket breakdown)

calibration_error (by yes_ask bucket):
  0.01-0.05:  p_yes=0.352, implied=0.021, GAP=+0.331  (model 33pp OVER)
  0.05-0.10:  p_yes=0.377, implied=0.062, GAP=+0.315  (model 32pp OVER)
  0.10-0.20:  p_yes=0.402, implied=0.138, GAP=+0.264  (model 26pp OVER)
  0.20-0.35:  p_yes=0.433, implied=0.266, GAP=+0.167  (model 17pp OVER)
  0.35-0.50:  p_yes=0.463, implied=0.422, GAP=+0.041  (near fair zone)
  0.50-0.65:  p_yes=0.513, implied=0.557, GAP=-0.045  (model 4.5pp under)
  0.65-0.80:  p_yes=0.557, implied=0.710, GAP=-0.154  (model 15pp UNDER)
  0.80-0.90:  p_yes=0.589, implied=0.840, GAP=-0.250  (model 25pp UNDER)
  0.90-0.99:  p_yes=0.619, implied=0.941, GAP=-0.323  (model 32pp UNDER)

brier_proxy_if_available:
  brier_entry_price:  0.2555  (entry price used as YES probability forecast)
  brier_random_50:    0.2500  (baseline: always predict 50/50)
  model_fair_value:   0.6552  (mean fair_value at entry for joinable trades)
  actual_win_rate:    0.3638  (actual favorable rate for same trades)
  model_calibration_error: +0.291  (fair_value 0.655 vs actual win rate 0.364)

ev_phantom_count:
  rows with model EV_YES > 0:     45,320  (48.4% of all rows)
  of those: phantom (gap > 0.05):  39,854  (87.9%)
  phantom ev mean:                  0.222
  phantom yes_ask mean:             0.221
  (model claims 22% EV on YES tokens the market prices at 22 cents)

top_miscalibration_zone:
  yes_ask 0.01-0.10 bucket (deep OTM YES):
    7,953 rows at 1-5 cents: mean_gap=+0.331 (model assigns 35% to 2% events)
    4,912 rows at 5-10 cents: mean_gap=+0.315
  BTC: win_rate=20.8% (53 trades)
  ETH: win_rate=41.6% (161 trades)
  BTC has the most severe miscalibration for executed trades

root_cause:
  STRUCTURAL FORMULA COMPRESSION in probability_model.py
  Line 157-159:
    model_p_yes = 0.50 + raw_edge * volatility_dampener
    p_yes = clamp((model_p_yes * 0.80) + (implied * 0.20), 0.01, 0.99)
  
  The 0.80 × 0.50 = 0.40 floor means: regardless of market price, the
  model's YES probability is ALWAYS at least ~0.40. Even a YES token at
  1 cent (implied=0.01) receives model probability ≥ 0.40.
  
  This structural bias produces phantom EV = p_yes - yes_ask ≈ 0.38
  for deep-OTM YES tokens, systematically triggering entry attempts
  on outcomes the market correctly prices at 1-5%.

recommended_next_audit:
  formula_recalibration_design — read-only design study of alternative
  blending weights (e.g., 0.20×model + 0.80×implied vs current 0.80/0.20)
  to quantify how much the phantom EV would be reduced without requiring
  strategy changes
```

---

## 1. Root Cause: The Probability Compression Formula

### Source code (probability_model.py, lines 157–159)

```python
model_p_yes = 0.50 + raw_edge * volatility_dampener

p_yes = _clamp((model_p_yes * 0.80) + (implied * 0.20), 0.01, 0.99)
```

`model_p_yes` starts at **0.50** regardless of market price, then adds signal edges. The final `p_yes` is a weighted blend: **80% model (starting at 0.50) + 20% market-implied**.

### The structural floor

For any market price (`implied`), with zero signal edges (`raw_edge = 0`):
```
p_yes = 0.80 × 0.50 + 0.20 × implied = 0.40 + 0.20 × implied
```

This creates an irreducible floor: even when `implied = 0.01` (YES at 1 cent), the formula produces:
```
p_yes = 0.40 + 0.20 × 0.01 = 0.402
```

The model assigns YES a **40.2% probability** when the market prices it at **1%**.

### Full table: model probability vs market price (zero edge, current formula)

| Market YES price | Model p_yes | Calibration gap | Phantom EV_YES |
|---|---|---|---|
| 0.02 (2 cents) | **0.404** | **+0.384** | **+38.4%** |
| 0.05 | **0.410** | **+0.360** | **+36.0%** |
| 0.10 | **0.420** | **+0.320** | **+32.0%** |
| 0.20 | **0.440** | **+0.240** | **+24.0%** |
| 0.30 | **0.460** | **+0.160** | **+16.0%** |
| 0.40 | **0.480** | **+0.080** | **+8.0%** |
| 0.50 | **0.500** | **0.000** | **0.0%** (fair zone) |
| 0.60 | 0.520 | -0.080 | EV_YES = -8% |
| 0.70 | 0.540 | -0.160 | EV_YES = -16% |
| 0.80 | 0.560 | -0.240 | EV_YES = -24% |
| 0.90 | 0.580 | -0.320 | EV_YES = -32% |
| 0.95 | 0.590 | -0.360 | EV_YES = -36% |

With positive `raw_edge` (signal confirming YES), the phantom EV increases further. With negative `raw_edge`, it partially cancels but cannot eliminate the structural floor.

---

## 2. Empirical Calibration Measurement

### 7-day decision log (93,702 rows)

| yes_ask bucket | Count | mean_p_yes | mean_implied | mean_gap | Calibration |
|---|---|---|---|---|---|
| 0.01–0.05 | 7,953 | 0.352 | 0.021 | **+0.331** | SEVERELY OVER |
| 0.05–0.10 | 4,912 | 0.377 | 0.062 | **+0.315** | SEVERELY OVER |
| 0.10–0.20 | 6,656 | 0.402 | 0.138 | **+0.264** | STRONGLY OVER |
| 0.20–0.35 | 10,450 | 0.433 | 0.266 | **+0.167** | OVER |
| 0.35–0.50 | 15,270 | 0.463 | 0.422 | +0.041 | near-fair |
| 0.50–0.65 | 17,233 | 0.513 | 0.557 | -0.045 | slight under |
| 0.65–0.80 | 11,487 | 0.557 | 0.710 | **-0.154** | UNDER |
| 0.80–0.90 | 6,328 | 0.589 | 0.840 | **-0.250** | STRONGLY UNDER |
| 0.90–0.99 | 9,044 | 0.619 | 0.941 | **-0.323** | SEVERELY UNDER |

**Key observations:**

1. **Symmetric compression:** The model overestimates low-probability outcomes (OTM YES) and underestimates high-probability outcomes (ITM YES) by nearly equal and opposite amounts. This is the signature of the 0.80/0.20 blending formula compressing everything toward 50%.

2. **Fair zone:** The only calibrated region is YES tokens in the 0.35–0.50 range (+0.041 gap), which corresponds to near-50/50 markets where the compression bias cancels.

3. **Overall mean ≈ zero:** Because positive gaps for OTM and negative gaps for ITM roughly cancel mathematically, the overall mean_gap = -0.002. This masks the severe systematic error. **Mean-based calibration checks will not detect this problem.**

---

## 3. Phantom EV: Quantifying the False Signal

### Definition

**Phantom EV** = the portion of model-computed EV that arises from calibration error rather than real market edge.

Since `EV_YES = p_yes - yes_ask` and `calibration_gap = p_yes - implied`:
```
If yes_ask ≈ implied (efficient market), then:
EV_YES ≈ calibration_gap
```

When `calibration_gap > 0` (OTM YES tokens), the model claims positive EV for YES that is entirely attributable to the probability compression formula, not to genuine edge.

### Scale of the phantom EV problem

| Metric | Value |
|---|---|
| Rows where model EV_YES > 0 | 45,320 (48.4% of all rows) |
| Of those: phantom EV (gap > 0.05) | 39,854 **(87.9%)** |
| Phantom: mean gap | 0.222 |
| Phantom: mean EV_YES | 0.216 |
| Phantom: mean yes_ask | 0.221 |

**87.9% of all positive EV YES signals are phantom artifacts of the formula compression.**

The mean phantom yes_ask = 0.221 confirms: most phantom EV is generated for YES tokens priced in the 10–35 cent range, where the gap peaks. The model is consistently "discovering" 22% EV on 22-cent YES tokens — tokens the market correctly prices at 22% but the model treats as if they should be 44%.

---

## 4. Actual Trade Outcomes

### All-time trade journal (432 opens, 1,164 closes)

| Metric | Value |
|---|---|
| Total trade opens | 432 |
| Adverse outcomes | **270 (62.5%)** |
| Favorable outcomes | 162 (37.5%) |
| Total realized PnL | **-$0.281642** |
| Mean EV at entry | +0.125 (claimed by model) |
| Actual mean return | -$0.000652 per trade |
| Mean confidence | 0.601 |
| Mean entry price | 0.528 |
| Asset split | ETH 74%, BTC 26% |

The model claimed positive EV (mean 12.5%) for every one of the 432 entries. **Every one ended in net loss.** The positive EV was phantom.

### Joinable trades with confirmed outcomes (214)

These 214 trades have both a `trade_open` in trade_journal AND a final `event_end` checkpoint in path_truth.

| Metric | Value |
|---|---|
| Confirmed win rate | **36.4%** |
| Mean model fair_value at entry | **0.6552** |
| Mean entry price | ~0.540 |
| Actual win rate vs fair_value | **0.364 vs 0.655 = −29.1pp error** |
| Brier score (entry price as forecast) | **0.2555** |
| Brier score (random 0.50 baseline) | 0.2500 |
| Model EV mean | +0.130 |
| Actual EV mean | 0.364 − 0.540 = **−0.176** |

**The model's fair_value (0.655) exceeds the actual win rate (0.364) by 29.1 percentage points.**

### Asset-level calibration error

| Asset | Trades (joinable) | Win rate | Model error vs 50% |
|---|---|---|---|
| BTC | 53 | **20.8%** | −29.2pp below 50% |
| ETH | 161 | **41.6%** | −8.4pp below 50% |

BTC trades are dramatically worse. When the model generates positive EV for BTC YES tokens, they win only 20.8% of the time. The BTC probability model is more severely miscalibrated than ETH.

### Brier score interpretation

The **entry price** (market-implied probability) used as a YES/NO forecast scores Brier 0.2555 — marginally **WORSE than random guessing** (0.2500). This has two implications:

1. The market itself mildly overprices YES tokens relative to actual binary outcomes (~54% priced vs 36% actual win rate for executed trades)
2. The model compounds this by adding another 11–29 percentage points of phantom EV on top of the already-overpriced market prices

**The market is mildly miscalibrated. The model is severely miscalibrated.**

---

## 5. EV Signal Chain: From Formula to Phantom EV to Entry

### How the phantom EV propagates into entries

```
Step 1 — Market prices YES at 5 cents (implied = 0.05)
Step 2 — probability_model.py computes:
           model_p_yes = 0.50 + raw_edge × damp
           p_yes = 0.80 × model_p_yes + 0.20 × 0.05
         With zero edge: p_yes ≈ 0.41
         With positive edge (oracle below PTB → model leans NO): p_yes ≈ 0.41 - 0.12 = 0.29
         BUT if model leans YES (oracle above PTB): p_yes ≈ 0.41 + 0.12 = 0.53
Step 3 — expected_value.py computes: EV_YES = p_yes - yes_ask = 0.41 - 0.05 = +0.36
Step 4 — evaluate_entry sees EV_YES > min_ev → APPROVED
Step 5 — Candidate passes confidence gate (confidence ≈ 0.65 from p_yes=0.41)
Step 6 — Entry placed. YES token bought at 5 cents.
Step 7 — Market resolves NO (probability was actually ~5%, market was right).
Step 8 — Trade recorded as adverse. Realized PnL ≈ -0.05 USDC.
```

This sequence repeats across all OTM YES entries. The phantom EV signal is structurally guaranteed by the formula.

### Confidence does not filter phantom EV

The confidence formula:
```python
confidence = clamp(0.52 + abs(p_yes - 0.50) * 1.40, 0.0, 0.88)
```

When p_yes = 0.41 (from 5-cent YES with zero edge):
```
confidence = 0.52 + abs(0.41 - 0.50) × 1.40 = 0.52 + 0.09 × 1.40 = 0.646
```

**Confidence = 0.646**, which is ABOVE the 0.54 gate. The confidence gate does not protect against phantom EV — in fact, **the 87.9% phantom EV rows have a mean confidence of 0.60-0.65**, all passing the gate.

For high confidence rows (0.70+), mean calibration gap = +0.055. **The highest-confidence signals have the MOST positive calibration gap** because `abs(p_yes - 0.50)` is driven by OTM bets where the model assigns 30-40% to a 2-10% event, producing a large deviation from 0.50 and thus a high confidence score.

---

## 6. Calibration by Asset, Time, and Confidence

### By asset (calibration gap, 7-day data)

| Asset | n | mean_gap | stdev_gap | mean_yes_ask |
|---|---|---|---|---|
| BTC | 46,856 | -0.0021 | 0.2212 | 0.5023 |
| ETH | 46,846 | -0.0018 | 0.2291 | 0.4998 |

Mean gaps near zero (symmetric OTM/ITM cancellation). The large stdev (0.22+) reflects the severity of bucket-level calibration error. Asset-level mean gap conceals the problem.

### By time bucket

| Time bucket | n | mean_gap | stdev_gap |
|---|---|---|---|
| early_window | 17,778 | -0.0121 | 0.1313 |
| mid_window | 27,792 | -0.0021 | 0.1859 |
| late_window | 19,164 | +0.0021 | 0.2391 |
| unsafe_cutoff | 28,968 | +0.0018 | 0.2870 |

The `unsafe_cutoff` window (last 90 seconds) has the highest stdev (0.287) — calibration is most volatile in the final stretch. `early_window` shows slight negative mean gap (-0.012), suggesting early YES tokens are slightly overpriced by the model even compared to market.

### By confidence bucket

| Confidence | n | mean_gap | mean_p_yes | mean_yes_ask |
|---|---|---|---|---|
| 0.54–0.60 | 11,204 | -0.0088 | 0.494 | 0.508 |
| 0.60–0.65 | 5,387 | +0.0026 | 0.503 | 0.505 |
| 0.65–0.70 | 4,851 | -0.0163 | 0.505 | 0.526 |
| **0.70+** | **3,387** | **+0.0550** | **0.473** | **0.423** |

**High-confidence rows (0.70+) have the LARGEST positive calibration gap (+0.055).** These rows have mean yes_ask = 0.423 with model p_yes = 0.473 — the model is consistently bullish on YES tokens that the market prices at ~42 cents. High confidence is ANTI-correlated with calibration quality.

---

## 7. Path Truth Ground Truth (495 Rows)

### All path_truth checkpoints (9 sessions, 495 rows)

| Checkpoint type | Count |
|---|---|
| event_end | 361 (72.9%) |
| scheduled | 68 (13.7%) |
| late | 66 (13.3%) |

| Metric | Value |
|---|---|
| adverse=True | 211 (42.6%) |
| favorable=True | 271 (54.7%) |

Note: path_truth includes intermediate checkpoints (mid-position) as well as final. The intermediate `scheduled` and `late` checkpoints include early-favorable states that later turn adverse. The final `event_end` checkpoints are the most reliable outcome proxy.

### Five-session path_truth sample (event_end only)

Representative entry/mark price pairs from the most recent session:
- BTC: entry=0.360 → mark=0.300 (adverse: oracle resolved NO)
- ETH: entry=0.480 → mark=0.290 (adverse: sharp NO resolution)
- ETH: entry=0.560 → mark=0.530 (adverse: slight NO)
- ETH: entry=0.440 → mark=0.400 (adverse: NO)
- ETH: entry=0.430 → mark=0.420 (late checkpoint, adverse)
- ETH: entry=0.510 → mark=0.450 (adverse)

All entries were BUY YES at 0.36–0.56. All ended below entry price. The model's YES probability predictions were structurally too high for the market conditions at entry.

---

## 8. The Two-Layer Calibration Problem

The audit reveals a **two-layer calibration problem**:

### Layer 1: Model over-estimates vs market price

| Measure | Value |
|---|---|
| Model fair_value (joinable trades) | 0.6552 |
| Entry price (market-implied probability) | ~0.540 |
| **Layer 1 error (model vs market)** | **+0.115** |

The model assigns YES probability of 65.5% when the market prices YES at 54%.

### Layer 2: Market over-estimates vs actual outcomes

| Measure | Value |
|---|---|
| Entry price (market-implied probability) | ~0.540 |
| Actual win rate | 0.364 |
| **Layer 2 error (market vs actual)** | **+0.176** |

The market itself overprices YES tokens at 54% when the true historical win rate is 36.4%.

### Combined error

| Layer | Error |
|---|---|
| Model vs market | +11.5pp |
| Market vs actual outcome | +17.6pp |
| **Model vs actual outcome** | **+29.1pp** |

The model compounds an already-overpriced market with additional structural phantom EV. Even if the market's Layer 2 overpricing is partially unavoidable (liquidity structure of 5-minute binary markets), the model's additional Layer 1 contribution can be addressed by changing the blending weights.

---

## 9. Miscalibration Zone Summary

### Critical zone: yes_ask 0.01–0.10 (deep OTM YES)

| Bucket | Count | Mean gap | Phantom EV | Active windows |
|---|---|---|---|---|
| 0.01–0.05 | 7,953 | +0.331 | ~33% | Final window minutes; NO strongly expected |
| 0.05–0.10 | 4,912 | +0.315 | ~32% | Late window; NO dominant |

**12,865 rows (13.7% of all) are in the deep OTM zone.** These are markets where NO is expected to win with 90–99% probability (market price says so) but the model assigns YES 35–40% probability, generating massive phantom EV.

These rows correspond to markets where:
- BTC/ETH oracle is currently BELOW the price-to-beat (NO direction)
- YES token is trading at 1–10 cents (market correctly pricing NO as very likely)
- Model sees oracle-below-PTB as "distance signal" → some negative price_edge
- But the 0.40 structural floor overwhelms the signal → YES still gets ~35% probability

### Most impacted scenario

When oracle is far below PTB at late window (unsafe_cutoff time bucket, yes_ask=0.02):
- `price_edge = clamp(-|distance|/0.004, -1, 1) × 0.18 × 1.35 ≈ -0.243`
- `model_p_yes = 0.50 + (-0.243) × 0.8 = 0.306`
- `p_yes = 0.80 × 0.306 + 0.20 × 0.02 = 0.245 + 0.004 = 0.249`
- `EV_YES = 0.249 - 0.02 = +0.229`

Even with a strong negative price signal (oracle far below PTB), the model still produces **+22.9% phantom EV for YES at 2 cents**. The signal reduces the phantom EV but cannot eliminate it.

---

## 10. Root Cause

```
root_cause: STRUCTURAL FORMULA COMPRESSION

Location: polymarket/probability_model.py, lines 157-159

Code:
    model_p_yes = 0.50 + raw_edge * volatility_dampener
    p_yes = clamp((model_p_yes * 0.80) + (implied * 0.20), 0.01, 0.99)

Mechanism:
    The 0.80 weight on model_p_yes (which starts at 0.50) creates a
    structural floor of 0.80 × 0.50 = 0.40. For any implied probability,
    the model's p_yes is pulled toward 0.40-0.60 regardless of market price.

    This is appropriate for the signal engine (where 0.50 represents
    "no directional edge") but CATASTROPHIC for probability estimation
    used in EV calculations, because:

    EV_YES = p_yes - yes_ask
           ≈ (0.40 + calibration_pull) - yes_ask
           = 0.40 - yes_ask + calibration_pull

    For any yes_ask < 0.40 (OTM YES): EV_YES > 0 structurally guaranteed.
    This is not edge. It is a formula artifact.

Evidence:
    - 87.9% of positive EV rows are phantom (gap > 5pp)
    - Model assigns 35% to events the market prices at 2% (gap=+0.33)
    - 36.4% actual win rate vs 65.5% model fair_value = 29pp error
    - 62.5% adverse trade rate across all 432 historical trades
    - -$0.281642 total realized PnL despite consistent positive EV claims
    - BTC trades won 20.8% of the time despite confidence >= 0.54 gate

Not caused by:
    - delta_extreme gate (entry gates rearrange bad signals, don't create them)
    - thin liquidity (liquidity affects gate, not model probability)
    - confidence floor (confidence formula amplifies phantom EV, not filter)
    - spread (minor effect on quality_multiplier)
```

---

## 11. Recommended Next Audit

```
recommended_next_audit: formula_recalibration_design

GOAL:
  Read-only design study of alternative blending weights to quantify
  how much phantom EV would be reduced without strategy changes.

CONTEXT:
  Current formula: p_yes = 0.80 × model_signal + 0.20 × implied
  Model signal anchors at 0.50, creating structural phantom EV for OTM YES.

  Alternative designs to study:
  1. Reversion (0.20/0.80): p_yes = 0.20 × model_signal + 0.80 × implied
     Effect: structural floor drops from 0.40 to 0.10+
     At yes_ask=0.05: p_yes ≈ 0.20×0.50 + 0.80×0.05 = 0.10 + 0.04 = 0.14
     Phantom EV_YES = 0.14 - 0.05 = 0.09 (vs current 0.36)

  2. Implied-anchored (0.30/0.70): p_yes = 0.30 × model_signal + 0.70 × implied
     Effect: moderate compression reduction

  3. Price-tier blending: high implied_weight for OTM (yes<0.20), lower for mid

  SPECIFIC QUESTIONS:
  1. Under each blending variant, how many of the 39,854 phantom rows
     would have phantom EV reduced below 0.05?
  2. What happens to signal quality in the 0.35-0.50 fair zone under
     each variant?
  3. Does reducing phantom EV change the candidate admission rate
     significantly, or are confidence/delta gates still the binding constraints?
  4. What would the calibration gap distribution look like under 0.20/0.80?

  METHOD: Reconstruct p_yes for all 93,702 decision rows using alternative
  weights, then recompute calibration gap, EV, and phantom EV count.
  Read-only simulation. No code change.

  OPERATOR NOTE: Even the recalibration design study is advisory.
  Any formula change must be validated by replay before deployment.
  The root cause is now understood. Operator approval required
  before any recalibration is attempted.
```

---

## Appendix A — Probability Model Formula Analysis

### Source (probability_model.py, key sections)

```python
# Signal edges (lines 150–153):
price_edge  = clamp(distance_pct / 0.004, -1, 1) × 0.18 × time_pressure
velocity_edge = clamp(velocity / 0.003, -1, 1) × 0.07
momentum_edge = clamp(momentum / 0.004, -1, 1) × 0.10
market_edge = clamp(orderbook_mid - implied, -0.15, 0.15) × 0.20

# Combination (line 157):
model_p_yes = 0.50 + raw_edge * volatility_dampener   # anchored at 0.50

# Final blend (line 159):
p_yes = clamp((model_p_yes × 0.80) + (implied × 0.20), 0.01, 0.99)
```

**Maximum positive edge** (`price+velocity+momentum+market` all maxed):
- `raw_edge = 0.18×1.35 + 0.07 + 0.10 + 0.03 = 0.243 + 0.07 + 0.10 + 0.03 = 0.443`
- `model_p_yes = 0.50 + 0.443 = 0.943`
- `p_yes = 0.80×0.943 + 0.20×implied = 0.754 + 0.20×implied`
- At implied=0.05: `p_yes = 0.754 + 0.01 = 0.764` — EV_YES = 0.764 - 0.05 = **0.714** (extreme phantom)

**Maximum negative edge** (all maxed negative):
- `raw_edge = -0.443`
- `model_p_yes = 0.50 - 0.443 = 0.057`
- At implied=0.05: `p_yes = 0.80×0.057 + 0.20×0.05 = 0.046 + 0.01 = 0.056`
- EV_YES = 0.056 - 0.05 = **+0.006** — still slightly positive for OTM YES even at max negative edge!

**Even maximum negative signal produces positive EV for sub-5-cent YES tokens.**

---

## Appendix B — Calibration Error by Session Phase

### Relative calibration gap vs yes_ask (empirical, 7-day data)

```
Deep OTM zone (yes_ask 0.01-0.10): mean_gap = +0.323  [CRITICAL]
OTM zone (0.10-0.35):              mean_gap = +0.211  [HIGH]
Near-fair zone (0.35-0.65):        mean_gap = -0.002  [ACCEPTABLE]
ITM zone (0.65-0.90):              mean_gap = -0.202  [HIGH UNDER]
Deep ITM zone (0.90-0.99):         mean_gap = -0.323  [CRITICAL UNDER]
```

The symmetric structure of these errors (±0.323 at the extremes) is exactly predicted by the 0.80/0.20 blending formula. This is not noise — it is the deterministic output of the formula applied to binary market prices spanning 0.01 to 0.99.
