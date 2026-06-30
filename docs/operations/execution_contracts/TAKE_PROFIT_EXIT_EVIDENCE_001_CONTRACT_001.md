# TAKE_PROFIT_EXIT_EVIDENCE_001 Contract

## 1. Task Identity

- Task ID: `TAKE_PROFIT_EXIT_EVIDENCE_001`
- Task class: `5 VALIDATION / PAPER EXIT EVIDENCE`
- Objective: Run bounded paper validation to determine whether current paper runtime naturally produces at least one `take_profit` exit and whether exit evidence is logged correctly.

## 2. Scope

Allowed actions:

- Run paper mode only.
- Capture run-scoped logs, trade journal events, position state, cash/exposure, and live-safety markers.
- Create report and update operations files.

Allowed files to modify:

- `docs/reports/TAKE_PROFIT_EXIT_EVIDENCE_001.md`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- active loop memory file
- this execution contract

Forbidden changes:

- Strategy thresholds.
- Take-profit thresholds.
- Stop-loss thresholds.
- Sizing.
- Risk.
- Execution behavior.
- Live behavior.
- `config/settings.py`.
- `.env`.
- Runtime source code.

## 7. Evidence Plan

- Preflight clean tree and no active Python runtime process.
- Preserve stale owner file if present; do not delete runtime data.
- Run `main.py --mode paper --interval 60 --ui compact` for 60-120 minutes if practical.
- Stop early only if a run-scoped `take_profit` close is observed and evidence is captured.
- Summarize:
  - run_id
  - duration
  - trade_open count
  - trade_close count
  - exit_reason distribution
  - take_profit count
  - stop_loss count
  - realized PnL
  - hold time
  - market regime at TP if present
  - confidence / EV at entry if present
  - cash/exposure reconciliation
  - live markers

## 13. Safety Findings

- Paper mode only.
- Existing stale owner file will not be deleted by the agent; runtime stale-owner handling may recover it.
- The task is validation-only and must not modify any trading policy, settings, or runtime source code.
- Blast radius score: `LOW` if only report/ops files change.
- Graph query: `NOT_REQUIRED_FOR_CLASS_5`; knowledge graph query is required for class 6+ only.

## 18. Validation Commands

Planned:

```powershell
.\.venv\Scripts\python.exe -m py_compile main.py polymarket\trader.py polymarket\observability\trader_trade_event_payload.py
.\.venv\Scripts\python.exe main.py --mode paper --interval 60 --ui compact
.\.venv\Scripts\python.exe -m json.tool docs\operations\ACTIVE_WORKFLOW_STATE_001.json
.\.venv\Scripts\python.exe -m json.tool docs\operations\TASK_QUEUE_001.json
.\.venv\Scripts\python.exe -m json.tool docs\operations\loop_memory\LOOP_MEMORY_20260628_001.json
git diff --check
```

## 19. Output Commit Plan

- Report: `docs/reports/TAKE_PROFIT_EXIT_EVIDENCE_001.md`
- Commit message: `docs: validate take profit exit evidence`
- Push target: `origin/main`
