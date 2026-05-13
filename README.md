# PolyTrade Bot / Polymarket 5M BTC-ETH Quant System

> Current status: paper-first, partially live-wired, not live-trading ready.
> Last synced: 2026-05-10.

PolyTrade Bot is a Python trading system for Polymarket BTC/ETH 5-minute binary prediction markets. The current main path runs real market data and real CLOB orderbooks through a paper-mode execution simulator by default.

Do not treat this repository as a new project or a rebuild candidate. It already has a working market scanner, oracle/feed path, terminal dashboard, paper execution path, risk modules, order intent guards, observability utilities, and tests. The current direction is to evolve from single-entry scalping into regime-aware probability diagnostics, paper-only inventory replay research, and eventually bounded multi-price inventory research after evidence supports it.

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

Startup validates key `.env` values before the bot runs. Invalid `MODE` or invalid boolean live flags fail clearly. Invalid `PAPER_BALANCE_SOURCE` falls back to `virtual` with a warning. Telegram is disabled safely if `TELEGRAM_ENABLED=true` but token/chat ID is missing. Secrets are never printed in startup logs.

Startup logs include a redacted configuration summary:

```text
Mode: PAPER
Execution: PAPER ONLY
Live Orders: DISABLED
Balance Source: paper_virtual
Wallet Reference Enabled: NO
Telegram Enabled: NO
Quant Logging: ENABLED
Replay Analyzer: AVAILABLE
RiskAgent: ENABLED
ExitAgent: ENABLED
```

Safe default paper runtime:

```bash
python main.py
```

Explicit paper runtime:

```bash
python main.py --mode paper --interval 60
```

Optional paper balance reference settings:

```env
PAPER_BALANCE_SOURCE=virtual
WALLET_REFERENCE_REFRESH_SECONDS=300
SHOW_WALLET_REFERENCE_BALANCE=true
```

`PAPER_BALANCE_SOURCE=virtual` keeps the existing isolated paper bankroll from `ACCOUNT_BALANCE`.

`PAPER_BALANCE_SOURCE=wallet_reference` lets paper mode fetch the real wallet/CLOB collateral balance and use it only as the paper sizing reference. The dashboard and startup messages label this as `wallet_reference_paper`, show `REAL WALLET BALANCE (REFERENCE ONLY)`, and keep execution as `PAPER ONLY` / `NO LIVE ORDERS`. If the wallet balance fetch fails, the bot warns and falls back to `paper_virtual`.

If `LIVE_TRADING_ENABLED=true` is set while running paper mode, startup warns loudly and keeps live orders disabled.

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
     -> polymarket/regime_diagnostics.py
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
  -> utils/scan_log_loader.py
  -> utils/quant_event_logger.py
  -> utils/telegram_reporter.py
  -> utils/telegram_alerts.py
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
- Paper mode can optionally mirror real wallet/CLOB collateral as a read-only sizing reference with `PAPER_BALANCE_SOURCE=wallet_reference`; execution remains paper-only.
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
- Offline analyzers and replay outputs must not feed automatic runtime decisions without a separately approved phase.
- Regime/probability diagnostics are evidence only until a future runtime-policy task explicitly scopes behavior changes.
- No martingale, unlimited averaging down, all-in behavior, or loss-chasing inventory scaling.

Partially implemented / needs validation:

- Live execution path exists but has not been proven end to end.
- Live allowance is currently a blocker in latest evidence.
- Fill/cancel/reconcile lifecycle is not confirmed live.
- Telegram alerting exists with a cooldown/dedup utility, and clear trader alert call sites are routed through it where safe.
- Daily report and Telegram summary readers now load combined `scan_log*.csv` files, but daily message wording still needs review for stale content.

## Logging System

Implemented:

- `utils/logger.py` configures console logging and per-run rotating file logs.
- File logs use `polytrade_bot_<timestamp>_<pid>.log`.
- `SafeRotatingFileHandler` disables itself if Windows locks a file or rollover fails with `PermissionError` / errno 13.
- `polymarket/realtime_logger.py` writes per-run scan CSV files under `runtime/realtime_logs/YYYY-MM-DD/`.
- Realtime CSV writes use `scan_log_<timestamp>_<pid>.csv`.
- CSV open/write/flush/close permission failures disable CSV logging for that session only.
- Paper summaries include cycles, markets, opportunities, orders, fills, exits, PnL, drawdown, skip reasons, risk mode, and bankroll tier data.
- `daily_report.py` and `utils/telegram_reporter.py` load and combine `scan_log*.csv`, including old `scan_log.csv` and per-run scan files.
- `utils/quant_event_logger.py` can write structured JSONL events under `runtime/quant_data/` with fail-soft per-writer disable behavior.
- `polymarket/trader.py` emits quant events for runtime market snapshots, decisions, order intent/submit/fill/fail, trade open/close, risk events, reconciliation blocks, and low-frequency system health.
- `tools/quant_data_quality.py` validates emitted quant JSONL files offline.
- `tools/replay_analyzer.py` summarizes emitted quant JSONL files offline into replay metrics and reports.
- Paper wallet-reference mode shows wallet bankroll, paper sizing balance, paper cash, source, and `NO LIVE ORDERS` in dashboard/startup surfaces when enabled.

Planned:

- Retention policy and log compaction.
- Incident report writer and health-event analytics.

## Offline Quant Analysis

These tools only read files under `runtime/quant_data/` and write reports under `runtime/reports/`. They do not affect live trading, paper trading, strategy, risk sizing, wallet state, orderbooks, or execution.

Validate JSONL data quality for one day:

```bash
python tools/quant_data_quality.py --date 2026-05-08 --write-report
```

Run replay analysis for one day:

```bash
python tools/replay_analyzer.py --date 2026-05-08 --csv
```

Run replay analysis for a date range:

```bash
python tools/replay_analyzer.py --from 2026-05-08 --to 2026-05-09 --csv
```

Generate a conservative paper-run evaluation from the data quality and replay reports:

```bash
python tools/paper_evaluation_report.py --date 2026-05-08
```

Evaluate a date range:

```bash
python tools/paper_evaluation_report.py --from 2026-05-08 --to 2026-05-09
```

Data quality checks include readable files, valid JSON lines, required base fields, parseable timestamps, valid mode values, non-empty event types, and numeric sanity checks for fields such as price, size, pnl, confidence, edge, spread, and liquidity.

Replay metrics include total closed trades, win rate, gross and average PnL, max win/loss, average holding time, skipped decisions, top skip reasons, approved/rejected ratio, risk reject count, execution failure count, average entry spread/confidence, and PnL by YES/NO outcome and BTC/ETH asset.

Paper evaluation reads the generated `quant_data_quality_*.json` and `replay_report_*.json` files, writes `paper_evaluation_*.json`, and returns `PASS`, `CAUTION`, or `FAIL`. It is conservative: malformed data, severe risk incidents, execution failures, system-health errors, or high drawdown can fail a run, while small samples, high spreads, and liquidity/spread-heavy skips usually produce caution. See `docs/PAPER_TRADING_RUNBOOK.md` for the 24-hour paper checklist, post-run workflow, and live-readiness checklist.

## Current Quant Roadmap

Phase 1:

- Regime classification.
- Probability scoring.
- Indicator evidence.
- Terminal/decision-log/JSONL observability only.
- No execution change.

Phase 2:

- Paper-only inventory replay.
- Reload/unload opportunity analysis.
- Opportunity decay.
- MFE/MAE tracking.

Phase 3:

- Bounded multi-price inventory engine design.
- Max inventory cap, max risk cap, max reload count.
- Stop loss, forced exit, panic exit.
- No martingale and no unlimited averaging down.

Phase 4:

- Continuous probabilistic inventory trading only after paper evidence supports it.

Planning docs:

- `DOCUMENTATION_MAP.md`
- `QUANT_REGIME_PROBABILITY_ENGINE.md`
- `INVENTORY_REPLAY_RESEARCH_PLAN.md`
- `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md`
- `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md`

## Telegram Alert System

Implemented:

- `TelegramNotifier` sends messages asynchronously through a single-worker thread pool.
- Telegram retries use `requests` session retry adapters.
- ERROR/CRITICAL logs can be routed through `TelegramLogHandler`.
- Message builders exist for startup, trade, exit, settlement, floor breach, drawdown, loss cluster, and errors.
- `daily_report.py` can send a daily Telegram summary if notifier setup succeeds.
- `utils/telegram_alerts.py` exposes `notify_startup`, `notify_entry`, `notify_exit`, `notify_risk`, `notify_critical`, `notify_summary`, and `notify_incident`.
- Risk, incident, summary, and repeated critical alerts can be cooldown/dedup limited through that utility.
- Clear trader alerts for entries, exits, risk blocks, critical close/reduce failures, summaries, and reconciliation incidents now route through the alert layer where safe.

Limitations:

- Telegram failures are intentionally non-blocking and mostly silent.
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
- Daily report scan CSV aggregation.
- Quant JSONL event logger fail-soft behavior.
- Telegram alert cooldown/dedup behavior.
- Trader observability failure regression in paper mode.
- Terminal dashboard layout, resize, and overflow behavior.
- Position manager/reconciliation and position tracker.
- Probability, expected value, delta engine, trend runner, lucky shot, trade frequency, stale feed kill switch.

Useful commands:

```bash
python -m pytest tests/ -q
pytest -q tests/test_terminal_dashboard_display.py tests/test_paper_mode.py tests/test_logging_resilience.py
pytest -q tests/test_scan_log_loading.py tests/test_quant_event_logger.py tests/test_telegram_alerts.py tests/test_logging_resilience.py
pytest -q tests/test_execution_risk_controls.py tests/test_paper_mode.py tests/test_polymarket_trader.py tests/test_risk_modes.py tests/test_exit_agent.py
```

## Known Limitations

- Live trading is not validated.
- Latest verify evidence still includes `missing_allowance`.
- No confirmed live order placement/fill/cancel/reconcile cycle.
- JSONL event logging is wired into the main trader loop, but retention/analytics are not implemented yet.
- Telegram cooldown/dedup is wired for clear trader alert call sites, but daily message copy still needs review.
- Daily Telegram message wording still has stale content that needs review.
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
    quant_data/
  logs/
  logs_vps/
  backtest_results/
  archive/
```

## Roadmap

Next priorities:

1. Keep documentation synchronized before new feature phases.
2. Collect Phase 1 regime/probability paper evidence without changing execution.
3. Use offline replay/evaluator output to decide whether Phase 2 paper inventory replay is justified.
4. Run longer paper sessions with real BTC/ETH market/orderbook data.
5. Resolve live allowance.
6. Validate tiny controlled live order, fill, cancel, and reconciliation only after explicit approval.
7. Consolidate dashboards and stale docs after runtime safety is stable.

## AI Assistant Instructions

Before modifying code, read:

1. `CODEX_START_HERE.md`
2. `PROJECT_RULES.md`
3. `AGENTS.md`
4. `MASTER_AGENT_ROUTER.md`
5. `CURRENT_PROJECT_STATUS.md`
6. `PROJECT_STRUCTURE.md`
7. `KNOWN_ISSUES.md`
8. `FILE_INDEX.md`
9. `QUANT_FUTURE_DECISION_ENGINE.md`
10. Relevant role docs under `docs/quant_agent_setup_md/roles/`

Never rebuild the bot from scratch unless explicitly requested.

Agent role docs are reusable Codex skill prompts, not autonomous runtime modules. For docs-only agent work, do not change Python runtime behavior. Use the router to choose the right role for risk, orderbook, Telegram, observability, paper evaluation, no-entry diagnostics, config safety, shutdown, testing, and docs tasks.
