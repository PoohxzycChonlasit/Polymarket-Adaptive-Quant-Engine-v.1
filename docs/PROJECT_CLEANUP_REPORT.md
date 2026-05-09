# Project Cleanup Report

Date: 2026-05-05

Documentation sync update: 2026-05-08

Markdown prompt cleanup update: 2026-05-09

## Scope

This cleanup pass focused on structure, documentation, and reducing root-level confusion. It did not change trading strategy logic, order sizing, exits, wallet configuration, runtime logs, trade logs, backtest results, or paper/live execution code.

The operating reference for future project work is:

- `CODEX_START_HERE.md`
- `AGENTS.md`
- `MASTER_AGENT_ROUTER.md`
- `PROJECT_RULES.md`
- `CURRENT_PROJECT_STATUS.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/KNOWN_ISSUES.md`

Use `docs/OBSERVABILITY_PLAN.md` for logging/Telegram work and `docs/PAPER_TRADING_RUNBOOK.md` for paper operation/review work.

## Actions Taken

- Created `archive/legacy/docs/`.
- Moved stale root-level AI handoff docs into `archive/legacy/docs/`.
- Added this cleanup report.
- Added `docs/PROJECT_STRUCTURE.md`.
- Updated `AGENTS.md` to reflect current safety-first cleanup rules and active paths.
- Updated `README.md` with the canonical operating docs and main runtime path.
- 2026-05-08 documentation sync rewrote current root docs to reflect the real paper-first implementation, Terminal UI V2, Windows logging resilience, order intent/risk mode/bankroll rank protections, and live blockers.
- 2026-05-08 documentation sync added `docs/OBSERVABILITY_PLAN.md`, `docs/KNOWN_ISSUES.md`, and root `PROJECT_STRUCTURE.md`.
- 2026-05-09 markdown prompt cleanup reduced root-level Codex/AI prompt clutter by archiving stale, task-specific, or duplicate `.md` files into `archive/legacy/docs/2026-05-09-md-cleanup/`.

## Moved Files

The files in this table are archived historical references only. Do not use them as the active Codex startup workflow.

| From | To | Reason |
|------|----|--------|
| `AI_AGENTS.md` | `archive/legacy/docs/AI_AGENTS.md` | Stale AI handoff doc, overlaps with `docs/quant_agent_setup_md/` and `AGENTS.md`. |
| `AI_CONTEXT.md` | `archive/legacy/docs/AI_CONTEXT.md` | Stale AI context doc, overlaps with current project status and quant-agent docs. |
| `MASTER_CODEX_PROMPT.md` | `archive/legacy/docs/2026-05-09-md-cleanup/MASTER_CODEX_PROMPT.md` | Task/session prompt duplicated current `AGENTS.md`, `CODEX_START_HERE.md`, and `PROJECT_RULES.md`. |
| `TASK_REQUEST.md` | `archive/legacy/docs/2026-05-09-md-cleanup/TASK_REQUEST.md` | Completed task-specific prompt for paper balance hardening; no longer a reusable operating doc. |
| `CLAUDE.md` | `archive/legacy/docs/2026-05-09-md-cleanup/CLAUDE.md` | Claude compatibility note duplicated current Codex docs and contained stale observability gaps. |
| `README_QUICK_CONTEXT.md` | `archive/legacy/docs/2026-05-09-md-cleanup/README_QUICK_CONTEXT.md` | Narrow context prompt duplicated current project rules and contained task-specific priorities. |
| `ARCHITECTURE.md` | `archive/legacy/docs/2026-05-09-md-cleanup/ARCHITECTURE.md` | Aspirational websocket-first architecture note duplicated `docs/PROJECT_STRUCTURE.md` and could be mistaken for implemented runtime structure. |
| `ROADMAP.md` | `archive/legacy/docs/2026-05-09-md-cleanup/ROADMAP.md` | Roadmap was subordinate to `CURRENT_PROJECT_STATUS.md` and contained stale observability status. |
| `research/FOR_OTHER_AI.md` | `archive/legacy/docs/2026-05-09-md-cleanup/FOR_OTHER_AI.md` | External-AI handoff prompt duplicated current agent docs and adds prompt clutter. |
| `research/DAILY_STARTUP_PROMPT.md` | `archive/legacy/docs/2026-05-09-md-cleanup/DAILY_STARTUP_PROMPT.md` | Copy-paste startup prompt duplicated `CODEX_START_HERE.md` and `AGENTS.md`. |

No Python modules, configs, logs, runtime state, trade logs, or backtest results were moved.

## Active Markdown Docs After 2026-05-09 Prompt Cleanup

Use this smaller set for normal Codex work:

| File | Purpose |
|------|---------|
| `AGENTS.md` | Auto-loaded safety-first Codex instructions. |
| `CODEX_START_HERE.md` | Minimal session startup context. |
| `PROJECT_RULES.md` | Current safety, architecture, token, and testing rules. |
| `CURRENT_PROJECT_STATUS.md` | Single source of truth for current implementation status and blockers. |
| `MASTER_AGENT_ROUTER.md` | Chooses the relevant role doc when role guidance is needed. |
| `docs/PROJECT_STRUCTURE.md` | Canonical runtime/data-flow structure. |
| `docs/KNOWN_ISSUES.md` | Current bugs, blockers, and technical debt. |
| `docs/PROJECT_CLEANUP_REPORT.md` | Cleanup history and active/archived doc decisions. |
| `docs/PAPER_TRADING_RUNBOOK.md` | Paper operation and review workflow. |
| `docs/OBSERVABILITY_PLAN.md` | Logging, JSONL, Telegram, and incident observability plan. |

Keep `docs/quant_agent_setup_md/roles/` because those files are still referenced by `AGENTS.md` and `MASTER_AGENT_ROUTER.md`. They are guidance prompts, not runtime modules.

## Active Entrypoints

| Entrypoint | Status | Purpose |
|------------|--------|---------|
| `python main.py` | Canonical safe default | Main Polymarket paper trading loop with real market/orderbook data and simulated execution. |
| `main.py --mode paper --interval 60` | Canonical paper | Explicit main Polymarket paper loop. |
| `main.py --mode polymarket-realtime --interval 60` | Legacy alias | Routed to safe paper mode; retained for compatibility. |
| `main.py --mode live --interval 60` | Blocked until ready | Runs verify preflight first; do not use until allowance/execution/reconciliation are validated. |
| `main.py --mode polymarket-backtest --days N --asset BTC/ETH` | Active | 5-minute Polymarket strategy backtest. |
| `main.py --mode polymarket-5m-dashboard` | Active | Streamlit dashboard for Polymarket 5-minute backtests. |
| `daily_report.py` | Active | Reads scan/trade logs and reports daily P&L. |
| `polymarket/five_min_monitor.py --interval 30` | Active utility | Live market monitor, separate from execution loop. |
| `hft_paper_run.py` | Active paper utility | Standalone HFT paper simulation and reporting. |
| `main.py --mode hft` / `python -m hft.main` | Experimental | HFT engine path. Keep paper-first until live token/execution safety is reviewed. |
| `main.py --mode scalper` | Secondary | Freqtrade-style crypto scalper path. Not the main Polymarket bot. |
| `check_balance.py` | Utility | Wallet balance check. |
| `register_api_keys.py` | Utility | Polymarket API credential setup. |
| `generate_bypass.py` | Utility | Cloudflare/bypass helper. |

## Actively Used Core Files

| File | Role |
|------|------|
| `main.py` | CLI dispatcher and canonical realtime loop orchestration. |
| `config/settings.py` | Pydantic settings and environment validation. |
| `polymarket/trader.py` | Main Polymarket trade coordinator: market lookup, signal, risk, order, exits, status. |
| `polymarket/client.py` | CLOB client setup, wallet auth, balances, orders, redemption helpers. |
| `polymarket/gamma_fetcher.py` | Gamma market discovery, token IDs, event/market metadata. |
| `polymarket/market_feed.py` | Binance market feed singleton. |
| `polymarket/oracle_price_feed.py` | Coinbase/Polymarket price-to-beat tracking path used by trader. |
| `polymarket/virtual_ptb.py` | Virtual PTB tracker used by trader. |
| `polymarket/signal.py` | Realtime signal engine. Do not change without matching backtest work. |
| `polymarket/backtester_5m.py` | Backtest implementation and strategy validation path. |
| `polymarket/order_manager.py` | Builds risk plan and order request from signal/risk inputs. |
| `polymarket/arbitrage.py` | Arbitrage/market pricing helper used by trader/display paths. |
| `polymarket/realtime_logger.py` | Runtime scan/trade logging. |
| `utils/risk_manager.py` | Main Polymarket risk manager, floor balance, sizing caps, daily drawdown logic. |
| `utils/position_tracker.py` | Position state and drawdown controls. |
| `utils/display.py` | Rich terminal displays for realtime and HFT paper paths. |
| `utils/telegram_reporter.py` | Telegram reporting and alerts. |
| `utils/logger.py` | Logging setup. |

## Files That Should Stay

Keep these in place unless a dedicated migration task updates all references and docs:

- `.env`, `.env.example`
- `CURRENT_PROJECT_STATUS.md`
- `README.md`
- `AGENTS.md`
- `PROJECT_RULES.md`
- `VULTR_PAPER_RUN.md`
- `requirements.txt`
- `config/`
- `polymarket/`
- `utils/`
- `hft/`
- `crypto_scalper/`
- `dashboard/`
- `web-dashboard/`
- `tests/`
- `scripts/`
- `research/`
- `runtime/`
- `logs/`
- `logs_vps/`
- `backtest_results/`
- `models/`

## Files That Look Unused Or Legacy

These look legacy, duplicated, or unclear, but were not moved because they may still be useful as historical references or for external tooling:

| File/Folder | Why it looks legacy or unclear | Recommendation |
|-------------|--------------------------------|----------------|
| `PROJECT_RULES.md` | Refreshed on 2026-05-08 to match paper-first runtime and current safety gates. | Keep as current rules companion to `AGENTS.md`. |
| `research/OVERVIEW.md` | Contains strategy history that may conflict with current v4/HFT docs. | Keep; mark as research history if stale. |
| `scratch/` | Scratch workspace by name. | Review manually before archiving. |
| `models/` | No clear active load path found during cleanup. | Review manually; do not delete. |

## Overlapping Risk Managers

| File | Current role | Risk |
|------|--------------|------|
| `utils/risk_manager.py` | Main Polymarket sizing and hard floor source. | Should remain canonical for `polymarket/trader.py`, `order_manager.py`, and backtests. |
| `hft/risk_manager.py` | HFT-specific bankroll/window risk manager. | Separate rules can drift from main risk policy. Keep scoped to HFT. |
| `config/settings.py` | Environment-level risk config and validation. | Can conflict with constants if changed without tests. |
| `polymarket/order_manager.py` | Converts risk calculations into `RiskPlan`. | Wrapper only; should not become independent policy. |
| `utils/position_tracker.py` | Position and daily drawdown state. | Needs consistency with `utils/risk_manager.py`. |

Recommendation: keep the separation for now, but document `utils/risk_manager.py` as the canonical Polymarket policy and `hft/risk_manager.py` as experimental/HFT-only.

## Overlapping Main Loops

| Loop | Status | Recommendation |
|------|--------|----------------|
| `main.py --mode polymarket-realtime` | Canonical | Use for live/paper Polymarket operations. |
| `hft_paper_run.py` | Active paper utility | Keep for HFT paper studies and reports. |
| `main.py --mode hft` / `hft/main.py` | Experimental | Paper-only until token/execution review is complete. |
| `main.py --mode polymarket` | Legacy/manual cycle | Keep for debugging, but do not treat as production loop. |
| `crypto_scalper/live_runner.py` | Separate product line | Keep separate from Polymarket docs. |

## Overlapping Dashboards

| Dashboard | Status | Recommendation |
|-----------|--------|----------------|
| `dashboard/polymarket_5m_dashboard.py` | Active via `main.py --mode polymarket-5m-dashboard` | Keep. |
| `dashboard/app.py` | Active via `main.py --mode dashboard` | Keep, but label as generic backtest dashboard. |
| `dashboard/live_dashboard.py` | Standalone | Keep; add explicit command to README in a later docs pass. |
| `web-dashboard/` | Separate Next.js dashboard | Keep; manual review before any consolidation. |

## Unclear Config And Runtime State

- `.env` currently controls real safety. It must be reviewed before any live run.
- `config/settings.py` defaults to `paper_trading=True` and `dry_run=True`, but local `.env` can override them.
- `runtime/bot_status.json` should be treated as runtime state, not source code.
- Logs under `logs/` and `logs_vps/` are operational evidence and were intentionally preserved.
- Backtest outputs under `backtest_results/` were intentionally preserved.

## Execution Safety Findings For Manual Review

These are real operational concerns found during cleanup, but no trading code was changed in this task:

1. Recent runtime status showed balance near or below the `$5` floor. Live execution must stay blocked until balance/floor state is reconciled.
2. Always confirm `.env` before running any live-risk command.
3. Older live `NO` SELL-without-inventory concerns were addressed by order intent guard tests, but live execution remains unvalidated.
4. Older research docs may still disagree on whether the active strategy is counter-momentum or v4 HFT/window-delta. Current docs now treat the Polymarket BTC/ETH 5M path as canonical and HFT as experimental.
5. HFT paper results must not promote HFT live path without risk review.
6. `daily_report.py` and `utils/telegram_reporter.py` still need updating for per-run `scan_log_*.csv` files.

## Recommended Final Project Structure

```text
polytrade-crypto-scalper-main/
  AGENTS.md
  README.md
  CURRENT_PROJECT_STATUS.md
  config/
  docs/
    PROJECT_CLEANUP_REPORT.md
    PROJECT_STRUCTURE.md
    OBSERVABILITY_PLAN.md
    KNOWN_ISSUES.md
    quant_agent_setup_md/
  polymarket/
  utils/
  hft/
  crypto_scalper/
  dashboard/
  web-dashboard/
  scripts/
  tests/
  research/
    daily/
  runtime/
  logs/
  logs_vps/
  backtest_results/
  archive/
    legacy/
      docs/
```

## Test Results

Command run:

```bash
python -m pytest tests/ -q
```

Result:

- Previous cleanup run: `52 passed`, `4 failed`
- Current run after execution-safety fixes: `62 passed`

Previous failures:

| Test | Failure summary |
|------|-----------------|
| `tests/test_polymarket_trader.py::PolymarketClientStubTests::test_cancel_order_returns_false_on_exception` | `PolymarketClient._require_clob()` raises because `py-clob-client` is not installed before the mocked `_client` path is used. |
| `tests/test_polymarket_trader.py::PolymarketClientStubTests::test_get_orderbook_parses_dict_response_best_prices` | Same mocked-client path blocked by `_CLOB_AVAILABLE` check. |
| `tests/test_polymarket_trader.py::PolymarketClientStubTests::test_place_limit_order_raises_on_invalid_side` | Expected validation error is hidden by missing `py-clob-client` runtime check. |
| `tests/test_polymarket_trader.py::PolymarketClientStubTests::test_place_limit_order_raises_on_zero_price` | Expected validation error is hidden by missing `py-clob-client` runtime check. |

Cleanup assessment: these failures were not caused by the archive/docs move. They were later fixed safely by allowing explicitly injected mocked CLOB clients in tests and by validating `place_limit_order()` inputs before requiring the optional live CLOB dependency.
