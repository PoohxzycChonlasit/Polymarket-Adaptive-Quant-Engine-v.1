# PolyTrade Bot / Polymarket 5M BTC-ETH Quant Scalper

> Current status: paper-first, partially live-wired, not live-trading ready.
> Last synced: 2026-05-08.

PolyTrade Bot is a Python trading system for Polymarket BTC/ETH 5-minute binary prediction markets. The current main path runs real market data and real CLOB orderbooks through a paper-mode execution simulator by default.

Do not treat this repository as a new project or a rebuild candidate. It already has a working market scanner, oracle/feed path, terminal dashboard, paper execution path, risk modules, order intent guards, and tests. The remaining work is validation, observability, and live-readiness hardening.

## Safety Disclaimer

This project is not financial advice and is not confirmed live-trading ready.

Live trading must not be claimed ready until all of these are proven in terminal/runtime evidence:

- Real BTC/ETH 5-minute markets are active.
- `BID`, `ASK`, and `SPREAD` are visible in terminal.
- Wallet/portfolio source reads real CLOB collateral balance in live mode.
- Live allowance is ready.
- Live order placement, fill, cancel, and reconciliation are validated.
- Risk floor, single-trade cap, daily drawdown guard, reconciliation gate, and order intent guard remain active.

Paper mode is the default. Live mode requires explicit `--mode live` and a passing readiness preflight.

## Quickstart

Install dependencies in a local environment:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create local settings:

```bash
copy .env.example .env
```

Review `.env` before any runtime command. If `PAPER_TRADING=false` or `DRY_RUN=false`, treat the repo as live-risk until proven otherwise.

Safe default paper runtime:

```bash
python main.py
```

Explicit paper runtime:

```bash
python main.py --mode paper --interval 60
```

Responsive terminal dashboard controls:

```bash
python main.py --mode paper --interval 60 --ui auto --fps medium
```

Read-only account/market verification:

```bash
python main.py --mode verify
```

Live runtime, blocked unless readiness passes:

```bash
python main.py --mode live --interval 60
```

## Supported Modes

Implemented:

- `python main.py` - safe default Polymarket paper loop.
- `python main.py --mode paper` - explicit Polymarket paper loop.
- `python main.py --mode polymarket-paper` - legacy alias routed to paper.
- `python main.py --mode polymarket-realtime` - legacy alias routed to paper.
- `python main.py --mode verify` - read-only environment, wallet, balance, market, and model verification.
- `python main.py --mode polymarket-backtest --days N --asset BTC|ETH` - 5-minute backtest path.
- `python main.py --mode polymarket-5m-dashboard` - Streamlit dashboard for Polymarket 5-minute analysis.
- `python main.py --mode dashboard` - generic Streamlit dashboard.
- `python main.py --mode realtime` - separate crypto ticker display path.

Partially implemented / blocked:

- `python main.py --mode live` - performs readiness preflight first; current known evidence still includes `missing_allowance`.

Experimental / secondary:

- `python main.py --mode hft` and `hft/` - experimental HFT path, paper-first only.
- `hft_paper_run.py` - standalone HFT paper simulation utility.
- `crypto_scalper/` and `--mode scalper` - separate crypto scalper path, not the canonical Polymarket bot.
- `dashboard/` and `web-dashboard/` - overlapping dashboard surfaces retained for later consolidation.

## Current Architecture

```text
main.py
  -> config/settings.py
  -> polymarket/trader.py
     -> polymarket/gamma_fetcher.py
     -> polymarket/market_feed.py
     -> polymarket/oracle_price_feed.py
     -> polymarket/virtual_ptb.py
     -> polymarket/signal.py
     -> polymarket/probability_model.py
     -> polymarket/expected_value.py
     -> polymarket/position_sizing.py
     -> polymarket/order_manager.py
     -> polymarket/order_intent.py
     -> utils/risk_manager.py
     -> utils/position_tracker.py
     -> polymarket/client.py
  -> utils/display.py
  -> polymarket/realtime_logger.py
  -> utils/logger.py
  -> utils/telegram_reporter.py
```

## Runtime Flow

1. `main.py` parses mode, interval, UI layout, and FPS options.
2. Settings load from `config/settings.py` and `.env`.
3. Paper mode is forced for default/legacy paper commands.
4. `PolymarketTrader` initializes market, CLOB, risk, bankroll, reconciliation, and paper-session state.
5. `RealtimeLogger` opens per-run scan CSV logging under `runtime/realtime_logs/`.
6. `PolymarketRealtimeDisplay` renders Terminal UI V2.
7. The loop refreshes portfolio/session state, BTC/ETH market snapshots, orderbooks, signals, EV, risk plans, and execution events.
8. Paper mode returns synthetic receipts and updates virtual cash/equity/exposure/PnL locally.
9. Live mode must pass readiness checks before the realtime loop is allowed to start.

## Current Protections

Implemented:

- Paper mode default.
- Paper mode blocks live order, cancel, redeem, signing, allowance, and wallet-collateral risk paths.
- Live mode requires explicit `--mode live`.
- Verify mode checks environment, wallet, balance source, positions, orderbooks, and model decisions.
- OrderIntent validation classifies ENTRY vs EXIT.
- ENTRY orders must be BUY.
- NO entries buy the NO token; they must not SELL without inventory.
- EXIT SELL is allowed only for tracked inventory.
- LOCKDOWN blocks entries while still allowing exits/management.
- Reconciliation gate blocks new entries on unsafe state.
- Bankroll Rank Lock / hysteresis reduces tier flapping.
- Risk Mode Ladder supports NORMAL, DEFENSIVE, MICRO_RECOVERY, and LOCKDOWN.
- ExitAgent, panic/forced exit, partial TP, and runner controls are present.
- Windows file-lock logging failures disable only the affected file logger and do not crash the loop.

Partially implemented / needs validation:

- Live execution path exists but has not been proven end to end.
- Live allowance is currently a blocker in latest evidence.
- Fill/cancel/reconcile lifecycle is not confirmed live.
- Telegram alerting exists, but spam cooldown/rate-limit policy is incomplete.
- Daily Telegram summaries currently look for `scan_log.csv`, while realtime logging now writes per-run `scan_log_<run_id>.csv`.

## Logging System

Implemented:

- `utils/logger.py` configures console logging and per-run rotating file logs.
- File logs use `polytrade_bot_<timestamp>_<pid>.log`.
- `SafeRotatingFileHandler` disables itself if Windows locks a file or rollover fails with `PermissionError` / errno 13.
- `polymarket/realtime_logger.py` writes per-run scan CSV files under `runtime/realtime_logs/YYYY-MM-DD/`.
- Realtime CSV writes use `scan_log_<timestamp>_<pid>.csv`.
- CSV open/write/flush/close permission failures disable CSV logging for that session only.
- Paper summaries include cycles, markets, opportunities, orders, fills, exits, PnL, drawdown, skip reasons, risk mode, and bankroll tier data.

Planned:

- JSONL event log for structured quant events.
- Unified daily-report reader for per-run CSV files.
- Retention policy and log compaction.
- Alert cooldown and deduplication.

## Telegram Alert System

Implemented:

- `TelegramNotifier` sends messages asynchronously through a single-worker thread pool.
- Telegram retries use `requests` session retry adapters.
- ERROR/CRITICAL logs can be routed through `TelegramLogHandler`.
- Message builders exist for startup, trade, exit, settlement, floor breach, drawdown, loss cluster, and errors.
- `daily_report.py` can send a daily Telegram summary if notifier setup succeeds.

Limitations:

- Telegram failures are intentionally non-blocking and mostly silent.
- No central cooldown/deduplication layer exists yet.
- Daily summary readers still assume fixed `scan_log.csv` names.
- Some Telegram message content contains stale backtest/live-blocker text and needs a dedicated cleanup before relying on daily reports.

## Terminal Dashboard

Implemented:

- Terminal UI V2 in `utils/display.py`.
- Layout modes: `--ui auto`, `compact`, `standard`, `wide`, `fullscreen`.
- Refresh modes: `--fps low`, `medium`, `high`.
- Panels: System Status, Portfolio, Risk, BTC Market, ETH Market, AI Decision, Execution, Skip Reasons, Rolling Logs.
- Bottom status line: `WS | ORACLE | ORDERBOOK | MODE | RISK | LATENCY | LOGGING`.
- Small terminals fall back to compact mode and show a minimum-size warning.
- Long messages are clipped with ellipsis so panel borders stay aligned.

## Existing Tests

Current test areas include:

- Bankroll tiers and hysteresis.
- Risk modes and sizing multipliers.
- Execution risk controls and order intent validation.
- Paper mode isolation and simulated accounting.
- ExitAgent, take-profit, stop-loss, runner behavior.
- Orderbook/client parsing and verify mode.
- Logging resilience on Windows file locks.
- Terminal dashboard layout, resize, and overflow behavior.
- Position manager/reconciliation and position tracker.
- Probability, expected value, delta engine, trend runner, lucky shot, trade frequency, stale feed kill switch.

Useful commands:

```bash
python -m pytest tests/ -q
pytest -q tests/test_terminal_dashboard_display.py tests/test_paper_mode.py tests/test_logging_resilience.py
pytest -q tests/test_execution_risk_controls.py tests/test_paper_mode.py tests/test_polymarket_trader.py tests/test_risk_modes.py tests/test_exit_agent.py
```

## Known Limitations

- Live trading is not validated.
- Latest verify evidence still includes `missing_allowance`.
- No confirmed live order placement/fill/cancel/reconcile cycle.
- Daily report and Telegram summary paths lag the new per-run CSV naming.
- No JSONL event store yet.
- Telegram alert cooldown/dedup is not implemented.
- HFT path is experimental and not canonical live execution.
- Dashboards overlap and need later consolidation.
- Some older docs/research notes still describe stale HFT or live-ready assumptions.

## Folder Structure

```text
.
  main.py
  config/
  polymarket/
  utils/
  hft/
  crypto_scalper/
  dashboard/
  web-dashboard/
  docs/
    PROJECT_STRUCTURE.md
    PROJECT_CLEANUP_REPORT.md
    OBSERVABILITY_PLAN.md
    KNOWN_ISSUES.md
    quant_agent_setup_md/
  tests/
  research/
    daily/
  runtime/
    realtime_logs/
  logs/
  logs_vps/
  backtest_results/
  archive/
```

## Roadmap

Next priorities:

1. Keep documentation synchronized before new feature phases.
2. Fix observability drift: per-run CSV daily-report reader, JSONL event plan, Telegram cooldown.
3. Run longer paper sessions with real BTC/ETH market/orderbook data.
4. Resolve live allowance.
5. Validate tiny controlled live order, fill, cancel, and reconciliation only after explicit approval.
6. Consolidate dashboards and stale docs after runtime safety is stable.

## AI Assistant Instructions

Before modifying code, read:

1. `CURRENT_PROJECT_STATUS.md`
2. `CODEX_START_HERE.md`
3. `AGENTS.md`
4. `docs/PROJECT_STRUCTURE.md`
5. `docs/KNOWN_ISSUES.md`
6. Relevant role docs under `docs/quant_agent_setup_md/roles/`

Never rebuild the bot from scratch unless explicitly requested.
