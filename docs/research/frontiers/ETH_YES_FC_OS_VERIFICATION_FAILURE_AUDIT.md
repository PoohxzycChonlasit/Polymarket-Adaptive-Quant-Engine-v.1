# ETH YES FC OS — Verification Failure Audit

type: failure_audit
cell: ETH × YES × FIRST_CYCLE × OPENING_SCAN × hold > 15s
generated_at: 2026-06-07
n_at_audit: 61
code_changed: No
strategy_changed: No
runtime_changed: No
risk_changed: No
execution_changed: No
committed: No

> READ ONLY. No section of this document authorizes a runtime change, strategy
> change, risk change, execution change, config change, or promotion decision.
> This is a forward-looking risk assessment only.

---

## Purpose

Determine what is most likely to prevent promotion even if canonical n reaches 100.

Key question: **what fails at n=100, and what can kill the campaign before n=100?**

These are two different problems with different characters:

- **Unmet gate at n=100 (delay):** The gate is not cleared at exactly n=100 but
  clears with additional trades if the edge remains intact. The cell is eventually
  promoted. Time cost: 5–30 additional trades.
- **Terminal failure (kills the campaign):** A kill criterion is triggered or the
  edge collapses permanently. The cell moves to FAILED_CANDIDATE. No promotion path.

A promotion failure audit must distinguish between these two outcomes. Confusing a
delay for a terminal failure is as costly as the reverse.

---

## 1. Criteria Reference

### 1a. Promotion Criteria (all 5 must be met simultaneously at n=100 snapshot)

| # | Criterion | Current (n=61) | Target | Status |
|---|---|---|---|---|
| P1 | n ≥ 100 | 61 | 100 | ❌ need 39 more |
| P2 | WR > 52% | 57.4% (CSV) / 58.1% (dedup) | > 52% | ✅ |
| P3 | PF > 1.5 | 2.022 (CSV) / 2.055 (dedup) | > 1.5 | ✅ |
| P4 | Binomial p-value < 0.05 | 0.126 | < 0.05 | ❌ |
| P5 | ≥ 3 calendar weeks | 3 (W21, W22, W23) | ≥ 3 | ✅ |

**Additional quality gates (non-blocking, but reviewed by governor):**
- Excl. top-5 PF > 1.0 at n=100 — current: 1.441 ✅
- LODO: all date-removals keep PF > 1.0 — current: min 1.909 ✅
- Bootstrap p5 > 1.0 — current: 1.261 ✅
- No unresolved join-key issue that materially changes the result — matched-sample
  PF=2.338 consistent with full-cell PF=2.055; path-truth mismatch does not
  materially change the result ✅ (noted but not blocking)

### 1b. Kill Criteria (any one terminates the campaign)

| # | Criterion | Measurement basis | Current | Status |
|---|---|---|---|---|
| K1 | WR < 48% over n ≥ 30 new trades | **Incremental block** of new trades since last baseline | WR=57.4% on existing | ✅ not triggered |
| K2 | PF < 1.3 at n ≥ 80 | **Cumulative** PF across full sequence | PF=2.022 on existing | ✅ not triggered |
| K3 | BTC exclusion invalid (BTC WR > 40% on n ≥ 20 new BTC trades) | Forward BTC block | BTC WR=9.1% (n=11) | ✅ not triggered |
| K4 | Concentration collapse (excl. top-5 PF < 1.0 at n=100) | Cumulative excl. top-5 at n=100 | 1.441 now | ✅ not triggered |

**Critical distinction for K2:** Kill criterion #2 uses **cumulative** PF, not rolling
PF. The drift audit's rolling-PF trough (1.257 at index #31) was a rolling-window
artifact — cumulative PF never approached 1.3. A future kill-criterion reviewer should
apply K2 to the cumulative series only.

---

## 2. Risk Register

Eight risks are assessed: probability of materializing between n=61 and n=100,
and impact if it does. Impact is defined as **severity** — terminal (kills campaign)
vs. delay (adds required trades) vs. drag (weakens metrics without killing).

### 2a. Summary Matrix

| Risk | Probability | Impact | Character |
|---|---|---|---|
| **p-value fails at n=100** | HIGH | MEDIUM | Delay — resolves with ~10-20 more trades if WR holds |
| **PF criterion erodes below 1.5 (nc_PF risk)** | MEDIUM | HIGH | Terminal — if cumulative PF < 1.5 at n=100 |
| **SIDEWAY contamination** | MEDIUM | LOW–MEDIUM | Drag — SIDEWAY PF=1.123 dilutes; weak but positive |
| **TREND_UP contamination** | MEDIUM | LOW–MEDIUM | Drag — TREND_UP PF=0.661 is structural negative |
| **Velocity stall** | HIGH | LOW | Delay — COMPRESSION absence extends timeline, not evidence quality |
| **Regime dependency (COMPRESSION absent)** | HIGH | HIGH | Root cause — drives risks above; structural until COMPRESSION returns |
| **Path-truth mismatch** | LOW | LOW | Quality note — matched-sample PF consistent; governor will note, not block |
| **Bootstrap instability** | LOW | LOW | Non-binding gate — p5=1.261 at n=60; more stable at n=100 |

### 2b. Detailed Risk Assessments

---

#### Risk 1: p-value fails to clear < 0.05 at n=100

**Probability: HIGH. Impact: MEDIUM (delay, not terminal).**

The p-value at n=100 depends on the cumulative WR through n=100. Using the exact
binomial (one-sided, null WR=0.50):

| Wins at n=100 | WR | p-value (exact binomial) | Result |
|---|---|---|---|
| 58 | 58.0% | ≈ 0.067 | ❌ fails |
| 59 | 59.0% | ≈ 0.044 | ✅ passes |
| 60 | 60.0% | ≈ 0.028 | ✅ passes |

**Implication:** To clear p<0.05 at exactly n=100, the cell needs **59+ wins — a
cumulative WR ≥ 59.0%.** The current WR is 57.4–58.1% (CSV vs. dedup). This means
even if the new 39 trades maintain exactly the historical WR, p-value fails at n=100
by a margin of 1–2 wins.

**WR projection for new 39 trades (non-COMPRESSION only, post-collapse):**

Historical non-COMP trade mix (TD=47.5%, SW=35.0%, TU=17.5%):
- Blended non-COMP WR ≈ 0.475×57.9% + 0.35×57.1% + 0.175×42.9% = 55.0%

| New-trade WR | Blended WR at n=100 | p at n=100 | p-value verdict |
|---|---|---|---|
| 60% | 58.4% | ≈ 0.045 | ✅ passes (barely) |
| 57.4% (historical) | 57.4% | ≈ 0.070 | ❌ fails |
| 55.0% (est. non-COMP) | 56.5% | ≈ 0.097 | ❌ fails |
| 50.0% | 54.6% | ≈ 0.135 | ❌ fails |

The central scenario (non-COMP blended WR ≈ 55%) puts n=100 p-value at approximately
0.09–0.10. Promotion would require additional accumulation past n=100.

**Tracker note:** The verification_tracker.md states "need n≈105 at WR=58.1% for p<0.05."
Under the exact binomial with continuity correction, this estimate is optimistic. At
sustained WR=58.1%, p<0.05 requires approximately n=115–120, not n=105. The tracker's
figure was derived from an uncorrected normal approximation. If WR drifts toward the
estimated non-COMP level (55%), the required n rises further to approximately n=150+.

**Character:** This is a DELAY risk, not a terminal one. The edge does not fail;
the significance gate moves. If WR holds, p<0.05 clears within 15–50 additional
trades beyond n=100. If WR deteriorates, this converges with Risk 2 (PF erosion).

---

#### Risk 2: PF criterion erodes below 1.5 at n=100

**Probability: MEDIUM. Impact: HIGH (terminal if cumulative PF < 1.5 at n=100).**

The cumulative PF at n=100 depends on the quality of 39 new non-COMP trades.

**Add-on PF calculation (historical non-COMP base):**

From regime stats (drift audit CSV, n=61):
- Non-COMP 40 trades (TD=19, SW=14, TU=7):
  - Gross wins: TD $0.122 + SW $0.064 + TU $0.019 = **$0.205**
  - Gross losses: TD $0.053 + SW $0.057 + TU $0.029 = **$0.139**
  - Add-on nc_PF = $0.205 / $0.139 = **1.476** (below the 1.5 promotion threshold)

**This is the central finding for PF risk:** every new non-COMP trade, on average,
adds at PF ≈ 1.47 — below the promotion threshold. The cumulative PF erodes
monotonically toward 1.47 as more non-COMP trades accumulate. COMPRESSION absence
removes the engine that has been carrying cumulative PF above 1.5.

| nc_PF of new 39 trades | Cumulative PF at n=100 | P3 verdict |
|---|---|---|
| 2.661 (historical nc_PF end value) | ≈ 2.09 | ✅ passes |
| **1.476 (historical non-COMP add-on)** | **≈ 1.79** | **✅ passes (central case)** |
| 1.0 (nc_PF break-even) | ≈ 1.51 | ✅ barely passes |
| 0.596 (historical nc_PF trough) | ≈ 1.28 | ❌ fails — also triggers K2 |

*Calculation basis: n=61 gross wins=$0.388, gross losses=$0.192. New-trade scenarios
scale nc_PF to estimate add-on gross wins and losses; cumulative PF = total gross
wins / total gross losses.*

**Central case:** cumulative PF ≈ 1.79 at n=100 — passes P3 with 0.29 PF units of
buffer. This is comfortable but not wide. The margin erodes monotonically as long as
COMPRESSION stays absent. If the campaign extends well past n=100 without COMPRESSION
recovery, cumulative PF asymptotes toward ≈ 1.47 — below the 1.5 threshold.

**Trough scenario:** The drift audit confirmed a 14-trade nc_PF negative zone
(nc_PF=0.596 at trough, index #38–#51, May 24–28). A repeat trough of similar
duration (14 of the 39 new trades at trough quality) could pull cumulative PF below
1.5 at n=100. This is also the path that approaches kill criterion K2 (PF<1.3 at
n≥80), though K2 (cumulative) requires an extreme and sustained trough to trigger
given the strong existing base.

**Character:** Terminal if triggered — PF<1.5 at n=100 means promotion criteria
are not met, and if cumulative PF also crosses 1.3 at n≥80, the campaign ends as
FAILED_CANDIDATE.

---

#### Risk 3: SIDEWAY contamination

**Probability: MEDIUM. Impact: LOW–MEDIUM (drag).**

SIDEWAY is the primary accumulation vehicle during the COMPRESSION-absent period.
Current stats: n=14, WR=57.1%, PF=1.123, net=+$0.007.

**Problems:**
1. PF=1.123 is effectively break-even. 14 trades is insufficient to confirm structural
   edge in SIDEWAY — bootstrap on 14-trade samples would show wide confidence intervals.
2. The win/loss ratio is below 1.0 (avg_win ≈ $0.008, avg_loss ≈ $0.010). Profitability
   depends entirely on WR staying above 50%. A brief WR dip (52% → 47%) flips SIDEWAY
   negative and contributes to nc_PF erosion.
3. SIDEWAY is expected to represent ~35% of post-collapse non-COMP trades. Over 39
   new trades, ~14 are likely SIDEWAY — approximately doubling current SIDEWAY n.
   If these 14 trades arrive at PF=1.0 instead of 1.123, cumulative PF drops by ~0.05
   PF units — a meaningful contribution but not catastrophic alone.

**Character:** Drag that amplifies Risk 2 if clustered with TREND_UP losses. SIDEWAY
alone cannot kill promotion, but SIDEWAY weakness combined with TREND_UP drag and no
COMPRESSION can make nc_PF trough recurrence more likely.

---

#### Risk 4: TREND_UP contamination

**Probability: MEDIUM. Impact: LOW–MEDIUM (structural drag).**

TREND_UP stats: n=7, WR=42.9%, PF=0.661, net=−$0.010. This is the only sub-regime
with PF below 1.0. All 7 trades are spread across the sequence (no clustering), which
is why cumulative PF has not been visibly dragged yet.

**Post-collapse TREND_UP share:** 18.8% of post-collapse decision cycles are TREND_UP.
At 39 new non-COMP trades, ~7 are expected TREND_UP — approximately doubling current
n to 14 TREND_UP trades. If those 7 new trades match historical (PF=0.661, WR=42.9%):
- New TREND_UP gross wins ≈ $0.019; new gross losses ≈ $0.029 (same as current 7 trades)
- Cumulative at n=100: TREND_UP adds −$0.010 net — small absolute drag but directionally
  worsening

**The BTC-regime dependence:** The W21/W22 causality audit found ETH TREND_DOWN WR
varies dramatically with BTC regime (WR=86% when BTC is also TREND_DOWN; WR=30% when
BTC is in macro COMPRESSION). TREND_UP is not documented to have the same pattern, but
if BTC shifts away from its current TREND_DOWN majority, TREND_UP performance may shift.

**Character:** Structural drag. TREND_UP cannot be excluded without changing the cell
definition. It contributes to nc_PF erosion when clustered with SIDEWAY losses (the
exact pattern that produced the historical 14-trade nc_PF negative zone: TU losses at
#38, #45 combined with SIDEWAY losses at #39, #44, #49).

---

#### Risk 5: Velocity stall

**Probability: HIGH. Impact: LOW (timing only, not evidence quality).**

Rolling 7-day rate: 0.43/day. Rolling 14-day rate: 2.07/day. Historical active rate:
4.29/day (before COMPRESSION collapse).

If velocity stays at 0.43/day, ETA to n=100 is 91 days (September 2026). At 14-day
blended rate, ETA is ~19 trading days. A velocity stall does not change the evidence
quality at n=100 — it only delays when n=100 is reached. However:
1. Long delays allow market conditions to shift further, possibly changing what the
   cell is measuring when n=100 finally arrives.
2. Extended SIDEWAY+TREND_DOWN accumulation without COMPRESSION recovery increases
   the probability of a SIDEWAY regime mix that triggers nc_PF erosion (Risk 2).

**Character:** Delay risk only. Does not prevent promotion at n=100 if edge holds.
Does extend the window over which other risks (Risks 2, 3, 4) can accumulate.

---

#### Risk 6: Regime dependency (COMPRESSION absent — root cause)

**Probability: HIGH (currently active since 2026-06-01). Impact: HIGH (root cause of all other risks).**

COMPRESSION has been absent since 2026-06-01 12:00 UTC (MARKET_STRUCTURE_SHIFT, not
a runtime defect). COMPRESSION drove 66.5% of net PnL from 34.4% of trades at PF=3.372.

**Structural math:** The add-on PF for the remaining 39 non-COMP trades is estimated
at ≈1.47 (below the 1.5 promotion threshold). This means COMPRESSION absence is not a
transient headwind — it is the structural constraint that makes every downstream risk
(WR drift, nc_PF erosion, PF threshold erosion) more likely to materialize.

**The TREND_DOWN quality signal:** Without COMPRESSION, the cell's survivability depends
entirely on TREND_DOWN quality. TREND_DOWN is the only non-COMP regime with PF
comfortably above 1.5 (PF=2.300, n=19). From the causality audit, TREND_DOWN WR=86%
when BTC is also TREND_DOWN vs. WR=30% when BTC is in macro COMPRESSION. Current BTC
is predominantly TREND_DOWN (36.5% of post-collapse decision cycles) — favorable. If
BTC shifts to COMPRESSION, TREND_DOWN performance could revert to 30% WR and:
- Kill criterion K1 risk (30-trade block WR < 48%) becomes active:
  0.475×30% + 0.35×57.1% + 0.175×42.9% ≈ 41.8% → triggers K1 at 30-trade new block
- nc_PF would enter negative territory, approaching the trough scenario in Risk 2

**Character:** Root cause driver. COMPRESSION absence is the single structural fact
that elevates all other risks above their baseline. COMPRESSION recovery would
simultaneously reduce all downstream risks.

---

#### Risk 7: Path-truth mismatch

**Probability: LOW. Impact: LOW (non-blocking quality note).**

Current path-truth match rate: 47% (28/60 trades). The gap is explained by design
(no path truth files before May 24) and a timing race for fast OS holds. The matched
sample PF=2.338 is consistent with full-cell PF=2.055 — the mismatch does not
materially change the result, which is the lifecycle gateway criterion
(verification_lifecycle.md: "no unresolved join-key or truth-field issue that
materially changes the result").

At n=100, the match rate will increase (all post-May 24 trades should have coverage).
Governor will note the 47% historical gap but it is unlikely to block promotion given
the demonstrated consistency.

**Character:** Quality documentation item. The governor review will note it; the
evidence itself does not contradict or materially alter the outcome claim.

---

#### Risk 8: Bootstrap instability

**Probability: LOW. Impact: LOW (non-binding gate).**

Bootstrap p5 (5th percentile of 2,000 resamples) = 1.261 at n=60 — well above 1.0.
Bootstrap is a supporting quality gate, not one of the 5 hard promotion criteria.
At n=100, the bootstrap distribution will tighten (more data). The p5 would need to
fall from 1.261 to below 1.0 to trigger concern. Given the structural positive edge
(WR=58%, PF=2.0), this requires an extreme trough concentration in the resamples.

**Character:** Non-blocking. Noted for completeness; not a meaningful failure path.

---

## 3. Ranked Failure Modes

Ranked by (probability × impact severity), distinguishing delay from terminal:

| Rank | Failure mode | Probability | Impact | Character | Path to resolution |
|---|---|---|---|---|---|
| **1** | **p-value fails at n=100** | HIGH | MEDIUM | **Delay** | Need 59% WR at n=100 (vs. est. 56-58%); resolve with ~10-50 additional trades |
| **2** | **PF erodes below 1.5 (nc_PF risk / trough)** | MEDIUM | HIGH | **Terminal** | nc_PF trough recurrence during COMPRESSION absence; TREND_DOWN quality is the key variable |
| **3** | **K1 triggered: 30-trade block WR<48%** | MEDIUM | HIGH | **Terminal** | If BTC shifts to COMPRESSION → TREND_DOWN WR reverts to 30% → blended WR ~42% |
| **4** | **TREND_UP drag worsening** | MEDIUM | LOW–MED | **Drag** | Cannot exclude; contributes to nc_PF erosion if share increases |
| **5** | **SIDEWAY contamination** | MEDIUM | LOW–MED | **Drag** | PF=1.123 at n=14; amplifies nc_PF risk if SIDEWAY WR dips below 50% |
| **6** | **Velocity stall (extended)** | HIGH | LOW | **Delay** | Timeline risk only; no impact on evidence quality at n=100 |
| **7** | **Regime dependency (COMPRESSION absent)** | HIGH | HIGH | **Root cause** | Structural; resolution requires market-structure recovery |
| **8** | **Path-truth mismatch** | LOW | LOW | **Quality note** | Governor notes 47% coverage; result not materially changed |
| —  | **Bootstrap instability** | LOW | LOW | **Non-binding** | Supporting gate; p5=1.261 well above floor |

*Note: Regime dependency (rank 7) is rated HIGH/HIGH because it is the common driver
of ranks 1–5. Its own "failure" is already active (COMPRESSION is absent). It is listed
separately to make the structural relationship explicit, not because it is an independent
future risk.*

---

## 4. Most Likely Failure Mode: n=61 → n=100

### Primary failure at n=100: p-value does not clear (delay)

The single most likely outcome at exactly n=100 is that p-value does not clear the
< 0.05 threshold. This is near-deterministic under the expected new-trade WR.

**Why this is nearly certain at n=100:**
- Exact binomial requires 59 wins out of 100 (WR≥59.0%) for p<0.05
- Estimated new-trade WR ≈ 55% (blended non-COMP mix)
- If new 39 trades arrive at 55% WR: blended WR at n=100 ≈ 56.5% → p≈0.097 ❌
- Even at historical average WR=57.4%: blended WR at n=100 ≈ 57.4% → p≈0.070 ❌
- p<0.05 clears at n=100 only if new trades arrive at WR≥60% (optimistic scenario)

**What this means:** Promotion will likely require n≈115–130, not n=100. The tracker's
estimate of "n≈105 at WR=58.1%" is optimistic — the exact binomial with continuity
correction requires approximately n=115–120 at sustained 58.1% WR, and the expected
WR of new non-COMP trades is below 58.1%.

**This is a delay, not a terminal outcome.** The edge remains real. The significance
gate is a sample-size requirement, not evidence of a failed hypothesis.

### Secondary failure risk: PF erosion (terminal)

The second-most-likely failure mode is cumulative PF eroding toward or below the 1.5
threshold through a nc_PF trough. This is:
- Lower probability than p-value failure (nc_PF trough requires a specific clustering
  of SIDEWAY and TREND_UP losses, or TREND_DOWN quality reversal)
- Higher severity than p-value failure (terminal — moves to FAILED_CANDIDATE)

Central scenario at n=100: cumulative PF ≈ 1.79 — passes with 0.29 margin. But the
margin erodes monotonically with each non-COMP trade, and a 14-trade trough (repeating
historical nc_PF negative zone) could pull cumulative PF below 1.5.

### En-route kill risk: K1 at 30-trade block

Between n=61 and n=100, kill criterion K1 (30-trade block WR<48%) represents the
primary pre-n=100 terminal risk. It does not require n=100 to be reached — it triggers
at the point when n_new ≥ 30 and new-trade WR < 48%.

This requires TREND_DOWN to revert to ~30% WR (BTC-COMP-embedded conditions). Currently
BTC is predominantly TREND_DOWN (favorable), so K1 risk is not imminent — but a BTC
regime shift is the single macro event that would elevate it sharply.

---

## 5. Evidence That Would Reduce the Primary Risk

### Reducing p-value risk (rank 1: delay)

| Evidence | How it reduces risk | Source |
|---|---|---|
| TREND_DOWN WR ≥ 65% on first 15 new TREND_DOWN trades | Demonstrates BTC-TD conditions maintained; blended WR near 60% | New qualifying trade journal |
| COMPRESSION returning (share > 10% of decision cycles for ≥ 3 days) | COMP trades arrive at WR~62%, PF~3.37 — directly elevates blended WR past 59% | Evidence velocity dashboard + regime monitor |
| n=70 snapshot showing cumulative WR ≥ 59% | Confirms trajectory; p<0.05 on track for n≈100 | n=70 formal snapshot |
| No TREND_UP clustering in new 30 trades | TREND_UP WR=42.9% is the primary WR depressor; keeping TU share ≤18% maintains blended WR |  regime breakdown at n=70 |

### Reducing PF erosion risk (rank 2: terminal)

| Evidence | How it reduces risk | Source |
|---|---|---|
| Rolling nc_PF (window=20) stays above 1.5 for all W23/W24 trades | Confirms non-COMP edge is above the add-on PF floor of 1.47; no trough in progress | n=70 nc_PF trajectory |
| TREND_DOWN WR on new trades matches BTC-TD historical (≥65%) | TREND_DOWN is the recovery engine that terminated the previous nc_PF trough | New trade WR by BTC-regime context |
| COMPRESSION recovery | COMP trades arrive at PF=3.37 — immediately arrests nc_PF erosion | COMPRESSION share monitoring |
| No 3-consecutive-trade SIDEWAY+TU loss cluster | The historical nc_PF trough was seeded by exactly this pattern | Drift monitoring at n=70 |

### Reducing K1 kill risk (rank 3: terminal pre-n=100)

| Evidence | How it reduces risk | Source |
|---|---|---|
| BTC stays in TREND_DOWN majority (≥30% of decision cycles) | BTC-TD context keeps ETH TREND_DOWN WR ≈ 65-86% | Evidence velocity dashboard |
| First 20 new trades show WR ≥ 55% | Leading indicator that 30-trade block WR stays above 48% | n=70 snapshot |

---

## 6. Governor Summary

**Verdict:** The ETH YES FC OS campaign is healthy with real edge (robustness 91/100,
bootstrap p5=1.261, LODO min PF=1.909). Its primary failure risk at n=100 is not the
edge itself but the significance threshold.

**What the campaign will likely look like at n=100:**

- n: ✅ met (by definition)
- WR: ✅ likely ~56–58% (above 52%)
- PF: ✅ likely ~1.6–1.8 (above 1.5, central scenario)
- p-value: ❌ likely ~0.07–0.10 (below 0.05 not reached at exactly n=100)
- calendar weeks: ✅ already met (W21, W22, W23)

**The n=100 snapshot will pass 4 of 5 promotion criteria.** The one that fails is
p-value. Promotion will then require n≈115–130 (assuming WR holds at historical range).

**The terminal risk is PF erosion, not p-value.** A repeat of the historical nc_PF
trough (14-trade nc_PF below 1.0, driven by SIDEWAY+TREND_UP clustering without
TREND_DOWN counterweight) would pull cumulative PF below 1.5 and threaten the
campaign with FAILED_CANDIDATE status before n=100. This risk is MEDIUM probability —
lower than p-value failure, higher in severity.

**The trigger to watch** is not the rolling PF (which is a noisy window metric) but:
1. **Rolling nc_PF (window=20)**: if it falls below 1.0 for more than 10 consecutive
   new W23/W24 trades, flag for review before n=80.
2. **BTC regime**: a BTC shift from TREND_DOWN to COMPRESSION would simultaneously
   suppress TREND_DOWN quality (WR reverts to ~30%), raise K1 kill risk, and accelerate
   nc_PF trough probability.

**Correct action:** Continue accumulating. Monitor rolling nc_PF and BTC regime
context at every milestone. Do not change any runtime, strategy, risk, or execution
parameter.

---

## 7. Projection Scenarios at n=100

| Scenario | Conditions | Expected WR | Expected PF | p-value | Verdict |
|---|---|---|---|---|---|
| **Best case** | COMPRESSION returns, contributes 30%+ of new trades | ~63% | ~2.3 | ~0.025 | ✅ All 5 criteria met at n=100 |
| **Central case** | COMPRESSION absent, TREND_DOWN WR holds at 58%, nc_PF ≈ 1.5 | ~57% | ~1.79 | ~0.070 | ❌ P4 fails; need n≈120 |
| **Adverse case** | TREND_DOWN WR reverts to 30% (BTC-COMP), nc_PF trough | ~45% | ~1.28 | ~0.30 | ❌❌ K1 triggered at n_new=30; K2 approaches at n=80 |
| **Stall case** | COMPRESSION absent, SIDEWAY+TU dominated, velocity 0.4/day | ~54% | ~1.55 | ~0.12 | ❌ P4 fails; n=100 not reached until Sep 2026+ |

---

## 8. What the Audit Does Not Authorize

- No runtime changes to filters, thresholds, or execution logic
- No regime-selective entry or exit rules based on COMPRESSION detection
- No stop-loss or sizing adjustments to compensate for nc_PF risk
- No pre-emptive demotion of the cell based on COMPRESSION absence alone
- No revision to promotion or kill criteria based on this audit

---

*Sources: verification_tracker.md (n=60 snapshot) · ETH_YES_FC_OS_CAMPAIGN_DASHBOARD.md
(n=61, 2026-06-06) · ETH_YES_FC_OS_DRIFT_AUDIT.md (2026-06-06) · verification_lifecycle.md ·
ETH_YES_FC_OS.md (watchlist) · COMPRESSION_MARKET_ARCHETYPE.md (regime context)*

*No code changes. No runtime changes. No strategy changes. No commits. Evidence only.*
