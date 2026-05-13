# Master Context - Polymarket BTC/ETH 5-Minute Quant Bot

> Last synced: 2026-05-10.

## Project Goal

Build and validate a Polymarket BTC/ETH 5-minute binary-market trading bot that prioritizes survival, clean execution, measurable edge, paper-first validation, and strong observability before live execution.

Current direction: evolve from single-entry scalping into a paper-first regime-aware probability system, then paper-only inventory replay research, then bounded multi-price inventory design. This roadmap does not authorize runtime execution changes by itself.

## Current State

Implemented:

- Safe paper mode is default.
- Real BTC/ETH market discovery and CLOB orderbook reads are wired.
- Terminal UI V2 responsive dashboard is active.
- Paper orders/fills/exits/PnL are simulated locally.
- Wallet source labeling exists for paper vs live.
- OrderIntent guard exists for ENTRY/EXIT.
- Bankroll Rank Lock / hysteresis exists.
- Risk Mode Ladder exists.
- Windows logging PermissionError resilience exists.
- Tests cover key paper, risk, exit, order intent, logging, verify, and terminal dashboard behavior.

Partially implemented:

- Live wallet/balance plumbing exists, but latest status still reports allowance blocker.
- Live execution path exists, but order placement/fill/cancel/reconcile is not validated.
- Telegram alerting exists, but cooldown/dedup and per-run CSV daily report support are incomplete.

Planned:

- Regime/probability diagnostics refinement.
- Paper-only inventory replay research.
- Bounded multi-price inventory design.
- Longer paper validation sessions.
- Tiny controlled live validation only after explicit approval and readiness.

## Core Principle

Do not make the bot more aggressive until it is harder to hurt.

Priority order:

1. Risk control.
2. Exit logic.
3. Data correctness.
4. Execution correctness.
5. Reconciliation correctness.
6. Observability.
7. Backtest/replay validation.
8. Strategy improvement.
9. Regime/probability research.
10. Paper-only inventory replay.
11. Bounded inventory design.
12. Live scaling.

## Non-Negotiable Rules

- Paper mode remains default.
- Live mode requires explicit `--mode live`.
- Do not claim live-ready until live order placement, fill, cancel, and reconciliation are proven.
- Every entry must pass risk, sizing, reconciliation, and order intent checks.
- Every exit must be for tracked existing inventory.
- Every trade and skip should log a reason.
- No strategy changes without matching backtest path and tests.
- No live scaling from paper results alone.
- No AI/LLM calls in the realtime trading loop.
- No martingale, unlimited averaging down, or all-in behavior.
- No automatic runtime decisions from offline analyzers.

## Current Known Problems

- Live allowance is not ready in latest evidence.
- Live execution lifecycle is not proven.
- Live allowance is not ready in latest evidence.
- Live execution lifecycle is not proven.
- Some older research docs may still overstate HFT/live readiness.

## Recommended Next Milestone

Documentation is now aligned toward the staged quant roadmap. The next research milestone should keep Phase 1 diagnostics separate from execution:

1. Collect paper evidence with regime/probability fields.
2. Use offline replay/evaluator output to judge whether probability/regime fields explain no-entry and timing compression.
3. Only then scope paper-only inventory replay.
4. Keep strategy/risk/execution behavior unchanged unless a future task explicitly scopes it.
