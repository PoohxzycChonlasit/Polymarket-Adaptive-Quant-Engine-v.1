# Replay-Only Ranking Candidate Dry Spec

audit_date: 2026-06-02
mode: dry_spec_only
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Candidate Summary

```text
candidate_name: confidence_gap_risk_penalty_v1
candidate_status: REPLAY_ONLY_SPEC
candidate_purpose: test whether high-confidence, high-probability-gap candidates should receive a ranking penalty instead of a positive confidence boost
recommended_next_step: operator-approved replay design review, not replay execution
```

This candidate exists because prior audits found that confidence is harmful as a global positive ranking feature. Current ranking promotes adverse-heavy high-confidence BTC/NO midprice candidates. The candidate is replay-only because the supporting evidence is based on a small joined outcome sample and proxy ranking simulations, not full replay.

## What It Changes Conceptually

The current ranking logic treats confidence as a positive score component. This candidate changes the concept:

```text
old concept:
  confidence increases rank

candidate concept:
  high confidence plus large probability gap is a risk condition
```

The candidate does not propose a live strategy change. It defines a replay-only ranking overlay for later validation.

## What It Must Not Change

blocked_runtime_changes:

```text
no live runtime mutation
no trading execution change
no replay execution in this task
no threshold change
no EV gate change
no confidence floor change
no position sizing change
no order routing change
no wallet/balance behavior change
no protected production behavior change
no push
```

## Ranking Inputs

ranking_inputs:

```text
ev_after_spread
probability_edge
confidence
p_yes
p_no
yes_ask
no_ask
selected_side
asset
price_bucket
probability_gap_bucket
lifecycle_phase
liquidity_depth_state
spread
delta_regime
time_remaining_seconds
candidate_id
paper_trade_replay_key
path_truth event_end outcome
```

The replay should preserve current ranking components and add candidate overlay fields so the old and candidate rankings can be compared side by side.

## Candidate Logic

Base candidate:

```text
start with existing reconstructed ranking score

if confidence >= 0.70
and probability_gap >= 0.10:
    apply confidence_gap_risk_penalty
```

Replay-only advisory penalty:

```text
confidence_gap_risk_penalty: 4 ranking points
```

The penalty value is not a runtime parameter. It is the value that produced the best read-only top-quartile simulation:

```text
top_quartile_alignment: 17 favorable / 15 adverse = 53.12%
```

## Confidence Penalty Logic

The candidate does not invert confidence globally. It only penalizes high confidence when paired with large claimed edge:

```text
confidence >= 0.70
probability_gap >= 0.10
```

Reason:

- high confidence alone may be noisy
- probability gap alone may be miscalibrated
- together they identified adverse-heavy ranking behavior in prior audits

## Probability Gap Penalty

The probability gap condition uses the selected side:

```text
YES: probability_gap = p_yes - yes_ask
NO:  probability_gap = p_no - no_ask
```

The penalty applies only when:

```text
probability_gap >= 0.10
```

This targets the 10-20pp and 20pp+ regions where claimed edge did not reliably improve outcomes.

## EV Treatment

EV treatment:

```text
do not change EV calculation
do not change EV gate
do not change min_ev
do not change ev_after_spread
do not replace EV with outcome-safe slices
```

Replay should compare:

```text
current_score
candidate_score
score_delta
rank_delta
```

## Blocked Slices

blocked_slices_for_runtime:

```text
BTC/NO hard block
ETH YES hard allow
0.35-0.50 hard block
outcome-safe slice deployment
historical favorable slice deployment
```

These remain blocked because they risk overfitting the small joined sample.

## Allowed Slices

allowed_slices_for_replay_analysis:

```text
BTC vs ETH
YES vs NO
0.35-0.50
0.50-0.65
OPENING_SCAN
ACTIVE_INVENTORY_TRADING
THIN liquidity
ACCEPTABLE liquidity
confidence 0.70+
probability_gap 10-20pp
probability_gap 20pp+
```

These are analysis slices only. They must not become live gates from this spec.

## Required Observability

required_observability:

```text
candidate_name
candidate_status
current_score
candidate_score
score_delta
current_rank
candidate_rank
rank_delta
confidence
probability_gap
confidence_gap_penalty_applied
confidence_gap_penalty_value
selected_side
asset
price_bucket
lifecycle_phase
liquidity_depth_state
spread
delta_regime
time_remaining_seconds
ev_after_spread
outcome_proxy_status
path_truth_join_status
favorable_from_entry
adverse_from_entry
```

Replay must make it possible to audit why a candidate moved up or down.

## Replay Metrics

replay_metrics:

```text
top_quartile_favorable_count
top_quartile_adverse_count
top_quartile_alignment
bottom_quartile_favorable_count
bottom_quartile_adverse_count
BTC_top_quartile_count
BTC_top_quartile_adverse_count
NO_top_quartile_count
NO_top_quartile_adverse_count
0.35_0.50_top_quartile_adverse_count
0.50_0.65_top_quartile_alignment
confidence_0.70_top_quartile_count
probability_gap_10pp_top_quartile_count
rank_delta_distribution
candidate_survival_count
path_truth_join_count
```

## Acceptance Gates

acceptance_gates:

```text
1. top_quartile_alignment >= 50%
2. top_quartile_adverse_count < current top_quartile_adverse_count
3. BTC top-quartile adverse concentration reduced by at least 50%
4. NO-side top-quartile adverse concentration not worse than current
5. 0.35-0.50 top-quartile adverse concentration reduced
6. ACTIVE_INVENTORY_TRADING adverse rate explicitly measured
7. time_remaining lineage reconstructed or limitation documented
8. no collapse into a single historical favorable slice
```

Passing all gates does not authorize deployment. It only authorizes further review.

## Rejection Gates

rejection_gates:

```text
1. top_quartile_alignment < current alignment
2. top_quartile_adverse_count not reduced
3. BTC adverse concentration remains dominant
4. NO-side adverse concentration worsens
5. 0.35-0.50 adverse concentration remains dominant
6. candidate ranking collapses to only one asset/side slice
7. path_truth join count too small for comparison
8. observability cannot explain rank movement
```

Any rejection gate should block promotion beyond replay-only research.

## Safety Guardrails

Safety guardrails:

```text
advisory_only: true
replay_only: true
no_live_trading: true
no_runtime_mutation: true
no_threshold_change: true
no_execution_change: true
operator_review_required: true
```

## Evidence Still Missing

Missing evidence:

```text
full replay result
larger joined path_truth sample
complete time_remaining lineage
exact live candidate ordering serialization
out-of-sample validation
side-by-side replay rank movement evidence
```

## What Would Pass

A replay would pass the dry spec only if it shows:

```text
better top-quartile alignment
lower adverse concentration
reduced BTC/high-confidence promotion
no overfit collapse
clear rank_delta observability
```

## What Would Fail

A replay would fail if:

```text
alignment does not improve
bad BTC/NO midprice rows remain top-ranked
confidence penalty removes favorable rows disproportionately
rank movements cannot be explained
sample size is too small
```

## Recommended Next Step

recommended_next_step:

```text
Operator-approved replay planning task for confidence_gap_risk_penalty_v1.
```

This task should remain separate from execution and should explicitly decide whether replay is allowed.

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
