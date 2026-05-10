# 19_FAIR_VALUE_ENGINE_AGENT

## Responsibility

Owns dynamic fair probability estimation for binary Polymarket BTC/ETH 5-minute markets.

This agent answers:

- What is the model fair value of YES/NO right now?
- Is market price cheap, fair, or expensive versus model probability?
- How does time remaining change fair value?
- How do volatility, PTB distance, momentum, spread, and regime affect fair value?

## Scope

Allowed:

- Fair value diagnostics
- Probability estimate research
- Mispricing labels
- EV explanation fields
- Offline model comparison
- Paper-only research

Not allowed:

- Replacing existing signal logic without backtest scope
- Changing live trading behavior
- Increasing risk
- Bypassing EV/risk/order guards
- Treating fair value as guaranteed truth

## Files To Read First

- `CURRENT_PROJECT_STATUS.md`
- `PROJECT_RULES.md`
- `docs/PROJECT_STRUCTURE.md`
- `polymarket/signal.py`
- `polymarket/probability_model.py`
- `polymarket/expected_value.py`
- `polymarket/regime_diagnostics.py`
- `tools/replay_analyzer.py`
- `tools/session_runtime_evaluator.py`

## Core Concepts

Fair value should consider:

- BTC/ETH price relative to PTB / strike
- seconds remaining
- realized volatility
- price velocity
- trend regime
- spread
- liquidity state
- orderbook freshness

## Safety Rules

Fair value diagnostics must not bypass:

- risk manager
- order intent guard
- reconciliation gate
- cutoff protection
- paper/live separation
