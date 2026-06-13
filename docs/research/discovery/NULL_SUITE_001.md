# Null Suite 001

Status: FROZEN REFERENCE

Scope: discovery research only

## Purpose

No single null can distinguish signal, selection, timing, market structure, and
data artifacts. Null Suite 001 defines the minimum set of counterfactuals used
to decide whether a candidate contains information beyond its environment.

## Required Nulls

### Random Entry Null

Purpose:

Compare the observed candidate or admitted population with random eligible
generated candidates while preserving the relevant sample count and clustering.

Failure mode prevented:

Mistaking ordinary market outcomes, admission frequency, or exit behavior for
candidate-specific edge.

Required when:

- evaluating candidate PnL or executable markout;
- evaluating admission-policy selection;
- comparing a selected population with the generated population.

### Shuffled Signal Null

Purpose:

Shuffle signal values or labels within valid grouping boundaries while
preserving outcomes, market structure, and sample composition.

Failure mode prevented:

Mistaking correlation created by class imbalance, repeated markets, or
calibration structure for genuine signal ordering.

Required when:

- testing prediction, ranking, calibration, or discrimination;
- a candidate uses a model score, probability, confidence, or EV field.

## Conditional Nulls

### Time Shift Null

Purpose:

Shift signal timestamps relative to market outcomes while retaining the same
market series and observation density.

Failure mode prevented:

Mistaking persistent market direction, clock effects, or stale information for
time-local predictive skill.

Required when:

- the hypothesis is lead-lag, momentum, timing, or decay based;
- signal timestamps and outcome timestamps are sufficiently complete.

### Market Conditioned Null

Purpose:

Randomize or resample only within comparable market, epoch, regime, price,
spread, liquidity, or lifecycle conditions.

Failure mode prevented:

Mistaking environment selection for candidate signal.

Required when:

- candidate frequency or outcomes vary materially by market condition;
- a result may be dominated by one regime, price range, or lifecycle state.

### Oracle Conditioned Null

Purpose:

Compare observations within equivalent oracle distance, direction, freshness,
and timing conditions.

Failure mode prevented:

Mistaking direct oracle-state exposure for an independent candidate signal.

Required when:

- the hypothesis uses spot, oracle, price-to-beat, distance, or settlement
  context;
- oracle fields have adequate coverage and reproducible timestamps.

## Null Selection Rules

- Random Entry Null and Shuffled Signal Null are required for every discovery
  candidate.
- Conditional nulls are required whenever their conditioning variable is part
  of the hypothesis or materially imbalanced in the evidence.
- Null construction must preserve market/epoch clustering.
- Null results must report effective sample size and replay coverage.
- Failure against a required null prevents a signal-present conclusion.
- A null suite is evidence only and has no runtime authority.

## Multiple-Testing Context

Every null-suite result must identify:

- candidate family;
- candidate version and fingerprint;
- number of tested variants in that family;
- number of tested families in the discovery portfolio;
- whether the candidate definition was informed by earlier replay results.

Null results must not be interpreted in isolation from family-wise and
portfolio-level false-discovery exposure. No post-hoc slice may reuse the
parent candidate's null result.
