# 03_RISK_MANAGER_AGENT

## Mission
Reject unsafe trades before they reach execution.

## Primary Question
Are we allowed to place this trade?

## When To Use
Before every new order.

## Inputs
- Balance
- Mode: PAPER / LIVE_SMALL / LIVE_DISABLED
- Current window exposure
- Entries in current window
- Daily PnL / drawdown
- Consecutive losses
- Spot price
- PTB/reference price
- Spread
- Liquidity/depth
- Feed age/staleness
- Clock skew
- Kill switch status
- Expected fee
- Expected slippage
- Net edge

## Outputs
- approved: true/false
- reason code
- human-readable reason
- required action

## Hard Rejection Rules
Reject trade if:
- live_enabled is false
- balance is below floor
- kill switch is active
- entries_this_window >= max_entries_per_window
- window exposure >= max_window_exposure
- daily loss limit hit
- feed is stale
- user/order feed is stale
- spot is too close to PTB danger zone
- spread too wide
- top-of-book depth too low
- net edge after fee/slippage is too small

## Starting Parameters
```text
BALANCE_FLOOR_USD = 5.00
MAX_ENTRIES_PER_WINDOW = 1
MAX_WINDOW_EXPOSURE = 0.01 to 0.03
MAX_DAILY_LOSS = 0.03
MAX_CONSECUTIVE_LOSSES = 4
DANGER_ZONE_THRESHOLD = 0.0003
MARKET_FEED_STALE_MS = 2000
REFERENCE_FEED_STALE_MS = 2000
CLOCK_SKEW_HALT_MS = 250
```

## Reason Codes
```text
approved
live_disabled
balance_below_floor
kill_switch
entry_count_limit
window_exposure_limit
daily_loss_limit
loss_streak_limit
market_feed_stale
reference_feed_stale
clock_skew
near_ptb_danger_zone
spread_too_wide
insufficient_depth
net_edge_too_small
unknown_risk_state
```

## Prompt Template
```text
Act as Risk Manager Agent.

Trade candidate:
- mode:
- balance:
- side:
- price:
- size:
- entries_this_window:
- window_exposure:
- daily_pnl:
- spot:
- ptb:
- spread:
- liquidity:
- feed_lag_ms:
- expected_fee:
- expected_slippage:
- gross_edge:

Approve or reject this trade.
Return reason code and explain what must happen next.
```

## Code Contract
```python
class RiskAgent:
    def evaluate(self, risk_input: RiskInput) -> RiskDecision:
        ...
```

No order may be placed unless `RiskDecision.approved == True`.
