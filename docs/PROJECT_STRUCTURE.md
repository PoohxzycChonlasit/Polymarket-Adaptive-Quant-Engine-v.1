# Project Structure

> Last synced: 2026-05-10.
> Scope: current implementation map for the Polymarket BTC/ETH 5-minute bot.

This document describes the current working structure without changing strategy, risk, orderbook, wallet, or execution logic.

## Canonical Runtime

Safe default paper loop:

```bash
python main.py
```

Explicit paper loop:

```bash
python main.py --mode paper --interval 60
```

Legacy paper aliases:

```bash
python main.py --mode polymarket-paper --interval 60
python main.py --mode polymarket-realtime --interval 60
```

Read-only verification:

```bash
python main.py --mode verify
```

Explicit live loop:

```bash
python main.py --mode live --interval 60
```

Live mode must pass `run_verify_mode()` first. Current status still includes live allowance/execution validation blockers.

## Runtime Folders

| Path | Status | Purpose |
|------|--------|---------|
| `runtime/` | generated | Runtime state and reports; do not treat as source code. |
| `runtime/bot_status.json` | generated | Current bot state for dashboards/API consumers. |
| `runtime/realtime_logs/YYYY-MM-DD/` | generated | Realtime scan CSV and daily summary output. |
| `logs/` | generated | Main per-run application logs. |
| `logs_vps/` | generated/evidence | VPS operational logs; preserve for incident review. |
| `backtest_results/` | generated/evidence | Backtest artifacts; preserve. |
| `archive/legacy/` | historical | Archived/stale docs or code from cleanup passes. |
| `research/daily/` | manual/agent notes | Daily work notes and project history. |

Do not delete runtime/log/backtest evidence during normal cleanup.

## Main Startup Flow

```text
main.py
  -> build_parser()
  -> get_settings()
  -> setup_logger()
  -> mode dispatcher
```

Paper runtime:

```text
run_polymarket_paper()
  -> run_polymarket_realtime(force_paper=True)
  -> settings.paper_trading=True
  -> settings.dry_run=True
  -> PAPER MODE banner
```

Live runtime:

```text
run_polymarket_live()
  -> run_verify_mode()
  -> block if readiness fails
  -> run_polymarket_realtime(force_paper=False)
```

## Main Trading Loop

```text
run_polymarket_realtime()
  -> PolymarketTrader()
  -> RealtimeLogger()
  -> PolymarketRealtimeDisplay()
  -> loop:
       refresh portfolio/session display
       update PTB/oracle/countdown
       refresh market display metrics/orderbooks
       panic/forced exit checks
       run_single_cycle()
       write scan records
       update terminal dashboard
```

## Market Data Flow

Implemented:

```text
Binance / crypto feed
  -> polymarket/market_feed.py
  -> polymarket/oracle_price_feed.py
  -> polymarket/virtual_ptb.py
  -> PolymarketTrader

Polymarket Gamma API
  -> polymarket/gamma_fetcher.py
  -> market slug, condition_id, YES/NO token IDs

Polymarket CLOB
  -> polymarket/client.py
  -> get_orderbook(token_id)
  -> normalized best bid/ask/spread
```

Orderbook path status:

- Implemented and verified in read-only mode for BTC/ETH in latest evidence.
- Rejects stale books older than 3 seconds in the trader/display metrics path.
- Uses bounded CLOB retry/backoff/cooldown and per-market circuit-breaker state for transient orderbook HTTP errors, timeouts, rate limits, and token/client issues.
- Uses a short bounded empty-book recovery window in paper runtime and reports `liquidity_state`, recovery attempt/success/failure, and retry count.
- Emits early-window timing diagnostics including market epoch, seconds since open/until close, first seen seconds remaining, first evaluable seconds remaining, and alignment reason.
- Logs token flow and best bid/ask.
- Must be monitored for regression; do not claim orderbook works if terminal lacks `BID`, `ASK`, and `SPREAD`.

## Signal And Model Flow

```text
market snapshot
  -> polymarket/signal.py
  -> polymarket/probability_model.py
  -> polymarket/expected_value.py
  -> polymarket/opportunity_scanner.py
  -> polymarket/order_manager.py
```

Implemented strategy modules include Counter-Momentum, Markov Bounds, Kelly Sizing, Micro-Grinder mode, ExitAgent protection, and risk floor.

Rule: Do not change realtime signal logic without updating `polymarket/backtester_5m.py` and running an appropriate backtest.

## Risk Flow

```text
PolymarketTrader
  -> utils/risk_manager.py
  -> polymarket/bankroll_tiers.py
  -> polymarket/position_sizing.py
  -> polymarket/risk_modes.py
  -> polymarket/order_manager.py
  -> RiskPlan
```

Implemented:

- Hard floor balance.
- Max risk / single-trade caps from settings and risk code.
- Bankroll Rank Lock / hysteresis.
- `BANKROLL_TIER_ARCHITECTURE_V2` centralized tier metadata in `polymarket/bankroll_tiers.py`.
- Paper-only `MICRO_SURVIVAL_MODE` for MICRO family bankrolls under the configured threshold.
- MICRO adaptive timing for paper MICRO tiers only; STANDARD / BASE / GROWTH / CAPITAL tiers do not inherit MICRO timing behavior.
- Risk Mode Ladder: NORMAL, DEFENSIVE, MICRO_RECOVERY, LOCKDOWN.
- Daily drawdown and loss-cluster controls.
- Reconciliation gate before new entries.
- Risk-mode sizing multiplier.

Do not increase live size or bypass risk caps.

## Reconciliation Flow

```text
PolymarketTrader.run_single_cycle()
  -> _ensure_connected()
  -> reconcile_live_positions()
  -> _block_on_reconciliation_if_needed()
  -> manage/exit existing positions
  -> only then analyze new markets
```

Implemented:

- Local position tracking in `utils/position_tracker.py`.
- Reconciliation report classification in `polymarket/trader.py`.
- LOCKDOWN on unsafe reconciliation/order failures.
- Tests for position reconciliation and order intent guards.

Live readiness still requires confirmed fill/cancel/reconcile behavior against real exchange state.

## Execution Flow

Entry:

```text
Signal / EV
  -> RiskPlan
  -> PositionSizing
  -> Risk approval
  -> Reconciliation gate
  -> OrderIntent ENTRY
  -> _submit_order()
```

Exit:

```text
Tracked local inventory
  -> ExitAgent / TP / SL / panic / forced exit
  -> OrderIntent EXIT
  -> _submit_order()
```

Implemented protections:

- ENTRY must be BUY.
- NO entry buys the NO token.
- SELL without tracked inventory is blocked.
- EXIT SELL requires tracked existing inventory.
- LOCKDOWN blocks ENTRY but allows EXIT/management.
- Paper mode enforces the same order intent guard.

Paper branch:

```text
settings.paper_trading=True
  -> no live CLOB order
  -> synthetic OrderReceipt
  -> [PAPER ORDER]
  -> [PAPER FILL]
  -> virtual cash/equity/exposure/PnL update
```

Live branch:

```text
settings.paper_trading=False
  -> CLOB orderbook price adjustment
  -> PolymarketClient.place_limit_order()
  -> balance/allowance preflight
  -> order response
  -> reconcile after attempt
```

Current live status: not validated end to end.

## Paper Mode Flow

Paper mode:

- Is default.
- Uses real market data and orderbooks.
- Simulates fills locally.
- Never sends live orders.
- Never requires allowance.
- Never touches wallet collateral.
- Uses virtual starting balance and paper portfolio state.
- Logs paper orders/fills/exits/PnL.
- Produces paper session summary.

## Portfolio Flow

Paper mode:

```text
settings.account_balance
  -> BankrollState
  -> virtual cash/equity/exposure/PnL
  -> dashboard_portfolio_state(balance_source=paper_virtual)
```

Live mode:

```text
PolymarketClient.get_usdc_balance_snapshot()
  -> CLOB collateral primary
  -> on-chain wallet diagnostic fallback
  -> dashboard_portfolio_state(balance_source=clob_collateral or onchain_wallet)
```

Do not claim wallet sync unless terminal/logs show real live balance source.

## Terminal UI Flow

```text
PolymarketRealtimeDisplay
  -> Terminal UI V2
  -> --ui auto|compact|standard|wide|fullscreen
  -> --fps low|medium|high
```

Implemented panels:

- System Status
- Portfolio
- Risk
- BTC Market
- ETH Market
- AI Decision
- Execution
- Skip Reasons
- Rolling Logs

Bottom status line:

```text
WS | ORACLE | ORDERBOOK | MODE | RISK | LATENCY | LOGGING | TIER | MICRO | LIQ | CUTOFF | RECOVERY
```

Current compact runtime visibility:

- Portfolio/Risk show BANKROLL_TIER_V2 tier id/name, family/profile, bankroll mode, `micro_survival_active`, and `micro_position_size`.
- Market/AI panels show seconds remaining, first seen/evaluable seconds, cutoff policy/effective cutoff, MICRO timing branch/allow/deny state, latest deny reason, liquidity state, and empty-book recovery state.
- This dashboard visibility is observability-only and does not alter strategy, risk sizing, execution, wallet/allowance, order intent, reconciliation, paper/live separation, or websocket/orderbook behavior.

## Logging Flow

Application logs:

```text
utils/logger.py
  -> console handler
  -> SafeRotatingFileHandler
  -> logs/polytrade_bot_<timestamp>_<pid>.log
  -> optional TelegramLogHandler for ERROR/CRITICAL
```

Realtime scan logs:

```text
polymarket/realtime_logger.py
  -> runtime/realtime_logs/YYYY-MM-DD/scan_log_<timestamp>_<pid>.csv
  -> runtime/realtime_logs/YYYY-MM-DD/daily_summary_<timestamp>_<pid>.json
```

Implemented resilience:

- Windows `PermissionError` on log setup, rollover, CSV open/write/flush/close disables only that file logger for the session.
- Trading loop should continue safely.
- `tools/session_runtime_evaluator.py` provides offline/session runtime evaluation and supports UTC same-day filters:
  - `python tools/session_runtime_evaluator.py --date YYYY-MM-DD --since HH:MM`
  - `python tools/session_runtime_evaluator.py --date YYYY-MM-DD --since HH:MM --until HH:MM`

Current observability status:

- `daily_report.py` and `utils/telegram_reporter.py` read `scan_log*.csv` through `utils/scan_log_loader.py`.
- Offline analyzers and evaluators remain reporting-only and must not feed automatic runtime decisions without a separately scoped phase.

## Notifier Flow

```text
setup_logger()
  -> TelegramNotifier if token/chat_id configured
  -> TelegramLogHandler for ERROR/CRITICAL

PolymarketTrader
  -> startup alert
  -> trade/exit/settlement/risk alerts where called

daily_report.py
  -> build_daily_message()
  -> TelegramNotifier.send_message()
```

Implemented:

- Async Telegram send via one-worker thread pool.
- Retry adapter for HTTP failures.
- HTML message builders.
- Central alert cooldown/dedup helpers in `utils/telegram_alerts.py`.

Missing:

- Structured alert event store.
- Daily Telegram copy/content cleanup before treating summaries as operationally authoritative.

## Secondary Paths

| Path | Status | Notes |
|------|--------|-------|
| `hft_paper_run.py` | experimental utility | Paper simulation; not canonical live Polymarket execution. |
| `main.py --mode hft` | experimental | Keep paper-first. |
| `main.py --mode scalper` | secondary | Separate crypto scalper product line. |
| `dashboard/` | active/overlapping | Streamlit dashboards. |
| `web-dashboard/` | active/overlapping | Next.js dashboard; not consolidated. |
| `polymarket/five_min_monitor.py` | utility | Market monitor separate from trade-loop ownership. |

## Test Structure

```text
tests/
  test_bankroll_tiers.py
  test_risk_modes.py
  test_execution_risk_controls.py
  test_paper_mode.py
  test_exit_agent.py
  test_logging_resilience.py
  test_terminal_dashboard_display.py
  test_position_reconciliation.py
  test_polymarket_trader.py
  ...
```

Use targeted tests for scoped changes, then broader suites when touching shared behavior.
