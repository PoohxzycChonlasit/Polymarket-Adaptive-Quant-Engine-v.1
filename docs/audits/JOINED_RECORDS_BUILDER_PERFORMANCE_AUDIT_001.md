# JOINED_RECORDS_BUILDER_PERFORMANCE_AUDIT_001

## Scope

Mode: READ ONLY AUDIT.

No code was changed. The full joined-records builder was not rerun.

Inspected files:

- `tools/joined_records_builder.py`
- `tests/test_joined_records_builder.py`
- `JOINED_RECORDS_REAL_DATA_AUDIT_001.md`
- `runtime/quant_data/decision_log/*.jsonl` metadata only
- `runtime/quant_data/trade_journal/*.jsonl` metadata only
- `scratch/execution_paper_phase_c_full_eligible_replay_rerun/output_root/runtime/quant_data/execution_paper/journals/trade/*.jsonl` bounded row/key scan only

## 1. Builder Memory Model

### Execution closes

Function: `_load_execution_closes`

Current behavior:

- Loads every `execution_paper_close` row into a list.
- Keeps full close payloads in memory.
- This population is small in the real-data run and is not the memory driver.

Observed real-data close population:

- execution close rows: 731
- execution trade journal files: 1
- execution trade journal bytes: 2.53 MB

### Trade journal indexes

Function: `_load_trade_indexes`

Current behavior:

- Streams `trade_journal/*.jsonl`, but parses every row.
- Stores full parsed trade rows in `source_ref`.
- Stores the same full open row into multiple indexes:
  - `open_by_identity`
  - `open_by_signal`
  - `open_by_candidate`
  - `open_by_condition_epoch`
- `source_ref` stores rows under multiple key forms from `_source_ref_keys`.

Impact:

- Duplicates row references across indexes.
- Trade journal size is only 11.98 MB, so this is inefficient but not the primary 18 GB memory cause.

### Decision-log indexes

Function: `_load_decision_indexes`

Current behavior:

- Scans every `decision_log/*.jsonl` file.
- Uses a prefilter containing `"event_type"`, which is present in most decision rows and therefore does not materially reduce parsing.
- Parses nearly every decision row with `json.loads`.
- Stores full parsed decision rows in:
  - `by_signal`
  - `by_candidate`
  - `by_condition`
- Does not filter by the run IDs, condition IDs, signal IDs, or candidate IDs required by the 731 execution closes before retaining rows.
- Can retain the same row in multiple indexes.

Impact:

- This loads a 12.49 GB decision-log corpus into memory-shaped Python objects.
- Python object expansion plus duplicated indexes explains the observed >18 GB RSS.
- The builder can exhaust memory before producing any output.

### Output assembly

Function: `build_joined_records`

Current behavior:

- Loads execution closes, trade indexes, and full decision indexes before joining.
- Accumulates joined output records before writing.

Impact:

- The largest memory spike occurs before output generation.
- No joined output is expected if decision-index loading times out or exhausts RAM.

## 2. Lightweight Metadata Counts

### File metadata

| Corpus | Files | Bytes | Size |
|---|---:|---:|---:|
| decision_log | 43 | 13,098,668,332 | 12,491.99 MB |
| trade_journal | 40 | 12,567,018 | 11.98 MB |
| execution paper trade journals | 1 | 2,651,309 | 2.53 MB |

### Execution close key scan

The execution close scan was bounded to the scratch execution-paper replay output.

| Metric | Count |
|---|---:|
| execution close rows | 731 |
| execution position IDs | 731 |
| historical position UIDs | 731 |
| referenced source trade files | 32 |
| referenced source date min | 2026-05-18 |
| referenced source date max | 2026-06-20 |
| required run IDs from closes | 101 |
| required condition IDs from closes | 707 |

### Date-range skip estimate

Filename-date pruning alone is not enough.

| Decision-log date bucket | Files | Size |
|---|---:|---:|
| total decision logs | 43 | 12,491.99 MB |
| filenames inside referenced source date range, 2026-05-18 through 2026-06-20 | 33 | 12,295.38 MB |
| filenames outside referenced source date range | 10 | 196.61 MB |

Filename-date skip share: 1.57%.

Conclusion: the bounded-memory fix must filter by required keys, not by date alone.

### Decision-log skip estimate

The real join target is small:

- 731 execution closes
- 101 required run IDs
- 707 required condition IDs

The current builder scans and retains from a 12.49 GB decision-log corpus. Exact row-level skip percentage was not computed because this audit did not run a full decision-log content scan. The expected skip is large because retained decision rows should be limited to rows matching required run IDs plus required signal, candidate, or condition keys.

## 3. Root Cause Classification

Primary root cause: **A. all-decision full payload load**

Secondary contributing causes:

- **B. duplicated indexes**
- **C. skip-event parsing blow-up**

Not primary:

- **D. source hash / raw line retention blow-up**

Rationale:

- Decision logs are 12.49 GB versus 11.98 MB of trade journals and 2.53 MB of execution-paper journals.
- `_load_decision_indexes` parses and indexes all matching-looking rows before it knows whether they are needed by the 731 closes.
- The `"event_type"` prefilter is too broad to reduce the decision corpus.
- Full row objects are retained in multiple decision indexes.
- Source hash/raw line handling is not large enough to explain >18 GB RAM.

## 4. Bounded-Memory Patch Design

### Required principles

The builder should become a selective three-pass joiner:

1. Load only execution close keys.
2. Load only trade rows referenced by those closes, plus the corresponding source opens.
3. Scan decision logs and retain only rows matching needed run ID plus signal, candidate, or condition keys.

It must never store full decision logs, skip rows, or duplicate full rows across indexes.

### Pass 1: execution close keys

Replace full close loading with projected close metadata.

Required retained fields:

- execution close payload fields needed for final output
- `source_file`
- `source_line`
- `source_event_sha256`
- `execution_position_id`
- `historical_position_uid`
- available `run_id`
- available `condition_id`
- available `signal_id`
- available `candidate_id`

Build:

- `required_source_refs`
- `required_source_files`
- `required_execution_position_ids`
- `required_historical_position_uids`
- initial `required_run_ids`
- initial `required_condition_ids`

### Pass 2: referenced trade rows only

Change `_load_trade_indexes(trade_root)` to accept required keys:

```text
_load_trade_indexes(
    trade_root,
    required_source_refs,
    required_source_files,
    required_identity_keys,
)
```

Behavior:

- Stream trade journals line by line.
- Parse rows only when either:
  - the row is a source close referenced by execution closes, or
  - the row matches an identity key needed to find its source open.
- Retain projected trade fields only.
- Do not populate `source_ref` for all trade rows.
- Do not retain close/open rows unrelated to execution closes.

After parsing referenced closes, enrich:

- `required_run_ids`
- `required_condition_ids`
- `required_signal_ids`
- `required_candidate_ids`
- required identity keys for source opens

### Pass 3: filtered decision-log scan

Change `_load_decision_indexes(decision_root)` to accept required keys:

```text
_load_decision_indexes(
    decision_root,
    required_run_ids,
    required_signal_ids,
    required_candidate_ids,
    required_condition_ids,
    max_decision_rows_loaded,
    progress_every_files,
)
```

Behavior:

- Stream decision logs one file at a time.
- Remove `"event_type"` as a retention prefilter.
- Optionally prefilter raw lines by required ID strings before `json.loads`.
- After parse, immediately skip rows where `run_id` is not in `required_run_ids`.
- Retain a projected decision row only when at least one of these is true:
  - `(run_id, signal_id)` in required signal keys
  - `(run_id, candidate_id)` in required candidate keys
  - `(run_id, condition_id)` in required condition keys
- Never retain rows with no join path to execution closes.
- Store one canonical projected decision row and let indexes reference row IDs or the same projected object.
- Store `by_condition` as `(timestamp, projected_row_id)` or `(timestamp, projected_row_ref)`, not duplicate full dicts.
- Add counters:
  - `decision_rows_seen`
  - `decision_rows_parsed`
  - `decision_rows_retained`
  - `decision_rows_skipped_run_id`
  - `decision_rows_skipped_key`

### Output writing

Change `build_joined_records` so joined output is streamed to JSONL instead of accumulated in a full `records` list.

Keep only aggregate counters in memory:

- total closes
- joined closes
- unjoined closes
- join offsets
- missing metadata counters
- join status counters

### Memory guard

Add optional guard options:

- `--max-decision-rows-loaded`
- `--memory-cap-mb`
- `--progress-every-files`

Fail closed if:

- retained decision rows exceed `max_decision_rows_loaded`
- estimated retained payload bytes exceed safe cap
- memory probe, if available, exceeds `memory-cap-mb`

The guard should report counts and stop before writing a misleading partial joined dataset.

## 5. Required Implementation Changes

Precise blocks to change in `tools/joined_records_builder.py`:

1. `_load_execution_closes`
   - Project close rows to required fields.
   - Return close records plus required key sets.

2. `_load_trade_indexes`
   - Accept required source refs and identity keys.
   - Stop indexing every trade row.
   - Store projected rows only.

3. `_load_decision_indexes`
   - Accept required run/signal/candidate/condition keys.
   - Stop retaining all decision rows.
   - Store projected rows and non-duplicating indexes.
   - Add scan/retention counters and progress logging.

4. `_find_trade_open`
   - Work against projected trade-open indexes.
   - Preserve existing join priority.

5. `_find_decision`
   - Work against filtered, projected decision indexes.
   - Preserve current signal, candidate, then condition/timestamp fallback logic.

6. `build_joined_records`
   - Build required keys before decision-log scan.
   - Stream output JSONL.
   - Populate report from counters, not from a retained output list.

7. CLI parser
   - Add `--max-decision-rows-loaded`.
   - Add `--memory-cap-mb`.
   - Add `--progress-every-files`.

8. Report JSON
   - Add:
     - `decision_rows_seen`
     - `decision_rows_parsed`
     - `decision_rows_retained`
     - `decision_retention_rate`
     - `required_run_id_count`
     - `required_condition_id_count`
     - `required_signal_id_count`
     - `required_candidate_id_count`
     - `memory_guard_status`

## 6. Required Tests

Add or update tests in `tests/test_joined_records_builder.py`:

1. Irrelevant decision rows are not retained.
2. Only matching `run_id` rows are parsed/retained after key filtering.
3. Only matching `condition_id`, `signal_id`, or `candidate_id` rows are indexed.
4. Memory guard triggers when retained decision rows exceed the configured cap.
5. Large irrelevant decision fixture remains fast and low-retention.
6. Builder still produces evaluator-compatible joined records.
7. Existing join-by-signal test remains passing.
8. Existing join-by-candidate test remains passing.
9. Existing nearest-timestamp fallback remains passing.
10. Ambiguous nearest timestamp remains fail-closed.
11. Source hash mismatch reporting remains intact.
12. Scratch-only output guard remains intact.
13. No forbidden imports remain enforced.

## 7. Risk Review

### Main implementation risk

The main risk is filtering too aggressively before all join keys are known.

Mitigation:

- Derive initial keys from execution closes.
- Enrich keys from referenced trade closes and source opens before scanning decision logs.
- Keep condition/timestamp fallback available for records without signal or candidate IDs.

### Join-quality risk

If decision rows lack run IDs or use inconsistent condition aliases, over-filtering can reduce join rate.

Mitigation:

- Count filtered reasons.
- Emit `decision_rows_skipped_run_id` and `decision_rows_skipped_key`.
- Preserve bounded nearest-timestamp fallback for required condition IDs.

### Output compatibility risk

Projection can accidentally drop fields required by `tools/shadow_filter_evaluator.py`.

Mitigation:

- Add evaluator-compatible fixture test.
- Required projected decision fields must include:
  - `edge`
  - `ev`
  - `ev_after_spread`
  - `true_probability`
  - `volatility_regime`
  - `trend_regime`

## Final Verdict

READY_FOR_MEMORY_PATCH

The failure is sufficiently explained by the current builder indexing the 12.49 GB decision-log corpus as Python objects before joining. The bounded-memory patch should be key-driven, projected, streaming, and guarded before the builder is run on real full eligible replay outputs again.
