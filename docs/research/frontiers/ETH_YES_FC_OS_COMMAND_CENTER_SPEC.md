---
type: command_center_spec
cell: ETH × YES × FIRST_CYCLE × OPENING_SCAN × hold > 15s
generated_at: 2026-06-07
n_at_spec: 61
code_changed: No
strategy_changed: No
runtime_changed: No
risk_changed: No
execution_changed: No
committed: No
---

# ETH YES FC OS — Verification Command Center Spec

**Operational dashboard design for VERIFICATION_IN_PROGRESS phase**

---

## Non-Authorization Clause

This is a design specification for an **observational dashboard maintained by the researcher by hand**.
It does not:

- Wire any metric into automated runtime decision-making
- Modify any alert, signal, or execution system
- Change risk gates, kill-switch logic, or order-intent validation
- Grant runtime authority to any offline tool or metric

All panels described below are for researcher monitoring only.
The project's offline-tools-are-evidence-only rule (CLAUDE.md § Architecture Rules) is not waived.
Governor sign-off is still required at every milestone named in §6 and before any lifecycle state transition.

---

## Design Principle

**Decision-relevance is the inclusion filter.**

A metric earns a daily slot on this command center only if a plausible value of it would
change what the researcher does — specifically: flag a risk, escalate to governor review,
revise an ETA, or trigger a milestone snapshot.

If no plausible value of the metric changes an action before the next formal milestone,
it is milestone-only (§6) or eliminated (§2).

This principle is what makes this document a *command center* rather than a
re-aggregation of the four existing source documents:

| Source document | Role |
|---|---|
| `verification_tracker.md` | Core criteria, robustness battery, path evidence, weekly log |
| `verification_lifecycle.md` | Governance lifecycle, state requirements, snapshot triggers |
| `ETH_YES_FC_OS_CAMPAIGN_DASHBOARD.md` | n=61 executive state across all dimensions |
| `ETH_YES_FC_OS_DRIFT_AUDIT.md` | Rolling series (PF/WR/nc_PF/COMP share), regime sequence |

Cross-document duplication is resolved by this spec being the single operational view.
Source documents remain authoritative for formal snapshot records.

---

## §1 — What Metrics Belong on the Command Center

### Promotion gate tracking (Panel A)

| Metric | Decision-relevance |
|---|---|
| n (canonical count) | Gates P1; changes with every qualifying trade |
| Cumulative WR | Gates P2; below 52% changes observer risk posture |
| Cumulative PF | Gates P3; approaching 1.5 triggers PF-erosion review |
| **n required for p<0.05 at current WR** | Actionable forward-looking transform of P4 (see §4); raw p-value is fully implied by n + WR and adds nothing |
| Calendar weeks with qualifying trades | Gates P5; advances only when a new calendar week yields a qualifying trade |

### Kill criterion monitors (Panel D)

| Metric | Decision-relevance |
|---|---|
| New-block WR since n=61 baseline (K1 precursor) | K1 activates at n_new=30; pre-monitoring from n_new≥15 gives early warning |
| Cumulative PF buffer above 1.3 (K2) | Activates at n=80; buffer (PF − 1.3) shows available runway; shrinkage is actionable |
| BTC WR on qualifying trades (K3) | Must stay below 40% on n_BTC≥20; confirms ETH exclusion validity |
| Excl. top-5 PF (K4) | Shown from n=80 onward as early indication; formally required at n=100 |

### Leading signals (Panel C)

| Metric | Decision-relevance |
|---|---|
| nc_PF rolling (w=20) | Primary leading indicator for PF trajectory; 14-consecutive-below-1.0 precedent; 1.0 tripwire is actionable |
| nc_PF consecutive-below-1.0 counter | Operationalizes the 10-trade tripwire; changes with each non-COMP qualifying trade |
| COMPRESSION share (rolling / post-collapse) | Root cause of velocity stall and nc_PF trough; observable every session without a qualifying trade |
| COMPRESSION-absence duration | Running counter since 2026-06-01 12:00 UTC; extended absence raises regime-dependency risk |
| BTC regime (daily observation) | Predicts TREND_DOWN quality (WR=86% BTC=TD; WR=30% BTC=COMP); observable without a qualifying trade |
| Evidence velocity (7d rolling) | Controls ETA; below 0.5/day warrants ETA revision |
| Days since last qualifying trade | Primary stall indicator; the single most relevant metric on zero-trade days |
| Recent regime sequence (last 5 trades) | Reveals compositional drift early; TREND_UP streak is actionable |

### Excluded from daily view

| Metric | Reason excluded | Disposition |
|---|---|---|
| Net PnL ($) | Derived from PF × gross losses; no information not already in PF | Milestone snapshots only |
| Median PnL | Useful at initial investigation; dominated by PF/WR once established | Milestone snapshots only |
| Raw p-value | Fully determined by n + WR; redundant with n-required transform | Shown as footnote; not a primary panel |
| Campaign health score (0–10) | Meta-aggregate of components already shown directly; adds indirection | Eliminated |
| Day-profit rate | 12/13 dates profitable at n=60; static until next snapshot | Milestone snapshots only |
| First/second-half PF split | Computed at n=60; static until n=70 snapshot | Milestone snapshots only |
| Bootstrap p5 / PF>1.0 rate | Fixed between snapshots | Milestone snapshots only |
| LODO min PF | Snapshot computation only | Milestone snapshots only |
| Win/loss streak χ² | One-time independence test; 0.03 confirmed at n=60 | Milestone snapshots only |
| MFE/MAE detailed table | Path truth analysis; stable | Milestone snapshots only |
| OPENING_SCAN coverage rate | Research bottleneck, not a verification gate | Eliminated from command center |
| Runtime integrity status | JSONL BLOCKED flag is a one-time defect; shown as a single line flag, not a panel | One-line status in Panel A |
| Rolling PF (w=20) | Converges to nc_PF at ~n=81 if COMPRESSION absent; see §2 | See §2 |
| Regime run table (34 runs) | Diagnostic context; not actionable daily | Milestone snapshots only |
| Three-phase edge structure (early/mid/late) | Historical summary; static | Milestone snapshots only |
| Evidence quality labels (DIRECT/PARTIAL) | Governance classification; not daily | Snapshot governance docs |

---

## §2 — What Metrics Are Redundant

Three distinct redundancy types — labeled because they are handled differently.

### Type 1: Cross-document duplication

Promotion criteria and kill criteria appear in `verification_tracker.md`,
`ETH_YES_FC_OS_CAMPAIGN_DASHBOARD.md`, and `ETH_YES_FC_OS_DRIFT_AUDIT.md`.
These are not "cut" — they are **consolidated here** as the single operational view.
Source documents remain authoritative for formal snapshot records.

### Type 2: Derived or implied

Metrics that are algebraically implied by other included metrics:

| Redundant metric | Implied by | Decision |
|---|---|---|
| Net PnL ($) | Fully implied by PF and total gross losses | Eliminated from daily; milestone footnote |
| Raw p-value | Exact function of n and cumulative WR (one-sided binomial) | Eliminated from daily; replaced by n-required transform |
| Campaign health score | Aggregate of WR, PF, velocity, runtime — all shown directly | Eliminated entirely |

### Type 3: Static results re-displayed daily

| Redundant metric | Why static | Decision |
|---|---|---|
| Day-profit rate | 12/13 dates profitable at n=60; won't move until next snapshot | Milestone only |
| First/second-half PF split | Computed at n=60; static until n=70 | Milestone only |
| Bootstrap p5 / PF>1.0 rate | 2,000-iteration resample; fixed until next snapshot | Milestone only |
| Win/loss streak χ² | 0.03 (independence confirmed at n=60); will not re-run daily | Milestone only |
| LODO min PF | 1.909 (all 13 dates at n=60); snapshot computation only | Milestone only |

### Special case: Rolling PF (w=20) vs nc_PF (w=20)

At n=61, the 20-trade window (#42–#61) still contains 5 COMPRESSION trades (#57–#60),
so rolling PF and nc_PF currently differ.

As non-COMPRESSION trades arrive and COMPRESSION remains absent, the COMPRESSION trades
roll out of the window. **By approximately n=81 (if COMPRESSION does not return),
rolling PF ≡ nc_PF** — the window becomes entirely non-COMPRESSION.

**Decision:** nc_PF is the primary daily metric.
It carries the established 1.0 tripwire, the 14-trade precedent (trades #38–#51),
and the operational definition (non-COMPRESSION edge quality only).
Rolling PF is eliminated from the daily view; note the structural convergence at n≈81.

---

## §3 — Leading Indicators

Metrics that indicate future state before the kill or promotion gate formally activates.

| Indicator | What it leads | Action threshold | Lead time before gate |
|---|---|---|---|
| **nc_PF rolling (w=20)** | Cumulative PF trajectory | < 1.0 for >10 consecutive new non-COMP trades → flag before n=80 | nc_PF trough at #45 preceded cumulative PF approaching 1.5 by ~15 trades |
| **COMPRESSION share** | Velocity and nc_PF direction | < 5% of decision cycles → COMPRESSION structurally absent | COMPRESSION collapse (Jun 1) preceded velocity stall by ~1 day |
| **COMPRESSION-absence duration** | Regime-dependency risk accumulation | > 7 days → document as MARKET_STRUCTURE_SHIFT | Concurrent; risk compounds with duration |
| **BTC regime (daily)** | TREND_DOWN quality | BTC=COMP → ETH-TD WR reverts toward 30% (vs 86% BTC=TD) | Simultaneous; observable before next qualifying trade |
| **Evidence velocity (7d rolling)** | n milestone ETA | < 0.5/day → stall flag; ETA revision required | Controls n trajectory; leads milestone timing by days to weeks |
| **Days since last qualifying trade** | Velocity stall onset | > 3 days → stall flag | Immediate; updates daily without a trade |
| **New-block WR (K1 precursor)** | K1 kill trigger | Rolling-15-trade WR on new trades < 45% → K1 risk elevated | K1 gate activates at n_new=30 (n≈91); precursor visible from n_new≥15 |
| **nc_PF consecutive-below-1.0 counter** | nc_PF trough depth | > 10 → flag for governor review before n=80 | Operationalizes the 14-trade precedent as an early-warning counter |

---

## §4 — Lagging Indicators

Metrics that describe current state from completed, irrevocable data.

| Indicator | What it describes | Update cadence |
|---|---|---|
| n (canonical) | Completed qualifying trades | Per qualifying trade |
| Cumulative WR | Win rate across all completed trades | Per qualifying trade |
| Cumulative PF | Profit factor across all completed trades | Per qualifying trade |
| Calendar weeks with qualifying trades | Session diversity (P5 gate) | Per calendar week |
| Net PnL ($) | Dollar result of all completed trades | Per qualifying trade |
| Bootstrap p5 | Lower-bound PF from completed sample (2,000 iterations) | Per formal snapshot |
| LODO min PF | Minimum PF excluding any one date | Per formal snapshot |
| Excl. top-5 PF (K4) | Concentration robustness | Per formal snapshot |
| Day-profit rate | Profitable dates / total dates | Per formal snapshot |
| First/second-half PF split | Temporal stability of edge | Per formal snapshot |
| Win/loss streak independence χ² | Serial correlation check | Once per formal snapshot |
| Path truth match rate | Verified path entries / total entries | Per formal snapshot |
| MFE/MAE summary | Trade quality (favorable vs adverse excursion) | Per formal snapshot |
| Regime breakdown (shares, WR, PF per regime) | Historical composition | Per formal snapshot |

**Note on the p-value transform:** "n required for p<0.05 at current WR" is computed
from lagging WR, but it reads as a forward-looking metric because it projects remaining
distance. It belongs in Panel B (Progress Rail) as the actionable P4 indicator.

At current WR=58.1%, the exact one-sided binomial requires n≈115–120 for p<0.05.
WR must reach 59.0% by n=100 for P4 to pass at exactly n=100.

| WR scenario | p at n=100 | Passes P4 at exactly n=100? |
|---|---|---|
| 58.1% (current sustained) | ≈0.067 ❌ | No — p<0.05 requires n≈115–120 total |
| 59.0% | ≈0.044 ✅ | Yes — 59 wins at n=100 is sufficient |

This table — not raw p-value — is the P4 display in Panel B.

---

## §5 — Daily Panel Specification

The daily view has four panels, checked in priority order.

**Operational cadence:** check every session, regardless of whether a qualifying trade occurred.
Panels A and B have new information only when n updates.
Panels C and D update every session and are the only panels with information on zero-trade days.

---

### Panel A: Gate Status [check first]

The binary go/no-go dashboard. Each row is ✅ PASS, ❌ FAIL, or INACTIVE.

**Promotion criteria — all 5 must pass simultaneously at n=100:**

| Gate | Criterion | Baseline (n=61) | Status |
|---|---|---|---|
| P1 | n ≥ 100 | 61 | ❌ |
| P2 | WR > 52% | 58.1% | ✅ |
| P3 | PF > 1.5 | 2.055 | ✅ |
| P4 | n required for p<0.05 ≤ 100 | ~115–120 at WR=58.1% | ❌ |
| P5 | ≥ 3 calendar weeks with qualifying trades | 3 (W21 / W22 / W23) | ✅ |

**Kill criteria — any one triggers termination:**

| Gate | Criterion | Baseline (n=61) | Status |
|---|---|---|---|
| K1 | new-block WR ≥ 48% on ≥30 new trades (baseline n=61) | n_new=1, earliest trigger n≈91 | INACTIVE |
| K2 | cumulative PF ≥ 1.3 at n ≥ 80 | 2.055 (inactive until n=80) | INACTIVE |
| K3 | BTC WR < 40% on n_BTC ≥ 20 | 9.1% on n_BTC=11 (insufficient n) | INACTIVE |
| K4 | excl. top-5 PF > 1.0 at n=100 | 1.441 informal (active at n=100) | INACTIVE |

**Runtime integrity (one-line flag):**

```
JSONL Writer Integrity: BLOCKED — duplicate write from overlapping sessions unmitigated
```

---

### Panel B: Progress Rail [check second]

N-centric view of promotion progress and ETA.

**n progress:**
```
n:     [====================>          ] 61 / 100
       |      |      |      |          |
      50     70     80     90        100
              ↑ next
n_new since baseline (n=61, 2026-06-06): [update daily]
```

**Cumulative metric snapshot:**

| Metric | Current | Target | Buffer |
|---|---|---|---|
| WR | 58.1% | > 52.0% | +6.1 pp |
| PF (cumulative) | 2.055 | > 1.5 | +0.555 |
| PF buffer above K2 floor | +0.755 | > 0 (K2 inactive until n=80) | — |

**P4 gate (n required for p<0.05 at current WR):**

| WR scenario | p at n=100 | Passes P4 at exactly n=100? |
|---|---|---|
| 58.1% (current sustained) | ≈0.067 ❌ | No — p<0.05 requires n≈115–120 total |
| 59.0% | ≈0.044 ✅ | Yes — 59 wins at n=100 is sufficient |

*Update WR row and n-required column after each qualifying trade.*

**ETA at current velocity:**

| Velocity | Trades remaining | ETA |
|---|---|---|
| 7d rolling: 0.43/day | 39 | ~91 days → ~Sep 5, 2026 |
| 14d rolling: 2.07/day | 39 | ~19 days → ~Jun 26, 2026 |
| Historical active: 4.29/day | 39 | ~9 days → ~Jun 16, 2026 (stale — COMPRESSION absent) |

---

### Panel C: Leading Indicators [check third]

**All observable on zero-trade days. Updated every session.**

**nc_PF monitor:**

| Metric | Baseline (n=61) | Tripwire | Status |
|---|---|---|---|
| nc_PF rolling (w=20) | 2.661 | < 1.0 → flag | ✅ |
| Consecutive-below-1.0 counter | 0 | > 10 → governor review before n=80 | ✅ |
| Historical max streak | 14 (#38–#51, May 24–28) | — | — |

*Update nc_PF and counter after each non-COMPRESSION qualifying trade.*

**Market structure:**

| Metric | Baseline (n=61) | Alert level | Status |
|---|---|---|---|
| COMPRESSION share (rolling) | ~2.5% | Historical base: 43.1%; < 5% → ABSENT | FLAG |
| COMPRESSION-absence duration | 6 days (since Jun 1 12:00 UTC) | > 7 days → MARKET_STRUCTURE_SHIFT | FLAG |
| BTC regime today | [observe each session] | BTC=COMP → ETH-TD quality degrades | — |

*Update COMPRESSION-absence duration daily. BTC regime: observe at session open.*

**Velocity / stall:**

| Metric | Baseline (n=61) | Alert level | Status |
|---|---|---|---|
| Days since last qualifying trade | 1 (Jun 6, SIDEWAY TP) | > 3 days → stall flag | ✅ |
| Evidence velocity (7d rolling) | 0.43/day | < 0.5/day → stall flag | FLAG |

*Update days-since daily. Update velocity after each qualifying trade.*

**Recent regime sequence (last 5 qualifying trades):**

| # | Regime | Outcome | Date |
|---|---|---|---|
| #57 | COMPRESSION | TP | — |
| #58 | COMPRESSION | TP | — |
| #59 | TREND_DOWN | TP | — |
| #60 | COMPRESSION | TP | — |
| #61 | SIDEWAY | TP | Jun 6, 2026 |

*Append new rows and drop oldest when n advances. TREND_UP entries warrant immediate review.*

---

### Panel D: Kill Criterion Monitors [check fourth]

**K1 monitor (new-block WR ≥ 48%):**

- Baseline: n=61, 2026-06-06
- n_new: 1 | WR_new: 100% (1 win / 1 trade)
- Earliest formal K1 trigger: n_new=30 → n≈91
- Pre-monitor: if rolling-15-trade WR on new trades falls below 45%, flag before K1 window completes
- Important: this criterion uses a **cumulative new-trade block**, not a rolling window

**K2 monitor (cumulative PF ≥ 1.3 at n ≥ 80):**

- Status: **INACTIVE until n=80**
- Current cumulative PF: 2.055 | Buffer above 1.3: +0.755
- Activates at n=80 (~19 new trades from baseline)
- This is **CUMULATIVE PF** — the rolling-PF trough of 1.257 at #31 was never a K2 event

**nc_PF tripwire (advisory — not a formal kill criterion):**

- Condition: rolling nc_PF < 1.0 for > 10 consecutive new non-COMPRESSION trades
- Current streak: 0
- Precedent: 14 consecutive below 1.0 at #38–#51 (May 24–28); sole recovery was TREND_DOWN win cluster
- Action: flag for governor review before n=80 if triggered; does not automatically terminate campaign

---

## §6 — Milestone-Only Metrics

These metrics are **not displayed daily**.
They are computed and recorded only at formal snapshot checkpoints.

---

### n=70 Snapshot (P0 required trigger: ≥10 new qualifying trades)

| Required computation | Notes |
|---|---|
| Formal WR, PF, net PnL record | Lock snapshot |
| Week count update (P5) | Confirm ≥ 3 calendar weeks |
| n-required transform update | Update Panel B P4 table |
| Regime breakdown vs n=61 baseline | COMP / TD / SW / TU shares, WR, PF; flag if TREND_UP share growing |
| nc_PF trajectory since n=61 | Plot rolling nc_PF for all W23/W24 new trades; confirm no streak below 1.0 |
| BTC-regime conditional TREND_DOWN WR | Split by BTC=TD vs BTC=COMP; update quality breakdown |
| Bootstrap quick-run (1,000 iterations) | p5 PF, PF>1.0 rate |
| LODO (all dates to n=70) | Min PF across all dates |
| Excl. top-5 PF | K4 informal early check |
| ETA revision | Update all three velocity scenarios in Panel B |
| Kill criteria formal evaluation | All four gates, with updated n |
| Governor sign-off | Required before any VIP→VERIFIED consideration |

---

### n=80 Snapshot (K2 activation + mandatory governor review)

| Required computation | Notes |
|---|---|
| All n=70 items | — |
| **K2 activation: cumulative PF ≥ 1.3 confirmed** | K2 is now live; if PF < 1.3 → FAILED_CANDIDATE |
| K1 evaluation: n_new=19 (approaching 30-trade window) | Review rolling-15-trade WR on new trades; flag if < 45% |
| nc_PF review: any streak below 1.0 for > 10 consecutive new trades? | If yes → flag; governor decides before proceeding to n=90 |
| Full robustness battery (2,000 bootstrap iterations) | Bootstrap p5, PF>1.0 rate, LODO all dates |
| First/second-half PF split update | Re-split at n=40 boundary |
| Win/loss streak independence re-run | χ² test on updated sequence |
| Day-profit rate update | Profitable dates / total dates |
| BTC-regime conditional WR update | Approaching n_BTC=20 for K3 activation power |
| Rolling PF (w=20) vs nc_PF comparison | Confirm convergence state; document if rolling PF ≡ nc_PF |
| Governor sign-off mandatory | Required before any work toward n=90 |

---

### n=90 Snapshot (pre-promotion preparation)

| Required computation | Notes |
|---|---|
| All n=80 items | — |
| P4 projection: WR trend, n-required estimate | Is p<0.05 still achievable at exactly n=100? |
| Promotion criteria status: all 5 with updated values | Identify which gates are at risk for final 10 trades |
| K1 window result: n_new=29 (block completes at n≈91) | Evaluate: WR of 29–30 new trades ≥ 48%? |
| Full snapshot for governor review | Pre-stage all materials for n=100 evaluation |

---

### n=100 Snapshot (promotion evaluation — governor sign-off mandatory before any transition)

| Required computation | Notes |
|---|---|
| All 5 promotion criteria simultaneously | ALL must pass; any single failure = not VERIFIED; delay, not terminate |
| Exact one-sided binomial p-value | P(X ≥ wins \| n=100, p=0.5) < 0.05 |
| All 4 kill criteria final evaluation | K4 (excl. top-5 PF > 1.0) now formally active |
| Full robustness battery | 2,000 bootstrap; LODO all dates; excl. top-5; first/second-half split |
| Session diversity | ≥ 70% of sessions support direction; no single session > 50% of all trades |
| Regime share final vs baseline | COMP share final; validate edge is not purely COMPRESSION-driven |
| BTC-regime conditional WR | Final split; validate K3 exclusion validity at n_BTC ≥ 20 |
| Path truth match rate | Final update; validated path-aware PF vs full-cell PF |
| JSONL integrity resolution | BLOCKED flag must be cleared or formally documented before VERIFIED |
| Formal VERIFIED application | Cannot change lifecycle state without governor sign-off |

---

## Quick-Reference Summary

### Daily check order

1. **Panel A — Gate Status:** binary go/no-go (promotion gates P1–P5, kill criteria K1–K4)
2. **Panel B — Progress Rail:** n, WR/PF vs targets, n-required transform table, ETA
3. **Panel C — Leading Indicators:** nc_PF, COMPRESSION, BTC regime, velocity, stall, last-5 sequence
4. **Panel D — Kill Criterion Monitors:** K1 new-block WR, K2 PF buffer (inactive until n=80), nc_PF advisory tripwire

### Leading vs lagging at a glance

| Leading (warns before gate activates) | Lagging (describes completed state) |
|---|---|
| nc_PF rolling (w=20) | Cumulative WR |
| nc_PF consecutive-below-1.0 counter | Cumulative PF |
| COMPRESSION share / absence duration | n |
| BTC regime (daily) | Calendar weeks |
| Evidence velocity (7d rolling) | Bootstrap p5 / LODO min PF |
| Days since last qualifying trade | Net PnL |
| New-block WR on ≥15 new trades (K1 precursor) | Excl. top-5 PF |

### Milestone-only (never daily)

Net PnL · median PnL · raw p-value · campaign health score · day-profit rate ·
first/second-half PF split · bootstrap runs · LODO computation · χ² independence test ·
MFE/MAE detailed table · regime run table · three-phase edge structure ·
OPENING_SCAN coverage rate · evidence quality labels

### Critical operational notes

1. **P4 gate:** n-required transform is the actionable form. At WR=58.1%, requirement is n≈115–120,
   not n=100. WR must reach 59.0% by n=100 for P4 to pass at exactly n=100.
   Delay, not terminal — resolves with ~10–50 additional trades if WR holds.

2. **Rolling PF ≡ nc_PF at ~n=81** if COMPRESSION remains absent.
   nc_PF is the daily primary. Rolling PF is eliminated from the daily view.

3. **K2 uses CUMULATIVE PF.** The rolling-PF trough of 1.257 at trade #31 was never a K2 event.
   K2 activates at n=80. Current cumulative PF buffer: +0.755 above the 1.3 floor.

4. **K1 baseline = n=61.** The 30-trade window completes at n≈91.
   Pre-monitor via rolling-15-trade WR from n_new≥15 onward.

5. **Zero-trade days:** Panel C (COMPRESSION share, BTC regime, days since last trade) is the
   only panel with new information. Check it every session regardless of qualifying trade activity.

6. **COMPRESSION absence.** Since 2026-06-01 12:00 UTC, COMPRESSION has contributed 2.5% of
   decision cycles vs 43.1% historically. This is documented as MARKET_STRUCTURE_SHIFT.
   It is the root cause of velocity stall and the driver of nc_PF trough risk.
   Until COMPRESSION returns or TREND_DOWN with BTC=TD sustains WR≥80%, the campaign's
   evidence velocity remains critically depressed.
