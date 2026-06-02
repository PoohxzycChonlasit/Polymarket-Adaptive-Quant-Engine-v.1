# Ranking Feature Ablation and Anti-Confidence Simulation Audit

audit_date: 2026-06-02
mode: read_only_ranking_simulation
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Executive Summary

Confidence is harmful in the current ranking stack, but confidence removal alone does not fix ranking. The best simulated rank improvement comes from outcome-safe slice rules that demote known bad BTC/NO midprice regions and favor ETH YES 50-65c. That result is useful as research evidence, but it is too history-fit to deploy.

Required outputs:

```text
scenario_count: 10
best_ranking_scenario: ev_plus_outcome_safe_slices
current_top_quartile_alignment: 9 favorable / 23 adverse = 28.12%
best_top_quartile_alignment: 17 favorable / 15 adverse = 53.12%
confidence_signal_verdict: harmful as a positive rank feature
top_bad_promoter_feature: confidence + EV/probability-edge saturation
top_good_suppressor_feature: favorable ETH midprice rows receive lower confidence and lose to bad high-confidence BTC/NO rows
dominant_ranking_failure_mode: ranking double-counts miscalibrated edge, then uses confidence to break ties in the wrong direction
recommended_next_audit: Outcome-Safe Ranking Slice Robustness Audit
```

No runtime change is recommended from this audit.

## Data Inspected

Inputs:

- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- ranking formula from `polymarket/opportunity_scanner.py`
- carried trade fields for EV, confidence, liquidity, spread, side, asset, lifecycle, and price buckets

Joined sample:

```text
joined_outcomes: 128
favorable: 50
adverse: 78
```

## Scenarios Tested

```text
1. current
2. remove_confidence
3. cap_confidence
4. invert_confidence
5. penalize_high_conf_large_gap
6. ev_only
7. ev_plus_liquidity
8. ev_plus_outcome_safe_slices
9. exclude_btc_no_midprice_failure
10. favor_historical_favorable_slice_only
```

## Top Quartile Results

```text
current: 9 favorable / 23 adverse = 28.12%
remove_confidence: 12 favorable / 20 adverse = 37.50%
cap_confidence: 11 favorable / 21 adverse = 34.38%
invert_confidence: 12 favorable / 20 adverse = 37.50%
penalize_high_conf_large_gap: 15 favorable / 17 adverse = 46.88%
ev_only: 12 favorable / 20 adverse = 37.50%
ev_plus_liquidity: 10 favorable / 22 adverse = 31.25%
ev_plus_outcome_safe_slices: 17 favorable / 15 adverse = 53.12%
exclude_btc_no_midprice_failure: 13 favorable / 19 adverse = 40.62%
favor_historical_favorable_slice_only: 17 favorable / 15 adverse = 53.12%
```

The only scenarios that produce favorable-majority top quartiles use explicit historical slice information.

## Bottom Quartile Results

```text
current: 14 favorable / 18 adverse = 43.75%
remove_confidence: 14 favorable / 18 adverse = 43.75%
cap_confidence: 14 favorable / 18 adverse = 43.75%
invert_confidence: 12 favorable / 20 adverse = 37.50%
penalize_high_conf_large_gap: 12 favorable / 20 adverse = 37.50%
ev_only: 14 favorable / 18 adverse = 43.75%
ev_plus_liquidity: 14 favorable / 18 adverse = 43.75%
ev_plus_outcome_safe_slices: 7 favorable / 25 adverse = 21.88%
exclude_btc_no_midprice_failure: 12 favorable / 20 adverse = 37.50%
favor_historical_favorable_slice_only: 10 favorable / 22 adverse = 31.25%
```

The outcome-safe simulations push more adverse rows into the bottom quartile, which is the desired ranking behavior. But this may reflect sample fitting.

## Is Confidence Helpful or Harmful?

Confidence is harmful as a positive ranking feature.

Evidence:

```text
current top quartile: 9 favorable / 23 adverse
remove_confidence top quartile: 12 favorable / 20 adverse
invert_confidence top quartile: 12 favorable / 20 adverse
penalize_high_conf_large_gap top quartile: 15 favorable / 17 adverse
```

Removing or penalizing confidence improves top-quartile alignment. However, it does not create a favorable-majority top quartile by itself.

## Does High Confidence Correlate With Adverse Outcomes?

Yes. Under current ranking, the top quartile is dominated by high-confidence rows:

```text
current top confidence bucket:
0.70+: 26 of 32 top-quartile rows
```

Current top-quartile outcome:

```text
9 favorable / 23 adverse
```

This confirms that the ranking system promotes high-confidence rows even though high confidence has been repeatedly adverse-heavy in prior audits.

## Does Removing Confidence Improve Ranking?

Yes, but only modestly.

```text
current top alignment: 28.12%
remove_confidence top alignment: 37.50%
invert_confidence top alignment: 37.50%
```

Confidence removal reduces the worst damage but does not fix the ranking stack, because EV and probability edge remain saturated and miscalibrated.

## Does Inverting Confidence Improve Ranking?

It improves ranking versus current, but not more than simply removing confidence:

```text
invert_confidence top alignment: 37.50%
remove_confidence top alignment: 37.50%
```

Conclusion: confidence should not be naively inverted globally. It should be treated as a risk feature in specific slices, especially high-confidence BTC/NO midprice rows.

## Scenario Notes

### Current

The current ranking performs worst among plausible rankers:

```text
top quartile: 9 favorable / 23 adverse
top asset split: BTC 22, ETH 10
top side split: NO 19, YES 13
top confidence: 26 rows at 0.70+
```

The current system actively promotes the known bad BTC/high-confidence cluster.

### Remove Confidence

```text
top quartile: 12 favorable / 20 adverse
```

This is better than current, but still adverse-heavy.

### Cap Confidence

```text
top quartile: 11 favorable / 21 adverse
```

Capping confidence is weaker than removing confidence.

### Penalize High Confidence With Large Gap

```text
top quartile: 15 favorable / 17 adverse
```

This is the best non-slice-specific anti-confidence scenario. It supports treating high-confidence, high-gap rows as risky.

### EV Only

```text
top quartile: 12 favorable / 20 adverse
```

EV-only ranking is no better than removing confidence because EV itself is derived from the same miscalibrated probability stack.

### EV Plus Liquidity

```text
top quartile: 10 favorable / 22 adverse
```

Liquidity makes ranking worse in this joined sample. It promotes ACCEPTABLE liquidity rows that prior audits found adverse-heavy.

### EV Plus Outcome-safe Slices

```text
top quartile: 17 favorable / 15 adverse
```

This is the best scenario, but it uses historical slice knowledge:

```text
bonus: ETH YES 0.50-0.65
penalty: BTC / NO / 0.35-0.50 bad slices
```

It is a research candidate, not a deployment rule.

### Exclude BTC NO Midprice Failure

```text
top quartile: 13 favorable / 19 adverse
```

Excluding only the single worst slice helps but does not solve the broader BTC/high-confidence and NO-side problems.

### Favor Historical Favorable Slice Only

```text
top quartile: 17 favorable / 15 adverse
```

This matches the best top-quartile alignment, but it is even more history-fit and narrow.

## Feature Verdict

```text
remove: global positive confidence contribution
cap: confidence if retained at all, but cap alone is insufficient
invert: do not globally invert; use as slice-specific risk signal only
keep: EV only as an input, not duplicated with probability_edge
penalize: high confidence plus high probability gap in BTC/NO/midprice regions
avoid: liquidity as a naive positive rank feature
```

## Ranking Splits

Best scenario top quartile, `ev_plus_outcome_safe_slices`:

```text
asset split: ETH 31, BTC 1
side split: YES 25, NO 7
price split: 0.50-0.65 = 31, <0.35 = 1
lifecycle split: OPENING_SCAN 26, ACTIVE_INVENTORY_TRADING 6
liquidity split: THIN 22, ACCEPTABLE 9, UNSTABLE 1
confidence split: 0.55-0.60 = 19, <0.55 = 9, 0.70+ = 3
gap split: 10-20pp = 25, 6-10pp = 6, 20pp+ = 1
```

This top quartile looks more like the previously identified research-positive ETH YES midprice region and less like the BTC/NO high-confidence failure cluster.

## Evidence Missing

Missing or weak evidence:

```text
joined sample is only 128 outcomes
scenario 8 and 10 use historical slice knowledge and may overfit
exact live candidate ordering is not fully serialized
rejected candidates lack outcome labels
score component fields are proxy-reconstructed
no replay validation was performed
```

The audit identifies a ranking direction, not a deployable ranking rule.

## Recommendation

Do not deploy any ranking change. The strongest research result is that confidence should stop acting as a global positive rank feature. The next audit should test whether the outcome-safe slice effect survives stricter validation.

## Recommended Next Audit

recommended_next_audit:

```text
Outcome-Safe Ranking Slice Robustness Audit
```

Scope:

```text
1. Validate ETH YES 0.50-0.65 outside the current joined sample.
2. Validate BTC/NO/high-confidence penalties outside the current joined sample.
3. Compare top-quartile alignment with and without confidence.
4. Avoid any runtime ranking change until slice robustness is proven.
```

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
