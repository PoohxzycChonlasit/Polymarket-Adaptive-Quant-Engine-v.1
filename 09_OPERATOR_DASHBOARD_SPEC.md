# 09 Operator Dashboard Spec

## Objective

Design an operator dashboard for the Profit Engine. The dashboard must make profit status, bottlenecks, market realism, sizing realism, and time truth visible without changing trading behavior.

## 1. Profit Engine Header

Fields:

- Mode.
- Live status.
- Bankroll.
- Equity.
- Daily PnL.
- Session PnL.
- Open positions.
- Risk mode.
- Current bottleneck.

Rules:

- Paper/live source labels must be explicit.
- Live status must never imply live readiness unless validated.

## 2. Trade Funnel

Fields:

- Decisions.
- Tradable markets.
- Candidates.
- EV pass.
- Risk approved.
- Order intents.
- Orders sent.
- Fills.
- Closes.
- Net PnL.

Purpose:

- Show where opportunities disappear.
- Separate no-entry protection from broken execution.

## 3. Gate Blocker Board

Fields:

- Blocker counts.
- Protective or over-conservative classification.
- Would-be EV if available.
- MFE/MAE evidence if available.
- Top near misses.

Purpose:

- Identify the gate most likely to suppress valid profit opportunities.

## 4. Quant Metrics Board

Fields:

- Expectancy.
- Profit factor.
- Win rate.
- Average win.
- Average loss.
- Max drawdown.
- MFE.
- MAE.
- TP count.
- SL count.
- Average hold time.

Validity:

- Metrics must show sample count.
- Metrics must warn when sample is too small.

## 5. Market Reality / Sizing Reality

Fields:

- Tick size.
- Minimum order.
- Fee.
- Taker delay.
- Spread.
- Liquidity.
- Fillability.
- Current sizing mode.
- Warning if paper sizing is not market-realistic.

Purpose:

- Prevent false paper profit caused by unrealistic shares, fills, or fees.

## 6. Time Truth / Data Freshness

Fields:

- Data age.
- Orderbook freshness.
- Clock drift.
- Seconds to expiry.
- Market window timestamps.
- Source timestamps.
- Stale-data warning.

Purpose:

- Prevent false profit evidence from stale or ambiguous timing.

## 7. Operator Action Panel

Fields:

- Current bottleneck.
- Next action.
- Do-not-do list.
- Evidence status.

Example next actions:

- Run entry throughput audit.
- Run market-time truth audit.
- Run paper sizing realism audit.
- Continue paper runtime only if current evidence is valid.

## Dashboard Boundary

The dashboard must not contain trading decision logic. It may display decisions, blockers, and metrics, but it must not approve trades.

## Current Data Availability

As of `CANONICAL_EVIDENCE_AND_MARKET_TIME_TRUTH_INSTRUMENTATION_001`, dashboard readiness is:

| Board | Status |
|---|---|
| Profit Engine Header | PARTIAL |
| Trade Funnel | PARTIAL |
| Gate Blocker Board | AVAILABLE |
| Quant Metrics Board | PARTIAL |
| Market Reality / Sizing Reality | PARTIAL |
| Time Truth / Data Freshness | PARTIAL |
| Operator Action Panel | AVAILABLE |

The dashboard should show an evidence-validity warning until canonical per-run summaries provide normalized time truth, market/sizing realism, and cost realism.
