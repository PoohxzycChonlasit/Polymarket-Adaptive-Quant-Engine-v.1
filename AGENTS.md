# PolyTrade Crypto Scalper - Codex Instructions

This file is auto-loaded for future AI sessions. Keep it current and safety-focused.

## Project Goal

Build and operate a Python trading bot for Polymarket BTC/ETH 5-minute binary prediction markets, with paper-first validation and strict risk controls before any live execution.

Use `docs/quant_agent_setup_md/` as the operating system for AI work on this repo.

Primary references:

- `CURRENT_PROJECT_STATUS.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/PROJECT_CLEANUP_REPORT.md`
- latest real daily note in `research/daily/`
- `research/OVERVIEW.md` for historical strategy context

## Session Startup

When starting work, read these first:

1. `CURRENT_PROJECT_STATUS.md`
2. latest real file in `research/daily/YYYY-MM-DD.md`
3. `docs/PROJECT_STRUCTURE.md`
4. `docs/PROJECT_CLEANUP_REPORT.md` if the task touches structure or cleanup

Run a smoke test only when strategy or import paths changed:

```bash
python main.py --mode polymarket-backtest --days 3 --asset BTC
```

## Canonical Runtime Path

Main Polymarket paper/live loop:

```bash
python main.py --mode polymarket-realtime --interval 60
```

The command name is not enough to guarantee paper mode. Always inspect `.env` and `config/settings.py` before live-risk work.

## Active Files

| File | Purpose |
|------|---------|
| `main.py` | CLI dispatcher and realtime loop orchestration. |
| `config/settings.py` | Environment settings and validation. |
| `polymarket/trader.py` | Main Polymarket trading coordinator. |
| `polymarket/client.py` | CLOB auth, balances, orders, redemption helpers. |
| `polymarket/gamma_fetcher.py` | Market/event/token discovery. |
| `polymarket/market_feed.py` | Binance feed singleton. |
| `polymarket/oracle_price_feed.py` | Oracle/PTB price path used by trader. |
| `polymarket/virtual_ptb.py` | Virtual price-to-beat tracker. |
| `polymarket/signal.py` | Realtime signal logic. |
| `polymarket/backtester_5m.py` | Backtest signal/performance path. |
| `polymarket/order_manager.py` | Converts signal/risk inputs into order risk plans. |
| `polymarket/realtime_logger.py` | Scan/trade logging. |
| `utils/risk_manager.py` | Canonical Polymarket risk policy. |
| `utils/position_tracker.py` | Position and drawdown state. |
| `utils/display.py` | Terminal display. |
| `utils/telegram_reporter.py` | Telegram alerts and reports. |

## Secondary Or Experimental Paths

Keep these, but do not treat them as canonical live Polymarket execution:

- `hft_paper_run.py` - active HFT paper simulation utility.
- `main.py --mode hft` and `hft/` - experimental HFT engine; paper-first only.
- `crypto_scalper/` - separate crypto scalper path.
- `dashboard/` and `web-dashboard/` - overlapping dashboards; keep until a dedicated consolidation task.
- `polymarket/five_min_monitor.py` - standalone monitor.

## Files And Data Not To Touch Casually

Do not delete, rewrite, or archive these in cleanup tasks:

- `.env`
- `.env.example`
- `config/`
- `runtime/`
- `logs/`
- `logs_vps/`
- `backtest_results/`
- trade logs and scan logs
- wallet/API credential helpers
- strategy research records

Do not edit private keys, wallet addresses, or live flags unless the user explicitly asks and understands the live-risk impact.

## Safety Rules

- Do not change trading strategy logic during cleanup tasks.
- Any signal change must update both `polymarket/signal.py` and `polymarket/backtester_5m.py`.
- Any signal change requires a backtest before promotion.
- Risk and exit safety outrank new strategy ideas.
- Keep `utils/risk_manager.py` canonical for Polymarket risk.
- Keep `hft/risk_manager.py` scoped to HFT unless a dedicated unification task is opened.
- Never bypass floor balance, single-trade cap, or daily drawdown checks.
- Never promote HFT/live behavior from paper results alone.
- If `.env` has `PAPER_TRADING=false` or `DRY_RUN=false`, treat the repo as live-risk until proven otherwise.

## Cleanup Rules

- Do not delete files immediately.
- Move clearly unused or stale files to `archive/legacy/` first.
- Do not move runtime logs, trade logs, backtest results, or config files unless clearly duplicated and safe.
- Keep imports working after any move.
- Update `docs/PROJECT_CLEANUP_REPORT.md` for cleanup decisions.
- Update `docs/PROJECT_STRUCTURE.md` when the main path or data flow changes.
- Update `README.md` only for user-facing command/path changes.

## Testing Commands

```bash
# Full test suite
python -m pytest tests/ -q

# Import smoke
python -c "from polymarket.backtester_5m import PolymarketBacktester5m; print('OK')"

# Strategy smoke when strategy/import paths changed
python main.py --mode polymarket-backtest --days 3 --asset BTC

# Main loop; verify .env first
python main.py --mode polymarket-realtime --interval 60
```

## Known Manual Review Items

- Confirm paper/live flags before any operation.
- Review recent live order failures where `NO` entries appear to route through a `SELL` path without inventory.
- Resolve drift between `README.md`, `CURRENT_PROJECT_STATUS.md`, and older research docs about the active strategy.
- Review `CLAUDE.md`, `research/FOR_OTHER_AI.md`, `PROJECT_RULES.md`, and `ROADMAP.md` before archiving or rewriting.
