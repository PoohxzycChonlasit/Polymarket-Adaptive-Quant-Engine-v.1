---
type: implementation_plan
cell: "ETH × YES × FIRST_CYCLE × OPENING_SCAN × hold > 15s"
generated_at: 2026-06-07
n_at_creation: 61
code_changed: No
strategy_changed: No
runtime_changed: No
risk_changed: No
execution_changed: No
committed: No
spec_source: docs/research/frontiers/ETH_YES_FC_OS_COMMAND_CENTER_SPEC.md
---

# ETH_YES_FC_OS Command Center — Implementation Plan

**Goal:** Convert `ETH_YES_FC_OS_COMMAND_CENTER_SPEC.md` into an executable reporting workflow.
**Output spec:** A new offline tool (`tools/eth_yes_fc_os_command_center.py`) that generates `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md` on demand.

---

## Key Finding: "Daily Verification Snapshot" Does Not Exist

The task lists "Daily Verification Snapshot" as a source document to review. A repository search
(`docs/research/**/*snapshot*`, `docs/research/**/*daily*`) returned no matching file. This document
has not been created. It is the DB-1 gap identified in `VERIFICATION_OPERATIONS_FREEZE.md` §3 —
"no live daily operator dashboard." The `ETH_YES_FC_OS_COMMAND_CENTER.md` report that this plan
specifies **is** that missing artifact. This plan both defines its format (§Q4) and provides the
tool to generate it (§Q6).

---

## Q1: Data Sources That Exist

### Primary — Canonical Trade Table (CSV)

| File | Source |
|------|--------|
| `runtime/research_exports/completed_trades_v1_2.csv` | Built by `tools/canonical_trade_table_v1.py` |

This is the authoritative source for all completed-trade metrics. It is built from raw JSONL:

```
runtime/quant_data/trade_journal/*.jsonl
runtime/quant_data/decision_log/*.jsonl
runtime/quant_data/execution_log/*.jsonl
runtime/quant_data/path_truth/*.jsonl   (available from 2026-05-24)
```

**Important:** The current CSV snapshot (`completed_trades_v1_2.csv`) was built prior to the
2026-06-06 W23 SIDEWAY trade. The CSV predates n=61. **Step 0 of any report generation run is
to rebuild the CSV from JSONL using `tools/canonical_trade_table_v1.py`.** The command center
tool is a consumer of a fresh canonical table; it should not be run against a stale export.

### Secondary — Decision Log (JSONL)

`runtime/quant_data/decision_log/*.jsonl` — one file per session date (2026-05-08 through present).

Schema (confirmed from `2026-06-06.jsonl`):
- Top-level keys: `event_type`, `mode`, `payload`, `run_id`, `schema_version`, `source_module`, `timestamp_utc`
- Relevant payload fields:

| Field | Purpose |
|-------|---------|
| `payload.asset` | ETH / BTC — regime filter |
| `payload.market_regime` | COMPRESSION / TREND_DOWN / SIDEWAYS / TREND_UP |
| `payload.lifecycle_phase` | OPENING_SCAN / ACTIVE_INVENTORY_TRADING / etc. |
| `payload.side` | YES / NO |
| `payload.decision_id` | Unique per decision cycle — uptime proxy |
| `payload.skipped` | True / False |

These fields power the session-based metrics in Panel C (COMPRESSION share, BTC regime, cycle count).

### Tertiary — Existing Offline Tools (Reference Only)

`tools/_drift_audit.py` — the primary model for the new generator:
- Already reads `completed_trades_v1_2.csv` with the correct ETH YES OPENING_SCAN hold>15s filter
- Already implements `rolling_comp_pf()` (= nc_PF, window=20, non-COMPRESSION rows only)
- Already computes regime breakdown, calendar-week segmentation, phase segmentation
- The new command center generator extends this pattern; it does not replace it

`tools/operator_summary.py` — **not a building block for this plan.** It reads from
`runtime/reports/compact_run_summary/*.json` (run-level system diagnostics), not from JSONL
or CSV trade data. Different data source, different purpose.

---

## Q2: Metrics That Can Be Generated Automatically

### Filter Predicate (applied to `completed_trades_v1_2.csv`)

```
asset == 'ETH'
AND side == 'YES'
AND 'OPENING_SCAN' in canonical_entry_lifecycle_phase      # FIRST_CYCLE operationalization
AND hold_seconds > 15
```

**FIRST_CYCLE operationalization note:** No separate `first_cycle` column exists in the CSV schema.
FIRST_CYCLE and OPENING_SCAN are coextensive in this dataset — the opening scan is definitionally
the first decision cycle in a market epoch. `canonical_entry_lifecycle_phase` containing `OPENING_SCAN`
is the correct and complete predicate.

**quarantine_flag note:** `quarantine_flag` exists in the CSV schema but is **not** part of the
authoritative filter — `_drift_audit.py` does not filter on it. The generator must omit this
predicate to reproduce the published n=61 baseline. A `--apply-quarantine-filter` flag may be
offered for optional hardening; if enabled, the output must carry a notice that the resulting n
differs from the published baseline and is not directly comparable.

### Auto-Computable from CSV (Panels A, B, D + partial C)

| # | Metric | Panel | Method |
|---|--------|-------|--------|
| 1 | n (qualifying row count) | A, B | `len(df)` after filter |
| 2 | Cumulative WR | A, B | `(df.outcome_win_loss == 'W').sum() / n` |
| 3 | Cumulative PF | A, B | `gross_profit / abs(gross_loss)` |
| 4 | Calendar weeks with ≥1 trade | A (P5) | `df.entry_ts.dt.isocalendar().week.nunique()` |
| 5 | n-required for p<0.05 at current WR | A (P4), B | Binary search on one-sided binomial using `math.comb` (stdlib) |
| 6 | Evidence velocity (7d) | B, C | Count rows where `entry_ts >= today - 7d` |
| 7 | Days since last qualifying trade | C | `(today - df.entry_ts.max()).days` |
| 8 | nc_PF rolling (w=20) | C | Non-COMPRESSION rows, rolling PF window=20; model: `_drift_audit.rolling_comp_pf()` |
| 9 | nc_PF consecutive-below-1.0 counter | C | Index ranges in nc_PF series where nc_PF < 1.0 consecutively |
| 10 | Last-5 regime sequence | C | `df.tail(5)['regime']` (qualifying rows, chronological) |
| 11 | K1 new-block WR | D | `df[df.entry_ts > '2026-06-06'].outcome_win_loss` → WR |
| 12 | K2 PF buffer | D | `cumulative_PF - 1.3` |
| 13 | K3 BTC WR | D | Same filter with `asset='BTC'`; compute WR on n_BTC rows |
| 14 | K4 excl. top-5 PF | D (milestone n=100) | Sort by `pnl_usdc` desc, drop top 5, recompute PF |
| 15 | ETA table | B | `(70 - n) / rate_7d`, `(70 - n) / rate_14d`, `(70 - n) / rate_hist` |

**nc_PF consecutive-counter note:** "Consecutive" means consecutive trade *indices* (not
calendar days) where the rolling nc_PF value is below 1.0. The current trough in the published
drift audit was trade indices #38–#51 = 14 consecutive. The counter must use the series index
(qualifying-trade ordinal), not raw calendar days.

**P4 transform note:** The n-required transform finds the smallest n such that the one-sided
binomial p-value P(X ≥ ⌈WR·n⌉ | p=0.5) < 0.05. `math.comb` from the Python stdlib is sufficient;
`scipy` is not required.

**Calendar weeks note:** Use `pd.Timestamp.isocalendar().week` — do not hardcode date-string
week boundaries as `_drift_audit.py` does for its internal segmentation. Hardcoded boundaries
will become stale as the campaign crosses year or ISO week boundaries.

### Auto-Computable from Decision Log JSONL (Panel C session metrics)

| # | Metric | Source |
|---|--------|--------|
| 16 | COMPRESSION share (daily) | Count ETH decision events with `market_regime=COMPRESSION` / total ETH decision events, per `decision_log/{date}.jsonl` |
| 17 | COMPRESSION-absence duration | Days since last session file where COMPRESSION share > 5% |
| 18 | BTC regime daily | Modal `market_regime` across BTC decision events in latest session file |
| 19 | Decision cycle count (uptime proxy) | Count of `event_type=decision` rows in latest session's JSONL file |

These require a second read pass over decision_log JSONL. The generator should accept
`--decision-log-dir` to enable this path. If the argument is omitted, Panel C emits
`[MANUAL REQUIRED]` placeholders for these four fields.

---

## Q3: Metrics That Require Manual Input

After confirming the decision_log schema, **only one metric is genuinely manual** — not derivable
from either data source:

| Metric | Reason | How to supply |
|--------|--------|---------------|
| JSONL Writer Integrity status | Static knowledge flag (BLOCKED / NOMINAL) describing the known pre-May-29 deduplication issue. Cannot be inferred from data. | `--jsonl-integrity-status` CLI argument (default: BLOCKED) |

All other metrics referenced in the Command Center Spec are either auto-computable from CSV
or auto-computable from decision_log JSONL.

---

## Q4: ETH_YES_FC_OS_COMMAND_CENTER.md — Report Design

The generated report follows the Command Center Spec's four-panel layout exactly. The template
below uses illustrative values from the n=61 published snapshot; all values are replaced at
generation time.

```markdown
# ETH_YES_FC_OS Command Center
_Generated: {timestamp_utc} | Source: completed_trades_v1_2.csv (rebuilt {csv_mtime}) | n={n}_

---

## Panel A: Gate Status

### Promotion Gates (5 simultaneous required)
| Gate | Criterion | Status | Current |
|------|-----------|--------|---------|
| P1 | n ≥ 100 | ❌ OPEN | n={n} |
| P2 | WR > 52% | ✅ MET | WR={wr:.1%} |
| P3 | PF > 1.5 | ✅ MET | PF={pf:.3f} |
| P4 | p < 0.05 (one-sided binomial) | ❌ OPEN | p={p_val:.3f}; need n≈{n_required} at current WR |
| P5 | ≥ 3 calendar weeks with trades | ✅ MET | {weeks} weeks (W{week_list}) |

### Kill Guards
| Guard | Criterion | Status | Current |
|-------|-----------|--------|---------|
| K1 | New-block WR < 48% on ≥30 new trades | INACTIVE | n_new={n_new} / 30 (formal trigger n≈91); pre-monitor advisory when n_new≥15 |
| K2 | Cumulative PF < 1.3 at n≥80 | INACTIVE | PF={pf:.3f} → buffer +{k2_buffer:.3f} (evaluable at n=80) |
| K3 | BTC WR > 40% on n_BTC≥20 | INACTIVE | n_BTC={n_btc} / 20 threshold |
| K4 | Excl. top-5 PF < 1.0 at n=100 | INACTIVE | Milestone metric — evaluated at n=100 only |

### Runtime Integrity
| Check | Status |
|-------|--------|
| JSONL Writer | {jsonl_integrity_status} |
| CSV freshness | Built {minutes_since_build} min ago |

---

## Panel B: Progress Rail

```
n = {n} / 100  [{bar}]  {pct:.0f}%
```

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| WR | {wr:.1%} | > 52% | +{wr_gap:.1%} ✅ |
| PF | {pf:.3f} | > 1.5 | +{pf_gap:.3f} ✅ |
| p-value | {p_val:.3f} | < 0.05 | Need n≈{n_required} at current WR |

### P4 Transform: n Required for p < 0.05
_[All values dynamically computed at generation time via math.comb binary search]_
| WR scenario | n required |
|-------------|-----------|
| Hold at {wr:.1%} | ≈{n_required} |
| Improve to 59.0% | ≈{n_required_59} |
| Improve to 60.0% | ≈{n_required_60} |

### ETA to n=70 (next snapshot trigger)
| Velocity basis | Rate | Days remaining |
|----------------|------|----------------|
| 7-day rolling | {rate_7d:.2f}/day | {eta_7d:.0f} days |
| 14-day rolling | {rate_14d:.2f}/day | {eta_14d:.0f} days |
| Historical (pre-stall) | {rate_hist:.2f}/day | {eta_hist:.0f} days |

---

## Panel C: Leading Indicators

### nc_PF Monitor (non-COMPRESSION, rolling window = 20)
- Current nc_PF (window=20): {nc_pf_current:.3f}
- Consecutive periods below 1.0: {nc_pf_consecutive} (tripwire threshold = 10)
- Last trough: trade #{nc_pf_trough_idx}, value {nc_pf_trough_val:.3f}

### Market Structure
- COMPRESSION share (today, ETH decisions): {comp_share_today:.1%}  [MANUAL REQUIRED if --decision-log-dir not set]
- COMPRESSION share (7d avg): {comp_share_7d:.1%}
- COMPRESSION-absence duration: {comp_absence_days} days (since {comp_last_date})
- Historical COMPRESSION share: 43.1%  [hardcoded from campaign dashboard]

### Velocity & Stall
- Qualifying trades today: {trades_today}
- Days since last qualifying trade: {days_since_last}
- 7d velocity: {rate_7d:.2f}/day
- 14d velocity: {rate_14d:.2f}/day
- Status: {velocity_status}   [ACCUMULATING_SLOWLY / STALLED / ACTIVE]

### Last-5 Regime Sequence
{regime_sequence}   [e.g. TREND_DOWN → SIDEWAY → SIDEWAY → TREND_DOWN → TREND_UP]

### BTC Regime (today)
{btc_regime_today}   [MANUAL REQUIRED if --decision-log-dir not set]

---

## Panel D: Kill Criterion Monitors

### K1 — New-Block Win Rate (baseline: n=61, date 2026-06-06)
- n_new (trades since baseline): {n_new}
- New-block WR: {k1_wr:.1%}  [INERT — formal trigger at n_new=30 (n≈91); pre-monitor advisory when n_new≥15]
- Advisory flag: {k1_flag}

### K2 — Cumulative PF Buffer
- Cumulative PF: {pf:.3f}  /  Threshold: 1.30
- Buffer: +{k2_buffer:.3f}
- Evaluable: at n≥80  [currently n={n}]

### nc_PF Tripwire Advisory
- Consecutive index periods below 1.0: {nc_pf_consecutive} / 10 tripwire
- Status: {tripwire_status}   [CLEAR / WARNING / ADVISORY]
```

**Note on Panel D / K3:** The BTC WR (K3) is read from the same CSV with `asset='BTC'` filter.
If n_BTC < 20, K3 displays as INACTIVE with current n_BTC count.

---

## Q5: Automation Feasibility Verdict

**YES** — the report can be generated automatically, in two tiers:

**Tier 1 (CSV only, ~95% of metrics):**
All trade-based metrics across Panels A, B, D, and partial Panel C are computable from
`completed_trades_v1_2.csv` using the filter predicate. No JSONL parsing needed. The
generator runs offline, reading only the pre-built canonical CSV.

**Tier 2 (CSV + decision_log, ~100% of metrics):**
COMPRESSION share, BTC regime, and decision cycle count additionally require parsing
decision_log JSONL files. Field names are confirmed: `payload.market_regime`, `payload.asset`,
`payload.decision_id`. The generator accepts `--decision-log-dir` to enable this path.

**One static input:** The JSONL Writer Integrity flag must be supplied by the operator via
`--jsonl-integrity-status`. It is static knowledge that cannot be derived from data.

**Pre-condition (non-optional):** The CSV must be freshly rebuilt from JSONL before running
the command center generator. The rebuild step uses the existing `tools/canonical_trade_table_v1.py`
tool. Generating the command center against a stale CSV will silently report out-of-date statistics.

---

## Q6: Implementation Plan (Offline Tool Only)

### New Tool: `tools/eth_yes_fc_os_command_center.py`

This tool is genuinely new — no existing tool covers this purpose.
- `tools/operator_summary.py` reads from `runtime/reports/compact_run_summary/*.json` (run-level
  system diagnostics) and is not a building block here.
- `tools/_drift_audit.py` is the design model: read CSV → apply filter → compute metrics → emit report.

### CLI Interface

```bash
# Tier 1: CSV only (fast path, COMPRESSION/BTC regime show as [MANUAL REQUIRED])
python tools/canonical_trade_table_v1.py          # Step 0: rebuild CSV
python tools/eth_yes_fc_os_command_center.py

# Tier 2: CSV + decision_log (full panels)
python tools/canonical_trade_table_v1.py
python tools/eth_yes_fc_os_command_center.py \
    --decision-log-dir runtime/quant_data/decision_log \
    --jsonl-integrity-status BLOCKED

# Custom paths
python tools/eth_yes_fc_os_command_center.py \
    --csv-path runtime/research_exports/completed_trades_v1_2.csv \
    --decision-log-dir runtime/quant_data/decision_log \
    --jsonl-integrity-status BLOCKED \
    --output-path docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md
```

### Argument Defaults

| Argument | Default | Description |
|----------|---------|-------------|
| `--csv-path` | `runtime/research_exports/completed_trades_v1_2.csv` | Canonical trade CSV (v1_2) |
| `--decision-log-dir` | (unset) | Decision log JSONL directory; if unset, Panel C session metrics show `[MANUAL REQUIRED]` |
| `--output-path` | `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md` | Output report path |
| `--jsonl-integrity-status` | `BLOCKED` | Static flag: BLOCKED or NOMINAL |
| `--baseline-n` | `61` | Trade count at K1 baseline (2026-06-06); used to separate new-block trades |
| `--baseline-date` | `2026-06-06` | Date string for K1 baseline filter |

### Implementation Phases

**Phase 0 — Load and validate CSV (dependency: Step 0 rebuild)**
- Read CSV; confirm `completed_trades_v1_2.csv` exists and mtime is recent (warn if >24h stale)
- Apply ETH YES OPENING_SCAN hold>15 quarantine=False filter
- Confirm n > 0; abort with clear message if filter yields zero rows

**Phase 1 — Compute Panel A gate status**
- P1: `n >= 100`
- P2: `wr > 0.52`
- P3: `pf > 1.5`
- P4: binomial p-value via `math.comb`; compute current p and n-required transform
- P5: `df.entry_ts.dt.isocalendar().week.nunique() >= 3`
- K1: filter new-block trades (`entry_ts > --baseline-date`); compute cumulative and rolling-15 new-block WR
  - Pre-monitor advisory: if n_new≥15 and rolling-15-WR < 45%, emit advisory (spec §4 Panel D)
  - Formal K1 window: evaluable when n_new≥30 (n≈91); flag if cumulative new-block WR < 48%
- K2: `cumulative_PF >= 1.3`; note evaluable at n≥80
- K3: re-filter CSV with `asset='BTC'`; compute BTC WR and n_BTC
- K4: sort descending by pnl_usdc, drop top 5, recompute PF; flag at n=100 only
- JSONL integrity: pass through `--jsonl-integrity-status`

**Phase 2 — Compute Panel B progress rail**
- n progress bar string
- WR/PF vs targets
- P4 transform table: compute n-required at current WR, 59.0%, 60.0%
- ETA table:
  - 7d velocity: count qualifying rows where `entry_ts >= today - 7 days` / 7
  - 14d velocity: count qualifying rows where `entry_ts >= today - 14 days` / 14
  - Historical velocity: `n / (today - df.entry_ts.min()).days` (campaign average from first qualifying trade — no arbitrary cutoff)
  - ETA: `ceil((70 - n) / rate)` for each velocity; show as `—` if rate == 0

**Phase 3 — Compute Panel C leading indicators (partial or full)**

*From CSV (always):*
- nc_PF series: filter non-COMPRESSION rows, rolling window=20 PF; extract current value
- nc_PF consecutive-below-1.0 counter: scan series for consecutive index runs < 1.0
- Last-5 regime sequence: `df.tail(5)['regime']`
- Days since last qualifying trade
- 7d/14d velocity

*From decision_log JSONL (if `--decision-log-dir` provided):*
- Load all JSONL files; parse line-by-line (one JSON object per line)
- For COMPRESSION share: filter `event_type=decision, payload.asset=ETH`; count `market_regime=COMPRESSION` / total
- For COMPRESSION-absence: find last date where COMPRESSION share > 5%
- For BTC regime: filter `event_type=decision, payload.asset=BTC` on latest session file; compute modal `market_regime`
- For cycle count: count `event_type=decision` rows in latest session file

**Phase 4 — Compute Panel D kill monitors**
- K1 block WR (from Phase 1)
- K2 PF buffer = `cumulative_PF - 1.3`
- nc_PF tripwire: compare consecutive counter to 10

**Phase 5 — Write markdown report**
- Render template (§Q4 above) with computed values
- Write to `--output-path`
- Print generation summary to stdout: n, WR, PF, p-value, velocity, output path

### Dependencies

| Dependency | Source | Notes |
|------------|--------|-------|
| `pandas` | Already in project | CSV reading, date arithmetic |
| `math.comb` | Python stdlib ≥ 3.8 | Binomial p-value — no scipy needed |
| `json` | Python stdlib | JSONL line parsing |
| `pathlib` | Python stdlib | Path handling |

No new packages required.

### Non-Authorization Clause

This tool reads evidence and emits a markdown report. It must not be wired into runtime
decisions, risk gates, order flow, or execution logic. It is an offline observability tool only
(CLAUDE.md: "Offline tools are evidence only. Replay outputs and analyzer reports must not be
wired into automatic runtime decisions without a separately approved implementation phase.").

### Output Location

`docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md`

This location places the command center alongside the campaign dashboard
(`ETH_YES_FC_OS_CAMPAIGN_DASHBOARD.md`) as a sibling operational document. It satisfies the
DB-1 gap identified in `VERIFICATION_OPERATIONS_FREEZE.md` without creating a new directory.

---

## Freeze Summary

| Question | Answer |
|----------|--------|
| Q1: Data sources | CSV (`completed_trades_v1_2.csv`) + Decision log JSONL + existing offline tools |
| Q2: Auto-computable metrics | 15 from CSV (all trade-based); 4 from decision_log JSONL (session-based) |
| Q3: Manual-only metrics | 1: JSONL Writer Integrity flag (static, operator-supplied) |
| Q4: Report design | Four-panel template (§Q4 above); placeholder mockup included |
| Q5: Automation feasibility | YES — Tier 1 (CSV only) or Tier 2 (CSV + decision_log) |
| Q6: Implementation | New tool `tools/eth_yes_fc_os_command_center.py`; 5 phases; stdlib only; no runtime changes |
| Daily Verification Snapshot | Does not exist — this plan creates it |
| Pre-condition | Rebuild `completed_trades_v1_2.csv` via `canonical_trade_table_v1.py` before each run |
| Phase scope | Offline evidence only; Phase 1 per `PROJECT_RULES.md` roadmap |
