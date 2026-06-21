# JOINED_RECORDS_BUILDER_MEMORY_PATCH_IMPLEMENTATION_REPORT_001

## Scope

Mode: CODE IMPLEMENTATION, OFFLINE TOOL ONLY.

Allowed files changed:

- `tools/joined_records_builder.py`
- `tests/test_joined_records_builder.py`

No runtime, strategy, risk, sizing, order, config, or source JSONL files were modified. The full real-data builder was not rerun.

## Implementation Summary

The joined records builder now uses key-filtered decision-log retention instead of retaining the full decision-log corpus.

Changes in `tools/joined_records_builder.py`:

- `_load_decision_indexes` now accepts:
  - `required_run_ids`
  - `required_signal_ids`
  - `required_candidate_ids`
  - `required_condition_ids`
  - `max_decision_rows_loaded`
  - `progress_every_files`
- Decision-log scanning remains line-by-line.
- Lines are skipped before `json.loads` when they do not contain required run ID strings.
- Rows are skipped after parse when `run_id` is not required.
- Rows are retained only when they match one of:
  - `(run_id, signal_id)`
  - `(run_id, candidate_id)`
  - `(run_id, condition_id)`
- Retained decision rows are projected to the fields needed by the evaluator-compatible output.
- Full unrelated decision rows and skip rows are no longer retained.
- Decision retention counters were added to `joined_records_report.json`.
- A fail-closed guard was added through `--max-decision-rows-loaded`, default `250000`.
- Progress logging was added through `--progress-every-files`, default `5`.
- Empty decision requirements short-circuit without parsing the decision log.

## Report Counters Added

- `decision_rows_seen`
- `decision_rows_parsed`
- `decision_rows_retained`
- `decision_rows_skipped_run_id`
- `decision_rows_skipped_key`
- `decision_retention_rate`
- `required_run_id_count`
- `required_condition_id_count`
- `required_signal_id_count`
- `required_candidate_id_count`
- `memory_guard_status`

## Tests Added / Updated

Added coverage for:

- irrelevant decision rows are not retained
- unmatched run ID rows are not parsed
- required condition fallback remains indexed
- `max_decision_rows_loaded` guard fails closed
- large irrelevant decision fixture remains low-retention
- empty decision requirements do not parse decision logs

Existing coverage preserved:

- join by signal ID
- join by candidate ID
- nearest timestamp fallback
- shadow filter evaluator compatibility
- scratch-only output guard
- no forbidden imports

## Validation

Commands run:

```text
py -3.11 -m py_compile tools\joined_records_builder.py
py -3.11 -m pytest tests\test_joined_records_builder.py -q
git diff --check
```

Results:

- py_compile: PASS
- pytest: PASS, 21 passed
- git diff --check: PASS

## Memory-Safety Effect

The builder no longer retains the 12.49 GB decision-log corpus as Python objects. Decision rows are retained only when they are reachable from execution closes through required run ID plus signal, candidate, or condition keys.

The trade-journal indexes still retain broader trade rows, but the observed trade-journal corpus is small compared with the decision logs. This patch targets the confirmed root cause of the >18 GB memory incident.

## Final Verdict

MEMORY_PATCH_IMPLEMENTED

The builder is ready for pre-commit review. Full real-data execution remains intentionally out of scope for this task.
