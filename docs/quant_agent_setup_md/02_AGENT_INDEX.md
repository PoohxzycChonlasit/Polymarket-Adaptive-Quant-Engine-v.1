# Agent Index

> Last synced: 2026-05-10.

Use these role docs for planning, implementation boundaries, review, and test design. They are operating instructions, not runtime proof that an agent module exists.

## Safety/Core Agents

1. Project Manager Agent - scope, sequencing, handoffs.
2. Code Architect Agent - module placement, interfaces, files to touch/avoid.
3. Risk Manager Agent - entry approval, sizing, drawdown, exposure, floor.
4. Exit Execution Agent - TP/SL, forced/panic exits, runner behavior.
5. Market Data Agent - orderbooks, token IDs, feed freshness, spread/depth.
6. Position Reconciliation Agent - true inventory, open orders, fills, mismatch handling.
7. Test CI Agent - test plan, regression coverage, CI gate.

## Research/Validation/Observability Agents

1. Research Quant Agent - offline research only.
2. Signal Strategy Agent - signal changes only when explicitly scoped.
3. Backtest Replay Agent - replay/backtest validation.
4. Observability Incident Agent - logs, alerts, health, incidents.
5. Review Learning Agent - postmortems and improvement notes.
6. Market Regime Agent - regime/probability diagnostics and grouping.
7. Execution Microstructure Agent - spread, liquidity, timing, and fill-quality research.
8. Inventory Engine Agent - bounded future inventory design.
9. Inventory Analytics Agent - paper-only inventory replay and MFE/MAE research.

## How To Use

- ChatGPT Project: analysis, planning, review, specs.
- Codex: scoped implementation, tests, docs updates.
- Repo markdown files: permanent operating manual.

## Current Runtime Boundaries

- Paper mode is default.
- Live mode is blocked until readiness passes.
- Do not bypass Risk, ExitAgent, Reconciliation, or OrderIntent.
- Do not treat HFT as canonical live execution.
- Do not claim planned observability systems are implemented.
- Treat regime/probability fields as diagnostics until explicitly scoped otherwise.
- Keep inventory research paper/offline until bounded runtime implementation is approved.

## Current Roadmap

1. Phase 1: regime/probability diagnostics and observability.
2. Phase 2: paper inventory replay and opportunity-decay research.
3. Phase 3: bounded multi-price inventory design.
4. Phase 4: continuous probabilistic inventory trading only after paper evidence.

## Folder Layout

```text
docs/quant_agent_setup_md/
  README.md
  00_MASTER_CONTEXT.md
  01_QUANT_OPERATING_SYSTEM.md
  02_AGENT_INDEX.md
  roles/
  playbooks/
  templates/
```
