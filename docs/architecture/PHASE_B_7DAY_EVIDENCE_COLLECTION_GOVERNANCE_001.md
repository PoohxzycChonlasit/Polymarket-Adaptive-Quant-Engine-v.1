# PHASE_B_7DAY_EVIDENCE_COLLECTION_GOVERNANCE_001

## Final Verdict

READY_FOR_EVIDENCE_COLLECTION

## Current State

Phase B live smoke status:

```text
PHASE_B_LIVE_SMOKE_PASS
```

Active runtime:

```text
run_id = 20260621T135117Z_28788_c56985cf
```

Phase B telemetry path:

```text
runtime/quant_data/signal_filter_shadow_phase_b/YYYY-MM-DD.jsonl
```

Legacy telemetry path:

```text
runtime/quant_data/signal_filter_shadow/YYYY-MM-DD.jsonl
```

This governance document authorizes evidence collection and review only. It does not authorize active blocking, strategy changes, sizing changes, risk changes, execution changes, or Phase C promotion.

## Scope

Filters under daily governance:

```text
block_btc_shadow
block_normal_vol_shadow
combined_broad_shadow
combined_conservative_shadow
```

Excluded from governance:

```text
block_edge_lt_005_shadow
```

Reason:

```text
It is not part of the requested four-filter Phase B evidence set.
```

## Evidence Sources

Primary Phase B source:

```text
runtime/quant_data/signal_filter_shadow_phase_b/YYYY-MM-DD.jsonl
```

Required Phase B schema:

- `filter_name`
- `filter_version == "1.0.0"`
- `filter_params`
- `shadow_pass`
- `shadow_reason`
- `would_trade`
- `run_id`
- `signal_id`
- `candidate_instance_id`
- `paper_trade_replay_key`
- `asset`
- `side`
- `edge`
- `ev`
- `probability`
- `entry_price`
- `proposed_size_usd`

PnL source:

```text
runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl
```

Join keys, in priority order:

1. `paper_trade_replay_key`
2. `candidate_instance_id`
3. `signal_id`
4. fallback only if explicitly audited: `run_id + condition_id + asset + side + nearest timestamp`

Runtime health source:

```text
runtime/quant_data/system_health/YYYY-MM-DD.jsonl
```

Ownership source:

```text
runtime/ownership/paper_runtime_owner.json
```

## Core Accounting Rules

Phase B is passive. It does not create or close trades.

All daily PnL metrics must be derived by joining Phase B filter decisions to actual baseline paper trade outcomes.

For each filter and review window:

```text
baseline_trades = all closed baseline paper trades with a joinable Phase B row for that filter
passed_trades = baseline_trades where shadow_pass == true
rejected_trades = baseline_trades where shadow_pass == false
```

Metric definitions:

| Metric | Definition |
| --- | --- |
| `candidates_seen` | Count of Phase B rows for the filter, before trade-close join |
| `closed_candidates_seen` | Count of candidates with a joined closed trade outcome |
| `candidates_passed` | Count of Phase B rows with `shadow_pass == true` |
| `candidates_rejected` | Count of Phase B rows with `shadow_pass == false` |
| `pass_rate` | `candidates_passed / candidates_seen` |
| `realized_pnl` | Sum of joined closed-trade PnL for `passed_trades` |
| `rejected_pnl` | Sum of joined closed-trade PnL for `rejected_trades` |
| `baseline_pnl` | `realized_pnl + rejected_pnl` |
| `delta_vs_baseline` | `realized_pnl - baseline_pnl`, equivalent to `-rejected_pnl` |
| `profit_factor` | `gross_profit(passed_trades) / abs(gross_loss(passed_trades))` |
| `winrate` | `winning passed_trades / non-flat passed_trades` |
| `max_drawdown` | Max peak-to-trough drawdown of cumulative `passed_trades` PnL in event time order |
| `baseline_max_drawdown` | Max peak-to-trough drawdown of cumulative `baseline_trades` PnL in event time order |
| `drawdown_delta` | `max_drawdown - baseline_max_drawdown`; lower is better |

Profit-factor edge cases:

| Condition | PF value |
| --- | --- |
| `gross_profit > 0` and `gross_loss == 0` | `INF`, but promotion cannot rely on PF alone |
| `gross_profit == 0` and `gross_loss == 0` | `UNDEFINED` |
| `closed passed_trades < 10` | `UNDERPOWERED` regardless of numeric PF |

## Daily Evidence Collection

Daily collection window:

```text
00:00:00Z to 23:59:59Z
```

Every daily collection must report both:

```text
day_only metrics
rolling_7_day metrics
```

For each filter, report:

| Field | Required |
| --- | --- |
| `filter_name` | yes |
| `filter_version` | yes |
| `runtime_days_observed` | yes |
| `schema_complete_rows` | yes |
| `schema_incomplete_rows` | yes |
| `joinable_closed_trades` | yes |
| `join_coverage_pct` | yes |
| `candidates_seen` | yes |
| `candidates_passed` | yes |
| `candidates_rejected` | yes |
| `pass_rate` | yes |
| `realized_pnl` | yes |
| `profit_factor` | yes |
| `max_drawdown` | yes |
| `winrate` | yes |
| `rejected_pnl` | yes |
| `delta_vs_baseline` | yes |
| `baseline_pnl` | yes |
| `baseline_profit_factor` | yes |
| `baseline_max_drawdown` | yes |
| `top_reject_reason` | yes |
| `asset_mix` | yes |
| `regime_mix` | yes |
| `exception_count` | yes |

Daily evidence must also include:

- active runtime PID and run_id
- owner status
- heartbeat age
- duplicate runtime status
- Phase B category row count
- legacy category leakage check

## Promotion State Machine

Every filter must have exactly one status:

```text
NOT_READY
WATCHLIST
CANDIDATE
PROMOTION_REVIEW
```

Status can only move one level upward per weekly review:

```text
NOT_READY -> WATCHLIST -> CANDIDATE -> PROMOTION_REVIEW
```

Status can move downward immediately if failure criteria trigger.

## Minimum Evidence Requirements

Hard minimums for any filter to leave `NOT_READY`:

| Requirement | Minimum |
| --- | ---: |
| Runtime days observed | 3 calendar days |
| Phase B schema completeness | 100% |
| Phase B category leakage | 0 old-schema rows |
| Legacy category leakage | 0 Phase B rows for the active run |
| Runtime shadow/telemetry exceptions | 0 |
| Join coverage to closed trades | >= 95% |
| Closed trades joined for the filter | >= 20 |

Hard minimums for `PROMOTION_REVIEW`:

| Requirement | Minimum |
| --- | ---: |
| Runtime days observed | >= 7 calendar days |
| Closed trades joined for the filter | >= 50 |
| Join coverage to closed trades | >= 98% |
| Schema completeness | 100% |
| Runtime shadow/telemetry exceptions | 0 |
| Distinct market epochs | >= 30 |
| Distinct UTC days with closed trades | >= 5 |

## Status Criteria

### NOT_READY

Assign `NOT_READY` if any of the following is true:

- runtime days observed < 3
- closed joined trades < 20
- join coverage < 95%
- Phase B schema completeness < 100%
- old-schema row appears in `signal_filter_shadow_phase_b`
- Phase B row appears in `signal_filter_shadow`
- shadow telemetry exception count > 0
- duplicate runtime contamination is detected
- any required metric is unavailable

### WATCHLIST

Assign `WATCHLIST` if all are true:

- runtime days observed >= 3
- closed joined trades >= 20
- join coverage >= 95%
- schema completeness == 100%
- shadow telemetry exception count == 0
- `delta_vs_baseline > 0`
- `profit_factor >= 1.00`
- `max_drawdown <= baseline_max_drawdown * 1.10`

WATCHLIST means:

```text
Information value exists, but sample is not yet sufficient for promotion consideration.
```

### CANDIDATE

Assign `CANDIDATE` if all are true:

- runtime days observed >= 5
- closed joined trades >= 35
- join coverage >= 97%
- `delta_vs_baseline > 0`
- `profit_factor` meets the filter-specific candidate PF threshold
- `winrate >= baseline_winrate - 5 percentage points`
- `max_drawdown <= baseline_max_drawdown`
- rejected trades have non-positive aggregate PnL:

```text
rejected_pnl <= 0
```

Filter-specific CANDIDATE PF thresholds:

| Filter | PF threshold |
| --- | ---: |
| `block_btc_shadow` | >= 1.00 |
| `block_normal_vol_shadow` | >= 1.15 |
| `combined_broad_shadow` | >= 1.10 |
| `combined_conservative_shadow` | >= 1.25 |

### PROMOTION_REVIEW

Assign `PROMOTION_REVIEW` if all hard minimums are met and all filter-specific promotion criteria are true.

Universal promotion criteria:

- runtime days observed >= 7
- closed joined trades >= 50
- join coverage >= 98%
- `delta_vs_baseline > 0`
- `rejected_pnl < 0`
- `max_drawdown <= baseline_max_drawdown`
- `drawdown_delta <= 0`
- `winrate >= baseline_winrate`
- no failure criterion is active

Filter-specific promotion criteria:

| Filter | Minimum PF | Minimum delta_vs_baseline | Maximum drawdown increase |
| --- | ---: | ---: | ---: |
| `block_btc_shadow` | >= 1.00 | > 0.00 | 0.00 |
| `block_normal_vol_shadow` | >= 1.20 | > 0.00 | 0.00 |
| `combined_broad_shadow` | >= 1.15 | > 0.00 | 0.00 |
| `combined_conservative_shadow` | >= 1.35 | > 0.00 | 0.00 |

PROMOTION_REVIEW does not mean deploy.

It means:

```text
The filter is eligible for a separate Phase C active-blocking review.
```

## Failure Criteria

A filter must be marked `NOT_READY` or `REJECTED_FOR_PHASE_C_REVIEW` in the weekly notes if any failure condition is active, even if it is profitable.

Failure criteria:

| Failure | Rule |
| --- | --- |
| Schema failure | Any Phase B row in `signal_filter_shadow_phase_b` missing required schema |
| Category leakage | Any old-schema row in Phase B category, or Phase B row in legacy category |
| Runtime exception | Any shadow telemetry exception, traceback, or uncaught telemetry error |
| Duplicate runtime | More than one active owner or contaminated run evidence |
| Low join coverage | Join coverage < 95% daily or < 98% weekly |
| Positive rejected PnL | `rejected_pnl > 0` after 50 closed joined trades |
| Hidden profit destruction | `delta_vs_baseline <= 0` after 50 closed joined trades |
| Drawdown worse than baseline | `max_drawdown > baseline_max_drawdown` at PROMOTION_REVIEW stage |
| Profit concentration | More than 60% of total positive PnL from one trade |
| Day concentration | More than 70% of total positive PnL from one UTC day |
| Epoch concentration | More than 25% of closed joined trades from one market epoch family |
| Regime blind spot | More than 80% of passed trades from one regime unless the filter explicitly targets that regime |
| Too few rejected trades | `candidates_rejected < 10` after 50 closed joined trades |
| Too few passed trades | `passed closed trades < 10` after 50 closed joined trades |
| Profitable only by flat removal | PF improves but `delta_vs_baseline <= 0` |

Rejected filters can remain logged passively but must not enter `PROMOTION_REVIEW` without a new pre-registered review.

## Weekly Review Report Format

Weekly report file name:

```text
PHASE_B_WEEKLY_EVIDENCE_REVIEW.md
```

Required sections:

1. Executive Summary
2. Runtime Coverage
3. Schema Integrity
4. Filter Evidence Table
5. Baseline Comparison
6. Rejected Trade Attribution
7. Drawdown And Path Quality
8. Concentration And Bias Checks
9. Failure Criteria Audit
10. Status Assignment
11. Promotion Eligibility
12. Operator Decision Log
13. Final Verdict

Required weekly filter table:

| Filter | Status | Runtime Days | Closed Trades | Pass Rate | WR | PF | PnL | Rejected PnL | Delta vs Baseline | Max DD | Failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `block_btc_shadow` |  |  |  |  |  |  |  |  |  |  |  |
| `block_normal_vol_shadow` |  |  |  |  |  |  |  |  |  |  |  |
| `combined_broad_shadow` |  |  |  |  |  |  |  |  |  |  |  |
| `combined_conservative_shadow` |  |  |  |  |  |  |  |  |  |  |  |

Allowed weekly verdicts:

```text
PHASE_B_COLLECTION_HEALTHY
PHASE_B_COLLECTION_CAUTION
PHASE_B_COLLECTION_INVALID
```

Filter-specific allowed statuses:

```text
NOT_READY
WATCHLIST
CANDIDATE
PROMOTION_REVIEW
REJECTED_FOR_PHASE_C_REVIEW
```

## Operator Dashboard Fields

Daily operator dashboard should monitor:

### Runtime Health

- active run_id
- owner PID
- heartbeat age
- duplicate runtime detected YES/NO
- shadow telemetry exception count
- system health traceback count
- active `SHADOW_TELEMETRY_ENABLED` status

### Schema Health

- Phase B row count today
- Phase B schema completeness %
- old-schema rows in Phase B category
- Phase B rows in legacy category
- malformed JSONL rows
- join coverage %

### Evidence Velocity

- candidates_seen by filter
- closed joined trades by filter
- daily closed-trade velocity
- estimated days to 50 closed trades per filter
- estimated days to 7-day review completion

### Filter Quality

For each filter:

- pass_rate
- candidates_passed
- candidates_rejected
- realized_pnl
- rejected_pnl
- delta_vs_baseline
- PF
- WR
- max_drawdown
- top reject reason
- current status

### Safety Flags

- positive rejected_pnl
- delta_vs_baseline <= 0
- max_drawdown worse than baseline
- profit concentration > 60%
- day concentration > 70%
- join coverage below gate
- exception count > 0

## Promotion Governance

No filter can become active from Phase B evidence alone.

Promotion sequence:

```text
Phase B passive collection
-> weekly evidence review
-> PROMOTION_REVIEW status
-> separate Phase C design
-> separate Phase C implementation plan
-> separate controlled paper validation
-> explicit operator approval
```

Forbidden conclusions from Phase B:

- "This filter is production ready"
- "This filter can block trades now"
- "This filter improves live trading"
- "This filter is safe under real execution sizing"
- "This filter should be enabled without Phase C review"

Allowed conclusions from Phase B:

- "This filter is not ready"
- "This filter has passive information value"
- "This filter is eligible for further review"
- "This filter failed passive evidence gates"
- "This filter needs more runtime evidence"

## Daily Collection Checklist

Each day:

- [ ] Confirm exactly one active paper runtime owner.
- [ ] Confirm heartbeat age is fresh.
- [ ] Confirm Phase B category has rows for active run_id.
- [ ] Confirm Phase B schema completeness is 100%.
- [ ] Confirm legacy category has no Phase B rows for active run_id.
- [ ] Join Phase B rows to closed trade outcomes.
- [ ] Compute daily metrics for all four filters.
- [ ] Compute rolling 7-day metrics for all four filters.
- [ ] Check failure criteria.
- [ ] Assign status for each filter.
- [ ] Record warnings without changing strategy, sizing, risk, or execution.

## Final Statement

Phase B is now ready for passive 7-day evidence collection under the isolated category:

```text
runtime/quant_data/signal_filter_shadow_phase_b/
```

Final verdict:

```text
READY_FOR_EVIDENCE_COLLECTION
```
