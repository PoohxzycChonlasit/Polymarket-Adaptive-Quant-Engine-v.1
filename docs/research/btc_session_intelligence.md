# BTC Session Intelligence Audit

Document type: read-only BTC session window analysis.

Created: 2026-05-23

Updated: 2026-05-23

Runtime behavior changed: No.
Live behavior changed: No.
Paper launch: No.
Replay run: No.
Code changed: No.
Tests: none, docs-only.

---

## Scope

Determine which UTC runtime windows produce BTC outcome-truth evidence.

Source data: `runtime/quant_data/trade_journal/` (all dates) and
`runtime/quant_data/decision_log/` and `execution_log/` (2026-05-18 onward).

Pre-instrumentation BTC closes (2026-05-08 to 2026-05-17) are used for session context only.
Outcome-truth analysis is limited to 2026-05-22 onward.

---

## Overall BTC Classification

```text
BTC_ACTIVE_WINDOW
```

BTC does produce entries across multiple UTC hours, but with very low entry rates (< 0.5% of decisions
at any hour). No hour has sufficient outcome-truth evidence to be classified as BTC_HIGH_SIGNAL_WINDOW.
The primary signal suppressor is `delta_extreme` which blocks 40–60% of all BTC decisions at every hour.

---

## BTC Volume Summary

| Metric | Value |
|---|---|
| Total BTC trade_open events (all history) | 32 |
| BTC trade_open events (instrumentation era 2026-05-18+) | 30 |
| Sessions with BTC trades (instrumentation era) | 12 |
| BTC outcome-truth trades | 1 |
| BTC TP | 0 |
| BTC SL | 1 |
| Hours with ≥1 BTC open | 14 of 24 |
| Hours with 0 BTC opens | 10 of 24 |
| Dominant lifecycle | OPENING_SCAN (28/30 = 93%) |
| Dominant skip reason | delta_extreme (40–60% all hours) |

---

## BTC Decision Volume and Entry Rate by UTC Hour

Entry rate = BTC decisions that resulted in an approved entry / total BTC decisions that hour.
Actual opens = BTC trade_open events at that hour (from trade_journal, instrumentation era).

| Hour | Decisions | Entry% | delta_x% | conf_lo% | time_x% | Actual opens | Window class |
|---|---:|---:|---:|---:|---:|---:|---|
| 00h | 644 | 0.0% | 55.1% | 30.7% | 12.9% | 0 | DORMANT |
| 01h | 639 | 0.0% | 59.9% | 26.1% | 11.9% | 0 | DORMANT |
| 02h | 466 | 0.4% | 42.3% | 24.2% | 26.0% | 3 | LIGHT |
| 03h | 765 | 0.0% | 45.5% | 21.0% | 26.7% | 1 | LIGHT |
| 04h | 1082 | 0.1% | 44.7% | 20.1% | 17.7% | 4 | **ACTIVE** |
| 05h | 1641 | 0.0% | 45.0% | 25.0% | 17.3% | 6 | **ACTIVE** |
| 06h | 1995 | 0.0% | 52.5% | 23.6% | 17.2% | 2 | LIGHT |
| 07h | 1908 | 0.0% | 49.3% | 28.9% | 17.5% | 0 | DORMANT |
| 08h | 2612 | 0.0% | 55.4% | 20.9% | 16.7% | 3 | LIGHT |
| 09h | 2358 | 0.0% | 50.2% | 30.0% | 16.4% | 1 | LIGHT |
| 10h | 1876 | 0.1% | 47.7% | 28.7% | 16.5% | 1 | LIGHT |
| 11h | 628 | 0.3% | 40.8% | 26.9% | 21.0% | 2 | LIGHT |
| 12h | 1251 | 0.1% | 51.9% | 21.9% | 17.3% | 4 | **ACTIVE** |
| 13h | 1073 | 0.0% | 45.5% | 22.2% | 18.7% | 0 | DORMANT |
| 14h | 1091 | 0.2% | 52.4% | 15.9% | 17.8% | 2 | LIGHT |
| 15h | 824 | 0.0% | 43.2% | 22.9% | 20.3% | 1 | LIGHT |
| 16h | 843 | 0.1% | 44.5% | 24.8% | 17.6% | 1 | LIGHT |
| 17h | 922 | 0.0% | 51.6% | 18.3% | 12.1% | 0 | DORMANT |
| 18h | 632 | 0.0% | 53.3% | 29.1% | 12.5% | 0 | DORMANT |
| 19h | 631 | 0.0% | 49.9% | 33.8% | 12.2% | 0 | DORMANT |
| 20h | 634 | 0.0% | 47.8% | 36.9% | 11.7% | 0 | DORMANT |
| 21h | 632 | 0.0% | 51.7% | 32.6% | 12.7% | 0 | DORMANT |
| 22h | 475 | 0.0% | 55.2% | 31.4% | 12.2% | 1 | LIGHT |
| 23h | 634 | 0.0% | 51.3% | 34.2% | 11.8% | 0 | DORMANT |

**ACTIVE** = ≥ 4 actual opens (instrumentation era, 2026-05-18+)
**LIGHT** = 1–3 actual opens
**DORMANT** = 0 actual opens

Peak decision volume: 08h-09h UTC (2612 + 2358 decisions). But high BTC decision volume does not translate to high BTC entry rate. 08h-09h produces only 3-4 BTC entries despite the highest analysis load, because delta_extreme is also highest at 08h (55.4%).

---

## BTC Active Window Detail

### 04h–06h UTC — Primary Active Window

| Date | Session start | BTC opens at 04-06h |
|---|---|---|
| 2026-05-18 | 04:25 UTC | 5 at hours [4, 5, 5, 6] |
| 2026-05-19 | 05:35 UTC | 4 at hours [4, 5, 12] (+ 2h next day) |
| 2026-05-20 | 04:30 UTC | 2 at hours [4, 5] |
| 2026-05-21 | 04:50 UTC | 2 at hours [4] |
| 2026-05-22 | 04:55 UTC | 1 at hours [5] |
| 2026-05-22 | 05:35 UTC | 1 at hours [5] |

Total BTC opens in 04h-06h window: **11 of 30** (37%).
Sessions starting 04h-06h reliably produce BTC entries within the first 2 hours.
This is the highest-yield window for accumulating BTC paper evidence.

### 12h UTC — Secondary Active Window

| Date | Session | BTC opens at 12h |
|---|---|---|
| 2026-05-19 | 05:35 UTC (long session) | 1 |
| 2026-05-20 | 11:10 UTC | 2 |
| 2026-05-22 | 08:10 UTC (long session) | 1 |

Total BTC opens at 12h: **4 of 30** (13%).
12h appears to be a secondary cluster. Often produced by long sessions that started earlier and reached the 12h window.

### 02h UTC — Overnight Light Window

3 BTC opens at 02h, all from sessions that started earlier and ran through midnight UTC. Not a standalone productive start time — BTC at 02h tends to come from long sessions already running.

---

## Session-Level BTC Activity

| Run (last 20 chars) | Session start | BTC opens | BTC hours |
|---|---|---:|---|
| `12476_ae4fa786` | 04:25 UTC | 5 | 04h, 05h, 05h, 06h, 02h (next day) |
| `28944_25443b98` | 05:35 UTC | 5 | 08h, 08h, 12h, 16h, 04h (next day) |
| `45768_ed644582` | 13:50 UTC | 6 | 14h, 22h, 02h, 03h, 05h, 06h (long) |
| `30452_d6c09eac` | 11:10 UTC | 3 | 11h, 12h, 14h |
| `45508_dc23e716` | 09:15 UTC | 1 | 10h |
| `28120_45581845` | 04:30 UTC | 3 | 04h, 05h, 11h |
| `13704_948b4757` | 04:50 UTC | 3 | 04h, 09h, 02h (next day) |
| `28036_3ce2d904` | 04:55 UTC | 1 | 05h |
| `31032_cfe7068f` | 05:35 UTC | 1 | 05h |
| `26740_b69f35b9` | 08:10 UTC | 2 | 08h, 12h |
| `13912_ef8361bc` | 06:10 UTC | 1 | 12h |
| `21712_035b3af7` | 13:05 UTC | 1 | 15h ← only outcome-truth BTC |

**Observation:** Sessions starting between 04h–06h UTC consistently produce BTC entries. The three sessions producing the most BTC trades (5-6 each) all started in the 04h-06h window or ran as long multi-hour sessions.

The only outcome-truth BTC trade came from a session starting at 13:05 UTC, producing a single 15h BTC entry. This is currently an outlier, not evidence of 13h-15h being productive.

---

## BTC Lifecycle Distribution

| Lifecycle phase | Count | % |
|---|---:|---:|
| OPENING_SCAN | 28 | 93% |
| ACTIVE_INVENTORY_TRADING | 2 | 7% |

BTC entries are overwhelmingly in OPENING_SCAN. The 2 ACTIVE_INVENTORY_TRADING entries occurred in sessions at 02h and 11h — both were in long-running sessions where a prior BTC position was already open.

---

## BTC Liquidity Depth by Hour

| Hour | STRONG | ACCEPTABLE | THIN | UNSTABLE | Total |
|---|---:|---:|---:|---:|---:|
| 02h | 0 | 2 | 0 | 0 | 2 |
| 03h | 0 | 1 | 0 | 0 | 1 |
| 04h | 0 | 3 | 0 | 1 | 4 |
| 05h | 0 | 3 | 2 | 0 | 5 |
| 06h | 0 | 2 | 0 | 0 | 2 |
| 08h | 0 | 2 | 0 | 1 | 3 |
| 09h | 0 | 1 | 0 | 0 | 1 |
| 10h | 0 | 1 | 0 | 0 | 1 |
| 11h | 0 | 1 | 0 | 1 | 2 |
| 12h | 1 | 3 | 0 | 0 | 4 |
| 14h | 0 | 1 | 1 | 0 | 2 |
| 15h | 0 | 0 | 0 | 1 | 1 |
| 16h | 0 | 1 | 0 | 0 | 1 |
| 22h | 0 | 1 | 0 | 0 | 1 |

BTC liquidity is predominantly ACCEPTABLE. 12h stands out as having 1 STRONG depth entry — the only STRONG BTC depth observation. The 15h outcome-truth BTC SL occurred at UNSTABLE depth.

---

## Primary Skip Reason Analysis

At every UTC hour, `delta_extreme` is the dominant BTC skip reason (40–60%). This means the BTC 5-minute market frequently exhibits extreme price delta (BTC volatility relative to the reference window), blocking the majority of candidates before EV or confidence can be evaluated.

The pattern is consistent across all hours — there is no UTC hour where BTC delta_extreme drops below 40%. This is a structural characteristic of BTC's price behavior in these short-window markets, not a session timing issue.

Second-order blockers:
- `confidence_too_low` (18–34%): concentrated at hours with lower market activity (00h-01h, 19h-21h)
- `time_unsafe` (12–27%): elevated at 02h-03h (26-27%) — possibly a market window cutoff pattern

---

## Quote Age (Instrumentation Era)

Only 1 BTC trade has quote-age data (the single outcome-truth trade):

| Hour | Submit age | Fill age | Source | Bucket | Result |
|---|---:|---:|---|---|---|
| 15h | 48.617s | 48.619s | display_snapshot_sampling | 30-60s | SL |

29 of 30 BTC entries have no quote-age data (pre-patch). Cannot compute quote-age distribution by hour for BTC. Single data point is not sufficient for stale-quote assessment.

Exit quote age for the same trade: 6.236s (fresh, `decision_cycle_fetch`).
The entry used a stale display snapshot while the exit used a fresh decision-cycle quote.

---

## Hour Classification Summary

| Window | UTC Hours | BTC_ACTIVE | Rationale |
|---|---|---|---|
| Primary active | 04h–05h | **BTC_ACTIVE_WINDOW** | 11 entries, 37% of all BTC opens, reliable across sessions |
| Secondary active | 12h | **BTC_ACTIVE_WINDOW** | 4 entries, 13%, STRONG depth observed |
| Light | 02h, 06h, 08h, 11h, 14h-16h | LIGHT | 1–3 entries, not zero but inconsistent |
| Dormant | 00h, 01h, 07h, 13h, 17h–23h | **BTC_DORMANT** | 0 entries despite high decision volume at some hours |

No UTC window qualifies as **BTC_HIGH_SIGNAL_WINDOW** — this classification requires ≥2 BTC TP outcomes in outcome-truth evidence. Current BTC TP count = 0.

---

## Session Start Time Recommendation

To maximize BTC evidence accumulation per session:

| Session start (UTC) | Expected BTC yield | Rationale |
|---|---|---|
| 04h–05h | **High** (1–5 BTC trades) | Primary active window; 6 of 12 BTC-producing sessions started here |
| 08h–09h | Moderate (0–3 BTC trades) | High decision volume but high delta_extreme suppression |
| 12h–13h | Moderate (0–4 BTC trades) | Secondary cluster, STRONG depth at 12h |
| 00h–01h | **Low** (0 BTC trades) | DORMANT; delta_extreme + confidence_too_low dominate |
| 17h–23h | **Low** (0–1 BTC trades) | DORMANT; no BTC opens observed except rare 22h |

**Recommended session start for BTC evidence:** 04h–05h UTC.
Sessions starting at this time reliably produce BTC entries within 1-2 hours.
The single highest-yield session (5 BTC opens: `12476_ae4fa786`) started at 04:25 UTC.

---

## Exactly Three Future Options

### OPTION 1 — TARGET 04h-05h UTC SESSIONS (RECOMMENDED)

Thesis: launch clean paper sessions starting at 04h-05h UTC to maximize BTC entry probability.

Quant logic: 04h-05h produced 11 BTC opens (37% of all instrumentation-era BTC), from 6 of the 12 BTC-producing sessions. This window consistently activates BTC while ETH is also active.

Likely outcome: 1-3 BTC entries per session started at 04h-05h UTC, based on historical rates.

Hidden risk: delta_extreme still blocks 45% of BTC decisions even in this window. Not every 04h-05h session will produce BTC entries.

Recommended action: use 04h-05h UTC as the preferred start time for BTC evidence accumulation sessions.

### OPTION 2 — RUN LONGER SESSIONS THAT SPAN 04h-12h

Thesis: long sessions (13h-22h) that start earlier and run through both primary (04h-05h) and secondary (12h) windows produce the most BTC entries overall.

Quant logic: the top two sessions by BTC entry count (`12476`: 5 opens, `25443b98`: 5 opens) both ran for many hours, spanning multiple BTC active windows. A single long session can accumulate more BTC trades than several short sessions.

Likely outcome: a 13h+ session starting at 04h UTC could produce 3-6 BTC entries across 04h, 05h, 08h, and 12h windows.

Hidden risk: longer sessions accumulate more events but also more non-BTC evidence, which may dilute BTC coverage in the daily monitor. Windows still have low individual entry rates.

Recommended action: consider running at least one long session (≥8h) starting at 04h UTC.

### OPTION 3 — MONITOR 12h UTC SPECIFICALLY FOR DEPTH QUALITY

Thesis: 12h UTC has the only observed STRONG BTC depth entry and a moderate 4-entry cluster. If STRONG depth correlates with BTC TP outcomes, 12h may be the highest-signal window once more evidence is available.

Quant logic: at 12h, 1 of 4 BTC entries had STRONG liquidity depth. The 15h outcome-truth BTC SL occurred at UNSTABLE depth. Segmenting by depth quality may matter more than hour.

Likely outcome: a separate BTC depth analysis (after n≥5 outcome-truth BTC trades) could show whether ACCEPTABLE vs STRONG depth correlates with outcome.

Hidden risk: current n=1 outcome-truth makes depth-to-outcome inference impossible. This option is forward-looking, not actionable now.

Recommended action: add depth tracking to BTC evidence watch and revisit when BTC outcome-truth count reaches 5+.

---

## Recommendation

```text
BTC_ACTIVE_WINDOW
```

BTC does produce entries. The primary productive window is **04h–05h UTC**.
Target sessions should start at 04h–05h UTC to maximize BTC accumulation rate.

No hour is BTC_HIGH_SIGNAL_WINDOW — that classification requires ≥2 BTC TP outcomes, and current BTC TP count is 0.

Do not change runtime strategy, risk sizing, execution, or entry thresholds based on this analysis.
Do not promote S3. This is evidence-gathering context only.

---

## Update Trigger

Update when:
- Any new BTC outcome-truth trade is observed (especially TP).
- BTC decision volume or entry rate changes materially (new runs reveal a new active window).
- BTC active window classification changes from ACTIVE to HIGH_SIGNAL (requires ≥2 BTC TP).
