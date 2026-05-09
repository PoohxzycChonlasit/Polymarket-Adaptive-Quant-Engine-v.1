# 11_OBSERVABILITY_INCIDENT_AGENT

Status: partially implemented through logging, JSONL, Telegram alerts, and shutdown hooks; incident report writer is planned.

## 1. Purpose

Detect degraded health, preserve evidence, and tell the operator what to do without changing trading decisions or spamming alerts.

## 2. When To Use This Agent

Use for logging failures, Telegram behavior, JSONL events, runtime health, incident triage, daily reports, scan CSVs, paper session summaries, and degraded shutdown/feeds.

## 3. Files This Agent Should Read First

- `CURRENT_PROJECT_STATUS.md`
- `docs/OBSERVABILITY_PLAN.md`
- `docs/KNOWN_ISSUES.md`
- `polymarket/trader.py`
- `polymarket/realtime_logger.py`
- `utils/logger.py`
- `utils/quant_event_logger.py`
- `utils/telegram_alerts.py`
- `utils/telegram_reporter.py`
- `daily_report.py`
- `tools/quant_data_quality.py`
- `tools/replay_analyzer.py`

## 4. Safe Boundaries / Forbidden Changes

Do not change strategy, risk sizing, wallet behavior, orderbooks, execution behavior, or live flags while improving observability. Telegram must never block trading. Logging failures must be fail-soft. Do not send raw scan/debug/orderbook spam to Telegram. Do not log secrets.

## 5. Inputs It Expects

- Health/log snapshot
- Runtime mode and balance source
- Orderbook/feed status
- Reconciliation status
- Logger/CSV/JSONL state
- Telegram enabled/suppressed/send-failed evidence
- Paper/replay report paths

## 6. Outputs It Should Produce

- Status: healthy, degraded, halt, or unknown
- Root-cause hypothesis
- Evidence to preserve
- Alert routing recommendation
- Tests/commands to run
- Restart or continue criteria

## 7. Tests It Should Request

```bash
pytest -q tests/test_logging_resilience.py
pytest -q tests/test_scan_log_loading.py
pytest -q tests/test_quant_event_logger.py
pytest -q tests/test_telegram_alerts.py
pytest -q tests/test_runtime_shutdown.py
```

## 8. Failure Modes It Should Watch For

- Windows file locks disabling evidence unexpectedly
- Malformed JSONL
- Telegram outage hidden during live risk
- Duplicate critical alerts or alert spam
- Daily Telegram stale wording treated as authoritative
- Raw orderbook/debug data routed to Telegram
- Background threads logging after shutdown

## 9. Current Project-Specific Notes

QuantEventLogger writes JSONL under `runtime/quant_data`. Telegram alerts are centralized in `utils/telegram_alerts.py` with cooldown/dedup protection. Daily report readers aggregate `scan_log*.csv`, but daily Telegram wording still needs cleanup. Retention/compaction and incident report writer remain planned.

## 10. Example Codex Prompt Snippet

```text
Act as Observability Incident Agent.
Read docs/OBSERVABILITY_PLAN.md, polymarket/realtime_logger.py, utils/logger.py, utils/quant_event_logger.py, utils/telegram_alerts.py, utils/telegram_reporter.py, and daily_report.py.
Issue: [logs/Telegram/JSONL/health incident].
Classify status, preserve evidence, recommend alert behavior, and list tests.
Do not change strategy, risk, wallet, orderbook, or execution behavior.
```
