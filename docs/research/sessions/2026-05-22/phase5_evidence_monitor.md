# Phase 5 Evidence Accumulation Monitor

Date: 2026-05-22

Scope: read-only monitor of Phase 5 quote-age evidence toward Phase 6 readiness.

Runtime behavior changed: No.

Live behavior changed: No.

Paper launch: No.

Replay run: No.

## Clean Runs Included

Included clean Phase 5 run:

```text
20260522T082440Z_32952_1b709e78
```

Clean-run filter:

- contains non-null Phase 5 quote-age fields
- no visible `market_analysis_exception` events
- trade journal can be joined to execution quote-age evidence by `paper_trade_replay_key`

Current qualifying evidence is still one run only. Earlier May 22 runs either predate Phase 5 quote-age emission or have no non-null `quote_age_at_submit_ms` / `quote_age_at_fill_ms` coverage.

## Current Coverage

| Metric | Current |
|---|---:|
| clean Phase 5 runs | 1 |
| paired trades with quote-age linkage | 3 |
| trade_open | 3 |
| trade_close | 3 |
| order_submit_attempt with `quote_age_at_submit_ms` | 6 / 6 |
| paper_fill with `quote_age_at_submit_ms` | 6 / 6 |
| paper_fill with `quote_age_at_fill_ms` | 6 / 6 |
| market_analysis_exception | 0 |

## Readiness Stop Conditions

| Stop condition | Required | Current | Remaining |
|---|---:|---:|---:|
| paired trades | 20 | 3 | 17 |
| BTC trades | 5 | 0 | 5 |
| ETH trades | 5 | 3 | 2 |
| TP | 5 | 1 | 4 |
| SL | 5 | 2 | 3 |
| 60s+ bucket or strong quote-aging effect | 1 qualifying condition | 0 | 1 |

Phase 6 readiness status:

```text
COLLECT_MORE_EVIDENCE
```

## Distribution

All paper fills with `quote_age_at_fill_ms`:

| Bucket | Count |
|---|---:|
| 0-5s | 0 |
| 5-15s | 2 |
| 15-30s | 2 |
| 30-60s | 2 |
| 60s+ | 0 |

By fill intent:

| Intent | Fills | Mean fill age | Buckets |
|---|---:|---:|---|
| ENTRY | 3 | 31,640 ms | 15-30s: 1, 30-60s: 2 |
| EXIT | 3 | 11,539 ms | 5-15s: 2, 15-30s: 1 |

By quote source:

| Quote source | Fills | Buckets |
|---|---:|---|
| `display_snapshot_sampling` | 5 | 5-15s: 1, 15-30s: 2, 30-60s: 2 |
| `decision_cycle_fetch` | 1 | 5-15s: 1 |

## Asset Segmentation

Paired trades:

| Asset | Trades | TP | SL | WIN | LOSS |
|---|---:|---:|---:|---:|---:|
| BTC | 0 | 0 | 0 | 0 | 0 |
| ETH | 3 | 1 | 2 | 1 | 2 |

Fill events:

| Asset | Paper fills | Buckets |
|---|---:|---|
| BTC | 0 | unavailable |
| ETH | 6 | 5-15s: 2, 15-30s: 2, 30-60s: 2 |

Asset verdict: BTC evidence is still absent. ETH still needs 2 more paired trades to satisfy the minimum asset stop condition.

## Outcome Segmentation

Entry-side quote age:

| Segment | Trades | Mean entry fill age | Buckets |
|---|---:|---:|---|
| TP / WIN | 1 | 26,164 ms | 15-30s: 1 |
| SL / LOSS | 2 | 34,378 ms | 30-60s: 2 |

Exit-side quote age:

| Segment | Trades | Mean exit fill age | Buckets |
|---|---:|---:|---|
| TP / WIN | 1 | 17,911 ms | 15-30s: 1 |
| SL / LOSS | 2 | 8,353 ms | 5-15s: 2 |

Interpretation:

- The weak pattern remains entry-side only: current SL entries used older quotes than the single TP entry.
- Exit-side age does not support the same pattern.
- The sample is too small to call this an effect, and there is no 60s+ bucket evidence yet.

## Lifecycle Segmentation

| Lifecycle field | Observed value | Count |
|---|---|---:|
| execution `lifecycle_phase` | OPENING_SCAN | 6 fills |
| trade-close `lifecycle_phase` | UNKNOWN | 3 closes |

Lifecycle verdict: no meaningful lifecycle differentiation yet.

## Current Distance To READY_FOR_PHASE6

The monitor is short by:

- 17 paired trades
- 5 BTC trades
- 2 ETH trades
- 4 TP outcomes
- 3 SL outcomes
- at least one 60s+ quote-age bucket or substantially stronger evidence of quote-aging effect

## Recommendation

Phase 6 recommendation:

```text
COLLECT_MORE_EVIDENCE
```

Reason:

- current sample is only 15% of the paired-trade minimum
- BTC coverage is 0%
- TP coverage is 20% of minimum
- SL coverage is 40% of minimum
- no 60s+ quote-age bucket has appeared
- observed quote-aging relationship is only a small entry-side hypothesis, not readiness evidence

Do not tune stale-quote thresholds from this sample.

## Historical BTC Coverage Hunt — 2026-05-22

### Scope

Read-only sweep of all historical execution_log and trade_journal JSONL files (2026-05-08 through 2026-05-21) for BTC `trade_open`, `trade_close`, `paper_fill`, and Phase 5 quote-age fields. Objective: determine whether historical data can accelerate Phase 6 readiness.

### Files Scanned

| Log type | Dates | BTC-event files |
|---|---|---|
| `execution_log/*.jsonl` | 2026-05-08 to 2026-05-21 (13 files) | all |
| `trade_journal/*.jsonl` | 2026-05-08 to 2026-05-21 (12 files) | all |

### Historical BTC Event Counts

| Date | BTC fills | BTC trade_open | BTC trade_close | replay_key | model_ready | quote_lineage | quote_age |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-05-08 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-05-09 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-05-10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-05-11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-05-12 | 125 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-05-13 | 55 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-05-14 | 71 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-05-15 | 324 | 0 | 0 | 0 | 20 | 0 | 0 |
| 2026-05-17 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-05-18 | 13 | 4 | 5 | 8 | 8 | 0 | 0 |
| 2026-05-19 | 10 | 5 | 5 | 10 | 10 | 0 | 0 |
| 2026-05-20 | 10 | 5 | 5 | 10 | 10 | 0 | 0 |
| 2026-05-21 | 14 | 7 | 7 | 14 | 14 | 0 | 0 |
| **Total** | **622** | **21** | **22** | **42** | **62** | **0** | **0** |

### Phase 5 Field Coverage in Historical Data

| Field | Historical fills with key | Historical fills with non-null value |
|---|---:|---:|
| `quote_age_at_fill_ms` | **0 / 622** | **0 / 622** |
| `quote_age_at_submit_ms` | **0 / 622** | **0 / 622** |
| `quote_lineage_id` | **0 / 622** | **0 / 622** |
| `quote_capture_ts` | **0 / 622** | **0 / 622** |
| `fill_ts` | **0 / 622** | **0 / 622** |

All Phase 5 (and Phase 1–4) fields are completely absent from historical fills. These phases were implemented on 2026-05-22.

### Best Historical BTC Run

Run `20260521T133858Z_45768_ed644` (May 21):

- 4 BTC fills, `model_output_ready=True`, `paper_trade_replay_key` present (both YES and NO sides)
- Lifecycle phase: `OPENING_SCAN`, EV after spread: `0.102`
- `model_handoff_stage=MODEL_OUTPUT_SERIALIZED` on trade_open
- `trade_result=None`, `pnl=None` — trade-close outcomes not populated for these runs
- All Phase 1–5 fields: KEY_MISSING (pre-instrumentation data)

### Why Historical Evidence Cannot Accelerate Phase 6

1. **`quote_age_at_fill_ms` requires Phase 4 + Phase 1/2.** It needs `quote_capture_ts` (Phase 4) and `fill_ts` (Phase 2). Both are absent from all historical fills.
2. **Backfilling is prohibited.** The quote lineage contract (`quote_lineage_contract_v1.md`) and JSONL compatibility rules explicitly prohibit historical JSONL rewrite. Backfilling derived fields into historical records requires a separate offline report, not runtime JSONL rewrite — and offline-derived age values would not qualify as Phase 5 evidence.
3. **No `fill_ts` exists.** Without a live-captured `fill_ts`, the fill-time quote age cannot be computed retroactively with any integrity. The timestamp would need to be fabricated.
4. **Trade outcomes are unpopulated.** Historical closes have `trade_result=None`, `pnl=None` — the trade journal was not recording outcomes for these runs. The TP/SL stop conditions cannot be satisfied from this data.
5. **`market_analysis_exception` not auditable.** The exception filter (`exception=0`) cannot be verified for pre-instrumentation runs because the field was not present.

### Clean BTC Runs That Could Contribute (If Re-Run Under Phase 5)

The May 18–21 BTC runs represent real market conditions where the model was activated (`MODEL_OUTPUT_SERIALIZED`) and trades were placed. These markets are closed (5-minute expiry). Re-running paper sessions against new BTC markets is the only path to BTC Phase 5 evidence.

| Clean-run window | BTC fills (pre-Phase5) | model_ready fills | TP/SL recorded |
|---|---:|---:|---:|
| 2026-05-18 | 8 | 8 | No (null) |
| 2026-05-19 | 10 | 10 | No (null) |
| 2026-05-20 | 10 | 10 | No (null) |
| 2026-05-21 | 14 | 14 | No (null) |

These represent 42 fills that would have been valid evidence — but were generated before Phase 5 instrumentation existed.

### Verdict

Historical BTC data cannot contribute to Phase 6 readiness. Zero historical fills carry Phase 5 fields. Backfilling is prohibited. The evidence corpus remains at the current Phase 5 run count only. BTC coverage requires continued live paper sessions under Phase 5 instrumentation.

```text
HISTORICAL_EVIDENCE: NONE — PRE-INSTRUMENTATION
```

## Current Distance To READY_FOR_PHASE6 (Updated Post-Hunt)

All stop conditions are unchanged. The historical hunt confirms no shortcut exists.

- 17 paired trades remaining
- 5 BTC trades remaining (confirmed: zero historical BTC Phase 5 fills)
- 2 ETH trades remaining
- 4 TP outcomes remaining
- 3 SL outcomes remaining
- at least one 60s+ quote-age bucket

## Recommendation

Phase 6 recommendation (updated post historical BTC hunt):

```text
COLLECT_MORE_EVIDENCE
```

Reason:

- Historical sweep confirmed zero historical BTC Phase 5 quote-age evidence
- No backfill path exists under current contract rules
- All BTC Phase 5 evidence must come from new live paper sessions
- Evidence corpus is 3 ETH paired trades only — 15% of minimum
- BTC coverage: 0 of required 5 paired trades
- Historical hunt does not change the recommendation, but closes the question: no hidden BTC evidence exists

## Next Monitor Update Trigger

Update this monitor after any clean run with non-null Phase 5 quote-age fields, especially if it adds:

- BTC paired trades
- TP outcomes
- 60s+ quote-age fills
- non-OPENING_SCAN lifecycle coverage
