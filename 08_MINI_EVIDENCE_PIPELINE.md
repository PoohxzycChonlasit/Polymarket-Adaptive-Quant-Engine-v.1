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

- Canonical per-run evidence summary JSON from `tools/canonical_run_evidence_summary_builder.py`.
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

## Current Pipeline State

Latest tooling report: `docs/reports/CANONICAL_RUN_EVIDENCE_SUMMARY_BUILDER_001.md`.

Current finding:

- Replay/counterfactual evidence identifies `risk_plan_zero` and `delta_extreme` as the most useful near-miss research targets.
- Paper runtime evidence proves accounting paths, but entry throughput is too low for profitability inference.
- Per-run evidence summaries are now canonicalized offline; the next evidence step should remain offline and consume those summaries before any shadow outcome replay with MFE/MAE, TP-hit, SL-hit, and settlement/path truth joins.
- Recent CLOB-compliant paper evidence summaries surfaced `book_warming`, but raw decision rows showed `risk_off` / `risk_mode_lockdown:hard_drawdown`. Treat classifier summaries as diagnostic overlays until raw-vs-classified blockers are shown side by side.
- Canonical summaries now include raw runtime blocker summaries, classified blocker summaries, and conflict summaries so replay/paper review can distinguish safety gates from classifier labels.
