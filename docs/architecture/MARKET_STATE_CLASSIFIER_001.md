# Polymarket Adaptive Quant Runtime - Market State Classifier v1 Spec

## 1. Executive Summary & Objective
The **Market State Classifier v1** introduces a passive, explainable labelling engine to characterize Polymarket 5-minute binary prediction markets. By categorizing market conditions before decision cycles, it provides reasoning context to telemetry logs (solving the lack of market state context in Telegram/TUI alerts) without altering live trading risks or strategies.

---

## 2. Market State Classifications
The classifier outputs one of nine distinct market state labels:
1. **`TREND_CONTINUATION`**: Strongly trending price movement with narrow spreads and high book momentum.
2. **`MEAN_REVERSION`**: Price deviates significantly from moving average averages with high exhaustion signals.
3. **`CHOP`**: Low-volatility sideways range-bound action with frequent direction reversals.
4. **`LOW_LIQUIDITY`**: Insufficient depth in top YES/NO order books to absorb standard scale orders.
5. **`WIDE_SPREAD`**: Bid-ask spread exceeds normal thresholds (e.g. > $0.05).
6. **`STALE_QUOTE`**: Last received orderbook quote exceeds age threshold (e.g. > 5,000ms).
7. **`LATE_MARKET`**: Time remaining to market resolution is less than threshold (e.g. < 60 seconds).
8. **`NO_EDGE`**: Spread/imbalance indicates fair pricing matches current probability estimation.
9. **`UNKNOWN`**: Input criteria corrupt, incomplete, or fails to resolve to a defined state.

---

## 3. Required Input Fields
The classifier aggregates the following metrics:
- **`price`** (float): Current middle price between bid/ask.
- **`spread`** (float): Current absolute difference between bid and ask prices.
- **`liquidity`** (float): Combined dollar depth within $0.05 of the inside market.
- **`quote_age_ms`** (integer): Difference between current timestamp and last quote timestamp.
- **`time_remaining`** (integer): Time in seconds until market resolution.
- **`recent_price_movement`** (float): Standard deviation of price changes over the past 30 cycles.
- **`orderbook_imbalance`** (float): Ratio of bids to asks at top levels.
- **`lifecycle_phase`** (string): Active loop phase designation.
- **`session_cycle`** (integer): Monotonically increasing loop cycle identifier.

---

## 4. Input Telemetry Status
- **Existing Fields**: `price`, `spread`, `quote_age_ms`, `time_remaining`, `session_cycle` are already resolved in current memory.
- **Telemetry Only (New)**: `liquidity`, `recent_price_movement`, `orderbook_imbalance` will be extracted passively in subsequent observability tasks without modification to strategy structures.

---

## 5. Output Schema
The classification outputs are serialized to JSON matching this contract:
```json
{
  "market_state": "TREND_CONTINUATION | MEAN_REVERSION | CHOP | LOW_LIQUIDITY | WIDE_SPREAD | STALE_QUOTE | LATE_MARKET | NO_EDGE | UNKNOWN",
  "confidence": 0.85,
  "reason_codes": ["MOMENTUM_BUY_PRESSURE", "LOW_SPREAD"],
  "blockers": [],
  "evidence_fields": {
    "spread_cents": 2.0,
    "quote_age_ms": 120
  },
  "recommended_action": "ALLOW | WARN | BLOCK | UNKNOWN"
}
```

---

## 6. Telegram Telemetry Schema
When a trading action occurs, Telegram alerts will incorporate the market state context:
```text
🔔 Polymarket Entry Alert
Task/Cycle: BATCH_3C / Cycle 142
Action: YES Buy
Price: $0.54
Market State: TREND_CONTINUATION (Confidence: 85%)
Reason: momentum buy pressure, low spread
Blockers: None
```

---

## 7. Validation & Replay Strategy
- **Telemetry Auditing**: Log scan verification to assert presence of `market_state` on every loop event payload.
- **Expectancy Audits**: Post-run replay analysis grouping realized PnL and win rate distributions by `market_state` to evaluate model predictive power.
- **False-Positive Analysis**: Diagnostic scanning to identify loops categorized as `TREND_CONTINUATION` that reverted immediately.
