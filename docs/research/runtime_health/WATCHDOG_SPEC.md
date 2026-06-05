# Watchdog Spec

type: reliability governance spec
created: 2026-06-06
status: DESIGN_ONLY
code_changed: No
strategy_changed: No
runtime_changed: No
live_changed: No

---

## Purpose

Define a future external watchdog for long-duration paper operation.

This document is a specification only. It does not implement a process, service,
thread, timer, restart loop, or runtime integration.

---

## Scope

The watchdog should observe paper runtime health from outside the trading loop.
It must never approve trades, alter risk, change strategy, change execution,
change config, or enable live mode.

Allowed future inputs:

- `runtime/ownership/paper_runtime_owner.json`
- `runtime/quant_data/system_health/YYYY-MM-DD.jsonl`
- latest JSONL append timestamps by category
- process list for the owner PID
- disk free space
- optional Telegram/operator notification channel

Disallowed inputs:

- private keys
- wallet secrets
- live order approval state
- strategy thresholds
- risk sizing parameters
- execution policy switches

---

## Monitored Signals

| Signal | Source | Healthy condition | Warning condition | Critical condition |
|---|---|---|---|---|
| Owner file exists | `runtime/ownership/paper_runtime_owner.json` | Present while paper runtime active | Missing while operator expects active runtime | Missing plus no system health |
| Owner PID alive | Process table | PID exists and command matches repo `main.py` | PID exists but command is ambiguous | PID absent while owner says active |
| Owner heartbeat age | owner file `heartbeat_utc` | <= 60s | > 60s and <= 180s | > 180s |
| System health age | latest `system_health` event | <= 120s | > 120s and <= 300s | > 300s |
| JSONL append continuity | file mtimes | active categories update during market loop | one category stale | multiple critical categories stale |
| Runtime loop exception rate | `system_health` payload | isolated exceptions | repeated burst | exception storm |
| Disk free space | filesystem | > 10 GB or > 20% free | 5-10 GB or 10-20% free | < 5 GB or < 10% free |
| Writer degradation | `quant_disabled_writers` | none | non-critical category disabled | trade/execution/system health disabled |
| Duplicate owner risk | ownership files/processes | one owner | stale prior owner recovered | active duplicate process |

---

## Heartbeat Monitoring

The owner heartbeat is the primary liveness signal.

Heartbeat age buckets:

| Bucket | Definition | State |
|---|---|---|
| `FRESH` | age <= 60s | healthy |
| `DELAYED` | 60s < age <= 180s | warning |
| `STALE` | 180s < age <= 600s | critical |
| `EXPIRED` | age > 600s | critical, recovery review required |

Heartbeat checks must compare:

- owner PID
- owner run_id
- owner status
- heartbeat timestamp
- system clock sanity

The watchdog must not delete owner files automatically unless a separate
operator-approved recovery phase explicitly permits it.

---

## JSONL Continuity Monitoring

Critical categories:

- `system_health`
- `decision_log`
- `risk_log`
- `trade_journal`
- `execution_log`

Supporting categories:

- `market_snapshots`
- `orderbook_lineage`
- `research_log`
- `path_truth`

Rules:

1. If `system_health` is stale, treat runtime health as unknown even if other
   files are updating.
2. If `trade_journal` is quiet but decisions are flowing, do not classify as
   failure; no-trade periods are valid.
3. If `decision_log` and `system_health` both stop while owner heartbeat stops,
   classify as `DEAD_OR_WEDGED`.
4. If one writer category is disabled, classify as `LOGGING_DEGRADED`.
5. If `system_health`, `trade_journal`, or `execution_log` writer is disabled,
   classify as `EVIDENCE_AT_RISK`.

---

## Incident Classes

| Class | Trigger |
|---|---|
| `WATCHDOG_HEARTBEAT_STALE` | owner heartbeat exceeds threshold |
| `WATCHDOG_PROCESS_MISSING` | owner PID no longer exists |
| `WATCHDOG_SYSTEM_HEALTH_STALE` | latest system health event too old |
| `WATCHDOG_JSONL_STALE` | expected JSONL category stops updating |
| `WATCHDOG_DUPLICATE_RUNTIME` | more than one matching paper process |
| `WATCHDOG_DISK_PRESSURE` | disk free threshold crossed |
| `WATCHDOG_EXCEPTION_STORM` | repeated runtime loop exceptions |
| `WATCHDOG_LOGGING_DEGRADED` | quant writer category disabled |
| `WATCHDOG_TELEGRAM_DEGRADED` | alert channel appears unavailable |

---

## Operator Actions

| State | Operator action |
|---|---|
| Healthy | Continue monitoring |
| Warning | Inspect terminal and latest system health |
| Critical | Preserve logs, stop or restart only via runbook |
| Evidence at risk | Do not use affected run for promotion without audit |
| Duplicate runtime | Stop and quarantine duplicate evidence |
| Disk pressure | Stop nonessential logging only after scoped approval; otherwise stop paper runtime cleanly |

---

## Restart Boundaries

The watchdog may recommend restart only when:

- heartbeat is stale or expired
- PID is missing
- system health is stale
- JSONL evidence is at risk
- operator confirms paper-only mode

The watchdog must not:

- start live mode
- change command-line flags except those approved in the runbook
- delete runtime data
- edit owner files
- clear stale owners without operator approval
- restart repeatedly without cooldown

Recommended restart cooldown: at least 5 minutes between automated restart
attempts if a future implementation is approved.

---

## Evidence Protection Rules

1. Every restart should create a new `run_id`.
2. Stale or duplicate periods must be labeled in research notes.
3. Do not merge day-level evidence across duplicate runtime windows without
   run-scoped filtering.
4. Do not delete malformed or partial JSONL; preserve for audit.
5. If writer degradation occurs, mark the run `EVIDENCE_PARTIAL`.
6. If duplicate writers exist, mark affected date `CONTAMINATION_RISK`.

---

## Future Tests Required

If implemented later, tests should cover:

- fresh heartbeat healthy
- delayed heartbeat warning
- stale heartbeat critical
- missing PID detection
- duplicate paper process detection
- system health stale detection
- disk pressure classification
- JSONL stale classification
- no live-mode launch
- no file deletion

---

## Non-Authorization Clause

This spec is documentation only. It does not change runtime behavior, live
behavior, strategy, risk, execution, config, Telegram, or file retention.
