# FILE_INDEX.md

> Last updated: 2026-07-01.
> Purpose: Code navigation source of truth for the Profit Engine mission.

## Current Mission

Build a profitable Polymarket Crypto 5-Minute Quant Profit Engine.

Read first:

1. `00_MISSION.md`
2. `01_SUCCESS_CRITERIA.md`
3. `02_PROJECT_RULES.md`
4. `03_MASTER_AGENT_ROUTER.md`
5. `04_CURRENT_PROJECT_STATUS.md`
6. `05_PROFIT_ROADMAP.md`
7. `06_BACKLOG.md`
8. `07_RUNTIME_SCOREBOARD.md`
9. `08_MINI_EVIDENCE_PIPELINE.md`
10. `09_OPERATOR_DASHBOARD_SPEC.md`
11. `10_LOOP_ENGINEERING.md`
12. `11_LOGGING_AND_MARKET_TIME_TRUTH.md`

Then read:

- `CODEX_START_HERE.md`
- `PROJECT_RULES.md`
- `AGENTS.md`
- `MASTER_AGENT_ROUTER.md`
- `CURRENT_PROJECT_STATUS.md`
- `DOCUMENTATION_MAP.md`

## Entrypoints

| File | Purpose |
|---|---|
| `main.py` | CLI dispatcher and realtime loop entrypoint. |
| `CODEX_START_HERE.md` | Minimal AI startup context. |
| `PROJECT_RULES.md` | Existing safety and workflow rules. |
| `AGENTS.md` | Codex/AI agent safety rules. |
| `MASTER_AGENT_ROUTER.md` | Existing role router. |
| `DOCUMENTATION_MAP.md` | Documentation navigation source of truth. |

## Runtime-Critical Path

```text
main.py
-> polymarket/trader.py
-> market discovery / orderbook / price feeds
-> signal / probability / EV
-> risk / sizing / order manager
-> order intent
-> paper or live execution branch
-> position tracking / trade journal / PnL
-> dashboard and logs
```

## Module Ownership Map

| Area | Primary Files |
|---|---|
| Runtime orchestration | `main.py`, `polymarket/trader.py` |
| Market discovery/data | `polymarket/gamma_fetcher.py`, `polymarket/client.py`, `polymarket/market_feed.py`, `polymarket/oracle_price_feed.py`, `polymarket/virtual_ptb.py` |
| Quant math/model | `polymarket/signal.py`, `polymarket/probability_model.py`, `polymarket/expected_value.py`, `polymarket/regime_diagnostics.py` |
| Risk/sizing/portfolio | `utils/risk_manager.py`, `polymarket/bankroll_tiers.py`, `polymarket/risk_modes.py`, `polymarket/position_sizing.py`, `polymarket/order_manager.py` |
| Execution/reconciliation | `polymarket/order_intent.py`, `polymarket/client.py`, `polymarket/position_manager.py`, `utils/position_tracker.py` |
| Observability/logging | `utils/quant_event_logger.py`, `polymarket/realtime_logger.py`, `utils/logger.py`, `utils/scan_log_loader.py` |
| Dashboard/operator visibility | `utils/display.py`, `dashboard/`, `web-dashboard/` |
| Offline evidence | `tools/`, `tests/`, `runtime/quant_data/`, `tools/canonical_run_evidence_summary_builder.py` |

## Large / Risky Files

| File | Risk |
|---|---|
| `polymarket/trader.py` | Large orchestrator with runtime lifecycle, risk, execution, paper accounting, exits, logging, and dashboard state. |
| `main.py` | Runtime entrypoint; mode safety matters. |
| `config/settings.py` | Live/paper and risk defaults. Do not edit without explicit scope. |
| `polymarket/client.py` | Live CLOB, orderbook, wallet, and order behavior. |
| `polymarket/order_manager.py` | Risk plan and size approval path. |
| `polymarket/position_sizing.py` | Position sizing math. |
| `utils/risk_manager.py` | Hard risk policy. |

## Safe Edit Zones

For this governance reset:

- Root Profit Engine docs.
- `docs/reports/`.
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`.
- `docs/operations/TASK_QUEUE_001.json`.
- Current active workday loop memory file.

Future safe docs-only zones:

- `docs/architecture/`.
- `docs/reports/`.
- `docs/audits/`.
- `docs/research/`.
- `docs/operations/`.

Current safe offline tooling:

- `tools/canonical_run_evidence_summary_builder.py` - reads existing JSONL logs and emits conservative per-run evidence summaries under `docs/reports/run_evidence/`.

Loop memory pointer rule:

- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json` must point to the current workday loop memory file.
- Archived loop memory files are read-only by policy and must not receive new task entries.
- `next_task` must not be followed blindly; Tech Lead review is required after workday rotation.

## Dangerous Edit Zones

Do not edit casually:

- `polymarket/trader.py`
- `main.py`
- `config/settings.py`
- `.env`
- `polymarket/client.py`
- `polymarket/order_manager.py`
- `polymarket/position_sizing.py`
- `utils/risk_manager.py`
- `utils/position_tracker.py`
- Runtime state under `runtime/`
- Logs and generated evidence

## Modularization Target

Use the global modular standard in `02_PROJECT_RULES.md`:

- Thin entrypoints.
- Thin orchestrators.
- Single-responsibility modules.
- No hidden trading logic in dashboard/telemetry.
- No behavior change during pure extraction.
- Tests after extraction.

## Update Rules

Update this file when:

- A canonical runtime file changes ownership.
- A new root Profit Engine entrypoint is added.
- A module becomes dangerous or safe to edit.
- Dashboard/operator visibility becomes canonical.
- Paper/live command behavior changes.

If file structure is uncertain, write `UNKNOWN` instead of guessing.
