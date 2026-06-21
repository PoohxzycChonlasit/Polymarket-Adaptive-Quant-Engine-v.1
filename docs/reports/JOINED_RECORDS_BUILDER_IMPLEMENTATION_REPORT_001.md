# JOINED_RECORDS_BUILDER_IMPLEMENTATION_REPORT_001

Date: 2026-06-21
Mode: Offline tool implementation report

## Scope

Approved design:

```text
JOINED_RECORDS_BUILDER_PLAN_001
```

Allowed implementation files:

```text
tools/joined_records_builder.py
tests/test_joined_records_builder.py
```

Implementation stayed within the approved offline-tool boundary.

## Files Created

```text
tools/joined_records_builder.py
tests/test_joined_records_builder.py
JOINED_RECORDS_BUILDER_IMPLEMENTATION_REPORT_001.md
JOINED_RECORDS_BUILDER_PRE_COMMIT_AUDIT_001.md
```

## Implemented Behavior

The builder creates evaluator-compatible joined execution close records:

- reads `execution_paper_close` events from `execution-journal-root/journals/trade/*.jsonl`
- reads source `trade_journal` JSONL
- reads `decision_log` JSONL
- joins execution close -> source trade close by `source_file + source_line`
- verifies source hash when available
- joins source close -> source open by identity fields
- enriches trade-open records from decision logs by:
  - `run_id + signal_id`
  - `run_id + candidate_id`
  - `run_id + condition_id + nearest timestamp`
- bounds nearest timestamp join by `--max-join-seconds`
- writes `joined_records.jsonl`
- writes `joined_records_report.json`
- rejects output paths outside `scratch/`

## CLI

Implemented command shape:

```text
py -3.11 tools/joined_records_builder.py ^
  --execution-journal-root scratch/execution_paper_phase_c_full_eligible_replay_rerun/output_root/runtime/quant_data/execution_paper ^
  --trade-journal-root runtime/quant_data/trade_journal ^
  --decision-log-root runtime/quant_data/decision_log ^
  --output-dir scratch/joined_records_builder/output ^
  --max-join-seconds 120
```

Implemented options:

```text
--execution-journal-root
--trade-journal-root
--decision-log-root
--output-dir
--max-join-seconds
--fail-on-source-hash-mismatch
--max-records
```

## Output Schema

Each joined record includes:

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

Additional provenance fields are included when available:

```text
execution_run_id
execution_source_event_sha256
trade_open_source_file
trade_open_source_line
trade_close_source_file
trade_close_source_line
decision_source_file
decision_source_line
candidate_id
condition_id
epoch_start_ts
```

## Tests Added

Targeted tests cover:

- join by `signal_id`
- join by `candidate_id`
- fallback nearest timestamp join
- outside-window decision behavior
- ambiguous nearest timestamp behavior
- source close missing
- source open missing
- missing metadata counts
- scratch-only output guard
- JSONL output schema
- source hash mismatch reporting
- no nested close-by-decision loop behavior fixture
- compatibility with `shadow_filter_evaluator`
- CLI output generation
- forbidden import audit

## Validation Results

Commands run:

```text
py -3.11 -m py_compile tools/joined_records_builder.py
py -3.11 -m pytest tests/test_joined_records_builder.py -q
git diff --check
```

Results:

```text
py_compile: PASS
pytest: PASS, 15 passed
git diff --check: PASS
```

## Safety Summary

- No runtime trading code changed.
- No strategy code changed.
- No risk code changed.
- No sizing code changed.
- No order/live code changed.
- No source JSONL files changed.
- No `runtime/` files written by implementation.
- No `tools/execution_paper_runtime.py` changes made by this task.
- No `tools/shadow_filter_evaluator.py` changes made.
- No staging performed.
- No commit performed.
- No push performed.
- Runtime was not restarted.

## Final Implementation Verdict

JOINED_RECORDS_BUILDER_READY_FOR_REVIEW

STOP: Do not commit. Do not push. Do not stage anything.
