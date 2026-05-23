# Session Survival Ranking

Updated: 2026-05-23 post-shutdown-fix evidence refresh

Scope: outcome-truth closed paper trades from 2026-05-22 through latest close `2026-05-23T11:17:06.416120Z`. Earlier legacy rows without `trade_result` are treated as weak context only and are not used as primary promotion evidence.

Runtime behavior changed: No

Live behavior changed: No

## Executive Read

Best survivable session: 09h UTC, but only as a candidate.

Most dangerous session: 02h UTC.

Current recommendation: COLLECT_MORE_EVIDENCE.

The post-shutdown-fix harvest materially changed the map. 09h produced the strongest modern cluster and includes both Opening and Active winners. 10h also produced positive evidence, but mixed. 02h remains the clearest avoid window.

## Ranking

| Tier | Hours UTC | Reason |
| --- | --- | --- |
| S candidate | 09h | 6 trades, 5 TP / 1 SL, mean pnl_usdc 0.00725024, includes BTC TP and ACTIVE TP. Needs cross-date repeat. |
| A candidate | 10h | 6 trades, 3 TP / 3 SL, mean pnl_usdc 0.00169250, includes ACTIVE TP and BTC TP. Mixed but positive. |
| B watch | 16h | 3 trades, 2 TP / 1 SL, mean pnl_usdc 0.00090138. Useful context, but current quote_stale_ms coverage is absent. |
| B watch | 01h | 2 trades, 1 TP / 1 SL, mean pnl_usdc 0.00112488. Too small. |
| Avoid | 02h | 5 trades, 0 TP / 5 SL, mean pnl_usdc -0.00802584. Strongest negative modern hour. |
| Avoid | 03h, 11h, 12h, 15h, 19h | Negative or zero-TP outcome-truth hours with limited evidence. |

## Modern Outcome-Truth Hour Table

| Hour UTC | Trades | TP | SL | TP rate | Mean pnl_usdc | BTC | ETH | Opening TP | Active TP | quote_stale_ms coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 01h | 2 | 1 | 1 | 50.0% | 0.00112488 | 0 | 2 | 1 | 0 | 2/2 |
| 02h | 5 | 0 | 5 | 0.0% | -0.00802584 | 1 | 4 | 0 | 0 | 5/5 |
| 03h | 1 | 0 | 1 | 0.0% | -0.01015042 | 0 | 1 | 0 | 0 | 1/1 |
| 09h | 6 | 5 | 1 | 83.3% | 0.00725024 | 2 | 4 | 3 | 2 | 4/6 |
| 10h | 6 | 3 | 3 | 50.0% | 0.00169250 | 1 | 5 | 2 | 1 | 4/6 |
| 11h | 2 | 0 | 2 | 0.0% | -0.01076142 | 0 | 2 | 0 | 0 | 2/2 |
| 12h | 1 | 0 | 1 | 0.0% | -0.01054603 | 0 | 1 | 0 | 0 | 0/1 |
| 13h | 3 | 1 | 2 | 33.3% | -0.00301011 | 0 | 3 | 1 | 0 | 0/3 |
| 15h | 2 | 0 | 2 | 0.0% | -0.01344219 | 1 | 1 | 0 | 0 | 0/2 |
| 16h | 3 | 2 | 1 | 66.7% | 0.00090138 | 0 | 3 | 2 | 0 | 0/3 |
| 17h | 3 | 1 | 2 | 33.3% | -0.00084027 | 1 | 2 | 1 | 0 | 0/3 |
| 19h | 1 | 0 | 1 | 0.0% | -0.00403272 | 1 | 0 | 0 | 0 | 0/1 |

## Survivability Score Inputs

| Input | Current read |
| --- | --- |
| TP rate | 09h leads at 83.3%; 10h is mixed at 50.0%. |
| Cross-date stability | Not proven. Current strongest cluster is 2026-05-23 heavy. |
| Mean pnl | 09h and 10h positive; overall dataset remains negative. |
| OPENING TP | OPENING_SCAN has 10 TP / 14 SL. Good relative to Active, not profitable overall. |
| ACTIVE TP | ACTIVE has 3 TP / 8 SL. No longer zero, but still weaker than Opening. |
| Modern outcome-truth weight | 35 closed trades. 2026-05-23 has quote_stale_ms coverage; 2026-05-22 does not. |
| Legacy penalty | High. Older rows without `trade_result` are excluded from primary ranking. |

## Candidate Harvest Windows

| Window | Action | Reason |
| --- | --- | --- |
| 09h UTC | Priority harvest candidate | Strongest TP and pnl pocket, includes BTC and Active disconfirmation events. |
| 10h UTC | Secondary harvest candidate | Positive pnl but mixed TP/SL. Needs more separation. |
| 16h UTC | Watch only | Positive but small and older/less instrumented. |
| 02h UTC | Avoid / caution | 0 TP / 5 SL with strongly negative mean pnl. |
| 11h UTC | Avoid / caution | Recent post-shutdown evidence added SL pressure. |

## Phase Interpretation

The original Opening-only thesis should not be promoted as a hard policy. A better current hypothesis is:

09h/10h may be a session-regime pocket where both Opening and selective Active trades can work, while 02h behaves like a recurring failure window.

This is a research hypothesis only. It does not authorize runtime policy, risk, strategy, threshold, or execution changes.

## Next Evidence Needed

- At least one more date with 09h/10h outcome-truth coverage.
- More BTC trades before treating BTC 09h TP as stable.
- More ACTIVE trades before deciding whether Active is conditionally useful or just a short pocket anomaly.
- Continued quote_stale_ms coverage to confirm that winners are not stale-quote artifacts.

## Final Status

COLLECT_MORE_EVIDENCE.
