# ROOT_MD_TRACKED_BATCH_T1_COMMIT_REPORT_001

**Date:** 2026-06-26  
**Task:** ROOT_MD_TRACKED_BATCH_T1_COMMIT_001  
**Task Class:** 3 (DOCS_HOUSEKEEPING) — Type C commit

---

## Commit Identity

| Field | Value |
|-------|-------|
| SHA | `95c35ab` |
| Message | `docs: batch T1 move tracked architecture docs` |
| Branch | `main` |

---

## File Count

| Metric | Count |
|--------|-------|
| Total files in commit | 23 |
| R100 renames to `docs/architecture/` | 22 |
| Batch report added (`ROOT_MD_TRACKED_BATCH_T1_001.md`) | 1 |
| Insertions | +94 (report only — renames add 0 net lines) |

---

## R100 Rename Preservation

All 22 moves committed as `rename ... (100%)` — git preserves full file history. `git log --follow docs/architecture/<file>` will show the complete history including commits made when the file was in root. This is the key advantage of `git mv` over `mv`.

---

## Staged Path Verification

Outside-scope check (`grep -v "^docs/architecture/" | grep -v "^ROOT_MD_TRACKED_BATCH_T1_001.md"`) returned zero lines. Every staged entry was either a `docs/architecture/` rename or the batch report.

---

## Confirmations

| Check | Result |
|-------|--------|
| R100 renames committed | 22 ✓ |
| All destinations under `docs/architecture/` | YES ✓ |
| Code files committed | NONE ✓ |
| Dashboard files committed | NONE ✓ |
| Runtime exports committed | NONE ✓ |
| Audit/report/research docs staged | NONE ✓ |
| Root entrypoints moved | NONE ✓ |
| Batch 2 started | NO ✓ |
| Tracked dirty set disturbed | NO ✓ |

---

## Git Log (Top 6)

```
95c35ab docs: batch T1 move tracked architecture docs   ← new
3762bcd docs: add final root markdown inventory
fdf1e73 docs: batch R7 route remaining markdown documents
8582a3b docs: batch R4 route report documents
7dcc6fd docs: batch R2 route audit documents
f70a737 docs: batch R1 route architecture documents
```

---

## Remaining Tracked-Root Move Batches

| Batch | Destination | Files | Status |
|-------|-------------|-------|--------|
| T1 | `docs/architecture/` | 22 | **COMMITTED** ✓ `95c35ab` |
| T2 | `docs/audits/` | 36 | Next |
| T3 | `docs/reports/` part 1 | ~25 | After T2 |
| T4 | `docs/reports/` part 2 + research | ~24+2 | After T3 |

---

## Next Recommended Task

**`ROOT_MD_TRACKED_BATCH_T2_001`** — Class 3, Role 24 (Repository Librarian)  
Move 36 tracked audit files from root to `docs/audits/` using `git mv`.

Files listed in `ROOT_MD_FINAL_INVENTORY_001.md` Section 4.

---

## Final Verdict

```
ROOT_MD_T1_COMMITTED
```

**Summary:** Commit `95c35ab` contains 22 `R100` tracked-file renames to `docs/architecture/` plus the T1 batch report. Full git rename history preserved for all 22 files. No code committed. Tracked dirty set unchanged. Batch 2 not started.
