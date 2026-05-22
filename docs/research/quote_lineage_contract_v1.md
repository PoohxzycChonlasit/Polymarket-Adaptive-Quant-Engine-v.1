# Quote Lineage Contract v1

Generated: 2026-05-22

Scope: Design/spec contract freeze for quote lineage observability layer.

Runtime behavior changed: No.

Live behavior changed: No.

Replay execution: No.

Paper launch: No.

S3 promotion: No.

Prerequisite: `execution_timestamp_contract_v1.md`. Phases 1–3 complete.

---

## Purpose

This contract freezes canonical field names, meanings, producer boundaries, truth labels, fail-soft rules, JSONL destinations, and backward compatibility requirements for the quote lineage layer.

Quote lineage connects the orderbook snapshot used at decision time to the submit and fill events. It is a prerequisite for `quote_stale_ms`, `signal_to_submit_ms` cross-log join, ghost fill truth, and delay replay realism.

This document does not authorize implementation. Implementation requires a separate explicitly scoped patch.

---

## Non-Implementation Guardrail

This contract is design/spec only.

Do not treat as implemented until code and tests prove:

- `quote_lineage_id` is emitted on decision, submit, and fill events
- `quote_capture_ts` is carried from decision boundary to fill boundary
- `quote_age_at_submit_ms` and `quote_age_at_fill_ms` fail soft to null on missing inputs
- Paper and live paths are correctly labelled
- Historical events without quote lineage fields parse without error
- No fake live timestamps, no fabricated ages, no historical rewrite

---

## Canonical Field Contract

All timestamps MUST be ISO-8601 UTC strings with `Z` suffix. Age fields MUST be float milliseconds or null. ID fields MUST be string with canonical prefix (`ql_`, `qs_`) or null.

| Field | Meaning | Allowed Event Types | JSONL Destination | Truth Label | Null Condition |
|---|---|---|---|---|---|
| `quote_lineage_id` | Stable ID linking the quote snapshot at decision time to submit and fill events. Deterministic hash of `(market_id, token_pair_key, quote_capture_ts_second)`. Prefix: `ql_`. | `decision`, `order_intent_approved`, `order_submit_attempt`, `paper_fill`, future `live_order_submitted`, future `live_fill`, future `trade_open`, future `trade_close` | `decision_log`, `execution_log`, future `trade_journal` | `proxy` (same truth level as quote source) | null if no successful executable book exists at decision time |
| `quote_capture_ts` | UTC ISO-8601 timestamp when the orderbook was last successfully captured as an executable yes/no book. Source: `_last_successful_yes_no_book_at_utc[ticker_key]`. | `decision`, `order_intent_approved`, `order_submit_attempt`, `paper_fill`, future `live_order_submitted`, future `live_fill` | `decision_log`, `execution_log` | `proxy` (paper) or `live_observed` (live, if source is verifiable) | null if no successful book exists |
| `quote_snapshot_id` | ID for the specific orderbook snapshot. In Phase 4 identical to `quote_lineage_id`. May become more granular in future (per-tick). Prefix: `qs_`. | `decision` (primary emitter); optionally on execution events if granularity differs | `decision_log` | `proxy` | null if no successful book |
| `quote_source` | Source of the quote snapshot. Allowed values: `clob_orderbook_rest`, `clob_orderbook_ws`, `stale_reuse`, `unknown`. | `decision`, `order_submit_attempt`, `paper_fill` | `decision_log`, `execution_log` | Static label | `unknown` if source unavailable |
| `quote_age_at_submit_ms` | `order_submit_ts − quote_capture_ts` in milliseconds. Computed at submit boundary. | `order_submit_attempt`, `paper_fill` (carry-through from submit) | `execution_log` | `paper_proxy` in paper, `live_observed` in live if both timestamps are live_observed | null if either timestamp missing, unparsable, or reversed |
| `quote_age_at_fill_ms` | `fill_ts − quote_capture_ts` in milliseconds. Computed at fill boundary. | `paper_fill`, future `live_fill` | `execution_log` | `paper_proxy` in paper, `live_observed` in live | null if either timestamp missing, unparsable, or reversed |

---

## ID Generation Contract

```
quote_capture_ts_second = quote_capture_ts.split(".")[0] + "Z"  # truncate sub-second

quote_lineage_id = "ql_" + sha1(f"{market_id}|{token_pair_key}|{quote_capture_ts_second}".encode()).hexdigest()[:12]

quote_snapshot_id = "qs_" + sha1(f"{market_id}|{token_pair_key}|{quote_capture_ts_second}".encode()).hexdigest()[:12]
```

Rules:
- `market_id` is the canonical market/condition identifier passed to `_submit_order`.
- `token_pair_key` is `_last_successful_yes_no_book_token_pair_key[ticker_key]`.
- `quote_capture_ts_second` strips sub-second precision for stability across concurrent decisions.
- If any input is empty or None, `quote_lineage_id` is null.
- The same snapshot produces the same ID across any number of events.
- ID generation MUST be wrapped in try/except returning null.

---

## Producer Boundaries

| Producer | Method | Fields Emitted | Condition |
|---|---|---|---|
| Quote context builder | `_build_orderbook_timing_context()` | Generates `quote_lineage_id`, `quote_capture_ts`, `quote_snapshot_id`, `quote_source`. Stores in `_last_quote_lineage_context[ticker_key]`. | Always, when orderbook context is computed |
| Decision payload builder | Before `log_decision` emit | Reads from `_last_quote_lineage_context[ticker_key]`. Adds `quote_lineage_id`, `quote_capture_ts`, `quote_snapshot_id`, `quote_source` to decision payload. | When context available |
| Intent emitter | `_validate_submit_order_intent()` | Reads `_last_quote_lineage_context[ticker_key]`. Carries `quote_lineage_id`, `quote_capture_ts` on `order_intent_approved`. | When context available |
| Submit emitter | `_submit_order()` | Reads carry-forward, computes `quote_age_at_submit_ms`. Adds to `order_submit_attempt`. | When `quote_capture_ts` and `order_submit_ts` both present |
| Paper fill emitter | `_submit_order()`, paper path | Carries `quote_lineage_id`, `quote_capture_ts`, `quote_age_at_submit_ms`. Computes `quote_age_at_fill_ms`. Adds to `paper_fill`. | When `quote_capture_ts` and `fill_ts` both present |

Events not listed MUST NOT emit quote lineage fields unless this contract is revised.

---

## Truth Labels

| Context | `quote_lineage_id` label | `quote_capture_ts` label | `quote_age_at_submit_ms` label | `quote_age_at_fill_ms` label |
|---|---|---|---|---|
| Paper mode | `proxy` | `proxy` | `paper_proxy` | `paper_proxy` |
| Live mode, REST/WS source | `proxy` | `live_observed` | `live_observed` | `live_observed` (only if `fill_ts` is `live_observed`) |
| Source unknown | `proxy` | `unknown` | null | null |

The `latency_truth_level` field on paper fill events in Phase 4 remains `paper_simulated` (inherited from Phase 2). Quote lineage fields carry their own truth context via `derived_metric_source`.

New provenance field added to quote age metrics:

| Field | Value |
|---|---|
| `quote_metric_source` | `paper_proxy` in paper; `live_observed` in live |

---

## Forwarding Mechanism

Quote lineage context must be carried from decision boundary to submit/fill boundary via instance state:

```python
# New instance dict (additive, initialized in __init__)
self._last_quote_lineage_context: dict[str, dict] = {}

# Schema of context dict stored per ticker_key:
{
    "quote_lineage_id": str or None,
    "quote_capture_ts": str or None,
    "quote_snapshot_id": str or None,
    "quote_source": str,
}
```

The forwarding mechanism MUST:
1. Store at decision boundary (before `log_decision`).
2. Read at intent approval (before `order_intent_approved`).
3. Read at submit (before `order_submit_attempt`).
4. Read at fill (before `paper_fill`).
5. Never modify execution policy, risk gates, or order placement based on context values.
6. Be keyed by `ticker_key` (not `market_id`) for consistency with existing instance dicts.

---

## Derived Metrics Contract

| Metric | Formula | Required Fields | Null Condition | Phase |
|---|---|---|---|---|
| `quote_age_at_submit_ms` | `order_submit_ts − quote_capture_ts` | `order_submit_ts` (Phase 1), `quote_capture_ts` (Phase 4) | null if either missing, unparsable, or reversed | Phase 4 |
| `quote_age_at_fill_ms` | `fill_ts − quote_capture_ts` | `fill_ts` (Phase 2), `quote_capture_ts` (Phase 4) | null if either missing, unparsable, or reversed | Phase 4 |
| `quote_stale_ms` | `max(quote_age_at_submit_ms, quote_age_at_fill_ms)` | Both age fields non-null, consistent `quote_lineage_id` | null if either age is null or `quote_lineage_id` mismatch | Phase 6 |
| `signal_to_submit_ms` | `order_submit_ts − signal_generated_ts` | `signal_generated_ts` (Phase 1, decision_log), `order_submit_ts` (Phase 1, execution_log), consistent `quote_lineage_id` OR `execution_trace_id` join | null if either missing or lineage mismatch | Phase 6 |

All derived metrics MUST:
- Default to null when required fields are absent. Never default to 0.
- Be wrapped in try/except returning null.
- Carry provenance label beside the metric value.
- Never affect order execution, risk decisions, or position management.

---

## Fail-Soft Rules

1. Missing `quote_lineage_id` must not break runtime. All downstream metrics null.
2. Missing `quote_capture_ts` must not break runtime. Age metrics null.
3. Reversed timestamps (`quote_capture_ts > order_submit_ts`) produce null age, not negative value.
4. Empty or None `token_pair_key` produces null `quote_lineage_id`.
5. Any exception in ID generation or age computation returns null. Exception never propagates.
6. `paper_fill` MUST emit even if all quote lineage fields are null.
7. Historical events without quote lineage fields are valid JSONL. Readers treat missing field as `NOT_COMPUTABLE`.
8. `quote_lineage_id` MUST NOT change the value of any existing field.
9. `_last_quote_lineage_context` read failure (key missing) produces null carry. No crash.
10. No fake live timestamps. No paper quote labels applied to live path.

---

## JSONL Compatibility

- All fields additive.
- No field renames.
- No deletion of existing proxy fields (`last_orderbook_refresh_at`, `orderbook_snapshot_age_ms_at_decision`, etc.).
- No historical JSONL rewrite.
- Existing readers tolerate missing quote lineage fields.
- New readers treat missing `quote_lineage_id` as `NOT_COMPUTABLE` for `quote_stale_ms`.
- Backfilling quote lineage IDs into historical records MUST use separate derived reports, not runtime JSONL rewrite.

---

## Tests Required Before Implementation

1. **ID generation tests:**
   - Same inputs produce same `quote_lineage_id`.
   - Empty `token_pair_key` produces null.
   - None `quote_capture_ts` produces null.
   - Exception in SHA-1 returns null.

2. **Payload shape tests:**
   - Decision payload carries `quote_lineage_id`, `quote_capture_ts`, `quote_snapshot_id`, `quote_source`.
   - `order_submit_attempt` carries `quote_lineage_id`, `quote_capture_ts`, `quote_age_at_submit_ms`.
   - `paper_fill` carries `quote_lineage_id`, `quote_capture_ts`, `quote_age_at_submit_ms`, `quote_age_at_fill_ms`.

3. **Fail-soft tests:**
   - Missing `quote_capture_ts` → `quote_age_at_submit_ms` null on submit.
   - Missing `quote_lineage_id` context → null on intent, submit, fill. No crash.
   - Reversed timestamps → null age, not negative.
   - Exception in computation → null, not propagated.

4. **Label tests:**
   - Paper fill carries `quote_metric_source: paper_proxy`.
   - Live path does not carry `paper_proxy` label on quote fields.

5. **Carry-through tests:**
   - `quote_lineage_id` on `paper_fill` matches `quote_lineage_id` on corresponding `order_submit_attempt` (same `execution_trace_id`).
   - `quote_capture_ts` on `paper_fill` matches `quote_capture_ts` on `decision` (same `candidate_trace_id`).

6. **Backward compatibility tests:**
   - Legacy payload without `quote_lineage_id` parses without error.
   - Existing fields (`last_orderbook_refresh_at`, `orderbook_snapshot_age_ms_at_decision`) unchanged.

7. **Phase 1–3 regression tests remain green:**
   - All Phase 1, Phase 2, Phase 3, and existing regression tests pass after Phase 4 patch.

---

## Future Metrics Unlocked by This Contract

| Metric | Prerequisite Fields | Phase |
|---|---|---|
| `quote_age_at_submit_ms` | `quote_capture_ts`, `order_submit_ts` | Phase 4 |
| `quote_age_at_fill_ms` | `quote_capture_ts`, `fill_ts` | Phase 4 |
| `quote_stale_ms` | Both age fields, consistent `quote_lineage_id` | Phase 6 |
| `signal_to_submit_ms` | `signal_generated_ts`, `order_submit_ts`, `quote_lineage_id` or `execution_trace_id` join | Phase 6 |
| Ghost fill truth | `quote_age_at_fill_ms` vs fill price delta | Phase 6 |
| Delay replay realism | `quote_lineage_id`, `quote_capture_ts`, `quote_age_at_submit_ms` | Phase 6 |
| Final derisk realism (S3 prerequisite) | `quote_stale_ms` across all fills | Phase 6 |

---

## S3 Implication

S3 status: CAUTION. No promotion.

Quote lineage is a prerequisite for fill realism assessment. Without `quote_stale_ms`, fills cannot be systematically audited for ghost fill risk. S3 promotion remains blocked until Phase 6 evidence exists.

---

## Safety

- Runtime behavior changed: No.
- Live behavior changed: No.
- Runtime code modified: No. (Contract only.)
- Strategy/risk/execution/live config modified: No.
- Replay run: No.
- Paper launch: No.
- Tests run: None (design/spec only).
- Persistent tests: Unchanged.
