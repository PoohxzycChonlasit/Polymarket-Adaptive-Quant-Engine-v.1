# RUNTIME_LOG_GOVERNANCE_001

**Date:** 2026-06-27 · **Destination:** `docs/architecture/` · **Status:** DESIGN v1 — Phase A

---

## 1. Objective

Design the Phase A offline log governance script (`tools/flaos/log_governance.py`) that safely inspects, plans, and optionally cleans the `logs/` directory and `runtime/` data artifacts — following the Maintenance Engine lifecycle and never touching active runtime processes.

---

## 2. Current Log Problem Summary (from Gate Check)

| Artifact | Size | Issue | Urgency |
|----------|------|-------|---------|
| `logs/polytrade_bot_*.log.*` (706 rotated backups) | ~1.4 GB | `RotatingFileHandler` with no `backupCount` limit; thousands of backups accumulated | CRITICAL |
| `logs/polytrade_bot_*.log` (299 active files) | ~200 MB | Many from past sessions no longer running | HIGH |
| `runtime/event_stream/*.jsonl` | 217 MB | No compression; 2026-06-26 = 135 MB | MEDIUM |
| `runtime/validation_run_output.log` | 27.8 MB | Single unrotated file growing with each tool run | MEDIUM |
| `runtime/validation/session_*_stdout.log` | ~16 KB | Mostly 0-byte stubs from session manager | LOW |

**Primary goal of Phase A:** Reclaim ~1.4 GB from rotated log backups without touching trading runtime.

---

## 3. Phase A Offline Tool Scope

**In scope for Phase A:**
- `logs/polytrade_bot_*.log.N` — rotated log backups (`.log.1`, `.log.2`, etc.)
- `runtime/validation/session_*_stdout.log` — session validation logs from completed sessions
- `runtime/validation/session_*_stderr.log` — same
- `runtime/event_stream/*.jsonl` — JSONL compression only (no deletion)
- `runtime/validation_run_output.log` — rotation check (no deletion, only alert)

**Out of scope for Phase A (requires Phase B):**
- `utils/logger.py` `backupCount` fix — runtime code change, separate gate
- Active `.log` files being written by running processes
- Live JSONL files being written by active paper runs
- Any file held open by an active PID

---

## 4. Command Design

The tool exposes subcommands following the Maintenance Engine lifecycle: `inspect → plan → dry-run → execute → report`.

### 4.1 `inspect` subcommand

```bash
python tools/flaos/log_governance.py inspect
```

**Action:** Read-only scan. Measures file sizes, counts files by type, identifies candidates for cleanup. No mutation.

**Output (JSON to stdout):**
```json
{
  "timestamp": "ISO",
  "scan_domains": {
    "logs_rotated_backups": {
      "file_count": 706,
      "total_bytes": 1441792000,
      "oldest_file": "polytrade_bot_20260508_234142_15588.log.706",
      "oldest_age_days": 50
    },
    "logs_active": {"file_count": 299, "total_bytes": 204800000},
    "runtime_validation_logs": {"file_count": 6, "total_bytes": 28672},
    "runtime_event_stream": {
      "file_count": 3,
      "total_bytes": 227499008,
      "compressible_files": ["runtime_events_2026-06-25_001.jsonl", "runtime_events_2026-06-26_001.jsonl"]
    },
    "validation_run_output": {"bytes": 27803940, "rotation_needed": true}
  },
  "active_session_guard": "PASS",
  "health_status": "CRITICAL",
  "recommended_action": "run plan"
}
```

### 4.2 `plan` subcommand

```bash
python tools/flaos/log_governance.py plan
```

**Action:** Read-only. Applies retention policies to the inspect output and produces a plan (list of files to compress, archive, or delete). No mutation.

**Output (JSON to stdout):**
```json
{
  "plan_id": "PLAN-20260627-001",
  "actions": [
    {
      "action": "DELETE",
      "target_pattern": "logs/*.log.N where N > 5 and file_age_days > 1",
      "estimated_files": 701,
      "estimated_bytes_reclaimed": 1430000000,
      "safe_guard": "active_pid_check required before each deletion"
    },
    {
      "action": "COMPRESS",
      "target": "runtime/event_stream/runtime_events_2026-06-25_001.jsonl",
      "estimated_bytes_reclaimed": 7700000,
      "output": "runtime_events_2026-06-25_001.jsonl.gz"
    },
    {
      "action": "COMPRESS",
      "target": "runtime/event_stream/runtime_events_2026-06-26_001.jsonl",
      "estimated_bytes_reclaimed": 128000000,
      "output": "runtime_events_2026-06-26_001.jsonl.gz"
    },
    {
      "action": "ALERT",
      "target": "runtime/validation_run_output.log",
      "message": "27.8 MB — rotation recommended but not performed by Phase A"
    }
  ],
  "estimated_total_reclaim_mb": 1523,
  "warnings": [],
  "dry_run_ready": true
}
```

### 4.3 `dry-run` subcommand

```bash
python tools/flaos/log_governance.py dry-run
```

**Action:** Runs the plan in simulation mode. Prints every action that WOULD be taken without actually executing. Verifies active session guard passes. Output includes a full dry-run report.

**Safety:** If `--session-guard` check fails (active paper session detected), dry-run still proceeds but marks all deletion actions as BLOCKED.

**Output:** Dry-run report JSON + human-readable summary to stdout. No file mutations.

### 4.4 `execute` subcommand

```bash
python tools/flaos/log_governance.py execute [--confirm]
```

**Action:** Executes the plan. Requires `--confirm` flag to prevent accidental runs. Performs active session guard before each DELETE action.

**Execution order:**
1. Session guard check → abort if active session found
2. Compress JSONL files (Phase A: 2026-06-25 and 2026-06-26 only)
3. Delete rotated log backups older than `backupCount` threshold (default: keep 5 per log name)
4. Write audit report to `docs/reports/MAINTENANCE_RUN_YYYYMMDD_NNN.md`
5. Append loop memory entry

**Atomic safety:** If any step fails, the remaining steps are still attempted but failures are logged. No rollback on success/failure mix — the audit report records every action taken.

### 4.5 `report` subcommand

```bash
python tools/flaos/log_governance.py report
```

**Action:** Read-only re-scan after execute. Measures post-cleanup sizes, computes space reclaimed, writes final report to `docs/reports/MAINTENANCE_RUN_*.md`.

---

## 5. Safety Policy

| Rule | Implementation |
|------|---------------|
| Dry-run first | `execute` without `--confirm` prints dry-run output and exits 0 |
| No deletion by default | `execute` requires explicit `--confirm` flag |
| No active session mutation | Call `tools/flaos/runtime_session.py guard` before any DELETE; abort if active |
| No live runtime interference | Skip any file whose PID is found in `runtime/sessions/*.json` active sessions |
| Session guard per-file | For each file in DELETE list, re-check PID ownership at deletion time |
| Audit trail required | Every execute writes `docs/reports/MAINTENANCE_RUN_YYYYMMDD_NNN.md` |
| JSONL always compressed, never deleted | Phase A only compresses JSONL; original retained until Phase C |
| Max deletions per run | Hard cap: 800 files per execute run (prevents runaway deletion) |
| Dry-run output shown before execute | Any execute that follows a dry-run prints "Proceeding from dry-run plan..." |

---

## 6. Target File Classes

### 6.1 `logs/polytrade_bot_*.log.N` (rotated backups)

**Retention policy:**
- Keep: last 5 rotated backups per base log name (`*.log.1` through `*.log.5`)
- Delete: `*.log.6` and above, if age > 1 day
- Never delete: any file whose base log name is held open by an active PID

**Estimated reclaim:** ~1.4 GB from 701 excess backups

### 6.2 `runtime/validation/session_*_stdout.log` and `session_*_stderr.log`

**Retention policy:**
- Keep: logs from sessions within last 7 days
- Delete: 0-byte stubs from sessions older than 7 days
- Keep: any non-zero logs from sessions where PID is still in sessions/ metadata

**Estimated reclaim:** negligible (mostly 0-byte stubs)

### 6.3 `runtime/event_stream/*.jsonl`

**Action: COMPRESS only (Phase A). Never delete.**
- Files older than 3 days → compress to `.jsonl.gz` in same directory
- Current day's file → NEVER touch
- Verify compressed file is readable before marking complete
- Keep original alongside `.gz` for 7 days, then delete original (Phase C)

**Phase A scope:** Compress `runtime_events_2026-06-25_001.jsonl` and `runtime_events_2026-06-26_001.jsonl`  
**Estimated reclaim after compression:** ~130–150 MB (`.jsonl.gz` is typically 3–5× smaller)

### 6.4 `runtime/validation_run_output.log`

**Action: ALERT only (Phase A)**
- Log size is 27.8 MB; threshold is 50 MB
- Phase A: report size, recommend rotation
- Phase B: add rotation to `tools/flaos/runtime_session.py`

---

## 7. Retention Policy

| File type | Keep | Compress after | Delete original after | Never delete |
|-----------|------|---------------|----------------------|-------------|
| `logs/*.log` (active) | Always | — | — | ✓ |
| `logs/*.log.N` (N ≤ 5) | Always | — | — | ✓ |
| `logs/*.log.N` (N > 5, age > 1d) | — | — | When execute runs | ✗ |
| `runtime/event_stream/current_day.jsonl` | Always | — | — | ✓ |
| `runtime/event_stream/*.jsonl` (age > 3d) | — | Immediately | After 7 more days | Never until Phase C |
| `runtime/validation/*.log` (age < 7d) | Always | — | — | ✓ |
| `runtime/validation/*.log` (0-byte, age > 7d) | — | — | When execute runs | ✗ |
| `runtime/sessions/*.json` | Last 30 | — | After 30 entries | ✓ |

---

## 8. Compression / Archive Policy

**Compression:**
- Algorithm: gzip (stdlib `gzip` module — no dependencies)
- Output: `filename.jsonl.gz` alongside original
- Verify: read first and last line from `.gz` file to confirm integrity
- Log: write compression action + byte counts to audit report

**Archive (Phase D — not Phase A):**
- Move old `.gz` files to `runtime/archive/YYYY/MM/`
- Monthly consolidation of loop memory

---

## 9. JSON Report Schema

```json
{
  "$schema": "maintenance_run_v1",
  "run_id": "MAINT-20260627-001",
  "mode": "dry_run | execute",
  "started_at": "ISO timestamp",
  "completed_at": "ISO timestamp",
  "session_guard": "PASS | BLOCKED",
  "active_sessions_at_start": 0,
  "actions": [
    {
      "action": "DELETE | COMPRESS | SKIP | ALERT",
      "file": "path/to/file",
      "bytes_before": 1999899,
      "bytes_after": 0,
      "status": "SUCCESS | SKIPPED | FAILED | DRY_RUN",
      "reason": "rotated backup N>5 and age>1d",
      "error": null
    }
  ],
  "summary": {
    "files_deleted": 701,
    "files_compressed": 2,
    "files_alerted": 1,
    "files_skipped": 0,
    "bytes_reclaimed": 1537000000,
    "bytes_compressed": 135000000,
    "errors": 0
  },
  "post_run_health": {
    "logs_mb": 200,
    "runtime_event_stream_mb": 90,
    "total_reclaimed_mb": 1447
  }
}
```

---

## 10. Verification Checklist (post-execute)

```
[ ] docs/reports/MAINTENANCE_RUN_YYYYMMDD_001.md created
[ ] logs/ size < 300 MB (from ~1.6 GB)
[ ] runtime/event_stream/ contains .jsonl.gz files for 2026-06-25 and 2026-06-26
[ ] runtime/event_stream/*.jsonl.gz readable (spot check first + last line)
[ ] No active paper sessions were affected (session_guard=PASS in report)
[ ] No current-day JSONL touched
[ ] No active log file (.log, not .log.N) deleted
[ ] runtime/validation_run_output.log still present and intact
[ ] bootstrap --diagnose still HEALTHY after run
[ ] loop memory entry appended with bytes_reclaimed
```

---

## 11. Stop Conditions

| Condition | Action |
|-----------|--------|
| `guard` detects active paper session | Abort execute; print "ACTIVE SESSION — aborting. Retry when session completes." |
| PID check finds file held by active process | Skip that file; continue with others; log SKIPPED |
| Compression of JSONL fails checksum | Do NOT delete original; mark FAILED in report; continue |
| More than 800 files queued for deletion | Abort with error: "Safety cap exceeded — manual review required" |
| `logs/` directory not found | Abort with error: wrong directory |
| Any file matches active session PID | Skip; log |
| `--confirm` flag missing | Print dry-run output only; exit 0 |

---

## 12. Future Phase B — Logger `backupCount` Fix

Phase B requires modifying `utils/logger.py` to add `backupCount=5` to the `RotatingFileHandler` call. This:
- Is a CLASS 7 runtime code change (requires separate gate)
- Prevents accumulation of excess backups going forward
- Does NOT reclaim existing backups (Phase A script handles that)
- Must be followed by a paper run validation (compile + 5 cycles + JSONL check)

**Phase B is NOT in scope for the current implementation.**
