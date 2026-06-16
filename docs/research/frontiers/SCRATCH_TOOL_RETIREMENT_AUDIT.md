# Scratch Tool Retirement Audit

Date: 2026-06-09
Mode: READ ONLY — no code changes, no commits, no pushes, no deletions
Scope: 6 untracked scratch tools in `tools/` with `_` prefix
Non-authorization: this document does not authorize deletion, archiving, or
any filesystem change. Any destructive action requires a separately authorized
write task.

---

## Governing Constraint

`LEGACY_REFERENCE_RETIREMENT_PLAN.md` (2026-06-09) explicitly states:

> *"Safe to delete only under a dedicated cleanup task."*

That reservation applies to `_audit_w21_w22.py` and `_delta_audit.py` directly,
and is adopted here as the governing constraint for all six tools. This audit
produces lifecycle classifications only. Execution requires a future write-authorized
task with explicit scope.

---

## Prior Dispositions (Existing Committed Docs)

Three committed documents already give dispositions. This audit refines them
from commit-scope decisions into lifecycle decisions. All refinements must be
consistent with the reasoning in those documents.

| Document | Disposition | Scope |
|---|---|---|
| `FINAL_N70_WAITING_STATE_HANDOFF.md` | "Leave untracked" — all 6 | Commit-scope only |
| `LEGACY_REFERENCE_RETIREMENT_PLAN.md` (2026-06-09) | `_audit_w21_w22.py`, `_delta_audit.py`: SCRATCH_TOOL; "safe to delete only under a dedicated cleanup task" | Lifecycle (partial) |
| `LEGACY_CSV_DEPENDENCY_AUDIT.md` | `_audit_w21_w22.py`, `_delta_audit.py` Part 2: "safe to leave pinned to `completed_trades_v1_2.csv` as a historical artifact" | Lifecycle (partial) |

"Leave untracked" (FINAL handoff) was a commit-scope ruling, not a permanent
lifecycle verdict. This audit makes the lifecycle classification explicit.

---

## Classification Criterion

For each tool, one question determines whether DELETE is safe:

> **Is this tool's analytical output preserved outside the tool itself in a
> committed document?**

- YES → archiving preserves provenance; DELETE is technically defensible but
  should be deferred if the tool is cited as a source in a committed doc.
- NO → output is destroyed permanently on deletion; ARCHIVE is the floor.
- PARTIAL → the tool that produced the inputs to this tool is being ARCHIVEd,
  so the output is preserved transitively; DELETE is defensible.

Independently: any tool explicitly cited as a data source in a committed
research document stays ARCHIVE (provenance integrity), even if the findings
are fully captured.

---

## Tool Classifications

---

### 1. `tools/_audit_cs_btc.py`

**Purpose:** W21/W22 TREND_DOWN BTC state cross-analysis. Cross-tabulates ETH
trade outcomes against BTC regime, BTC compression_score, and BTC
volatility_score at trade entry time. Contains a hardcoded `trades_data` list
of 19 W21/W22 ETH trades with ETH cs values pre-populated from a prior
`_audit_decision_state.py` run.

**CSV dependency:** None. Reads `runtime/quant_data/decision_log/` JSONL only.

**Committed research coverage:** No dedicated committed doc captures the BTC
state cross-analysis output. The W22_W23_HOLD_TIME_COLLAPSE_AUDIT.md and
TREND_DOWN_FAST_RESOLUTION_AUDIT.md address hold-time patterns but not BTC
regime correlation. The analysis appears to have been an exploratory investigation
not escalated to a committed finding.

**Referenced by committed docs:** No committed doc cites this tool as a data
source. FINAL_N70_WAITING_STATE_HANDOFF.md and N70_DRY_RUN_STATUS.md list it
as a scratch tool to exclude, without attribution to research output.

**Currency:** Hardcoded to W21/W22 (2026-05-19 to 2026-05-29). Not reusable
without editing the `trades_data` list. Point-in-time retrospective.

**Output preservation check:** The BTC cross-tab output is NOT preserved in any
committed doc. Deletion would permanently destroy it.

**Verdict: ARCHIVE**

Rationale: output not preserved elsewhere; hardcoded data cannot be regenerated
from scratch without the prior run state. ARCHIVE is the floor per the criterion.
The fact that no committed research escalated its findings does not make its
output zero-value — it makes it unverifiable without the script.

---

### 2. `tools/_audit_decision_state.py`

**Purpose:** W21/W22 TREND_DOWN ETH decision state lookup. For each trade in a
hardcoded W21/W22 list, finds the closest ETH decision_log record to extract
`market_regime`, `compression_score`, `volatility_score`, and `trend_score` at
entry time. This is the tool that produced the ETH cs values hardcoded in
`_audit_cs_btc.py`'s `trades_data` list.

**CSV dependency:** None. Reads `runtime/quant_data/decision_log/` JSONL only.

**Committed research coverage:** None. Not cited in any committed doc.

**Referenced by committed docs:** Only in FINAL_N70_WAITING_STATE_HANDOFF.md
and N70_DRY_RUN_STATUS.md as a scratch tool to exclude.

**Currency:** Hardcoded to 18 W21/W22 trades (2026-05-19 to 2026-05-29).
Point-in-time retrospective.

**Output preservation check:** PARTIAL. The specific ETH cs values this tool
produced are already hardcoded in `_audit_cs_btc.py`'s `trades_data` list. If
`_audit_cs_btc.py` is ARCHIVEd, this tool's output survives there. The tool
itself is a run-once input-collection script; it served its purpose when it
populated cs_btc's hardcoded data.

**Verdict: DELETE (recommended; future authorized cleanup task)**

Rationale: this tool's analytical output is preserved transitively in
`_audit_cs_btc.py`'s hardcoded `trades_data`. The tool itself carries no
information that is not already captured in cs_btc. Per the criterion, DELETE
is defensible when output is preserved elsewhere. However, this is a
recommendation only — actual deletion requires a separately authorized task.

**Pre-condition:** `_audit_cs_btc.py` must be ARCHIVEd before this tool is
deleted. If cs_btc is deleted instead, this tool's verdict reverts to ARCHIVE.

---

### 3. `tools/_audit_w21_w22.py`

**Purpose:** 14-dimension W21 vs W22 TREND_DOWN causality analysis. Entry
price, exit delta, spread, distance from PTB, expected value, true probability,
confidence, EV quartile, TP/SL distribution, hold time, session hour, quote
age, notional entry, and epoch age. Reads `completed_trades_v1_2.csv`.

**CSV dependency:** `completed_trades_v1_2.csv`. LEGACY_CSV_DEPENDENCY_AUDIT.md
documents 10+ decision-quality columns absent from the canonical export:
`spread`, `confidence`, `expected_value`, `true_probability`, `ev_quartile`,
`tp_hit`, `sl_hit`, `session_hour_utc`, `quote_age_at_submit_ms`,
`notional_entry`, `distance_from_ptb`. If pointed at the canonical export,
the `r['regime'] != 'TREND_DOWN'` filter at line 23 produces 0 rows (no
`regime` field in canonical export — it uses `market_regime`). Cannot be
migrated without a schema-bridge or new JSONL join.

**Committed research coverage:** No dedicated committed doc captures the
14-dimension output. W22_W23_HOLD_TIME_COLLAPSE_AUDIT.md and
TREND_DOWN_FAST_RESOLUTION_AUDIT.md cover W22 hold-time patterns but not
spread, EV, confidence, session, notional, or TP/SL distributions. The causality
analysis data exists only in this tool.

**Referenced by committed docs:**
- LEGACY_CSV_DEPENDENCY_AUDIT.md: MEDIUM risk, classified "safe as historical
  CSV artifact"; "safe to leave pinned to `completed_trades_v1_2.csv`"
- LEGACY_REFERENCE_RETIREMENT_PLAN.md: SCRATCH_TOOL; "safe to delete only under
  a dedicated cleanup task"
- DRIFT_AUDIT_MIGRATION_PLAN.md: "NOT replaceable (10+ decision-quality columns
  absent)"

**Output preservation check:** NO. The 14-dimension analysis is not preserved in
any committed doc. Deletion permanently destroys the only W21/W22 TREND_DOWN
multi-factor causality analysis.

**Verdict: ARCHIVE**

Rationale: output not preserved elsewhere; tool requires `completed_trades_v1_2.csv`
and cannot be migrated to canonical export. LEGACY_CSV_DEPENDENCY_AUDIT.md
explicitly recommends leaving it as a historical artifact. LEGACY_REFERENCE_
RETIREMENT_PLAN.md reserves deletion for a dedicated cleanup task. ARCHIVE
respects both constraints.

---

### 4. `tools/_delta_audit.py`

**Purpose:** Two-part delta extreme protection analysis.
- **Part 1** (JSONL only): 7-day decision log analysis of `delta_extreme`
  blocks — daily breakdown, regime breakdown, quality of blocked candidates,
  counterfactual admission estimate.
- **Part 2** (CSV): ETH YES FC OS historical validation against
  `completed_trades_v1_2.csv` — spread, confidence, decision timing from close,
  EV after spread at entry, split by win/loss.

**CSV dependency:** Part 1: none. Part 2: `completed_trades_v1_2.csv`. Four
decision-quality columns absent from canonical export: `spread`, `confidence`,
`decision_join_ts_delta_from_close_s`, `ev_after_spread`. If pointed at canonical
export, Part 2 produces empty spread/confidence/EV statistics and UNKNOWN regime
breakdown. Part 1 unaffected.

**Committed research coverage:** `DELTA_EXTREME_PROTECTION_AUDIT.md` (committed,
AUDIT_COMPLETE, dated 2026-06-07) captures all key findings from both parts:
54.8% delta_extreme block rate, dual sub-trigger breakdown, counterfactual ~43
admissions, calibration verdict REASONABLE, historical spread/confidence/timing
patterns. The committed doc explicitly states: *"Analysis scripts: `tools/_delta_audit.py`,
`tools/_delta_causal_verify.py`"* — this tool is named as the data source.

**Referenced by committed docs:**
- DELTA_EXTREME_PROTECTION_AUDIT.md: cited as data source (line 9)
- LEGACY_CSV_DEPENDENCY_AUDIT.md: MEDIUM risk, Part 2 "safe as historical CSV artifact"
- LEGACY_REFERENCE_RETIREMENT_PLAN.md: SCRATCH_TOOL; "safe to delete only under a
  dedicated cleanup task"
- DRIFT_AUDIT_MIGRATION_PLAN.md: "NOT replaceable (Part 2)"

**Output preservation check:** YES — findings captured in
DELTA_EXTREME_PROTECTION_AUDIT.md. Deletion would not destroy information, but
would break the provenance claim in that committed doc ("Analysis scripts: …").

**Verdict: ARCHIVE**

Rationale: deletion is technically safe from an information-preservation standpoint,
but the tool is explicitly named as a data source in a committed audit. Archiving
preserves provenance integrity without leaving it as a permanent untracked file.

---

### 5. `tools/_delta_causal_verify.py`

**Purpose:** Causal verification follow-up for delta extreme protection. Three
targeted checks: (A) CLOB circuit open × executable book state cross-tab for
delta_extreme blocks; (B) orderbook snapshot age at decision — executed vs
delta_extreme blocked; (C) sub-trigger breakdown — hard time gate (≤90s) vs
formula EXTREME (>90s).

**CSV dependency:** None. Reads `runtime/quant_data/decision_log/` JSONL only.
Dates hardcoded to 2026-06-01 to 2026-06-06.

**Committed research coverage:** DELTA_EXTREME_PROTECTION_AUDIT.md captures all
key findings: §6 clob_circuit_open cross-verification (91.6% co-occurrence is
temporal, not causal), §7 orderbook age (delta-blocked p50=30ms, executed
p50=282ms), §2 sub-trigger breakdown (24.5% hard block / 75.5% formula EXTREME).
The committed doc's "stale-accumulator artifact" finding (§7f) was produced by
this tool's Section A cross-tab.

**Referenced by committed docs:**
- DELTA_EXTREME_PROTECTION_AUDIT.md: cited as data source (line 9)
- FINAL_N70_WAITING_STATE_HANDOFF.md / N70_DRY_RUN_STATUS.md: scratch tool, exclude

**Output preservation check:** YES — findings captured in
DELTA_EXTREME_PROTECTION_AUDIT.md. Same provenance constraint as `_delta_audit.py`.

**Verdict: ARCHIVE**

Rationale: same as `_delta_audit.py` — tool is named as a data source in a
committed audit. Archive preserves provenance; deletion is information-safe but
breaks the citation.

---

### 6. `tools/_opp_capture_audit.py`

**Purpose:** 24/7 opportunity capture analysis for trade starvation diagnosis.
15-section analysis of 12-hour and 6-hour decision log windows: asset/regime
distribution, admission probe state, block reasons, skip reasons, risk-plan-zero
breakdown, bankroll mode, specific blocker counts (delta_extreme, confidence,
time_unsafe, budget/cooldown, spread), OPENING_SCAN coverage, high-quality missed
candidates, lifecycle phase distribution, execution intent, confidence of blocked
candidates, hourly activity heatmap.

**CSV dependency:** None. Reads `runtime/quant_data/decision_log/` JSONL only.
Dates hardcoded to `['2026-06-06', '2026-06-05']` with `path_today` hardcoded
to `2026-06-06.jsonl` (lines 13, 25). Not directly re-runnable against other
dates without editing.

**Committed research coverage:** No dedicated committed doc captures its specific
output. W22_W23_OPPORTUNITY_SUPPRESSION_AUDIT.md (committed) answers the W23
starvation research question at a high level (volume × hold-time decomposition),
but does not contain this tool's 15-section block-reason breakdown for the
specific 12h/6h windows it analyzed. The tool's findings (what was blocking
during the 2026-06-05/06 window) are not preserved anywhere.

**Referenced by committed docs:** Only in exclusion lists: N70_PREFLIGHT_AUDIT.md,
N70_READINESS_STATUS.md (glob patterns), FINAL_N70_WAITING_STATE_HANDOFF.md,
N70_DRY_RUN_STATUS.md. Not cited as a data source in any committed research doc.

**Output preservation check:** NO — the specific 12h/6h block-reason findings
are not captured in any committed doc. The methodology (the 15-section framework)
is also not documented elsewhere, but is reconstructible from scratch.

**Verdict: ARCHIVE**

Rationale: output not preserved elsewhere; the 15-section analysis framework has
future diagnostic value for trade starvation episodes. The hardcoded dates limit
direct reuse, but the methodology is sound and would require only date-editing to
reapply. An archive note should flag that dates must be updated before re-running.

---

## Summary

| Tool | Lines | CSV dep? | Output preserved? | Cited as source? | Verdict |
|---|---:|---|---|---|---|
| `_audit_cs_btc.py` | 118 | No | **No** | No | **ARCHIVE** |
| `_audit_decision_state.py` | 110 | No | Partial (in cs_btc) | No | **DELETE** ¹ |
| `_audit_w21_w22.py` | 192 | `completed_trades_v1_2.csv` | **No** | Cited by 3 docs | **ARCHIVE** |
| `_delta_audit.py` | 427 | Part 2 only | Yes (DELTA_EXTREME_AUDIT) | Cited as source | **ARCHIVE** |
| `_delta_causal_verify.py` | 185 | No | Yes (DELTA_EXTREME_AUDIT) | Cited as source | **ARCHIVE** |
| `_opp_capture_audit.py` | 276 | No | **No** | No | **ARCHIVE** |

¹ DELETE recommendation is conditional: `_audit_cs_btc.py` must be ARCHIVEd
before `_audit_decision_state.py` is deleted. If cs_btc is deleted, revert
`_audit_decision_state.py` to ARCHIVE.

---

## Recommended Action for Future Authorized Cleanup Task

When a write-authorized cleanup task is opened, the recommended sequence is:

1. **Create `tools/archive/` directory** (or equivalent; no file changes in
   this task).
2. **Move to archive:** `_audit_cs_btc.py`, `_audit_w21_w22.py`,
   `_delta_audit.py`, `_delta_causal_verify.py`, `_opp_capture_audit.py`.
3. **Add archive header** to each moved file noting: date moved, research
   question, data sources, and if dates are hardcoded.
4. **Delete:** `_audit_decision_state.py` (output preserved in cs_btc's
   hardcoded `trades_data`; tool was a one-time input collector).
5. **Add `tools/archive/` to `.gitignore`** or document it as explicitly
   not committed, consistent with scratch-tool convention.
6. **Update LEGACY_REFERENCE_RETIREMENT_PLAN.md** status for `_audit_w21_w22.py`
   and `_delta_audit.py` from SCRATCH_TOOL (untracked) to ARCHIVED.

None of steps 1–6 are authorized by this document.

---

## Governor Note

No runtime, strategy, risk, execution, sizing, or live change is implied.
These are offline read-only retrospective scripts. Their retirement has no
impact on paper mode, live mode, or the N70 evidence accumulation workflow.

*Offline/reporting only. No commits authorized by this document.*
