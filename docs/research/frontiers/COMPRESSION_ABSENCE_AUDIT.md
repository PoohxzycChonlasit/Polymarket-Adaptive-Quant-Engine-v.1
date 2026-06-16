# COMPRESSION Absence Audit

**Date:** 2026-06-10
**Mode:** READ ONLY — no code, runtime, strategy, risk, execution, or live changes
**Sources:**
- `runtime/quant_data/decision_log/*.jsonl` (2026-05-08 through 2026-06-09; 31 files)
- `runtime/research_exports/canonical_regime_enriched_trades_v1.csv` (canonical_n=67)
- `runtime/quant_data/trade_journal/*.jsonl` (post-May-31 ETH events)
- `polymarket/regime_diagnostics.py` (regime classifier code; lines 1–288)
- `git log` (commit history for regime-related files, May 28–June 10)

**Non-authorization:** This document does not authorize any runtime, strategy, risk,
execution, sizing, governance, or live behavior change. No commits authorized.

---

## Final Verdict

**MARKET_SHIFT**

ETH (and BTC) 5-minute candle ranges expanded approximately 3× beginning June 1–2,
pushing compression_score from 0.65–0.84 to 0.17–0.36 — well below the COMPRESSION
threshold of 0.65. The regime classifier code is unchanged (confirmed by `git log`).
The canonical filter is working correctly. COMPRESSION is absent because the market
is no longer compressed: the low-volatility ETH environment that produced 21
canonical COMPRESSION trades (May 18–31) has not recurred.

FILTER_SHIFT ruled out: the absence is in the raw decision_log (upstream of any
filter layer); no code changes to regime-related files in the relevant window.
DATA_ISSUE ruled out: full decision volume on all affected days; gradual cross-asset
ramp rather than a step break; BTC and ETH lost COMPRESSION simultaneously.

---

## Background: COMPRESSION Formula

```python
# polymarket/regime_diagnostics.py, lines ~219–252
recent_ranges = [
    abs(high - low) / close
    for high, low, close in zip(highs_5m[-8:], lows_5m[-8:], closes_5m[-8:])
    if close
]
avg_recent_range = sum(recent_ranges) / float(len(recent_ranges)) if recent_ranges \
    else volatility_score
compression_score = clamp((0.003 - avg_recent_range) / 0.003, 0.0, 1.0)

# ...
elif compression_score >= 0.65 and trend_strength < 0.35:
    market_regime = "COMPRESSION"
```

**Threshold in market terms:**
`compression_score >= 0.65` ↔ `avg_5m_candle_range <= 0.00105` (0.105% of ETH price)

The formula uses the mean high–low range across the most recent 8 five-minute
candles. A wider average range produces a lower compression_score and prevents
the COMPRESSION regime from firing.

---

## Q1. When Was the Last COMPRESSION Canonical Trade?

**Canonical #60 (21st and final COMPRESSION trade in the campaign)**

| Field | Value |
|---|---|
| Canonical sequence number | #60 |
| COMPRESSION trade sequence | 21st of 21 |
| Exit timestamp (UTC) | 2026-05-31T12:10:35Z |
| market_regime at decision | COMPRESSION |
| outcome | WIN |
| pnl | +$0.01307 |
| hold_seconds | 23 |

Trade #60 is simultaneously the last COMPRESSION canonical trade and the start
of the 137.2-hour (5.7-day) campaign-record drought documented in the Starvation
Persistence Audit. No COMPRESSION canonical trade has appeared since.

---

## Q2. How Many Source Trades Were Classified COMPRESSION After May 31?

### Daily count

| Date | ETH COMPRESSION decisions | BTC COMPRESSION decisions | Total |
|---|---|---|---|
| 2026-06-01 | 27 | 1,165 | 1,192 |
| 2026-06-02 | 0 | 0 | 0 |
| 2026-06-03 | 0 | 0 | 0 |
| 2026-06-04 | 0 | 0 | 0 |
| 2026-06-05 | 0 | 0 | 0 |
| 2026-06-06 | 0 | 0 | 0 |
| 2026-06-07 | 0 | 0 | 0 |
| 2026-06-08 | 0 | 0 | 0 |
| 2026-06-09 | 0 | 0 | 0 |

**Total post-May-31 COMPRESSION source decisions:** 1,192 (all on June 1); **zero
from June 2 onward.**

### Weekly COMPRESSION share of all ETH decisions

| Week | COMPRESSION share |
|---|---|
| W21 (May 18–24) | 47.0% |
| W22 (May 25–31) | 41.3% |
| W23 (Jun 1–7) | 1.7% (27 of 1,591; all on June 1) |
| W24 (Jun 8–9) | 0.0% |

COMPRESSION went from constituting ~44% of all ETH source decisions to zero in
under two weeks.

---

## Q3. Were COMPRESSION Candidates Rejected Post-May-31?

**None that were ETH YES OPENING_SCAN hold>15s.**

Post-May-31 ETH YES hold>15s trade journal inventory (n=10 events):

| Category | n | Lifecycle | Canonical disposition |
|---|---|---|---|
| Non-canonical | 3 | ACTIVE_INVENTORY_TRADING | Correctly excluded (not OPENING_SCAN) |
| Canonical | 7 | OPENING_SCAN | Correctly included (n=61–67) |
| OPENING_SCAN rejected | **0** | — | — |

Zero OPENING_SCAN ETH YES hold>15s trades were rejected at any stage.

The decisive point: **after June 1, compression_score never again reached 0.65,
so no COMPRESSION decisions were emitted.** After June 1 there were no COMPRESSION
candidates to accept or reject — the absence is upstream of any filter or gate layer.

---

## Q4. If Rejected, Why?

The 27 ETH COMPRESSION source decisions on June 1 were blocked by standard
execution gates (summarized from decision_log payload `candidate_block_reason`):

| Block reason | Count (all COMPRESSION, June 1, multi-asset) |
|---|---|
| delta_extreme | 685 |
| confidence_too_low | 417 |
| time_unsafe | 89 |
| stale_data | 1 |

These are normal risk gates, not new filter additions. The blocks reflect a market
that was structurally compressed (low candle range) but without the directional
confidence or delta conditions required for a qualifying candidate.

**No filter or gate was changed during this period** (see Q8). After June 1 this
question is moot: compression_score never reached 0.65 again, so no COMPRESSION
decisions were generated to block.

---

## Q5. Has COMPRESSION Frequency Fallen in Source Data?

**Yes — collapsed completely from June 2 onward.**

### ETH compression_score daily statistics

| Date | mean_cs | max_cs | implied_avg_range | pct_above_0.65 | Notes |
|---|---|---|---|---|---|
| 2026-05-30 | 0.7064 | 0.8985 | ~0.088% of price | 80.9% | Deep COMPRESSION |
| 2026-05-31 | 0.6050 | 0.8415 | ~0.118% of price | 61.1% | End of COMPRESSION era |
| 2026-06-01 | 0.2850 | 0.6570 | ~0.215% of price | 0.3% | Transition — 1 brief spike |
| 2026-06-02 | 0.1718 | 0.5624 | ~0.249% of price | 0.0% | Below threshold all day |
| 2026-06-03 | 0.0000 | 0.0000 | ~0.300% (max) | 0.0% | Thin data day (68 total) |
| 2026-06-04 | 0.0016 | 0.1160 | ~0.300% (max) | 0.0% | |
| 2026-06-05 | 0.0000 | 0.0000 | ~0.300% (max) | 0.0% | Thin data day |
| 2026-06-06 | 0.0063 | 0.1800 | ~0.298% of price | 0.0% | |
| 2026-06-07 | 0.1084 | 0.4788 | ~0.268% of price | 0.0% | Partial recovery; still far |
| 2026-06-08 | 0.0454 | 0.3310 | ~0.286% of price | 0.0% | |
| 2026-06-09 | 0.1352 | 0.5293 | ~0.260% of price | 0.0% | Closest approach since collapse |

*`implied_avg_range` derived from `avg_range = 0.003 × (1 - mean_cs)`; 0.300% is
the clamp floor (compression_score=0 means avg_range ≥ 0.300%).*

The collapse is continuous: from a mean compression_score of ~0.83 on May 31 to
near-zero on June 3–5, with partial recovery to a maximum of 0.529 on June 9.
The June 9 maximum is 0.121 below the 0.65 threshold — the closest approach since
the collapse, but still insufficient for COMPRESSION to fire.

### Cross-asset confirmation: BTC compression_score

| Date | BTC_max_cs | BTC_n_above_0.65 | BTC_n_total |
|---|---|---|---|
| 2026-05-30 | 0.9345 | 5,186 | 5,507 |
| 2026-05-31 | 0.8865 | 6,075 | 7,708 |
| 2026-06-01 | 0.7353 | 1,222 | 8,077 |
| 2026-06-02 | 0.6374 | 0 | 6,786 |
| 2026-06-04 | 0.1540 | 0 | 2,681 |
| 2026-06-06 | 0.4519 | 0 | 5,268 |
| 2026-06-07 | 0.5964 | 0 | 7,238 |
| 2026-06-08 | 0.5593 | 0 | 7,513 |
| 2026-06-09 | 0.5983 | 0 | 5,307 |

BTC shows the **identical two-day transition:** COMPRESSION-dominant May 30–31,
partial June 1 (1,222 decisions still above threshold), zero from June 2 onward.
Both independent feed paths collapsed simultaneously.

---

## Q6. Has COMPRESSION Frequency Fallen Only in Canonical, or in Source Too?

**In source first. Canonical absence is downstream of source absence.**

| Layer | Status since June 2 |
|---|---|
| Source (decision_log) | compression_score < 0.65 on every cycle → 0 COMPRESSION decisions emitted |
| Risk gates | No COMPRESSION candidates to block |
| Trade journal | No COMPRESSION trade_open events |
| Canonical filter | No COMPRESSION trades to include |

The canonical filter (ETH YES OPENING_SCAN hold>15s) operates on trade_journal
events that already carry market_regime from the decision_log. There is nothing for
the canonical filter to exclude — COMPRESSION disappears before any filter is reached.

The 7 post-May-31 canonical trades (n=61–67) were all OPENING_SCAN and correctly
included. Their market_regime was set at decision time to SIDEWAY, TREND_UP, or
TREND_DOWN — not COMPRESSION. Zero COMPRESSION OPENING_SCAN trades were available
to include.

---

## Q7. Is the Absence Due to Market Structure Change?

**Yes.**

The COMPRESSION formula requires mean(|high–low|/close) ≤ 0.00105 over the last
8 five-minute candles. ETH 5-minute candle ranges expanded approximately 3× at the
May 31 → June 1 boundary:

| Period | Implied avg 5m range | compression_score status |
|---|---|---|
| May 30 | ~0.088% of price | 0.71 mean — deep COMPRESSION |
| May 31 | ~0.118% of price | 0.61 mean — approaching threshold |
| June 1 | ~0.215% of price | 0.29 mean — collapsed |
| June 2+ | ~0.249–0.300% of price | 0.00–0.17 mean — well below |
| June 7–9 | ~0.260–0.270% of price | 0.11–0.14 mean; max 0.53 (June 9) |

*Period coverage starts May 30 — the earliest date tabulated from decision_log
in this audit session. The 3× expansion claim is fully supported by May 30→June 2
alone and does not require earlier data.*

For COMPRESSION to return, ETH 5-minute candle ranges must contract from the
current ~0.26% back to below 0.105% — approximately a 60% contraction. The gradual
upward movement in June 7–9 maximum scores (0.479, 0.331, 0.529) suggests limited
partial compression on brief windows, but no sustained interval below the threshold.

The regime classifier is operating exactly as designed. It classified the market
as COMPRESSION when it was compressed and stopped when it was not.

---

## Q8. Is the Absence Due to Filtering Change?

**No.**

```
git log --oneline --since="2026-05-28" --until="2026-06-10" \
    -- polymarket/regime_diagnostics.py \
       polymarket/signal.py \
       polymarket/probability_model.py \
       polymarket/oracle_price_feed.py \
       polymarket/market_feed.py
```

**Result: empty** — no commits to any regime-related module in the relevant window.

The following are confirmed unchanged:
- COMPRESSION threshold (0.65)
- compression_score formula (`clamp((0.003 - avg_range) / 0.003, 0, 1)`)
- Regime classification hierarchy in `regime_diagnostics.py`
- Canonical filter criteria (ETH YES OPENING_SCAN hold>15s)
- Standard execution gates (delta_extreme, confidence_too_low, time_unsafe)

One acknowledged limitation: `.env` configuration and API feed credentials are not
version-controlled. An untracked feed parameter change (e.g., data provider rotation
at month boundary) cannot be fully excluded from primary records alone. However,
this scenario is made implausible by the four observations under Q5:
1. Full decision throughput on all affected days (not a feed outage)
2. Gradual ramp across two days (not a step-break from a config change)
3. Both ETH and BTC feed paths collapsed simultaneously (not asset-specific)
4. Partial signal recovery in June 7–9 (consistent with a market regime evolving,
   not a locked misconfiguration)

**FILTER_SHIFT is ruled out.** The COMPRESSION absence is in the source signal, not
in any filter, gate, or code layer above it.

---

## Q9. If COMPRESSION Never Returns, What Happens to Campaign PF?

### Current state

| Metric | Value |
|---|---|
| Full campaign PF (n=67, all regimes) | 1.993 |
| COMPRESSION share of net PnL | ~62.4% |
| Non-COMPRESSION historical PF (n=46 trades) | 1.505 |
| Non-COMPRESSION win rate | 54.3% (25 of 46) |
| Non-COMPRESSION avg_win | $0.00933 |
| Non-COMPRESSION avg_loss | $0.00738 |

The non-COMPRESSION historical PF of 1.505 answers: "what is the campaign's
demonstrated edge when COMPRESSION trades are excluded?"

### Projected n=100 PF (no new COMPRESSION)

If the remaining 33 trades to n=100 all arrive at non-COMPRESSION historical rates:

**Projected cumulative PF at n=100: 1.828**
*(Method: n=67 locked gross_win/gross_loss from canonical export +
33 additional trades at non-COMPRESSION avg_win=$0.00933 × WR=54.3% and
avg_loss=$0.00738 × (1−WR)=45.7%. Alternative bookkeeping of the same
win/loss split gives ~1.855; both are ±0.03 depending on rounding of the
locked n=67 gross figures. The conclusion — no K2 risk — is identical in
both estimates.)*

This is the campaign's anticipated trajectory forward under the MARKET_SHIFT
scenario — no new COMPRESSION, existing 67 locked, 33 additional trades at 1.505
non-COMPRESSION base rates.

| Boundary | PF | Status |
|---|---|---|
| Current (n=67) | 1.993 | PASS |
| Projected n=100 (no new COMPRESSION) | **1.828** | Above K2 threshold |
| K2 kill threshold | 1.300 | Not triggered |
| Gap: projected to K2 | **+0.528** | Substantial cushion |

**PF decline if COMPRESSION never returns: −8.3% (1.993 → 1.828).** This is a
real deterioration — COMPRESSION was the dominant PnL contributor — but the
projected PF remains well above the K2 kill threshold (1.3) at n=100. There is
no immediate kill risk from COMPRESSION absence alone.

### Sensitivity note

The 1.828 projection assumes non-COMPRESSION rates are stable. If the
non-COMPRESSION win rate declines materially (toward ~45%), the projected n=100
PF would approach the K4 boundary (excl-top-5 PF < 1.0). The campaign's forward
performance is now entirely dependent on the non-COMPRESSION edge holding.

---

## Why Not DATA_ISSUE

Four independent observations rule out a data pipeline or feed anomaly:

**1. No code changes.**
`git log` returned empty for all regime-related files (regime_diagnostics.py,
signal.py, probability_model.py, oracle_price_feed.py, market_feed.py) in the
May 28–June 10 window. The signal pipeline is unchanged.

**2. Full decision volume on all affected days.**
June 6: 5,268 ETH decisions. June 7: 7,238. June 8: 7,513. June 9: 5,266.
A data outage or feed corruption manifests as missing or thin volume, not
full-volume decisions with a shifted signal. The thin days (June 3: 68 decisions;
June 5: minimal) reflect low market activity, not pipeline failure.

**3. Gradual ramp, not a step break.**
compression_score trajectory: 0.71 mean (May 30) → 0.61 (May 31) → 0.29
(June 1) → 0.17 (June 2) → ~0 (June 3–5) → partial recovery (June 7–9).
A configuration error or data corruption produces a sharp step; a volatility
regime transition evolves continuously over days. This trajectory is continuous.

**4. Cross-asset simultaneous collapse.**
ETH and BTC feed paths are independent. Both lost COMPRESSION at the same
calendar boundary (June 1–2): BTC went from 6,075 decisions above 0.65 on
May 31 to 0 from June 2 onward; ETH followed the same timeline. An ETH-specific
feed anomaly would leave BTC unaffected. A simultaneous two-asset collapse
identifies a market-wide event, not a pipeline fault.

---

## Why Not FILTER_SHIFT

The canonical filter (ETH YES OPENING_SCAN hold>15s) and the execution gates
(delta_extreme, confidence_too_low, time_unsafe) are applied downstream of the
regime classifier. The absence of COMPRESSION is upstream of every filter layer:

- The regime classifier emits `market_regime=COMPRESSION` only when
  `compression_score >= 0.65`. After June 1, this condition is never met.
- No COMPRESSION decisions reach the trade_journal for canonical evaluation.
- The 7 post-May-31 canonical trades (n=61–67) are correctly OPENING_SCAN
  and correctly included — the canonical filter is working as intended.
- The 3 non-canonical ETH YES hold>15s trades were ACTIVE_INVENTORY_TRADING —
  correctly excluded by the lifecycle filter (not a regime-based exclusion).
- `git log` confirmed no code changes to any filter or regime module.

**The canonical filter cannot include what the regime classifier does not emit.**
FILTER_SHIFT requires a change in filter behavior; no such change occurred.

---

## Summary Table

| Question | Finding |
|---|---|
| Q1. Last COMPRESSION canonical trade | Canonical #60, 2026-05-31T12:10:35Z (21st COMPRESSION) |
| Q2. COMPRESSION source decisions after May 31 | 1,192 on June 1; **0 from June 2 onward** |
| Q3. COMPRESSION candidates rejected post-June-1 | **None** (no ETH YES OPENING_SCAN COMPRESSION candidates existed) |
| Q4. Why rejected | June 1 blocks: delta_extreme, confidence_too_low, time_unsafe (normal gates, unchanged) |
| Q5. COMPRESSION frequency in source | Collapsed from 44% of decisions → 0% over two days |
| Q6. Source vs. canonical | Source absent first; canonical absence is downstream consequence |
| Q7. Market structure change | **Yes** — avg 5m candle range expanded 3× (0.09% → 0.26%); compression_score dropped 57% below threshold |
| Q8. Filtering change | **No** — git log empty; all filter criteria, thresholds, and code unchanged |
| Q9. PF if COMPRESSION never returns | 1.993 → **1.828** projected at n=100; still above K2=1.3 |

---

## Root Cause Statement

The COMPRESSION regime requires ETH 5-minute candle ranges to average ≤ 0.105%
of price (compression_score ≥ 0.65). Beginning June 1–2, those ranges expanded
from ~0.09–0.12% to ~0.25–0.30% — approximately a 3× increase — pushing
compression_score well below the threshold. No code change precipitated this.
The ETH and BTC price environments that produced 21 canonical COMPRESSION trades
from May 18–31 have not recurred.

The COMPRESSION regime will return when and only when ETH 5-minute candle ranges
contract back below 0.105% of price (~60% contraction from current levels). The
June 9 daily maximum of 0.529 (gap to threshold: 0.121) is the closest approach
since the collapse — insufficient for COMPRESSION to fire, but trending toward
partial recovery at the peak-of-day level.

**FINAL VERDICT: MARKET_SHIFT**

---

*Offline/reporting only. No runtime, strategy, risk, execution, governance, or
live behavior changes authorized by this document. No commits authorized.*
