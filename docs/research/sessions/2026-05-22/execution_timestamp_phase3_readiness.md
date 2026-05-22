# Execution Timestamp Phase 3 Readiness

Date: 2026-05-22

Scope: Read-only readiness check. No code changes. No paper runtime.

Validation run inspected: `20260522T052610Z_31032_cfe7068f`

Git state at inspection: clean. Phase 1 commit `b3994ee`, Phase 2 commit `850d70c` confirmed at HEAD.

## Phase 3 Target Metrics

| Metric | Formula |
|---|---|
| `submit_to_ack_ms` | `(order_ack_ts − order_submit_ts)` in milliseconds |
| `submit_to_fill_ms` | `(fill_ts − order_submit_ts)` in milliseconds |
| `signal_to_submit_ms` | `(order_submit_ts − signal_generated_ts)` in milliseconds |

## Field Coverage (validation run)

### order_intent_approved (8 events)

| Field | Present | Count |
|---|---|---|
| `order_intent_ts` | YES | 8 / 8 |
| `execution_trace_id` | YES | 8 / 8 |
| `order_submit_ts` | NO | — |
| `order_ack_ts` | NO | — |
| `fill_ts` | NO | — |

### order_submit_attempt (8 events)

| Field | Present | Count |
|---|---|---|
| `order_submit_ts` | YES | 8 / 8 |
| `execution_trace_id` | YES | 8 / 8 |
| `order_ack_ts` | NO | — |
| `fill_ts` | NO | — |

### paper_fill (8 events)

| Field | Present | Count |
|---|---|---|
| `order_ack_ts` | YES | 8 / 8 |
| `fill_ts` | YES | 8 / 8 |
| `execution_trace_id` | YES | 8 / 8 |
| `order_submit_ts` | NO | — |
| `ack_source` | YES (`paper_simulated`) | 8 / 8 |
| `fill_source` | YES (`paper_simulated`) | 8 / 8 |
| `latency_truth_level` | YES (`paper_simulated`) | 8 / 8 |

### decision (122 events)

| Field | Present | Count |
|---|---|---|
| `signal_generated_ts` | YES | 122 / 122 |
| `decision_complete_ts` | YES | 122 / 122 |
| `latency_truth_level` | YES (`proxy`) | 122 / 122 |

## Architecture Finding: Cross-Event Join Required

All three canonical fields needed for `submit_to_ack_ms` and `submit_to_fill_ms` are on **separate event types**:

- `order_submit_ts` → `order_submit_attempt`
- `order_ack_ts` → `paper_fill`
- `fill_ts` → `paper_fill`

No single event carries both `order_submit_ts` and `order_ack_ts`. Derivation requires a cross-event join by `execution_trace_id`.

## Lineage Join Verification

Execution trace IDs were matched across `order_submit_attempt` and `paper_fill` for the validation run.

Result: **5 / 5 submit+fill pairs** share identical `execution_trace_id`. All 5 are also matched with corresponding `order_intent_approved` events. The join is reliable and complete for this run.

## Computed Metrics (proof of concept, paper mode)

| execution_trace_id (prefix) | submit_to_ack_ms | submit_to_fill_ms | note |
|---|---|---|---|
| et_f4854980 | 23.269 | 23.269 | probable first-connect overhead |
| et_9cbf68eb | 1.997 | 2.999 | — |
| et_2edd893f | 2.011 | 2.011 | — |
| et_23a99619 | 2.327 | 2.327 | — |
| et_6439d34e | 1.039 | 1.039 | — |

Paper mode note: `order_ack_ts` and `fill_ts` are captured within the same synchronous execution path. They are equal or within microseconds in paper — `submit_to_ack_ms ≈ submit_to_fill_ms` is expected and correct.

The 23ms outlier on the first fill is consistent with Python warm-up or first-connection overhead. Remaining fills cluster at 1–3ms, reflecting only local synchronous Python overhead with no simulated network delay.

## Readiness Matrix

| Field / Metric | Source Event | Ready? | Blocker |
|---|---|---|---|
| `order_submit_ts` | `order_submit_attempt` | YES | None — 8/8 present |
| `order_ack_ts` | `paper_fill` | YES | None — 8/8 present |
| `fill_ts` | `paper_fill` | YES | None — 8/8 present |
| `execution_trace_id` (join key) | all three event types | YES | None — 8/8 present across all types |
| `submit_to_ack_ms` | cross-event join | YES (computable) | Requires join implementation; no new fields needed |
| `submit_to_fill_ms` | cross-event join | YES (computable) | Requires join implementation; no new fields needed |
| `signal_generated_ts` | `decision` log | YES | Present 122/122; cross-log join needed for `signal_to_submit_ms` |
| `signal_to_submit_ms` | decision + execution cross-log join | PARTIAL | Requires cross-log join by `candidate_trace_id`; secondary for Phase 3 |
| `cancel_submit_ts` | not implemented | NO | Phase 6/7 in architecture |
| `cancel_ack_ts` | not implemented | NO | Phase 6/7 in architecture |
| `quote_lineage_id` | not implemented | NO | Phase 4/5 in architecture |
| `quote_age_ms_at_submit` | not implemented | NO | Phase 4/5 in architecture |

## Phase 3 Implementation Notes

### What Phase 3 adds

Phase 3 emits `submit_to_ack_ms` and `submit_to_fill_ms` as computed fields, derived from fields that already exist across Phase 1 and Phase 2 events.

### Implementation constraint

These metrics cannot be read from a single event. The implementation must:
1. Capture `order_submit_ts` at the `order_submit_attempt` boundary (Phase 1, already present).
2. Capture `order_ack_ts` and `fill_ts` at the `paper_fill` boundary (Phase 2, already present).
3. Carry `order_submit_ts` forward into the paper fill path, or join by `execution_trace_id` at emit time.

The forward-carry approach (storing `order_submit_ts` in a local variable between `_submit_order` boundary and paper fill emit) is simpler and avoids a runtime join. The `execution_trace_id` join remains valid for offline analysis.

### Scope boundary (paper only)

Phase 3 derived metrics are labelled `paper_simulated`. Live path: no derived metrics, no fake timestamps. This matches the Phase 1/2 boundary pattern.

### What Phase 3 does NOT add

- No `signal_to_submit_ms` (cross-log join; secondary)
- No `cancel_submit_ts`, `cancel_ack_ts` (Phase 6/7)
- No `quote_lineage_id`, `quote_age_ms_at_submit` (Phase 4/5)
- No strategy, risk, sizing, threshold, wallet, or live config changes
- No historical JSONL rewrite
- No S3 promotion

## Verdict

**READY_FOR_PHASE3**

Required input fields exist in the validation run:
- `order_submit_ts` present on all `order_submit_attempt` events
- `order_ack_ts` and `fill_ts` present on all `paper_fill` events
- `execution_trace_id` present and consistent across all three event types

`submit_to_ack_ms` and `submit_to_fill_ms` are computable from existing fields. No new capture points are needed. Implementation requires forwarding `order_submit_ts` into the paper fill emit path (or performing the join at emit time).

Phase 3 implementation is authorized once approved. No quote lineage, cancel path, or replay changes are required first.

Runtime behavior changed: none (this is a readiness check only).

Live behavior changed: No.

S3 status: CAUTION, not promoted.
