# ROOT_MD_TRACKED_BATCH_T1_001

**Date:** 2026-06-26  
**Role:** 24_REPOSITORY_LIBRARIAN_AGENT  
**Task Class:** 3 (DOCS_HOUSEKEEPING) — git mv only, no commit  
**Baseline:** `3762bcd` docs: add final root markdown inventory

---

## Summary

Moved 22 tracked root architecture/design markdown files to `docs/architecture/` using `git mv`. All 22 renames are staged as `R100` (100% identical content — pure rename, no edits). No commit made.

---

## Source → Destination Table (22 files)

| Source (root) | Destination | git status |
|--------------|-------------|------------|
| `CANDIDATE_LIFECYCLE_ANALYTICS_V1_DESIGN_001.md` | `docs/architecture/` | R100 ✓ |
| `EVENT_CATALOG_V1.md` | `docs/architecture/` | R100 ✓ |
| `EVENT_CONSUMER_MATRIX_V1.md` | `docs/architecture/` | R100 ✓ |
| `EVENT_DASHBOARD_STATE_MAP_V1.md` | `docs/architecture/` | R100 ✓ |
| `EVENT_DROP_POLICY_V1.md` | `docs/architecture/` | R100 ✓ |
| `EVENT_PRIORITY_MATRIX_V1.md` | `docs/architecture/` | R100 ✓ |
| `EVENT_REPLAY_ARCHITECTURE_V1.md` | `docs/architecture/` | R100 ✓ |
| `EVENT_SCHEMA_STANDARD_V1.md` | `docs/architecture/` | R100 ✓ |
| `EXIT_IMPLEMENTATION_PLAN_001.md` | `docs/architecture/` | R100 ✓ |
| `PHASE_B_7DAY_EVIDENCE_COLLECTION_GOVERNANCE_001.md` | `docs/architecture/` | R100 ✓ |
| `PHASE_B_DAILY_EVIDENCE_COLLECTOR_DESIGN_001.md` | `docs/architecture/` | R100 ✓ |
| `PHASE_B_DAILY_PIPELINE_MANUAL_RUNNER_PLAN_001.md` | `docs/architecture/` | R100 ✓ |
| `PHASE_B_SCHEMA_ISOLATION_PATCH_PLAN_001.md` | `docs/architecture/` | R100 ✓ |
| `REGIME_ANALYTICS_V1_DESIGN_001.md` | `docs/architecture/` | R100 ✓ |
| `REPLAY_ANALYTICS_V1_DESIGN_001.md` | `docs/architecture/` | R100 ✓ |
| `RUNTIME_EVENT_STREAM_IMPLEMENTATION_PLAN_V2.md` | `docs/architecture/` | R100 ✓ |
| `RUNTIME_EVENT_STREAM_V1.md` | `docs/architecture/` | R100 ✓ |
| `RUNTIME_EVENT_TAXONOMY_V1.md` | `docs/architecture/` | R100 ✓ |
| `RUNTIME_HEARTBEAT_SPEC_V1.md` | `docs/architecture/` | R100 ✓ |
| `SESSION_ANALYTICS_V1_DESIGN_001.md` | `docs/architecture/` | R100 ✓ |
| `SHADOW_TELEMETRY_PHASE_B_DESIGN_001.md` | `docs/architecture/` | R100 ✓ |
| `SHADOW_TELEMETRY_PHASE_B_IMPLEMENTATION_PLAN_001.md` | `docs/architecture/` | R100 ✓ |

---

## git mv Confirmation

All 22 moves used `git mv source docs/architecture/`. Staged as rename type `R100` — meaning file content is 100% identical at source and destination (pure rename, no content modification).

`git diff --cached --name-status | wc -l` = **22** — exactly the expected count, nothing extra.

---

## Scope Verification

| Check | Result |
|-------|--------|
| Total staged entries | 22 |
| All destinations start with `docs/architecture/` | YES ✓ |
| Python files staged | NONE ✓ |
| Dashboard files staged | NONE ✓ |
| Runtime export files staged | NONE ✓ |
| Audit/report/research docs staged | NONE ✓ |
| Root entrypoints moved | NONE ✓ |
| Batch 2 started | NO ✓ |
| Commits made | NONE ✓ |

---

## Confirmation No Code Touched

- [A] `git diff --cached --name-status` shows only `R100` entries with `.md` extensions
- [A] No `.py`, `.ts`, `.tsx`, `.json`, `.csv`, `.lock` files in staged set
- [A] Tracked non-markdown dirty files (`CURRENT_PROJECT_STATUS.md`, `dashboard/`, etc.) unchanged

---

## Remaining Tracked-Root Move Batches

| Batch | Destination | Files | Status |
|-------|-------------|-------|--------|
| T1 | `docs/architecture/` | 22 | **DONE (staged, uncommitted)** |
| T2 | `docs/audits/` | 36 | Next |
| T3 | `docs/reports/` part 1 | ~25 | After T2 |
| T4 | `docs/reports/` part 2 + research | ~24+2 | After T3 |

---

## Final Verdict

```
ROOT_MD_T1_READY_TO_COMMIT
```

**Summary:** 22 tracked root architecture/design files moved to `docs/architecture/` via `git mv`. All staged as `R100` renames — no content changes, pure rename history preserved. Zero scope violations. Ready to commit as a single Type C batch.
