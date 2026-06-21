# JOINED_RECORDS_BUILDER_RUNTIME_PATCH_IMPLEMENTATION_REPORT_001

## Scope

Mode: CODE IMPLEMENTATION, OFFLINE TOOL ONLY.

Allowed files changed:

- `tools/joined_records_builder.py`
- `tests/test_joined_records_builder.py`

No runtime, strategy, risk, sizing, order, config, `.env`, source JSONL, `tools/execution_paper_runtime.py`, or `tools/shadow_filter_evaluator.py` files were modified.

The full real-data builder was not run.

## Implementation Summary

The joined records builder no longer performs large token-list substring scans against every decision-log line.

Removed runtime bottleneck pattern:

```text
any(token in line for token in run_id_tokens)
```

New behavior:

- `extract_json_string_field(line, field_name)` extracts simple JSON string fields from raw JSONL lines without `json.loads`.
- Decision-log scan first extracts `run_id`.
- Rows with `run_id not in required_run_ids` are skipped before `json.loads`.
- Rows then extract `signal_id`, `candidate_id`, and `condition_id` from the raw line.
- Candidate rows are selected through O(1) tuple membership:
  - `(run_id, signal_id) in required_signal_ids`
  - `(run_id, candidate_id) in required_candidate_ids`
  - `(run_id, condition_id) in required_condition_ids`
- `json.loads` is called only after raw extracted keys match the required key sets.

## Progress Sidecar

The builder now writes:

`joined_records_progress.json`

under the scratch-guarded output directory.

Fields:

- `files_processed`
- `current_file`
- `decision_rows_seen`
- `decision_rows_parsed`
- `decision_rows_retained`
- `last_updated_utc`
- `phase`

Progress phases:

- `decision_scan_started`
- `decision_scan`
- `decision_scan_complete`

CLI option added:

```text
--progress-every-rows
```

Default:

```text
250000
```

Existing option retained:

```text
--progress-every-files
```

## Output Safety

Final output filenames remain unchanged:

- `joined_records.jsonl`
- `joined_records_report.json`

Write behavior now uses temporary files and atomic rename:

- `joined_records.jsonl.tmp` -> `joined_records.jsonl`
- `joined_records_report.json.tmp` -> `joined_records_report.json`

Successful runs leave no `.tmp` output files behind.

## Tests Added / Updated

Added coverage for:

- raw field extractor extracts `run_id` from compact JSON
- raw field extractor extracts `run_id` from spaced JSON
- raw field extractor returns `None` for missing field
- progress sidecar is written under scratch output
- final output temp files are not left behind after successful write

Existing relevant coverage remains:

- irrelevant run IDs are skipped before parse
- low-retention decision scan behavior
- signal ID join
- candidate ID join
- nearest timestamp fallback
- evaluator-compatible output schema
- no forbidden imports

## Validation

Commands run:

```text
py -3.11 -m py_compile tools\joined_records_builder.py
py -3.11 -m pytest tests\test_joined_records_builder.py -q
git diff --check
```

Results:

```text
py_compile: PASS
pytest: 25 passed
git diff --check: PASS
```

`git diff --check` emitted only LF/CRLF warnings for the two edited source files.

## Final Verdict

RUNTIME_PATCH_IMPLEMENTED

The builder is ready for pre-commit review. A full real-data builder rerun remains out of scope for this task.
