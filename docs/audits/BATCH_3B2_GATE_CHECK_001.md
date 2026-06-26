# BATCH_3B2_GATE_CHECK_001

**Date:** 2026-06-27  
**Task Class:** 2 (DESIGN_ONLY / ARCHITECTURE AUDIT)  
**Document type:** Gate check audit  
**Destination:** `docs/audits/`  
**Baseline:** `1317010` — working tree clean  
**Phase Review Verdict:** PROCEED_TO_BATCH_3B2_GATE

---

## 1. Baseline State

| Item | Value |
|------|-------|
| HEAD | `1317010 docs: add batch 3 phase review` |
| `trader.py` size | 12,913 lines, 294 methods |
| `trader_observability.py` size | 285 lines, 7 methods |
| Working tree | clean |
| Active Question | OPEN — `LOW_PRICE_TRUTH_RESOLUTION_001` (does NOT block structural refactors) |

---

## 2. Dependency Audit — State Fields

### 2.1 `_last_decision_cycle_monotonic` — dict[str, float]

| Property | Detail |
|----------|--------|
| Init location | `trader.py` line 470 |
| **Read locations** | `trader_observability.py` line 209 (`getattr(trader, "_last_decision_cycle_monotonic", {}).get(ticker_key)`) |
| **Write locations** | `trader_observability.py` lines 214-216 (`trader._last_decision_cycle_monotonic[ticker_key] = now_mono`) |
| Runtime ownership | Pure timing dict — cycle interval tracking for JSONL |
| JSONL ownership | `decision_cycle_interval_seconds` in `_orderbook_refresh_observability_detail` output |
| Execution coupling | **NONE** — written from observability method only |
| Scheduler coupling | **NONE** — tracks cycle intervals passively |
| Test direct SET | **0 tests** — not set directly in any test file |
| **Risk score** | 1/10 (lowest) |
| **Safe Extraction Score** | 10/10 |
| Proxy strategy | Property shim (getter+setter) |
| Notes | **Already half-migrated**: the helper's `_orderbook_refresh_observability_detail` already reads/writes it via `trader.*`. Moving the field to helper changes these to `self.*` — trivial. |

---

### 2.2 `_market_evaluation_started_monotonic` — dict[str, float]

| Property | Detail |
|----------|--------|
| Init location | `trader.py` line 471 |
| **Read locations** | `_scheduler_cadence_observability_detail` line 1342 (via `getattr`) |
| **Write locations** | `_mark_market_evaluation_started` line 1330 (`self._market_evaluation_started_monotonic[ticker_key] = time.monotonic()`) |
| **Clear locations** | `_begin_cycle_timing` line 1286 (`self._market_evaluation_started_monotonic.clear()`) |
| Runtime ownership | Per-ticker monotonic timestamp at market evaluation start |
| JSONL ownership | `market_evaluation_duration_ms`, `market_evaluation_started_ms_since_cycle` in scheduler cadence payload |
| Execution coupling | **NONE** — read/written only by observability and timing methods |
| Scheduler coupling | **LOW** — cleared at cycle start by `_begin_cycle_timing`; `.clear()` on live dict object works correctly through property shim |
| Test direct SET | **7 test files** set `trader._market_evaluation_started_monotonic = {}`; `test_paper_mode.py:1070` does `trader._market_evaluation_started_monotonic["BTC"] -= 0.05` (in-place mutation) |
| **Risk score** | 3/10 |
| **Safe Extraction Score** | 8/10 |
| Proxy strategy | Property shim (getter+setter); getter returns live dict so `.clear()` and in-place mutation both work |
| Notes | `.clear()` call in `_begin_cycle_timing` will work correctly since property getter returns the same dict object on the helper — `.clear()` is called in-place on that dict. |

---

### 2.3 `_market_evaluation_started_at_utc` — dict[str, str]

| Property | Detail |
|----------|--------|
| Init location | `trader.py` line 472 |
| **Read locations** | `_scheduler_cadence_observability_detail` line 1359 (via `getattr`) |
| **Write locations** | `_mark_market_evaluation_started` line 1331 |
| **Clear locations** | `_begin_cycle_timing` line 1287 |
| Test direct SET | **7 test files** set `trader._market_evaluation_started_at_utc = {}` |
| **Risk score** | 3/10 |
| **Safe Extraction Score** | 8/10 |
| Proxy strategy | Property shim (getter+setter) — identical pattern to `_market_evaluation_started_monotonic` |

---

### 2.4 `_current_cycle_market_sequence_index` — dict[str, int]

| Property | Detail |
|----------|--------|
| Init location | `trader.py` line 473 |
| **Read locations** | `_scheduler_cadence_observability_detail` line 1360 (via `getattr`) |
| **Write locations** | `_mark_market_evaluation_started` line 1333 (conditional) |
| **Clear locations** | `_begin_cycle_timing` line 1288 |
| Test direct SET | **0 tests** |
| **Risk score** | 2/10 |
| **Safe Extraction Score** | 9/10 |
| Proxy strategy | Property shim (getter+setter) |

---

### 2.5 `_current_cycle_market_sequence_count` — dict[str, int]

| Property | Detail |
|----------|--------|
| Init location | `trader.py` line 474 |
| **Read locations** | `_scheduler_cadence_observability_detail` line 1361 (via `getattr`, fallback to `_current_cycle_market_count`) |
| **Write locations** | `_mark_market_evaluation_started` line 1335 (conditional) |
| **Clear locations** | `_begin_cycle_timing` line 1289 |
| Test direct SET | **0 tests** |
| **Risk score** | 2/10 |
| **Safe Extraction Score** | 9/10 |
| Proxy strategy | Property shim (getter+setter) |

---

## 3. Dependency Audit — Methods

### 3.1 `_event_producer_label(event_method: str) -> str` — line 797

| Property | Detail |
|----------|--------|
| Implementation | Simple dict lookup; maps `log_market_snapshot` → `"market_snapshots"` etc. (8 entries) |
| **Called from** | Lines 1176, 1220 (both within `_observability_health_from_payload` context) |
| State reads | **NONE** — pure function, no instance state access |
| State writes | **NONE** |
| Execution coupling | **NONE** |
| Test direct access | **0 tests** |
| **Risk score** | 1/10 |
| **Safe Extraction Score** | 10/10 |
| Proxy strategy | Simple method proxy `def _event_producer_label(self, m): return self._get_observability()._event_producer_label(m)` |
| Notes | **Lowest-risk item in entire Batch 3B-2 scope.** No state, no execution coupling, pure string mapping. |

---

### 3.2 `_scheduler_cadence_observability_detail(ticker: str) -> dict` — line 1337

| Property | Detail |
|----------|--------|
| **Called from** | Line 3986 (within cycle evaluation loop), Line 5496 (within market scan loop) |
| **State reads — 3B-2 fields (move to helper)** | `_market_evaluation_started_monotonic`, `_market_evaluation_started_at_utc`, `_current_cycle_market_sequence_index`, `_current_cycle_market_sequence_count` (all via `getattr(self, ...)`) |
| **State reads — already in helper (Batch 3B-1)** | `_last_successful_yes_no_book_monotonic`, `_last_successful_yes_no_book_at_utc`, `_last_orderbook_refresh_source` (accessible via property getters OR `self.*` in helper) |
| **State reads — remain on trader (pass via `trader` arg)** | `_cycle_started_monotonic`, `_last_empty_book_recovery_detail`, `_configured_decision_loop_interval_seconds`, `_intended_decision_loop_target_seconds`, `_effective_outer_loop_interval_seconds`, `_snapshot_sampling_interval_seconds`, `_market_discovery_interval_seconds`, `_outer_loop_poll_interval_seconds`, `_current_cycle_market_count` |
| **Method calls — remain on trader** | `self._cycle_elapsed_ms()`, `self._utc_timestamp()` |
| State writes | **NONE** — pure read + return dict |
| Execution coupling | **NONE** — docstring: "Expose cycle/market hot-path timing without changing cadence or gates." |
| Test direct access | **0 tests** call this directly |
| **Risk score** | 3/10 |
| **Safe Extraction Score** | 8/10 |
| Proxy strategy | Method proxy passes `self` as `trader` arg. Helper method signature: `def _scheduler_cadence_observability_detail(self, trader: Any, ticker: str) -> dict` |
| Notes | After Batch 3B-2 moves the 5 cadence fields to the helper, the method reads `self._market_evaluation_started_monotonic.get(...)` etc. (from helper). Reads for already-moved Batch 3B-1 fields (`_last_successful_yes_no_book_*`, `_last_orderbook_refresh_source`) also become `self.*`. Reads for remaining-on-trader fields use `getattr(trader, ...)`. |

---

### 3.3 `_emit_hybrid_v1_snapshot(ticker, outcome, timing_payload)` — line 4412

| Property | Detail |
|----------|--------|
| **Called from** | Line 4404 (wrapped in `try: ... except Exception: pass`) |
| **State reads — remain on trader** | `_preloaded_next_markets`, `_preload_started_ts`, `_preload_success_ts`, `_preload_failed_reason`, `_preload_lead_seconds`, `_preload_book_ready_ts` |
| **Args with rich data** | `outcome: TradeOutcome` (carries `.display`, `.decision`, `.market_id`, `.skip_reason`, `.skipped`), `timing_payload: dict` |
| **Method calls — remain on trader** | `self._ticker_from_market_id()`, `self.quant_events.log_hybrid_v1_snapshot()` |
| State writes | **NONE** to any moved fields |
| Execution coupling | **NONE** — docstring: "Offline-only research evidence — does not affect strategy, risk, or execution." |
| Call site safety | Wrapped in `try: ... except Exception: pass` — fail-soft |
| **Risk score** | 4/10 (higher than other 3B-2 items due to preload state dependencies) |
| **Safe Extraction Score** | 7/10 |
| Proxy strategy | Method proxy passes `self` as `trader` arg. Helper method: `def _emit_hybrid_v1_snapshot(self, trader: Any, ticker: str, outcome: Any, timing_payload: dict) -> None`. All preload state accessed via `getattr(trader, ...)`. |
| Notes | More complex than other Batch 3B-2 items due to 6 preload field reads and typed `TradeOutcome` arg. The `trader: Any` pattern handles the preload reads. Consider extracting this last within Batch 3B-2, after fields and simpler methods. |

---

## 4. Dependency Graph

```
trader.py owns (to be moved in Batch 3B-2):
  _last_decision_cycle_monotonic ──────────────────────────► trader_observability.py
  _market_evaluation_started_monotonic ────────────────────► trader_observability.py
  _market_evaluation_started_at_utc ───────────────────────► trader_observability.py
  _current_cycle_market_sequence_index ────────────────────► trader_observability.py
  _current_cycle_market_sequence_count ────────────────────► trader_observability.py
  _event_producer_label ───────────────────────────────────► trader_observability.py
  _scheduler_cadence_observability_detail ─────────────────► trader_observability.py
  _emit_hybrid_v1_snapshot ────────────────────────────────► trader_observability.py

trader.py retains (permanent or out-of-scope):
  _cycle_started_monotonic ────────────────────────────────► PERMANENT (cycle timing root)
  _last_empty_book_recovery_detail ────────────────────────► PERMANENT (orderbook recovery)
  _current_cycle_market_count ─────────────────────────────► PERMANENT (scalar counter)
  _configured_decision_loop_interval_seconds etc ──────────► PERMANENT (runtime config)
  _preloaded_next_markets, _preload_* ─────────────────────► PERMANENT (preload system)
  _begin_cycle_timing() ───────────────────────────────────► PERMANENT (cycle root writer)
  _mark_market_evaluation_started() ──────────────────────► PERMANENT (writer proxy needed)

Dependencies within trader_observability.py AFTER Batch 3B-2:
  _scheduler_cadence_observability_detail(trader, ticker):
    self._market_evaluation_started_monotonic (moved 3B-2)
    self._market_evaluation_started_at_utc (moved 3B-2)
    self._current_cycle_market_sequence_index (moved 3B-2)
    self._current_cycle_market_sequence_count (moved 3B-2)
    self._last_successful_yes_no_book_monotonic (moved 3B-1)
    self._last_successful_yes_no_book_at_utc (moved 3B-1)
    self._last_orderbook_refresh_source (moved 3B-1)
    getattr(trader, "_cycle_started_monotonic", ...)
    getattr(trader, "_last_empty_book_recovery_detail", ...)
    getattr(trader, "_configured_*", ...)
    trader._cycle_elapsed_ms()
    trader._utc_timestamp()
```

---

## 5. Ownership Graph After Batch 3B-2

```
TraderObservabilityHelper (trader_observability.py) — post-3B-2 state:
  [From Batch 3A]   _recent_display_trades
                    _observability_health_display_state
                    _record_display_trade()
                    dashboard_observability_health_state()
                    _observability_health_from_payload()

  [From Batch 3B-1] _last_orderbook_refresh_{at_utc, monotonic, source, trigger, token_pair_key}
                    _last_successful_yes_no_book_{at_utc, monotonic, token_pair_key}
                    _mark_orderbook_refresh()
                    _orderbook_refresh_observability_detail()

  [From Batch 3B-2] _last_decision_cycle_monotonic
                    _market_evaluation_started_monotonic
                    _market_evaluation_started_at_utc
                    _current_cycle_market_sequence_index
                    _current_cycle_market_sequence_count
                    _event_producer_label()
                    _scheduler_cadence_observability_detail()
                    _emit_hybrid_v1_snapshot()
```

---

## 6. Blast Radius Assessment

| Risk area | Assessment |
|-----------|-----------|
| Test suite | 7 test files directly SET `_market_evaluation_started_monotonic` and `_market_evaluation_started_at_utc`; property shims required. `test_paper_mode.py:1070` does in-place mutation — works correctly through getter returning live dict. |
| `_begin_cycle_timing()` `.clear()` calls | SAFE — `.clear()` on dict returned by property getter mutates the helper's dict in-place. No behavior change. |
| `_mark_market_evaluation_started()` | Must remain on trader as a writer; it sets fields via `self.*` which will hit the property setters → delegate to helper. Proxy NOT needed — setter path handles it. |
| `_scheduler_cadence_observability_detail` call sites | 2 call sites (lines 3986, 5496). After extraction, trader proxy `def _scheduler_cadence_observability_detail(self, ticker): return self._get_observability()._scheduler_cadence_observability_detail(self, ticker)` handles both transparently. |
| `_emit_hybrid_v1_snapshot` call site | 1 call site (line 4404), already wrapped in `try/except`. Any extraction error is fail-soft. |
| `_last_decision_cycle_monotonic` migration | `trader_observability.py` currently writes `trader._last_decision_cycle_monotonic` (via `trader.*`). After moving the field, those writes become `self._last_decision_cycle_monotonic` — this requires **updating the 2 write lines inside `_orderbook_refresh_observability_detail` in the helper**. This is a small but critical internal edit to the already-committed helper code. |

---

## 7. Critical Implementation Note: Helper Internal Update Required

When `_last_decision_cycle_monotonic` moves to the helper, the 2 existing lines in `trader_observability.py::_orderbook_refresh_observability_detail` must be updated:

**Current (Batch 3B-1):**
```python
if not hasattr(trader, "_last_decision_cycle_monotonic"):
    trader._last_decision_cycle_monotonic = {}
trader._last_decision_cycle_monotonic[ticker_key] = now_mono
```

**After Batch 3B-2:**
```python
self._last_decision_cycle_monotonic[ticker_key] = now_mono
```

The read on line 209 also changes:
```python
# Current:
previous_decision_mono = getattr(trader, "_last_decision_cycle_monotonic", {}).get(ticker_key)
# After:
previous_decision_mono = self._last_decision_cycle_monotonic.get(ticker_key)
```

This is a **3-line internal edit to an already-committed helper file** — it is in scope for Batch 3B-2.

---

## 8. Forbidden Scope Verification

Confirmed these remain permanently in `trader.py` and are NOT candidates:

| Item | Line | Status | Reason |
|------|------|--------|--------|
| `_phase4_build_quote_lineage` | 1239 | **PERMANENT** | Execution path — writes lineage context |
| `_phase4_quote_lineage_carry` | 1267 | **PERMANENT** | Execution path — reads lineage context |
| `_last_quote_lineage_context` | 469 | **PERMANENT** | Written from execution path |
| `_risk_plan_zero_diagnostics` | 3567 | **PERMANENT** | Risk-coupled — reads bankroll tiers/modes |
| `_diagnostic_float` | 3550 | **PERMANENT** | Used in 99+ core math paths |
| `_diagnostic_int` | 3559 | **PERMANENT** | Used in 99+ core math paths |

All 6 forbidden items verified present in `trader.py` at expected lines. None are in `trader_observability.py`.

---

## 9. Recommended Extraction Order Within Batch 3B-2

| Step | Item(s) | Rationale |
|------|---------|-----------|
| 1 | 5 cadence fields + helper internal update | Fields first; also update `_orderbook_refresh_observability_detail` reads/writes in helper |
| 2 | `_event_producer_label` | Simplest method, no state, 1-line proxy |
| 3 | `_scheduler_cadence_observability_detail` | Reads all moved fields (step 1 must be done first for `self.*` to work) |
| 4 | `_emit_hybrid_v1_snapshot` | Most complex — last, after all fields and simpler methods validated |

**Single-commit approach is safe** — all items are observability-only with no execution coupling. Extracting in one commit reduces intermediate risk states.

---

## 10. Implementation Checklist

- [ ] Pre-implementation baseline test run (capture pass/fail counts)
- [ ] Grep `_market_evaluation_started_*` across tests to confirm setter-override count
- [ ] Move 5 fields to `TraderObservabilityHelper.__init__`
- [ ] Update 3 lines inside `_orderbook_refresh_observability_detail` in helper (3B-1 → 3B-2 transition)
- [ ] Add 10 property shims in `trader.py` (5 fields × getter + setter)
- [ ] Move `_event_producer_label` to helper, add proxy
- [ ] Move `_scheduler_cadence_observability_detail` to helper (accepts `trader: Any`), add proxy
- [ ] Move `_emit_hybrid_v1_snapshot` to helper (accepts `trader: Any`), add proxy
- [ ] `py_compile` both files
- [ ] `IMPORT_OK` check
- [ ] Full test run — zero new failures expected
- [ ] 5-cycle paper run with JSONL field verification for cadence fields

---

## Final Verdict

```
PROCEED_BATCH_3B2
```

**Summary:** All 8 Batch 3B-2 candidates are OBSERVABILITY_ONLY with zero execution coupling. Safe Extraction Scores range from 7/10 (`_emit_hybrid_v1_snapshot`) to 10/10 (`_event_producer_label`, `_last_decision_cycle_monotonic`). Test touchpoints are well-understood: 7 test files SET `_market_evaluation_started_*` fields, handled by property shims returning live dicts. The critical internal update to `_orderbook_refresh_observability_detail` (3 lines in the helper) is straightforward. Recommended extraction order: fields → `_event_producer_label` → `_scheduler_cadence_observability_detail` → `_emit_hybrid_v1_snapshot`. Forbidden scope confirmed intact.
