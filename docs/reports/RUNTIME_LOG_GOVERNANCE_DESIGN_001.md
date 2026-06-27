# RUNTIME_LOG_GOVERNANCE_DESIGN_001

**Date:** 2026-06-27 · **Tier:** LOOP Class 4 · **Repairs:** 0

## Files Created

| File | Content |
|------|---------|
| `docs/architecture/RUNTIME_LOG_GOVERNANCE_001.md` | 12-section Phase A design: 5 subcommands, safety policy, 4 target file classes, retention table, JSON report schema, verification checklist, stop conditions |
| `docs/reports/RUNTIME_LOG_GOVERNANCE_DESIGN_001.md` | This report |

## Design Summary

**5 subcommands** following Maintenance Engine lifecycle:

| Command | Action | Mutates files? |
|---------|--------|----------------|
| `inspect` | Measure sizes, count files, identify candidates | NO |
| `plan` | Apply retention policies, produce action plan | NO |
| `dry-run` | Simulate execute, show every action that WOULD run | NO |
| `execute --confirm` | Perform actions; requires explicit `--confirm` | YES |
| `report` | Re-scan post-execute, write audit report | NO |

**Safety rules enforced:**
- `execute` without `--confirm` always runs dry-run only
- Session guard (`runtime_session.py guard`) called before any DELETE
- Per-file PID check before each deletion
- Hard cap: 800 files per execute run
- JSONL: compress only, never delete (Phase A)
- Audit report written to `docs/reports/MAINTENANCE_RUN_*.md` after every execute

**Estimated Phase A space reclaim:** ~1.4–1.5 GB
- 701 excess log backups (`.log.N` where N > 5): ~1.4 GB
- JSONL compression (2 files): ~130 MB additional space freed

**Phase B (out of scope):** `utils/logger.py` `backupCount=5` fix — CLASS 7, separate gate.

## Target File Classes

| Class | Retention | Phase A action |
|-------|-----------|---------------|
| `logs/*.log.N` N > 5, age > 1d | Delete | DELETE (after guard) |
| `runtime/event_stream/*.jsonl` age > 3d | Compress | COMPRESS to .jsonl.gz |
| `runtime/validation/*.log` 0-byte, age > 7d | Delete | DELETE |
| `runtime/validation_run_output.log` | Rotate at 50 MB | ALERT only |

## Final Verdict

```
RUNTIME_LOG_GOVERNANCE_DESIGN_COMMITTED
```
