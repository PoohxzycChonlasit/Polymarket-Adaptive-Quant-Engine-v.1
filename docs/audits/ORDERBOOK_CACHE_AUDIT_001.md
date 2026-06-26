# ORDERBOOK_CACHE_AUDIT_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

This document audits the orderbook and market caching layers of the Polymarket Crypto 5M Quant Engine, analyzing memory storage, invalidation, TTL, and preloading behaviors.

---

## 1. Caching Layer Architecture

The data pipeline utilizes two main levels of caching to prevent redundant API queries and minimize latency:

### Level 1: Market Scanner Cache (Gamma Fetcher)
* **Target File**: [polymarket/gamma_fetcher.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/gamma_fetcher.py)
* **Target Variable**: `self._five_min_market_cache`
* **Storage Medium**: In-memory dictionary (`dict[str, tuple[float, list[ActiveFiveMinMarket]]]`).
* **TTL (Time to Live)**: **5.0 seconds** (defined in `self._five_min_cache_ttl_seconds`).
* **Refresh Trigger**: Triggered when a new lookup is made and current monotonic time exceeds the cached expiry timestamp.
* **Invalidation Policy**: Automatically overwritten on refresh. No manual cache purging exists.

### Level 2: Token Mapping Cache (Trader)
* **Target File**: [polymarket/trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py)
* **Target Variables**: `self._real_token_ids` and `self._market_token_meta`
* **Storage Medium**: In-memory dictionaries.
* **TTL**: Valid for the duration of the active 5-minute epoch (300 seconds).
* **Refresh Trigger**: The trader evaluates if the cache is valid at the start of each cycle.
* **Invalidation Policy**: Checked in `_cached_active_market_valid`. If the current timestamp is greater than `epoch_end_ts`, the cache is invalidated, and the new epoch's preloaded token mappings are promoted.

---

## 2. Startup States (Cold vs. Warm)

### Cold Start
* At startup, both Level 1 and Level 2 caches are empty.
* The system must query the Gamma API to resolve active markets and extract token IDs.
* This initial fetch introduces a small latency overhead (~300ms–800ms) on the first cycle.

### Warm Start (Preloading / Warmup)
* During active trading, the preloader fetches the token IDs for the *next upcoming* 5-minute epoch.
* The preloader attempts to fetch and parse the orderbooks for these next-epoch tokens.
* If successful, the tokens are cached in `self._preloaded_token_ids` and the orderbook is "warmed."
* At the epoch boundary, the system shifts to a warm start by immediately promoting the preloaded tokens, completely bypassing cold-start Gamma API queries.

---

## 3. Storage Analysis (Disk vs. Memory)

* **Memory Cache**: Yes. All token ID mappings and active market metadata are cached in RAM.
* **Disk Cache**: **No**. No token mappings or orderbook snapshots are cached to disk. This is a design choice to maximize execution speed and minimize IO latency.

---

## 4. Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
