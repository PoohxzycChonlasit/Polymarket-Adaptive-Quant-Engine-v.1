# Quant Operating System

> Last synced: 2026-05-10.

## Purpose
This document defines how the project should be operated like a small quant trading desk, even if only one person is working on it.

## Desk Roles
Real quant teams split responsibilities clearly. For this project, each role becomes an AI agent or a workflow.

| Role | Main Question | Output |
|---|---|---|
| Project Manager | What is the single highest-priority fix? | Daily task list |
| Research Quant | Is there real edge? | Hypothesis + experiment |
| Data Engineer | Is the data trustworthy? | Feed status + clean events |
| Signal Engineer | Should we trade? | Probability + edge |
| Regime Analyst | What market state are we in? | Regime + probability evidence |
| Risk Manager | Are we allowed to trade? | Approve / reject |
| Execution Trader | How should we place/exit orders? | Order plan |
| Position Manager | What do we actually hold? | Position truth |
| Backtest Engineer | Did this work historically? | Replay report |
| QA/CI Engineer | Did code changes break anything? | Test result |
| Observability Engineer | Is the bot healthy? | Alerts + dashboard |
| Post-Trade Analyst | What did we learn? | Daily review |
| Inventory Researcher | Could bounded reload/unload help? | Paper-only replay table |

## Daily Loop
```text
1. Read CURRENT_PROJECT_STATUS.md
2. Read CODEX_START_HERE.md, PROJECT_RULES.md, AGENTS.md, MASTER_AGENT_ROUTER.md, FILE_INDEX.md, and QUANT_FUTURE_DECISION_ENGINE.md
3. Review latest paper/live evidence if relevant
4. Pick one problem only
5. Use the correct role doc
6. Write the scoped fix spec
7. Let Codex implement with tests
8. Run targeted tests
9. Run paper/replay when behavior changed
10. Update docs
11. Only then consider live validation, and only after readiness passes
```

## Current Roadmap

1. Phase 1: regime classification, probability scoring, indicator evidence, observability only.
2. Phase 2: paper-only inventory replay, reload/unload opportunity, opportunity decay, MFE/MAE.
3. Phase 3: bounded multi-price inventory engine with strict caps and exits.
4. Phase 4: continuous probabilistic inventory trading only after evidence supports it.

Offline analyzers and replay tables are decision evidence, not automatic runtime policy.

## Rule: One Problem Per Session
Bad workflow:
```text
Fix exit + change strategy + change risk + change dashboard + live test
```

Good workflow:
```text
Today only fix: force exit before close
```

## Output Standard
Every answer from an agent should contain:
- Decision
- Reason
- Risk
- Files likely affected
- Test needed
- Rollback plan

## Failure Handling
If any of these happen, stop live trading:
- Feed stale
- Position mismatch
- Bot holds into close unintentionally
- Balance below floor
- Daily loss limit hit
- Kill switch active
- Unknown exception in execution loop
- Missing allowance
- Live fill/cancel/reconcile unknown
- OrderIntent guard blocks the order
