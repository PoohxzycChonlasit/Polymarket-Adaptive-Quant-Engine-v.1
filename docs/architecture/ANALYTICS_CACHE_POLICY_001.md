# ANALYTICS_CACHE_POLICY_001
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document formalizes the caching strategy, TTL parameters, and staleness thresholds for the Analytics Loader V1 in the Polymarket Crypto 5M Quant Engine.

---

## 1. The AnalyticsCache Structure

To prevent excessive disk I/O on the VPS, the engine stores loaded metrics in an in-memory `AnalyticsCache` structure:

```python
@dataclass
class AnalyticsCache:
    cached_metrics: dict[str, Any] = field(default_factory=dict)
    last_loaded_ts: float = 0.0          # System timestamp of memory update
    file_mtime: float = 0.0              # Disk file modification timestamp
    ttl_seconds: float = 300.0           # Cache Time-To-Live (5 minutes)
    max_staleness_seconds: float = 7200.0 # Stale file limit (2 hours)
```

---

## 2. Cache Read and Refresh Logic

At the beginning of each 5-minute cycle loop, the engine queries the cache:

1. **TTL Check**:
   - If $\text{Current Time} - \text{last\_loaded\_ts} < \text{ttl\_seconds}$, the cache is valid. The engine reads metrics directly from memory.
2. **Disk Check**:
   - If $\text{Current Time} - \text{last\_loaded\_ts} \ge \text{ttl\_seconds}$, the engine performs a low-overhead disk call (`os.path.getmtime`) to inspect the file timestamp.
   - **If the timestamp matches `file_mtime`**: The file has not changed. The engine extends `last_loaded_ts` by another 300 seconds and continues reading from memory, avoiding unnecessary read/parse overhead.
   - **If the timestamp differs**: The file has been updated. The engine initiates a read, validates the version, parses the JSON payload, updates `cached_metrics`, and sets `file_mtime` and `last_loaded_ts` to current values.

---

## 3. Staleness and Expiration Rules

Stale analytics introduce risk by applying outdated performance assumptions to a changed market regime:

- **Definition of Stale**:
  - An analytics file is marked as `STALE` if the file modification timestamp is older than **2 hours (7200 seconds)** relative to the current system clock:
    $$\text{Current Time} - \text{file\_mtime} \ge 7200.0\text{s}$$
- **Action on Staleness**:
  - If a file is marked as stale, the loader instantly **invalidates the cache** and empties `cached_metrics`.
  - The engine logs a `[ANALYTICS_STALE]` warning, sends a Telegram alert, and shifts to conservative static default parameters.
