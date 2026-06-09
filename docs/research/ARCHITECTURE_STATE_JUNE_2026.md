# Architecture State - June 2026

Date: 2026-06-09
Mode: documentation snapshot only

This document records the current evidence-governance architecture at a high level. It does not authorize runtime, strategy, risk, execution, sizing, config, or live-mode changes.

## Operating Mode

Current operating posture: **ACCUMULATION MODE**.

Allowed routine work:

- Refresh canonical export.
- Refresh command center.
- Run drift audit.
- Maintain N70 readiness tracker.
- Report tripwires.

Not authorized:

- New market research.
- New frontier audits.
- Runtime policy changes.
- Strategy changes.
- Risk changes.
- Execution changes.
- Live trading changes.

## Evidence Pipeline

| Layer | Primary Artifact | Purpose |
| --- | --- | --- |
| Raw trade truth | `runtime/quant_data/trade_journal/*.jsonl` | Trade outcome and lifecycle truth |
| Regime truth | `runtime/quant_data/decision_log/*.jsonl` | Regime enrichment source |
| Canonical export | `runtime/research_exports/canonical_regime_enriched_trades_v1.csv` | Offline canonical opportunity table |
| Export metadata | `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json` | Validation, freshness, duplicate count |
| Command center | `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md` | Current campaign state |
| Drift audit | `tools/_drift_audit.py` output | Rolling WR/PF/nc_PF and regime drift |
| Readiness tracker | `docs/research/frontiers/N70_READINESS_TRACKER.md` | N70 gate state |

## Governance Documents

| Document | Role |
| --- | --- |
| `docs/research/frontiers/N70_RUNBOOK.md` | Operator workflow for N70 trigger handling |
| `docs/research/frontiers/N100_RESEARCH_BACKLOG.md` | Deferred backlog for N100 review only |
| `docs/research/N70_EXECUTION_PACKAGE.md` | Formal N70 package checklist |
| `docs/research/frontiers/N70_PREFLIGHT_AUDIT.md` | N70 dependency and validation preflight |
| `docs/research/frontiers/N70_READINESS_TRACKER.md` | Current milestone readiness state |

## Automation

| Automation | Status | Purpose |
| --- | --- | --- |
| `eth-yes-fc-os-accumulation-monitor` | ACTIVE | Daily evidence workflow and tripwire notification |

The monitor is scoped to maintain existing evidence artifacts only. It should not create new research threads unless a defined tripwire fires and the operator explicitly opens that scope.

## Tripwire Boundary

Immediate notification conditions:

- Canonical n reaches 70.
- nc_PF tripwire triggers.
- PF falls below 1.5.
- WR falls below 52%.
- COMPRESSION share materially changes.
- TREND_UP sample doubles.

If no tripwire is active, the system remains in accumulation mode.

## Commit Hygiene

Generated runtime exports remain uncommitted unless explicitly approved.

Scratch tooling remains excluded unless explicitly promoted from scratch to maintained tooling.

Docs-only commits should stage exact approved paths. Do not use `git add .`.

## State Verdict

Architecture state: **STABLE_FOR_EVIDENCE_ACCUMULATION**.

Next milestone: **N70 trigger**.
