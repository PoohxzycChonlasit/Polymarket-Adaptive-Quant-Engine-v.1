# Runtime Replay-Key Blocker Audit

Run ID: `20260527T110608Z_26764_9d379e2c`

Audit date: 2026-05-27

Scope: read-only runtime blocker audit. No replay, bot run, runtime mutation, strategy change, execution change, commit, or push.

## Summary

The run has active signal and decision activity, but no downstream executable/path-truth materialization. Every run-scoped decision row carries a `paper_trade_replay_key`, but no trade journal rows, trade open rows, execution rows, path truth rows, or trade path checkpoints exist for this run.

Top blocker: `PATH_JOIN_0_77_BLOCKED_BY_NO_TRADE_OPEN`

Runtime state: `SIGNAL_REJECTED_NO_TRADE_OPEN`

## Required Counts

| Metric | Count | Source |
| --- | ---: | --- |
| candidate_count | 194 | unique `candidate_id` values in `runtime/quant_data/decision_log/2026-05-27.jsonl` |
| decision_count | 1400 | run-scoped decision rows |
| entry_intent_count | 0 | run-scoped entry intent markers in decision/research logs |
| trade_open_count | 0 | `runtime/quant_data/trade_journal/2026-05-27.jsonl` |
| path_checkpoint_count | 0 | `runtime/quant_data/path_truth/2026-05-27.jsonl` |
| risk_reject_count | 65 | decision rows with `risk_rejected`, `risk_plan_zero`, or zero-size plan markers |
| top_blocker | `PATH_JOIN_0_77_BLOCKED_BY_NO_TRADE_OPEN` | no opens, no path checkpoints, no path truth rows |
| runtime_state | `SIGNAL_REJECTED_NO_TRADE_OPEN` | decisions remain skipped/rejected before executable materialization |

## Runtime Evidence Inventory

| Evidence Area | Result |
| --- | --- |
| decision rows | 1400 rows from `2026-05-27T11:08:33.098485Z` to `2026-05-27T14:06:53.724875Z` |
| decision types | `skipped=1335`; `risk_rejected=65` |
| paper replay key rows | 1400 decision rows carry `paper_trade_replay_key` |
| trade journal rows | 0 run-scoped rows |
| trade close rows | 0 run-scoped rows |
| execution rows | 0 run-scoped rows |
| path truth rows | 0 run-scoped rows |
| readiness rows | 1400 decision rows include readiness fields |
| market activity rows | 1161 run-scoped market snapshot rows |
| system health rows | 1760 run-scoped health rows |
| paper runtime state | `mode=paper`, `paper_trading=True`, `open_positions=0` |

## Rejection Profile

Dominant normalized skip reasons:

| Reason | Count |
| --- | ---: |
| delta_extreme | 869 |
| time_unsafe | 239 |
| empty_book | 157 |
| risk_plan_zero | 65 |
| confidence_too_low | 41 |
| stale_data | 15 |
| ev_below_threshold | 8 |
| clob_http_error | 5 |
| orderbook_unavailable | 1 |

## Blocker Interpretation

The replay key exists at the decision layer, but the join remains blocked because there is no executable transition point. With `trade_open=0`, `trade_close=0`, `path_truth=0`, and `path_checkpoint_count=0`, there is no canonical path from decision evidence to trade path evidence.

`PATH_JOIN_0_77` therefore remains blocked by absence of trade-open/path-checkpoint materialization, not by absence of decision-layer replay keys.

## Operator Notes

- Treat this as blocker evidence only.
- Do not promote executable truth from these rows.
- Continue separating decision-layer replay keys from path truth.
- Next read-only review should focus on why skipped/rejected candidates do not produce entry intent or trade-open materialization.

## Safety

- Runtime repository was inspected read-only.
- No replay was run.
- No bot was run.
- No logs were modified.
- No strategy or execution files were changed.
- No executable approval or truth promotion was performed.
