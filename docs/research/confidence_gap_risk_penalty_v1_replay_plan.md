# Confidence Gap Risk Penalty v1 Replay Plan

plan_date: 2026-06-02
candidate_name: confidence_gap_risk_penalty_v1
plan_status: AWAITING_OPERATOR_APPROVAL
operator_approval_required: true
mode: planning_only
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## 1. Replay Objective

Evaluate whether `confidence_gap_risk_penalty_v1` improves replay-only ranking quality by reducing high-confidence, high-gap adverse candidates in the top-ranked set.

Primary objective:

```text
Improve top-quartile favorable/adverse alignment without collapsing ranking into one overfit historical slice.
```

## 2. Candidate Logic Summary

Candidate logic:

```text
start with existing ranking score

if confidence >= 0.70
and probability_gap >= 0.10:
    subtract 4 ranking points
```

Selected-side probability gap:

```text
YES: p_yes - yes_ask
NO:  p_no - no_ask
```

## 3. Required Input Data

Required input data:

```text
decision_log
trade_journal
path_truth
market_snapshots
candidate_id
paper_trade_replay_key
selected_side
asset
p_yes / p_no
yes_ask / no_ask
confidence
ev_after_spread
spread
liquidity_depth_state
lifecycle_phase
delta_regime
time_remaining_seconds
favorable/adverse event_end outcome proxy
```

## 4. Required Observability Fields

Required observability:

```text
candidate_name
plan_status
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
path_truth_join_status
favorable_from_entry
adverse_from_entry
```

## 5. Replay Windows

Replay windows should be operator selected before implementation.

Recommended windows:

```text
primary: all available joined trade/path_truth event_end rows
secondary: latest 7 decision-log days
diagnostic: BTC/NO midprice rows
diagnostic: high-confidence high-gap rows
diagnostic: ETH YES 0.50-0.65 rows
```

No replay window is approved by this document.

## 6. Replay Metrics

Replay metrics:

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

## 7. Acceptance Gates

acceptance_gate_count: 8

Acceptance gates:

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

## 8. Rejection Gates

rejection_gate_count: 8

Rejection gates:

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

## 9. Safety Guardrails

Safety guardrails:

```text
planning_only: true
operator_approval_required: true
no_replay_execution: true
no_runtime_mutation: true
no_strategy_change: true
no_threshold_change: true
no_execution_change: true
no_trading_execution: true
no_push: true
```

## 10. Test Scope

replay_scope:

```text
replay-only ranking comparison
current ranking vs confidence_gap_risk_penalty_v1
no order execution
no live trading
no threshold mutation
no runtime behavior mutation
```

## 11. Files That May Be Read

Files that may be read during an approved implementation:

```text
polymarket/opportunity_scanner.py
polymarket/probability_model.py
polymarket/trader.py
runtime/quant_data/decision_log/*.jsonl
runtime/quant_data/trade_journal/*.jsonl
runtime/quant_data/path_truth/*.jsonl
runtime/quant_data/market_snapshots/*.jsonl
docs/research/replay_only_ranking_candidate_dry_spec.md
docs/research/confidence_replacement_robustness_replay_candidate_spec.md
```

## 12. Files That Must Not Be Modified

Files that must not be modified:

```text
polymarket/*.py
runtime/*
config/*
.env
.env.*
secrets/*
wallet files
trading runtime files
execution code
strategy code
threshold settings
```

## 13. Files That May Be Created Later If Approved

Files that may be created later only if implementation is explicitly approved:

```text
docs/research/confidence_gap_risk_penalty_v1_replay_result.md
research/replay_outputs/confidence_gap_risk_penalty_v1_replay_summary.json
research/replay_outputs/confidence_gap_risk_penalty_v1_rank_deltas.json
research/replay_outputs/confidence_gap_risk_penalty_v1_slice_metrics.json
```

No such files are created by this planning task.

## 14. Operator Approval Checklist

Operator approval checklist:

```text
[ ] approve replay-only implementation plan
[ ] confirm no runtime mutation
[ ] confirm no trading execution
[ ] confirm no threshold change
[ ] confirm replay windows
[ ] confirm output file paths
[ ] confirm observability fields
[ ] confirm acceptance/rejection gates
[ ] confirm no push
```

## 15. Rollback / No-op Guarantee

Rollback / no-op guarantee:

```text
This planning document changes no code.
No replay is executed.
No runtime files are modified.
No strategy behavior changes.
No thresholds change.
No execution path changes.
If replay implementation is later approved, it must be read-only and produce additive research outputs only.
```

## Recommended Next Step

recommended_next_step:

```text
approve replay-only implementation plan
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
