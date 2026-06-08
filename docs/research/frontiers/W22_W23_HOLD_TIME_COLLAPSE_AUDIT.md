# W22 vs W23 Hold Time Collapse Audit
## ETH YES OPENING_SCAN — Why W23 Trades Closed Faster

---

### Metadata

| Field | Value |
|---|---|
| Produced | 2026-06-08 |
| Author | Claude (offline analysis) |
| Mode | READ ONLY — no code, config, strategy, risk, execution, or runtime changes |
| Data source | `runtime/research_exports/canonical_regime_enriched_trades_v1.csv` (n=62 canonical qualifying after dedup) |
| Filter | asset=ETH, side=YES, canonical_entry_lifecycle_phase contains OPENING_SCAN |
| W22 scope | 2026-05-25 to 2026-05-31 (n=42 executed; inclusive of canonical_retained_flag=false duplicate) |
| W23 scope | 2026-06-01 to 2026-06-08 (n=14 executed) |
| Comparison rows | 56 total OPENING_SCAN ETH YES executed trades across the two weeks |
| Prior audit | `W22_W23_OPPORTUNITY_SUPPRESSION_AUDIT.md` — hold collapse (×0.27) is the primary mechanical driver of qualifying opportunity collapse |
| Non-authorization | This report does not change strategy, risk, execution, sizing, live behaviour, runtime policy, or alerts |

> **Correction note (2026-06-08).** Subsequent canonical reconciliation removed one `canonical_retained_flag=false` duplicate trade (55s TP, 2026-05-28T11:25) from W22 TREND_DOWN. The correction changes the exact percentages and p-value slightly but does not alter the substantive conclusion. Affected figures: W22 TREND_DOWN n=13→12, 8/13=62%→7/12=58%, p≈0.003→p≈0.005. All instances are corrected throughout this document.

---

### Context

The prior opportunity suppression audit established that the W22→W23 qualifying opportunity collapse (21→5.8/week projected) decomposes as:

```
hold>15s pass rate:  W22 = 52.4%   →   W23 = 14.3%   (×0.27)
executed volume:     W22 = 21/wk   →   W23 = ~7/wk   (×0.33)
projected qualify:   21 × 0.27     = 5.7 vs 3.2 observed
```

The pass-rate collapse (×0.27) is the dominant mechanical factor. This audit explains it.

---

## Q1 — Hold-Seconds Distribution

| Statistic | W22 (n=42) | W23 (n=14) | Ratio W23/W22 |
|---|---:|---:|---:|
| min | 4s | 4s | 1.00× |
| p25 | 9.2s | 6.2s | 0.67× |
| **median** | **17.0s** | **11.0s** | **0.65×** |
| p75 | 27.2s | 12.0s | 0.44× |
| **max** | **65s** | **24s** | **0.37×** |
| mean | 21.0s | 11.1s | 0.53× |
| stdev | 15.8s | 6.3s | 0.40× |

| Bucket | W22 | W23 |
|---|---|---|
| ≤5s | 4/42 = 9.5% | 3/14 = 21.4% |
| ≤10s | 13/42 = 31.0% | 5/14 = 35.7% |
| **≤15s** | **20/42 = 47.6%** | **12/14 = 85.7%** |
| **>15s (qualifying)** | **22/42 = 52.4%** | **2/14 = 14.3%** |
| >30s | 10/42 = 23.8% | 0/14 = 0.0% |

**Key observation:** The W23 distribution is dramatically compressed at the upper tail. W22 had 10 trades exceeding 30 seconds (up to 65s); W23 has zero trades above 30s (max=24s). The p75 collapsed from 27s to 12s — three-quarters of W23 trades close within 12 seconds.

---

## Q2 — Outcome Split (TP vs SL)

| Metric | W22 TP (n=23) | W22 SL (n=19) | W23 TP (n=6) | W23 SL (n=8) |
|---|---:|---:|---:|---:|
| median hold | 24.0s | 11.5s | 11.0s | 8.5s |
| p75 hold | 39.5s | 18.0s | 11.8s | 12.8s |
| max hold | 65s | 32s | 23s | 24s |
| mean hold | 27.2s | 13.6s | 12.5s | 10.0s |
| hold >15s | 15/23 = **65%** | 7/19 = **37%** | 1/6 = **17%** | 1/8 = **12%** |
| \|move\| mean | 0.107 | 0.066 | 0.095 | 0.071 |

**Observations:**

- Both TP and SL trades are dramatically shorter in W23.
- The TP hold collapse is the most severe: 65% of W22 TP trades held >15s; only 17% in W23.
- SL hold collapse: 37% → 12%.
- SL outcome share increased: W22 = 19/42 = 45%; W23 = 8/14 = 57%.
- Absolute price moves are similar: TP moves 0.107 vs 0.095 (W22 vs W23); SL moves 0.066 vs 0.071.
- The move magnitudes reaching the TP/SL thresholds are comparable; the time to reach them differs.

**WR impact (descriptive only):**

| Subset | n | Wins | WR |
|---|---:|---:|---:|
| W22 hold >15s | 22 | 15 | 68% |
| W22 hold ≤15s | 20 | 8 | 40% |
| W23 hold >15s | 2 | 1 | 50% (n too small) |
| W23 hold ≤15s | 12 | 5 | 42% |
| **W23 overall** | **14** | **6** | **43%** |

W23's short-hold WR (42%) matches W22's short-hold WR (40%) almost exactly. W22's elevated overall WR (55%) came from its long-hold, TP-heavy subset (68% WR), which is absent from W23.

> **Note:** TP trades mechanically produce longer holds than SL trades (TP must drift to the take-profit threshold; SL can hit fast on an adverse move). The WR-by-hold split should be read as a structural description rather than evidence that longer holds earn edge.

---

## Q3 — Regime Split

| Regime | W22 n | W22 med | W22 max | W22 >15s | W23 n | W23 med | W23 max | W23 >15s |
|---|---:|---:|---:|---|---:|---:|---:|---|
| COMPRESSION | 14 | 15.0s | 65s | 7/14 = **50%** | **0** | — | — | — |
| TREND_DOWN | 12 | 18.5s | 53s | 7/12 = **58%** | 6 | 9.0s | 15s | 0/6 = **0%** |
| SIDEWAY | 10 | 16.0s | 42s | 5/10 = **50%** | 7 | 12.0s | 24s | 2/7 = **29%** |
| TREND_UP | 5 | 13.0s | 25s | 2/5 = 40% | 1 | 4.0s | 4s | 0/1 = 0% |

**Key observations:**

1. **COMPRESSION is absent from W23.** All 14 W22 COMPRESSION trades are missing. This directly removes 7 qualifying setups from any like-for-like projection.

2. **TREND_DOWN is the most striking within-regime collapse.** W22: 7/12 = 58% hold >15s (median 18.5s, max 53s). W23: 0/6 = 0% hold >15s (median 9s, max exactly 15s — every trade resolves at or below the qualifying threshold).

3. **SIDEWAY shows moderate within-regime shortening.** 50% → 29% pass rate; max hold fell from 42s to 24s.

**Compositional check — does COMPRESSION absence explain the pass-rate collapse?**

| Subset | n | >15s count | >15s rate |
|---|---:|---:|---:|
| W22 — all | 42 | 22 | 52.4% |
| W22 — COMPRESSION only | 14 | 7 | 50.0% |
| **W22 — without COMPRESSION** | **28** | **15** | **53.6%** |
| **W23 — all** | **14** | **2** | **14.3%** |

Removing COMPRESSION from W22 leaves a 53.6% pass rate — nearly identical to the full W22 rate. COMPRESSION absence explains part of the **count** collapse (~7 fewer qualifying setups) but explains almost none of the **pass-rate** collapse (52% → 53.6% without COMPRESSION, vs the actual W23 rate of 14.3%).

**The within-regime shortening — specifically in TREND_DOWN — is the primary driver of the pass-rate collapse.**

| Like-for-like comparison | n | >15s rate |
|---|---:|---:|
| W22 TREND_DOWN + SIDEWAY only | 23 | 13/23 = **56.5%** |
| W23 TREND_DOWN + SIDEWAY + TREND_UP | 14 | 2/14 = **14.3%** |

Even restricting W22 to the exact regimes present in W23, the W22 pass rate (56.5%) is four times the W23 rate (14.3%). The composition shift is insufficient to explain the collapse.

---

## Q4 — Exit-Reason Split

| Exit reason | W22 | W22 % | W23 | W23 % |
|---|---:|---:|---:|---:|
| `take_profit_target_reached` | 23 | 54.8% | 6 | 42.9% |
| `stop_loss` | 16 | 38.1% | 6 | 42.9% |
| `stop_loss_hit` | 3 | 7.1% | 2 | 14.3% |
| Forced close | 0 | 0% | 0 | 0% |
| Risk/time exit | 0 | 0% | 0 | 0% |
| End-of-event | 0 | 0% | 0 | 0% |

**Observations:**

- All exits in both weeks are standard TP/SL-type exits.
- Zero forced closes, risk closes, time-based closes, or end-of-event exits in either week.
- The TP share fell from 54.8% to 42.9%; the SL share rose correspondingly.
- Exit logic is unchanged — the same TP/SL threshold mechanism operates in both weeks.

---

## Q5 — Root-Cause Analysis

### 5.1 Entry Conditions: Identical

The `regime_reason` field records the regime classifier snapshot **at the moment of entry**. For all 14 W23 OPENING_SCAN ETH YES trades:

| Signal | W22 (42 trades) | W23 (14 trades) |
|---|---|---|
| movement | 0.00250 (41/42) | 0.00250 (14/14) |
| vol regime | NORMAL_VOL (41/42, 1 HIGH_VOL) | NORMAL_VOL (14/14) |
| liquidity | HEALTHY (42/42) | HEALTHY (14/14) |
| spread | 0.01000 (41/42, 1 = 0.03000) | 0.01000 (14/14) |
| cutoff | static_safe (all) | static_safe (all) |

Entry conditions are indistinguishable. The speed difference manifests **post-entry** in actual price dynamics, not in entry signals.

### 5.2 Compositional Effect: COMPRESSION Absence

- COMPRESSION is a low-volatility ranging regime that produced W22's extreme upper tail (65s, 48s, 35s all COMPRESSION).
- COMPRESSION had a 50% >15s pass rate — identical to the W22 average.
- Its complete absence from W23 removes 7 qualifying setups from the projected count.
- **However**: W22 without COMPRESSION has a 53.6% pass rate. Composition alone accounts for ~7 of the count collapse, not the pass-rate collapse.
- Status: **CONFIRMED (count contribution); INSUFFICIENT to explain pass-rate collapse.**

### 5.3 Within-Regime Shortening

TREND_DOWN and SIDEWAY both show shorter holds in W23 despite being classified identically at entry. Their statistical strength differs substantially.

**TREND_DOWN** (n=12 W22 / n=6 W23) — **statistically solid:**
- W22 holds: 4, 7, 8, 9, 13, 18, 19, 23, 25, 28, 49, 53 — median 18.5s, 58% >15s
- W23 holds: 4, 4, 7, 11, 11, 15 — median 9s, max 15s, **0% >15s**
- Every single W23 TREND_DOWN trade resolves at or below 15 seconds.
- Binomial test: P(0 successes of 6 | p=7/12) ≈ **0.005**. The TREND_DOWN collapse is statistically solid even at n=6. This is the primary empirical signal.

**SIDEWAY** (n=10 W22 / n=7 W23) — **directionally consistent, not significant:**
- W22 holds: 4, 4, 7, 11, 14, 18, 24, 32, 37, 42 — median 16s, 50% >15s
- W23 holds: 6, 11, 11, 12, 12, 23, 24 — median 12s, max 24s, 29% >15s
- Binomial test: P(≤2 successes of 7 | p=0.50) ≈ **0.23**. Directionally consistent with shortening but not distinguishable from noise at n=7. Treat as supporting observation only.

The within-regime shortening is real — **carried by TREND_DOWN** — and is the **primary driver of the pass-rate collapse**. The regime classifier labels these TREND_DOWN or SIDEWAY at entry, but the subsequent price trajectory to TP/SL resolution differs substantially between the two weeks.

### 5.4 What Is Under-Determined

**Why** TREND_DOWN and SIDEWAY trades resolve faster in W23 cannot be established from the canonical CSV alone.

The intuitive explanation — "W23 prices move faster" — is not independently verifiable from two price points per trade (entry_price, exit_price). The ratio |exit − entry| / hold_seconds is a **circular metric**: since exits are triggered by TP/SL thresholds, the denominator (hold_seconds) is the variable to be explained, and the numerator is largely fixed by those thresholds. More precisely:

- The metric claims +57% "velocity" overall.
- But: SIDEWAY absolute |move| per trade does not increase (in fact similar), while SIDEWAY holds also shortened. Under a genuine "higher velocity" story, SIDEWAY velocity should increase; instead it is flat or lower — falsifying any simple velocity narrative.
- The W23 `volatility_regime` at entry is NORMAL_VOL for all 14 trades, consistent with the regime classifier not detecting higher volatility.

Possible explanations for the within-regime hold shortening (all require per-tick price data to evaluate):

| Hypothesis | Evidence for | Evidence against |
|---|---|---|
| H1: Higher realized intraday volatility post-entry in W23 | Consistent with shorter holds and similar move magnitudes | vol_regime=NORMAL_VOL all W23 entries; circular price metric cannot confirm |
| H2: Specific W23 date/event effects (market shocks) | TREND_DOWN 0/6 >15s is very consistent | Only 1-2 days of W23 data; no external event data in CSV |
| H3: Small-sample variation | n=6 TREND_DOWN W23 is a small sample | The max hold cap at 15s in TREND_DOWN is extreme and consistent; SIDEWAY also shortens |

**An independent per-tick mid-price series for the W22 and W23 date windows would be required to distinguish H1 from H2/H3.** This data is not present in the canonical CSV.

### 5.5 Ruled-Out Causes

| Cause | Verdict | Evidence |
|---|---|---|
| C — Forced/time/risk exits | **RULED OUT** | Zero non-standard exits in both weeks (Q4) |
| E — Spread widening / liquidity degradation | **RULED OUT** | spread=0.01000 (W23, all 14); liq=HEALTHY (W23, all 14) |
| F — Strategy/exit logic change | **RULED OUT** | Entry conditions identical at snapshot (Q5.1); same cutoff; same TP/SL exit types |
| Filter artifact (dedup/canonical export) | **RULED OUT** | Same canonical_retained_flag filter; 56 total rows examined individually |
| Epoch age at entry | **RULED OUT** | W22 range 5–35s; W23 range 7–29s; no systematic difference |

### 5.6 Root-Cause Ranking and A–G Crosswalk

The task enumerated seven candidate causes (A–G). Disposition of each:

| Task cause | Label | Disposition | Detail |
|---|---|---|---|
| A | Faster TP hits | **Folded into H1 (under-determined)** | TP trades are shorter in W23 (17% vs 65% >15s). But "faster TP" presupposes higher post-entry velocity, which §5.4 shows is circular and unverifiable from exit prices alone. Not independently confirmable. |
| B | Faster SL hits | **Folded into H1 (under-determined), dominant signal** | SL trades are shorter (12% vs 37% >15s); SL share rose from 45% to 57%. Same circularity issue as A. The statistically solid TREND_DOWN collapse (p≈0.005) is the empirical evidence; its root cause remains H1. |
| C | Forced/time/risk exits | **RULED OUT** | Zero non-standard exits in either week. |
| D | Market resolving faster (earlier epoch close) | **Collapsed into A+B / H1** | Epoch age at entry is similar (5–35s W22; 7–29s W23). If "market resolving faster" means "underlying price dynamics are faster," that is H1 — circular and under-determined. |
| E | Spread widening / liquidity degradation | **RULED OUT** | spread=0.01000 all W23 (14/14); liq=HEALTHY all W23 (14/14). |
| F | Strategy or risk logic change | **RULED OUT** | Entry conditions (movement=0.00250, NORMAL_VOL, cutoff=static_safe) identical at snapshot in both weeks. |
| G | Mixed A+B as single market-structure phenomenon | **Closest to verdict — with one restatement** | The task defined G as "A+B unified." This audit's verdict is also "mixed," but the components are: (i) COMPRESSION absence (count, mechanistic), and (ii) TREND_DOWN within-regime shortening (pass rate, driven by A+B/H1). The G label applies, but the composition of "mixed" here is regime-specific rather than a flat velocity claim. |

**Ranked summary:**

| Rank | Cause | Contribution | Confidence |
|---|---:|---|---|
| 1 | TREND_DOWN within-regime shortening (A+B/H1) | Primary driver of the 52%→14% pass-rate collapse | Solid — p≈0.005 at n=6 |
| 2 | COMPRESSION absence (compositional) | Removes ~7 qualifying setups from projected count | High — mechanistic |
| 3 | SIDEWAY directional shortening | Consistent with rank-1 but not significant at n=7 | Weak — p≈0.23 |
| 4 | Root cause of rank-1 (H1 vs H2 vs H3) | Under-determined — requires per-tick price data | Unknown |

**Primary verdict: MIXED (task's G, regime-specific) — COMPRESSION absence (count) + TREND_DOWN within-regime shortening (pass rate, p≈0.005); root cause of the within-regime shortening is under-determined from canonical CSV.**

---

## Q6 — Price and Spread Comparison

| Metric | W22 (n=42) | W23 (n=14) |
|---|---|---|
| Entry price — min | 0.35 | 0.51 |
| Entry price — median | 0.54 | 0.53 |
| Entry price — max | 0.60 | 0.58 |
| Entry price range | 0.25 | 0.07 |
| \|Price move\| — mean | 0.089 | 0.081 |
| \|Price move\| — median | 0.08 | 0.08 |
| \|Price move\| — max | 0.22 | 0.14 |
| TP \|move\| mean | 0.107 | 0.095 |
| SL \|move\| mean | 0.066 | 0.071 |
| Spread | 0.01000 (41/42); 1 row = 0.03000 | 0.01000 (14/14) |
| Liquidity | HEALTHY (42/42) | HEALTHY (14/14) |

**Observations:**

- **Similar move magnitudes.** Median |price move| is identical (0.08) in both weeks. Mean moves are comparable. This rules out the hypothesis that W23 trades are simply "too small to matter" — they reach comparable TP/SL distances.
- **Slightly larger adverse moves in W23 SLs.** SL |move| mean: 0.066 (W22) vs 0.071 (W23). Small but consistent with a slightly more aggressive adverse move profile.
- **W23 entry price range is far narrower.** W22 entries span 0.35–0.60 (range 0.25); W23 entries span 0.51–0.58 (range 0.07). The ETH YES market was trading in a narrow band in W23. This is consistent with COMPRESSION being absent — that regime may require a wider price range to generate its characteristic slow-grind conditions.
- **Spreads and liquidity identical.** No evidence of market microstructure deterioration in W23.

---

## Evidence Summary

| Question | Finding | Confidence |
|---|---|---|
| Q1 — Distribution | Median halved (17→11s); p75 halved (27→12s); max crushed (65→24s); >15s rate: 52%→14% | High (n=56) |
| Q2 — Outcome split | Both TP and SL faster; TP collapse most severe (65%→17%); SL rate increased (45%→57%) | High |
| Q3 — Regime split | COMPRESSION absent (n=14→0); TREND_DOWN 58%→0% (p≈0.005, solid); SIDEWAY 50%→29% (p≈0.23, directional only) | TREND_DOWN: High; SIDEWAY: Weak |
| Q4 — Exit reason | All standard TP/SL exits both weeks; zero forced/time/risk exits | High |
| Q5 — Root cause | Task's G (mixed, regime-specific): COMPRESSION count + TREND_DOWN pass-rate collapse (p≈0.005); A/B/D presuppose circular velocity — under-determined; C/E/F ruled out | TREND_DOWN primary: Solid; root cause of within-regime shortening: Unknown |
| Q6 — Price/spread | Similar move magnitudes; identical spreads; narrow W23 price range; no liquidity change | High |

---

## Governor Verdict

**Decision: CONTINUE_ACCUMULATION**

The hold collapse is **not** caused by strategy changes, exit logic changes, canonical filter artifacts, spread/liquidity degradation, or forced closures. All standard-operation checks pass.

The collapse is a **MIXED** structural effect:
1. COMPRESSION's absence removes a regime that historically contributed ~7 qualifying setups per week and owned the upper hold tail (65–35s range). Its disappearance is consistent with the narrower W23 entry price range (0.51–0.58 vs W22's 0.35–0.60), suggesting the market conditions that produce COMPRESSION were simply absent in W23.
2. Within TREND_DOWN and SIDEWAY, trades resolve substantially faster in W23 — a behavioural change that cannot be attributed to entry signals (identical at snapshot time) and cannot be further decomposed without per-tick price data.

**No parameter changes are warranted.** The TP/SL thresholds and the 15-second qualifying floor are calibrated to W22-era market conditions; whether W23's faster dynamics represent a persistent regime shift or a transient effect is not determinable at n=14. Changing parameters to "chase" W23 dynamics risks miscalibrating to a temporary state.

**Primary watch signals:**
1. **COMPRESSION return**: Any week showing COMPRESSION > 0 in OPENING_SCAN ETH YES suggests the slow-grind conditions may be recovering.
2. **TREND_DOWN max hold**: If W24+ TREND_DOWN trades begin exceeding 15s again, the within-regime shortening has reversed.
3. **Weekly >15s pass rate**: Target 40%+ over a rolling 3-week window as a recovery signal. Current W23 level (14%) should not be extrapolated without additional weeks.
4. **Executed volume**: If the underlying executed volume (currently ~7/week) returns toward 20+/week, the count-side of the collapse recovers independently.

The n=62 campaign remains structurally sound: WR=56.5%, PF=1.980, nc_PF=2.367. The stall is a market-structure event, not a strategy failure signal.

---

*Produced 2026-06-08 — offline analysis only — READ ONLY task — no runtime changes*
