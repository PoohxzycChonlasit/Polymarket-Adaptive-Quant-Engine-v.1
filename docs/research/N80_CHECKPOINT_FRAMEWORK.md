# N80 Checkpoint Framework

Date frozen: 2026-06-10

Candidate: ETH YES FIRST_CYCLE OPENING_SCAN hold > 15s

Mode: informational research governance only

## Purpose

Define the informational checkpoint to run when the canonical opportunity count
first reaches `n=80`.

N80 exists to describe the health of early forward validation, identify data or
evidence drift that must be watched through N100, and preserve a clear record of
the N71-N80 block.

**N80 is informational only and cannot override N100 architecture.**

N80 cannot:

- promote the candidate
- fail the candidate
- invalidate the candidate
- change the canonical cell
- change N100 thresholds
- change strategy, risk, execution, sizing, stop loss, config, or live behavior

## Evidence Boundary

```text
Rows 1-70   = discovery / retrospective selected-slice evidence
Rows 71-80  = N80 informational checkpoint block
Rows 71-100 = frozen N100 forward validation block
```

N80 must not reset, subdivide, or reinterpret the N71-N100 forward block. The
N71-N80 block is an interim view of the first 10 forward observations only.

## Data Integrity Check

Before reporting N80 health metrics, record:

| Field | Required N80 report |
|---|---|
| Canonical n | Exactly 80 |
| Raw qualifying rows | Count |
| Duplicate rows removed | Count and reconciliation note |
| Latest canonical key | Exact key |
| Outcome truth coverage | Count and rate |
| Export validation | Status |
| Export freshness | Status and timestamp |
| Regime join rate | Rate |
| UNKNOWN regime rate | Rate |
| N71-N80 boundary | Exact 10 canonical keys |

Data concerns at N80 create a warning only. They do not invalidate the candidate
or alter the N100 invalid-data rules.

## N80 Health Metrics

Report the cumulative N80 population and compare it with the frozen N70
snapshot:

| Metric | Required comparison |
|---|---|
| Canonical n | N80 value and change from N70 |
| Wins / losses | N80 cumulative and delta |
| WR | N80 cumulative versus N70 57.1% |
| PF | N80 cumulative versus N70 2.006 |
| Net PnL | N80 cumulative versus N70 +$0.215774 |
| Median PnL | N80 cumulative versus N70 +$0.005783 |
| p-value | N80 cumulative versus N70 0.141 |
| nc_PF | Current value versus N70 3.865 |
| Consecutive nc_PF below 1.0 | Current count |
| Calendar weeks / active dates | Current breadth |
| 7-day and 14-day velocity | Current accumulation rate |
| Remaining to N100 | Count |

These metrics describe trajectory only. N80 cumulative metrics cannot trigger
promotion, failure, invalidation, or a change to N100 interpretation.

## Forward-Block-Only Metrics

Report N71-N80 separately from cumulative N80:

- exactly 10 canonical opportunities
- exact canonical opportunity keys
- wins and losses
- WR
- PF
- net PnL
- median PnL
- gross winning PnL
- gross losing PnL
- average and median hold seconds
- TP / SL counts
- active dates and ISO weeks
- maximum observations from one date
- regime mix
- path-truth coverage

The N71-N80 block is too small for a final positive or negative verdict. Its
metrics must be labeled `EARLY_FORWARD_EVIDENCE`.

## Regime Drift

Report cumulative N80 and N71-N80 separately for:

- COMPRESSION
- TREND_DOWN
- SIDEWAY
- TREND_UP
- UNKNOWN

For each regime report:

| Metric | Required |
|---|---|
| n and share | Yes |
| Wins / losses | Yes |
| WR | Yes |
| PF | Yes |
| Net PnL | Yes |
| Median PnL | Yes |
| Active dates | Yes |

Compare against the frozen N70 regime mix:

| Regime | N70 n | N70 share |
|---|---:|---:|
| COMPRESSION | 21 | 30.0% |
| TREND_DOWN | 19 | 27.1% |
| SIDEWAY | 18 | 25.7% |
| TREND_UP | 12 | 17.1% |

Required notes:

- Whether COMPRESSION remains absent or returns.
- Whether TREND_UP reaches or exceeds the existing sample-doubling watch level
  of `n=14`.
- Whether one regime contributes more than half of N71-N80.
- Whether any regime accounts for most forward gains or losses.

No regime observation at N80 authorizes a runtime filter or a change to the
candidate definition.

## Concentration Drift

Report:

- Largest winning and losing N71-N80 trade.
- Top-1 and top-3 winner share of forward gross winning PnL.
- N71-N80 PF after removing its top winner.
- Maximum share of N71-N80 observations from one date.
- Maximum share from one ISO week.
- Largest winning and losing date.
- Cumulative ex-top-5 PF as an informational comparison with N70.

N80 concentration reporting is diagnostic only. Formal N100 concentration
thresholds remain unchanged and are not evaluated early.

## Path-Quality Drift

Report cumulative N80 and N71-N80 path evidence separately:

- path-truth matched count and rate
- MFE median
- MAE median
- percentage reaching positive unrealized PnL
- clean-path rate
- winner MFE / MAE
- loser MFE / MAE
- missing-path count and reasons

Assign one informational path label:

| Label | Meaning |
|---|---|
| `DIRECTION_STABLE` | Early forward path evidence is directionally consistent with N70 |
| `MIXED_PATH_SIGNAL` | Early path evidence is internally mixed |
| `COVERAGE_WARNING` | Coverage is too low or systematically missing |
| `CONTRADICTION_TO_WATCH` | Early path evidence conflicts with N70 and must be re-evaluated at N100 |

`CONTRADICTION_TO_WATCH` is not an N80 failure verdict and cannot override the
N100 path-quality rules.

## Warning Categories

N80 uses exactly three informational warning categories:

| Category | Meaning | Allowed action |
|---|---|---|
| `CLEAR` | No material early-forward concern observed | Continue accumulation |
| `WATCH` | A metric moved adversely or evidence is concentrated | Record and continue accumulation |
| `ESCALATE_AT_N100` | A concern may affect N100 interpretation if it persists | Highlight for the frozen N100 review |

Suggested warning triggers:

| Area | WATCH | ESCALATE_AT_N100 |
|---|---|---|
| Cumulative WR | At or below 52% | Below 50% |
| Cumulative PF | Below 1.5 | Below 1.3 |
| N71-N80 WR | Below 50% | Below 40% |
| N71-N80 PF | Below 1.3 | Below 1.0 |
| N71-N80 net PnL | Non-positive | Negative with PF below 1.0 |
| nc_PF | Below 1.0 | Persistent below 1.0 through the checkpoint |
| Regime concentration | One regime exceeds 50% of N71-N80 | One weak regime exceeds 60% |
| Date concentration | One date exceeds 40% of N71-N80 | One date exceeds 50% |
| Path coverage | Materially below N70 coverage | Systematically missing or contradictory |
| Data quality | Join or truth coverage concern | Concern persists into N100 preparation |

These thresholds are monitoring prompts only. They are not promotion, failure,
invalidation, kill, or strategy-change thresholds.

## Required N80 Output

The N80 checkpoint report must contain:

1. Data-integrity summary.
2. Cumulative N80 health table.
3. Exact N71-N80 canonical keys.
4. N71-N80 forward-block-only metrics.
5. Cumulative and forward regime tables.
6. Concentration drift section.
7. Path-quality drift section.
8. Warning summary using only `CLEAR`, `WATCH`, or `ESCALATE_AT_N100`.
9. Remaining count to N100.
10. The explicit non-decision statement below.

## Required Final Statement

Every N80 checkpoint report must end with:

> N80 is informational only and cannot override N100 architecture.

The only permitted operational conclusion at N80 is:

```text
CONTINUE_N71_N100_FORWARD_VALIDATION
```

No N80 result authorizes promotion, failure, invalidation, candidate
redefinition, or runtime, strategy, risk, execution, sizing, configuration, or
live-trading changes.
