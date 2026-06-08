# N62 vs N63 Reconciliation Audit

Generated: 2026-06-08
Source: canonical_regime_enriched_trades_v1.csv
Mode: READ ONLY — offline/reporting only. No code changes. No commits. No pushes.
Non-authorization: this document does not change strategy, risk, execution, sizing, live behavior, runtime policy, or alerts.

---

## 1. The Question

The daily evidence run (2026-06-08) produced two different qualifying-trade counts:

| Tool | n reported |
|---|---:|
| `canonical_regime_export.py` | 62 |
| `eth_yes_fc_os_command_center.py` | 62 |
| `tools/_drift_audit.py` | 63 |

This audit traces the exact row counts through each pipeline step, identifies the responsible row(s), and determines which count is authoritative.

---

## 2. Source File

```
runtime/research_exports/canonical_regime_enriched_trades_v1.csv
Total rows in file: 502
```

The CSV contains ALL trade rows (ETH + BTC, all sides, all lifecycle phases). Both the command center and the drift audit read this same file and apply their own filters independently.

---

## 3. Filter Pipeline Trace

### Step-by-step counts (both pipelines)

| Filter step | Export (canonical) | Drift Audit |
|---|---:|---:|
| Total rows in CSV | 502 | 502 |
| asset = ETH | 369 | 369 |
| + side = YES | 152 | 152 |
| + OPENING_SCAN in canonical_entry_lifecycle_phase | 121 | 121 |
| + hold_seconds > 15 | **63** | **63** |
| + outcome quality gate (see §4) | 63 | — (not applied) |
| + canonical_retained_flag = true | **62** | — (not applied) |
| **Final n** | **62** | **63** |

Both pipelines are **identical through `hold_seconds > 15`** — they produce the same 63-row working set. The divergence occurs at the deduplication step, not before.

---

## 4. Filter Definitions Side-by-Side

### Export pipeline — `_cell_qualifies()` + deduplication flag

```python
# canonical_regime_export.py  _cell_qualifies()
return (
    row.get("asset") == "ETH"
    and row.get("side") == "YES"
    and "OPENING_SCAN" in str(row.get("canonical_entry_lifecycle_phase") or "")
    and hold > 15                                                          # float, strict >
    and (
        row.get("trade_result") in {"TP", "SL"}                           # outcome quality gate
        or row.get("pnl_usdc") not in {None, ""}
    )
)
# After _cell_qualifies: additionally requires
# row["canonical_retained_flag"] == "true"
```

The outcome quality gate (`trade_result` or `pnl_usdc`) applies 0 additional exclusions — all 63 rows pass it. The only reduction from 63 to 62 is `canonical_retained_flag`.

### Drift audit pipeline — `tools/_drift_audit.py`

```python
# _drift_audit.py  __main__ filter loop
if r.get('asset', '') != 'ETH':                              continue
if r.get('side', '') != 'YES':                               continue
if 'OPENING_SCAN' not in r.get('canonical_entry_lifecycle_phase', ''): continue
hs = _flt(r.get('hold_seconds', ''))
if hs is None or hs <= 15:                                   continue
# No outcome quality gate check.
# No canonical_retained_flag check.
```

The drift audit applies no deduplication and no outcome quality gate. It counts all 63 rows that pass the four core filters.

---

## 5. Outcome Quality Gate — Non-Factor Confirmed

All 63 hold-filtered rows have either `trade_result in {TP, SL}` or non-empty `pnl_usdc`. The outcome quality gate reduces the count by **zero**.

```
Rows failing outcome_quality_gate: 0
```

The outcome quality gate is not a source of divergence. It is irrelevant to this discrepancy.

---

## 6. The Exact Duplicate Row

Among the 63 qualifying rows, one `canonical_opportunity_key` appears **twice** — two bot runs executed the same market opportunity within 4 seconds. The export marks one row `canonical_retained_flag = false` and excludes it; the drift audit includes both.

### Duplicate pair

```
canonical_opportunity_key:
  0xb50b55a177d8aa82b1d52cfb4c37cb029bf3742ceccfeb1686ebff0ede26c0fd|1779967500|ETH|YES|candidate_b6eb567d95f1
```

| Field | Row 1 (RETAINED) | Row 2 (EXCLUDED) |
|---|---|---|
| row_id | cre_ed07bc90a8c3d5a0328c | cre_91c9e71be369d0fbbdc2 |
| run_id | 20260528T112210Z_29912_e98efd38 | 20260528T110330Z_21492_318145bc |
| entry_ts | 2026-05-28T11:25:13.407255Z | 2026-05-28T11:25:17.808939Z |
| exit_ts | 2026-05-28T11:26:02.262224Z | 2026-05-28T11:26:12.512224Z |
| hold_seconds | 49 | 55 |
| trade_result | TP | TP |
| pnl_usdc | +0.005657 | +0.010044 |
| market_regime | TREND_DOWN | TREND_DOWN |
| canonical_retained_flag | **true** | **false** |
| duplicate_opportunity_flag | true | true |
| duplicate_opportunity_count | 2 | 2 |
| regime_join_confidence | DIRECT | DIRECT |
| canonical_entry_lifecycle_phase | OPENING_SCAN | OPENING_SCAN |

### Why this opportunity fired twice

Two separate bot runs (`run_id` differs, spawned ~20 minutes apart: `T112210Z` and `T110330Z`) both opened and closed a paper trade for the same opportunity. Same `condition_id`, same `epoch_start_ts`, same `asset`, same `side`, same `candidate_id`.

### Deduplication strategy (export)

`_mark_duplicates()` in `canonical_regime_export.py` groups rows by `canonical_opportunity_key`, sorts by `exit_ts` ascending, and marks only the first row `canonical_retained_flag = true`. Row 1 (exit_ts 11:26:02) is retained; Row 2 (exit_ts 11:26:12) is excluded.

### Why the drift audit includes Row 2

`tools/_drift_audit.py` reads `canonical_retained_flag` from the CSV (the column exists) but **never filters on it**. Both rows pass the four-filter chain (ETH / YES / OPENING_SCAN / hold > 15). Both are counted. n = 63.

---

## 7. Verdict

**Answer: Option C — both tools are correct under their own internal contracts, but only one contract is valid for the campaign.**

| Contract | Tool | n | What it counts |
|---|---|---:|---|
| Unique opportunities (deduplicated) | canonical export + command center | **62** | Each market opportunity counted once; duplicate executions of the same opportunity excluded via `canonical_retained_flag` |
| All qualifying executions (no dedup) | drift audit | **63** | Every row passing the four core filters, including both executions of a duplicated opportunity |

The drift audit's count of 63 is arithmetically correct under its own (less strict) filter contract. However, "correct under its own contract" is **not** the same as "valid for the campaign.** The campaign tracks independent market observations for the P4 binomial p-value test. Counting the same opportunity twice inflates n by 1 and inflates WR by ~0.6pp — both biasing the significance test. **63 is not valid for any campaign gate or milestone document.** The canonical export's 62 is authoritative for all campaign purposes.

The discrepancy is fully explained by a single duplicate pair executed on 2026-05-28.

---

## 8. Authoritative n for Campaign Purposes

**n = 62 is the authoritative canonical count.**

The campaign gate P1 (`n >= 100`) and the N70 milestone track *unique market opportunities*, not execution count. An opportunity that fires in two simultaneous bot runs is one opportunity, not two. The canonical export's deduplication enforces this correctly.

N70 milestone threshold: **8 unique qualifying opportunities remaining** (62 → 70).

---

## 9. Impact on Drift Audit Metrics

The drift audit's extra row (Row 2, TREND_DOWN TP +0.010044) is included in its rolling and aggregate metrics. Quantitative impact:

| Metric | Canonical (n=62) | Drift Audit (n=63) | Delta |
|---|---:|---:|---:|
| n | 62 | 63 | +1 |
| WR | 56.5% (35W/27L) | 57.1% (36W/27L) | +0.6pp |
| PF (cumulative) | 1.980 | 2.031 | +0.051 |
| Net PnL | +0.192241 | +0.202285 (est.) | +0.010044 |

The drift audit slightly overstates WR and PF by including the duplicate TP. The overstatement is small and consistent (same every run until the canonical source changes). Phase segmentation and nc_PF series are also offset by 1 index from trade #50 onward.

---

## 10. Required Fix (Informational — Code Change Not In Scope Today)

### Minimum fix (dedup alignment)

The drift audit is missing a deduplication filter. Adding this after the `hold_seconds` filter aligns n=63 with canonical n=62:

```python
# Add after the hold_seconds filter in the __main__ loop:
if r.get('canonical_retained_flag', 'true') != 'true':
    continue
```

The `.get(..., 'true')` default is intentional and safe: if the column is absent (e.g., a legacy CSV that predates the dedup step), the row is included rather than silently dropped.

### Why the minimum fix is correct for today but not durable

The export `_cell_qualifies()` applies two filters the drift audit lacks:
1. **Dedup**: `canonical_retained_flag = 'true'`
2. **Outcome quality gate**: `trade_result in {TP, SL} OR pnl_usdc not empty`

Today, the outcome quality gate removes 0 rows (all 63 qualifying rows have a resolved outcome). The minimum dedup-only fix therefore produces n=62 — matching exactly. However, if a future export contains an open position or a row with empty `pnl_usdc` and no `trade_result`, the drift audit would diverge again: it would count a row the export excludes.

### Durable fix (contract-complete alignment)

The drift audit should match the full export contract. Both filters should be added:

```python
# Add after the hold_seconds filter in the __main__ loop:
if r.get('canonical_retained_flag', 'true') != 'true':
    continue
trade_result = r.get('trade_result', '')
pnl_raw      = r.get('pnl_usdc', '')
if trade_result not in {'TP', 'SL'} and pnl_raw in {None, ''}:
    continue  # outcome quality gate — mirrors _cell_qualifies()
```

This is the fix that should be scoped into the authorized patch task.

### Application status

Neither fix is applied here (READ ONLY task). Both require a separately authorized patch task.

---

## 11. Summary

| Finding | Detail |
|---|---|
| CSV total rows | 502 |
| Rows failing ETH filter | 133 (all BTC) |
| Rows failing YES filter | 217 |
| Rows failing OPENING_SCAN filter | 31 |
| Rows failing hold > 15 filter | 58 |
| Rows after all four filters | 63 |
| Rows failing outcome quality gate | 0 |
| Rows marked duplicate (canonical_retained_flag=false) | 1 |
| Canonical n (unique opportunities) | **62** |
| Drift audit n (all qualifying executions) | **63** |
| Discrepancy source | Deduplication only |
| Responsible row | cre_91c9e71be369d0fbbdc2 (2026-05-28T11:25:17, TREND_DOWN TP +0.010044) |
| Required fix | Add `canonical_retained_flag == 'true'` filter to `_drift_audit.py` |
| Authoritative n for N70 milestone | **62** |
| Operational decision unchanged | CONTINUE_ACCUMULATION (62 < 70 either way) |

---

*Offline/reporting only. No runtime, strategy, risk, or execution changes. No commits authorized by this document.*
