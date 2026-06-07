# Drift Audit Migration Plan

**Generated:** 2026-06-08
**Status:** READ-ONLY analysis — no code changes, no commits, no runtime changes.
**Task:** Plan the minimal safe migration for `tools/_drift_audit.py` from
`completed_trades_v1_2.csv` to `canonical_regime_enriched_trades_v1.csv`.

**Non-authorization:** This document does not change strategy, risk, execution, sizing,
live behavior, runtime policy, or alerts.

---

## 1. Current Status of `tools/_drift_audit.py`

### 1.1 Git Tracking

**`tools/_drift_audit.py` is UNTRACKED.** It is a scratch tool, never committed.

Confirmed by:

```
git ls-files --error-unmatch tools/_drift_audit.py
# → error: pathspec 'tools/_drift_audit.py' did not match any file(s) known to git
```

Tracking status of the tools directory:

| Pattern | Category | Tracked? |
|---|---|---|
| `eth_yes_fc_os_` prefix (e.g., `eth_yes_fc_os_command_center.py`) | Promoted / production tool | YES — committed, tested |
| `_` prefix (e.g., `_drift_audit.py`, `_delta_audit.py`, `_audit_w21_w22.py`) | Scratch / exploratory | NO — never committed |

`tools/_drift_audit.py` is 187 lines. It is a top-level script body (no importable
functions); it produces regime transition analysis and rolling nc_PF/WR metrics by
printing to stdout. A human analyst reads the stdout and authors
`docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md` from it.

### 1.2 N70 Dependency

`docs/research/N70_EXECUTION_PACKAGE.md` (line 115) mandates:

```
docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md | Mandatory | Update drift, nc_PF, regime composition
```

`docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md` (592 lines) closes with:

```
*Analysis tool: tools/_drift_audit.py*
```

Dependency chain: **N70 → `ETH_YES_FC_OS_DRIFT_AUDIT.md` (mandatory) → `_drift_audit.py` → source CSV**.

The N70 package's input contract is file-agnostic ("Fresh canonical completed-trades
export | Yes if available"). The hardcoded source path is inside `_drift_audit.py` itself.

---

## 2. All Defects Blocking Correct N70 Output

Three defects must be addressed. The schema field-name mismatch (Defect 2) is the primary
migration goal. Defects 3a and 3b are N70-blocking collateral issues revealed during
migration analysis — they are in scope for this plan because a migration that fixes the
source path but leaves these intact produces a confidently-wrong N70 drift document.

### Defect 1 — Stale Source Path (Line 5)

```python
# Current (line 5):
path = 'runtime/research_exports/completed_trades_v1_2.csv'
```

`completed_trades_v1_2.csv` is stale (>59 hours as of audit date; confirmed by
`COMMAND_CENTER_EXPORT_INTEGRATION_AUDIT.md`). It is missing the 2026-06-06 SIDEWAY
qualifying trade that is present in the canonical export (n=61 vs. n=60 after dedup).

Target path: `runtime/research_exports/canonical_regime_enriched_trades_v1.csv`

### Defect 2 — Schema Field Name (Line 27) — PRIMARY MIGRATION TARGET

```python
# Current (line 27):
regime = r.get('regime', 'UNKNOWN')
```

`canonical_regime_enriched_trades_v1.csv` uses `market_regime`; `completed_trades_v1_2.csv`
uses `regime`. When the canonical export is read with `r.get('regime')`, every row returns
`None` → every trade resolves to `'UNKNOWN'`.

**Impact: COMPRESSION exclusion is completely inoperative.**

Line 49:
```python
nc = [t for t in window if t['regime'] != 'COMPRESSION']
```

With all `t['regime'] == 'UNKNOWN'`, every trade passes this filter. nc_PF is computed
on the full 20-trade window, not on non-COMPRESSION trades only — a definitional violation.
Distortion at individual trade indices can exceed ±0.5 PF units (quantified in
`COMMAND_CENTER_EXPORT_INTEGRATION_AUDIT.md` §5, Table).

This is the same root cause and the same fix pattern as Command Center Task 8.

**Fix: `_regime()` dual-field helper (Task 8 pattern):**

```python
def _regime(r: dict) -> str:
    """Read market_regime (canonical export), fall back to regime (legacy CSV), then UNKNOWN."""
    return (r.get('market_regime') or r.get('regime') or 'UNKNOWN').strip().upper()
```

Line 27 becomes:
```python
regime = _regime(r)
```

**Column coverage verification:** `regime` is the ONLY column absent from the canonical
export that `_drift_audit.py` reads. All other fields used by the tool are confirmed
present in `canonical_regime_enriched_trades_v1.csv` header (verified from primary source):

| Column read by `_drift_audit.py` | Present in canonical export? |
|---|---|
| `asset` | YES |
| `side` | YES |
| `canonical_entry_lifecycle_phase` | YES |
| `hold_seconds` | YES |
| `pnl_usdc` | YES |
| `pnl_recomputed` | NO — but used only as fallback to `pnl_usdc` (line 28); fallback path never triggers when `pnl_usdc` is present |
| `trade_result` | YES |
| `outcome_win_loss` | YES |
| `entry_ts` | YES |
| `epoch_start_ts` | YES |
| `regime` | NO → migrated to `market_regime` via `_regime()` helper |

### Defect 3a — Hardcoded Week Boundaries (Line 139) — N70-BLOCKING

```python
# Current (line 139):
w = 'W21' if d <= '2026-05-24' else ('W22' if d <= '2026-05-31' else 'W23')
```

Any trade dated after 2026-05-31 is silently mislabeled `W23`. The 2026-06-06 qualifying
trade already in the canonical export is mislabeled. At N70, there will be trades across
W24, W25, and W26 (or later) — all collapsed to `W23`. The calendar-week breakdown section
of the drift document would be factually wrong.

**Fix:** derive the ISO week label from the date at runtime:

```python
from datetime import date as _date
d_obj = _date.fromisoformat(d)            # d is already an ISO-format date string
iso_year, iso_week, _ = d_obj.isocalendar()
w = f'{iso_year}-W{iso_week:02d}'         # e.g. '2026-W21', '2026-W24' — see Q2 for bare vs. year-qualified format
```

This matches the `P5` gate in `N70_EXECUTION_PACKAGE.md` which already tracks
"3 calendar weeks" and references `2026-W21`, `2026-W22`, `2026-W23`.

### Defect 3b — Hardcoded Phase Segmentation (Line 176) — N70-BLOCKING

```python
# Current (line 176):
for label, lo, hi in [('Early #1-20', 1, 20), ('Mid   #21-40', 21, 40), ('Late  #41-61', 41, 61)]:
```

Buckets are hardcoded to n=61. Trades #62–70 match no bucket and vanish from the phase
segmentation section entirely — the Late phase would undercount by 9 trades at N70, with
no warning.

**Fix:** derive phase boundaries from `n = len(trades)` at runtime:

```python
n = len(trades)
third = n // 3
boundaries = [
    (f'Early #1-{third}',          1,       third),
    (f'Mid   #{third+1}-{2*third}', third+1, 2*third),
    (f'Late  #{2*third+1}-{n}',    2*third+1, n),
]
```

This preserves the equal-thirds structure that matches the current document's section
labels while generalising correctly to any n.

---

## 3. Three Migration Options

### Option A — Patch `_drift_audit.py` in place, leave untracked

Change lines 5, 27, 139, 176 in the existing scratch tool. File remains untracked.

**Pros:** Minimal implementation effort; fastest path to runnable output.
**Cons:** Still untracked — no history, no tests, no regression guard. An accidental edit
or overwrite of `_drift_audit.py` silently reverts the fix. A mandatory N70 governance
artifact rests on an unversioned, untested script with no audit trail.

### Option B — Promote to new tracked tool `tools/eth_yes_fc_os_drift_audit.py` (with full test suite)

Create a new tracked file following the command center promotion pattern. Patch all four
defects. Refactor the script body into a callable `generate_drift_report(trades)` function
to enable unit testing. Write comprehensive tests in
`tests/test_eth_yes_fc_os_drift_audit.py`. Commit both.

**Pros:** Matches project naming convention; fully tracked; full test coverage; durable
for N80/N100.
**Cons:** Substantially more implementation effort. Requires refactoring a flat 187-line
script into an importable function API before tests can be written. Out of scope for a
"minimal safe" migration.

**Note on the command center precedent:** The command center was already tracked and tested
when Task 8 patched it. The command center precedent is not "promote a scratch tool" —
it is "add `_regime()` + validation + tests to an existing tracked tool." Full Option B is
a separately-scoped upgrade.

### Option C — Leave `_drift_audit.py` alone; substitute command center outputs manually

Do nothing to `_drift_audit.py`. Document that the N70 drift report will be manually
assembled from command center panel outputs.

**Not viable.** The command center produces: nc_PF rolling value (Panel C), COMPRESSION
share (Panel C), last-5 regime sequence (Panel C), and regime mix totals (Panel C). It
does NOT produce:

- Regime run table (consecutive runs of the same regime, with lengths and trade indices)
- Calendar week breakdown (WR, PF, net PnL, regime mix per ISO week)
- Phase segmentation (early/mid/late nc_PF, WR, regime counts)
- Per-trade rolling PF and WR series at each index #1–n
- WR trough detection (consecutive-below-threshold periods with min value and index)

These are the primary analytical sections of `ETH_YES_FC_OS_DRIFT_AUDIT.md`. The command
center is not a superset of the drift audit tool and cannot produce the mandatory N70 drift
artifact. Option C is not viable.

---

## 4. Recommended Minimal Safe Path

**Recommendation: Option A + `git add` (patched scratch tool, immediately tracked) with
one targeted regression test file.**

This is not bare Option A (patch and leave untracked) and not full Option B
(from-scratch promoted module). It is the point on the spectrum where the change is
minimal and the result is durable.

### Why not bare Option A

"Safe" requires a regression guard — a test that fires if the schema fix is reverted or
if the n=61 hardcodings reappear. Without `git add` and at least one test, the fix is not
durable: an edit to `_drift_audit.py` from any session could silently regress it, and
nothing would catch it before N70.

### Why not full Option B

The incremental safety gain from refactoring the flat script into a modular API
(required for full test coverage under the command center pattern) is real, but out of
scope for a minimal migration. Extracting importable functions from `_drift_audit.py` requires a modest restructure —
far short of a full module rewrite, but more than a one-liner: the script body must be
wrapped in an `if __name__ == '__main__':` guard (without which `import tools._drift_audit`
executes the entire script at import time, reads the hardcoded path, prints all output,
and hits the fail-loud `sys.exit()` before a test can reach `_regime()`), and the three
computational units must be lifted into module-scope functions accepting their inputs as
parameters: `_regime(r)`, an nc_PF-window function (e.g. `_nc_pf(window)`), and a
week/phase-assignment function. That is the minimum prerequisite for the five tests below.
It is still minimal — it does not require renaming the file, creating a CLI entry point,
or building a `generate_drift_report()` API.

### Implementation checklist (defines scope only; not an authorization to implement)

| Step | Action | Location in `_drift_audit.py` |
|---|---|---|
| 1 | Add `_regime(r)` dual-field helper (reads `market_regime` → `regime` → `UNKNOWN`) | New function near top of file |
| 2 | Change source path to canonical export | Line 5 |
| 3 | Replace `r.get('regime','UNKNOWN')` with `_regime(r)` | Line 27 |
| 4 | Add fail-loud guard: warn + exit if `unknown_regime_rate > 0` after trade list construction | After trade list build loop |
| 5 | Replace hardcoded week boundaries with ISO week arithmetic | Line 139 |
| 6 | Replace hardcoded phase buckets with n-derived equal thirds | Line 176 |
| 6a | Wrap the top-level script body in `if __name__ == '__main__':` | Wraps lines 5–187 |
| 6b | Lift `_regime`, nc_PF-window computation, and week/phase-assignment into module-scope functions accepting inputs as args | Enables import without execution; prerequisite for tests |
| 7 | `git add tools/_drift_audit.py` | — |
| 8 | Write `tests/test_drift_audit_schema.py` with the five tests below | New file |

**Total code change: 6 targeted points in `_drift_audit.py` + 1 new test file.**

The fail-loud guard (Step 4) converts the highest-risk failure mode — silent UNKNOWN
fallback with no signal — into a loud one. When `_drift_audit.py` is run against any
source where `market_regime` is absent (e.g., a stale CSV, a wrong export path), the tool
halts with an explicit error rather than producing a confidently-wrong drift document. One
line converts HIGH-risk silent failure into a caught, actionable error.

---

## 5. Tests Required

Five tests verify N70-correctness. Tests are written against thin importable functions
extracted from `_drift_audit.py` (the `_regime()` helper and the nc_PF computation
extracted into a callable). Fixture pattern: copy `_write_canonical_csv()` from
`tests/test_eth_yes_fc_os_command_center.py` — it writes `market_regime` field rows and
is the canonical fixture helper in this repo.

| # | Test | What it verifies |
|---|---|---|
| T1 | `test_market_regime_maps_zero_unknown` | `_regime()` applied to a batch of `market_regime`-keyed rows → 0 UNKNOWN; directly guards Defect 2 |
| T2 | `test_compression_excluded_from_nc_pf` | Build a 5-trade window: 2 COMPRESSION + 3 non-COMPRESSION via `market_regime`; nc_PF computed using only the 3 non-COMPRESSION trades; COMPRESSION exclusion is operative end-to-end |
| T3 | `test_dual_schema_fallback` | Row with `regime` but no `market_regime` → `_regime()` returns the correct regime value (backward compatibility with legacy CSV manual use) |
| T4 | `test_fail_loud_guard_triggers_on_unknown` | Row with neither `market_regime` nor `regime` → `_regime()` returns `'UNKNOWN'`; fail-loud guard triggers; assert `pytest.raises(SystemExit)` — no silent drift document produced |
| T5 | `test_week_and_phase_correct_at_n70` | Fixture of 70 trades spanning W21–W26 with `market_regime` populated; all trades assigned to correct ISO week label (no W24+ trade mislabeled `W23`); phase segmentation buckets cover all 70 trades with no gaps or double-counting |

T5 is the critical N70-readiness test — it is the test that proves the tool is correct at
the milestone count for which this migration is required. T1 and T2 are the core
COMPRESSION exclusion regression. T3 ensures the fix is backward-compatible with any
legacy-CSV manual run.

---

## 6. Open Questions for Implementation Session

| # | Question | Implication |
|---|---|---|
| Q1 | Should the fail-loud guard (T4) call `sys.exit(1)` or print a warning and continue? | Exit is safer for a governance tool (no partial drift doc written); warning allows partial output for debugging. Recommended: exit with an explicit error message. |
| Q2 | ISO week label format: `'2026-W21'` or `'W21'`? | The current document uses bare `W21` / `W22` / `W23`. The N70 `P5` gate also uses bare week labels. Recommended: keep bare `W{nn}` within a year, e.g. `f'W{iso_week:02d}'`, unless the campaign spans a year boundary. |
| Q3 | Phase boundary strategy: equal thirds (`n//3`) or fixed-20 (`early=20`, `mid=20`, `late=n-40`)? | Equal thirds generalises cleanly across n. Fixed-20 preserves continuity with the existing drift document's section headers. Recommended: equal thirds (avoids "Late #41–70" having 30 trades vs. "Early #1–20" having 20). |
| Q4 | Should `_drift_audit.py` accept a `--path` CLI argument? | CLI arg adds flexibility for future canonical export refreshes with no code edit; hardcoded path with a doc comment is simpler. Recommended: add a positional-or-default CLI arg to allow runtime path override. |

---

## 7. Scope Boundaries: Not in This Plan

| Item | Reason excluded |
|---|---|
| `_audit_w21_w22.py` migration | NOT replaceable (10+ decision-quality columns absent from canonical export). Accepted as-is per `LEGACY_CSV_DEPENDENCY_AUDIT.md`. |
| `_delta_audit.py` Part 2 migration | NOT replaceable (4+ decision-quality columns absent). Accepted as-is. |
| Command Center | ALREADY DONE (Task 8). No action needed. |
| Full Option B promotion of `_drift_audit.py` | Separately scoped. Appropriate for N80/N100 milestone governance upgrade cycle. |
| `ETH_YES_FC_OS_DRIFT_AUDIT.md` regeneration | Execution step, not planning step. Must be done after migration is implemented and verified. |

---

## 8. Relationship to LEGACY_CSV_DEPENDENCY_AUDIT

This plan resolves the single HIGH-risk item from `LEGACY_CSV_DEPENDENCY_AUDIT.md`.
Post-implementation status:

| Item | Risk level | Status |
|---|---|---|
| Command Center | LOW (Task 8 done) | Done |
| N70 Package (spec doc) | LOW* | No action needed |
| `_drift_audit.py` | HIGH — cleanly replaceable | **RESOLVED by this plan (when implemented)** |
| ETH YES FC OS Verification Failure Audit | LOW (static doc) | No action needed |
| Evidence Velocity Dashboard | LOW (no CSV ref) | No action needed |
| `_audit_w21_w22.py` | MEDIUM — NOT replaceable | Accepted as-is |
| `_delta_audit.py` Part 2 | MEDIUM — NOT replaceable | Accepted as-is |
| Future milestone packages | LOW* | No action needed |

---

## Governor Read

This document is offline research evidence only. It must not be wired into runtime
decisions, automated processes, strategy, risk, execution, sizing, or alerts.

All implementation steps defined above require a separate, explicitly authorized
implementation session. No code has been changed, no files have been staged or committed,
and no runtime behavior has been affected by the production of this document.

---

*Provenance: Based on primary source reads of `tools/_drift_audit.py` (187 lines),
`tools/eth_yes_fc_os_command_center.py`, `tests/test_eth_yes_fc_os_command_center.py`,
`docs/research/N70_EXECUTION_PACKAGE.md` (line 115), `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md`
(592 lines), `docs/research/frontiers/LEGACY_CSV_DEPENDENCY_AUDIT.md`, and
`docs/research/frontiers/COMMAND_CENTER_EXPORT_INTEGRATION_AUDIT.md`. Git tracking
confirmed by `git ls-files tools/` and `git ls-files --error-unmatch`. Column coverage
verified against `runtime/research_exports/canonical_regime_enriched_trades_v1.csv` line 1
header. All reads performed 2026-06-07/08.*
