# Observability Plan

> Last synced: 2026-05-29.
> Scope: current logging/alerting implementation and planned quant observability work.

This plan documents what exists now and what still needs to be built. Do not describe planned observability systems as implemented.

## Current Observability Status

Implemented:

- Console logging through `utils/logger.py`.
- Per-run rotating file logs under `logs/`.
- Windows file-lock resilience for rotating log files.
- Realtime scan CSV logging through `polymarket/realtime_logger.py`.
- Per-run CSV filenames: `scan_log_<timestamp>_<pid>.csv`.
- Per-run daily summary filenames: `daily_summary_<timestamp>_<pid>.json`.
- PermissionError handling on CSV open, write, flush, close, and summary save.
- Shared scan CSV reader in `utils/scan_log_loader.py`.
- Daily reports and Telegram summaries now combine `scan_log*.csv`, including legacy `scan_log.csv`.
- Fail-soft JSONL writer in `utils/quant_event_logger.py`.
- Telegram cooldown/dedup utility in `utils/telegram_alerts.py`.
- Main trader loop wiring for market snapshot, decision, execution, trade, risk, reconciliation, and low-frequency system health JSONL events.
- Main trader alert routing through centralized Telegram alert helpers for clear entry, exit, risk, critical, summary, and incident call sites.
- Terminal UI V2 bounded rolling log panel.
- Paper session summary logging.
- Optional Telegram notifier and Telegram error handler.
- Runtime shutdown hardening for oracle/WebSocket feeds, realtime CSV logging, Telegram notifier executor, daily report scheduler, and trader-owned feed cleanup.
- Closed-stream console logging is fail-soft during shutdown.
- Runtime Ownership v1 is `PAPER_VALIDATED`: fresh patched run `20260529T033511Z_32308_89dc46d3` validated owner file creation, heartbeat, duplicate startup block, graceful Ctrl+Break shutdown, owner release, return code `0`, and zero run-scoped parse errors.
- Exception Observability v1 is `TEST_VALIDATED`: targeted tests passed and simulated `runtime_loop_exception` system_health emission works. Paper validation is pending until a natural runtime-loop exception occurs.
- Offline quant data quality checker in `tools/quant_data_quality.py`.
- Offline replay analyzer in `tools/replay_analyzer.py`.

Partially implemented:

- Daily report generation exists in `daily_report.py`.
- Telegram daily message generation exists in `utils/telegram_reporter.py`.
- Telegram startup/trade/exit/settlement/risk/error message builders exist.
- JSONL event logger is wired into `polymarket/trader.py`; additional analytics and retention jobs remain planned.
- Telegram alert cooldown/dedup is wired into clear trader alert call sites; daily message copy/content cleanup remains planned.

Known gaps:

- No formal retention/compaction job yet.
- No incident report writer yet.
- JSONL Writer Integrity v1.1 is not implemented. Runtime Ownership v1 reduces duplicate paper runtime writers, but it does not provide interprocess JSONL writer locking.
- Previous date-level evidence from duplicate-runtime periods remains contamination-risk evidence; use run-scoped analysis only for old mixed periods.
- No health endpoint that consolidates market/user feed lag, orderbook age, reconciliation status, logging state, and Telegram state.
- Some daily Telegram message wording still contains stale context and needs a copy/content cleanup pass.

## Current Log Architecture

Application logs:

```text
setup_logger()
  -> console handler
  -> SafeRotatingFileHandler
  -> logs/polytrade_bot_<timestamp>_<pid>.log
  -> optional TelegramLogHandler for ERROR/CRITICAL
```

Realtime scan logs:

```text
RealtimeLogger
  -> runtime/realtime_logs/YYYY-MM-DD/
     -> scan_log_<timestamp>_<pid>.csv
     -> daily_summary_<timestamp>_<pid>.json

utils.scan_log_loader
  -> loads runtime/realtime_logs/YYYY-MM-DD/scan_log*.csv
  -> keeps scan_log.csv compatibility
  -> combines rows and sorts by timestamp_utc when available
```

Quant JSONL logs:

```text
QuantEventLogger
  -> runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl
  -> runtime/quant_data/decision_log/YYYY-MM-DD.jsonl
  -> runtime/quant_data/execution_log/YYYY-MM-DD.jsonl
  -> runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl
  -> runtime/quant_data/risk_log/YYYY-MM-DD.jsonl
  -> runtime/quant_data/system_health/YYYY-MM-DD.jsonl
```

Runtime status:

```text
PolymarketTrader.update_dashboard_status()
  -> runtime/bot_status.json
```

Shutdown lifecycle:

```text
PolymarketTrader.shutdown()
  -> VirtualPriceToBeatTracker.close()
     -> PolymarketOracleFeed.stop()
        -> stop price thread
        -> stop epoch/PTB thread
        -> signal and join WebSocket thread
        -> close oracle HTTP client
  -> stop shared Binance/quant indicator feeds when they were started

RealtimeLogger.close(save_summary=True)
  -> flush/close scan CSV fail-soft
  -> write daily summary fail-soft

TelegramNotifier.close()
  -> shutdown single-worker executor
  -> close requests session
```

Terminal observability:

```text
PolymarketRealtimeDisplay
  -> System Status
  -> Portfolio
  -> Risk
  -> BTC/ETH Market
  -> AI Decision
  -> Execution
  -> Skip Reasons
  -> Rolling Logs
  -> WS | ORACLE | ORDERBOOK | MODE | RISK | LATENCY | LOGGING
```

## JSONL Event Logging

Implemented utility file pattern:

```text
runtime/quant_data/
  market_snapshots/YYYY-MM-DD.jsonl
  decision_log/YYYY-MM-DD.jsonl
  execution_log/YYYY-MM-DD.jsonl
  trade_journal/YYYY-MM-DD.jsonl
  risk_log/YYYY-MM-DD.jsonl
  system_health/YYYY-MM-DD.jsonl
```

Implemented base schema:

```json
{
  "timestamp_utc": "2026-05-08T00:00:00Z",
  "event_type": "market_snapshot",
  "mode": "paper",
  "run_id": "20260508T000000Z_1234_abcd1234",
  "source_module": "utils.quant_event_logger",
  "schema_version": "1.0",
  "payload": {}
}
```

Implemented methods:

- `log_market_snapshot(payload)`
- `log_decision(payload)`
- `log_execution(payload)`
- `log_trade_open(payload)`
- `log_trade_close(payload)`
- `log_risk_event(payload)`
- `log_system_health(payload)`

Implementation rules:

- JSONL logging must be additive.
- JSONL failure must not crash the trading loop.
- JSONL must not change strategy, risk, wallet, orderbook, or execution decisions.
- Use event correlation IDs so a cycle can be reconstructed.
- Do not log secrets, private keys, full API credentials, or unmasked wallet secrets.
- PermissionError / Windows errno 13 must disable only the affected writer category for the session.

Implemented trader integration:

- Market snapshots after orderbook reads.
- Decision events for approved, skipped, rejected, and risk-rejected outcomes.
- Execution events for order intent approval/rejection, submit attempts, paper fills, live submits, submit failures, cancel success/failure, and analysis exceptions.
- Trade journal events for opened and closed/reduced/settled positions.
- Risk events for risk mode, floor breach, balance guard, reconciliation mismatch, exit failure, cycle risk pause, and periodic risk state.
- System health events on startup and low-frequency cycle checkpoints.
- `runtime_loop_exception` system_health events are implemented and test-validated; natural paper-runtime validation is pending.

Still planned:

- Retention and compression job.
- Incident report writer.
- Deeper analytics over JSONL files.
- Dedicated `LOGGING_DEGRADED` events for every file logger state transition.
- JSONL Writer Integrity v1.1 interprocess durability/locking design.

## Offline Data Quality And Replay

Implemented data quality command:

```bash
python tools/quant_data_quality.py --date YYYY-MM-DD --write-report
```

Checks:

- JSONL files are readable.
- Each non-empty line is valid JSON.
- Required base fields exist: `timestamp_utc`, `event_type`, `mode`, `run_id`, `source_module`, `schema_version`.
- Timestamps are parseable.
- `event_type` is non-empty.
- `mode` is one of the accepted offline values.
- Numeric fields are numeric when present: `price`, `size`, `shares`, `pnl`, `confidence`, `edge`, `spread`, `liquidity`.

Optional output:

```text
runtime/reports/quant_data_quality_YYYY-MM-DD.json
```

Implemented replay commands:

```bash
python tools/replay_analyzer.py --date YYYY-MM-DD --csv
python tools/replay_analyzer.py --from YYYY-MM-DD --to YYYY-MM-DD --csv
```

Replay reads:

- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/decision_log/*.jsonl`
- `runtime/quant_data/execution_log/*.jsonl`
- `runtime/quant_data/risk_log/*.jsonl`
- `runtime/quant_data/market_snapshots/*.jsonl`

Replay outputs:

```text
runtime/reports/replay_report_YYYY-MM-DD.json
runtime/reports/replay_trades_YYYY-MM-DD.csv
```

Replay metrics:

- Total closed trades, win rate, gross PnL, average PnL, max win, max loss.
- Average holding time when matching open/close events are available.
- Skipped decisions and top skip reasons.
- Approved/rejected decision counts and ratio.
- Risk reject count and execution failure count.
- Average spread and confidence at entry.
- PnL by YES/NO outcome and BTC/ETH asset when available.

Safety rule:

- These analyzers are offline-only. They must not change strategy, risk sizing, wallet state, orderbook behavior, execution behavior, or live-trading readiness.

## Telegram Alert Design

Implemented alert surfaces:

- Startup alert from `main.py`.
- Error/critical log alert through `TelegramLogHandler`.
- Settlement alert from `PolymarketTrader`.
- Risk/floor/drawdown/loss-cluster alert builders in `utils/telegram_reporter.py`.
- Daily report sender path.
- Cooldown/dedup utility in `utils/telegram_alerts.py`.
- Public wrapper functions:
  - `notify_startup`
  - `notify_entry`
  - `notify_exit`
  - `notify_risk`
  - `notify_critical`
  - `notify_summary`
  - `notify_incident`

Current utility behavior:

- Telegram failures are caught and returned as send failures.
- Entry and exit alerts send immediately.
- Risk, incident, and summary alerts are cooldown-limited.
- Repeated critical alerts are deduped within cooldown; different critical messages can send immediately.

Implemented trader routing:

- Entry and exit notifications use `notify_entry` / `notify_exit`.
- Floor, balance guard, panic-sell block, and cycle risk pauses use `notify_risk`.
- Reconciliation blocks use `notify_incident`.
- Close/reduce failures use `notify_critical`.
- Auto-redeem cycle summaries use `notify_summary`.

Required next routing:

- Add severity routing in call sites:
  - `INFO`: summaries only.
  - `WARN`: bounded frequency.
  - `ERROR`: immediate but deduped.
  - `CRITICAL`: immediate and repeated only after cooldown.
- Add counters for suppressed alerts.
- Add terminal/log message when alerts are suppressed.

Suggested cooldown defaults:

| Event | Cooldown |
|-------|----------|
| Startup | none |
| Paper order/fill | 30s per market |
| Skip reason summary | 5m |
| Orderbook degraded | 60s |
| Reconciliation mismatch | 30s |
| LOCKDOWN | none first alert, then 60s |
| ERROR/CRITICAL duplicate | 60s |
| Daily report | once per day |

## Retention Strategy

Planned:

- Keep raw app logs for 14-30 days locally.
- Keep realtime CSV/JSONL event logs for 30 days locally.
- Keep daily summaries indefinitely or archive monthly.
- Do not delete logs automatically until the operator approves retention policy.
- Archive before delete.

Current settings defaults:

- `quant_log_retention_days = 90`
- `market_snapshot_retention_days = 14`
- `trade_journal_retention_days = 3650`
- `compress_old_quant_logs = True`

Do not move or delete:

- `runtime/`
- `logs/`
- `logs_vps/`
- `backtest_results/`

## Incident Workflow

Use `docs/quant_agent_setup_md/roles/11_OBSERVABILITY_INCIDENT_AGENT.md`.

Trigger incident review for:

- Market/orderbook feed stale.
- User/reconciliation mismatch.
- Unknown open position.
- Failed forced exit.
- Live order API failure during open risk.
- Duplicate order attempt.
- Logging degraded plus active live risk.
- Telegram outage during live risk.
- Daily drawdown hard stop.

Incident note should capture:

- Date/time.
- Mode: paper/live.
- Market(s).
- Current positions.
- Reconciliation status.
- Orderbook age.
- Risk mode.
- Logs saved.
- Root cause hypothesis.
- Restart conditions.

## Future Analytics Goals

Planned analytics:

- Top skip reason trend by market/window.
- Orderbook availability and age histogram.
- Spread/liquidity distribution.
- EV distribution vs actual entries.
- Confidence distribution vs realized outcome.
- Risk mode transition frequency.
- Bankroll rank lock raw vs active tier drift.
- Paper PnL and max drawdown by session.
- Alert volume and suppression counts.

## Immediate TODO

1. Review JSONL output from a longer real paper session.
2. Clean stale daily Telegram message wording in `utils/telegram_reporter.py`.
3. Add retention/compaction job only after operator approval.
4. Add incident report writer and richer `TELEGRAM_DEGRADED` / `LOGGING_DEGRADED` health events.
5. Add deeper analytics for orderbook availability, EV distribution, and alert suppression.
6. Monitor longer Ctrl+C paper exits for any delayed oracle/WebSocket logging after shutdown.
7. Run offline data quality and replay reports after longer paper sessions.
