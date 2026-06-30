# MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001

**Task class:** 6 SAFE RUNTIME REPAIR / MARKET DATA AVAILABILITY
**Date:** 2026-06-30
**Final verdict:** REPAIR_COMPLETE

## Scope

Repaired the Market Availability Engine false negative where broad Gamma
`/markets?limit=50` could miss active BTC/ETH 5-minute exact-slug markets and return
`MARKET_NOT_SCHEDULED`.

No strategy thresholds, execution behavior, live execution, order submission, risk logic,
sizing logic, wallet/balance behavior, `.env`, or `config/settings.py` were modified.

## Fix Applied

`polymarket/market_availability_engine.py` now preserves the existing broad scan first.
Only when that path returns `MARKET_NOT_SCHEDULED`, the engine performs a bounded exact
fallback against four deterministic Gamma event slugs:

- `btc-updown-5m-{current_epoch}`
- `btc-updown-5m-{next_epoch}`
- `eth-updown-5m-{current_epoch}`
- `eth-updown-5m-{next_epoch}`

The fallback uses read-only Gamma `/events?slug=...` calls, extracts event markets, and
passes those markets through the existing classifier. If exact lookup also finds no
candidate markets, the engine still returns `MARKET_NOT_SCHEDULED`.

## Fallback Diagnostics

`MarketAvailabilityResult` and telemetry payloads now include:

| Field | Meaning |
|---|---|
| `fallback_used` | Whether exact-slug fallback was used |
| `exact_slug_checked` | Exact slugs queried by fallback |
| `exact_slug_match_count` | Candidate markets found by exact fallback |
| `availability_source` | `broad_markets` or `exact_slug_fallback` |

Existing broad scan ACTIVE behavior remains unchanged and does not call the fallback.

## Tests

| Command | Result |
|---|---:|
| focused red tests before implementation | 4 failed as expected |
| `.\.venv\Scripts\python.exe -m pytest tests\polymarket\test_market_availability_engine.py -q --tb=short -ra` | 42 passed, 5 warnings |
| `.\.venv\Scripts\python.exe -m py_compile polymarket\market_availability_engine.py polymarket\gamma_fetcher.py` | PASS |
| `.\.venv\Scripts\python.exe -m pytest tests\polymarket tests\observability -q --tb=short -ra` | 957 passed, 5 warnings |

## Direct Diagnostic

Read-only direct MAE check:

```text
state=ACTIVE
availability_source=exact_slug_fallback
fallback_used=true
active_market_count=4
btc_market_count=2
eth_market_count=2
exact_slug_match_count=4
matching_slugs=[
  btc-updown-5m-1782792000,
  btc-updown-5m-1782792300,
  eth-updown-5m-1782792000,
  eth-updown-5m-1782792300
]
```

## Paper Smoke

Command:

```powershell
.\.venv\Scripts\python.exe main.py --mode paper --interval 60
```

Bounded wrapper:

- 90 seconds
- UTF-8 environment
- `CTRL_BREAK_EVENT` shutdown
- return code `0`
- stopped cleanly after 2 cycles

Run id:

```text
20260630T040247Z_44448_80399ee5
```

Run-id scoped evidence:

| Evidence | Result |
|---|---:|
| `market_availability_check` rows | 2 |
| `state=ACTIVE` | 2/2 |
| `fallback_used=true` | 2/2 |
| `availability_source=exact_slug_fallback` | 2/2 |
| cycle selection probes | 2 |
| selected BTC/ETH markets | 2/2 |
| `early_return_reason` | null in both probes |
| `selection_empty_reason` | null in both probes |
| live/order/fill/exit markers scoped to run id | 0 |

## Safety Verdict

SAFE_RUNTIME_REPAIR.

The repair changes only the market availability/data-selection guard. It does not change
strategy thresholds, risk, sizing, wallet behavior, live execution, order submission, or
configuration. Paper runtime remained paper-only with zero live/order/fill/exit markers in
the scoped validation run.

## Remaining Risks

- Exact fallback adds up to four Gamma event reads only when the broad scan sees no BTC/ETH
  5-minute candidates. This is intentionally bounded but still adds latency during broad
  false-negative windows.
- Current paper smoke reached market selection and fresh orderbook paths, but no paper
  trade/fill path was reached because runtime policy/risk gates blocked entries.
- The seeded runtime knowledge graph did not include `MarketAvailabilityEngine`; the Class 6
  graph query used source fallback evidence.

## Next Task

`MARKET_AVAILABILITY_ENGINE_POST_REPAIR_PAPER_VALIDATION_001`

Run a longer bounded paper validation window during active BTC/ETH 5-minute markets to
confirm the repaired guard continues to select current markets across at least one epoch
rollover and does not regress to stale-token orderbook paths.
