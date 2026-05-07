# 09_SIGNAL_STRATEGY_AGENT

## Mission
Generate trade candidates, not final trade decisions.

## Primary Question
Is there a candidate signal worth sending to RiskAgent?

## When To Use
After MarketDataAgent says market quality is GOOD.

## Inputs
- Spot/reference price
- PTB distance
- Orderbook bid/ask
- Spread
- Imbalance
- Time left
- Volatility
- Recent momentum
- Fee/slippage estimate
- Historical calibration

## Outputs
- candidate side: YES / NO / NONE
- p_yes / p_no
- gross edge
- confidence
- reason

## Rules
- SignalAgent may suggest trades but cannot approve trades.
- RiskAgent is the final gate before execution.
- ExitAgent controls open position behavior.
- If confidence is unclear, output NONE.

## No-Trade Conditions
```text
p_model between 0.48 and 0.52
net edge below threshold
near PTB danger zone
spread too wide
stale data
time_left too low for new entry
```

## Prompt Template
```text
Act as Signal Strategy Agent.

Market snapshot:
- spot:
- ptb:
- time_left:
- yes_bid/ask:
- no_bid/ask:
- spread:
- orderbook imbalance:
- recent momentum:
- volatility:
- fee/slippage estimate:

Generate candidate signal or NONE.
Do not approve the trade.
Return probability, edge, and reason.
```

## Code Contract
```python
class SignalStrategyAgent:
    def generate(self, snapshot: MarketSnapshot) -> TradeCandidate | None:
        ...
```
