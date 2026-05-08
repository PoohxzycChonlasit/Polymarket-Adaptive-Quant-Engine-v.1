# CODEX_START_HERE - Minimal Context

Project: PolyTrade Bot / Polymarket 5M Binary BTC-ETH Quant Scalper.

Before modifying code, read `CURRENT_PROJECT_STATUS.md` and do not assume the project is new or needs rebuilding.

Before implementing any new feature phase, run a documentation sync first if docs are stale or the user requests it.

## Current Runtime Commands

Safe paper default:

```bash
python main.py
```

Explicit paper:

```bash
python main.py --mode paper --interval 60
```

Paper with Terminal UI V2 controls:

```bash
python main.py --mode paper --interval 60 --ui auto --fps medium
```

Read-only verify:

```bash
python main.py --mode verify
```

Explicit live, blocked unless readiness passes:

```bash
python main.py --mode live --interval 60
```

## Read First

1. `CURRENT_PROJECT_STATUS.md`
2. `AGENTS.md`
3. `PROJECT_RULES.md`
4. `docs/PROJECT_STRUCTURE.md`
5. `docs/KNOWN_ISSUES.md`
6. Relevant `docs/quant_agent_setup_md/roles/*.md`

For observability/logging/Telegram tasks, also read:

- `docs/OBSERVABILITY_PLAN.md`
- `polymarket/realtime_logger.py`
- `utils/logger.py`
- `utils/telegram_reporter.py`
- `daily_report.py`

## Current Safety Rules

- Paper mode is the default unless `--mode live` is explicitly passed.
- Paper mode uses real market data/orderbooks but simulated execution only.
- Paper mode must not touch wallet collateral, require allowance, sign orders, send live orders, cancel live orders, or redeem live positions.
- Live mode requires verify preflight and remains blocked while allowance/execution/reconciliation are unproven.
- Reconcile positions before every trading cycle.
- Block new entries on mismatch, partial hedge, unknown state, or LOCKDOWN.
- ENTRY orders must be BUY.
- NO entries must buy NO tokens, not sell YES without inventory.
- EXIT SELL is allowed only for tracked existing inventory.
- No new entries when entry cutoff/risk/reconciliation rules block them.
- Force-exit/panic-exit protections must remain active.
- `arb_auto_execute` must remain false by default.
- No martingale, no averaging down by default, no all-in, no fixed 20% live risk.

## Current Implemented Highlights

- Terminal UI V2 responsive dashboard.
- Paper mode default.
- Real BTC/ETH market/orderbook display path.
- Paper order/fill/exit/PnL simulation.
- Wallet source labeling: paper virtual vs live CLOB collateral.
- OrderIntent guard for ENTRY/EXIT.
- Bankroll rank lock / hysteresis.
- Risk Mode Ladder.
- Windows logging PermissionError resilience.

## Known Gaps

- Live allowance still blocks live readiness.
- No confirmed live order placement/fill/cancel/reconcile cycle.
- Daily report and Telegram daily summary still read fixed `scan_log.csv`, while realtime logging writes per-run `scan_log_<run_id>.csv`.
- Telegram lacks central cooldown/dedup.
- JSONL quant event logging is planned, not implemented.

## Token Budget Rules

- Open only files directly needed for the current task.
- Do not scan `.venv`, `backtest_results`, `runtime`, `archive`, or logs unless requested or needed for evidence.
- Do not refactor unrelated files.
- Do not rewrite unchanged files.
- Make the smallest safe change and run targeted tests first.

## Important Code Areas

- Runtime: `main.py`, `polymarket/trader.py`
- Settings: `config/settings.py`
- Risk/sizing: `utils/risk_manager.py`, `polymarket/bankroll_tiers.py`, `polymarket/position_sizing.py`, `polymarket/risk_modes.py`
- Execution guard: `polymarket/order_intent.py`, `polymarket/order_manager.py`, `polymarket/client.py`
- Reconciliation/positions: `utils/position_tracker.py`, `tests/test_position_reconciliation.py`
- Logging/observability: `utils/logger.py`, `polymarket/realtime_logger.py`, `utils/telegram_reporter.py`, `daily_report.py`
- Terminal UI: `utils/display.py`
- Tests: `tests/`
