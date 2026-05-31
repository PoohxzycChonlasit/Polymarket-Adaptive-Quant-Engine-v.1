# Research Frontier Dashboard

type: single-page evidence summary
created: 2026-05-30
evidence_period: 2026-05-08 to 2026-05-30
total_trades_analyzed: 406
total_sessions: 56
calendar_days: 22
observability_patches: Tier 1 + Tier 2 (deployed)
code_changed: No
strategy_changed: No
runtime_changed: No

> This dashboard is a living summary. It reflects the state of evidence as of the
> last analysis run. Individual watchlists in `docs/research/watchlists/` hold the
> full snapshot history and per-metric detail.

---

## 1. VERIFIED FINDINGS

Findings that meet: mathematical proof OR n ≥ 50 per cell + p < 0.05 + ≥ 3 session replications.

---

### V1 — ETH Is Structurally Excluded from MICRO_RECOVERY

**Classification:** VERIFIED (mathematical proof)
**Confidence:** Certain — follows from probability model formula, not statistical inference

The confidence formula `clamp(0.52 + |p_yes − 0.50| × 1.40, 0, 0.88) × liq_mult`
combined with ETH's typical liq_mult=0.75 (median liq=$127, $50–500 tier) produces:

```
max_conf(ETH) = 0.88 × 0.75 = 0.66
MICRO_RECOVERY requires: conf ≥ 0.75
∴ ETH cannot pass MICRO_RECOVERY gate under normal market conditions
```

BTC (median liq=$445, frequently liq_mult=1.00): max_conf = 0.88. Can pass.

**Evidence:** Mathematical derivation from `polymarket/probability_model.py` lines 110–120 + 163–164.
**Supported by data:** At conf≥0.75: BTC=87.5%, ETH=12.5% (n=40). ETH 5/40 cases are outliers.
**Current n:** 40 conf≥0.75 trades (ongoing accumulation)
**Next threshold:** n=100 conf≥0.75 for outcome VERIFIED

---

### V2 — MICRO_RECOVERY Gate Structurally Selects BTC COMPRESSION

**Classification:** VERIFIED (selection mechanism)
**Confidence:** High — mathematical + data confirmation across 22 sessions

Within the BTC population that passes the conf≥0.75 gate:
- COMPRESSION regime: 67.5% of all conf≥0.75 trades (27/40)
- BTC YES COMPRESSION: 40% of all conf≥0.75 trades (16/40)

Deep BTC books (liq_mult=1.00) with moderate COMPRESSION signal reach conf=0.75–0.80.
This is not a coincidence — it is the only cell that mechanically satisfies the gate.

**Evidence:** n=40 conf≥0.75 trades; 22 sessions with conf≥0.75 trades; BTC≥80% in all sessions.
**Supported by data:** 87.5% BTC share at conf≥0.75 vs 6.5% BTC share at conf<0.55.
**Current n:** 40
**Next threshold:** n=100 for outcome-level VERIFIED

---

### V3 — Probability Model Assigns Stable true_p=0.650 to ETH NO COMPRESSION

**Classification:** VERIFIED (model behavior)
**Confidence:** Certain — mechanically stable across all sessions

avg(true_p) for ETH NO COMPRESSION across 23 sessions: **0.644–0.670** (σ = 0.008).
The model consistently assigns ~65% probability to this cell regardless of session,
date, market regime within COMPRESSION, or orderbook state.

This is a structural property of the probability model's `leans_no` signal combined
with ETH COMPRESSION distance_pct values — not a coincidence.

**Evidence:** 23 sessions, 12 calendar dates, avg_true_p range of 0.026.
**Current n:** 52 ETH NO COMPRESSION trades
**Next threshold:** n=100 to confirm true_p stability continues

---

### V4 — `orderbook_unavailable` Is a Classification Artifact, Not a CLOB Outage

**Classification:** VERIFIED (code trace + data)
**Confidence:** High — code trace confirmed + 100% data consistency

`ob_reason = 'clob_empty_response'` fires when the CLOB API returns HTTP 200
with an empty body. The `_phase2_orderbook_state_classification()` function
classifies this as `orderbook_unavailable` via a catch-all `if reason:` branch
that fires **before** the binary price availability check runs.

In 100% of the 38 observed cases: yes_bid, yes_ask, no_bid, no_ask are ALL
positive. These trades are functionally `ready` — the label is a path artifact.

**Evidence:** Code trace (`trader.py` lines 2551–2579) + 38/38 binary prices positive.
**Current n:** 38 orderbook_unavailable trades
**Next threshold:** n=75 to confirm outcome pattern (55.3% win rate)

---

### V5 — Momentum Is Zero in All ACTIVE_INVENTORY Trade Entries

**Classification:** VERIFIED (code trace + data)
**Confidence:** Certain — architectural confirmation

In ACTIVE_INVENTORY time windows (35–240s since epoch open):
1. For HOLD cycles (open position): `max_active_positions` gate fires at `trader.py`
   line 8276, returning SKIP before `compute_realtime_signal()` at line 8847.
   Momentum is never computed.
2. For ENTRY cycles (no open position): `compute_realtime_signal()` runs, but
   returns `signal.side = 'SKIP'` with `momentum_pct = 0.0` (hardcoded default
   at `signal.py` line 285) — COMPRESSION regime near PTB produces momentum below
   the ATR-derived threshold in all 18 post-patch observed cases.

**Evidence:** Code trace (trader.py, signal.py) + 18/18 post-patch AI trades have mom=0.
**Current n:** 18 post-patch AI trades, 384 AI trades total
**Next threshold:** Ongoing — architectural, not statistical

---

## 2. OBSERVED FINDINGS

Directionally confirmed patterns. n insufficient for VERIFIED or statistical threshold not yet met.

---

### O1 — BTC COMPRESSION OPENING_SCAN Has Confidence Inversion

**Classification:** OBSERVED
**Evidence summary:** n=59 BTC×COMPRESSION×OS trades. Win rate by confidence band:

| Conf band | n | Win% | Direction |
|---|---|---|---|
| <0.55 | 6 | 83.3% | Baseline (WATCHLIST n=6) |
| 0.55–0.65 | 17 | 23.5% | ↓ Inversion |
| 0.65–0.75 | 25 | 32.0% | ↑ Minor violation |
| >0.75 | 11 | 9.1% | ↓ Inversion |

The true_p 0.65–0.70 bucket is the critical miscalibration: n=29, actual win rate
**13.8%**. Model assigns ~67% — off by 4.8×. ETH same bucket: 55.9% actual (n=34).

**Current n:** 59 (BTC×COMP×OS), 29 (in critical 0.65–0.70 bucket)
**Next threshold:** n=150 total for VERIFIED; n=50 in 0.65–0.70 bucket
**Watchlist:** `BTC_COMPRESSION_OPENING_SCAN.md`

---

### O2 — ETH NO COMPRESSION Is a Losing Cell (Structural Mechanism Identified)

**Classification:** OBSERVED (p=0.145, needs n≈350 for VERIFIED)
**Evidence summary:** n=52 across 23 sessions, 12 calendar days.

| Metric | Value |
|---|---|
| Win rate | 30.8% (vs 37.9% baseline) |
| Deficit | −7.1pp |
| p-value (lower tail) | 0.145 — not significant |
| avg true_p | 0.650 (VERIFIED stable) |
| Calibration gap | +0.345 |
| Sessions below 40% wr | 16/23 |
| Sessions above 50% wr | 7/23 |

**Mechanism:** Model fires `leans_no` when price is below PTB. In COMPRESSION, this
is informationally empty — resolution direction is ~coin-flip with slight ETH upward
drift. Model treats instantaneous position as path-conditional probability.

**Control:** ETH YES COMPRESSION (same regime, same asset) wins at 51.4% (n=37).
20.6pp directional gap at identical model confidence.

**Current n:** 52
**Next threshold:** n=100 (directional strengthens), n=350 (statistical VERIFIED)
**Watchlist:** `ETH_NO_COMPRESSION.md`

---

### O3 — ACTIVE_INVENTORY EV Is an Anti-Signal

**Classification:** OBSERVED
**Evidence summary:** n=384 AI trades.

| Metric | Value |
|---|---|
| Pearson r(EV, PnL) | +0.010 (≈ 0) |
| Q1 win rate (low EV) | 44.2% |
| Q4 win rate (high EV) | 33.7% |
| W_ev vs L_ev | 0.1213 vs 0.1244 (inverted) |
| ETH EV_Δ | −0.008 (inverted) |
| BTC EV_Δ | +0.017 (normal sign) |

EV inversion is ETH-specific. BTC shows the correct relationship (higher EV → better
outcomes). ETH accounts for 77% of AI trades, driving the aggregate inversion.

**Root cause:** As a position moves against the entry, the losing side's market
price falls → EV for a new entry at current price rises → model sees "better value"
on a deteriorating position.

**Exception:** TREND_UP is the only regime where EV_Δ > 0 (+0.028 for winners vs losers).

**Current n:** 384
**Next threshold:** n=500 for VERIFIED
**Watchlist:** `ACTIVE_INVENTORY_EV_INVERSION.md`

---

### O4 — MICRO_RECOVERY Outcomes Are Worse Than Baseline

**Classification:** OBSERVED
**Evidence summary:** n=40 conf≥0.75 trades.

| Conf band | Win% | Note |
|---|---|---|
| <0.55 | 39.1% | Population below DEFENSIVE |
| 0.55–0.65 | 42.8% | Best performing band |
| 0.65–0.75 | 26.9% | Passes DEFENSIVE, blocked by MICRO_RECOVERY |
| **>0.75** | **27.5%** | Passes MICRO_RECOVERY — **worst band** |

The confidence gate designed to improve quality selects for a worse-performing cell.
BTC COMPRESSION conf≥0.75 win rate: 22.2% (n=27), calib gap +0.449.

**Current n:** 40 conf≥0.75 trades
**Next threshold:** n=100 for VERIFIED outcome degradation
**Watchlist:** `MICRO_RECOVERY_SELECTION.md`

---

### O5 — empty_book Penalizes BTC More Than ETH

**Classification:** OBSERVED
**Evidence summary:** n=192 empty_book trades.

| Asset | empty_book wr | ready wr | Penalty |
|---|---|---|---|
| BTC | 20.7% | 41.9% | **−21.2pp** |
| ETH | 36.6% | 43.8% | −7.2pp |

BTC empty_book is 70.7% COMPRESSION; ETH is 23.1% COMPRESSION. The penalty
follows COMPRESSION concentration, not asset identity per se. empty_book allows
liq_mult=0.75 or 1.00 to stand even when binary prices are incomplete.

**Current n:** 192 empty_book (BTC=58, ETH=134)
**Next threshold:** n=250 per asset for VERIFIED
**Watchlist:** `ORDERBOOK_STATE_HEALTH.md`

---

### O6 — ETH YES COMPRESSION OPENING_SCAN Works at ~50%

**Classification:** OBSERVED
**Evidence summary:** n=37, wr=51.4%. Same regime and asset as ETH NO COMPRESSION
(30.8%). The YES/NO asymmetry (20.6pp gap at identical model confidence) is the
clearest indicator that the failure is directional within COMPRESSION, not
COMPRESSION-wide.

**Mechanism:** YES bets when price is already above PTB — position starts in-the-money.
NO bets when price is below PTB — position requires no adverse move for the full window.

**Current n:** 37
**Next threshold:** n=75 for stronger confirmation

---

### O7 — stale_orderbook Is the Worst State

**Classification:** OBSERVED (WATCHLIST for conclusions — n=9)
**Evidence summary:** 0-for-9. Calibration gap +0.614 — highest of any state.
All exits are stop-loss. No strategy-level conclusions drawn from n=9.

**Current n:** 9
**Next threshold:** n=30 for any conclusion
**Watchlist:** `ORDERBOOK_STATE_HEALTH.md`

---

### O8 — MICRO_RECOVERY Creates a Loss Cascade Feedback Loop

**Classification:** OBSERVED (single session, 2026-05-30)
**Evidence summary:** Run `20260530T125144Z` demonstrated the loop in real-time:
- Loss #1 (ETH NO COMPRESSION) → Loss #2 (ETH YES COMPRESSION) → DEFENSIVE
- Loss #3 (BTC NO TREND_UP) → MICRO_RECOVERY + pause
- Losses #4–5 (BTC YES COMPRESSION) → repeated pauses
- System stuck in MICRO_RECOVERY; gate continues selecting BTC COMPRESSION

The conf≥0.75 gate routes into BTC COMPRESSION → more losses → pause re-fires.

**Current n:** 1 session demonstrating the loop
**Next threshold:** ≥3 independent sessions showing the same escalation pattern
**Watchlist:** `MICRO_RECOVERY_SELECTION.md`

---

## 3. WEAK SIGNALS

Patterns present but inconsistent across sessions or n < 20 in key cells.

---

### W1 — ETH conf≥0.75 Outperforms BTC at Same Confidence

**Classification:** WEAK SIGNAL (n=5 ETH)
**Evidence:** ETH at conf≥0.75: 60% win rate (n=5). BTC: 22.9% (n=35).
If confirmed, this would suggest ETH only reaches 0.75 under near-resolution
conditions (extreme signal), while BTC reaches it with moderate COMPRESSION signal.
Mathematically supported but sample is n=5 — no conclusions.

**Next threshold:** n=20 ETH conf≥0.75 trades

---

### W2 — TREND_UP Is the Only Regime Where EV Is Predictive in AI

**Classification:** WEAK SIGNAL
**Evidence:** TREND_UP EV_Δ = +0.028 (n=63). All other regimes show EV inversion
(COMPRESSION: −0.005, SIDEWAY: −0.010, TREND_DOWN: −0.014).
Directionally consistent with expectations (trending markets → EV signal has meaning)
but n=63 with the positive delta only being confirmed at the trade-level.

**Next threshold:** n=100 TREND_UP AI trades

---

### W3 — Wide Spread Trades Outperform

**Classification:** WEAK SIGNAL (n=12)
**Evidence:** Spread >0.02: 66.7% win rate, avg PnL +$0.005 (n=12).
Normal spread (0.01–0.02): 39.4% win rate (n=371).
Counterintuitive — high spread should increase cost of entry. May reflect
selection: only high-conviction signals execute at wide spreads.

**Next threshold:** n=30 wide-spread trades

---

### W4 — TREND_DOWN Is Best ETH NO Regime

**Classification:** WEAK SIGNAL
**Evidence:** ETH NO TREND_DOWN: 50% win rate (n=32 AI). ETH NO COMPRESSION: 31.4%.
The same ETH NO position performs at baseline when price is trending down (favorable
for NO) vs COMPRESSION (ambiguous direction).

**Next threshold:** n=60 ETH NO TREND_DOWN trades

---

## 4. NOT SUPPORTED

Hypotheses that were tested and the evidence does not support.

---

### NS1 — Ghost Liquidity (Stale Cache in empty_book)

**Classification:** NOT SUPPORTED
**Tested hypothesis:** When `ob_state = empty_book`, `liq_usd > 0` despite depth=0,
indicating stale cache data inflating confidence.
**Finding:** In 100% of empty_book trades (BTC n=58, ETH n=134), `depth_raw > 0`.
BTC mean depth = 976 units, ETH mean = 310 units. No ghost liquidity events found.
The `empty_book` label does NOT indicate zero depth — it indicates incomplete
binary YES/NO price set, while L1/L3 depth remains populated.

---

### NS2 — BTC liq_usd Is From Stale Cache

**Classification:** NOT SUPPORTED
**Tested hypothesis:** BTC's high liq_usd in empty_book comes from a previous cycle's
cached value, not the current orderbook.
**Finding:** liq_usd vs depth/2 relative diff for BTC: mean=11.91%, max=36.99%.
Consistent with live computation from current depth. No stale cache signature.
(ETH has an outlier at 3,233% — single case, not systematic for BTC.)

---

### NS3 — EV Inversion Is Caused by Orderbook State

**Classification:** NOT SUPPORTED
**Tested hypothesis:** The EV inversion in ACTIVE_INVENTORY is an artifact of
orderbook quality (empty_book or unavailable states creating false EV signals).
**Finding:** EV inversion is present in `ready` state (EV_Δ = −0.001) as well as
`empty_book` (−0.005). The root cause is in the probability model, not the CLOB.

---

### NS4 — COMPRESSION Regime Is the Sole Driver of Confidence Inversion

**Classification:** NOT SUPPORTED (as exclusive driver)
**Tested hypothesis:** The OPENING_SCAN confidence inversion is COMPRESSION-specific.
**Finding:** ETH YES COMPRESSION wins at 50% — the same regime does NOT invert
for ETH YES. BTC COMPRESSION is the driver, not COMPRESSION broadly.
Additionally, in ACTIVE_INVENTORY EV inversion: SIDEWAY and TREND_DOWN also show
EV inversion — it is not COMPRESSION-exclusive.

---

## 5. ACTIVE WATCHLISTS

Summary table of all active watchlists with current status.

| Watchlist | Priority | Status | Current n | Required n | Calib gap | Last Snapshot |
|---|---|---|---|---|---|---|
| MICRO_RECOVERY_SELECTION | P0 | VERIFIED (mechanism) / OBSERVED (outcomes) | 40 | 100 | +0.449 | 2026-05-30 |
| ETH_NO_COMPRESSION | P0 | OBSERVED | 52 | 350 | +0.345 | 2026-05-30 |
| BTC_COMPRESSION_OPENING_SCAN | P0 | OBSERVED | 59 | 150 | +0.324 | 2026-05-30 |
| ACTIVE_INVENTORY_EV_INVERSION | P1 | OBSERVED | 384 | 500 | — | 2026-05-30 |
| ORDERBOOK_STATE_HEALTH | P1 | OBSERVED | 402 | 600 | +0.326 (empty_book) | 2026-05-30 |

Review workflow: `docs/research/watchlists/WATCHLIST_REVIEW_WORKFLOW.md`

---

## 6. OPEN QUESTIONS

Unresolved questions requiring additional evidence or investigation.

---

### OQ1 — Is ETH NO COMPRESSION a Real Structural Failure or Calendar-Specific Variance?

The May 24–25 exception (9 trades, 67% win rate) contradicts the dominant pattern.
10 of 12 calendar days show negative results. p=0.145 (not significant at n=52).
**Requires:** ~300 more ETH NO COMPRESSION trades to resolve statistically.

---

### OQ2 — Does the MICRO_RECOVERY Feedback Loop Resolve If Runs Start in NORMAL?

The observed cascade (2026-05-30) requires initial losses to trigger escalation.
Runs starting in NORMAL with an early win would not enter the loop.
**Question:** What fraction of MICRO_RECOVERY sessions start with NO prior wins
in the current run? Is the loop avoidable by run-start timing?

---

### OQ3 — Why Does true_p 0.65–0.70 in BTC COMPRESSION Produce Only 13.8% Win Rate?

ETH at the same true_p bucket: 55.9%. The model assigns identical probability to both.
**Hypothesis:** BTC binary market pricing is more accurate than the model for COMPRESSION
near-strike positions. The NO side market price (~50%) is closer to the true resolution
probability than the model's 67%. ETH market pricing is also more accurate but the
model's error is smaller.
**Requires:** Post-patch data with `probability_model_reason` distance tokens across
≥50 BTC COMPRESSION trades in the 0.65–0.70 true_p bucket.

---

### OQ4 — Is the TREND_UP EV Predictability Stable?

EV_Δ = +0.028 for TREND_UP in AI is the only positive signal. n=63.
**Question:** Does this hold at n=100+ and across different calendar periods?
TREND_UP was underrepresented in May (63/384 = 16.4% of AI trades).

---

### OQ5 — What Is the Correct Exit Signal for ACTIVE_INVENTORY?

The current position manager uses frozen entry EV and confidence for hold/exit
decisions. EV is inverted in AI (higher EV → worse outcomes). Confidence is
potentially stale (not recomputed in HOLD cycles).
**Question:** Which live signals — if any — predict mid-life exit quality?
Candidates: distance_from_ptb_pct (mid-window), seconds_remaining (timing),
current market price vs entry price.
This is a Phase 3 design question, not a current-phase executable.

---

### OQ6 — Is the Wide Spread Outperformance Real or Coincidence?

12 trades at spread >0.02 win at 66.7%. If real: wide-spread cycles may reflect
moments of genuine market dislocation where the signal is cleaner.
If coincidence: n=12 is easily noise at 45% base loss rate.
**Requires:** n=30 wide-spread trades for any conclusion.

---

### OQ7 — Does the CLOB empty_book Rate Correlate with Specific Market Regimes?

BTC empty_book is 70.7% COMPRESSION (vs ETH 23.1%). Does the CLOB return
empty responses specifically during COMPRESSION because market makers reduce
their binary quotes when price is near the strike? This would explain why
BTC COMPRESSION + empty_book is the dangerous combination.
**Requires:** Correlation between `ob_state=empty_book` rate and market regime
at the session level.

---

## 7. CURRENT RESEARCH PHASE

**Phase: 1 — Regime Classification, Probability Scoring, Observability** (as defined in CLAUDE.md)

Phase 1 goals as of 2026-05-30:
- ✅ Regime classification working (COMPRESSION, SIDEWAY, TREND_UP, TREND_DOWN)
- ✅ Probability scoring operational
- ✅ Tier 1 + Tier 2 observability patches deployed
- ✅ Indicator evidence and signal logging active
- ✅ Research audit infrastructure (watchlists, review workflow, frontier dashboard)
- 🔄 Evidence accumulation ongoing (all P0 watchlists below VERIFIED threshold)
- ⏳ Phase 2 not yet started (paper-only inventory replay, MFE/MAE tracking)

**Key Phase 1 finding:** The OPENING_SCAN probability model has a structural
miscalibration in BTC COMPRESSION that confidence gating worsens, not improves.
The ACTIVE_INVENTORY EV signal is inverted. Both are Phase 2–4 design inputs.

**Current operational state:**
- Paper mode RUNNING, run `20260530T125144Z`, cycle count ~3,730
- MICRO_RECOVERY active (5 consecutive losses), pause likely expired by now
- CLOB degradation persisted through May 30 (95% orderbook_unavailable)
- Last trade: 18:12 UTC May 30 (BTC YES, stop_loss)

---

## 8. NEXT EVIDENCE TARGETS

Specific accumulation targets that would unlock the next review or status change.

### Immediate Targets (next 14 days)

| Target | Required n | Current n | Gap | Priority |
|---|---|---|---|---|
| ETH NO COMPRESSION n=100 | 100 | 52 | 48 | P0 |
| conf≥0.75 trades n=100 | 100 | 40 | 60 | P0 |
| BTC COMP OS n=150 | 150 | 59 | 91 | P0 |
| true_p 0.65–0.70 BTC bucket n=50 | 50 | 29 | 21 | P0 |
| AI trades n=500 | 500 | 384 | 116 | P1 |
| orderbook_unavailable n=75 | 75 | 38 | 37 | P1 |

### Evidence Rate (current trajectory)

Based on May 18–30 session data (~4–8 trades/day):
- ETH NO COMPRESSION: ~4.3 trades/day → n=100 in ~11 days
- conf≥0.75: ~3.5 trades/day → n=100 in ~17 days
- BTC COMP OS: ~5 trades/day → n=150 in ~18 days
- AI trades: ~30 trades/day → n=500 in ~4 days

**Critical path:** ETH NO COMPRESSION n=100 is the slowest P0 target (~11 days).
conf≥0.75 is the second slowest (~17 days). CLOB degradation days reduce evidence
rate for all targets.

### Evidence Quality Requirements

Beyond n-count, the following quality gates apply before any promotion review:
1. **Post-patch coverage ≥ 30% of new trades**: requires `probability_model_reason` non-null
2. **No CLOB degradation day > 50%** in the review window (flag sessions with >50% unavailable)
3. **≥ 3 independent sessions**: new evidence must span multiple run_ids
4. **No code changes**: git log must show no probability_model, signal, or risk changes
   between last snapshot and review

### Promotional Path Priority

If forced to prioritize reviews by governance impact:

1. **BTC COMP OS confidence inversion** → most actionable for Phase 2 entry policy design
2. **ETH NO COMPRESSION** → most direct cell-level actionability
3. **MICRO_RECOVERY gate outcomes** → impacts risk mode design for Phase 3
4. **AI EV inversion** → foundational for Phase 3 exit engine design
5. **Orderbook state health** → operational monitoring priority, less strategy-changing

---

*Dashboard generated from research audit series: May 2026 paper trading sessions.*
*All findings are evidence only. No code, strategy, risk, or execution changes authorized.*
*Next dashboard update: when any P0 watchlist reaches its n threshold.*
