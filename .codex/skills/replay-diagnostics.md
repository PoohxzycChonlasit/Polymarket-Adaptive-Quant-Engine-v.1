# Skill: Replay Diagnostics

## Purpose

Analyze offline replay evidence across JSONL categories and generated reports.

This skill is for evidence quality, semantic consistency, and report trust. It does not change runtime behavior.

## Source Categories

Inspect run-scoped counts for:

| Category | Expected Role |
|----------|---------------|
| `trade_journal` | Paper `trade_open` and `trade_close` evidence, PnL, fill receipts. |
| `execution_log` | Execution-stage diagnostics, submit attempts, paper fills, failures. |
| `decision_log` | Approved/rejected/skipped decisions and blockers. |
| `risk_log` | Risk events, risk-plan-zero, risk mode, tier, exposure clues. |
| `market_snapshots` | Orderbook, spread, liquidity, timing, token/readiness state. |
| `system_health` | Runtime health, cycle timing, summary counters, logging state. |
| `research_log` | Shadow research, lifecycle/probability/regime observability. |

## Required Checks

1. Count exact events by `category` and `event_type`.
2. Count execution payload events separately from top-level `event_type`.
3. Compare replay report totals against raw JSONL.
4. Compare session health counters against offline evidence.
5. Identify stale or misnamed counters.
6. Separate malformed JSON impact from selected-run evidence.
7. Separate true execution attempts/failures from diagnostic event volume.
8. State whether replay trade/PnL counts are trustworthy.

## Known Mismatch Risks

- Runtime summary counters can be stale or zero while `trade_journal` proves paper opens/closes.
- `execution_log` volume can be high without true submit/fill/cancel failures.
- Whole-day malformed JSON can fail quality while a selected run_id is still trustworthy.
- Replay can count closed trades from `trade_close` even when a session summary field is misnamed.
- Research/shadow fields can be present but not runtime decision authority.

## Output Shape

Report:

1. selected run_id
2. event counts by category and event_type
3. report sources used by each analyzer
4. mismatch root cause
5. corrected interpretation
6. trade/PnL trust verdict
7. caveats
8. tests or checks run

## Forbidden

- Do not repair JSONL unless explicitly scoped.
- Do not modify JSONL writers.
- Do not modify runtime execution or strategy.
- Do not wire offline evidence into runtime decisions.
