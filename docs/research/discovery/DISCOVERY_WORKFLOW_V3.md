# Discovery Workflow V3

Status: FROZEN DISCOVERY GOVERNANCE

Scope: offline and paper research only

Authority: none over runtime, strategy, thresholds, risk, sizing, or execution

## Purpose

Discovery Workflow V3 defines the required order of evidence before a candidate
may be treated as a research signal. It separates signal discovery from
execution outcomes and prevents candidate definitions from changing to preserve
an attractive result.

## Replay First

Every candidate begins with an offline, reproducible population definition.
Before outcome interpretation:

1. Identify the source datasets and their coverage.
2. Freeze the generated-candidate population and decision-bearing unit.
3. Reproduce joins, duplicate handling, and exclusions.
4. Report unresolved, missing, and non-replayable rows.
5. Run the required null suite.

Runtime activation is outside discovery scope.

## Signal Before Execution

A candidate must demonstrate signal value before execution outcomes are treated
as evidence of edge.

Required sequence:

1. Test terminal predictive skill against market consensus.
2. Test executable short-horizon markout.
3. Test selection against appropriate nulls.
4. Only then study sizing, exits, slippage, or execution policy.

Positive historical PnL cannot substitute for signal evidence.

## Candidate Lifecycle

| State | Meaning |
|---|---|
| PROPOSED | Definition exists but evidence contract is not frozen |
| QUEUED | Definition and required datasets are identified |
| AUDITING | Replayable signal and null tests are running |
| OBSERVED | Descriptive evidence exists; no verification claim |
| VERIFICATION_IN_PROGRESS | Pre-registered forward evidence is accumulating |
| VERIFIED | Required signal, null, stationarity, and execution evidence passed |
| PARKED | Evidence does not support continuation, or validity is compromised |
| FAILED_CANDIDATE | Predefined failure evidence is satisfied |
| RETIRED | Candidate is no longer relevant or testable |

State changes require a written evidence record. A state label never authorizes
runtime behavior.

## Candidate Kill Rules

A candidate must be parked or failed when any predefined condition applies:

- Signal tests show no predictive or executable information value.
- Required nulls explain the observed result.
- Replay coverage is insufficient for the claimed conclusion.
- Admission, labeling, or data-generation rules become non-stationary.
- The candidate depends on post-hoc filtering or changing definitions.
- Evidence cannot be independently reproduced.

Kill rules preserve research capacity. They do not remove runtime safeguards or
authorize strategy edits.

## Stationarity Tripwire

Every forward-validation candidate must track whether its admission and
measurement process remains comparable with the process that produced the
reference sample.

The tripwire must report:

- generated-to-approved rate through time;
- risk-mode and balance-state composition;
- filter and rejection-reason composition;
- source-data and join-contract changes;
- candidate-definition or label changes.

When material non-stationarity is detected, confirmatory interpretation stops.
Existing evidence may remain usable only as a non-stationary diagnostic.

## Balance-Decouple Rule

Signal discovery must be evaluated on generated candidates before bankroll,
balance state, sizing, risk mode, or admission gates select the population.

Balance-conditioned results must be labeled as admission-policy evidence, not
candidate-signal evidence. A balance-state-dependent gate cannot validate the
underlying signal.

## Decision-Bearing Unit Rule

The decision-bearing unit must be frozen before analysis.

Default hierarchy:

1. market and epoch;
2. candidate definition and side;
3. first eligible generated-candidate observation;
4. explicitly documented later observations only when the hypothesis requires
   them.

Repeated polls, decisions, executions, and runtime restarts must not be treated
as independent opportunities. Raw row count and effective market/epoch sample
size must both be reported.

## Candidate Fingerprint Contract

Every candidate specification must be frozen before audit and carry one
immutable fingerprint record.

Mandatory schema:

```yaml
candidate_name:
edge_class: A-G
hypothesis:
asset:
side:
lifecycle:
horizon:
decision_bearing_unit:
data_boundary:
duplicate_policy:
null_suite_mapping:
replay_oos_boundary:
version:
frozen_at:
fingerprint_hash: PENDING_FREEZE_HASH
```

The fingerprint hash is computed only when the specification is frozen. Any
change to a fingerprint field creates a new candidate version and a new
out-of-sample boundary. Prior evidence does not transfer automatically.

## Multiple-Testing And FDR Governance

Discovery governance must track:

- number of tested candidate families;
- number of tested candidate variants;
- family-wise false-discovery exposure;
- portfolio-level false-discovery exposure;
- every replay result used to create or refine a later candidate.

Rules:

- All candidate specifications and fingerprints must be frozen before audit.
- No candidate moves from replay discovery to forward validation without
  out-of-sample replay confirmation under its frozen specification.
- No post-hoc slicing is permitted after a replay result is observed.
- A derived slice is counted as a new tested variant and receives a new
  fingerprint and out-of-sample boundary.
- Family and portfolio interpretation must acknowledge accumulated
  multiple-testing exposure.
- No attractive isolated result overrides required nulls, stationarity, or
  portfolio stopping governance.

This section creates research-accounting requirements only. It does not define
statistical promotion thresholds or authorize implementation.

## Candidate Graveyard Requirement

Every parked, failed, or retired candidate requires a graveyard record containing:

- frozen candidate definition;
- research timeline;
- signal and null findings;
- stationarity and data-quality findings;
- final verdict;
- explicit reopen criteria;
- lessons that should constrain future discovery.

The graveyard prevents repeated rediscovery of rejected hypotheses.

## Anti-Metastasis Clause

A failed or parked candidate must not silently split into narrower sessions,
regimes, price buckets, sides, or lifecycle slices after results are known.

Any derived sub-slice is a new candidate. It requires:

- a new definition;
- a new discovery-board entry;
- fresh null tests;
- separate pre-registration;
- evidence collected after the new definition is frozen.

No derived candidate inherits the parent candidate's sample size, verification
status, or governance standing.

## Frozen Workflow Order

```text
definition
-> data and replay coverage
-> harness validation
-> generated-population signal tests
-> null suite
-> stationarity assessment
-> executable-reality assessment
-> pre-registered forward validation
-> governance verdict
```
