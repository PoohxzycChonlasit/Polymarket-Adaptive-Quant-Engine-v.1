# N70 Runbook

Date: 2026-06-08

Mode: accumulation governance only. This runbook does not authorize new market research, runtime changes, strategy changes, risk changes, execution changes, replay promotion, or live trading.

## Purpose

Use this runbook when ETH YES FC OS reaches canonical `n >= 70`, or when the daily accumulation monitor reports a tripwire. The goal is to refresh existing evidence artifacts, verify count integrity, and decide whether to continue accumulation.

## Current Baseline

| Field | Baseline |
| --- | ---: |
| Canonical n | 62 |
| Remaining to n=70 | 8 |
| WR | 56.5% |
| PF | 1.980 |
| nc_PF | 2.367 |
| p-value | 0.187 |
| COMPRESSION share | 33.9% historical, 0% W23 |
| TREND_UP n | 7 |
| Latest trigger state | INACTIVE |

Source: `docs/research/frontiers/N70_READINESS_TRACKER.md`.

## Daily Accumulation Workflow

Run only the existing offline evidence workflow:

```powershell
py -3.11 tools/canonical_regime_export.py
py -3.11 tools/eth_yes_fc_os_command_center.py
py -3.11 tools/_drift_audit.py --path runtime/research_exports/canonical_regime_enriched_trades_v1.csv
git diff --check
git status --short
```

Expected maintained artifacts:

| Artifact | Purpose |
| --- | --- |
| `runtime/research_exports/canonical_regime_enriched_trades_v1.csv` | Canonical export input |
| `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json` | Export validation metadata |
| `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md` | Daily campaign command center |
| `docs/research/frontiers/N70_READINESS_TRACKER.md` | Milestone readiness state |

Do not create new audits during routine accumulation. Only update maintained tracking artifacts when requested or when the daily workflow is explicitly scoped to do so.

## N70 Trigger Conditions

N70 review becomes active only when all are true:

1. Canonical export reports `canonical_n >= 70`.
2. Export validation status is `PASS`.
3. Duplicate removal is reconciled.
4. Regime join rate is at least 95%.
5. Drift audit runs successfully against the same export.
6. No runtime, strategy, risk, execution, live, or config change is bundled with the review.

If `canonical_n < 70`, verdict remains `ACCUMULATING`.

## Immediate Notification Tripwires

Notify the operator immediately if any condition is detected:

| Tripwire | Threshold |
| --- | --- |
| N70 reached | `canonical_n >= 70` |
| nc_PF warning | Existing nc_PF tripwire triggers, especially sustained below 1.0 |
| PF deterioration | Full-cell `PF < 1.5` |
| WR deterioration | Full-cell `WR < 52%` |
| COMPRESSION shift | COMPRESSION share materially changes from current historical/W23 context |
| TREND_UP expansion | TREND_UP sample doubles from baseline `n=7` to `n >= 14` |

If none trigger, report only concise accumulation status.

## N70 Review Commands

At trigger time, run:

```powershell
py -3.11 tools/canonical_regime_export.py
py -3.11 tools/eth_yes_fc_os_command_center.py
py -3.11 tools/_drift_audit.py --path runtime/research_exports/canonical_regime_enriched_trades_v1.csv
py -3.11 -m pytest -q tests/test_drift_audit.py tests/test_canonical_regime_export.py tests/test_eth_yes_fc_os_command_center.py
py -3.11 -m py_compile tools/_drift_audit.py tools/canonical_regime_export.py tools/eth_yes_fc_os_command_center.py
git diff --check
git status --short
```

Use `docs/research/N70_EXECUTION_PACKAGE.md` and `docs/research/frontiers/N70_PREFLIGHT_AUDIT.md` as the governing checklist.

## Required Outputs At N70

The N70 package may update existing governance docs and create the dedicated N70 snapshot if scoped:

| Output | Status |
| --- | --- |
| `docs/research/watchlists/ETH_YES_FC_OS.md` | Required |
| `docs/research/verification_tracker.md` | Required |
| `docs/research/campaigns/ETH_YES_FC_OS_CAMPAIGN_DASHBOARD.md` | Required |
| `docs/research/evidence_velocity_dashboard.md` | Required |
| `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md` | Required |
| `docs/research/N70_SNAPSHOT_REVIEW.md` | Required at N70 |
| `docs/research/CANONICAL_N70_REPRODUCIBILITY_AUDIT.md` | Optional if reconciliation uncertainty appears |

Generated runtime exports should remain uncommitted unless explicitly approved.

## Failure Modes

| Failure Mode | Response |
| --- | --- |
| Export validation fails | Stop N70 review; report export failure |
| Command center n differs from export n | Stop and reconcile count |
| Drift audit fails | Stop and report tool failure |
| `UNKNOWN` regime rate rises materially | Mark review as blocked until source is explained |
| Duplicate count changes unexpectedly | Run count reconciliation before any tracker update |
| Runtime/code/config files appear in staged diff | Stop; do not commit |
| Scratch tools appear | Exclude from commit scope |
| Generated runtime exports appear | Exclude unless explicitly approved |

## Automation Audit

Automation id: `eth-yes-fc-os-accumulation-monitor`

| Field | Observed |
| --- | --- |
| Kind | `heartbeat` |
| Status | `ACTIVE` |
| Schedule | `FREQ=DAILY;BYHOUR=9;BYMINUTE=0;BYSECOND=0` |
| Scope | Daily ETH YES FC OS evidence workflow |
| Data sources | Canonical export, command center, drift audit, N70 readiness tracker |
| Output behavior | Immediate tripwire notice; otherwise concise daily accumulation status |
| Runtime boundary | Prompt explicitly forbids runtime, strategy, risk, execution, live config changes |

Audit verdict: **MONITOR_SCOPE_VALID**.

Minor limitation: the automation prompt says "COMPRESSION share materially changes" without a numeric threshold. Until a numeric threshold is approved, materiality should be interpreted against the current baseline: historical COMPRESSION share 33.9%, W23 COMPRESSION share 0%.

## Governor Verdict

Status: **ACCUMULATION_MODE_ACTIVE**.

Next formal milestone: `canonical_n >= 70`.
