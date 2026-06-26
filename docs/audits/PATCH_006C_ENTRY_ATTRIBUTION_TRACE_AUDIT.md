# Patch 6C Entry Attribution Trace Audit (PATCH_006C_ENTRY_ATTRIBUTION_TRACE_AUDIT)

This document details the read-only audit of the missing `candidate_trace_id` field inside the `entry_attribution` snapshot, which causes new model-driven trades to be quarantined by the Edge Inventory Report tool.

---

## Precheck Validation

1. **No paper runtime is active**: **FAIL** (Processes `22072` and `43468` are active).
2. **Owner file absent or inactive**: **FAIL** (`paper_runtime_owner.json` is active).
3. **Logs not growing**: **FAIL** (Active CSV logs are currently growing).
4. **New evidence exists after Patch 6B timestamp**: Checked.

---

## Diagnostic Answers

### 1. Presence in `quant_detail`
* **Question**: Is `candidate_trace_id` present in `quant_detail` before position metadata is built?
* **Answer**: **NO**. The `clob_detail` dict and the returned `detail` inside `_record_quant_detail` only contain the keys `candidate_instance_trace_id` (mapped to `candidate.candidate_trace_id`) and `candidate_id` (legacy hash-based), but completely lack a key named `candidate_trace_id`.

### 2. Presence in Decision Payload
* **Question**: Is `candidate_trace_id` present in decision payload before trade open?
* **Answer**: **YES**. It is added dynamically to the decision payload during emission/logging in `_emit_quant_event` -> `_display_payload_with_candidate_trace_identity` using companion-field hashing.

### 3. Missing in `_build_trade_position_metadata()` Inputs
* **Question**: Is `candidate_trace_id` missing in `_build_trade_position_metadata()` inputs?
* **Answer**: **YES**. The signature of `_build_trade_position_metadata()` does not accept trace fields directly, so it relies on pulling them from `self.last_quant_details[ticker_key]`.

### 4. Overwritten inside `_build_trade_position_metadata()`
* **Question**: Is `candidate_trace_id` overwritten to null inside `_build_trade_position_metadata()`?
* **Answer**: **NO**. It is not overwritten; it is queried from `quant_details.get("candidate_trace_id")`. Since this key is missing from `quant_details`, the dict query returns `None`, which is serialized as `null` in the final metadata.

### 5. Naming Mismatch
* **Question**: Is there a naming mismatch between `candidate_trace_id`, `candidate_instance_trace_id`, and `parent_candidate_trace_id`?
* **Answer**: **YES**.
  * `candidate_trace_id` on the `OpportunityCandidate` object represents the specific candidate instance trace ID.
  * In `clob_detail` / `quant_detail`, this is mapped to `"candidate_instance_trace_id"`.
  * Meanwhile, `"candidate_trace_id"` is expected by `_build_trade_position_metadata()` and the Edge Inventory Report tool to represent the companion-derived (legacy parent) trace ID.
  * Since `"candidate_trace_id"` is never mapped or derived within `_record_quant_detail`, it remains missing in `quant_details`.

### 6. Recommended Source Field
* **Question**: Which field should `entry_attribution.candidate_trace_id` use?
* **Answer**: **C. logger-derived trace** (companion-derived trace). Using the companion-field hashing mechanism ensures that the trace ID inside `entry_attribution` matches the `candidate_trace_id` written at the root of the logged decision, risk, and trade events.

### 7. Smallest Safe Fix
* **Question**: What is the smallest safe fix?
* **Answer**: At the end of `_record_quant_detail` in `polymarket/trader.py` (around line 5480), dynamically derive `candidate_trace_id` from the companion fields of the detail payload using the existing `QuantEventLogger._candidate_trace_identity_fields` helper:
  ```python
  companion = QuantEventLogger._candidate_trace_identity_fields(detail, self._utc_timestamp())
  if companion.get("candidate_trace_id"):
      detail["candidate_trace_id"] = companion["candidate_trace_id"]
  ```
  This stores `candidate_trace_id` in `self.last_quant_details`, allowing `_build_trade_position_metadata()` to successfully retrieve and write it to the `entry_attribution` snapshot without interface changes.

### 8. Required Tests
* **Question**: Which tests are needed?
* **Answer**: We should update [test_entry_attribution_snapshot.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tests/test_entry_attribution_snapshot.py) to assert that `candidate_trace_id` is successfully derived and populated during the mock execution flow, rather than requiring it to be explicitly injected.

---

## Audit Details

### Root Cause
`entry_attribution.candidate_trace_id` is evaluated to `None` because `_build_trade_position_metadata()` pulls this field from the cached `quant_details` (sourced from `last_quant_details`), which only contains `"candidate_instance_trace_id"` and lacks a `"candidate_trace_id"` key. While the logging layer dynamically appends the companion `"candidate_trace_id"` to root-level event payloads via `_display_payload_with_candidate_trace_identity`, it does not enrich nested dictionaries like `entry_attribution`.

### Exact Source Location
* **Omission Location**: [polymarket/trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L9060-L9088) inside the `clob_detail` dict population.
* **Retrieval Location**: [polymarket/trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L4535-L4550) inside `_build_trade_position_metadata()`.

### Affected Evidence
* **Trade Journal Logs**: In [2026-06-15.jsonl](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/runtime/quant_data/trade_journal/2026-06-15.jsonl), lines 36 and 38 (`trade_open` events) contain `null` inside `"entry_attribution": { "candidate_trace_id": null }` despite having valid root-level `"candidate_trace_id"` values.
* **Edge Inventory Report**: New trades are quarantined as `malformed_attribution` in [edge_inventory_report_v1.json](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/runtime/reports/edge_inventory_report_v1.json#L993-L1005).

---

## Recommended Fix

At the end of `_record_quant_detail` (specifically before returning `detail` around line 5480), enrich the quant details with the companion-derived `candidate_trace_id`:

```python
        # Derive companion trace ID for attribution downstream
        companion = QuantEventLogger._candidate_trace_identity_fields(detail, self._utc_timestamp())
        if companion.get("candidate_trace_id"):
            detail["candidate_trace_id"] = companion["candidate_trace_id"]
```

---

## Test Plan

1. **Unit Tests**:
   * Run pytest suite: `python -m pytest tests/ -q`
   * Update [test_entry_attribution_snapshot.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tests/test_entry_attribution_snapshot.py) to assert that `candidate_trace_id` is automatically populated during `_record_quant_detail` -> `_build_trade_position_metadata` calls.
2. **Offline Replay**:
   * Run the offline report generator: `python tools/edge_inventory_report.py --date 2026-06-15`
   * Verify that new `PROBABILITY_EV_EDGE` trades are successfully grouped under the signal summary instead of being quarantined.

---

## Risk Level
* **LOW**. The proposed fix is purely telemetry-focused. It modifies only the local caching of quant details for logging/observability and has zero impact on strategy thresholds, EV estimation, risk sizing, or live order routing.

---

## Final Recommendation
Implement the fix in `_record_quant_detail` to populate `candidate_trace_id` from the companion trace. This will resolve the quarantine issue in the Edge Inventory Report without violating the shadow propagation constraints.
