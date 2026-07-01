# 08 Mini Evidence Pipeline

## Purpose

Keep the evidence pipeline small until profitability exists.

## Pipeline

```text
Replay
-> Counterfactual
-> Paper Runtime
-> PnL Review
```

## Stage 1 - Replay

Question:

- What did current evidence say happened?

Outputs:

- Entry counts.
- Gate blockers.
- EV and confidence distributions.
- Timing and orderbook quality.
- Existing PnL and lifecycle truth where available.

## Stage 2 - Counterfactual

Question:

- Which single gate or assumption suppresses plausible entries?

Rules:

- Relax one gate at a time.
- Do not claim profitability.
- Flag stale data, late cutoff, low liquidity, negative EV, and unrealistic sizing.

## Stage 3 - Paper Runtime

Question:

- Does the hypothesis survive live market data in paper mode?

Rules:

- Paper only.
- No threshold changes unless separately scoped.
- Capture run ID, duration, fills, closes, PnL, exposure, cash, risk mode, and live markers.

## Stage 4 - PnL Review

Question:

- Did the paper run improve expectancy or reveal the true bottleneck?

Outputs:

- Expectancy.
- Profit factor.
- Drawdown.
- Entry throughput.
- Gate blocker shift.
- Time-truth validity.
- Execution realism caveats.

## Anti-Expansion Rule

Do not build a larger research lab until the mini pipeline fails to answer a clearly profit-relevant question.
