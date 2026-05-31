# Frontier Evidence Collection Plan

type: 30-day evidence collection plan
sources:
  - docs/research/RESEARCH_FRONTIER_DASHBOARD.md
  - docs/research/RESEARCH_FRONTIER_PRIORITIZATION_AUDIT.md
created: 2026-05-30
plan_start: 2026-05-31
plan_end: 2026-06-29
code_changed: No
strategy_changed: No
runtime_changed: No

> This document defines what evidence must be collected before any fix,
> design change, or phase transition is authorized. Fixes come later.
> Evidence gates come first.

---

## 1. Executive Summary

Six research frontiers require active evidence collection over the next 30 days.
They are ordered by urgency, not importance — urgency reflects proximity to a
decision-quality change in evidence status.

**Fastest closing frontiers (Days 1–7):**
- AI EV Inversion → VERIFIED (116 trades needed, ~4 days)
- TREND_UP EV Predictability → OBSERVED (37 trades needed, ~7 days)

**Mid-term frontiers (Days 7–17):**
- ETH NO COMP → strong OBSERVED (48 trades needed, ~11 days)
- MICRO_RECOVERY outcomes → VERIFIED candidate (60 conf≥0.75 trades needed, ~17 days)

**Long-term frontiers (Days 17–30):**
- BTC COMP confidence inversion → VERIFIED (91 trades needed, ~18 days)
- ETH conf≥0.75 outperforms BTC → OBSERVED (15 ETH trades needed, ~23 days)

**Structural constraints (no time target):**
- stale_orderbook: n=9, ~50+ days to minimum conclusion threshold — passive monitoring only
- No evidence authorizes any fix during this plan period

**Governance principle:** Every status change (WEAK SIGNAL → OBSERVED, OBSERVED →
VERIFIED, or any DOWNGRADE) requires a named reviewer sign-off and a snapshot
entry in the relevant watchlist file before the change takes effect.

---

## 2. Evidence Targets by Frontier

### Frontier A: AI EV Inversion

**Current state:** OBSERVED (n=384, Pearson r=+0.010)
**Target state:** VERIFIED
**Required n:** 500 total ACTIVE_INVENTORY trade closes
**Gap:** 116 trades
**Estimated time to close:** ~4 days at ~30 AI trades/day
**Hard gate:** n=500 AND Pearson r ∈ [−0.05, +0.05] in the new increment

**Evidence to collect per trade:**
- `ev_after_spread` at decision time
- `pnl_usdc` at close
- `asset` (BTC/ETH split is mandatory)
- `market_regime` (TREND_UP isolation is mandatory)
- `side` (YES/NO split)
- `lifecycle_phase` (confirm ACTIVE_INVENTORY)

**Specific sub-analyses required at n=500:**
1. Pearson r(EV, PnL) full population — confirm ≤ 0.05
2. EV quartile win rates (Q1/Q2/Q3/Q4) — confirm Q4 < Q1
3. ETH-only Pearson r — confirm ETH drives inversion
4. BTC-only Pearson r — confirm BTC is NOT inverted
5. TREND_UP EV_Δ at n=100+ — confirm positive sign persists
6. COMPRESSION EV_Δ — confirm negative sign persists

**Blocking question answered by this evidence:**
Can EV be used as a hold/exit signal in Phase 3 for ETH positions?
Expected answer at n=500: **No** (Pearson r ≈ 0 for ETH).

---

### Frontier B: MICRO_RECOVERY Outcome Degradation

**Current state:** VERIFIED mechanism / OBSERVED outcomes (n=40 conf≥0.75)
**Target state:** VERIFIED outcomes
**Required n:** 100 conf≥0.75 trade closes
**Gap:** 60 conf≥0.75 trades
**Estimated time to close:** ~17 days at ~3.5 conf≥0.75 trades/day
**Hard gate:** n=100 conf≥0.75 AND BTC share ≥ 75% in new increment AND BTC COMP win rate < 35%

**Evidence to collect per trade (conf≥0.75 only):**
- `confidence` — must be ≥ 0.75 at decision time
- `market_regime` (COMPRESSION vs non-COMPRESSION)
- `asset` (BTC/ETH split)
- `side` (YES/NO split)
- `pnl_usdc` at close
- `orderbook_state_classification`
- `prob_model_liquidity_usd` (liq_mult derivation)
- `run_id` (session tracking)

**Specific sub-analyses required at n=100:**
1. BTC share at conf≥0.75 — confirm > 75%
2. COMPRESSION share at conf≥0.75 — confirm > 60%
3. BTC COMPRESSION conf≥0.75 win rate — confirm < 35%
4. BTC COMPRESSION conf≥0.75 calibration gap — confirm > +0.35
5. ETH conf≥0.75 count — confirm < 20% of total conf≥0.75
6. Cross-session stability: win rate by session at conf≥0.75 — confirm majority below 40%
7. Win rate by confidence band comparison (all 4 bands with new n added) — confirm >0.75 is lowest

**Blocking question answered by this evidence:**
Does the MICRO_RECOVERY gate structurally degrade outcomes, or was the 27.5% win
rate at conf≥0.75 noise at n=40?
Expected answer at n=100: **Degradation likely confirmed** — mechanism is mathematical;
outcomes expected to strengthen with n.

---

### Frontier C: BTC COMPRESSION OPENING_SCAN Confidence Inversion

**Current state:** OBSERVED (n=59)
**Target state:** VERIFIED
**Required n:** 150 total BTC×COMPRESSION×OPENING_SCAN trade closes
**Gap:** 91 trades
**Estimated time to close:** ~18 days at ~5 BTC COMP OS trades/day
**Hard gate:** n=150 AND true_p 0.65–0.70 bucket win rate < 25% on n≥50 in that bucket AND monotone inversion holds across all 4 confidence bands

**Evidence to collect per trade (BTC×COMP×OS only):**
- `confidence` — confidence band assignment is the primary variable
- `true_probability` — bucket assignment (0.60–0.65, 0.65–0.70 critical)
- `pnl_usdc` at close
- `orderbook_state_classification` (empty_book vs ready)
- `prob_model_liquidity_usd` (liq_mult derivation)
- `side` (YES/NO — BTC YES vs NO comparison)
- `probability_model_reason` (post-patch: distance, quality tokens)
- `seconds_remaining` at decision time

**Specific sub-analyses required at n=100 (interim) and n=150 (final):**
1. Win rate by confidence band — 4 bands with n≥15 each required at n=150
2. Win rate by true_p bucket — focus on 0.65–0.70: does 13.8% hold?
3. Monotonicity check — is the inversion monotone across all 4 bands?
4. BTC YES vs BTC NO win rate — directional split at each confidence band
5. empty_book vs ready win rate — does ob_state moderate the inversion?
6. liq_mult=0.75 vs liq_mult=1.00 — which tier drives the miscalibration?
7. Calibration gap by conf band — does gap widen with confidence?

**Critical check at n=50 in the 0.65–0.70 true_p bucket:**
If win rate in this bucket rises above 25% on the new n=21 increment →
trigger DOWNGRADE_REVIEW for this specific bucket.
If win rate stays below 20% → OBSERVED(strong) for this bucket.

**Blocking question answered by this evidence:**
Is BTC COMPRESSION OPENING_SCAN systematically miscalibrated in the
true_p 0.65–0.70 range, or was 13.8% a small-sample artifact?
Expected answer at n=150: **Miscalibration confirmed** if 4.8× model error
persists with n≥50 in the bucket.

---

### Frontier D: ETH NO COMPRESSION Losing Cell

**Current state:** OBSERVED (n=52, p=0.145)
**Target state (30-day):** Strong OBSERVED (n=100, p improving)
**Full VERIFIED target:** n=350 (outside 30-day window)
**Gap to n=100:** 48 trades
**Estimated time to n=100:** ~11 days at ~4.3 ETH NO COMP trades/day
**Hard gate at n=100:** win rate < 40% AND p (lower tail) < 0.25 AND sessions contributing ≥ 5

**Evidence to collect per trade (ETH×NO×COMPRESSION only):**
- `pnl_usdc` at close
- `true_probability` — confirm true_p stability (σ < 0.015 expected)
- `confidence` at decision time
- `ev_after_spread` at decision time
- `orderbook_state_classification`
- `lifecycle_phase` (OS vs AI split)
- `run_id` (session diversity check)
- `timestamp_utc` (calendar day diversity check)
- `probability_model_reason` (post-patch: leans_no token, distance)

**Specific sub-analyses required at n=100:**
1. Win rate overall — expected < 40%
2. p-value (lower tail, base_p=0.379) — expected to improve from 0.145
3. avg(true_p) — confirm σ < 0.015 (model stability test)
4. Calibration gap — expected > +0.25
5. Sessions count and session win rate distribution — confirm pattern not concentrated in 1–2 sessions
6. Calendar day count — confirm ≥ 14 unique dates
7. Check May 24–25 exception: how does it look at n=100? Still isolated or part of a cluster?
8. ETH YES COMPRESSION (control) at same n=100 window — confirm still ~50%
9. ETH NO SIDEWAY at same window — confirm still ~41% (regime control)

**n=100 decision table:**

| Outcome | Win rate at n=100 | p (lower tail) | Decision |
|---|---|---|---|
| Pattern strengthens | < 35% | < 0.10 | Promote to Strong OBSERVED |
| Pattern holds | 35–40% | 0.10–0.25 | Maintain OBSERVED |
| Pattern softens | 40–45% | 0.25–0.40 | Flag for DOWNGRADE_REVIEW |
| Pattern reverses | > 45% | > 0.40 | DOWNGRADE_REVIEW required |

**Blocking question answered by this evidence:**
Is the 30.8% win rate a real structural pattern or calendar-period noise?
The May 24–25 exception (67% over 9 trades) is the key test: if the next
48 trades include another 40%+ cluster, the pattern is less stable than
believed.

---

### Frontier E: stale_orderbook Worst State

**Current state:** OBSERVED (n=9, 0% win rate) — WATCHLIST level
**Target state (30-day):** OBSERVED (n=30)
**Gap:** 21 trades
**Estimated time:** 50+ days at ~0.4 stale trades/day
**Status:** PASSIVE MONITORING ONLY — this frontier cannot close in 30 days

**Evidence to collect per trade (stale_orderbook only):**
- `pnl_usdc` at close (win/loss flag)
- `asset` and `side`
- `market_regime`
- `confidence` and `ev_after_spread`
- `timestamp_utc` (cluster detection — are stale events time-clustered?)
- `run_id` (session context)

**30-day target:** Accumulate passively. At n=15 (if reached), check whether
0-for-9 is still holding or first win appears.

**No analysis required below n=20.** Do not draw conclusions from n<20.

**Blocking question:** Does stale_orderbook reliably produce losses?
Cannot answer in 30 days. This question is deferred to 60-day window.

---

### Frontier F: ETH conf≥0.75 Outperforming BTC

**Current state:** WEAK SIGNAL (n=5 ETH at conf≥0.75)
**Target state (30-day):** OBSERVED (n=20 ETH at conf≥0.75)
**Gap:** 15 ETH conf≥0.75 trades
**Estimated time:** ~23 days at ~0.65 ETH conf≥0.75 trades/day
**Status:** Low priority, passive accumulation

**Evidence to collect per trade (ETH × conf≥0.75 only):**
- `pnl_usdc`
- `confidence` (exact value — not just band)
- `market_regime`
- `side`
- `prob_model_liquidity_usd` (confirm ≥ $500 → liq_mult=1.00)
- `probability_model_reason` (what signal pushed ETH to ≥0.75?)

**At n=20:**
- Report win rate and compare to BTC conf≥0.75 win rate at same time
- If ETH wr > 50% and BTC wr < 30%: promote to OBSERVED
- If ETH wr < 40%: revert to WATCHLIST (not statistically distinguishable)

**Blocking question:** Is ETH conf≥0.75 a genuinely better signal than BTC conf≥0.75?
Cannot fully answer in 30 days. This is a secondary frontier.

---

## 3. Required Metrics and Fields

This section lists all fields that must be present in trade-level evidence
for a snapshot to be included in a frontier's analysis. Missing fields make
the trade count as "lower quality" — it still counts toward n, but is flagged.

### Tier 1 Fields (required — missing = flag trade as partial)

| Field | Source | Use |
|---|---|---|
| `pnl_usdc` | trade_journal (trade_close) | Win/loss classification |
| `candidate_id` | trade_journal | Join key to decision_log |
| `asset` | trade_journal or decision_log | BTC/ETH split |
| `side` | trade_journal or decision_log | YES/NO split |
| `market_regime` | decision_log | Regime classification |
| `lifecycle_phase` | decision_log | OPENING_SCAN vs AI confirmation |
| `orderbook_state_classification` | decision_log | ob_state for analysis |
| `confidence` | decision_log | Confidence band assignment |
| `ev_after_spread` | decision_log | EV for inversion analysis |
| `true_probability` | decision_log | Calibration gap calculation |
| `run_id` | any event | Session diversity tracking |
| `timestamp_utc` | any event | Calendar day tracking |

### Tier 2 Fields (preferred — present if post-patch run)

| Field | Source | Use |
|---|---|---|
| `probability_model_reason` | decision_log (Tier 1 patch) | Direction + quality tokens |
| `prob_model_momentum_input` | decision_log (Tier 1 patch) | Momentum confirmation (=0 in AI) |
| `prob_model_liquidity_usd` | decision_log (Tier 1 patch) | liq_mult derivation |
| `price_change_pct` | decision_log (Tier 2 patch) | Regime signal input |
| `realized_volatility` | decision_log (Tier 2 patch) | Vol quality input |
| `distance_from_ptb_pct` | decision_log (Tier 2 patch) | Distance saturation check |

### Tier 3 Fields (optional — enrichment only)

| Field | Source | Use |
|---|---|---|
| `seconds_remaining` | decision_log | Timing analysis |
| `spread` | decision_log | Wide spread frontier |
| `best_bid_size`, `best_ask_size` | decision_log | Book depth context |
| `total_bid_depth_l1_l3`, `total_ask_depth_l1_l3` | decision_log | Liquidity reconstruction |
| `clob_api_failure` | decision_log | CLOB health tracking |
| `yes_bid`, `yes_ask`, `no_bid`, `no_ask` | decision_log | Binary price availability |

### Minimum Tier Coverage Per Analysis

- For any analysis contributing to VERIFIED promotion: ≥80% of trades must have all Tier 1 fields
- For calibration gap analysis: `true_probability` must be present in ≥70% of the n count
- For regime-specific analysis: `market_regime` must be present in ≥90% of the n count
- For EV analysis: `ev_after_spread` must be present in ≥85% of the n count
- If Tier 2 fields are absent: note the limitation but do not exclude trade from n count

---

## 4. Minimum Sample Size Gates

These are hard gates. No frontier analysis proceeds to the next review stage
without meeting the n threshold for that stage.

### Per-Frontier Minimum Gates

| Frontier | Minimum n for Snapshot | Minimum n for Interim Review | Minimum n for Promotion Review |
|---|---|---|---|
| AI EV Inversion | 400 | 450 | **500** |
| MICRO_RECOVERY outcomes | 50 conf≥0.75 | 75 conf≥0.75 | **100** conf≥0.75 |
| BTC COMP confidence inversion | 70 | 100 | **150** |
| ETH NO COMP | 60 | **100** (30-day gate) | 350 (full VERIFIED) |
| ETH conf≥0.75 outperforms BTC | 10 ETH | **20** ETH | 50 ETH |
| stale_orderbook | — | — | **30** (deferred beyond 30 days) |

### Sub-cell Minimum Gates

These apply to specific analysis within a frontier:

| Analysis | Minimum n for inclusion | Note |
|---|---|---|
| BTC COMP true_p 0.65–0.70 bucket | 30 | Currently n=29 — almost met |
| BTC COMP per confidence band | 15 per band | Band 0.65–0.75 currently n=25 ✓ |
| TREND_UP AI EV_Δ | 80 | Currently n=63 — 17 more needed |
| ETH NO COMP per session claim | 5 per session | For session-level win rate claims |
| ETH vs BTC win rate comparison at conf≥0.75 | 30 BTC + 15 ETH | Both sides needed simultaneously |

### n Counting Rules

1. **Only real paper trades count.** Filter by `mode=paper` and exclude trades
   with `reason=test` or `size=10.0` at `entry_price=0.5` (known test artifacts).
2. **Only confirmed trade_close events count.** trade_open events do not count toward n.
3. **pnl must be non-null.** Trades without pnl are excluded from n.
4. **|pnl| ≤ $0.50 filter applies.** Trades with |pnl| > $0.50 are flagged as
   potential artifacts and excluded from standard n counts.
5. **All sessions count.** Do not exclude MICRO_RECOVERY or CLOB degradation sessions —
   these are real operating conditions and must be represented in the evidence.
6. **CLOB degradation sessions are flagged but not excluded.** Tag sessions where
   >50% of decisions are `orderbook_unavailable` as CLOB_DEGRADED. Include their
   trades with the tag for analysis.

---

## 5. Daily Review Workflow

### What to do every day the runtime is active

**Step 1: Count new trades in each tracked cell (5 minutes)**

For each of the six frontiers, count new trade_close events since last review:
```
Frontier A (AI EV):          new_n = trades_today with lifecycle_phase=ACTIVE_INVENTORY
Frontier B (MICRO_RECOVERY): new_n = trades_today with confidence ≥ 0.75
Frontier C (BTC COMP OS):    new_n = trades_today where asset=BTC, regime=COMPRESSION, phase=OPENING_SCAN
Frontier D (ETH NO COMP):    new_n = trades_today where asset=ETH, side=NO, regime=COMPRESSION
Frontier E (stale):          new_n = trades_today with ob_state=stale_orderbook
Frontier F (ETH conf≥0.75):  new_n = trades_today where asset=ETH, confidence ≥ 0.75
```

**Step 2: Update running totals**
Maintain a running total for each frontier against the cumulative n from the prior
snapshot. Mark any frontier that crosses 10 new trades since last snapshot.

**Step 3: Trigger snapshot if threshold met**
If any frontier has ≥ 10 new trades since last snapshot:
- Append a new snapshot to that frontier's watchlist file
- Record: new n, win rate for new increment only, cumulative win rate, calibration gap
- Update `current_n` in WATCHLIST_INDEX.md

**Step 4: Check for CLOB degradation**
If today's decision_log shows > 50% `orderbook_unavailable` decisions:
- Tag today's evidence as CLOB_DEGRADED in the daily log
- Note that CLOB_DEGRADED sessions will be included in n counts but flagged in analysis

**Step 5: Note risk mode state**
If risk mode is MICRO_RECOVERY at end of day:
- Log which conf≥0.75 trades were entered
- Note whether the cascade loop pattern repeated (ETH COMP losses → BTC COMP selections)

---

## 6. Day 5 / Day 17 / Day 28 Review Criteria

These are the three structured review checkpoints with decision authority.

---

### Day 5 Review (target: ~2026-06-05)

**Primary objective:** Close Frontier A (AI EV Inversion to VERIFIED)

**Criteria for VERIFIED declaration:**
- [ ] Total AI trade closes ≥ 500
- [ ] Pearson r(EV, PnL) for full population ∈ [−0.05, +0.05]
- [ ] Q4 win rate < Q1 win rate in the full population
- [ ] ETH-only Pearson r < +0.05 (inverted or zero)
- [ ] BTC-only EV_Δ still positive (W_ev > L_ev for BTC)
- [ ] Evidence comes from ≥ 3 independent sessions
- [ ] No code changes to probability_model.py or signal.py since May 30

**If all criteria met:** Update ACTIVE_INVENTORY_EV_INVERSION.md status to VERIFIED.
Update WATCHLIST_INDEX.md. Update RESEARCH_FRONTIER_DASHBOARD.md Section 1.

**If criteria NOT met (n < 500):**
- Report reason for shortfall (CLOB degradation? Low session frequency?)
- Adjust Day 7 target and continue collection

**Secondary check at Day 5:**
- TREND_UP EV_Δ at current n (expected ~90): still positive?
- ETH NO COMP new increment win rate: consistent with 30.8% baseline?
- BTC COMP OS new increment: any change to confidence band win rates?

---

### Day 17 Review (target: ~2026-06-17)

**Primary objective:** Evaluate MICRO_RECOVERY outcomes at n=100 conf≥0.75

**Criteria for VERIFIED declaration (outcomes):**
- [ ] Total conf≥0.75 trades ≥ 100
- [ ] BTC share at conf≥0.75 ≥ 75% in the full 100-trade population
- [ ] COMPRESSION share at conf≥0.75 ≥ 55%
- [ ] BTC COMPRESSION conf≥0.75 win rate < 35% in full population AND < 40% in new n=60 increment
- [ ] ETH conf≥0.75 win rate cannot be calculated meaningfully (< 20 ETH trades)
- [ ] Calibration gap at conf≥0.75 > +0.35
- [ ] Evidence from ≥ 3 independent sessions

**If all criteria met:** Update MICRO_RECOVERY_SELECTION.md outcomes to VERIFIED.
Update WATCHLIST_INDEX.md and RESEARCH_FRONTIER_DASHBOARD.md.

**Secondary objectives at Day 17:**
- ETH NO COMP n=100 check (expected ~100 by Day 11, re-verify at Day 17)
  - Report p-value at current n — should be improving from 0.145
  - If p < 0.10: strong OBSERVED, note in ETH_NO_COMPRESSION.md
  - If p > 0.30: trigger DOWNGRADE_REVIEW protocol (Section 8)
- TREND_UP EV (expected n=100 by Day 7): confirm EV_Δ still positive in full n
- BTC COMP OS (expected ~135 trades): interim analysis at n=100

---

### Day 28 Review (target: ~2026-06-28)

**Primary objective:** Promote BTC COMP confidence inversion to VERIFIED

**Criteria for VERIFIED declaration:**
- [ ] Total BTC×COMPRESSION×OPENING_SCAN trades ≥ 150
- [ ] true_p 0.65–0.70 bucket n ≥ 50 with win rate < 25%
- [ ] Confidence band inversion is monotone or near-monotone across 4 bands
  - Acceptable: 3 of 4 bands show downward inversion; one minor violation allowed
  - Not acceptable: two or more bands show upward violation
- [ ] Calibration gap overall > +0.25
- [ ] Calibration gap in 0.65–0.70 bucket > +0.40
- [ ] Evidence from ≥ 3 independent sessions
- [ ] No code changes to probability_model.py or signal.py since May 30

**If all criteria met:** Update BTC_COMPRESSION_OPENING_SCAN.md to VERIFIED.
Update WATCHLIST_INDEX.md and RESEARCH_FRONTIER_DASHBOARD.md.

**Secondary objectives at Day 28:**
- ETH NO COMP n (expected ~140): report p-value trajectory
  - If win rate < 35% and p < 0.15: strong OBSERVED confirmed
  - If win rate drifting toward 38%: note softening
- ETH conf≥0.75 n (expected ~20): first formal win rate analysis
- MICRO_RECOVERY cascade loop: count how many sessions triggered the pattern
  - Need ≥ 3 sessions with documented cascade for the loop to reach OBSERVED

---

## 7. Promotion Rules: OBSERVED → VERIFIED

A frontier may be promoted to VERIFIED only when all conditions in its
specific check list AND all universal conditions are met.

### Universal Conditions (all frontiers)

| Condition | Requirement |
|---|---|
| Minimum n | Per frontier gate (Section 4) — hard gate, no exceptions |
| p-value (correct tail) | < 0.05 |
| Session diversity | Evidence from ≥ 3 independent run sessions |
| Calendar breadth | ≥ 7 unique calendar days in the evidence set |
| Code stability | No changes to `probability_model.py`, `signal.py`, `risk_modes.py` or `risk_manager.py` since the starting n snapshot |
| Data quality | ≥ 80% of trades in the n count have all Tier 1 fields populated |
| Direction consistency | Pattern direction present in ≥ 70% of contributing sessions |
| Reviewer sign-off | Named reviewer (not the analysis tool) acknowledges the promotion |

### Frontier-Specific Promotion Conditions

**Frontier A (AI EV Inversion):**
- Pearson r(EV, PnL) ∈ [−0.05, +0.05] at n ≥ 500
- Q4 win rate < Q1 win rate
- ETH-specific inversion confirmed (ETH-only r ≤ 0)
- BTC-specific normal sign confirmed (BTC-only EV_Δ > 0)

**Frontier B (MICRO_RECOVERY outcomes):**
- n ≥ 100 conf≥0.75 trades
- BTC share at conf≥0.75 ≥ 75% in the full n (mechanism already VERIFIED)
- BTC COMPRESSION conf≥0.75 win rate < 35%
- Outcome win rate at conf≥0.75 < 35% (currently 27.5% at n=40)
- p (lower tail, conf≥0.75 population vs baseline) < 0.05

**Frontier C (BTC COMP confidence inversion):**
- n ≥ 150 BTC×COMPRESSION×OS
- true_p 0.65–0.70 bucket: n ≥ 50 AND win rate < 25%
- Inversion monotone or near-monotone (≤ 1 band violation)
- Calibration gap > +0.25 at overall level

**Frontier D (ETH NO COMP):**
- n ≥ 350 (statistical VERIFIED) — outside 30-day window
- 30-day target: strong OBSERVED at n=100 with p < 0.15
- Full VERIFIED requires p < 0.05 (requires n ≈ 350 at current effect size)

**Frontier F (ETH conf≥0.75):**
- n ≥ 50 ETH conf≥0.75 trades (outside 30-day window for most sessions)
- 30-day target: n ≥ 20 with win rate consistently > 50%

---

## 8. Demotion Rules: OBSERVED → NOT SUPPORTED

A frontier is demoted when the evidence materially contradicts the pattern
across a substantial new data block.

### Universal Demotion Triggers

| Trigger | Condition |
|---|---|
| Win rate reversal | New win rate exceeds OBSERVED pattern by > 10pp on n ≥ 30 new trades |
| p-value too high | p (correct tail) > 0.30 on new n ≥ 50 block |
| Calibration collapse | avg(true_p) − win_rate < +0.10 on n ≥ 30 |
| Session contradiction | ≥ 6 of last 10 sessions contradict the pattern |

### Frontier-Specific Demotion Conditions

**Frontier A (AI EV Inversion → NOT SUPPORTED):**
- Pearson r(EV, PnL) > +0.15 on new n ≥ 100 AI trades
- Q4 win rate exceeds Q1 by > 5pp on new n ≥ 100

**Frontier B (MICRO_RECOVERY → NOT SUPPORTED for outcomes):**
- BTC COMPRESSION conf≥0.75 win rate rises above 45% on new n ≥ 30 conf≥0.75 trades
- Note: the selection mechanism itself (V1, V2) cannot be demoted — it is mathematical

**Frontier C (BTC COMP inversion → NOT SUPPORTED):**
- true_p 0.65–0.70 bucket win rate rises above 35% on new n ≥ 25 in that bucket
- Two or more confidence bands show upward violation on new n ≥ 15 each

**Frontier D (ETH NO COMP → NOT SUPPORTED):**
- Win rate rises above 45% on new n ≥ 30 trades AND p (lower tail) > 0.30
- avg(true_p) drifts below 0.62 (signals model or code change, not market change)

**Frontier F (ETH conf≥0.75 → WATCHLIST only):**
- Win rate falls below 45% on new n ≥ 15 ETH conf≥0.75 trades

### Demotion Process

1. The analysis that triggers a demotion condition records it as a snapshot
   with header `⚠ DEMOTION_CANDIDATE` in the watchlist file
2. The snapshot records: triggering evidence, n of new block, prior n, delta
3. A reviewer acknowledges the demotion candidate and approves or overrules
4. If approved: status is updated to NOT_SUPPORTED in watchlist file AND in WATCHLIST_INDEX.md
5. All prior snapshots are preserved (no deletion)
6. The RESEARCH_FRONTIER_DASHBOARD.md is updated to move the finding to Section 4 (NOT SUPPORTED)

---

## 9. Phase 2 Blockers

Phase 2 is: paper-only inventory replay, reload/unload analysis, MFE/MAE tracking.
These are the conditions that must be resolved before Phase 2 can be interpreted
with confidence.

### Hard Blockers (Phase 2 cannot start until resolved)

**Blocker PH2-1: AI EV Inversion must reach VERIFIED**
- Phase 2 inventory replay uses MFE/MAE to evaluate exit quality.
- If EV is an anti-signal, any Phase 2 analysis that incorporates EV-based
  exit evaluation will be backwards.
- **Gate:** Frontier A reaches VERIFIED (n=500, Pearson r ≈ 0) — expected Day 5.
- **Action when met:** Note in Phase 2 design that EV cannot be used as exit signal for ETH.

**Blocker PH2-2: MICRO_RECOVERY session contamination must be documented**
- Phase 2 replay evidence collected during MICRO_RECOVERY sessions is biased —
  it reflects BTC COMPRESSION selection, not general entry quality.
- **Gate:** All Phase 2 evidence must be tagged with risk_mode state.
  MICRO_RECOVERY sessions are analyzed separately from NORMAL sessions.
- **Action:** Include `risk_mode` in the Phase 2 offline replay join methodology.
  Do not pool NORMAL and MICRO_RECOVERY trades in Phase 2 without the risk_mode split.

### Soft Blockers (Phase 2 can start but analysis is limited)

**Soft Blocker PH2-3: BTC COMP confidence inversion at VERIFIED**
- Phase 2 entry policy design for BTC COMPRESSION will be stronger with VERIFIED
  evidence about which confidence bands underperform.
- Phase 2 can START before this is verified but BTC COMP entry policy in Phase 2
  should be held at draft status until Frontier C reaches VERIFIED.

**Soft Blocker PH2-4: ETH NO COMP at n=100**
- Phase 2 inventory replay includes ETH NO COMPRESSION positions.
- Before n=100, the pattern direction is confirmed but the statistical signal
  is weak (p=0.145). Phase 2 must acknowledge this uncertainty explicitly.

### Phase 2 Pre-Conditions Checklist

Before beginning Phase 2 analysis, confirm:

- [ ] PH2-1: AI EV Inversion → VERIFIED (expected Day 5)
- [ ] PH2-2: risk_mode field documented in Phase 2 join methodology
- [ ] Evidence period for Phase 2 replay uses post-observability-patch data only
  (Tier 1 + Tier 2 patches deployed May 30 — all evidence after this date is
  post-patch eligible)
- [ ] MICRO_RECOVERY sessions tagged and split in Phase 2 data pipeline
- [ ] No Phase 2 analysis uses EV as a hold/exit signal for ETH positions

---

## 10. Final 30-Day Operating Plan

### Week 1 (Days 1–7): Foundation Closing

**Target:** Close Frontier A. Establish Frontier C baseline.

| Day | Action |
|---|---|
| Day 1–2 | Passive accumulation. No analysis required. |
| Day 4 | If AI trades ≥ 500: run Frontier A full analysis. Record VERIFIED if criteria met. |
| Day 5 | Day 5 Review (Section 6). Declare AI EV status. Check TREND_UP EV at current n. |
| Day 7 | If TREND_UP AI trades ≥ 100: run EV_Δ analysis. If still +0.028 or better: promote to OBSERVED. |

**Week 1 deliverable:** AI EV Inversion = VERIFIED. TREND_UP EV = OBSERVED (if n=100 met).

---

### Week 2 (Days 8–14): Mid-term Evidence

**Target:** ETH NO COMP n=100. Conf≥0.75 at n=70.

| Day | Action |
|---|---|
| Day 8–10 | Passive accumulation. |
| Day 11 | If ETH NO COMP ≥ 100: run full Frontier D analysis at n=100. Apply n=100 decision table (Section 2D). Append snapshot to ETH_NO_COMPRESSION.md. |
| Day 12–14 | If conf≥0.75 ≥ 70: run interim MICRO_RECOVERY analysis. Not yet promotion-level but note trajectory. |

**Week 2 deliverable:** ETH NO COMP classified per n=100 decision table. MICRO_RECOVERY n=70 snapshot appended.

---

### Week 3 (Days 15–21): Structured Review

**Target:** MICRO_RECOVERY outcomes n=100. BTC COMP n=100 interim.

| Day | Action |
|---|---|
| Day 15–16 | Passive accumulation. |
| Day 17 | Day 17 Review (Section 6). Declare MICRO_RECOVERY outcome status. BTC COMP n=100 interim analysis. |
| Day 18–21 | If ETH conf≥0.75 ≥ 20: first formal win rate analysis for Frontier F. |

**Week 3 deliverable:** MICRO_RECOVERY outcomes VERIFIED or Strong OBSERVED. BTC COMP interim confirmed.

---

### Week 4 (Days 22–30): Final Verification

**Target:** BTC COMP n=150. All watchlists updated.

| Day | Action |
|---|---|
| Day 22–27 | Passive accumulation. Append snapshots when thresholds crossed. |
| Day 28 | Day 28 Review (Section 6). Declare BTC COMP status at n=150. |
| Day 29 | Append all watchlist snapshots. Update WATCHLIST_INDEX.md. |
| Day 30 | Update RESEARCH_FRONTIER_DASHBOARD.md with all status changes. Prepare Phase 2 readiness statement. |

**Week 4 deliverable:** BTC COMP VERIFIED or strong OBSERVED at n=150. All watchlists current. Phase 2 blockers assessed.

---

### 30-Day Summary of Expected Outcomes

| Frontier | Start Status | Expected End Status | Gate Condition |
|---|---|---|---|
| AI EV Inversion | OBSERVED (n=384) | **VERIFIED** | n=500, Pearson r≈0 |
| MICRO_RECOVERY outcomes | OBSERVED (n=40) | **VERIFIED** or Strong OBSERVED | n=100, BTC COMP wr<35% |
| BTC COMP confidence inversion | OBSERVED (n=59) | **VERIFIED** or Strong OBSERVED | n=150, true_p bucket wr<25% |
| ETH NO COMP | OBSERVED (n=52) | Strong OBSERVED (n=100) | p improving, wr<40% |
| TREND_UP EV predictability | WEAK SIGNAL (n=63) | **OBSERVED** | n=100, EV_Δ>0 confirmed |
| ETH conf≥0.75 outperforms BTC | WEAK SIGNAL (n=5) | OBSERVED (n=20) or maintained WATCHLIST | ETH wr>50% at n=20 |
| stale_orderbook | OBSERVED (n=9) | OBSERVED (n=15–20 if lucky) | Passive only |

---

### Failure Modes to Watch For

**Evidence drought:** If CLOB degradation continues (>50% `orderbook_unavailable`
per day), trade frequency drops. In a CLOB_DEGRADED session, ETH NO COMP and
BTC COMP OS entries may be skewed toward `orderbook_unavailable` state trades
which have anomalous win rates (+55%). Flag all evidence collected during
CLOB_DEGRADED sessions and analyze separately when n of clean sessions allows.

**Run-length concentration:** If the majority of new evidence comes from
one long run session, the evidence is concentrated. Pause and wait for a
session restart to get at least two independent run_ids contributing to the n.

**Systematic code change:** If a probability_model.py or signal.py change
is made (even for bug fixes), freeze all frontier n counts at the pre-change
date. Evidence before and after a model change cannot be pooled without
explicit documentation of what changed and in what direction.

---

*This plan defines evidence requirements. It does not propose fixes.*
*All evidence collection is observational. No runtime, strategy, risk,*
*confidence, EV, or execution changes are authorized during this plan period.*
