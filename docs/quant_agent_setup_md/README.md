# Quant Agent System

> Last synced: 2026-05-10.

This folder is the operating manual for AI-assisted work on the PolyTrade Bot. It defines role responsibilities, workflows, and templates for scoped, safety-first work.

The markdown files are guidance for ChatGPT/Codex sessions. They are not proof that corresponding runtime modules are fully implemented.

## Start Here

| File | Purpose |
|------|---------|
| `00_MASTER_CONTEXT.md` | Project goal, safety priorities, current state. |
| `01_QUANT_OPERATING_SYSTEM.md` | Daily quant-desk style workflow. |
| `02_AGENT_INDEX.md` | Agent roles and usage order. |
| `playbooks/CODEX_WORKFLOW.md` | How to hand scoped tasks to Codex. |

## Current Source Of Truth

Before using any role doc, read:

1. `../../CODEX_START_HERE.md`
2. `../../PROJECT_RULES.md`
3. `../../AGENTS.md`
4. `../../MASTER_AGENT_ROUTER.md`
5. `../../CURRENT_PROJECT_STATUS.md`
6. `../../PROJECT_STRUCTURE.md`
7. `../../KNOWN_ISSUES.md`
8. `../../FILE_INDEX.md`
9. `../../QUANT_FUTURE_DECISION_ENGINE.md`
10. `../OBSERVABILITY_PLAN.md` for logging/Telegram work

## Agent Roles

| Phase | Agent | File |
|-------|-------|------|
| Safety/core | Project Manager | `roles/01_PROJECT_MANAGER_AGENT.md` |
| Safety/core | Code Architect | `roles/02_CODE_ARCHITECT_AGENT.md` |
| Safety/core | Risk Manager | `roles/03_RISK_MANAGER_AGENT.md` |
| Safety/core | Exit Execution | `roles/04_EXIT_EXECUTION_AGENT.md` |
| Safety/core | Market Data | `roles/05_MARKET_DATA_AGENT.md` |
| Safety/core | Position Reconciliation | `roles/06_POSITION_RECONCILIATION_AGENT.md` |
| Safety/core | Test CI | `roles/07_TEST_CI_AGENT.md` |
| Research | Research Quant | `roles/08_RESEARCH_QUANT_AGENT.md` |
| Research | Signal Strategy | `roles/09_SIGNAL_STRATEGY_AGENT.md` |
| Validation | Backtest Replay | `roles/10_BACKTEST_REPLAY_AGENT.md` |
| Observability | Observability Incident | `roles/11_OBSERVABILITY_INCIDENT_AGENT.md` |
| Review | Review Learning | `roles/12_REVIEW_LEARNING_AGENT.md` |
| Research | Market Regime | `roles/18_MARKET_REGIME_AGENT.md` |
| Research | Inventory Engine | `roles/20_INVENTORY_ENGINE_AGENT.md` |
| Research | Execution Microstructure | `roles/21_EXECUTION_MICROSTRUCTURE_AGENT.md` |
| Research | Inventory Analytics | `roles/22_INVENTORY_ANALYTICS_AGENT.md` |

## Current Roadmap

1. Phase 1: regime classification, probability scoring, indicator evidence, observability only.
2. Phase 2: paper-only inventory replay, reload/unload analysis, opportunity decay, MFE/MAE tracking.
3. Phase 3: bounded multi-price inventory engine with strict caps, stop loss, forced exit, no martingale, and no unlimited averaging down.
4. Phase 4: continuous probabilistic inventory trading only after paper evidence supports it.

## Usage Rule

Use these docs to plan and review work. Codex should implement only scoped tasks with tests and must not bypass paper/live, risk, exit, reconciliation, order intent, or logging safety boundaries.
