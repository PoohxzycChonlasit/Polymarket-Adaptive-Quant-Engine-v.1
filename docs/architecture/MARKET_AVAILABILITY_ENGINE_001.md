# MARKET_AVAILABILITY_ENGINE_001

**Version:** 1.0  
**Date:** 2026-06-28  
**Status:** DESIGN

---

## 1. Problem Statement

The Polymarket 5-minute BTC/ETH binary markets (`btc-updown-5m-*`, `eth-updown-5m-*`) are **scheduled epoch-based markets**, not continuous. They exist on the Gamma API only when a specific oracle price-feed epoch is scheduled. Between epochs, or when no epochs are scheduled (as observed on 2026-06-28 05-06 UTC), the Gamma API returns zero matching markets and the CLOB orderbooks are truly empty.

Current behaviour: the runtime runs a full scan cycle every `interval` seconds, finds TRUE EMPTY orderbooks, logs a no-op, and sleeps. Over 54 minutes were spent in this idle loop before the operator noticed.

**Goal:** detect market availability before starting a scan cycle and adapt sleep/retry behaviour accordingly.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  PolymarketTrader main loop                         │
│                                                     │
│  ┌─────────────────────────────┐                   │
│  │  MarketAvailabilityEngine   │                   │
│  │                             │                   │
│  │  check() → AvailabilityState│                   │
│  │                             │                   │
│  │  ACTIVE              → scan │                   │
│  │  BETWEEN_EPOCHS      → 15s  │                   │
│  │  MARKET_NOT_SCHEDULED→ 300s │                   │
│  │  API_UNAVAILABLE     → 60s  │                   │
│  │  UNKNOWN             → 30s  │                   │
│  └──────────┬──────────────────┘                   │
│             │ emit telemetry                        │
│             ▼                                       │
│  log_market_availability_check()                    │
└─────────────────────────────────────────────────────┘
```

---

## 3. Market Availability States

### 3.1 State Definitions

| State | Condition | Next check | Action |
|---|---|---|---|
| `ACTIVE` | ≥1 `btc-updown-5m-*` OR `eth-updown-5m-*` market exists with `active=True`, `acceptingOrders=True`, `bestBid>0`, `bestAsk>0` | 60s (normal interval) | Run full scan cycle |
| `BETWEEN_EPOCHS` | ≥1 matching market exists on Gamma but `bestBid=0` AND `bestAsk=0` (empty book, market scheduled but not yet populated) | 15s | Short sleep, retry |
| `MARKET_NOT_SCHEDULED` | Zero `btc-updown-5m-*` / `eth-updown-5m-*` markets exist on Gamma API | 300s | Long sleep, emit alert |
| `API_UNAVAILABLE` | Gamma API request fails or returns non-200 | 60s (backoff) | Fail-soft retry |
| `UNKNOWN` | Unexpected response schema or parse error | 30s | Log and retry |

### 3.2 State Transition Diagram

```
           startup
               │
               ▼
          ┌─────────────────┐
          │  API check       │
          └─────────────────┘
               │
    ┌──────────┼──────────────────┐
    │          │                  │
    ▼          ▼                  ▼
API_ERROR  ZERO_MARKETS     MARKETS_FOUND
    │          │                  │
    │      MARKET_NOT_       book check
    │      SCHEDULED         bid/ask > 0?
    │          │             ┌────┴────┐
    │          │             │         │
    │          │           YES        NO
    │          │             │         │
    │          │          ACTIVE  BETWEEN_EPOCHS
    │          │             │         │
    └──────────┴─────────────┴─────────┘
               │         (retry)
          sleep(delay)
               │
          next check
```

---

## 4. Market Detection Logic

### 4.1 Slug Pattern Matching

```
SLUG_PATTERNS = [
    "btc-updown-5m-",
    "eth-updown-5m-",
    "btcusd-5m-",
    "ethusd-5m-",
]

def is_5m_binary(market: dict) -> bool:
    slug = market.get("slug", "").lower()
    return any(pattern in slug for pattern in SLUG_PATTERNS)
```

### 4.2 Availability Check Algorithm

```python
def check(self) -> AvailabilityResult:
    try:
        markets = self._fetch_markets()           # Gamma API call
    except Exception as exc:
        return AvailabilityResult(
            state=State.API_UNAVAILABLE,
            error=str(exc),
            active_count=0,
            next_check_seconds=self.api_failure_cooldown,
        )

    candidates = [m for m in markets if is_5m_binary(m)]

    if not candidates:
        return AvailabilityResult(
            state=State.MARKET_NOT_SCHEDULED,
            active_count=0,
            next_check_seconds=self.not_scheduled_sleep_seconds,
        )

    # At least one candidate exists — check if accepting orders
    tradable = [
        m for m in candidates
        if m.get("active") and m.get("acceptingOrders")
        and float(m.get("bestBid") or 0) > 0
        and float(m.get("bestAsk") or 0) > 0
    ]

    if tradable:
        return AvailabilityResult(
            state=State.ACTIVE,
            active_count=len(tradable),
            symbols=[self._symbol(m) for m in tradable],
            next_check_seconds=self.active_recheck_seconds,
        )

    return AvailabilityResult(
        state=State.BETWEEN_EPOCHS,
        active_count=0,
        next_check_seconds=self.between_epochs_sleep_seconds,
    )
```

### 4.3 Gamma API Endpoint

```
GET https://gamma-api.polymarket.com/markets
  ?limit=50
  &closed=false
  &active=true
```

Key fields consumed:
- `slug` — pattern match for 5m binary
- `active` — boolean
- `acceptingOrders` — boolean
- `bestBid`, `bestAsk` — float (0 = no book)
- `conditionId` — used for token lookup
- `endDate` — used to predict next epoch start

---

## 5. Scheduler Behaviour

### 5.1 Main Loop Integration

```
BEFORE each scan cycle:
  result = market_availability_engine.check()
  emit_telemetry(result)

  if result.state == ACTIVE:
      proceed to normal scan
  elif result.state == BETWEEN_EPOCHS:
      sleep(15)
      continue           # short retry
  elif result.state == MARKET_NOT_SCHEDULED:
      sleep(300)
      continue           # long sleep, ~5 min
  elif result.state == API_UNAVAILABLE:
      sleep(60 * backoff_multiplier)
      continue
  elif result.state == UNKNOWN:
      sleep(30)
      continue
```

### 5.2 Sleep Durations (configurable)

| State | Default sleep | Rationale |
|---|---|---|
| `BETWEEN_EPOCHS` | 15s | Book populates within ~30s of epoch start |
| `MARKET_NOT_SCHEDULED` | 300s (5 min) | Markets may appear on next oracle cycle |
| `API_UNAVAILABLE` | 60s × backoff | Exponential backoff up to 600s max |
| `UNKNOWN` | 30s | Conservative retry |

### 5.3 Cooldown and Cache

The engine caches the last check result for `cache_ttl_seconds` (default: 30s). This prevents hammering the Gamma API when the scan interval is shorter than the cache window.

```
if (now - last_check_ts) < cache_ttl_seconds:
    return cached_result
```

---

## 6. Telemetry Schema

### 6.1 Event: `market_availability_check`

Emitted to `research_log` after each availability check (not every scan cycle — only when state changes or cache expires).

```json
{
  "event_type": "market_availability_check",
  "timestamp_utc": "2026-06-28T05:31:09Z",
  "run_id": "...",
  "payload": {
    "state": "MARKET_NOT_SCHEDULED",
    "active_market_count": 0,
    "candidate_market_count": 0,
    "symbols_available": [],
    "next_check_seconds": 300,
    "gamma_api_latency_ms": 142,
    "cache_hit": false,
    "error": null,
    "schema_version": "market_availability_v1"
  }
}
```

### 6.2 Event: `market_schedule_alert`

Emitted (once, deduplicated) when `MARKET_NOT_SCHEDULED` is first detected.

```json
{
  "event_type": "market_schedule_alert",
  "payload": {
    "state": "MARKET_NOT_SCHEDULED",
    "message": "No active btc-updown-5m-* / eth-updown-5m-* markets found on Gamma API",
    "last_known_epoch_slug": "btc-updown-5m-1782565800",
    "last_known_epoch_ts": 1782565800
  }
}
```

### 6.3 Key Telemetry Fields

| Field | Type | Description |
|---|---|---|
| `state` | string enum | Availability state |
| `active_market_count` | int | Markets with active bids/asks |
| `candidate_market_count` | int | Markets matching slug pattern (any state) |
| `symbols_available` | list[str] | `["BTC", "ETH"]` if active |
| `next_check_seconds` | int | When to re-check availability |
| `gamma_api_latency_ms` | int | API response time |
| `cache_hit` | bool | Whether result came from cache |
| `error` | string or null | Error message if API_UNAVAILABLE |

---

## 7. Resource Governance Integration

### 7.1 Impact on Machine Resources

| Scenario | Before (current) | After (with engine) |
|---|---|---|
| No markets (54 min) | 54 min × ~60s scans = 54 full cycles | ~11 checks × 300s sleep |
| Between epochs (30s gap) | 30s of full cycles | 2 checks × 15s sleep |
| Active market | Same as before | Same as before |
| API unavailable | Repeated attempts | Backoff to max 10min |

### 7.2 Bounded Paper Session Protocol

When the operator runs a validation session:
1. Pre-check availability before starting paper loop
2. If `MARKET_NOT_SCHEDULED`, immediately report and exit with status code
3. If `BETWEEN_EPOCHS`, wait once (up to 60s) then start session
4. If `ACTIVE`, start immediately

This prevents the operator from accidentally running a 90-minute empty session.

---

## 8. Bankroll Rank / Capital Score Schema Clarification

This section addresses the schema confusion discovered in `CANONICAL_TRADE_OPEN_RUNTIME_VALIDATION_002`.

### 8.1 Field Definitions

| Field name | Type | Source | Meaning |
|---|---|---|---|
| `bankroll_rank` | **string** | `bankroll_rank_engine.evaluate()["bankroll_rank"]` | Tier identifier (e.g. `"T0_MICRO_SEED"`, `"T6_GROWTH_1"`) — the categorical tier assignment |
| `bankroll_family` | string | `evaluate()["bankroll_family"]` | Family label (e.g. `"MICRO"`, `"STANDARD"`, `"GROWTH"`) |
| `capital_score` | **float** | `evaluate()["capital_score"]` | Smoothed quality score 0.0–1.0 (continuous numeric rank) |
| `bankroll_rank_score` | float (optional) | Alias for `capital_score` | Numeric alias for `bankroll_rank` if a float rank is needed in the canonical context |

### 8.2 Design Rule

> **`bankroll_rank` must NOT silently become `capital_score`.**

The field name `bankroll_rank` in the canonical context must retain its tier-string meaning. It is the same as `bankroll_tier_id` but sourced from the trade_open payload rather than the decision_log.

If the canonical builder or policy engine needs a numeric rank, it must use `capital_score` (already defined) or `bankroll_rank_score` (a new optional alias). Do not coerce the tier-string into a float.

### 8.3 Canonical Builder Implication

The canonical builder's line:
```python
"bankroll_rank": _to_float(extract_field(events, "bankroll_rank")),
```
is incorrect for the tier-string meaning. It should be:
```python
"bankroll_rank": extract_field(events, "bankroll_rank"),  # keep as string
"capital_score": _to_float(extract_field(events, "capital_score")),
```

### 8.4 Revert Required

The change in commit `5458885` (`self._last_bankroll_rank = evaluation.get("capital_score")`) silently redirected `bankroll_rank` to mean `capital_score`. This must be reverted in the implementation task, and `_last_bankroll_rank` restored to store the tier-string `evaluation.get("bankroll_rank")`.

A new `_last_capital_score: float | None = None` attribute should be added for the numeric score carry-forward.

---

## 9. Implementation Task Scope

`MARKET_AVAILABILITY_ENGINE_OBSERVABILITY_IMPLEMENTATION_001` must:

1. Add `polymarket/market_availability_engine.py` — pure function, no runtime side effects
2. Add `log_market_availability_check()` to `QuantEventLogger`
3. Wire availability check into `PolymarketTrader` main loop header (before scan)
4. Add `market_availability_not_scheduled_sleep_seconds` and `market_availability_between_epochs_sleep_seconds` to `config/settings.py`
5. Revert `_last_bankroll_rank` to store tier-string (`evaluation["bankroll_rank"]`)
6. Add `_last_capital_score` to store float (`evaluation["capital_score"]`)
7. Emit `capital_score` separately in trade_open payload alongside `bankroll_rank`
8. Fix canonical builder: treat `bankroll_rank` as string, add `capital_score` as float

All changes: observability-only. No strategy/risk/sizing changes.

---

## 10. Configuration Schema (proposed)

```python
# config/settings.py additions
market_availability_check_enabled: bool = True
market_availability_cache_ttl_seconds: int = 30
market_availability_between_epochs_sleep_seconds: int = 15
market_availability_not_scheduled_sleep_seconds: int = 300
market_availability_api_failure_cooldown_seconds: int = 60
market_availability_api_failure_max_backoff_seconds: int = 600
market_availability_slug_patterns: list[str] = [
    "btc-updown-5m-",
    "eth-updown-5m-",
]
```

---

## 11. Testing Requirements

| Test | Scope |
|---|---|
| `test_state_active` | API returns market with bid/ask > 0 → ACTIVE |
| `test_state_between_epochs` | Market exists but bid=0 ask=0 → BETWEEN_EPOCHS |
| `test_state_not_scheduled` | Zero matching slugs → MARKET_NOT_SCHEDULED |
| `test_state_api_unavailable` | Request throws → API_UNAVAILABLE |
| `test_cache_hit` | Second call within TTL → returns cached result |
| `test_telemetry_emitted` | `market_availability_check` event written |
| `test_slug_pattern_matching` | Various slugs → correct is_5m_binary classification |
| `test_sleep_durations` | State → correct next_check_seconds |
