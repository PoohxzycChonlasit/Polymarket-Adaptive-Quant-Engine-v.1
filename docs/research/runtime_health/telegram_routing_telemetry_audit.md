# Telegram Routing Telemetry Audit

Date: 2026-05-23

Scope: read-only audit of Telegram notification routing, cooldown behavior, async sender health, fail-soft handling, event triggers, and structured route/ack visibility.

Runtime behavior changed: No
Live behavior changed: No

## Verdict

Classification: TELEGRAM_ROUTE_TELEMETRY_GAP

Telegram is not proven broken from the inspected evidence. The stronger finding is that Telegram delivery health is not observable enough to distinguish clean silence from suppressed, unavailable, or failed delivery.

Recent 2026-05-23 logs show Telegram config warnings, but no Telegram send-failure tracebacks or `telegram_degraded` structured events. Runtime JSONL files for system health, execution log, trade journal, and decision log contain no Telegram route, suppression, send, or ack records.

## Files Inspected

- `utils/logger.py`
- `utils/telegram_alerts.py`
- `utils/telegram_reporter.py`
- `polymarket/trader.py`
- `main.py`
- `daily_report.py`
- `config/settings.py`
- `tests/test_telegram_alerts.py`
- `logs/polytrade_bot_20260523*.log`
- `runtime/quant_data/system_health/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/decision_log/2026-05-23.jsonl`

## Notify Flow

The runtime has three Telegram paths:

1. Startup path:
   - `main.py` gets `get_telegram_notifier()`.
   - If a notifier exists, it sends `build_startup_alert(...)` directly.
   - There is no structured route or delivery acknowledgement.

2. Alert-layer path:
   - `polymarket/trader.py` initializes `TelegramAlertLayer`.
   - `_notify_telegram(...)` calls alert methods for incidents, risk, entry, exit, critical events, and summaries.
   - It emits `telegram_degraded` only when the alert result reason is `send_failed` or when `_notify_telegram` itself raises.

3. Error-log path:
   - `utils/logger.py` attaches `TelegramLogHandler` for `ERROR` and `CRITICAL` logs when token/chat_id are configured.
   - The notifier submits messages asynchronously.

## Cooldown Suppression

Cooldown defaults:

- `telegram_alert_cooldown_seconds`: 300 seconds
- `telegram_summary_interval_minutes`: 60 minutes

Cooldown applies to:

- `notify_risk`
- `notify_critical`
- `notify_incident`
- `notify_summary`

Cooldown does not apply to:

- `notify_entry`
- `notify_exit`
- `notify_startup`

Suppression returns `AlertResult(sent=False, suppressed=True, reason="cooldown")`, but this is not emitted to JSONL. As a result, cooldown volume cannot be audited after the fact.

Finding: cooldown is not too aggressive for entry/exit visibility because those paths are not cooldown-limited. It can suppress repeated risk, critical, incident, and summary alerts for five minutes, but suppression is currently invisible unless a caller explicitly records the returned result.

## Async Sender Health

`TelegramNotifier` uses a single-worker `ThreadPoolExecutor` and a `requests.Session`.

Observed behavior:

- `send_message(...)` returns immediately after submitting work.
- If notifier is closed or missing token/chat_id, it returns without telemetry.
- If executor submission raises `RuntimeError`, it is swallowed.
- `_send_blocking(...)` catches all exceptions and intentionally passes.
- HTTP response success/failure is not recorded.
- No Telegram message id or response body is captured.

Finding: the async worker can fail silently at the actual HTTP send layer. The alert layer can catch only synchronous `send_message(...)` exceptions. Since `send_message(...)` normally schedules background work and returns, most delivery failures are not visible to the alert layer and therefore do not become `telegram_degraded` events.

## Event Trigger Coverage

Telegram triggers exist for:

- Startup alert
- Position reconciliation incident
- Floor breach / balance guard risk alert
- Entry alert
- Exit alert
- Critical close/reduce failure
- Panic sell
- Stop loss
- Auto-redeem
- Take-profit full/partial
- Settlement
- Loss-cluster and drawdown risk alerts
- Daily report helper

Potential quiet zones:

- Routine decision skips do not route to Telegram.
- No-entry and low-signal behavior is primarily observability/research evidence, not Telegram output.
- Market-analysis exceptions are not proven to have route/ack telemetry unless they pass through the existing incident path.

Finding: Telegram may be quiet because no Telegram-worthy event fired, but the current telemetry cannot prove that. It also cannot prove that events fired and were successfully delivered.

## Runtime Evidence

Log scan:

- 2026-05-23 logs contain repeated config warning text:
  - `TELEGRAM_ENABLED missing; Telegram will enable only when token/chat_id are configured`
- No inspected log showed `telegram alert send failed`.
- No inspected log showed Telegram HTTP delivery acknowledgement.

JSONL scan:

- `runtime/quant_data/system_health/2026-05-23.jsonl`: no Telegram route/ack/suppression records found.
- `runtime/quant_data/execution_log/2026-05-23.jsonl`: no Telegram route/ack/suppression records found.
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`: no Telegram route/ack/suppression records found.
- `runtime/quant_data/decision_log/2026-05-23.jsonl`: no Telegram route/ack/suppression records found.

Interpretation: current evidence supports "route telemetry missing" more strongly than "Telegram broken."

## Required Answers

1. Telegram broken?

Not proven. The code has routing paths and tests for cooldown/fail-soft alert-layer behavior. However, actual HTTP delivery health is not observable because async send failures are swallowed and successful sends are not acknowledged in structured telemetry.

2. Telegram quiet because no events?

Possibly, but unproven. Runtime has explicit entry/exit/risk/critical/incident triggers, while routine skips do not alert. Without route-attempt telemetry, there is no durable way to distinguish "no alert-worthy event" from "event fired but notifier unavailable/suppressed/failed."

3. Cooldown too aggressive?

Not for entry/exit/startup. Those are not cooldown-limited. Risk, critical, incident, and summary alerts are cooldown-limited by default, and repeated alerts may be suppressed for 300 seconds. The issue is less the cooldown value and more the absence of suppression counters or JSONL records.

4. Async worker failing silently?

Possible and currently invisible. `_send_blocking(...)` catches all exceptions and does not log or emit telemetry. This is safe for the trading loop but weak for operations visibility.

5. Missing JSONL route/ack telemetry?

Yes. This is the primary gap. There is no structured event for attempted route, notifier unavailable, cooldown suppression, HTTP send success, HTTP send failure, or async worker exception.

## Minimal Future Fix Plan

No code was changed for this audit. If scoped later, the minimal observability-only fix would be:

1. Add structured Telegram route telemetry:
   - `telegram_route_attempt`
   - `telegram_route_suppressed`
   - `telegram_notifier_unavailable`
   - `telegram_send_ack`
   - `telegram_send_failed`

2. Preserve fail-soft behavior:
   - Never block trading on Telegram.
   - Keep ERROR/CRITICAL visible.
   - Do not raise from Telegram paths into trading logic.

3. Record async worker results without blocking:
   - Attach a callback to the submitted future.
   - Emit/log failure reason and HTTP status when available.
   - Avoid message body or secret leakage.

4. Add a session-level Telegram health summary:
   - attempts
   - sent/ack count
   - suppressed count
   - unavailable count
   - failed count
   - last success timestamp
   - last failure reason

## Final Classification

Telegram delivery is unverified, not confirmed broken.

The current problem is an observability blind spot:

- Alert routes exist.
- Cooldowns are intentional.
- Fail-soft behavior is intentional.
- Async HTTP failures are swallowed.
- Structured route/ack telemetry is missing.

Recommended status: COLLECT_TELEGRAM_ROUTE_TELEMETRY_BEFORE_CLAIMING_HEALTHY

Tests: not run; docs-only read-only audit.

