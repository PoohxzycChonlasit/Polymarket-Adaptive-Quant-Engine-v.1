# Fast Close Distribution Audit

Date: 2026-05-25

Scope: read-only path truth distribution audit. No code changes. No runtime changes.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Source Evidence

Files inspected:

- `runtime/quant_data/path_truth/2026-05-24.jsonl`
- `runtime/quant_data/path_truth/2026-05-25.jsonl`
- `runtime/quant_data/trade_journal/2026-05-24.jsonl`
- `runtime/quant_data/trade_journal/2026-05-25.jsonl`

Snapshot note: `2026-05-25` is in-progress. Counts can grow while paper runtime remains active.

Join method:

- path truth trades were grouped by `run_id + trade_id`
- trade outcomes and durations were joined from `trade_journal` using `position_id` / `trade_id`
- all 25 path truth trades in this snapshot had `trade_journal.hold_seconds`

## Summary

| Metric | Count |
|---|---:|
| path truth trades | 25 |
| trades with joined hold_seconds | 25 |
| TP | 7 |
| SL | 18 |
| BTC | 8 |
| ETH | 17 |
| YES | 16 |
| NO | 9 |
| OPENING | 18 |
| ACTIVE | 7 |

Fast close definition for this audit:

```text
duration < 60 seconds
```

Fast-close share:

```text
22 / 25 = 88%
```

Only 3 trades reached 60s+ and all three had full checkpoint coverage.

## Duration Buckets

| Bucket | Trades | Share |
|---|---:|---:|
| 0-15s | 11 | 44% |
| 15-30s | 9 | 36% |
| 30-45s | 1 | 4% |
| 45-60s | 1 | 4% |
| 60s+ | 3 | 12% |

Interpretation:

- Most closes happen before the second scheduled checkpoint.
- The path truth writer is not missing later checkpoints for most partial trades; the trades are already closed.
- The sparse 45-60s and 60s+ buckets mean longer path evolution is still under-sampled.

## TP vs SL

| Bucket | TP | SL |
|---|---:|---:|
| 0-15s | 3 | 8 |
| 15-30s | 2 | 7 |
| 30-45s | 0 | 1 |
| 45-60s | 0 | 1 |
| 60s+ | 2 | 1 |
| Total | 7 | 18 |

Outcome interpretation:

- SL dominates the sample: 18 / 25 trades.
- Fast closes are not only losses: 5 TP trades closed under 30s.
- But the fastest bucket is loss-heavy: 8 SL vs 3 TP in 0-15s.
- 60s+ is small but more balanced: 2 TP vs 1 SL.

Verdict: fast close is compatible with both quick profit capture and quick stop-out, but the current sample leans toward adverse fast exits.

## BTC vs ETH

| Bucket | BTC | ETH |
|---|---:|---:|
| 0-15s | 5 | 6 |
| 15-30s | 2 | 7 |
| 30-45s | 0 | 1 |
| 45-60s | 0 | 1 |
| 60s+ | 1 | 2 |
| Total | 8 | 17 |

Outcome by asset:

| Asset | TP | SL |
|---|---:|---:|
| BTC | 0 | 8 |
| ETH | 7 | 10 |

Asset interpretation:

- BTC is concerning in this snapshot: 8 / 8 path-truth trades are SL.
- ETH contains all observed TP outcomes, but still has more SL than TP.
- BTC sample size is still small, but the all-SL split is a signal-quality or timing hypothesis worth tracking.

## YES vs NO

| Bucket | YES | NO |
|---|---:|---:|
| 0-15s | 8 | 3 |
| 15-30s | 5 | 4 |
| 30-45s | 1 | 0 |
| 45-60s | 0 | 1 |
| 60s+ | 2 | 1 |
| Total | 16 | 9 |

Outcome by side:

| Side | TP | SL |
|---|---:|---:|
| YES | 6 | 10 |
| NO | 1 | 8 |

Side interpretation:

- YES has more volume and most TPs, but still has more SL than TP.
- NO is weak in this sample: 8 SL vs 1 TP.
- The NO weakness overlaps with BTC and should not be over-interpreted until more dates are available.

## OPENING vs ACTIVE

Lifecycle mapping:

- `OPENING_SCAN` -> OPENING
- `ACTIVE_INVENTORY_TRADING` -> ACTIVE

| Bucket | OPENING | ACTIVE |
|---|---:|---:|
| 0-15s | 5 | 6 |
| 15-30s | 8 | 1 |
| 30-45s | 1 | 0 |
| 45-60s | 1 | 0 |
| 60s+ | 3 | 0 |
| Total | 18 | 7 |

Outcome by lifecycle:

| Lifecycle | TP | SL |
|---|---:|---:|
| OPENING | 5 | 13 |
| ACTIVE | 2 | 5 |

Lifecycle interpretation:

- ACTIVE closes are extremely fast: 6 / 7 close in 0-15s and none reach 60s.
- OPENING produces every 60s+ trade and the only full path coverage.
- ACTIVE fast closes look more like exit-rule or inventory-state behavior than path-truth writer failure.

## Session Split

| Session | Trades | 0-15s | 15-30s | 30-45s | 45-60s | 60s+ | TP | SL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `20260524T043315Z_29264_52c95bee` | 3 | 1 | 0 | 0 | 0 | 2 | 2 | 1 |
| `20260524T045213Z_24036_f64d2821` | 3 | 2 | 1 | 0 | 0 | 0 | 1 | 2 |
| `20260524T052743Z_26444_0defea84` | 9 | 2 | 4 | 1 | 1 | 1 | 4 | 5 |
| `20260524T134430Z_22940_add0ad1f` | 6 | 3 | 3 | 0 | 0 | 0 | 0 | 6 |
| `20260525T024022Z_53032_26cbf48f` | 4 | 3 | 1 | 0 | 0 | 0 | 0 | 4 |

Session interpretation:

- The first 2026-05-24 session had the healthiest duration/outcome mix.
- The late 2026-05-24 session and current 2026-05-25 snapshot are all SL and mostly sub-30s.
- Session effects are visible, but current evidence cannot separate market regime, signal quality, and risk mode effects.

## Is Fast Close Market Structure?

Answer: partly, but not only.

Evidence for market-structure involvement:

- These are 5-minute binary markets where price can move sharply near short horizons.
- Both TP and SL can occur quickly, which is consistent with fast-moving microstructure rather than writer failure.
- Path truth event_end rows align with trade closes; partial checkpoint coverage is mostly explained by short hold duration.

Evidence against pure market-structure explanation:

- BTC is 8 / 8 SL in this snapshot.
- NO is 8 / 9 SL.
- ACTIVE lifecycle closes are almost all under 15s and mostly SL.
- Session-level clustering shows some runs produce only SL fast closes.

Verdict:

```text
MIXED: market structure + strategy/exit behavior + possible signal-quality issue
```

## Is Fast Close Strategy Behavior?

Answer: yes, likely.

Evidence:

- Fast TP and fast SL both occur, implying exit thresholds can close trades before checkpoint 2.
- ACTIVE lifecycle closes are especially fast, suggesting position-state or exit-rule behavior after inventory is active.
- Fast close is not a path truth scheduler bug; it is real trade lifecycle behavior observed by trade journal duration.

This does not imply the strategy should be changed. It only means path truth should classify fast closes as a normal lifecycle outcome rather than a coverage failure.

## Is Fast Close A Signal Quality Issue?

Answer: plausible but not proven.

Evidence:

- SL dominates overall: 18 / 25.
- BTC is 0 TP / 8 SL.
- NO is 1 TP / 8 SL.
- Two recent sessions are all SL.

Counter-evidence:

- ETH has 7 TP.
- Fast TP exists in 0-15s and 15-30s buckets.
- Sample size and date diversity are still limited.

Verdict:

```text
POSSIBLE_SIGNAL_OR_TIMING_ISSUE; NEED_MORE_DATES
```

## Research Interpretation

Root problem:

Path truth partial coverage is mostly caused by actual fast closes, not missing checkpoint writes.

Quant interpretation:

- Fast closes are expected in this market type and current exit model.
- The adverse skew in BTC, NO, ACTIVE, and recent sessions deserves monitoring.
- Longer path truth is under-sampled; only 3 trades reached 60s+.
- Path truth is already useful for distinguishing scheduler coverage from lifecycle reality.

Risk / safety impact:

- No field wiring should occur from this audit.
- No strategy, risk, or execution change is justified by this sample alone.
- The all-SL BTC split is a caution flag, not an implementation mandate.

## Next Action

OPTION 1 - SAFE EV PRESERVATION:
Keep collecting path truth until the `EARLY_RESEARCH_GATE` has at least 3 completed dates, then rerun this distribution.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:
Run a later read-only session-level audit comparing risk mode, market regime, and fast-close buckets once more dates accumulate.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:
After the implementation gate, add observability-only identity fields so fast-close path truth can join more directly to candidate and decision context.

Recommendation:

```text
OPTION 1
```

Reason: current evidence is informative but still too thin and session-skewed for any runtime or policy decision.

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; docs-only/read-only audit.
