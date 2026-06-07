# N70 Execution Package

Date: 2026-06-07

Cell: ETH YES FIRST_CYCLE OPENING_SCAN hold > 15s

Mode: READ ONLY / docs-only execution design

Runtime authority: None

Verdict: `N70_SNAPSHOT_PACKAGE_READY_TO_EXECUTE_WHEN_CANONICAL_N_REACHES_70`

## Purpose

This package defines the exact governance workflow to execute when the ETH YES FC OS canonical opportunity count reaches `n = 70`.

Current locked state:

| Field | Value |
|---|---:|
| Canonical n | 61 |
| Target n | 100 |
| Next milestone | 70 |
| Trades needed for N70 | 9 |
| Current lifecycle state | VERIFICATION_IN_PROGRESS |
| Runtime authority | None |

N70 is a milestone snapshot, not a promotion event. It exists to detect drift, update the tracker, compare the new block against the n=61 baseline, and decide whether evidence accumulation should continue unchanged.

## Non-Authorization Clause

This document does not authorize:

- strategy changes
- risk changes
- execution changes
- sizing changes
- stop-loss changes
- live trading
- runtime filters
- config changes
- replay promotion
- code implementation

All N70 outputs are research governance evidence only.

## Baseline For Comparison

Use the locked `n = 61` canonical state as the comparison baseline.

Baseline sources:

| Source | Role |
|---|---|
| `docs/research/CANONICAL_N61_REPRODUCIBILITY_AUDIT.md` | Canonical count and key contract |
| `docs/research/campaigns/ETH_YES_FC_OS_CAMPAIGN_DASHBOARD.md` | Current n=61 campaign state |
| `docs/research/watchlists/ETH_YES_FC_OS.md` | Watchlist definition and n=60 robustness baseline |
| `docs/research/verification_tracker.md` | Promotion and kill gate structure |
| `docs/research/frontiers/ETH_YES_FC_OS_COMMAND_CENTER_SPEC.md` | Operational panels and daily monitoring logic |
| `docs/research/frontiers/VERIFICATION_OPERATIONS_FREEZE.md` | Operations backlog and non-authorization boundaries |

Baseline metrics to compare:

| Metric | Baseline handling |
|---|---|
| WR | Compare N70 cumulative WR and n=62-70 block WR against n=61 baseline |
| PF | Compare N70 cumulative PF and n=62-70 block PF against n=61 baseline |
| nc_PF | Compare N70 rolling non-COMPRESSION PF against n=61 command-center baseline |
| Regime composition | Compare N70 cumulative and new-block mix against n=61 regime mix |
| COMPRESSION share | Compare post-collapse share against historical and n=61 state |
| Velocity | Compare 7d, 14d, and since-n61 opportunity rate |
| Kill criteria | Re-evaluate all kill guards, including inactive guards |

## Canonical Input Contract

Primary inputs:

| Input | Required | Purpose |
|---|---|---|
| `runtime/quant_data/trade_journal/*.jsonl` | Yes | Raw trade open/close truth |
| `runtime/quant_data/decision_log/*.jsonl` | Yes | Regime, lifecycle, decision-cycle context |
| `runtime/quant_data/execution_log/*.jsonl` | Yes | Execution linkage and candidate evidence |
| `runtime/quant_data/path_truth/*.jsonl` | Optional but expected | MFE/MAE and path truth coverage |
| Fresh canonical completed-trades export | Yes if available | Compact metric computation |

Canonical filter:

```text
event_type == trade_close
AND outcome truth exists
AND asset == ETH
AND side/outcome == YES
AND trade_open.lifecycle_phase contains OPENING_SCAN
AND hold_seconds > 15
```

Canonical duplicate key:

```text
condition_id | epoch_start_ts | asset | side | candidate_id
```

N70 is reached only when this key count equals `70`.

## Required Outputs At N70

Create or update these research artifacts:

| Output | Required | Purpose |
|---|---|---|
| `docs/research/watchlists/ETH_YES_FC_OS.md` | Mandatory | Append N70 snapshot |
| `docs/research/verification_tracker.md` | Mandatory | Update progress, gates, next trigger |
| `docs/research/campaigns/ETH_YES_FC_OS_CAMPAIGN_DASHBOARD.md` | Mandatory | Update executive campaign view |
| `docs/research/evidence_velocity_dashboard.md` | Mandatory | Update velocity and ETA |
| `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md` | Mandatory | Update drift, nc_PF, regime composition |
| `docs/research/N70_SNAPSHOT_REVIEW.md` | Mandatory | One-shot governor review record |
| `docs/research/CANONICAL_N70_REPRODUCIBILITY_AUDIT.md` | Optional | Exact 70 keys if reconciliation uncertainty appears |

Do not update runtime code, config, strategy, risk, execution, or live settings.

## Analysis Matrix

| Analysis | Class | Required inputs | Expected output | Pass | Caution | Fail |
|---|---|---|---|---|---|---|
| Canonical count reconciliation | Mandatory | trade_journal, execution_log | Proof that n=70 is unique logical opportunities | n=70 exactly, no unexplained duplicates | n=70 with explainable duplicate/removal note | Count cannot be reproduced |
| Filter-chain audit | Mandatory | trade_journal joined to trade_open | Raw count -> canonical count table | All filters deterministic | One field requires documented fallback | Missing core field or ambiguous predicate |
| Cumulative WR/PF snapshot | Mandatory | canonical N70 trade set | WR, PF, W/L, gross win/loss | WR > 52%, PF > 1.5 | WR 50-52% or PF 1.3-1.5 | WR < 50% or PF < 1.3 |
| New-block n=62-70 review | Mandatory | canonical N70 trade set | 9-trade block WR/PF/PnL | Block WR >= 50% and PF >= 1.3 | Block WR 45-50% or PF 1.0-1.3 | Block WR < 45% or PF < 1.0 |
| Regime composition update | Mandatory | decision_log, trade context | COMPRESSION/TREND_DOWN/SIDEWAY/TREND_UP mix | Mix explained, no hostile dominance | TREND_UP or SIDEWAY share materially rises | Below-1.0 regime dominates new block |
| COMPRESSION dependency check | Mandatory | decision_log, campaign dashboard | COMPRESSION share and absence duration | Share recovering or non-COMP PF healthy | COMPRESSION absent but PF buffer intact | COMPRESSION absent and PF buffer collapsing |
| nc_PF rolling review | Mandatory | canonical trade set with regimes | Rolling non-COMP PF, consecutive below-1.0 count | nc_PF >= 1.0 or below count <= 5 | nc_PF < 1.0 for 6-10 new points | nc_PF < 1.0 for >10 new points |
| Kill criteria check | Mandatory | canonical N70 metrics | K1-K4 status table | No criteria triggered; inactive guards documented | Any precursor warning active | Any formal kill criterion triggered |
| Calendar week gate | Mandatory | canonical entry timestamps | ISO week count and W23/W24 contribution | >= 3 weeks retained | 3 weeks but new week has only 1 trade | Week count or timestamp logic ambiguous |
| Evidence velocity update | Mandatory | canonical timestamps | 7d/14d/since-n61 rates and ETA | Rate >= 1/day or ETA stable | Rate 0.5-1/day | Rate < 0.5/day with no recovery |
| Path truth coverage | Mandatory if path files exist | path_truth, trade_journal | Match rate, MFE/MAE summary | Coverage >= 47% and direction stable | Coverage lower but explainable | Coverage regression unexplained |
| MFE/MAE sanity check | Mandatory if path files exist | path_truth matched trades | MFE median, MAE median, clean-path rate | MFE/MAE remains directionally positive | Mixed path evidence | Path evidence contradicts cell |
| Concentration quick check | Mandatory | canonical N70 trade set | Top-1/top-3/top-5 removal PF | Ex-top-5 PF > 1.0 | Ex-top-5 PF 0.9-1.0 | Ex-top-5 PF < 0.9 |
| p-value projection | Mandatory | N70 WR | n required for p<0.05 at current WR | Required n <= 110 | Required n 111-130 | Required n > 130 or worsening fast |
| BTC exclusion monitor | Mandatory | BTC YES FC OS comparison | BTC n, WR, PF | BTC remains weak or insufficient | BTC improving but n<20 | BTC WR > 40% with n>=20 |
| OPENING_SCAN coverage note | Optional | decision_log, coverage docs | Intake bottleneck update | No material deterioration | Coverage bottleneck worsening | Evidence intake invalidated |
| Executability note | Optional | completed trades sizing fields | Signal/executable label | Signal-only label preserved | Mixed sizing interpretation | Executable claims made without proof |
| Telegram/runtime health note | Milestone-only | runtime health docs/log summaries | Health footnote | No incidents affecting evidence | Incident with isolated impact | Incident affects count integrity |

## Mandatory N70 Workflow

1. Freeze the raw evidence window at the moment canonical n first equals 70.
2. Reproduce the canonical count from raw JSONL using the N61 key contract.
3. List the 9 new canonical keys since n=61.
4. Confirm no run_id-based duplicate is being counted as a new logical opportunity.
5. Recompute cumulative WR, PF, gross wins, gross losses, net PnL, and median PnL.
6. Compute the n=62-70 block WR, PF, PnL, regime mix, and session mix.
7. Update COMPRESSION share and COMPRESSION-absence/recovery status.
8. Update rolling nc_PF and consecutive-below-1.0 counter.
9. Re-evaluate all promotion gates, even though n=70 cannot pass P1.
10. Re-evaluate all kill criteria, including inactive guards.
11. Recompute ETA to n=80, n=90, n=100, and p<0.05.
12. Update tracker logic and set the next formal snapshot trigger.
13. Write a governor verdict: `CONTINUE_ACCUMULATION`, `CAUTION_DRIFT_REVIEW`, or `FAIL_REVIEW_REQUIRED`.

## Optional Analyses

Run these only if the mandatory analysis reveals drift, ambiguity, or data quality concern:

| Optional analysis | Trigger |
|---|---|
| Exact N70 reproducibility audit | Any count mismatch or duplicate ambiguity |
| Leave-one-new-trade-out | New-block PF depends on one winner |
| New-block bootstrap | N62-70 block contains mixed or adverse evidence |
| Session/hour split | New trades cluster in one hour/session |
| Price-bucket split | New trades cluster in one entry-price bucket |
| Path-truth deep dive | Path coverage falls or MFE/MAE contradicts outcome |
| OPENING_SCAN miss audit refresh | Opportunity production remains stalled despite healthy runtime |

## Milestone-Only Analyses

These should be recorded at N70 but not watched daily:

| Analysis | N70 action |
|---|---|
| Day-profit rate | Update if N70 adds new calendar dates |
| First/second/recent split | Add third segment: n=62-70 |
| LODO min PF | Recompute only if tooling is already available; otherwise defer to n=80 |
| Bootstrap p5 | Optional at N70, mandatory at n=100 |
| Excl. top-5 PF | Compute as early warning; formal at n=100 |
| Win/loss streak independence | Recompute only if new block streaks heavily |
| Full campaign health score | Deprecated for daily ops; optional executive footnote |

## Pass / Caution / Fail Thresholds

### N70 Overall PASS

All must be true:

| Gate | Threshold |
|---|---|
| Count integrity | n=70 reproducible from raw JSONL |
| Cumulative WR | > 52% |
| Cumulative PF | > 1.5 |
| New-block WR | >= 50% |
| New-block PF | >= 1.3 |
| Kill criteria | 0 formal triggers |
| nc_PF | >= 1.0 or no more than 5 consecutive below-1.0 points |
| Path truth | No contradiction if available |
| Evidence quality | No unresolved join-key, truth, or duplicate issue affecting n |

Result label: `CONTINUE_ACCUMULATION`.

### N70 CAUTION

Any one of these is enough:

| Condition | Meaning |
|---|---|
| Cumulative WR between 50% and 52% | Promotion WR gate at risk |
| Cumulative PF between 1.3 and 1.5 | PF buffer eroding before n=80 |
| New-block WR between 45% and 50% | Weak new evidence |
| New-block PF between 1.0 and 1.3 | Edge survives but degraded |
| nc_PF below 1.0 for 6-10 consecutive points | Non-COMPRESSION drift warning |
| COMPRESSION share remains near zero and velocity < 0.5/day | Evidence production risk |
| Path truth match rate materially below prior 47% | Observability regression |
| One trade contributes most new-block profit | Concentration warning |

Result label: `CAUTION_DRIFT_REVIEW`.

### N70 FAIL REVIEW

Any one of these is enough:

| Condition | Meaning |
|---|---|
| n=70 cannot be reproduced | Governance count failure |
| Cumulative WR < 50% | Directional signal weakened materially |
| Cumulative PF < 1.3 | Near formal K2 territory before n=80 |
| New-block WR < 45% | New evidence contradicts candidate |
| New-block PF < 1.0 | New evidence loses money on signal basis |
| nc_PF below 1.0 for >10 consecutive new points | Command-center warning threshold breached |
| Any formal kill criterion triggers | Candidate enters failure review |
| Outcome truth missing for any included opportunity | Count cannot support promotion logic |
| Duplicate-removal ambiguity changes n | Canonical key contract failure |

Result label: `FAIL_REVIEW_REQUIRED`.

## Promotion Tracker Logic Update At N70

At N70, update `docs/research/verification_tracker.md` as follows:

| Tracker field | Required N70 update |
|---|---|
| `n` | Set to 70 |
| Remaining to target | Set to 30 |
| Progress bar | Set to 70 / 100 |
| Last updated | Set to N70 snapshot date |
| Last evidence run | Set to latest contributing run_id/date |
| WR | Recomputed cumulative N70 WR |
| PF | Recomputed cumulative N70 PF |
| Net PnL | Recomputed cumulative N70 net PnL |
| Median PnL | Recomputed cumulative N70 median PnL |
| p-value | Recomputed one-sided binomial |
| n required for p<0.05 | Recomputed from current WR |
| Calendar weeks | Recomputed ISO week count |
| Promotion criteria met | Recomputed full table |
| Kill criteria | Recomputed full table |
| Path evidence | Updated if path truth available |
| Weekly progress log | Add W23/W24 rows as applicable |
| Next snapshot trigger | Set to n=80 |

Do not mark `VERIFIED` at N70. Promotion remains blocked by P1 unless n>=100 and all criteria pass simultaneously.

## Metrics To Compare Against N61 Baseline

| Metric | Compare as | Required interpretation |
|---|---|---|
| WR | cumulative N70 vs n61; new-block vs baseline | Is direction stable or weakening? |
| PF | cumulative N70 vs n61; new-block vs baseline | Is profit buffer preserved? |
| nc_PF | latest rolling non-COMP vs n61 warning framework | Is non-COMP drift improving or deteriorating? |
| Regime composition | cumulative and new-block shares | Did the new evidence come from COMPRESSION, TREND_DOWN, SIDEWAY, or TREND_UP? |
| COMPRESSION share | decision-cycle share and trade share | Is production still blocked by market structure? |
| Velocity | 7d, 14d, since-n61, historical | Is ETA improving or slipping? |
| Kill criteria | K1-K4 status | Is any kill guard active or approaching activation? |

## Governor Review Checklist

Before issuing an N70 verdict, answer every item:

1. Does raw JSONL reproduce exactly 70 canonical logical opportunities?
2. Are the 9 new opportunity keys since n=61 listed?
3. Are any of the new 9 duplicate runtime rows?
4. Do all 70 included opportunities have outcome truth?
5. Did cumulative WR remain above 52%?
6. Did cumulative PF remain above 1.5?
7. Did the n=62-70 block preserve positive PF?
8. Did nc_PF breach the >10 consecutive below-1.0 warning?
9. Did COMPRESSION recover, remain absent, or worsen?
10. Did TREND_UP or SIDEWAY become a larger drag?
11. Did BTC exclusion remain valid?
12. Did velocity improve enough to make n=100 plausible before the next governance review?
13. Did path truth confirm or contradict the outcome evidence?
14. Did any JSONL integrity issue, duplicate issue, or join-key issue affect the count?
15. Are all conclusions labeled as research-only with no runtime authority?

## N70 Verdict Options

Use exactly one:

| Verdict | Meaning | Next action |
|---|---|---|
| `CONTINUE_ACCUMULATION` | Evidence remains directionally intact | Continue to n=80 snapshot |
| `CAUTION_DRIFT_REVIEW` | Evidence survives but drift risk is active | Continue collecting, but add a drift review note |
| `FAIL_REVIEW_REQUIRED` | Count, quality, or performance materially failed | Stop promotion path until governor review |

## Expected N70 Summary Format

```text
N70 Snapshot Verdict: <CONTINUE_ACCUMULATION | CAUTION_DRIFT_REVIEW | FAIL_REVIEW_REQUIRED>

Canonical n: 70
New since n=61: 9
WR: <value> vs n61 baseline <value>
PF: <value> vs n61 baseline <value>
New-block WR/PF: <value> / <value>
nc_PF: <value>; consecutive below 1.0: <count>
COMPRESSION share: <value>
Regime mix: COMP <n>, TD <n>, SIDEWAY <n>, TU <n>
Kill criteria triggered: <0-4>
Next trigger: n=80
Runtime behavior changed: No
Live behavior changed: No
Strategy/risk/execution changed: No
```

## Safest Execution Boundary

The safest N70 boundary is:

```text
research snapshot only
docs update only
no runtime policy
no replay promotion
no strategy/risk/execution/live change
```

N70 can justify continued evidence accumulation or a caution review. It cannot justify live readiness, runtime filtering, threshold activation, or promotion to VERIFIED.
