# QUANT_OPERATING_SYSTEM

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
| Risk Manager | Are we allowed to trade? | Approve / reject |
| Execution Trader | How should we place/exit orders? | Order plan |
| Position Manager | What do we actually hold? | Position truth |
| Backtest Engineer | Did this work historically? | Replay report |
| QA/CI Engineer | Did code changes break anything? | Test result |
| Observability Engineer | Is the bot healthy? | Alerts + dashboard |
| Post-Trade Analyst | What did we learn? | Daily review |

## Daily Loop
```text
1. Read CURRENT_STATUS.md
2. Review yesterday's trades
3. Pick one problem only
4. Ask the correct agent
5. Write the fix spec
6. Let Codex implement
7. Run tests
8. Run paper/replay
9. Update docs
10. Only then consider live small
```

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
