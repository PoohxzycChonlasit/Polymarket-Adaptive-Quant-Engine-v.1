# 01 Success Criteria

## Profit Engine Success

The project is succeeding when paper runtime shows repeatable positive expectancy under market-realistic assumptions.

## Required Evidence Before Micro Live

Micro live remains blocked until all conditions below are met:

| Area | Minimum Standard |
|---|---|
| Expectancy | Positive expectancy across enough closed paper trades to reduce luck/noise risk. |
| Drawdown | Max drawdown controlled and consistent with current bankroll rank. |
| Equity curve | Stable or growing after fees, spread, slippage, and realistic fill assumptions. |
| Entry throughput | Enough entries per session/day to learn and compound evidence. |
| Execution realism | Paper sizing, shares, tick size, fees, spread, liquidity, and fillability reflect market mechanics. |
| Time truth | Logs carry market window, source timestamp, local receive, decision, submit, fill, close, and settlement timing where available. |
| Operator visibility | Dashboard or status surfaces current bottleneck, risk mode, PnL, and gate blockers. |
| Runtime stability | 24/7 paper mode can run without unsafe state drift, owner lock leaks, live markers, or unbounded logs. |

## Evidence Grades

| Grade | Use |
|---|---|
| A | Runtime observed in paper/live logs, JSONL, terminal output, or generated state. |
| B | Source verified by reading code. |
| C | Test verified. |
| D | Documentation aligned. |
| E | Inferred only; never enough for profit or live claims. |

## Paper Profit Evidence Gate

Evidence is not valid if any are missing or ambiguous:

- Market-time truth.
- Orderbook freshness.
- Fillability or execution realism.
- Position sizing realism.
- Cash/exposure/PnL reconciliation.
- Exit reason and close/PnL accounting.

## Failure Is Useful If It Is Truthful

A losing paper run can still be useful if it identifies the real bottleneck:

- Bad EV.
- Low confidence.
- Excess spread.
- Low liquidity.
- Late timing.
- Bad sizing geometry.
- Poor exit behavior.
- Market regime mismatch.
- Runtime/accounting issue.

## Current Promotion Status

Live readiness: NOT READY.

Micro live: BLOCKED until paper profitability evidence exists and live order/fill/cancel/reconciliation is separately validated.
