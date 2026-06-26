# JOINED_RECORDS_BUILDER_PLAN_001

Date: 2026-06-21
Mode: Design only

## Context

Offline shadow filter evaluator commit:

```text
37e7a7effbf2dd7c3d0b4259bcb092ecc29c4263
```

Problem:

```text
tools/shadow_filter_evaluator.py requires joined_records.jsonl, but joined records are currently produced by scratch analysis scripts instead of a committed reusable builder.
```

Target output:

```text
scratch/joined_records_builder/output/joined_records.jsonl
```

Final verdict:

```text
READY_FOR_BUILDER_IMPLEMENTATION
```

## 1. Join Strategy

The builder should produce one joined record per `execution_paper_close` event.

Primary join path:

```text
execution_paper_close -> source trade_close -> paired source trade_open -> decision_log enrichment
```

Required input roots:

```text
scratch/execution_paper_phase_c_full_eligible_replay_rerun/output_root/runtime/quant_data/execution_paper/journals/trade/*.jsonl
runtime/quant_data/trade_journal/*.jsonl
runtime/quant_data/decision_log/*.jsonl
```

Recommended join stages:

1. Execution close to source trade close:
   - Use `source_file` + `source_line` from the execution close event.
   - Verify `source_event_sha256` matches the source line hash when possible.
   - Extract source trade close payload.

2. Source trade close to source trade open:
   - Prefer `historical_position_uid` when present in execution close and source open metadata.
   - Otherwise use `execution_position_id` or its historical resolver inputs:
     - `position_id`
     - `execution_position_id`
     - `receipt.order_id`
     - `order_id`
   - Secondary identity match:
     - `paper_trade_replay_key`
     - `signal_id`
     - `candidate_id`
     - `condition_id + asset + outcome + epoch_start_ts`

3. Source trade open to decision log:
   - Primary decision join:
     - `run_id + signal_id`
   - Secondary decision join:
     - `run_id + candidate_id`
   - Fallback decision join:
     - `run_id + condition_id + nearest timestamp`
   - The nearest timestamp fallback must be bounded:
     - `abs(decision.timestamp_utc - trade_open.timestamp_utc) <= 120 seconds`

4. If multiple fallback candidates exist within the window:
   - choose the smallest absolute timestamp delta
   - if tied, choose the earlier decision timestamp
   - if still tied, mark `join_status = AMBIGUOUS_DECISION_JOIN` and do not attach decision-only metrics

Recommended `join_status` values:

```text
JOINED_SIGNAL_ID
JOINED_CANDIDATE_ID
JOINED_NEAREST_CONDITION
JOINED_TRADE_OPEN_ONLY
UNJOINED_SOURCE_CLOSE_MISSING
UNJOINED_SOURCE_OPEN_MISSING
UNJOINED_DECISION_MISSING
AMBIGUOUS_DECISION_JOIN
SOURCE_HASH_MISMATCH
```

The evaluator can still run on `JOINED_TRADE_OPEN_ONLY` records when trade-open metadata already contains `edge`, `ev`, `ev_after_spread`, `true_probability`, and regime fields. Decision joins enrich missing fields but should not overwrite non-null source-open values unless explicitly configured later.

## 2. Indexing Strategy

Avoid nested close-by-decision loops.

### Execution Close Load

Load execution close events once from:

```text
<execution-journal-root>/journals/trade/*.jsonl
```

Filter:

```text
event_type == "execution_paper_close"
```

Keep in memory:

- close event list
- set of referenced source files
- close identity keys

Expected scale is replay output sized, not raw runtime-log sized.

### Trade Journal Load

Load trade journal rows once, streaming line by line.

Indexes:

```text
source_ref_index[(source_file_normalized, source_line)] = source_row
historical_position_index[historical_position_uid] = source_open
execution_position_index[resolved_execution_position_id] = source_open
paper_replay_key_index[paper_trade_replay_key] = source_open
signal_index[(run_id, signal_id)] = source_open
candidate_index[(run_id, candidate_id)] = source_open
condition_epoch_index[(run_id, condition_id, epoch_start_ts, asset, outcome)] = [source_open]
```

Only `trade_open` and `trade_close` rows need full payload retention. Non-trade rows can be ignored after counts.

### Decision Log Load

Decision logs can be large, so prefilter by cheap string checks before `json.loads`.

Potential prefilter:

```text
line contains one of:
  "event_type\": \"decision"
  "edge"
  "ev"
  "ev_after_spread"
  "true_probability"
  "volatility_regime"
  "trend_regime"
```

This is an optimization only. It must not be the only correctness gate; parsed rows still need schema checks.

Decision indexes:

```text
decision_signal_index[(run_id, signal_id)] = [decision_row]
decision_candidate_index[(run_id, candidate_id)] = [decision_row]
decision_condition_index[(run_id, condition_id)] = sorted list by timestamp_utc
```

Nearest timestamp lookup should use a sorted timestamp list per `(run_id, condition_id)` plus binary search, not a linear scan over all decisions.

### Performance Guard

The implementation should not contain a nested loop shaped like:

```text
for close in closes:
    for decision in all_decisions:
```

Tests should detect this indirectly by instrumenting lookup calls or by using a fixture where many irrelevant decisions exist and asserting bounded lookup behavior.

## 3. Output Safety

Output directory must resolve under:

```text
scratch/
```

Required guard:

```text
os.path.commonpath([workspace/scratch, resolved_output_dir]) == workspace/scratch
```

Forbidden behavior:

- never write under `runtime/`
- never modify source trade journals
- never modify source decision logs
- never mutate execution-paper replay artifacts
- never create runtime execution-paper output

Allowed output:

```text
scratch/joined_records_builder/output/joined_records.jsonl
scratch/joined_records_builder/output/joined_records_report.json
```

The builder should fail closed if output path is outside scratch.

## 4. Joined Record Schema

Each output line must be a JSON object with these fields:

```text
timestamp_utc
run_id
source_file
source_line
asset
market_slug
side
outcome
edge
ev
ev_after_spread
true_probability
volatility_regime
trend_regime
execution_pnl_5_share_model
execution_entry_price
execution_exit_price
execution_shares
historical_position_uid
execution_position_id
signal_id
join_status
join_offset_seconds
```

Recommended additional provenance fields:

```text
execution_run_id
execution_source_file
execution_source_line
execution_source_event_sha256
trade_open_source_file
trade_open_source_line
trade_close_source_file
trade_close_source_line
decision_source_file
decision_source_line
decision_join_key
candidate_id
condition_id
epoch_start_ts
join_quality
missing_fields
```

Field resolution priority:

1. execution close event for execution PnL and execution prices
2. source trade open for signal identity, market metadata, and entry context
3. source trade close for close timestamp and close-specific metadata
4. decision log for missing edge/EV/probability/regime fields

Side/outcome:

- `side` should be normalized to `YES` or `NO` when possible.
- `outcome` should preserve the source value if separate from `side`.
- If only one is available, write both fields with the same normalized value when safe.

PnL:

```text
execution_pnl_5_share_model = execution_close.execution_pnl
```

Do not use signal dust PnL for this field.

## 5. Join Quality Metrics

The report should include:

```text
total_closes
joined_closes
unjoined_closes
join_rate
avg_join_offset_seconds
max_join_offset_seconds
missing_edge_count
missing_ev_count
missing_volatility_count
missing_trend_count
missing_true_probability_count
join_status_counts
source_hash_mismatch_count
ambiguous_join_count
output_record_count
```

Definitions:

- `total_closes`: count of `execution_paper_close` events read.
- `joined_closes`: records with any status beginning `JOINED_`.
- `unjoined_closes`: records with status beginning `UNJOINED_` or `SOURCE_HASH_MISMATCH`.
- `join_rate`: `joined_closes / total_closes`.
- `join_offset_seconds`: decision timestamp minus trade-open timestamp for decision-enriched records.
- missing metadata counts should be counted after all enrichment attempts.

The report should preserve enough counts to decide whether shadow filter results are trustworthy. A low join rate should not block JSONL emission, but must be visible.

## 6. CLI Plan

Command shape:

```text
py -3.11 tools/joined_records_builder.py ^
  --execution-journal-root scratch/execution_paper_phase_c_full_eligible_replay_rerun/output_root/runtime/quant_data/execution_paper ^
  --trade-journal-root runtime/quant_data/trade_journal ^
  --decision-log-root runtime/quant_data/decision_log ^
  --output-dir scratch/joined_records_builder/output ^
  --max-join-seconds 120
```

CLI options:

```text
--execution-journal-root
--trade-journal-root
--decision-log-root
--output-dir
--max-join-seconds
--fail-on-source-hash-mismatch
--max-records
```

Defaults:

```text
--max-join-seconds 120
--fail-on-source-hash-mismatch false
--max-records 0
```

`--max-records 0` means no record cap.

## 7. Tests Required

Target test file:

```text
tests/test_joined_records_builder.py
```

Target tool file:

```text
tools/joined_records_builder.py
```

Required tests:

1. `test_join_by_signal_id`
   - synthetic close references source close; source close/open share `signal_id`; decision row has same `(run_id, signal_id)`.
   - expected `join_status = JOINED_SIGNAL_ID`.

2. `test_join_by_candidate_id_when_signal_missing`
   - source rows have `candidate_id`; decision row has same `(run_id, candidate_id)`.
   - expected `join_status = JOINED_CANDIDATE_ID`.

3. `test_fallback_nearest_timestamp_join`
   - no signal/candidate join available; matching `(run_id, condition_id)` decision within 120 seconds.
   - expected `join_status = JOINED_NEAREST_CONDITION`.

4. `test_nearest_timestamp_outside_window_unjoined`
   - matching condition exists but offset is greater than 120 seconds.
   - expected `join_status = UNJOINED_DECISION_MISSING`.

5. `test_ambiguous_nearest_timestamp_join`
   - two equally near decisions.
   - expected `join_status = AMBIGUOUS_DECISION_JOIN`.

6. `test_unjoined_close_when_source_close_missing`
   - execution close source reference does not exist.
   - expected output record with `UNJOINED_SOURCE_CLOSE_MISSING`.

7. `test_unjoined_close_when_source_open_missing`
   - source close exists but open cannot be found.
   - expected `UNJOINED_SOURCE_OPEN_MISSING`.

8. `test_missing_metadata_behavior`
   - joined record missing edge/EV/regime fields is emitted with nulls and report missing counts incremented.

9. `test_scratch_only_output_guard`
   - output under `runtime/` raises.

10. `test_jsonl_output_schema`
    - every output row contains all required fields.

11. `test_source_hash_mismatch_reported`
    - source line hash mismatch increments `source_hash_mismatch_count`; optional fail flag raises.

12. `test_no_nested_close_decision_loop_behavior`
    - many irrelevant decision rows do not multiply close processing work.

13. `test_shadow_filter_evaluator_compatibility`
    - joined output can be passed into `tools/shadow_filter_evaluator.py` on a fixture and produce summary output.

14. `test_no_forbidden_imports`
    - no imports from runtime trading modules, strategy, risk, execution, or wallet paths.

## 8. Implementation Boundary

Builder may read:

- execution-paper scratch replay journals
- runtime trade journal JSONL
- runtime decision log JSONL

Builder may write:

- `scratch/joined_records_builder/output/joined_records.jsonl`
- `scratch/joined_records_builder/output/joined_records_report.json`

Builder must not:

- import `main.py`
- import `polymarket.trader`
- import order/risk/sizing modules
- modify source JSONL
- write under `runtime/`
- run live or paper runtime
- change shadow filter evaluator behavior

## 9. Open Design Choices

No blocking design gaps were found.

Non-blocking implementation choices:

- whether `fail-on-source-hash-mismatch` should default to false or true
- whether to emit unjoined records into `joined_records.jsonl` or only count them in the report
- whether decision rows with missing `payload` should be counted as malformed or ignored

Recommended defaults:

- source hash mismatch should emit `SOURCE_HASH_MISMATCH` by default and fail only when the flag is set
- unjoined closes should still be emitted so evaluator exclusions can be traced
- decision rows without object payload should be ignored with a count in the report

## 10. Final Verdict

READY_FOR_BUILDER_IMPLEMENTATION

Reason:

The required evaluator-compatible record shape is clear, source artifacts expose enough identity fields for deterministic joins, and fallback nearest-timestamp enrichment can be bounded to 120 seconds without nested loops.

STOP: Design only. No code. No commit. No push. No runtime restart.
