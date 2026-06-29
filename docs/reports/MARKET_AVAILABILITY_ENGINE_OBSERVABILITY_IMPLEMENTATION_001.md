# MARKET_AVAILABILITY_ENGINE_OBSERVABILITY_IMPLEMENTATION_001

**Date:** 2026-06-28  
**Task Class:** 5 OBSERVABILITY  
**Status:** COMPLETE

---

## FINAL_VERDICT

**PASS** — 74 tests pass. Market availability guard implemented and wired. bankroll_rank/capital_score schema corrected. All changes observability/scheduler-only.

---

## FILES_CHANGED

| File | Change |
|---|---|
| `polymarket/market_availability_engine.py` | **NEW** — `MarketAvailabilityEngine`, `MarketAvailabilityResult`, `MarketAvailabilityState` (5 states) |
| `polymarket/trader.py` | Wire MAE into `run_single_cycle`; add import + instance; fix bankroll_rank→string, add `_last_capital_score`; fix trade_open/close emit |
| `config/settings.py` | 6 new availability guard settings |
| `utils/quant_event_logger.py` | Add `log_market_availability_check()` to research_log |
| `tools/canonical_trade_context_builder.py` | `bankroll_rank` → `extract_field()` (string, not `_to_float`) |
| `tests/test_market_availability_engine.py` | **NEW** — 38 tests |

---

## TESTS_RUN

**74 passed in 9.28s**

| Test file | Count |
|---|---|
| `test_market_availability_engine.py` | 38 new |
| `test_telemetry_backfill.py` | 16 |
| `test_canonical_trade_context_builder.py` | 20 |

New test coverage:
- All 5 scheduler states (ACTIVE, BETWEEN_EPOCHS, MARKET_NOT_SCHEDULED, API_UNAVAILABLE, UNKNOWN)
- Exponential backoff up to max cap
- Cache hit / miss / invalidation
- Slug pattern matching (btc, eth, case-insensitive, non-5m rejection)
- Symbol extraction from slugs
- Telemetry method exists + writes to research_log
- Trader skips scan when MARKET_NOT_SCHEDULED
- Trader proceeds when guard disabled
- `bankroll_rank` is string, `capital_score` is float
- Canonical builder preserves bankroll_rank as string
- Legacy rows compile without error

---

## SCHEDULER_STATES

| State | Sleep | Trigger |
|---|---|---|
| `ACTIVE` | 0 (scan immediately) | ≥1 matching market with bestBid>0, bestAsk>0, acceptingOrders=True |
| `BETWEEN_EPOCHS` | **15s** | Matching markets exist but orderbook empty |
| `MARKET_NOT_SCHEDULED` | **300s** | Zero btc/eth-updown-5m-* markets on Gamma API |
| `API_UNAVAILABLE` | **60s × 2^n** (max 600s) | Request fails / non-200 |
| `UNKNOWN` | **30s** | Malformed schema / parse error |

### Pre-scan hook location
`run_single_cycle()` at line ~13299, after cycle preamble (bankroll update, reconciliation), before `_select_markets()`. Returns `[]` immediately on any non-ACTIVE state.

### Configuration
```python
enable_market_availability_guard: bool = True       # disable with False
market_availability_cache_ttl_sec: int = 30
market_between_epochs_sleep_sec: int = 15
market_not_scheduled_sleep_sec: int = 300
market_api_unavailable_base_sleep_sec: int = 60
market_api_unavailable_max_sleep_sec: int = 600
```

---

## TELEMETRY_ADDED

| Event | Stream | Payload |
|---|---|---|
| `market_availability_check` | `research_log` | state, active_market_count, btc_market_count, eth_market_count, symbols_available, matching_slugs, next_check_seconds, cache_hit, api_latency_ms, error, schema_version |

Emitted on every non-cached availability check (every 30s by default).

---

## SCHEMA_FIX

### Problem
Commit `5458885` silently stored `capital_score` (float) in `_last_bankroll_rank`, changing its semantic meaning.

### Fix applied (all 3 locations)

**`__init__`:**
```python
self._last_bankroll_rank: str | None = None    # tier-string
self._last_capital_score: float | None = None  # numeric score
```

**`_update_bankroll_state` persistence:**
```python
self._last_bankroll_rank = evaluation.get("bankroll_rank")   # "T0_MICRO_SEED"
self._last_capital_score = evaluation.get("capital_score")   # 0.75
```

**`_emit_trade_opened_event` payload:**
```python
"bankroll_rank": self._last_bankroll_rank,   # string
"bankroll_family": self._last_bankroll_family,
"capital_score": self._last_capital_score,   # float
```

**`_emit_trade_closed_event` carry:**
```python
"bankroll_rank": metadata.get("bankroll_rank"),   # string carried from open
"capital_score": metadata.get("capital_score"),   # float carried from open
```

**Canonical builder:**
```python
"bankroll_rank": extract_field(events, "bankroll_rank"),  # string, NOT _to_float
"capital_score": _to_float(extract_field(events, "capital_score")),  # unchanged
```

### Schema table (canonical)

| Field | Type | Example | Source |
|---|---|---|---|
| `bankroll_rank` | string | `"T0_MICRO_SEED"` | `evaluate()["bankroll_rank"]` |
| `bankroll_family` | string | `"MICRO"` | `evaluate()["bankroll_family"]` |
| `capital_score` | float | `0.75` | `evaluate()["capital_score"]` |
| `bankroll_tier_id` | string | `"T0_MICRO_SEED"` | decision_log (99.9% coverage) |

---

## OBSERVABILITY_ONLY_VERDICT

**CONFIRMED**

- `MarketAvailabilityEngine` is read-only: queries Gamma API, never writes to state
- Guard in `run_single_cycle` returns `[]` early — identical to the existing `if not markets: return []` path
- `enable_market_availability_guard: bool = True` can be set to `False` to disable entirely
- `_last_bankroll_rank` and `_last_capital_score` are read ONLY in emit helpers — never by risk_plan, sizing, order_intent, or execution
- No strategy, sizing, risk, EV, or execution logic changed
- Source guard verified: existing test `test_source_guard_execution_paths_do_not_read_bankroll_rank` still passes

---

## RESOURCE_SAVINGS_EXPECTED

| Scenario | Before | After |
|---|---|---|
| 54-min dead window (2026-06-28) | 108+ scan cycles, continuous CLOB API calls | 11 Gamma checks × 300s sleep |
| Between-epoch 30s gap | 3–4 full scan cycles | 2 checks × 15s |
| API failure storm | Continuous retry | Backoff to 10-min cap |

**~91% reduction in API calls during dead market windows.**

---

## NEXT_TASK

**BACKTEST_ENGINE_V2_POLICY_GRID_EXPANSION_001**

The implementation track is now stable:
- Telemetry backfill complete and type-correct
- Market availability guard prevents idle loops
- Bankroll rank schema is correct (string tier, float score)

Ready to proceed with policy grid expansion on the 886-row signal-driven dataset.

---

## ADDENDUM — OBSERVABILITY MODULE (2026-06-29)

**Scope:** Added `polymarket/observability/market_availability.py` — a pure, trader-free
observability layer that describes WHY a market is or is not tradable. Companion to the
existing runtime engine (not a replacement). No changes to trader.py, config, or any
execution path.

### Module: `polymarket/observability/market_availability.py`

**Schema version:** `market_availability_obs_v1` (distinct from engine's `market_availability_v1`)

**6 TypedDicts (all `total=False`):**

| TypedDict | Purpose |
|---|---|
| `AvailabilityReason` | Per-market reason with code, detail, severity |
| `AvailabilityScore` | Dimensional scores: bid_ask, liquidity, latency, penalty, final |
| `AvailabilitySnapshot` | Single-market evaluation (20 fields) |
| `AvailabilitySummary` | Aggregate across multiple snapshots (15 fields) |
| `AvailabilityHealth` | Health verdict + grade + embedded AvailabilityScore |
| `AvailabilityDiagnostics` | Debug diagnostics sub-field |

**9 reason codes (all reachable via `evaluate_market_availability`):**
CLIENT_ERROR → TOKEN_NOT_FOUND → MARKET_CLOSED → STALE_FEED →
ORDERBOOK_NOT_READY → EMPTY_ORDERBOOK → UNKNOWN (crossed book) →
LOW_LIQUIDITY → HIGH_SPREAD

**4 builder functions:**
- `evaluate_market_availability()` — per-market snapshot with precedence logic
- `summarize_market_availability()` — aggregate across snapshots
- `build_availability_health()` — health verdict + AvailabilityScore embedding
- `build_market_availability_payload()` — full observability payload (15 top-level keys)

**62 new tests** (`tests/observability/test_market_availability.py`):
- Precedence table: all 9 codes + ACTIVE (parametrized, 17 cases)
- Golden snapshots: exact match for evaluate_market_availability (20 keys) and build_market_availability_payload (15 keys, health nested)
- JSON serializability: all builders
- Health verdicts: HEALTHY / DEGRADED / UNAVAILABLE per state

**Acceptance:** 953 tests pass (891 prior + 62 new).

**Safety:** Observability-only. stdlib-only leaf. No trader.py, no QuantEventLogger, no config, no risk/sizing/execution.
