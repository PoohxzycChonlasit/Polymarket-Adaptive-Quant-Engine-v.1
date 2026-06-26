# ANALYTICS_LOADER_V1_DESIGN_001
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document presents the master design for the **Analytics Loader V1**. The Loader bridges the gap between offline/dashboard analytics and the real-time runtime decision engine, providing a fail-soft integration that enhances sizer and risk decisions without introducing operational runtime dependencies.

---

## 1. Master Loader Architecture

The Analytics Loader operates as a non-blocking, cycle-level file reader that runs at the beginning of each 5-minute cycle loop:

```
                  Start of 5-Minute Trading Cycle
                                 │
                                 ▼
                     Check Analytics Cache TTL
             ┌───────────────────┴───────────────────┐
      Cache Valid? (TTL < 300s)              Cache Expired?
             │                                       │
             ▼                                       ▼
     Read from Memory                     Read JSON files from Disk
                                                     │
                                           ┌─────────┴─────────┐
                                      Read Success?       Read Failure? (Locked/Missing)
                                           │                   │
                                           ▼                   ▼
                                    Validate Version     Use Static Defaults
                                           │                   │
                                           ▼                   ▼
                                    Update Cache       Log Warning & Continue
```

- **Execution Threading**: To ensure that file disk latency does not block the time-critical market scanner, the loader executes reads inside a separate worker thread or using non-blocking asynchronous file I/O.
- **Fail-Soft Disk Reading**: The loader handles file read errors (such as Windows `PermissionError` locks) by retrying with a short backoff (e.g. 5 retries over 500ms). If the lock persists, the loader aborts, uses cached or default values, and continues cycle execution.

---

## 2. Ingestion & Version Validation

- **File Path**: The loader reads metrics from JSON files written under `runtime/reports/` (e.g., `paper_evaluation_latest.json`).
- **Version Verification**: Every report contains a `schema_version` string (e.g. `"1.0.0"`).
- **Validation Gates**:
  1. **Schema Check**: If `schema_version` is missing or is incompatible with the loader's expected version, the file is rejected.
  2. **Staleness Check**: The file's modification timestamp is checked. If the file is older than **2 hours (7200 seconds)**, it is classified as `STALE` and ignored.
  3. **Data Integrity Check**: If the JSON payload is corrupt, truncated, or fails Pydantic structural validation, it is rejected.
- **Fallback**: If validation fails for any reason, the system falls back immediately to static default values.
