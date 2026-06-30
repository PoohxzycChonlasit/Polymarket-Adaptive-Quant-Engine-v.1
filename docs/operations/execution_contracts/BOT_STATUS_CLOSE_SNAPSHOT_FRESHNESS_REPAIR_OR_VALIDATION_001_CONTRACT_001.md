# BOT_STATUS_CLOSE_SNAPSHOT_FRESHNESS_REPAIR_OR_VALIDATION_001 Contract

## 1. Task Identity

- Task ID: `BOT_STATUS_CLOSE_SNAPSHOT_FRESHNESS_REPAIR_OR_VALIDATION_001`
- Task class: `5 VALIDATION / BOT STATUS SNAPSHOT FRESHNESS`
- Objective: Validate or minimally repair stale `runtime/bot_status.json` after a paper close while preserving close/PnL accounting and all trading behavior.

## 2. Scope

Allowed inspection:

- `docs/reports/TRADE_CLOSE_AND_PNL_ACCOUNTING_VALIDATION_001.md`
- `runtime/position_tracker_state.json`
- `runtime/bot_status.json`
- `polymarket/trader.py` status snapshot and close paths
- `main.py` paper realtime status/close ordering
- focused status/exit tests under `tests/polymarket` or `tests/observability`
- ops state files and this report

Allowed changes if repair is required:

- Status snapshot freshness only.
- Focused regression tests.
- Report and operations metadata.

Forbidden changes:

- Strategy logic.
- Sizing logic.
- Risk thresholds.
- Order submission semantics.
- Live execution behavior.
- Wallet or live balance behavior.
- `config/settings.py`.
- `.env`.
- Runtime data deletion or manual reset.

## 7. Evidence Plan

- Reproduce the stale status condition with a focused unit test before any runtime-code edit.
- Verify source ordering of forced/pre-close exit and dashboard status writes.
- Compile changed Python files.
- Run focused pytest for the touched status/exit behavior.
- Run broader focused acceptance set if the change touches `polymarket/trader.py`.
- Use bounded paper validation only if unit/source evidence is insufficient.

## 13. Safety Findings

- Paper mode remains default for validation.
- The target issue is observability freshness: canonical position tracker state and trade-close accounting were already proven correct.
- A status refresh must not alter entry approval, exit approval, order intent, risk thresholds, sizing, live submission, wallet mutation, or reconciliation.
- Blast radius score: `LOW-MEDIUM` because `polymarket/trader.py` may be touched, but the intended change is a fail-soft dashboard snapshot write after a successful close.
- Graph query: `NOT_REQUIRED_FOR_CLASS_5`; knowledge-graph query is required for class 6+ only.

## 18. Validation Commands

Planned:

```powershell
.\.venv\Scripts\python.exe -m py_compile main.py polymarket\trader.py
.\.venv\Scripts\python.exe -m pytest tests\polymarket\test_exit_agent.py -q --tb=short -ra
.\.venv\Scripts\python.exe -m pytest tests\observability tests\polymarket -q --tb=short -ra
.\.venv\Scripts\python.exe -m json.tool docs\operations\ACTIVE_WORKFLOW_STATE_001.json
.\.venv\Scripts\python.exe -m json.tool docs\operations\TASK_QUEUE_001.json
.\.venv\Scripts\python.exe -m json.tool docs\operations\loop_memory\LOOP_MEMORY_20260628_001.json
git diff --check
```

Bounded paper validation is optional and will only run if needed to prove freshness beyond focused tests.

## 19. Output Commit Plan

- Report: `docs/reports/BOT_STATUS_CLOSE_SNAPSHOT_FRESHNESS_REPAIR_OR_VALIDATION_001.md`
- Commit message: `fix: refresh bot status after paper close`
- Push target: `origin/main`
