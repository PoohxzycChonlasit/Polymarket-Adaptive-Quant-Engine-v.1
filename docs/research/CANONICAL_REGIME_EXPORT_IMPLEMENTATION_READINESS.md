# Canonical Regime Export Implementation Readiness

Date: 2026-06-07

Mode: READ ONLY / governance readiness review

Spec reviewed:

- `docs/research/CANONICAL_REGIME_EXPORT_SPEC.md`

Related evidence:

- `docs/research/REGIME_ENRICHMENT_SOURCE_AUDIT.md`
- `docs/research/COMMAND_CENTER_OPERATIONAL_READINESS.md`
- `docs/research/N70_EXECUTION_PACKAGE.md`

Verdict: `BUILD_NOW_AS_OFFLINE_EXPORT`

## Executive Summary

The canonical regime export should be implemented now, not deferred until N70.

Reason: the command center is already operational for canonical n, WR, PF, and velocity, but its regime and nc_PF panels are degraded today because raw trade-journal mode produces `UNKNOWN` regimes. N70 explicitly requires regime composition and nc_PF review. Waiting until N70 would make the milestone review depend on a new export implementation at the same time as the governance snapshot, increasing operational risk.

The implementation should remain offline/report-only and should not touch runtime, strategy, risk, execution, live mode, or source JSONL evidence.

## Current State

| Area | Current status |
|---|---|
| Canonical n | Reproducible from raw trade_journal |
| WR/PF | Correct from raw trade_journal |
| Velocity | Correct from raw trade_journal |
| Regime sequence | Degraded in raw trade-journal mode |
| nc_PF | Degraded in raw trade-journal mode |
| Authoritative regime source | `decision_log.payload.market_regime` |
| Existing CSV | Has regime labels but stale/identity-limited |
| N70 requirement | Regime composition and nc_PF are mandatory |

## Implementation Complexity Estimate

Classification: `MEDIUM`

Required work:

| Component | Complexity | Notes |
|---|---|---|
| Trade-journal completed-trade builder | Low/Medium | Existing command-center logic already reconstructs paired rows |
| Canonical opportunity key and duplicate retention | Low | Contract already proven in N61 audit |
| Decision-log targeted scan | Medium | Must avoid multi-GB full scan; scan by trade dates/keys |
| Deterministic regime tie-breaker | Medium | Must handle repeated decision rows per candidate |
| Export schema writer | Low | CSV + metadata JSON |
| Validation summary | Medium | Needs canonical n, duplicate count, join confidence, UNKNOWN rate |
| Command-center integration | Low/Medium | Prefer new export when valid, fallback to raw trade journal |
| Tests | Medium | Need unit tests for join confidence, tie-breaks, unknown handling, stale export rejection |

Estimated implementation size:

```text
1 new offline tool
1-2 small command-center integration changes
1 targeted test file or extension
1 generated export + summary
```

No runtime imports are required.

## Runtime Cost Estimate

Classification: `OFFLINE_MEDIUM_COST`

This export is not runtime cost. It is an offline reporting cost.

Expected cost drivers:

| Source | Cost | Notes |
|---|---|---|
| trade_journal | Low | Files are small enough for full scan |
| decision_log | Medium/High if full scan | Multi-GB directory; must target only needed date files |
| execution_log | Low optional | Small files, but not needed for regime |
| CSV write | Low | Hundreds to low-thousands of rows |

Recommended cost boundary:

```text
Scan only decision_log files for dates present in completed trade rows.
Do not scan all decision logs by default.
```

Expected daily runtime if date-targeted:

| Scenario | Estimate |
|---|---|
| Current n-scale, trade dates only | seconds to low tens of seconds |
| Full historical decision-log scan | potentially minutes / interactive timeout risk |
| Future daily append mode | seconds |

## Maintenance Burden Estimate

Classification: `MEDIUM_BUT_CONTAINED`

Maintenance risks:

| Risk | Burden | Mitigation |
|---|---|---|
| decision_log schema drift | Medium | Validate required fields and emit MISSING/UNKNOWN |
| duplicate key contract drift | Low/Medium | Keep N61/N70 reproducibility tests |
| command-center source selection | Low | Clear preference order: valid export -> raw fallback |
| stale export confusion | Medium | Metadata freshness and invalid/expired labels |
| tie-break ambiguity | Medium | Deterministic rule table from spec |
| large log scans | Medium | Date/key-targeted scanning only |

This burden is acceptable because it creates one reusable offline export instead of repeatedly reimplementing joins in every research report.

## Immediate Research Value

Classification: `HIGH`

Immediate benefits:

1. Restores research-grade regime sequence in the command center.
2. Restores research-grade nc_PF.
3. Allows daily monitoring of COMPRESSION absence without stale CSV contamination.
4. Prevents N70 review from mixing fresh canonical n with stale regime labels.
5. Creates a reusable export for N70, N80, N90, and N100 milestones.
6. Makes unknown regime coverage visible instead of silently collapsing to `UNKNOWN:61`.
7. Reduces operator ambiguity around whether the command center is “ready.”

The value is immediate because current command-center regime output is known degraded.

## Option A: Build Export Now

### Benefits

| Benefit | Impact |
|---|---|
| Fixes current command-center regime gap | High |
| Prepares N70 before the milestone arrives | High |
| Makes nc_PF daily-monitorable | High |
| Avoids stale CSV dependency | High |
| Gives validation time before N70 | High |
| Keeps implementation outside milestone pressure | Medium/High |

### Costs

| Cost | Impact |
|---|---|
| Adds new offline tool/artifact | Medium |
| Requires tests and validation | Medium |
| Requires command-center integration | Low/Medium |
| Requires careful decision-log scan bounds | Medium |

### Risk

Primary risk is implementation quality, not trading risk.

Mitigation:

- offline-only tool
- no runtime imports
- targeted tests
- write metadata with validation status
- command center fallback remains available

### Fit

Strong fit. This is a reporting infrastructure issue already blocking full command-center quality.

## Option B: Wait Until N70

### Benefits

| Benefit | Impact |
|---|---|
| Avoids immediate tool work | Low/Medium |
| Keeps current focus on accumulation only | Medium |
| Lets sample grow before adding export layer | Low |

### Costs

| Cost | Impact |
|---|---|
| N70 snapshot will arrive with known regime/nc_PF gap | High |
| Implementation pressure moves into milestone review | High |
| Drift review may depend on stale CSV or degraded raw mode | High |
| Delays validation of join confidence rules | Medium/High |
| Keeps command center partially operational | Medium |

### Risk

Waiting creates research-governance risk:

```text
N70 requires regime composition and nc_PF,
but current command center cannot produce research-grade versions of those fields.
```

This would either force a rushed implementation at N70 or require manual regime analysis at the milestone.

### Fit

Weak fit. Waiting preserves a known data-quality gap in the exact metrics the N70 package marks mandatory.

## Option Comparison

| Dimension | Build now | Wait until N70 |
|---|---|---|
| Implementation complexity | Medium now | Medium later |
| Runtime/trading risk | None | None |
| Offline runtime cost | Medium, manageable | Same cost later |
| Maintenance burden | Medium, starts now | Medium, delayed |
| Immediate research value | High | Low |
| N70 readiness | Strong | Weak |
| Risk of rushed milestone work | Low | High |
| Command-center quality | Improves now | Remains partial |

## Recommended Option

Recommendation: `BUILD_NOW_AS_OFFLINE_EXPORT`

The export should be implemented before N70 because:

1. It directly fixes a known command-center degradation.
2. It supports mandatory N70 metrics.
3. It is offline/report-only and does not affect runtime behavior.
4. It creates time to validate join confidence before governance decisions depend on it.
5. Deferring does not reduce complexity; it only moves the same work into a higher-pressure milestone.

## Recommended Implementation Boundary

If approved later, keep scope limited to:

```text
offline export only
read trade_journal and decision_log
write runtime/research_exports/canonical_regime_enriched_trades_v1.csv
write metadata/summary
update command center to consume valid export
targeted tests only
```

Do not include:

- runtime loop changes
- strategy logic
- risk logic
- execution logic
- live trading
- policy thresholds
- Telegram changes
- replay promotion

## Required Tests If Implemented

Minimum targeted tests:

| Test | Purpose |
|---|---|
| canonical n reproduces N61 | Protect count contract |
| duplicate key removes one known duplicate | Protect logical opportunity semantics |
| direct decision join selects OPENING_SCAN row | Protect regime truth |
| tie-breaker chooses nearest entry decision | Protect deterministic matching |
| missing decision emits UNKNOWN/MISSING | Protect fail-soft behavior |
| stale export metadata labels EXPIRED | Protect command-center freshness |
| command center prefers valid export | Protect integration |
| command center falls back on invalid export | Preserve report availability |

## Governor Verdict

`BUILD_NOW_AS_OFFLINE_EXPORT`

Implementation should happen now if the operator approves an implementation task. It should not wait for N70.

This recommendation is not authorization to implement. It is a readiness verdict only.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No
