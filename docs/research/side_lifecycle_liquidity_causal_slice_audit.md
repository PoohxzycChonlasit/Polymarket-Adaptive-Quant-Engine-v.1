# Side-Lifecycle-Liquidity Causal Slice Audit

audit_date: 2026-06-02
mode: read_only_causal_slice
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Executive Summary

Formula changes alone did not isolate favorable outcomes because the bad rows are not only a low-price YES calibration artifact. The outcome-joined failures concentrate in side/lifecycle/liquidity/price interactions, especially midprice rows where the model claims a 5-20pp edge.

Required outputs:

```text
slice_count: 46
joinable_outcome_count: 125
best_slice: asset=ETH | side=YES | price_bucket=0.50-0.65 | lifecycle=OPENING_SCAN
best_slice_alignment: 12 favorable / 8 adverse = 60.0%
worst_slice: liquidity=ACCEPTABLE | price_bucket=0.35-0.50
worst_slice_alignment: 0 favorable / 11 adverse = 0.0%
dominant_causal_hypothesis: side and lifecycle interact with midprice probability-gap rows; formula calibration reduces phantom EV but cannot separate directionally bad midprice entries
sample_limitation: only 125 joinable event-end outcomes after requiring classifiable trade fields
recommended_next_audit: Midprice Directional Signal Failure Audit
```

No slice is robust enough to justify runtime change. The best slice is promising only as a research lead.

## Data Inspected

Inputs:

- `runtime/quant_data/decision_log/2026-05-27.jsonl` through `2026-06-02.jsonl`
- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- `runtime/quant_data/market_snapshots/2026-05-27.jsonl` through `2026-06-02.jsonl`

Context rows:

```text
decision_rows_with_probability: 94,402
market_snapshot_rows_with_price: inspected for distribution context
joined_trade_path_outcomes: 125
baseline joined alignment: 49 favorable / 76 adverse = 39.2%
```

Decision and market snapshot context both show heavy coverage in the same broad price regions, so the joined sample is not failing only because deep-low-price rows dominate the data.

## What Failed

The prior formula families failed because they attacked the wrong layer by themselves:

- Low-price formula caps reduce phantom YES admission.
- No-trade low-price overlays remove some obviously bad regions.
- But the outcome-joined adverse rows are mostly midprice rows, especially `0.35-0.50` and `0.50-0.65`.

The main failure is not just probability calibration. It is candidate selection under side, lifecycle, liquidity, and midprice uncertainty.

## Where It Failed

### Asset-Side Failure Map

```text
ETH: 43 favorable / 56 adverse = 43.4%
BTC: 6 favorable / 20 adverse = 23.1%

YES: 20 favorable / 25 adverse = 44.4%
NO: 29 favorable / 51 adverse = 36.3%

ETH YES: 17 favorable / 16 adverse = 51.5%
BTC YES: 3 favorable / 9 adverse = 25.0%
BTC NO: 3 favorable / 11 adverse = 21.4%
```

BTC is the weakest asset in this joined sample. NO-side trades are weaker overall than YES-side trades, but ETH YES is the only broad asset-side slice near breakeven.

### Lifecycle Failure Map

```text
OPENING_SCAN: 35 favorable / 51 adverse = 40.7%
ACTIVE_INVENTORY_TRADING: 14 favorable / 25 adverse = 35.9%
```

OPENING_SCAN has the largest adverse count, but ACTIVE_INVENTORY_TRADING has a worse rate. This suggests lifecycle does not work as a simple include/exclude rule. It must be combined with side, asset, and price bucket.

### Liquidity Failure Map

```text
THIN: 35 favorable / 46 adverse = 43.2%
ACCEPTABLE: 12 favorable / 26 adverse = 31.6%
UNSTABLE: 2 favorable / 3 adverse = 40.0%
STRONG: 0 favorable / 1 adverse = 0.0%
```

The prior assumption that THIN liquidity alone explains failure is incomplete. THIN has the largest count, but ACCEPTABLE has worse alignment in the joined sample. Liquidity is a context variable, not a standalone causal filter.

### Price Bucket Failure Map

```text
0.20-0.35: 2 favorable / 1 adverse = 66.7% (n=3, too small)
0.35-0.50: 6 favorable / 20 adverse = 23.1%
0.50-0.65: 41 favorable / 55 adverse = 42.7%
```

The worst robust price bucket is `0.35-0.50`, not the low-price buckets. The largest adverse count is `0.50-0.65`, but it also contains many favorable rows.

### Probability Gap Failure Map

```text
5-10pp gap: 14 favorable / 21 adverse = 40.0%
10-20pp gap: 30 favorable / 47 adverse = 39.0%
20pp+ gap: 5 favorable / 8 adverse = 38.5%
```

Higher model-vs-market gap does not improve alignment. The model's claimed edge is not ranking outcome quality in the joined sample.

### Confidence Failure Map

```text
0.50-0.55: 14 favorable / 25 adverse = 35.9%
0.55-0.60: 25 favorable / 25 adverse = 50.0%
0.65-0.70: 2 favorable / 2 adverse = 50.0%
0.70+: 8 favorable / 23 adverse = 25.8%
```

High confidence is actively suspicious. The `0.70+` bucket is adverse-heavy, confirming earlier calibration findings that confidence is not a reliable quality signal here.

### Spread Failure Map

```text
0-1c spread: 49 favorable / 76 adverse = 39.2%
```

All joined rows landed in the tight-spread bucket. Spread does not explain the observed adverse outcomes in this sample.

## Best Slice

```text
asset=ETH
side=YES
price_bucket=0.50-0.65
lifecycle=OPENING_SCAN

favorable: 12
adverse: 8
alignment_rate: 60.0%
false_positive_risk: 40.0%
sample_size: 20
```

This is the best slice with at least 8 joined outcomes. It is not robust enough for deployment, but it is the strongest research lead. It suggests that ETH YES in the 50-65c range may be less broken than the broader model population.

Related favorable slices:

```text
ETH YES OPENING_SCAN: 13 favorable / 12 adverse = 52.0%
ETH YES overall: 17 favorable / 16 adverse = 51.5%
YES 0.50-0.65: 18 favorable / 18 adverse = 50.0%
```

These are not decisive, but they are materially better than the 39.2% baseline.

## Worst Slice

```text
liquidity=ACCEPTABLE
price_bucket=0.35-0.50

favorable: 0
adverse: 11
alignment_rate: 0.0%
false_positive_risk: 100.0%
sample_size: 11
```

Other bad slices:

```text
ACTIVE_INVENTORY_TRADING + 0.35-0.50: 2 favorable / 9 adverse = 18.2%
0.35-0.50 + 10-20pp gap: 3 favorable / 13 adverse = 18.8%
BTC NO: 3 favorable / 11 adverse = 21.4%
YES 0.35-0.50: 2 favorable / 7 adverse = 22.2%
NO 0.35-0.50: 4 favorable / 13 adverse = 23.5%
BTC YES: 3 favorable / 9 adverse = 25.0%
```

The `0.35-0.50` price bucket is consistently poor across side and lifecycle combinations.

## Why It Failed

The strongest causal explanation is:

```text
Formula calibration reduces phantom low-price EV, but outcome failure is dominated by midprice directional selection.
```

Evidence:

- `0.35-0.50` is the worst robust price bucket.
- `0.50-0.65` has the largest adverse count but contains both good and bad slices.
- BTC is weak across YES and NO.
- NO-side alignment is worse than YES-side alignment.
- High confidence does not imply favorable outcomes.
- Probability gap does not rank favorable outcomes.
- Spread is not the differentiator in joined rows.

The model appears to mistake directional confidence for edge in midprice markets. A formula-only fix cannot solve that because both favorable and adverse rows can live in the same probability-gap and price buckets.

## What Evidence Is Missing

Missing or weak evidence:

```text
time_remaining bucket is missing for joined trade/path rows after strict field reconstruction
only 125 event-end joined outcomes are available in this classifiable sample
some trade opens have no path_truth event-end join
market snapshots are available for context but not a perfect event-end outcome join
price/lifecycle/side slices become small quickly
no replay validation was performed
```

The main limitation is sample size once sliced. The best slice has only 20 outcomes.

## Interpretation

The audit does not identify a deployable trading rule. It does identify where future research should look:

- Avoid treating low-price phantom EV as the only root cause.
- Study `0.35-0.50` midprice rows as a likely danger zone.
- Study BTC side behavior separately from ETH.
- Study NO-side logic separately from YES-side logic.
- Treat high confidence as potentially inverted until proven otherwise.
- Reconstruct better time_remaining lineage for joined outcomes.

## Recommended Next Audit

recommended_next_audit:

```text
Midprice Directional Signal Failure Audit
```

Scope:

```text
1. Focus on 0.35-0.50 and 0.50-0.65 price buckets.
2. Split YES vs NO side separately.
3. Split BTC vs ETH separately.
4. Inspect probability_model_reason, indicator_evidence, trend_regime, volatility_regime, distance_from_ptb_pct, price_velocity, momentum, and confidence.
5. Reconstruct time_remaining from epoch timestamps where possible.
6. Compare favorable/adverse outcomes only for event-end path_truth joins.
7. Determine whether high-confidence signals are inverted in specific side/asset/price slices.
```

No replay, strategy change, threshold change, runtime mutation, or execution change should occur before that audit.

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
