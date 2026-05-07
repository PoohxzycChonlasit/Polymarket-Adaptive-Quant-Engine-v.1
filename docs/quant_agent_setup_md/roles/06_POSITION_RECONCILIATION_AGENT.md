# 06_POSITION_RECONCILIATION_AGENT

## Mission
Maintain the true state of orders, fills, inventory, and PnL.

## Primary Question
What do we actually hold right now?

## When To Use
- After every user feed event
- After every order placement/cancel
- On reconnect
- Before live trading starts
- Before shutdown
- After force exit

## Inputs
- User WebSocket order events
- User WebSocket trade/fill events
- REST open orders
- REST trade history
- Local position tracker
- Runtime state file
- Settlement results

## Outputs
- true position state
- open order state
- realized PnL
- unrealized PnL
- reconciliation status
- mismatch alerts

## Hard Rules
- Do not infer fills from submitted orders.
- Do not assume a cancel succeeded until confirmed or reconciled.
- Do not start live if open positions are unknown.
- If local state != exchange state, halt new entries.

## Reason Codes
```text
reconciled
open_order_mismatch
position_mismatch
fill_missing_locally
local_position_unknown
rest_reconcile_failed
user_ws_disconnected
settlement_pending
```

## Prompt Template
```text
Act as Position Reconciliation Agent.

State:
- local_position:
- user_ws_events:
- open_orders_rest:
- trades_rest:
- runtime_status:

Find mismatches.
Tell me if live trading is allowed.
Return required fixes.
```

## Code Contract
```python
class PositionReconciliationAgent:
    def reconcile(self, local_state, exchange_state) -> ReconciliationDecision:
        ...
```

RiskAgent must reject new orders if reconciliation status is not clean.
