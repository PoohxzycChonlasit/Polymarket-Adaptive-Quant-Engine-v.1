# RUNTIME_LOG_GOVERNANCE_GATE_001

**Date:** 2026-06-27  
**Role:** 29_ARCHITECTURE_GOVERNANCE_AGENT  
**Task Class:** 2 (GATE_CHECK / LOG_GOVERNANCE)  
**Workflow Tier:** GATE  
**Bootstrap status:** HEALTHY — next_task=RUNTIME_LOG_GOVERNANCE_001, tier=GATE

---

## 1. Audit Summary

| Area | Path | Size | Files | Status |
|------|------|------|-------|--------|
| JSONL event stream | `runtime/event_stream/` | **217 MB** | 3 | ⚠️ GROWING — 2026-06-26 file is 135 MB |
| Validation outlogs | `runtime/validation_run_output.log` | **27.8 MB** | 1 | ⚠️ UNROTATED — single large file |
| Validation err | `runtime/validation_run_err.log` | 6.5 KB | 1 | OK |
| Session metadata | `runtime/sessions/` | 16 KB | 3 | OK — small JSON files |
| Session validation logs | `runtime/validation/` | 28 KB | 6 | OK — mostly 0-byte stubs |
| Console logs | `logs/` | **1.6 GB** | 1,005 total (299 `.log` + 706 `.log.*`) | 🔴 CRITICAL — needs rotation |

---

## 2. Critical Finding: `logs/` at 1.6 GB

`logs/` contains **1,005 log files** — 299 active `.log` files and 706 rotated `.log.N` files — totalling **1.6 GB**. This is the largest disk consumer by far.

**Root cause:** The Python logging handler (`utils/logger.py`) uses a `RotatingFileHandler` that creates `.log.N` backup files. 706 backup files accumulated without deletion. Each backup is ~2 MB × 706 = ~1.4 GB of rotated backups alone.

**Risk level:** HIGH — disk exhaustion will crash any paper or live runtime. At current growth rate (if sessions continue), this will fill available disk.

**Governance needed:**
1. Set `backupCount` in RotatingFileHandler to a small number (e.g., 5)
2. Delete or archive backup files older than 7 days
3. Compress `.log.N` files older than 24 hours

**Important:** Deletion of log files is a CLASS 7 change (modifies runtime behavior of logger). Governance design must specify: which files are safe to delete offline, which require code change, and which require user sign-off.

---

## 3. JSONL Event Stream Analysis

| File | Date | Size | Lines | Growth rate |
|------|------|------|-------|-------------|
| `runtime_events_2026-06-25_001.jsonl` | Jun 25 | 8.1 MB | 8,377 | ~8 MB/day |
| `runtime_events_2026-06-26_001.jsonl` | Jun 26 | **135 MB** | 47,181 | ~135 MB/day (heavy session day) |
| `runtime_events_2026-06-27_001.jsonl` | Jun 27 (in progress) | 83 MB | 19,081 | ~83 MB/6h → ~160 MB/day projected |

**Key observation:** 2026-06-26 was an unusually large day (Batch 3A–3C paper runs + FLAOS development). Normal days may be ~8–30 MB. But the event stream has no compression or retention policy today.

**Governance needed:**
- Compress JSONL files older than 3 days to `.jsonl.gz`
- Retain compressed files for 30 days
- Alert if any single day file exceeds 200 MB before compression

**Safe governance:** These are read-only archived logs. Compression is safe as an offline operation. NO runtime code change required for compression — this is a manual or offline script action.

---

## 4. Runtime Validation Outlogs

| File | Size | Issue |
|------|------|-------|
| `runtime/validation_run_output.log` | **27.8 MB** | Single growing file — no rotation |
| `runtime/validation_run_err.log` | 6.5 KB | OK |
| `runtime/validation/*.log` (session-scoped) | 0–16 KB each | OK — controlled by Runtime Session Manager |

**Governance needed:** `runtime/validation_run_output.log` is written by the runtime session manager for ad-hoc runs outside the session manager framework. It needs a rotation cap (e.g., 50 MB max, keep last 3).

**Safe governance:** This is a documentation/tools-level change to the session manager, not a trading runtime change. Class 4 task.

---

## 5. Runtime Session Manager Logs

`runtime/sessions/` contains 3 JSON metadata files (~600 bytes each). `runtime/validation/` contains 6 log files (mostly 0-byte stubs plus one 16 KB stdout log). Both are well-governed by the Runtime Session Manager already.

**Governance needed:** Mild — set a max session retention of 30 entries, delete older metadata.

---

## 6. Scope Assessment for Governance Design

### Safe for offline script (CLASS 4 — no code change)
- Compress `runtime/event_stream/*.jsonl` older than 3 days to `.jsonl.gz`
- Compress `logs/*.log.N` backups older than 7 days
- Archive and delete `logs/*.log.N` files keeping last 5 per session
- Rotate `runtime/validation_run_output.log` when it exceeds 50 MB

### Requires runtime code change (CLASS 7 — gate needed)
- Reduce `backupCount` in `utils/logger.py` RotatingFileHandler
- Add retention limit to Runtime Session Manager log cleanup
- Add size limit to `validation_run_output.log` writer

### Requires explicit user sign-off (CLASS 8 — live risk boundary)
- Any deletion of live trading logs
- Any modification of JSONL event streams older than 24h (replay tooling depends on them)
- Any change to event schema versioning

---

## 7. Active Question Status

`OPEN: LOW_PRICE_TRUTH_RESOLUTION_001` — does NOT block log governance. Log governance is infrastructure, not strategy.

---

## 8. Recommended Design Scope for RUNTIME_LOG_GOVERNANCE_DESIGN_001

**Phase A (CLASS 4 — offline tools only):**
- `tools/flaos/log_governance.py` — offline script: compress JSONL, compress/archive logs/.log.N, rotate validation_run_output.log
- Safe to run without any code changes
- Evidence Grade B (write-only to runtime/, no trading path)

**Phase B (CLASS 7 — runtime code change with gate):**
- Modify `utils/logger.py` `backupCount` from current unlimited to 5
- Add session log cleanup to Runtime Session Manager
- Requires separate gate + design + paper run validation

**Recommended immediate action:** Proceed with Phase A design only. Phase B gets its own gate check after Phase A is complete and validated.

---

## 9. Stop Conditions Verified

| Check | Result |
|-------|--------|
| No deletion of runtime data during this audit | ✓ |
| No modification to polymarket/ | ✓ |
| No modification to utils/logger.py | ✓ |
| No modification to trading runtime | ✓ |
| No live trading path touched | ✓ |
| JSONL event stream integrity unchanged | ✓ |

---

## 10. Final Verdict

```
PROCEED_RUNTIME_LOG_GOVERNANCE_DESIGN
```

**Scope:** Phase A only (CLASS 4 offline script). Phase B (CLASS 7 runtime code change) requires separate gate after Phase A is validated.

**Next task:** `RUNTIME_LOG_GOVERNANCE_DESIGN_001` — design the `tools/flaos/log_governance.py` offline script with compress/rotate/archive capabilities. LOOP tier, Class 4.

**Urgency:** HIGH — `logs/` is at 1.6 GB. Phase A script can safely reclaim ~1.4 GB of rotated backup files without touching trading runtime.
