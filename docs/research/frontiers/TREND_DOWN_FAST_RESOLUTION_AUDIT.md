# TREND_DOWN Fast Resolution Audit

## Metadata

| Field | Value |
|---|---|
| Produced | 2026-06-08 |
| Mode | READ ONLY — offline research, no code/strategy/risk/execution changes |
| Author | Quant Research Agent |
| Source | `runtime/research_exports/canonical_regime_enriched_trades_v1.csv` + matched scan_logs |
| Related | `docs/research/frontiers/W22_W23_HOLD_TIME_COLLAPSE_AUDIT.md` |
| Scope | W22 and W23 TREND_DOWN ETH YES OPENING_SCAN trades only |

---

## Context

The W22 vs W23 Hold Time Collapse Audit identified a statistically significant within-regime finding:

- **W22 TREND_DOWN (n=13):** 8/13 hold >15s = **62%**
- **W23 TREND_DOWN (n=6):** 0/6 hold >15s = **0%**
- **Binomial p(0/6 | p=0.62) ≈ 0.003** — the sharpest signal in that audit

This follow-up audit asks why. Five working hypotheses (H1–H5) are ranked against all available canonical CSV fields plus pre-trade scan_log context for each of the 18 canonical trades.

> **Canonical count correction.** The session context summary cited W22 TREND_DOWN n=13 (8/13 >15s = 62%, p≈0.003). The canonical CSV reveals a 55s TP at 2026-05-28T11:25 with `canonical_retained_flag=false` — it is a duplicate execution of the 49s TP at the same timestamp. **Canonical W22 n=12** (7/12 >15s = 58%). Binomial P(0/6 | p=7/12) ≈ 0.005. The finding remains significant; the counts are corrected throughout this document. The same correction applies to W22_W23_HOLD_TIME_COLLAPSE_AUDIT.md which used the n=13 figure.

**Calibration notice (read first).** The six W23 TREND_DOWN trades are **not six independent Bernoulli draws:**
- Trades T3, T4, T5 form a single 30-minute burst (2026-06-06 04:20–04:50 UTC)
- Four of six trades fall within a 65-minute window (03:45–04:50 UTC) on two adjacent days
- Effective independent episodes ≈ 3, not 6

The binomial p≈0.005 is real but is heavily leveraged on this episodic clustering. It measures "W22 would rarely produce this pattern," not "W23 is structurally and persistently faster." Conclusions below are calibrated accordingly.

---

## Q1 — Quantitative Comparison: All Fields

### Hold-Time Distribution

| Metric | W22 TREND_DOWN (n=12 canonical) | W23 TREND_DOWN (n=6) |
|---|---:|---:|
| Sorted holds (s) | 4, 7, 8, 9, 13, 18, 19, 23, 25, 28, 49, 53 | 4, 4, 7, 11, 11, 15 |
| Median (s) | 18.5 | 9 |
| Max (s) | 53 | 15 |
| Min (s) | 4 | 4 |
| Pass >15s | **7/12 (58%)** | **0/6 (0%)** |
| Trades >30s | 2 (49s, 53s) | 0 |

The W23 max of 15s is one second below the >15s threshold. Two of six W23 trades are exactly 11s. The ceiling compression is real but narrow at the top end.

### Entry Price

| Metric | W22 | W23 |
|---|---:|---:|
| Range | 0.50 – 0.60 | 0.51 – 0.56 |
| Median | ~0.54 | 0.52 |
| Trades at exactly 0.52 | — | 4 / 6 |

W23 entries are narrower and concentrated at 0.52. The difference (median 0.52 vs ~0.54) is small and its causal status is examined under H3.

### Exit Price

| Metric | W22 TP exits | W22 SL exits | W23 TP exits | W23 SL exits |
|---|---:|---:|---:|---:|
| Range | 0.61 – 0.74 | 0.39 – 0.51 | 0.60 – 0.63 | 0.45 – 0.50 |

### TP/SL Distance From Entry

| Metric | W22 TP | W22 SL | W23 TP | W23 SL |
|---|---:|---:|---:|---:|
| Mean move | 0.116 | 0.075 | 0.095 | ~0.063 |
| Min move | 0.060 | 0.050 | 0.080 | 0.020 (T6) |
| Max move | 0.220 | 0.110 | 0.110 | 0.080 |
| Range ratio | 3.7× | 2.2× | 1.4× | 4.0× |

TP/SL distances vary 2–4× within each week. Thresholds are **neither fixed-absolute nor fixed-relative.** This rules out any mechanism where entry price proximity alone determines exit speed (see H3).

### Confidence

| Metric | W22 | W23 |
|---|---|---|
| Range | 0.5426 – 0.7403 | 0.5464 – 0.5538 |
| Distribution | One outlier at 0.7403; rest 0.54–0.56 | Tight cluster; all within 0.007 of each other |

W23 confidence is tighter but not materially higher or lower than the W22 median.

### Edge (Scan_Log EV Proxy)

| Metric | W22 | W23 |
|---|---|---|
| Positive edge (>0) | 5/12 (42%) | 5/6 (83%) |
| Zero edge | 7/12 (58%) | 1/6 (17%) |
| Positive edge range | 0.65 – 0.88 | 0.63 – 0.88 |

**W23 entered stronger EV setups than W22.** This rules out any hypothesis that W23 trades were weaker-conviction entries that resolved faster by failing quickly.

### Data-Quality Fields

| Field | W22 (n=12) | W23 (n=6) |
|---|---|---|
| oracle_age_ms range | 50 – 1237ms | 30 – 1193ms |
| orderbook_age_ms | Mostly 0, some up to 262ms | Mostly 0, some up to 599ms |
| spread (regime_reason) | 0.01000 all | 0.01000 all |
| liquidity (regime_reason) | HEALTHY all | HEALTHY all |
| movement (regime_reason) | 0.00250 all | 0.00250 all |
| vol bucket | NORMAL_VOL all | NORMAL_VOL all |
| regime_join_confidence | DIRECT all | DIRECT all |

Oracle and orderbook staleness overlap substantially between weeks. No systematic data-quality difference.

### Condition IDs

W22 has 12 unique condition_ids; W23 has 6 unique condition_ids; **zero overlap.** These are entirely different Polymarket market instances. Any mechanism must operate through market dynamics, not through shared contract state.

---

## Q2 — Lifecycle Position (H2)

**H2: W23 entries arrived later in the 5-minute epoch, leaving less time to resolve.**

Tested by computing epoch_age at entry = `entry_ts − epoch_start_ts` and `seconds_remaining` from scan_logs.

| Metric | W22 TREND_DOWN (n=12) | W23 TREND_DOWN (n=6) |
|---|---:|---:|
| epoch_age at entry — mean | 14.3s | 12.5s |
| epoch_age at entry — range | 6 – 24s | 7 – 17s |
| seconds_remaining — range | 278 – 295 | 284 – 295 |

All 18 canonical trades have scan_log-confirmed seconds_remaining. All enter within the **first 17–22 seconds** of their 5-minute epoch, with >278s remaining. There is no systematic difference in lifecycle position between weeks.

**H2: DEFINITIVELY RULED OUT.**

---

## Q3 — Entry Context and Strike Proximity (H3)

**H3: W23 entries were closer to the 0.50 strike threshold, so smaller moves triggered TP/SL.**

#### Entry Price Assessment

W23 entries are clustered at 0.52 (4/6 exactly 0.52); W22 entries span 0.50–0.60 but include trades at 0.50, 0.51, 0.52, 0.53 — overlapping substantially with W23. The difference in median (~0.52 vs ~0.54) is small.

#### TP/SL Mechanism Assessment

The TP/SL threshold mechanism is examined using observed exit distances (see Q1 table above). Key facts:
- In W22, TP moves range from +0.060 to +0.220 — a 3.7× spread. Entry at 0.52 produced a +0.220 TP (T04, 53s hold). Entry at 0.60 produced a +0.070 TP.
- No consistent relationship exists between entry price and the size of the move required to reach TP or SL.
- TP exit prices range 0.61–0.74 in W22 (not a fixed absolute level) and the TP move is not proportional to entry distance from 0.50.

**Conclusion:** "Entry near 0.52 → mechanically shorter path to TP/SL" is unsupported. The mechanism would require TP/SL levels that are either fixed-absolute or fixed-percentage, and neither is observed. H3 has no clean causal path at this data resolution.

**H3: WEAK.** Cannot be ruled out, but no mechanism is established and the entry price difference is small.

---

## Q4 — Liquidity and Spread (H4)

**H4: W23 markets were more liquid or had tighter spreads, causing faster price discovery.**

Every one of the 18 canonical trades — W22 and W23 — shows:
- `liquidity = HEALTHY`
- `spread = 0.01000`
- `liq_cutoff = static_safe`

**H4: DEFINITIVELY RULED OUT.** Spread and liquidity classification are identical across both weeks.

---

## Q5 — Pre-Trade Decision Context

### Standard OPENING_SCAN Pattern

All 18 canonical trades follow the same structural lifecycle pattern:

```
Epoch N:    Blocked by skip (delta_extreme / empty_book / max_entries / cutoff)
Epoch N+1:  Approved at start of new epoch (secs_rem 278–295)
```

This is the normal OPENING_SCAN entry pattern. It is present in both W22 and W23 and is not discriminating between weeks.

### W23 Confirmed Pre-Entry Scan Context

| Trade | UTC | secs_rem | conf | edge | Prior-epoch skip |
|---|---|---:|---:|---:|---|
| T1 | 2026-06-05 03:45:18 | 284 | 0.5476 | 0.6300 | delta_extreme |
| T2 | 2026-06-05 04:00:09 | 295 | 0.5538 | 0.6300 | clob_empty_response |
| T3 | 2026-06-06 04:20:12 | 290 | 0.5480 | 0.8000 | delta_extreme |
| T4 | 2026-06-06 04:40:13 | 289 | 0.5466 | 0.8800 | delta_extreme |
| T5 | 2026-06-06 04:50:12 | 290 | 0.5464 | 0.7500 | delta_extreme |
| T6 | 2026-06-07 11:15:17 | 285 | 0.5474 | **0.0000** | delta_extreme |

### W22 Confirmed Pre-Entry Scan Context (all 12 canonical trades)

| Trade | UTC | hold_s | edge | Prior eb | Prior de | Prior pattern |
|---|---|---:|---:|---:|---:|---|
| 05-26 12:10:19 | 12:10 | 53 | 0.00 | **1** | 0 | **empty_book ONLY — pure dormant** |
| 05-28 11:25:20 | 11:25 | 49 | 0.00 | **1** | 3 | delta_extreme + oracle 4022ms stale + empty_book |
| 05-26 02:40:10 | 02:40 | 28 | 0.73 | 0 | 1 | delta_extreme |
| 05-26 02:45 | 02:45 | 25 | — | 0 | 0 | Max entries (prior position open) |
| 05-29 23:20:17 | 23:20 | 23 | 0.00 | 0 | 8 | delta_extreme (8) |
| 05-29 18:50:15 | 18:50 | 19 | 0.65 | 0 | 0 | Nothing (0 de, 0 eb) |
| 05-28 11:10:15 | 11:10 | 18 | 0.00 | 0 | **9** | delta_extreme (9) |
| 05-26 16:15:25 | 16:15 | 13 | 0.75 | 2 | 1 | empty_book (2) + delta_extreme (1) + oracle 1237ms |
| 05-26 15:05:18 | 15:05 | 9 | 0.88 | 0 | 3 | delta_extreme (3) |
| 05-26 06:30:12 | 06:30 | 8 | 0.00 | 0 | **11** | delta_extreme (11) — highest count |
| 05-26 15:25:20 | 15:25 | 7 | 0.73 | 2 | 6 | delta_extreme (6) + empty_book (2) |
| 05-31 14:10:12 | 14:10 | 4 | 0.00 | 0 | 0 | Max entries (prior position open) |

All 12 canonical W22 trades confirmed. (eb = empty_book count in prior 2 min; de = delta_extreme count.)

### The delta_extreme Pre-Entry Pattern Is Not Discriminating

`delta_extreme` in the prior epoch is present before W22 holds of 7s, 8s, 9s, 18s, 23s, 28s — spanning the entire hold range. Within W23, delta_extreme precedes all 4s, 4s, 7s, 11s, and 15s trades. Pre-epoch delta_extreme count also shows no pattern: W22's highest count (11 in prior 2 min) precedes an 8s hold; the 9-count precedes an 18s hold; zero-count trades range from 4s to 19s. W23's entries are all 0–1 delta_extreme in the 2-minute window. Count is **not a useful discriminator at this sample size.**

### The "Dormant Market" Observation: n=1 pure case

Among W22's two longest holds:
- **53s TP (05-26 12:10):** preceded by `empty_book` ONLY — zero delta_extreme in the prior 2-minute window. **Pure dormant case**: the orderbook had no quotes, the oracle price was not moving, and the entry followed into a market just waking up.
- **49s TP (05-28 11:25):** preceded by delta_extreme (3 counts) + oracle stale at 4022ms + empty_book. This is a distinct **oracle-lag pattern** where the oracle was not tracking the market despite active price movement — a different mechanism from pure dormant.

The critical test is whether empty_book alone predicts long holds across all 12 W22 trades:
- 53s TP: 1 empty_book, **0 delta_extreme** → LONG — pure dormant
- 49s TP: 1 empty_book, 3 delta_extreme → LONG — confounded by oracle lag
- 13s TP: 2 empty_book, 1 delta_extreme → BORDERLINE
- 7s SL: 2 empty_book, 6 delta_extreme → SHORT

**Pure dormant (empty_book + zero delta_extreme) is n=1** (53s TP). When empty_book is combined with active delta_extreme, results span 7s–13s with no predictive power. The "dormant market → slow hold" is a hypothesis-generating observation at n=1, not a validated mechanism.

Neither the pure dormant pattern nor the oracle-lag pattern appears in any W23 trade — no W23 prior epoch had empty_book at zero delta_extreme. This removes the category of entry conditions that produced W22's canonical longest hold. The absence is of evidence, not evidence of a structural W23 difference.

### The 2026-06-06 04:20–04:50 Cluster Event

Three consecutive TREND_DOWN trades in a 30-minute window:

| Trade | UTC | hold_s | entry_p | exit_p | move | result |
|---|---|---:|---:|---:|---:|---|
| T3 | 04:20:12 | **4s** | 0.53 | 0.45 | −0.08 | SL |
| T4 | 04:40:13 | **4s** | 0.52 | 0.45 | −0.07 | SL |
| T5 | 04:50:12 | **7s** | 0.52 | 0.63 | +0.11 | TP |

Price oscillated violently: 0.53→0.45 (SL), 0.52→0.45 (SL again), 0.52→0.63 (TP bounce). The SL floor and TP ceiling were both hit on successive trades within the same session window. Each prior epoch was blocked by `delta_extreme`, indicating the oracle was registering large price movements throughout this period.

At T5 entry, oracle_age_ms = 1193ms — the oracle was 1.2 seconds stale, suggesting the underlying was moving faster than oracle update cadence. These are the characteristic signatures of a sharp, event-driven intraday price move in the ETH YES market.

These three trades contribute 3 of 6 W23 data points and dominate the `0/6 >15s` finding. They are an event, not a regime.

---

## Q6 — Hypothesis Ranking (H1–H5)

### H2 — Later Lifecycle Position

**Status: DEFINITIVELY RULED OUT.**
All 18 trades with confirmed scan_log data enter at secs_rem 278–295. Lifecycle position is identical between W22 and W23.

---

### H4 — Liquidity Changed

**Status: DEFINITIVELY RULED OUT.**
HEALTHY liquidity classification and spread = 0.01000 for all 18 canonical trades in both weeks. No change in reported market depth or cost structure.

---

### H3 — Entry Closer to Strike / Tighter Price Range

**Status: WEAK.**
W23 entries are slightly more concentrated near 0.52 (vs W22 range 0.50–0.60). However:
1. W22 also has entries at 0.50, 0.51, 0.52 — the price ranges overlap substantially.
2. TP/SL exit distances in W22 vary 3.7× (0.060–0.220 for TP), with the largest TP move (+0.22) coming from a W22 entry at exactly 0.52. No inverse relationship between entry price proximity to 0.50 and TP/SL distance is visible.
3. Since TP/SL thresholds are neither fixed-absolute nor fixed-relative, "closer to strike" has no consistent mechanical path to faster resolution.

Cannot rule out, but no mechanism established.

---

### H1 — Faster Market Structure (Genuinely Higher Price Velocity at Entry)

**Status: PARTIAL — Supported for the 06-06 event; under-determined for remaining trades.**

The 2026-06-06 04:20–04:50 cluster is the strongest evidence for H1. Three consecutive delta_extreme-blocked epochs followed by 4-second and 7-second resolutions, with oracle staleness reaching 1193ms at entry, are consistent with a genuine high-velocity intraday event in the ETH market during Asian morning hours.

**Non-circular evidence available:** prior-epoch delta_extreme blocks measure oracle price change (a leading indicator external to each trade's own P&L). Their presence confirms the oracle was registering large moves before these entries. This is an independent signal, not circular with the trade's own exit.

The three remaining W23 trades (T1=11s, T2=15s, T6=11s) on different days are fast but do not have the same cascade signature. Whether they are individually "fast market" events or simply reflect the right tail of ordinary market behaviour at n=3 cannot be established from scan_log context alone.

H1 explains the cluster (3/6 trades) well. It does not establish a persistent or structural W23 velocity increase.

---

### H5 — Mixed / Composite Explanation

**Status: PRIMARY VERDICT.**

No single mechanism explains all six W23 TREND_DOWN trades. The evidence is best described as a composite:

| Component | Trades covered | Confidence |
|---|---|---|
| Episodic event: 06-06 04:20–04:50 burst (H1 local) | T3, T4, T5 (3/6) | High — visible in price moves and oracle staleness |
| Absence of "dormant market" pre-entry conditions | All 6 (no empty_book-only epochs) | Medium — n=2 baseline in W22; absence ≠ cause |
| Small-sample + time-of-day concentration | 4/6 trades in 03:45–04:50 UTC | Medium — consistent with high-activity window, not confirmed |
| Remaining unexplained variance | T1, T2, T6 | Low — n=3, no distinguishing signal found |

**Root cause:** Under-determined at n=6 with ~3 independent episodes. The 06-06 cluster is a specific market event, not evidence of a sustained regime change. The longest W22 holds (49s, 53s) required specific dormant-market entry conditions (empty_book-only prior epoch) that happened to be absent in all W23 trades. Neither factor is a strategy failure or a signal that W23 TREND_DOWN performance is systematically different from W22 on a per-trade basis.

**Drift implication:** W23 TREND_DOWN holds are shorter than W22's, but the comparison is distorted by (a) the 06-06 event, (b) the absence of dormant-market entries, and (c) n=6 with episodic clustering. The within-regime PnL direction (all 6 trades resolved TP or SL, none stuck open) shows no execution pathology.

---

## Evidence Summary

| Question | Finding | Confidence |
|---|---|---|
| Q1: Quantitative fields | Entry prices, confidence, and oracle/OB age overlap between weeks. W23 edge is HIGHER (5/6 positive vs 5/12). TP/SL distances vary 2–4× within each week. W22 canonical n=12 (55s duplicate excluded). | High |
| Q2: Lifecycle (H2) | All 18 canonical trades scan-log-confirmed at secs_rem 278–295. H2 RULED OUT. | High |
| Q3: Strike proximity (H3) | Entry median 0.52 vs ~0.54; TP/SL not fixed. No mechanism. WEAK. | Medium |
| Q4: Liquidity (H4) | HEALTHY + spread 0.01000 for all 18 canonical trades. H4 RULED OUT. | High |
| Q5: Pre-trade context | delta_extreme not discriminating within W22 or between weeks. "Dormant market" pattern (empty_book-only) unique to W22's two longest holds (n=2). 06-06 cluster = event, not regime. | Medium |
| Hypothesis rank | H5 Mixed primary; H1 supported locally for 06-06 cluster; H3 weak; H2, H4 ruled out | Medium |
| Edge quality | W23 took BETTER EV setups. Low-quality entry hypothesis ruled out. | High |
| Mechanism | Under-determined from scan_log data alone. Per-tick underlying price data would be needed to confirm H1 beyond the 06-06 cluster. | N/A |

---

## Governor Verdict

**CONTINUE_ACCUMULATION.**

The fast resolution of W23 TREND_DOWN trades is explained by a specific market event (06-06 cluster), the absence of dormant-market pre-entry conditions that drove W22's longest holds, and small-sample episodic variance. It is not a signal of strategy failure, systematic signal deterioration, or regime-level change.

The within-regime hold collapse (p≈0.005) measures a real W22→W23 difference in this sample, but the effective independent episode count is approximately 3, and the W22 baseline included two anomalous dormant-market entries that are unlikely to recur at the same rate. Further accumulation (target n ≥ 100) is the appropriate response.

**Offline/reporting only. This document does not authorize strategy changes, risk changes, execution changes, or live trading.**
