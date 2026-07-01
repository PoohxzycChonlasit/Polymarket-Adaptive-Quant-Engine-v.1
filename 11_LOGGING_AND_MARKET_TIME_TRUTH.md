# 11 Logging And Market Time Truth

## Objective

All logs must match real market timing and market mechanics.

Any paper, replay, or live result is not valid profitability evidence if timing truth is missing, ambiguous, stale, or inconsistent with market mechanics.

## Timestamp Rule

All persisted timestamps must use UTC ISO-8601.

Do not mix local machine time with market source time.

## Required Time Fields

Every decision/trade log should distinguish these fields when available:

- `market_window_start_utc`
- `market_window_end_utc`
- `chainlink_reference_ts_utc`
- `source_orderbook_ts_utc`
- `local_receive_ts_utc`
- `decision_ts_utc`
- `order_submit_ts_utc`
- `order_ack_ts_utc`
- `fill_ts_utc`
- `close_ts_utc`
- `settlement_ts_utc`
- `data_age_ms`
- `decision_latency_ms`
- `submit_latency_ms`
- `fill_latency_ms`
- `clock_drift_status`

## Polymarket Crypto 5M Fields

Required when available:

- `asset`
- `market_slug`
- `condition_id`
- `token_id`
- `price_to_beat`
- `opening_reference_price`
- `final_reference_price`
- `resolved_outcome`
- `resolution_source`
- `seconds_since_open`
- `seconds_to_expiry`
- `clob_book_freshness_ms`
- `taker_delay_ms`

## Evidence Rule

Profit evidence is invalid if:

- Source timestamps are missing for a claim that depends on data freshness.
- Orderbook age is unknown.
- Decision timestamp is local-only and not UTC.
- Fill/close time cannot be tied to the market window.
- Market resolution source is ambiguous.
- Seconds to expiry is missing for entry/exit quality review.

## Operator Warning Rule

Dashboard and reports should warn when:

- Data age is stale.
- Clock drift is unknown or degraded.
- Market window mapping is missing.
- Paper sizing or fills are not market-realistic.

## Design Boundary

This document is a logging truth standard only. It does not authorize code changes, schema changes, or runtime behavior changes without a separate scoped task.
