# ETH YES FC OS — Regime Transition & Drift Audit

type: drift_audit
generated_at: 2026-06-06
cell: ETH × YES × FIRST_CYCLE × OPENING_SCAN × hold > 15s
source: runtime/research_exports/completed_trades_v1_2.csv
n: 61 (canonical filter applied; see §0 for reconciliation note)
rolling_window: 20
code_changed: No
strategy_changed: No
runtime_changed: No

> READ ONLY. No section authorizes a runtime change, strategy change, risk
> change, execution change, filter, or promotion decision.

---

## §0. Data Note

The CSV filter returns n=61 through 2026-05-31. The evidence_velocity_dashboard
records n=61 including a 2026-06-06 W23 SIDEWAY TP (+$0.01161) not yet reflected
in the CSV export. The verification_tracker records n=60 canonical (62 raw) from
a prior deduplication pass. Regime counts from the CSV: COMPRESSION=21,
TREND_DOWN=19, SIDEWAY=14, TREND_UP=7. The SIDEWAY count (14) differs by 1 from
the verification_tracker (15). The TREND_DOWN count (19) matches ETH_YES_FC_OS.md
snapshot 1 and resolves the 18-vs-19 reconciliation. Full-cell stats from CSV:
WR=57.4%, PF=2.022, net=+$0.196. Minor variance from the tracker's 58.1%/2.055
is attributable to the deduplication delta.

All findings below use the CSV as the authoritative sequence source.

---

## 1. Timeline Chart: Regime × Outcome Sequence

Each cell = one canonical trade. Opportunity index increases left-to-right, top-to-bottom.

```
Regime key: C=COMPRESSION  D=TREND_DOWN  S=SIDEWAY  T=TREND_UP
Outcome key: + = WIN  . = LOSS

Idx  1   2   3   4   5   6   7   8   9  10  11  12  13  14  15
     S+  D+  D.  T.  D+  C+  C+  C.  C+  T+  T+  S.  D.  C.  C+

Idx 16  17  18  19  20  21  22  23  24  25  26  27  28  29  30
     C.  D+  D+  D.  D.  D+  T.  C.  S+  S.  C+  S+  S+  S+  S.

Idx 31  32  33  34  35  36  37  38  39  40  41  42  43  44  45
     D.  C.  C+  C+  D.  C.  C+  T.  S.  C+  T+  C+  S+  S.  T.

Idx 46  47  48  49  50  51  52  53  54  55  56  57  58  59  60  61
     D+  D.  D+  S.  D.  D+  D+  S+  D+  S+  D+  C.  C+  C+  C.  C+
```

### Regime by calendar date

```
Date        Trades   Sequence (regime/outcome)
2026-05-18   1       S+
2026-05-19   4       D+ D. T. D+
2026-05-20   7       C+ C+ C. C+ T+ T+ S.
2026-05-21   9       D. C. C+ C. D+ D+ D. D. D+
2026-05-22   8       T. C. S+ S. C+ S+ S+ S.
2026-05-23   2       D. C.
2026-05-24   7       C+ C+ D. C. C+ T. S.
2026-05-25   6       C+ T+ C+ S+ S. T.
2026-05-26   3       D+ D. D+
(May 27 —   0       no trades)
2026-05-28   5       S. D. D+ D+ S+
2026-05-29   3       D+ S+ D+
2026-05-30   3       C. C+ C+
2026-05-31   2       C. C+
```

### Regime run table (34 consecutive same-regime runs)

| Run | Regime      | Index range | n | W/L  | PnL      |
|-----|-------------|-------------|---|------|----------|
| 1   | SIDEWAY     | #1          | 1 | 1W/0 | +$0.007  |
| 2   | TREND_DOWN  | #2–#3       | 2 | 1W/1L| +$0.004  |
| 3   | TREND_UP    | #4          | 1 | 0W/1L| −$0.011  |
| 4   | TREND_DOWN  | #5          | 1 | 1W/0 | +$0.009  |
| 5   | COMPRESSION | **#6–#9**   |**4**| 3W/1L| **+$0.044**|
| 6   | TREND_UP    | #10–#11     | 2 | 2W/0 | +$0.015  |
| 7   | SIDEWAY     | #12         | 1 | 0W/1L| −$0.019  |
| 8   | TREND_DOWN  | #13         | 1 | 0W/1L| −$0.004  |
| 9   | COMPRESSION | #14–#16     | 3 | 1W/2L| +$0.017  |
| 10  | TREND_DOWN  | #17–#21     | 5 | 3W/2L| +$0.027  |
| 11  | TREND_UP    | #22         | 1 | 0W/1L| −$0.006  |
| 12  | COMPRESSION | #23         | 1 | 0W/1L| −$0.008  |
| 13  | SIDEWAY     | #24–#25     | 2 | 1W/1L| +$0.002  |
| 14  | COMPRESSION | #26         | 1 | 1W/0 | +$0.008  |
| 15  | SIDEWAY     | #27–#30     | 4 | 3W/1L| +$0.014  |
| 16  | TREND_DOWN  | #31         | 1 | 0W/1L| −$0.009  |
| 17  | COMPRESSION | #32–#34     | 3 | 2W/1L| +$0.026  |
| 18  | TREND_DOWN  | #35         | 1 | 0W/1L| −$0.008  |
| 19  | COMPRESSION | #36–#37     | 2 | 1W/1L| +$0.011  |
| 20  | TREND_UP    | #38         | 1 | 0W/1L| −$0.004  |
| 21  | SIDEWAY     | #39         | 1 | 0W/1L| −$0.012  |
| 22  | COMPRESSION | #40         | 1 | 1W/0 | +$0.012  |
| 23  | TREND_UP    | #41         | 1 | 1W/0 | +$0.005  |
| 24  | COMPRESSION | #42         | 1 | 1W/0 | +$0.009  |
| 25  | SIDEWAY     | #43–#44     | 2 | 1W/1L| +$0.003  |
| 26  | TREND_UP    | #45         | 1 | 0W/1L| −$0.009  |
| 27  | TREND_DOWN  | **#46–#48** |**3**| 2W/1L| **+$0.033**|
| 28  | SIDEWAY     | #49         | 1 | 0W/1L| −$0.004  |
| 29  | TREND_DOWN  | #50–#52     | 3 | 2W/1L| +$0.005  |
| 30  | SIDEWAY     | #53         | 1 | 1W/0 | +$0.008  |
| 31  | TREND_DOWN  | #54         | 1 | 1W/0 | +$0.008  |
| 32  | SIDEWAY     | #55         | 1 | 1W/0 | +$0.009  |
| 33  | TREND_DOWN  | #56         | 1 | 1W/0 | +$0.006  |
| 34  | COMPRESSION | **#57–#61** |**5**| 3W/2L| **+$0.011**|

34 runs across 61 trades = average run length 1.8. The sequence is heavily
interleaved. No single regime dominates for more than 5 consecutive trades.

---

## 2. Rolling Profit Factor (window = 20)

Computed from trade #20 onward (first full window).

```
WR scale: 0% ──── 50% ──── 100%

#20  50.0%  PF=2.020  ████████████████████░░░░░░░░░░░░░░░░░░░░
#25  50.0%  PF=1.934  ███████████████████░░░░░░░░░░░░░░░░░░░░░
#30  50.0%  PF=1.513  ███████████████░░░░░░░░░░░░░░░░░░░░░░░░░
#31  45.0%  PF=1.257  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ← TROUGH
#35  50.0%  PF=1.543  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░
#39  45.0%  PF=1.347  █████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░  ← 2nd low
#45  55.0%  PF=1.661  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░
#52  55.0%  PF=2.124  █████████████████████░░░░░░░░░░░░░░░░░░░
#56  65.0%  PF=2.642  ██████████████████████████░░░░░░░░░░░░░░
#59  70.0%  PF=2.832  ████████████████████████████░░░░░░░░░░░░  ← PEAK
#61  65.0%  PF=2.521  █████████████████████████░░░░░░░░░░░░░░░
```

Full rolling PF series:

```
Idx  PF       Bar (each # ≈ 0.1 PF)
 20  2.020  ####################
 21  2.228  ######################
 22  1.931  ###################
 23  1.845  ##################
 24  2.278  ####################
 25  1.934  ###################
 26  1.820  ##################
 27  1.754  #################
 28  1.995  ####################
 29  1.788  ###################
 30  1.513  ###############
 31  1.257  ############ ← PF trough
 32  1.467  ##############
 33  1.973  ####################
 34  2.226  ######################
 35  1.543  ###############
 36  1.589  ################
 37  1.740  #################
 38  1.487  ##############
 39  1.347  #############
 40  1.613  ################
 41  1.405  ##############
 42  1.657  ################
 43  2.007  ####################
 44  1.724  #################
 45  1.661  ################
 46  1.783  #################
 47  1.562  ###############
 48  1.780  #################
 49  1.582  ###############
 50  1.497  ##############
 51  1.775  #################
 52  2.124  #####################
 53  1.833  ##################
 54  1.859  ##################
 55  2.292  #######################
 56  2.642  ##########################
 57  1.866  ##################
 58  2.105  #####################
 59  2.832  ########################### ← PF peak
 60  2.364  #######################
 61  2.521  #########################
```

| Stat | Value | At index |
|---|---|---|
| Minimum PF | **1.257** | #31 (2026-05-23) |
| Maximum PF | **2.832** | #59 (2026-05-30) |
| Final PF | **2.521** | #61 (2026-05-31) |
| Entries below 1.5 | 7 | #4, #31, #32, #38–#39, #41, #50 |
| Entries below 1.3 | 1 | #31 only |

---

## 3. Rolling Win Rate (window = 20)

```
WR scale: 40% ── 50% ── 60% ── 70%
                  ↑
                 52% promotion threshold

Idx  WR
 20  55.0%  ##########▒▒▒▒▒▒▒▒▒▒
 25  50.0%  #########▒▒▒▒▒▒▒▒▒▒▒
 30  50.0%  #########▒▒▒▒▒▒▒▒▒▒▒
 31  45.0%  ########▒▒▒▒▒▒▒▒▒▒▒▒  ← WR trough (below promotion threshold)
 35  50.0%  #########▒▒▒▒▒▒▒▒▒▒▒
 40  50.0%  #########▒▒▒▒▒▒▒▒▒▒▒
 45  55.0%  ##########▒▒▒▒▒▒▒▒▒▒
 52  55.0%  ##########▒▒▒▒▒▒▒▒▒▒
 56  65.0%  ############▒▒▒▒▒▒▒▒
 59  70.0%  #############▒▒▒▒▒▒▒  ← WR peak
 61  65.0%  ############▒▒▒▒▒▒▒▒
```

| Stat | Value | At index |
|---|---|---|
| Minimum WR | **45.0%** | #31, #32 (2026-05-23); #38–#39 (2026-05-24); #49–#50 (2026-05-28) |
| Maximum WR | **70.0%** | #59 (2026-05-30) |
| Final WR | **65.0%** | #61 (2026-05-31) |
| Entries < 52% (full window only) | 15 | #22–#51 (clustered May 22–28) |

Periods when rolling WR was below 52%: **#22 through #51** (with some gaps).
The below-52% cluster spans approximately 30 consecutive index positions,
representing the entire May 22–28 trading window.

---

## 4. Rolling Non-COMPRESSION Profit Factor (window = 20)

This metric answers: "What is the PF of the non-COMPRESSION trades in the
most recent 20-trade window?" It is the leading indicator for how the cell
will perform during the current COMPRESSION-absent period.

```
1.0 threshold (break-even)
         ↓
Idx  nc_PF
 20  1.154  ████████████
 24  1.792  ##################
 30  1.391  ##############
 31  1.069  ███████████  ← approaching 1.0
 38  0.957  █████████░   ← BELOW 1.0 (start of negative nc_PF zone)
 39  0.836  ████████░
 40  0.923  █████████░
 41  0.636  ██████░      ← nc_PF floor
 42  0.711  ███████░
 43  0.866  █████████░
 44  0.623  ██████░
 45  0.596  ██████░      ← absolute minimum
 46  0.893  █████████░
 47  0.701  ███████░
 48  0.962  █████████░
 49  0.780  ████████░
 50  0.731  ███████░
 51  0.943  █████████░
 52  1.113  ████████████ ← recovery above 1.0
 53  1.254  █████████████
 54  1.383  ██████████████
 55  1.781  ##################
 56  1.897  ###################
 57  1.897  ###################  (COMP trades enter window, nc recalculated)
 58  2.080  █████████████████████
 59  2.811  ████████████████████████████ ← nc_PF peak
 60  2.811  ████████████████████████████
 61  2.661  ███████████████████████████
```

| Stat | Value | At index |
|---|---|---|
| Minimum nc_PF | **0.596** | #45 (2026-05-25) |
| Maximum nc_PF | **2.811** | #59–#60 (2026-05-30) |
| Final nc_PF | **2.661** | #61 (2026-05-31) |
| Entries below 1.0 | **14** | #38–#51 (2026-05-24 to 2026-05-28) |
| Recovery above 1.0 | at #52 | 2026-05-28 |

**nc_PF negative zone:** The non-COMPRESSION edge was in negative territory
(PF < 1.0) for indices #38 through #51 — a 14-trade consecutive window
spanning May 24–28. During this period, the non-COMPRESSION sub-population
in the rolling window was unprofitable on a PF basis. The nc_PF recovery
above 1.0 at #52 was driven by the May 28–29 TREND_DOWN run (4 consecutive
wins: #51–#56) which flushed the worst non-COMPRESSION losses from the window.

---

## 5. Rolling COMPRESSION Share (window = 20)

```
50%  ─────────────────────────────────────
40%  ────────────────────────────────────
                                           Historical mean ~43%
30%  ──────────────────────────
20%  ─────────────
10%  ────

Idx  COMP%   Bar
 20   35%   ###################################
 24   40%   ########################################
 30   25%   #########################
 31   25%   #########################
 37   35%   ###################################
 40   40%   ########################################
 42   45%   ############################################ ← peak
 46   35%   ###################################
 52   30%   ##############################
 54   20%   ####################
 56   15%   ###############          ← pre-collapse low (W22 late phase)
 58   20%   ####################
 59   25%   #########################
 61   30%   ##############################           ← final
```

| Stat | Value | At index |
|---|---|---|
| Minimum COMP share | **15.0%** | #56 (2026-05-29) |
| Maximum COMP share | **45.0%** | #42 (2026-05-25) |
| Final COMP share | **30.0%** | #61 (2026-05-31) |

The 15% rolling low at #56 (May 29) is the pre-collapse minimum. This
represents the within-W22 compression trough — even before the June 1
market-structure collapse, the rolling COMPRESSION share was falling as
TREND_DOWN trades accumulated in the late-May window.

---

## 6. Drift Detection

### 6a. Regime Drift

**CONFIRMED.** The regime composition changed materially between W21 and W22.

| Regime | W21 (n=39) | W22 (n=22) | Shift |
|---|---|---|---|
| COMPRESSION | 14 / 36% | 7 / 32% | −4 pp |
| TREND_DOWN | 11 / 28% | 8 / 36% | +8 pp |
| SIDEWAY | 9 / 23% | 5 / 23% | flat |
| TREND_UP | 5 / 13% | 2 / 9% | −4 pp |
| WR | **51.3%** | **68.2%** | +17 pp |
| PF | **1.720** | **2.861** | +1.141 |

**W21 to W22 regime transition:** TREND_DOWN replaced COMPRESSION as the
plurality regime. TREND_UP declined. SIDEWAY share was stable. The shift
is not a regime collapse — both regimes remain active — but it changed
the character of the cell's edge.

**Intra-sequence regime fragmentation:** 34 distinct regime runs across 61
trades. Average run length = 1.8 trades. The maximum consecutive same-regime
run is 5 (COMPRESSION: #6–#9 and #57–#61). This is structural: the market
cycles through regimes within a single trading session.

---

### 6b. Edge Drift

**CONFIRMED — midgame trough, complete late recovery.**

Phase segmentation:

| Phase | Idx | WR | PF | Regime mix |
|---|---|---|---|---|
| Early | #1–#20 | **55.0%** | **2.020** | COMP:7 TD:8 SW:2 TU:3 |
| Mid | #21–#40 | **50.0%** | **1.613** | COMP:8 SW:7 TD:3 TU:2 |
| Late | #41–#61 | **66.7%** | **2.622** | TD:8 COMP:6 SW:5 TU:2 |

The mid-game phase (#21–#40) represents a genuine edge trough. Both WR
(50.0%) and PF (1.613) declined from the early phase. The late phase
fully recovered and exceeded early-phase performance on both metrics.

**Edge drift verdict:** The trough was real and statistically meaningful —
rolling WR hit 45%, rolling PF hit 1.257. However, both fully recovered
by the end of the sequence. The overall trajectory is:
`INITIAL → TROUGH → RECOVERY`. Not ongoing deterioration.

---

### 6c. PF Drift

**CONFIRMED — trough at #31, full recovery by #52.**

Rolling PF timeline:

| Phase | Range | Notes |
|---|---|---|
| #20–#29 | 1.754–2.278 | Moderate; SIDEWAY-heavy May 22 period |
| **#30–#31** | **1.513–1.257** | **PF trough. May 23 TD loss + accumulated SIDEWAY losses** |
| #32–#37 | 1.467–1.740 | Partial recovery from May 24 COMP wins |
| **#38–#41** | **1.347–1.487** | **Second trough. May 24–25 TU/SW losses** |
| #42–#51 | 1.405–1.783 | Grinding recovery |
| **#52–#61** | **1.775–2.832** | **Full recovery driven by May 28–31 win runs** |

**Kill criterion context:** The kill criterion #2 threshold is PF < 1.3 at
n ≥ 80. The rolling PF minimum was 1.257 at #31. Had the rolling PF been
reported as the kill criterion metric (it is not — the criterion uses
cumulative PF), this would have been a near-miss. The cumulative PF never
approached 1.3. The rolling PF trough reflects concentration of losses in
a 20-trade window, not cumulative deterioration.

---

### 6d. WR Drift

**CONFIRMED — extended low-WR cluster, full recovery.**

Rolling WR below 52% (promotion threshold): 22 index points.

The below-52% cluster was concentrated in two sub-periods:

| Sub-period | Idx range | Dates | Rolling WR | Driver |
|---|---|---|---|---|
| Sub-period A | #22–#32 | May 21–23 | 45–50% | SIDEWAY losses, TU losses, TD/COMP mix |
| Sub-period B | #38–#51 | May 24–28 | 45–50% | TU/SW losses, TD slow recovery |

Between these sub-periods (#33–#37), rolling WR recovered briefly to 50%.
After #52, WR recovered to 55–70% and remained there through end of sequence.

**WR drift verdict:** The WR never stayed above 52% for an extended period
during W21 (it was at or below for most of May 22–28). This is the same
period identified as the mid-game trough. WR recovered completely by W22's
final phase and the full-sequence WR of 57.4% is above the 52% threshold.

---

## 7. Regime Stats Summary

| Regime | n | WR | PF | Net PnL | Share of trades | Share of PnL |
|---|---|---|---|---|---|---|
| COMPRESSION | 21 | 61.9% | **3.372** | +$0.130 | 34.4% | **66.5%** |
| TREND_DOWN | 19 | 57.9% | **2.300** | +$0.069 | 31.1% | 35.3% |
| SIDEWAY | 14 | 57.1% | **1.123** | +$0.007 | 23.0% | 3.6% |
| TREND_UP | 7 | 42.9% | **0.661** | −$0.010 | 11.5% | −5.4% |
| **Total** | **61** | **57.4%** | **2.022** | **+$0.196** | | |

**SIDEWAY note:** PF=1.123 (14 trades). This is weaker than the 1.258 reported
in prior analysis (15 trades). The difference is attributable to the n=14 vs
n=15 deduplication delta. SIDEWAY is marginally profitable but the lowest PF
of any positive regime and effectively break-even after 14 trades. This is
the weakest regime; it is the primary accumulation vehicle during the current
COMPRESSION-absent period.

**TREND_DOWN note:** PF=2.300 (19 trades). This matches the COMPRESSION_MARKET_ARCHETYPE
§3b figure and resolves the prior 18-vs-19 discrepancy. TREND_DOWN is the
strongest non-COMPRESSION regime.

---

## 8. Critical Finding: Non-COMPRESSION PF Was Negative for 14 Consecutive Trades

The rolling nc_PF (non-COMPRESSION PF, window=20) fell below 1.0 for indices
#38 through #51 — 14 consecutive index points spanning May 24–28.

During this window, the non-COMPRESSION sub-population of the rolling 20-trade
window was loss-making on a PF basis. The specific driver was the accumulation
of losses from:
- 3 TREND_UP losses (#38, #45, plus prior ones in window)
- 3 SIDEWAY losses (#39, #44, #49)
- 4 TREND_DOWN losses (spread across window)

The nc_PF recovered above 1.0 at #52 (2026-05-28) when the May 28–29 TD
win cluster (#51–#56) began displacing the May 24–25 losses from the window.

**Why this matters for the current period:**

COMPRESSION has been absent since 2026-06-01. The cell is now operating
entirely in non-COMPRESSION regimes (SIDEWAY + TREND_DOWN + TREND_UP).
The historical nc_PF at end of sequence is 2.661 — strong. But the historical
nc_PF also spent 14 consecutive trades at PF < 1.0. This is the risk range
to monitor as W23/W24 non-COMPRESSION trades accumulate.

The nc_PF recovery from 0.596 to 2.661 was driven by:
1. The May 28–29 TREND_DOWN win run (4 of 5 wins: #51, #52, #54, #56)
2. The May 30–31 COMPRESSION resurgence lifting the window quality

In the current COMPRESSION-absent period, driver #2 is unavailable. The
recovery will depend entirely on TREND_DOWN and SIDEWAY quality.

---

## 9. Drift Summary Table

| Dimension | Verdict | Peak concern | Recovery | Status |
|---|---|---|---|---|
| Regime composition | CONFIRMED drift | W21→W22 TD replacing COMP | Stable two-regime split | Monitoring |
| Edge (WR + PF combined) | CONFIRMED trough | #31 (WR=45%, PF=1.257) | Full by #52 | Recovered |
| PF drift | CONFIRMED midgame | #31 PF=1.257 | Full by #52 | Recovered |
| WR drift | CONFIRMED midgame | #31 WR=45%, 22 entries below 52% | Full by #52 | Recovered |
| nc_PF (non-COMP edge) | CONFIRMED negative period | #38–#51 nc_PF<1.0 for 14 trades | Full by #52 | Recovered (historically) |
| COMPRESSION share drift | CONFIRMED decline | 15% at #56 (before June collapse) | N/A (COMP absent since Jun 1) | Active risk |

---

## 10. Structural Observations

**Observation 1: The trough was compositional, not random.**
The mid-game trough (#21–#40) coincided with elevated SIDEWAY and TREND_UP
exposure and reduced COMPRESSION share. When COMPRESSION re-concentrated
in the rolling window (#42 onwards), both PF and WR recovered. This is
consistent with the COMPRESSION archetype finding that COMPRESSION is the
dominant PF driver.

**Observation 2: TREND_DOWN is the only reliable non-COMPRESSION engine.**
Of the three non-COMPRESSION regimes, TREND_DOWN (PF=2.300) is the only
one with a PF comfortably above 1.5. SIDEWAY (PF=1.123) is marginal.
TREND_UP (PF=0.661) is loss-making. The entire non-COMPRESSION case rests
on TREND_DOWN continuing to produce clean directional wins.

**Observation 3: SIDEWAY needs more n before conclusions.**
14 SIDEWAY trades (net +$0.007) is insufficient to distinguish edge from
noise. The 57.1% WR and 1.123 PF could collapse or strengthen with the
next 10–15 trades. SIDEWAY is the regime most likely to be accumulating
during the current COMPRESSION-absent period and warrants closer monitoring.

**Observation 4: TREND_UP is a structural drag.**
7 trades, PF=0.661, net=−$0.010. All 7 are spread across the sequence with
no concentration. If TREND_UP share grows while COMPRESSION is absent (TREND_UP
was 18.8% of post-collapse decision cycles), cumulative PF will face increasing
drag. Current TREND_UP net is small (−$0.010) but the directional concern is valid.

**Observation 5: The sequence is not trend-reversing.**
The overall arc (early strong → mid trough → late recovery) does not indicate
a deteriorating edge. The late phase (PF=2.622, WR=66.7%) is the strongest
segment of the sequence. If anything, the cell showed improving performance
as it matured. This is consistent with the LODO result (min PF=1.909 excluding
May 26, all 13 dates positive) and the second-half PF=2.462 from the robustness
audit.

---

## 11. Implications for Post-COMPRESSION Accumulation

Given COMPRESSION is absent (2.5% of evaluation cycles since Jun 1), new trades
will arrive primarily from SIDEWAY and TREND_DOWN.

**What the historical nc_PF says about current risk:**

| nc_PF scenario | Basis | Implication |
|---|---|---|
| nc_PF remains at 2.661 (final historical value) | Strong TREND_DOWN run in late-W22 | ETA to n=100 unchanged; PF stays above 1.5 |
| nc_PF reverts to trough (0.596) | Mid-game trough period | Promotion PF criterion (>1.5) at risk; monitor closely |
| nc_PF settles at historical non-COMP average | Average of all nc_PF readings | Moderate; PF likely 1.3–1.7 |

The nc_PF is volatile. A sustained negative period (14 trades below 1.0)
happened once already. Whether the post-COMPRESSION accumulation period
reproduces the trough or maintains the recovery depends on TREND_DOWN quality.

**TREND_DOWN quality indicator to watch:**
The W21 vs W22 causality audit showed that TREND_DOWN behaves better when
BTC is also trending down (WR=86%) vs. when BTC is in macro COMPRESSION
(WR=30%). In the current environment, BTC is predominantly in TREND_DOWN
(36.5% of post-collapse cycles). This is the favorable BTC context for
TREND_DOWN trades. Monitor whether new TREND_DOWN entries show WR closer
to 86% (BTC-TD-confirmed) or 30% (BTC-COMP-embedded) as they accumulate.

---

## 12. Governor Verdict

`EDGE_DRIFT_CONFIRMED_RECOVERED`

The ETH YES FC OS sequence shows real regime drift, edge drift, PF drift, WR drift,
and a sustained period of negative non-COMPRESSION PF — all of which fully recovered
by the end of the sequence. No drift is ongoing at the final observation point.

**What this audit confirms:**
- The cell's edge is not static. It experiences meaningful mid-sequence troughs.
- The trough at #31 (PF=1.257, WR=45%) would have triggered monitoring alerts
  had rolling metrics been tracked in real time.
- The nc_PF negative zone (#38–#51) is the most important historical warning
  for the current COMPRESSION-absent period.
- The full recovery demonstrates structural resilience: the edge reasserts
  after trough periods driven by TREND_DOWN quality improvement.

**What this audit does not authorize:**
- No runtime changes.
- No filter activations based on rolling WR or rolling PF.
- No regime-selective entry changes.
- No stop-loss or sizing adjustments.
- No promotion based on late-sequence strong performance alone.
- No demotion based on midgame trough alone.

**Correct action:** Continue accumulating. Monitor rolling nc_PF as the primary
leading indicator during the COMPRESSION-absent period. If nc_PF falls below 1.0
for more than 10 consecutive new trades in W23/W24, flag for a dedicated review
before n=80.

---

*Source: runtime/research_exports/completed_trades_v1_2.csv (canonical filter)*
*Analysis tool: tools/_drift_audit.py*
*No code changes. No runtime changes. No strategy changes. No commits.*
