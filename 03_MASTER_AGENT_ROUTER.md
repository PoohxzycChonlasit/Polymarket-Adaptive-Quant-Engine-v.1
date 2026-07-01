# 03 Master Agent Router

## Profit-First Routing

Use this file before choosing a role or starting a task. Root rule: route work to the smallest owner that improves Profit Engine evidence.

## Primary Routes

| Task Type | Primary Owner | Supporting Owners |
|---|---|---|
| Mission, scope, sequencing, backlog, promotion gates | Project Manager | Verification Officer |
| Code boundaries, modularity, extraction planning | Code Architect | Test/CI, Repository Librarian |
| Entry throughput, no-entry, gate blockers | No-Entry Diagnostics | Market Data, Replay, Microstructure |
| EV, probability, fair value, quant math | Fair Value / Signal Strategy | Replay, Market Regime |
| Spread, liquidity, fillability, timing, adverse selection | Execution Microstructure | Market Data, Exit Execution |
| Drawdown, bankroll, risk mode, exposure | Risk Manager | Position Reconciliation |
| Paper run validation and profit evidence | Paper Evaluation | Runtime Operations, Replay |
| Logging, time truth, JSONL, incidents | Observability Incident | Data Steward |
| Dashboard/operator visibility | Code Architect | Observability Incident |
| Docs/navigation/governance | Repository Librarian | Project Manager |

## Stop Routes

Stop and report instead of continuing if a task attempts to:

- Change strategy, risk, sizing, execution, live behavior, config, or `.env` without explicit scope.
- Promote live trading from docs or offline evidence alone.
- Build a framework unrelated to immediate profit evidence.
- Tune thresholds from weak samples.
- Touch runtime code during docs-only work.

## Required Routing Block

Every task should state:

- Primary role.
- Supporting roles.
- Why selected.
- Files allowed to inspect.
- Files intentionally ignored.
- Explicit Tech Lead authorization source.

## Task Authorization Rule

`NEXT_TASK` is not authorization.

- Agents must not auto-start `NEXT_TASK` from workflow state, reports, queue entries, or loop memory.
- Agents may only provide candidate tasks for Tech Lead review.
- Tech Lead Review is required before every new task.
- If authorization is unclear, stop and ask before proceeding.

## Current Default Route

For Profit Engine Day 1 work:

- Primary: Project Manager.
- Supporting: Code Architect, Repository Librarian, Verification Officer.
- Forbidden: runtime code, strategy, sizing, risk, execution, config, `.env`, live behavior.
