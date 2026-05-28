# ORDERBOOK_LINEAGE_PROBE_V1 Schema Completion Report

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Mode: implementation, observability only.

## Executive Verdict

The missing canonical alias fields from the paper validation gap review have been added to the existing `ORDERBOOK_LINEAGE_PROBE_V1` payload builder.

This is additive schema completion only. It does not consume probe fields in policy, change orderbook fetch behavior, change retry behavior, change gates, change strategy, change risk, change execution, infer executable truth, or promote `PAPER_VALIDATED`.

Fresh paper evidence is still required before promoting the probe lifecycle state.

## Files Changed

Code:

- `polymarket/trader.py`

Tests:

- `tests/test_orderbook_lineage_probe_v1.py`

Docs:

- `docs/research/runtime_health/orderbook_lineage_probe_v1_schema_completion_report.md`

## Fields Added

Canonical aliases added:

- `book_used_for_decision`
- `book_used_token_pair_match`
- `empty_book_role`
- `serialized_book_source`
- `serialized_yes_no_bid_ask_present`
- `serialized_depth_present`
- `serialized_spread_present`
- `terminal_skip_reason`
- `terminal_gate_stage`
- `yes_normalization_status`
- `no_normalization_status`

Existing fields were preserved:

- `book_used_for_decision_source`
- `book_used_for_decision_token_pair_key`
- `terminal_blocker`
- `terminal_blocker_stage`
- `serialized_truth_source`
- `normalization_status`
- `contextual_blockers`

## Field Derivation

| New field | Source | Fallback |
|---|---|---|
| `book_used_for_decision` | Existing `book_used_for_decision_source`. | `unknown` when source is unknown. |
| `book_used_token_pair_match` | Current token pair presence for current fetch, otherwise `cache_token_pair_match`. | `null` when unknown. |
| `empty_book_role` | `terminal_blocker`, `contextual_blockers`, and `orderbook_readiness_reason`. | `unknown` when source status is unknown. |
| `serialized_book_source` | Existing `book_used_for_decision_source` / executable state. | `unknown` when source is unknown. |
| `serialized_yes_no_bid_ask_present` | Current executable YES/NO book boolean. | `false` when not executable. |
| `serialized_depth_present` | Current executable YES/NO book boolean. | `false` when not executable. |
| `serialized_spread_present` | Current executable YES/NO book boolean. | `false` when not executable. |
| `terminal_skip_reason` | Existing `terminal_blocker`. | `null` when no terminal blocker exists. |
| `terminal_gate_stage` | Existing `terminal_blocker_stage`, canonicalized from `market_data_orderbook` to `market_data`. | `none` for non-terminal observed rows, `unknown` when status is unknown. |
| `yes_normalization_status` | Existing `yes_fetch_status`. | `unknown` when side status is unknown or fetch failed. |
| `no_normalization_status` | Existing `no_fetch_status`. | `unknown` when side status is unknown or fetch failed. |

## Canonical Value Behavior

Book-used alias:

- `current_fetch` when current executable YES/NO book is used.
- `unavailable` when no book is used because current fetch failed or is non-executable.
- `unknown` when source is not observable.

Empty-book role:

- `terminal` when `empty_book` or `empty_orderbook` is the terminal blocker.
- `contextual` when empty-book evidence is present in contextual blockers but not terminal.
- `absent` when current observed lineage has no empty-book role.
- `unknown` when the source state itself is unknown.

Side normalization aliases:

- `accepted_executable` for executable side fetches.
- `rejected_empty_bids`, `rejected_empty_asks`, or `rejected_empty_both` for side-specific empty-book states.
- `rejected_stale` for stale side status.
- `rejected_invalid_price` for invalid side status.
- `not_attempted` for not-attempted side status.
- `unknown` when source data does not support a canonical claim.

## Unavailable Fields And Fallback Behavior

No new field fabricates runtime truth.

When source data is missing:

- terminal reason stays `null`;
- terminal gate stage becomes `unknown` or `none` depending on whether the row is observable but non-terminal;
- side-specific normalization becomes `unknown`;
- book-used truth becomes `unknown`;
- token-pair match becomes `null`;
- serialized booleans stay `false` unless current executable YES/NO top-of-book exists.

## Tests Run

Red test first:

```text
python -m pytest tests/test_orderbook_lineage_probe_v1.py -q
```

Expected failure before implementation:

```text
4 failed, 3 passed
```

Required final regression command:

```text
python -m pytest tests/test_orderbook_lineage_probe_v1.py tests/test_empty_orderbook_fail_soft.py tests/test_quant_event_logger.py tests/test_logging_resilience.py -q
```

Final result:

```text
24 passed
```

Warnings observed:

- Existing third-party `websockets` deprecation warnings from installed dependencies.

## Runtime Safety Confirmation

This patch:

- adds only derived alias fields to an existing probe payload;
- does not add policy consumers;
- does not branch runtime decisions on probe fields;
- does not alter orderbook fetch behavior;
- does not alter retry behavior;
- does not alter gates;
- does not alter strategy, risk, sizing, execution, live config, or replay;
- does not emit raw orderbook arrays;
- does not add hot-loop joins;
- preserves backward-compatible existing probe fields.

Runtime behavior changed: observability schema only.

Live behavior changed: No.

Strategy/risk/execution changed: No.

Threshold tuning: No.

Replay execution: No.

PAPER_VALIDATED promotion: No; fresh paper evidence must confirm emitted canonical fields first.
