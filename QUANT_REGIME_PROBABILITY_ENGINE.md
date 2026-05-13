# Quant Regime Probability Engine

> Status: Phase 1 diagnostics foundation.
> Scope: regime/probability thinking only. No execution, risk, sizing, cutoff, or paper/live behavior changes.

## Purpose

Move the project from simple ENTER / SKIP thinking toward probability and regime interpretation.

The current Phase 1 objective is to observe:

- current market regime
- bullish and bearish probability estimates
- trend strength
- reversal risk
- volatility score
- indicator evidence
- how those fields relate to no-entry, cutoff, spread, and liquidity outcomes

These fields are diagnostics. They are not trade approvals.

## Phase 1 Allowed Work

- Lightweight regime classification from candles and market structure.
- Probability scoring as a research estimate.
- Indicator evidence summaries such as RSI, EMA slope, ATR, VWAP deviation, volatility, and momentum persistence.
- Terminal, decision-log, and JSONL visibility.
- Offline evaluator grouping by regime and probability buckets.

## Phase 1 Forbidden Work

- No execution behavior change.
- No inventory scaling.
- No reload/unload runtime logic.
- No live behavior changes.
- No strategy threshold loosening.
- No risk sizing changes.
- No cutoff bypass.
- No spread-filter bypass.
- No OrderIntent, reconciliation, stale-data, forced-exit, or panic-exit bypass.

## Current Labels

Primary research labels:

- `TREND_UP`
- `TREND_DOWN`
- `SIDEWAY`
- `EXTREME_VOL`
- `COMPRESSION`

Existing compatibility labels may remain in place:

- `volatility_regime`
- `trend_regime`
- `regime_reason`

## Required Output Fields

- `market_regime`
- `bullish_probability`
- `bearish_probability`
- `trend_strength`
- `reversal_risk`
- `volatility_score`
- `compression_score`
- `indicator_evidence`

## Agent Ownership

Primary:

- `18_MARKET_REGIME_AGENT.md`

Supporting:

- `09_SIGNAL_STRATEGY_AGENT.md`
- `10_BACKTEST_REPLAY_AGENT.md`
- `11_OBSERVABILITY_INCIDENT_AGENT.md`

## Validation

Phase 1 is validated by paper-session observability and offline analysis only. Any future use of these fields for runtime policy requires a separate scoped task and explicit approval.

