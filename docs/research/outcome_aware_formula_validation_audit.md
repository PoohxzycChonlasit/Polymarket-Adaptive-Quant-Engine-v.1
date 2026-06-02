# Outcome-Aware Formula Validation Audit

audit_date: 2026-06-02
mode: read_only_outcome_validation
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Scope

Inputs inspected:

- `runtime/quant_data/decision_log/2026-05-27.jsonl` through `2026-06-02.jsonl`
- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- market snapshot fields serialized in decision rows

No replay was run. No code, strategy, threshold, runtime, or execution behavior was changed.

## Summary

```text
formula_count: 20
total_rows: 94,170
joinable_outcome_count: 127
classifiable_trade_opens: 335
baseline_joinable_outcomes: 50 favorable / 77 adverse
baseline_alignment_rate: 39.37%
baseline_false_positive_risk: 60.63%
```

## Survival Count by Formula

```text
edge_cap_0.02: 0
edge_cap_0.03: 0
edge_cap_0.05: 0
edge_cap_0.08: 36,996
edge_cap_0.10: 38,118

blend_model_weight_0.05: 0
blend_model_weight_0.10: 1
blend_model_weight_0.15: 756
blend_model_weight_0.20: 13,212
blend_model_weight_0.30: 23,293

bucket_lowcap_0.02_normal_0.08: 17,896
bucket_lowcap_0.02_normal_0.10: 18,493
bucket_lowcap_0.03_normal_0.08: 17,896
bucket_lowcap_0.03_normal_0.10: 18,493
bucket_lowcap_0.05_normal_0.08: 17,896
bucket_lowcap_0.05_normal_0.10: 18,493

current_plus_no_trade_under_0.05: 28,660
current_plus_no_trade_under_0.10: 23,718
current_plus_no_trade_under_0.15: 20,199
current_plus_no_trade_under_0.20: 17,048
```

## Favorable Count by Formula

```text
zero-survival formulas: 0 favorable
blend_model_weight_0.20: 3 favorable
blend_model_weight_0.30: 7 favorable
all bucket_lowcap formulas: 50 favorable
edge_cap_0.08/0.10: 50 favorable
current_plus_no_trade_under_*: 50 favorable
```

## Adverse Count by Formula

```text
zero-survival formulas: 0 adverse
blend_model_weight_0.20: 4 adverse
blend_model_weight_0.30: 16 adverse
all bucket_lowcap formulas: 77 adverse
edge_cap_0.08/0.10: 77 adverse
current_plus_no_trade_under_*: 77 adverse
```

## Alignment Rate by Formula

```text
blend_model_weight_0.20: 42.86% on 7 joinable survivors
blend_model_weight_0.30: 30.43% on 23 joinable survivors
bucket_lowcap_*: 39.37% on 127 joinable survivors
edge_cap_0.08/0.10: 39.37% on 127 joinable survivors
current_plus_no_trade_under_*: 39.37% on 127 joinable survivors
edge_cap_0.02/0.03/0.05: no joinable survivors
blend_model_weight_0.05/0.10/0.15: no joinable survivors
```

## Phantom Removed by Formula

```text
edge_cap_0.02: 39,382
edge_cap_0.03: 39,382
edge_cap_0.05: 39,382
edge_cap_0.08: 2,386
edge_cap_0.10: 1,264

blend_model_weight_0.05: 39,382
blend_model_weight_0.10: 39,381
blend_model_weight_0.15: 38,626
blend_model_weight_0.20: 26,170
blend_model_weight_0.30: 16,089

bucket_lowcap_*_normal_0.08: 21,486
bucket_lowcap_*_normal_0.10: 20,889

current_plus_no_trade_under_0.05: 10,722
current_plus_no_trade_under_0.10: 15,664
current_plus_no_trade_under_0.15: 19,183
current_plus_no_trade_under_0.20: 22,334
```

## False Positive Risk by Formula

False positive risk is adverse outcomes divided by surviving joinable outcomes.

```text
blend_model_weight_0.20: 57.14%
blend_model_weight_0.30: 69.57%
bucket_lowcap_*: 60.63%
edge_cap_0.08/0.10: 60.63%
current_plus_no_trade_under_*: 60.63%
zero-survival formulas: not measurable
```

## Best Outcome Formula

```text
blend_model_weight_0.20
surviving_rows: 13,212
phantom_removed: 26,170
joinable_survived: 7
favorable: 3
adverse: 4
alignment_rate: 42.86%
false_positive_risk: 57.14%
```

This is the best outcome-ranked formula, but the sample is too small to validate. It should not be treated as deployable.

## Best Balanced Formula

```text
bucket_lowcap_0.03_normal_0.08
surviving_rows: 17,896
phantom_removed: 21,486
joinable_survived: 127
favorable: 50
adverse: 77
alignment_rate: 39.37%
false_positive_risk: 60.63%
```

This remains the best balanced research candidate because it reduces phantom EV and preserves enough rows for further analysis. It does not improve outcome alignment.

## Blocked Formula Options

```text
edge_cap_0.02/0.03/0.05: blocked; zero survival.
blend_model_weight_0.05/0.10/0.15: blocked; zero or negligible outcome survival.
blend_model_weight_0.30: blocked; worse outcome alignment and high adverse rate.
edge_cap_0.08/0.10: blocked; too loose and removes little phantom EV.
current_plus_no_trade_under_*: blocked as formula replacement; these are gating overlays, not recalibration formulas.
```

## Recommendation

No formula candidate passes outcome-aware validation. Keep `bucket_lowcap_0.03_normal_0.08` only as a research candidate, not a deployment candidate. The formula layer can reduce phantom EV, but outcome quality still depends on asset, lifecycle, liquidity, spread, timing, and directional signal quality.

## Recommended Next Audit

Run a read-only causal slice audit on `bucket_lowcap_0.03_normal_0.08` and `blend_model_weight_0.20`, split by:

```text
asset BTC/ETH
price bucket
lifecycle phase
time_remaining bucket
liquidity_depth_state
spread bucket
confidence bucket
trade side
event-end favorable/adverse
```

The goal should be to identify whether any narrow slice has both enough survival and better-than-baseline outcome alignment. No replay or threshold change should occur before that result.

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
