# PolyTrade Bot Roadmap

> Last synced: 2026-05-08.
> This roadmap is subordinate to `CURRENT_PROJECT_STATUS.md`.

## Current Position

Phase: paper-first validation and observability hardening.

The project is not live-trading ready. Live mode remains blocked until allowance and live execution lifecycle validation are complete.

## Completed / Implemented

- Safe paper mode default.
- Real BTC/ETH Polymarket market discovery.
- Real BTC/ETH CLOB orderbook display path.
- Paper order/fill/exit/PnL simulation.
- Wallet source labeling for paper vs live.
- Terminal UI V2 responsive dashboard.
- OrderIntent ENTRY/EXIT guard.
- Bankroll Rank Lock / hysteresis.
- Risk Mode Ladder.
- ExitAgent and TP/SL/runner protections.
- Windows logging PermissionError resilience.
- Focused tests for paper, risk, execution guard, exit, logging, terminal UI, verify, and model modules.

## Current Blockers

- Live allowance not ready in latest evidence.
- Live order placement not confirmed.
- Live fill/cancel/reconcile cycle not confirmed.
- Daily report and Telegram daily summary readers do not yet support per-run `scan_log_*.csv`.
- Telegram cooldown/dedup not implemented.
- JSONL event logging not implemented.

## Phase 1 - Documentation Sync

Status: completed on 2026-05-08.

Updated:

- `README.md`
- `CURRENT_PROJECT_STATUS.md`
- `CODEX_START_HERE.md`
- `PROJECT_RULES.md`
- `AGENTS.md`
- `CLAUDE.md`
- `ROADMAP.md`
- `docs/PROJECT_STRUCTURE.md`
- `PROJECT_STRUCTURE.md`
- `docs/OBSERVABILITY_PLAN.md`
- `docs/KNOWN_ISSUES.md`
- quant-agent index/context docs

## Phase 2 - Observability Sync

Recommended next phase.

Goals:

- Update `daily_report.py` to aggregate `scan_log_*.csv`.
- Update `utils/telegram_reporter.py` to aggregate `scan_log_*.csv`.
- Add tests for multiple per-run CSV files.
- Add fail-soft JSONL event logging.
- Add Telegram cooldown/dedup layer.
- Keep trading logic unchanged.

## Phase 3 - Longer Paper Validation

Goals:

- Run longer BTC/ETH paper sessions.
- Confirm Terminal UI V2 remains readable.
- Confirm orderbook `BID`, `ASK`, `SPREAD` stay visible.
- Track top skip reasons.
- Confirm paper orders/fills/exits/PnL only when risk naturally allows.
- Do not loosen risk just to force trades.

## Phase 4 - Live Readiness

Prerequisites:

- Resolve allowance.
- Verify live CLOB collateral balance.
- Confirm clean reconciliation.
- Design tiny controlled live validation.
- Get explicit operator approval.

Validation must prove:

- Order placement.
- Order status.
- Fill detection.
- Cancel path.
- Reconciliation.
- Exit for tracked inventory.

## Phase 5 - Dashboard / Docs Consolidation

Goals:

- Consolidate overlapping dashboard docs.
- Review `dashboard/` vs `web-dashboard/`.
- Mark HFT path clearly experimental.
- Archive stale docs only after explicit review.

## Not On The Roadmap Without Explicit Approval

- Rebuilding the bot from scratch.
- Promoting HFT to live.
- Increasing live size.
- Bypassing allowance.
- Bypassing risk/reconciliation/order intent.
- Changing strategy without backtest and tests.
