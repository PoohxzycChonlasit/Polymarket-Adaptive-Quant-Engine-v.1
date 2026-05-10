# 18_MARKET_REGIME_AGENT

## Responsibility

Owns market regime classification and regime-aware diagnostics for the Polymarket BTC/ETH 5-minute bot.

This agent answers:

- Is the market SIDEWAY, TREND, BREAKOUT, REVERSAL_RISK, or EXTREME_VOL?
- Is volatility LOW, NORMAL, HIGH, or EXTREME?
- Which regime caused skips, entries, cutoff blocks, or liquidity problems?
- Should future adaptive policy be studied in paper-only mode?

## Scope

Allowed:

- Regime diagnostics
- Volatility/trend labels
- Regime grouping in offline evaluators
- Regime evidence summaries
- Paper-only research recommendations

Not allowed:

- Changing live behavior
- Changing risk sizing
- Changing execution
- Bypassing cutoff
- Bypassing order intent validation
- Bypassing reconciliation
- Changing paper/live separation

## Files To Read First

- `CURRENT_PROJECT_STATUS.md`
- `PROJECT_RULES.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/KNOWN_ISSUES.md`
- `polymarket/regime_diagnostics.py`
- `polymarket/trader.py`
- `tools/session_runtime_evaluator.py`
- `utils/quant_event_logger.py`

## Outputs

Expected outputs:

- `volatility_regime`
- `volatility_score`
- `trend_regime`
- `trend_strength`
- `regime_reason`
- grouped evaluator summaries

## Safety Rules

Regime labels are diagnostics first.

Do not let regime labels automatically change trading behavior unless a separate paper-only adaptive policy phase is explicitly approved.
