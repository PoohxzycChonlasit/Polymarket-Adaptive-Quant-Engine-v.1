# Research Frontier Prioritization Audit

type: prioritization audit
source: RESEARCH_FRONTIER_DASHBOARD.md
created: 2026-05-30
evidence_period: 2026-05-08 to 2026-05-30
code_changed: No
strategy_changed: No
runtime_changed: No

> READ-ONLY analysis. No findings are marked complete. No runtime, strategy,
> risk, confidence, EV, or execution changes are authorized or implied.
> All conclusions are evidence-based assessments only.

---

## 1. Executive Summary

After 22 days of paper trading across 56 sessions and 406 real trades, five
research frontiers are sufficiently mature to prioritize for the next 30-day
evidence accumulation window.

**The single most important finding is not about a specific trading cell — it is
about the risk system itself.** The MICRO_RECOVERY conf≥0.75 gate is VERIFIED to
select BTC COMPRESSION (the system's worst cell) and OBSERVED to produce a
27.5% win rate at exactly the moment the system is supposed to be at its most
conservative. This is a safety-first priority because it amplifies losses after
any loss cluster, and the May 30 session confirmed the loop in real-time.

Below MICRO_RECOVERY, three structural failure modes compound each other:
BTC COMPRESSION entries are miscalibrated at the critical true_p 0.65–0.70
bucket (13.8% actual vs 67% model), ETH NO COMPRESSION continues to bleed
at 30.8% win rate, and ACTIVE_INVENTORY's EV signal is an anti-signal
(Pearson r ≈ 0, Q4 wins at 33.7%). These are not independent problems —
they share a root cause: the probability model's confidence assignments are
structurally decoupled from actual binary option resolution probabilities
in COMPRESSION and near-PTB regimes.

**Top 5 frontiers in priority order:**

| Rank | Frontier | Status | Key Metric | Days to Next Review |
|---|---|---|---|---|
| 1 | MICRO_RECOVERY Outcome Degradation | VERIFIED mech / OBSERVED outcome | 27.5% wr at conf≥0.75 | ~17 days |
| 2 | AI EV Inversion | OBSERVED (n=384) | Pearson r=+0.010 | ~4 days |
| 3 | BTC COMP Confidence Inversion | OBSERVED (n=59) | 13.8% wr in true_p 0.65–0.70 | ~18 days |
| 4 | ETH NO COMP Losing Cell | OBSERVED (n=52) | 30.8% wr, p=0.145 | ~11 days |
| 5 | TREND_UP EV Predictability | WEAK SIGNAL (n=63) | EV_Δ=+0.028 (only positive) | ~7 days |

---

## 2. Top 5 Research Frontiers

### Frontier #1: MICRO_RECOVERY Outcome Degradation

**Why first:** This is the only frontier where a VERIFIED mechanism actively
worsens system behavior during stress. The risk protection layer is counter-productive
by design, and the proof requires no additional data — it is mathematical.

**The mechanism (VERIFIED):** MICRO_RECOVERY requires conf≥0.75. ETH's liq_mult=0.75
caps max conf at 0.66. Therefore MICRO_RECOVERY structurally routes all entries
into BTC (liq_mult=1.00 → max conf=0.88). Within BTC at conf≥0.75, COMPRESSION
dominates (67.5% of trades). BTC COMPRESSION conf≥0.75 wins 22.2% with calib
gap +0.449. The gate is routing into the system's worst confirmed cell.

**The outcome (OBSERVED):** 27.5% win rate at conf≥0.75 vs 37.9% baseline.
42.8% win rate at conf 0.55–0.65 — the gate improves nothing and worsens outcomes.

**Phase 2 relevance:** Any Phase 2 inventory replay evidence gathered during
MICRO_RECOVERY sessions is contaminated by this selection bias. Phase 2 must
account for risk-mode state in all analysis.

---

### Frontier #2: ACTIVE_INVENTORY EV Inversion

**Why second:** At n=384, this is the most statistically mature finding that
is not yet VERIFIED. It is 116 trades from the n=500 threshold. The Pearson
r=+0.010 is already effectively zero. This is the foundational constraint
for Phase 3 exit engine design: **the current primary exit signal (EV) is
not predictive.**

The ETH-specificity (ETH EV_Δ=−0.008 inverted; BTC EV_Δ=+0.017 normal) is
important — BTC AI trades are 23% of the population and show correct EV sign.
ETH, 77% of AI trades, drives the aggregate inversion.

The only positive signal: TREND_UP regime has EV_Δ=+0.028 (n=63). If Phase 3
must use EV for exit decisions, TREND_UP is the only regime that warrants it.

---

### Frontier #3: BTC COMPRESSION OPENING_SCAN Confidence Inversion

**Why third:** The entry miscalibration in BTC COMPRESSION is the origin
point for multiple downstream problems: it produces the OPENING_SCAN losses
that trigger risk escalation, which then activates MICRO_RECOVERY, which then
re-selects BTC COMPRESSION. Breaking this chain at the entry stage would have
cascading benefits.

The true_p 0.65–0.70 bucket is the surgical target: n=29, 13.8% actual win
rate vs 67% model estimate. This 4.8× error means every BTC COMPRESSION trade
in this range is expected-value negative from the model's perspective but
actually deeply negative in reality. Only 21 more trades in this bucket are
needed to reach n=50 for strong OBSERVED confidence.

---

### Frontier #4: ETH NO COMPRESSION Losing Cell

**Why fourth:** The structural mechanism is clear, the model behavior is
VERIFIED stable (true_p=0.650±0.008), and the directional pattern is consistent
across 16/23 sessions. The statistical gap (p=0.145, needs n=350) is the
only barrier to VERIFIED.

At ~4.3 trades/day, n=100 arrives in ~11 days — a reasonable immediate target.
At n=100, if win rate remains below 38%, the probability of p<0.05 improves
substantially with the effect size.

The YES/NO asymmetry (ETH YES COMPRESSION at 51.4% vs ETH NO at 30.8%) is
the critical control — both cells have identical model confidence, confirming
the failure is directional, not regime-wide.

---

### Frontier #5: TREND_UP EV Predictability

**Why fifth:** This is the only green light in the entire analysis. All other
regimes in AI show EV inversion. If TREND_UP EV is confirmed predictive at
n=100+ (currently n=63, EV_Δ=+0.028), it gives Phase 3 exactly one regime
where EV-based hold/exit signals can be trusted.

At ~30 AI trades/day with 16.4% TREND_UP share (~5/day), n=100 is ~7 days
away. This is the fastest-moving frontier relative to its information value.

---

## 3. Ranking Criteria

Each frontier is scored 1–5 on five dimensions (5=highest). Scores are
judgments based on available evidence, not formulas.

### Scoring Dimensions

**A. Expected Information Gain**
How much will the next n-increment change our understanding?
- 5: Finding is almost unknown; n=10 would reveal something major
- 4: Pattern is directional but could easily reverse; more n is decisive
- 3: Pattern is consistent; more n will confirm, unlikely to reverse
- 2: Already well-understood; next increment adds marginal value
- 1: Already VERIFIED; mathematically certain or code-confirmed

**B. Decision Quality Impact**
If confirmed VERIFIED, how much does it change Phase 2/3/4 design?
- 5: Completely changes a core design assumption
- 4: Removes or enables a significant design choice
- 3: Refines an existing design constraint
- 2: Confirms something already architected around
- 1: No design decision changes — informational only

**C. Risk / Safety Impact**
Does the finding affect loss exposure, cascade risk, or system stability?
- 5: Active safety mechanism is broken; amplifies losses during stress
- 4: Creates sustained losses in a frequently-entered cell
- 3: Affects a specific cell that can be avoided
- 2: Rare event; bounded exposure
- 1: No safety implication

**D. Data Availability**
How quickly can n increase at current evidence rate?
- 5: n=threshold reachable in < 7 days at current rate
- 4: n=threshold reachable in 7–14 days
- 3: n=threshold reachable in 14–30 days
- 2: n=threshold reachable in 30–60 days
- 1: n=threshold requires 60+ days or is mathematically constrained

**E. Phase 2 Readiness Impact**
Does this finding gate or unblock Phase 2 research?
- 5: Phase 2 cannot be interpreted accurately without this being resolved
- 4: Phase 2 analysis would be significantly stronger with this confirmed
- 3: Phase 2 would benefit but can proceed without it
- 2: Phase 2 is largely independent of this finding
- 1: Phase 2 is fully independent

---

## 4. Frontier Ranking Table

| # | Frontier | Status | A: Info Gain | B: Decision | C: Safety | D: Data | E: Phase 2 | Total | Days to Review |
|---|---|---|---|---|---|---|---|---|---|
| 1 | MICRO_RECOVERY Outcome Degradation | VERIFIED mech | 3 | 5 | **5** | 3 | **5** | **21** | ~17 |
| 2 | AI EV Inversion | OBSERVED (n=384) | 2 | **5** | 4 | **5** | 4 | **20** | ~4 |
| 3 | BTC COMP Confidence Inversion | OBSERVED (n=59) | 4 | **5** | 4 | 3 | **5** | **21** | ~18 |
| 4 | ETH NO COMP Losing Cell | OBSERVED (n=52) | 3 | 4 | 4 | 4 | 4 | **19** | ~11 |
| 5 | TREND_UP EV Predictability | WEAK SIGNAL (n=63) | **5** | 4 | 2 | **5** | 3 | **19** | ~7 |
| 6 | ETH YES COMP at 50% | OBSERVED (n=37) | 3 | 3 | 3 | 4 | 3 | **16** | ~10 |
| 7 | orderbook_unavailable misclass. | VERIFIED | 1 | 2 | 2 | 4 | 2 | **11** | ~10 |
| 8 | ETH conf≥0.75 outperforms BTC | WEAK SIGNAL (n=5) | 4 | 2 | 1 | 1 | 1 | **9** | ~23 |
| 9 | ETH liq_mult exclusion | VERIFIED | 1 | 3 | 3 | — | 2 | **9** | N/A |
| 10 | stale_orderbook worst state | OBSERVED (n=9) | 3 | 2 | 2 | 1 | 1 | **9** | ~50+ |
| 11 | Wide spread advantage | WEAK SIGNAL (n=12) | 3 | 1 | 1 | 1 | 1 | **7** | ~36+ |

**Notes:**
- Frontiers #1 and #3 tie on total score (21); #1 ranked higher due to safety impact of 5 (active feedback loop) vs 4.
- `orderbook_unavailable` (V4) and `ETH liq_mult exclusion` (V1) are already VERIFIED — their "frontier" value is in design implications, not additional evidence.
- Scores for Data Availability (D) reflect speed to the next meaningful review threshold, not to full VERIFIED.

---

## 5. Why Each Frontier Matters

### #1 — MICRO_RECOVERY Outcome Degradation

**The cascade problem:** When the system suffers 3 consecutive losses, it enters
MICRO_RECOVERY and requires conf≥0.75. This mathematically routes to BTC COMPRESSION.
BTC COMPRESSION wins at 22.2% at conf≥0.75. More losses follow. The pause fires
again. The system is trapped in a loop that was designed to protect it.

**Why this is the safety-first issue:** Unlike the other frontiers, this one actively
worsens outcomes in response to stress. The ETH NO COMPRESSION cell (Frontier #4)
bleeds money at a steady rate — predictable and bounded. MICRO_RECOVERY multiplies
that bleeding by activating exactly when the system is most vulnerable and routing
into a cell with a 22% win rate.

**The May 30 evidence:** 5 consecutive losses in the current run (run `20260530T125144Z`).
Loss #1 was ETH NO COMPRESSION — the known bad cell. This started the cascade.

---

### #2 — AI EV Inversion

**Why EV matters to architecture:** The `manage_position()` function in the current
codebase uses `metadata.get("entry_ev", 0.02)` — frozen entry EV — for hold/exit
decisions. EV is inverted (Pearson r≈0). The position manager is using a signal
that has no predictive value for hold/exit quality.

**The ETH-BTC split:** BTC AI trades show the correct EV sign (W_ev=0.140 > L_ev=0.123).
ETH AI trades are inverted (W_ev=0.117 < L_ev=0.125). This means the problem is
specific to how ETH positions behave in ACTIVE_INVENTORY — not universal.

**Why it's nearly VERIFIED now:** At n=384, Pearson r=+0.010. The 95% confidence
interval for r at n=384 is approximately [−0.09, +0.11]. This already excludes
any meaningfully positive r. Adding 116 more trades pushes the CI to [−0.08, +0.10]
— confirming effective zero correlation. No additional qualitative change expected.

---

### #3 — BTC COMPRESSION OPENING_SCAN Confidence Inversion

**The 4.8× error:** In the true_p 0.65–0.70 bucket, BTC COMPRESSION wins 13.8%.
The model expects 65–70%. This is not a calibration issue — it is a fundamental
mismatch between what the model's distance+liquidity signal is encoding and what
Polymarket binary options actually require.

**Why this bucket is critical:** Of the 59 BTC COMP OS trades, 29 (49%) fall in
the 0.65–0.70 bucket. This is not a tail event — it is the modal cell. Half of
all BTC COMP OS entries are in the range where the model is most catastrophically
wrong.

**The ETH control:** ETH at the same true_p bucket wins 55.9% (n=34). The model
assigns the same probability to both — the error is BTC-specific. This rules out
a universal calibration problem and points to something specific to BTC's book
structure or price dynamics relative to the binary strike.

---

### #4 — ETH NO COMPRESSION Losing Cell

**The model invariant:** avg(true_p)=0.650±0.008 across 23 sessions. The model
has never assigned anything different to this cell. This is not noise — it is
the probability model's deterministic output for a specific combination of inputs
(price below PTB, thin ETH book, low volatility in COMPRESSION).

**The mechanism:** `leans_no` fires when price is below PTB (negative window_delta).
In COMPRESSION (price oscillating ±1–2% around PTB), this is informationally
empty — the direction at resolution is approximately random with slight ETH upward
drift. The model treats "below PTB now" as a path-conditional statement about the
next 4+ minutes. It is not.

**The 7/23 counterexamples:** Seven sessions showed win rate > 50%. The May 24–25
cluster (9 trades, 67%) is the strongest counterexample. Until n=100+, the 7 sessions
are genuine uncertainty — they could reflect calendar-specific ETH market structure
differences not captured in the current model.

---

### #5 — TREND_UP EV Predictability

**The lone green light:** Every other regime in ACTIVE_INVENTORY shows EV inversion:
COMPRESSION (−0.005), SIDEWAY (−0.010), TREND_DOWN (−0.014). TREND_UP is +0.028.

**Why this matters more than its size suggests:** If TREND_UP EV is confirmed
predictive at n=100, it means the model's EV signal has meaning in exactly one
context: when price is trending upward and the AI position is held against that
trend. This could be the foundation for the first valid exit signal in Phase 3.

**The mechanism hypothesis:** In TREND_UP, the model's EV signal reflects genuine
directional edge — price is moving with momentum, the binary option price reflects
this, and EV encodes real information about resolution probability. In COMPRESSION
and SIDEWAY, the EV signal reflects only liquidity-driven confidence inflation,
which is disconnected from resolution.

---

## 6. What Evidence Is Still Missing

### Critical Gaps (block Phase 2/3 design)

**Gap 1: True_p calibration with post-patch distance tokens**
We know BTC COMPRESSION true_p 0.65–0.70 → 13.8% actual. We do NOT yet know
whether the calibration error is driven by `distance_from_ptb_pct` clamping
(at ±2.0%), momentum=0 in AI entries, or a structural BTC pricing mismatch.
- Missing: ≥50 post-patch BTC COMP trades with `probability_model_reason` distance data
- Currently: 18 post-patch AI trades, all momentum=0, reason available
- Gap closes: ~10 more days at current rate

**Gap 2: Valid exit signal identification**
EV is inverted. Confidence is not recomputed in HOLD cycles. Momentum=0 in AI.
We have no confirmed positive predictive signal for hold/exit quality.
- Missing: Any signal with Pearson r > +0.15 on n ≥ 50 AI trades
- Candidates to test (Phase 3 prep): distance_from_ptb_pct at mid-window, seconds_remaining, unrealized price change since entry
- Gap closes: Requires Phase 3 design work, not just more data

**Gap 3: MICRO_RECOVERY escalation replication**
One session (2026-05-30) confirmed the feedback loop. Single-session evidence
is insufficient for design conclusions.
- Missing: ≥3 independent sessions showing the same ETH COMP → DEFENSIVE → MICRO_RECOVERY → BTC COMP → loss cascade pattern
- Gap closes: Depends on how often ETH COMP losses cluster (currently rare at ~4.3/day)

**Gap 4: TREND_UP EV predictability confirmation**
n=63, EV_Δ=+0.028. Could be noise.
- Missing: n=100 TREND_UP AI trades with EV_Δ remaining positive
- Gap closes: ~7 days at current rate (fastest gap)

### Non-Critical Gaps (informational, not design-blocking)

- ETH conf≥0.75 outperforming BTC (n=5): interesting but rare, slow to accumulate
- Wide spread advantage (n=12): rare, not immediately exploitable
- stale_orderbook conclusions (n=9): 50+ days to n=30, very slow
- orderbook_unavailable outcome pattern (n=38): ~10 days to n=75

---

## 7. Recommended 30-Day Research Focus

### Days 1–7: Fast wins and foundation

**Primary target: TREND_UP EV predictability (n=63 → n=100)**
- ~7 days to n=100 at current rate
- Highest information gain per day of any frontier
- Confirms or refutes the only positive AI signal
- Run ACTIVE_INVENTORY EV audit at n=100 with TREND_UP isolated

**Secondary target: AI EV Inversion to VERIFIED (n=384 → n=500)**
- ~4 days to n=500
- Run full EV audit at n=500; if Pearson r still <0.05, record as VERIFIED
- Focus specifically on ETH vs BTC split and TREND_UP exception

**Watchlist updates:** Append snapshot to ACTIVE_INVENTORY_EV_INVERSION.md and
BTC_COMPRESSION_OPENING_SCAN.md (any new trades in each).

---

### Days 7–14: Mid-term confirmation targets

**Primary target: ETH NO COMPRESSION n=52 → n=100**
- ~11 days at ~4.3 trades/day
- At n=100, run full replication audit
- Check if May 24–25 exception repeats or remains isolated
- If win rate < 35% at n=100: strong OBSERVED; if 35–42%: pattern is softening; > 42%: begin downgrade review

**Secondary target: conf≥0.75 trades n=40 → n=100**
- ~17 days (still in progress at day 14)
- Run partial MICRO_RECOVERY audit at n=70+
- Focus on BTC COMPRESSION win rate in the new increment: is 22.2% stable?

**Watchlist updates:** ETH_NO_COMPRESSION.md snapshot at n=100. MICRO_RECOVERY_SELECTION.md at n=70.

---

### Days 14–30: Deep verification targets

**Primary target: BTC COMP OS n=59 → n=150**
- ~18 days total from today
- Run full confidence band audit at n=100 and again at n=150
- Check monotonicity: does the 0.65–0.75 band violation persist or resolve?
- Check true_p 0.65–0.70 bucket: does 13.8% hold or was it small-sample noise?

**Secondary target: conf≥0.75 to n=100**
- Completes at ~day 17
- If BTC COMPRESSION win rate at conf≥0.75 is still <30%, record MICRO_RECOVERY outcomes as VERIFIED

**Secondary target: MICRO_RECOVERY feedback loop replication**
- Passive — watch for sessions that trigger the cascade
- Log each MICRO_RECOVERY session with: trigger losses, cascade structure, outcome
- At 3 replications: promote loop observation to OBSERVED

**Watchlist updates:** BTC_COMPRESSION_OPENING_SCAN.md at n=100 and n=150. MICRO_RECOVERY_SELECTION.md at n=100. WATCHLIST_INDEX.md updated throughout.

---

### 30-Day Summary

| Target | Day window | Expected outcome |
|---|---|---|
| AI EV VERIFIED | Days 1–4 | Pearson r≈0 confirmed, ETH-specific |
| TREND_UP EV n=100 | Days 1–7 | +0.028 delta confirmed or refuted |
| ETH NO COMP n=100 | Days 7–14 | p improves; OBSERVED strengthened |
| conf≥0.75 n=100 | Days 7–17 | MICRO_RECOVERY outcomes OBSERVED→VERIFIED candidate |
| BTC COMP OS n=100 | Days 14–20 | 13.8% bucket confirmed or softening |
| BTC COMP OS n=150 | Days 14–28 | VERIFIED candidate for confidence inversion |

---

## 8. What NOT To Do Yet

### Do NOT act on OBSERVED findings as if they were VERIFIED

**ETH NO COMPRESSION (n=52):** 7/23 sessions show >50% win rate. The pattern
is directional but statistically inconclusive (p=0.145). Do not suppress entries
in this cell based on current evidence.

**BTC COMP confidence inversion (n=59):** The 0.65–0.75 band shows a minor
violation (32.0% win — higher than 0.55–0.65 band at 23.5%). This could reflect
sampling noise. Do not draw hard confidence thresholds from n=25 per band.

**MICRO_RECOVERY feedback loop (1 session):** One session does not establish
that the loop always fires. Do not change risk mode thresholds based on a
single-session observation.

---

### Do NOT attempt to fix the MICRO_RECOVERY gate mechanically

The mathematical proof shows ETH cannot reach conf≥0.75. The obvious "fix" —
separate ETH and BTC thresholds or lower the MICRO_RECOVERY threshold — would
change risk architecture without sufficient evidence that such a change improves
outcomes across all regimes. This is a Phase 3 design question.

---

### Do NOT treat EV as confirmed useless before n=500

At n=384, EV inversion is strong but not at the VERIFIED threshold. BTC shows
the correct EV sign (+0.017). Acting on "EV is useless" could foreclose valid
BTC position-sizing signals. Wait for n=500 with the ETH/BTC split confirmed.

---

### Do NOT conflate COMPRESSION regime failure with COMPRESSION regime avoidance

COMPRESSION is 38% of AI trades. Avoiding it entirely would reduce trade volume
significantly without clear evidence that non-COMPRESSION wins make up the difference.
The finding is not "COMPRESSION is bad" — it is "BTC COMPRESSION at high confidence
is miscalibrated." ETH YES COMPRESSION wins at 51.4%. The failure is directional
and cell-specific.

---

### Do NOT prioritize stale_orderbook or wide spread research

At n=9 (stale) and n=12 (wide spread), there is no actionable information.
Both would require 30–50 days just to reach minimum-conclusion thresholds.
Opportunity cost is too high given the critical frontiers above.

---

### Do NOT advance to Phase 2 before AI EV inversion is VERIFIED

Phase 2 (paper-only inventory replay, MFE/MAE tracking) requires understanding
what signals govern exit quality. If EV is inverted, Phase 2 replay analysis
that relies on EV for exit optimization will produce incorrect conclusions.
Wait for n=500 EV VERIFIED (expected ~4 days).

---

## 9. Final Recommendation

**The 30-day research program should converge on three verdicts:**

### Verdict 1: AI EV Inversion → VERIFIED (by Day 5)

This is the fastest and most important VERIFIED finding to obtain. It closes
the book on EV as an AI exit signal (for ETH) and sets the table for Phase 3
exit signal research. The Pearson r is already effectively zero at n=384.

**Action when confirmed:** Update ACTIVE_INVENTORY_EV_INVERSION.md status to
VERIFIED. Record that Phase 3 exit engine cannot rely on EV for ETH positions.
Add to RESEARCH_FRONTIER_DASHBOARD.md Section 1 (VERIFIED FINDINGS).

---

### Verdict 2: BTC COMPRESSION OPENING_SCAN Inversion → VERIFIED (by Day 28)

The true_p 0.65–0.70 bucket at 13.8% actual win rate is the most specific
failure point in the entire system. If this survives to n=150 with the inversion
pattern intact and the bucket win rate below 25%, it becomes the strongest
VERIFIED finding about entry quality degradation.

**Action when confirmed:** Update BTC_COMPRESSION_OPENING_SCAN.md status to
VERIFIED. This is the primary Phase 2 entry policy design input.

---

### Verdict 3: MICRO_RECOVERY Selection → OBSERVED (outcomes) Strengthened

By Day 17, conf≥0.75 should reach n=100. If BTC COMPRESSION win rate at conf≥0.75
remains below 30% in the new n=60 increment, the outcome degradation reaches
strong OBSERVED. Combined with the mathematically VERIFIED selection mechanism,
this provides the governance-level evidence needed to flag the risk mode design
for Phase 3 review.

**Action when confirmed:** Update MICRO_RECOVERY_SELECTION.md outcomes from
OBSERVED to OBSERVED (strong). Flag for Phase 3 risk mode design.

---

### What success looks like at Day 30

By Day 30, the following should be in place:

- **VERIFIED:** AI EV is an anti-signal in ETH ACTIVE_INVENTORY (Pearson r confirmed ≈ 0)
- **VERIFIED or strong OBSERVED:** BTC COMPRESSION confidence inversion with 13.8% bucket surviving
- **Strong OBSERVED:** ETH NO COMPRESSION win rate < 38% confirmed at n=100 with p improving
- **OBSERVED → VERIFIED candidate:** MICRO_RECOVERY outcomes at n=100 conf≥0.75 with BTC COMP still <30%
- **WEAK → OBSERVED:** TREND_UP EV predictability at n=100 with EV_Δ remaining positive

This evidence base would justify initiating Phase 2 planning with:
1. A confirmed invalid exit signal (EV for ETH AI) to work around
2. A confirmed entry quality degradation (BTC COMP) to account for in replay
3. A confirmed risk mechanism failure (MICRO_RECOVERY) to note in all Phase 2 analysis

---

*This document is READ-ONLY evidence analysis.*
*No findings are marked complete. No runtime, strategy, risk, or execution changes authorized.*
*All prioritizations reflect expected information gain under current evidence — not confirmed facts.*
