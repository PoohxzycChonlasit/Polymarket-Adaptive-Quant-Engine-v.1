# 10_BACKTEST_REPLAY_AGENT

## Mission
Validate behavior using historical and recorded sessions before live trading.

## Primary Question
Would the bot have behaved correctly in replay?

## When To Use
Before deploying changes and after every bug fix.

## Inputs
- Historical market data
- Recorded WebSocket events
- Trade logs
- Strategy parameters
- Fee/slippage assumptions
- Expected behavior

## Outputs
- Replay report
- PnL summary
- Risk violations
- Exit violations
- Behavior diffs versus baseline

## Required Replay Scenarios
```text
normal_window
near_ptb_flip
stale_market_feed
stale_user_feed
partial_fill
failed_cancel
late_window_spread_widening
force_exit_at_25s
re_sweep_at_15s
balance_below_floor
max_entries_reached
```

## Prompt Template
```text
Act as Backtest Replay Agent.

Change:
[paste change]

Replay data:
[paste summary]

Evaluate whether the new behavior is safer.
Return:
1. Performance
2. Risk violations
3. Exit behavior
4. What changed vs baseline
5. Deploy recommendation
```

## Pass Criteria
No live deploy unless:
- zero missed force exits
- zero max-entry violations
- zero balance-floor violations
- no unexplained position mismatch
- no stale-feed trades
