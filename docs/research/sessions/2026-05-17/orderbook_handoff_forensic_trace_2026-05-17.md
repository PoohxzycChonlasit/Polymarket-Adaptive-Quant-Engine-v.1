# Orderbook Handoff Forensic Trace - 2026-05-17

## Scope

Read-only forensic trace of the decision-stage orderbook handoff / completeness regression observed on 2026-05-17.

Runtime behavior changed: No  
Live behavior changed: No

## Role Routing

- Primary role: `14_NO_ENTRY_DIAGNOSTICS_AGENT`
- Supporting roles: `05_MARKET_DATA_AGENT`, `10_BACKTEST_REPLAY_AGENT`, `11_OBSERVABILITY_INCIDENT_AGENT`
- Scope boundary: no patches, no validation run, no threshold change, no JSONL modification.

## Exact Break Stage

Exact break stage:

```text
_analyze_market_quant() successful/available book evidence
  -> market_snapshot emits YES/NO bid/ask and readiness
  -> skip/cutoff/stale-feed outcome builds partial extra_detail
  -> _skip_outcome()
  -> _record_quant_detail()
  -> _decision_diagnostics_payload()
  -> decision-stage orderbook completeness is recomputed from missing serialized YES/NO fields
  -> current_executable_yes_no_book=False
  -> orderbook_current_fetch_status=fresh_fetch_non_executable
  -> orderbook_state_classification=unavailable
  -> model activation blocks before probability/EV
```

The key transition is not CLOB parser failure. It is a decision serialization/handoff gap: snapshot payloads carry the normalized book, but skipped decision payloads often do not.

## Code Path Trace

1. Cycle selects and analyzes markets:
   - `run_single_cycle()` selects markets and calls `_analyze_market(market)`.
   - Relevant lines: `polymarket/trader.py:10433`, `polymarket/trader.py:10559`, `polymarket/trader.py:10579`.

2. Market timing/readiness bucket is initialized before orderbook fetch:
   - `_analyze_market_quant()` creates `timing_detail` through `_market_timing_detail()`.
   - `_market_timing_detail()` calls `_active_window_alignment_detail()` with tokens but without orderbook objects.
   - Relevant lines: `polymarket/trader.py:7017`, `polymarket/trader.py:3988`, `polymarket/trader.py:3989`.

3. Readiness bucket can mark token state before book state:
   - `_active_window_alignment_detail()` calls `_phase2_mark_readiness()`.
   - `_phase2_mark_readiness()` computes `TOKEN_READY`, `BOOK_SEEN`, `NONZERO_BOOK`, `SPREAD_NORMALIZED`, `TRADABLE`, and keeps `executable_book_state_best_seen` monotonic.
   - Relevant lines: `polymarket/trader.py:2729`, `polymarket/trader.py:1551`, `polymarket/trader.py:1637`, `polymarket/trader.py:1650`.

4. Decision-cycle orderbook fetch normalizes actual YES/NO books:
   - `_fetch_orderbook_pair_with_empty_recovery()` fetches YES and NO books.
   - `yes_bid`, `yes_ask`, `no_bid`, `no_ask`, sizes, spread, liquidity, and orderbook age are derived.
   - `_mark_orderbook_refresh()` records executable success if all YES/NO bid/ask fields are positive.
   - Relevant lines: `polymarket/trader.py:7284`, `polymarket/trader.py:7292`, `polymarket/trader.py:7307`, `polymarket/trader.py:7326`, `polymarket/trader.py:7338`.

5. Market snapshot writer has the complete book:
   - `log_market_snapshot` emits normalized `yes_bid`, `yes_ask`, `no_bid`, `no_ask`, spread, age, readiness reason, and refresh details.
   - Relevant lines: `polymarket/trader.py:7434`, `polymarket/trader.py:7449`, `polymarket/trader.py:7454`, `polymarket/trader.py:7459`, `polymarket/trader.py:7462`, `polymarket/trader.py:7475`.

6. Pre-model skip branches lose normalized book fields:
   - If `stale_feed` triggers before orderbook fetch, `_skip_outcome()` receives only `timing_detail`.
   - If adaptive cutoff rejects after orderbook fetch, the cutoff skip branch passes `timing_detail`, age, spread, empty-book detail, and refresh detail, but not `yes_bid`, `yes_ask`, `no_bid`, `no_ask`, or their sizes.
   - Relevant lines: `polymarket/trader.py:7150`, `polymarket/trader.py:7167`, `polymarket/trader.py:7538`, `polymarket/trader.py:7556`, `polymarket/trader.py:7568`, `polymarket/trader.py:7575`.

7. Decision diagnostics recomputes book completeness from the skipped outcome display:
   - `_skip_outcome()` calls `_record_quant_detail()`, then `_emit_decision_event()`.
   - `_decision_diagnostics_payload()` copies only fields present in `outcome.display`.
   - If YES/NO bid/ask fields are absent, `decision_orderbook_completeness_source=not_serialized_or_unavailable`.
   - It then calls `_orderbook_refresh_observability_detail()` with `current_executable_yes_no_book=False`.
   - If the display still has `orderbook_current_fetch_status=fresh_fetch_executable`, that is rewritten as decision-stage `fresh_fetch_non_executable`.
   - Relevant lines: `polymarket/trader.py:5259`, `polymarket/trader.py:5301`, `polymarket/trader.py:5321`, `polymarket/trader.py:3010`, `polymarket/trader.py:3235`, `polymarket/trader.py:3377`, `polymarket/trader.py:3388`, `polymarket/trader.py:3400`.

8. Decision-stage orderbook state becomes unavailable:
   - `_phase2_orderbook_state_classification()` only returns `ready` when serialized YES/NO bid/ask fields, or generic bid/ask fields, are present.
   - It does not treat `executable_book_state=TRADABLE`, `executable_book_state_best_seen=TRADABLE`, or `orderbook_current_fetch_status=fresh_fetch_executable` as sufficient readiness evidence.
   - Relevant lines: `polymarket/trader.py:2120`, `polymarket/trader.py:2139`, `polymarket/trader.py:2145`, `polymarket/trader.py:2149`, `polymarket/trader.py:3414`.

9. Probability, EV, and sizing are downstream:
   - Probability starts only after feed, token/book, cutoff, and early pre-model gates pass.
   - EV scanning follows probability output.
   - Order sizing follows EV/trade-quality approval.
   - Relevant lines: `polymarket/trader.py:7619`, `polymarket/trader.py:7647`, `polymarket/trader.py:7868`.

## Evidence Chain

Real May 17 runs inspected:

- `20260517T142049Z_12712_d4120fa6`
- `20260517T152232Z_15908_225e60fb`

Decision log, real May 17 runs only:

- Rows: 542
- `orderbook_state_classification=ready`: 0
- `orderbook_state_classification=unavailable`: 542
- Serialized YES/NO bid/ask fields: 0
- `executable_book_state=TRADABLE`: 56
- `executable_book_state_best_seen=TRADABLE`: 332
- `orderbook_current_fetch_status=fresh_fetch_non_executable`: 518
- `orderbook_current_fetch_status=fresh_fetch_not_attempted_or_unobserved`: 24
- `orderbook_lineage_match=true`: 542
- `orderbook_stale_reuse_source=CURRENT_FETCH_NON_EXECUTABLE_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR`: 518
- Admission stages: `ORDERBOOK=256`, `CUTOFF=210`, `MODEL_GATE=68`, `NORMALIZATION=8`
- Skip reasons: `time_unsafe=249`, `stale_data=232`, `orderbook_unavailable=61`

Market snapshots, real May 17 runs only:

- Rows: 1,549
- `orderbook_state_classification=ready`: 1,549
- `orderbook_current_fetch_status=fresh_fetch_executable`: 1,549
- Serialized YES/NO bid/ask fields: 1,549
- `executable_book_state=TRADABLE`: 1,457
- `executable_book_state_best_seen=TRADABLE`: 1,545
- Market readiness: `ready=1,457`, `late_hard_close_zone=56`, `spread_not_ready=36`

CSV scan comparison:

- May 17 real scan logs: 542 rows, `age_gt_1000ms=363`, `age_avg=1197.83ms`, normalized skips `time_unsafe=249`, `stale_data=232`, `orderbook_unavailable=61`.
- May 15 available scan logs: 318 rows, `age_gt_1000ms=0`, `age_avg=0ms`, normalized skips `time_unsafe=318`.

The May 15 raw comparison is limited because `runtime/quant_data/market_snapshots/2026-05-15.jsonl` was unreadable/corrupted and `runtime/reports` could not be listed. The available scan-log comparison still shows that May 17 introduced orderbook-age/stale-data pressure and orderbook-unavailable decisions that were not present in the selected May 15 scan logs.

## Transition Diagnosis

The observed transition is:

```text
BOOK_PRESENT in snapshot
  yes_bid/yes_ask/no_bid/no_ask present
  fresh_fetch_executable
  orderbook_state_classification=ready
  executable_book_state=TRADABLE

Decision display / diagnostics
  yes_bid/yes_ask/no_bid/no_ask absent
  decision_orderbook_completeness_source=not_serialized_or_unavailable
  current_executable_yes_no_book=False
  fresh_fetch_non_executable
  orderbook_state_classification=unavailable
```

This is a snapshot/decision mismatch plus normalization loss in skipped decision payloads.

## A-H Findings

A. Stale readiness overwrite: partial. The code has a monotonic guard for `executable_book_state_best_seen`, so best-seen readiness survives. However, the decision classifier does not use best-seen readiness as readiness proof.

B. State downgrade: yes, at decision serialization/classification. The refresh path can report prior executable same token pair, while the decision path recomputes current executable as false because serialized YES/NO fields are missing.

C. Reconciliation overwrite: not supported. Parsed May 17 rows showed `reconciliation_blocks_trading=true` zero times and `reconciliation_blocks_trading=false` 350 times.

D. Bucket reset: not the primary break. The readiness bucket preserves many best-seen TRADABLE states. The problem is that decision classification ignores those fields when bid/ask fields are absent.

E. Normalization loss: yes. The market snapshot payload has normalized YES/NO book fields; several skipped decision paths do not carry them into `extra_detail`.

F. Snapshot/decision mismatch: yes. The code explicitly labels the pipeline as `market_snapshot_decision_pipeline_linkage=disconnected_passive_snapshot_to_scheduled_decision`, and the evidence confirms the disconnection.

G. Lifecycle timing race: contributing. May 17 had high orderbook-age pressure and many pre-model exits: stale feed, adaptive orderbook stale, hard-close, and latency/spread blocks. These are runtime gates before probability/EV.

H. Stale May 15 run contamination: contributing to day-level evidence hygiene, not the core root cause. Real May 17 run IDs still reproduce the mismatch.

## Runtime Affecting Or Observability Only?

Mixed.

Runtime affecting:

- `stale_feed` returns before decision-cycle orderbook fetch.
- Adaptive cutoff can reject after a book fetch when `orderbook_age_ms > adaptive_entry_max_orderbook_age_ms` (`1000ms` in `config/settings.py`).
- These blocks prevent probability, EV, and sizing from running.

Observability / handoff affecting:

- Successful/available book fields are not consistently propagated into skipped decision payloads.
- The decision classifier then labels the decision as `orderbook_unavailable` even when `executable_book_state_best_seen=TRADABLE` and the snapshot for the same token pair had a ready book.

The S3 blocker is therefore runtime-affecting in outcome, but the exact `BOOK_PRESENT -> orderbook_unavailable` transition is primarily a decision-payload normalization/classification bug.

## Smallest Possible Future Fix Scope

Smallest future patch scope, if approved later:

1. In pre-model skip branches after an orderbook fetch, include the same normalized `clob_detail` fields used by the post-model path: `yes_bid`, `yes_ask`, `no_bid`, `no_ask`, sizes, mids, spread, token IDs, condition ID, orderbook age, and refresh detail.
2. In `_decision_diagnostics_payload()` or `_phase2_orderbook_state_classification()`, avoid downgrading to `unavailable` when current serialized bid/ask fields are missing but the same decision payload has strong evidence such as `executable_book_state_best_seen=TRADABLE`, `orderbook_lineage_match=true`, and `last_successful_yes_no_book_token_pair_key == decision_token_pair_key`.
3. Keep runtime gates intact: do not loosen stale-book, cutoff, spread, risk, or reconciliation behavior.

That patch would be observability/handoff scoped first. A separate review would be needed before changing runtime admission behavior.

## Restart Alone?

Restart helps evidence hygiene but is unlikely to be sufficient by itself.

Why restart helps:

- May 17 files contain stale May 15 run IDs writing May 17 timestamps.
- Scan logs under `runtime/realtime_logs/2026-05-17/` include May 15 filenames.
- A clean single run would remove stale-writer contamination.

Why restart is not enough:

- The mismatch reproduces inside real May 17 run IDs.
- The code path can deterministically omit book fields from skipped decision payloads.
- The decision classifier deterministically returns `unavailable` when those fields are absent.

Recommended next step before patching: one clean paper-only run with a single active process, then verify whether decision payloads still show `best_seen=TRADABLE` but `orderbook_state_classification=unavailable`.

## Files Inspected

- `orderbook_degradation_diagnosis_2026-05-17.md`
- `polymarket/trader.py`
- `config/settings.py` via targeted `rg`
- `runtime/quant_data/decision_log/2026-05-17.jsonl`
- `runtime/quant_data/market_snapshots/2026-05-17.jsonl`
- `runtime/quant_data/risk_log/2026-05-17.jsonl`
- `runtime/realtime_logs/2026-05-17/scan_log_20260517_212051_12712.csv`
- `runtime/realtime_logs/2026-05-17/scan_log_20260517_222235_15908.csv`
- selected readable `runtime/realtime_logs/2026-05-15/scan_log_*.csv`

## Not Touched

- Runtime code
- `polymarket/trader.py`
- Strategy, risk, execution, wallet, live config
- JSONL evidence
- Thresholds
- Tests
- S3 validation

## Tests / Commands

No runtime validation or tests were run. All work was read-only code inspection plus offline evidence parsing.
