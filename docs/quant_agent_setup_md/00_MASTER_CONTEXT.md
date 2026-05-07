# MASTER_CONTEXT — Polymarket BTC/ETH 5-Minute Quant Bot

## Project Goal
Build an execution-grade Polymarket BTC/ETH 5-minute trading bot that prioritizes survival, clean execution, measurable edge, and fast iteration.

## Core Principle
Do not make the bot smarter until it is harder to hurt.

Priority order:
1. Risk control
2. Exit logic
3. Data correctness
4. Execution correctness
5. Observability
6. Backtest/replay validation
7. Strategy improvement
8. Live scaling

## Current Known Problems
- Bot can enter multiple prices in the same window.
- Bot may not exit before close.
- Near-PTB windows can become almost 50/50 but still expose large loss.
- Current strategy and execution logic are spread across multiple modules.
- Runtime status, README, and actual trading mode may drift from each other.
- Fee/slippage and stale-data handling must be treated as first-class risk.

## Non-Negotiable Rules
- One canonical main trading loop.
- One source of truth for mode: PAPER / LIVE_SMALL / LIVE_DISABLED.
- Every trade must pass RiskAgent before order placement.
- Every open position must be watched by ExitAgent.
- Every trade and skip must log a reason.
- No live scaling until replay + paper + canary results are reviewed.

## Recommended First Milestone
Create the agent system as documentation first, then implement it in code:

```text
agents/
  risk_manager_agent.py
  exit_execution_agent.py
  market_data_agent.py
  position_reconciliation_agent.py
  review_agent.py
```

This folder of markdown files defines the working system before code changes are made.
