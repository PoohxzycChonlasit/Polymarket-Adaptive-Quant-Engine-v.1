# PTB Distance Saturation and Confidence Inversion Audit

audit_date: 2026-06-02
mode: read_only_ptb_confidence_audit
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Executive Summary

PTB distance saturation is a plausible cause of midprice directional mis-ranking. In joined event-end outcomes where distance evidence was recoverable, saturated PTB-distance rows were adverse-heavy, while non-saturated distance rows were small but favorable-heavy. Confidence also appears inverted in midprice rows: high-confidence rows are mostly adverse, with the worst inversion slice at BTC NO 35-50c.

Required outputs:

```text
distance_feature_count: 2 distance-derived mechanisms inspected
  1. PTB distance input to price_edge
  2. confidence distance from p=0.50
saturation_slice_count: 11
confidence_inversion_count: 23 high-confidence adverse rows
worst_inversion_slice: BTC NO 0.35-0.50 confidence 0.70+
side_bias: NO worse than YES
asset_bias: BTC worse than ETH
price_bucket_bias: 0.35-0.50 worst robust bucket
dominant_saturation_mode: distance clipped near +/-0.020 creates strong directional edge without velocity/momentum confirmation
dominant_confidence_failure_mode: confidence rewards probability extremity, not outcome quality
recommended_next_audit: Distance Feature Serialization and Anti-Confidence Gate Design Audit
```

No runtime change is recommended from this audit.

## Data Inspected

Inputs:

- `polymarket/probability_model.py`
- feature serialization references in `polymarket/trader.py`
- `runtime/quant_data/decision_log/*.jsonl`
- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- market snapshot fields carried into decision/trade rows

Joined sample:

```text
event_end_joinable_outcomes: 125
decision_enriched_join_count: 124
distance_observed_count: 44
saturated_distance_count: 37
non_saturated_distance_count: 7
```

## How PTB Distance Contributes to Raw Edge

The probability model converts PTB distance into the largest single additive edge:

```text
distance_pct = clamp(distance_pct, -0.02, +0.02)
price_edge = clamp(distance_pct / 0.004, -1, +1) * 0.18 * time_pressure
```

This means distance reaches full directional contribution once absolute distance is at least 0.004. Because `distance_pct` itself is clipped at +/-0.02, many rows serialize as:

```text
distance=-0.02000
distance=+0.02000
```

Those values represent saturated distance evidence. In the joined sample, velocity and momentum were usually zero, so distance was often the only visible directional feature.

## Where PTB Distance Saturates

Distance-observed rows:

```text
saturated: 37 rows
non_saturated: 7 rows
```

Outcome split:

```text
saturated distance: 12 favorable / 25 adverse = 32.4%
non_saturated distance: 5 favorable / 2 adverse = 71.4%
```

The non-saturated sample is too small to trust by itself, but the contrast is clear enough to treat saturation as a failure lead.

Worst saturated slices:

```text
BTC NO 0.35-0.50 confidence 0.70+: 0 favorable / 4 adverse
BTC YES 0.50-0.65 confidence 0.70+: 0 favorable / 2 adverse
BTC YES 0.35-0.50 confidence 0.70+: 0 favorable / 1 adverse
ETH YES 0.50-0.65 confidence 0.55-0.60: 1 favorable / 5 adverse
ETH NO 0.50-0.65 confidence <0.55: 1 favorable / 4 adverse
```

The worst saturation behavior appears in BTC and midprice slices.

## Does Confidence Increase When It Should Decrease?

Yes, in several midprice slices. The model computes confidence from distance away from 50:

```text
confidence = 0.52 + abs(p_yes - 0.50) * 1.40
```

This rewards probability extremity. If the probability is extreme because PTB distance saturated in the wrong direction, confidence becomes an amplifier of a bad signal.

High-confidence outcomes:

```text
confidence >= 0.70: 8 favorable / 23 adverse = 25.8%
midprice high confidence: 7 favorable / 23 adverse = 23.3%
```

Worst inversion slice:

```text
BTC NO 0.35-0.50 confidence 0.70+
0 favorable / 9 adverse = 0.0%
```

This is the clearest confidence inversion evidence in the sample.

## Is Midprice Confidence Inverted?

The midprice result is adverse-heavy:

```text
0.35-0.50: 6 favorable / 22 adverse = 21.4%
0.50-0.65: 41 favorable / 53 adverse = 43.6%
```

High-confidence midprice rows are worse:

```text
midprice confidence >= 0.70: 7 favorable / 23 adverse = 23.3%
```

The `0.35-0.50` bucket is the worst robust price bucket. It is especially dangerous when paired with BTC, NO, or high confidence.

## BTC and NO Failure Evidence

Side map:

```text
NO: 29 favorable / 51 adverse = 36.3%
YES: 20 favorable / 25 adverse = 44.4%
```

Asset map:

```text
BTC: 6 favorable / 20 adverse = 23.1%
ETH: 43 favorable / 56 adverse = 43.4%
```

Worst BTC/NO confidence slice:

```text
BTC NO 0.35-0.50 confidence 0.70+
0 favorable / 9 adverse
```

This supports the hypothesis that BTC/NO failures are driven by directional confidence mis-ranking. The model is most wrong where it appears most confident.

## Evidence Supporting Saturation Hypothesis

Evidence:

```text
1. Distance is the largest additive feature in probability_model.py.
2. Serialized model reasons often show distance exactly at +/-0.02000.
3. Saturated distance rows are adverse-heavy: 12 favorable / 25 adverse.
4. Non-saturated distance rows are small but favorable-heavy: 5 favorable / 2 adverse.
5. Velocity and momentum are often zero in serialized reasons.
6. Volatility dampener is near 1.0, so it does not suppress saturated distance.
7. High-confidence rows are adverse-heavy.
```

Interpretation:

PTB distance saturation can create a strong directional push without confirming movement evidence. The confidence formula then promotes that pushed probability as more trustworthy.

## Evidence Missing

Missing or weak evidence:

```text
exact raw_edge not serialized
exact price_edge, velocity_edge, momentum_edge, and market_edge not serialized
distance available on only 44 joined outcomes
time_remaining incomplete on joined rows
oracle movement at entry and event_end not consistently joinable
PTB distance source is not uniformly carried from decision to path_truth
market snapshots are contextual, not a complete event-end feature join
```

The audit supports a strong hypothesis, not a deployable rule.

## Findings

### Dominant Saturation Mode

The dominant saturation mode is:

```text
distance reaches +/-0.02000, price_edge saturates, velocity and momentum provide no confirmation, volatility dampener remains near 1.0
```

This can overstate directional edge in midprice BTC/NO rows.

### Dominant Confidence Failure Mode

The dominant confidence failure mode is:

```text
confidence increases with distance from 50 even when distance-from-50 is caused by saturated PTB edge
```

The model treats extremity as confidence. The joined outcomes show extremity can be an anti-signal.

### Side Bias

NO-side rows are worse than YES-side rows:

```text
NO false-positive risk: 63.7%
YES false-positive risk: 55.6%
```

### Asset Bias

BTC is materially worse than ETH:

```text
BTC false-positive risk: 76.9%
ETH false-positive risk: 56.6%
```

### Price Bucket Bias

The worst robust price bucket is:

```text
0.35-0.50 false-positive risk: 78.6%
```

The `0.50-0.65` bucket is mixed and cannot be globally blocked without losing favorable ETH YES rows.

## Recommendation

Do not change runtime behavior. Treat PTB distance saturation and confidence inversion as the next research target. A safe design would need better feature serialization and a replay-free validation set before any formula or gate proposal.

## Recommended Next Audit

recommended_next_audit:

```text
Distance Feature Serialization and Anti-Confidence Gate Design Audit
```

Scope:

```text
1. Verify exact feature serialization gaps for raw_edge and its components.
2. Design advisory-only anti-confidence diagnostics for BTC/NO midprice rows.
3. Compare saturated vs non-saturated PTB distance by asset, side, and price bucket.
4. Inspect whether confidence >= 0.70 should be treated as risk in BTC/NO midprice slices.
5. Preserve read-only mode until feature attribution is complete.
```

No replay, runtime change, strategy change, threshold change, or execution change should occur before that audit.

## Safety Confirmation

runtime_behavior_changed: false
trading_runtime_modified: false
replay_logic_modified: false
runtime_repo_mutated: false
replay_executed: false
strategy_changed: false
threshold_changed: false
execution_changed: false
push_performed: false
