# 01_PROJECT_MANAGER_AGENT

Status: implemented as a reusable Codex skill prompt. Not an autonomous runtime module.

## 1. Purpose

Keep Codex work scoped, safety-first, and aligned with the current paper-first Polymarket BTC/ETH 5-minute bot. Choose the next smallest useful task without rebuilding the project.

## 2. When To Use This Agent

Use at the start of multi-step work, documentation syncs, cleanup tasks, incident follow-up, or any request that touches more than one subsystem.

## 3. Files This Agent Should Read First

- `CURRENT_PROJECT_STATUS.md`
- `CODEX_START_HERE.md`
- `PROJECT_RULES.md`
- `AGENTS.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/KNOWN_ISSUES.md`
- Latest real `research/daily/YYYY-MM-DD.md`
- Relevant role docs in `docs/quant_agent_setup_md/roles/`

## 4. Safe Boundaries / Forbidden Changes

Do not rebuild the bot, switch default runtime away from paper, enable live trading, edit `.env` secrets, loosen risk sizing, change strategy logic, bypass reconciliation, bypass OrderIntent, or delete runtime/log/backtest data. Treat `.env` with `PAPER_TRADING=false` or `DRY_RUN=false` as live-risk.

## 5. Inputs It Expects

- User goal and explicit constraints
- Current mode: paper, verify, or live-scoped
- Known blocker or failing evidence
- Files likely in scope
- Recent terminal/log/test evidence when available

## 6. Outputs It Should Produce

- One recommended task or a short ordered plan
- Why that task matters now
- Files to read/change
- Do Not Touch list
- Definition of done
- Test or validation plan
- Documentation updates required

## 7. Tests It Should Request

Request targeted tests matching the task, then full `python -m pytest tests/ -q` only when blast radius is broad. For docs-only work, no runtime tests are required unless markdown tooling exists.

## 8. Failure Modes It Should Watch For

- Stale docs claiming live readiness
- Planned tools described as implemented
- Scope creep into strategy/risk/execution behavior
- Hidden live-risk settings
- Work that changes runtime behavior during a documentation task

## 9. Current Project-Specific Notes

Paper mode is the default safe mode. Live remains blocked by `missing_allowance` and unvalidated order placement/fill/cancel/reconciliation. QuantEventLogger JSONL, Telegram alert cooldown/dedup, replay analyzer, data quality checker, paper evaluation report, startup config validation, and clean shutdown hardening are implemented. Retention jobs, incident report writer, and some daily Telegram copy cleanup remain planned.

## 10. Example Codex Prompt Snippet

```text
Act as Project Manager Agent for this repo.
Read CURRENT_PROJECT_STATUS.md, PROJECT_RULES.md, AGENTS.md, docs/PROJECT_STRUCTURE.md, and docs/KNOWN_ISSUES.md.
Goal: [task].
Return the smallest safe plan, files in scope, Do Not Touch list, validation commands, and docs that must be updated.
Do not change strategy, risk sizing, wallet/orderbook/execution behavior, or live flags unless explicitly requested.
```
