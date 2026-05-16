# Skill: Lifecycle Inventory Planning

## Purpose

Plan future paper-first Quant Lifecycle Inventory System work.

This skill is for design and offline research. It does not implement inventory execution and does not authorize live trading.

## Required Lifecycle Vocabulary

Use these official phases:

| Phase | Purpose |
|-------|---------|
| `OPENING_SCAN` | Discover market early, resolve token IDs, warm orderbook, mark first tradable second. |
| `ACTIVE_INVENTORY_TRADING` | Future bounded starter/reload/reduce logic only when EV, liquidity, time, and risk budget agree. |
| `PROFIT_MANAGEMENT` | Protect realized PnL, unload exposure, and prepare for derisk. |
| `FINAL_DERISK` | Reduce most exposure, cancel unsafe orders, no new entries. |
| `CLOSED_OR_UNSAFE` | Stop when market, data, reconciliation, or risk state is unsafe. |

## Planning Questions

- What lifecycle phase is visible in evidence?
- Does candidate timing show early enough discovery?
- Are token/orderbook/liquidity readiness visible?
- Are EV, fair value, probability, and spread visible before risk?
- Is Dynamic Quant Risk Budget visible?
- Is inventory truth visible?
- Are MFE/MAE and reload/unload opportunities measurable?
- Which pieces remain offline-only?

## Hard Boundaries

- Keep inventory research paper/offline until separately scoped and tested.
- No martingale.
- No unlimited averaging down.
- No runtime inventory implementation from planning tasks.
- No OrderIntent bypass.
- No reconciliation bypass.
- No stale-book bypass.
- No live behavior changes.

## Output Shape

Report:

1. lifecycle evidence maturity
2. phase coverage
3. missing observability fields
4. replay readiness
5. risk-budget readiness
6. inventory execution readiness claim: always false unless explicitly proven by scoped implementation and tests
7. exactly 3 future options
