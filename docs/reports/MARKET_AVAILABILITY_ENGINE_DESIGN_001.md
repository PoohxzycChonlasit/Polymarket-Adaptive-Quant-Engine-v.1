# MARKET_AVAILABILITY_ENGINE_DESIGN_001

**Date:** 2026-06-28  
**Task Class:** 2 DESIGN  
**Status:** COMPLETE

---

## FINAL_VERDICT

**DESIGN COMPLETE**

Architecture approved for implementation. Five scheduler states defined, Gamma API detection strategy validated, resource savings quantified, bankroll_rank/capital_score schema conflict resolved with explicit design rule.

---

## ARCHITECTURE_SUMMARY

The Market Availability Engine is a lightweight pre-scan guard injected into the PolymarketTrader main loop. Before each scan cycle, it:

1. Queries the Gamma API for `btc-updown-5m-*` / `eth-updown-5m-*` markets (cached for 30s)
2. Classifies availability into one of 5 states
3. Emits a `market_availability_check` telemetry event
4. Returns the appropriate sleep duration or `ACTIVE` signal

**Full spec:** [`docs/architecture/MARKET_AVAILABILITY_ENGINE_001.md`](../architecture/MARKET_AVAILABILITY_ENGINE_001.md)

### Key design choices

| Decision | Rationale |
|---|---|
| Gamma API (not CLOB) for availability | Gamma returns market metadata including slug, `active`, `acceptingOrders`, `bestBid/Ask` — single call covers all markets |
| Slug pattern matching | `btc-updown-5m-` prefix is stable; conditionId changes each epoch |
| 300s sleep for MARKET_NOT_SCHEDULED | ~5min aligns with 5-min epoch cadence; avoids hammering API during dead windows |
| 15s sleep for BETWEEN_EPOCHS | Order books typically populate within 15-30s of epoch start |
| 30s cache TTL | Prevents API spam on short intervals (e.g. `--interval 30`) |
| Observability-only | Engine reads only, never modifies strategy/sizing/risk state |

---

## SCHEDULER_STATES

| State | Detection | Sleep | Main loop action |
|---|---|---|---|
| `ACTIVE` | ≥1 matching market with `bestBid>0`, `bestAsk>0`, `acceptingOrders=True` | n/a (scan immediately) | Run full scan cycle |
| `BETWEEN_EPOCHS` | ≥1 matching market exists but orderbook is empty (bid=0, ask=0) | **15s** | Skip scan, short retry |
| `MARKET_NOT_SCHEDULED` | Zero `btc-updown-5m-*` / `eth-updown-5m-*` markets on Gamma API | **300s** | Skip scan, long sleep, emit alert |
| `API_UNAVAILABLE` | Gamma API request fails / non-200 | **60s × backoff** (max 600s) | Skip scan, exponential backoff |
| `UNKNOWN` | Unexpected response schema | **30s** | Skip scan, log, retry |

### Observed market gap (2026-06-28 05–06 UTC)

- Session 1 (05:02 UTC): TRUE EMPTY throughout 90s
- Session 2 (05:19 UTC): TRUE EMPTY throughout 54 min
- Gamma API confirmed: 0 `updown-5m-*` markets at 05:21 UTC

With this engine, both sessions would have immediately detected `MARKET_NOT_SCHEDULED` and slept 300s instead of running 54+ cycles.

**Estimated resource saving for the 54-minute gap:**
- Before: ~108 scan cycles × ~5s each = 9 minutes of CPU, continuous API polling
- After: ~11 availability checks × 1 API call each = 11 API calls, zero scan cycles

---

## SCHEMA_DECISION

### Problem

`bankroll_rank_engine.evaluate()["bankroll_rank"]` returns a tier-string (e.g. `"T0_MICRO_SEED"`, `"T6_GROWTH_1"`), not a float. In commit `5458885`, `_last_bankroll_rank` was changed to store `evaluation.get("capital_score")` (float) to make the canonical builder work. This silently changed the semantic meaning of `bankroll_rank`.

### Decision: restore correct semantics

| Field | Type | Semantic | Source |
|---|---|---|---|
| `bankroll_rank` | **string** | Categorical tier assignment | `evaluate()["bankroll_rank"]` e.g. `"T0_MICRO_SEED"` |
| `bankroll_family` | string | Family label | `evaluate()["bankroll_family"]` e.g. `"MICRO"` |
| `capital_score` | **float** | Numeric quality score (0.0–1.0) | `evaluate()["capital_score"]` |

**Rule:** `bankroll_rank` must NOT silently become `capital_score`.

### Required fix (implementation task scope)

1. **Revert** `_last_bankroll_rank = evaluation.get("capital_score")` → restore `evaluation.get("bankroll_rank")` (tier-string)
2. **Add** `_last_capital_score: float | None = None` to store the numeric score
3. **Emit** both fields separately in trade_open payload:
   - `"bankroll_rank": self._last_bankroll_rank` → tier string
   - `"capital_score": self._last_capital_score` → float
4. **Fix canonical builder** extraction:
   - `bankroll_rank` → string field (no `_to_float`)
   - `capital_score` → float field (use `_to_float`)

### Why `bankroll_rank_score` is not needed

`capital_score` already serves as the numeric rank. Adding a `bankroll_rank_score` alias would duplicate it. Use `capital_score` where a float rank is needed.

---

## RESOURCE_SAVINGS_EXPECTED

### Direct savings

| Scenario | Before | After |
|---|---|---|
| 54 min with no markets | 108+ scan cycles | 11 API checks × 300s sleep |
| 30s between-epoch gap | 3–4 full cycles with TRUE EMPTY | 2 checks × 15s sleep |
| API failure storm | Continuous retry | Backoff to 10min cap |

### Operator time saved

- No more "session ran for 90 minutes producing nothing" surprises
- Pre-check exits immediately with clear `MARKET_NOT_SCHEDULED` status
- Reduces need for operator to monitor running sessions

### API rate saved

A 54-minute session with 30s intervals = 108 Gamma API calls + 108 CLOB orderbook fetches.  
With the engine: 11 Gamma API checks × 1 call each = 11 calls total.

**~91% reduction in API calls during dead market windows.**

---

## NEXT_TASK

**MARKET_AVAILABILITY_ENGINE_OBSERVABILITY_IMPLEMENTATION_001**

Implementation scope:
1. `polymarket/market_availability_engine.py` — `MarketAvailabilityEngine` class
2. `utils/quant_event_logger.py` — add `log_market_availability_check()`
3. `polymarket/trader.py` — wire engine into main loop header
4. `config/settings.py` — add 6 new availability config fields
5. **Revert** `_last_bankroll_rank` to tier-string; **add** `_last_capital_score` float
6. **Fix** canonical builder `bankroll_rank` → string, `capital_score` → float
7. Tests: 8 new tests for availability states, cache, telemetry, slug matching

All observability-only. No strategy/risk/sizing changes.
