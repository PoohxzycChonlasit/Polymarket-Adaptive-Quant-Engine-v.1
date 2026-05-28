# ORDERBOOK_LINEAGE_PROBE_V1 Implementation Report

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Mode: scoped implementation, observability only.

## Executive Verdict

`ORDERBOOK_LINEAGE_PROBE_V1` is implemented as an additive, fail-soft runtime JSONL probe.

It emits compact orderbook lineage evidence to:

```text
runtime/quant_data/orderbook_lineage/YYYY-MM-DD.jsonl
```

The probe has no policy authority and is not consumed by strategy, risk, sizing, execution, order placement, thresholds, live configuration, replay, or readiness promotion.

## Files Changed

Code:

- `polymarket/trader.py`
- `utils/quant_event_logger.py`

Tests:

- `tests/test_orderbook_lineage_probe_v1.py`

Docs:

- `docs/research/runtime_health/orderbook_lineage_probe_v1_design.md`
- `docs/research/runtime_health/orderbook_lineage_probe_v1_implementation_report.md`

## Runtime Producer

Producer:

```text
PolymarketTrader._emit_orderbook_lineage_probe(...)
```

Builder:

```text
PolymarketTrader._build_orderbook_lineage_probe_payload(...)
```

Logger method:

```text
QuantEventLogger.log_orderbook_lineage_probe(...)
```

Producer label:

```text
orderbook_lineage
```

## Fields Emitted

Probe identity:

- `probe_id`
- `schema_version`
- `event_type`
- `event_ts`
- `producer`
- `probe_scope`
- `orderbook_lineage_id`

Authority and safety:

- `probe_authority_level`
- `policy_authority`
- `runtime_decision_authority`
- `execution_authority`
- `risk_authority`

Identity:

- `asset`
- `ticker`
- `market_id`
- `market_slug`
- `condition_id`
- `yes_token_id`
- `no_token_id`
- `token_id`
- `outcome`
- `orderbook_token_pair_key`

Current fetch lineage:

- `fetch_attempt_ts`
- `fetch_complete_ts`
- `fetch_duration_ms`
- `current_fetch_status`
- `current_fetch_succeeded`
- `current_fetch_error_type`
- `current_fetch_error_message`

Side-specific YES/NO truth:

- `yes_fetch_status`
- `no_fetch_status`
- `yes_bids_count`
- `yes_asks_count`
- `no_bids_count`
- `no_asks_count`
- `yes_best_bid`
- `yes_best_ask`
- `yes_best_bid_size`
- `yes_best_ask_size`
- `no_best_bid`
- `no_best_ask`
- `no_best_bid_size`
- `no_best_ask_size`
- `yes_raw_age_ms`
- `no_raw_age_ms`

Cache and attribution:

- `last_successful_yes_no_book_at`
- `last_successful_yes_no_book_age_ms`
- `last_successful_yes_no_book_token_pair_key`
- `cache_token_pair_match`
- `cached_executable_book_available`
- `cached_book_used_for_decision`
- `cache_reuse_reason`
- `book_used_for_decision_source`
- `book_used_for_decision_token_pair_key`

Normalization and blockers:

- `normalization_status`
- `serialized_truth_source`
- `orderbook_readiness_reason`
- `orderbook_unavailable_reason`
- `liquidity_state`
- `terminal_blocker`
- `terminal_blocker_stage`
- `contextual_blockers`

Quote-age lineage:

- `quote_age_ms`
- `quote_age_source`
- `quote_age_truth_level`

Lifecycle:

- `lifecycle_phase`
- `seconds_remaining`
- `lineage_confidence`
- `source_module`

## Fail-Soft Behavior

The probe is fail-soft at two layers:

1. Payload construction serializes missing data as `null`, empty string, `unknown`, or `not_available`.
2. `_emit_orderbook_lineage_probe(...)` catches probe exceptions and returns `False`.

JSONL writer failures do not alter the existing market-analysis path.

## Runtime Safety Confirmation

Observed from implementation review and targeted tests:

- no policy consumer added;
- no runtime gate reads the probe;
- no strategy/risk/execution/sizing/order-placement path changed;
- no thresholds changed;
- no replay dependency added;
- no hot-loop joins added;
- no raw orderbook arrays emitted;
- payload is bounded to compact top-of-book/count/error fields;
- existing orderbook unavailable skip behavior is preserved.

## Tests Run

Initial expected red state:

```text
python -m pytest tests/test_orderbook_lineage_probe_v1.py -q
```

Result before implementation:

```text
6 failed
```

Final targeted tests:

```text
python -m pytest tests/test_orderbook_lineage_probe_v1.py -q
python -m pytest tests/test_orderbook_lineage_probe_v1.py tests/test_empty_orderbook_fail_soft.py -q
python -m pytest tests/test_quant_event_logger.py -q
python -m pytest tests/test_logging_resilience.py -q
```

Results:

```text
6 passed
8 passed
7 passed
8 passed
```

## Validation Notes

Probe emission is verified through targeted unit coverage:

- payload shape;
- evidence-only authority fields;
- side-specific YES/NO current fetch truth;
- cached available versus cached used distinction;
- terminal versus contextual blocker serialization;
- quote-age lineage;
- fail-soft missing field behavior;
- fail-soft emitter behavior;
- JSONL category routing.

No paper runtime was launched for this implementation report. No replay was run.

## Behavior Change Classification

Runtime behavior changed: observability only.

Live behavior changed: No.

Strategy/risk/execution changed: No.

Threshold tuning: No.

Readiness promotion: No.
