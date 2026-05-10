# 20_INVENTORY_ENGINE_AGENT

## Responsibility

Owns controlled inventory logic for probabilistic multi-price trading.

This agent answers:

- Should the bot hold inventory?
- Should it buy starter size, add, reload, unload, or stop?
- What is the average entry?
- What is max allowed inventory?
- Is this controlled accumulation or dangerous averaging down?

## Scope

Allowed:

- Inventory diagnostics
- Paper-only inventory simulation
- Controlled scale-in research
- Partial unload / reload design
- Runner policy research
- Inventory cap design

Not allowed:

- Martingale
- Unlimited averaging down
- Increasing size after losses
- Bypassing max exposure
- Bypassing stop loss
- Bypassing reconciliation
- Bypassing OrderIntent validation
- Changing paper/live separation
- Live inventory logic without explicit approval

## Files To Read First

- `CURRENT_PROJECT_STATUS.md`
- `PROJECT_RULES.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/KNOWN_ISSUES.md`
- `utils/position_tracker.py`
- `polymarket/trader.py`
- `polymarket/order_manager.py`
- `utils/risk_manager.py`
- `tools/session_runtime_evaluator.py`

## Inventory Concepts

Track:

- current inventory
- average entry
- realized PnL
- unrealized PnL
- max favorable excursion
- max adverse excursion
- reload opportunity
- unload opportunity
- inventory turnover

## Safety Rules

Every inventory idea must have:

- max inventory cap
- max risk cap
- time remaining protection
- liquidity protection
- stop loss
- forced exit
- paper-only validation first
