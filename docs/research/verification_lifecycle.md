# Verification Lifecycle

type: governance roadmap
created: 2026-06-06
version: 1.0
code_changed: No
strategy_changed: No
runtime_changed: No

---

## Purpose

This document defines the next research governance lifecycle for watchlists,
verification trackers, promotion criteria, and kill criteria.

All states are evidence labels only. No state in this lifecycle authorizes a
runtime change, strategy change, risk change, execution change, config change,
Telegram change, live-mode change, or position-sizing change.

The lifecycle replaces mixed legacy labels such as `WEAK_SIGNAL`,
`NOT_SUPPORTED`, and `DORMANT` with five canonical states:

1. `OBSERVED`
2. `VERIFICATION_IN_PROGRESS`
3. `VERIFIED`
4. `RETIRED`
5. `FAILED_CANDIDATE`

---

## State Definitions

| State | Meaning | Runtime Authority |
|---|---|---|
| `OBSERVED` | A directional pattern exists, but the sample is too small or incomplete for active verification. | None |
| `VERIFICATION_IN_PROGRESS` | The candidate has enough structure, evidence quality, and initial robustness to track against explicit promotion and kill criteria. | None |
| `VERIFIED` | The candidate met all predefined statistical, robustness, replication, and governance gates. | None |
| `RETIRED` | The candidate is no longer actively tracked because it is obsolete, superseded, structurally resolved, or no longer accumulates evidence. | None |
| `FAILED_CANDIDATE` | The candidate failed explicit kill criteria or contradicted its hypothesis on sufficient new evidence. | None |

---

## Lifecycle Flow

```text
OBSERVED
  -> VERIFICATION_IN_PROGRESS
  -> VERIFIED

OBSERVED
  -> FAILED_CANDIDATE

VERIFICATION_IN_PROGRESS
  -> FAILED_CANDIDATE

OBSERVED
  -> RETIRED

VERIFICATION_IN_PROGRESS
  -> RETIRED

VERIFIED
  -> RETIRED
```

`VERIFIED` findings should not be demoted casually. If new evidence contradicts
a verified finding, open a new review snapshot with `VERIFIED_REVIEW_REQUIRED`.
Only after a dedicated governor review may it move to `RETIRED` or
`FAILED_CANDIDATE`.

---

## State Entry Requirements

### OBSERVED

Use `OBSERVED` when a pattern is real enough to track but not mature enough for
formal verification.

Minimum evidence:

| Requirement | Minimum |
|---|---|
| Trade count | n >= 20, or n >= 10 with a documented structural mechanism |
| Direction | Pattern direction visible in the tracked cell |
| Source | Paper trade journal, decision log, execution log, path truth, or documented code trace |
| Scope | Exact cell definition exists |
| Safety label | `code_changed: No`, `strategy_changed: No`, `runtime_changed: No` |

OBSERVED candidates must include:

- hypothesis
- exact filter definition
- current n
- latest win rate or relevant metric
- known limitations
- next evidence threshold

### VERIFICATION_IN_PROGRESS

Use `VERIFICATION_IN_PROGRESS` when an OBSERVED candidate has enough quality to
track with formal promotion and kill gates.

Minimum evidence:

| Requirement | Minimum |
|---|---|
| Trade count | n >= 50, unless mechanism-only candidate has deterministic proof |
| Cell definition | Exact and reproducible |
| Outcome truth | `trade_result` and `pnl_usdc` available for outcome candidates |
| Replication | At least 3 independent sessions or 7 calendar dates |
| Initial robustness | At least one robustness check passed |
| Tracker | Dedicated tracker or watchlist section with promotion and kill criteria |

Recommended robustness checks:

- leave-one-date-out or leave-one-session-out
- top winner removal
- top 5 winner removal for n >= 50
- first-half vs second-half split
- bootstrap if n >= 50
- session concentration check
- path truth check if path behavior is part of the claim

### VERIFIED

Use `VERIFIED` only when all predefined gates pass on the same evidence snapshot.

Universal minimum requirements:

| Requirement | Threshold |
|---|---|
| Minimum total n | n >= 100 preferred, n >= 50 absolute minimum for very large effects |
| Statistical significance | p < 0.05 in the correct tail, or documented deterministic proof for mechanism-only claims |
| Session diversity | At least 3 independent sessions |
| Calendar breadth | At least 7 unique calendar dates |
| Direction consistency | At least 70% of contributing sessions support the direction |
| Concentration control | No single session contributes more than 50% of supporting evidence |
| Governance review | Explicit governor sign-off before status update |

Additional requirements for positive-edge candidates:

- profit factor > 1.5 at n >= 100, unless a stricter per-watchlist rule exists
- median PnL > 0
- net PnL > 0
- top-5-winner removal keeps profit factor > 1.0
- no unresolved join-key or truth-field issue that materially changes the result

Additional requirements for negative-edge or failure candidates:

- win rate below baseline by the predefined effect threshold
- calibration gap remains material if the claim is model overconfidence
- new evidence block does not reverse the effect
- source logs confirm the cell is not an artifact of test data or replay leakage

### RETIRED

Use `RETIRED` when a candidate should remain documented but no longer needs
active accumulation.

Valid retirement reasons:

- superseded by a better-defined watchlist
- merged into a parent watchlist
- structurally resolved by a later audit
- no longer accumulates because the runtime regime changed
- obsolete because field definitions changed
- verified finding has been archived into phase-design evidence
- candidate is no longer decision-relevant to the current research frontier

Retirement is not failure. A retired candidate may have been true, useful, or
verified. It is simply no longer active.

Retirement requirements:

- final snapshot or final note
- retirement reason
- successor watchlist if applicable
- impact statement
- confirmation that no runtime action is authorized

### FAILED_CANDIDATE

Use `FAILED_CANDIDATE` when sufficient new evidence contradicts the candidate.

Minimum failure evidence:

| Requirement | Threshold |
|---|---|
| New contradicting block | n >= 30 new trades for active candidates |
| Strong contradiction | n >= 50 new trades preferred |
| Statistical failure | p > 0.30 in the claim direction, or per-watchlist kill criteria met |
| Direction reversal | New block reverses the expected direction by more than 5 percentage points |
| Robustness collapse | Concentration, bootstrap, or session split fails predefined kill gates |

FAILED_CANDIDATE is the replacement for legacy `NOT_SUPPORTED` when a tracked
candidate has actively failed. Use `RETIRED`, not `FAILED_CANDIDATE`, when the
candidate merely stops accumulating evidence.

---

## Promotion Rules

### OBSERVED -> VERIFICATION_IN_PROGRESS

Promote when all are true:

1. Exact cell definition exists.
2. Current evidence reaches n >= 50, or n >= 20 with deterministic mechanism.
3. Metrics are directionally stable across at least 3 sessions or 7 dates.
4. Promotion and kill criteria are written before further tracking.
5. Evidence fields are sufficient for the claim.
6. The watchlist index is updated with current n, required n, and last snapshot.

### VERIFICATION_IN_PROGRESS -> VERIFIED

Promote when all are true:

1. Required n threshold is met.
2. Statistical threshold is met in the correct tail.
3. Replication requirements are met.
4. Robustness checks pass.
5. No material truth-field gap remains.
6. No single session or date dominates the result.
7. A dedicated governor review approves the status change.

### OBSERVED -> VERIFIED

Direct promotion is allowed only for mechanism-only claims with deterministic
code or math proof. Outcome claims should pass through
`VERIFICATION_IN_PROGRESS`.

---

## Demotion Rules

### VERIFICATION_IN_PROGRESS -> OBSERVED

Use this demotion when evidence weakens but does not fail.

Triggers:

- n is later found to include ineligible rows
- join-key quality reduces confidence below verification standard
- required field coverage drops below acceptable level
- replication is narrower than originally believed
- robustness checks become inconclusive but not negative

### OBSERVED or VERIFICATION_IN_PROGRESS -> FAILED_CANDIDATE

Use this demotion when kill criteria are met.

Triggers:

- p > 0.30 in the claim direction on n >= 50 new evidence
- win rate or profit factor crosses a written kill threshold
- top-winner removal collapses the candidate below threshold
- session split shows the candidate only works in one outlier session
- path truth contradicts the original outcome interpretation
- required exclusion rule is invalidated

### VERIFIED -> Review Required

Do not demote VERIFIED automatically.

If contradictory evidence appears:

1. Append a `VERIFIED_REVIEW_REQUIRED` snapshot.
2. Identify whether the contradiction is market drift, code drift, data quality,
   or original overfit.
3. Run a dedicated governor review.
4. Decide between `RETIRED`, `FAILED_CANDIDATE`, or retaining `VERIFIED`.

---

## Retirement Rules

Retire a candidate when the research system should stop actively collecting it.

Allowed paths:

- `OBSERVED -> RETIRED`
- `VERIFICATION_IN_PROGRESS -> RETIRED`
- `VERIFIED -> RETIRED`

Retirement checklist:

- final status date
- final n
- final metrics
- reason for retirement
- successor or parent watchlist, if any
- statement that no runtime action is authorized
- update `WATCHLIST_INDEX.md`

Retirement reasons should use one of:

- `SUPERSEDED`
- `MERGED`
- `OBSOLETE_FIELD_DEFINITION`
- `NO_LONGER_ACCUMULATING`
- `STRUCTURALLY_RESOLVED`
- `ARCHIVED_TO_PHASE_DESIGN`
- `LOW_RELEVANCE`

---

## Evidence Requirements

### Required Fields by Claim Type

| Claim type | Required evidence |
|---|---|
| Outcome edge | `trade_result`, `pnl_usdc`, asset, side, lifecycle, session/date |
| Model calibration failure | `true_probability` or model probability, market price, outcome, pnl |
| Confidence failure | confidence, outcome, pnl, confidence band, source formula or reason |
| EV inversion | EV at decision, outcome, pnl, lifecycle, asset, side |
| Path behavior | entry price, checkpoint prices, MFE, MAE, hold seconds, exit reason |
| Execution realism | entry price, size, notional, liquidity, min executable assumption, spread |
| Mechanism proof | code reference, formula, deterministic derivation, scope boundary |

### Evidence Quality Labels

| Label | Meaning |
|---|---|
| `DIRECT` | Joined from canonical runtime fields with run/candidate identity |
| `PARTIAL_DIRECT` | Some direct fields exist but path or join coverage is incomplete |
| `PROXY` | Inferred from adjacent fields or older logs |
| `PRE_PATCH` | Evidence predates current instrumentation |
| `MECHANISM_ONLY` | Deterministic code/math proof, no outcome claim |

Promotion to `VERIFIED` should use `DIRECT` or `PARTIAL_DIRECT` evidence.
`PROXY` and `PRE_PATCH` evidence may support `OBSERVED`, but should not be the
sole basis for outcome `VERIFIED`.

---

## Minimum Sample Sizes

### Universal Guidance

| Use case | Minimum n |
|---|---|
| Mention in notes | 10 |
| OBSERVED | 20 |
| VERIFICATION_IN_PROGRESS | 50 |
| VERIFIED, very large effect | 50 |
| VERIFIED, normal outcome edge | 100 |
| VERIFIED, medium effect | 200 to 350 |
| VERIFIED, small effect | 500+ |

### Positive Candidate Minimums

Positive-edge candidates should target:

- n >= 100
- p < 0.05 against the declared baseline
- profit factor > 1.5
- median PnL > 0
- at least 3 calendar weeks when the claim is session/time dependent
- top-5 removal remains profitable

### Negative Candidate Minimums

Failure-mode candidates should target:

- n >= 100 for large effects
- n >= 200 to 350 for medium effects
- correct-tail p < 0.05
- calibration gap or win-rate deficit remains directionally stable
- at least 7 unique dates

### Mechanism-Only Minimums

Mechanism-only claims may be `VERIFIED` without outcome n if:

- source code or formula is read directly
- scope is narrow and deterministic
- the finding makes no outcome or profitability claim
- runtime behavior is not changed by the finding

---

## Governance Workflow

### 1. Create or Update Watchlist

Every active watchlist must include:

- state
- priority
- exact cell definition
- current n
- required n
- evidence source
- promotion criteria
- kill criteria
- latest snapshot date
- limitations
- no-runtime-authority statement

### 2. Maintain Verification Tracker

Every `VERIFICATION_IN_PROGRESS` candidate should have either:

- a dedicated tracker file, or
- a clearly marked tracker section inside its watchlist.

Tracker must show:

- current metrics vs target
- criteria passed/failed
- hard blockers
- ETA to required n
- latest robustness status
- next snapshot trigger

### 3. Snapshot Triggers

Append a snapshot when any trigger occurs:

- at least 10 new qualifying trades for P0
- at least 20 new qualifying trades for P1
- 7 calendar days elapsed
- candidate reaches 80% of required n
- candidate reaches required n
- any kill criterion is triggered
- material data quality issue is discovered

### 4. Governor Review

Governor review is required before:

- `OBSERVED -> VERIFICATION_IN_PROGRESS`
- `VERIFICATION_IN_PROGRESS -> VERIFIED`
- any transition to `FAILED_CANDIDATE`
- any transition from `VERIFIED`
- any retirement of a P0 watchlist

Governor review must answer:

1. Is the evidence clean?
2. Is the cell definition stable?
3. Are there unrelated files or runtime changes mixed in?
4. Are the promotion or kill criteria predeclared?
5. Is the sample large enough for the claim?
6. Are there unresolved join-key or truth-field gaps?
7. Does the status change authorize no runtime action?

### 5. Index Update

After any state change, update `docs/research/watchlists/WATCHLIST_INDEX.md`:

- state
- current n
- required n
- last snapshot
- successor or retirement marker if applicable

### 6. Commit Hygiene

Research governance commits should include only:

- watchlist file
- verification tracker
- watchlist index
- supporting research doc if explicitly part of the review

Do not include:

- runtime logs
- code files
- config files
- strategy files
- risk files
- execution files
- live-mode files

---

## Legacy Status Mapping

| Legacy label | New state |
|---|---|
| `WEAK_SIGNAL` | `OBSERVED` with `low_n` limitation, or no watchlist yet |
| `OBSERVED` | `OBSERVED` |
| `OBSERVED (strong)` | `VERIFICATION_IN_PROGRESS` if criteria are written |
| `NOT_SUPPORTED` | `FAILED_CANDIDATE` |
| `DORMANT` | `RETIRED` with reason `NO_LONGER_ACCUMULATING` |
| `VERIFIED candidate` | `VERIFICATION_IN_PROGRESS` |
| `VERIFIED` | `VERIFIED` |

---

## Recommended File Layout

```text
docs/research/watchlists/
  WATCHLIST_INDEX.md
  WATCHLIST_REVIEW_WORKFLOW.md
  <WATCHLIST_NAME>.md

docs/research/
  verification_tracker.md
  verification_lifecycle.md
```

For multiple active verification candidates, prefer one tracker per candidate:

```text
docs/research/verification/
  ETH_YES_FC_OS.md
  ACTIVE_INVENTORY_EV_INVERSION.md
```

Do not move existing tracker files without a separate docs organization task.

---

## Non-Authorization Clause

This lifecycle is governance documentation only. It does not authorize:

- code changes
- runtime changes
- strategy changes
- risk changes
- execution changes
- stop-loss changes
- sizing changes
- live-mode changes
- replay execution
- S3 promotion

Any implementation or policy change requires a separate task with explicit
scope, tests, and safety review.
