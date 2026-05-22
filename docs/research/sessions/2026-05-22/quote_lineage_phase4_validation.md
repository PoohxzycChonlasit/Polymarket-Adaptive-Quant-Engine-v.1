# Quote Lineage Phase 4 Validation

Date: 2026-05-22

Scope: Phase 4 quote lineage capture and propagation. Observability only.

Runtime behavior changed: observability only.

Live behavior changed: No.

S3 status: CAUTION, not promoted.

## Phase 4 Commit

Commit hash: `8236da7`

Message: `feat: add Phase 4 quote lineage capture and propagation`

Pushed to: `origin/main`

## Phase 4 Implementation Summary

Added `quote_lineage_id`, `quote_capture_ts`, `quote_snapshot_id`, and `quote_source` to four event types. All fields are additive. No strategy, risk, sizing, order placement, threshold, wallet, or live config behavior was changed.

### Fields added

| Field | Value | Source |
|---|---|---|
| `quote_lineage_id` | `ql_` + SHA-1 (12 hex chars) of `market_id \| token_pair_key \| quote_capture_ts_second` | `_phase4_build_quote_lineage` |
| `quote_capture_ts` | ISO-8601 UTC Z timestamp of last successful executable yes/no book | `_last_successful_yes_no_book_at_utc[ticker_key]` |
| `quote_snapshot_id` | `qs_` + same hash body as `quote_lineage_id` | `_phase4_build_quote_lineage` (decision only) |
| `quote_source` | Source label of orderbook refresh | `_last_orderbook_refresh_source[ticker_key]` |

### Event coverage

| Event | JSONL Destination | Phase 4 Fields |
|---|---|---|
| `decision` | `decision_log` | `quote_lineage_id`, `quote_capture_ts`, `quote_snapshot_id`, `quote_source` |
| `order_intent_approved` | `execution_log` | `quote_lineage_id`, `quote_capture_ts` |
| `order_submit_attempt` | `execution_log` | `quote_lineage_id`, `quote_capture_ts`, `quote_source` |
| `paper_fill` | `execution_log` | `quote_lineage_id`, `quote_capture_ts`, `quote_source` |

### Fail-soft behavior

- Null `quote_lineage_id` when no successful executable book exists for the ticker.
- At submit time: if carry from decision is empty, rebuilds lineage from current instance state.
- All computation wrapped in try/except returning null/empty dict.
- No exception propagates to execution path.

### Live path

No quote lineage fields added to `live_order_submitted`. No fake live timestamps introduced.

### Phase 1–3 fields

All Phase 1, Phase 2, and Phase 3 fields remain present and unchanged.

## Files Modified

- `polymarket/trader.py` — `_last_quote_lineage_context` instance dict + `_phase4_build_quote_lineage` helper (32 lines) + `_phase4_quote_lineage_carry` helper (7 lines) + 4 fields on decision, 2 on intent, 3 on submit, 3 on paper_fill (additive only)

## Files Created

- `tests/test_quote_lineage_phase4.py` — 14 test cases

## Tests

### Command

```bash
python -m pytest tests/test_quote_lineage_phase4.py -q
python -m pytest tests/test_execution_timestamp_phase1.py tests/test_execution_timestamp_phase2.py tests/test_execution_timestamp_phase3.py tests/test_empty_orderbook_fail_soft.py tests/test_trade_open_model_visibility_serialization.py -q
```

### Results

```
Phase 4 suite:       14 passed
Phase 1–3 + regression: 23 passed
Total: 37 passed, 0 failed
```

Deprecation warnings only (websockets library).

### Phase 4 test cases

1. `test_quote_lineage_id_generated_when_context_present` — PASSED
2. `test_quote_lineage_id_is_deterministic` — PASSED
3. `test_quote_lineage_id_matches_expected_hash` — PASSED
4. `test_quote_capture_ts_propagated_from_instance_state` — PASSED
5. `test_quote_source_propagated` — PASSED
6. `test_quote_snapshot_id_uses_qs_prefix` — PASSED
7. `test_missing_quote_context_returns_null_ids` — PASSED
8. `test_missing_context_carry_fails_soft` — PASSED
9. `test_paper_fill_carries_quote_lineage_id` — PASSED
10. `test_paper_fill_carries_quote_capture_ts` — PASSED
11. `test_submit_attempt_carries_quote_lineage_id` — PASSED
12. `test_quote_lineage_consistent_across_submit_and_fill` — PASSED
13. `test_paper_fill_without_quote_context_emits_null_lineage_id` — PASSED
14. `test_phase1_to_phase3_fields_still_present_with_phase4` — PASSED

## Paper Validation

### Command

```bash
python main.py --mode paper --interval 10 --ui compact --fps medium
```

### Validation Run ID

```
20260522T075658Z_26740_b69f35b9
```

## Lineage Coverage (validation run)

### Decision log

| Metric | Count |
|---|---|
| Decision events | 150 |
| `signal_generated_ts` | 150 / 150 |
| `decision_complete_ts` | 150 / 150 |
| `quote_lineage_id` (non-null, `ql_` prefix) | **150 / 150** |
| `quote_capture_ts` | **150 / 150** |
| `quote_snapshot_id` | **150 / 150** |
| `quote_source` | **150 / 150** |
| `market_analysis_exception` | **0** |

### Execution log (validation run)

| Metric | Count |
|---|---|
| `order_intent_approved` events | 4 |
| `quote_lineage_id` on intent | **4 / 4** |
| `quote_capture_ts` on intent | **4 / 4** |
| `order_submit_attempt` events | 4 |
| `quote_lineage_id` on submit | **4 / 4** |
| `quote_capture_ts` on submit | **4 / 4** |
| `quote_source` on submit | **4 / 4** |
| `order_submit_ts` (Phase 1) | 4 / 4 |
| `paper_fill` events | 4 |
| `quote_lineage_id` on fill | **4 / 4** |
| `quote_capture_ts` on fill | **4 / 4** |
| `quote_source` on fill | **4 / 4** |
| `order_ack_ts` (Phase 2) | 4 / 4 |
| `fill_ts` (Phase 2) | 4 / 4 |
| `submit_to_ack_ms` (Phase 3) | 4 / 4 |
| `submit_to_fill_ms` (Phase 3) | 4 / 4 |

### Lineage consistency: `quote_lineage_id` across intent → submit → fill

| Fill | `quote_lineage_id` | intent match | submit match |
|---|---|---|---|
| 1 | `ql_f3c7a4c96563` | YES | YES |
| 2 | `ql_65dd1714b7e8` | YES | YES |
| 3 | `ql_b6583cbc7dbe` | YES | YES |
| 4 | `ql_8e17119012ff` | YES | YES |

All 4/4 lineage IDs are consistent across `order_intent_approved` → `order_submit_attempt` → `paper_fill`.

### Observed `quote_source` values

| Value | Meaning |
|---|---|
| `decision_cycle_fetch` | Quote from a fresh orderbook fetch in the current decision cycle |
| `display_snapshot_sampling` | Quote from display/snapshot sampling path |

Two distinct source labels observed — the lineage correctly captures the actual refresh source path used at decision time.

### Observed JSONL values (paper_fill sample, fill 2)

```json
{
  "quote_lineage_id": "ql_65dd1714b7e8",
  "quote_capture_ts": "2026-05-22T08:10:13.956116Z",
  "quote_source": "decision_cycle_fetch",
  "order_ack_ts": "2026-05-22T08:10:21.904580Z",
  "fill_ts": "2026-05-22T08:10:21.904580Z",
  "ack_source": "paper_simulated",
  "fill_source": "paper_simulated",
  "timestamp_source": "paper_fill_emit",
  "latency_truth_level": "paper_simulated",
  "submit_to_ack_ms": 1.998,
  "submit_to_fill_ms": 1.998,
  "derived_metric_source": "paper_proxy"
}
```

### Quote staleness preview (Phase 6 target, manual calculation)

With `quote_capture_ts` and `fill_ts` both present, the future `quote_age_at_fill_ms` metric is already computable offline:

| Fill | `quote_capture_ts` | `fill_ts` | approx quote age at fill |
|---|---|---|---|
| 1 | `08:07:38.997` | `08:10:14.534` | **~155 s (2 min 35 s)** — stale quote |
| 2 | `08:10:13.956` | `08:10:21.905` | **~8 s** — fresh quote |
| 3 | `08:10:18.509` | `08:10:36.482` | **~18 s** |
| 4 | `08:10:21.865` | `08:10:37.008` | **~15 s** |

Fill 1 shows a quote approximately 155 seconds old at fill — a significant staleness gap that would flag as high ghost fill risk under Phase 6 `quote_stale_ms` thresholds. This is the primary motivation for Phase 6.

### Errors and exceptions

```
market_analysis_exception count: 0
Traceback / TypeError / ERROR in log: 0
```

## Full Timestamp + Lineage Chain Coverage (paper mode, after Phase 1 + 2 + 3 + 4)

| Field | Event | Present | Label |
|---|---|---|---|
| `signal_generated_ts` | `decision` | 150/150 | `proxy` |
| `decision_complete_ts` | `decision` | 150/150 | `proxy` |
| `quote_lineage_id` | `decision` | **150/150** | `proxy` |
| `quote_capture_ts` | `decision` | **150/150** | `proxy` |
| `quote_snapshot_id` | `decision` | **150/150** | — |
| `quote_source` | `decision` | **150/150** | — |
| `order_intent_ts` | `order_intent_approved` | 4/4 | `paper_simulated` |
| `quote_lineage_id` | `order_intent_approved` | **4/4** | — |
| `order_submit_ts` | `order_submit_attempt` | 4/4 | `paper_simulated` |
| `quote_lineage_id` | `order_submit_attempt` | **4/4** | — |
| `order_ack_ts` | `paper_fill` | 4/4 | `paper_simulated` |
| `fill_ts` | `paper_fill` | 4/4 | `paper_simulated` |
| `submit_to_ack_ms` | `paper_fill` | 4/4 | `paper_proxy` |
| `submit_to_fill_ms` | `paper_fill` | 4/4 | `paper_proxy` |
| `quote_lineage_id` | `paper_fill` | **4/4** | — |
| `quote_capture_ts` | `paper_fill` | **4/4** | — |

Remaining for future phases:
- `quote_age_at_submit_ms`, `quote_age_at_fill_ms` (Phase 5)
- `quote_stale_ms` (Phase 6)
- `signal_to_submit_ms` cross-log join (Phase 6)
- `cancel_submit_ts`, `cancel_ack_ts` (Phase 7/8)

## Compatibility Notes

- Payload changes are additive.
- Historical events without Phase 4 fields remain valid JSONL — no parse errors.
- No historical JSONL files were rewritten.
- Phase 1–3 fields intact on all events.
- No `quote_age_at_submit_ms`, `quote_age_at_fill_ms`, `quote_stale_ms`, or `signal_to_submit_ms` emitted.
- No live path modification.

## Verdict

Phase 4 quote lineage is present in live paper JSONL evidence:

- `quote_lineage_id` (`ql_` prefix) emitted on all 150 decision events and all 4 paper_fill, submit, and intent events
- `quote_capture_ts` carried consistently from decision through intent, submit, and fill
- `quote_lineage_id` identical across intent → submit → fill for all 4 fills
- Two distinct `quote_source` values observed (`decision_cycle_fetch`, `display_snapshot_sampling`)
- Phase 1–3 fields intact and unmodified
- 0 market_analysis_exceptions, 0 errors
- 37 tests pass across all phases and regression suites

Quote staleness preview shows fill 1 used a 155-second-old quote — Phase 6 `quote_age_at_fill_ms` and `quote_stale_ms` will make this directly observable and auditable for all fills.

Runtime behavior changed: observability only.

Live behavior changed: No.
