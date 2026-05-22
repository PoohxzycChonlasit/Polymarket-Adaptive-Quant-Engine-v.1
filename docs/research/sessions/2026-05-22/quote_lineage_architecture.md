# Quote Lineage Architecture v1

Date: 2026-05-22

Scope: Design only. No code changes, no paper run, no replay, no S3 promotion, no runtime change.

Runtime behavior changed: No.

Live behavior changed: No.

Prerequisite phases complete: Phase 1 (canonical timestamps), Phase 2 (paper ack/fill), Phase 3 (derived proxy metrics).

---

## Purpose

Quote lineage connects the orderbook snapshot used at decision time to the submit and fill events that follow. Without it, `quote_stale_ms`, `signal_to_submit_ms` cross-log joins, ghost fill truth, and delay replay are all uncomputable.

Phase 4 adds the quote lineage layer. Phase 5 extends it to fill. Phase 6 computes `quote_stale_ms`.

---

## Existing Quote Context (already in runtime)

The following fields already exist on the trader instance and in decision payloads. They are the raw material for quote lineage — no new data capture is needed, only forwarding and ID generation.

### Instance state (per `ticker_key`)

| Field | Type | Meaning |
|---|---|---|
| `_last_orderbook_refresh_at_utc[ticker_key]` | str (ISO-8601 Z) | UTC timestamp of last orderbook refresh attempt |
| `_last_orderbook_refresh_monotonic[ticker_key]` | float | Monotonic time of last refresh (for age calculation) |
| `_last_orderbook_refresh_token_pair_key[ticker_key]` | str | Token pair key of last refresh |
| `_last_successful_yes_no_book_at_utc[ticker_key]` | str (ISO-8601 Z) | UTC timestamp of last successful executable yes/no book |
| `_last_successful_yes_no_book_monotonic[ticker_key]` | float | Monotonic time of last successful book |
| `_last_successful_yes_no_book_token_pair_key[ticker_key]` | str | Token pair key of last successful book |
| `_last_orderbook_refresh_source[ticker_key]` | str | Source of last refresh (REST, WS, etc.) |

### Already on decision payloads

| Field | Meaning |
|---|---|
| `last_orderbook_refresh_at` | UTC timestamp of last refresh |
| `orderbook_snapshot_age_ms_at_decision` | Age of snapshot at decision (monotonic-derived) |
| `last_successful_yes_no_book_at` | UTC timestamp of last executable book |
| `last_successful_yes_no_book_token_pair_key` | Token pair of last executable book |
| `orderbook_refresh_source` | Source label |
| `orderbook_lineage_match` | Whether decision token pair matches last successful book |
| `orderbook_current_fetch_status` | `fresh_fetch_executable`, `fresh_fetch_failed`, etc. |

These are proxy fields. Quote lineage Phase 4 promotes them into a stable, ID-keyed lineage that propagates through to submit and fill.

---

## New Fields: Quote Lineage Layer

### Canonical quote lineage fields

| Field | Type | Meaning | JSONL Destination | Null Condition |
|---|---|---|---|---|
| `quote_lineage_id` | str (`ql_` prefix) | Stable ID linking the quote snapshot at decision time to submit and fill events. Deterministic hash of `(market_id, token_pair_key, quote_capture_ts_truncated_to_second)`. | `decision_log`, `execution_log` | null if no successful book exists at decision time |
| `quote_capture_ts` | str (ISO-8601 Z) | UTC timestamp when the orderbook was last successfully captured as an executable yes/no book. Source: `_last_successful_yes_no_book_at_utc[ticker_key]`. | `decision_log`, `execution_log` | null if no successful book |
| `quote_snapshot_id` | str (`qs_` prefix) | ID for the specific snapshot. In Phase 4 identical to `quote_lineage_id`. Future phases may make this more granular (per-tick). | `decision_log` | null if no successful book |
| `quote_source` | str | Source of the quote: `clob_orderbook_rest`, `clob_orderbook_ws`, `stale_reuse`, `unknown`. Source: `orderbook_refresh_source` field. | `decision_log`, `execution_log` | `unknown` if source is unavailable |
| `quote_age_at_submit_ms` | float or null | `order_submit_ts − quote_capture_ts` in milliseconds. Computed at submit boundary. | `execution_log` (`order_submit_attempt`, `paper_fill`) | null if either timestamp missing or unparsable |
| `quote_age_at_fill_ms` | float or null | `fill_ts − quote_capture_ts` in milliseconds. Computed at fill boundary. | `execution_log` (`paper_fill`) | null if either timestamp missing or unparsable |

### ID generation (Phase 4 design)

```
quote_lineage_id = "ql_" + sha1(f"{market_id}|{token_pair_key}|{quote_capture_ts_second}").hexdigest()[:12]
quote_snapshot_id = "qs_" + sha1(f"{market_id}|{token_pair_key}|{quote_capture_ts_second}").hexdigest()[:12]
```

`quote_capture_ts_second` = ISO-8601 truncated to second precision (strip sub-second) for stability across concurrent decisions on the same snapshot.

---

## Lineage Flow: Decision → Submit → Fill

```
Orderbook fetch (each cycle, per ticker_key)
  ↓ writes _last_successful_yes_no_book_at_utc[ticker_key]
  ↓ writes _last_successful_yes_no_book_token_pair_key[ticker_key]
  ↓ writes _last_orderbook_refresh_source[ticker_key]

Decision boundary (_build_orderbook_timing_context)
  → compute quote_lineage_id from (market_id, token_pair_key, quote_capture_ts)
  → emit quote_lineage_id, quote_capture_ts, quote_snapshot_id, quote_source
  → store _last_quote_lineage_context[ticker_key] on instance
  → JSONL: decision_log (additive fields on existing decision payload)

order_intent_approved (_validate_submit_order_intent)
  → read _last_quote_lineage_context[ticker_key]
  → carry quote_lineage_id, quote_capture_ts forward
  → JSONL: execution_log (additive fields on existing order_intent_approved payload)

order_submit_attempt (_submit_order, before paper/live submit)
  → read quote_lineage_id, quote_capture_ts from local scope or instance
  → compute quote_age_at_submit_ms = order_submit_ts − quote_capture_ts
  → JSONL: execution_log (additive fields on existing order_submit_attempt payload)

paper_fill (_submit_order, paper path)
  → carry quote_lineage_id, quote_capture_ts, quote_age_at_submit_ms
  → compute quote_age_at_fill_ms = fill_ts − quote_capture_ts
  → JSONL: execution_log (additive fields on existing paper_fill payload)
```

### Instance state for forwarding

One new instance dict is required to carry quote lineage context from decision to submit:

```python
self._last_quote_lineage_context: dict[str, dict] = {}
```

Set at decision boundary. Consumed at `_validate_submit_order_intent` → `_submit_order`. This is consistent with existing per-`ticker_key` instance dicts.

---

## JSONL Destinations

| Event | Log | Phase 4 Fields Added |
|---|---|---|
| `decision` | `decision_log` | `quote_lineage_id`, `quote_capture_ts`, `quote_snapshot_id`, `quote_source` |
| `order_intent_approved` | `execution_log` | `quote_lineage_id`, `quote_capture_ts` |
| `order_submit_attempt` | `execution_log` | `quote_lineage_id`, `quote_capture_ts`, `quote_age_at_submit_ms` |
| `paper_fill` | `execution_log` | `quote_lineage_id`, `quote_capture_ts`, `quote_age_at_submit_ms`, `quote_age_at_fill_ms` |

Phase 5 (fill-side lineage) would extend this to `trade_open` and `trade_close` in `trade_journal`.

---

## Producer Boundaries

| Producer | Role | Inserts |
|---|---|---|
| `_build_orderbook_timing_context()` | Quote capture context builder | Generates `quote_lineage_id`, `quote_capture_ts`, `quote_snapshot_id`, `quote_source` and stores in `_last_quote_lineage_context[ticker_key]` |
| Decision payload builder (before `log_decision`) | Decision emitter | Reads from context, writes to decision payload |
| `_validate_submit_order_intent()` | Intent approval emitter | Reads from `_last_quote_lineage_context`, carries forward |
| `_submit_order()` | Submit + fill emitter | Reads carry-forward, computes `quote_age_at_submit_ms` and `quote_age_at_fill_ms` |

No new producers are required. All insertions are at existing emit boundaries.

---

## Paper vs Live Behavior

### Paper mode

| Field | Value | Source | Truth Level |
|---|---|---|---|
| `quote_capture_ts` | Real UTC timestamp from live REST/WS orderbook fetch | `_last_successful_yes_no_book_at_utc` | `proxy` (real timestamp but paper execution) |
| `quote_source` | Real source label (`clob_orderbook_rest`, etc.) | `orderbook_refresh_source` | Real |
| `quote_age_at_submit_ms` | Real age of live quote at paper submit time | Computed | `paper_proxy` (real quote, simulated submit) |
| `quote_age_at_fill_ms` | Real age of live quote at paper fill time | Computed | `paper_proxy` |
| `quote_lineage_id` | Deterministic — same snapshot same ID | Computed | Stable |

Paper quote age metrics are **useful and meaningful**: even in paper mode, the quote was a real live orderbook fetch. The quote age at submit tells us how stale the price information was when the order decision-to-submit transition occurred. This is the primary input for `quote_stale_ms` diagnostics.

### Live mode

| Field | Value | Source | Truth Level |
|---|---|---|---|
| `quote_capture_ts` | Real UTC timestamp from live REST/WS orderbook fetch | Same source | `live_observed` |
| `quote_age_at_submit_ms` | Real age of live quote at live submit time | Computed | `live_observed` |
| `quote_age_at_fill_ms` | Real age of live quote at live fill time | Computed | `live_observed` if fill_ts is live_observed |

No fake timestamps. No paper labels on live path.

---

## Fail-Soft Rules

1. If no successful executable book exists for the ticker at decision time, `quote_lineage_id` is null. All downstream quote age metrics are null.
2. If `quote_capture_ts` is missing or unparsable, `quote_age_at_submit_ms` is null. Never default to 0.
3. If `quote_lineage_id` is missing from the instance at submit time (context not set), pass null through. Do not fabricate.
4. Null `quote_age_at_fill_ms` does not block `paper_fill` emission. All existing fill fields emit regardless.
5. If `quote_capture_ts` is later than `order_submit_ts` (impossible in normal operation but defensively handled), `quote_age_at_submit_ms` is null.
6. No exception from quote lineage computation may propagate to order execution. All computation wrapped in try/except returning null.
7. Historical events without `quote_lineage_id` remain valid JSONL. Readers must treat missing field as `NOT_COMPUTABLE`.
8. `quote_lineage_id` must not change the value of any existing field.

---

## Backward Compatibility

All Phase 4 fields are additive. No existing field is removed, renamed, or changed in value. The following existing proxy fields remain unchanged:

- `last_orderbook_refresh_at`
- `orderbook_snapshot_age_ms_at_decision`
- `last_successful_yes_no_book_at`
- `last_successful_yes_no_book_token_pair_key`
- `orderbook_lineage_match`
- `orderbook_current_fetch_status`

Phase 4 adds canonical IDs and a forwarded carry. Proxy fields are kept for backward compatibility and as redundant signals.

---

## Future Metrics Unlocked

### `quote_stale_ms` (Phase 6)

```
quote_stale_ms = max(quote_age_at_submit_ms, quote_age_at_fill_ms)
```

Requires: `quote_lineage_id` consistent across submit and fill, both age fields non-null.

Meaning: Maximum staleness of the quote at any execution boundary. High value → price discovered on a stale book → ghost fill risk.

### `signal_to_submit_ms` (cross-log join, Phase 6)

Currently blocked because `signal_generated_ts` is on `decision_log` and `order_submit_ts` is on `execution_log`. The join key is `candidate_trace_id` / `execution_trace_id`. With `quote_lineage_id` shared across both logs, a second join path exists:

```
decision where quote_lineage_id = X  →  order_submit_attempt where quote_lineage_id = X
→ signal_to_submit_ms = order_submit_ts − signal_generated_ts
```

This is a secondary join path. The primary join remains `execution_trace_id`.

### Ghost fill truth (Phase 6)

A "ghost fill" is a paper fill on a stale or fabricated quote. With `quote_age_at_fill_ms`, the staleness of the price at fill is directly observable. Thresholds can be set for:

- `quote_age_at_submit_ms > N ms` → flag as stale-submit
- `quote_age_at_fill_ms > M ms` → flag as ghost fill risk

### Delay replay realism (Phase 6)

Replay currently has no quote staleness context. With `quote_lineage_id`, a replay tool can reconstruct: which quote snapshot was used at what age, what the market had moved to by fill time, and whether the fill price is realistic given quote staleness.

### Final derisk realism (Phase 6 / S3 prerequisite)

S3 promotion requires evidence that fills are not at arbitrary prices. `quote_age_at_fill_ms` and `quote_stale_ms` provide the staleness evidence required to assess fill realism. Without these fields, fill price quality cannot be systematically audited.

---

## Field Graph

```
Orderbook fetch
  │
  ├─ quote_capture_ts ──────────────────────────────────────────────────────┐
  │   (= _last_successful_yes_no_book_at_utc)                                │
  │                                                                          │
  ├─ quote_lineage_id ──────────────────────────────────────────────────────┤
  │   (hash of market_id + token_pair_key + quote_capture_ts_second)         │
  │                                                                          │
  └─ quote_source                                                            │
      (= orderbook_refresh_source)                                           │
              │                                                              │
              ▼                                                              │
         decision payload                                                    │
         (decision_log)                                                      │
              │                                                              │
              ├─ quote_lineage_id  ◄─────────────────────────────────────────┘
              ├─ quote_capture_ts
              ├─ quote_snapshot_id
              └─ quote_source
                      │
                      ▼
         order_intent_approved
         (execution_log)
              ├─ quote_lineage_id
              └─ quote_capture_ts
                      │
                      ▼
         order_submit_attempt                  order_submit_ts (Phase 1)
         (execution_log)                            │
              ├─ quote_lineage_id                   │
              ├─ quote_capture_ts                   │
              └─ quote_age_at_submit_ms ◄───────────┘
                  = order_submit_ts − quote_capture_ts
                      │
                      ▼
         paper_fill                            fill_ts (Phase 2)
         (execution_log)                            │
              ├─ quote_lineage_id                   │
              ├─ quote_capture_ts                   │
              ├─ quote_age_at_submit_ms (carried)   │
              └─ quote_age_at_fill_ms ◄─────────────┘
                  = fill_ts − quote_capture_ts

              ▼ (Phase 6)
         quote_stale_ms
              = max(quote_age_at_submit_ms, quote_age_at_fill_ms)
```

---

## Dependency on Completed Phases

| Phase | Status | Dependency for Phase 4 |
|---|---|---|
| Phase 1 (canonical timestamps) | COMPLETE (commit b3994ee) | `order_submit_ts` available for `quote_age_at_submit_ms` |
| Phase 2 (paper ack/fill timestamps) | COMPLETE (commit 850d70c) | `fill_ts` available for `quote_age_at_fill_ms` |
| Phase 3 (derived paper proxy metrics) | COMPLETE (commit 7d01a7d) | Established pattern for inline metric computation |
| Phase 4 (quote lineage) | THIS DESIGN | Prerequisite for Phases 5–6 |

---

## Implementation Phase Order (Phase 4 scope)

Phase 4 implementation (when authorized):

1. Add `_quote_lineage_id_for_context` helper: deterministic hash of `(market_id, token_pair_key, quote_capture_ts_second)`.
2. Add `_last_quote_lineage_context: dict[str, dict]` instance state.
3. In `_build_orderbook_timing_context`: generate and return `quote_lineage_id`, `quote_capture_ts`, `quote_snapshot_id`, `quote_source`. Store in `_last_quote_lineage_context[ticker_key]`.
4. In decision payload builder: read from `_last_quote_lineage_context`, add fields to decision payload.
5. In `_validate_submit_order_intent`: read `_last_quote_lineage_context`, carry `quote_lineage_id` and `quote_capture_ts` to `order_intent_approved` payload.
6. In `_submit_order`: read carry-forward, compute `quote_age_at_submit_ms`, add to `order_submit_attempt` payload.
7. In paper fill path: carry forward, compute `quote_age_at_fill_ms`, add to `paper_fill` payload.
8. All computation wrapped in try/except returning null.
9. Tests: shape tests (fields present), fail-soft tests (null on missing), label tests (paper_proxy), live-clean test (live path carries no fabricated quote age).
10. Paper validation run: verify coverage on decision, submit, and fill events.

Phase 5 (fill-side lineage to trade journal) is a separate scope.

---

## Safety

- Runtime behavior changed: No.
- Live behavior changed: No.
- Runtime code modified: No. (Design only.)
- Strategy/risk/execution/live config modified: No.
- Replay run: No.
- Paper launch: No.
- S3 promotion: No. CAUTION maintained.
