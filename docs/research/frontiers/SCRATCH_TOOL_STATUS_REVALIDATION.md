# Scratch Tool Status Revalidation

Date: 2026-06-09
Mode: READ ONLY — no code changes, no commits, no deletions, no archiving
Purpose: Cross-check current working tree against SCRATCH_TOOL_RETIREMENT_AUDIT.md
  (same session, 2026-06-09) — confirm classifications are current and no
  anomalies have emerged since the audit was written.
Non-authorization: this document does not authorize any filesystem change,
  archiving, deletion, or commit.

---

## Verdict

**CONFIRMED** — all 6 scratch tools remain present and untracked. Classifications
from SCRATCH_TOOL_RETIREMENT_AUDIT.md (2026-06-09) are current and accurate.
No new scratch tools detected. No committed scratch tools found. No anomalies.

One critical exclusion confirmed: `tools/_drift_audit.py` is **not** a scratch
tool. See §3 below.

---

## 1. Glob Match Scope

Phase 2 review scope per task definition:
- `tools/*audit*.py`
- `tools/*delta*.py`
- `tools/*opp*.py`

Git status at time of this review (same session as SCRATCH_TOOL_RETIREMENT_AUDIT.md):

```
?? tools/_audit_cs_btc.py
?? tools/_audit_decision_state.py
?? tools/_audit_w21_w22.py
?? tools/_delta_audit.py
?? tools/_delta_causal_verify.py
?? tools/_opp_capture_audit.py
```

All 6 tools that were untracked when the retirement audit was written remain
untracked. No status changes since that audit.

---

## 2. Tool-by-Tool Revalidation

| Tool | Git status | Retirement classification | Revalidation |
|---|---|---|---|
| `tools/_audit_cs_btc.py` | `??` untracked | **ARCHIVE** | ✅ CONFIRMED |
| `tools/_audit_decision_state.py` | `??` untracked | **DELETE** (recommended; conditional) | ✅ CONFIRMED |
| `tools/_audit_w21_w22.py` | `??` untracked | **ARCHIVE** | ✅ CONFIRMED |
| `tools/_delta_audit.py` | `??` untracked | **ARCHIVE** | ✅ CONFIRMED |
| `tools/_delta_causal_verify.py` | `??` untracked | **ARCHIVE** | ✅ CONFIRMED |
| `tools/_opp_capture_audit.py` | `??` untracked | **ARCHIVE** | ✅ CONFIRMED |

Recall: `_audit_decision_state.py` DELETE is conditional on `_audit_cs_btc.py`
being ARCHIVEd first. If `_audit_cs_btc.py` were deleted instead, the verdict
for `_audit_decision_state.py` reverts to ARCHIVE. Neither action is authorized
by this or the retirement audit document.

---

## 3. Critical Exclusion: `tools/_drift_audit.py`

The glob pattern `tools/*audit*.py` also matches `tools/_drift_audit.py`.

**This file is NOT a scratch tool.**

| Property | Value |
|---|---|
| Git status | Tracked (committed, unmodified — **not** in `??` list) |
| Classification | LEGACY_FALLBACK active tool (`LEGACY_REFERENCE_RETIREMENT_PLAN.md`) |
| Used by | Daily N70 workflow (`_drift_audit.py --path canonical_csv`) |
| CSV fallback | `tools/_drift_audit.py:4,44` references `completed_trades_v1_2.csv` as a fallback default; explicit `--path` bypasses it |
| Test coverage | `tests/test_drift_audit.py` — 22 tests passing (N70_DRY_RUN_STATUS.md, same session) |
| Retirement scope | **EXCLUDED** — active committed tool; retirement scope is untracked `_`-prefix scratch tools only |

Excluding `_drift_audit.py` from cleanup is mandatory. Archiving or deleting
this file would break the daily drift monitoring workflow and the N70 execution
pipeline.

This exclusion is also consistent with `N70_PREFLIGHT_AUDIT.md` (2026-06-08):

> *"If scratch tools under `tools/_audit*.py`, `tools/_delta*.py`, or
> `tools/_opp_capture_audit.py` appear, exclude them from commits."*

The preflight's exclusion language targets untracked scratch tools only —
`_drift_audit.py` was already committed at time of that ruling.

---

## 4. No New Scratch Tools

The retirement audit identified exactly 6 untracked scratch tools. The current
working tree shows no additional `??` files in `tools/` that match the audit
glob patterns beyond those 6.

Additionally confirmed: no scratch tool has been committed into the tracked
tree since the retirement audit was written. All 6 remain in `??` (untracked)
state.

---

## 5. Authorization Status

The retirement audit's recommended cleanup sequence (6 steps: create archive dir,
move 5 ARCHIVE tools, add headers, delete `_audit_decision_state.py`, update
`.gitignore`, update `LEGACY_REFERENCE_RETIREMENT_PLAN.md`) is:

- **Not yet authorized** — no separately scoped write task has been opened
- **Not yet started** — all 6 tools remain in their original untracked state
- **Governing constraint:** `LEGACY_REFERENCE_RETIREMENT_PLAN.md` (2026-06-09):
  *"Safe to delete only under a dedicated cleanup task."*

This revalidation does not advance the cleanup authorization. It confirms only
that the inventory and classifications from the retirement audit are current.

---

## Summary

| Check | Result |
|---|---|
| All 6 scratch tools present | ✅ CONFIRMED — all `??` untracked |
| No new untracked scratch tools | ✅ CONFIRMED |
| No committed scratch tools | ✅ CONFIRMED |
| `_drift_audit.py` correctly excluded | ✅ CONFIRMED — tracked, active, not in scope |
| Retirement audit classifications current | ✅ CONFIRMED — no status changes |
| Cleanup authorized | ❌ NO — dedicated write task required |

---

*Offline/reporting only. No code changes, no commits, no archiving authorized.*
