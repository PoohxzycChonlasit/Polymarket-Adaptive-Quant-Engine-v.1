# CODEX_START_HERE - Minimal Context

Project: PolyTrade Bot / Polymarket 5M BTC-ETH Quant System.

Before modifying code, read `CURRENT_PROJECT_STATUS.md` and do not assume the project is new or needs rebuilding.

Before implementing any new feature phase, run a documentation sync first if docs are stale or the user requests it.

For research, replay, observability-review, no-entry, lifecycle, or paper-session analysis tasks, first read the compact state:

```text
runtime/research_state/latest_research_state.md
```

Use larger `runtime/reports`, JSONL, logs, or generated data only when the compact state points to a gap, the task explicitly asks for deeper evidence, or targeted debugging requires it.

Current direction: paper-first Polymarket 5M quant system evolving from single-entry scalping into regime-aware probability diagnostics, then paper-only inventory replay, then bounded multi-price inventory research. The future inventory vocabulary is OPENING_SCAN, ACTIVE_INVENTORY_TRADING, PROFIT_MANAGEMENT, FINAL_DERISK, and CLOSED_OR_UNSAFE, governed by Dynamic Quant Risk Budget thinking. This does not make live trading ready.

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

1. `CODEX_START_HERE.md`
2. `PROJECT_RULES.md`
3. `AGENTS.md`
4. `MASTER_AGENT_ROUTER.md`
5. `CURRENT_PROJECT_STATUS.md`
6. `PROJECT_STRUCTURE.md`
7. `KNOWN_ISSUES.md`
8. `FILE_INDEX.md`
9. `QUANT_FUTURE_DECISION_ENGINE.md`

Then read `DOCUMENTATION_MAP.md` when the task involves docs, structure, routing, or future-phase planning.

For the current quant roadmap, use:

- `QUANT_REGIME_PROBABILITY_ENGINE.md`
- `INVENTORY_REPLAY_RESEARCH_PLAN.md`
- `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md`
- `QUANT_LIFECYCLE_INVENTORY_ENGINE.md`
- `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md`
- Only the selected `docs/quant_agent_setup_md/roles/*.md`

## Role-Routed Compact Workflow

Before implementation on every task:

1. Read `MASTER_AGENT_ROUTER.md`.
2. Select exactly one PRIMARY role.
3. Select zero to three SUPPORTING roles only if the task crosses boundaries.
4. Read only the selected role docs.
5. State the compact routing block: primary role, supporting roles, why selected, files allowed to inspect, and files intentionally ignored.
6. Keep role usage compact and do not paste full role docs into chat.

For research/replay/evidence tasks, read `runtime/research_state/latest_research_state.md` before larger evidence artifacts.

Role docs guide reasoning only. They do not authorize scope expansion or runtime behavior changes.

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
- Offline analyzers and replay reports must not feed automatic runtime decisions without a separately approved phase.

## Current Roadmap

1. Phase 1: regime classification, probability scoring, indicator evidence, observability only.
2. Phase 2: paper-only inventory replay, reload/unload analysis, opportunity decay, MFE/MAE tracking.
3. Phase 3: bounded multi-price inventory engine with max inventory cap, risk cap, stop loss, forced exit, no martingale, and no unlimited averaging down.
4. Phase 4: continuous probabilistic inventory trading only after paper evidence supports it.

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
- QuantEventLogger JSONL event logging under `runtime/quant_data`.
- Telegram alert cooldown/dedup layer.
- Offline data quality, replay analyzer, and paper evaluation report.
- Offline no-entry/session runtime evaluator diagnostics.
- Regime/probability diagnostic fields for observability.
- Startup config validation.
- Clean shutdown hardening for major runtime feeds/loggers.

## Known Gaps

- Live allowance still blocks live readiness.
- No confirmed live order placement/fill/cancel/reconcile cycle.
- Daily Telegram summary wording still needs copy cleanup before relying on it operationally.
- Retention/compaction and incident report writer are planned.
- Future inventory replay and bounded multi-price inventory tooling remain research/planned unless code/tests prove otherwise.

## Token Budget Rules

- Open only files directly needed for the current task.
- Prefer `runtime/research_state/latest_research_state.md` over large reports/logs/JSONL for research-task startup.
- Prefer compact counts and distributions over raw dumps.
- Prefer targeted grep/search over broad report inspection.
- Do not scan `.venv`, `backtest_results`, `runtime`, `archive`, or logs unless requested or needed for evidence.
- Exception: `runtime/research_state/latest_research_state.md` is intentionally compact and may be read first for research context.
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
