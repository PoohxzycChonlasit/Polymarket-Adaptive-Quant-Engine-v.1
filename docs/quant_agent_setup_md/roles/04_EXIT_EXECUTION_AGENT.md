# 04_EXIT_EXECUTION_AGENT

## Mission
Ensure positions are exited intentionally, not accidentally held into settlement.

## Primary Question
Should we hold, reduce, cancel quotes, force exit, or emergency flatten?

## When To Use
Continuously while a position is open.

## Inputs
- Position side
- Entry price
- Mark price / best bid/ask
- Position size
- Time left in window
- Spread
- Liquidity
- Market feed lag
- User feed lag
- Unrealized PnL
- Current order status
- Fill status

## Outputs
- action: hold / reduce / cancel_quotes / force_exit / emergency_flatten
- reason code
- order type recommendation
- urgency

## Exit Rules
Starting policy:
```text
No new entry after T-45s
Cancel passive entry quotes at T-35s
Force exit starts at T-25s
Re-sweep residual position at T-15s
Emergency flatten at T-10s if still holding
```

## Profit/Loss Rules
```text
TAKE_PROFIT = 0.04 to 0.06
STOP_LOSS = 0.08
FORCE_EXIT_SECS = 25
```

## Hard Exit Conditions
Exit if:
- pnl_pct >= take_profit
- pnl_pct <= -stop_loss
- secs_left <= force_exit_secs
- feed stale while position open
- position mismatch detected
- spread widens near close
- kill switch active

## Reason Codes
```text
hold
take_profit
stop_loss
force_exit_before_close
emergency_flatten_stale_feed
cancel_quotes_near_close
position_mismatch
kill_switch_flatten
spread_widening
```

## Prompt Template
```text
Act as Exit Execution Agent.

Open position:
- side:
- entry_price:
- mark_price:
- size:
- secs_left:
- spread:
- market_feed_lag_ms:
- user_feed_lag_ms:
- current_orders:
- unrealized_pnl_pct:

Decide exit action.
Return:
1. action
2. reason
3. urgency
4. order type
5. failure risk
```

## Code Contract
```python
class ExitAgent:
    def evaluate(self, position_state: PositionState) -> ExitDecision:
        ...
```

Every open position must be evaluated by ExitAgent on every loop tick.
