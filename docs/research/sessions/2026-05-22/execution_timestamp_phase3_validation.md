# Execution Timestamp Phase 3 Validation

Date: 2026-05-22

Scope: Phase 3 paper proxy derived metrics observability only.

Runtime behavior changed: observability only.

Live behavior changed: No.

S3 status: CAUTION, not promoted.

## Phase 3 Commit

Commit hash: `7d01a7d`

Message: `feat: add Phase 3 paper proxy derived metrics (submit_to_ack_ms, submit_to_fill_ms)`

Pushed to: `origin/main`

## Phase 3 Implementation Summary

Added two paper proxy derived metrics to the `paper_fill` event in `polymarket/trader.py`.

Changes are additive only. No strategy, risk, sizing, order placement, threshold, wallet, or live config behavior was changed.

### Helper added

```python
def _phase3_paper_proxy_ms(self, ts_start: str, ts_end: str) -> "float | None":
    try:
        def _parse(s: str) -> datetime:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return round((_parse(ts_end) - _parse(ts_start)).total_seconds() * 1000, 3)
    except Exception:
        return None
```

Returns `None` on any parse error (fail-soft). No exception can propagate to runtime.

### Fields added to `paper_fill` event

| Field | Value (paper) | Source |
|---|---|---|
| `submit_to_ack_ms` | float ms or null | `_phase3_paper_proxy_ms(order_submit_ts, order_ack_ts)` |
| `submit_to_fill_ms` | float ms or null | `_phase3_paper_proxy_ms(order_submit_ts, fill_ts)` |
| `derived_metric_source` | `paper_proxy` | static label |

### Derivation approach

`order_submit_ts`, `order_ack_ts`, and `fill_ts` are all local variables in the same `_submit_order` function scope. No cross-event join is required at emit time. The computation is inline between `fill_ts` capture and `paper_fill` emit.

### Live path

The `live_order_submitted` event was not modified. No derived metrics were added to the live path.

### Phase 1 + 2 fields

All Phase 1 and Phase 2 fields remain present and unchanged on their respective events.

## Files Modified

- `polymarket/trader.py` — `_phase3_paper_proxy_ms` helper (8 lines) + 3 fields on `paper_fill` payload (additive only)
- `tests/test_execution_timestamp_phase2.py` — removed stale "no derived metrics" guard (`submit_to_ack_ms`/`submit_to_fill_ms` now correctly present)

## Files Created

- `tests/test_execution_timestamp_phase3.py` — 5 test cases

## Tests

### Command

```bash
python -m pytest tests/test_execution_timestamp_phase1.py tests/test_execution_timestamp_phase2.py tests/test_execution_timestamp_phase3.py -q
python -m pytest tests/test_empty_orderbook_fail_soft.py tests/test_trade_open_model_visibility_serialization.py -q
```

### Results

```
Phase 1+2+3 suite: 16 passed
Regression suite:  7 passed
Total: 23 passed, 0 failed
```

Deprecation warnings only (websockets library).

### Phase 3 test cases

1. `test_paper_fill_emits_submit_to_ack_ms` — PASSED
2. `test_paper_fill_emits_submit_to_fill_ms` — PASSED
3. `test_phase3_metrics_fail_soft_on_missing_or_invalid_fields` — PASSED
4. `test_paper_fill_labels_preserved_alongside_phase3_metrics` — PASSED
5. `test_live_path_does_not_emit_phase3_derived_metrics` — PASSED

## Paper Validation

### Command

```bash
python main.py --mode paper --interval 10 --ui compact --fps medium
```

### Validation Run ID

```
20260522T055830Z_13912_ef8361bc
```

### Log file

```
logs/polytrade_bot_20260522_125828_13912.log
```

## Metric Coverage (validation run)

### Decision log

| Metric | Count |
|---|---|
| Decision events | 653 |
| `signal_generated_ts` | 653 / 653 |
| `decision_complete_ts` | 653 / 653 |
| `timestamp_source` (`decision_emit`) | 653 / 653 |
| `latency_truth_level` (`proxy`) | 653 / 653 |
| `market_analysis_exception` | **0** |

### Execution log (validation run)

| Metric | Count |
|---|---|
| `order_intent_approved` events | 8 |
| `order_intent_ts` | 8 / 8 |
| `order_submit_attempt` events | 8 |
| `order_submit_ts` | 8 / 8 |
| `paper_fill` events | 8 |
| `order_ack_ts` | 8 / 8 |
| `fill_ts` | 8 / 8 |
| `submit_to_ack_ms` | **8 / 8** |
| `submit_to_fill_ms` | **8 / 8** |
| `derived_metric_source` (`paper_proxy`) | **8 / 8** |
| `ack_source` (`paper_simulated`) | 8 / 8 |
| `fill_source` (`paper_simulated`) | 8 / 8 |
| `timestamp_source` (`paper_fill_emit`) | 8 / 8 |
| `latency_truth_level` (`paper_simulated`) | 8 / 8 |

### Observed metric values (paper_fill, all 8 fills)

| Fill | `submit_to_ack_ms` | `submit_to_fill_ms` | Note |
|---|---|---|---|
| 1 | 1.505 | 1.505 | — |
| 2 | 2.351 | 2.351 | — |
| 3 | 10.928 | 10.928 | probable first warm-up in window |
| 4 | 3.179 | 3.179 | — |
| 5 | 4.029 | 4.029 | — |
| 6 | 3.009 | 3.009 | — |
| 7 | 1.940 | 1.940 | — |
| 8 | 2.152 | 2.152 | — |

**Range:** 1.505ms – 10.928ms

**Mean:** 3.637ms

**`submit_to_ack_ms` = `submit_to_fill_ms` on all 8 fills.** Expected: in paper mode, ack and fill are captured in the same synchronous execution path with no simulated network delay. Both measure local Python overhead from `order_submit_ts` to the paper fill boundary.

### Observed JSONL values (sample, fill 1)

```json
{
  "order_ack_ts": "2026-05-22T06:10:07.775034Z",
  "fill_ts": "2026-05-22T06:10:07.775034Z",
  "ack_source": "paper_simulated",
  "fill_source": "paper_simulated",
  "timestamp_source": "paper_fill_emit",
  "latency_truth_level": "paper_simulated",
  "submit_to_ack_ms": 1.505,
  "submit_to_fill_ms": 1.505,
  "derived_metric_source": "paper_proxy"
}
```

Note: `order_submit_ts` lives on the `order_submit_attempt` event (Phase 1) and is not duplicated on `paper_fill`. The derived metrics are computed inline before emit using `order_submit_ts` from the same function scope.

### Errors and exceptions

```
market_analysis_exception count: 0
Traceback / TypeError / ERROR in log: 0
```

## Compatibility Notes

- Payload changes are additive.
- Historical `paper_fill` events (prior sessions) remain valid — missing Phase 3 fields fail soft through `_phase3_paper_proxy_ms`.
- No historical JSONL files were rewritten.
- Phase 1 fields (`order_intent_ts`, `order_submit_ts`, `signal_generated_ts`, `decision_complete_ts`) remain present and unchanged on their canonical events.
- Phase 2 fields (`order_ack_ts`, `fill_ts`, `ack_source`, `fill_source`) remain present and unchanged on `paper_fill`.
- No `signal_to_submit_ms`, `cancel_latency_ms`, `quote_stale_ms`, or `quote_lineage_id` fields were emitted.

## Full Timestamp Chain Coverage (paper mode, after Phase 1 + 2 + 3)

| Field | Event | Present | Label |
|---|---|---|---|
| `signal_generated_ts` | `decision` | 653/653 | `proxy` |
| `decision_complete_ts` | `decision` | 653/653 | `proxy` |
| `order_intent_ts` | `order_intent_approved` | 8/8 | `paper_simulated` |
| `order_submit_ts` | `order_submit_attempt` | 8/8 | `paper_simulated` |
| `order_ack_ts` | `paper_fill` | 8/8 | `paper_simulated` |
| `fill_ts` | `paper_fill` | 8/8 | `paper_simulated` |
| `submit_to_ack_ms` | `paper_fill` (derived) | **8/8** | `paper_proxy` |
| `submit_to_fill_ms` | `paper_fill` (derived) | **8/8** | `paper_proxy` |

Remaining for future phases:
- `cancel_submit_ts`, `cancel_ack_ts` (Phase 6/7 in architecture)
- `signal_to_submit_ms` (requires cross-log join by `candidate_trace_id`)
- Quote lineage: `quote_lineage_id`, `quote_age_ms_at_submit`, `quote_age_ms_at_fill` (Phase 4/5)

## Verdict

Phase 3 paper proxy derived metrics are present in live paper JSONL evidence:

- `submit_to_ack_ms` emitted on all 8 `paper_fill` events with `paper_proxy` label
- `submit_to_fill_ms` emitted on all 8 `paper_fill` events with `paper_proxy` label
- `derived_metric_source: paper_proxy` on all 8 fills
- Phase 1 and Phase 2 fields intact and unmodified
- No `signal_to_submit_ms`, cancel metrics, or quote lineage emitted
- No live faking
- No historical rewrite
- 23 tests pass across Phase 1, Phase 2, Phase 3, and regression suites
- `market_analysis_exception` count: 0

Runtime behavior changed: observability only.

Live behavior changed: No.
