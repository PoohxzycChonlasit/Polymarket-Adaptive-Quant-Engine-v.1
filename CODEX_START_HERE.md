# CODEX_START_HERE — Minimal Context

Project: Polymarket 5M Quant Scalper.

Before modifying code, read CURRENT_PROJECT_STATUS.md and do not assume the project is new or needs rebuilding.

Main command, safe paper default:
```bash
python main.py
```

Explicit paper command:
```bash
python main.py --mode paper --interval 60
```

Live command requires explicit operator intent and readiness preflight:
```bash
python main.py --mode live --interval 60
```

Current safety rules that must not be removed:
- Paper mode is the default unless `--mode live` is explicitly passed.
- Paper mode uses real market data/orderbooks but simulated execution only.
- Paper mode must not touch wallet collateral, require allowance, sign orders, or send live orders.
- Reconcile positions before every trading cycle.
- Block trading on mismatch, partial hedge, or unknown state.
- No new entries when time remaining <= 90s.
- Force-exit logic remains for time remaining <= 60s.
- Exit by selling the token actually held.
- NO entries must buy NO tokens, not sell YES.
- arb_auto_execute must remain false by default.
- No martingale, no averaging down by default, no all-in, no fixed 20% live risk.

Token budget rules for Codex:
- Open only files directly needed for the current task.
- Do not scan .venv, backtest_results, runtime, archive, or docs unless requested.
- Do not refactor unrelated files.
- Do not rewrite unchanged files.
- Make the smallest safe change and run targeted tests first.

Important code areas:
- Live entry/trading path: main.py, polymarket/trader.py, polymarket/order_manager.py
- Risk/sizing: polymarket/bankroll_tiers.py, polymarket/position_sizing.py, config/settings.py
- Arbitrage: polymarket/arbitrage.py, polymarket/arbitrage_executor.py
- Reconciliation/positions: utils/position_tracker.py, tests/test_position_reconciliation.py
- Tests: tests/
