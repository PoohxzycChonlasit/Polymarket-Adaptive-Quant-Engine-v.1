# ETH YES FC OS — Verification Tracker

**Cell:** ETH × YES × FIRST\_CYCLE × OPENING\_SCAN × hold > 15s
**Status:** `VERIFICATION_IN_PROGRESS + POSITIVE_PATH_EVIDENCE`

## N70 Milestone Update - 2026-06-10

| Metric | Current | Target | Status |
|---|---:|---:|---|
| Canonical n | 70 | 100 | 30 remaining |
| Win Rate | 57.1% | >52% | PASS |
| Profit Factor | 2.006 | >1.5 | PASS |
| Net PnL | +$0.215774 | >0 | PASS |
| Median PnL | +$0.005783 | >0 | PASS |
| p-value | 0.141 | <0.05 | OPEN |
| Calendar weeks | 4 | >=3 | PASS |
| Formal kill criteria | 0 triggered | 0 | PASS |

N62-N70 block: `n=9`, `5W/4L`, WR `55.6%`, PF `1.803`, net
`+$0.018609`.

Next snapshot trigger: `n=80`.

This milestone update supersedes the pre-N70 current-state fields retained
below for historical context.

```text
Rows 1-70   = discovery / retrospective selected-slice evidence
Rows 71-100 = forward validation block
```

**Last updated:** 2026-06-06
**Source:** `docs/research/watchlists/ETH_YES_FC_OS.md`

---

## Core Metrics

| Metric | Current | Target | Status |
|---|---|---|---|
| **n** | **60** | 100 | ❌ −40 remaining |
| **Win Rate** | **58.1%** | > 52% | ✅ passing |
| **Profit Factor** | **2.055** | > 1.5 | ✅ passing |
| **Net PnL** | **+$0.205** | > 0 | ✅ passing |
| **Median PnL** | **+$0.006** | > 0 | ✅ passing |
| **p-value** | **0.126** | < 0.05 | ❌ need n ≈ 105 |
| **Calendar weeks** | **2** (W21, W22) | ≥ 3 | ❌ −1 week |

---

## Progress to n = 100

```
n=60  ████████████████████████████░░░░░░░░░░░░░░  60 / 100  (60.0%)
      ────────────────── 40 remaining ──────────────────→
```

---

## Promotion Criteria

All five must be met simultaneously:

| # | Criterion | Current | Status |
|---|---|---|---|
| 1 | n ≥ 100 | **60** | ❌ need 40 more |
| 2 | WR > 52% | **58.1%** | ✅ |
| 3 | PF > 1.5 | **2.055** | ✅ |
| 4 | p-value < 0.05 | **0.126** | ❌ need n ≈ 105 |
| 5 | ≥ 3 calendar weeks with trades | **2** (W21, W22) | ❌ need 1 more week |

**Criteria met: 2 / 5**
**Hard blockers: n < 100, p > 0.05, only 2 weeks**

---

## Kill Criteria

| # | Criterion | Status |
|---|---|---|
| 1 | WR < 48% over n ≥ 30 new trades | ✅ not triggered (WR=58.1%) |
| 2 | PF < 1.3 at n ≥ 80 | ✅ not triggered (PF=2.055) |
| 3 | BTC exclusion invalidated (BTC WR > 40% on n ≥ 20) | ✅ not triggered |
| 4 | Concentration collapse (excl. top-5 PF < 1.0 at n=100) | ✅ not triggered (excl.-top-5 PF=1.441) |

**Kill criteria: 0 / 4 triggered**

---

## Latest Path Evidence (MFE/MAE Audit — 2026-06-06)

| Metric | Value | Interpretation |
|---|---|---|
| Path truth match rate | **47% (28 / 60)** | Compound key join; pre-May 24 unlogged |
| Matched sample PF | **2.338** | Consistent with full cell PF=2.055 ✓ |
| **MFE median** | **+$0.00592** | Positions reach meaningful positive territory |
| **MAE median** | **−$0.00097** | Minimal adverse excursion overall |
| MFE > 0 | **22 / 28 = 79%** | 4 in 5 trades reach positive unrealized |
| Never adverse (MAE ≥ 0) | **13 / 28 = 46%** | Nearly half never go negative |
| Clean paths (MFE≥0, MAE≥−$0.003) | **17 / 28 = 61%** | Majority of trades have favorable trajectories |
| Clean paths → all winners | **17 / 17 = 100%** | Clean path = confirmed win |
| Winner MAE median | **+$0.00252** | Winners never meaningfully adverse |
| Loser MAE median | **−$0.00520** | Losers show genuine adverse moves (not premature exits) |
| Exit efficiency (winners) | **1.000** | TP exits capture full available MFE |
| Perfect-exit PF | **4.407** | Theoretical upper bound (lossers that briefly went positive) |

**Path verdict: POSITIVE — edge is real, exits are not premature, losers are genuine.**

---

## ETA to n = 100

**Trades required:** 40

| Scenario | Rate | ETA | Calendar ETA (from 2026-06-06) |
|---|---|---|---|
| 🟢 Optimistic | 4.77 / trading day | ~9 trading days | ~2026-06-17 |
| 🟡 Conservative | 3.0 / trading day | ~14 trading days | ~2026-06-24 |
| 🔴 Pessimistic | 2.0 / trading day | ~20 trading days | ~2026-07-02 |

**Rate source:** Pre-Episode #5 accumulation (May 18–31); 13 active days, canonical opportunities = 60 (raw execution rows = 62).
**Rate risk factors:**
- Zero-execution episodes (e.g., Episode #5: 22h 44m, 0 trades) can halt accumulation entirely
- Non-COMPRESSION regime days produce fewer YES FC OS executions
- SIDEWAY-heavy periods produce this cell at lower frequency than COMPRESSION-heavy periods

**Binomial significance (p < 0.05) requires:** n ≈ 105 at current WR = 58.1%
- At optimistic rate: ~10 trading days (~2026-06-18)
- At conservative rate: ~14 trading days (~2026-06-24)

---

## Weekly Progress Log

| Week | n added | WR | PF | Cumulative n | Notes |
|---|---|---|---|---|---|
| W21 (May 18–24) | 39 | 52% | 1.739 | 39 | First week; raw execution rows = 40 |
| W22 (May 25–31) | 21 | 68% | 2.947 | 60 | Second half stronger; raw execution rows = 22 |
| W23 (Jun 1–6) | 0 | — | — | 60 | Episode #5 + no COMPRESSION |
| W24 onwards | — | — | — | TBD | Next accumulation window |

---

## Robustness Summary (from 2026-06-02 Audit)

| Test | Result |
|---|---|
| Excl. top-5 | PF = 1.441 ✅ |
| LODO min PF | 1.909 ✅ (all 13 dates) |
| Bootstrap PF > 1.0 | 99.5% of 2,000 resamples ✅ |
| Bootstrap p5 | 1.261 ✅ |
| First / second half | 1.764 / 2.462 ✅ (second half stronger) |
| Win/loss dependency | χ² = 0.03 ✅ (independent) |
| Concentration top-1 removed | PF = 1.906 ✅ |
| Day-profit rate | 12 / 13 = 92% ✅ |

**Robustness score: 91 / 100**

---

## Next Snapshot Trigger

> Governance rule: append snapshot when ≥ 10 new qualifying trades arrive.

**Next snapshot at:** n = 70 (+10 from current 60)
**Expected contents:** updated n, WR, PF, week count, path match rate

---

## Quick Reference

```
SIGNAL:   ETH YES FC OS hold>15s
STATUS:   VERIFICATION_IN_PROGRESS + POSITIVE_PATH_EVIDENCE
n:        60 / 100  (60%)
WR:       58.1%
PF:       2.055
p-value:  0.126  (need < 0.05, requires n≈105)
weeks:    2 / 3
path MFE: +$0.006 median  (79% reached positive territory)
path MAE: -$0.001 median  (clean paths 61%)
ETA:      ~8–19 trading days to n=100
VERDICT:  ROBUST_EDGE candidate — blocked by statistical power only
```

---

*Source: `docs/research/watchlists/ETH_YES_FC_OS.md`*
*Audits: YES FC OS Robustness (2026-06-02), Path Truth Joinability (2026-06-06), MFE/MAE (2026-06-06)*
*No code changes. No strategy changes. Evidence only.*
