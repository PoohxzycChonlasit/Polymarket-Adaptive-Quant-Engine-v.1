# ETH YES FC OS — Campaign Status Dashboard

type: campaign_dashboard
generated_at: 2026-06-06
campaign_phase: VERIFICATION_ACCUMULATION
cell: ETH × YES × FIRST_CYCLE × OPENING_SCAN × hold > 15s
source_docs:
  - docs/research/verification_tracker.md
  - docs/research/evidence_velocity_dashboard.md
  - docs/research/watchlists/ETH_YES_FC_OS.md
  - docs/research/frontiers/COMPRESSION_MARKET_ARCHETYPE.md
  - docs/research/frontiers/OPENING_SCAN_COVERAGE_BOTTLENECK.md
  - docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md
  - CURRENT_PROJECT_STATUS.md
code_changed: No
strategy_changed: No
runtime_changed: No

> This document is a read-only executive summary. No section authorizes a runtime
> change, strategy change, risk change, execution change, or promotion decision.

---

## 1. Campaign Status

| Field | Value |
|---|---|
| **Status** | `VERIFICATION_IN_PROGRESS` |
| **Campaign phase** | `VERIFICATION_ACCUMULATION` |
| **Positive path evidence** | `POSITIVE_PATH_EVIDENCE` |
| **Kill criteria triggered** | 0 / 4 |
| **Promotion criteria met** | 3 / 5 |
| **Hard blockers** | n < 100 · p-value > 0.05 |
| **Last updated** | 2026-06-06 |

---

## 2. Progress

```text
n = 61 / 100   [#########################-----------]   61.0%
               ←———————————— 39 remaining ————————————→
```

| Metric | Value |
|---|---|
| Canonical n | **61** |
| Target n | 100 |
| Remaining | 39 |
| Completion | 61.0% |
| W23 addition | 1 qualifying trade (SIDEWAY, TP, Jun 6, +$0.01160556) |

> WR, PF, and robustness metrics below are from the n=60 snapshot (verified
> baseline). The W23 Jun 6 trade is included in the n=61 count but the next
> official snapshot triggers at n=70.

---

## 3. Snapshot History

| Snapshot | n | Status | WR | PF | Notes |
|---|---|---|---|---|---|
| n=60 | 60 | ✅ Verified baseline | 58.1% | 2.055 | W21+W22 accumulation, robustness 91/100 |
| n=61 | 61 | Current (pre-snapshot) | ~58% est. | ~2.0 est. | W23 SIDEWAY TP Jun 6 added; no formal snapshot yet |
| n=70 | — | Pending | — | — | Trigger: +9 qualifying trades; full snapshot required |
| n=100 | — | Target | — | — | All 5 promotion criteria evaluated simultaneously |

Next snapshot trigger: n ≥ 70. Required action: full WR, PF, week count, path
match rate, and regime composition update.

---

## 4. Promotion Criteria

All five must be met simultaneously on the same snapshot.

| # | Criterion | Current | Target | Status |
|---|---|---|---|---|
| 1 | n ≥ 100 | **61** | 100 | ❌ need 39 more |
| 2 | Win Rate > 52% | **58.1%** | > 52% | ✅ passing |
| 3 | Profit Factor > 1.5 | **2.055** | > 1.5 | ✅ passing |
| 4 | p-value < 0.05 | **0.126** | < 0.05 | ❌ need n ≈ 105 at current WR |
| 5 | ≥ 3 calendar weeks | **3** (W21, W22, W23) | ≥ 3 | ✅ met (W23 has 1 trade) |

**Criteria met: 3 / 5**
**Hard blockers: n < 100 · p-value > 0.05**

Supporting metrics (n=60 snapshot):

| Metric | Value |
|---|---|
| Net PnL | +$0.205 |
| Median PnL per trade | +$0.006 |
| Robustness score | 91 / 100 |

---

## 5. Kill Criteria

| # | Criterion | Threshold | Current | Status |
|---|---|---|---|---|
| 1 | WR collapse | < 48% on ≥ 30 new trades | WR = 58.1% | ✅ not triggered |
| 2 | PF collapse | < 1.3 at n ≥ 80 | PF = 2.055 | ✅ not triggered |
| 3 | BTC exclusion invalid | BTC WR > 40% on n ≥ 20 | Not reached | ✅ not triggered |
| 4 | Concentration collapse | Excl. top-5 PF < 1.0 at n = 100 | PF = 1.441 now | ✅ not triggered |

**Kill criteria triggered: 0 / 4**

**nc_PF trajectory monitoring (active — COMPRESSION-absent period):**
Rolling non-COMPRESSION PF (window=20) is the primary leading indicator while
COMPRESSION is absent. Historical range: 0.596 (trough, May 24–28) to 2.811
(peak, May 30). Kill criterion #2 (PF < 1.3 at n ≥ 80) activates in 9 trades
after n=70. If rolling nc_PF falls below 1.0 for more than 10 consecutive new
W23/W24 trades, flag for review before n=80. See §9 Drift Risk.

---

## 6. Evidence Velocity

| Window | Rate | ETA to n=100 | Calendar ETA |
|---|---:|---:|---|
| Today (Jun 6) | 1.00 / day | 39 days | 2026-07-15 |
| Rolling 7 days | **0.43 / day** | **91 days** | **2026-09-05** |
| Rolling 14 days | 2.07 / day | 19 days | 2026-06-25 |
| Historical active (May 18–31) | 4.29 / day | 9 days | 2026-06-15 |

**Current velocity status:** `ACCUMULATING_SLOWLY`

Cumulative growth:

```text
2026-05-18 →  1  #
2026-05-22 → 30  ##############################
2026-05-25 → 45  #############################################
2026-05-31 → 60  ############################################################
2026-06-01 → 60  ──── STALL (5-day gap, COMPRESSION collapse) ────
2026-06-06 → 61  #############################################################
```

Rolling 7-day rate (0.43/day) is dominated by the 5-day post-collapse stall. The
14-day blended (2.07/day) is a better proxy for the sustainable rate if COMPRESSION
recovers. COMPRESSION recovery to historical 43% share would restore ~4.3/day and
reduce ETA to approximately 9 days.

---

## 7. Regime Dependency

Regime breakdown within n=61 ETH YES FC OS canonical trades:

| Regime | n | Share | PF (est.) | Current Eval Frequency | Status |
|---|---|---|---|---|---|
| **COMPRESSION** | **21** | **34.4%** | **3.372** | **2.5%** (was 43.1%) | ⚠️ ABSENT |
| TREND_DOWN | 18–19 | 29.5% | ~2.271 | 36.5% | ✅ Active |
| SIDEWAY | 15 | 24.6% | 1.258 | 27.2% | ✅ Active |
| TREND_UP | 7 | 11.5% | 0.661 | 18.8% | ⚠️ Below 1.0 |

Note: TREND_DOWN n has a pending ±1 reconciliation (duplicate timestamp in W22 data).

**COMPRESSION dependency:**
- COMPRESSION contributes 64% of net PnL from 35% of trades (PF = 3.372)
- COMPRESSION has been absent since 2026-06-01 12:00 UTC (MARKET_STRUCTURE_SHIFT, not a runtime defect)
- Post-collapse share: 2.5% vs historical 43.1% — a 17× reduction
- Without COMPRESSION: estimated non-COMPRESSION PF ≈ 1.45, above the 1.5 threshold but with reduced buffer

**TREND_DOWN sub-regime note (monitoring only, not a runtime filter):**
Compression-environment hypothesis from W21/W22 causality audit:
- ETH cs < 0.50 at entry → WR = 100% (n = 6, directional only)
- ETH cs ≥ 0.60 at entry → WR = 0% (n = 3, directional only)
- BTC = TREND_DOWN at entry → WR = 86% (n = 7, directional only)
- BTC = COMPRESSION at entry → WR = 30% (n = 10, directional only)
These are collinear (same market-wide compression signal). Neither authorizes a runtime filter at current n.

**W21 vs W22 PF gap** (1.491 vs 4.180): explained by W22's lower BTC-COMP exposure
(38% vs W21's 64%), not better entries, liquidity, or session effects. Within matched
BTC regime environments W21 and W22 perform comparably.

**TREND_UP warning:** PF = 0.661. This is the only sub-regime below 1.0. If
TREND_UP share grows while COMPRESSION remains absent, cumulative PF faces
increasing drag. Monitor at the n=70 snapshot.

---

## 8. Evidence Quality

Path truth and robustness (n=60 snapshot):

| Test | Result | Verdict |
|---|---|---|
| Path truth match rate | 47% (28 / 60) | Partial — pre-May 24 exit paths unlogged by design |
| Matched-sample PF | 2.338 | Consistent with full-cell PF = 2.055 ✓ |
| MFE median (matched) | +$0.00592 | Positions reach meaningful positive territory |
| MAE median (matched) | −$0.00097 | Minimal adverse excursion on losers |
| MFE > 0 | 79% (22 / 28) | 4 in 5 trades reach positive unrealized PnL |
| Clean-path → winner rate | 100% (17 / 17) | Every clean path confirmed as win |
| Exit efficiency (winners) | 1.000 | TP exits capture full available MFE |
| Bootstrap p5 | **1.261** | Floor above 1.0 at 5th percentile ✅ |
| Bootstrap PF > 1.0 rate | 99.5% (2,000 resamples) | ✅ |
| LODO minimum PF | **1.909** (excl. May 26) | All 13 active dates produce positive PF ✅ |
| Excl. top-5 trades PF | 1.441 | Above 1.0 threshold ✅ |
| First-half PF | 1.764 | Positive across both halves |
| Second-half PF | 2.462 | Improving directional trend ✅ |
| Win/loss streak independence | χ² = 0.03 | Independent — no streak dependence ✅ |
| Day-profit rate | 92% (12 / 13 dates) | High day-level consistency ✅ |
| **Robustness score** | **91 / 100** | ✅ |

**Path truth verdict:** POSITIVE. Edge is real, exits are not premature, losers are
genuine adverse moves. ENTRY_MODEL_TRUTH_ENVELOPE_V1 is PAPER_VALIDATED.

**Truth ladder position:** Signal Truth ✅ → Path Truth ✅ → Executable Truth ❌ (not reached)

Executable Truth requires n=100 and p<0.05. Currently in Path Truth phase.

---

## 9. Drift Risk

**Source:** [ETH_YES_FC_OS_DRIFT_AUDIT.md](ETH_YES_FC_OS_DRIFT_AUDIT.md) (2026-06-06)

### 9a. Regime Drift

`CONFIRMED`. W21 → W22 regime composition shifted:

| Regime | W21 share | W22 share | Direction |
|---|---|---|---|
| TREND_DOWN | 28% | 36% | +8 pp — became dominant |
| COMPRESSION | 36% | 32% | −4 pp — fell to secondary |
| SIDEWAY | 23% | 23% | flat |
| TREND_UP | 13% | 9% | −4 pp |

The regime sequence across 61 trades comprises 34 distinct same-regime runs
(avg run = 1.8 trades). No single regime holds for more than 5 consecutive
trades. The mix is structurally interleaved, not phase-separated.

### 9b. Edge Drift — Three-Phase Structure

`CONFIRMED` — midgame trough, complete late recovery.

| Phase | Idx | WR | PF | Character |
|---|---|---|---|---|
| Early | #1–#20 | 55.0% | **2.020** | COMP + TD dominant |
| **Mid** | **#21–#40** | **50.0%** | **1.613** | **Trough. May 22–25. SIDEWAY + TU losses.** |
| Late | #41–#61 | 66.7% | **2.622** | TD-led win run + COMP finish |

Mid-phase minimum: rolling WR = 45%, rolling PF = 1.257 (index #31, May 23).

The trough was compositional — elevated SIDEWAY and TREND_UP exposure with
reduced COMPRESSION share. Full recovery by index #52 (May 28) when the
TREND_DOWN win cluster flushed trough losses from the rolling window.

### 9c. Non-COMPRESSION PF (nc_PF) — Primary Leading Risk Indicator

The rolling non-COMPRESSION PF (nc_PF, window=20) was negative (< 1.0) for
**14 consecutive index points: #38 through #51 (May 24–28)**.

| Stat | Value |
|---|---|
| nc_PF trough | **0.596** (index #45, May 25) |
| nc_PF negative zone | #38–#51 — 14 consecutive trades |
| nc_PF recovery above 1.0 | index #52 (May 28) |
| nc_PF at sequence end | **2.661** |

Recovery from the trough was driven by the May 28–29 TREND_DOWN win cluster
(4 of 5 wins at #51–#56) displacing the worst non-COMPRESSION losses from
the rolling window.

**Why this matters now:** COMPRESSION has been absent since 2026-06-01. All
new W23/W24 trades accumulate in non-COMPRESSION regimes. The nc_PF negative
zone demonstrates that the non-COMPRESSION sub-population can sustain a
prolonged loss period (14 trades, PF trough 0.596) before recovering. If
new SIDEWAY + TREND_UP trades cluster without sufficient TREND_DOWN wins to
counteract them, nc_PF can re-enter negative territory.

### 9d. SIDEWAY — Weak and Borderline

From drift audit (CSV canonical source, n=14):

| Metric | Value | Prior reported | Delta |
|---|---|---|---|
| n | 14 | 15 | −1 (deduplication) |
| WR | 57.1% | ~47% | discrepancy across sources |
| PF | **1.123** | 1.258 | −0.135 |
| Net PnL | +$0.007 | +$0.021 | −$0.014 |

PF=1.123 over 14 trades is effectively break-even. SIDEWAY is the
primary accumulation vehicle during the current COMPRESSION-absent period
and provides the weakest edge of any positive regime. It should not be
relied upon to sustain the overall PF above the 1.5 promotion threshold
without TREND_DOWN support.

### 9e. Warning Rule (observability tripwire only)

> **If rolling nc_PF falls below 1.0 for more than 10 consecutive new
> trades in W23 or W24, flag for dedicated review before the n=80 milestone.**

This rule does not authorize any runtime, strategy, risk, execution, or
sizing change. It is a passive monitoring tripwire for the campaign observer.
The historical precedent (14-trade nc_PF negative zone) shows this condition
is possible under normal market variation and does not by itself constitute
an edge failure.

---

## 10. Research Intake (OPENING_SCAN Coverage)

Current run: `20260606T041414Z_23488_8bde4b5d`

| Metric | Value |
|---|---|
| OPENING_SCAN-ready candidates | 543 |
| OPENING_SCAN-covered candidates | 280 |
| **Overall coverage rate** | **51.6%** |
| Missed after OPENING_SCAN | 266 |
| **ETH YES coverage** | **44%** |
| ETH YES misses | 44 |
| Medium-quality missed candidates | 156 |
| High-quality missed candidates | **0** |
| OPENING_SCAN window duration | 35 seconds |

**Bottleneck classification:** `RESEARCH_INTAKE_LOSS_CONFIRMED`

This is NOT proven PnL loss. Zero high-quality misses means missed candidates would
still likely fail downstream entry, risk, EV, or execution gates. The bottleneck is
first-decision timing, not market unavailability.

**Coverage status:** `COVERAGE_BOTTLENECK` (coverage < 60%)

Required next step: observability tooling design phase only. No scheduling changes,
lifecycle changes, or filter activations are authorized from this evidence.

---

## 11. Runtime Integrity

| System | Status | Evidence |
|---|---|---|
| Runtime Ownership v1 | ✅ `PAPER_VALIDATED` | Run 20260529T033511Z_32308_89dc46d3 |
| Exception Observability v1 | ✅ `PAPER_VALIDATED` | 77 natural exception rows confirmed |
| ENTRY_MODEL_TRUTH_ENVELOPE_V1 | ✅ `PAPER_VALIDATED` | 5 / 5 JSONL categories confirmed |
| **JSONL Writer Integrity v1.1** | ⚠️ `BLOCKED` | Interprocess locking not implemented |

**Active integrity risk:** JSONL_WRITER_INTEGRITY_V1_1 is the only remaining
unmitigated evidence threat. Duplicate writes from overlapping paper sessions can
contaminate the canonical trade table without detection. Runtime Ownership v1
reduces (but does not eliminate) concurrent writer risk.

**Evidence cleanliness rule:** For analysis covering pre-May-29 overlap periods,
prefer run-scoped analysis only. Post-May-29 evidence should be clean under the
Runtime Ownership v1 single-writer guard.

---

## 12. Campaign Health Score

Scored at the n=61 / 2026-06-06 state. Each dimension rated on a 0–10 scale.

| Dimension | Score | Notes |
|---|---|---|
| **Evidence Quality** | **9 / 10** | Bootstrap p5=1.261, LODO min 1.909, robustness 91/100, clean-path→win 100%, day-profit 92%. Path truth partial (47% match) — pre-May 24 gap by design, not defect. |
| **Velocity** | **4 / 10** | Rolling 7d=0.43/day dominated by 5-day stall. 14d=2.07/day more representative. COMPRESSION absence is the primary velocity suppressor. Accumulation has resumed but is slow. |
| **Runtime Integrity** | **7 / 10** | 3 of 4 reliability systems PAPER_VALIDATED. One active BLOCKED item (JSONL writer locking) with no current contamination event but unresolved design gap. |
| **Verification Progress** | **6 / 10** | 61/100 canonical trades (61%), 3/5 promotion criteria met. Both hard blockers (n, p-value) are accumulation-only problems — no analytical fix available. |
| **Overall Campaign Health** | **6.5 / 10** | Healthy edge, real evidence, no kill criteria triggered. Primary constraint is COMPRESSION absence suppressing velocity. Campaign is on track but pace is uncertain. |

**Health interpretation:**
- 8–10: Healthy and accelerating
- 6–7: Healthy but constrained — monitor the constraint
- 4–5: At risk — investigate before continuing
- 0–3: Escalate immediately

Current state: **Healthy but velocity-constrained.** The edge quality is strong;
the accumulation rate is structurally suppressed by COMPRESSION absence. No action
required beyond continued accumulation and COMPRESSION monitoring.

---

## 13. Top Risks

| Rank | Risk | Severity | Proximity | Mitigation |
|---|---|---|---|---|
| 1 | **COMPRESSION absence** | Critical | Active now | Passive monitor; wait for market-structure recovery |
| 2 | **JSONL writer integrity BLOCKED** | High | Ongoing | Design-only scope before a contamination event occurs |
| 3 | **Statistical power gap** (p=0.126 vs 0.05) | High | 39–44 trades away | Continue accumulation; no shortcut available |
| 4 | **nc_PF drift risk** | Medium | Active now | Non-COMPRESSION PF was < 1.0 for 14 consecutive trades historically; could recur with SIDEWAY+TU clustering. Monitor rolling nc_PF. |
| 5 | **TREND_DOWN W22 concentration** | Medium | Latent | n=8 with 2 losses; composition effect, not structural signal |
| 6 | **Evidence velocity degraded** | Medium | Active now | 0.43/day rolling 7d; watch COMPRESSION recovery |
| 7 | **TREND_UP drag** | Medium | Growing | PF=0.661 at n=7; monitor share at n=70 snapshot |
| 8 | **SIDEWAY edge weak** | Medium | Active now | PF=1.123 at n=14 (break-even); primary non-COMP vehicle; insufficient n to confirm edge |
| 9 | **Zero-production episodes** | Low | Episodic | Episode #5: 22h44m zero trades; can halt accumulation |
| 10 | **Dormant failure-mode frontiers** | Low | Deferred | MICRO_RECOVERY / AI EV / BTC COMP calibration — dormant, not resolved |
| 11 | **Opening scan coverage gap** | Low | Ongoing | 44% ETH YES coverage; observability design phase only |

---

## 14. Next Milestones

| Milestone | Trigger | Estimated window | Required action |
|---|---|---|---|
| **n = 70** | +9 qualifying trades | ~Jun 12 (optimistic) → Jul (slow) | Full snapshot: WR, PF, week count, path match rate, regime breakdown, **rolling nc_PF trajectory** |
| **n = 80** | +19 trades | ~Jun 17 → Jul | Kill criterion #2 activates: PF must remain > 1.3. Re-run robustness battery. **Evaluate nc_PF trajectory; if nc_PF < 1.0 for > 10 consecutive new trades, escalate before this milestone.** |
| **n = 90** | +29 trades | ~Jun 22 → Aug | Prepare final verification audit checklist. Assess p-value trajectory. |
| **n = 100** | +39 trades | ~Jun 25 → Sep | Full verification audit: all 5 promotion criteria evaluated simultaneously. Governor review required before any status change. |
| **p < 0.05** | n ≈ 105 at WR=58.1% | Slightly after n=100 | Binomial significance threshold crossed. |

**COMPRESSION recovery trigger:** If COMPRESSION share recovers above 10% of
decision cycles for ≥ 3 consecutive days, revise all ETA projections to the
optimistic scenario (≈9-day horizon to n=100).

**TREND_DOWN review trigger:** When TREND_DOWN n reaches 30+, re-evaluate the
compression-environment hypothesis (ETH cs segmentation) with sufficient statistical
power.

**JSONL integrity design trigger:** Before the next sustained accumulation run,
scope a design-only solution for interprocess JSONL writer locking.

---

## 15. Governor Summary

**Status:** `VERIFICATION_IN_PROGRESS + POSITIVE_PATH_EVIDENCE`

**Evidence:** 61 canonical opportunities, 3 of 5 promotion criteria met
(WR=58.1% ✅, PF=2.055 ✅, 3 calendar weeks ✅), robustness 91/100. Bootstrap
floor p5=1.261. LODO minimum PF=1.909. The edge is real and has survived every
stress test applied to it.

**Hard blockers:** n < 100 and p-value > 0.05. Both require continued accumulation.
No analytical shortcut exists. The only valid action is running paper sessions.

**Structural risk:** COMPRESSION has been absent since 2026-06-01 12:00 UTC
(MARKET_STRUCTURE_SHIFT, not a runtime defect). COMPRESSION powers the campaign's
strongest sub-regime (PF=3.372, 64% of net PnL). Without it, estimated ongoing PF
from remaining regimes is approximately 1.45 — above the 1.5 promotion threshold
but with reduced margin. If TREND_UP drag grows while COMPRESSION remains absent,
the margin narrows further.

**Integrity risk:** JSONL_WRITER_INTEGRITY_V1_1 is the only unmitigated evidence
threat. Scope a design-only solution before a contamination event occurs.

**Drift risk:** The sequence audit (ETH_YES_FC_OS_DRIFT_AUDIT.md) confirmed
regime drift, edge drift, and a sustained non-COMPRESSION PF negative zone
(nc_PF < 1.0 for 14 consecutive trades, trough 0.596) during May 24–28.
All drift fully recovered by the end of the sequence (nc_PF = 2.661, rolling
PF = 2.521, rolling WR = 65%). The drift does not indicate ongoing deterioration
but it establishes the primary leading risk indicator for the current
COMPRESSION-absent accumulation period: rolling nc_PF. If nc_PF falls below
1.0 for more than 10 consecutive new W23/W24 trades, flag for review before n=80.

**Do not:**
- Promote the watchlist before all 5 criteria are met simultaneously
- Add runtime filters based on the compression-environment hypothesis (n=19)
- Treat TREND_DOWN W22 PF=4.180 as a stable structural signal (n=8, 2 losses)
- Treat the OPENING_SCAN coverage gap as proven PnL loss (0 high-quality misses)
- Treat dormant May 30 failure-mode frontiers as resolved
- Interpret COMPRESSION absence as a runtime defect or trigger system changes

**The campaign is healthy and on track. Accumulate. Monitor. Do not change.**

---

*Sources: verification_tracker.md (n=60 snapshot) · evidence_velocity_dashboard.md
(n=61 current) · COMPRESSION_MARKET_ARCHETYPE.md · OPENING_SCAN_COVERAGE_BOTTLENECK.md
· CURRENT_PROJECT_STATUS.md · W21 vs W22 Causality Audit (session 2026-06-06)*
*Drift audit: ETH_YES_FC_OS_DRIFT_AUDIT.md (2026-06-06) · n=61 sequence, window=20*

*No code changes. No runtime changes. No strategy changes. No commits. Evidence only.*
