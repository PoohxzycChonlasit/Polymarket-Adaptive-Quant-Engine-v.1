# 09h Recurrence Audit

Generated: 2026-05-23  
Scope: read-only recurrence audit across historical `trade_journal`, `execution_log`, and `decision_log` JSONL files.  
Hours are UTC.

No code, replay, runtime, policy, strategy, risk, execution, live, or S3 changes were made.

## Source Coverage

Files scanned:

- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/execution_log/*.jsonl`
- `runtime/quant_data/decision_log/*.jsonl`

Dates present in one or more source streams:

`2026-05-08`, `2026-05-09`, `2026-05-10`, `2026-05-11`, `2026-05-12`, `2026-05-13`, `2026-05-14`, `2026-05-15`, `2026-05-17`, `2026-05-18`, `2026-05-19`, `2026-05-20`, `2026-05-21`, `2026-05-22`, `2026-05-23`.

## Schema Caveat

Historical trade rows before the latest outcome-truth instrumentation often lack `trade_result`. This audit separates:

- Confirmed TP / SL: uses `trade_result` when present.
- Proxy W / L: uses PnL sign only for legacy rows where `trade_result` is missing.

Do not treat proxy W / L as equivalent to confirmed TP / SL. It is recurrence context only.

## Classification

Classification: `SESSION_EDGE_CANDIDATE`

Rationale:

- 09h is not a single-day anomaly: across all historical rows, 09h has 34 closed trades, 24 proxy wins, 10 proxy losses, and positive mean PnL.
- Phase 6 era confirms 09h outperformed 02h and the all-day baseline.
- The edge is not proven as a pure time-of-day rule because multiple 09h dates were negative or no-trade, and confirmed ACTIVE TP evidence is still concentrated on 2026-05-23.
- The better interpretation is a candidate session window that can host a favorable market regime, not an always-on 09h policy.

## Aggregate Comparison

### All Historical Rows

| Bucket | Trades | Confirmed TP | Confirmed SL | Proxy W | Proxy L | BTC | ETH | OPENING W / N | ACTIVE W / N | Mean PnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 09h | 34 | 5 | 1 | 24 | 10 | 18 | 16 | 9 / 16 | 2 / 3 | +0.292287 |
| 02h | 75 | 0 | 8 | 53 | 22 | 62 | 13 | 1 / 10 | 0 / 6 | +0.374056 |
| All-day | 704 | 11 | 21 | 532 | 172 | 566 | 138 | 69 / 146 | 7 / 33 | +0.389449 |

Historical mean PnL is heavily influenced by older pre-outcome-truth rows with larger PnL scale. Use the Phase 6 era table below for cleaner interpretation.

### Phase 6 / Outcome-Truth Era Rows

| Bucket | Trades | Confirmed TP | Confirmed SL | Proxy W | Proxy L | BTC | ETH | OPENING W / N | ACTIVE W / N | Mean PnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 09h | 8 | 5 | 1 | 5 | 3 | 2 | 6 | 3 / 5 | 2 / 3 | +0.003448 |
| 02h | 10 | 0 | 8 | 0 | 10 | 3 | 7 | 0 / 6 | 0 / 4 | -0.007449 |
| All-day | 70 | 11 | 21 | 27 | 43 | 16 | 54 | 24 / 54 | 4 / 19 | -0.000713 |

Phase 6 read: 09h is materially better than 02h and better than the all-day baseline, but sample size is still small.

## 09h By Date

| Date | Trades | BTC | ETH | Confirmed TP | Confirmed SL | Proxy W | Proxy L | OPENING W / N | ACTIVE W / N | Mean PnL | Quote Stale | Decision Rows | Top Skip Reasons |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| 2026-05-08 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 / 0 | n/a | n/a | 0 | none |
| 2026-05-09 | 9 | 9 | 0 | 0 | 0 | 7 | 2 | 0 / 0 | 0 / 0 | +0.432222 | n/a | 26 | `unknown:26` |
| 2026-05-10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 / 0 | n/a | n/a | 17 | `unknown:17` |
| 2026-05-11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 / 0 | n/a | n/a | 12 | `time_unsafe:10`, `empty_book:2` |
| 2026-05-12 | 6 | 6 | 0 | 0 | 0 | 6 | 0 | 0 / 0 | 0 / 0 | +1.000000 | n/a | 31 | `time_unsafe:18`, `frequency_cooldown:6`, `empty_book:6` |
| 2026-05-13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 / 0 | n/a | n/a | 110 | `time_unsafe:86`, `empty_book:18`, `warmup_pending:6` |
| 2026-05-14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 / 0 | n/a | n/a | 23 | `time_unsafe:23` |
| 2026-05-15 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 / 0 | n/a | n/a | 0 | none |
| 2026-05-17 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 / 0 | n/a | n/a | 0 | none |
| 2026-05-18 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0 / 2 | 0 / 0 | -0.007324 | n/a | 132 | `time_unsafe:78`, `frequency_cooldown:48`, `risk_plan_zero:6` |
| 2026-05-19 | 4 | 0 | 4 | 0 | 0 | 4 | 0 | 4 / 4 | 0 / 0 | +0.009963 | n/a | 201 | `time_unsafe:82`, `frequency_cooldown:81`, `risk_plan_zero:32` |
| 2026-05-20 | 4 | 0 | 4 | 0 | 0 | 2 | 2 | 2 / 4 | 0 / 0 | +0.000143 | n/a | 177 | `time_unsafe:84`, `frequency_cooldown:84`, `risk_plan_zero:5` |
| 2026-05-21 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 / 1 | 0 / 0 | -0.005581 | n/a | 988 | `delta_extreme:584`, `confidence_too_low:276`, `time_unsafe:124` |
| 2026-05-22 | 4 | 0 | 4 | 1 | 1 | 1 | 3 | 1 / 3 | 0 / 1 | -0.006653 | n/a | 3420 | `delta_extreme:1974`, `confidence_too_low:863`, `time_unsafe:423` |
| 2026-05-23 | 4 | 2 | 2 | 4 | 0 | 4 | 0 | 2 / 2 | 2 / 2 | +0.013548 | n=4 mean=9974.105ms | 1998 | `delta_extreme:1064`, `confidence_too_low:546`, `time_unsafe:236` |

## 02h By Date

| Date | Trades | BTC | ETH | Confirmed TP | Confirmed SL | Proxy W | Proxy L | OPENING W / N | ACTIVE W / N | Mean PnL | Quote Stale | Decision Rows | Top Skip Reasons |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| 2026-05-08 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 / 0 | n/a | n/a | 0 | none |
| 2026-05-09 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 / 0 | n/a | n/a | 0 | none |
| 2026-05-10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 / 0 | n/a | n/a | 18 | `unknown:18` |
| 2026-05-11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 / 0 | n/a | n/a | 1 | `unknown:1` |
| 2026-05-12 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 / 0 | 0 / 0 | +1.000000 | n/a | 30 | `time_unsafe:24`, `empty_book:4`, `frequency_cooldown:2` |
| 2026-05-13 | 4 | 4 | 0 | 0 | 0 | 4 | 0 | 0 / 0 | 0 / 0 | +1.000000 | n/a | 107 | `time_unsafe:81`, `empty_book:22`, `frequency_cooldown:4` |
| 2026-05-14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 / 0 | n/a | n/a | 95 | `time_unsafe:70`, `empty_book:21`, `stale_data:3` |
| 2026-05-15 | 52 | 52 | 0 | 0 | 0 | n/a | n/a | 0 / 0 | 0 / 0 | +0.426346 | n/a | 0 | none |
| 2026-05-17 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 | 0 / 0 | n/a | n/a | 0 | none |
| 2026-05-18 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0 / 0 | 0 / 0 | -0.007815 | n/a | 69 | `frequency_cooldown:47`, `time_unsafe:18`, `risk_plan_zero:3` |
| 2026-05-19 | 2 | 1 | 1 | 0 | 0 | 1 | 1 | 0 / 1 | 0 / 1 | -0.000194 | n/a | 61 | `frequency_cooldown:41`, `time_unsafe:20` |
| 2026-05-20 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 0 / 1 | 0 / 0 | -0.004768 | n/a | 67 | `time_unsafe:39`, `frequency_cooldown:22`, `risk_plan_zero:6` |
| 2026-05-21 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0 / 2 | 0 / 1 | -0.010252 | n/a | 117 | `time_unsafe:71`, `frequency_cooldown:33`, `max_active_positions_per_market_reached:10` |
| 2026-05-22 | 2 | 2 | 0 | 0 | 0 | 0 | 2 | 0 / 2 | 0 / 0 | -0.004669 | n/a | 734 | `delta_extreme:441`, `confidence_too_low:182`, `time_unsafe:100` |
| 2026-05-23 | 8 | 1 | 7 | 0 | 8 | 0 | 8 | 0 / 4 | 0 / 4 | -0.008145 | n=8 mean=23146.514ms | 1410 | `delta_extreme:718`, `confidence_too_low:341`, `time_unsafe:179` |

Note: 2026-05-15 02h had 52 legacy BTC rows with older schema and no decision rows in the current `decision_log` set. Treat that block as historical context, not comparable Phase 6 evidence.

## Skip Reason Comparison

| Bucket | Top Skip Reasons |
|---|---|
| 09h | `delta_extreme:3622`, `confidence_too_low:1685`, `time_unsafe:1164`, `frequency_cooldown:369`, `empty_book:103` |
| 02h | `delta_extreme:1159`, `time_unsafe:602`, `confidence_too_low:523`, `frequency_cooldown:272`, `empty_book:73` |
| All-day | `delta_extreme:39048`, `confidence_too_low:16176`, `time_unsafe:13780`, `frequency_cooldown:3314`, `empty_book:2091` |

Skip reasons do not show a unique 09h admission regime. 09h shares the same dominant blockers as the all-day baseline. The apparent 09h edge comes from the subset of admitted trades, not from a radically different skip distribution.

## Interpretation

### Single-Day Anomaly?

No, not in the broad historical PnL-sign view.

09h had positive proxy behavior on multiple dates:

- 2026-05-09: 7 proxy wins / 2 proxy losses.
- 2026-05-12: 6 proxy wins / 0 proxy losses.
- 2026-05-19: 4 proxy wins / 0 proxy losses.
- 2026-05-20: 2 proxy wins / 2 proxy losses.
- 2026-05-23: 4 confirmed TP / 0 confirmed SL.

But the strongest confirmed outcome-truth evidence is still recent and small.

### Repeating Session Effect?

Yes, candidate only.

09h repeatedly appears as a productive session in legacy PnL-sign rows and remains positive in Phase 6 era. However, it is not clean:

- 2026-05-18 was negative.
- 2026-05-21 was negative.
- 2026-05-22 was negative overall despite one confirmed TP.

This supports `SESSION_EDGE_CANDIDATE`, not a hard clock-based rule.

### Time-of-Day Regime?

Possible, not proven.

The 09h window may coincide with a recurring liquidity or directional session, but current evidence does not prove the clock causes the edge. The same skip reasons dominate 09h, 02h, and all-day baselines. The meaningful distinction is outcome behavior among admitted trades.

### Market Regime Candidate?

09h can host a favorable market regime, but the regime is not always present.

2026-05-23 09h looked like trend/continuation plus opening dislocation. Earlier 09h sessions include both positive and negative outcomes. The clock is likely a filter for when a favorable regime may appear, not the regime itself.

## Final Determination

Classification: `SESSION_EDGE_CANDIDATE`

The 09h edge is not just a single-day anomaly, because historical 09h trades are often positive and Phase 6 09h outperformed both 02h and all-day baseline. It is also not yet a confirmed `MARKET_REGIME_CANDIDATE`, because the evidence is mixed by date, skip reasons are not unique, and confirmed ACTIVE TP recurrence is still too thin.

Recommended next evidence step: continue collecting Phase 6 outcome-truth rows and track 09h as a session candidate with separate OPENING and ACTIVE counters.

Runtime behavior changed: No  
Live behavior changed: No  
Tests: not run, docs-only  
Persistent tests unchanged
