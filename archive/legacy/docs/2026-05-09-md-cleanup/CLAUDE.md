# Claude / AI Assistant Notes

> Last synced: 2026-05-08.
> This file is a compatibility note for Claude-style tooling. The current authoritative instructions are `AGENTS.md`, `CODEX_START_HERE.md`, and `CURRENT_PROJECT_STATUS.md`.

## Current Project Identity

PolyTrade Bot is a Polymarket BTC/ETH 5-minute binary-market quant scalper.

Current posture:

- Paper mode is default.
- Real market data and real CLOB orderbooks are used in paper mode.
- Execution is simulated locally in paper mode.
- Live mode is not confirmed ready.
- Latest status still includes live allowance and live execution validation blockers.

Do not describe the bot as live-ready.

## Read First

1. `CURRENT_PROJECT_STATUS.md`
2. `CODEX_START_HERE.md`
3. `AGENTS.md`
4. `PROJECT_RULES.md`
5. `docs/PROJECT_STRUCTURE.md`
6. `docs/KNOWN_ISSUES.md`
7. `docs/OBSERVABILITY_PLAN.md`

## Safe Commands

```bash
python main.py
python main.py --mode paper --interval 60
python main.py --mode verify
```

Live command requires explicit user intent and readiness:

```bash
python main.py --mode live --interval 60
```

## Current Safety Rules

- Do not rebuild from scratch.
- Do not change strategy logic during documentation, UI, logging, or cleanup work.
- Do not bypass Risk, ExitAgent, Reconciliation, or OrderIntent.
- Do not increase live size.
- Do not touch `.env` secrets.
- Do not claim orderbook is working unless terminal shows `BID`, `ASK`, and `SPREAD`.
- Do not claim wallet sync unless terminal/logs show real live balance source.
- Do not promote HFT paths to live.

## Current Known Gaps

- Live allowance unresolved.
- Live order placement/fill/cancel/reconcile unvalidated.
- Daily report and Telegram summary readers still expect fixed `scan_log.csv`.
- Telegram cooldown/dedup not implemented.
- JSONL event logging planned, not implemented.

For details, use `docs/KNOWN_ISSUES.md`.
