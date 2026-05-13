# Inventory Replay Research Plan

> Status: Phase 2 research plan.
> Scope: offline and paper-only analysis. No runtime inventory execution.

## Purpose

Before building inventory trading, use paper-session evidence to answer whether bounded reload/unload behavior would have improved outcomes or simply increased risk.

## Research Questions

- Did a valid candidate appear too early, too late, or at the wrong price?
- What was MFE after candidate formation?
- What was MAE after candidate formation?
- Was there a cheaper reload opportunity?
- Was there a profitable unload opportunity?
- Did opportunity half-life decay before execution conditions became healthy?
- Which regimes produce repeatable reload/unload opportunity?

## Required Metrics

- candidate timestamp
- market regime at candidate
- entry price candidate
- lowest reachable price after candidate
- highest reachable price after candidate
- MFE
- MAE
- seconds to MFE
- seconds to MAE
- reload opportunity
- unload opportunity
- opportunity half-life
- liquidity/spread state at each opportunity

## Forbidden Work

- Do not feed replay output into runtime decisions.
- Do not change live or paper execution.
- Do not change thresholds or risk sizing.
- Do not use hindsight as a live signal.
- Do not claim profitability from theoretical replay alone.

## Agent Ownership

Primary:

- `22_INVENTORY_ANALYTICS_AGENT.md`

Supporting:

- `10_BACKTEST_REPLAY_AGENT.md`
- `18_MARKET_REGIME_AGENT.md`
- `21_EXECUTION_MICROSTRUCTURE_AGENT.md`

## Promotion Gate

Only move to a bounded inventory design after repeated paper sessions show that reload/unload opportunities are regime-repeatable, liquidity-feasible, and risk-contained.

