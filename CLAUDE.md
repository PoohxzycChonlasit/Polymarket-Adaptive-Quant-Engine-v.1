# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PolyTrade Bot — a Polymarket 5M BTC/ETH quant scalper. Paper-first, observability-first. Not live-trading-ready yet.

## Commands

```bash
# Run (paper is the safe default)
python main.py
python main.py --mode paper --interval 60 --ui auto --fps medium

# Verify environment/wallet read-only
python main.py --mode verify

# Backtest
python main.py --mode polymarket-backtest --days 7 --asset BTC

# Live (blocked unless readiness preflight passes)
python main.py --mode live --interval 60

# Tests
python -m pytest tests/ -q
pytest -q tests/test_paper_mode.py           # single file
pytest -q -k "bankroll"                      # keyword filter

# Offline analysis tools
python tools/quant_data_quality.py --date 2026-05-08 --write-report
python tools/replay_analyzer.py --date 2026-05-08 --csv
python tools/paper_evaluation_report.py --date 2026-05-08
```

## Architecture

Entry point `main.py` loads `config/settings.py` (Pydantic BaseSettings from `.env`), validates config, then routes to a mode function. All modes ultimately drive `PolymarketTrader` (`polymarket/trader.py`).

**Main loop (paper/live):**
1. `PolymarketTrader` initialises market feed, CLOB orderbook, risk state, portfolio
2. Each cycle: fetch BTC/ETH snapshots → update orderbooks → compute signals → estimate probability → calculate EV → size position → execute (simulated in paper) → log JSONL event → render Terminal UI

**Key module groups:**

| Group | Files |
|---|---|
| Orchestration | `main.py`, `polymarket/trader.py` |
| Settings | `config/settings.py` |
| Market data | `polymarket/gamma_fetcher.py`, `polymarket/market_feed.py`, `polymarket/oracle_price_feed.py`, `polymarket/client.py` |
| Signals & alpha | `polymarket/signal.py`, `polymarket/regime_diagnostics.py`, `polymarket/probability_model.py`, `polymarket/expected_value.py` |
| Risk & sizing | `utils/risk_manager.py`, `polymarket/bankroll_tiers.py`, `polymarket/position_sizing.py`, `polymarket/risk_modes.py` |
| Execution guard | `polymarket/order_intent.py`, `polymarket/order_manager.py` |
| Paper execution | `polymarket/virtual_ptb.py` |
| Reconciliation | `utils/position_tracker.py`, `polymarket/position_manager.py` |
| Observability | `utils/logger.py`, `polymarket/realtime_logger.py`, `utils/quant_event_logger.py`, `utils/telegram_alerts.py` |
| Terminal UI | `utils/display.py` |
| Offline tools | `tools/` (never wired into runtime decisions) |

## Before Editing

Read in order: `CODEX_START_HERE.md` → `PROJECT_RULES.md` → `CURRENT_PROJECT_STATUS.md`. For research/replay tasks, read `runtime/research_state/latest_research_state.md` before opening large logs or JSONL.

Route every task through `MASTER_AGENT_ROUTER.md`: pick exactly one PRIMARY role and up to three SUPPORTING roles. Read only the selected role docs in `docs/quant_agent_setup_md/roles/`.

## Architecture Rules

- **WebSocket-first.** The WebSocket cache is the primary market state source. REST is fallback only. Never poll REST orderbooks every second.
- **Event-driven.** Logging is event-driven and sampled. Log budget: <150 MB/day compressed. No unbounded log files.
- **Paper/live separation is inviolable.** Paper mode: real data, simulated execution only — never touches wallet, signs orders, or sends live orders. Live mode: requires explicit `--mode live` + passing readiness preflight.
- **Offline tools are evidence only.** Replay outputs and analyzer reports must not be wired into automatic runtime decisions without a separately approved implementation phase.
- Do not bypass `order_intent` validation, stale-data protection, risk gates, or execution protections without explicit approval.
- No martingale, no unlimited averaging down, no all-in. `arb_auto_execute` must remain `false` by default.

## Project Roadmap

1. **Phase 1** (current): regime classification, probability scoring, indicator evidence, observability only.
2. **Phase 2**: paper-only inventory replay — reload/unload analysis, opportunity decay, MFE/MAE tracking.
3. **Phase 3**: bounded multi-price inventory engine with hard caps, stop-loss, forced exit.
4. **Phase 4**: continuous probabilistic inventory trading only after paper evidence supports it.

## File Scope Rules

- Never scan `runtime/`, `logs/`, `reports/`, `parquet/`, `archives/`, or generated files unless explicitly debugging those areas. Exception: `runtime/research_state/latest_research_state.md` is intentionally compact and safe to read first for research context.
- Prefer targeted inspection over repository-wide grep.
- Make the smallest safe change and run targeted tests before broader ones.
- Do not refactor files unrelated to the current task.
