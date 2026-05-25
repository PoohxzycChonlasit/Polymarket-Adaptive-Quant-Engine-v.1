# Path Truth Gate Revision

Date: 2026-05-25

Scope: design/spec only. No code changes. No runtime changes. No field wiring.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Purpose

Revise the single 7 completed-date path truth gate into two staged gates:

1. Stage A: 3 completed dates = `EARLY_RESEARCH_GATE`
2. Stage B: 7 completed dates = `IMPLEMENTATION_GATE`

This separates research interpretation from implementation permission. The 3-date gate can support early evidence analysis, but it does not authorize field wiring, strategy changes, risk changes, execution changes, or live behavior.

## Current Status

Current monitor state:

```text
INSUFFICIENT_DATES
```

Completed dates with path truth data:

```text
1 / 7
```

Current known field gaps:

- `quote_age_ms`
- `candidate_id`
- `decision_id`

These remain blocked for wiring until Stage B.

## Stage A - EARLY_RESEARCH_GATE

Minimum dates:

```text
3 completed dates
```

Purpose:

Allow early research synthesis on path truth behavior once there is enough date diversity to reduce single-session bias.

### Coverage Requirements

Stage A opens only when all conditions are met:

| Requirement | Threshold |
|---|---|
| completed dates with path truth data | >= 3 |
| JSONL parse errors | 0 on all included dates |
| duplicate checkpoint keys | 0 on all included dates |
| path truth write errors | 0 on all included dates |
| eligible full coverage | >= 80% on at least 2 of 3 dates |
| severe regression | none across the last 2 completed dates |

Eligible full coverage means:

```text
full coverage trades / trades with a 60s checkpoint
```

Fast closes before scheduled checkpoint eligibility do not count as coverage failures.

### Allowed Actions

Stage A allows:

- early research summaries
- coverage trend analysis
- field-gap persistence tracking
- path lifecycle hypothesis generation
- identifying whether fast-close partial coverage remains expected
- drafting implementation candidates without editing runtime code
- recommending whether to keep collecting evidence or prepare a scoped implementation plan

### Blocked Actions

Stage A still blocks:

- field wiring for `quote_age_ms`
- field wiring for `candidate_id`
- field wiring for `decision_id`
- path truth producer code changes
- replay behavior changes
- strategy changes
- risk changes
- stop-loss or take-profit changes
- execution/order placement changes
- live enablement or live-readiness claims
- S3 or phase promotion based on path truth alone

### Risk Rationale

Three completed dates are enough to reduce the risk that the first path truth result was a one-off artifact, but not enough to prove producer stability across market regimes, runtime restarts, long sessions, and varying trade durations.

Stage A is therefore useful for research direction only. It should not be used to alter runtime behavior because:

- field gaps are already known and may hide downstream identity issues
- fast-close concentration can distort coverage interpretation
- date diversity remains thin
- a single clean cluster can mask later writer or lifecycle regressions
- path truth is observability evidence, not a trading approval system

## Stage B - IMPLEMENTATION_GATE

Minimum dates:

```text
7 completed dates
```

Purpose:

Authorize a separately scoped observability-only implementation task for known path truth field gaps, if coverage remains stable.

### Coverage Requirements

Stage B opens only when all conditions are met:

| Requirement | Threshold |
|---|---|
| completed dates with path truth data | >= 7 |
| JSONL parse errors | 0 on all included dates |
| duplicate checkpoint keys | 0 on all included dates |
| path truth write errors | 0 on all included dates |
| eligible full coverage | >= 80% on at least 6 of 7 dates |
| severe regression | none across any 2 consecutive completed dates |
| event_end rows | present and parseable on all included dates |
| scheduled checkpoint rows | present on dates with eligible trades |

### Allowed Actions

Stage B allows, in a separately scoped task:

- observability-only field wiring for `quote_age_ms`
- observability-only field wiring for `candidate_id`
- observability-only field wiring for `decision_id`
- focused regression tests for path truth payload shape and fail-soft behavior
- post-wiring paper validation of field population
- updating research docs and monitors with post-wiring field coverage

Stage B does not automatically implement anything. It only permits proposing or executing a narrowly scoped implementation task.

### Blocked Actions

Stage B still blocks:

- strategy changes
- risk sizing changes
- stop-loss or take-profit changes
- order placement or fill behavior changes
- replay behavior changes unless separately scoped
- live mode enablement
- live-readiness claims
- S3 promotion from path truth alone

### Risk Rationale

Seven completed dates provide enough date diversity to test writer stability, eligible checkpoint coverage, fast-close classification, duplicate protection, and JSONL parse health under multiple sessions. This reduces the chance that field wiring is being added on top of an unstable producer.

Even at Stage B, the allowed implementation is observability-only because path truth fields are diagnostic. They must not feed runtime strategy, risk, or execution decisions without a later scoped phase and separate validation.

## Verdict Labels

Use these labels in future path truth monitors:

| Label | Meaning |
|---|---|
| `INSUFFICIENT_DATES` | Fewer than 3 completed dates. No research gate and no implementation gate. |
| `EARLY_RESEARCH_GATE` | At least 3 completed dates and Stage A coverage requirements met. Research synthesis allowed; implementation blocked. |
| `COVERAGE_REGRESSED` | Parse errors, duplicate keys, write errors, or consecutive coverage deterioration detected. Both gates closed until resolved. |
| `IMPLEMENTATION_GATE` | At least 7 completed dates and Stage B coverage requirements met. Observability-only field wiring may be scoped. |

## Current Application

Current status remains:

```text
INSUFFICIENT_DATES
```

Reason:

- only 1 completed date currently exists
- Stage A requires 3 completed dates
- Stage B requires 7 completed dates
- field gaps remain known but intentionally unwired

## Field Wiring Policy

No field wiring until:

```text
IMPLEMENTATION_GATE
```

The first eligible field wiring candidates remain:

1. `quote_age_ms`
2. `candidate_id`
3. `decision_id`

Implementation must be observability-only, additive, backward compatible, fail-soft, and covered by focused tests.

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; docs-only gate revision.
