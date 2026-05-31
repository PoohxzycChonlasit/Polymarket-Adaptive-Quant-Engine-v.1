# ORDERBOOK_STATE_HEALTH Watchlist

type: living evidence tracker
priority: P1
status: OBSERVED
current_n: 402 (all trades, across all ob_states)
last_snapshot: 2026-05-30
last_evidence_run: 2026-05-30
created: 2026-05-30
code_changed: No
strategy_changed: No
runtime_changed: No

---

## Purpose

Track trade outcomes, calibration, and CLOB health by orderbook state
classification. Monitor three known anomalies:

1. **`orderbook_unavailable` overperforms** (55.3% win rate despite 100% CLOB fail
   rate): All 38 `orderbook_unavailable` trades have `ob_reason = clob_empty_response`
   — HTTP 200 with empty body. Binary prices are still available; the label is a
   classification path artifact, not a true data outage. OBSERVED.

2. **`empty_book` underperforms** (31.8% win rate, BTC penalty 21pp vs ready):
   `empty_book` fires when YES/NO binary prices are incomplete (one side missing),
   while L1/L3 depth fields remain populated. BTC suffers 3× the penalty of ETH.

3. **`stale_orderbook` is the worst state** (0-for-9): All 9 stale trades are losses.
   Calibration gap +0.614. n=9 is WATCHLIST only but directionally definitive.

### ob_state Classification Source (from code)

`_phase2_orderbook_state_classification()` in `trader.py` classifies based on
reason strings in the payload, not direct orderbook data:
- `clob_empty_response` in reason → `orderbook_unavailable` (catch-all branch)
- `liquidity_state == EMPTY` or `empty_book` in reason → `empty_book`
- `stale` in reason → `stale_orderbook`
- All four YES/NO prices > 0 → `ready`
- Any YES/NO price present but not all four positive → `empty_book`

`orderbook_unavailable` is therefore NOT a true CLOB failure for trading purposes —
binary prices are present and valid in 100% of observed cases.

---

## Tracked Metrics

| Metric | Definition |
|---|---|
| ready count + win rate | ob_state=ready trades and W/n |
| empty_book count + win rate | ob_state=empty_book trades and W/n |
| orderbook_unavailable count + win rate | ob_state=orderbook_unavailable trades and W/n |
| stale_orderbook count + win rate | ob_state=stale_orderbook trades and W/n |
| ready calibration gap | avg(true_p) − wr for ready state |
| empty_book calibration gap | avg(true_p) − wr for empty_book state |
| unavailable calibration gap | avg(true_p) − wr for unavailable state |
| CLOB fail rate by state | clob_api_failure=True fraction per state |
| BTC empty_book penalty | Δ win rate (ready − empty_book) for BTC only |
| ETH empty_book penalty | Δ win rate (ready − empty_book) for ETH only |
| unavailable anomaly flag | Is orderbook_unavailable still outperforming ready? |

---

## Promotion Criteria (OBSERVED → VERIFIED per state)

- ready: n ≥ 250 (currently 161)
- empty_book: n ≥ 250 (currently 192)
- orderbook_unavailable: n ≥ 75 (currently 38 — anomaly needs replication)
- stale_orderbook: n ≥ 30 (currently 9 — smallest, all losses)

## Downgrade Criteria

- `unavailable` win rate falls below 43% over n ≥ 30 new trades (anomaly resolves → reclassify)
- `empty_book` win rate rises above 40% sustained (penalty resolves)
- `stale_orderbook` achieves any wins over n ≥ 10 new trades (flip from all-loss pattern)

---

## Snapshot 1 — 2026-05-30

analysis_run: 2026-05-30
sessions_covered: all sessions May 18–30 (402 total trades)
new_trades_since_last: 402 (first snapshot)

```
ready:         161 / 250  [####################################----------]  64.4%  wr=43.5%
empty_book:    192 / 250  [#######################################-------]  76.8%  wr=31.8%
unavailable:    38 / 75   [##########################--------------------]  50.7%  wr=55.3% ⚠ ANOMALY
stale:           9 / 30   [############----------------------------------]  30.0%  wr=0.0%  ⚠ WORST
```

### Core Metrics by ob_state

| ob_state | n | Win% | Avg PnL | Avg Conf | Calib gap | CLOB fail% |
|---|---|---|---|---|---|---|
| **ready** | **161** | **43.5%** | +$0.000 | 0.573 | +0.215 | 0% |
| empty_book | 192 | 31.8% | −$0.001 | 0.605 | +0.326 | 0% |
| **orderbook_unavailable** | **38** | **55.3%** | +$0.002 | 0.573 | +0.097 | **100%** |
| stale_orderbook | 9 | **0.0%** | −$0.007 | 0.629 | +0.614 | 0% |

### empty_book Penalty: BTC vs ETH

| Asset | empty_book wr | ready wr | Penalty | Mechanism |
|---|---|---|---|---|
| BTC | 20.7% | 41.9% | **−21.2pp** | High conf inflation, COMPRESSION concentration |
| ETH | 36.6% | 43.8% | −7.2pp | Moderate, spread across regimes |

BTC is 3× more penalized by empty_book than ETH. BTC empty_book trades are
70.7% COMPRESSION regime; ETH empty_book trades are only 23.1% COMPRESSION.

### orderbook_unavailable Anomaly: Root Cause

All 38 `orderbook_unavailable` trades have `ob_reason = 'clob_empty_response'`.
Despite this label:
- yes_bid, yes_ask, no_bid, no_ask: ALL positive in 100% of trades (38/38 BTC, 32/32 ETH)
- The label fires because `clob_empty_response` hits the `if reason: return "orderbook_unavailable"` catch-all BEFORE the binary price check runs
- These trades are functionally equivalent to `ready` — binary prices valid

Win rate 55.3% is not a real edge — it reflects: (a) misclassification of
functional trades, (b) paper execution independence from CLOB quality, and
(c) statistical noise at n=38.

### CLOB Degradation Event: 2026-05-30

May 30 session `20260530T125144Z` had 95% `orderbook_unavailable` all day:
- 10,427 / 10,980 decisions (95.0%) classified `orderbook_unavailable`
- `clob_api_failure=True` in 10,438 / 10,980 decisions (95.1%)
- Empty book recovery: 671 attempts, 244 failures, 2 successes (0.3% success rate)
- Token preload: 100% hit rate (6,286 hits, 122 misses) — preload unaffected
- Last trade: 18:12 UTC; last system event: 23:59 UTC

**Flag this as an outlier session** when computing rolling ob_state health averages.

### stale_orderbook Detail (WATCHLIST — n=9)

- 9 trades, 0 wins, gross = −$0.061
- Avg conf = 0.629, avg EV = 0.107 — normal model inputs
- Calib gap = +0.614 — most severely miscalibrated state
- All BTC (8/9) or ETH (1/9)
- **n=9 is insufficient for conclusions; pattern is consistent but unreliable**

### EV Inversion by ob_state

| ob_state | W_ev | L_ev | EV_Δ |
|---|---|---|---|
| ready | 0.123 | 0.124 | −0.001 (slight inversion) |
| empty_book | 0.120 | 0.125 | −0.005 (moderate inversion) |
| orderbook_unavailable | 0.121 | 0.123 | −0.002 (slight inversion) |

EV inversion is present in all ob_states — it is not an orderbook quality artifact.
The root cause is the probability model, not the CLOB state.
