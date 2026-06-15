# N70 Failure Scenario Audit

Date: 2026-06-09
Mode: READ ONLY — no code, runtime, strategy, risk, execution, or live changes
Source: canonical_regime_enriched_trades_v1.csv, n=67
Purpose: stress-test the upcoming N70 milestone; identify conditions under which
  N70 could produce a misleading or invalid conclusion
Non-authorization: this document does not authorize any runtime, strategy,
  risk, execution, governance, or live behavior change.

---

## Final Verdict

**MODERATE_RISK**

N70, correctly executed and correctly interpreted, will not produce a misleading
conclusion. The framework is designed to continue accumulation after N70 — not
to confirm edge, not to authorize live trading. The verdict vocabulary
(`CONTINUE_ACCUMULATION` / `CAUTION_DRIFT_REVIEW` / `FAIL_REVIEW_REQUIRED`)
explicitly does not license a "edge proven, proceed to live" read.

The residual risk is **operator-interpretation risk**: if a PASS verdict is
treated as edge confirmation rather than as a milestone on the way to n=100 and
p<0.05, the same evidence that should produce CONTINUE_ACCUMULATION could be
misread as justification for promotion. That misread would make the risk HIGH.

The verdict is MODERATE, not HIGH, because the framework forces the caveats —
p=0.164 will appear in the governor checklist; the 95% CI will be visible; kill
criteria status will be evaluated. The governance architecture is honest by
design. The MODERATE rating reflects the genuine evidence fragilities documented
below, not a failure of the process itself.

---

## 1. False Positive N70

**How could N70 appear successful while the edge is not real?**

### Statistical fact: results are not significant

The 95% Wilson confidence interval for the observed WR of 56.7% at n=67 is:

```
[44.8%, 67.9%]
```

The lower bound of **44.8% is below 50%**. With n=67 the data does not rule
out a true win rate below even-odds. The p-value (0.164) reflects a 16.4%
probability that results this good arise from a fair coin. N70 does not change
this; it merely adds 9 trades to a dataset that still needs 76 more (n=143) to
achieve p<0.05 at the observed WR.

**N70 PASS does not change p=0.164 into p<0.05.** It remains well above the
significance threshold. A CONTINUE_ACCUMULATION verdict is correct precisely
because significance has not been reached.

### Survivorship on the campaign window

The campaign opened 2026-05-18. The specific 22-day window may have coincided
with unusually favorable ETH 5-minute market structure. The sample contains no
cross-period validation; there is no out-of-sample test.

### W22 anomaly

W22 produced WR=66.7% on n=21 trades. A 66.7% WR window on n=21 is consistent
with a 50% true rate — it could represent variance rather than signal. W21
produced WR=51.3% on n=39, which is barely above the floor. If W22 is a lucky
cluster, the underlying WR may be closer to 51–53% than 56.7%.

---

## 2. Concentration Risk

**How dependent are results on top trades, top regime, top burst?**

### Top-5 trade concentration

| Rank | n | Date | Regime | Hold | PnL | Share of total |
|---|---|---|---|---|---|---|
| 1 | #15 | 2026-05-21 | COMPRESSION | 21s | +$0.02884 | 13.8% |
| 2 | #33 | 2026-05-24 | COMPRESSION | 77s | +$0.02714 | 13.0% |
| 3 | #9 | 2026-05-20 | COMPRESSION | 22s | +$0.02132 | 10.2% |
| 4 | #48 | 2026-05-26 | TREND_DOWN | 53s | +$0.02120 | 10.2% |
| 5 | #21 | 2026-05-21 | TREND_DOWN | 31s | +$0.02047 | 9.8% |
| **Top 5 total** | | | | | **+$0.11897** | **57.1%** |

Five trades (7.5% of the campaign) produced 57.1% of total net PnL.
Three of the five were COMPRESSION regime.

**Without top 5:**

| Metric | Full dataset | Excl. top 5 |
|---|---|---|
| n | 67 | 62 |
| WR | 56.7% | 53.2% |
| PF | 1.993 | **1.426** |
| Net PnL | +$0.208 | +$0.089 |

Excl-top-5 PF of 1.426 is meaningful — above 1.0, above the 1.3 kill threshold,
but 28% lower than the headline. This is precisely the metric that K4 monitors
at n=100 (kill fires if excl-top-5 PF < 1.0). At current trajectory, K4 will
not fire; but the gap between 1.993 and 1.426 is real.

**The headline PF of 1.993 overstates the de-concentrated edge by 40%.**

### Regime concentration

| Regime | n (%) | WR | PF | Net PnL | PnL share |
|---|---|---|---|---|---|
| COMPRESSION | 21 (31%) | 61.9% | 3.372 | +$0.13007 | **62.4%** |
| TREND_DOWN | 19 (28%) | 57.9% | 2.209 | +$0.06422 | **30.8%** |
| TREND_UP | 10 (15%) | 50.0% | 1.294 | +$0.01005 | 4.8% |
| SIDEWAY | 17 (25%) | 52.9% | 1.059 | +$0.00398 | **1.9%** |

Two regimes — COMPRESSION and TREND_DOWN — jointly produce 93.2% of net PnL
on 59.7% of trades. SIDEWAY (25% of trades) produces 1.9% of PnL. The campaign
rests almost entirely on a two-pillar structure.

**SIDEWAY is effectively breakeven.** PF=1.059 means the SIDEWAY sub-campaign
generates $0.06 per dollar risked in gross wins over gross losses. At n=17 this
is not distinguishable from noise.

---

## 3. Regime Fragility

**What happens under regime shift scenarios?**

### Scenario A: TREND_UP displaces COMPRESSION

COMPRESSION has been absent since 2026-06-01. TREND_UP has grown from n=7
(n=62 baseline) to n=10 (n=67 current). If TREND_UP continues to displace
COMPRESSION in new trades:

| Forward PF estimate (if only TREND_DOWN + SIDEWAY + TREND_UP) | |
|---|---|
| Regime mix assumption | Equal share of remaining regimes |
| Weighted forward PF | ~1.52 |

Still above the 1.5 floor, but barely. The buffer to P3 failure narrows from
0.493 to ~0.02 under this scenario.

### Scenario B: SIDEWAY expands

If SIDEWAY share grows from 25% toward 40-50% of new trades (plausible in
a low-volatility, range-bound ETH environment):

- SIDEWAY PF = 1.059 at n=17 — potentially degrading toward 1.0 at larger n
- A 40% SIDEWAY share with PF=1.06 and remaining regimes at historical PF
  gives estimated forward PF = ~1.4–1.5 — approaching the 1.5 watch floor
- More critically: SIDEWAY PnL contribution is nearly zero; the campaign would
  accumulate trades without proportional PnL growth

### Scenario C: COMPRESSION never returns (most material risk)

COMPRESSION is the top PnL regime (PF=3.372, 62% of net PnL). Its absence is
the central fragility. Two-pillar risk: if COMPRESSION stays gone AND
TREND_DOWN reverts to its historical floor:

| Scenario | Expected PF | Status |
|---|---|---|
| Historical full (all regimes present) | 1.993 | Current |
| COMPRESSION absent, others at historical rate | ~1.59 | Elevated risk |
| COMPRESSION absent + TREND_DOWN degrades to PF~1.5 | ~1.25 | K2 approaches |
| COMPRESSION absent + SIDEWAY expands to 40% | ~1.30 | K2 threshold level |

At the severe tail (COMPRESSION absent + TREND_DOWN weakens + SIDEWAY expands),
the campaign reaches K2 territory before n=100.

**COMPRESSION absence is not currently a tripwire event — it is the established
baseline since 2026-06-01 (confirmed in N70_WAITING_STATE_HEALTHCHECK.md). But
its non-return into the n=68–100 block is the single most dangerous forward
scenario.**

---

## 4. Forward Block Fragility

**Could N70 look good but N70→N100 fail?**

### The P4 / n=143 gap

The campaign needs n=143 to achieve p<0.05 at the observed WR. N70 delivers
n=70. N100 delivers n=100. Neither clears the statistical significance bar.
A N70 PASS verdict says nothing about whether P4 will pass at n=100.

**N100 will likely not produce p<0.05 unless WR improves.** At n=100 with
WR=56.7%, p≈0.085 — still not significant. Even at n=100, the campaign may not
resolve P4.

### K2 fragility window

Kill criterion K2 evaluates cumulative PF at n≥80. Current PF=1.993, buffer=0.693.
To breach K2 between n=70 and n=80 (10 new trades), PF would need to fall from
1.993 to below 1.3. This requires a catastrophic run — not likely in 10 trades.
K2 is structurally sound for the near term.

### WR reversion in new block

The n=62–70 new block (W23+W24) shows:
- W23 (n=2): WR=50.0%, PF=2.357
- W24 (n=5): WR=60.0%, PF=2.180

New block performance is currently healthy. But n=7 is too small to distinguish
signal from variance. A W25 block with WR=40–45% on n=10 would raise K1
considerations (K1 fires at WR<48% on n_new≥30). K1 is not in play at n=70
(n_new=9), but the forward window is relevant.

### Regime structural shift at n=70→100

If the next 33 trades (n=70→100) are predominantly SIDEWAY and TREND_UP:
- SIDEWAY PF~1.06: contributes ~zero to cumulative PF
- TREND_UP PF~1.29: modest contribution
- Cumulative PF would migrate toward ~1.5–1.6 range, still above K2 but
  creating a very different N100 story than N70 implies

---

## 5. Sample Illusion Risk

**How much confidence does N70 actually buy?**

### The Wilson CI is the honest answer

```
n=67, WR=56.7%
95% CI: [44.8%, 67.9%]
```

The confidence interval spans 23.1 percentage points. The true WR could be
anywhere from 44.8% (loss-making) to 67.9% (strong edge). N70 does not
resolve this ambiguity.

### Non-IID trades: effective sample is smaller than 67

The burst-clustering analysis (N70_WAITING_STATE_HEALTHCHECK.md,
OPPORTUNITY_STARVATION_PERSISTENCE_AUDIT.md) identified 11 distinct burst
clusters, each 3–9 trades within a 5–12-hour window. Within a burst:
- Same regime period (one market structure environment)
- Same session UTC window
- Correlated entry prices and market conditions
- Potentially correlated outcomes

Independent and identically distributed (IID) is an assumption of the binomial
test. If each burst is effectively one "macro-observation" rather than n
independent observations, the effective sample size for statistical purposes may
be closer to 11–16 clusters than 67 individual trades.

**Under a cluster-adjusted view, p=0.164 is optimistic.** The actual uncertainty
in the edge estimate may be substantially higher than the p-value implies.

This does not invalidate the data — the 67 trades are real outcomes. It means
the statistical confidence bands are likely wider than the binomial test reports.

### What N70 actually confirms vs. implies

| Claim | Status at N70 |
|---|---|
| WR > 52% in the observed sample | CONFIRMED (56.7%) |
| PF > 1.5 in the observed sample | CONFIRMED (1.993) |
| True WR > 50% with p<0.05 | NOT CONFIRMED (p=0.164) |
| Edge is statistically significant | NOT CONFIRMED (needs n=143) |
| Edge persists under regime shift | UNTESTED |
| Edge is not driven by top-5 concentration | PARTIAL (excl-top-5 PF=1.426) |

N70 confirms metrics within the observed sample only. It does not confirm edge.

---

## 6. Selection Bias Residual

**What remains unresolved even after the reconstructed ledger?**

### Canonical filter as a selection mechanism

The filter (ETH YES OPENING_SCAN hold>15s) was applied retrospectively to all
available trade_close events. Trades below the 15s hold threshold were excluded.
The burst precursor audit (BURST_PRECURSOR_AUDIT, same session) found multiple
ETH/YES/OPENING_SCAN events with hold=15s (1 second short of qualifying), which
were excluded. The filter boundary is sharp and creates a mechanical selection
effect at the hold=15s threshold.

**There is no documented validation that hold>15s selects for a better-performing
subset vs. hold≥10s or hold≥20s.** The threshold was chosen, not discovered.

### Campaign window selection

The campaign began 2026-05-18. The W21 opening week was the densest (39 trades).
There is no evidence that W21 was selected because it was a favorable environment,
but there is also no evidence it was not. A campaign that started two weeks
earlier or later might have produced different results.

### No cross-period validation

All 67 trades are from a single 22-day window. There is no out-of-sample period,
no walk-forward test, no paper-mode blind hold-out set. The reconstructed ledger
eliminates look-ahead bias in accounting, but does not provide independent
out-of-sample validation.

### COMPRESSION regime: selected vs. structural

COMPRESSION produced 62% of net PnL with PF=3.372. Without understanding why
COMPRESSION outperforms (model calibration, market microstructure, or specific
favorable periods in W21–W22), there is no basis for assuming this level of
outperformance continues. The COMPRESSION sub-campaign at n=21 is itself
below any reasonable significance threshold.

---

## 7. Evidence Tier Review

### Proven

| Claim | Evidence | Source |
|---|---|---|
| WR = 56.7% in 67 observed trades | Exact count: 38W/29L | Canonical export, PASS validation |
| PF = 1.993 in 67 observed trades | Gross wins / gross losses | Same |
| Kill criteria K1–K4 all INACTIVE at n=67 | All thresholds unmet | Command center |
| 0 duplicate condition_id in canonical set | Dedup key verified | Export meta: 1 dup removed |
| Regime join rate = 100% (0 UNKNOWN regimes) | meta.json | Export meta |
| P2 (WR>52%) passes | 56.7% > 52% | Command center |
| P3 (PF>1.5) passes | 1.993 > 1.5 | Command center |
| P5 (≥3 weeks) passes | 4 weeks (W21–W24) | Campaign dashboard |

### Partially Proven

| Claim | Evidence | Caveat |
|---|---|---|
| Edge exists in COMPRESSION sub-regime | PF=3.372, n=21, WR=61.9% | n=21 insufficient for significance; regime absent since June 1 |
| Edge exists excl. top-5 concentration | PF=1.426, n=62 | Weaker; 95% CI likely still includes breakeven |
| nc_PF recovery is durable | nc_PF=2.921, 0 consecutive <1.0 | Rolling window=20; only 14 trades since the trough period |
| W22 WR=66.7% reflects real signal | n=21, 3.4/day | Could be favorable-window variance |

### Unproven

| Claim | Status |
|---|---|
| True WR > 50% (statistical significance) | p=0.164 (16.4% chance of luck); n_required=143 |
| Edge is IID across independent market conditions | Burst clustering creates non-IID structure |
| COMPRESSION outperformance will persist | Regime absent since June 1; no forward evidence |
| Edge survives without top-5 trades with significance | Excl-top-5 PF=1.426; 95% CI likely includes breakeven at n=62 |
| Edge is robust to regime shift toward SIDEWAY/TREND_UP | Speculative forward scenario; no out-of-sample data |
| p<0.05 will be achievable by n=100 | At current WR, p≈0.085 at n=100 — P4 gate may not pass at N100 |

---

## 8. Most Dangerous Wrong Conclusion

**If the operator misunderstood N70, what mistake would be most likely?**

### The wrong conclusion

> *"N70 passed. WR=56.7%, PF=1.993, kill criteria clean. The edge is confirmed.
> We can proceed to Phase 2 / consider live trading."*

### Why this is dangerous

1. **p=0.164 is not confirmation.** A 16.4% probability of luck is not evidence
   of edge. The N70 PASS verdict means metrics are above minimum thresholds for
   continued accumulation — nothing more.

2. **The 95% CI [44.8%, 67.9%] includes edge-less outcomes.** The true WR could
   be 44.8% — that would be a losing strategy. The data does not rule this out.

3. **Top-5 concentration could evaporate.** If the 5 largest trades (57% of PnL,
   all from COMPRESSION / TREND_DOWN in W21) were slightly worse, or if
   COMPRESSION doesn't return, the headline metrics are materially weaker.

4. **Phase 2 (paper-only inventory replay) is not Phase 4 (live trading).**
   The roadmap requires Phase 2 and Phase 3 evidence before any live consideration.
   N70 is a Phase 1 milestone — it opens Phase 1 continuation, not Phase 2 entry.

5. **CONTINUE_ACCUMULATION is not PROMOTE.** The verdict vocabulary is designed
   for exactly this: continue evidence accumulation, not begin production.

### The hinge

If the operator treats CONTINUE_ACCUMULATION as edge-confirmed:
- The risk classification shifts from MODERATE → HIGH
- All the fragilities documented in Sections 1–7 become live risks rather than
  monitored risks
- The most severe scenario: live trading begins on a strategy with p=0.164,
  COMPRESSION-concentrated PnL, and a 95% CI that includes <50% WR

### The correct read

> *"N70 shows the campaign is within historical operating parameters. Metrics
> pass minimum thresholds. Evidence is encouraging but not significant.
> Continue accumulation to n=100 while monitoring K1–K4 and COMPRESSION
> re-emergence. P4 (p<0.05) will likely require n=143+."*

---

## Summary Table

| Risk Factor | Severity | Mitigant in framework | Net risk |
|---|---|---|---|
| p=0.164 (not significant) | High | P4 gate (p<0.05 required) | Monitored |
| 95% CI includes <50% WR | High | WR floor (P2) requires >52% | Monitored |
| Top-5 = 57% of PnL | High | K4 (excl-top-5 PF at n=100) | Monitored |
| COMPRESSION = 62% of PnL; absent Jun 1+ | High | nc_PF, regime drift audit | Monitored |
| Non-IID burst clustering | Medium | Effective sample risk acknowledged | Unmitigated |
| SIDEWAY PF=1.059 (breakeven) | Medium | Kill criteria; governor review | Monitored |
| W22 WR=66.7% may be variance | Medium | P4 gate | Monitored |
| No out-of-sample validation | High | Campaign continues to n=100+ | Unmitigated |
| Operator interpretation risk | High | 15-question governor checklist | Partially mitigated |
| Forward block fragility (n=70→100) | Medium | K1, K2, K3, K4 kill criteria | Monitored |

**Verdict: MODERATE_RISK**

The process is sound. The fragilities are real. The framework forces honest
reporting of all of the above. MODERATE becomes HIGH only if the operator reads
a PASS verdict as edge confirmation.

---

*Offline/reporting only. No runtime, strategy, risk, or execution changes.
No commits authorized by this document.*
