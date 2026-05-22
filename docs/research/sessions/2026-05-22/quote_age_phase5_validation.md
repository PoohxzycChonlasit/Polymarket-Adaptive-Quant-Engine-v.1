# Quote Age Phase 5 Validation

Date: 2026-05-22

Scope: Phase 5 quote age metrics capture and propagation. Observability only.

Runtime behavior changed: observability only.

Live behavior changed: No.

S3 status: CAUTION, not promoted.

## Phase 5 Commit

Commit hash: `296f232`

Message: `feat: add Phase 5 quote age metrics (quote_age_at_submit_ms, quote_age_at_fill_ms)`

Pushed to: `origin/main`

## Phase 5 Implementation Summary

Added `quote_age_at_submit_ms` and `quote_age_at_fill_ms` to two event types. All fields additive. Paper path only — live path emits null. Fail-soft: null when `quote_capture_ts` absent. No `quote_stale_ms` computed. No strategy, risk, sizing, order placement, threshold, wallet, or live config behavior changed.

### Fields added

| Field | Formula | Event | Condition |
|---|---|---|---|
| `quote_age_at_submit_ms` | `order_submit_ts − quote_capture_ts` (ms) | `order_submit_attempt`, `paper_fill` (carry) | paper path only; null if `quote_capture_ts` absent |
| `quote_age_at_fill_ms` | `fill_ts − quote_capture_ts` (ms) | `paper_fill` | paper path only; null if `quote_capture_ts` absent |

### Event coverage

| Event | JSONL Destination | Phase 5 Fields |
|---|---|---|
| `order_submit_attempt` | `execution_log` | `quote_age_at_submit_ms` |
| `paper_fill` | `execution_log` | `quote_age_at_submit_ms`, `quote_age_at_fill_ms` |

### Fail-soft behavior

- Null `quote_age_at_submit_ms` when `quote_capture_ts` is absent or unparsable.
- Null `quote_age_at_fill_ms` when `quote_capture_ts` is absent or unparsable.
- Null on live path (gated by `self.settings.paper_trading`).
- All computation delegated to `_phase3_paper_proxy_ms` which wraps in try/except returning null.
- No exception propagates to execution path.

### Live path

`quote_age_at_submit_ms` is `None` on live `order_submit_attempt`. No fake live quote ages introduced.

### Phase 1–4 fields

All Phase 1, Phase 2, Phase 3, and Phase 4 fields remain present and unchanged.

## Files Modified

- `polymarket/trader.py` — `_p5_quote_age_at_submit_ms` computed before `order_submit_attempt` emit; `_p5_quote_age_at_fill_ms` computed before `paper_fill` emit; both fields added to respective payloads (additive only)
- `tests/test_quote_lineage_phase4.py` — removed stale forward-guard assertions for `quote_age_at_submit_ms` and `quote_age_at_fill_ms` (same pattern as Phase 2 guard update when Phase 3 was added)

## Files Created

- `tests/test_quote_age_phase5.py` — 7 test cases

## Tests

### Command

```bash
python -m pytest tests/test_quote_age_phase5.py -q
python -m pytest tests/test_execution_timestamp_phase1.py tests/test_execution_timestamp_phase2.py tests/test_execution_timestamp_phase3.py tests/test_quote_lineage_phase4.py tests/test_quote_age_phase5.py -q
```

### Results

```
Phase 5 suite:        7 passed
Phase 1–4 + regression: 37 passed
Total: 37 passed, 0 failed
```

Deprecation warnings only (websockets library).

### Phase 5 test cases

1. `test_paper_fill_emits_quote_age_at_fill_ms_when_context_present` — PASSED
2. `test_submit_attempt_emits_quote_age_at_submit_ms_when_context_present` — PASSED
3. `test_quote_age_at_fill_ms_is_null_when_quote_capture_ts_missing` — PASSED
4. `test_quote_age_at_submit_ms_is_null_when_quote_capture_ts_missing` — PASSED
5. `test_quote_age_at_fill_ge_quote_age_at_submit` — PASSED
6. `test_live_path_does_not_emit_quote_age_at_submit_ms` — PASSED
7. `test_phase1_to_phase4_fields_intact_alongside_phase5` — PASSED

## Paper Validation

### Command

```bash
python main.py --mode paper --interval 10 --ui compact --fps medium
```

### Validation Run ID

```
20260522T082440Z_32952_1b709e78
```

## Age Coverage (validation run)

### Execution log

| Metric | Count |
|---|---|
| Total `paper_fill` events (today) | 66 |
| Phase 5 `paper_fill` events (have `quote_age_at_fill_ms` key) | **4 / 4** |
| `quote_age_at_fill_ms` non-null | **4 / 4** |
| `quote_age_at_submit_ms` non-null on `paper_fill` | **4 / 4** |
| `quote_age_at_fill_ms` null | 0 |
| `quote_age_at_submit_ms` null on `paper_fill` | 0 |
| Total `order_submit_attempt` events (today) | 66 |
| Phase 5 `order_submit_attempt` (have `quote_age_at_submit_ms` key) | **4 / 4** |
| `quote_age_at_submit_ms` non-null on `order_submit_attempt` | **4 / 4** |
| `fill_age < submit_age` violations | **0** |

### Age distribution

| Metric | n | min | mean | max |
|---|---|---|---|---|
| `quote_age_at_fill_ms` | 4 | 7,768 ms | 21,577 ms | 34,467 ms |
| `quote_age_at_submit_ms` (on paper_fill) | 4 | 7,765 ms | 21,571 ms | 34,449 ms |
| `quote_age_at_submit_ms` (on order_submit_attempt) | 4 | 7,765 ms | 21,571 ms | 34,449 ms |

### Ordering invariant

`quote_age_at_fill_ms >= quote_age_at_submit_ms` for all 4 fills. Fill always happens after submit — verified.

### Per-fill evidence

| Fill | `quote_capture_ts` | `fill_ts` | `quote_age_at_submit_ms` | `quote_age_at_fill_ms` | `quote_source` |
|---|---|---|---|---|---|
| 1 | `08:44:34.108` | `08:45:08.575` | 34,449 ms | 34,467 ms | `display_snapshot_sampling` |
| 2 | `08:45:08.432` | `08:45:16.199` | 7,765 ms | 7,768 ms | `decision_cycle_fetch` |
| 3 | `08:49:48.283` | `08:50:14.447` | 26,162 ms | 26,164 ms | `display_snapshot_sampling` |
| 4 | `08:50:27.089` | `08:50:45.000` | 17,909 ms | 17,911 ms | `display_snapshot_sampling` |

Fill 1 shows a 34-second-old quote at fill — a meaningful staleness gap visible now in JSONL. Fill 2 used a fresh quote (8 seconds). Two distinct `quote_source` values observed.

### Observed JSONL values (paper_fill sample, fill 2)

```json
{
  "quote_lineage_id": "ql_3d95321115ef",
  "quote_capture_ts": "2026-05-22T08:45:08.431523Z",
  "quote_source": "decision_cycle_fetch",
  "quote_age_at_submit_ms": 7764.513,
  "quote_age_at_fill_ms": 7767.51,
  "order_ack_ts": "2026-05-22T08:45:16.196036Z",
  "fill_ts": "2026-05-22T08:45:16.199033Z",
  "ack_source": "paper_simulated",
  "fill_source": "paper_simulated",
  "timestamp_source": "paper_fill_emit",
  "latency_truth_level": "paper_simulated",
  "submit_to_ack_ms": 2.997,
  "submit_to_fill_ms": 2.997,
  "derived_metric_source": "paper_proxy"
}
```

### Errors and exceptions

```
market_analysis_exception count: 0
Traceback / TypeError / ERROR in log: 0
```

## Full Timestamp + Lineage + Age Chain Coverage (paper mode, after Phase 1–5)

| Field | Event | Present | Label |
|---|---|---|---|
| `signal_generated_ts` | `decision` | present | `proxy` |
| `decision_complete_ts` | `decision` | present | `proxy` |
| `quote_lineage_id` | `decision` | present | `proxy` |
| `quote_capture_ts` | `decision` | present | `proxy` |
| `quote_snapshot_id` | `decision` | present | — |
| `quote_source` | `decision` | present | — |
| `order_intent_ts` | `order_intent_approved` | present | `paper_simulated` |
| `quote_lineage_id` | `order_intent_approved` | present | — |
| `order_submit_ts` | `order_submit_attempt` | present | `paper_simulated` |
| `quote_lineage_id` | `order_submit_attempt` | present | — |
| `quote_age_at_submit_ms` | `order_submit_attempt` | **4/4** | `paper_proxy` |
| `order_ack_ts` | `paper_fill` | present | `paper_simulated` |
| `fill_ts` | `paper_fill` | present | `paper_simulated` |
| `submit_to_ack_ms` | `paper_fill` | present | `paper_proxy` |
| `submit_to_fill_ms` | `paper_fill` | present | `paper_proxy` |
| `quote_lineage_id` | `paper_fill` | present | — |
| `quote_capture_ts` | `paper_fill` | present | — |
| `quote_age_at_submit_ms` | `paper_fill` | **4/4** | `paper_proxy` |
| `quote_age_at_fill_ms` | `paper_fill` | **4/4** | `paper_proxy` |

Remaining for future phases:
- `quote_stale_ms` (Phase 6)
- `signal_to_submit_ms` cross-log join (Phase 6)
- `cancel_submit_ts`, `cancel_ack_ts` (Phase 7/8)

## Compatibility Notes

- Payload changes are additive.
- Historical events without Phase 5 fields remain valid JSONL — no parse errors.
- No historical JSONL files were rewritten.
- Phase 1–4 fields intact on all events.
- No `quote_stale_ms` or `signal_to_submit_ms` emitted.
- No live path modification.

## Verdict

Phase 5 quote age metrics are present in live paper JSONL evidence:

- `quote_age_at_submit_ms` emitted on all 4 Phase 5 `order_submit_attempt` events (non-null, float)
- `quote_age_at_submit_ms` carried through to all 4 `paper_fill` events (non-null, float)
- `quote_age_at_fill_ms` emitted on all 4 `paper_fill` events (non-null, float)
- `quote_age_at_fill_ms >= quote_age_at_submit_ms` for all 4 fills — 0 violations
- Range: 7,768 ms to 34,467 ms — real staleness variation visible in observability layer
- Two distinct `quote_source` values observed (`decision_cycle_fetch`, `display_snapshot_sampling`)
- Phase 1–4 fields intact and unmodified
- 0 market_analysis_exceptions, 0 errors
- 37 tests pass across all phases and regression suites

Runtime behavior changed: observability only.

Live behavior changed: No.
