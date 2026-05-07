# PolyTrade Bot / Polymarket 5M Binary BTC-ETH Quant Scalper - Current Project Status

> Updated: 2026-05-07
> Purpose: Single source of truth for future AI assistants and project work.
> Important: This project is not confirmed live-trading ready. Do not claim live readiness until orderbook, wallet sync, execution, fill/cancel, allowance, and reconciliation are all proven in terminal/runtime evidence.

---

## 1. Current Project Identity

This repository is the **PolyTrade Bot / Polymarket 5M Binary BTC-ETH Quant Scalper**.

It is a Python trading bot for Polymarket 5-minute BTC/ETH binary prediction markets. The system is intended to run paper-first, validate real market data and risk behavior, then move toward live execution only after the missing live-risk pieces are verified.

Do not treat this repo as a new project. Do not recommend rebuilding from scratch. The project already has a working terminal UI, market scanner, price/oracle feed path, cycle loop, paper mode, and multiple strategy/risk modules. Current work should focus on validating and completing the existing runtime path.

Canonical safe paper command:

```bash
python main.py
```

Explicit paper command:

```bash
python main.py --mode paper --interval 60
```

Live runtime requires explicit operator intent:

```bash
python main.py --mode live --interval 60
```

Live mode is still blocked by readiness checks while allowance/execution validation is incomplete. Always inspect `.env` and `config/settings.py` before live-risk work.

---

## 2. What Works Now

The following parts are currently working or present in the project:

- Terminal UI works.
- BTC/ETH 5-minute market scanner works.
- Binance/price oracle feed works.
- WebSocket status shows `Synced`.
- Cycle loop works.
- Paper mode exists.
- Paper mode is now the default runtime unless `--mode live` is explicitly passed.
- Paper mode uses real Polymarket market data/orderbooks but simulates orders and fills locally.
- Paper mode never connects to live wallet balance, never requires allowance, and never sends live orders.
- Market window timing works.
- Portfolio panel displays values.
- AI cycle panel displays decisions.
- Live orderbook read path now returns fresh BTC/ETH 5-minute `BID`, `ASK`, and `SPREAD` values through the trader/display metrics path.
- Wallet/portfolio source is now explicit:
  - Paper mode uses virtual paper capital only.
  - Live mode refreshes terminal portfolio cash/equity from live CLOB collateral balance.
  - Terminal portfolio includes `balance_source` so operators can see whether values are paper virtual or live wallet/CLOB sourced.

Strategy and risk modules exist:

- Counter-Momentum.
- Markov Bounds.
- Kelly Sizing.
- Micro-Grinder mode.
- ExitAgent protection.
- Risk floor.

These working parts are meaningful. Future assistants should build on them instead of replacing the architecture.

---

## 3. What Is Not Working Yet

The bot is not fully validated for live trading.

Current known gaps:

- Execution is not validated.
- No confirmed live order placement has been proven.
- No confirmed fill/cancel/reconcile cycle has been proven.
- Live account allowance is not ready in current verification evidence.
- Live runtime is not the default and must not be started except with explicit `--mode live`.

Orderbook status:

- The previous `no_orderbook` blocker was fixed in code on 2026-05-07.
- `python main.py --mode verify` reported BTC and ETH `orderbook=OK` with live `BID`, `ASK`, and `SPREAD`.
- The same `PolymarketTrader.get_market_display_metrics()` path feeding the realtime terminal returned live BTC/ETH YES/NO orderbook values.
- Continue monitoring the full realtime UI, but do not restart/rebuild the orderbook architecture unless fresh evidence shows it regressed.

Wallet/portfolio status:

- The previous wallet/portfolio source ambiguity was fixed in code on 2026-05-07.
- In paper mode, the terminal remains virtual and must not fetch live balances.
- Paper mode uses virtual starting balance, simulated cash/equity/exposure/PnL, and `balance_source=paper_virtual`.
- In live mode, `dashboard_portfolio_state()` refreshes from the live CLOB collateral balance after connection.
- In live mode, `Start`, `Cash`, and `Equity` are aligned to the live wallet/CLOB balance at session startup instead of the paper/config seed.
- `python main.py --mode verify` reported balance source `clob_collateral` with cash/equity/sizing matching.
- The same verify run still reported `missing_allowance`, so do not describe the bot as live-ready.

---

## 4. Current Terminal Evidence

Observed terminal evidence:

- Terminal UI renders.
- BTC/ETH scanner panels render.
- Price/oracle feed updates.
- WebSocket status shows `Synced`.
- Cycle loop continues running.
- AI cycle panel shows decisions.
- Portfolio panel shows `Start`, `Cash`, and `Equity` values.
- Portfolio panel now carries a `Source` value, such as `paper_virtual` or `clob_collateral`.
- Paper runtime prints a clear `PAPER MODE` banner showing real market data on, live orders off, simulated execution on, and wallet risk none.
- Read-only verify mode showed live BTC/ETH orderbooks with non-empty `BID`, `ASK`, and `SPREAD`.
- Example verification status: BTC `orderbook=OK`, ETH `orderbook=OK`.
- Read-only verify mode logged `[WALLET CONNECTED]`, `[USDC BALANCE]`, `[VERIFY BALANCE]`, and `[LIVE MODE READY]`.
- Latest verify evidence showed wallet balance source `clob_collateral`, balance status `MATCH`, zero positions, and `[LIVE MODE READY] ready=False` because `missing_allowance` remains.
- Paper validation run on 2026-05-07 used real BTC/ETH 5-minute markets and live CLOB orderbooks with `balance_source=paper_virtual`.
- The paper session summary reported `cycles_scanned=6`, `total_markets_scanned=12`, `total_opportunities_found=3`, `paper_orders_created=0`, `paper_fills=0`, `paper_exits=0`, `simulated_pnl=0.0`, and `max_drawdown=0.0`.
- Top paper skip reasons in that run were `confidence_too_low` (4), `Risk plan returned zero position size -- skipping.` (3), entry cutoff near market close (4 total), and `ev_below_threshold` (1).
- The strategy/orderbook path moved beyond the old `no_orderbook` failure: live orderbook EV evaluation produced an EV-level `decision=ENTER` candidate, but the risk/sizing layer blocked it with zero size. This indicates the observed no-trade result was caused by current risk/strategy thresholds and tiny bankroll sizing, not missing orderbook data.

Interpretation:

- Market discovery, timing, and feed plumbing are partly operational.
- The bot is cycling and can now read fresh live CLOB orderbooks for active BTC/ETH 5-minute markets.
- Portfolio values are now source-labeled. In live mode they are wired to CLOB collateral balance; in paper mode they stay virtual.
- Paper mode is operating safely with real market data and isolated virtual capital. A short validation session did not naturally create paper orders/fills/exits because risk/strategy gates blocked all entries.

Do not over-interpret the UI panels. Visible portfolio numbers are only meaningful when the displayed/logged source is checked. `clob_collateral` means live CLOB balance; `paper_virtual` means simulated paper capital.

---

## 5. Architecture Status

Primary runtime path:

```text
main.py
  -> polymarket realtime mode
  -> polymarket/trader.py
  -> market discovery / scanner
  -> Binance and oracle price feed
  -> signal modules
  -> risk and order planning
  -> terminal display and logging
```

Important project areas:

- `main.py` - CLI dispatcher and realtime loop orchestration.
- `config/settings.py` - environment settings, live/paper flags, validation.
- `polymarket/trader.py` - main Polymarket trading coordinator.
- `polymarket/client.py` - CLOB authentication, balances, orders, redemption helpers.
- `polymarket/gamma_fetcher.py` - market/event/token discovery.
- `polymarket/market_feed.py` - Binance feed singleton.
- `polymarket/oracle_price_feed.py` - oracle/PTB price path.
- `polymarket/virtual_ptb.py` - virtual price-to-beat tracker.
- `polymarket/signal.py` - realtime signal logic.
- `polymarket/backtester_5m.py` - backtest signal/performance path.
- `polymarket/order_manager.py` - converts signal/risk inputs into order risk plans.
- `polymarket/realtime_logger.py` - scan/trade logging.
- `utils/risk_manager.py` - canonical Polymarket risk policy.
- `utils/position_tracker.py` - position and drawdown state.
- `utils/display.py` - terminal display.
- `utils/telegram_reporter.py` - Telegram alerts and reports.

Secondary or experimental paths:

- `hft_paper_run.py` - active HFT paper simulation utility.
- `main.py --mode hft` and `hft/` - experimental HFT engine; paper-first only.
- `crypto_scalper/` - separate crypto scalper path.
- `dashboard/` and `web-dashboard/` - overlapping dashboards retained until a dedicated consolidation task.
- `polymarket/five_min_monitor.py` - standalone monitor.

Current architecture should be repaired and verified in place. Do not replace it with a new bot unless the user explicitly requests a rebuild.

Default runtime behavior:

```text
python main.py
  -> paper mode
  -> real market scanner/orderbooks
  -> local simulated execution only
  -> no wallet collateral or live order APIs

python main.py --mode live
  -> live readiness preflight
  -> blocked if allowance/execution readiness is not proven
```

---

## 6. Active Blockers

### 1. no_orderbook - fixed, monitor for regression

Previous symptoms:

- `BID`, `ASK`, and `SPREAD` are empty.
- Decision shows `SKIP no_orderbook`.
- Strategy cannot calculate real EV from live orderbook yet.

Current outcome:

- Terminal displays real `BID`, `ASK`, and `SPREAD` for active BTC/ETH 5-minute markets.
- Signal/risk path consumes the same orderbook values displayed in terminal.
- Orderbook reads retry temporary empty responses and reject stale books older than 3 seconds.
- Logs include market slug, condition ID, YES/NO token IDs, compact orderbook response, and best bid/ask.

Remaining caution:

- If `SKIP no_orderbook` reappears, first inspect fresh logs for stale or empty orderbook responses before changing strategy modules.

### 2. Wallet/Portfolio Sync - fixed, monitor for regression

Previous symptoms:

- Terminal shows `Start`, `Cash`, and `Equity`.
- It was not verified whether these values came from real wallet balance, paper seed, runtime state, or hardcoded config.

Current outcome:

- In paper mode, terminal clearly uses paper capital/state.
- In live mode, terminal `Start`, `Cash`, `Equity`, and sizing state connect to the live CLOB collateral balance.
- Logs include wallet address, balance source, cash/equity, exposure, and positions count.
- Startup/verify logs include `[WALLET CONNECTED]`, `[USDC BALANCE]`, and `[LIVE MODE READY]`.

Remaining caution:

- Current runtime `.env` still has `PAPER_TRADING=true` and `DRY_RUN=true`.
- Verify mode currently reports `missing_allowance`, so live mode is not ready for execution.
- Future assistants must still inspect `.env`, `config/settings.py`, and wallet/client code before making claims about balance sync.

### 3. Live Allowance / Execution Not Yet Validated

Symptoms:

- Verify mode reports `missing_allowance`.
- No confirmed live order placement.
- No confirmed fill/cancel/reconcile cycle.

Required outcome:

- A tiny controlled live-order validation plan exists before any live-risk execution.
- Order placement, fill detection, cancellation, and reconciliation are proven end to end.
- Logs and terminal output confirm exactly what happened.

### 4. Safe Paper Runtime - active default

Current outcome:

- `--mode` is no longer required; no argument defaults to safe paper mode.
- Legacy `--mode polymarket-realtime` and `--mode polymarket-paper` route to paper mode.
- Live runtime requires explicit `--mode live`.
- Paper order APIs are blocked from calling live CLOB order placement directly.
- Paper logs include `[PAPER ORDER]`, `[PAPER FILL]`, `[PAPER EXIT]`, and `[PAPER PNL]`.
- Paper session summary logs include cycles scanned, markets scanned, opportunities found, paper orders, fills, exits, PnL, max drawdown, and top skip reasons.

Latest paper validation:

- A real-data BTC/ETH paper run completed without touching live order APIs.
- Fresh BTC/ETH YES/NO orderbooks were visible in logs with bid/ask/spread and age under 3 seconds.
- The run found opportunities, including one EV-level `ENTER`, but all entries were blocked before execution by entry cutoff, low confidence, low EV, or zero-size risk planning.
- Result: no paper orders/fills/exits occurred in that short session; simulated cash/equity stayed at `$8.70`, exposure stayed `$0.00`, PnL stayed `0.0`.

---

## 7. Do Not Rebuild Rules

- Do not tell the user to rebuild the bot from scratch.
- Do not replace the terminal UI, scanner, feed, strategy, or risk modules unless the user explicitly asks.
- Do not delete runtime logs, trade logs, scan logs, backtest results, config files, wallet helpers, or research records.
- Do not rewrite strategy logic during cleanup or documentation tasks.
- Do not bypass floor balance, single-trade cap, daily drawdown, reconciliation, or unknown-state guards.
- Do not claim live trading is ready without verified orderbook, wallet, execution, fill/cancel, and reconciliation evidence.
- Do not switch the default runtime away from paper mode.
- Do not route legacy realtime commands to live order execution.
- Do not call live order, cancel, redeem, signing, allowance, or wallet collateral paths from paper runtime.
- Do not claim orderbook works until `BID`, `ASK`, and `SPREAD` are visible in terminal.
- Do not claim wallet balance is synced unless the terminal reads real wallet balance.
- Do not promote HFT/live behavior from paper results alone.

If `.env` has `PAPER_TRADING=false` or `DRY_RUN=false`, treat the repo as live-risk until proven otherwise.

---

## 8. Next Priority Tasks

1. Continue longer safe paper sessions with live market data.
   - Use `python main.py` or `python main.py --mode paper --interval 60`.
   - Confirm the paper banner is visible.
   - Confirm terminal `Source paper_virtual`.
   - Confirm real `BID`, `ASK`, and `SPREAD` remain visible.
   - Watch whether natural market conditions create `[PAPER ORDER]`, `[PAPER FILL]`, `[PAPER EXIT]`, and `[PAPER PNL]` events without loosening risk rules.
   - If sessions keep skipping, compare top skip reasons before changing any strategy or risk thresholds.

2. Resolve live account allowance.
   - Confirm collateral allowance source and required approval path.
   - Do not bypass allowance checks.
   - Keep `[LIVE MODE READY] ready=False` until balance, floor, allowance, and verification checks pass.

3. Validate execution safely after allowance is fixed.
   - Confirm order creation code path.
   - Confirm cancel path.
   - Confirm fill detection.
   - Confirm position reconciliation.
   - Use paper mode or a tiny controlled live test only after explicit user approval.

4. Monitor orderbook regression.
   - Confirm full realtime terminal continues showing non-empty `BID`, `ASK`, and `SPREAD`.
   - If books are stale or empty, inspect `[TOKEN_FLOW]`, `[ORDERBOOK_FLOW]`, `[ORDERBOOK_RESPONSE]`, and `[ORDERBOOK_BEST]` logs.

5. Monitor portfolio regression.
   - Confirm paper mode keeps `Source paper_virtual`.
   - Confirm live mode keeps `Source clob_collateral`.
   - Confirm `[PORTFOLIO_SYNC]` logs cash/equity/exposure/positions count.

6. Keep docs aligned.
   - Update this file when terminal evidence changes.
   - Update `docs/PROJECT_STRUCTURE.md` when main path or data flow changes.
   - Update `docs/PROJECT_CLEANUP_REPORT.md` for cleanup decisions.
   - Update `README.md` only for user-facing command/path changes.

---

## 9. Codex Working Instructions

Before modifying code:

1. Read `CURRENT_PROJECT_STATUS.md`.
2. Read the latest real daily note in `research/daily/YYYY-MM-DD.md`.
3. Read `docs/PROJECT_STRUCTURE.md`.
4. Read `docs/PROJECT_CLEANUP_REPORT.md` if the task touches structure or cleanup.
5. Inspect `.env` and `config/settings.py` before any live-risk work.

Testing guidance:

```bash
# Full test suite
python -m pytest tests/ -q

# Import smoke
python -c "from polymarket.backtester_5m import PolymarketBacktester5m; print('OK')"

# Strategy smoke when strategy or import paths changed
python main.py --mode polymarket-backtest --days 3 --asset BTC

# Safe default paper loop
python main.py

# Explicit paper loop
python main.py --mode paper --interval 60

# Explicit live loop; readiness preflight must pass first
python main.py --mode live --interval 60
```

Run the strategy smoke only when strategy or import paths changed.

Any signal change must update both:

- `polymarket/signal.py`
- `polymarket/backtester_5m.py`

Any signal change requires a backtest before promotion.

---

## 10. Definition of Done

The project can only be described as live-trading ready when all of the following are true:

- Terminal shows active BTC/ETH 5-minute market windows.
- Terminal shows real `BID`, `ASK`, and `SPREAD`.
- Strategy calculates EV from the live orderbook data path.
- `SKIP no_orderbook` is resolved for valid active markets.
- Paper mode is clearly separated from live mode.
- Paper mode is the default runtime.
- Paper mode uses real market data and local simulated execution only.
- Live mode portfolio reads actual wallet balance.
- Live account allowance is confirmed ready.
- Order placement is confirmed.
- Cancel path is confirmed.
- Fill detection is confirmed.
- Position reconciliation is confirmed.
- Risk floor, single-trade cap, daily drawdown, and unknown-state guards remain active.
- Logs and terminal output provide evidence for every live-risk claim.

Until then, describe the bot as an active, partially working Polymarket 5-minute scalper with important live-readiness blockers, not as fully live-trading ready.
