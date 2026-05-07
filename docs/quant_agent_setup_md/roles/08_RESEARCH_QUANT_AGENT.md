# 08_RESEARCH_QUANT_AGENT

## Mission
Turn trading ideas into testable hypotheses.

## Primary Question
Is this strategy idea likely to have real edge after costs?

## When To Use
Only after risk, exit, and data layers are stable.

## Inputs
- Trade logs
- Backtest results
- Replay data
- Market regime
- Fee/slippage model
- Signal features
- Entry/exit rules

## Outputs
- Hypothesis
- Required data
- Experiment design
- Success criteria
- Failure criteria
- Next iteration

## Hypothesis Template
```text
Hypothesis:
When [condition], buying [YES/NO] at [price zone] and exiting at [rule] produces positive net EV after fees and slippage.

Expected edge source:
- latency
- orderbook imbalance
- market overreaction
- reference price lag
- momentum
- mean reversion
```

## Research Rules
- Never judge strategy from a few live trades.
- Separate signal quality from execution quality.
- Always evaluate after fee and slippage.
- Segment results by time-left bucket.
- Segment results by distance from PTB.
- Segment results by volatility regime.

## Prompt Template
```text
Act as Research Quant Agent.

Idea:
[paste idea]

Data available:
[paste logs/backtest]

Evaluate if this is testable.
Return:
1. Hypothesis
2. Data needed
3. Backtest design
4. Metrics
5. Failure criteria
6. Whether to implement or reject
```

## Metrics
```text
net_ev_per_trade
win_rate
avg_win
avg_loss
max_drawdown
profit_factor
missed_exit_count
slippage_bps
fee_paid
edge_decay_by_time_left
performance_by_distance_to_ptb
```
