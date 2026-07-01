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
