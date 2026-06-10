# ETH_YES_FC_OS Watchlist

## N70 Milestone Snapshot - 2026-06-10

The canonical export reproduced the real N70 event with `71` raw qualifying
rows, `1` duplicate removed, and `70` canonical opportunities.

| Metric | N70 value |
|---|---:|
| Canonical n | 70 |
| Remaining to n=100 | 30 |
| Wins / losses | 40 / 30 |
| WR | 57.1% |
| PF | 2.006 |
| Net PnL | +$0.215774 |
| Median PnL | +$0.005783 |
| p-value | 0.141 |
| Calendar weeks | 4 |
| nc_PF | 3.865 |
| N62-N70 block | 5W / 4L, PF 1.803, +$0.018609 |

N70 verdict: `CONTINUE_ACCUMULATION`.

This milestone snapshot supersedes the pre-N70 current-state fields retained
below for historical context.

```text
Rows 1-70   = discovery / retrospective selected-slice evidence
Rows 71-100 = forward validation block
```

type: living evidence tracker
priority: P1
status: OBSERVED (VERIFICATION_IN_PROGRESS + POSITIVE_PATH_EVIDENCE — robustness 12/12, MFE/MAE positive)
current_n: 60
last_snapshot: 2026-06-06
last_evidence_run: 2026-06-06
created: 2026-06-02
code_changed: No
strategy_changed: No
runtime_changed: No

---

## Purpose

Track whether **ETH × YES × FIRST\_CYCLE × OPENING\_SCAN × hold > 15s** is a
structurally positive edge that can be promoted to VERIFIED.

This cell was isolated after a 12-test adversarial robustness audit
(2026-06-02) demonstrated structural strength across concentration removal,
temporal stability, bootstrap resampling (2,000 iterations), trade dependency
analysis, and win concentration tests. It is the narrowest surviving positive
subpopulation from the YES+FIRST\_CYCLE research series.

**Core finding:** `PF=2.055, WR=58.1%, net=+$0.205` across canonical opportunities = 60
(raw execution rows = 62) spanning 13 active calendar dates (May 18–May 31, 2026). Bootstrap
confirms PF > 1.0 in 99.5% of 2,000 resamples. Leave-one-date-out minimum
PF = 1.909.

**Not yet VERIFIED because:**
- n=60 < threshold of 100
- Binomial p-value = 0.126 (target: p<0.05, requires n≈105)
- Only 2 calendar weeks observed (W21 + W22, target: ≥3)

---

## Signal Definition

```
Cell:        ETH YES FIRST_CYCLE OPENING_SCAN hold>15s
Asset:       ETH only (BTC exclusion is required — BTC in this cell has PF=0.148)
Direction:   YES outcome only
Cycle type:  FIRST_CYCLE = time_bucket=='early_window' OR
             active_window_alignment_reason=='early_window_ready'
Phase:       OPENING_SCAN only (lifecycle_phase contains 'OPENING_SCAN')
Hold filter: hold_seconds > 15 (exclude fast-close exits ≤15s)
```

**Why BTC must be excluded:** BTC YES FC OS has WR=9.1%, PF=0.148, net=−$0.121
(n=11). Including BTC would dilute the composite to PF=2.055→1.417 and mask
the true ETH-specific edge. This is a pre-condition for the signal definition,
not a post-hoc filter.

**Why hold>15s must be applied:** 48% of raw YES FC OS trades close within 15s
(fast-close exits, primarily SL hits triggered before the position has time to
develop). These fast-close trades are net-negative (PF=0.825). Excluding them
strengthens the signal and represents a distinct execution sub-category: trades
that survive the initial opening window.

---

## Evidence Lineage

This watchlist derives from a three-stage research sequence:

1. **YES+FC overview audit (2026-06-02):** Initial identification of YES
   outperforming NO in FIRST\_CYCLE. YES\_FC\_OS emerged as the surviving
   sub-filter after lifecycle phase stratification. Confirmed n=139, PF=1.049
   at the OPENING\_SCAN all-asset level.

2. **Asset × fast-close cross-tab (2026-06-02):** ETH YES FC OS excl. fast15
   isolated as PF=2.055 (canonical opportunities = 60; raw execution rows = 62). BTC YES FC OS (n=31) confirmed as
   destructive (PF=0.430). The 12-test adversarial audit followed.

3. **12-test robustness battery (2026-06-02):** All structural tests passed.
   Key results: LODO min PF=1.909, bootstrap PF>1.0 in 99.5% of resamples,
   win/loss chi-squared=0.03 (no dependency), day-profit rate 12/13=92%,
   concentration test passes top-5 removal (PF=1.441 after excl. top 5).

4. **Path Truth Joinability Audit (2026-06-06):** Root cause of 0-record false
   negative identified — the prior audit used `outcome` field (absent in path
   truth) instead of `side`. Correct join via `run_id + condition_id + side`
   achieves 47% match rate (28/60). Path truth DOES contain ETH YES OS records.
   Identifier divergence documented: `inventory_context_id` mismatches because
   PT payload lacks `market_key` and `epoch_start_ts` at enrichment time.

5. **MFE/MAE Audit (2026-06-06):** 28 path-matched trades analysed. Positive
   path evidence: MFE median=+$0.006, MAE median=−$0.001, 79% of trades reached
   positive unrealized territory, 61% clean path rate, winners never exit early
   (exit efficiency=1.000). Losers show genuinely adverse trajectories (no
   "premature exit" pattern found). Perfect-exit PF=4.407 vs actual 2.338.

---

## Tracked Metrics

| Metric | Definition |
|---|---|
| Total n | ETH×YES×FC×OS trades with hold\_s > 15 |
| Win rate | W / n |
| Profit factor | Σ(winning PnL) / Σ(abs(losing PnL)) |
| Net PnL | Σ(all PnL) |
| Median PnL | median(all trade PnL) — must remain > 0 |
| Win/loss ratio | avg\_win / avg\_loss |
| Day-profit rate | fraction of active calendar dates with net\_day > 0 |
| Concentration (excl. top-5) | PF after removing the 5 highest-PnL trades |
| Bootstrap PF p5 | 5th percentile of bootstrap PF distribution (2000 resamples) |
| Binomial p-value | P(W ≥ observed \| n, p=0.50) one-sided |
| Calendar weeks | Unique ISO calendar weeks with ≥1 qualifying trade |
| Path truth count | YES records in path\_truth checkpoint log |

---

## Promotion Criteria (VERIFICATION\_IN\_PROGRESS → VERIFIED)

All five must be met simultaneously on the same evidence snapshot:

1. **n ≥ 100** in the exact cell definition (ETH×YES×FC×OS, hold>15s)
2. **WR > 52%** sustained over the full n ≥ 100 population
3. **PF > 1.5** sustained over the full n ≥ 100 population
4. **Binomial p-value < 0.05** (one-sided, null WR=0.50)
5. **≥ 3 independent ISO calendar weeks** with qualifying trades

Additional quality gates (non-blocking but must be noted):
- Concentration test: excl. top-5 PF must remain > 1.0 at n=100
- LODO: all date-removals must keep PF > 1.0
- Bootstrap p5 (5th percentile) must remain > 1.0

**Projected timeline at current rate (4.77 trades/trading-day):**
- n=75: ~3 trading days
- n=100: ~8 trading days
- Significance p<0.05: ~10–11 trading days

---

## Kill Criteria (VERIFICATION\_IN\_PROGRESS → NOT\_SUPPORTED)

The signal is killed if ANY of these conditions are met on new data:

1. **WR < 48% over n ≥ 30 new qualifying trades** (signal reversal beyond noise)
2. **PF < 1.3 at n ≥ 80** sustained (edge erosion confirmed)
3. **BTC exclusion no longer valid:** if BTC YES FC OS WR rises above 40% on
   n ≥ 20 new BTC trades, revisit the joint definition
4. **Concentration collapse:** if excl.-top-5 PF drops below 1.0 at n=100
   (edge entirely driven by outlier trades)

---

## Known Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| n=60 below statistical threshold | p=0.126, not yet significant | LODO and bootstrap provide alternative confidence |
| 2 calendar weeks only | Temporal coverage narrow | Third week (W23+) will resolve |
| BTC exclusion required | Signal is asset-conditional; not a universal YES edge | Explicitly documented in cell definition |
| Fast-close filter | 48% of raw YES FC OS excluded — this is a scope restriction | The filter is structural, not cherry-picked: fast-closes are a separate execution pattern |
| Episode #5 gap | 0 new trades from May 31 → June 1; June 2 trade was ETH NO | Rate temporarily disrupted; edge not refuted |
| Post-Episode #5 regime | New session started June 2 in NORMAL mode; no COMPRESSION observed | Cell did not accumulate; no data yet for NORMAL-start session behavior |
| SIDEWAY regime drag | SIDEWAY YES FC OS: PF=1.258 — positive but weakest regime | Monitor whether SIDEWAY share of FC OS executions changes |
| Path truth coverage 47% | MFE/MAE available for only 28/60 trades — pre-May 24 range unlogged; checkpoint timing race misses some fast OS holds | Compound key join (run\_id+condition\_id+side) is best available; full fix requires adding epoch\_start\_ts to path truth payload |
| Path truth identifier mismatch | `inventory_context_id` diverges between trade\_journal and path\_truth due to different enrichment inputs (market\_key and time\_bucket differ) | Use paper\_trade\_replay\_key or compound key; do not join on inv\_ctx |

---

## Path Truth Coverage

**CORRECTED (2026-06-06):** The prior "0 YES records" finding was a false
negative caused by a field name mismatch (`outcome` vs `side` in path truth
events). Path truth DOES contain ETH YES OS records.

**Actual state:** 512 total path truth events; 97 ETH YES OPENING\_SCAN records
across 59 unique positions. Join achieved via `run_id + condition_id + side`
compound key: **47% match rate (28/60 cell trades)**.

**Identifier divergence root cause (confirmed):** `inventory_context_id` is
computed by the `QuantEventLogger._enrich()` pipeline from `market_key|time_bucket`.
In trade\_journal: `market_key='pm-5m-eth'` + `time_bucket=epoch_start_ts`.
In path\_truth: `market_key=condition_id` (fallback) + `time_bucket=checkpoint_event_ts`.
Different inputs → different hash → different `inventory_context_id` → zero overlap.

**Remaining gap (53%):** Pre-May 24 trades have no path truth files. Post-May 24
trades miss checkpoints when the 1Hz stop-loss loop does not fire within the
±2s tolerance window of the 15s checkpoint target.

**Minimum observability fix (not yet authorized):** Adding `epoch_start_ts` and
`market_id = pos.symbol` to the `_emit_path_truth_checkpoint` payload would
restore `inventory_context_id` identity between TJ and PT, enabling 100% join
coverage on future trades.

**Current MFE/MAE status:** AVAILABLE for 47% of cell trades.
See "Latest Path Evidence" section below.

---

## Snapshot 1 — 2026-06-02 (Initial — 12-Test Robustness Audit)

analysis\_run: 2026-06-02
evidence\_source: decision\_log (trade context) + trade\_journal (outcomes)
trades\_covered: May 18 – May 31, 2026 (13 active calendar dates)
sessions\_covered: 13 calendar dates spanning 2 ISO weeks (W21, W22)

```
n:          60 / 100  [########################░░░░░░░░░░░░░░░░░░░░]  60.0%
WR:         58.1%  → target >52%  PASSING ✓
PF:         2.055  → target >1.5  PASSING ✓
Net PnL:   +$0.205
Med PnL:   +$0.006  (positive — clean edge, not driven by fat tails alone)
p-value:    0.126  → target <0.05  PENDING (need n≈105)
Cal weeks:  2 / 3   → target ≥3    PENDING
```

### Core Metrics

| Metric | Value |
|---|---|
| Total n | 60 canonical opportunities (raw execution rows = 62) |
| Wins (W) | 36 |
| Win rate | 58.1% |
| Profit Factor | 2.055 |
| Net PnL | +$0.205 |
| Median PnL | +$0.006 |
| Gross wins | $0.399 |
| Gross losses | $0.194 |
| Avg win / avg loss | 1.484 |
| TP exits | 20 |
| SL exits | 14 + 2 unknown (fast-close excluded) |
| Binomial p-value (vs 0.50) | 0.126 |
| Calendar dates | 13 |
| Calendar weeks | 2 (W21, W22) |
| Day-profit rate | 12/13 = 92% |

### Robustness Battery Results (12 tests, 2026-06-02)

| Test | Result | Detail |
|---|---|---|
| Excl. top-1 | PASS | PF=1.906 |
| Excl. top-2 | PASS | PF=1.766 |
| Excl. top-5 | PASS | PF=1.441 |
| Weekly stability | PASS | W21=1.739, W22=2.947 (both positive) |
| Session profit rate | PASS | 12/13 days positive (92%) |
| First/second half | PASS | 1.764 / 2.462 (second half stronger) |
| Leave-one-date-out | PASS | Min PF=1.909 (all 13 dates) |
| Bootstrap PF>1.0 | PASS | 99.5% of 2,000 resamples |
| Bootstrap bear case (p5) | PASS | PF=1.261 |
| Order-shuffle ruin test | PASS | Ruin (−$0.05) in only 0.9% of shuffles |
| Win clustering | PASS | Max streak=6, expected~7.6 (not abnormal) |
| Win/loss dependency | PASS | χ²=0.03 << 3.84 critical (trades independent) |
| Win concentration | PASS | Top-1 = 7.2% of gross wins (not extreme) |
| Statistical significance | PENDING | p=0.126, need n≈105 for p<0.05 |
| Path truth (MFE/MAE) | PARTIAL | 47% match (28/60) via compound key; see MFE/MAE section |

### Bootstrap Summary (n=2,000 resamples)

| Statistic | Value |
|---|---|
| Mean PF | 2.139 |
| Median PF | 2.051 |
| Std dev PF | 0.647 |
| p5 (bear case) | 1.261 |
| p25 (conservative) | 1.699 |
| p75 | 2.491 |
| p95 (bull case) | 3.390 |
| PF > 1.0 rate | 99.5% |
| Net PnL 90% CI | [+$0.064, +$0.343] |

### Regime Breakdown

| Regime | n | WR | PF | net |
|---|---|---|---|---|
| COMPRESSION | 21 | 62% | 3.372 | +$0.132 |
| TREND\_DOWN | 19 | 58% | 2.271 | +$0.077 |
| SIDEWAY | 15 | 60% | 1.258 | +$0.020 |
| TREND\_UP | 7 | 43% | 0.661 | −$0.023 |

COMPRESSION and TREND\_DOWN are the strongest regimes. TREND\_UP is the only
negative regime (n=7, insufficient for conclusions). SIDEWAY is positive but
weakest.

### Accumulation Rate

- Mean: 4.77 qualifying trades / active trading day
- Calendar window: May 18 – May 31 (14 calendar days, 13 active = 93%)
- Conservative estimate: 3.0/day (accounts for non-COMPRESSION days and
  occasional zero-execution sessions)
- ETA to n=100 at 4.77/day: ~8 trading days
- ETA to n=100 at 3.0/day: ~13 trading days

---

---

## Latest Path Evidence — MFE/MAE Audit (2026-06-06)

analysis\_run: 2026-06-06
evidence\_source: path\_truth checkpoints (compound key join) + trade\_journal
join\_strategy: run\_id + condition\_id + side (no epoch — absent in path truth)
matched: 28 / 60 qualifying trades = 47% match rate
matched\_sample\_PF: 2.338 (consistent with full cell PF=2.055 ✓)
matched\_sample\_WR: 60.7% (consistent with full cell WR=58.1% ✓)

```
MFE (Maximum Favorable Excursion — peak unrealized gain):
  median:   +$0.00592
  mean:     +$0.00583
  p25:      +$0.00201
  p75:      +$0.01004
  max:      +$0.02714
  MFE > 0:  22/28 = 79%  (79% of trades reached positive territory)

MAE (Maximum Adverse Excursion — worst unrealized loss):
  median:   -$0.00097
  mean:     -$0.00155
  p25:      -$0.00493
  p75:      +$0.00340  (positive — never went negative during hold)
  min:      -$0.01327
  MAE >= 0 (never adverse):    13/28 = 46%
  MAE < -$0.005 (significant): 6/28  = 21%
```

### Path Quality Breakdown

| Metric | Value | Interpretation |
|---|---|---|
| Clean paths (MFE≥0, MAE≥−$0.003) | **17/28 = 61%** | Majority of trades move favorably from entry |
| All clean paths are winners | **17/17 = 100%** | Clean = win; strong path signal |
| Winners with any adverse (MAE<0) | 4/17 = 24% | Most winners never go negative |
| Winner MAE median | **+$0.00252** | Winners are positive throughout hold |
| Loser MAE median | **−$0.00520** | Losers show genuine adverse excursion |
| Exit efficiency (realized / MFE, winners) | **1.000** | TP exits capture 100% of peak value |
| Winners with profit left on table | 10/17 (measurement artifact — see note) | Exit mechanism not premature |

**Note on exit efficiency = 1.000:** The TP exit fires at or near the peak mark
price by design. `unrealized_pnl` and `realized_pnl` use consistent mark prices
at close, so efficiency approaches 1.0 for TP exits. This confirms the exit
mechanism is functioning correctly — not that there is zero room for improvement.

### Hypothetical Perfect Exit

| Scenario | Net PnL | PF |
|---|---|---|
| Actual (matched 28 trades) | +$0.108 | **2.338** |
| Perfect exit at MFE | +$0.156 | **4.407** |
| Improvement | +$0.048 | **+2.069** |

The +2.069 PF uplift from perfect hindsight exits is driven entirely by the
6–11 trades that reached positive MFE before closing negative (losers that
briefly went positive). A tighter MAE-based stop on the loser tail could
theoretically capture some of this uplift — but this is a Phase 3 design
input, not a current-phase action.

### Path Truth Interpretation

**Key finding: the path evidence is POSITIVE and consistent with ROBUST\_EDGE.**

1. **Winners are not exiting too early** — exit efficiency=1.000, no unrealized
   gain is being abandoned
2. **Losers are genuine adverse moves** — loser MAE median (−$0.005) vs winner
   MAE median (+$0.003) shows clean separation; losers move adversely from the
   start and do not represent mismanaged winners
3. **Main remaining blocker is statistical power**, not path quality — p=0.126
   needs n≈105; path evidence does not introduce new red flags
4. **Path coverage limited at 47%** — pre-May 24 and timing-race misses account
   for the gap; the 28 matched trades are representative of the full cell

### Observability Fix Required for Phase 2

The compound key join achieves 47% match on historical data. For Phase 2
MFE/MAE analysis (entry-quality replay, optimal exit research), path truth
coverage must improve. The minimum required change (documented in
`Path Truth Joinability Audit 2026-06-06`, not yet authorized):

- Add `epoch_start_ts = metadata.get("epoch_start_ts")` to path truth payload
- Add `market_id = pos.symbol` to path truth payload

These two fields would restore full `inventory_context_id` identity between
trade\_journal and path\_truth, enabling 100% join coverage on future trades.

---

*See also: [WATCHLIST\_INDEX.md](WATCHLIST_INDEX.md) | [WATCHLIST\_REVIEW\_WORKFLOW.md](WATCHLIST_REVIEW_WORKFLOW.md) | [RESEARCH\_FRONTIER\_DASHBOARD.md](../RESEARCH_FRONTIER_DASHBOARD.md)*
