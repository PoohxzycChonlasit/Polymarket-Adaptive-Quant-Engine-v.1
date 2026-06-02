# Probability Model Feature Attribution Audit

audit_date: 2026-06-02
mode: read_only_feature_attribution
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Executive Summary

The joined outcome evidence points to a feature attribution failure, not only a probability blend failure. BTC and NO-side midprice trades are mis-ranked because the model appears to lean heavily on PTB distance saturation while velocity and momentum often contribute no discriminating information. Confidence then rewards probability extremity rather than outcome quality.

Required outputs:

```text
feature_count: 4 additive edge features
attribution_slice_count: 19 primary outcome slices
joinable_outcome_count: 125
decision_enriched_join_count: 124
dominant_bad_feature: distance/PTB edge saturation
dominant_bad_formula_component: 50-anchor raw_edge blend plus confidence-from-distance-to-50
side_specific_failure: YES, but NO is worse at 29 favorable / 51 adverse = 36.3%
asset_specific_failure: BTC at 6 favorable / 20 adverse = 23.1%
price_bucket_specific_failure: 0.35-0.50 at 6 favorable / 22 adverse = 21.4%
confidence_failure_mode: 0.70+ confidence has 8 favorable / 23 adverse = 25.8%
ev_failure_mode: 10-20pp claimed gap has 29 favorable / 45 adverse = 39.2%; larger gap does not improve outcomes
recommended_next_audit: PTB Distance Saturation and Confidence Inversion Audit
```

No runtime conclusion is safe from this audit alone.

## Model Components Inspected

`polymarket/probability_model.py` constructs probability from:

```text
price_edge    = clamp(distance_pct / 0.004, -1, 1) * 0.18 * time_pressure
velocity_edge = clamp(velocity / 0.003, -1, 1) * 0.07
momentum_edge = clamp(momentum / 0.004, -1, 1) * 0.10
market_edge   = clamp(orderbook_mid - implied, -0.15, 0.15) * 0.20

raw_edge = price_edge + velocity_edge + momentum_edge + market_edge
volatility_dampener = clamp(1 - volatility / 0.08, 0.35, 1.0)
model_p_yes = 0.50 + raw_edge * volatility_dampener
p_yes = 0.80 * model_p_yes + 0.20 * implied

confidence = clamp(0.52 + abs(p_yes - 0.50) * 1.40, 0, 0.88)
confidence *= quality_multiplier
```

The key design issue is that confidence increases as the final probability moves away from 50, even when that movement is caused by a saturated or misdirected PTB distance edge.

## Data Inspected

Inputs:

- `polymarket/probability_model.py`
- `polymarket/trader.py` feature serialization references
- `runtime/quant_data/decision_log/*.jsonl`
- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- market snapshot fields carried into decision/trade rows

Joined sample:

```text
event-end joinable outcomes: 125
favorable: 49
adverse: 76
decision-enriched joined rows: 124
```

## Which Features Contribute to Mis-ranking

### Distance / PTB Feature

Distance is the strongest bad-feature candidate. In enriched reason strings, many rows are serialized as:

```text
distance=-0.02000
distance=0.02000
velocity=0.00000
momentum=0.00000
```

That means the distance feature is often clipped at the model's maximum input range while velocity and momentum provide little or no offsetting evidence.

Observed adverse reason examples include:

```text
leans_no;distance=-0.02000;velocity=0.00000;momentum=0.00000;thin_liquidity
leans_yes;distance=0.02000;velocity=0.00000;momentum=0.00000;thin_liquidity
leans_no;distance=-0.02000;velocity=0.00000;momentum=0.00000
leans_yes;distance=0.02000;velocity=0.00000;momentum=0.00000
```

This supports the hypothesis that distance saturation creates directional conviction without enough confirmation.

### Velocity and Momentum

Velocity and momentum do not explain favorable/adverse separation in the joined rows. Where available, both are mostly zero.

```text
favorable velocity mean: near 0
adverse velocity mean: near 0
favorable momentum mean: near 0
adverse momentum mean: near 0
```

This is important: the model has velocity and momentum components, but the joined failures do not show those components acting as useful validators.

### Market Edge

Market edge was only proxy-reconstructable from carried yes/no ask fields. It does not appear to rescue the bad slices. The proxy market edge is small and slightly negative in both favorable and adverse sets.

```text
favorable market_edge_proxy mean: -0.005837
adverse market_edge_proxy mean: -0.003827
```

The market edge component is not the dominant observed failure driver, though exact `market_edge` was not serialized.

### Volatility Dampener

The volatility dampener is effectively inactive in the joined outcome set:

```text
favorable dampener mean: 0.999688
adverse dampener mean: 0.999927
```

This means volatility dampening did not materially reduce bad signals in the joined sample.

## Formula Component Responsibility

### Raw Edge

Exact `raw_edge` is not serialized, but proxy reconstruction shows the critical issue: directional edge often comes from a clipped distance term, while other feature terms are zero or small.

The issue is not simply that raw edge is too large. The issue is that raw edge is not outcome-ranked.

### Implied Blend

The 80/20 model-heavy blend is already known to create phantom EV. This audit adds that even when the blend is reduced or capped in formula simulations, outcome quality remains weak because the surviving midprice direction is mis-ranked.

### Confidence Logic

Confidence is the clearest bad formula component:

```text
0.70+ confidence: 8 favorable / 23 adverse = 25.8%
```

Confidence is not measuring correctness. It is measuring probability extremity after the formula pushes away from 50. In BTC/high-confidence slices, that extremity is adverse-heavy.

## Side-specific Failure

Side map:

```text
YES: 20 favorable / 25 adverse = 44.4%
NO: 29 favorable / 51 adverse = 36.3%
```

The failure is side-specific. NO is worse overall and contains the worst midprice failure slice from the prior audit:

```text
NO 0.35-0.50 with 10-20pp gap: 2 favorable / 9 adverse = 18.2%
```

The model's NO-side confidence appears especially poorly calibrated in midprice rows.

## Asset-specific Failure

Asset map:

```text
BTC: 6 favorable / 20 adverse = 23.1%
ETH: 43 favorable / 56 adverse = 43.4%
```

BTC is the dominant asset-specific failure. The model's distance/edge logic appears much less reliable for BTC than ETH in the joined sample.

This supports separate BTC and ETH feature attribution before any shared formula or threshold change.

## Price-bucket-specific Failure

Price bucket map:

```text
0.35-0.50: 6 favorable / 22 adverse = 21.4%
0.50-0.65: 41 favorable / 53 adverse = 43.6%
<0.35: 2 favorable / 1 adverse = 66.7%, n=3
```

The worst robust failure is `0.35-0.50`. The `0.50-0.65` bucket is mixed: it contains both the best ETH YES slice and many adverse NO/BTC rows.

## EV and Probability Gap Failure Mode

Claimed EV/probability gap does not rank outcomes:

```text
6-10pp gap: 15 favorable / 20 adverse = 42.9%
10-20pp gap: 29 favorable / 45 adverse = 39.2%
20pp+ gap: 5 favorable / 11 adverse = 31.3%
```

The larger the claimed edge, the worse the observed alignment becomes. This is consistent with confidence inversion and PTB distance saturation.

## Liquidity, Spread, and Time

Liquidity:

```text
THIN: 35 favorable / 46 adverse = 43.2%
ACCEPTABLE: 12 favorable / 26 adverse = 31.6%
```

Liquidity does not behave as a simple filter. ACCEPTABLE is worse than THIN in the joined sample.

Spread:

```text
all joined rows are effectively tight-spread rows
```

Spread is not the observed cause of mis-ranking.

Time remaining:

```text
time_remaining is incomplete on joined event-end rows
```

Timing may still matter, but this audit cannot prove it from the available join.

## Evidence Missing

Missing or weak evidence:

```text
exact raw_edge not serialized
exact price_edge, velocity_edge, momentum_edge, market_edge not serialized
probability_model_reason missing on a meaningful subset of joined rows
time_remaining lineage incomplete on joined trade/path rows
oracle movement and PTB distance not consistently available at event_end
market_edge only proxy-reconstructable
feature values are available for fewer rows than outcome labels
```

The audit can identify likely attribution failure but cannot fully decompose every formula term without better feature serialization.

## Conclusion

The dominant bad feature is distance/PTB edge saturation. The dominant bad formula component is confidence logic layered on a 50-anchor raw-edge model. Velocity and momentum are mostly absent as discriminators in joined failures, and volatility dampening is effectively inactive.

The model is not just too loose. It is directionally mis-ranked in BTC and NO-side midprice rows.

## Recommended Next Audit

recommended_next_audit:

```text
PTB Distance Saturation and Confidence Inversion Audit
```

Scope:

```text
1. Focus on BTC and NO-side midprice rows.
2. Compare distance=-0.02000 / +0.02000 saturated rows against non-saturated rows.
3. Split by confidence bucket, especially 0.70+.
4. Reconstruct or serialize exact raw_edge components in read-only analysis if possible from logs.
5. Join PTB distance, oracle movement, and event-end outcome.
6. Test whether confidence should be treated as an anti-signal in BTC/NO midprice slices.
```

No replay, runtime change, threshold change, strategy change, or execution change should occur before that audit.

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
