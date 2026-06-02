# Trade Ranking Failure Audit

audit_date: 2026-06-02
mode: read_only_ranking_audit
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Executive Summary

The ranking layer promotes bad candidates above good candidates. In the joined outcome sample, adverse trades have a higher average ranking score than favorable trades. The top-ranked quartile is adverse-heavy, while favorable outcomes are more common in the lower-ranked portion than they should be.

Required outputs:

```text
ranking_feature_count: 10
ranking_bias_count: 5 primary positive-bias contributors
favorable_rank_distribution: mean percentile 47.69%, top quartile 9, bottom quartile 14
adverse_rank_distribution: mean percentile 52.12%, top quartile 24, bottom quartile 18
top_bad_promoter_feature: EV/probability_edge score saturation, amplified by confidence
top_good_suppressor_feature: lower confidence despite similar EV/edge
ranking_failure_mode: score rewards claimed edge and confidence even when those features are anti-correlated with outcome quality
recommended_next_audit: Ranking Feature Ablation and Anti-Confidence Simulation Audit
```

No runtime change is recommended from this audit.

## Ranking Formula Inspected

`polymarket/opportunity_scanner.py` ranks candidates with:

```text
score =
  clamp(ev * 100, -5, 10)
+ clamp(probability_edge * 100, -5, 10)
+ confidence_score
+ liquidity_score
+ momentum_score
+ distance_bonus
- spread_penalty
- delta_penalty
- drawdown_penalty
- time_penalty
```

Where:

```text
confidence_score = clamp((confidence - 0.50) * 10, 0, 3)
liquidity_score = clamp(liquidity / 1000, 0, 2)
momentum_score = velocity score + orderbook imbalance score
distance_bonus = clamp(0.004 / abs(distance_to_strike), 0, 1.5)
```

The largest positive terms are EV and probability edge. Each can contribute up to 10 points, so claimed model edge dominates the ranking.

## Data Inspected

Inputs:

- `polymarket/opportunity_scanner.py`
- `polymarket/trader.py`
- `runtime/quant_data/decision_log/*.jsonl`
- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- market snapshot fields carried through decision/trade rows

Sample:

```text
decision_rows_inspected: 247,271
trade_open_rows: 433
joined_trade_outcomes: 128
favorable_joined: 50
adverse_joined: 78
```

## Favorable vs Adverse Ranking

Joined outcome rank distribution:

```text
favorable mean rank percentile: 47.69%
adverse mean rank percentile: 52.12%

favorable in top quartile: 9
adverse in top quartile: 24

favorable in bottom quartile: 14
adverse in bottom quartile: 18

top quartile outcome: 9 favorable / 24 adverse
bottom quartile outcome: 14 favorable / 18 adverse
```

This answers the central question: favorable rows are ranked lower than adverse rows on average.

## Which Feature Dominates Ranking?

The dominant ranking features are EV and probability edge.

Mean score components:

```text
adverse ev_score: 9.6132
favorable ev_score: 9.4443

adverse edge_score: 9.6132
favorable edge_score: 9.4443

adverse confidence_score: 1.1397
favorable confidence_score: 0.8949
```

Because EV and edge are capped at 10 and most joined trades are near the cap, they compress candidates into a high-score band. Confidence then breaks ties in the wrong direction.

## Which Feature Pushes Bad Trades Up?

Top bad promoter feature:

```text
EV/probability_edge score saturation
```

The ranking formula gives adverse outcomes slightly higher EV and edge scores than favorable outcomes:

```text
adverse - favorable ev_score: +0.1689
adverse - favorable edge_score: +0.1689
adverse - favorable confidence_score: +0.2448
adverse - favorable score_proxy: +0.6266
```

This is the core ranking failure: bad trades are not just slipping through. They are being actively promoted by the score.

## Which Feature Suppresses Good Trades?

Top good suppressor feature:

```text
lower confidence despite similar EV/edge
```

Favorable rows have slightly lower confidence:

```text
favorable confidence mean: 0.5895
adverse confidence mean: 0.6140
```

Favorable rows also receive lower confidence-score contribution:

```text
favorable confidence_score mean: 0.8949
adverse confidence_score mean: 1.1397
```

This means the ranking system is using confidence as a positive ranking feature even though confidence is not outcome-ranked.

## Top-ranked Candidates

The top quartile is adverse-heavy:

```text
top quartile: 9 favorable / 24 adverse
```

Top bad promoted slices:

```text
BTC NO 0.35-0.50: 7 adverse
BTC YES 0.50-0.65: 6 adverse
ETH NO 0.50-0.65: 2 adverse
ETH NO 0.35-0.50: 2 adverse
BTC NO 0.50-0.65: 2 adverse
BTC YES 0.35-0.50: 2 adverse
```

The highest-ranked bad candidates cluster in BTC and NO-side midprice slices, matching prior audits.

## Bottom-ranked Candidates

The bottom quartile is still adverse-heavy, but less severely:

```text
bottom quartile: 14 favorable / 18 adverse
```

Bottom good suppressed slices:

```text
ETH YES 0.50-0.65: 6 favorable
ETH NO 0.50-0.65: 6 favorable
BTC YES 0.50-0.65: 2 favorable
```

This suggests the ranking layer is not identifying the better ETH midprice rows with enough consistency.

## Executed vs Rejected Candidates

Executed trade-open rows score much higher than rejected or skipped decision rows:

```text
executed score_proxy mean: 16.5135
rejected score_proxy mean: 7.0879

executed ev_score median: 10
rejected ev_score median: 0

executed edge_score median: 10
rejected edge_score median: 9.3937

executed confidence_score mean: 1.0095
rejected confidence_score mean: 0.3491
```

The admission stack is selecting high-claimed-edge, high-confidence rows. The issue is that those selected rows are not outcome-ranked.

## Asset-specific Ranking Failure

The highest-ranked adverse clusters are BTC-heavy:

```text
BTC NO 0.35-0.50: top bad cluster
BTC YES 0.50-0.65: second top bad cluster
```

Asset-specific failure:

```text
BTC ranking is materially worse than ETH ranking.
```

The ranking system appears to treat BTC and ETH score features as comparable, but prior outcome audits show BTC is much weaker.

## Side-specific Ranking Failure

NO-side ranking is worse than YES-side ranking:

```text
NO midprice rows are repeatedly promoted into adverse top-score clusters.
```

The worst top-bad cluster is:

```text
BTC NO 0.35-0.50
```

This indicates side-specific ranking calibration is missing.

## Lifecycle-specific Ranking Failure

Lifecycle fields were available but not strong enough to explain ranking quality on their own. Prior audits show:

```text
OPENING_SCAN has larger adverse count
ACTIVE_INVENTORY_TRADING has worse adverse rate
```

In this ranking audit, lifecycle does not appear to be a dominant ranking component. That is itself a problem: the ranking formula heavily rewards claimed edge and confidence, while lifecycle risk is not strongly represented in the score.

## Ranking Bias Count

Primary ranking biases identified:

```text
1. EV score saturation promotes claimed edge.
2. Probability edge score duplicates EV-like signal.
3. Confidence score rewards bad extremity.
4. Distance bonus is always high in joined rows.
5. Lifecycle/asset/side risk is not penalized in ranking.
```

ranking_bias_count: 5

## What Failed

Ranking failed because it ranks model-claimed opportunity, not realized outcome quality. EV, probability edge, and confidence are all derived from the same miscalibrated probability stack. The score then double-counts that stack:

```text
EV score + probability edge score + confidence score
```

When probability is wrong, the ranking score becomes confidently wrong.

## Evidence Missing

Missing or weak evidence:

```text
logged final candidate ordering is incomplete for all candidate pools
score is not always serialized on trade opens
exact opportunity scanner component scores are not serialized
ranking comparison uses proxy reconstruction where needed
joined outcome sample is 128 rows
rejected candidates generally lack outcome labels
market snapshot ordering is contextual, not a full execution ranking trace
```

The conclusion is strong enough for research direction, but not enough for runtime change.

## Recommended Next Audit

recommended_next_audit:

```text
Ranking Feature Ablation and Anti-Confidence Simulation Audit
```

Scope:

```text
1. Remove duplicate EV/probability-edge contribution in read-only simulation.
2. Penalize confidence in known bad slices: BTC, NO, 0.35-0.50, high confidence.
3. Add advisory asset/side/lifecycle risk penalties.
4. Compare top-quartile favorable/adverse outcome shift.
5. Verify whether ETH YES 0.50-0.65 remains rankable without promoting BTC/NO failures.
```

No replay, runtime change, threshold change, strategy change, or execution change should occur before that audit.

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
