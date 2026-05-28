# Regime Split Next Hypothesis Audit

Updated: 2026-05-23

Scope: 35 matched outcome-truth paper trades from 2026-05-22 through latest close `2026-05-23T11:17:06.416120Z`.

Sources:

- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`

Runtime behavior changed: No

Live behavior changed: No

## Verdict

Classification: REGIME_SPLIT_CANDIDATE

Recommendation: COLLECT_MORE_EVIDENCE

The strongest current separator is not raw quote staleness, asset, side, or EV. The strongest separator is hour/session context, especially the 09h/10h UTC pocket versus the 02h/03h/11h/12h/15h/19h failure cluster.

## Current Dataset

| Metric | Value |
| --- | ---: |
| Matched trades | 35 |
| TP | 13 |
| SL | 22 |
| TP rate | 37.1% |
| Mean pnl_usdc | -0.00189161 |
| EV coverage | 35/35 |
| Confidence coverage | 35/35 |
| quote_stale_ms coverage | 18/35 |
| 60s+ quote stale count | 0 |

## TP vs SL

| Metric | TP | SL | Read |
| --- | ---: | ---: | --- |
| Count | 13 | 22 | SL remains dominant. |
| Mean pnl_usdc | 0.009599 | -0.008682 | Winners and losers are both meaningful; not dust-only noise. |
| Mean elapsed_seconds | 25.80 | 36.67 | Earlier entries still perform better. |
| Median elapsed_seconds | 15.51 | 31.49 | Timing split remains visible. |
| Mean EV | 0.106034 | 0.127560 | EV is inverted; higher EV did not protect outcomes. |
| Mean confidence | 0.571025 | 0.597552 | Confidence is also inverted. |
| Mean quote_stale_ms | 18487.60 | 15959.22 | Stale quotes do not explain losses in this sample. |

## Main Splits

### Asset

| Asset | Trades | TP | SL | TP rate | Mean pnl_usdc | Mean EV | Mean confidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTC | 7 | 3 | 4 | 42.9% | -0.001714 | 0.127939 | 0.668262 |
| ETH | 28 | 10 | 18 | 35.7% | -0.001936 | 0.117471 | 0.567558 |

Read: asset alone is not the separator. BTC now has TP, but the sample is too small and mean pnl remains negative.

### Lifecycle

| Lifecycle | Trades | TP | SL | TP rate | Mean pnl_usdc | Mean elapsed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OPENING_SCAN | 24 | 10 | 14 | 41.7% | -0.002457 | 18.37 |
| ACTIVE_INVENTORY_TRADING | 11 | 3 | 8 | 27.3% | -0.000658 | 63.74 |

Read: Opening is still better by TP rate, but Active is no longer dead. Active needs session conditioning.

### Timing

| Timing | Trades | TP | SL | TP rate | Mean pnl_usdc | Mean EV | Mean confidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| elapsed <=30s | 19 | 9 | 10 | 47.4% | -0.001184 | 0.112432 | 0.574177 |
| elapsed >30s | 16 | 4 | 12 | 25.0% | -0.002732 | 0.128035 | 0.603756 |

Read: the timing cliff still matters, but it is weakened by four >30s TP events.

### Session

| Session slice | Trades | TP | SL | TP rate | Mean pnl_usdc | Mean EV | Mean confidence | Mean quote_stale_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 09h/10h UTC | 12 | 8 | 4 | 66.7% | 0.004471 | 0.104931 | 0.574799 | 12361.66 |
| Not 09h/10h | 23 | 5 | 18 | 21.7% | -0.005211 | 0.127200 | 0.594430 | 20607.13 |
| 02h/03h/11h/12h/15h/19h | 12 | 0 | 12 | 0.0% | -0.009439 | 0.142494 | 0.625846 | 18021.72 |

Read: this is the strongest split. The best hours have lower EV/confidence than the worst cluster, which points to regime context overriding the model's raw score.

### Side

| Side | Trades | TP | SL | TP rate | Mean pnl_usdc |
| --- | ---: | ---: | ---: | ---: | ---: |
| YES | 13 | 5 | 8 | 38.5% | -0.001667 |
| NO | 22 | 8 | 14 | 36.4% | -0.002024 |

Read: side is not a useful separator yet.

### Quote Staleness

| Bucket | Trades | TP | SL | TP rate | Mean pnl_usdc |
| --- | ---: | ---: | ---: | ---: | ---: |
| <10s | 1 | 0 | 1 | 0.0% | -0.005025 |
| 10s-20s | 15 | 6 | 9 | 40.0% | -0.000242 |
| >=20s | 2 | 1 | 1 | 50.0% | 0.001075 |

Read: quote_stale_ms does not separate TP from SL yet. Coverage exists only on 2026-05-23 and there are no 60s+ stale events in this current matched set.

## Top 3 Explanatory Candidates

### 1. Session regime split

Evidence:

- 09h/10h UTC: 8 TP / 4 SL, TP rate 66.7%, mean pnl_usdc 0.004471.
- Non-09h/10h: 5 TP / 18 SL, TP rate 21.7%, mean pnl_usdc -0.005211.
- Failure cluster 02h/03h/11h/12h/15h/19h: 0 TP / 12 SL, mean pnl_usdc -0.009439.

Hypothesis:

09h/10h is a temporary or recurring session-regime pocket with more exploitable dislocation/trend follow-through. The poor hours may be chop, adverse selection, or model overconfidence during lower-quality market movement.

Evidence needed:

- At least two more dates with 09h/10h outcome-truth trades.
- At least 20 total 09h/10h matched trades before treating this as more than a candidate.

### 2. Lifecycle works only when conditioned on session

Evidence:

- ACTIVE 09h/10h: 3 TP / 1 SL, mean pnl_usdc 0.012631.
- ACTIVE outside 09h/10h: 0 TP / 7 SL, mean pnl_usdc -0.008252.
- OPENING <=30s: 9 TP / 10 SL, TP rate 47.4%, still better than late trades.
- OPENING >30s: 1 TP / 4 SL, TP rate 20.0%, mean pnl_usdc -0.007292.

Hypothesis:

OPENING_SCAN remains the safer default, but ACTIVE is not universally bad. ACTIVE may only become viable inside the same session-regime pocket where 09h/10h dislocations persist longer than the first 30 seconds.

Evidence needed:

- More Active trades in and outside 09h/10h.
- Confirm whether Active winners are tied to specific market regimes rather than just one lucky run.

### 3. EV/confidence inversion and adverse-selection candidate

Evidence:

- TP mean EV: 0.106034.
- SL mean EV: 0.127560.
- TP mean confidence: 0.571025.
- SL mean confidence: 0.597552.
- Confidence >=0.60: 1 TP / 6 SL, mean pnl_usdc -0.006430.
- Confidence <0.60: 12 TP / 16 SL, mean pnl_usdc -0.000757.
- Failure cluster mean EV/confidence is higher than 09h/10h mean EV/confidence.

Hypothesis:

Higher model conviction may be appearing during adverse-selection regimes, not during profitable regimes. EV/confidence might be measuring directional conviction but missing lifecycle/session/microstructure risk.

Evidence needed:

- Track EV/confidence by hour and lifecycle for another harvest day.
- Check whether high-confidence losers cluster around high spread, thin depth, late entries, or one-sided market moves.

## Candidates Rejected For Now

| Candidate | Why not primary |
| --- | --- |
| Asset-only split | BTC TP rate is slightly higher than ETH, but BTC has only 7 trades and negative mean pnl. |
| YES/NO side | YES and NO TP rates are nearly identical. |
| Quote stale | Winners have higher mean quote_stale_ms than losers, and no 60s+ evidence appears in the current joined set. |
| Raw EV threshold | Higher EV does not map to better results; thresholding EV alone would likely overfit or worsen selection. |
| Raw confidence threshold | High confidence is currently worse, not better. |

## Recommended Next Monitor Fields

For the next harvest update, track these jointly, not independently:

- hour UTC
- lifecycle phase
- elapsed_seconds
- EV
- confidence
- quote_stale_ms
- asset
- side
- pnl_usdc
- trade_result

The next useful table is a compact `hour x lifecycle x TP/SL x EV/confidence` matrix.

## Final Recommendation

COLLECT_MORE_EVIDENCE.

Do not promote thresholds, policy, strategy, risk, or execution changes from this audit. The next hypothesis to test is session-conditioned lifecycle behavior, especially 09h/10h Active versus non-09h/10h Active.
