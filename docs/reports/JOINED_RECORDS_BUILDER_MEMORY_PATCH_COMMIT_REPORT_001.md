# JOINED_RECORDS_BUILDER_MEMORY_PATCH_COMMIT_REPORT_001

## Commit

Commit hash:

`61ae4e0963c252c5b9ccc5c0e8d45625dba30d7b`

Commit message:

`Optimize joined records builder memory usage`

## Files Committed

- `tools/joined_records_builder.py`
- `tests/test_joined_records_builder.py`

Committed stat:

```text
61ae4e0 Optimize joined records builder memory usage
 tests/test_joined_records_builder.py | 102 +++++++++++++++++
 tools/joined_records_builder.py      | 213 ++++++++++++++++++++++++++++++-----
 2 files changed, 285 insertions(+), 30 deletions(-)
```

## Test Evidence

Validation evidence from pre-commit implementation task:

```text
py -3.11 -m py_compile tools\joined_records_builder.py
PASS

py -3.11 -m pytest tests\test_joined_records_builder.py -q
21 passed

git diff --check
PASS
```

## Memory Patch Summary

- Decision-log loading is now filtered by required `run_id` plus required `signal_id`, `candidate_id`, or `condition_id`.
- Retained decision rows are projected to evaluator-needed fields only.
- Unrelated decision rows and skip rows are not retained.
- Added decision retention counters to `joined_records_report.json`.
- Added `--max-decision-rows-loaded`, default `250000`.
- Added `--progress-every-files`, default `5`.
- Empty decision requirements no longer trigger full decision-log parsing.

## Safety Summary

- No runtime trading code was committed.
- No strategy, risk, sizing, order, execution, config, or `.env` files were committed.
- No `runtime/`, `scratch/`, generated reports, source JSONL, or RPC/acquisition artifacts were committed.
- `tools/execution_paper_runtime.py` remains pre-existing dirty and was not staged.
- The two memory patch reports remain untracked and were not staged.

## Full Real-Data Run Status

The full real-data joined-records builder run has not been rerun after this memory patch.

## Next Action

Run a separate safe offline validation of the patched builder on real full eligible replay outputs, with memory monitoring and no runtime/source mutation.
