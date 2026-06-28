# Market Microstructure Research Plan

> Status: active research direction.
> Scope: offline/paper diagnostics first. No spread, cutoff, or execution loosening.

## Purpose

Determine whether no-entry and missed-opportunity behavior is caused by signal quality, timing compression, spread width, liquidity readiness, or orderbook recovery timing.

## Research Areas

- spread normalization timing
- spread compression velocity
- empty-book and transient orderbook recovery
- liquidity readiness by regime
- candidate timing before cutoff
- adverse selection risk
- fill feasibility for micro bankroll sizes
- SIDEWAY vs TREND spread behavior
- NORMAL_VOL vs EXTREME_VOL spread behavior

## Required Outputs

- spread compression summary
- liquidity readiness summary
- candidate gap summary
- regime spread matrix
- candidate timing by regime
- repeated no-entry patterns
- market-selection/liquidity-quality recommendation

## Forbidden Work

- Do not loosen spread filters.
- Do not loosen cutoff.
- Do not change EV or confidence thresholds.
- Do not change risk sizing.
- Do not change execution behavior.
- Do not add adaptive runtime policy without a separate approved phase.

## Agent Ownership

Primary:

- `21_EXECUTION_MICROSTRUCTURE_AGENT.md`

Supporting:

- `14_NO_ENTRY_DIAGNOSTICS_AGENT.md`
- `18_MARKET_REGIME_AGENT.md`
- `10_BACKTEST_REPLAY_AGENT.md`

