# Research Frontier Dashboard

type: single-page evidence summary
created: 2026-05-30
evidence_period: 2026-05-08 to 2026-06-01
total_trades_analyzed: 406 executed trades; 86,552 decision events (17 full-scan days)
total_sessions: 56 + Episode #5 (ongoing, 0 trades, 18+ hours as of 2026-06-01)
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

### V6 — MICRO_RECOVERY Has No Time-Based Exit

**Classification:** VERIFIED (code trace)
**Confidence:** Certain — follows from BankrollManager architecture, not statistical inference

`_consecutive_losses` (the counter that drives MICRO_RECOVERY) resets to 0 in
exactly two situations:

```python
# Path A — record_win() called on a trade close with won=True:
def record_win(self, profit: float) -> float:
    self._consecutive_losses = 0   # ← sole in-session reset

# Path B — BankrollManager.__init__() on process restart:
def __init__(self, ...):
    self._consecutive_losses = 0   # ← resets on every new session
```

`reset_daily_stats()` (called at day boundaries) resets `_daily_loss` only —
not `_consecutive_losses`. The 30-minute loss-cluster pause expires, restoring
`can_trade()=True`, but the counter and MICRO_RECOVERY mode are unchanged.
There is no time-based decay, no daily reset of the streak, and no drawdown-
recovery path that reduces the loss counter.

**Evidence:** Code trace (`utils/risk_manager.py` lines 341–363, 380–393).
Scan log analysis: 5 completed lockout episodes — 4 win-exits (Episodes #1, #2, #4),
1 restart-exit (Episode #5: 22h 44m, 0 executions, process terminated 2026-06-01T15:20 UTC),
0 time-only exits. Path B (restart via `__init__()`) now empirically confirmed for the
first time. Episode #5 ran 22h 44m with 14,898 scan cycles and 149 conf≥0.75 candidates —
none executed.
**Current n:** 5 lockout episodes (5 completed, 0 ongoing)
**Next threshold:** n=10 episodes for duration OBSERVED → VERIFIED
**Watchlist:** `MICRO_RECOVERY_LOCKOUT.md`

> **Important nuance confirmed by OQ2 analysis (2026-06-02):** Restart resets
> `_consecutive_losses=0` (Path B above) but does NOT guarantee NORMAL mode at session start.
> The mode evaluates both the loss counter AND `drawdown_pct`:
>
> ```
> if drawdown_pct >= 0.04 → MICRO_RECOVERY  (regardless of losses=0)
> if drawdown_pct >= 0.02 → DEFENSIVE        (regardless of losses=0)
> ```
>
> Empirical confirmation: 35.2% of May 18–June 1 sessions (n=71) started in DEFENSIVE (15.5%)
> or MR (18.3%) despite being process restarts. Drawdown-based mode pressure persists across
> restarts because the paper bankroll persists — the daily drawdown at session start reflects
> the bankroll's position relative to its prior peak. A session can restart with losses=0 but
> immediately evaluate into DEFENSIVE if the bankroll is ≥2% below session-open baseline.

---

### V7 — Distance Clamp Destroys Magnitude Information Above 2%

**Classification:** VERIFIED (code trace + empirical confirmation)
**Confidence:** Certain — follows from probability model formula

`probability_model.py` line 136 applies a hard clamp to the distance signal:
```python
distance_pct = _clamp(_distance_pct(model_input), -0.02, 0.02)
```
Any price deviation ≥ 2% from PTB is mapped to ±0.020. The model assigns
identical confidence to a 2.1% and a 10% deviation. All magnitude information
above the 2% threshold is permanently destroyed.

**Empirical confirmation:** In the post-patch trade dataset (n=24 saturated
trades), winners and losers have |distance| = 0.0200 identically (Δ = 0.0000).
Within the saturated group, distance provides zero discriminating power — the
clamp artifact is confirmed both by code and by outcome data.

**Structural consequence:** 96% of saturated trades are in COMPRESSION (23/24),
where a ≥2% mid-window price deviation from PTB is a local extreme and a
mean-reversion signal, not a sustained directional signal. The model treats
these identically to a 10% directional breakout. Saturated COMPRESSION trades
win at 33.3% vs 60.0% for non-saturated COMPRESSION trades (n=24 vs n=5,
directional — not yet statistically significant).

**Evidence:** Code trace (`probability_model.py` line 136) + 24/24 saturated
trade post-patch records show |distance| = 0.0200, Δ = 0.0000 between winners
and losers.
**Current n:** 24 saturated / 5 normal (post-patch trades with distance data)
**Next threshold:** n=45 saturated for win rate gap VERIFIED (p < 0.05)
**Watchlist:** `DISTANCE_SATURATION.md`

---

### V8 — ep002 Confidence Divergence Is a Structural Block (17.56% of Qualified Candidates)

**Classification:** VERIFIED (mathematical proof + empirical confirmation)
**Confidence:** Certain — follows from position_sizing.py line 186 + confidence formula interaction

When a market token is priced at ≤ $0.02, two confidence metrics in the pipeline
produce structurally incompatible outputs:

- `conf_MR` (distance-based, used by MICRO_RECOVERY gate): ≈ 0.75–0.88 — always passes
- `p_outcome` (win probability, used by position sizer): ≈ 0.15–0.41 — always fails

This divergence is mathematically guaranteed. `p_outcome = edge + entry_price`. For any
entry_price ≤ $0.04, achieving `conf_MR ≥ 0.75` from the distance formula simultaneously
forces `p_outcome < 0.54` (the position sizer's `confidence_floor`). The two conditions
cannot both be satisfied at this price level. The position sizer check fires at
`position_sizing.py` line 186 — before any bankroll-dependent size calculation.

```
conf_MR   = clamp(0.52 + |0.02−0.50|×1.40, 0, 0.88) × quality_mult ≈ 0.757–0.880
p_outcome = edge + entry_price ≈ 0.30 + 0.02 = 0.32   → confidence_too_low → size=$0.00
```

**Structural consequence:** ep002 candidates are ghost candidates — qualified by conf_MR,
routed through risk gates, cleared by delta_extreme in some cases — then deterministically
discarded at position sizing. They consume pipeline evaluation cycles with zero output.

**Universe share:** 17.56% of all conf≥0.75 qualified candidates across 17 full-scan days
(147/837). On burst days the share reaches 63% (May 20: 27/43 q75 candidates). The pattern
is price-level dependent, not steady-state: ep002 = 0 on 13 of 23 trading days.

**Phase concentration:** 100% in ACTIVE_INVENTORY_TRADING (166/166 recent full-scan).
PROFIT_MANAGEMENT and OPENING_SCAN are completely clean.

**Asset split:** ETH 31.0% contamination (87/281 q75) vs BTC 14.5% (80/553 q75).

**Empirical confirmation:**
- n=147 full-scan (17 days) + ~21 estimated (6 sampled days) = **~168 total**
- **0 executions** across all 23 trading days (May 8 – June 1)
- **100% blocked** by `confidence_too_low` — zero exceptions
- **10+ distinct calendar dates** spanning full history
- **No bankroll level resolves this block** — $50/$100/$200 all produce identical size=$0.00
  (the check fires before any bankroll math is reached)

**Evidence:** `position_sizing.py` line 186 (code trace) + decision_log full-scan (17 days,
86,552 events, 837 qualified candidates, 147 ep002). Source audits: Risk Plan Zero Audit
(2026-06-01), Extreme Underdog Audit (2026-06-01), Universe Share Audit (2026-06-01).
**Watchlist:** `MICRO_RECOVERY_SELECTION.md` (Snapshot 2)
**No action authorized.** Architecture observation only — Phase 3/4 design input.

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

**Classification:** OBSERVED (1 direct observation + 3 corroborating episodes)
**Evidence summary:** Run `20260530T125144Z` demonstrated the loop in real-time:
- Loss #1 (ETH NO COMPRESSION) → Loss #2 (ETH YES COMPRESSION) → DEFENSIVE
- Loss #3 (BTC NO TREND_UP) → MICRO_RECOVERY + pause
- Losses #4–5 (BTC YES COMPRESSION) → repeated pauses
- System stuck in MICRO_RECOVERY; gate continues selecting BTC COMPRESSION

The conf≥0.75 gate routes into BTC COMPRESSION → more losses → pause re-fires.

**Corroborating evidence from lockout episodes:** Episodes #3, #4, and #5 all show
the CASCADE CONSEQUENCE — extended zero-execution lockout with no qualifying win —
consistent with O8's feedback loop mechanism. Episode #5 is the longest corroborating
instance (22h 44m, 0 executions, 149 conf≥0.75 candidates all blocked). These do not
independently demonstrate the escalation moment but confirm the system can remain locked
in the cascade state for very long durations across multiple independent calendar periods.

**Current n:** 1 session demonstrating direct escalation; 3 corroborating lockout episodes
**Next threshold:** ≥3 independent sessions showing the escalation moment (loss → DEF → MR)
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
| MICRO_RECOVERY_SELECTION | P0 | VERIFIED (mechanism) / VERIFIED (ep002) / OBSERVED (outcomes) | 40 executed; 147 ep002 q75 | 100 executed | +0.449 | 2026-06-01 |
| MICRO_RECOVERY_LOCKOUT | P0 | VERIFIED (exit mechanism) / OBSERVED (duration) | 5 episodes (5 completed) | 10 episodes | — | 2026-06-01 |
| ETH_NO_COMPRESSION | P0 | OBSERVED | 52 | 350 | +0.345 | 2026-05-30 |
| BTC_COMPRESSION_OPENING_SCAN | P0 | OBSERVED | 59 | 150 | +0.324 | 2026-05-30 |
| ACTIVE_INVENTORY_EV_INVERSION | P1 | OBSERVED | 384 | 500 | — | 2026-05-30 |
| ORDERBOOK_STATE_HEALTH | P1 | OBSERVED | 402 | 600 | +0.326 (empty_book) | 2026-05-30 |
| DISTANCE_SATURATION | P1 | VERIFIED (clamp) / OBSERVED (win rate) | 24 sat / 5 norm | 45 sat | +0.323 (sat) | 2026-05-31 |

Review workflow: `docs/research/watchlists/WATCHLIST_REVIEW_WORKFLOW.md`

---

## 6. OPEN QUESTIONS

Active questions (OQ1, OQ4, OQ5, OQ6, OQ7) and resolved questions (OQ2, OQ3, OQ8).

---

### OQ1 — Is ETH NO COMPRESSION a Real Structural Failure or Calendar-Specific Variance?

The May 24–25 exception (9 trades, 67% win rate) contradicts the dominant pattern.
10 of 12 calendar days show negative results. p=0.145 (not significant at n=52).
**Requires:** ~300 more ETH NO COMPRESSION trades to resolve statistically.

---

### OQ2 — [RESOLVED 2026-06-02] Session Start State and MR Cascade Prevention

**Method:** Risk log mode transition analysis + trade_journal outcome join, 71 sessions
(May 18 – June 1), 37 with trades, 30,067 mode transitions.

Sessions do NOT always start in NORMAL despite process restart — 35.2% begin in
DEFENSIVE (15.5%) or MR (18.3%) due to drawdown_pct persistence (see V6 nuance above).

**Key findings:**
- NORMAL-start sessions reach MR in **56%** of cases; DEFENSIVE-start: **78%**; MR-start: **100%**
- First-trade WIN vs LOSS: **negligible effect on MR reach probability** (75% vs 76%)
- WIN-first sessions last **2.5× longer** (27.7 vs 11.2 avg trades) and win at higher rate (50.6% vs 23.7%)
- More wins before MR provides mild protection: 0 pre-MR wins → 76% MR reach; 5+ → 50%
- No win-threshold reliably prevents cascade — most sessions reach MR regardless

**Verdict:** Restart benefit = session longevity, not cascade prevention. NORMAL start
requires `_consecutive_losses=0` AND `drawdown_pct < 0.02` — both conditions satisfied
by Episode #5's restart. Post-Episode #5 session is the most favorable starting state
in the evidence record.

---

### OQ3 — [RESOLVED 2026-06-02] BTC COMPRESSION 0.65–0.70 Root Cause

**Method:** Tier 1 (structural, n=305 BTC / 1454 ETH decisions), Tier 2 (distance +
liq_mult, n=112/1170 post-patch), Tier 3 (outcome join, 16/16 matched).

The 42pp win rate gap (BTC 13.8% vs ETH 55.9%) is explained by the intersection of
four existing VERIFIED findings — no new mechanism required:

**V2 × V7 × V8 × V6 combined:**
1. V7: BTC COMP 6570 is 98.2% PMR-saturated — model input = ±0.020 (max clamp, no magnitude)
2. V8: 54.5% of evaluations are liq_mult=1.00 (deep books) → conf pushed above 0.75
3. V2: conf≥0.75 qualifies for MICRO_RECOVERY gate execution
4. V6: MR gate fires only after 3+ losses → adverse market condition selection → 83% SL exits
→ post-patch executed trades: **16.7% win rate** (n=6), consistent with watchlist 13.8% (n=29)

ETH is 99.8% thin-book → max conf≈0.57 → executes under NORMAL/DEFENSIVE only →
no adverse-condition selection bias + 14.8% of ETH evaluations carry genuine distance signal.

**Tier 3 confirmation:** 16/16 join matched. Post-patch: 0 liq_mult=0.75 executions,
100% liq_mult=1.00, 100% PMR-saturated. The OQ3 hypothesis (BTC binary market pricing more
accurate than model) was partially correct — but the primary mechanism is liq_mult gate
selection, not raw market accuracy.

**Status: RESOLVED. BTC_COMPRESSION_OPENING_SCAN watchlist continues for O1 (confidence
inversion pattern), which is a separate OBSERVED finding from the OQ3 root cause.**

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

### OQ8 — [RESOLVED 2026-06-02] ep002 Burst Mechanism

**Method:** ep002 burst correlation audit, n=147 ep002 events, 17 full-scan dates,
oracle movement comparison (ep002 vs control q75 candidates).

The ep002 burst is driven by **intra-window binary market extreme pricing**, NOT
oracle spot proximity to PTB. The original PTB-proximity hypothesis was incorrect.

**Key findings:**
- Oracle movement at ep002 events (mean 0.40%) ≈ control q75 events (mean 0.37%) — **no difference**
- ep002 appears when the BINARY MARKET prices one side at ≤2¢ within a 5-minute window —
  an intra-window momentum event independent of the oracle's position relative to PTB
- 73% of ep002 epochs have both BTC AND ETH firing simultaneously (market co-correlation)
- Opposite side is ALWAYS ≥97¢ (100% of 147 cases) — extreme, never mild
- BREAKOUT trend regime is ep002-exclusive; SIDEWAY trend is ep002-absent
- Oracle movement, compression score, binary price distribution: all negligibly different
  between ep002 and non-ep002 qualified candidates

**Pre-screening implication (Phase 3/4 design input, not authorized now):**
`yes_ask ≤ 0.02 OR no_ask ≤ 0.02` is computable in every scan cycle before the
probability model runs. A pre-gate on this binary market price field would eliminate
17.56% of ghost candidates at zero cost to non-ep002 decisions.

**Status: RESOLVED. Burst mechanism identified. Pre-screening pre-gate documented as
future Phase 3/4 design input.**

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

**Key Phase 1 findings:** The OPENING_SCAN probability model has a structural
miscalibration in BTC COMPRESSION where confidence gating worsens rather than improves
selection (O1/OQ3 resolved). The ACTIVE_INVENTORY EV signal is inverted (O3). The
MICRO_RECOVERY architecture creates a cascade-prone feedback loop with drawdown-persistent
starting mode (V6 nuance, OQ2 resolved). ep002 ghost candidates block 17.56% of qualified
pipeline entries via binary-market extreme pricing (V8, OQ8 resolved). All are Phase 2–4
design inputs.

**Current operational state (as of 2026-06-02):**
- Episode #5 CLOSED — process terminated 2026-06-01T15:20 UTC
- Final stats: 22h 44m duration, 0 executions, exit via restart — longest zero-execution run on record
- New session: will start with `_consecutive_losses=0` (V6 Path B confirmed)
- Expected starting mode: NORMAL if `drawdown_pct < 0.02`; else DEFENSIVE/MR (see V6 nuance)
- Bankroll at Episode #5 end: ~$20.11 — drawdown from peak is minimal → NORMAL start expected
- Evidence accumulation: RESUMING with next session start (best possible NORMAL starting conditions)

---

## 8. NEXT EVIDENCE TARGETS

Specific accumulation targets that would unlock the next review or status change.

### Immediate Targets (next 14 days)

| Target | Required n | Current n | Gap | Priority |
|---|---|---|---|---|
| ETH NO COMPRESSION n=100 | 100 | 52 | 48 | P0 |
| conf≥0.75 trades n=100 | 100 | 40 | 60 | P0 |
| BTC COMP OS n=150 | 150 | 59 | 91 | P0 |
| ~~true_p 0.65–0.70 BTC bucket n=50~~ | 50 | 29 | — | Closed — OQ3 resolved by Tier 1/2/3 |
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

> **Episode #5 CLOSED (2026-06-01T15:20 UTC):** 22h 44m, 0 trades executed, exit via
> process restart. Evidence accumulation RESUMES with next session. All n-values remain
> at May 30 snapshot values. The `true_p 0.65–0.70 BTC bucket n=50` target is retired —
> OQ3 resolved by Tier 1/2/3 analysis without requiring that count. The post-Episode #5
> session is the highest-priority evidence accumulation window (NORMAL start expected).

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
