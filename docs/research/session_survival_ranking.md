# Session Survival Ranking

Generated: 2026-05-23  
Scope: read-only survivability ranking across all historical JSONL dates.  
Hours are UTC.

No code, replay, runtime, policy, strategy, risk, execution, live, or S3 changes were made.

## Sources

- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/execution_log/*.jsonl`
- `runtime/quant_data/decision_log/*.jsonl`

## Scoring Model

Survival score combines:

- TP / proxy-win rate.
- Cross-date stability.
- Mean PnL.
- OPENING success rate.
- ACTIVE success rate.
- Modern outcome-truth weight.
- Legacy penalty.

Weights:

| Component | Weight |
|---|---:|
| TP / proxy success rate | 28% |
| Cross-date stability | 22% |
| Mean PnL score | 18% |
| OPENING success | 10% |
| ACTIVE success | 10% |
| Modern outcome-truth weight | +17% |
| Legacy penalty | -15% |

Historical rows without `trade_result` are counted by PnL sign only and penalized as legacy evidence. This means high-scoring legacy-heavy hours are deliberately held below S tier.

## Tier Summary

| Tier | Hours |
|---|---|
| S | none |
| A | 01h, 16h |
| B | 18h, 20h, 06h, 13h, 19h, 09h, 12h, 11h, 17h, 10h, 04h |
| Avoid | 08h, 03h, 02h, 14h, 15h, 07h, 05h, 00h, 21h, 22h, 23h |

## Full Ranking

| Tier | Hour | Score | Trades | TP/SL | Success Rate | Date W/L/M | Mean PnL | OPENING | ACTIVE | Modern Weight | Legacy Penalty | BTC/ETH | Mean quote_stale_ms |
|---|---:|---:|---:|---|---:|---|---:|---|---|---:|---:|---|---:|
| A | 01h | 0.608 | 7 | 1/1 | 85.7% | 2/0/1 | +0.714607 | 1/1 | 0/1 | 0.29 | 0.71 | 5/2 | 29010.5 |
| A | 16h | 0.588 | 28 | 2/1 | 78.6% | 4/0/0 | +0.440293 | 5/6 | 0/1 | 0.11 | 0.89 | 22/6 | n/a |
| B | 18h | 0.577 | 21 | 0/0 | 81.0% | 1/0/0 | +0.513333 | n/a | n/a | 0.00 | 1.00 | 21/0 | n/a |
| B | 20h | 0.574 | 30 | 0/0 | 80.0% | 2/0/0 | +0.489000 | n/a | n/a | 0.00 | 1.00 | 30/0 | n/a |
| B | 06h | 0.568 | 56 | 0/0 | 83.9% | 4/1/0 | +0.327362 | 6/10 | 2/3 | 0.00 | 1.00 | 45/11 | n/a |
| B | 13h | 0.549 | 76 | 1/2 | 81.6% | 6/1/1 | +0.437316 | 5/8 | 1/2 | 0.04 | 0.96 | 66/10 | n/a |
| B | 19h | 0.520 | 3 | 0/1 | 66.7% | 2/1/0 | +0.665322 | n/a | 0/1 | 0.33 | 0.67 | 3/0 | n/a |
| B | 09h | 0.517 | 34 | 5/1 | 70.6% | 4/3/1 | +0.292287 | 9/16 | 2/3 | 0.18 | 0.82 | 18/16 | 9974.1 |
| B | 12h | 0.503 | 63 | 0/1 | 79.4% | 5/1/0 | +0.468222 | 5/8 | 0/1 | 0.02 | 0.98 | 59/4 | n/a |
| B | 11h | 0.464 | 80 | 0/0 | 82.5% | 3/1/1 | +0.387141 | 5/7 | 0/2 | 0.00 | 1.00 | 73/7 | n/a |
| B | 17h | 0.463 | 12 | 1/2 | 75.0% | 2/2/0 | +0.666008 | 1/3 | 0/1 | 0.25 | 0.75 | 9/3 | n/a |
| B | 10h | 0.463 | 19 | 2/1 | 63.2% | 4/2/1 | +0.258000 | 2/5 | 2/5 | 0.16 | 0.84 | 11/8 | 10945.0 |
| B | 04h | 0.448 | 102 | 0/0 | 82.4% | 5/2/1 | +0.389820 | 7/14 | 0/1 | 0.00 | 1.00 | 91/11 | n/a |
| Avoid | 08h | 0.396 | 12 | 0/0 | 66.7% | 2/0/1 | +0.005983 | 8/12 | 1/2 | 0.00 | 1.00 | 3/9 | n/a |
| Avoid | 03h | 0.364 | 17 | 0/1 | 64.7% | 3/3/1 | +0.410302 | 4/10 | 0/1 | 0.06 | 0.94 | 8/9 | 10251.7 |
| Avoid | 02h | 0.345 | 75 | 0/8 | 70.7% | 3/5/1 | +0.374056 | 1/10 | 0/6 | 0.11 | 0.89 | 62/13 | 23146.5 |
| Avoid | 14h | 0.338 | 12 | 0/0 | 58.3% | 2/1/2 | +0.248573 | 4/7 | 0/2 | 0.00 | 1.00 | 5/7 | n/a |
| Avoid | 15h | 0.318 | 26 | 0/2 | 65.4% | 1/3/0 | +0.374203 | 1/4 | 0/2 | 0.08 | 0.92 | 21/5 | n/a |
| Avoid | 07h | 0.276 | 13 | 0/0 | 38.5% | 2/3/0 | +0.379924 | 0/8 | n/a | 0.00 | 1.00 | 5/8 | n/a |
| Avoid | 05h | 0.264 | 18 | 0/0 | 38.9% | 1/3/1 | +0.112503 | 5/16 | n/a | 0.00 | 1.00 | 8/10 | n/a |
| Avoid | 00h | 0.040 | 0 | 0/0 | n/a | 0/0/0 | n/a | n/a | n/a | 0.00 | 1.00 | 0/0 | n/a |
| Avoid | 21h | 0.040 | 0 | 0/0 | n/a | 0/0/0 | n/a | n/a | n/a | 0.00 | 1.00 | 0/0 | n/a |
| Avoid | 23h | 0.040 | 0 | 0/0 | n/a | 0/0/0 | n/a | n/a | n/a | 0.00 | 1.00 | 0/0 | n/a |
| Avoid | 22h | 0.000 | 1 | 0/0 | 0.0% | 0/1/0 | -0.002402 | 0/1 | n/a | 0.00 | 1.00 | 1/0 | n/a |

## Best Survivable Session

Best practical survivable session: `16h UTC`.

Why not 01h despite higher score?

- 01h has only three active dates.
- Its modern outcome truth is mixed: 1 TP / 1 SL.
- ACTIVE failed in the modern sample.
- It looks like a narrow opening-dislocation candidate, not a broad survivable session.

Why 16h survives better:

- 4 active dates, 4 win dates, 0 loss dates.
- Confirmed outcome truth: 2 TP / 1 SL.
- Strong proxy success: 22 wins / 6 losses.
- Better cross-date stability than 09h.

Caveat: 16h is still legacy-heavy, so it is A tier, not S tier.

## Most Dangerous Session

Most dangerous tradable session: `02h UTC`.

Evidence:

- Confirmed outcome truth: 0 TP / 8 SL.
- ACTIVE success: 0 / 6.
- OPENING success: 1 / 10.
- Loss dates exceed win dates: 5 loss dates vs 3 win dates.
- Mean quote staleness where available: 23.147s.
- Recent Phase 6 02h was especially bad: 0 TP / 8 SL on 2026-05-23.

`22h` has the lowest numeric score, but it has only one trade and is better treated as low-evidence. `02h` is the more dangerous session because it has enough activity and confirmed adverse outcome truth.

## Candidate Harvest Windows

| Window | Tier | Use Case | Caveat |
|---|---|---|---|
| 16h | A | Best survivability candidate | Needs more Phase 6 quote-stale and outcome-truth evidence. |
| 01h | A | Opening-dislocation candidate | Thin sample; modern result is mixed. |
| 09h | B | Modern Phase 6 trend/session candidate | Cross-date stability is weak, but confirmed TP/SL is favorable. |
| 06h | B | Legacy stable trend candidate | No modern outcome-truth support yet. |
| 13h | B | Legacy BTC-active candidate | Confirmed TP/SL is mixed and legacy-biased. |
| 10h | B | Balanced trend watchlist | Modern support exists but stability is not clean. |

## Avoid Windows

| Window | Reason |
|---|---|
| 02h | Confirmed SL-heavy profile; current chop/risk session. |
| 05h | Low proxy success and recurring loss dates. |
| 07h | Weak opening profile and recurring losses. |
| 15h | Confirmed SL-heavy and unstable. |
| 00h, 21h, 23h | No closed-trade survival evidence. |
| 22h | One observed proxy loss, no positive evidence. |

## Final Interpretation

No hour deserves S tier yet. The data is still split between modern outcome truth and legacy proxy evidence.

- Best survivable session: `16h UTC`.
- Strongest modern research window: `09h UTC`.
- Most dangerous session: `02h UTC`.
- Best opening-dislocation watch: `01h UTC`.

Classification: `LEGACY_BIASED`

Reason: the ranking can identify candidates, but too much of the cross-date strength still comes from older rows without confirmed `trade_result`, quote staleness, or full lifecycle evidence. The system should continue harvesting, not promote session policy.

Runtime behavior changed: No  
Live behavior changed: No  
Tests: not run, docs-only  
Persistent tests unchanged
