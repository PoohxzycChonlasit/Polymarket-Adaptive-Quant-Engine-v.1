# Saturated Feature Removal Simulation Audit

audit_date: 2026-06-02
mode: read_only_simulation
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Executive Summary

This audit simulated whether saturated PTB distance should be removed, downweighted, or paired with safer confidence logic. The best research candidate is removing saturated PTB distance contribution. It modestly improves outcome alignment while preserving most candidates. Confidence-only capping does not materially change survival, and history-adverse confidence penalties remove too many candidates.

Required outputs:

```text
scenario_count: 6
saturated_rows: 6,359
non_saturated_rows: 235,773
best_candidate_scenario: remove_saturated_distance
dominant_risk: confidence and EV remain weak outcome rankers even after saturated distance removal
recommended_next_audit: Saturated Distance Removal Slice Validation Audit
```

## Method

Inputs inspected:

- `polymarket/probability_model.py`
- `runtime/quant_data/decision_log/*.jsonl`
- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- market snapshot fields carried through decision/trade rows

Simulation rules:

- No replay was run.
- No code, runtime, threshold, or execution behavior was changed.
- Candidate survival used existing row-level `min_ev` and a proxy confidence floor of `0.54`.
- Outcome alignment used event-end `path_truth` joins from trade opens.

## Scenarios Tested

```text
1. current
2. remove_saturated_distance
3. downweight_saturated_distance_50
4. confidence_cap_saturated
5. history_adverse_gap_penalty
6. downweight_plus_confidence_cap
```

Saturated distance definition:

```text
abs(distance) >= 0.0199
```

This captures rows where PTB distance is effectively clipped at the model's `+/-0.02000` input bound.

## Candidate Survival by Scenario

```text
current: 27,976
remove_saturated_distance: 27,147
downweight_saturated_distance_50: 27,254
confidence_cap_saturated: 27,976
history_adverse_gap_penalty: 9,882
downweight_plus_confidence_cap: 27,254
```

Interpretation:

- Removing saturated distance preserves most candidates.
- Downweighting by 50% preserves slightly more candidates than full removal.
- Confidence capping alone does not change candidate survival.
- History-adverse confidence penalty removes too much of the candidate pool.

## Confidence Reduction by Scenario

Mean confidence reduction on saturated rows:

```text
current: 0.000000
remove_saturated_distance: 0.109094
downweight_saturated_distance_50: 0.061073
confidence_cap_saturated: 0.004164
history_adverse_gap_penalty: 0.014088
downweight_plus_confidence_cap: 0.061413
```

The distance-removal scenarios produce meaningful confidence reduction because they change the probability extremity that feeds the confidence formula. A simple confidence cap at `0.60` barely changes this sample.

## Phantom EV Reduction by Scenario

Rows with current gap above 5pp that no longer survive:

```text
current: 75,435
remove_saturated_distance: 76,268
downweight_saturated_distance_50: 76,179
confidence_cap_saturated: 75,435
history_adverse_gap_penalty: 93,529
downweight_plus_confidence_cap: 76,179
```

Removing saturated distance provides modest extra phantom-EV filtering. The history-adverse penalty removes far more, but it does so by sharply reducing candidate survival.

## Outcome Alignment by Scenario

Event-end joined survivors:

```text
current: 46 favorable / 75 adverse = 38.02%
remove_saturated_distance: 34 favorable / 53 adverse = 39.08%
downweight_saturated_distance_50: 35 favorable / 57 adverse = 38.04%
confidence_cap_saturated: 46 favorable / 75 adverse = 38.02%
history_adverse_gap_penalty: 19 favorable / 28 adverse = 40.43%
downweight_plus_confidence_cap: 35 favorable / 57 adverse = 38.04%
```

The best alignment rate is the history-adverse penalty, but it survives only 47 joined outcomes and cuts candidate survival to 9,882. That is too destructive for a balanced candidate.

The best balanced outcome is `remove_saturated_distance`: it removes 22 adverse joined survivors while removing 12 favorable joined survivors and keeps 27,147 row-level candidates.

## Scenario Notes

### Current

The current formula has the largest joined survivor set but remains adverse-heavy:

```text
46 favorable / 75 adverse
```

It does not address saturated distance or confidence inversion.

### Remove Saturated PTB Distance Contribution

This is the best research candidate.

```text
candidate_survival: 27,147
joined_survivors: 87
outcome_alignment: 39.08%
mean_confidence_reduction_saturated: 0.109094
```

Why it helps:

- Removes the strongest saturated PTB contribution.
- Reduces false confidence more than any non-destructive scenario.
- Filters more adverse than favorable joined outcomes.
- Does not kill the candidate pool.

Why it is not enough:

- Alignment is still below 50%.
- Remaining survivors are still adverse-heavy.
- Feature removal alone does not solve BTC/NO midprice direction quality.

### Downweight Saturated PTB Distance by 50%

This is the conservative alternative.

```text
candidate_survival: 27,254
joined_survivors: 92
outcome_alignment: 38.04%
mean_confidence_reduction_saturated: 0.061073
```

It reduces confidence moderately but does not improve outcome alignment relative to current.

### Confidence Capped When Distance Is Saturated

This scenario is blocked as ineffective.

```text
candidate_survival: 27,976
joined_survivors: 121
outcome_alignment: 38.02%
mean_confidence_reduction_saturated: 0.004164
```

The cap barely changes the sample and does not alter outcome quality.

### Confidence Penalized by Adverse History Risk

This scenario is too destructive.

```text
candidate_survival: 9,882
joined_survivors: 47
outcome_alignment: 40.43%
```

It improves alignment only by aggressively removing candidates. It should remain an audit concept, not a formula candidate.

### Downweighted PTB Plus Confidence Cap

This behaves almost identically to 50% downweighting.

```text
candidate_survival: 27,254
joined_survivors: 92
outcome_alignment: 38.04%
```

The confidence cap adds little after downweighting.

## Best Candidate Scenario

```text
remove_saturated_distance
```

Rationale:

- Preserves 27,147 candidates.
- Reduces saturated-row confidence by about 10.9pp.
- Removes additional phantom EV rows versus current.
- Improves joined outcome alignment from 38.02% to 39.08%.
- Filters adverse joined outcomes more than favorable ones.

This is not deployable. It is only the best read-only simulation candidate.

## Blocked Scenarios

```text
current: blocked; retains saturated-distance confidence inversion.
confidence_cap_saturated: blocked; no meaningful survival or outcome change.
history_adverse_gap_penalty: blocked; too destructive and history-conditioned.
downweight_plus_confidence_cap: blocked as redundant with 50% downweighting.
downweight_saturated_distance_50: not blocked, but weaker than full removal in outcome alignment.
```

## Dominant Risk

The dominant risk is that saturated distance removal reduces false confidence but does not fix directional ranking. The remaining candidates are still adverse-heavy. That means the next research question is not only whether to remove saturated distance, but which slices remain unsafe after removal.

## Recommended Next Audit

recommended_next_audit:

```text
Saturated Distance Removal Slice Validation Audit
```

Scope:

```text
1. Compare current vs remove_saturated_distance by BTC/ETH.
2. Compare YES vs NO separately.
3. Focus on 0.35-0.50 and 0.50-0.65 price buckets.
4. Measure which adverse slices remain after saturated distance removal.
5. Verify whether ETH YES 0.50-0.65 remains the only positive research slice.
6. Keep all analysis read-only until a larger joined outcome sample exists.
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
