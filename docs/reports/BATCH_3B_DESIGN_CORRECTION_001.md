# BATCH_3B_DESIGN_CORRECTION_001

**Date:** 2026-06-27  
**Role:** 02_CODE_ARCHITECT_AGENT  
**Supporting Role:** 29_ARCHITECTURE_GOVERNANCE_AGENT  
**Task Class:** 2 (DESIGN_ONLY)  
**Document type:** Design correction report  
**Destination:** `docs/reports/`  
**Source design:** `docs/reports/BATCH_3B_DESIGN_001.md`  
**Review verdict:** `BATCH_3B_DESIGN_NEEDS_SCOPE_REDUCTION` (`docs/reports/BATCH_3B_DESIGN_REVIEW_001.md`)  
**Active Question:** OPEN — `LOW_PRICE_TRUTH_RESOLUTION_001` (does NOT block structural refactor)

---

## 1. Correction Summary

The original Batch 3B design proposed 14 state fields and 5 methods in a single extraction. The design review identified two blocking concerns:

| Concern | Original design flaw | Correction |
|---------|---------------------|-----------|
| Lineage coupling | `_last_quote_lineage_context` written inside `_phase4_build_quote_lineage` (execution path) | Defer to Batch 3B-2 |
| Cadence/scheduler coupling | `_scheduler_cadence_observability_detail`, `_emit_hybrid_v1_snapshot`, and timing fields cross into runtime timing | Defer to Batch 3B-2 |
| Lazy init crash | `self.settings` unavailable when tests use `__new__` | `TraderObservabilityHelper(settings=None)` — helper accepts `None`; `_get_observability()` passes `getattr(self, "settings", None)` without importing `get_settings()` |

**Result:** Batch 3B is split into:
- **Batch 3B-1** (this document): orderbook refresh timing only — 8 fields + 2 methods
- **Batch 3B-2** (future): cadence/scheduler timing + event identifiers + lineage

---

## 2. Batch 3B-1 Scope (Final)

### 2.1 Allowed: Fields

| Field | Current location | Batch 3B-1 decision | Justification |
|-------|-----------------|---------------------|---------------|
| `_last_orderbook_refresh_at_utc` | `trader.py` line 467 | **MOVE to helper** | Pure timing dict, observability only |
| `_last_orderbook_refresh_monotonic` | `trader.py` line 468 | **MOVE to helper** | Monotonic timestamps for refresh-age calc |
| `_last_orderbook_refresh_source` | `trader.py` line 469 | **MOVE to helper** | Transport method tag (WS/HTTP) |
| `_last_orderbook_refresh_trigger` | `trader.py` line 470 | **MOVE to helper** | Event trigger tag (TUI/schedule) |
| `_last_orderbook_refresh_token_pair_key` | `trader.py` line 471 | **MOVE to helper** | Token pair lineage key |
| `_last_successful_yes_no_book_at_utc` | `trader.py` line 472 | **MOVE to helper** | Last executable fetch UTC |
| `_last_successful_yes_no_book_monotonic` | `trader.py` line 473 | **MOVE to helper** | Last executable fetch monotonic |
| `_last_successful_yes_no_book_token_pair_key` | `trader.py` line 474 | **MOVE to helper** | Last executable fetch pair key |

### 2.2 Allowed: Methods

| Method | Batch 3B-1 decision | Key dependency notes |
|--------|---------------------|---------------------|
| `_mark_orderbook_refresh` | **MOVE to helper** | Calls `_utc_timestamp()` and `_orderbook_token_pair_key()` — resolved by pre-computing in trader proxy before delegating |
| `_orderbook_refresh_observability_detail` | **MOVE to helper** | Reads `_last_decision_cycle_monotonic` (deferred field, stays on trader) and `_cycle_started_at_utc` — resolved by accepting `trader: Any` as first arg |

### 2.3 Deferred from Batch 3B-1 (all moved to Batch 3B-2 or later)

| Item | Reason deferred |
|------|----------------|
| `_last_quote_lineage_context` | Written from `_phase4_build_quote_lineage` (execution path) — per design review |
| `_phase4_build_quote_lineage` | EXECUTION_COUPLED — stays in trader |
| `_phase4_quote_lineage_carry` | EXECUTION_COUPLED — stays in trader |
| `_last_decision_cycle_monotonic` | Written inside `_orderbook_refresh_observability_detail` — keeping on trader via `trader` arg reference in helper |
| `_market_evaluation_started_monotonic` | Cadence/runtime timing — Batch 3B-2 |
| `_market_evaluation_started_at_utc` | Cadence/runtime timing — Batch 3B-2 |
| `_current_cycle_market_sequence_index` | Runtime loop counter — Batch 3B-2 |
| `_current_cycle_market_sequence_count` | Runtime loop counter — Batch 3B-2 |
| `_scheduler_cadence_observability_detail` | Closer to execution timing — Batch 3B-2 |
| `_emit_hybrid_v1_snapshot` | Assembles timing dict touching runtime state — Batch 3B-2 |
| `_event_producer_label` | Kept together with cadence helpers — Batch 3B-2 |
| `_risk_plan_zero_diagnostics` | RISK_COUPLED — keep in trader permanently |
| `_diagnostic_float` | RUNTIME_COUPLED — keep in trader permanently |
| `_diagnostic_int` | RUNTIME_COUPLED — keep in trader permanently |

---

## 3. Updated Ownership Diagram

```
PolymarketTrader
  ├── Core loop, evaluation, signals, risk, execution (PERMANENT)
  ├── _phase4_build_quote_lineage (PERMANENT — execution path)
  ├── _phase4_quote_lineage_carry (PERMANENT — execution path)
  ├── _last_quote_lineage_context (PERMANENT for now — deferred to 3B-2)
  ├── _last_decision_cycle_monotonic (PERMANENT for now — deferred to 3B-2)
  ├── _risk_plan_zero_diagnostics (PERMANENT — risk coupled)
  ├── _diagnostic_float / _diagnostic_int (PERMANENT — runtime coupled)
  │
  │   ┌── Property shims (route to helper) ──────────────────────────┐
  │   │  _last_orderbook_refresh_at_utc                             │
  │   │  _last_orderbook_refresh_monotonic                          │
  │   │  _last_orderbook_refresh_source                             │
  │   │  _last_orderbook_refresh_trigger                            │
  │   │  _last_orderbook_refresh_token_pair_key                     │
  │   │  _last_successful_yes_no_book_at_utc                        │
  │   │  _last_successful_yes_no_book_monotonic                     │
  │   │  _last_successful_yes_no_book_token_pair_key                │
  │   └──────────────────────────────────────────────────────────────┘
  │
  │   ┌── Method proxies (delegate to helper) ────────────────────────┐
  │   │  _mark_orderbook_refresh(...)                                │
  │   │  _orderbook_refresh_observability_detail(...)                │
  │   └──────────────────────────────────────────────────────────────┘
  │
  └──► TraderObservabilityHelper (trader_observability.py)
         ├── [existing] _recent_display_trades
         ├── [existing] _observability_health_display_state
         ├── [existing] methods from Batch 3A
         │
         └── [NEW in 3B-1] orderbook refresh state + methods
               _last_orderbook_refresh_at_utc: dict[str, str]
               _last_orderbook_refresh_monotonic: dict[str, float]
               _last_orderbook_refresh_source: dict[str, str]
               _last_orderbook_refresh_trigger: dict[str, str]
               _last_orderbook_refresh_token_pair_key: dict[str, str]
               _last_successful_yes_no_book_at_utc: dict[str, str]
               _last_successful_yes_no_book_monotonic: dict[str, float]
               _last_successful_yes_no_book_token_pair_key: dict[str, str]
               _mark_orderbook_refresh(ticker, *, source, trigger, ...)
               _orderbook_refresh_observability_detail(trader, ticker, ...)
```

---

## 4. Corrected Implementation Design

### 4.1 TraderObservabilityHelper additions (`trader_observability.py`)

```python
# --- Added inside TraderObservabilityHelper.__init__ ---
self._last_orderbook_refresh_at_utc: dict[str, str] = {}
self._last_orderbook_refresh_monotonic: dict[str, float] = {}
self._last_orderbook_refresh_source: dict[str, str] = {}
self._last_orderbook_refresh_trigger: dict[str, str] = {}
self._last_orderbook_refresh_token_pair_key: dict[str, str] = {}
self._last_successful_yes_no_book_at_utc: dict[str, str] = {}
self._last_successful_yes_no_book_monotonic: dict[str, float] = {}
self._last_successful_yes_no_book_token_pair_key: dict[str, str] = {}
```

```python
# --- New method: _mark_orderbook_refresh ---
# Accepts pre-computed now_mono, now_utc, token_pair_key from trader proxy
# to avoid any dependency on trader methods inside the helper.
def _mark_orderbook_refresh(
    self,
    ticker: str,
    *,
    source: str,
    trigger: str,
    now_mono: float,
    now_utc: str,
    token_pair_key: str,
    executable_yes_no_book: bool = False,
) -> None:
    ticker_key = ticker.upper()
    self._last_orderbook_refresh_monotonic[ticker_key] = now_mono
    self._last_orderbook_refresh_at_utc[ticker_key] = now_utc
    self._last_orderbook_refresh_source[ticker_key] = source
    self._last_orderbook_refresh_trigger[ticker_key] = trigger
    self._last_orderbook_refresh_token_pair_key[ticker_key] = token_pair_key
    if executable_yes_no_book:
        self._last_successful_yes_no_book_monotonic[ticker_key] = now_mono
        self._last_successful_yes_no_book_at_utc[ticker_key] = now_utc
        self._last_successful_yes_no_book_token_pair_key[ticker_key] = token_pair_key
```

```python
# --- New method: _orderbook_refresh_observability_detail ---
# Accepts trader: Any as first arg (consistent with existing _observability_health_from_payload).
# Reads _last_decision_cycle_monotonic and _cycle_started_at_utc from trader
# (these remain on trader — deferred to Batch 3B-2).
def _orderbook_refresh_observability_detail(
    self,
    trader: Any,
    ticker: str,
    *,
    current_executable_yes_no_book: bool = False,
    record_decision_cycle: bool = False,
    current_fetch_succeeded: bool | None = None,
    condition_id: object = "",
    yes_token_id: object = "",
    no_token_id: object = "",
    market_slug: object = "",
) -> dict[str, object]:
    import time
    ticker_key = ticker.upper()
    now_mono = time.monotonic()
    last_refresh_mono = self._last_orderbook_refresh_monotonic.get(ticker_key)
    last_success_mono = self._last_successful_yes_no_book_monotonic.get(ticker_key)
    # _last_decision_cycle_monotonic remains on trader (deferred field)
    previous_decision_mono = getattr(trader, "_last_decision_cycle_monotonic", {}).get(ticker_key)
    decision_interval = None
    if record_decision_cycle:
        if previous_decision_mono is not None:
            decision_interval = round(max(0.0, now_mono - previous_decision_mono), 3)
        if not hasattr(trader, "_last_decision_cycle_monotonic"):
            trader._last_decision_cycle_monotonic = {}
        trader._last_decision_cycle_monotonic[ticker_key] = now_mono
    # ... remainder of computation logic unchanged, reading from self.* for 8 moved fields
    # and from trader.* for _cycle_started_at_utc and _last_decision_cycle_monotonic
    decision_token_pair_key = trader._orderbook_token_pair_key(
        condition_id=condition_id, yes_token_id=yes_token_id,
        no_token_id=no_token_id, market_slug=market_slug,
    )
    # ... (full stale_source classification logic copied verbatim, referencing self.*)
    return { ... }  # same output dict as current implementation
```

**Key design principle:** The helper only reads from `self.*` for the 8 fields it owns. It reads from `trader.*` exclusively for fields not yet migrated (`_last_decision_cycle_monotonic`, `_cycle_started_at_utc`). It calls `trader._orderbook_token_pair_key(...)` for the pair-key computation (a stateless utility on trader).

### 4.2 Proxy and property shims in `trader.py`

```python
# --- Method proxy: _mark_orderbook_refresh ---
# Pre-computes the values that require trader methods, then delegates to helper.
def _mark_orderbook_refresh(
    self,
    ticker: str,
    *,
    source: str,
    trigger: str,
    executable_yes_no_book: bool = False,
    condition_id: object = "",
    yes_token_id: object = "",
    no_token_id: object = "",
    market_slug: object = "",
) -> None:
    import time
    now_mono = time.monotonic()
    now_utc = self._utc_timestamp()
    token_pair_key = self._orderbook_token_pair_key(
        condition_id=condition_id, yes_token_id=yes_token_id,
        no_token_id=no_token_id, market_slug=market_slug,
    )
    self._observability._mark_orderbook_refresh(
        ticker,
        source=source,
        trigger=trigger,
        now_mono=now_mono,
        now_utc=now_utc,
        token_pair_key=token_pair_key,
        executable_yes_no_book=executable_yes_no_book,
    )


# --- Method proxy: _orderbook_refresh_observability_detail ---
def _orderbook_refresh_observability_detail(self, ticker: str, **kwargs) -> dict[str, object]:
    return self._observability._orderbook_refresh_observability_detail(self, ticker, **kwargs)
```

```python
# --- Property shims (8 fields) ---
# Safe lazy init: uses get_settings() fallback when self.settings is absent (test __new__ usage).

@property
def _last_orderbook_refresh_at_utc(self) -> dict[str, str]:
    return self._get_observability()._last_orderbook_refresh_at_utc

@_last_orderbook_refresh_at_utc.setter
def _last_orderbook_refresh_at_utc(self, val: dict[str, str]) -> None:
    self._get_observability()._last_orderbook_refresh_at_utc = val

# ... repeat for all 8 fields with identical getter/setter pattern ...
```

### 4.3 Safe lazy helper accessor (`trader.py`)

**Why not `get_settings()`:**  
Using `get_settings()` as a fallback introduces an implicit module-level dependency and a `lru_cache` call inside a property getter path. Tests that use `PolymarketTrader.__new__(PolymarketTrader)` to construct lightweight mock traders do NOT need real settings — the 8 moved fields are plain dicts with `{}` defaults. Calling `get_settings()` would load `.env` files, parse Pydantic validators, and touch file-system state unnecessarily. The safer design is to pass `None` and let the helper guard against it.

**Corrected `TraderObservabilityHelper.__init__` signature** (`trader_observability.py`):

```python
def __init__(self, settings: "Settings | None" = None) -> None:
    self.settings = settings  # may be None; fields below do not require settings
    self._presentation = TraderPresentationHelper()
    self._recent_display_trades: deque[dict[str, Any]] = deque(maxlen=12)
    self._observability_health_display_state: dict[str, Any] = (
        self._presentation.default_observability_health_display_state()
    )
    # --- Batch 3B-1 additions ---
    self._last_orderbook_refresh_at_utc: dict[str, str] = {}
    self._last_orderbook_refresh_monotonic: dict[str, float] = {}
    self._last_orderbook_refresh_source: dict[str, str] = {}
    self._last_orderbook_refresh_trigger: dict[str, str] = {}
    self._last_orderbook_refresh_token_pair_key: dict[str, str] = {}
    self._last_successful_yes_no_book_at_utc: dict[str, str] = {}
    self._last_successful_yes_no_book_monotonic: dict[str, float] = {}
    self._last_successful_yes_no_book_token_pair_key: dict[str, str] = {}
```

Note: None of the 8 moved fields read from `self.settings`. They are pure timing dicts. The `settings=None` default is safe.

**Corrected `_get_observability()` accessor** (`trader.py`):

```python
def _get_observability(self) -> "TraderObservabilityHelper":
    """Return the observability helper, initializing it safely if not yet present.

    Handles PolymarketTrader.__new__(PolymarketTrader) construction in tests,
    where self._observability and self.settings may both be absent.

    Does NOT call get_settings() — the helper's 8 orderbook timing fields are
    plain dicts with {} defaults and require no settings at all. Passing
    settings=None is safe and avoids loading .env or triggering Pydantic
    validators in test contexts.
    """
    if not hasattr(self, "_observability"):
        from polymarket.orchestration.trader_observability import TraderObservabilityHelper
        self._observability = TraderObservabilityHelper(
            settings=getattr(self, "settings", None)
        )
    return self._observability
```

**Why `getattr(self, "settings", None)` without `or get_settings()`:**
- If `self.settings` exists (normal runtime): passed through unchanged.
- If `self.settings` is absent (`__new__` test construction): `None` is passed.
- `TraderObservabilityHelper(settings=None)` initializes all 8 fields to `{}` — this is correct behavior for a fresh mock trader that has no orderbook data yet.
- No `.env` file is read, no Pydantic validator runs, no file-system side effects.

All 8 property shims and 2 method proxies call `self._get_observability()` instead of `self._observability` directly. This eliminates the `AttributeError` from `__new__`-constructed test traders without introducing any new side effects.

---

## 5. Updated Allocation Table (Batch 3B-1 only)

| Item | Batch 3B-1 action | Helper location | Trader proxy/shim |
|------|------------------|-----------------|-------------------|
| `_last_orderbook_refresh_at_utc` | MOVE | `self._last_orderbook_refresh_at_utc` | `@property` shim + setter |
| `_last_orderbook_refresh_monotonic` | MOVE | `self._last_orderbook_refresh_monotonic` | `@property` shim + setter |
| `_last_orderbook_refresh_source` | MOVE | `self._last_orderbook_refresh_source` | `@property` shim + setter |
| `_last_orderbook_refresh_trigger` | MOVE | `self._last_orderbook_refresh_trigger` | `@property` shim + setter |
| `_last_orderbook_refresh_token_pair_key` | MOVE | `self._last_orderbook_refresh_token_pair_key` | `@property` shim + setter |
| `_last_successful_yes_no_book_at_utc` | MOVE | `self._last_successful_yes_no_book_at_utc` | `@property` shim + setter |
| `_last_successful_yes_no_book_monotonic` | MOVE | `self._last_successful_yes_no_book_monotonic` | `@property` shim + setter |
| `_last_successful_yes_no_book_token_pair_key` | MOVE | `self._last_successful_yes_no_book_token_pair_key` | `@property` shim + setter |
| `_mark_orderbook_refresh` | MOVE | `_mark_orderbook_refresh(ticker, *, source, trigger, now_mono, now_utc, token_pair_key, ...)` | Proxy pre-computes `now_mono`, `now_utc`, `token_pair_key` then delegates |
| `_orderbook_refresh_observability_detail` | MOVE | `_orderbook_refresh_observability_detail(trader, ticker, ...)` | Proxy passes `self` as `trader` arg |

---

## 6. Confirmed Forbidden Scope (Batch 3B-1)

The following are **explicitly and permanently forbidden** from Batch 3B-1. This list is confirmed unchanged from the design review and carries forward without exception:

**No lineage extraction:**

```
FORBIDDEN — no lineage:
  _last_quote_lineage_context        — deferred (execution coupling risk; written in execution path)
  _phase4_build_quote_lineage        — PERMANENT (execution path — never move)
  _phase4_quote_lineage_carry        — PERMANENT (execution path — never move)
```

**No cadence/scheduler extraction:**

```
FORBIDDEN — no cadence:
  _last_decision_cycle_monotonic     — deferred to Batch 3B-2
  _market_evaluation_started_monotonic  — deferred to Batch 3B-2
  _market_evaluation_started_at_utc  — deferred to Batch 3B-2
  _current_cycle_market_sequence_index  — deferred to Batch 3B-2
  _current_cycle_market_sequence_count  — deferred to Batch 3B-2
  _scheduler_cadence_observability_detail  — deferred to Batch 3B-2
  _emit_hybrid_v1_snapshot           — deferred to Batch 3B-2
```

**No event identifiers:**

```
FORBIDDEN — no event identifiers:
  _event_producer_label              — deferred to Batch 3B-2
```

**Permanent — never extract:**

```
PERMANENT in trader.py — never move:
  _risk_plan_zero_diagnostics        — RISK_COUPLED (reads bankroll tiers and risk modes)
  _diagnostic_float                  — RUNTIME_COUPLED (used in core math paths)
  _diagnostic_int                    — RUNTIME_COUPLED (used in core math paths)
```

Any implementation that moves a forbidden or deferred item MUST trigger the Hard Stop (Section 10) and be immediately reverted.

---

## 7. Test Compatibility Plan

### 7.1 __new__ mock safety
**Problem:** Tests call `PolymarketTrader.__new__(PolymarketTrader)` and then set mock values directly on the instance (e.g., `trader._last_successful_yes_no_book_at_utc = {...}`).

**Solution:** All 8 property shims call `self._get_observability()`, which initializes `TraderObservabilityHelper(settings=None)` lazily if `self._observability` is absent — no `get_settings()` call, no Pydantic side effects.

**Verification:** The setter `trader._last_successful_yes_no_book_at_utc = {...}` will:
1. Hit the `@property.setter` shim on `PolymarketTrader`
2. Call `self._get_observability()` — initializes `TraderObservabilityHelper(settings=None)` lazily
3. Set `self._observability._last_successful_yes_no_book_at_utc = {...}`
4. Subsequent reads via the getter return the mocked value correctly
5. No `.env` load, no Pydantic validator, no file-system access

### 7.2 Tests that directly access instance dict
Some tests may use `trader.__dict__["_last_successful_yes_no_book_at_utc"]` or `vars(trader)`. These will NOT work with property shims.

**Mitigation:** Grep for `__dict__` and `vars(trader)` access patterns in the test suite before Batch 3B-1 implementation. If any are found, address case-by-case.

### 7.3 Property collision guard
Before adding `@property _last_orderbook_refresh_at_utc` to `PolymarketTrader`, verify there are no existing `@property` definitions with the same name in `trader.py` or any parent class. If a plain attribute exists in `__init__`, it will be shadowed by the property — this is the intended behavior.

---

## 8. Verification Plan

| Step | Command | Expected |
|------|---------|---------|
| 1. Compile | `py_compile polymarket/trader.py polymarket/orchestration/trader_observability.py` | COMPILE_OK |
| 2. Import | `.venv/Scripts/python.exe -c "from polymarket.trader import PolymarketTrader; print('IMPORT_OK')"` | IMPORT_OK |
| 3. Test suite | `.venv/Scripts/python.exe -m pytest tests/ -q` | All pass except known pre-existing failures |
| 4. Orderbook tests | `.venv/Scripts/python.exe -m pytest tests/test_orderbook_*.py tests/test_quote_*.py -v` | All pass |
| 5. Paper boot | `.venv/Scripts/python.exe main.py --mode paper --interval 60` | Boots, DATA_OK after first cycle |
| 6. Paper cycles | At least 3 cycles completing without exception | No `_last_orderbook_refresh` AttributeError in logs |
| 7. JSONL check | Verify `orderbook_refresh_source`, `orderbook_snapshot_age_ms_at_decision` present in events | Fields emitted correctly |

---

## 9. Performance Verification

Property shim indirection adds one Python attribute lookup and one conditional `hasattr` check per access. These must not measurably degrade the paper runtime loop.

| Verification | Method | Pass criterion |
|-------------|--------|----------------|
| Cycle-time regression | Compare paper cycle latency before and after — check `decision_latency_ms` in heartbeat events | No single-cycle latency increase > 20ms vs pre-3B-1 baseline |
| Memory growth | Monitor `event_stream_file_size` across 5+ paper cycles | No unexpected growth rate vs pre-3B-1 baseline |
| Property shim overhead | `timeit` one getter call on `_last_orderbook_refresh_monotonic` | < 5µs per call (dict lookup dominates) |
| Orderbook refresh latency | Check `orderbook_snapshot_age_ms_at_decision` in JSONL events | Values unchanged from pre-3B-1 runs |
| Paper run stability | `python main.py --mode paper --interval 60` for 5+ cycles | Zero AttributeError, zero `_last_orderbook_refresh` key errors in output |
| JSONL field shape | After 3 cycles, read emitted events and confirm all existing keys present | `orderbook_refresh_source`, `orderbook_snapshot_age_ms_at_decision`, `executable_book_last_seen_age_ms` all present |

Required paper run: minimum **5 cycles** post-implementation before claiming Batch 3B-1 validated.

---

## 10. Hard Stop Criteria

Implementation must **stop immediately and revert** if any of the following occur:

**Code scope violations:**
- Any file outside `polymarket/trader.py` and `polymarket/orchestration/trader_observability.py` is modified
- Any file in `polymarket/risk_manager.py`, `utils/`, `config/`, `main.py`, `polymarket/virtual_ptb.py`, `polymarket/order_intent.py` is touched
- Dashboard files (`dashboard/`) or runtime exports (`runtime/research_exports/`) are modified
- A `.md` file is created in repository root (output location policy violation)

**Deferred scope violations:**
- `_last_quote_lineage_context` is moved or accessed via helper
- `_phase4_build_quote_lineage` or `_phase4_quote_lineage_carry` are modified
- `_last_decision_cycle_monotonic` is moved to helper (reads/writes via `trader.*` are allowed)
- `_scheduler_cadence_observability_detail`, `_emit_hybrid_v1_snapshot`, or `_event_producer_label` are touched
- `_risk_plan_zero_diagnostics`, `_diagnostic_float`, or `_diagnostic_int` are modified

**Test failures:**
- Any previously-passing test now fails (outside documented pre-existing failures in `CURRENT_PROJECT_STATUS.md`)
- `py_compile` fails on any modified file
- `from polymarket.trader import PolymarketTrader` fails

**Runtime violations:**
- `_last_orderbook_age_ms` or `_orderbook_warmup_pending_counts` fields change shape or value
- Any `orderbook_refresh_*` JSONL key disappears or changes type
- Paper runtime raises an `AttributeError` referencing any of the 8 moved fields
- A second `TraderObservabilityHelper` instance is created per trader (memory leak)

**Revert command:** `git restore polymarket/trader.py polymarket/orchestration/trader_observability.py`

---

## 11. Rollback Plan

1. `git restore polymarket/trader.py polymarket/orchestration/trader_observability.py`
2. Restores HEAD to current clean state (`bd97d4c` as of 2026-06-27)
3. Zero blast radius — no other files touched by Batch 3B-1

---

## 12. Change Count Estimate

| File | Expected changes |
|------|----------------|
| `polymarket/orchestration/trader_observability.py` | +~80 lines (8 field inits + 2 new methods) |
| `polymarket/trader.py` | +~60 lines (8 `@property` shims, 2 proxies, `_get_observability` helper) — net negative after field/method removal |
| Net reduction in `trader.py` | Approx −50 lines (8 field init lines + 2 method bodies removed, replaced with shorter shims/proxies) |

---

## Final Verdict

```
READY_FOR_BATCH_3B1_IMPLEMENTATION
```

**Summary of corrections applied (including patch v2):**

1. **Scope reduced** to 8 fields + 2 methods (orderbook refresh timing only) — cadence, lineage, event identifiers all deferred to Batch 3B-2
2. **Lazy init corrected (patch v2)** — `_get_observability()` uses `TraderObservabilityHelper(settings=getattr(self, "settings", None))` — no `get_settings()` import, no `.env` load, no Pydantic side effects; helper accepts `settings=None` as safe default because the 8 fields are plain `{}` dicts requiring no settings
3. **`_mark_orderbook_refresh` coupling resolved** — proxy pre-computes `now_mono`, `now_utc`, `token_pair_key` before delegating; helper signature is pure, no trader method calls inside it
4. **`_orderbook_refresh_observability_detail` coupling resolved** — takes `trader: Any` as first arg; reads deferred fields via `getattr(trader, ...)`
5. **Ownership diagram updated** — clean 3B-1 boundary with deferred items explicitly retained on trader
6. **Forbidden scope confirmed (patch v2)** — three explicit sub-groups: no lineage, no cadence, no event identifiers; permanent items listed separately
7. **Test compatibility plan updated** — addresses `__new__` mocks, `__dict__` access, and property collision guard; references corrected (no `get_settings()` in test flow)
8. **Performance verification added (patch v2)** — Section 9: cycle-time regression, memory, shim overhead, JSONL field shape; 5-cycle paper run required
9. **Hard stop criteria added (patch v2)** — Section 10: code scope violations, deferred scope violations, test failures, runtime violations; revert command stated
