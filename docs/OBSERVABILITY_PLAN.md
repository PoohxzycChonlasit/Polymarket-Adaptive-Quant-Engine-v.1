# Observability Plan

> Last synced: 2026-05-08.
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
- Terminal UI V2 bounded rolling log panel.
- Paper session summary logging.
- Optional Telegram notifier and Telegram error handler.

Partially implemented:

- Daily report generation exists in `daily_report.py`.
- Telegram daily message generation exists in `utils/telegram_reporter.py`.
- Telegram startup/trade/exit/settlement/risk/error message builders exist.

Known gaps:

- No JSONL quant event store yet.
- No alert cooldown/dedup layer yet.
- Daily report and Telegram summary readers still assume fixed `scan_log.csv`.
- No formal retention/compaction job yet.
- No incident report writer yet.
- No health endpoint that consolidates market/user feed lag, orderbook age, reconciliation status, logging state, and Telegram state.

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
```

Runtime status:

```text
PolymarketTrader.update_dashboard_status()
  -> runtime/bot_status.json
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

## JSONL Event Logging Plan

Planned file pattern:

```text
runtime/events/YYYY-MM-DD/events_<timestamp>_<pid>.jsonl
```

Planned event schema:

```json
{
  "ts_utc": "2026-05-08T00:00:00Z",
  "event_type": "ORDERBOOK_BEST",
  "mode": "paper",
  "market": "BTC",
  "market_slug": "...",
  "condition_id": "...",
  "token_id": "...",
  "severity": "info",
  "data": {},
  "correlation_id": "cycle-123"
}
```

Planned event types:

- `CYCLE_START`
- `CYCLE_END`
- `MARKET_SELECTED`
- `TOKEN_FLOW`
- `ORDERBOOK_RESPONSE`
- `ORDERBOOK_BEST`
- `MODEL_DECISION`
- `RISK_PLAN`
- `RISK_MODE`
- `BANKROLL_RANK_LOCK`
- `ORDER_INTENT_APPROVED`
- `ORDER_INTENT_BLOCKED`
- `PAPER_ORDER`
- `PAPER_FILL`
- `PAPER_EXIT`
- `PAPER_PNL`
- `LIVE_ORDER_SUBMITTED`
- `LIVE_ORDER_FAILED`
- `RECONCILIATION_STATUS`
- `LOCKDOWN_TRIGGERED`
- `LOGGING_DEGRADED`
- `TELEGRAM_SEND_FAILED`

Implementation rules:

- JSONL logging must be additive.
- JSONL failure must not crash the trading loop.
- JSONL must not change strategy, risk, wallet, orderbook, or execution decisions.
- Use event correlation IDs so a cycle can be reconstructed.
- Do not log secrets, private keys, full API credentials, or unmasked wallet secrets.

## Telegram Alert Design

Implemented alert surfaces:

- Startup alert from `main.py`.
- Error/critical log alert through `TelegramLogHandler`.
- Settlement alert from `PolymarketTrader`.
- Risk/floor/drawdown/loss-cluster alert builders in `utils/telegram_reporter.py`.
- Daily report sender path.

Required next design:

- Add alert event types.
- Add cooldown by `(event_type, market, reason)`.
- Add severity routing:
  - `INFO`: summaries only.
  - `WARN`: bounded frequency.
  - `ERROR`: immediate but deduped.
  - `CRITICAL`: immediate and repeated only after cooldown.
- Add dedup hash of normalized alert body.
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

1. Update `daily_report.py` to read all/latest `scan_log_*.csv`.
2. Update `utils/telegram_reporter.py` to read all/latest `scan_log_*.csv`.
3. Add tests for per-run CSV daily report aggregation.
4. Add `runtime/events` JSONL writer with fail-soft behavior.
5. Add Telegram cooldown/dedup service.
6. Add tests for alert suppression and logging-degraded behavior.
