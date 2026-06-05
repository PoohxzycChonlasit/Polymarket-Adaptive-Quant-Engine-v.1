# Stale Runtime Policy

type: reliability governance spec
created: 2026-06-06
status: DESIGN_ONLY
code_changed: No
strategy_changed: No
runtime_changed: No
live_changed: No

---

## Purpose

Define stale runtime states, classification rules, and operator actions for
long-duration paper operation.

This document is policy only. It does not implement detection, restart, cleanup,
or process control.

---

## Runtime State Model

| State | Meaning |
|---|---|
| `HEALTHY` | Runtime is active, heartbeat fresh, system health flowing, JSONL evidence intact. |
| `DEGRADED` | Runtime is alive but one or more non-fatal health signals are delayed or partial. |
| `STALE_HEARTBEAT` | Owner heartbeat has stopped updating beyond warning threshold. |
| `STALE_SYSTEM_HEALTH` | Owner heartbeat may exist, but system health JSONL is stale. |
| `WEDGED_ALIVE` | Process exists but loop evidence is not progressing. |
| `DEAD_OWNER` | Owner file points to a PID that no longer exists. |
| `DUPLICATE_RUNTIME_RISK` | More than one paper runtime appears active or evidence writers overlap. |
| `EVIDENCE_AT_RISK` | Runtime may continue, but evidence quality is compromised. |
| `STOPPING` | Owner status says stopping; shutdown should complete soon. |
| `UNKNOWN` | Insufficient evidence to classify. |

---

## Classification Inputs

Minimum inputs:

- owner file status
- owner PID liveness
- owner heartbeat age
- latest `system_health` timestamp
- latest JSONL append times
- command line for matching Python processes

Optional inputs:

- latest console log tail
- Telegram route telemetry
- data quality report
- session runtime evaluator report
- disk free space

---

## State Rules

### HEALTHY

All must be true:

- owner file exists
- owner PID exists
- command line matches paper `main.py`
- heartbeat age <= 60s
- latest `system_health` age <= 120s
- no critical writer category disabled
- no duplicate paper runtime process

### DEGRADED

Any may be true:

- heartbeat age 60-180s
- latest `system_health` age 120-300s
- non-critical writer category disabled
- Telegram degraded but runtime evidence intact
- one supporting JSONL category stale

### STALE_HEARTBEAT

Trigger:

- heartbeat age > 180s while owner status is `active`

Escalate to `WEDGED_ALIVE` if PID exists and system health is also stale.
Escalate to `DEAD_OWNER` if PID no longer exists.

### STALE_SYSTEM_HEALTH

Trigger:

- latest `system_health` age > 300s while owner heartbeat remains fresh

Interpretation:

- heartbeat may still update even when the main loop is unhealthy
- system health has higher evidence value than owner heartbeat for trading-loop
  continuity

### WEDGED_ALIVE

All are true:

- owner PID exists
- owner status is `active`
- heartbeat is stale or system health is stale
- decision or market snapshot logs are not updating

Operator action:

- preserve evidence
- inspect process
- stop cleanly if terminal is responsive
- force stop only if clean stop fails
- do not treat affected interval as clean evidence

### DEAD_OWNER

Trigger:

- owner file exists, but owner PID is absent

Operator action:

- preserve owner file contents
- label prior run as unclean unless shutdown evidence exists
- start new paper runtime only after confirming no duplicate Python process

### DUPLICATE_RUNTIME_RISK

Trigger:

- more than one matching paper `main.py` process
- owner override is true
- same date has overlapping active run IDs with concurrent append times

Operator action:

- stop duplicate runtimes
- quarantine overlapping evidence
- require run-scoped analysis
- do not use day-level aggregate evidence for promotions

### EVIDENCE_AT_RISK

Trigger:

- `system_health`, `execution_log`, or `trade_journal` writer disabled
- malformed JSONL lines appear
- disk pressure threatens writes
- duplicate writers overlap

Operator action:

- continue only if paper safety is intact
- do not use affected run for promotion without data-quality audit
- stop cleanly if evidence loss continues

### STOPPING

Expected behavior:

- owner status is `stopping`
- process exits within bounded shutdown window
- owner file is released
- shutdown `system_health` event appears

Warning:

- if `STOPPING` persists longer than 120s, classify as `SHUTDOWN_HANG`.

---

## Operator Actions Matrix

| State | Action |
---|---|
| `HEALTHY` | Continue |
| `DEGRADED` | Watch closely; inspect latest logs |
| `STALE_HEARTBEAT` | Check process and system health |
| `STALE_SYSTEM_HEALTH` | Treat loop as suspect; inspect terminal |
| `WEDGED_ALIVE` | Attempt clean stop; force only if needed |
| `DEAD_OWNER` | Confirm no process; start new run with contamination note |
| `DUPLICATE_RUNTIME_RISK` | Stop duplicates; quarantine evidence |
| `EVIDENCE_AT_RISK` | Preserve logs; require data-quality audit |
| `STOPPING` | Wait bounded period, then diagnose shutdown hang |
| `UNKNOWN` | Do not promote evidence; inspect manually |

---

## Restart Safety

Restart is allowed only for paper mode and only after:

1. Confirm no live-mode command is involved.
2. Confirm no duplicate runtime remains.
3. Preserve owner file and latest logs.
4. Record previous run ID and final heartbeat.
5. Start with canonical paper command.
6. Confirm new run ID and fresh owner heartbeat.
7. Mark old run as clean, unclean, or unknown.

No restart should:

- delete runtime data
- edit JSONL files
- edit owner files
- change strategy/risk/execution settings
- switch to live mode
- use force kill before clean stop has been attempted, unless process is fully
  unresponsive

---

## Evidence Labels

Use these labels in research notes:

| Label | Meaning |
|---|---|
| `CLEAN_RUN` | Normal owner release and shutdown evidence |
| `UNCLEAN_STOP` | Force kill, missing shutdown event, or orphan owner |
| `STALE_INTERVAL` | Runtime state stale for part of evidence window |
| `DUPLICATE_CONTAMINATION_RISK` | Multiple runtimes may have written same date |
| `PARTIAL_EVIDENCE` | One or more writer categories degraded |
| `RUN_SCOPED_ONLY` | Day-level aggregates are unsafe; use run_id filter |

---

## Non-Authorization Clause

This policy is documentation only. It does not change runtime behavior, live
behavior, restart behavior, strategy, risk, execution, config, or file handling.
