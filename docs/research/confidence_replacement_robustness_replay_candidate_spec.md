# Confidence Replacement Robustness and Replay-Candidate Spec Audit

audit_date: 2026-06-02
mode: read_only_replay_candidate_spec
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Executive Summary

The confidence replacement is stable enough for replay-only testing, but not for runtime deployment. The best replay candidate is not the fully slice-aware replacement. The best candidate v1 is a simpler risk rule: penalize high confidence when the probability gap is large.

Required outputs:

```text
candidate_count: 5
best_replay_candidate: penalize_high_conf_large_gap
robustness_pass_count: 4
robustness_fail_count: 4
candidate_spec: replay-only high-confidence large-gap risk penalty
blocked_candidate_options: outcome_safe_slice_confidence, no_confidence, confidence_as_risk_penalty_only, ev_plus_outcome_safe_slice_ranking
acceptance_criteria: improve top-quartile alignment without collapsing sample or over-concentrating one historical slice
recommended_next_audit: Replay-Only Ranking Candidate Dry Spec Review
```

No replay was run. This is a replay-candidate design document only.

## Candidates Tested

```text
1. outcome_safe_slice_confidence
2. confidence_as_risk_penalty_only
3. no_confidence
4. penalize_high_conf_large_gap
5. ev_plus_outcome_safe_slice_ranking
```

Joined outcome sample:

```text
joined_outcomes: 128
top_quartile_size: 32
```

## Top-Quartile Results

```text
no_confidence: 10 favorable / 22 adverse = 31.25%
confidence_as_risk_penalty_only: 15 favorable / 17 adverse = 46.88%
outcome_safe_slice_confidence: 16 favorable / 16 adverse = 50.00%
ev_plus_outcome_safe_slice_ranking: 16 favorable / 16 adverse = 50.00%
penalize_high_conf_large_gap: 17 favorable / 15 adverse = 53.12%
```

The high-confidence large-gap penalty is the only candidate that produces a favorable-majority top quartile without explicitly forcing the known ETH YES favorable slice.

## Robustness Checks

### BTC vs ETH

`penalize_high_conf_large_gap` top quartile:

```text
ETH: 17 favorable / 11 adverse = 60.71%
BTC: 0 favorable / 4 adverse = 0.00%
```

Pass: it reduces BTC exposure but does not fully eliminate BTC adverse rows.

### YES vs NO

```text
NO: 10 favorable / 6 adverse = 62.50%
YES: 7 favorable / 9 adverse = 43.75%
```

Pass with caution: unlike prior rankings, NO is not the dominant failure in the top quartile. YES still contains adverse concentration.

### Price Bucket

```text
0.35-0.50: 3 favorable / 3 adverse = 50.00%
0.50-0.65: 13 favorable / 11 adverse = 54.17%
<0.35: 1 favorable / 1 adverse = 50.00%
```

Pass: the worst `0.35-0.50` bucket no longer dominates top ranking.

### Lifecycle Phase

```text
OPENING_SCAN: 12 favorable / 6 adverse = 66.67%
ACTIVE_INVENTORY_TRADING: 5 favorable / 9 adverse = 35.71%
```

Fail: ACTIVE_INVENTORY_TRADING remains adverse-heavy.

### Time Remaining

```text
time_bucket: missing for all joined top-quartile rows
```

Fail: cannot validate timing robustness.

### Liquidity

```text
THIN: 12 favorable / 7 adverse = 63.16%
ACCEPTABLE: 5 favorable / 6 adverse = 45.45%
STRONG: 0 favorable / 1 adverse
UNSTABLE: 0 favorable / 1 adverse
```

Mixed: THIN improves, ACCEPTABLE remains weak. Liquidity should not become a positive confidence replacement.

### Probability Gap

```text
10-20pp: 14 favorable / 10 adverse = 58.33%
20pp+: 3 favorable / 2 adverse = 60.00%
6-10pp: 0 favorable / 3 adverse = 0.00%
```

Mixed: high-gap top rows improve under penalty, but 6-10pp rows are weak.

### Sample Size Sensitivity

```text
top_quartile_size: 32
joined_total: 128
```

Fail: sample remains too small for runtime confidence.

## Robustness Pass / Fail Count

```text
robustness_pass_count: 4
  BTC/ETH exposure improves
  YES/NO balance improves
  price-bucket failure concentration improves
  top-quartile alignment becomes favorable-majority

robustness_fail_count: 4
  ACTIVE_INVENTORY_TRADING remains adverse-heavy
  time_remaining cannot be validated
  liquidity remains mixed
  sample size is too small
```

## Best Replay Candidate

best_replay_candidate:

```text
penalize_high_conf_large_gap
```

Why:

- It produces the best top-quartile alignment: `17 favorable / 15 adverse`.
- It does not hard-code the ETH YES favorable slice.
- It directly addresses the observed confidence inversion.
- It preserves a mixed enough top quartile to test generality.

## Candidate Spec

candidate_spec:

```text
name: confidence_gap_risk_penalty_v1
mode: replay_only
purpose: prevent high-confidence, high-gap rows from receiving positive rank boost

ranking change:
  start from existing score reconstruction
  subtract risk penalty when:
    confidence >= 0.70
    probability_gap >= 0.10

risk penalty:
  advisory simulation value: 4 ranking points

must remain unchanged:
  no execution behavior
  no live runtime
  no threshold change
  no trade sizing change
  no replay execution during this audit

primary evaluation:
  top-quartile favorable/adverse alignment
  BTC/ETH split
  YES/NO split
  price bucket split
  lifecycle split
  liquidity split
  confidence bucket split
```

This is a replay-only candidate spec, not an implementation request.

## Blocked Candidate Options

```text
outcome_safe_slice_confidence:
  blocked for now because it is history-fit to ETH YES 0.50-0.65.

ev_plus_outcome_safe_slice_ranking:
  blocked for same history-fit reason.

no_confidence:
  blocked because it improves too little: 31.25% top alignment.

confidence_as_risk_penalty_only:
  not blocked as concept, but weaker than high-confidence large-gap penalty.
```

## Acceptance Criteria

A replay-only candidate should pass all of the following before any implementation discussion:

```text
1. top_quartile_alignment >= 50%
2. top_quartile_adverse_count < current adverse count
3. BTC top-quartile adverse concentration reduced by at least 50%
4. NO-side top-quartile adverse concentration not worse than current
5. 0.35-0.50 top-quartile adverse concentration reduced
6. ACTIVE_INVENTORY_TRADING adverse rate explicitly measured
7. time_remaining lineage reconstructed or limitation documented
8. no reduction to a single overfit historical slice
```

## What Must Remain Blocked

Blocked:

```text
runtime mutation
live ranking change
threshold change
execution change
trade sizing change
confidence as positive global rank feature
slice-hardcoded deployment rule
```

## Evidence Missing

Missing evidence:

```text
larger joined outcome sample
time_remaining on joined rows
full live candidate ordering serialization
exact replay comparison
out-of-sample validation for ETH YES and BTC/NO slices
```

## Recommendation

The confidence replacement is robust enough for replay-only candidate design, not implementation. Candidate v1 should be `confidence_gap_risk_penalty_v1`. Outcome-safe slice logic should remain research-only until validated out of sample.

## Recommended Next Audit

recommended_next_audit:

```text
Replay-Only Ranking Candidate Dry Spec Review
```

Scope:

```text
1. Write a replay-only spec for confidence_gap_risk_penalty_v1.
2. Define required replay metrics and safety boundaries.
3. Confirm no runtime mutation or execution change.
4. Decide whether replay should be operator-approved in a later task.
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
