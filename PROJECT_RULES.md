# PolyTrade Bot - Project Rules

> Last synced: 2026-05-08.
> These rules describe the current implementation and safety boundaries. They do not certify live readiness.

## 1. Project Identity

- Project: PolyTrade Bot / Polymarket 5M Binary BTC-ETH Quant Scalper.
- Language: Python 3.11+.
- Primary market: Polymarket BTC/ETH 5-minute binary prediction markets.
- Current operating posture: paper-first with real market/orderbook data and simulated execution.
- Live status: blocked until allowance, live order placement, fill/cancel, and reconciliation are proven.

## 2. Canonical Command Rules

Safe default:

```bash
python main.py
```

Explicit paper:

```bash
python main.py --mode paper --interval 60
```

Explicit live:

```bash
python main.py --mode live --interval 60
```

Live must run `verify` preflight first and must remain blocked if readiness fails.

## 3. Architecture Rules

- `main.py` is the top-level CLI dispatcher.
- `polymarket/trader.py` is the canonical Polymarket trade coordinator.
- `utils/risk_manager.py` is the canonical hard risk policy for the Polymarket path.
- `hft/risk_manager.py` is HFT-only unless a dedicated unification task is opened.
- Risk logic must not move into signal logic.
- Exit logic must not be mixed into entry signal generation.
- Position truth must come from tracked inventory and reconciliation, not assumptions.
- Runtime files are generated state, not source of truth.
- No AI/LLM API calls are allowed inside the realtime trading loop.

## 4. Documentation Rules

- Before new feature phases, sync docs if project status has drifted.
- `CURRENT_PROJECT_STATUS.md` is the single source of truth for current bot state.
- `docs/PROJECT_STRUCTURE.md` is the source of truth for runtime/data flow.
- `docs/KNOWN_ISSUES.md` tracks bugs, technical debt, and unfinished systems.
- `docs/OBSERVABILITY_PLAN.md` tracks logging/alerting design and gaps.
- Do not describe planned systems as implemented.
- Clearly label implemented, partially implemented, planned, experimental, and disabled systems.

## 5. Paper Mode Rules

Paper mode must:

- Be the default runtime.
- Use real Polymarket market data.
- Use real BTC/ETH orderbooks.
- Use real spread/liquidity.
- Simulate fills locally.
- Use virtual starting balance only.
- Keep live wallet fully isolated.
- Never send live orders.
- Never sign transactions.
- Never approve allowance.
- Never require allowance.
- Never touch wallet collateral.

Paper mode logs should include:

- `[PAPER ORDER]`
- `[PAPER FILL]`
- `[PAPER EXIT]`
- `[PAPER PNL]`
- paper session summary

## 6. Live Mode Rules

Live mode requires:

- Explicit `--mode live`.
- Passing verify preflight.
- Valid wallet/API credentials.
- Real CLOB collateral balance source.
- Confirmed allowance.
- Risk floor and drawdown checks.
- Clean reconciliation.
- Order intent validation.
- Confirmed order placement, fill, cancel, and reconciliation cycle before any live-ready claim.

Do not bypass `missing_allowance`.

## 7. Order Pipeline Rules

Every ENTRY order must pass:

```text
Signal / EV
  -> RiskPlan
  -> PositionSizing
  -> Risk Approval
  -> Reconciliation Gate
  -> Order Intent Guard
  -> _submit_order()
```

Every EXIT order must pass:

```text
Tracked inventory
  -> ExitAgent / TP / SL / forced exit
  -> Order Intent Guard
  -> _submit_order()
```

Hard rules:

- Strategy modules must not submit orders directly.
- ENTRY must be BUY.
- NO entry is BUY on NO token, not SELL without inventory.
- SELL is allowed only for tracked existing inventory.
- LOCKDOWN blocks entries but allows exit/management.
- Paper mode enforces the same guards.

## 8. Risk Rules

Never bypass:

- Floor balance.
- Single-trade cap.
- Daily drawdown checks.
- Reconciliation gate.
- Unknown-state guards.
- Bankroll rank lock / hysteresis.
- Risk Mode Ladder.
- ExitAgent.
- OrderIntent validation.

Risk Mode Ladder:

- NORMAL: normal locked-tier sizing.
- DEFENSIVE: reduced sizing after loss/drawdown triggers.
- MICRO_RECOVERY: very small sizing after deeper drawdown/loss streak.
- LOCKDOWN: no new entries; manage/exit existing positions only.

## 9. Strategy Change Rules

- Do not change strategy logic during docs, cleanup, logging, UI, or CI tasks.
- Any signal change must update both `polymarket/signal.py` and `polymarket/backtester_5m.py`.
- Any signal change requires a backtest before promotion.
- Do not loosen risk rules to force paper trades.
- If all trades skip, inspect skip reasons first.

## 10. Logging And Observability Rules

Implemented:

- Per-run app logs in `logs/`.
- Per-run scan CSV in `runtime/realtime_logs/YYYY-MM-DD/`.
- Windows file-lock resilience for app log and realtime CSV logging.
- Terminal UI V2 rolling log panel.
- Optional Telegram notifier and Telegram error handler.

Current gaps:

- No JSONL event log yet.
- No central Telegram cooldown/dedup.
- Daily report and Telegram daily summary readers still expect fixed `scan_log.csv`.
- Retention/archival strategy is planned, not implemented.

Logging failures must not crash paper mode. Fix logging in `utils/logger.py` or `polymarket/realtime_logger.py`; do not change trading logic to handle log file locks.

## 11. Telegram Rules

- Telegram must never block the trading loop.
- Telegram failures should not trigger order/risk changes.
- Do not rely on daily Telegram summaries until per-run CSV reader drift is fixed.
- Add cooldown/dedup before increasing alert volume.

## 12. Testing Rules

Use targeted tests for scoped work.

Important suites:

```bash
pytest -q tests/test_paper_mode.py
pytest -q tests/test_execution_risk_controls.py
pytest -q tests/test_exit_agent.py
pytest -q tests/test_risk_modes.py
pytest -q tests/test_bankroll_tiers.py
pytest -q tests/test_logging_resilience.py
pytest -q tests/test_terminal_dashboard_display.py
pytest -q tests/test_verify_mode.py
```

Full suite:

```bash
python -m pytest tests/ -q
```

Tests must mock external APIs unless explicitly running a controlled integration/verify task.

## 13. Forbidden Modifications Without Explicit Approval

- Editing `.env` secrets.
- Switching default runtime away from paper.
- Increasing live trade size.
- Bypassing allowance.
- Bypassing risk or reconciliation.
- Rebuilding the project from scratch.
- Deleting runtime logs, trade logs, backtest results, or config.
- Moving strategy research records during unrelated cleanup.
- Promoting HFT path to live.

## 14. Violation Handling

If a safety rule appears to block progress:

1. Stop and document the blocker.
2. Add/update `CURRENT_PROJECT_STATUS.md`.
3. Add/update `docs/KNOWN_ISSUES.md`.
4. Add tests for any proposed fix.
5. Do not bypass the rule unless the user explicitly approves the live-risk impact.
