# Phase 5 Quote Age Distribution Audit

Date: 2026-05-22

Scope: read-only audit of Phase 5 quote age evidence before Phase 6.

Runtime behavior changed: No.

Live behavior changed: No.

Replay run: No.

Paper launch: No.

## Source Evidence

Primary clean Phase 5 run:

```text
20260522T082440Z_32952_1b709e78
```

Files inspected:

- `docs/research/sessions/2026-05-22/quote_age_phase5_validation.md`
- `runtime/quant_data/execution_log/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `runtime/quant_data/decision_log/2026-05-22.jsonl`
- `runtime/quant_data/system_health/2026-05-22.jsonl`

Other May 22 runs either predate Phase 5 quote-age emission or had no non-null `quote_age_at_submit_ms` / `quote_age_at_fill_ms` coverage. They were excluded from distribution conclusions.

## Coverage

Run-level coverage:

| Metric | Count |
|---|---:|
| paired trades | 3 |
| trade_open | 3 |
| trade_close | 3 |
| order_submit_attempt with `quote_age_at_submit_ms` | 6 / 6 |
| paper_fill with `quote_age_at_submit_ms` | 6 / 6 |
| paper_fill with `quote_age_at_fill_ms` | 6 / 6 |
| assets represented | ETH only |
| BTC fills | 0 |
| execution lifecycle phase represented | OPENING_SCAN only |

Trade outcomes:

| Outcome | Count | PnL |
|---|---:|---:|
| TP / win | 1 | +0.010254 |
| SL / loss | 2 | -0.019251 total |

## Bucket Definitions

| Bucket | Range |
|---|---|
| 0-5s | 0 ms to < 5,000 ms |
| 5-15s | 5,000 ms to < 15,000 ms |
| 15-30s | 15,000 ms to < 30,000 ms |
| 30-60s | 30,000 ms to < 60,000 ms |
| 60s+ | >= 60,000 ms |

## Overall Distribution

All Phase 5 paper fills:

| Field | n | min | mean | median | max |
|---|---:|---:|---:|---:|---:|
| `quote_age_at_fill_ms` | 6 | 7,768 | 21,590 | 22,038 | 34,467 |
| `quote_age_at_submit_ms` | 6 | 7,765 | 21,584 | 22,035 | 34,449 |

All fill buckets:

| Bucket | Count |
|---|---:|
| 0-5s | 0 |
| 5-15s | 2 |
| 15-30s | 2 |
| 30-60s | 2 |
| 60s+ | 0 |

By fill intent:

| Intent | n | Mean fill age | Buckets |
|---|---:|---:|---|
| ENTRY | 3 | 31,640 ms | 15-30s: 1, 30-60s: 2 |
| EXIT | 3 | 11,539 ms | 5-15s: 2, 15-30s: 1 |

## Per-Trade Join

Joined by `paper_trade_replay_key`.

| Trade | Asset | Side | Result | PnL | Entry fill age | Entry bucket | Exit fill age | Exit bucket | Hold seconds |
|---|---|---|---|---:|---:|---|---:|---|---:|
| 1 | ETH | YES | SL / loss | -0.001850 | 34,467 ms | 30-60s | 7,768 ms | 5-15s | 7 |
| 2 | ETH | NO | TP / win | +0.010254 | 26,164 ms | 15-30s | 17,911 ms | 15-30s | 30 |
| 3 | ETH | YES | SL / loss | -0.017401 | 34,289 ms | 30-60s | 8,939 ms | 5-15s | 12 |

## Outcome Segmentation

Entry-side fill age:

| Segment | n | Mean entry fill age | Buckets |
|---|---:|---:|---|
| TP / win | 1 | 26,164 ms | 15-30s: 1 |
| SL / loss | 2 | 34,378 ms | 30-60s: 2 |

Exit-side fill age:

| Segment | n | Mean exit fill age | Buckets |
|---|---:|---:|---|
| TP / win | 1 | 17,911 ms | 15-30s: 1 |
| SL / loss | 2 | 8,353 ms | 5-15s: 2 |

Interpretation:

- Entry quote age is directionally worse for losses in this tiny sample: both SL trades entered with 30-60s quotes, while the TP entered with a 15-30s quote.
- Exit quote age does not show the same pattern: SL exits used younger quotes than the TP exit.
- This suggests any quote-age/outcome effect, if real, is more likely tied to entry quote staleness than exit quote staleness.
- The sample is too small to treat this as a proven edge or blocker.

## Asset Segmentation

| Asset | Fills | Trades | Outcomes | Mean fill age |
|---|---:|---:|---|---:|
| ETH | 6 | 3 | TP: 1, SL: 2 | 21,590 ms |
| BTC | 0 | 0 | unavailable | unavailable |

Asset verdict: no BTC-vs-ETH comparison is possible yet. Current Phase 5 quote-age evidence is ETH-only.

## Lifecycle Segmentation

Execution lifecycle phase:

| Lifecycle phase | Fills | Mean fill age | Outcomes |
|---|---:|---:|---|
| OPENING_SCAN | 6 | 21,590 ms | TP: 1, SL: 2 |

Trade journal close lifecycle phase:

| Lifecycle phase | Closes |
|---|---:|
| UNKNOWN | 3 |

Lifecycle verdict:

- Execution-side lifecycle segmentation is not informative yet because all fills are `OPENING_SCAN`.
- Trade-close lifecycle is still `UNKNOWN`, so close-side lifecycle outcome analysis is not available from current evidence.

## Quote Source Segmentation

| Quote source | Fills | Mean fill age | Buckets |
|---|---:|---:|---|
| `display_snapshot_sampling` | 5 | 24,348 ms | 5-15s: 1, 15-30s: 2, 30-60s: 2 |
| `decision_cycle_fetch` | 1 | 7,768 ms | 5-15s: 1 |

Interpretation:

- `decision_cycle_fetch` produced the youngest observed quote, but only once.
- `display_snapshot_sampling` spans all observed stale-ish buckets, including both 30-60s entry fills.
- Phase 6 should preserve source segmentation because source may explain age distribution.

## Audit Questions

### Are winners younger quotes?

Entry-side: yes, directionally. The one TP entered on a 26.2s quote, while both SL entries used roughly 34.3-34.5s quotes.

Exit-side: no. The TP exit used a 17.9s quote, while SL exits used 7.8s and 8.9s quotes.

Verdict: weak entry-side signal only; insufficient sample.

### Are losers older quotes?

Entry-side: yes in this sample.

Exit-side: no.

Verdict: possible entry-staleness relationship, not proven.

### Do stale fills correlate with SL?

If stale means `quote_age_at_fill_ms >= 30,000`, then both stale entry fills were SL outcomes. No stale exits were observed.

Verdict: possible entry stale-fill risk, but only 2 stale entries and 3 paired trades. Treat as a hypothesis for Phase 6, not a conclusion.

### Any asset difference?

No. Phase 5 quote-age evidence in the clean run is ETH-only.

### Any lifecycle phase difference?

No. Execution-side lifecycle is all `OPENING_SCAN`; trade-close lifecycle is `UNKNOWN`.

## Phase 6 Implications

Phase 6 can compute `quote_stale_ms`, but the current sample is too small to tune thresholds or claim a causal stale-fill relationship.

Minimum useful Phase 6 audit targets:

- at least 30 paired trades with non-null quote ages
- both BTC and ETH represented
- separate entry and exit quote staleness
- preserve `quote_source`
- join `quote_stale_ms` to TP/SL, win/loss, lifecycle phase, and side
- keep threshold analysis descriptive until sample size improves

## Future Options

OPTION 1 - SAFE EV PRESERVATION:
Implement Phase 6 as observability-only `quote_stale_ms = max(quote_age_at_submit_ms, quote_age_at_fill_ms)` with no policy threshold or runtime block.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:
Collect more paper evidence first, targeting at least 30 paired trades before Phase 6.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:
Audit why entry quotes are older than exit quotes and why execution lifecycle remains all `OPENING_SCAN` while close lifecycle is `UNKNOWN`.

## Recommendation

Recommendation: `COLLECT_MORE_EVIDENCE`.

Reason:

- only 3 paired trades have Phase 5 quote-age/outcome linkage
- all linked trades are ETH
- no BTC comparison is available
- lifecycle segmentation is not informative yet
- the possible stale-entry/SL relationship is interesting but underpowered

Phase 6 should remain allowed as an observability-only field addition if needed, but not as a policy or threshold decision. Do not use this sample to define stale quote limits.
