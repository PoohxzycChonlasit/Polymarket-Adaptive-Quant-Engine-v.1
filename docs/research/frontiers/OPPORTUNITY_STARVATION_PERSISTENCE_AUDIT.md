# Opportunity Starvation Persistence Audit

Date: 2026-06-09
Mode: READ ONLY — no code, runtime, strategy, risk, execution, or live changes
Source: `runtime/research_exports/canonical_regime_enriched_trades_v1.csv`
  canonical_n=67, filter: ETH YES OPENING_SCAN hold>15s, canonical_retained_flag=true
Non-authorization: this document does not authorize any runtime, strategy,
  risk, execution, sizing, or live behavior change.

---

## Verdict

**NORMAL**

The current 18-hour drought (since trade #67, 2026-06-08T23:30Z) is historically
normal. It ranks 9th of 66 inter-trade gaps — at the 87th percentile — and sits
below the P90 threshold (23.7h). Eight historical gaps exceeded it. The campaign
has recovered from a 5.7-day drought (W22→W23, the all-time maximum) and a
cluster of five consecutive zero-trade days (2026-06-01 through 2026-06-05).

The current environment closely resembles the W23→W24 transition: a 26.2-hour
pause followed by a 5-trade burst on 2026-06-08. The current drought has not
yet reached the 26.2-hour W23→W24 gap length.

**Current state: NORMAL. Not rare. Not historically extreme.**

---

## 1. Campaign Drought Statistics

| Statistic | Value |
|---|---|
| Total canonical trades | 67 |
| Total inter-trade gaps measured | 66 |
| Campaign calendar span | 22 days (2026-05-18 to 2026-06-08) |
| Active trade days | 16 |
| Zero-trade days within campaign span | 6 |
| Min gap | 0.08h (< 5 min) |
| Median gap | **1.67h** |
| Mean gap | **7.92h** |
| P90 gap | **23.7h** |
| P95 gap | **29.3h** |
| Max gap (campaign record) | **137.2h (5.7 days)** |
| Current drought | **18.0h** (as of 2026-06-09T17:30Z) |
| Current drought percentile | **87th** (8 of 66 historical gaps exceeded it) |

---

## 2. Drought Classification

| Class | Threshold | Historical count | % of all gaps |
|---|---|---|---|
| Normal | < 12h | 55 | 83% |
| Minor drought | 12–24h | 5 | 8% |
| Moderate drought | 24–48h | 5 | 8% |
| Severe drought | > 48h | 1 | 1% |
| **Current** | **18.0h** | **— (minor class)** | — |

---

## 3. All Droughts >= 12h (ranked by severity)

| Rank | Gap (h) | Days | From | To | From → To regime |
|---|---|---|---|---|---|
| 1 | **137.2** | **5.7** | #60 2026-05-31T12:10 | #61 2026-06-06T05:20 | COMPRESSION → SIDEWAY |
| 2 | 43.9 | 1.8 | #48 2026-05-26T12:11 | #49 2026-05-28T08:05 | TREND_DOWN → SIDEWAY |
| 3 | 34.7 | 1.4 | #61 2026-06-06T05:20 | #62 2026-06-07T16:05 | SIDEWAY → SIDEWAY |
| 4 | 29.3 | 1.2 | #1  2026-05-18T04:35 | #2  2026-05-19T09:51 | SIDEWAY → TREND_DOWN |
| 5 | 26.2 | 1.1 | #62 2026-06-07T16:05 | #63 2026-06-08T18:15 | SIDEWAY → TREND_UP |
| 6 | 24.6 | 1.0 | #58 2026-05-30T10:30 | #59 2026-05-31T11:05 | COMPRESSION → COMPRESSION |
| 7 | 23.7 | 1.0 | #52 2026-05-28T19:05 | #53 2026-05-29T18:50 | SIDEWAY → TREND_DOWN |
| 8 | 19.8 | 0.8 | #5  2026-05-19T14:35 | #6  2026-05-20T10:21 | TREND_DOWN → COMPRESSION |
| **9 (current)** | **18.0+** | **0.75+** | **#67 2026-06-08T23:30** | **—** | **SIDEWAY → (pending)** |
| 10 | 17.1 | 0.7 | #32 2026-05-23T11:45 | #33 2026-05-24T04:51 | COMPRESSION → COMPRESSION |
| 11 | 16.3 | 0.7 | #39 2026-05-24T13:45 | #40 2026-05-25T06:00 | SIDEWAY → COMPRESSION |
| 12 | 12.2 | 0.5 | #22 2026-05-21T15:30 | #23 2026-05-22T03:40 | TREND_UP → COMPRESSION |

The current drought enters the table at rank 9 and is actively growing. It
becomes RARE (P90+) if it exceeds 23.7h, i.e., if no qualifying trade appears
before approximately 2026-06-09T23:12Z.

---

## 4. Week-by-Week Comparison

### W21 (2026-05-18 to 2026-05-24)

| Metric | Value |
|---|---|
| Canonical trades | **39** |
| Velocity | **6.1 trades/day** |
| Active days | 7 / 7 |
| Zero-trade days | 0 |
| Max intra-week gap | 29.3h (start-of-campaign; #1 → #2) |
| Avg gap | 4.0h |
| Regime mix | COMPRESSION:14, TREND_DOWN:11, SIDEWAY:9, TREND_UP:5 |

Highest-velocity week. All 4 regimes active. Dense trading cluster 2026-05-20
to 2026-05-22 (25 trades in 3 days). The 29.3h gap at the top of W21 was the
opening of the campaign, not a deterioration.

---

### W22 (2026-05-25 to 2026-05-31)

| Metric | Value |
|---|---|
| Canonical trades | **21** |
| Velocity | **3.4 trades/day** |
| Active days | 6 / 7 |
| Zero-trade days | 1 (2026-05-27) |
| Max intra-week gap | 43.9h (#48 → #49, 2026-05-26 to 2026-05-28) |
| Avg gap | 7.5h |
| Regime mix | COMPRESSION:7, TREND_DOWN:7, SIDEWAY:5, TREND_UP:2 |

Velocity declined from W21 pace. One zero-trade day. A 43.9h moderate drought
mid-week (spanning the zero day). COMPRESSION and TREND_DOWN dominant.
W22 closed on 2026-05-31 with 2 COMPRESSION trades (#59–#60).

---

### W22→W23 Inter-Week Drought (CAMPAIGN RECORD)

```
137.2 hours = 5.7 days
2026-05-31T12:10Z (#60, COMPRESSION) to 2026-06-06T05:20Z (#61, SIDEWAY)
```

Five consecutive zero-trade days: 2026-06-01, 2026-06-02, 2026-06-03,
2026-06-04, 2026-06-05. This is the single longest drought in the campaign
and is an extreme outlier — it is 3.1x longer than the second-longest gap
(43.9h) and dwarfs all others.

---

### W23 (2026-06-06 to 2026-06-07)

| Metric | Value |
|---|---|
| Canonical trades | **2** |
| Velocity | 1.4 trades/day (within active span) |
| Active days | 2 |
| Zero-trade days | 0 (within active span) |
| Intra-week gap | 34.7h (#61 → #62, both SIDEWAY) |
| Regime mix | SIDEWAY:2 |

Sparse recovery after the 5.7-day drought. Only SIDEWAY regime. The 34.7h
gap between the 2 trades makes this the lowest-density active week.

---

### W23→W24 Inter-Week Gap

```
26.2 hours
2026-06-07T16:05Z (#62, SIDEWAY) to 2026-06-08T18:15Z (#63, TREND_UP)
```

Above-average but not extreme (ranks 5th of 66 historical gaps). Campaign
resumed with a burst of 5 trades on 2026-06-08.

---

### W24 (2026-06-08 — current, incomplete)

| Metric | Value |
|---|---|
| Canonical trades | **5** |
| Velocity | **5.0 trades/day** (burst on single day) |
| Active days | 1 (2026-06-08 only) |
| Zero-trade days | 0 active, 1 pending (2026-06-09 so far) |
| Max intra-day gap | 2.2h |
| Avg gap | 1.3h |
| Regime mix | TREND_UP:3, TREND_DOWN:1, SIDEWAY:1 |

All 5 W24 trades occurred on 2026-06-08 in a tight burst. High burst velocity
(5.0/day), very low intra-burst gaps. Post-burst drought currently 18.0h.

---

## 5. Daily Activity Log (full campaign)

| Date | n_day | Canon # | Regimes |
|---|---|---|---|
| 2026-05-18 | 1 | #1 | SIDEWAY:1 |
| 2026-05-19 | 4 | #2–5 | TREND_DOWN:3, TREND_UP:1 |
| 2026-05-20 | 7 | #6–12 | COMPRESSION:4, TREND_UP:2, SIDEWAY:1 |
| 2026-05-21 | 10 | #13–22 | TREND_DOWN:6, COMPRESSION:3, TREND_UP:1 |
| 2026-05-22 | 8 | #23–30 | SIDEWAY:6, COMPRESSION:2 |
| 2026-05-23 | 2 | #31–32 | TREND_DOWN:1, COMPRESSION:1 |
| 2026-05-24 | 7 | #33–39 | COMPRESSION:4, TREND_UP:1, TREND_DOWN:1, SIDEWAY:1 |
| 2026-05-25 | 6 | #40–45 | COMPRESSION:2, TREND_UP:2, SIDEWAY:2 |
| 2026-05-26 | 3 | #46–48 | TREND_DOWN:3 |
| **2026-05-27** | **0** | — | *(zero-trade day)* |
| 2026-05-28 | 4 | #49–52 | SIDEWAY:2, TREND_DOWN:2 |
| 2026-05-29 | 3 | #53–55 | TREND_DOWN:2, SIDEWAY:1 |
| 2026-05-30 | 3 | #56–58 | COMPRESSION:3 |
| 2026-05-31 | 2 | #59–60 | COMPRESSION:2 |
| **2026-06-01** | **0** | — | *(zero-trade day)* |
| **2026-06-02** | **0** | — | *(zero-trade day)* |
| **2026-06-03** | **0** | — | *(zero-trade day)* |
| **2026-06-04** | **0** | — | *(zero-trade day)* |
| **2026-06-05** | **0** | — | *(zero-trade day)* |
| 2026-06-06 | 1 | #61 | SIDEWAY:1 |
| 2026-06-07 | 1 | #62 | SIDEWAY:1 |
| 2026-06-08 | 5 | #63–67 | TREND_UP:3, TREND_DOWN:1, SIDEWAY:1 |
| **2026-06-09** | **0** | — | *(zero-trade day in progress; 8 source trades, all rejected)* |

---

## 6. Zero-Trade Days

| Date | Context | Duration of surrounding drought |
|---|---|---|
| 2026-05-27 | W22, mid-week | Part of 43.9h gap (#48→#49) |
| 2026-06-01 | W22→W23 transition | Part of 137.2h campaign-record drought |
| 2026-06-02 | W22→W23 transition | Part of 137.2h campaign-record drought |
| 2026-06-03 | W22→W23 transition | Part of 137.2h campaign-record drought |
| 2026-06-04 | W22→W23 transition | Part of 137.2h campaign-record drought |
| 2026-06-05 | W22→W23 transition | Part of 137.2h campaign-record drought |
| 2026-06-09 | W24 post-burst | **Current — 18.0h elapsed** |

Six zero-trade days total. Five were consecutive (the W22→W23 extreme event).
One was mid-week W22 (2026-05-27). 2026-06-09 is the current day, currently
at 18h elapsed.

---

## 7. Current Drought Ranking

| Question | Answer |
|---|---|
| Current drought duration | 18.0h |
| Historical gaps longer than current | **8 of 66** |
| Percentile from bottom | 87th |
| P90 threshold (rare) | 23.7h |
| Gap until RARE classification | **+5.7h** (if drought continues past ~23:12Z tonight) |
| P95 threshold (very rare) | 29.3h |
| Campaign record to beat | 137.2h |
| Current drought rank | **9th longest** of 66 |

---

## 8. Comparative Assessment

| Question | Answer |
|---|---|
| Is current state unusual? | **No** — 87th percentile; 8 prior gaps were longer |
| Is current state rare? | **Not yet** — rare threshold is P90 = 23.7h |
| Is current state historically extreme? | **No** — campaign record is 137.2h (W22→W23) |
| Has campaign recovered from worse? | **Yes** — recovered from 5.7-day drought + 5 zero-trade days |
| Closest historical analogue | W23→W24 gap (26.2h before 5-trade burst on 2026-06-08) |
| Regime mix on 2026-06-09 | BTC-dominant; sole ETH trade was NO/ACTIVE_INVENTORY/8s |

---

## Summary

| Item | Status |
|---|---|
| Current drought | **18.0h — NORMAL** (87th pct; below P90=23.7h) |
| Campaign record drought | 137.2h / 5.7 days (W22→W23; Jun 1–5) |
| W21 velocity | 6.1/day — highest week |
| W22 velocity | 3.4/day — deceleration; 1 zero-day |
| W22→W23 drought | **5.7 days** — extreme outlier; recovered fully |
| W23 trades | 2 (SIDEWAY only; post-drought recovery) |
| W24 trades | 5 (burst on 2026-06-08; post-W23 recovery) |
| 2026-06-09 qualifying trades | 0 (source active; no ETH YES OPENING_SCAN hold>15s) |
| Drought → RARE threshold | +5.7h from now (P90 = 23.7h) |
| Drought → EXTREME threshold | +119h from now (campaign record = 137.2h) |

**Current state is NORMAL. The campaign has a documented history of multi-day
droughts followed by burst recoveries. No action threshold is breached.**

---

*Offline/reporting only. No runtime, strategy, risk, or execution changes.
No commits authorized by this document.*
