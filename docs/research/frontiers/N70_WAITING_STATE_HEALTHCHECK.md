# N70 Waiting State Health Check

Date: 2026-06-09
Mode: READ ONLY — no code, runtime, strategy, risk, execution, or live changes
Provenance: all metrics read from today's regenerated artifacts; tools were
NOT re-run this session. Command center regenerated at 2026-06-09T06:53:38Z,
export meta at 2026-06-09T06:53:04Z. Tool/test health evidenced by the
same-session `N70_DRY_RUN_STATUS.md` which recorded all three tools running
clean and 22/22 tests passing.

Non-authorization: this document does not authorize any runtime, strategy,
risk, execution, sizing, or live behavior change.

---

## Verdict

**CAUTION**

All functional health metrics are strong. All kill criteria INACTIVE. All hard
tripwires CLEAR. nc_PF = 2.921 with zero consecutive below-1.0 points.
P5 gate upgraded to PASS (4 calendar weeks: W21 through W24). WR, PF, and
velocity all above monitoring floors.

Two caution items carry over from sibling governance docs
(`N70_READINESS_STATUS.md` and `N70_DRY_RUN_STATUS.md`, both 2026-06-09)
and remain unresolved:

- **C1 (governance hygiene):** legacy `DEFAULT_CSV_PATH = completed_trades_v1_2.csv`
  still present in `tools/eth_yes_fc_os_command_center.py:14` and
  `tools/_drift_audit.py:4,44`. Daily workflow bypasses it with explicit
  `--path`. Non-blocking operationally; uncleared governance bar.
- **C2 (watch):** TREND_UP n=10, monitoring threshold n=14. Four more
  TREND_UP trades would fire the TREND_UP-expansion notification. Not triggered,
  but within observable proximity.

Stale tracker docs (N70_READINESS_TRACKER.md at n=62, verification_tracker.md
at n=60) are pre-existing and benign — they will be updated as part of the N70
execution package.

**Functional health: HEALTHY. Caution is governance hygiene and one watch
item — not operational deterioration.**

---

## 1. Canonical Export

Source: `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json`

| Field | Value |
|---|---|
| Export generated | 2026-06-09T06:53:04Z |
| Schema version | canonical_regime_enriched_v1 |
| Validation status | **PASS** |
| Canonical n | **67** |
| Raw filtered rows | 68 |
| Duplicate rows removed | 1 |
| Regime join rate | 1.0 (100%) |
| Unknown regime count | **0** |
| Unknown regime rate | 0.0% |
| Freshness status | **FRESH** |
| Source lag (s) | 0.0 |
| Latest trade close | 2026-06-09T03:15:14Z |
| Latest decision scanned | 2026-06-09T03:15:09Z |
| Decision log files | 31 |
| Trade journal files | 29 |
| Trade journal latest | 2026-06-09.jsonl |
| Decision log latest | 2026-06-09.jsonl |

Assessment: **HEALTHY** — PASS, FRESH, zero unknown regimes, zero lag.

---

## 2. Command Center

Source: `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md`
Generated: 2026-06-09T06:53:38Z
Source evidence: `canonical_export:runtime/research_exports/canonical_regime_enriched_trades_v1.csv`

### Core Metrics

| Metric | Value | Floor / Gate | Status |
|---|---:|---|---|
| Canonical n | **67** | — | n=67; 3 from N70 |
| Remaining to N70 | **3** | < 70 → INACTIVE | INACTIVE |
| Remaining to N100 | **33** | — | — |
| WR | **56.7%** | > 52% watch floor | ✅ CLEAR |
| PF | **1.993** | > 1.5 watch floor | ✅ CLEAR |
| nc_PF (window=20) | **2.921** | > 1.0 | ✅ CLEAR |
| nc_PF consecutive < 1.0 | **0** | > 10 → advisory | ✅ CLEAR |
| p-value | 0.164 | < 0.05 (P4 gate) | OPEN (accumulation only) |
| Calendar weeks | **4** | ≥ 3 (P5 gate) | ✅ PASS — W21, W22, W23, W24 |
| Export validation | VALID | — | ✅ |
| Source freshness | FRESH/RECENT (0.0h) | — | ✅ |

### Promotion Gates

| Gate | Criterion | Status | Current |
|---|---|---|---|
| P1 | n ≥ 100 | OPEN | n=67 |
| P2 | WR > 52% | **PASS** | 56.7% |
| P3 | PF > 1.5 | **PASS** | 1.993 |
| P4 | p < 0.05 at or before n=100 | OPEN | p=0.164; n_required=143 |
| P5 | ≥ 3 calendar weeks | **PASS** | 4 weeks (W21–W24) |

**3 / 5 promotion gates passing. Hard blockers: P1 (n<100), P4 (p>0.05).**

### Kill Criteria

| Guard | Criterion | Status | Detail |
|---|---|---|---|
| K1 | New-block WR < 48% on ≥ 30 new trades | **INACTIVE** | n_new=6; WR=50.0%; PF=1.601 |
| K2 | Cumulative PF < 1.3 at n ≥ 80 | **INACTIVE** | PF=1.993; buffer=0.693 |
| K3 | BTC WR > 40% on n_BTC ≥ 20 | **INACTIVE** | n_BTC=13; WR=23.1% |
| K4 | Excl. top-5 PF < 1.0 at n=100 | **INACTIVE** | excl_top_5_pf=1.426 |
| nc_PF | > 10 consecutive below 1.0 advisory | **CLEAR** | 0/10 |

**Kill criteria triggered: 0 / 4.**

### Snapshot Summary

| Metric | Value |
|---:|---:|
| Wins | 38 |
| Losses | 29 |
| Gross win PnL | +$0.418174 |
| Gross loss PnL | −$0.209857 |
| Net PnL | +$0.208317 |
| Median PnL | +$0.005684 |

### Velocity

Note: command center velocity figures (generated 2026-06-09T06:53:38Z) supersede
the 0.29/day figure in `N70_DRY_RUN_STATUS.md` and the 0.29/day in
`N70_READINESS_TRACKER.md` (2026-06-08). The command center reflects 6 new
qualifying trades since the n=62 tracker baseline.

| Basis | Rate | ETA to N70 |
|---|---:|---:|
| 7-day rolling | **1.00/day** | **3 days** |
| 14-day rolling | 1.57/day | 2 days |
| Historical campaign | 3.05/day | 1 day |

Assessment: **HEALTHY** — velocity recovered from the post-COMPRESSION stall.

---

## 3. Drift Audit Health

The drift audit was not re-run this session (READ ONLY). Health is evidenced by:

1. `N70_DRY_RUN_STATUS.md` (same session): `_drift_audit.py --path canonical_csv`
   reported rolling WR=65.0%, PF=2.509, nc_PF=2.921, all monitors CLEAR.
2. Command center Panel C: nc_PF = 2.921, consecutive below 1.0 = 0, data
   quality = RELIABLE — computed from the same canonical export that today's
   drift audit would read.
3. Tool compile: `py -3.11 -m py_compile tools/_drift_audit.py` — PASS (same-session
   N70_DRY_RUN_STATUS.md §Tool and Test Health).

Assessment: **HEALTHY** — nc_PF strong; no sign of deterioration.

---

## 4. Tripwire Status

| Tripwire | Threshold | Current | Status |
|---|---|---|---|
| N70 reached | canonical_n ≥ 70 | n=67 | ❌ INACTIVE — 3 short |
| nc_PF warning | sustained below 1.0 | nc_PF = 2.921; 0 consec < 1.0 | ✅ CLEAR |
| PF deterioration | PF < 1.5 | PF = 1.993 | ✅ CLEAR |
| WR deterioration | WR < 52% | WR = 56.7% | ✅ CLEAR |
| COMPRESSION shift | material change | n=21 (unchanged); W23+ share = 0%; continued absence, no new shift | ✅ NO NEW SHIFT |
| TREND_UP expansion | TREND_UP n ≥ 14 | n_TU = 10; threshold = 14; 4 more trades to alert | ⚠️ WATCH (4 away) |

COMPRESSION note: the command center shows MANUAL REQUIRED fields for
current-cycle COMPRESSION share. The 21-trade count is unchanged since the last
committed snapshot. The absence (zero new COMPRESSION trades post-2026-06-01)
is the established baseline condition, not a new shift event.

TREND_UP note: 3 new TREND_UP trades since the n=62 tracker baseline (n_TU was 7,
now 10). The alert threshold is n=14. Not fired; within observable proximity.

---

## 5. Stale Governance Doc Status

| Document | Last updated | Shows | Actual | Impact |
|---|---|---|---|---|
| `N70_READINESS_TRACKER.md` | 2026-06-08 | n=62 | n=67 | Benign — update trigger is N70 |
| `verification_tracker.md` | 2026-06-06 | n=60 | n=67 | Benign — stale robustness/path stats; update at N70 |
| `evidence_velocity_dashboard.md` | 2026-06-06 | n=61 | n=67 | Benign — velocity estimate stale; command center is current |
| `ETH_YES_FC_OS_CAMPAIGN_DASHBOARD.md` | 2026-06-06 | n=61 | n=67 | Benign — executive view stale; will update at N70 |
| `N70_RUNBOOK.md` | 2026-06-08 | n=62 baseline | n=67 | Governance-OK — runbook reads at N70, not daily |

All staleness is pre-existing and expected. N70 execution is the authorized
update trigger for all of these docs.

---

## 6. Open Cautions

### C1 — Legacy CSV Default Path (pre-existing, governance hygiene)

Same item documented in `N70_READINESS_STATUS.md` and `N70_DRY_RUN_STATUS.md`
(both 2026-06-09). Bar set by `N70_READINESS_STATUS.md`:

> *"Before declaring full READY, clear or explicitly accept the legacy
> completed-trades fallback/default in active tooling."*

| Location | Finding |
|---|---|
| `tools/eth_yes_fc_os_command_center.py:14` | `DEFAULT_CSV_PATH = completed_trades_v1_2.csv` |
| `tools/_drift_audit.py:4,44` | Legacy fallback text references `completed_trades_v1_2.csv` |

Daily workflow uses explicit `--path`. This caution is governance hygiene
only — operational impact: none.

### C2 — TREND_UP Expansion Watch (active, not triggered)

TREND_UP n=10 (was 7 at n=62 tracker baseline, was 7 at n=61 campaign snapshot).
Notification threshold: n=14. Four more qualifying TREND_UP trades would fire
the alert. TREND_UP PF remains 0.661 — the only sub-regime below 1.0. No kill
criterion is activated at current n.

---

## Summary

| Component | Status |
|---|---|
| Canonical export | ✅ HEALTHY — n=67, PASS, FRESH, zero unknown regimes |
| Command center | ✅ HEALTHY — n=67, WR=56.7%, PF=1.993, nc_PF=2.921 |
| Drift audit health | ✅ HEALTHY — nc_PF CLEAR, all monitors clear |
| Runtime JSONL inputs | ✅ CURRENT — all 4 dirs populated, latest 2026-06-09 |
| All baseline source docs | ✅ ALL EXIST |
| All output target docs | ✅ ALL EXIST |
| All governance docs | ✅ ALL EXIST |
| Kill criteria | ✅ 0 / 4 triggered |
| Promotion gates | 3 / 5 PASS (P1, P4 open — accumulation only) |
| Tripwires | ✅ ALL CLEAR (N70 INACTIVE — n=67) |
| TREND_UP watch | ⚠️ n=10; threshold n=14; 4 trades from alert |
| Legacy CSV caution (C1) | ⚠️ PRE-EXISTING — non-blocking, governance hygiene |
| Stale tracker docs | ⚠️ PRE-EXISTING — benign, N70 is update trigger |
| N70 trigger | ❌ INACTIVE — n=67, need 3 more |

---

*Offline/reporting only. No runtime, strategy, risk, or execution changes.
No commits authorized by this document.*
