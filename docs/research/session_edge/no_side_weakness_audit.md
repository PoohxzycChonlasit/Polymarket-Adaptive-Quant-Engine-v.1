# NO Side Weakness Audit

Date: 2026-05-25

Scope: read-only audit of whether NO-side weakness is global, session-dependent, asset-specific, lifecycle-specific, or an artifact.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Role Routing

Primary role: `10_BACKTEST_REPLAY_AGENT.md`

Supporting roles:

- `16_PAPER_EVALUATION_AGENT.md`
- `11_OBSERVABILITY_INCIDENT_AGENT.md`
- `07_TEST_CI_AGENT.md`

Why selected: this is an offline outcome/session/lifecycle segmentation audit using trade-journal and path-truth evidence. It does not authorize runtime, strategy, risk, stoploss, field-wiring, or live changes.

## Sources Inspected

- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/research/session_edge/failure_triangle_audit.md`
- `docs/research/session_edge/session_09h10h_failure_escape_audit.md`
- `docs/research/session_edge/session_pressure_comparison_audit.md`
- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`

Files intentionally ignored:

- `polymarket/trader.py`
- `polymarket/order_manager.py`
- `utils/risk_manager.py`
- wallet/live config
- replay execution paths

## Method

Two evidence lenses are kept separate:

1. Recent trade-journal window: `2026-05-21` through `2026-05-25`.
2. Path-truth-backed subset: current rows with matching passive `path_truth` coverage, concentrated on `2026-05-24` and `2026-05-25`.

Pairing method:

- `trade_open` rows paired to `trade_close` rows by run, asset, and selected side order.
- Lifecycle stage comes from paired `trade_open.lifecycle_phase`.
- Outcome comes from close reason:
  - `take_profit_target_reached` -> `TP`
  - `stop_loss` / `stop_loss_hit` -> `SL`
- Hold uses `trade_close.hold_seconds`.
- Price bucket derives from entry price.

Important note:

- Prior failure-triangle context showed `NO = 1 TP / 8 SL`.
- The latest path-truth-backed NO evidence has grown to `1 TP / 11 SL`.
- The audit uses the latest local evidence while retaining the prior finding as the baseline context.

## Overall NO Evidence

| Scope | NO Trades | TP | SL | Win Rate | Median Hold | Fast Close | Hold Buckets | Path Truth Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Recent trade-journal window | 85 | 26 | 59 | 30.6% | 11s | 97.6% | 0-15s: 47, 15-30s: 20, 30-45s: 12, 45-60s: 4, 60s+: 2 | 12 / 85 |
| Path-truth-backed subset | 12 | 1 | 11 | 8.3% | 22.5s | 91.7% | 0-15s: 4, 15-30s: 6, 45-60s: 1, 60s+: 1 | 12 / 12 |

Comparison to YES in the same recent trade-journal window:

- YES: `27 TP / 50 SL`, `35.1%` win rate.
- NO: `26 TP / 59 SL`, `30.6%` win rate.

Interpretation:

NO is weak, but the broad recent window is not a clean pure-side diagnosis because YES is also weak. The path-truth-backed subset is much more severe and keeps NO weakness as an active candidate.

## Required Splits

Recent trade-journal window: `2026-05-21` through `2026-05-25`.

| Bucket | Trades | TP | SL | Win Rate | Median Hold | Fast Close | Hold Buckets | Session Mix | Price Buckets | Path Truth Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| BTC + NO + OPENING | 19 | 4 | 15 | 21.1% | 8s | 94.7% | 0-15s: 13, 15-30s: 3, 30-45s: 2, 60s+: 1 | 04h, 05h, 09h10h, 22h, 03h, 06h, 12h, 15h, 17h, 07h | 0.40-0.49: 5, 0.50-0.59: 9, 0.60+: 4, <0.40: 1 | 3 / 19 |
| BTC + NO + ACTIVE | 6 | 1 | 5 | 16.7% | 10.5s | 100.0% | 0-15s: 5, 45-60s: 1 | 19h, 11h, 16h, 17h, 03h | <0.40: 1, 0.40-0.49: 2, 0.50-0.59: 2, 0.60+: 1 | 1 / 6 |
| ETH + NO + OPENING | 52 | 19 | 33 | 36.5% | 17s | 98.1% | 0-15s: 23, 15-30s: 15, 30-45s: 10, 45-60s: 3, 60s+: 1 | broad, includes 02h, 09h10h, 16h | 0.40-0.49: 8, 0.50-0.59: 43, 0.60+: 1 | 7 / 52 |
| ETH + NO + ACTIVE | 8 | 2 | 6 | 25.0% | 8s | 100.0% | 0-15s: 6, 15-30s: 2 | 06h, 09h10h, 13h, 15h, 16h, 05h | 0.40-0.49: 2, 0.50-0.59: 4, 0.60+: 2 | 1 / 8 |
| 09h10h + NO | 9 | 4 | 5 | 44.4% | 11s | 100.0% | 0-15s: 7, 15-30s: 1, 45-60s: 1 | 09h10h only | 0.50-0.59: 8, 0.60+: 1 | 0 / 9 |
| 02h + NO | 5 | 0 | 5 | 0.0% | 7s | 100.0% | 0-15s: 3, 15-30s: 2 | 02h only | 0.50-0.59: 5 | 1 / 5 |
| 16h + NO | 6 | 2 | 4 | 33.3% | 18s | 100.0% | 0-15s: 3, 15-30s: 2, 30-45s: 1 | 16h only | 0.40-0.49: 2, 0.50-0.59: 3, 0.60+: 1 | 0 / 6 |
| OPENING + NO | 71 | 23 | 48 | 32.4% | 14s | 97.2% | 0-15s: 36, 15-30s: 18, 30-45s: 12, 45-60s: 3, 60s+: 2 | broad | 0.40-0.49: 13, 0.50-0.59: 52, 0.60+: 5, <0.40: 1 | 10 / 71 |
| ACTIVE + NO | 14 | 3 | 11 | 21.4% | 10s | 100.0% | 0-15s: 11, 15-30s: 2, 45-60s: 1 | broad | 0.40-0.49: 4, 0.50-0.59: 6, 0.60+: 3, <0.40: 1 | 2 / 14 |

## Path-Truth-Backed NO Splits

This subset is smaller but has direct path-truth coverage.

| Bucket | Trades | TP | SL | Win Rate | Median Hold | Fast Close | Hold Buckets | Session Mix | Price Buckets | Path Truth Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| BTC + NO + OPENING | 3 | 0 | 3 | 0.0% | 27s | 66.7% | 0-15s: 1, 15-30s: 1, 60s+: 1 | 04h, 07h, 06h | 0.40-0.49: 1, 0.50-0.59: 2 | 3 / 3 |
| BTC + NO + ACTIVE | 1 | 0 | 1 | 0.0% | 8s | 100.0% | 0-15s: 1 | 17h | 0.40-0.49: 1 | 1 / 1 |
| ETH + NO + OPENING | 7 | 0 | 7 | 0.0% | 22s | 100.0% | 0-15s: 2, 15-30s: 4, 45-60s: 1 | 05h, 07h, 14h, 02h, 03h, 06h | 0.50-0.59: 6, 0.60+: 1 | 7 / 7 |
| ETH + NO + ACTIVE | 1 | 1 | 0 | 100.0% | 23s | 100.0% | 15-30s: 1 | 05h | 0.50-0.59: 1 | 1 / 1 |
| 09h10h + NO | 0 | 0 | 0 | N/A | N/A | N/A | none | none | none | 0 / 0 |
| 02h + NO | 1 | 0 | 1 | 0.0% | 22s | 100.0% | 15-30s: 1 | 02h | 0.50-0.59: 1 | 1 / 1 |
| 16h + NO | 0 | 0 | 0 | N/A | N/A | N/A | none | none | none | 0 / 0 |
| OPENING + NO | 10 | 0 | 10 | 0.0% | 23s | 90.0% | 0-15s: 3, 15-30s: 5, 45-60s: 1, 60s+: 1 | 04h, 05h, 07h, 14h, 02h, 03h, 06h | 0.40-0.49: 1, 0.50-0.59: 8, 0.60+: 1 | 10 / 10 |
| ACTIVE + NO | 2 | 1 | 1 | 50.0% | 15.5s | 100.0% | 0-15s: 1, 15-30s: 1 | 05h, 17h | 0.40-0.49: 1, 0.50-0.59: 1 | 2 / 2 |

Path-truth interpretation:

- The sharpest confirmed weakness is `OPENING + NO`: `0 TP / 10 SL`.
- `ETH + NO + OPENING` remains a major weak pocket: now `0 TP / 7 SL` in latest path-truth-backed rows.
- `ACTIVE + NO` is too thin at `1 TP / 1 SL`; it does not rescue the NO side.

## Session Dependence

Recent NO session splits:

| Session | NO Trades | TP | SL | Win Rate | Median Hold | Fast Close | Read |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 02h | 5 | 0 | 5 | 0.0% | 7s | 100.0% | hostile |
| 09h10h | 9 | 4 | 5 | 44.4% | 11s | 100.0% | partial recovery, still mixed |
| 16h | 6 | 2 | 4 | 33.3% | 18s | 100.0% | weak/mixed |
| 03h | 10 | 5 | 5 | 50.0% | 7.5s | 100.0% | neutral |
| 06h | 11 | 5 | 6 | 45.5% | 28s | 100.0% | partial recovery |
| 07h | 6 | 0 | 6 | 0.0% | 9s | 100.0% | hostile |

Interpretation:

NO is session-dependent. `02h` and `07h` are hostile, `09h10h` and `06h` partially recover, and `03h` is neutral. This rejects a simple "NO always fails the same way" rule.

## Direct Answers

### Is NO globally weak?

Verdict: yes as a candidate, strongest in path-truth-backed evidence.

Recent NO win rate is `30.6%`, which is weak. The path-truth-backed subset is much worse at `1 TP / 11 SL`. However, YES is also weak in the same recent window, so NO is not the only adverse side.

### Only BTC?

Verdict: no.

BTC + NO is weak (`5 TP / 20 SL` combined across OPENING and ACTIVE), but ETH + NO is also weak (`21 TP / 39 SL`). Path-truth-backed ETH + NO + OPENING is `0 TP / 7 SL`, so this is not BTC-only.

### Only ETH?

Verdict: no.

BTC + NO is weaker than ETH + NO in the broad recent window. Path-truth-backed BTC + NO is also `0 TP / 4 SL`.

### Only OPENING?

Verdict: no, but OPENING is the clearest confirmed path-truth failure.

Opening NO is `23 TP / 48 SL` in the recent window and `0 TP / 10 SL` in path-truth-backed rows. ACTIVE NO is also weak in the recent window at `3 TP / 11 SL`, so weakness is not opening-only.

### Only ACTIVE?

Verdict: no.

ACTIVE NO is poor, but OPENING NO has much larger sample size and the strongest path-truth-backed failure. This is not active-only.

### Only hostile sessions?

Verdict: partly.

Hostile sessions explain a lot of the damage: `02h + NO` is `0 TP / 5 SL`, and `07h + NO` is `0 TP / 6 SL`. But NO remains weak across broader non-02h/non-07h rows, so hostile sessions do not explain all of it.

## Classification

Primary classification:

- NO_SESSION_DEPENDENT
- INSUFFICIENT_SAMPLE

Secondary candidate:

- NO_GLOBAL_WEAKNESS

Rejected classifications:

- NO_BTC_ONLY
- NO_ETH_ONLY
- NO_OPENING_ONLY
- NO_ACTIVE_ONLY
- ONE_DATE_ARTIFACT

Reason:

NO weakness appears across asset and lifecycle splits, but it changes materially by session. The most reliable current path-truth finding is `OPENING + NO` weakness, especially `ETH + NO + OPENING`, but the broader recent window shows partial recovery in `09h10h`, `03h`, and `06h`.

## Three Future Options

OPTION 1 - SAFE EV PRESERVATION:

Keep NO-side weakness as a research label only. No strategy, stoploss, risk, threshold, field-wiring, or live change.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:

Continue path-truth collection until there are at least 20 NO path-truth-backed trades, with at least 5 each in BTC, ETH, OPENING, ACTIVE, and at least one `09h10h` NO path-truth row.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:

Once path-truth coverage is deeper, compare NO losses by quote age, lifecycle stage, price bucket, and session to separate adverse selection from session-timing effects.

Recommended option: OPTION 2.

## Final Status

Files created:

- `docs/research/session_edge/no_side_weakness_audit.md`

Tests run: none. This was a read-only evidence and documentation audit.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No
