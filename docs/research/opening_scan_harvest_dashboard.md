# Opening Scan Harvest Dashboard

Updated: 2026-05-23 post-shutdown-fix evidence refresh

Scope: outcome-truth closed paper trades from `runtime/quant_data/trade_journal/2026-05-22.jsonl` and `runtime/quant_data/trade_journal/2026-05-23.jsonl`. Quote-staleness fields are joined from `runtime/quant_data/execution_log/2026-05-23.jsonl` where available.

Latest matched close: `2026-05-23T11:17:06.416120Z`

Latest run id: `20260523T110140Z_7368_cfbbb3a1`

Runtime behavior changed: No

Live behavior changed: No

## Current Status

Status: HARVESTING_WITH_DISCONFIRMATION

Recommendation: COLLECT_MORE_EVIDENCE

The post-shutdown-fix harvest added enough evidence to weaken the original pure Opening Scan hypothesis. Opening still performs better than Active and <=30s still performs better than >30s, but Active TP, >30s TP, and BTC TP are no longer zero. The edge is not broken, but it is no longer clean enough for policy.

## Snapshot Counters

| Metric | Current |
| --- | ---: |
| Matched outcome-truth trades | 35 |
| TP | 13 |
| SL | 22 |
| TP rate | 37.1% |
| Mean pnl_usdc | -0.00189161 |
| BTC | 7 |
| ETH | 28 |
| quote_stale_ms coverage | 18/35 |
| Mean quote_stale_ms | 16942.48 |
| 60s+ quote stale count | 0 |

## Asset Split

| Asset | Trades | TP | SL | TP rate | Mean pnl_usdc | quote_stale_ms coverage | Mean quote_stale_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTC | 7 | 3 | 4 | 42.9% | -0.00171397 | 4/7 | 13239.50 |
| ETH | 28 | 10 | 18 | 35.7% | -0.00193602 | 14/28 | 18000.47 |

## Lifecycle Split

| Lifecycle | Trades | TP | SL | TP rate | Mean pnl_usdc | Read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| OPENING_SCAN | 24 | 10 | 14 | 41.7% | -0.00245679 | Still best lifecycle, but not profitable overall. |
| ACTIVE_INVENTORY_TRADING | 11 | 3 | 8 | 27.3% | -0.00065849 | No longer zero-TP; keep monitoring before making policy. |

## Timing Split

| Timing | Trades | TP | SL | TP rate | Mean pnl_usdc | Read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| elapsed <=30s | 19 | 9 | 10 | 47.4% | -0.00118430 | Better than late entries, still negative mean pnl. |
| elapsed >30s | 16 | 4 | 12 | 25.0% | -0.00273154 | Weak, but not zero-TP anymore. |

## Date Ledger

| Date UTC | Trades | TP | SL | TP rate | BTC | ETH | Opening | Active | quote_stale_ms coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-05-22 | 17 | 6 | 11 | 35.3% | 3 | 14 | 12 | 5 | 0/17 |
| 2026-05-23 | 18 | 7 | 11 | 38.9% | 4 | 14 | 12 | 6 | 18/18 |

## Hour Highlights

| Hour UTC | Trades | TP | SL | TP rate | Mean pnl_usdc | BTC | ETH | Opening TP | Active TP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 01h | 2 | 1 | 1 | 50.0% | 0.00112488 | 0 | 2 | 1 | 0 |
| 02h | 5 | 0 | 5 | 0.0% | -0.00802584 | 1 | 4 | 0 | 0 |
| 03h | 1 | 0 | 1 | 0.0% | -0.01015042 | 0 | 1 | 0 | 0 |
| 09h | 6 | 5 | 1 | 83.3% | 0.00725024 | 2 | 4 | 3 | 2 |
| 10h | 6 | 3 | 3 | 50.0% | 0.00169250 | 1 | 5 | 2 | 1 |
| 11h | 2 | 0 | 2 | 0.0% | -0.01076142 | 0 | 2 | 0 | 0 |
| 12h | 1 | 0 | 1 | 0.0% | -0.01054603 | 0 | 1 | 0 | 0 |
| 13h | 3 | 1 | 2 | 33.3% | -0.00301011 | 0 | 3 | 1 | 0 |
| 15h | 2 | 0 | 2 | 0.0% | -0.01344219 | 1 | 1 | 0 | 0 |
| 16h | 3 | 2 | 1 | 66.7% | 0.00090138 | 0 | 3 | 2 | 0 |
| 17h | 3 | 1 | 2 | 33.3% | -0.00084027 | 1 | 2 | 1 | 0 |
| 19h | 1 | 0 | 1 | 0.0% | -0.00403272 | 1 | 0 | 0 | 0 |

## Delta vs Prior Dashboard Snapshot

Previous dashboard snapshot: 28 matched trades, 7 TP, 21 SL.

Current snapshot: 35 matched trades, 13 TP, 22 SL.

Delta:

| Metric | Previous | Current | Delta |
| --- | ---: | ---: | ---: |
| Matched trades | 28 | 35 | +7 |
| TP | 7 | 13 | +6 |
| SL | 21 | 22 | +1 |
| BTC TP | 0 | 3 | +3 |
| Active TP | 0 | 3 | +3 |
| elapsed >30s TP | 0 | 4 | +4 |

## Read

- Opening edge: weakened, not invalidated. OPENING_SCAN still has the better TP rate, but negative mean pnl keeps it below promotion quality.
- Active disconfirmation: real enough to track. ACTIVE TP appeared 3 times, concentrated in the 09h/10h pocket.
- Timing cliff: weakened, not invalidated. >30s trades still underperform <=30s trades, but >30s TP is no longer zero.
- BTC evidence: improved from zero TP to 3 TP / 4 SL, but sample remains too small.
- Quote stale: 2026-05-23 has full quote_stale_ms coverage and no 60s+ events. Staleness does not explain the 09h/10h TP pocket yet.

## Recommendation

COLLECT_MORE_EVIDENCE.

Do not promote a Phase policy from this monitor alone. Keep harvesting the 09h/10h pocket, avoid over-weighting the old pure Opening hypothesis, and require more cross-date confirmation before changing strategy/risk/execution behavior.
