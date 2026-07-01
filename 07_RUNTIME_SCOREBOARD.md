# 07 Runtime Scoreboard

## Purpose

The runtime scoreboard is the operator's first truth surface for the Profit Engine.

It should answer:

- Are we making money?
- If not, why not?
- Is the system protecting capital or missing valid opportunities?
- Is the market data fresh and market-time accurate?
- Is paper execution realistic enough to trust?

## Scoreboard Sections

### Profit Engine Header

- Mode.
- Live status.
- Bankroll.
- Equity.
- Daily PnL.
- Session PnL.
- Open positions.
- Risk mode.
- Current bottleneck.

### Trade Funnel

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

### Gate Blocker Board

- Blocker counts.
- Protective or over-conservative label.
- Would-be EV if available.
- MFE/MAE evidence if available.
- Near-miss count.

### Quant Metrics

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

### Market Reality / Sizing Reality

- Tick size.
- Minimum order.
- Fee assumption.
- Taker delay.
- Spread.
- Liquidity.
- Fillability.
- Current sizing mode.
- Paper realism warning.

### Time Truth / Data Freshness

- Data age.
- Orderbook freshness.
- Clock drift.
- Seconds to expiry.
- Source timestamps.
- Stale-data warning.

### Operator Action Panel

- Current bottleneck.
- Next action.
- Do-not-do list.
- Evidence status.

## Scoreboard Validity Rule

Scoreboard metrics are not profitability evidence unless time truth, cash/exposure/PnL reconciliation, and execution realism are present.

## Latest Audit Snapshot

`PROFIT_ENGINE_ENTRY_THROUGHPUT_MARKET_REALISM_AUDIT_001` classifies current scoreboard readiness as PARTIAL.

- Trade funnel evidence exists, but one canonical per-run funnel row is still needed.
- Gate blocker counts are available and useful.
- Market/sizing reality is partial because fractional-share and minimum-order live behavior are not proven.
- Time-truth evidence is partial because current logs have timing proxies, but not all canonical field names from `11_LOGGING_AND_MARKET_TIME_TRUTH.md`.
- Current data is valid for blocker diagnosis and paper accounting, not for a profitability claim.

## Canonical Evidence Requirement

Before the scoreboard is treated as a profit surface, it should consume a per-run evidence summary with:

- `trade_funnel_summary_v1`
- `market_time_truth_field_map_v1`
- `dashboard_data_availability_v1`
- `evidence_validity_v1`

Until those are available, dashboard values are operational diagnostics, not profitability proof.
