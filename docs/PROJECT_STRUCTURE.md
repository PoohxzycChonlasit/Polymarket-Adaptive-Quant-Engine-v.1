# Project Structure

This document describes the current working path of the Polymarket BTC/ETH 5-minute bot without changing strategy or execution logic.

## Main Path

The canonical safe paper runtime path is:

```bash
python main.py
```

Explicit paper runtime:

```bash
python main.py --mode paper --interval 60
```

Explicit live runtime:

```bash
python main.py --mode live --interval 60
```

Paper mode is the default. Legacy `--mode polymarket-realtime` and `--mode polymarket-paper` route to safe paper mode. Live runtime requires explicit `--mode live` and a passing readiness preflight.

Runtime safety still depends on `.env` and `config/settings.py`, especially:

- `PAPER_TRADING`
- `DRY_RUN`
- wallet/API variables
- balance and risk settings

Before live operation, always confirm `.env` explicitly.

## Startup Flow

1. `main.py` builds the CLI parser.
2. Default mode, `--mode paper`, `--mode polymarket-paper`, or legacy `--mode polymarket-realtime` enters the paper realtime runner.
3. Settings load from `config/settings.py` and `.env`.
4. The runtime creates `PolymarketTrader`, `RealtimeLogger`, and the terminal display.
5. The loop runs at the requested interval.
6. Each cycle calls the trader, logs scan/trade state, settles expired positions, checks exits, and writes status.

## Main Trading Loop

```text
main.py
  -> PolymarketTrader.run_single_cycle()
     -> load active market
     -> load price/market data
     -> compute signal
     -> build risk plan
     -> submit paper/live order if allowed
     -> update open positions
  -> settle expired positions
  -> check panic/take-profit/stop-loss exits
  -> update runtime status and logs
```

## Market Data Flow

```text
Binance/Coinbase price feeds
  -> polymarket/market_feed.py
  -> polymarket/oracle_price_feed.py
  -> polymarket/virtual_ptb.py

Polymarket Gamma API
  -> polymarket/gamma_fetcher.py
  -> active market, event, token IDs, prices

Polymarket CLOB
  -> polymarket/client.py
  -> balances, allowances, order placement, redemption helpers
```

The realtime trader combines market metadata, token IDs, spot price, price-to-beat, and orderbook/price information before evaluating a trade.

## Signal Flow

```text
market snapshot
  -> polymarket/signal.py
  -> side / confidence / edge
  -> polymarket/order_manager.py
```

Backtest signal behavior lives in `polymarket/backtester_5m.py`.

Do not change realtime signal logic without updating the matching backtest path and running the required backtest. Cleanup tasks must not modify signal behavior.

## Risk Flow

Canonical Polymarket risk policy is split between hard account safety and rank-based sizing:

- `utils/risk_manager.py` keeps hard safety helpers such as the floor balance and drawdown state.
- `polymarket/bankroll_tiers.py` defines the bankroll ranks and smooth base-risk interpolation.
- `polymarket/position_sizing.py` applies the Bankroll Rank Engine multipliers and block conditions.

```text
PolymarketTrader
  -> polymarket/position_sizing.py
  -> polymarket/order_manager.py
  -> RiskPlan
```

Important safety constraints:

- Stop trading below `FLOOR_BALANCE`.
- Respect tier-based single-trade sizing; do not use fixed 20% bankroll risk.
- Respect daily drawdown checks.
- Reduce sizing when drawdown, spread, liquidity, confidence, EV, delta, time-to-settlement, or trade frequency are unfavorable.
- Keep paper mode safe by default.
- Do not bypass `RiskPlan` for live orders.

The HFT path has a separate manager in `hft/risk_manager.py`. Treat it as HFT-only unless a dedicated risk unification task is opened.

## Execution Flow

```text
RiskPlan approved
  -> PolymarketTrader._submit_order()
  -> paper branch OR live branch
```

Paper branch:

```text
default runtime OR settings.paper_trading == True
  -> no CLOB order
  -> synthetic/paper order receipt
  -> trade logged as paper
  -> local cash/equity/exposure/PnL simulation
  -> no wallet collateral or allowance access
```

Live branch:

```text
--mode live only, with readiness preflight passed
  -> settings.paper_trading == False
  -> polymarket/client.py
  -> CLOB API order
  -> order response logged
```

Manual review needed: recent logs suggest `NO` entries can route through a `SELL` order path and fail when the wallet has no inventory. That is an execution-safety issue and should be fixed in a separate task with tests.

## Exit Flow

Exit and protection logic is coordinated by `PolymarketTrader`:

```text
open positions
  -> expired window settlement
  -> panic sell checks
  -> take-profit / stop-loss checks
  -> auto close / redeem path when eligible
```

Position and drawdown state is supported by:

- `utils/position_tracker.py`
- `utils/risk_manager.py`
- `polymarket/realtime_logger.py`
- `utils/telegram_reporter.py`

Risk and exit safety have higher priority than new strategy work.

## Logging Flow

```text
trading cycle
  -> polymarket/realtime_logger.py
  -> logs/
  -> runtime/bot_status.json
  -> daily_report.py
  -> optional Telegram messages
```

Do not delete or archive runtime evidence during cleanup:

- `runtime/`
- `logs/`
- `logs_vps/`
- `backtest_results/`

These folders are used to debug missed trades, rejected orders, balance drift, and strategy performance.

## Paper Mode Vs Live Mode

Paper mode is the default command behavior and is also controlled by settings.

Paper mode:

- `PAPER_TRADING=true`
- should avoid real CLOB order placement
- should still log decisions, exits, and simulated receipts
- is required before live promotion
- uses real Polymarket market data and orderbooks
- simulates fills locally only
- logs `[PAPER ORDER]`, `[PAPER FILL]`, `[PAPER EXIT]`, and `[PAPER PNL]`
- must not require allowance or touch wallet collateral

Live mode:

- `PAPER_TRADING=false`
- must be requested with `--mode live`
- requires valid wallet/API credentials
- requires enough USDC and MATIC
- requires allowance readiness
- requires risk floor and daily drawdown checks to pass
- must not be used while execution-safety findings are unresolved

## Secondary Paths

| Path | Purpose |
|------|---------|
| `hft_paper_run.py` | Standalone HFT paper simulation. |
| `main.py --mode hft` | Experimental HFT engine. |
| `main.py --mode scalper` | Separate crypto scalper path. |
| `dashboard/live_dashboard.py` | Standalone live dashboard. |
| `web-dashboard/` | Separate Next.js dashboard. |
| `polymarket/five_min_monitor.py` | Market monitor without full trade loop ownership. |

## Run Commands

```bash
# Safe paper loop
python main.py

# Explicit paper loop
python main.py --mode paper --interval 60

# Explicit live loop; verify readiness first
python main.py --mode live --interval 60

# Quick backtest smoke
python main.py --mode polymarket-backtest --days 3 --asset BTC

# Full test suite
python -m pytest tests/ -q

# Daily report
python daily_report.py

# Market monitor
python polymarket/five_min_monitor.py --interval 30
```
