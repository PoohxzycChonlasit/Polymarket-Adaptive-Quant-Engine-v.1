# 13_TELEGRAM_ALERT_AGENT

Status: partially implemented in `utils/telegram_alerts.py`, `utils/telegram_reporter.py`, `utils/logger.py`, and trader call sites.

## 1. Purpose

Keep Telegram alerts useful, fail-soft, deduplicated, and low-noise. Alerts should notify operators without blocking trading or flooding them with scan/debug/orderbook raw data.

## 2. When To Use This Agent

Use for Telegram alert routing, cooldown/dedup behavior, daily report wording, startup/trade/exit/risk/critical/incident notifications, and Telegram outage handling.

## 3. Files This Agent Should Read First

- `CURRENT_PROJECT_STATUS.md`
- `docs/OBSERVABILITY_PLAN.md`
- `docs/KNOWN_ISSUES.md`
- `config/settings.py`
- `utils/telegram_alerts.py`
- `utils/telegram_reporter.py`
- `utils/logger.py`
- `daily_report.py`
- `polymarket/trader.py`
- `tests/test_telegram_alerts.py`

## 4. Safe Boundaries / Forbidden Changes

Do not edit `.env` secrets or print tokens/chat IDs. Do not make Telegram blocking. Do not change strategy, risk sizing, wallet/orderbook/execution behavior, or live flags. Do not send raw scan/debug/orderbook spam to Telegram. Do not rely on daily Telegram copy as authoritative until stale wording is cleaned.

## 5. Inputs It Expects

- Alert type and severity
- Message content or context fields
- Dedup key/cooldown expectation
- Telegram enabled/config status
- Runtime mode and market/asset context
- Existing failure/suppression evidence

## 6. Outputs It Should Produce

- Alert route recommendation
- Cooldown/dedup key
- Message wording changes
- Suppression/failure behavior
- Tests to run
- Remaining limitations

## 7. Tests It Should Request

```bash
pytest -q tests/test_telegram_alerts.py
pytest -q tests/test_scan_log_loading.py
pytest -q tests/test_logging_resilience.py
```

For daily report wording/reader changes, include any daily report or reporter tests found with `rg "telegram_reporter|daily_report|scan_log" tests`.

## 8. Failure Modes It Should Watch For

- Duplicate critical alerts inside cooldown
- Missing alert for risk/reconciliation incident
- Alert send exception crashing runtime
- Telegram configured without token/chat ID
- Secrets printed in logs or docs
- High-volume scan/debug/orderbook data sent to Telegram
- Daily message with stale live-ready/backtest wording

## 9. Current Project-Specific Notes

`TelegramAlertLayer` exposes `notify_startup`, `notify_entry`, `notify_exit`, `notify_risk`, `notify_critical`, `notify_summary`, and `notify_incident`. Risk, incident, summary, and repeated critical alerts are cooldown/dedup protected. Telegram sends are asynchronous/fail-soft. Daily Telegram message copy still needs cleanup.

## 10. Example Codex Prompt Snippet

```text
Act as Telegram Alert Agent.
Read utils/telegram_alerts.py, utils/telegram_reporter.py, utils/logger.py, daily_report.py, polymarket/trader.py, and docs/OBSERVABILITY_PLAN.md.
Task: [alert route/copy/cooldown issue].
Return safe message routing, dedup/cooldown behavior, tests, and remaining limitations.
Do not edit secrets or change trading behavior.
```
