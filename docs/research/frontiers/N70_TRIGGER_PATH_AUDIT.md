# N70 Trigger Path Audit

Date: 2026-06-09
Mode: READ ONLY — no code, runtime, strategy, risk, execution, or live changes
Source basis: N70_EXECUTION_PACKAGE.md (governing checklist) +
  N70_RUNBOOK.md (execution procedure) + N70_READINESS_TRACKER.md (trigger rule) +
  N70_READINESS_STATUS.md (caution baseline) + N70_PREFLIGHT_AUDIT.md (preflight ref)
Non-authorization: this document does not authorize any runtime, strategy,
  risk, execution, sizing, or live behavior change. N70 execution requires
  canonical_n >= 70 (currently n=67).

---

## Verdict

**CAUTION**

The N70 trigger path is fully defined, all dependencies are confirmed present,
all failure modes are documented, and the detection-to-execution chain is
unambiguous. The path is operational.

Two pre-existing governance items are inherited from sibling documents
(`N70_READINESS_STATUS.md`, `N70_DRY_RUN_STATUS.md`, `N70_WAITING_STATE_HEALTHCHECK.md`,
`N70_PRELAUNCH_CHECKLIST.md` — all 2026-06-09) and carry into this audit:

- **C1 (governance hygiene):** legacy `DEFAULT_CSV_PATH = completed_trades_v1_2.csv`
  present in `tools/eth_yes_fc_os_command_center.py:14` and
  `tools/_drift_audit.py:4,44`. Bar set by `N70_READINESS_STATUS.md` not yet
  cleared. Operational impact: none — all N70 Review Commands use explicit
  `--path`. Active report confirmed healthy.
- **C2 (watch):** TREND_UP n=10, notification threshold n=14. Four more
  TREND_UP trades to fire the alert; only 3 trades remain to n=70 — the alert
  cannot fire before N70 (max n_TU=13 at trigger). Forward watch for the
  n=70→n=80 block; not a path blocker.

One cross-document discrepancy is surfaced and resolved (§11): N70_EXECUTION_PACKAGE.md
locks a n=61 comparison baseline (9-trade new block); N70_RUNBOOK.md and
N70_PREFLIGHT_AUDIT.md reference n=62. N70_EXECUTION_PACKAGE.md is the governing
document and prevails: n=61 / 9-trade block (n=62–70) governs all analysis.

**Path verdict: CAUTION — operational, two pre-existing inherited items.**

---

## 1. Trigger Path Overview

Sequential phases from the moment canonical_n first reaches 70:

| Phase | Description |
|---|---|
| **A** | Daily automation detects canonical_n ≥ 70; issues notify-only alert |
| **B** | Operator runs N70 Review Commands (7-command suite) |
| **C** | All 6 trigger conditions verified; if all pass → proceed |
| **D** | Evidence window frozen (Step 1); 13-step mandatory workflow begins |
| **E** | 17-item analysis matrix executed; 6 mandatory output documents produced |
| **F** | Governor review: 15-question checklist completed manually |
| **G** | N70 verdict issued; N70_READINESS_TRACKER.md updated (Step 13) |

Nothing auto-executes after Phase A. Each subsequent phase requires deliberate
operator action. Manual governor approval (Phase F–G) is mandatory before any
verdict is issued. The automation's notify-only design is precisely why manual
approval is required — no verdict is automated.

---

## 2. Check 1: Canonical Export Update Path

**Tool:** `tools/canonical_regime_export.py`

**Input sources:**
- `runtime/quant_data/trade_journal/` (29 files; latest: 2026-06-09.jsonl)
- `runtime/quant_data/decision_log/` (31 files; latest: 2026-06-09.jsonl)

**Canonical filter chain** (N70_EXECUTION_PACKAGE.md §Canonical Input Contract):
```
event_type == trade_close
AND asset == ETH
AND side == YES
AND scan_type == OPENING_SCAN
AND hold_seconds > 15
```

**Dedup key:** `condition_id | epoch_start_ts | asset | side | candidate_id`

**Outputs:**
- `runtime/research_exports/canonical_regime_enriched_trades_v1.csv`
- `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json`

**Verification required at N70:**

| meta.json field | Required value |
|---|---|
| validation.status | PASS |
| canonical_n | exactly 70 |
| unknown_regime_count | 0 |
| regime_join_rate | ≥ 0.95 (95%) |
| freshness | FRESH |
| source_lag_s | ≈ 0.0 |

**Failure mode:** export validation FAIL → stop; do not proceed to any
downstream step; fix export tooling in a separate scope.

**Status:** ✅ Path documented; tool clean; current output: n=67, PASS, FRESH,
regime_join=100%, lag=0.0s (same-session `N70_DRY_RUN_STATUS.md`).

---

## 3. Check 2: Command Center Update Path

**Command:**
```powershell
py -3.11 tools/eth_yes_fc_os_command_center.py --path runtime/research_exports/canonical_regime_enriched_trades_v1.csv
```

**Input:** canonical export CSV — explicit `--path` required (see C1 note)

**Output:** `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md`
Git status after run: `M` modified; expected; not committed at this stage.

**Panels computed:**
- Panel A: Core performance (WR, PF, nc_PF, p-value, promotion gates P1–P5, kill criteria K1–K4)
- Panel B: Regime mix snapshot (COMPRESSION / TREND_DOWN / SIDEWAY / TREND_UP counts and shares)
- Panel C: Drift indicators (nc_PF rolling window=20, consecutive below 1.0 count)
- Panel D: Evidence velocity and ETA projections (7d/14d/campaign rates)

**C1 note:** `tools/eth_yes_fc_os_command_center.py:14` contains
`DEFAULT_CSV_PATH = completed_trades_v1_2.csv`. This default is bypassed by
the explicit `--path` argument used in the N70 Review Commands. The legacy
default is never exercised in the N70 workflow. Active report confirmed healthy
by `N70_READINESS_STATUS.md`.

**Verification at N70:** command center n must match export canonical_n (70).
Mismatch → stop and reconcile count before proceeding.

**Status:** ✅ Path documented; explicit `--path` confirmed in N70_RUNBOOK.md
§N70 Review Commands; n/WR/PF confirmed by prior session tool runs.

---

## 4. Check 3: Drift Audit Update Path

**Command:**
```powershell
py -3.11 tools/_drift_audit.py --path runtime/research_exports/canonical_regime_enriched_trades_v1.csv
```

**Input:** canonical export CSV — explicit `--path` required (see C1 note)

**Output:** stdout only; no file written by the drift audit tool itself.

**What the drift audit computes:**
- Rolling WR and PF (20-trade window, non-COMPRESSION trades only)
- nc_PF (non-COMPRESSION Profit Factor, rolling window=20)
- Consecutive nc_PF below 1.0 count (advisory threshold: > 10)
- Per-monitor tripwire status

**C1 note:** `tools/_drift_audit.py:4,44` contains a legacy fallback reference
to `completed_trades_v1_2.csv`. The explicit `--path canonical_csv` argument
in the N70 Review Commands bypasses this fallback entirely. The legacy default
is never exercised in the N70 workflow.

**JSONL Writer BLOCKED note:** the command center's Panel C may display
`JSONL Writer: BLOCKED`. This is an integrity-status input label, not an
export failure or drift audit path failure (`N70_READINESS_STATUS.md` §stale
dependency findings). It does not indicate a blocked path.

**Failure mode:** if drift audit cannot run (import error, tool failure) →
treat N70 review as blocked; report tool failure; do not proceed.

**Status:** ✅ Path documented; tool clean; nc_PF=2.921, all monitors CLEAR,
no consecutive below 1.0 (same-session `N70_DRY_RUN_STATUS.md`).

---

## 5. Check 4: N70 Readiness Tracker Update Path

**Target file:** `docs/research/frontiers/N70_READINESS_TRACKER.md`

**Current status:** STALE — shows n=62 (written 2026-06-08); actual n=67.
This is expected and benign. The tracker's update trigger is N70 execution
(Step 13 of 13), not the daily workflow.

**When it updates:** Step 13 — the final step of the 13-step mandatory workflow
in `N70_EXECUTION_PACKAGE.md`. This step occurs only after all analysis is
complete and the governor verdict has been determined.

**Fields updated at N70** (per §Promotion Tracker Logic Update at N70):

| Field | Updated to |
|---|---|
| n | 70 |
| Trades remaining to N100 | 30 |
| Progress bar | ████████████████░░░░ 70 / 100 |
| WR / PF / nc_PF | Values from frozen analysis |
| Regime mix (4 regimes) | Counts and shares at n=70 |
| Kill criteria K1–K4 | Evaluated status at n=70 |
| Promotion gates P1–P5 | Evaluated status at n=70 |
| Next trigger | n=80 |
| Governor verdict issued | CONTINUE_ACCUMULATION / CAUTION_DRIFT_REVIEW / FAIL_REVIEW_REQUIRED |

**Failure mode:** tracker update failure at Step 13 does not invalidate the
governor verdict, but must be completed before the N70 session closes.

**Status:** ✅ Update path documented; target file confirmed present; update
sequencing confirmed at Step 13 of 13.

---

## 6. Check 5: N70 Package Trigger Path

**Governing document:** `docs/research/N70_EXECUTION_PACKAGE.md` (2026-06-07)
This is the sole authoritative document for N70 execution (see Q2 in §10).

### Trigger Conditions

All 6 conditions must be TRUE simultaneously before the N70 workflow begins
(N70_RUNBOOK.md §N70 Trigger Conditions):

| # | Condition |
|---|---|
| 1 | `canonical_regime_export.py` reports canonical_n ≥ 70 |
| 2 | Export validation status = PASS |
| 3 | Duplicate removal has been reconciled (dedup count verified) |
| 4 | Regime join rate ≥ 95% (zero unexplained UNKNOWN regimes) |
| 5 | `_drift_audit.py --path canonical_csv` runs without error |
| 6 | No runtime / strategy / risk / execution mutations bundled with this review |

Note: N70_READINESS_TRACKER.md §N70 Trigger Rule lists 7 conditions (adds explicit
"UNKNOWN regime rate is reviewed and explained"). This is not a material conflict;
condition 7 in the tracker is implied by condition 4 (see §11 D2).

### 13-Step Mandatory Workflow

Per `N70_EXECUTION_PACKAGE.md` §Mandatory N70 Workflow:

| Step | Action |
|---|---|
| 1 | Freeze the raw evidence window at canonical_n = 70 |
| 2 | Reproduce count from raw JSONL (verify filter chain; no off-by-one) |
| 3 | List the 9 new canonical keys since n=61 (trades n=62 through n=70) |
| 4 | Confirm no duplicate condition_id in the 9-trade new block |
| 5 | Recompute cumulative metrics: WR, PF, W/L, gross win/loss PnL, net PnL, median |
| 6 | Compute new-block metrics: WR, PF, PnL, regime mix for n=62–70 |
| 7 | Update COMPRESSION count and absence status; compare against baseline share |
| 8 | Update nc_PF (rolling window=20) and consecutive-below-1.0 count |
| 9 | Evaluate all 5 promotion gates (P1–P5) |
| 10 | Evaluate all 4 kill criteria (K1–K4) |
| 11 | Compute ETAs and velocity against n=80 and n=100 targets |
| 12 | Produce all required output documents (§Required Outputs) |
| 13 | Issue governor verdict; update N70_READINESS_TRACKER.md |

### 17-Item Analysis Matrix

The full analysis matrix in `N70_EXECUTION_PACKAGE.md` covers (excerpt):

| Category | Items |
|---|---|
| Core performance | Cumulative WR, PF, W/L ratio, net PnL, median PnL |
| New-block analysis | Block WR vs 50% threshold, block PF vs 1.3 threshold |
| Regime health | COMPRESSION share, TREND_UP expansion, regime mix comparison |
| Drift / nc_PF | Rolling nc_PF, consecutive below 1.0, tripwire status |
| Kill criteria | K1–K4 evaluation against respective thresholds |
| Promotion gates | P1–P5 status update |
| Statistical | p-value, n_required for p<0.05, confidence interval |

### N70 PASS Thresholds (from §Analysis Matrix)

| Metric | PASS | CAUTION | FAIL |
|---|---|---|---|
| Cumulative WR | > 52% | 50–52% | < 50% |
| Cumulative PF | > 1.5 | 1.3–1.5 | < 1.3 |
| New-block WR | ≥ 50% | 48–50% | < 48% |
| New-block PF | ≥ 1.3 | 1.0–1.3 | < 1.0 |
| Kill criteria | 0 triggered | — | Any triggered |
| nc_PF | ≥ 1.0 or ≤ 5 consecutive below | 6–10 consecutive | > 10 consecutive |

**Status:** ✅ Trigger path fully documented; all 6 trigger conditions traceable
to source documents; 13-step workflow confirmed in governing document.

---

## 7. Check 6: Required Inputs

Per `N70_EXECUTION_PACKAGE.md` §Canonical Input Contract and
`N70_PREFLIGHT_AUDIT.md` §Source Files:

| Input | Source | Requirement at N70 |
|---|---|---|
| Canonical export CSV | `runtime/research_exports/canonical_regime_enriched_trades_v1.csv` | n=70, regenerated at review time |
| Export meta.json | `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json` | validation.status=PASS |
| Trade journal JSONL | `runtime/quant_data/trade_journal/` (29 files) | Must not lag trade close |
| Decision log JSONL | `runtime/quant_data/decision_log/` (31 files) | Must not lag trade close |
| n=61 baseline doc | `docs/research/CANONICAL_N61_REPRODUCIBILITY_AUDIT.md` | Exists; locked comparison anchor |
| N70 governing checklist | `docs/research/N70_EXECUTION_PACKAGE.md` | Exists; sole governing document |

All 6 inputs confirmed present and current (`N70_PRELAUNCH_CHECKLIST.md` §2, §4, §6, §7).

**Stale input checks** (per `N70_PREFLIGHT_AUDIT.md` §Stale Input Checks):

| Check | Rule |
|---|---|
| Lag check | trade_journal latest and decision_log latest must be current to review date |
| UNKNOWN regime | 0 UNKNOWN required before proceeding (or each explicitly explained) |
| n mismatch | If export n ≠ command center n → stop and reconcile count |
| Runtime exports | Generated exports excluded from commit unless explicitly approved |

---

## 8. Check 7: Required Outputs

Per `N70_EXECUTION_PACKAGE.md` §Required Outputs:

### Mandatory (6 documents)

| Output | Target file | Action |
|---|---|---|
| Watchlist snapshot | `docs/research/watchlists/ETH_YES_FC_OS.md` | Append N70 snapshot block |
| Verification tracker | `docs/research/verification_tracker.md` | Update per §Tracker Logic in EXECUTION_PACKAGE |
| Campaign dashboard | `docs/research/campaigns/ETH_YES_FC_OS_CAMPAIGN_DASHBOARD.md` | Update executive campaign view |
| Velocity dashboard | `docs/research/evidence_velocity_dashboard.md` | Update velocity and ETA |
| Drift audit doc | `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md` | Update drift audit findings |
| Snapshot review | `docs/research/N70_SNAPSHOT_REVIEW.md` | **Create fresh at N70** — currently absent (expected) |

### Optional (1 document)

| Output | Target file | Condition |
|---|---|---|
| Reproducibility audit | `docs/research/CANONICAL_N70_REPRODUCIBILITY_AUDIT.md` | Only if reconciliation uncertainty arises during analysis |

### Tool runs also required (N70_RUNBOOK.md §N70 Review Commands)

```powershell
py -3.11 tools/canonical_regime_export.py
py -3.11 tools/eth_yes_fc_os_command_center.py
py -3.11 tools/_drift_audit.py --path runtime/research_exports/canonical_regime_enriched_trades_v1.csv
py -3.11 -m pytest -q tests/test_drift_audit.py tests/test_canonical_regime_export.py tests/test_eth_yes_fc_os_command_center.py
py -3.11 -m py_compile tools/_drift_audit.py tools/canonical_regime_export.py tools/eth_yes_fc_os_command_center.py
git diff --check
git status --short
```

Estimated total runtime per `N70_PREFLIGHT_AUDIT.md` §Estimated Runtime:
export <1 min, command center <1 min, drift audit <1 min, tests 1–3 min,
manual governor review 15–30 min.

---

## 9. Check 8: Failure Scenarios

Combined from `N70_RUNBOOK.md` §Failure Modes and `N70_PREFLIGHT_AUDIT.md` §Blockers:

| Scenario | Governing source | Required response |
|---|---|---|
| Export validation FAIL | RUNBOOK, PREFLIGHT | Stop all downstream steps; fix export tooling in separate scope |
| Command center n ≠ export n | RUNBOOK | Stop; run count reconciliation before proceeding |
| Drift audit cannot run (tool error) | RUNBOOK, PREFLIGHT | Treat N70 review as blocked; report tool failure |
| UNKNOWN regime rate rises materially | RUNBOOK | Mark review as blocked; resolve regime enrichment before proceeding |
| Regime join rate < 95% | PREFLIGHT | Run regime enrichment reconciliation audit first |
| Duplicate count changes unexpectedly | RUNBOOK, PREFLIGHT | Run canonical count reconciliation before tracker update |
| Runtime / code / config / strategy files in staged diff | RUNBOOK | Stop; do not commit; split scope into separate task |
| Scratch tools appear in staging area | RUNBOOK | Exclude from commit scope; leave untracked |
| Generated runtime exports appear in staging area | RUNBOOK | Exclude unless explicitly approved for this session's scope |
| Kill criterion K1–K4 activates during analysis | EXECUTION_PACKAGE | Kill criterion triggered; governor verdict likely FAIL_REVIEW_REQUIRED |
| nc_PF > 10 consecutive below 1.0 | EXECUTION_PACKAGE | Advisory threshold breached; governor review required |
| N70 analysis outputs incomplete | EXECUTION_PACKAGE | Do not issue verdict; complete all 6 mandatory outputs first |

**Not a failure scenario:** `JSONL Writer: BLOCKED` in the command center is an
integrity-status input label (`N70_READINESS_STATUS.md` §stale dependency findings).
It does not indicate a blocked trigger path.

---

## 10. Question Answers

### Q1: What file/operator action officially opens N70?

There is no single file that opens N70. The sequence is:

1. **Detection:** `eth-yes-fc-os-accumulation-monitor` (daily heartbeat, 09:00 UTC)
   detects canonical_n ≥ 70 and issues a **notify-only** alert.
   Nothing auto-executes.
2. **Operator action:** the operator manually runs the 7-command N70 Review Command
   suite (canonical export → command center → drift audit → pytest → py_compile →
   git diff → git status).
3. **Confirmation:** all 6 trigger conditions in `N70_RUNBOOK.md` §N70 Trigger
   Conditions must be TRUE.
4. **Official opening:** the operator begins `N70_EXECUTION_PACKAGE.md` §Mandatory
   N70 Workflow Step 1 — *"Freeze the raw evidence window at the moment canonical
   n first equals 70."*

The `canonical_regime_export.py` output reporting canonical_n=70 with PASS
validation is the primary gating signal. The automation's notify-only design is
precisely why manual operator approval is required — nothing proceeds automatically.

### Q2: Which document becomes authoritative?

**`docs/research/N70_EXECUTION_PACKAGE.md`** is the sole governing checklist at N70.

`N70_RUNBOOK.md` explicitly defers to it: *"Use `docs/research/N70_EXECUTION_PACKAGE.md`
and `docs/research/frontiers/N70_PREFLIGHT_AUDIT.md` as the governing checklist."*

**`docs/research/N70_SNAPSHOT_REVIEW.md`** becomes the one-shot governor review
record, created fresh at N70. It does not yet exist — this is expected and
confirmed correct (`N70_PRELAUNCH_CHECKLIST.md` §5).

### Q3: What metrics are frozen at trigger time?

**What is frozen (Step 1):** the raw evidence window — the 70-trade canonical
set in `canonical_regime_enriched_trades_v1.csv` at the moment n first equals 70.
This is the input data; it is frozen to prevent drift during the review session.

**What is computed from the frozen set** (not frozen themselves):

| Category | Computed metrics |
|---|---|
| Cumulative | WR, PF, W/L count, gross win/loss PnL, net PnL, median PnL, p-value |
| New block (n=62–70) | Block WR, block PF, block PnL, block regime mix |
| Drift | nc_PF (rolling 20-trade, excl. COMPRESSION), consecutive-below-1.0 count |
| Regime | COMPRESSION share, TREND_UP count, TREND_DOWN count, SIDEWAY count |
| Kill criteria | K1–K4 evaluation results |
| Promotion gates | P1–P5 evaluation results |
| Velocity | 7d/14d/since-n61 rates; ETA to n=80, n=100 |

### Q4: What outputs must be generated?

See §8 (Check 7) above. Summary: 6 mandatory documents + 7 tool/test commands.
`N70_SNAPSHOT_REVIEW.md` is created fresh; the 5 other mandatory documents are
updated. One optional document (`CANONICAL_N70_REPRODUCIBILITY_AUDIT.md`) is
generated only if reconciliation uncertainty arises.

### Q5: What conditions can block N70 even if n >= 70?

From `N70_RUNBOOK.md` §Failure Modes and `N70_PREFLIGHT_AUDIT.md` §Blockers:

1. Export validation FAIL (most critical — stops all downstream steps)
2. Regime join rate < 95% (unexplained UNKNOWN regimes)
3. Duplicate count unexplained / not reconciled
4. Drift audit cannot run (tool error)
5. Runtime / code / config / strategy mutations bundled with the review
6. UNKNOWN regime rate rises materially from 0.0% baseline

Additionally: kill criterion activation (K1–K4) during analysis does not block
N70 from opening, but drives a FAIL_REVIEW_REQUIRED governor verdict rather
than CONTINUE_ACCUMULATION.

### Q6: Is manual operator approval required?

**YES — unambiguously.** Three independent sources confirm this:

1. **`N70_EXECUTION_PACKAGE.md` §Governor Review Checklist:** 15 questions must
   be answered by the governor before a verdict is issued.
2. **`N70_PREFLIGHT_AUDIT.md` §Estimated Runtime:** "Manual governor review:
   15–30 minutes" — the longest single phase in the execution timeline.
3. **`N70_RUNBOOK.md` §Automation Audit:** `eth-yes-fc-os-accumulation-monitor`
   scope = notify-only. No automation issues verdicts.

The three possible N70 verdicts — `CONTINUE_ACCUMULATION` / `CAUTION_DRIFT_REVIEW` /
`FAIL_REVIEW_REQUIRED` — are issued by the governor, not by any tool or
automation. This vocabulary is distinct from the current waiting-state vocabulary
(`CONTINUE_WAITING` / `OPEN_N70_PACKAGE` / `RESEARCH_REVIEW_REQUIRED`) and from
this audit's own verdict vocabulary (READY / CAUTION / BLOCKED).

---

## 11. Cross-Document Discrepancies

Two discrepancies are surfaced and resolved.

### D1: Comparison Baseline — n=61 vs n=62

**Primary discrepancy. Affects new-block size calculation.**

| Document | Stated baseline | Implied new-block size |
|---|---|---|
| `N70_EXECUTION_PACKAGE.md` line 49 | n=61 (locked canonical state) | 9 trades (n=62 through n=70) |
| `N70_RUNBOOK.md` baseline table | n=62 (WR=56.5%, PF=1.980, nc_PF=2.367) | 8 trades (n=63 through n=70) |
| `N70_PREFLIGHT_AUDIT.md` line 92 | n=62 current baseline | 8 trades |

**Resolution:** `N70_EXECUTION_PACKAGE.md` is the governing checklist; `N70_RUNBOOK.md`
explicitly defers to it. The n=61 comparison baseline and 9-trade new block
(n=62–70) govern all analysis.

The RUNBOOK and PREFLIGHT references to n=62 describe the current-state operational
baseline at the time those documents were written (2026-06-08), not the locked
comparison baseline for the N70 analysis matrix. The EXECUTION_PACKAGE's locking
language is unambiguous: *"Use the locked n=61 canonical state as the comparison
baseline."*

**The n=61 baseline is not stale.** It is a deliberately locked comparison anchor
by design — not an outdated figure. The RUNBOOK/PREFLIGHT n=62 references will
be superseded by n=67 (current) by the time N70 executes.

### D2: Trigger Condition Count — 6 vs 7

| Document | Condition count |
|---|---|
| `N70_RUNBOOK.md` §N70 Trigger Conditions | 6 conditions |
| `N70_READINESS_TRACKER.md` §N70 Trigger Rule | 7 conditions |

**Resolution:** not a material conflict. The 7th condition in the tracker —
*"UNKNOWN regime rate is reviewed and explained"* — is implied by runbook
condition 4 (*"regime join rate ≥ 95%"*). A join rate of ≥ 95% with zero
unexplained UNKNOWN records satisfies both formulations. The tracker's 7-condition
form is more explicit; the runbook's 6-condition form is the operational checklist
used at execution time.

---

## 12. Open Cautions

### C1 — Legacy CSV Default Path (pre-existing, governance hygiene)

Pre-existing item documented in `N70_READINESS_STATUS.md`, `N70_DRY_RUN_STATUS.md`,
`N70_WAITING_STATE_HEALTHCHECK.md`, and `N70_PRELAUNCH_CHECKLIST.md` (all 2026-06-09).

| Location | Legacy reference |
|---|---|
| `tools/eth_yes_fc_os_command_center.py:14` | `DEFAULT_CSV_PATH = completed_trades_v1_2.csv` |
| `tools/_drift_audit.py:4,44` | Legacy fallback reference to `completed_trades_v1_2.csv` |

Bar set by `N70_READINESS_STATUS.md`:
> *"Before declaring full READY, clear or explicitly accept the legacy
> completed-trades fallback/default in active tooling."*

Bar not cleared. **Operational impact: none.** All N70 Review Commands use
explicit `--path`. The legacy default is never exercised. Active report confirmed
healthy by `N70_READINESS_STATUS.md`.

This governance hygiene item prevents the path audit from issuing a READY verdict
until the bar is cleared or explicitly accepted by the governor. It does not block
the trigger path from executing.

### C2 — TREND_UP Expansion Watch (forward note for N70 snapshot governor)

n_TREND_UP = 10; notification threshold = 14. Four more qualifying TREND_UP
trades to alert.

With 3 trades remaining to n=70, the alert threshold will not be reached from
n=67 alone (3 trades cannot add 4 to TREND_UP count). However, TREND_UP count
will be evaluated as part of the N70 snapshot's 17-item analysis matrix. The
snapshot governor will compare n_TU at n=70 against the n=61 baseline (n_TU=7 at
n=61). TREND_UP PF at last check = 0.661 (sub-1.0 sub-regime). Not a kill
criterion at current n; not a path blocker.

---

## Summary

| Check | Finding | Status |
|---|---|---|
| Check 1: Canonical export path | Tool clean; filter chain confirmed; PASS/FRESH at n=67 | ✅ OPERATIONAL |
| Check 2: Command center path | Explicit --path bypasses C1; n confirmed | ✅ OPERATIONAL |
| Check 3: Drift audit path | Explicit --path bypasses C1; nc_PF=2.921 CLEAR | ✅ OPERATIONAL |
| Check 4: Tracker update path | Target exists; update at Step 13 of 13 | ✅ OPERATIONAL |
| Check 5: N70 package trigger | 6 conditions documented; 13-step workflow confirmed | ✅ OPERATIONAL |
| Check 6: Required inputs | All 6 present and current | ✅ ALL PRESENT |
| Check 7: Required outputs | 6 mandatory + 1 optional; N70_SNAPSHOT_REVIEW correctly absent | ✅ ALL READY |
| Check 8: Failure scenarios | 12 failure modes documented; 3 governing sources | ✅ DOCUMENTED |
| Q1: What officially opens N70? | Operator runs export confirming n=70 + 6 trigger conditions | ✅ UNAMBIGUOUS |
| Q2: Authoritative document | `N70_EXECUTION_PACKAGE.md` — RUNBOOK defers to it explicitly | ✅ IDENTIFIED |
| Q3: Metrics frozen | Raw evidence window (70-trade canonical set); metrics computed from it | ✅ DEFINED |
| Q4: Required outputs | 6 mandatory + 1 optional docs + 7 tool/test runs | ✅ ENUMERATED |
| Q5: Conditions blocking at n≥70 | 6 blocker conditions: export FAIL / regime / dup / drift / mutation / UNKNOWN | ✅ DOCUMENTED |
| Q6: Manual approval required? | YES — 15-question governor checklist; automation notify-only | ✅ CONFIRMED |
| D1: n=61 vs n=62 baseline | n=61 / 9-trade block governs (EXECUTION_PACKAGE is authoritative) | ✅ RESOLVED |
| D2: 6 vs 7 trigger conditions | Not material; 7th implied by 6th | ✅ RESOLVED |
| C1: Legacy CSV governance bar | Pre-existing, non-blocking; 4 sibling docs also CAUTION for this | ⚠️ OPEN |
| C2: TREND_UP watch | Forward note for snapshot governor; not a path blocker | ⚠️ WATCH |

**When n reaches 70: automation notifies → operator runs N70 Review Commands
→ confirm all 6 trigger conditions → begin N70_EXECUTION_PACKAGE.md Step 1.**

---

*Offline/reporting only. No runtime, strategy, risk, or execution changes.
No commits authorized by this document.*
