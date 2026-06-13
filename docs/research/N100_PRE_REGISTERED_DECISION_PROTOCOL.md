# N100 Decision Architecture

Date frozen: 2026-06-10

Candidate: ETH YES FIRST_CYCLE OPENING_SCAN hold > 15s

Mode: research governance only

Runtime authority: None

## Purpose

Define exactly how the N100 evidence snapshot will be interpreted before any
N71-N100 outcomes are reviewed.

This architecture freezes the decision rules, required evidence, allowed
conclusions, and forbidden conclusions. Thresholds must not be changed after
seeing N100 results.

## Evidence Boundary

```text
Rows 1-70   = discovery / retrospective selected-slice evidence
Rows 71-100 = forward validation block
```

The cumulative N100 population and the N71-N100 forward block must always be
reported separately. Strong cumulative results cannot conceal a weak forward
block. Strong forward results cannot repair invalid cumulative data.

Canonical cell:

```text
asset == ETH
AND side == YES
AND trade_open lifecycle contains OPENING_SCAN
AND hold_seconds > 15
AND outcome truth exists
```

Canonical duplicate key:

```text
condition_id | epoch_start_ts | asset | side | candidate_id
```

## Decision Order

Evaluate N100 in this fixed order:

1. Validate source data and reproduce exactly 100 canonical opportunities.
2. Evaluate formal kill criteria.
3. Evaluate N71-N100 forward-block evidence.
4. Evaluate cumulative promotion criteria.
5. Evaluate regime, concentration, and path-quality evidence.
6. Assign exactly one scenario and one governor verdict.

An invalid-data result stops all performance interpretation.

## Required Metrics

### Count And Data Integrity

| Metric | Requirement |
|---|---|
| Canonical n | Exactly 100 unique logical opportunities |
| Raw qualifying rows | Reported |
| Duplicate rows removed | Reported and reconciled |
| Outcome truth coverage | 100% |
| Regime join rate | At least 95% |
| UNKNOWN regime rate | At most 5%, with every UNKNOWN retained |
| Export validation | PASS |
| Export freshness | FRESH or explicitly frozen at the N100 boundary |
| Latest canonical key | Reported |

### Cumulative N100 Metrics

- Wins and losses
- WR
- PF
- Net PnL
- Median PnL
- Gross winning PnL
- Gross losing PnL
- One-sided binomial p-value against 50% WR
- Calendar weeks and unique active dates
- nc_PF and consecutive observations below 1.0
- Excluding-top-1, top-3, and top-5 PF
- Leave-one-date-out minimum PF
- Bootstrap PF distribution and fifth percentile

### N71-N100 Forward-Block Metrics

- Exactly 30 canonical opportunities
- Wins and losses
- WR
- PF
- Net and median PnL
- Gross winning and losing PnL
- Regime mix
- Date and week distribution
- Excluding-top-1 and top-3 PF
- Maximum single-date share
- Path-quality coverage and direction

## Required Regime Reporting

Report cumulative N100 and N71-N100 separately for:

- COMPRESSION
- TREND_DOWN
- SIDEWAY
- TREND_UP
- UNKNOWN

For every regime report:

- n and share
- wins and losses
- WR
- PF
- net PnL
- median PnL
- active dates

Required interpretation:

- State whether the forward block survives without COMPRESSION.
- State whether TREND_UP remains a drag, improves, or is inconclusive.
- State whether SIDEWAY remains marginal, strengthens, or weakens.
- State whether one regime dominates forward-block gains or losses.
- Do not create or activate a regime filter from N100 reporting alone.

## Required Concentration Reporting

Report:

- Top-1, top-3, and top-5 winners as shares of gross winning PnL.
- PF after removing top-1, top-3, and top-5 winners.
- Largest winning and losing date.
- Leave-one-date-out PF minimum and maximum.
- Maximum share of forward-block observations from one date and one week.
- Forward-block PF after removing its top winner and top three winners.

Concentration requirements:

| Check | Success threshold | Caution threshold | Failure threshold |
|---|---:|---:|---:|
| Cumulative ex-top-5 PF | >=1.0 | Not applicable | <1.0 |
| Forward ex-top-3 PF | >1.0 | 0.90-1.0 | <0.90 |
| Maximum single-date share | <35% | 35-50% | >50% |
| Leave-one-date-out minimum PF | >1.0 | 0.90-1.0 | <0.90 |

The existing formal concentration kill criterion remains:

```text
ex-top-5 PF < 1.0 at n=100
```

If it triggers, the candidate cannot receive a success verdict even when other
metrics pass.

## Required Path-Quality Reporting

Path-quality evidence is supporting evidence, not a substitute for outcome
truth.

Report:

- Path-truth match count and rate for cumulative N100.
- Path-truth match count and rate for N71-N100.
- MFE median and distribution.
- MAE median and distribution.
- Clean-path rate.
- Percentage reaching positive unrealized PnL.
- Winner and loser MFE/MAE separately.
- Missing-path reasons.
- Whether path evidence confirms, weakens, contradicts, or cannot evaluate the
  outcome interpretation.

Path-quality classifications:

| Classification | Rule |
|---|---|
| CONFIRMS | Direction remains positive and no material contradiction appears |
| MIXED | Coverage is adequate but path evidence is internally mixed |
| INSUFFICIENT | Coverage is too low or systematically missing |
| CONTRADICTS | Path evidence materially conflicts with the claimed outcome edge |

Path evidence classified `CONTRADICTS` prevents a success verdict. Path evidence
classified `INSUFFICIENT` produces a mixed verdict unless every required success
gate passes and the governor explicitly records the limitation.

## Scenario 1: Success

Assign `SUCCESS` only when all conditions pass simultaneously:

| Gate | Required result |
|---|---|
| Data validity | Valid and exactly reproducible N100 |
| Cumulative WR | >52% |
| Cumulative PF | >1.5 |
| Cumulative p-value | <0.05 |
| Cumulative median PnL | >0 |
| Calendar breadth | At least 3 ISO weeks and 7 active dates |
| Forward-block WR | >=50% |
| Forward-block PF | >=1.3 |
| Forward-block net PnL | >0 |
| Cumulative ex-top-5 PF | >1.0 |
| Leave-one-date-out minimum PF | >1.0 |
| Formal kill criteria | None triggered |
| Path quality | CONFIRMS, or explicitly limited without contradiction |

Success interpretation:

```text
The ETH YES FC OS signal candidate passed its predefined N100 research
verification gates, including a positive N71-N100 forward block.
```

Success governor verdict:

```text
VERIFIED_RESEARCH_CANDIDATE
```

This verdict remains research-only and does not authorize runtime use.

## Scenario 2: Mixed

Assign `MIXED` when data is valid and no failure condition triggers, but at
least one success gate is not met.

Mixed examples:

- Cumulative WR and PF pass, but p-value remains >=0.05.
- Cumulative metrics pass, but forward-block WR is 45-50% or PF is 1.0-1.3.
- Forward block is positive but concentrated in one regime, date, or winner.
- Forward ex-top-3 PF or leave-one-date-out minimum PF is 0.90-1.0.
- Path evidence is mixed or insufficient.
- Regime joins are valid but a key regime has too little forward-block n for a
  durable conclusion.

Mixed governor verdict:

```text
VERIFICATION_IN_PROGRESS
```

The candidate remains documented and may continue accumulating evidence. It is
not promoted, failed, or converted into runtime policy.

## Scenario 3: Failure

Assign `FAILURE` when valid data triggers any predefined failure condition:

| Failure condition | Threshold |
|---|---|
| Cumulative WR | <50% |
| Cumulative PF | <1.3 |
| Forward-block WR | <45% |
| Forward-block PF | <1.0 |
| Forward-block net PnL | <=0 with PF <1.0 |
| nc_PF warning | Below 1.0 for more than 10 consecutive observations |
| Concentration collapse | Cumulative ex-top-5 PF <1.0 at n=100 |
| Severe concentration | More than 50% of evidence from one date |
| Path-quality contradiction | Materially contradicts the outcome interpretation |
| Existing kill criterion | Any formal kill criterion triggers |

Failure governor verdict:

```text
FAILED_CANDIDATE_REVIEW_REQUIRED
```

Failure does not authorize strategy removal or runtime changes. Any status
change to `FAILED_CANDIDATE` requires explicit governor review after the N100
report.

## Scenario 4: Invalid Data

Assign `INVALID_DATA` and stop performance interpretation if any condition is
true:

- Canonical n cannot be reproduced exactly.
- Duplicate-policy ambiguity changes n.
- Any included opportunity lacks outcome truth.
- The N71-N100 boundary cannot be reproduced.
- Export validation fails.
- Required source files are missing or corrupt.
- Regime join rate is below 95% without an approved explanation.
- UNKNOWN regime rate exceeds 5% and affects required regime conclusions.
- Source timestamps show an unfrozen or inconsistent evidence window.
- The cell definition or thresholds changed after N70.

Invalid-data governor verdict:

```text
N100_REVIEW_BLOCKED_INVALID_DATA
```

No success, mixed, or failure conclusion may be issued until the data contract
is restored and the same frozen rules are rerun.

## Scenario Precedence

Use this precedence when multiple conditions appear:

```text
INVALID_DATA > FAILURE > MIXED > SUCCESS
```

A stronger positive metric cannot override a higher-precedence adverse state.

## Allowed Conclusions

At N100, the governor may conclude only:

1. The predefined research candidate passed, partially passed, failed, or could
   not be evaluated under this frozen architecture.
2. The N71-N100 forward block confirmed, weakened, contradicted, or was
   insufficient to evaluate the historical selected slice.
3. The edge is concentrated or distributed across documented regimes, dates,
   and trades.
4. Path evidence confirms, weakens, contradicts, or cannot evaluate outcome
   truth.
5. The candidate should be labeled `VERIFIED_RESEARCH_CANDIDATE`, remain
   `VERIFICATION_IN_PROGRESS`, or enter `FAILED_CANDIDATE_REVIEW_REQUIRED`.

## Forbidden Conclusions

N100 must not be used to claim:

- Live-trading readiness.
- Executable profitability.
- Guaranteed profitability or future returns.
- Causal proof that a regime creates the edge.
- Approval to add or remove runtime filters.
- Approval to exclude TREND_UP, SIDEWAY, or any other regime.
- Approval to change strategy, risk, sizing, stop loss, or execution.
- Approval to activate live trading.
- Approval to reinterpret the cell definition after seeing results.
- Approval to change N100 thresholds after seeing results.
- Approval to promote a sub-slice discovered only during the N100 review.
- Approval to treat dust-sized paper PnL as executable PnL.

Any new sub-slice discovered at N100 starts as a separate retrospective
hypothesis with its own future validation block.

## Required N100 Output

The N100 governor packet must contain:

1. Canonical count and duplicate reconciliation.
2. Exact N71-N100 opportunity keys.
3. Cumulative N100 metric table.
4. N71-N100 forward-block metric table.
5. Cumulative and forward regime tables.
6. Concentration and outlier-dependency tables.
7. Path-quality report.
8. Promotion and kill-criteria table.
9. Data-validity checklist.
10. Exactly one scenario and one governor verdict.

## Frozen Governor Decision

The N100 interpretation architecture is frozen before N71-N100 results are
reviewed.

No result may bypass data validity. No cumulative result may conceal forward
block weakness. No research verdict authorizes runtime, strategy, risk,
execution, configuration, or live-trading changes.
