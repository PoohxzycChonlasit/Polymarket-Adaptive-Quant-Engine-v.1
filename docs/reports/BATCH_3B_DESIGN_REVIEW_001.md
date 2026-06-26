# Batch 3B Design Review Report

**Date:** 2026-06-27  
**Role:** 29_ARCHITECTURE_GOVERNANCE_AGENT  
**Supporting Role:** 27_VERIFICATION_OFFICER_AGENT  
**Task Class:** 0 (HEALTH_CHECK / DESIGN_REVIEW)  
**Verdict:** BATCH_3B_DESIGN_NEEDS_SCOPE_REDUCTION  
**Active Question Status:** OPEN — LOW_PRICE_TRUTH_RESOLUTION_001  

---

## 1. Scope and Risk Assessment

The proposed Batch 3B design (`BATCH_3B_DESIGN_001.md`) encompasses 14 state fields and 5 helper methods, covering orderbook refresh details, scheduler cadence latencies, and quote lineage contexts. Attempting to extract all of these components concurrently presents high structural complexity and integration risks.

### 1.1 Execution Path & Lineage Coupling
- **Lineage Context (`_last_quote_lineage_context`):** This is updated directly inside `_phase4_build_quote_lineage` which is called from the live order submission/execution path.
- **Risk:** Extracting the lineage context to the helper creates runtime dependencies within the critical order-execution path. If any delegation shim fails during live execution, order submission will crash.
- **Recommendation:** Defer the quote lineage context entirely from Batch 3B to eliminate any risk to the execution path.

### 1.2 Property Shim Risk (`__new__` mocks)
- **Lazy Initialization Danger:** The design proposes lazy initialization of `self._observability` via `self.settings` if shims are accessed.
- **Risk:** Unit tests using `__new__` often do not set `self.settings` before mock properties are set. Doing `TraderObservabilityHelper(self.settings)` would raise `AttributeError: 'PolymarketTrader' object has no attribute 'settings'`.
- **Correction:** Use a safer fallback lookup:
  ```python
  if not hasattr(self, "_observability"):
      from polymarket.orchestration.trader_observability import TraderObservabilityHelper
      from config.settings import get_settings
      settings = getattr(self, "settings", None) or get_settings()
      self._observability = TraderObservabilityHelper(settings)
  ```

---

## 2. Recommended Scope Correction

To align with conservative architecture governance, we recommend **Option B + Option D (Scope Reduction)**:

### 2.1 Reduced Scope: Batch 3B-1 (Orderbook Refresh Timing Only)
Only the following items will be extracted in the next immediate step (Batch 3B-1):
- **Fields:**
  - `_last_orderbook_refresh_at_utc`
  - `_last_orderbook_refresh_monotonic`
  - `_last_orderbook_refresh_source`
  - `_last_orderbook_refresh_trigger`
  - `_last_orderbook_refresh_token_pair_key`
  - `_last_successful_yes_no_book_at_utc`
  - `_last_successful_yes_no_book_monotonic`
  - `_last_successful_yes_no_book_token_pair_key`
- **Methods:**
  - `_mark_orderbook_refresh`
  - `_orderbook_refresh_observability_detail`

### 2.2 Deferred Scope (Batch 3B-2 / Subsequent Batches)
- **Cadence/Scheduler Timing:** `_last_decision_cycle_monotonic`, `_market_evaluation_started_monotonic`, `_market_evaluation_started_at_utc`, `_current_cycle_market_sequence_index`, `_current_cycle_market_sequence_count`, `_scheduler_cadence_observability_detail`, `_emit_hybrid_v1_snapshot`
- **Lineage Context:** `_last_quote_lineage_context`
- **Event Identifiers:** `_event_producer_label`

---

## 3. Final Verdict

```
BATCH_3B_DESIGN_NEEDS_SCOPE_REDUCTION
```
