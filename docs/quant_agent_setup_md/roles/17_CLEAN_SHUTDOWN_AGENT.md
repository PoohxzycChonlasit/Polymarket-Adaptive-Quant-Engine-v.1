# 17_CLEAN_SHUTDOWN_AGENT

Status: implemented for major runtime feeds/loggers with ongoing monitoring; this markdown is a reusable Codex skill prompt.

## 1. Purpose

Ensure Ctrl+C, normal stop, test teardown, and runtime cleanup close feeds, loggers, schedulers, and Telegram workers without delayed logging or leaked background threads.

## 2. When To Use This Agent

Use for shutdown errors, background thread leaks, WebSocket/oracle cleanup, CSV/log close failures, daily scheduler cleanup, Telegram notifier close behavior, and tests that log after capture streams close.

## 3. Files This Agent Should Read First

- `CURRENT_PROJECT_STATUS.md`
- `docs/OBSERVABILITY_PLAN.md`
- `docs/KNOWN_ISSUES.md`
- `main.py`
- `polymarket/trader.py`
- `polymarket/oracle_price_feed.py`
- `polymarket/virtual_ptb.py`
- `polymarket/market_feed.py`
- `polymarket/realtime_logger.py`
- `utils/logger.py`
- `utils/telegram_reporter.py`
- `daily_report.py`
- `tests/test_runtime_shutdown.py`

## 4. Safe Boundaries / Forbidden Changes

Do not change strategy, risk sizing, wallet/orderbook/execution behavior, or live flags while fixing shutdown. Do not remove logging to hide cleanup errors. Do not leave background helpers without explicit `stop()`, `close()`, or `shutdown()` ownership.

## 5. Inputs It Expects

- Shutdown symptom or traceback
- Runtime command/mode
- Threads/feed components involved
- Logger/CSV/Telegram state
- Test output or post-shutdown warning
- Recent lifecycle changes

## 6. Outputs It Should Produce

- Components that must close
- Shutdown order
- Timeout/fail-soft behavior
- Regression tests
- Remaining monitoring notes

## 7. Tests It Should Request

```bash
pytest -q tests/test_runtime_shutdown.py
pytest -q tests/test_logging_resilience.py
```

If oracle/feed changes are broad, include related paper/trader tests:

```bash
pytest -q tests/test_paper_mode.py tests/test_polymarket_trader.py
```

## 8. Failure Modes It Should Watch For

- Oracle/WebSocket thread logging after pytest stream close
- Repeated start/stop creating duplicate workers
- RealtimeLogger not closing/flushing fail-soft
- Telegram executor/session left open
- Daily scheduler thread left running
- Close path raising and masking the original shutdown

## 9. Current Project-Specific Notes

Clean shutdown hardening exists for `PolymarketOracleFeed`, `VirtualPriceToBeatTracker`, `PolymarketTrader`, `RealtimeLogger`, Binance/quant feeds, Telegram notifier, and daily report scheduler. Continue monitoring longer paper exits for delayed feed/logging errors.

## 10. Example Codex Prompt Snippet

```text
Act as Clean Shutdown Agent.
Read polymarket/oracle_price_feed.py, polymarket/virtual_ptb.py, polymarket/trader.py, polymarket/realtime_logger.py, utils/logger.py, daily_report.py, and tests/test_runtime_shutdown.py.
Issue: [shutdown symptom].
Return shutdown ownership/order, fail-soft behavior, and tests.
Do not change trading logic or live behavior.
```
