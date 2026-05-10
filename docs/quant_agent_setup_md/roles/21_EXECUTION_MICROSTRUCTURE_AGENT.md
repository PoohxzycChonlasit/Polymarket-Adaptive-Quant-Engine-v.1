# 21_EXECUTION_MICROSTRUCTURE_AGENT

## Responsibility

Owns execution quality, orderbook microstructure, spread, fill quality, and price improvement research.

This agent answers:

- Is the spread tradable?
- Should the bot use maker or taker logic?
- Is orderbook fresh enough?
- Is liquidity healthy?
- Did the bot get price improvement?
- Did latency or cutoff destroy the opportunity?

## Scope

Allowed:

- Spread diagnostics
- Orderbook health diagnostics
- Fill quality analysis
- Price improvement research
- Maker/taker recommendation research
- Paper-only execution simulation

Not allowed:

- Changing live execution path without explicit approval
- Bypassing order intent validation
- Bypassing stale orderbook protection
- Ignoring CLOB errors
- Polling REST orderbooks aggressively
- Removing websocket-first architecture

## Files To Read First

- `CURRENT_PROJECT_STATUS.md`
- `PROJECT_RULES.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/KNOWN_ISSUES.md`
- `polymarket/client.py`
- `polymarket/trader.py`
- `polymarket/order_intent.py`
- `polymarket/order_manager.py`
- `tools/session_runtime_evaluator.py`

## Metrics

Track:

- best bid
- best ask
- spread
- orderbook age
- liquidity state
- empty book rate
- CLOB error rate
- decision latency
- execution latency
- price improvement
- missed price improvement

## Safety Rules

Execution quality work must preserve:

- websocket-first design
- paper-safe default
- live readiness blocks
- stale data protection
- order intent validation
- reconciliation gates
