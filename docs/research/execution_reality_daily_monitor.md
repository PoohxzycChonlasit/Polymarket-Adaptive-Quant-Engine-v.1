# Execution Reality Daily Harvest Monitor v1

Document type: read-only daily execution reality tracker.

Updated: 2026-05-22

Runtime behavior changed: No.

Live behavior changed: No.

Paper launch: No.

Replay run: No.

Code changed: No.

Tests: none, docs-only.

---

## Scope

Track instrumentation-era execution reality only:

```text
date >= 2026-05-22
```

Daily rows use confirmed outcome-truth fields where available:

- `trade_result`
- `pnl_usdc`
- `quote_age_at_submit_ms`
- `quote_age_at_fill_ms`
- `quote_lineage_id`

Pre-instrumentation and pre-outcome-truth events are excluded from TP/SL/WIN/LOSS/PnL gate counts.

---

## Inclusion Policy

A run is eligible for the daily outcome table when:

- `paper_fill` events have non-null `quote_age_at_fill_ms`.
- `order_submit_attempt` events have non-null `quote_age_at_submit_ms`.
- `quote_lineage_id` is present on fills.
- `paper_trade_replay_key` is present on fills.
- `model_output_ready=True` on fills.
- `market_analysis_exception` count is 0.
- `trade_close` events have non-null `trade_result`, `pnl_usdc`, and `entry_price`.

---

## Instrumentation-Era Run Ledger

| Date | Run ID | Phase 5 fills | Outcome-truth closes | Assets | Included in daily outcome table | Note |
|---|---|---:|---:|---|---|---|
| 2026-05-22 | `20260522T082440Z_32952_1b709e78` | 6 | 0 | ETH | No | Phase 5 quote-age clean, pre-outcome-truth |
| 2026-05-22 | `20260522T094222Z_46088_040fac20` | 10 | 5 | ETH | Yes | Clean outcome-truth run |
| 2026-05-22 | `20260522T130017Z_21712_035b3af7` | 8 | 4 | BTC, ETH | Yes | Clean outcome-truth run |

---

## Daily Execution Reality Table

Current JSONL aggregation from clean outcome-truth runs:

| Date | Paired trades | BTC | ETH | TP | SL | WIN | LOSS | Mean PnL | Mean submit quote age | Mean fill quote age | Quote lineage IDs | 60s+ fills | Phase 6 readiness |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-05-22 | 9 | 1 | 8 | 3 | 6 | 3 | 6 | -0.005455 | 18.987s | 18.990s | 18 | 1 | 65.0% |

Readiness percent is the capped average of these five gates:

```text
paired / 20
BTC / 5
TP / 5
SL / 5
60s+ / 1
```

---

## Daily Delta

Delta is measured from the prior accepted Phase 6 gate baseline to the current raw clean-run aggregation.

| Field | Previous | Current | Delta |
|---|---:|---:|---:|
| Paired trades | 8 | 9 | +1 |
| BTC trades | 0 | 1 | +1 |
| TP outcomes | 3 | 3 | 0 |
| Phase 6 readiness | 60.0% | 65.0% | +5.0 pp |

Status:

```text
ACCUMULATING
```

## Gate Progress

```text
paired 9/20 [#########-----------]
BTC    1/5  [####----------------]
TP     3/5  [############--------]
SL     6/5  [####################] capped
60s+   1/1  [####################] capped
```

---

## Trend Layer

Trend layer uses the prior accepted Phase 6 gate baseline as the previous point and the current raw clean-run aggregation as the current point.

| Date | Paired trades | BTC | ETH | TP | SL | Readiness | Mean fill quote age | Mean PnL | 60s+ count | Daily delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-05-22 | 9 | 1 | 8 | 3 | 6 | 65.0% | 18.990s | -0.005455 | 1 | paired +1, BTC +1, TP 0, readiness +5.0 pp |

Rolling trend:

| Metric | Previous | Current | Trend |
|---|---:|---:|---|
| Paired trades | 8 | 9 | UP |
| BTC trades | 0 | 1 | UP |
| TP outcomes | 3 | 3 | FLAT |
| Readiness | 60.0% | 65.0% | UP |

Readiness ETA if current accumulation speed continues:

| Gate | Current | Target | Current speed | ETA |
|---|---:|---:|---:|---|
| Paired trades | 9 | 20 | +1 per monitor delta | 11 deltas |
| BTC trades | 1 | 5 | +1 per monitor delta | 4 deltas |
| TP outcomes | 3 | 5 | 0 per monitor delta | Not estimable until TP resumes |

Trend status:

```text
ACCUMULATING
```

---

## Current Raw Gate Progress

| Gate | Progress | Percent | Status |
|---|---:|---:|---|
| Paired trades | 9/20 | 45% | NOT MET |
| BTC trades | 1/5 | 20% | NOT MET |
| ETH trades | 8/5 | 100% capped | MET |
| TP outcomes | 3/5 | 60% | NOT MET |
| SL outcomes | 6/5 | 100% capped | MET |
| 60s+ quote-age fills | 1/1 | 100% capped | MET |

The project should not promote because paired count, BTC count, and TP count remain below readiness targets.

---

## Daily Notes

2026-05-22:

- Confirmed outcome-truth evidence exists.
- `trade_result` and `pnl_usdc` support direct TP/SL/WIN/LOSS counting.
- `quote_age_at_submit_ms`, `quote_age_at_fill_ms`, and `quote_lineage_id` are present on included fills.
- ETH coverage is above the minimum gate.
- BTC coverage has started but remains under target.
- TP coverage remains under target.
- 60s+ evidence exists, but the stale-quote relationship is not strong enough for Phase 6.

---

## Exactly Three Future Options

## OPTION 1 - SAFE EV PRESERVATION

Thesis: keep Phase 6 blocked until all gates pass with margin.

Quant logic: paired sample, BTC coverage, and TP coverage remain too thin, and stale-quote behavior is not stable enough to become policy.

Likely outcome: additional clean sessions clarify whether BTC behaves differently and whether TP coverage catches up.

Hidden risk: treating capped SL or 60s+ gates as sufficient may hide weak BTC and TP coverage.

Recommended action: continue daily tracking without runtime changes.

## OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

Thesis: collect more clean outcome-truth rows across asset, side, quote source, and lifecycle.

Quant logic: the tracker shows useful daily structure, but the next information gain comes from BTC and TP samples.

Likely outcome: one or two more clean sessions will decide whether the current ETH-heavy evidence generalizes.

Hidden risk: same-day clustering can make evidence look broader than it is.

Recommended action: prioritize future analysis around BTC confirmed pairs and TP outcomes.

## OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Thesis: gate readiness should separate the accepted monitor baseline from raw append-only JSONL drift.

Quant logic: raw logs can grow within the same date after a monitor note is written. A daily tracker should show current totals while preserving prior gate snapshots.

Likely outcome: fewer contradictions between daily monitors, phase monitors, and Obsidian notes.

Hidden risk: stale docs can silently lag new JSONL evidence and confuse readiness gates.

Recommended action: refresh this daily monitor after each accepted Phase 5 monitor update.

---

## Recommendation

```text
COLLECT_MORE_EVIDENCE
```

Phase 6 is not ready. Paired count, BTC evidence, and TP evidence remain insufficient.
