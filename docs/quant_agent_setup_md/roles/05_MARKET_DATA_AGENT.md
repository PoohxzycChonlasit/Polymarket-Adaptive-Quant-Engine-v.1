# 05_MARKET_DATA_AGENT

Status: partially implemented in market discovery/orderbook/feed paths; this markdown is a reusable Codex skill prompt.

## 1. Purpose

Verify that BTC/ETH 5-minute Polymarket markets, token IDs, orderbooks, spreads, liquidity, oracle/PTB, and Binance feeds are fresh and usable before signals or orders rely on them.

## 2. When To Use This Agent

Use for `SKIP no_orderbook`, stale books, token mismatch, Gamma discovery, market rollover, orderbook display, oracle/PTB feed issues, or claims that orderbook works.

## 3. Files This Agent Should Read First

- `CURRENT_PROJECT_STATUS.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/KNOWN_ISSUES.md`
- `polymarket/trader.py`
- `polymarket/client.py`
- `polymarket/gamma_fetcher.py`
- `polymarket/market_feed.py`
- `polymarket/oracle_price_feed.py`
- `polymarket/virtual_ptb.py`
- `utils/display.py`
- Relevant verify/orderbook tests

## 4. Safe Boundaries / Forbidden Changes

Do not change strategy thresholds, risk sizing, wallet behavior, execution, live flags, or order submission while fixing market data. Do not claim orderbook works unless terminal/logs show active `BID`, `ASK`, and `SPREAD`. Do not replace the market scanner architecture without a scoped refactor.

## 5. Inputs It Expects

- Market slug, condition ID, YES/NO token IDs
- Best bid/ask/spread/depth
- Orderbook age and response shape
- Oracle/PTB price and feed age
- Market window open/close and seconds left
- Terminal or verify output
- Relevant `[TOKEN_FLOW]`, `[ORDERBOOK_FLOW]`, `[ORDERBOOK_RESPONSE]`, `[ORDERBOOK_BEST]` logs

## 6. Outputs It Should Produce

- Market quality: good, degraded, halt, or unknown
- Data blocker reason
- Normalized snapshot fields
- Whether strategy/risk can evaluate
- Logs/tests needed to prove the fix

## 7. Tests It Should Request

```bash
pytest -q tests/test_verify_mode.py
pytest -q tests/test_polymarket_trader.py
pytest -q tests/test_terminal_dashboard_display.py
```

Use `python main.py --mode verify` only when a read-only integration check is explicitly useful.

## 8. Failure Modes It Should Watch For

- Empty, stale, crossed, or malformed orderbooks
- YES/NO token ID mismatch
- Active market window unknown or rolled over
- Display path not using same orderbook values as signal/risk path
- `SKIP no_orderbook` caused by data regression
- Excess raw scan/debug/orderbook details routed to Telegram

## 9. Current Project-Specific Notes

The old `no_orderbook` blocker is fixed but must be monitored. Current status says verify showed BTC/ETH orderbooks with non-empty `BID`, `ASK`, and `SPREAD`. Market snapshots are logged by QuantEventLogger under `runtime/quant_data/market_snapshots/`. Orderbook/debug raw data should stay in logs/JSONL/CSV, not spam Telegram.

## 10. Example Codex Prompt Snippet

```text
Act as Market Data Agent.
Read polymarket/trader.py, polymarket/client.py, polymarket/gamma_fetcher.py, oracle/feed files, and current status docs.
Issue: [orderbook/feed/token/window problem].
Classify data quality, identify root cause, list exact files to inspect/change, and request tests.
Do not change strategy, risk, wallet, or execution behavior.
```
