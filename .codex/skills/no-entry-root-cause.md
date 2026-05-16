# Skill: No-Entry Root Cause

## Purpose

Diagnose zero-entry, zero-fill, or no-trade paper sessions without assuming the bot failed.

A no-entry session can be correct if the market was unsafe, EV was poor, liquidity was weak, spread was too wide, cutoff pressure dominated, or risk budget protected the bankroll.

## Required Inputs

- `runtime/research_state/latest_research_state.md` when available.
- Run-scoped offline reports under `runtime/reports/*.json`.
- `tools/no_entry_analyzer.py` output when available.
- `tools/replay_analyzer.py` output when available.
- `tools/session_runtime_evaluator.py` output when available.
- Data quality or continuity reports for the selected `run_id`.

## Required Analysis

Check all of these before assigning a root cause:

| Area | Questions |
|------|-----------|
| Cutoff | Did `time_unsafe`, hard-close, adaptive cutoff, or late-entry blocks dominate? |
| Liquidity | Was liquidity ready, recovering, stale, shallow, or missing? |
| Spread | Was spread executable after fees/slippage assumptions? |
| EV | Were EV fields visible, positive, and propagated to decisions? |
| Probability | Were probability/fair-value fields visible, missing, stale, or shadow-only? |
| Risk | Did `risk_plan_zero`, risk reject, LOCKDOWN, drawdown, or exposure cap block entry? |
| Bankroll tier | Did MICRO or tier floor make order size too small? |
| Lifecycle timing | Was the market in OPENING_SCAN, ACTIVE, PROFIT, FINAL_DERISK, or UNSAFE? |
| Orderbook | Were token IDs, YES/NO bids/asks, spread, and book age healthy? |

## Evidence Rules

- Separate missing evidence from negative evidence.
- Separate execution-log volume from true submit/fill/cancel attempts.
- Separate runtime summary counters from offline `trade_journal` evidence.
- Do not call execution the root cause unless an entry passed decision/risk and reached a true execution attempt/failure.

## Output Shape

Report:

1. selected run_id and evidence cutoff timestamp
2. continuity PASS/FAIL
3. analyze phase present or absent
4. lifecycle phase distribution
5. top blockers
6. EV/probability visibility
7. liquidity/orderbook readiness
8. risk/bankroll state
9. root cause verdict
10. confidence and caveats

## Forbidden

- Do not change strategy, cutoff, risk sizing, orderbook, execution, wallet, or live config.
- Do not wire analyzer output into runtime decisions.
- Do not bypass OrderIntent, reconciliation, stale-book, or risk gates.
