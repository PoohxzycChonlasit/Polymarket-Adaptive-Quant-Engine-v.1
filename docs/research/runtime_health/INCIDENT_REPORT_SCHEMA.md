# Incident Report Schema

type: reliability governance spec
created: 2026-06-06
status: DESIGN_ONLY
code_changed: No
strategy_changed: No
runtime_changed: No
live_changed: No

---

## Purpose

Define the minimum schema for future runtime incident reports.

This document is schema design only. It does not implement report generation,
runtime telemetry, alerting, file writing, or incident automation.

---

## Incident Classes

| Class | Severity default | Description |
|---|---|---|
| `RUNTIME_CRASH` | critical | Process exits unexpectedly or cannot continue. |
| `RUNTIME_WEDGED` | critical | Process alive but heartbeat/system health/log progression stalls. |
| `SHUTDOWN_HANG` | high | Stop requested but shutdown does not complete in bounded time. |
| `DUPLICATE_RUNTIME` | critical | Multiple paper runtimes risk contaminating evidence. |
| `JSONL_WRITE_FAILURE` | high | Quant event category cannot write or is disabled. |
| `JSONL_INTEGRITY_ERROR` | high | Malformed JSONL or missing required base fields. |
| `SYSTEM_HEALTH_STALE` | high | System health events stop updating. |
| `RUNTIME_LOOP_EXCEPTION` | medium | Cycle exception is caught and loop continues. |
| `EXCEPTION_STORM` | high | Repeated runtime loop exceptions in a short window. |
| `FEED_STALE` | high | Oracle, market feed, or orderbook data stale across repeated cycles. |
| `ORDERBOOK_DEGRADED` | medium | Empty, unavailable, stale, or incomplete orderbook state clusters. |
| `RECONCILIATION_BLOCK` | high | Reconciliation blocks trading due to unknown/mismatch state. |
| `RISK_LOCKDOWN` | high | Risk mode enters severe protection state. |
| `TELEGRAM_DEGRADED` | low | Alerts fail or are disabled unexpectedly. |
| `DISK_PRESSURE` | high | Disk free space threatens evidence continuity. |
| `RESEARCH_EXPORT_GAP` | medium | Expected reports or summaries are missing or stale. |

---

## Severity Levels

| Severity | Meaning | Default operator posture |
|---|---|---|
| `critical` | Paper safety or evidence integrity is immediately threatened. | Stop or isolate runtime after preserving evidence. |
| `high` | Reliability degraded; long-duration evidence may be unsafe. | Inspect promptly; stop if persistent. |
| `medium` | Runtime continued, but review is required. | Monitor and include in post-run audit. |
| `low` | Operator convenience or secondary alerting issue. | Track; does not stop paper by itself. |

---

## Required Report Fields

```yaml
incident_id: string
schema_version: "1.0"
created_utc: timestamp
incident_class: string
severity: critical | high | medium | low
status: OPEN | ACKNOWLEDGED | RESOLVED | RETIRED
mode: paper | live | verify | unknown
run_id: string
pid: integer | null
repo_root: string
branch: string | null
commit: string | null

summary: string
first_seen_utc: timestamp
last_seen_utc: timestamp
duration_seconds: number | null

evidence_sources:
  - path: string
    category: owner | system_health | decision_log | execution_log | trade_journal | risk_log | market_snapshot | log | process | report
    run_id_scoped: boolean
    notes: string

trigger:
  signal: string
  threshold: string
  observed_value: string

runtime_state:
  owner_status: string | null
  heartbeat_age_seconds: number | null
  system_health_age_seconds: number | null
  process_alive: boolean | null
  duplicate_runtime_detected: boolean
  stale_runtime_state: string | null

data_integrity:
  malformed_jsonl_lines: integer | null
  disabled_writers:
    - string
  affected_categories:
    - string
  evidence_label: CLEAN_RUN | UNCLEAN_STOP | STALE_INTERVAL | DUPLICATE_CONTAMINATION_RISK | PARTIAL_EVIDENCE | RUN_SCOPED_ONLY | UNKNOWN

operator_action:
  recommended_action: string
  allowed_actions:
    - inspect
    - continue_monitoring
    - clean_stop
    - force_stop_if_clean_stop_fails
    - restart_paper_after_preflight
    - quarantine_evidence
  prohibited_actions:
    - enable_live
    - change_strategy
    - change_risk
    - change_execution
    - delete_runtime_data

resolution:
  resolved_utc: timestamp | null
  resolution_summary: string
  follow_up_required: boolean
  follow_up_doc: string | null
```

---

## Classification Rules

### Runtime crash

Classify as `RUNTIME_CRASH` when:

- owner PID disappears unexpectedly
- process exits without shutdown evidence
- terminal reports an unhandled exception
- no owner release occurs after process exit

### Runtime wedged

Classify as `RUNTIME_WEDGED` when:

- process exists
- owner heartbeat or system health is stale
- decision and market snapshot logs stop progressing

### Exception storm

Classify as `EXCEPTION_STORM` when:

- `runtime_loop_exception` appears in repeated consecutive cycles
- exception rate exceeds a future configured threshold
- loop continues but evidence quality or trading safety is suspect

Suggested initial threshold for future implementation:

- 5 exceptions in 10 minutes, or
- 10 exceptions in 1 hour, or
- same exception class repeats across 3 consecutive cycles

### Duplicate runtime

Classify as `DUPLICATE_RUNTIME` when:

- two matching paper `main.py` processes exist
- ownership override is active
- same date has overlapping run IDs writing concurrently

### JSONL evidence incident

Classify as `JSONL_WRITE_FAILURE` when:

- `quant_disabled_writers` is non-empty
- PermissionError disables writer category
- critical JSONL category stops updating

Classify as `JSONL_INTEGRITY_ERROR` when:

- malformed JSONL lines are detected
- required base event fields are missing above threshold
- timestamps are invalid or non-parseable

---

## Evidence Protection Rules

1. Incident reports must reference evidence files, not rewrite them.
2. Never include secrets, private keys, API tokens, or full wallet secrets.
3. Do not include full Telegram message bodies if they may contain sensitive data.
4. Do not delete partial or malformed JSONL.
5. Label contaminated periods; do not silently filter them away.
6. Prefer run-scoped evidence when duplicate or mixed same-day runs exist.
7. Keep incident reports additive and append-only.

---

## Suggested Storage

Future report path:

```text
runtime/reports/incidents/YYYY-MM-DD/<incident_id>.json
```

Optional markdown summary:

```text
docs/research/runtime_health/incidents/YYYY-MM-DD_<incident_id>.md
```

Do not create these paths automatically until an implementation task is
explicitly approved.

---

## Operator Action Map

| Incident class | Continue | Clean stop | Force stop | Restart paper | Quarantine evidence |
|---|---|---|---|---|---|
| `RUNTIME_CRASH` | No | n/a | n/a | Yes, after preflight | Yes |
| `RUNTIME_WEDGED` | No | Yes | If needed | Yes, after preflight | Yes |
| `SHUTDOWN_HANG` | No | already attempted | If needed | After audit | Maybe |
| `DUPLICATE_RUNTIME` | No | Yes | If needed | After cleanup | Yes |
| `JSONL_WRITE_FAILURE` | Maybe | If critical | No | Maybe | Yes |
| `RUNTIME_LOOP_EXCEPTION` | Yes if isolated | No | No | No | No |
| `EXCEPTION_STORM` | No | Yes | If needed | After audit | Maybe |
| `FEED_STALE` | Maybe | If persistent | No | Maybe | Maybe |
| `DISK_PRESSURE` | Short-term only | Yes if critical | No | No until resolved | Maybe |

---

## Non-Authorization Clause

This schema is documentation only. It does not change runtime behavior, live
behavior, strategy, risk, execution, config, Telegram, report generation, or
file retention.
