# Bankroll Rank Engine

The Bankroll Rank Engine replaces fixed bankroll-risk sizing with smooth rank-based position sizing for Polymarket 5-minute binary markets.

## Rules

- No martingale.
- No all-in sizing.
- No fixed 20% bankroll risk.
- Base risk is selected from the current bankroll rank and interpolated inside that rank.
- Final size is reduced when confidence, EV, drawdown, spread, liquidity, delta, time-to-settlement, or trade frequency are unfavorable.
- A blocked sizing result returns zero executable size and a reason.

## Rank Table

| Rank | Bankroll | Base Risk Range | Max Trades/Hour |
|---|---:|---:|---:|
| SEED_TEST | $0-$25 | 3%-5% | 2-4 |
| MICRO | $25-$50 | 4%-6% | 3-5 |
| MICRO_PLUS | $50-$100 | 4%-5% | 4-6 |
| SMALL | $100-$250 | 3%-4% | 5-8 |
| SMALL_PLUS | $250-$500 | 2.5%-3.5% | 6-8 |
| BUILDER | $500-$1,000 | 2%-3% | 6-10 |
| GROWTH | $1,000-$2,500 | 1.5%-2.5% | 6-10 |
| GROWTH_PLUS | $2,500-$5,000 | 1%-2% | 5-8 |
| SERIOUS | $5,000-$10,000 | 0.75%-1.5% | 4-7 |
| CAPITAL_BASE | $10,000-$25,000 | 0.5%-1.25% | 3-6 |
| CAPITAL_PLUS | $25,000-$50,000 | 0.4%-1% | 3-5 |
| ADVANCED | $50,000-$100,000 | 0.25%-0.75% | 2-4 |
| PROFESSIONAL | $100,000+ | 0.1%-0.5% | 1-3 |

Inside each tier, `calculate_base_risk_pct()` linearly interpolates from the tier's high risk at the lower bankroll boundary to the tier's low risk at the upper boundary. Professional accounts taper from 0.5% toward 0.1% over the next $400k.

## Formula

```text
final_size =
bankroll
* tier_base_risk_pct
* confidence_multiplier
* ev_multiplier
* drawdown_multiplier
* liquidity_multiplier
* spread_multiplier
* time_to_settlement_multiplier
* delta_multiplier
* frequency_multiplier
```

All multipliers are capped at `1.0`, so the engine can reduce size but cannot boost beyond the rank base risk.

## Block Conditions

`calculate_position_size()` blocks the trade when any of these are true:

- `final_size < min_position_size_usd`
- daily loss limit reached
- hard drawdown reached
- `time_remaining_seconds <= 90`
- confidence below `confidence_floor`
- `ev <= 0`
- spread wider than `max_spread`
- liquidity below `min_liquidity_usd`
- current trades/hour has reached the rank cap

## Runtime Integration

`polymarket/order_manager.py` converts `PositionSizingResult` into the legacy `RiskPlan` shape expected by `polymarket/trader.py`. This preserves the existing order pipeline while moving the active sizing policy to:

- `polymarket/bankroll_tiers.py`
- `polymarket/position_sizing.py`

The old fixed 20% per-market exposure route is capped by the current bankroll rank's `max_market_exposure_pct` before an order can be submitted.
