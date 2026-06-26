# ANALYTICS_DEPENDENCY_BOUNDARY_001
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document formalizes the Dependency Boundary and reader/writer isolation rules for the Analytics Loader V1, establishing the strict requirement that offline telemetry cannot block runtime execution.

---

## 1. Zero Dependency Boundary (0% Runtime Dependency)

The core quant engine operates under the absolute constraint that **analytics are an enhancement layer, not a runtime requirement**:

- **Liveness Invariant**:
  - The trading engine must remain 100% operational if all files in `runtime/reports/` are deleted, corrupted, stale, or have a version mismatch.
- **Zero-File Ingestion**:
  - If the loader starts with zero files found, it populates the `AnalyticsCache` with pre-defined static fallback constants (e.g. Normal mode caps, 10% Kelly bounds, and standard correlation overrides). The execution loop continues scanning and placing orders.
- **Memory Safety**:
  - The loader uses read-only, non-blocking file handles and parses inputs in-memory. Memory allocation for cached metrics is bounded to prevent heap expansion.

---

## 2. Writer and Reader Isolation

To avoid resource lockups, file sharing violations (such as Windows `PermissionError` and errno 13), and database write conflicts, the engine enforces a strict read/write boundary:

```
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     OFFLINE ENGINES (WRITERS)   │       │     RUNTIME TRADER (READER)     │
├─────────────────────────────────┤       ├─────────────────────────────────┤
│ - tools/replay_analyzer.py      │       │ - polymarket/trader.py          │
│ - tools/paper_evaluation_rep.py │       │ - AnalyticsLoader V1            │
├─────────────────────────────────┤       ├─────────────────────────────────┤
│ Writes JSON reports to disk.    │ ────► │ Non-blocking read-only parsing. │
│ Bounded write loops.            │       │ Bypasses file on locks.         │
└─────────────────────────────────┘       └─────────────────────────────────┘
```

- **Writers**: Standalone python scripts process raw JSONL and scan logs offline, writing reports under `runtime/reports/`. They run on cron schedules or operator request, and have no access to the CLOB execution client or wallet signatures.
- **Reader**: The runtime engine is a strict reader in this directory. The loader performs read-only parsing and *never* writes back to the report files or attempts to clean up old reports.
- **Isolation Rule**: Because the runtime engine is a reader, any crash or lockup of the offline analyzer has zero impact on liveness. The bot continues trading on the last cached metrics until the TTL expires, then shifts to static defaults.
