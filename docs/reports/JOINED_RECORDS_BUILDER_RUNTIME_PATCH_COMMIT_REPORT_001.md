# JOINED_RECORDS_BUILDER_RUNTIME_PATCH_COMMIT_REPORT_001

## Commit

Commit hash:

`f1cef2df84fb91911eb90cec717662c161d21c96`

Commit message:

`Speed up joined records builder decision scan`

## Files Committed

- `tools/joined_records_builder.py`
- `tests/test_joined_records_builder.py`

Committed stat:

```text
f1cef2d Speed up joined records builder decision scan
 tests/test_joined_records_builder.py |  41 +++++++++-
 tools/joined_records_builder.py      | 146 +++++++++++++++++++++++++++++++----
 2 files changed, 169 insertions(+), 18 deletions(-)
```

## Test Evidence

Validation evidence from the implementation task:

```text
py -3.11 -m py_compile tools\joined_records_builder.py
PASS

py -3.11 -m pytest tests\test_joined_records_builder.py -q
25 passed

git diff --check
PASS
```

## Runtime Patch Summary

- Removed the expensive repeated token-list substring decision scan pattern.
- Added raw JSON string extraction for `run_id`, `signal_id`, `candidate_id`, and `condition_id`.
- Decision-log rows now use O(1) set membership before `json.loads`.
- Added `joined_records_progress.json` under the scratch-guarded output directory.
- Added `--progress-every-rows`, default `250000`.
- Final `joined_records.jsonl` and `joined_records_report.json` now write through `.tmp` files and publish via atomic rename.

## Safety Summary

- No runtime trading code was committed.
- No strategy, risk, sizing, order, execution, config, or `.env` files were committed.
- No `runtime/`, `scratch/`, source JSONL, generated reports, or live/RPC artifacts were committed.
- `tools/execution_paper_runtime.py` remains pre-existing dirty and was not staged.
- `tools/shadow_filter_evaluator.py` was not touched.
- Runtime patch reports remain untracked and were not staged.

## Full Real-Data Run Status

The full real-data builder has not yet been rerun after this runtime patch.

## Next Action

Run a fresh safe offline full real-data rerun of `tools/joined_records_builder.py` with process monitoring, then run `tools/shadow_filter_evaluator.py` only if `joined_records.jsonl` is produced successfully.
