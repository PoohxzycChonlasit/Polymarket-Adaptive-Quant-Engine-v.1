# Formula Failure Decomposition Audit

audit_date: 2026-06-02
mode: read_only_failure_decomposition
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Executive Summary

The prior formula audits were directionally correct but incomplete. The original formula creates too much phantom EV, while tightly implied-anchored formulas remove too much admission. The middle-ground formulas reduce low-price phantom EV, but outcome-aware validation still fails because the joined adverse outcomes are not concentrated only in deep-low-price YES rows.

The dominant failure mode is broader than a probability blend problem:

```text
formula_family_count: 5
failed_formula_count: 21
dominant_failure_mode: formula recalibration reduces phantom EV but does not isolate favorable outcomes
worst_price_bucket: 0.50-0.65
worst_asset: ETH
worst_lifecycle_phase: OPENING_SCAN
worst_time_bucket: unavailable in joined trade/path_truth rows
worst_probability_gap_bucket: 10-20pp
sample_limitation: only 127 joinable event-end outcomes from 335 classifiable trade opens
recommended_next_audit: causal slice audit across side, lifecycle, liquidity, and price bucket before replay
```

No tested formula family passes outcome-aware validation.

## Data Used

Inputs inspected:

- `runtime/quant_data/decision_log/2026-05-27.jsonl` through `2026-06-02.jsonl`
- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- market snapshot fields serialized into decision and trade rows

Observed sample:

```text
decision_rows: 94,252
joinable_outcome_count: 127
classifiable_trade_opens: 335
baseline_joined_outcomes: 50 favorable / 77 adverse
baseline_alignment_rate: 39.37%
baseline_false_positive_risk: 60.63%
```

## What Failed

Every formula family failed for one of two reasons:

1. It removed phantom EV but also removed nearly all outcome-joinable candidates.
2. It preserved candidates but preserved the same adverse-heavy outcome set.

The best outcome formula from the prior audit, `blend_model_weight_0.20`, survived only 7 joined outcomes:

```text
favorable: 3
adverse: 4
alignment_rate: 42.86%
sample: too small
```

The best balanced formula, `bucket_lowcap_0.03_normal_0.08`, survived all 127 joined outcomes:

```text
favorable: 50
adverse: 77
alignment_rate: 39.37%
false_positive_risk: 60.63%
```

That is not an improvement over the baseline joined outcome set.

## Why It Failed

The formula search was initially aimed at the low-price YES phantom EV problem. That problem is real, but the outcome-joined failures show a different concentration:

```text
worst joined adverse price bucket: 0.50-0.65, 56 adverse
second: 0.35-0.50, 20 adverse
low-price adverse joined rows: sparse in the joined trade/path_truth set
```

This means low-price phantom EV was a major decision-log calibration issue, but not the only outcome driver in executed or joinable trades. The bad joined rows are mostly near-midprice entries where a formula cap alone does not distinguish favorable from adverse outcomes.

## Where It Failed

For formulas that preserved the joined outcome set, the adverse survivors concentrated as follows:

```text
asset:
ETH: 57 adverse
BTC: 20 adverse

side:
NO: 52 adverse
YES: 25 adverse

lifecycle:
OPENING_SCAN: 52 adverse
ACTIVE_INVENTORY_TRADING: 25 adverse

liquidity:
THIN: 47 adverse
ACCEPTABLE: 27 adverse
UNSTABLE: 3 adverse

price_bucket:
0.50-0.65: 56 adverse
0.35-0.50: 20 adverse
0.20-0.35: 1 adverse

confidence_bucket:
0.50-0.55: 26 adverse
0.55-0.60: 25 adverse
0.70+: 23 adverse

EV / probability gap:
10-20pp: 48 adverse
5-10pp: 21 adverse
20pp+: 8 adverse

spread:
0-1c: 77 adverse
```

Spread is not the visible cause in the joined sample. Most adverse joined rows occurred with tight top-of-book spread. The failures are more consistent with directional signal, lifecycle timing, side selection, and liquidity context.

## Formula Family Failure Notes

### Current Formula

The current formula fails because it over-anchors probability around 50%. This creates phantom EV in low-price YES rows and preserves an adverse-heavy joined trade set.

Failure evidence:

```text
joined outcome alignment: 50 favorable / 77 adverse
worst price bucket: 0.50-0.65
worst side: NO
worst lifecycle: OPENING_SCAN
dominant gap bucket: 10-20pp
```

The current formula is too loose and miscalibrated.

### Implied-first Bounded Edge Variants

Caps at 2pp, 3pp, and 5pp fail because they are too strict under the unchanged `min_ev=0.06` threshold:

```text
edge_cap_0.02: zero joined survivors
edge_cap_0.03: zero joined survivors
edge_cap_0.05: zero joined survivors
```

Caps at 8pp and 10pp fail in the opposite direction:

```text
edge_cap_0.08: 50 favorable / 77 adverse
edge_cap_0.10: 50 favorable / 77 adverse
```

They restore survival but do not improve outcome quality.

### Blend Model Weight Variants

Very low model weights fail by filtering everything:

```text
blend_model_weight_0.05: zero joined survivors
blend_model_weight_0.10: zero joined survivors
blend_model_weight_0.15: zero joined survivors
```

Higher weights preserve some candidates but remain adverse-heavy:

```text
blend_model_weight_0.20: 3 favorable / 4 adverse
blend_model_weight_0.30: 7 favorable / 16 adverse
```

The 20% model-weight variant has the best alignment rate, but only because it filters almost everything. Its 7-row joined survivor set is too small to validate.

### Bucket-aware Low-price Penalty Variants

Bucket-aware caps reduce low-price phantom survival, which is useful. However, they do not improve joined outcomes:

```text
bucket_lowcap_*_normal_0.08: 50 favorable / 77 adverse
bucket_lowcap_*_normal_0.10: 50 favorable / 77 adverse
```

They solve part of the calibration problem but not the outcome-selection problem.

### No-trade Low-price Variants

No-trade low-price overlays reduce rows and remove some phantom EV, but they are not formula recalibrations. They also fail to improve joined outcomes:

```text
current_plus_no_trade_under_0.05: 50 favorable / 77 adverse
current_plus_no_trade_under_0.10: 50 favorable / 77 adverse
current_plus_no_trade_under_0.15: 50 favorable / 77 adverse
current_plus_no_trade_under_0.20: 50 favorable / 77 adverse
```

The joined adverse rows mostly live outside the deep-low-price area, so low-price blocking alone cannot solve the failure.

## Rows That Survived But Were Bad

The bad survivors under current, loose cap, bucket-aware, and no-trade formulas were mostly:

```text
ETH rows: 57 adverse
NO side: 52 adverse
OPENING_SCAN: 52 adverse
THIN liquidity: 47 adverse
0.50-0.65 price bucket: 56 adverse
10-20pp model-vs-market gap: 48 adverse
0-1c spread: 77 adverse
```

Interpretation:

- The failure is not primarily wide spread.
- The failure is not only deep-low-price YES.
- The failure appears concentrated in near-midprice entries where the model still claims 6-20pp of edge.
- NO-side rows are more adverse in the joined sample than YES-side rows.
- OPENING_SCAN has the worst joined adverse concentration, suggesting timing and early-window signal quality matter.

## Rows Filtered But Might Be Good

Strict formulas filter all or nearly all joined favorable rows:

```text
edge_cap_0.02/0.03/0.05 filtered favorable: 50
blend_model_weight_0.05/0.10/0.15 filtered favorable: 50
```

Filtered favorable rows were mostly:

```text
ETH: 44 favorable
NO side: 29 favorable
YES side: 21 favorable
OPENING_SCAN: 36 favorable
THIN liquidity: 36 favorable
0.50-0.65 price bucket: 42 favorable
10-20pp gap: 31 favorable
```

This is why simple hard filtering fails. The same slices contain both favorable and adverse outcomes. A formula-only rule cannot separate them cleanly with the current features.

## Failure Cause Assessment

```text
model_calibration: confirmed contributor
weak_outcome_proxy: contributor; only 127 joined event-end outcomes
timing: likely contributor; OPENING_SCAN dominates joined adverse rows
liquidity: likely contributor; THIN dominates joined adverse rows
side_bias: likely contributor; NO dominates joined adverse rows
spread: not primary in joined sample; adverse rows were mostly 0-1c spread
insufficient_sample: material limitation
```

The formula layer is necessary but not sufficient. Outcome failure appears to require a causal slice analysis across lifecycle, side, liquidity, and directional signal quality.

## Evidence Missing

Missing or weak evidence:

```text
time_remaining bucket unavailable for most joined trade/path_truth rows
only 127 joined event-end outcomes
many trade opens are classifiable but not outcome-joinable
decision rows have rich timing fields, but outcome rows do not always preserve them
market snapshots are mostly useful through serialized decision/trade fields, not a clean event-end join
no replay validation performed
```

The missing time-aligned outcome join is the largest blocker for a confident formula choice.

## What Should Be Audited Next

recommended_next_audit:

```text
Side-Lifecycle-Liquidity Causal Slice Audit
```

Scope:

```text
1. Compare YES vs NO outcomes separately.
2. Split OPENING_SCAN vs ACTIVE_INVENTORY_TRADING.
3. Split THIN vs ACCEPTABLE liquidity.
4. Split 0.35-0.50 and 0.50-0.65 price buckets.
5. Split 5-10pp, 10-20pp, and 20pp+ probability-gap buckets.
6. Reconstruct time_remaining for trade opens from epoch timestamps where missing.
7. Identify whether any narrow slice has enough joined outcomes and better-than-baseline alignment.
```

No replay, strategy change, threshold change, or runtime change should occur before that audit.

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
