# Midprice Directional Signal Failure Audit

audit_date: 2026-06-02
mode: read_only_directional_failure_audit
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Executive Summary

Directional selection fails because the model does not rank side quality reliably in midprice markets. The failure is not symmetric: ETH YES has the only modestly favorable cluster, while BTC and NO-side midprice slices are materially adverse. High confidence is especially dangerous in BTC slices.

Required outputs:

```text
success_slice_count: 9
failure_slice_count: 17
best_directional_slice: ETH YES, 0.50-0.65, OPENING_SCAN
best_directional_slice_alignment: 12 favorable / 8 adverse = 60.0%
worst_directional_slice: NO, 0.35-0.50, 10-20pp gap
worst_directional_slice_alignment: 2 favorable / 9 adverse = 18.2%
directional_bias: NO-biased failure; YES is less bad overall
asset_bias: BTC-biased failure; ETH is materially better
lifecycle_bias: ACTIVE_INVENTORY_TRADING has worse rate, OPENING_SCAN has larger count
price_bucket_bias: 0.35-0.50 is the worst robust bucket
dominant_directional_failure_mode: BTC/NO midprice directional edge is mis-ranked, especially at high confidence and 10-20pp claimed gap
recommended_next_audit: Probability Model Feature Attribution Audit
```

No slice is deployment-ready. The best slice is a research lead only.

## Data Inspected

Inputs:

- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- carried trade fields from decision/market context where present

Outcome sample:

```text
joinable_event_end_outcomes: 125
baseline: 49 favorable / 76 adverse
baseline_alignment: 39.2%
```

Fields inspected:

```text
asset, side, lifecycle, price bucket, probability gap, confidence, EV proxy,
liquidity, spread, reconstructed time_remaining, oracle/path mark movement,
PTB distance fields when present, favorable/adverse outcome proxy
```

Important limitation: time, trend, volatility, oracle movement, and PTB fields were incomplete or absent on many joined trade/path rows. This limits causal certainty.

## Where Direction Selection Succeeds

The best repeatable directional slice is:

```text
ETH YES 0.50-0.65 OPENING_SCAN
favorable: 12
adverse: 8
alignment: 60.0%
sample_size: 20
```

Related supportive slices:

```text
ETH YES 0.50-0.65: 15 favorable / 11 adverse = 57.7%
YES 0.50-0.65 with 6-10pp gap: 8 favorable / 6 adverse = 57.1%
ETH YES confidence 0.55-0.60: 10 favorable / 9 adverse = 52.6%
ETH YES OPENING_SCAN: 13 favorable / 12 adverse = 52.0%
ETH YES overall: 17 favorable / 16 adverse = 51.5%
```

Evidence supports a narrow hypothesis: ETH YES in the 50-65c range may sometimes carry useful directional information, especially in OPENING_SCAN. But the sample is small and the edge is not strong enough to trust without additional validation.

## Where Direction Selection Fails

The worst directional slices are:

```text
NO 0.35-0.50 with 10-20pp gap: 2 favorable / 9 adverse = 18.2%
BTC NO ACCEPTABLE liquidity: 2 favorable / 9 adverse = 18.2%
BTC YES confidence 0.70+: 2 favorable / 8 adverse = 20.0%
BTC NO: 3 favorable / 11 adverse = 21.4%
YES 0.35-0.50: 2 favorable / 7 adverse = 22.2%
NO 0.35-0.50: 4 favorable / 13 adverse = 23.5%
BTC YES: 3 favorable / 9 adverse = 25.0%
BTC NO confidence 0.70+: 3 favorable / 10 adverse = 23.1%
NO 0.50-0.65 with 6-10pp gap: 6 favorable / 15 adverse = 28.6%
```

This shows two failure modes:

1. BTC direction selection is poor on both YES and NO.
2. NO-side midprice selection is poor, especially 35-50c and 50-65c with claimed model edge.

## Is Failure Symmetric?

No. It is not symmetric by side or asset.

Side map:

```text
YES: 20 favorable / 25 adverse = 44.4%
NO: 29 favorable / 51 adverse = 36.3%
```

Asset map:

```text
ETH: 43 favorable / 56 adverse = 43.4%
BTC: 6 favorable / 20 adverse = 23.1%
```

The broad outcome set is adverse-heavy overall, but BTC is much worse than ETH and NO is worse than YES.

## YES Bias vs NO Bias

The model is not simply YES-biased. The worst joined directional failure is more NO-biased:

```text
NO 0.35-0.50 with 10-20pp gap: 18.2% alignment
NO 0.50-0.65 with 6-10pp gap: 28.6% alignment
BTC NO: 21.4% alignment
```

YES has failures too, especially BTC YES and YES 35-50c, but the only positive research lead is ETH YES 50-65c.

## Asset Bias

BTC is the dominant asset failure:

```text
BTC overall: 6 favorable / 20 adverse = 23.1%
BTC YES: 3 favorable / 9 adverse = 25.0%
BTC NO: 3 favorable / 11 adverse = 21.4%
BTC YES confidence 0.70+: 2 favorable / 8 adverse = 20.0%
BTC NO confidence 0.70+: 3 favorable / 10 adverse = 23.1%
```

ETH is still not good enough globally, but it is less broken:

```text
ETH overall: 43 favorable / 56 adverse = 43.4%
ETH YES overall: 17 favorable / 16 adverse = 51.5%
ETH YES 0.50-0.65 OPENING_SCAN: 60.0%
```

Evidence supports asset-specific calibration or asset-specific signal attribution before any generic formula change.

## Lifecycle Bias

Lifecycle map:

```text
OPENING_SCAN: 35 favorable / 51 adverse = 40.7%
ACTIVE_INVENTORY_TRADING: 14 favorable / 25 adverse = 35.9%
```

OPENING_SCAN has the larger adverse count, but ACTIVE has worse alignment. The best slice is still OPENING_SCAN, so lifecycle alone cannot be used as a filter.

Interpretation:

- OPENING_SCAN can be good only when paired with ETH YES 50-65c.
- ACTIVE_INVENTORY_TRADING does not rescue BTC or NO-side failures.
- Lifecycle must be interpreted jointly with asset, side, and price bucket.

## Price Bucket Bias

Price bucket map:

```text
0.35-0.50: 6 favorable / 20 adverse = 23.1%
0.50-0.65: 41 favorable / 55 adverse = 42.7%
<0.35: 2 favorable / 1 adverse = 66.7%, n=3 only
```

The strongest danger zone is `0.35-0.50`. The `0.50-0.65` bucket is mixed: it contains both the best ETH YES slice and many adverse NO/BTC slices.

This is the central midprice finding: midprice itself is not uniformly bad, but the model is poor at choosing direction inside midprice ranges.

## Probability Gap, EV, and Confidence

Probability gap map:

```text
6-10pp: 14 favorable / 21 adverse = 40.0%
10-20pp: 30 favorable / 47 adverse = 39.0%
20pp+: 5 favorable / 8 adverse = 38.5%
```

The model's claimed edge does not improve outcome alignment. Larger gaps are not better.

Confidence map:

```text
<0.55: 14 favorable / 25 adverse = 35.9%
0.55-0.60: 25 favorable / 25 adverse = 50.0%
0.65-0.70: 2 favorable / 2 adverse = 50.0%, n=4
0.70+: 8 favorable / 23 adverse = 25.8%
```

High confidence is a failure cluster, especially in BTC. This supports the hypothesis that confidence is measuring extremity or compression artifact, not true outcome quality.

## Liquidity and Spread

Liquidity map:

```text
THIN: 35 favorable / 46 adverse = 43.2%
ACCEPTABLE: 12 favorable / 26 adverse = 31.6%
UNSTABLE: 2 favorable / 3 adverse = 40.0%
STRONG: 0 favorable / 1 adverse = 0.0%, n=1
```

ACCEPTABLE liquidity is worse than THIN in the joined sample, so liquidity is not a simple quality filter.

Spread map:

```text
0-1c: 49 favorable / 76 adverse = 39.2%
```

All joined outcomes were tight-spread rows. Spread is not the visible source of directional failure.

## Time Remaining, Oracle Movement, and PTB Distance

Time remaining, oracle movement, and PTB distance were requested, but joined outcome rows did not consistently carry these fields in a usable way.

Observed limitation:

```text
time_remaining bucket: missing for joined rows after reconstruction
trend_regime: UNKNOWN on joined rows
volatility_regime: UNKNOWN on joined rows
distance_from_ptb_pct: mostly unavailable on joined trade opens
oracle movement fields: not consistently joinable at event_end
```

This prevents a confident conclusion about whether the directional failure is caused by PTB distance, oracle movement, or late/early timing. Those fields need stronger lineage into trade/path rows.

## Evidence Supporting Hypotheses

Hypothesis 1: NO-side signal is weak.

Evidence:

```text
NO overall: 36.3%
NO 0.35-0.50 with 10-20pp gap: 18.2%
NO 0.50-0.65 with 6-10pp gap: 28.6%
```

Hypothesis 2: BTC directional model is weak.

Evidence:

```text
BTC overall: 23.1%
BTC YES: 25.0%
BTC NO: 21.4%
BTC high-confidence slices: around 20-23%
```

Hypothesis 3: high confidence is anti-correlated with outcome quality.

Evidence:

```text
0.70+ confidence: 8 favorable / 23 adverse = 25.8%
BTC YES confidence 0.70+: 2 favorable / 8 adverse = 20.0%
```

Hypothesis 4: ETH YES 50-65c is the only research-positive slice.

Evidence:

```text
ETH YES 0.50-0.65 OPENING_SCAN: 60.0%
ETH YES 0.50-0.65: 57.7%
ETH YES overall: 51.5%
```

## What Failed

Directional selection failed because the model's probability gap and confidence do not rank outcomes. In the worst slices, the model sees 6-20pp of edge, but outcomes are adverse-heavy. This is a signal attribution problem, not only a blending formula problem.

## What Evidence Is Missing

Missing evidence:

```text
complete time_remaining lineage on trade/path joins
PTB distance on joined trade rows
oracle movement at entry and event_end in a common join key
indicator_evidence parsed into numeric features
trend/volatility regime carried into path_truth event_end joins
larger joined outcome sample
```

Without those fields, this audit can identify directional failure zones but cannot fully explain the mechanism.

## Recommended Next Audit

recommended_next_audit:

```text
Probability Model Feature Attribution Audit
```

Scope:

```text
1. Parse probability_model_reason and indicator_evidence.
2. Extract distance_from_ptb_pct, price_velocity, momentum, trend_regime, volatility_regime, and oracle movement where available.
3. Join features to event-end path_truth outcomes.
4. Compare BTC vs ETH and YES vs NO separately.
5. Focus on 0.35-0.50 and 0.50-0.65 buckets.
6. Test whether high-confidence failures come from distance, velocity, momentum, or market_edge terms.
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
