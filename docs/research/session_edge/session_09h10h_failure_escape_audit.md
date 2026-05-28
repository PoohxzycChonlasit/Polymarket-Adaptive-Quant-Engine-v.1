# 09h10h Failure Escape Audit

Date: 2026-05-25

Scope: read-only audit of whether the prior `09h10h` `SESSION_EDGE_CANDIDATE` survives the BTC / NO / ACTIVE failure triangle.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Role Routing

Primary role: `10_BACKTEST_REPLAY_AGENT.md`

Supporting roles:

- `16_PAPER_EVALUATION_AGENT.md`
- `11_OBSERVABILITY_INCIDENT_AGENT.md`
- `07_TEST_CI_AGENT.md`

Why selected: this is an offline session/lifecycle outcome audit using trade-journal and path-truth evidence, with no runtime or strategy changes.

## Sources Inspected

- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/research/session_edge/session_pressure_comparison_audit.md`
- `docs/research/session_edge/session_regime_09h10h_persistence.md`
- `docs/research/session_edge/failure_triangle_audit.md`
- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`

Files intentionally ignored:

- `polymarket/trader.py`
- `polymarket/order_manager.py`
- `utils/risk_manager.py`
- wallet/live configuration
- replay execution paths

## Method

Target session:

- `09h10h` = UTC hours `09` and `10`.

Primary sample:

- Completed recent session-pressure window: `2026-05-21` through `2026-05-23`.
- This matches the prior `09h10h` session-pressure evidence window.

Important limitation:

- The current path-truth failure-triangle sample from `2026-05-24` and `2026-05-25` has `0` trades in UTC hours `09` or `10`.
- Therefore, this is not a same-sample proof that `09h10h` escapes the current path-truth failure triangle.
- It is a cross-window verification using the latest completed `09h10h` evidence.

Pairing method:

- `trade_open` rows were paired to `trade_close` rows by run, asset, and selected side order.
- Stage comes from the paired `trade_open.lifecycle_phase`.
- Outcome is derived from close `reason`:
  - `take_profit_target_reached` -> `TP`
  - `stop_loss` / `stop_loss_hit` -> `SL`
- Hold uses `trade_close.hold_seconds`.

## 09h10h Summary

Window: `2026-05-21` through `2026-05-23`

| Metric | Value |
| --- | ---: |
| Trades | 16 |
| TP | 8 |
| SL | 8 |
| Win rate | 50.0% |
| Fast close <60s | 15 / 16 |
| Median hold | 11.0s |
| BTC split | 3 TP / 1 SL |
| ETH split | 5 TP / 7 SL |
| YES split | 4 TP / 3 SL |
| NO split | 4 TP / 5 SL |
| OPENING split | 5 TP / 6 SL |
| ACTIVE split | 3 TP / 2 SL |

Interpretation:

`09h10h` still looks better than the failure-triangle baseline, but not clean. It survives BTC and ACTIVE pressure directionally. It does not cleanly escape NO-side pressure or ETH losses.

## Session Survival By Date

| Date | Trades | TP | SL | Fast Close <60s | Read |
| --- | ---: | ---: | ---: | ---: | --- |
| 2026-05-21 | 2 | 0 | 2 | 2 / 2 | fails on first available day |
| 2026-05-22 | 6 | 2 | 4 | 6 / 6 | mixed, net adverse |
| 2026-05-23 | 8 | 6 | 2 | 7 / 8 | strong survival cluster |

The survival is date-concentrated. The positive read depends heavily on `2026-05-23`; `2026-05-21` and `2026-05-22` do not independently prove the edge.

## Failure Escape Matrix

| Bucket | Trades | TP | SL | Win Rate | Median Hold | Fast Close | Hold Buckets | Dates | Price Buckets | Read |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| 09h10h + BTC + YES + OPENING | 1 | 1 | 0 | 100.0% | 10s | 1 / 1 | 0-15s: 1 | 2026-05-23: 1 | 0.60+: 1 | survives, but one trade |
| 09h10h + BTC + YES + ACTIVE | 1 | 1 | 0 | 100.0% | 49s | 1 / 1 | 45-60s: 1 | 2026-05-23: 1 | 0.50-0.59: 1 | survives, but one trade |
| 09h10h + BTC + NO + OPENING | 2 | 1 | 1 | 50.0% | 20s | 2 / 2 | 0-15s: 1, 15-30s: 1 | 2026-05-21: 1, 2026-05-23: 1 | 0.50-0.59: 2 | mixed |
| 09h10h + BTC + NO + ACTIVE | 0 | 0 | 0 | N/A | N/A | 0 / 0 | none | none | none | no evidence |
| 09h10h + ETH + YES + OPENING | 3 | 1 | 2 | 33.3% | 5s | 3 / 3 | 0-15s: 2, 30-45s: 1 | 2026-05-21: 1, 2026-05-22: 2 | 0.50-0.59: 3 | fails/mixed |
| 09h10h + ETH + YES + ACTIVE | 2 | 1 | 1 | 50.0% | 47.5s | 1 / 2 | 15-30s: 1, 60s+: 1 | 2026-05-22: 1, 2026-05-23: 1 | 0.50-0.59: 2 | mixed |
| 09h10h + ETH + NO + OPENING | 5 | 2 | 3 | 40.0% | 11s | 5 / 5 | 0-15s: 4, 45-60s: 1 | 2026-05-22: 2, 2026-05-23: 3 | 0.50-0.59: 5 | weak |
| 09h10h + ETH + NO + ACTIVE | 2 | 1 | 1 | 50.0% | 8s | 2 / 2 | 0-15s: 2 | 2026-05-22: 1, 2026-05-23: 1 | 0.50-0.59: 1, 0.60+: 1 | mixed |

## Single-Factor Escape Check

### BTC Weakness

Inside `09h10h`:

- BTC: `3 TP / 1 SL`
- Win rate: `75.0%`
- Fast close: `4 / 4`
- Median hold: `20s`

Verdict: BTC weakness is not visible inside `09h10h` in this sample.

Caveat: three of the four BTC rows are from `2026-05-23`, and the only BTC loss is from `2026-05-21`. BTC survival is candidate-grade, not durable.

### NO Weakness

Inside `09h10h`:

- NO: `4 TP / 5 SL`
- Win rate: `44.4%`
- Fast close: `9 / 9`
- Median hold: `11s`

Verdict: NO weakness does not fully disappear.

The NO side improves versus the failure-triangle sample, but it remains below 50% win rate and all NO trades are fast closes. `ETH + NO + OPENING` is the main weak pocket at `2 TP / 3 SL`.

### ACTIVE Weakness

Inside `09h10h`:

- ACTIVE: `3 TP / 2 SL`
- Win rate: `60.0%`
- Fast close: `4 / 5`
- Median hold: `22s`

Verdict: ACTIVE weakness partially escapes inside `09h10h`.

This is one of the cleaner reads: prior pressure work showed ACTIVE outside `09h10h` was poor, while inside `09h10h` ACTIVE is net positive. Still, the sample is only five trades.

## Direct Answer

Does `09h10h` escape the failure triangle?

Verdict: PARTIAL_SURVIVAL.

Reason:

- It survives BTC weakness directionally: `BTC 3 TP / 1 SL`.
- It survives ACTIVE weakness directionally: `ACTIVE 3 TP / 2 SL`.
- It does not fully survive NO weakness: `NO 4 TP / 5 SL`.
- It is date-concentrated: `2026-05-23` carries most positive evidence.
- The current path-truth failure-triangle sample has no 09h/10h trades, so same-sample confirmation is unavailable.

## Classification

Primary verdict: `PARTIAL_SURVIVAL`

Secondary warning: `INSUFFICIENT_SAMPLE`

Rejected verdicts:

- `SURVIVES`: too strong because NO remains mixed/weak and the edge is date-concentrated.
- `FAILS`: too harsh because BTC and ACTIVE both improve meaningfully inside `09h10h`.
- `INSUFFICIENT_SAMPLE` as sole verdict: sample size is thin, but there is enough directional evidence to classify partial survival.

## Three Future Options

OPTION 1 - SAFE EV PRESERVATION:

Keep `09h10h` as a research label only. Continue collecting paper evidence without changing strategy, risk, stops, thresholds, or live behavior.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:

Prioritize read-only monitoring of future `09h10h` rows until there are at least 30 matched trades, 8 BTC trades, 10 NO trades, and 10 ACTIVE trades inside the bucket.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:

Run a later offline-only comparison of `09h10h` versus the path-truth failure triangle once a completed path-truth date includes actual 09h/10h trades.

Recommended option: OPTION 1 now, with OPTION 2 as the next research monitor.

## Final Status

Files created:

- `docs/research/session_edge/session_09h10h_failure_escape_audit.md`

Tests run: none. This was a read-only documentation and evidence audit.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No
