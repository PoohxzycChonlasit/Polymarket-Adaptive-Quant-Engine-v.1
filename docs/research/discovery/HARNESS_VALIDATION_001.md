# Harness Validation 001

Status: DESIGN ONLY

Implementation: none

## Purpose

The discovery harness can create false confidence even when individual analyses
appear reproducible. Harness validation tests whether population construction,
joins, clustering, nulls, and metrics can correctly detect both signal and
absence of signal.

## Monoculture Risk

A single data path, join contract, metric implementation, or null generator can
repeat the same error across every candidate. Repeated reports from one flawed
harness are not independent confirmation.

Harness validation therefore requires positive, negative, and synthetic
controls before broad candidate discovery.

## Known Signal Test

Purpose:

Run the harness on a relationship whose direction and timing are independently
known from the data contract.

Expected outcome:

- adequate replay and join coverage;
- positive skill detected in the expected direction;
- clustering and null tests preserve the known result;
- no signal appears outside the known boundary.

Failure meaning:

The harness may be unable to detect genuine signal or may be joining the wrong
observations.

## Known Null Test

Purpose:

Run the harness on a population with no decision-bearing relationship.

Expected outcome:

- no material predictive or executable skill;
- observed metrics remain inside the null distribution;
- final classification rejects or marks the candidate insufficient.

Failure meaning:

The harness may manufacture edge through leakage, duplicate weighting,
selection bias, or invalid null construction.

## Synthetic Injected Signal Test

Purpose:

Inject a controlled offline relationship with known strength, timing, and
coverage into a copy of the analytical input.

Expected outcome:

- the harness detects the injected direction;
- reported effect changes with injected strength;
- the signal disappears when shuffled or time-shifted;
- coverage loss and clustering affect uncertainty as expected.

Failure meaning:

The harness may have incorrect metrics, poor sensitivity, leakage, or invalid
uncertainty estimates.

## Validation Record

Each harness validation must document:

- frozen input and expected result;
- candidate or control fingerprint where applicable;
- join and replay coverage;
- raw and effective sample size;
- required null outcomes;
- detected direction and uncertainty;
- contradictions;
- final harness status.

Harness validation does not authorize strategy, runtime, risk, or execution
changes.

Harness controls do not count as candidate-family discoveries. Candidate
variants evaluated through the harness remain subject to family-wise and
portfolio-level multiple-testing governance.
