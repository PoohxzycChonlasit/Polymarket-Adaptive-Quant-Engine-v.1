# PolyTrade Bot - Codex / AI Agent Instructions

> Last synced: 2026-05-08.
> Keep this file safety-first. It is auto-loaded for future AI sessions.

## Project Goal

Build, validate, and operate a Python trading bot for Polymarket BTC/ETH 5-minute binary prediction markets with paper-first validation and strict risk controls before any live execution.

The project is not confirmed live-trading ready. Current work should harden the existing implementation, not rebuild it.

## Documentation Sync Rule

Before implementing any new feature phase, perform a documentation synchronization pass when docs are stale or when the user requests it.

Before modifying code, read `CURRENT_PROJECT_STATUS.md` and do not assume the project is new or needs rebuilding.

## Session Startup

Read these first:

1. `CURRENT_PROJECT_STATUS.md`
2. `CODEX_START_HERE.md`
3. latest real file in `research/daily/YYYY-MM-DD.md`
4. `docs/PROJECT_STRUCTURE.md`
5. `docs/KNOWN_ISSUES.md`
6. relevant role docs in `docs/quant_agent_setup_md/roles/`

If the task touches cleanup or structure, also read:

- `docs/PROJECT_CLEANUP_REPORT.md`

If the task touches observability or Telegram, also read:

- `docs/OBSERVABILITY_PLAN.md`
- `polymarket/realtime_logger.py`
- `utils/logger.py`
- `utils/telegram_reporter.py`
- `daily_report.py`

## Canonical Runtime Path

Safe default paper runtime:

```bash
python main.py
```

Explicit paper runtime:

```bash
python main.py --mode paper --interval 60
```

Legacy aliases routed to paper:

```bash
python main.py --mode polymarket-paper --interval 60
python main.py --mode polymarket-realtime --interval 60
```

Live runtime requires explicit operator intent and readiness preflight:

```bash
python main.py --mode live --interval 60
```

Always inspect `.env` and `config/settings.py` before live-risk work.

## Available AI Agent Role Docs

The agent playbooks live under `docs/quant_agent_setup_md/roles/`.

Use these as guidance; they are markdown instructions, not autonomous runtime modules.

| Agent doc | Responsibility | Use when |
|-----------|----------------|----------|
| `01_PROJECT_MANAGER_AGENT.md` | Scope, sequencing, handoffs | Planning multi-step work. |
| `02_CODE_ARCHITECT_AGENT.md` | File ownership, interfaces, modularity | Any multi-file change. |
| `03_RISK_MANAGER_AGENT.md` | Risk rejection rules and safety gates | Risk, sizing, drawdown, exposure, entry approval. |
| `04_EXIT_EXECUTION_AGENT.md` | Exit, TP/SL, forced/panic exits | Exit-system changes. |
| `05_MARKET_DATA_AGENT.md` | Freshness, orderbook, token IDs, spread/depth | Market data/orderbook work. |
| `06_POSITION_RECONCILIATION_AGENT.md` | True inventory, orders, fills, mismatch handling | Reconciliation/order lifecycle work. |
| `07_TEST_CI_AGENT.md` | Test plan and CI safety gates | Every implementation task. |
| `08_RESEARCH_QUANT_AGENT.md` | Offline research context | Strategy research only. |
| `09_SIGNAL_STRATEGY_AGENT.md` | Signal changes | Only when explicitly changing strategy. |
| `10_BACKTEST_REPLAY_AGENT.md` | Backtest/replay validation | Strategy/import path changes. |
| `11_OBSERVABILITY_INCIDENT_AGENT.md` | Logs, alerts, health, incidents | Logging/Telegram/monitoring work. |
| `12_REVIEW_LEARNING_AGENT.md` | Postmortem/review learning | After incidents or paper sessions. |

## Agent Use Boundaries

- Do not use agent markdowns as permission to rewrite architecture.
- Do not create AI/LLM calls inside the realtime trading loop.
- Do not bypass Risk Manager, ExitAgent, reconciliation, or order intent guards.
- Do not change live size unless explicitly requested.
- Do not alter strategy logic during documentation, observability, cleanup, or UI tasks.
- Do not claim planned agent contracts are implemented unless code/tests prove it.

## Active Files

| File | Purpose |
|------|---------|
| `main.py` | CLI dispatcher and realtime loop orchestration. |
| `config/settings.py` | Pydantic settings, env defaults, live/paper validation. |
| `polymarket/trader.py` | Main Polymarket trading coordinator. |
| `polymarket/client.py` | CLOB auth, orderbooks, balances, orders, redemption helpers. |
| `polymarket/gamma_fetcher.py` | Gamma market/event/token discovery. |
| `polymarket/market_feed.py` | Binance feed singleton. |
| `polymarket/oracle_price_feed.py` | Oracle/PTB price path used by trader. |
| `polymarket/virtual_ptb.py` | Virtual price-to-beat tracker. |
| `polymarket/signal.py` | Realtime signal logic. |
| `polymarket/backtester_5m.py` | Backtest signal/performance path. |
| `polymarket/order_manager.py` | Builds order risk plans. |
| `polymarket/order_intent.py` | ENTRY/EXIT validation guard. |
| `polymarket/bankroll_tiers.py` | Bankroll tiers and rank hysteresis. |
| `polymarket/risk_modes.py` | NORMAL/DEFENSIVE/MICRO_RECOVERY/LOCKDOWN. |
| `polymarket/realtime_logger.py` | Runtime scan/trade CSV and summary logging. |
| `utils/risk_manager.py` | Canonical hard risk policy for Polymarket path. |
| `utils/position_tracker.py` | Position and drawdown state. |
| `utils/display.py` | Terminal UI V2 and other Rich displays. |
| `utils/logger.py` | Console/file/Telegram logging setup. |
| `utils/telegram_reporter.py` | Telegram message builders and daily report sender. |

## Secondary Or Experimental Paths

Keep these, but do not treat them as canonical live Polymarket execution:

- `hft_paper_run.py` - active HFT paper simulation utility.
- `main.py --mode hft` and `hft/` - experimental HFT engine; paper-first only.
- `crypto_scalper/` - separate crypto scalper path.
- `dashboard/` and `web-dashboard/` - overlapping dashboards.
- `polymarket/five_min_monitor.py` - standalone monitor.

## Files And Data Not To Touch Casually

Do not delete, rewrite, or archive these without explicit scope:

- `.env`
- `.env.example`
- `config/`
- `runtime/`
- `logs/`
- `logs_vps/`
- `backtest_results/`
- trade logs and scan logs
- wallet/API credential helpers
- strategy research records

Never edit private keys, wallet addresses, live flags, or allowance behavior unless the user explicitly asks and understands the live-risk impact.

## Safety Rules

- Paper mode is default.
- Paper mode uses real market data/orderbooks and simulated execution only.
- Paper mode must not touch wallet collateral, require allowance, sign orders, send live orders, cancel live orders, or redeem live positions.
- Live mode requires explicit `--mode live`.
- Live mode must pass readiness preflight.
- Do not claim live-ready until order placement, fill, cancel, and reconciliation are proven.
- Do not claim orderbook works unless `BID`, `ASK`, and `SPREAD` are visible in terminal.
- Do not claim wallet sync unless terminal/logs show real live balance source.
- Reconcile positions before new entries.
- Block trading on mismatch, partial hedge, unknown state, or LOCKDOWN.
- ENTRY orders must be BUY.
- NO entries must buy NO tokens, not sell YES without inventory.
- EXIT SELL is allowed only for tracked existing inventory.
- `arb_auto_execute` must remain false by default unless explicitly scoped.
- No martingale, no averaging down by default, no all-in, no fixed 20% live risk.
- Risk and exit safety outrank new strategy ideas.

If `.env` has `PAPER_TRADING=false` or `DRY_RUN=false`, treat the repo as live-risk until proven otherwise.

## Cleanup Rules

- Do not delete files immediately.
- Move clearly unused/stale files to `archive/legacy/` only in a dedicated cleanup task.
- Do not move runtime logs, trade logs, backtest results, or config files.
- Keep imports working after any move.
- Update `docs/PROJECT_CLEANUP_REPORT.md` for cleanup decisions.
- Update `docs/PROJECT_STRUCTURE.md` when runtime/data flow changes.
- Update `README.md` for user-facing command/status changes.
- Update `CURRENT_PROJECT_STATUS.md` whenever real project state changes.

## Testing Commands

```bash
# Full test suite
python -m pytest tests/ -q

# Import smoke
python -c "from polymarket.backtester_5m import PolymarketBacktester5m; print('OK')"

# Strategy smoke when strategy/import paths changed
python main.py --mode polymarket-backtest --days 3 --asset BTC

# Safe paper loop
python main.py

# Read-only verify
python main.py --mode verify
```

Run strategy smoke only when strategy or import paths changed.

## Known Manual Review Items

- `daily_report.py` and `utils/telegram_reporter.py` still read fixed `scan_log.csv`, but realtime logging writes per-run `scan_log_<run_id>.csv`.
- Telegram alerts have no central cooldown/dedup layer.
- Live allowance remains a blocker in latest status.
- Live fill/cancel/reconcile cycle is not validated.
- Some older research docs may still describe HFT/live readiness too optimistically.
