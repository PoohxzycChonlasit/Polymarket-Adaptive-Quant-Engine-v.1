# Skill: Session Regime Analysis

## Purpose

Analyze time-of-day and session market personality for Polymarket BTC/ETH 5-minute markets.

This is observability and research only. It does not authorize strategy, threshold, sizing, or runtime behavior changes.

## Required Dimensions

| Dimension | Required View |
|-----------|---------------|
| `hour_utc` | Count decisions, entries, skips, fills, PnL, and bad data by hour. |
| `session_type` | Compare Asia, Europe, US, overlap, quiet, and high-volatility windows when labels exist. |
| Volatility by hour | Group volatility regime, realized move, PTB/oracle movement, and compression by hour. |
| Liquidity by hour | Compare orderbook readiness, book age, empty/stale states, depth, and recovery. |
| Spread/fill quality | Compare spread width, executable spread, paper fills, exits, and slippage proxy by session. |
| Replay research | Use run-scoped replay and trade_journal evidence to avoid whole-day contamination. |

## Method

1. Select a run_id or date range.
2. Verify continuity and bad JSON impact.
3. Build hour/session distributions.
4. Compare blocker mix by hour:
   - `time_unsafe`
   - `risk_plan_zero`
   - `spread_too_wide`
   - `no_orderbook`
   - `stale_data`
   - `confidence_too_low`
   - `ev_below_threshold`
5. Compare paper trade evidence by hour:
   - trade count
   - fills
   - exits
   - gross PnL
   - win/loss count
6. Label uncertainty and sample size.

## Safety Boundary

Session findings are research evidence only. They must not automatically change runtime cadence, cutoff thresholds, strategy thresholds, risk sizing, live flags, or execution behavior.

## Output Shape

Report:

1. run/date scope
2. continuity status
3. strongest hour/session patterns
4. best and worst liquidity windows
5. best and worst spread/fill windows
6. blocker mix by session
7. whether evidence is sufficient for session-aware replay research
8. exactly 3 future options using `QUANT_FUTURE_DECISION_ENGINE.md`
