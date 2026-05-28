# 09h10h Regime Persistence Audit

Updated: 2026-05-23

Scope: all matched outcome-truth paper trades with `trade_result` from local trade journals.

Latest matched close: `2026-05-23T11:17:06.416120Z`

Sources:

- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/execution_log/*.jsonl`

Runtime behavior changed: No

Live behavior changed: No

## Verdict

Classification: SESSION_EDGE_CANDIDATE

Recommendation: COLLECT_MORE_EVIDENCE

The 09h/10h UTC advantage persists directionally across both available outcome-truth dates, but the strongest positive cluster is still concentrated on 2026-05-23. This is more than a single-trade anomaly, but not enough to call a durable SESSION_REGIME.

## 09h10h vs Other Hours

| Slice | Trades | TP | SL | TP rate | BTC | ETH | Opening TP | Active TP | Mean pnl_usdc | Mean EV | Mean confidence | quote_stale_ms coverage | Mean quote_stale_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 09h10h | 12 | 8 | 4 | 66.7% | 3 | 9 | 5 | 3 | 0.004471 | 0.104931 | 0.574799 | 8/12 | 12361.66 |
| Other hours | 23 | 5 | 18 | 21.7% | 4 | 19 | 5 | 0 | -0.005211 | 0.127200 | 0.594430 | 10/23 | 20607.13 |

Interpretation:

- 09h10h has a 45.0 percentage point TP-rate advantage.
- 09h10h is positive mean pnl; other hours are materially negative.
- Other hours have higher mean EV and confidence, so raw model conviction does not explain the edge.
- Actual `quote_stale_ms` coverage exists only on Phase 6 era rows, mostly 2026-05-23. 09h10h has lower mean quote_stale_ms than other hours where covered.

## Date x Session Matrix

| Date | Session | Trades | TP | SL | TP rate | BTC TP/SL | ETH TP/SL | Opening TP/SL | Active TP/SL | Mean pnl_usdc | Mean EV | Mean confidence | quote_stale_ms coverage |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 2026-05-22 | 09h10h | 4 | 2 | 2 | 50.0% | 0/0 | 2/2 | 2/1 | 0/1 | -0.002349 | 0.097101 | 0.560206 | 0/4 |
| 2026-05-22 | Other | 13 | 4 | 9 | 30.8% | 0/3 | 4/6 | 4/5 | 0/4 | -0.003870 | 0.124260 | 0.586103 | 0/13 |
| 2026-05-23 | 09h10h | 8 | 6 | 2 | 75.0% | 3/0 | 3/2 | 3/2 | 3/0 | 0.007882 | 0.108846 | 0.582095 | 8/8 |
| 2026-05-23 | Other | 10 | 1 | 9 | 10.0% | 0/1 | 1/8 | 1/6 | 0/3 | -0.006955 | 0.131021 | 0.605255 | 10/10 |

Read:

- The 09h10h slice beats other hours on both dates by TP rate.
- On 2026-05-22, the advantage is mild and still negative mean pnl.
- On 2026-05-23, the advantage is large and positive mean pnl.
- Therefore persistence is directional, but the high-confidence edge is still not cross-date proven.

## Asset Persistence

| Slice | Asset | Trades | TP | SL | TP rate | Mean pnl_usdc | Mean EV | Mean confidence | quote_stale_ms coverage |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 09h10h | BTC | 3 | 3 | 0 | 100.0% | 0.007286 | 0.097065 | 0.625902 | 3/3 |
| 09h10h | ETH | 9 | 5 | 4 | 55.6% | 0.003533 | 0.107553 | 0.557764 | 5/9 |
| Other | BTC | 4 | 0 | 4 | 0.0% | -0.008464 | 0.151095 | 0.700033 | 1/4 |
| Other | ETH | 19 | 5 | 14 | 26.3% | -0.004527 | 0.122169 | 0.572197 | 9/19 |

Answers:

- ETH-only? No. ETH participates, but BTC is currently the cleanest 09h10h asset split.
- BTC survives there? Yes in current evidence: 3 TP / 0 SL inside 09h10h, 0 TP / 4 SL outside.
- Caveat: all BTC 09h10h TP evidence is from 2026-05-23, so this is still small-sample and date-concentrated.

## Lifecycle Persistence

| Slice | Lifecycle | Trades | TP | SL | TP rate | Mean pnl_usdc | Mean EV | Mean confidence | quote_stale_ms coverage |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 09h10h | OPENING_SCAN | 8 | 5 | 3 | 62.5% | 0.000392 | 0.104448 | 0.578789 | 5/8 |
| 09h10h | ACTIVE_INVENTORY_TRADING | 4 | 3 | 1 | 75.0% | 0.012631 | 0.105898 | 0.566818 | 3/4 |
| Other | OPENING_SCAN | 16 | 5 | 11 | 31.3% | -0.003881 | 0.116459 | 0.601163 | 7/16 |
| Other | ACTIVE_INVENTORY_TRADING | 7 | 0 | 7 | 0.0% | -0.008252 | 0.151751 | 0.579039 | 3/7 |

Answers:

- ACTIVE survival dependent on session? Current evidence says yes.
- Active inside 09h10h: 3 TP / 1 SL.
- Active outside 09h10h: 0 TP / 7 SL.
- This is the strongest lifecycle-regime split, but Active sample is only 11 total trades.

## Hour Detail

| Hour UTC | Trades | TP | SL | TP rate | BTC TP/SL | ETH TP/SL | Opening TP | Active TP | Mean pnl_usdc |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |
| 09h | 6 | 5 | 1 | 83.3% | 2/0 | 3/1 | 3 | 2 | 0.007250 |
| 10h | 6 | 3 | 3 | 50.0% | 1/0 | 2/3 | 2 | 1 | 0.001692 |
| 02h | 5 | 0 | 5 | 0.0% | 0/1 | 0/4 | 0 | 0 | -0.008026 |
| 11h | 2 | 0 | 2 | 0.0% | 0/0 | 0/2 | 0 | 0 | -0.010761 |
| 15h | 2 | 0 | 2 | 0.0% | 0/1 | 0/1 | 0 | 0 | -0.013442 |

09h is the stronger half of the window. 10h remains positive but mixed.

## Direct Questions

1. Persistent edge?

Directionally yes, confirmed no. 09h10h outperforms other hours on both available dates, but only two dates exist and the biggest edge is concentrated on 2026-05-23.

2. Single cluster artifact?

Partly. It is not a single-trade artifact because the slice has 12 trades and appears on two dates. But the strongest BTC and Active evidence is a 2026-05-23 cluster, so persistence is not proven.

3. ETH-only?

No. BTC is actually cleaner inside 09h10h in the current dataset, with 3 TP / 0 SL.

4. BTC survives there?

Yes, but only as a candidate. BTC inside 09h10h is 3 TP / 0 SL; BTC outside is 0 TP / 4 SL.

5. ACTIVE survival dependent on session?

Yes in current evidence. Active inside 09h10h is 3 TP / 1 SL; Active outside is 0 TP / 7 SL.

## Interpretation

The best current hypothesis is not "OPENING only" and not "ACTIVE always bad." It is:

09h10h UTC may be a session pocket where both OPENING_SCAN and selective ACTIVE_INVENTORY_TRADING survive, while Active outside that pocket is currently hostile.

This remains a research hypothesis only. It does not authorize thresholds, policy, strategy, risk, execution, replay, or live changes.

## Evidence Needed Next

- At least 3 distinct dates with 09h10h matched trades.
- At least 20 total 09h10h matched trades.
- At least 8 BTC trades inside 09h10h.
- At least 10 Active trades inside 09h10h and 10 Active trades outside.
- Continued actual `quote_stale_ms` coverage, not only derived quote-age proxy.

## Final Status

SESSION_EDGE_CANDIDATE.

COLLECT_MORE_EVIDENCE.
