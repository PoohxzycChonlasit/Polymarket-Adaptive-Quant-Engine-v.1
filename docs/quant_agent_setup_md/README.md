# Quant Agent System

> Last synced: 2026-05-08.

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

1. `../../CURRENT_PROJECT_STATUS.md`
2. `../../CODEX_START_HERE.md`
3. `../../AGENTS.md`
4. `../PROJECT_STRUCTURE.md`
5. `../KNOWN_ISSUES.md`
6. `../OBSERVABILITY_PLAN.md` for logging/Telegram work

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

## Usage Rule

Use these docs to plan and review work. Codex should implement only scoped tasks with tests and must not bypass paper/live, risk, exit, reconciliation, order intent, or logging safety boundaries.
