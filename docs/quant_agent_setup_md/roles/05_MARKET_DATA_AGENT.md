# 05_MARKET_DATA_AGENT

## Mission
Make sure the bot trades only when market data is fresh, aligned, and usable.

## Primary Question
Is the market data trustworthy right now?

## When To Use
Before signal generation and before every order decision.

## Inputs
- Polymarket orderbook feed status
- User/order feed status
- Reference price feed status
- Server time / local time skew
- Best bid / ask
- Spread
- Top-of-book depth
- Recent trades
- Market metadata
- Token IDs
- Window start/end time

## Outputs
- market_quality: GOOD / DEGRADED / HALT
- reason codes
- normalized market snapshot
- warning flags

## Data Quality Rules
Return HALT if:
- Market WebSocket stale > 2s
- Reference price stale > 2s
- User WebSocket stale while position open
- Clock skew > 250ms
- Orderbook crossed/invalid
- Token ID mismatch
- Market window unknown
- Spread/depth abnormal

## Reason Codes
```text
data_good
market_ws_stale
user_ws_stale
reference_feed_stale
clock_skew
invalid_orderbook
token_id_mismatch
unknown_window
spread_abnormal
depth_insufficient
market_rollover_uncertain
```

## Prompt Template
```text
Act as Market Data Agent.

Current market state:
- market:
- token_id_yes:
- token_id_no:
- best_bid:
- best_ask:
- spread:
- top_depth:
- market_ws_lag_ms:
- user_ws_lag_ms:
- reference_feed_lag_ms:
- server_clock_skew_ms:
- secs_left:

Classify market quality: GOOD / DEGRADED / HALT.
Explain whether the trading system may continue.
```

## Code Contract
```python
class MarketDataAgent:
    def evaluate(self, snapshot: MarketSnapshot) -> MarketQualityDecision:
        ...
```

SignalAgent and RiskAgent must consume this decision.
