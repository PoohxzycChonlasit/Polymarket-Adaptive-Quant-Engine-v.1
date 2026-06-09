# N100 Research Backlog

Date: 2026-06-08

Mode: backlog only. This document does not authorize new audits, new frontier research, runtime changes, strategy changes, risk changes, execution changes, replay promotion, or live trading.

## Purpose

Define the restrained research backlog to use only after ETH YES FC OS reaches canonical `n >= 100`, or after the governor explicitly opens an N100 review. During accumulation mode, this file is a parking lot, not an action list.

## Current State

| Field | Value |
| --- | ---: |
| Current canonical n | 62 |
| Remaining to n=100 | 38 |
| Current milestone | N70 pending |
| Candidate state | VERIFICATION_IN_PROGRESS |
| Runtime authority | None |

## N100 Entry Conditions

N100 research review may begin only when:

1. Canonical export reproduces `canonical_n >= 100`.
2. Export metadata validation is `PASS`.
3. Duplicate removals are reconciled.
4. Outcome truth is present for every included opportunity.
5. Regime enrichment is complete enough for governor review.
6. N70 and any later milestone notes are archived or explicitly superseded.
7. The operator explicitly opens the N100 review scope.

## Mandatory N100 Questions

These are parked until N100:

| Question | Required Evidence |
| --- | --- |
| Is ETH YES FC OS promotable from OBSERVED/VERIFICATION_IN_PROGRESS to VERIFIED? | n>=100, WR, PF, p-value, robustness checks |
| Does PF survive concentration removal? | Ex-top-1, ex-top-3, ex-top-5 checks |
| Does non-COMPRESSION edge survive? | nc_PF and regime split at n>=100 |
| Did COMPRESSION recover or remain structurally absent? | Regime composition across W23+ |
| Is TREND_UP still a drag? | TREND_UP n, WR, PF, contribution |
| Is SIDEWAY durable or marginal? | SIDEWAY n, WR, PF, date spread |
| Does path truth support outcome truth? | MFE/MAE and checkpoint coverage if available |
| Is evidence executable or still signal-only? | Executability overlay and share/notional reality |

## Required N100 Metrics

| Metric | Purpose |
| --- | --- |
| Canonical n | Promotion sample gate |
| WR | Directional outcome quality |
| PF | Signal profitability quality |
| nc_PF | Non-COMPRESSION survivability |
| p-value | Statistical strength against random baseline |
| Median PnL | Robust central tendency |
| Gross win / gross loss | PF decomposition |
| Regime mix | Dependence and drift review |
| Date/week distribution | Stability and concentration |
| Leave-one-date-out PF | Date concentration risk |
| Ex-top-winner PF | Outlier dependency |
| Bootstrap PF distribution | Robustness estimate |
| Path truth coverage | MFE/MAE support if available |

## N100 Backlog Items

| Item | Class | Run Before N100? |
| --- | --- | --- |
| Canonical N100 reproducibility audit | Mandatory at N100 | No |
| Full promotion criteria review | Mandatory at N100 | No |
| Kill criteria review | Mandatory at N100 | Only tripwire-driven before N100 |
| Regime robustness review | Mandatory at N100 | No |
| Concentration and outlier dependency | Mandatory at N100 | No |
| p-value and required-n projection | Mandatory at N100 | Milestone snapshots only |
| Path truth confirmation | Optional/conditional | Only if path truth coverage changes materially |
| Executability reality review | Optional/conditional | Only if sizing mode changes by explicit scope |
| OPENING_SCAN coverage revisit | Optional/conditional | Only if intake loss affects count integrity |

## Deferred Questions

Do not open these during accumulation mode unless a tripwire requires it:

- Whether to promote ETH YES FC OS.
- Whether to add runtime filters.
- Whether to alter OPENING_SCAN scheduling.
- Whether to change stop loss, sizing, risk, execution, or live readiness.
- Whether COMPRESSION absence requires policy.
- Whether TREND_UP should be excluded.

## Tripwire Exceptions

The backlog may be partially opened before N100 only if the accumulation monitor reports:

| Exception | Allowed Response |
| --- | --- |
| `canonical_n >= 70` | Run N70 package only |
| PF < 1.5 | Governor deterioration review |
| WR < 52% | Governor deterioration review |
| nc_PF tripwire | Non-COMPRESSION warning review |
| TREND_UP sample doubles | TREND_UP drag review |
| COMPRESSION share materially changes | COMPRESSION context update |

Even under exception, do not change runtime policy without explicit implementation authorization.

## Report Format At N100

```text
N100 Governor Review

Canonical n:
WR:
PF:
nc_PF:
p-value:
Regime mix:
Outlier dependency:
Date stability:
Path truth:
Kill criteria:
Promotion criteria:
Verdict:
Runtime behavior changed: No
Live behavior changed: No
Strategy/risk/execution changed: No
```

## Governor Verdict

Status: **BACKLOG_ONLY_UNTIL_N100**.

Current action: continue accumulation toward N70. Do not open new research threads unless a defined tripwire fires.
