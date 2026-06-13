# Discovery Portfolio Stop Rule 001

Status: FROZEN GOVERNANCE REFERENCE

Scope: research-capacity allocation only

## Purpose

Discovery has a portfolio cost. Repeated testing of candidates, families, or a
venue after their evidence becomes consistently uninformative creates false
discovery risk and consumes evidence capacity. These rules define escalation
states without inventing implementation thresholds.

## Candidate Stop

A candidate stops when its frozen hypothesis is not supported, cannot be
reproduced, fails required nulls, or becomes non-stationary.

Required action:

- classify as PARKED, FAILED_CANDIDATE, or RETIRED;
- create a candidate graveyard record;
- prohibit post-hoc sub-slice promotion;
- preserve explicit reopen criteria.

Candidate stop does not imply family or venue failure.

## Family Stop

A family stop is considered when multiple independently defined candidates
within the same edge class repeatedly fail for the same structural reason.

Evidence considered:

- repeated absence of signal before execution;
- repeated failure against required nulls;
- repeated non-replayability or missing essential feeds;
- shared structural false positives;
- absence of independent successful controls.

Required action:

- pause new candidates in the family;
- preserve completed evidence;
- require a materially different hypothesis or data source before reopening.

Family stop does not imply venue failure.

## Venue Stop

Venue-level states summarize whether continued broad discovery remains
informative.

| State | Meaning |
|---|---|
| VENUE_EDGE_DOUBTFUL | Evidence is mixed or dominated by unresolved data and null limitations |
| VENUE_EDGE_UNLIKELY | Multiple independent families fail signal and null tests despite adequate data |
| VENUE_EDGE_REJECTED | Broad, reproducible evidence shows no usable edge under the frozen research scope |

Venue-stop rationale must distinguish:

- absence of edge;
- absence of executable edge;
- insufficient data;
- invalid harness;
- missing feeds;
- non-stationary research conditions.

## Governance Constraints

- No numerical stop threshold in this document authorizes implementation.
- Stop states require written evidence and independent review.
- A strong result in one candidate cannot erase repeated failures elsewhere.
- The portfolio record must track the number of tested families and tested
  variants.
- Family-wise and portfolio-level false-discovery exposure must be considered
  before any research promotion.
- Candidate specifications must be frozen before audit, and no post-hoc slice
  may be promoted from the result it was derived from.
- Replay discovery cannot enter forward validation without out-of-sample replay
  confirmation under the frozen candidate fingerprint.
- A venue stop does not authorize runtime, strategy, risk, or execution changes.
- Reopening requires new evidence or a materially new research contract.
