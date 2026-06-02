# Confidence Gap Risk Penalty v1 Implementation Plan

plan_date: 2026-06-02
candidate_name: confidence_gap_risk_penalty_v1
implementation_plan_status: PLAN_ONLY
operator_next_approval: approve replay-only implementation
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Purpose

Plan a replay-only comparison tool for `confidence_gap_risk_penalty_v1`.

This document does not authorize implementation, replay, runtime mutation, strategy changes, threshold changes, or execution changes.

## Intended Replay-only Module Path

Intended future module path:

```text
research/replay_tools/confidence_gap_risk_penalty_v1_replay.py
```

The module must be read-only against runtime data and additive-only for research outputs.

## Input Files

Input files:

```text
runtime/quant_data/decision_log/*.jsonl
runtime/quant_data/trade_journal/*.jsonl
runtime/quant_data/path_truth/*.jsonl
runtime/quant_data/market_snapshots/*.jsonl
docs/research/confidence_gap_risk_penalty_v1_replay_plan.md
docs/research/replay_only_ranking_candidate_dry_spec.md
docs/research/confidence_replacement_robustness_replay_candidate_spec.md
```

## Output Files

Output files allowed only after implementation approval:

```text
research/replay_outputs/confidence_gap_risk_penalty_v1_replay_summary.json
research/replay_outputs/confidence_gap_risk_penalty_v1_rank_deltas.json
research/replay_outputs/confidence_gap_risk_penalty_v1_slice_metrics.json
docs/research/confidence_gap_risk_penalty_v1_replay_result.md
```

## Ranking Formula Description

Current score reconstruction:

```text
current_score =
  ev_score
+ probability_edge_score
+ confidence_score
+ liquidity_score
+ momentum_score
+ distance_bonus
- spread_penalty
- delta_penalty
- drawdown_penalty
- time_penalty
```

Candidate overlay:

```text
if confidence >= 0.70
and selected_side_probability_gap >= 0.10:
    candidate_score = current_score - 4.0
else:
    candidate_score = current_score
```

Selected-side probability gap:

```text
YES: p_yes - yes_ask
NO:  p_no - no_ask
```

## Observability Fields

Required observability fields:

```text
candidate_name
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

## CLI Command Proposal

Proposed future CLI:

```text
python research/replay_tools/confidence_gap_risk_penalty_v1_replay.py --dry-run
python research/replay_tools/confidence_gap_risk_penalty_v1_replay.py --write-research-outputs
```

Rules:

```text
--dry-run must not write outputs
--write-research-outputs may write only approved research output files
no execution flags
no trading flags
no runtime mutation flags
```

## Test Plan

test_plan_required: true

Future tests must verify:

```text
input parsing is read-only
score reconstruction is deterministic
penalty applies only when confidence >= 0.70 and probability_gap >= 0.10
rank deltas are calculated correctly
path_truth joins are optional and explicit
outputs are additive research files only
runtime/config/trading files are not written
```

## Acceptance Gates

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

## Rejection Gates

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

## Safety Guardrails

Safety guardrails:

```text
plan_only: true
operator_approval_required_for_implementation: true
no_replay_execution: true
no_runtime_mutation: true
no_strategy_change: true
no_threshold_change: true
no_execution_change: true
no_trading_execution: true
no_push: true
```

## Allowed Future Files

allowed_future_files:

```text
research/replay_tools/confidence_gap_risk_penalty_v1_replay.py
research/replay_outputs/confidence_gap_risk_penalty_v1_replay_summary.json
research/replay_outputs/confidence_gap_risk_penalty_v1_rank_deltas.json
research/replay_outputs/confidence_gap_risk_penalty_v1_slice_metrics.json
docs/research/confidence_gap_risk_penalty_v1_replay_result.md
tests/test_confidence_gap_risk_penalty_v1_replay.py
```

## Forbidden Files

forbidden_files:

```text
polymarket/*.py
runtime/*
config/*
.env
.env.*
secrets/*
wallet files
execution code
strategy code
threshold settings
trading runtime files
```

## Pytest Files To Create Later

pytest files that must be created later if implementation is approved:

```text
tests/test_confidence_gap_risk_penalty_v1_replay.py
```

Required pytest coverage:

```text
penalty trigger
penalty non-trigger
YES probability gap
NO probability gap
rank delta calculation
read-only input handling
approved output paths only
```

## Rollback / No-op Guarantee

Rollback / no-op guarantee:

```text
This document is plan-only.
No implementation is created.
No replay is executed.
No runtime files are changed.
No strategy behavior is changed.
No threshold is changed.
No execution behavior is changed.
If later implementation is rejected, no rollback is required because this task creates only a research plan.
```

## Recommended Next Step

operator_next_approval:

```text
approve replay-only implementation
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
