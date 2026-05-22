# Execution Reality Harvest Monitor

Document type: read-only accumulation monitor.

Updated: 2026-05-22

Runtime behavior changed: No.

Live behavior changed: No.

Paper launch: No.

Replay run: No.

---

## Era Boundaries

| Era | Date range | Description |
|---|---|---|
| **Pre-instrumentation archive** | 2026-05-08 → 2026-05-21 | No Phase 1–5 fields. `fill_ts`, `quote_capture_ts`, `quote_lineage_id`, `quote_age_at_fill_ms` all absent. Backfill prohibited. |
| **Instrumentation era** | 2026-05-22 → present | Phase 1–5 fields present on all paper_fill and order_submit_attempt events. |

Evidence eras must not be mixed. All readiness gates are evaluated on instrumentation-era data only.

Pre-instrumentation archive: swept exhaustively on 2026-05-22. Zero Phase 5 fields found across 622 historical BTC fills. See Historical BTC Coverage Hunt section for full details.

---

## Clean-Run Filter

A run qualifies for this monitor if:

- Non-null `quote_age_at_fill_ms` present on paper_fill events
- `paper_trade_replay_key` present
- `model_output_ready=True` on fills
- `market_analysis_exception` count = 0 for the run

---

## Instrumentation-Era Runs

| Run ID | Date | Fills | Assets | replay_key | model_ready | mex |
|---|---|---:|---|---:|---:|---:|
| `20260522T082440Z_32952_1b709e78` | 2026-05-22 | 6 | ETH | 6/6 | 6/6 | 0 |
| **Total** | | **6** | **ETH only** | **6/6** | **6/6** | **0** |

---

## Current Coverage

| Metric | Current | Required | Remaining |
|---|---:|---:|---:|
| Clean runs | 1 | — | — |
| `paper_fill` with `quote_age_at_fill_ms` | 6 | — | — |
| `order_submit_attempt` with `quote_age_at_submit_ms` | 6 | — | — |
| Paired trades (ENTRY+EXIT fill pair) | 3 | 20 | 17 |
| BTC paired trades | 0 | 5 | 5 |
| ETH paired trades | 3 | 5 | 2 |
| TP / WIN outcomes | 1 | 5 | 4 |
| SL / LOSS outcomes | 2 | 5 | 3 |
| 60s+ quote-age bucket fills | 0 | 1 | 1 |

---

## Phase 5 Field Integrity

| Field | Non-null fills | Null fills | Missing-key fills |
|---|---:|---:|---:|
| `quote_age_at_fill_ms` | 6 | 0 | 0 |
| `quote_age_at_submit_ms` (on paper_fill) | 6 | 0 | 0 |
| `quote_age_at_submit_ms` (on submit_attempt) | 6 | 0 | 0 |
| `quote_lineage_id` | 6 | 0 | 0 |
| `quote_capture_ts` | 6 | 0 | 0 |
| `fill_ts` | 6 | 0 | 0 |
| `order_submit_ts` | 6 | 0 | 0 |

Ordering invariant `quote_age_at_fill_ms >= quote_age_at_submit_ms`: 6/6 — 0 violations.

---

## Quote-Age Distribution

### `quote_age_at_fill_ms` — all instrumentation-era fills

| Bucket | Count | % |
|---|---:|---:|
| 0–5 s | 0 | 0% |
| 5–15 s | 2 | 33% |
| 15–30 s | 2 | 33% |
| 30–60 s | 2 | 33% |
| **60 s+** | **0** | **0%** |

Summary statistics:

| Stat | `quote_age_at_fill_ms` | `quote_age_at_submit_ms` |
|---|---:|---:|
| n | 6 | 6 |
| min | 7,768 ms | 7,765 ms |
| mean | 21,590 ms | 21,584 ms |
| max | 34,467 ms | 34,449 ms |
| 60s+ count | 0 | 0 |

### By Intent

| Intent | n | mean fill age | min | max | Buckets |
|---|---:|---:|---:|---:|---|
| ENTRY | 3 | 31,640 ms | 26,164 ms | 34,467 ms | 15–30s: 1, 30–60s: 2 |
| EXIT | 3 | 11,539 ms | 7,768 ms | 17,911 ms | 5–15s: 2, 15–30s: 1 |

Entry-side quotes are consistently older than exit-side quotes. This is a directional signal (entries use display-snapshot quotes; exits may use fresher decision-cycle quotes), but sample size is too small to treat as an effect.

### By Quote Source

| Source | n | mean fill age | Buckets |
|---|---:|---:|---|
| `display_snapshot_sampling` | 5 | 24,354 ms | 5–15s: 1, 15–30s: 2, 30–60s: 2 |
| `decision_cycle_fetch` | 1 | 7,768 ms | 5–15s: 1 |

`decision_cycle_fetch` produces fresher quotes than `display_snapshot_sampling`. One data point — not sufficient for a threshold claim.

---

## Paired Trade Detail

Three ENTRY+EXIT fill pairs from run `20260522T082440Z_32952_1b709e78`. Joined by `execution_trace_id` (shared between ENTRY and EXIT fills of the same trade). `trade_result` and `pnl_usdc` fields are `None` in trade_journal for this run — outcomes inferred from fill price delta only.

| Trade | Asset | Side | Entry price | Exit price | Price delta | Hold | Inferred result | Outcome type |
|---|---|---|---:|---:|---:|---:|---|---|
| 1 | ETH | YES | 0.57 | 0.55 | −0.02 | 7 s | LOSS | small move / early exit |
| 2 | ETH | NO | 0.49 | 0.59 | +0.10 | 30 s | WIN | TP candidate |
| 3 | ETH | YES | 0.52 | 0.34 | −0.18 | 12 s | LOSS | SL candidate |

**Note on outcome classification:** `trade_result` is `None` in the trade journal for this run. Outcomes are inferred from fill price delta only. A delta of −0.18 on a YES position is consistent with a stop-loss exit or forced market close. Until `trade_result` is populated by the runtime, TP/SL counts in the readiness gates are estimates, not ground truth.

### Per-Trade Quote-Age Evidence

| Trade | Intent | Quote age at fill | Quote source | Quote lineage |
|---|---|---:|---|---|
| 1 ENTRY | ENTRY | 34,467 ms | `display_snapshot_sampling` | `ql_de9beb3b1af1` |
| 1 EXIT | EXIT | 7,768 ms | `decision_cycle_fetch` | `ql_3d95321115ef` |
| 2 ENTRY | ENTRY | 26,164 ms | `display_snapshot_sampling` | `ql_e60fa2e613bb` |
| 2 EXIT | EXIT | 17,911 ms | `display_snapshot_sampling` | `ql_4fc5f10ee57d` |
| 3 ENTRY | ENTRY | 34,289 ms | `display_snapshot_sampling` | `ql_89851cf8d28b` |
| 3 EXIT | EXIT | 8,939 ms | `display_snapshot_sampling` | `ql_1299b9acfe3a` |

---

## Asset Segmentation

| Asset | Paired trades | TP/WIN | SL/LOSS | Small/early | Fills |
|---|---:|---:|---:|---:|---:|
| BTC | 0 | 0 | 0 | 0 | 0 |
| ETH | 3 | 1 | 1 | 1 | 6 |

BTC evidence: zero fills in instrumentation era. Historical BTC hunt confirmed no pre-instrumentation BTC Phase 5 evidence exists.

---

## Outcome Segmentation

### Entry-side quote age by outcome

| Outcome | Trades | Mean entry fill age |
|---|---:|---:|
| WIN / TP | 1 | 26,164 ms |
| LOSS / SL | 1 | 34,289 ms |
| Small / early | 1 | 34,467 ms |

Direction: LOSS entries used older quotes than WIN entry. Consistent with a quote-staleness hypothesis, but n=3 makes this unactionable.

### Exit-side quote age by outcome

| Outcome | Trades | Mean exit fill age |
|---|---:|---:|
| WIN / TP | 1 | 17,911 ms |
| LOSS / SL | 1 | 8,939 ms |
| Small / early | 1 | 7,768 ms |

Exit-side pattern is reversed: losing trades had fresher exit quotes. No consistent relationship identified.

---

## Lifecycle Segmentation

| Field | Observed value | Count |
|---|---|---:|
| `lifecycle_phase` on fills | `OPENING_SCAN` | 6 |
| `lifecycle_phase` on trade_close | `UNKNOWN` | 3 |

All fills occurred in `OPENING_SCAN`. No `CLOSING_SCAN`, `LATE_WINDOW`, or `FORCED_EXIT` lifecycle coverage yet.

---

## Readiness Gates

| Gate | Required | Current | Status |
|---|---:|---:|---|
| Paired trades | ≥ 20 | 3 | NOT MET |
| BTC trades | ≥ 5 | 0 | NOT MET |
| ETH trades | ≥ 5 | 3 | NOT MET |
| TP/WIN outcomes | ≥ 5 | 1 (inferred) | NOT MET |
| SL/LOSS outcomes | ≥ 5 | 2 (inferred) | NOT MET |
| 60s+ quote-age fill OR strong staleness relationship | ≥ 1 | 0 | NOT MET |

All six gates are unmet.

---

## Historical BTC Coverage Hunt — Summary

Swept on 2026-05-22. All 13 historical execution_log files (2026-05-08 → 2026-05-21) and 12 trade_journal files. Total BTC fills found: 622. Phase 5 fields found: 0.

| Historical stat | Value |
|---|---|
| BTC fills scanned | 622 |
| BTC fills with `quote_age_at_fill_ms` | 0 |
| BTC fills with `quote_lineage_id` | 0 |
| BTC fills with `fill_ts` | 0 |
| Best pre-instrumentation BTC run | `20260521T133858Z` — model_ready, replay_key, 4 fills |
| Backfill possible | No — `fill_ts` absent, JSONL rewrite prohibited |

Verdict: historical data cannot contribute to Phase 6 readiness.

```
HISTORICAL_EVIDENCE: NONE — PRE-INSTRUMENTATION
```

---

## Current Recommendation

```
COLLECT_MORE_EVIDENCE
```

Shortfall:

- 17 of 20 paired trades remain
- 5 of 5 BTC paired trades remain (zero BTC instrumentation-era fills)
- 2 of 5 ETH paired trades remain
- 4 of 5 TP outcomes remain (1 inferred, unconfirmed by `trade_result`)
- 3 of 5 SL outcomes remain (1 inferred, unconfirmed by `trade_result`)
- 0 of required 60s+ evidence

Do not calibrate stale-quote thresholds from this sample. The entry-side quote-age pattern (older quotes on losing entries) is directionally interesting but statistically unactionable at n=3.

Secondary issue: `trade_result` and `pnl_usdc` are `None` in trade_journal for all instrumentation-era closes. TP/SL counts are inferred from price delta. This gap should resolve as the runtime matures, but current outcome classification carries uncertainty.

---

## Next Monitor Update Trigger

Update after any clean run (replay_key + model_ready + mex=0) that adds any of:

- BTC paired trades (highest priority — zero coverage)
- TP/WIN outcomes (confirmed by `trade_result`, not inferred)
- 60s+ quote-age fills
- SL/LOSS outcomes beyond the current 2 inferred
- Non-OPENING_SCAN lifecycle fills
