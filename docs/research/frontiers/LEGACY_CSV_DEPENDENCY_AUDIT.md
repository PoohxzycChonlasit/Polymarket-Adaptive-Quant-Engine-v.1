# Legacy CSV Dependency Audit

**Generated:** 2026-06-08
**Status:** READ ONLY — no code changes, no commits, no runtime changes, no pushes.

**Non-authorization:** This audit does not authorize strategy changes, risk changes, execution changes,
runtime filters, config changes, code changes, or live trading. All findings are research governance
evidence only.

---

## Scope

Traces every ETH YES FC OS workflow that references
`runtime/research_exports/completed_trades_v1_2.csv` (the compact canonical trade table produced by
`tools/canonical_trade_table_v1.py`), and compares each against the newer
`runtime/research_exports/canonical_regime_enriched_trades_v1.csv` (the regime-enriched canonical
export integrated by Task 8).

**Coverage:** hardcoded and default-path filename references in active code tools and research docs.
Parameterised `--csv-path` arguments supplied at call time are out of scope.

**Schema root cause:** `completed_trades_v1_2.csv` uses column `regime`.
`canonical_regime_enriched_trades_v1.csv` uses column `market_regime`. Any tool that reads
`r.get('regime')` and is fed the canonical export silently returns UNKNOWN for every row — the same
schema-mismatch bug documented in `COMMAND_CENTER_EXPORT_INTEGRATION_AUDIT.md` and fixed for the
command center in Task 8.

**Canonical export header (verified 2026-06-08, primary source):**
```
export_schema_version, export_generated_at_utc, row_id, canonical_opportunity_key, run_id,
paper_trade_replay_key, condition_id, epoch_start_ts, asset, side, candidate_id, token_id,
entry_ts, exit_ts, hold_seconds, entry_price, exit_price, size, trade_result, outcome_win_loss,
pnl_usdc, exit_reason, trade_open_lifecycle_phase, trade_close_lifecycle_phase,
canonical_entry_lifecycle_phase, canonical_entry_lifecycle_source, market_regime, trend_regime,
volatility_regime, regime_reason, regime_source, regime_join_key, regime_join_confidence,
regime_decision_ts, regime_decision_delta_from_entry_s, duplicate_opportunity_flag,
duplicate_opportunity_count, canonical_retained_flag, row_quality, validation_notes
```

Absent from canonical export (confirmed by header): `spread`, `confidence`, `expected_value`,
`true_probability`, `ev_quartile`, `tp_hit`, `sl_hit`, `session_hour_utc`,
`quote_age_at_submit_ms`, `notional_entry`, `distance_from_ptb`,
`decision_join_ts_delta_from_close_s`, `ev_after_spread`, `pnl_recomputed`, `regime`.

---

## 8-Workflow Summary Table

| # | Workflow | File | Purpose | Required? (CSV needed for correct output) | Replaceable by canonical export? | Risk |
|---|---|---|---|---|---|---|
| 1 | Command Center | `tools/eth_yes_fc_os_command_center.py` | Daily ops: gates, nc_PF, regime sequence | NO — Task 8 done; canonical export now preferred source | ALREADY DONE | LOW |
| 2 | N70 Package | `docs/research/N70_EXECUTION_PACKAGE.md` | Milestone governance spec | N/A — spec doc (no file reads) | N/A | LOW* |
| 3 | Drift Audit | `tools/_drift_audit.py` | nc_PF, regime mix, rolling WR/PF for drift monitoring | YES until fixed; NO after `_regime()` fix | YES — `regime`→`market_regime` rename only | **HIGH** |
| 4 | Verification Failure Audit | `docs/research/frontiers/ETH_YES_FC_OS_VERIFICATION_FAILURE_AUDIT.md` | Historical analysis of criteria failures | N/A — static doc (no file reads) | N/A | LOW |
| 5 | Evidence Velocity Dashboard | `docs/research/evidence_velocity_dashboard.md` | Opportunity production velocity tracking | N/A — no CSV reference | N/A | LOW |
| 6 | Campaign Tooling | `tools/_audit_w21_w22.py` | W21 vs W22 TREND_DOWN causality retrospective | YES — 10+ decision-quality columns absent from canonical export | NOT replaceable | MEDIUM |
| 7 | Report Generators | `tools/_delta_audit.py` (Part 2) | ETH YES FC OS delta-risk historical validation | YES (Part 2) — 4 decision-quality columns absent; NO (Part 1, decision log) | NOT replaceable (Part 2) | MEDIUM |
| 8 | Future Milestone Packages | `docs/research/N70_EXECUTION_PACKAGE.md` | N70/N80/N100 snapshot governance | N/A — spec doc (no file reads) | N/A | LOW* |

\* N70 Package and future milestones have no direct CSV dependency, but mandate regenerating
`ETH_YES_FC_OS_DRIFT_AUDIT.md` via `tools/_drift_audit.py` — which is the HIGH-risk item 3 above.
The indirect dependency is real.

---

## Per-Workflow Detail

### 1. Command Center — ALREADY UPGRADED (Task 8)

**File:** `tools/eth_yes_fc_os_command_center.py`
**Hardcoded path:** None after Task 8. `DEFAULT_CANONICAL_EXPORT_PATH` now points to
`canonical_regime_enriched_trades_v1.csv`. `completed_trades_v1_2.csv` is the final fallback only.

**What was done:** Task 8 implemented a 3-tier source priority (canonical_export → trade_journal →
csv) and added a `_regime()` helper that reads `market_regime` first, falls back to `regime`, then
`UNKNOWN`. The `--canonical-regime-export` CLI flag is wired. `_validate_canonical_export()` checks
for `market_regime` column presence and qualifying ETH rows.

**End-to-end verification (2026-06-07):** All 6 ground-truth values matched the canonical export
exactly: n=61, unknown_regime_rate=0.0%, nc_PF=2.707, COMPRESSION=21, TREND_DOWN=18, SIDEWAY=15,
TREND_UP=7. K3 preserved (n_BTC=11, WR=27.3%) because the export contains 494 total rows including
BTC qualifying rows.

**Risk:** LOW. The schema-mismatch bug is fixed.

---

### 2. N70 Package — NO DIRECT DEPENDENCY

**File:** `docs/research/N70_EXECUTION_PACKAGE.md`
**grep result:** `completed_trades_v1_2` — no match.

**Content check:** Primary inputs table reads:

> "Fresh canonical completed-trades export | Yes if available | Compact metric computation"

File-agnostic. The N70 package accepts either source.

**Indirect dependency:** N70 mandates regenerating `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md`
(required output, line 115 of N70 package). That document is generated by `tools/_drift_audit.py`,
which is hardcoded to `completed_trades_v1_2.csv` (item 3 below). This is the real risk vector: a
grep-only audit misses it.

**Risk:** LOW for the package itself. The indirect dependency via the drift audit tool is HIGH.

---

### 3. Drift Audit — HARDCODED, HIGH RISK

**File:** `tools/_drift_audit.py`
**Line 5:** `path = 'runtime/research_exports/completed_trades_v1_2.csv'`
**Line 27:** `regime = r.get('regime','UNKNOWN')`

**Column diff against canonical export:**

| Column read by `_drift_audit.py` | In canonical export? | Note |
|---|---|---|
| `asset` | ✓ YES | — |
| `side` | ✓ YES | — |
| `canonical_entry_lifecycle_phase` | ✓ YES | — |
| `hold_seconds` | ✓ YES | — |
| `pnl_usdc` | ✓ YES | — |
| `pnl_recomputed` | ✗ Absent (fallback only) | `pnl_usdc` is present; fallback path unused |
| `trade_result` | ✓ YES | — |
| `outcome_win_loss` | ✓ YES | — |
| `entry_ts` | ✓ YES | — |
| `epoch_start_ts` | ✓ YES | — |
| **`regime`** | ✗ Absent | Export uses `market_regime` — rename required |

**Assessment:** All required data is present in the canonical export. The only mismatch is the
`regime` vs. `market_regime` field name — a pure rename, not a missing column.

**Risk if path-swapped without fix:** Identical to the pre-Task 8 command center bug.
`r.get('regime','UNKNOWN')` returns UNKNOWN for every row. COMPRESSION is never excluded from
nc_PF windows. Regime run table, regime stats, and calendar week breakdown all show UNKNOWN.
Per the quantified distortion table in `COMMAND_CENTER_EXPORT_INTEGRATION_AUDIT.md §5`, nc_PF
distortion can exceed ±0.5 PF units in rolling windows — direction is non-deterministic.

**Why this is HIGH:** `_drift_audit.py` is the active ops tool that generates
`ETH_YES_FC_OS_DRIFT_AUDIT.md`, a mandatory N70 milestone output. Its regime outputs (nc_PF,
regime mix, COMPRESSION share) directly feed the N70 governance decision.

**Replaceable:** YES — same approach as Task 8. Required changes:
1. Change `path = 'runtime/research_exports/completed_trades_v1_2.csv'` to the canonical export path.
2. Add a `_regime(row)` helper: reads `market_regime` first, falls back to `regime`, then `UNKNOWN`.
3. Replace `r.get('regime','UNKNOWN')` at line 27 with `_regime(r)`.

No other column substitutions needed. This is a minimal targeted fix.

**Provenance note:** After migration, `ETH_YES_FC_OS_DRIFT_AUDIT.md` would reflect:
source=canonical_regime_enriched_trades_v1.csv, n=61, SIDEWAY=15 (was 14 — one additional
2026-06-06 qualifying trade not in the stale CSV).

---

### 4. Verification Failure Audit — NO DIRECT DEPENDENCY

**File:** `docs/research/frontiers/ETH_YES_FC_OS_VERIFICATION_FAILURE_AUDIT.md`
**grep result:** `completed_trades_v1_2` — no match.

**Content check:** References "CSV vs. dedup" WR values (e.g., "57.4% (CSV) / 58.1% (dedup)") as
historical comparison labels — not a live file dependency. No hardcoded path. No Python code reads.

**Risk:** LOW. Static provenance label only.

---

### 5. Evidence Velocity Dashboard — NO DEPENDENCY

**File:** `docs/research/evidence_velocity_dashboard.md`
**grep result:** `completed_trades_v1_2` — no match.

**Related doc note:** `docs/research/frontiers/EVIDENCE_VELOCITY_ROOT_CAUSE_AUDIT.md` (a separate
document) references `completed_trades_v1_2.csv` at full n=440 scope (all completed trades, not
the ETH YES FC OS subset). That usage is not replaceable by the canonical regime export, which
covers only the regime-enriched subset. It is a static research artifact, not regenerated in
normal ops.

**Risk:** LOW for the dashboard. The root-cause audit doc is a static historical artifact.

---

### 6. Campaign Tooling — HARDCODED, NOT REPLACEABLE

**File:** `tools/_audit_w21_w22.py`
**Line 7:** `with open('runtime/research_exports/completed_trades_v1_2.csv', newline='', encoding='utf-8') as f:`
**Line 23:** `if r['regime'] != 'TREND_DOWN': return False` — hard field reference, no fallback.

**Column diff against canonical export:**

| Column read by `_audit_w21_w22.py` | In canonical export? | Note |
|---|---|---|
| `asset` | ✓ YES | — |
| `side` | ✓ YES | — |
| `canonical_entry_lifecycle_phase` | ✓ YES | — |
| `hold_seconds` | ✓ YES | — |
| `entry_ts` | ✓ YES | — |
| `epoch_start_ts` | ✓ YES | — |
| `pnl_usdc` | ✓ YES | — |
| `entry_price` | ✓ YES | — |
| `exit_price` | ✓ YES | — |
| **`regime`** | ✗ Absent | Export uses `market_regime`; line 23 filter would return 0 rows |
| **`spread`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`distance_from_ptb`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`expected_value`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`true_probability`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`ev_quartile`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`tp_hit`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`sl_hit`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`session_hour_utc`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`quote_age_at_submit_ms`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`notional_entry`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`confidence`** | ✗ Absent | Decision-quality field from JSONL pipeline |

**Assessment:** 10+ columns are absent from the canonical export. These decision-quality fields
(`spread`, `confidence`, `expected_value`, `true_probability`, `ev_quartile`, `tp_hit`, `sl_hit`,
`session_hour_utc`, `quote_age_at_submit_ms`, `notional_entry`, `distance_from_ptb`) are produced
by `canonical_trade_table_v1.py` from decision-log JSONL. The regime enrichment process does not
carry them. There is no path to replace this tool's CSV source with the canonical export without
losing its core analytic output.

**Nature of the tool:** W21 vs W22 TREND_DOWN causality analysis — a completed point-in-time
retrospective. Not a routine ops tool. Safe to leave pinned to `completed_trades_v1_2.csv` as a
historical artifact. If re-run, `completed_trades_v1_2.csv` must be freshly regenerated from JSONL
first using `tools/canonical_trade_table_v1.py`.

**Risk:** MEDIUM. Not actively re-run under normal ops. If mistakenly pointed at the canonical
export, the `r['regime'] != 'TREND_DOWN'` filter at line 23 returns 0 rows (no `regime` field
→ KeyError or empty result), producing an empty or crashing analysis rather than silently wrong
numbers.

---

### 7. Report Generators — HARDCODED, PARTIAL REPLACEMENT ONLY

**File (consumer):** `tools/_delta_audit.py`
**Line 13:** `CSV_PATH = 'runtime/research_exports/completed_trades_v1_2.csv'`

**File (producer — out of scope):** `tools/canonical_trade_table_v1.py`
**Line 22:** `CSV_V1_2_NAME = "completed_trades_v1_2.csv"` — this file **generates** the CSV from
raw JSONL. It is the upstream producer, not a consumer. It is not a legacy dependency to replace.

**`_delta_audit.py` structure:**
- **Part 1:** reads `runtime/quant_data/decision_log/` JSONL for decision-log analysis. **No CSV
  dependency.** Part 1 is unaffected regardless of what happens to the CSV.
- **Part 2 (line 279+):** reads ETH YES FC OS trades from `CSV_PATH` for historical validation.
  Uses `r.get('regime','UNK')` for regime breakdown (line 356).

**Column diff against canonical export (Part 2 only):**

| Column read by `_delta_audit.py` Part 2 | In canonical export? | Note |
|---|---|---|
| `asset` | ✓ YES | — |
| `side` | ✓ YES | — |
| `canonical_entry_lifecycle_phase` | ✓ YES | — |
| `hold_seconds` | ✓ YES | — |
| `trade_result` | ✓ YES | — |
| `outcome_win_loss` | ✓ YES | — |
| `pnl_usdc` | ✓ YES | — |
| `pnl_recomputed` | ✗ Absent (fallback only) | `pnl_usdc` present; fallback path unused |
| **`spread`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`confidence`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`decision_join_ts_delta_from_close_s`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`ev_after_spread`** | ✗ Absent | Decision-quality field from JSONL pipeline |
| **`regime`** | ✗ Absent | Export uses `market_regime` — rename required for regime breakdown |

**Assessment:** 4 decision-quality columns are absent from the canonical export. These are the
primary analytic output of Part 2: spread at entry, confidence at entry, decision timing from close
(time-pressure delta proxy), and EV after spread. The canonical export cannot supply them.

**Nature of the tool:** Delta Extreme Protection retrospective analysis. Completed report generator.
Not routinely re-run. If re-run, `completed_trades_v1_2.csv` must be freshly regenerated first.

**Risk:** MEDIUM. Part 2 would silently produce empty spread/confidence/EV/timing statistics if
pointed at the canonical export (all `flt(r.get('spread'))` calls return None → sections print
nothing or show n=0). The regime breakdown would show all UNKNOWN. Part 1 is unaffected.

---

### 8. Future Milestone Packages — NO DIRECT DEPENDENCY

Same finding as item 2. Future milestone packages (N80, N100) are modelled on
`docs/research/N70_EXECUTION_PACKAGE.md` and inherit its file-agnostic input contract.

**Indirect dependency:** Any future milestone package that mandates regenerating
`ETH_YES_FC_OS_DRIFT_AUDIT.md` inherits the HIGH-risk dependency on `tools/_drift_audit.py`
(item 3). The fix for item 3 must precede or accompany the first N70/N80/N100 drift audit
regeneration using the canonical export.

**Risk:** LOW for the package specs. Indirect dependency on the drift audit tool is HIGH.

---

## Column-Diff Summary: Why Only Drift Audit Is Cleanly Replaceable

The canonical regime export (`canonical_regime_enriched_trades_v1.csv`) carries:
trade-outcome fields (`pnl_usdc`, `trade_result`, `outcome_win_loss`, `entry_price`, `exit_price`,
`hold_seconds`) and regime-join fields (`market_regime`, `trend_regime`, `volatility_regime`,
`regime_reason`, `regime_source`, `regime_join_confidence`, `regime_decision_delta_from_entry_s`).

It does **not** carry decision-quality fields produced by the JSONL pipeline in
`canonical_trade_table_v1.py`: `spread`, `confidence`, `expected_value`, `true_probability`,
`ev_quartile`, `tp_hit`, `sl_hit`, `session_hour_utc`, `quote_age_at_submit_ms`, `notional_entry`,
`distance_from_ptb`, `decision_join_ts_delta_from_close_s`, `ev_after_spread`.

`tools/_drift_audit.py` needs only the trade-outcome and regime fields → cleanly replaceable.

`tools/_audit_w21_w22.py` and `tools/_delta_audit.py` Part 2 need decision-quality fields →
not replaceable by the canonical export. They must remain pinned to `completed_trades_v1_2.csv`.

---

## Risk Summary

| Risk | Tool/File | Reason | Action required |
|---|---|---|---|
| **HIGH** | `tools/_drift_audit.py` | Mandatory N70 ops tool; nc_PF COMPRESSION-exclusion inoperative if schema-mismatched; cleanly fixable | Add `_regime()` helper + path swap (same fix as Task 8) — separate approved implementation phase |
| MEDIUM | `tools/_audit_w21_w22.py` | Completed retrospective; 10+ missing columns; safe as historical CSV artifact | Leave pinned to CSV; note freshly-regenerated CSV required if re-run |
| MEDIUM | `tools/_delta_audit.py` (Part 2) | Completed retrospective; 4 missing decision-quality columns; Part 1 CSV-independent | Leave Part 2 pinned to CSV; note freshly-regenerated CSV required if re-run |
| LOW | All others | Already fixed, static docs, file-agnostic specs, or no dependency | No action required |

---

## Static Report Provenance References (Not Code)

These docs reference `completed_trades_v1_2.csv` in provenance metadata only. They are static
research artifacts, not live dependencies. Re-running their generator tools would update the
source references automatically.

| Doc | Reference type | Notes |
|---|---|---|
| `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md` | Source header + footer | n=61, SIDEWAY=14 (CSV era); after drift audit migration: n=61, SIDEWAY=15 |
| `docs/research/frontiers/EVIDENCE_VELOCITY_ROOT_CAUSE_AUDIT.md` | Sources declaration (n=440 full scope) | Not replaceable — uses full completed-trades dataset, not ETH subset |
| `docs/research/frontiers/DELTA_EXTREME_PROTECTION_AUDIT.md` | Historical source declaration | Generated by `_delta_audit.py` Part 2 |
| `docs/research/CANONICAL_REGIME_EXPORT_SPEC.md` | Reference table entry; labeled "Reference only unless freshly regenerated" | Design doc |
| `docs/research/REGIME_ENRICHMENT_SOURCE_AUDIT.md` | Source audit table entry | Notes CSV has `regime` column but is stale |
| `docs/research/CANONICAL_N61_REPRODUCIBILITY_AUDIT.md` | Cross-check source | Count reproducibility only; not regime |
| `docs/research/frontiers/COMMAND_CENTER_EXPORT_INTEGRATION_AUDIT.md` | Documents pre-Task 8 bug | Historical; superseded by Task 8 |
| `docs/research/frontiers/ETH_YES_FC_OS_COMMAND_CENTER_IMPLEMENTATION_PLAN.md` | Pre-Task 8 plan doc | Historical; superseded by Task 8 |

---

*Audit covers hardcoded and default-path filename references only. Scope: eight ETH YES FC OS
workflow areas checked 2026-06-07/08. No code changes made. No commits. No pushes.*
