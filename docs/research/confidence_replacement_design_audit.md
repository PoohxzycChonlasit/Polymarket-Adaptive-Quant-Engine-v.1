# Confidence Replacement Design Audit

audit_date: 2026-06-02
mode: read_only_confidence_design
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Executive Summary

The old confidence feature failed because it acted as a positive rank signal even though high confidence was repeatedly adverse-heavy. Replacing confidence with slice-aware logic improves top-quartile alignment, but the strongest replacement is also the most history-fit. The safest design conclusion is that confidence should not remain a global positive ranking feature. It should be removed from positive ranking or converted into a risk penalty until slice robustness is proven.

Required outputs:

```text
replacement_count: 8
candidate_survival_count: 128 joined outcome candidates
current_alignment: 9 favorable / 23 adverse = 28.12% top-quartile alignment
best_replacement: outcome_safe_slice_confidence
best_replacement_alignment: 16 favorable / 16 adverse = 50.00% top-quartile alignment
confidence_replacement_verdict: convert confidence from positive rank feature into risk-aware/slice-aware penalty signal
dominant_remaining_risk: best replacement uses historical slice knowledge and may overfit
recommended_next_audit: Confidence Replacement Robustness and Replay-Candidate Spec Audit
```

No replacement is safe for live runtime. The best candidates are replay-only design inputs.

## Data Inspected

Inputs:

- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- ranking components from `polymarket/opportunity_scanner.py`
- carried trade fields for asset, side, price bucket, lifecycle, liquidity, gap, confidence, and time bucket

Joined sample:

```text
joined_outcomes: 128
favorable: 50
adverse: 78
top_quartile_size: 32
```

## Candidate Replacements

Tested confidence replacements:

```text
1. outcome_safe_slice_confidence
2. calibration_gap_penalized_confidence
3. liquidity_weighted_confidence
4. time_remaining_weighted_confidence
5. side_asset_slice_confidence
6. adverse_history_penalized_confidence
7. rank_confidence_none
8. confidence_as_risk_penalty_only
```

The current confidence ranking was retained as baseline.

## Why Old Confidence Failed

Current confidence promoted the known bad clusters:

```text
current top quartile: 9 favorable / 23 adverse = 28.12%
top confidence bucket: 0.70+ appears in 26 of 32 top-quartile rows
top side split: NO 20, YES 12
top asset split: BTC 22, ETH 10
top price buckets: 0.50-0.65 = 15, 0.35-0.50 = 14
```

The old confidence was not an outcome-quality signal. It mainly helped high-confidence BTC/NO midprice rows outrank lower-confidence favorable ETH rows.

## Replacement Results

Top-quartile alignment:

```text
current: 9 favorable / 23 adverse = 28.12%
outcome_safe_slice_confidence: 16 favorable / 16 adverse = 50.00%
calibration_gap_penalized_confidence: 8 favorable / 24 adverse = 25.00%
liquidity_weighted_confidence: 10 favorable / 22 adverse = 31.25%
time_remaining_weighted_confidence: 9 favorable / 23 adverse = 28.12%
side_asset_slice_confidence: 15 favorable / 17 adverse = 46.88%
adverse_history_penalized_confidence: 15 favorable / 17 adverse = 46.88%
rank_confidence_none: 10 favorable / 22 adverse = 31.25%
confidence_as_risk_penalty_only: 15 favorable / 17 adverse = 46.88%
```

Bottom-quartile alignment:

```text
current: 14 favorable / 18 adverse = 43.75%
outcome_safe_slice_confidence: 11 favorable / 21 adverse = 34.38%
side_asset_slice_confidence: 12 favorable / 20 adverse = 37.50%
adverse_history_penalized_confidence: 13 favorable / 19 adverse = 40.62%
confidence_as_risk_penalty_only: 13 favorable / 19 adverse = 40.62%
```

Better replacements push more adverse rows downward and reduce BTC/high-confidence concentration at the top.

## Best Replacement

```text
best_replacement: outcome_safe_slice_confidence
top_quartile: 16 favorable / 16 adverse = 50.00%
top asset split: ETH 32, BTC 0
top side split: YES 31, NO 1
top price split: 0.50-0.65 = 24, 0.35-0.50 = 7, <0.35 = 1
top confidence split: 0.55-0.60 = 18, <0.55 = 11, 0.70+ = 1
```

This replacement works best because it demotes known bad slices and promotes the only recurring favorable research slice. It is not safe enough for runtime because it is explicitly history-fit.

## Safer Replacement Candidate

```text
confidence_as_risk_penalty_only
top_quartile: 15 favorable / 17 adverse = 46.88%
```

This is weaker than outcome-safe slice confidence, but more conceptually defensible:

- confidence stops being a global positive feature
- high confidence becomes a risk condition
- top quartile shifts toward ETH and away from BTC
- high-confidence top rows fall materially

This is the best replay-only design candidate if overfit risk must be minimized.

## Replacement Failures

### Calibration Gap Penalized Confidence

```text
top_quartile: 8 favorable / 24 adverse = 25.00%
```

This made ranking worse. Penalizing gap alone does not address side/asset-specific failure.

### Liquidity Weighted Confidence

```text
top_quartile: 10 favorable / 22 adverse = 31.25%
```

Liquidity weighting is weak because ACCEPTABLE liquidity was not outcome-safe in prior audits.

### Time Remaining Weighted Confidence

```text
top_quartile: 9 favorable / 23 adverse = 28.12%
```

No useful effect. Time fields are missing in joined outcomes, so this replacement cannot be validated.

### Rank Confidence None

```text
top_quartile: 10 favorable / 22 adverse = 31.25%
```

Removing confidence helps only slightly because EV and probability edge remain miscalibrated and saturated.

## Should Confidence Be Removed, Capped, Inverted, or Converted?

Verdict:

```text
remove as global positive rank feature: yes
cap globally: insufficient
invert globally: not recommended
convert into risk penalty: best safer design direction
slice-aware replacement: best performance, but overfit risk
```

Confidence should be treated as evidence of risk in known bad regions, especially BTC/NO/midprice/high-gap rows. It should not be a universal boost.

## Splits Under Best Replacement

`outcome_safe_slice_confidence` top quartile:

```text
BTC/ETH split: ETH 32, BTC 0
YES/NO split: YES 31, NO 1
price bucket split: 0.50-0.65 = 24, 0.35-0.50 = 7, <0.35 = 1
lifecycle split: OPENING_SCAN 24, ACTIVE_INVENTORY_TRADING 8
liquidity split: THIN 28, ACCEPTABLE 3, UNSTABLE 1
probability gap split: 10-20pp = 23, 6-10pp = 5, 20pp+ = 4
time remaining split: missing 32
```

The best replacement heavily concentrates in ETH YES and removes BTC from the top quartile. That is exactly why it improves alignment, and exactly why it may be overfit.

## Evidence Missing

Missing or weak evidence:

```text
joined outcome sample is only 128 rows
time_remaining is missing for joined rows
rejected candidates lack outcomes
candidate survival is measured on joined candidates, not full replay
replacement scenarios use proxy ranking, not live candidate ordering
outcome_safe_slice_confidence uses historical slice labels
no replay validation performed
```

## Replay-only Candidate Design Safety

No replacement is safe for deployment. Two replacements are suitable for replay-only design:

```text
1. confidence_as_risk_penalty_only
2. outcome_safe_slice_confidence
```

The first is safer conceptually. The second performs better but needs robustness validation.

## Recommended Next Audit

recommended_next_audit:

```text
Confidence Replacement Robustness and Replay-Candidate Spec Audit
```

Scope:

```text
1. Validate outcome_safe_slice_confidence out of sample if possible.
2. Validate confidence_as_risk_penalty_only as a less overfit alternative.
3. Compare top-quartile alignment by asset, side, price bucket, and confidence bucket.
4. Draft replay-only candidate specs without runtime mutation.
5. Keep confidence removed from any proposed positive rank feature unless proven robust.
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
