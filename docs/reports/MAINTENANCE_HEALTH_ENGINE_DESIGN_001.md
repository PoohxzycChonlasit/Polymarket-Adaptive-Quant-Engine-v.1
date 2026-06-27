# MAINTENANCE_HEALTH_ENGINE_DESIGN_001

**Date:** 2026-06-27 · **Tier:** GATE Class 2 · **Repairs:** 1 (bootstrap Class 4 pipeline fix)

## Files Created

| File | Content |
|------|---------|
| `docs/architecture/MAINTENANCE_ENGINE_001.md` | 8 sections: 9 maintenance domains, 5-phase lifecycle, safety rules, hot/cold policy, roadmap |
| `docs/architecture/HEALTH_ENGINE_001.md` | 10 sections: 11 dimensions, 5 statuses, health check schema, threshold table, integration with ME/RSM |
| `docs/reports/MAINTENANCE_HEALTH_ENGINE_DESIGN_001.md` | This report |

## Files Updated (bootstrap repair)

| File | Change |
|------|--------|
| `docs/operations/AGENT_PIPELINE_001.json` | TOOL_PIPELINE_LOOP: added task_class 4 |
| `docs/operations/TOOL_PIPELINES_001.json` | Added TOOL_PIPELINE_LOOP pipeline entry |
| `docs/operations/ACTIVE_WORKFLOW_STATE_001.json` | Fixed next_workflow_tier from GATE to LOOP |

## Why This Before Log Governance Implementation

The gate check (`RUNTIME_LOG_GOVERNANCE_GATE_001`) revealed that `logs/` is at 1.6 GB. Before implementing the fix:
1. The Maintenance Engine design ensures the offline script follows a safe lifecycle (inspect → plan → dry_run → execute → verify)
2. The Health Engine design provides the thresholds that define when each domain needs action
3. Together they ensure the log governance script is not a one-off hack but the first phase of a structured framework

Without this design: the log governance script might delete files unsafely, skip dry-run mode, or miss the integration with the Runtime Session Manager guard.

## Architecture Summary

**Maintenance Engine:** Policy-driven operations on 9 domains (logs, JSONL, sessions, temp, archives, loop memory, snapshots, disk). All operations run dry-run first. Safety rules: no deletion without policy, no active session mutation, full audit trail. 5-phase roadmap: Phase A (offline script) → Phase B (runtime code fix) → Phase C (JSONL compaction) → Phase D (archive engine) → Phase E (scheduler).

**Health Engine:** 11 dimensions producing a single `HealthReport` with 5 statuses (HEALTHY → STOP_REQUIRED). Threshold table with concrete values from the gate check (e.g., 706 rotated backups = CRITICAL). Integrates with Maintenance Engine (trigger cleanup) and Runtime Session Manager (guard active sessions).

## How It Responds to Gate Evidence

| Gate finding | Engine design response |
|-------------|----------------------|
| `logs/` = 1.6 GB, 706 backup files | Phase A: offline script compresses/deletes backups > 5; Phase B: `backupCount=5` in logger |
| JSONL = 217 MB, ~135 MB/day peaks | Phase C: nightly `.jsonl.gz` rotation; Health Engine warns at 200 MB |
| `validation_run_output.log` = 27.8 MB unrotated | Phase A: rotate at 50 MB, keep last 3 |
| Sessions healthy (16 KB) | No immediate action; RSM guard sufficient |

## Next Recommended Task

**`RUNTIME_LOG_GOVERNANCE_DESIGN_001`** — LOOP tier Class 4. Implement `tools/flaos/log_governance.py` Phase A offline script following the Maintenance Engine lifecycle (inspect → dry_run → execute). URGENCY HIGH.

## Final Verdict

```
MAINTENANCE_HEALTH_ENGINE_DESIGN_COMMITTED
```
