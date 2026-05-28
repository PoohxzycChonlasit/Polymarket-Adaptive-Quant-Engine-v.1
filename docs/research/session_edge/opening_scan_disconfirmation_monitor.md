# Opening Scan Disconfirmation Monitor

Updated: 2026-05-23 post-shutdown-fix evidence refresh

Scope: outcome-truth closed paper trades from 2026-05-22 through latest close `2026-05-23T11:17:06.416120Z`.

Runtime behavior changed: No

Live behavior changed: No

## Verdict

Classification: EDGE_WEAKENING

Recommendation: COLLECT_MORE_EVIDENCE

The original Opening Scan hypothesis is no longer cleanly intact. Active TP, elapsed >30s TP, and BTC TP all appeared after the newer harvest. However, OPENING_SCAN still beats ACTIVE_INVENTORY_TRADING by TP rate, and elapsed <=30s still beats elapsed >30s by TP rate. That weakens the edge but does not break it.

## Disconfirmation Counters

| Signal | Count | Interpretation |
| --- | ---: | --- |
| ACTIVE TP | 3 | Disconfirms the earlier zero-Active-TP claim. |
| elapsed >30s TP | 4 | Disconfirms the earlier zero-late-TP claim. |
| BTC TP | 3 | Disconfirms the earlier zero-BTC-TP claim. |
| 60s+ quote stale winners | 0 | No stale quote winner cluster yet. |

## Current Outcome Matrix

| Slice | Trades | TP | SL | TP rate | Mean pnl_usdc |
| --- | ---: | ---: | ---: | ---: | ---: |
| All outcome-truth | 35 | 13 | 22 | 37.1% | -0.00189161 |
| OPENING_SCAN | 24 | 10 | 14 | 41.7% | -0.00245679 |
| ACTIVE_INVENTORY_TRADING | 11 | 3 | 8 | 27.3% | -0.00065849 |
| elapsed <=30s | 19 | 9 | 10 | 47.4% | -0.00118430 |
| elapsed >30s | 16 | 4 | 12 | 25.0% | -0.00273154 |
| BTC | 7 | 3 | 4 | 42.9% | -0.00171397 |
| ETH | 28 | 10 | 18 | 35.7% | -0.00193602 |

## Disconfirmation Events

| Close timestamp UTC | Hour | Asset | Side | Lifecycle | Elapsed sec | Result | pnl_usdc | quote_stale_ms |
| --- | ---: | --- | --- | --- | ---: | --- | ---: | ---: |
| 2026-05-23T09:10:41.747343Z | 09 | BTC | YES | OPENING_SCAN | 31.65 | TP | 0.00200799 | 10548.36 |
| 2026-05-23T09:17:06.393106Z | 09 | ETH | YES | ACTIVE_INVENTORY_TRADING | 53.24 | TP | 0.03219290 | 15336.34 |
| 2026-05-23T09:20:31.789528Z | 09 | ETH | NO | OPENING_SCAN | 20.78 | TP | 0.00788456 | 11247.65 |
| 2026-05-23T09:22:03.769909Z | 09 | BTC | YES | ACTIVE_INVENTORY_TRADING | 74.84 | TP | 0.01210521 | 15229.54 |
| 2026-05-23T10:16:08.125207Z | 10 | ETH | NO | ACTIVE_INVENTORY_TRADING | 55.88 | TP | 0.01040964 | 12486.66 |
| 2026-05-23T10:20:37.167892Z | 10 | BTC | NO | OPENING_SCAN | 7.81 | TP | 0.00774464 | 17006.72 |

## Questions

1. Same trade or different?

Different trades. Some ACTIVE TP and >30s TP overlap, but the disconfirmation set spans six TP events across BTC and ETH.

2. Single hour anomaly?

Mostly a 09h pocket, with continuation into 10h. It is not spread across the whole day.

3. 09h-only effect?

Not strictly. 10h produced one ACTIVE TP and one BTC Opening TP. The strongest cluster remains 09h.

4. ETH-only?

No. BTC produced 3 TP / 4 SL in the current outcome-truth set.

5. Does this weaken or break Opening edge?

Weakens. OPENING_SCAN remains ahead of ACTIVE by TP rate, and <=30s remains ahead of >30s, but the earlier zero-counter assumptions are false.

6. Is quote staleness the explanation?

Not yet. 2026-05-23 quote_stale_ms coverage is 18/18, mean quote_stale_ms is 16942.48, and 60s+ count is 0. The TP pocket is not a 60s+ stale quote artifact in current evidence.

## Watch Conditions

Escalate to EDGE_BROKEN if either condition appears:

- ACTIVE TP rate reaches or exceeds OPENING_SCAN TP rate across at least 20 Active outcome-truth trades.
- elapsed >30s TP rate reaches or exceeds elapsed <=30s TP rate across at least 20 late outcome-truth trades.

Escalate to SESSION_EDGE_CANDIDATE if 09h/10h positive pnl repeats across additional dates with both BTC and ETH coverage.

## Current Action

COLLECT_MORE_EVIDENCE.

Do not implement policy, thresholds, strategy changes, risk changes, or execution changes from this monitor.
