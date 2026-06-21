# JOINED_RECORDS_BUILDER_RUNTIME_BOTTLENECK_AUDIT_001

## Scope

Mode: READ ONLY AUDIT.

No code changes, commits, pushes, runtime restarts, or full builder reruns were performed.

Inspected:

- `tools/joined_records_builder.py`
- `tests/test_joined_records_builder.py`
- `JOINED_RECORDS_BUILDER_FULL_REAL_DATA_RERUN_001.md`
- `JOINED_RECORDS_BUILDER_BOUNDED_REAL_DATA_VALIDATION_001.md`
- lightweight metadata from execution-paper scratch journal and runtime JSONL file metadata

## 1. Algorithm Flow

Current flow in `tools/joined_records_builder.py`:

| Step | Function | Evidence | Runtime implication |
|---|---|---|---|
| Load execution closes | `_load_execution_closes` line 171 | reads `execution_paper_close` rows | Small input; full set is 731 closes |
| Load trade indexes | `_load_trade_indexes` line 182 | scans all trade journals once | Reads about 12 MB; not the timeout driver |
| Build decision requirements | `_collect_decision_requirements` line 460 | loops over closes and in-memory trade indexes | No nested file scans; likely not the timeout driver |
| Load decision indexes | `_load_decision_indexes` line 245 | scans all decision logs once | Main bottleneck |
| Raw run-token check | line 295 | `any(token in line for token in run_id_tokens)` | O(decision_rows x required_run_ids) string checks |
| Raw signal/candidate/condition token check | lines 303-305 | three more `any(token in line ...)` checks | O(decision_rows x required_join_keys) string checks |
| Join records | `build_joined_records` line 640 | builds in-memory `records` list | Small at 731 records; not the timeout driver |
| Write outputs | `_write_outputs` line 572 | writes only after all records/report are complete | No partial output before successful completion |

## 2. Lightweight Metadata

File metadata:

| Corpus | Files | Size |
|---|---:|---:|
| `runtime/quant_data/decision_log/*.jsonl` | 43 | 12,498.31 MB |
| `runtime/quant_data/trade_journal/*.jsonl` | 41 | 12.00 MB |
| execution-paper scratch trade journal | 1 | 2,651,309 bytes |

Execution-close metadata from the scratch execution-paper journal:

| Metric | Count |
|---|---:|
| execution close rows | 731 |
| source run IDs from closes | 101 |
| condition IDs from closes | 707 |
| signal IDs directly on closes | 0 |
| candidate IDs directly on closes | 0 |

Notes:

- Signal and candidate IDs are not directly present on execution closes in this metadata pass.
- The builder derives signal/candidate requirements later from source trade-open rows through `_collect_decision_requirements`.
- The full run therefore likely has hundreds of required signal/candidate keys even though the close-only metadata shows zero.

## 3. Bounded vs Full Scaling

Bounded run evidence:

- `max_records=50`
- elapsed time: 35.363 seconds
- total closes: 50
- required run IDs: 5
- required condition IDs: 50
- required signal IDs: 50
- required candidate IDs: 50
- decision rows seen: 421,327
- decision rows parsed: 1,607
- decision rows retained: 1,303
- retained / seen: 0.309%

Full run evidence:

- intended closes: 731
- command timeout: 304.038 seconds
- output: none
- stale offline builder child process remained and was terminated
- no memory blow-up was reported

Linear close-count estimate:

```text
35.363 * 731 / 50 = 517.0 seconds
```

The 304-second timeout is consistent with a job that had not yet completed under close-count scaling.

However, the remaining bottleneck is probably worse than pure close-count scaling. The bounded decision scan had 5 required run IDs. The full close set has 101 source run IDs. The current run-ID prefilter checks every decision-log line against every required run token until a match:

```text
any(token in line for token in run_id_tokens)
```

That makes scan cost grow with required run-ID count:

```text
101 / 5 = 20.2x more run-token checks than bounded mode
```

The same pattern applies to signal, candidate, and condition tokens. This explains why the memory patch solved retention but full runtime still timed out.

## 4. Root Cause

Primary runtime bottleneck:

**O(decision_log_lines x required_key_count) raw-line token scanning in `_load_decision_indexes`.**

Secondary bottleneck:

**Output is delayed until all records and final report are complete.**

Non-primary causes:

- Repeated full decision-log scans: not observed inside one invocation; the builder scans decision logs once per run.
- Repeated full trade-journal scans: not observed; trade journals are scanned once and are small.
- Per-close source-open file scans: not observed; source-open lookup uses in-memory indexes.
- Source hash verification rereads: not observed; hash is stored in the trade index row.
- Nearest timestamp search: uses `bisect`; not likely material at 731 closes.
- Full output accumulation: small record count, but it prevents partial outputs and makes timeout recovery poor.

## 5. Why No Output Was Created

`build_joined_records` does not write `joined_records.jsonl` until after:

1. all execution closes are loaded,
2. all trade indexes are loaded,
3. all decision indexes are built,
4. all closes are joined,
5. the final report is computed.

Only then does `_write_outputs` run.

Because the timeout occurred before `_write_outputs`, no `joined_records.jsonl` or `joined_records_report.json` was created.

This is correct from an atomic-completion standpoint but poor for long-running diagnostics. There is no checkpoint, partial progress file, or durable decision-scan progress artifact.

## 6. Runtime Patch Design

### A. Replace O(K) token scans with O(1) extracted-key checks

Current raw-line prefilter:

```text
for every line:
  any(required_run_token in line)
  any(required_signal_token in line)
  any(required_candidate_token in line)
  any(required_condition_token in line)
```

Patch design:

1. Compile small regex extractors for raw-line fields:
   - top-level `run_id`
   - `payload.signal_id`
   - `payload.candidate_id`
   - `payload.condition_id`
2. For each decision-log line:
   - extract `run_id` once
   - skip if `run_id not in required_run_ids`
   - extract available signal/candidate/condition IDs once
   - check tuple membership in sets:
     - `(run_id, signal_id) in required_signal_ids`
     - `(run_id, candidate_id) in required_candidate_ids`
     - `(run_id, condition_id) in required_condition_ids`
   - call `json.loads` only after a tuple match

Expected effect:

- Converts the largest pre-parse check from O(required_key_count) substring scans to O(1) set membership after field extraction.
- Preserves fail-closed full parsing for candidate lines only.

### B. Write durable progress before final output

Add a progress sidecar under the scratch output directory:

- `joined_records_progress.json`

Suggested fields:

- phase
- files_scanned
- decision_rows_seen
- decision_rows_parsed
- decision_rows_retained
- required_run_id_count
- required_signal_id_count
- required_candidate_id_count
- required_condition_id_count
- elapsed_seconds
- last_decision_file

Update this file every `progress_every_files`.

This preserves diagnostics if the job is interrupted before final output.

### C. Stream joined records after decision indexing

After decision indexes are built, write `joined_records.jsonl.tmp` incrementally:

1. open temp JSONL under output dir,
2. write one joined record per close,
3. flush periodically,
4. compute counters while streaming,
5. write final report,
6. atomically rename `joined_records.jsonl.tmp` to `joined_records.jsonl` only after success.

This does not solve decision-scan timeout by itself, but it prevents post-index join/write failures from losing all record-level progress.

### D. Add chunkable execution-close selection

`--max-records` currently supports only a prefix. Add safe chunking:

- `--record-offset`
- `--source-date-from`
- `--source-date-to`
- optional `--output-suffix`

Chunk requirements:

- chunks must preserve source hash verification,
- report must include chunk bounds,
- merged output must be deterministic,
- duplicate records across chunks must fail closed or be explicitly rejected by merge tooling.

### E. Date-window decision-log scanning

Add optional decision-log date bounding:

- `--decision-log-date-from`
- `--decision-log-date-to`
- or auto derive from source open/close timestamps with a one-day safety margin.

Caution:

- Filename-date pruning alone was previously weak for the full date range.
- It becomes useful for chunked source-date runs.

### F. Avoid repeated decision scans

Current single invocation scans decision logs once. But chunked reruns would rescan unless a cache is introduced.

Add a filtered decision cache option:

- build `filtered_decision_rows.jsonl.tmp` while scanning,
- write only projected retained rows,
- include manifest hash over required key sets and decision-log file metadata,
- reuse cache only if manifest hash matches.

This allows safe chunked record joining without repeated 12.5 GB decision scans.

### G. Progress logs every N closes

Add join-phase progress:

- closes_processed
- records_written
- joined_count
- unjoined_count
- elapsed_seconds

This is separate from decision-scan progress and confirms the job has moved past indexing.

### H. Optional partial output on timeout

Do not enable partial output by default.

If implemented, require explicit:

```text
--output-partial-on-timeout
```

Partial-output rules:

- write `.partial.jsonl`, never final `joined_records.jsonl`,
- report `partial=true`,
- include last completed close index,
- evaluator must reject partial input unless explicitly allowed.

## 7. Required Implementation Changes

Precise blocks in `tools/joined_records_builder.py`:

1. `_load_decision_indexes`
   - replace repeated token scanning with extracted-key membership checks.
   - add decision-scan progress sidecar writes.
   - keep projected-row retention and `max_decision_rows_loaded`.

2. `_build_parser`
   - add `--record-offset`.
   - add optional decision-log date window arguments.
   - add optional progress sidecar controls if needed.

3. `_load_execution_closes`
   - support offset plus limit, not only prefix limit.
   - optionally filter by source date.

4. `build_joined_records`
   - pass progress/report context into decision loader.
   - stream joined records into temp file after decision indexing.
   - compute report counters incrementally.

5. `_write_outputs`
   - split into streaming writer and final report writer.
   - atomic rename temp output only after success.

6. New helper functions
   - raw-line field extraction for `run_id`, `signal_id`, `candidate_id`, `condition_id`.
   - progress sidecar atomic writer.
   - output temp-path guard under scratch.

## 8. Required Tests

Add/update tests in `tests/test_joined_records_builder.py`:

1. Raw-line prefilter extracts IDs once and does not loop over every required token.
2. Irrelevant decision rows are skipped without `json.loads`.
3. Matching decision rows are parsed and projected.
4. Decision scan progress sidecar is written before final output.
5. Output streaming writes `.tmp` records before final report.
6. Final report remains accurate after streaming output.
7. Failed run does not publish final `joined_records.jsonl`.
8. Successful run atomically publishes final `joined_records.jsonl`.
9. Repeated decision scans are not performed in a single invocation.
10. `--record-offset` plus `--max-records` produces deterministic chunks.
11. Chunk reports include bounds and source counts.
12. Chunk merge rejects duplicate execution/source keys.
13. Evaluator-compatible output remains unchanged after streaming.
14. Progress logs/counters are exposed in report.
15. No forbidden imports remain enforced.

## 9. Need for Profiling

A profiling run is not required before the next patch.

Reason:

- The bounded run already proved memory retention is fixed.
- The full run timed out without memory blow-up.
- Static code inspection identifies the remaining asymptotic problem.
- Full metadata shows key count expands from 5 bounded run IDs to 101 full source run IDs.
- The current prefilter linearly scans every decision line against required token lists.

Profiling can be useful after the runtime patch, but it is not needed to justify the next implementation step.

## Final Verdict

READY_FOR_RUNTIME_PATCH

The remaining bottleneck is not record joining and not memory retention. It is CPU/runtime cost from repeated raw-line token scans in `_load_decision_indexes`, combined with final-output-only writing. The next patch should replace token-list substring scanning with extracted-key set membership and add durable progress/streamed output behavior before another full real-data attempt.
