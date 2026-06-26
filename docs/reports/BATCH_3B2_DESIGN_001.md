# BATCH_3B2_DESIGN_001

**Date:** 2026-06-27  
**Role:** 02_CODE_ARCHITECT_AGENT  
**Supporting Role:** 29_ARCHITECTURE_GOVERNANCE_AGENT  
**Task Class:** 2 (DESIGN_ONLY)  
**Document type:** Implementation design  
**Destination:** `docs/reports/`  
**Gate:** `docs/audits/BATCH_3B2_GATE_CHECK_001.md` — Verdict: PROCEED_BATCH_3B2  
**Active Question:** OPEN — `LOW_PRICE_TRUTH_RESOLUTION_001` (does NOT block structural refactors)

---

## 1. Ownership Diagram

```
BEFORE Batch 3B-2
═══════════════════════════════════════════════════════
PolymarketTrader (trader.py)
  ├─ [deferred from 3B-1]
  │   _last_decision_cycle_monotonic: dict[str,float]
  │   _market_evaluation_started_monotonic: dict[str,float]
  │   _market_evaluation_started_at_utc: dict[str,str]
  │   _current_cycle_market_sequence_index: dict[str,int]
  │   _current_cycle_market_sequence_count: dict[str,int]
  │   _event_producer_label()
  │   _scheduler_cadence_observability_detail()
  │   _emit_hybrid_v1_snapshot()
  └─ [permanent — never move]
      _phase4_build_quote_lineage()
      _phase4_quote_lineage_carry()
      _last_quote_lineage_context
      _risk_plan_zero_diagnostics()
      _diagnostic_float() / _diagnostic_int()

AFTER Batch 3B-2
═══════════════════════════════════════════════════════
PolymarketTrader (trader.py)
  ├─ [property shims → helper]
  │   _last_decision_cycle_monotonic (getter+setter)
  │   _market_evaluation_started_monotonic (getter+setter)
  │   _market_evaluation_started_at_utc (getter+setter)
  │   _current_cycle_market_sequence_index (getter+setter)
  │   _current_cycle_market_sequence_count (getter+setter)
  ├─ [method proxies → helper]
  │   _event_producer_label()
  │   _scheduler_cadence_observability_detail()
  │   _emit_hybrid_v1_snapshot()
  └─ [permanent — unchanged]
      _begin_cycle_timing()  ← writes fields via property setters
      _mark_market_evaluation_started()  ← writes fields via property setters
      _phase4_build_quote_lineage() / _phase4_quote_lineage_carry()
      _last_quote_lineage_context
      _risk_plan_zero_diagnostics() / _diagnostic_float() / _diagnostic_int()

TraderObservabilityHelper (trader_observability.py)
  ├─ [Batch 3A] display state, recent trades, health monitoring
  ├─ [Batch 3B-1] orderbook refresh timing (8 fields + 2 methods)
  └─ [Batch 3B-2 — NEW]
      _last_decision_cycle_monotonic: dict[str,float]
      _market_evaluation_started_monotonic: dict[str,float]
      _market_evaluation_started_at_utc: dict[str,str]
      _current_cycle_market_sequence_index: dict[str,int]
      _current_cycle_market_sequence_count: dict[str,int]
      _event_producer_label(event_method: str) -> str
      _scheduler_cadence_observability_detail(trader: Any, ticker: str) -> dict
      _emit_hybrid_v1_snapshot(trader: Any, ticker, outcome, timing_payload) -> None
```

---

## 2. Runtime Data Flow

```
CYCLE START
  trader._begin_cycle_timing()
    ├─ self._market_evaluation_started_monotonic.clear()
    │   └─ hits @property getter → returns helper dict → .clear() in-place ✓
    ├─ self._market_evaluation_started_at_utc.clear()  [same]
    ├─ self._current_cycle_market_sequence_index.clear()  [same]
    └─ self._current_cycle_market_sequence_count.clear()  [same]

PER-MARKET EVALUATION START
  trader._mark_market_evaluation_started(ticker, sequence_index, sequence_count)
    ├─ self._market_evaluation_started_monotonic[key] = time.monotonic()
    │   └─ hits @property getter → live dict → dict[key] = ... ✓
    ├─ self._market_evaluation_started_at_utc[key] = self._utc_timestamp()  [same]
    ├─ self._current_cycle_market_sequence_index[key] = int(sequence_index)  [same]
    └─ self._current_cycle_market_sequence_count[key] = int(sequence_count)  [same]

ORDERBOOK REFRESH (already in helper)
  trader._mark_orderbook_refresh(...)
    └─ self._get_observability()._mark_orderbook_refresh(...)

DECISION CYCLE TIMING (moved 3B-2)
  trader._orderbook_refresh_observability_detail(ticker)
    └─ self._get_observability()._orderbook_refresh_observability_detail(self, ticker)
       ├─ self._last_decision_cycle_monotonic.get(key)  ← NOW self.* (was trader.*)
       └─ self._last_decision_cycle_monotonic[key] = now_mono  ← NOW self.* (was trader.*)

CADENCE DETAIL (moved 3B-2)
  trader._scheduler_cadence_observability_detail(ticker)
    └─ self._get_observability()._scheduler_cadence_observability_detail(self, ticker)
       ├─ self._market_evaluation_started_monotonic.get(key)
       ├─ self._market_evaluation_started_at_utc.get(key)
       ├─ self._current_cycle_market_sequence_index.get(key)
       ├─ self._current_cycle_market_sequence_count.get(key)
       ├─ self._last_successful_yes_no_book_monotonic.get(key)  [Batch 3B-1 field]
       ├─ self._last_successful_yes_no_book_at_utc.get(key)  [Batch 3B-1 field]
       ├─ self._last_orderbook_refresh_source.get(key)  [Batch 3B-1 field]
       ├─ getattr(trader, "_cycle_started_monotonic", 0.0)  [stays on trader]
       ├─ getattr(trader, "_last_empty_book_recovery_detail", {}).get(key)
       ├─ getattr(trader, "_configured_decision_loop_interval_seconds", None)
       ├─ getattr(trader, "_intended_decision_loop_target_seconds", 1.0)
       ├─ trader._cycle_elapsed_ms()
       └─ trader._utc_timestamp()

HYBRID SNAPSHOT (moved 3B-2)
  trader._emit_hybrid_v1_snapshot(ticker, outcome, timing_payload)
    └─ self._get_observability()._emit_hybrid_v1_snapshot(self, ticker, outcome, timing_payload)
       ├─ getattr(trader, "_preloaded_next_markets", {}).get(ticker)
       ├─ getattr(trader, "_preload_started_ts", 0)
       ├─ getattr(trader, "_preload_success_ts", 0)
       ├─ getattr(trader, "_preload_failed_reason", None)
       ├─ getattr(trader, "_preload_lead_seconds", 0)
       ├─ getattr(trader, "_preload_book_ready_ts", 0)
       ├─ trader._ticker_from_market_id(outcome.market_id)
       └─ trader.quant_events.log_hybrid_v1_snapshot(payload)
```

---

## 3. Property Shim Strategy

All 5 cadence fields require getter+setter shims. The getter returns the **live dict object** on the helper — not a copy — so that:
- In-place mutations (`self._market_evaluation_started_monotonic["BTC"] -= 0.05`) work correctly
- `.clear()` calls in `_begin_cycle_timing` work in-place

```python
# trader.py — 5 property shims (getter + setter × 5 = 10 decorators)

@property
def _last_decision_cycle_monotonic(self) -> "dict[str, float]":
    return self._get_observability()._last_decision_cycle_monotonic

@_last_decision_cycle_monotonic.setter
def _last_decision_cycle_monotonic(self, val: "dict[str, float]") -> None:
    self._get_observability()._last_decision_cycle_monotonic = val

@property
def _market_evaluation_started_monotonic(self) -> "dict[str, float]":
    return self._get_observability()._market_evaluation_started_monotonic

@_market_evaluation_started_monotonic.setter
def _market_evaluation_started_monotonic(self, val: "dict[str, float]") -> None:
    self._get_observability()._market_evaluation_started_monotonic = val

@property
def _market_evaluation_started_at_utc(self) -> "dict[str, str]":
    return self._get_observability()._market_evaluation_started_at_utc

@_market_evaluation_started_at_utc.setter
def _market_evaluation_started_at_utc(self, val: "dict[str, str]") -> None:
    self._get_observability()._market_evaluation_started_at_utc = val

@property
def _current_cycle_market_sequence_index(self) -> "dict[str, int]":
    return self._get_observability()._current_cycle_market_sequence_index

@_current_cycle_market_sequence_index.setter
def _current_cycle_market_sequence_index(self, val: "dict[str, int]") -> None:
    self._get_observability()._current_cycle_market_sequence_index = val

@property
def _current_cycle_market_sequence_count(self) -> "dict[str, int]":
    return self._get_observability()._current_cycle_market_sequence_count

@_current_cycle_market_sequence_count.setter
def _current_cycle_market_sequence_count(self, val: "dict[str, int]") -> None:
    self._get_observability()._current_cycle_market_sequence_count = val
```

**`.clear()` interaction verification:** `self._market_evaluation_started_monotonic.clear()` in `_begin_cycle_timing`:
1. `self._market_evaluation_started_monotonic` hits the `@property` getter
2. Getter returns `self._get_observability()._market_evaluation_started_monotonic` — the live dict on the helper
3. `.clear()` is called on that dict in-place
4. Helper's dict is now empty — correct behavior ✓

---

## 4. Proxy Method Strategy

### 4.1 `_event_producer_label` proxy

```python
# trader.py — simplest proxy in this batch
def _event_producer_label(self, event_method: str) -> str:
    return self._get_observability()._event_producer_label(event_method)
```

Helper implementation (move verbatim):
```python
# trader_observability.py
def _event_producer_label(self, event_method: str) -> str:
    return {
        "log_market_snapshot": "market_snapshots",
        "log_decision": "decision_log",
        "log_execution": "execution_log",
        "log_risk_event": "risk_log",
        "log_trade_open": "trade_journal",
        "log_trade_close": "trade_journal",
        "log_trade_path_checkpoint": "path_truth",
        "log_orderbook_lineage_probe": "orderbook_lineage",
        "log_system_health": "system_health",
    }.get(event_method, "unknown")
```

### 4.2 `_scheduler_cadence_observability_detail` proxy

```python
# trader.py — passes self as trader context
def _scheduler_cadence_observability_detail(self, ticker: str) -> "dict[str, object]":
    return self._get_observability()._scheduler_cadence_observability_detail(self, ticker)
```

Helper implementation (move body, replace `self.*` with appropriate `self.*` or `getattr(trader, ...)`):
```python
# trader_observability.py
def _scheduler_cadence_observability_detail(
    self,
    trader: Any,
    ticker: str,
) -> "dict[str, object]":
    ticker_key = ticker.upper()
    now_mono = time.monotonic()
    cycle_started = float(getattr(trader, "_cycle_started_monotonic", 0.0) or 0.0)
    market_started = self._market_evaluation_started_monotonic.get(ticker_key)  # self.*
    last_success_mono = self._last_successful_yes_no_book_monotonic.get(ticker_key)  # self.*
    recovery_detail = getattr(trader, "_last_empty_book_recovery_detail", {}).get(ticker_key, {})
    # ... (full body, replacing getattr(self, "_market_evaluation_*", {}) → self.*)
    # ... all _last_successful_yes_no_book_at_utc.get() → self.*
    # ... all _last_orderbook_refresh_source.get() → self.*
    # ... all _configured_*, _intended_* → getattr(trader, ...)
    # ... trader._cycle_elapsed_ms(), trader._utc_timestamp() as-is
    return detail
```

### 4.3 `_emit_hybrid_v1_snapshot` proxy

```python
# trader.py — passes self as trader context
def _emit_hybrid_v1_snapshot(
    self,
    ticker: str,
    outcome: "TradeOutcome",
    timing_payload: "dict[str, object]",
) -> None:
    self._get_observability()._emit_hybrid_v1_snapshot(self, ticker, outcome, timing_payload)
```

Helper implementation (all `self.*` → `getattr(trader, ...)` for preload fields):
```python
# trader_observability.py
def _emit_hybrid_v1_snapshot(
    self,
    trader: Any,
    ticker: str,
    outcome: Any,
    timing_payload: "dict[str, object]",
) -> None:
    _next_market = getattr(trader, "_preloaded_next_markets", {}).get(ticker)
    snapshot_payload = {
        **timing_payload,
        "preload_started_ts": getattr(trader, "_preload_started_ts", 0),
        "preload_success_ts": getattr(trader, "_preload_success_ts", 0),
        "preload_failed_reason": getattr(trader, "_preload_failed_reason", None),
        "preload_lead_seconds": getattr(trader, "_preload_lead_seconds", 0),
        "preload_book_ready_ts": getattr(trader, "_preload_book_ready_ts", 0),
        # ... rest of body unchanged
    }
    # quant_events call via trader reference:
    # trader.quant_events.log_hybrid_v1_snapshot(snapshot_payload)
```

---

## 5. Internal Helper Update — `_last_decision_cycle_monotonic` Transition

This is the **most critical step** in Batch 3B-2. The existing `_orderbook_refresh_observability_detail` in `trader_observability.py` (Batch 3B-1) currently accesses `_last_decision_cycle_monotonic` via `trader.*` because the field was deferred. After Batch 3B-2 moves the field to the helper, those 3 lines must be updated.

**Current state (Batch 3B-1, lines ~209–216 in `trader_observability.py`):**
```python
previous_decision_mono = getattr(trader, "_last_decision_cycle_monotonic", {}).get(ticker_key)
# ...
if not hasattr(trader, "_last_decision_cycle_monotonic"):
    trader._last_decision_cycle_monotonic = {}
trader._last_decision_cycle_monotonic[ticker_key] = now_mono
```

**After Batch 3B-2 (field now on helper):**
```python
previous_decision_mono = self._last_decision_cycle_monotonic.get(ticker_key)
# ...
self._last_decision_cycle_monotonic[ticker_key] = now_mono
# (the hasattr guard is removed — field always exists after __init__)
```

**Net change to helper:** 3 lines replaced by 2 lines. The docstring comment on this method must also be updated to remove the note about `_last_decision_cycle_monotonic` being on trader.

---

## 6. Test Compatibility

### Fields directly SET in tests

| Field | Test files | Action |
|-------|-----------|--------|
| `_market_evaluation_started_monotonic` | 7 files (`= {}`) + `test_paper_mode.py` (`["BTC"] -= 0.05`) | Property setter routes to helper; in-place mutation via getter returns live dict ✓ |
| `_market_evaluation_started_at_utc` | 7 files (`= {}`) | Property setter routes to helper ✓ |
| `_last_decision_cycle_monotonic` | **0 files** | No test compatibility concern |
| `_current_cycle_market_sequence_index` | **0 files** | No test compatibility concern |
| `_current_cycle_market_sequence_count` | **0 files** | No test compatibility concern |

### Test pattern for fields (existing — from Batch 3B-1 tests, verified working):
```python
# Tests set the field:
trader._market_evaluation_started_monotonic = {}
# → hits @property.setter → calls _get_observability() → helper.__init__ creates {} already → replaces helper field

# Tests then set individual keys:
trader._market_evaluation_started_monotonic["BTC"] = some_value
# → hits @property getter → returns live dict on helper → dict["BTC"] = value ✓

# Tests do in-place arithmetic:
trader._market_evaluation_started_monotonic["BTC"] -= 0.05
# → hits getter → returns live dict → mutates in-place ✓
```

### `_event_producer_label` tests
No tests directly call `_event_producer_label` by name. It is called internally by `_observability_health_from_payload` (already delegated to helper in Batch 3A). After proxy is added, the call chain is:
```
trader._event_producer_label(m)  [proxy]
  → helper._event_producer_label(m)  [implementation]
```
And the existing `_observability_health_from_payload` in helper calls:
```python
producer = trader._event_producer_label(event_method)
```
This continues to work through the proxy (trader delegates to helper, which is the same object) ✓

### `_scheduler_cadence_observability_detail` and `_emit_hybrid_v1_snapshot` tests
No tests directly call these methods by name. They are called from within the trading loop. The proxy delegation pattern (as proven in Batch 3A and 3B-1) is transparent to call sites.

---

## 7. `__new__` Compatibility

The existing `_get_observability()` accessor (added in Batch 3B-1) already handles `__new__`-constructed test traders:

```python
def _get_observability(self) -> "TraderObservabilityHelper":
    if not hasattr(self, "_observability"):
        self._observability = TraderObservabilityHelper(
            settings=getattr(self, "settings", None)  # None if __new__ used
        )
    return self._observability
```

After Batch 3B-2, `TraderObservabilityHelper.__init__` adds 5 new fields:
```python
self._last_decision_cycle_monotonic: dict[str, float] = {}
self._market_evaluation_started_monotonic: dict[str, float] = {}
self._market_evaluation_started_at_utc: dict[str, str] = {}
self._current_cycle_market_sequence_index: dict[str, int] = {}
self._current_cycle_market_sequence_count: dict[str, int] = {}
```

When a test uses `__new__` and then does `trader._market_evaluation_started_monotonic = {}`:
1. Property setter calls `_get_observability()`
2. `_get_observability()` sees no `_observability` attr → creates `TraderObservabilityHelper(settings=None)`
3. All 5 new fields initialized to `{}` ✓
4. Setter replaces the field with the test's `{}` ✓

No `get_settings()` is called. No Pydantic validators triggered. No `.env` file read.

---

## 8. Runtime Preservation

### `_begin_cycle_timing` (stays on trader)
Calls `.clear()` on all 4 market evaluation fields. After Batch 3B-2:
- `self._market_evaluation_started_monotonic.clear()` → getter → live helper dict → `.clear()` in-place ✓
- `self._market_evaluation_started_at_utc.clear()` → same ✓
- `self._current_cycle_market_sequence_index.clear()` → same ✓
- `self._current_cycle_market_sequence_count.clear()` → same ✓

**No behavioral change.** The `.clear()` still empties the dicts between cycles.

### `_mark_market_evaluation_started` (stays on trader)
Sets values on the 4 fields via `self._market_evaluation_started_monotonic[key] = ...` etc. After Batch 3B-2, these hit property getters returning live helper dicts — the assignment into the dict is identical in behavior.

### Cadence JSONL output
`_scheduler_cadence_observability_detail` produces the same dict keys and values. The only change is WHERE the fields are read from (helper vs trader). The JSONL shape is identical.

### Hybrid snapshot JSONL output
`_emit_hybrid_v1_snapshot` produces identical output. All preload fields are accessed via `getattr(trader, ...)` — same values as direct `self._preload_*` access.

---

## 9. Forbidden Scope Verification

These items must NOT be touched in Batch 3B-2:

| Item | Location | Status |
|------|----------|--------|
| `_phase4_build_quote_lineage` | `trader.py` line 1239 | **PERMANENT** — execution path |
| `_phase4_quote_lineage_carry` | `trader.py` line 1267 | **PERMANENT** — execution path |
| `_last_quote_lineage_context` | `trader.py` line 469 | **PERMANENT** — written from execution path |
| `_risk_plan_zero_diagnostics` | `trader.py` line 3567 | **PERMANENT** — risk-coupled |
| `_diagnostic_float` | `trader.py` line 3550 | **PERMANENT** — core math dependency |
| `_diagnostic_int` | `trader.py` line 3559 | **PERMANENT** — core math dependency |

Implementation must stop immediately (hard stop) if any of these are modified.

---

## 10. Rollback Plan

```bash
git restore polymarket/trader.py polymarket/orchestration/trader_observability.py
```

Restores HEAD to `210b6ba` (current clean state). Zero blast radius — only these 2 files are touched in Batch 3B-2.

---

## 11. Verification Plan

| Step | Command | Pass criterion |
|------|---------|----------------|
| 1. Baseline | Run tests before editing | Record pass/fail counts (expect: 1 pre-existing fail in test_paper_mode) |
| 2. Compile | `py_compile trader.py trader_observability.py` | COMPILE_OK |
| 3. Import | `from polymarket.trader import PolymarketTrader; print('IMPORT_OK')` | IMPORT_OK |
| 4. Full tests | `pytest tests/ -q` | 0 new failures vs baseline |
| 5. Targeted tests | `pytest tests/test_execution_timestamp_phase*.py tests/test_outcome_truth_patch.py tests/test_quote_age_phase5.py tests/test_quote_lineage_phase4.py -q` | All pass (these directly SET the moved fields) |
| 6. Paper mode | `python main.py --mode paper --interval 60` ×5 cycles | Boot clean, DATA_OK, 0 AttributeError, exit 0 |
| 7. JSONL cadence | Check `_scheduler_cadence_observability_detail` output fields in event stream | `market_evaluation_duration_ms`, `market_evaluation_started_at`, `market_sequence_index` present |
| 8. JSONL decision timing | Check `decision_cycle_interval_seconds` in `_orderbook_refresh_observability_detail` output | Field present, non-null after first decision cycle |
| 9. Forbidden scope | `git diff -- ... | grep "_phase4\|_last_quote_lineage\|_risk_plan_zero\|_diagnostic_"` | Empty — no matches |

---

## 12. Implementation Order

| Step | Action | Files changed |
|------|--------|--------------|
| 1 | Add 5 field inits to `TraderObservabilityHelper.__init__` | `trader_observability.py` |
| 2 | Update 3 lines in `_orderbook_refresh_observability_detail` (trader.* → self.*) | `trader_observability.py` |
| 3 | Add `_event_producer_label` to helper | `trader_observability.py` |
| 4 | Add `_scheduler_cadence_observability_detail(trader, ticker)` to helper | `trader_observability.py` |
| 5 | Add `_emit_hybrid_v1_snapshot(trader, ticker, outcome, timing_payload)` to helper | `trader_observability.py` |
| 6 | Remove 5 field inits from `trader.__init__` (replace with comment) | `trader.py` |
| 7 | Add 10 property shims (5 × getter+setter) | `trader.py` |
| 8 | Replace `_event_producer_label` body with proxy | `trader.py` |
| 9 | Replace `_scheduler_cadence_observability_detail` body with proxy | `trader.py` |
| 10 | Replace `_emit_hybrid_v1_snapshot` body with proxy | `trader.py` |

**All in one commit.** The 10 steps are internally consistent — no intermediate state is valid without all steps complete.

---

## 13. Change Count Estimate

| File | Expected changes |
|------|----------------|
| `polymarket/orchestration/trader_observability.py` | +~120 lines (5 field inits, 3-line internal update, 3 new methods) |
| `polymarket/trader.py` | +~60 lines added (10 property shims), −~80 lines removed (5 field inits + 3 method bodies) — net ~−20 lines |

---

## Final Verdict

```
READY_FOR_BATCH_3B2_IMPLEMENTATION
```

All design decisions are consistent with the gate check findings. The proxy/shim pattern is proven across Batches 1, 2A, 3A, and 3B-1 (zero regressions). The critical `_last_decision_cycle_monotonic` internal update is clearly specified (3 lines → 2 lines, removing the `trader.*` access pattern). Forbidden scope is explicitly listed and must be verified untouched via `git diff` before committing.
