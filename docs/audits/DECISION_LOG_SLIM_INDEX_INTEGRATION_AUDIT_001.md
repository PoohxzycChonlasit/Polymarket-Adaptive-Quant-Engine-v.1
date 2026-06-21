# DECISION_LOG_SLIM_INDEX_INTEGRATION_AUDIT_001

## Scope

Status: DISCOVERY + IMPLEMENTATION PLAN ONLY.

No runtime, strategy, signal generation, risk, execution, config, source JSONL, commit, push, or runtime restart changes were made.

Inspected files:

- `tools/joined_records_builder.py`
- `tools/decision_log_slim_index.py`
- `tests/test_joined_records_builder.py`
- `tests/test_decision_log_slim_index.py`
- `scratch/decision_log_slim_index_full/output/decision_log_slim.sqlite`
- `scratch/decision_log_slim_index_full/output/decision_log_slim_manifest.json`

## A. Current Builder Flow

Relevant functions:

| Function | File / Line | Purpose |
|---|---|---|
| `_project_decision_row` | `tools/joined_records_builder.py:261` | Projects raw decision JSONL rows into the small decision row used for joins/output. |
| `_load_decision_indexes` | `tools/joined_records_builder.py:304` | Scans every decision-log JSONL file and builds `by_signal`, `by_candidate`, and `by_condition`. |
| `_find_decision` | `tools/joined_records_builder.py:530` | Applies join precedence: signal id, candidate id, nearest condition timestamp. |
| `_collect_decision_requirements` | `tools/joined_records_builder.py:561` | Collects required `run_id`, signal, candidate, and condition keys from execution close -> source trade open. |
| `_build_record` | `tools/joined_records_builder.py:632` | Merges close, source trade rows, and decision metadata into evaluator-compatible records. |
| `build_joined_records` | `tools/joined_records_builder.py:718` | Orchestrates execution close loading, trade journal indexing, decision indexing, record output. |

Current high-level flow:

1. Load execution paper close events.
2. Load source trade journal indexes.
3. Match each execution close to source `trade_close`.
4. Match source `trade_close` to source `trade_open`.
5. Collect required decision keys from source `trade_open`:
   - required `run_id`
   - required `(run_id, signal_id)`
   - required `(run_id, candidate_id)`
   - required `(run_id, condition_id)`
6. Scan all `decision_log/*.jsonl` files.
7. Parse and retain only rows matching required keys.
8. Build in-memory indexes:
   - `by_signal[(run_id, signal_id)] -> [decision_row]`
   - `by_candidate[(run_id, candidate_id)] -> [decision_row]`
   - `by_condition[(run_id, condition_id)] -> [(timestamp, decision_row)]`
9. For each source open, join decision metadata by precedence:
   - `JOINED_SIGNAL_ID`
   - `JOINED_CANDIDATE_ID`
   - `JOINED_NEAREST_CONDITION`
   - otherwise `JOINED_TRADE_OPEN_ONLY`

Current bottleneck:

The builder still walks the raw decision-log corpus on every run. The full slim-index build confirmed the corpus scan covers 43 files and 421,605 non-empty/malformed candidate lines for the current retained population. Prior full builder attempts timed out after 304.038s without output.

## B. Current Slim Index Schema

Source:

- `tools/decision_log_slim_index.py`
- built artifact: `scratch/decision_log_slim_index_full/output/decision_log_slim.sqlite`

Schema creator:

- `tools/decision_log_slim_index.py:79`

Table:

```text
decisions
```

Columns:

| Column | Type |
|---|---|
| `id` | INTEGER PRIMARY KEY |
| `timestamp_utc` | TEXT |
| `run_id` | TEXT |
| `signal_id` | TEXT |
| `candidate_id` | TEXT |
| `condition_id` | TEXT |
| `edge` | REAL |
| `ev` | REAL |
| `ev_after_spread` | REAL |
| `true_probability` | REAL |
| `volatility_regime` | TEXT |
| `trend_regime` | TEXT |
| `source_file` | TEXT |
| `source_line` | INTEGER |

Indexes:

| Index | Columns |
|---|---|
| `idx_run_signal` | `run_id`, `signal_id` |
| `idx_run_candidate` | `run_id`, `candidate_id` |
| `idx_run_condition_time` | `run_id`, `condition_id`, `timestamp_utc` |

Full build metrics:

| Metric | Value |
|---|---:|
| files_indexed | 43 |
| rows_seen | 421,605 |
| rows_inserted | 421,571 |
| malformed_rows | 34 |
| distinct_run_id | 717 |
| signal_id not null | 420,561 |
| candidate_id not null | 420,561 |
| condition_id not null | 420,670 |
| sqlite_size_bytes | 248,479,744 |

## C. Field Mapping Matrix

| Builder Decision Field | Current Raw Projection | Slim Index Column | Required For |
|---|---|---|---|
| `timestamp_utc` | yes | yes | nearest condition join, join offset reporting |
| `run_id` | yes | yes | all decision join keys |
| `signal_id` | yes | yes | primary decision join |
| `candidate_id` | yes | yes | secondary decision join |
| `condition_id` | yes | yes | fallback nearest timestamp join |
| `edge` | yes | yes | evaluator metadata |
| `ev` | yes | yes | evaluator metadata |
| `ev_after_spread` | yes | yes | evaluator metadata |
| `true_probability` | yes | yes | evaluator metadata |
| `volatility_regime` | yes | yes | evaluator metadata |
| `trend_regime` | yes | yes | evaluator metadata |
| `source_file` | yes | yes | provenance in output record |
| `source_line` | yes | yes | provenance in output record |

Decision fields used by `_build_record` are already present in the slim index.

Fields such as `asset`, `side`, `outcome`, `market_slug`, and `epoch_start_ts` are not in the slim index, but they are also not present in the current builder's decision projection. Current joined records obtain them from source trade rows before consulting the decision row. Therefore their absence is not a regression for slim-index integration.

## D. Missing Field Audit

### Required Fields Missing From Slim Index

None for parity with current `joined_records_builder` decision projection.

The slim index contains all fields currently produced by `_project_decision_row`.

### Non-Field Integration Gaps

The following integration controls are missing and must be added before the builder should consume the index:

| Gap | Impact | Required Handling |
|---|---|---|
| No builder CLI option for slim index | Builder cannot use SQLite yet | Add `--decision-slim-index-root`. |
| No builder freshness validation | Stale/incomplete index could be used | Compare manifest source files against `decision_log_root`. |
| No builder schema validation | Wrong SQLite file could be used | Verify table columns, indexes, and `schema_version`. |
| No mode disclosure in builder report | Audits cannot prove raw scan was skipped | Report `decision_source_mode=SLIM_INDEX` or `RAW_SCAN`. |
| No stale-index fail-closed path | Could silently mix old data with new source logs | Fail closed when supplied index is stale. |

### Existing Slim Index Limitation

The current index builder inserts all valid decision rows, including rows where `signal_id`, `candidate_id`, and `condition_id` are null. This does not block integration, because indexed lookup only retrieves required keyed rows. A later optimization can exclude null-key rows, but that is not required for correctness.

## E. Integration Design

### Recommended Interface

Add optional CLI argument to `tools/joined_records_builder.py`:

```text
--decision-slim-index-root scratch/decision_log_slim_index_full/output
```

Keep existing raw scan path unchanged when this option is omitted.

### New Builder Flow With Slim Index

1. Load execution closes.
2. Load trade journal indexes.
3. Collect required decision keys exactly as today.
4. If `--decision-slim-index-root` is provided:
   - validate index root is under `scratch/`
   - load and validate `decision_log_slim_manifest.json`
   - validate `decision_log_slim.sqlite` exists
   - validate schema version and required columns/indexes
   - validate source file freshness against `--decision-log-root`
   - query SQLite for only required keys
   - build the same in-memory structures as current raw scan:
     - `by_signal`
     - `by_candidate`
     - `by_condition`
5. If `--decision-slim-index-root` is omitted:
   - use current `_load_decision_indexes` raw JSONL scan.

### Proposed Helper Functions

Add to `tools/joined_records_builder.py`:

```text
_validate_decision_slim_index(index_root, decision_log_root) -> dict
_load_decision_indexes_from_slim_index(index_root, requirements, max_decision_rows_loaded) -> dict
_query_slim_index_by_signal(conn, required_signal_ids) -> iterable[dict]
_query_slim_index_by_candidate(conn, required_candidate_ids) -> iterable[dict]
_query_slim_index_by_condition(conn, required_condition_ids) -> iterable[dict]
```

### Query Strategy

For v1, use simple keyed SQL lookups. The expected required key set is small enough for this to be safe:

- bounded run required keys are tiny
- recent full joined builder required keys are roughly hundreds, not hundreds of thousands

Signal join:

```sql
SELECT ... FROM decisions
WHERE run_id = ? AND signal_id = ?
ORDER BY timestamp_utc, source_file, source_line
```

Candidate join:

```sql
SELECT ... FROM decisions
WHERE run_id = ? AND candidate_id = ?
ORDER BY timestamp_utc, source_file, source_line
```

Condition join:

```sql
SELECT ... FROM decisions
WHERE run_id = ? AND condition_id = ?
ORDER BY timestamp_utc, source_file, source_line
```

If repeated per-key queries become slow, v2 can use a temporary required-key table and a single join query. That should not be built before v1 is measured.

### Report Additions

Add to `joined_records_report.json`:

```json
{
  "decision_source_mode": "SLIM_INDEX",
  "decision_slim_index_root": "scratch/decision_log_slim_index_full/output",
  "decision_slim_index_schema_version": "decision_log_slim_index.v1",
  "decision_slim_index_freshness_status": "FRESH",
  "decision_slim_index_rows_loaded": 0,
  "decision_rows_seen": 0,
  "decision_rows_parsed": 0,
  "decision_rows_retained": 0
}
```

For raw scan mode:

```json
{
  "decision_source_mode": "RAW_SCAN"
}
```

## F. Expected Runtime Impact

Known measurements:

| Measurement | Runtime |
|---|---:|
| bounded 50 builder before runtime patch | 35.363s |
| bounded 50 builder after runtime patch | 49.038s |
| full builder after memory patch | timed out after 304.038s |
| full slim index build | 160.324s |

Current full builder runtime:

- observed: `>304.038s` because the full builder timed out before output
- bounded linear estimate using post-runtime-patch bounded 50:
  - `49.038 * 731 / 50 ~= 717s`
  - this is only a rough scaling estimate because the decision scan is largely fixed-cost and not purely per-record

Expected after SQLite lookup:

- bounded 50 target: `<10s`
- full joined builder target: `<60s`
- conservative expected full range before measurement: `20-75s`

Estimated speedup:

| Baseline | Expected Runtime | Estimated Speedup |
|---|---:|---:|
| observed timeout `>304s` | `<60s target` | at least 5x |
| bounded-linear estimate `~717s` | `20-75s` | ~9.5x to 35x |

Primary saved cost:

- eliminating repeated raw decision-log JSONL scans
- avoiding repeated line parsing/extraction over the decision-log corpus
- loading only approximately the rows needed for the joined-records requirements

Important caveat:

The full joined builder has not yet been benchmarked with SQLite integration. These are estimates based on measured raw scan costs and the full slim index artifact.

## G. Safety Review

Integration must preserve these boundaries:

- no runtime modifications
- no strategy/risk/execution changes
- no source JSONL writes
- no writes under `runtime/`
- no live trading paths
- no automatic index rebuild from inside the builder
- no silent fallback from stale slim index to raw scan when `--decision-slim-index-root` is explicitly supplied

Fail-closed conditions:

- missing `decision_log_slim.sqlite`
- missing `decision_log_slim_manifest.json`
- schema version mismatch
- missing required columns
- missing required indexes
- source file count mismatch
- source file added/removed
- source file size mismatch
- source file `mtime_ns` mismatch
- SQLite query failure
- retained/loaded row count exceeds `--max-decision-rows-loaded`

Potential failure modes:

| Failure Mode | Risk | Control |
|---|---|---|
| Stale index | Wrong decisions joined | Manifest freshness validation. |
| Bounded/test index used as full index | Incomplete joins | Validate manifest files/rows against decision-log root. |
| Schema mismatch | Missing metadata or crash | Validate schema before query. |
| Different ordering than raw scan | Join status drift | Order by `timestamp_utc, source_file, source_line`; compare raw vs slim fixture tests. |
| Duplicate condition timestamp ambiguity changes | Different ambiguity counts | Preserve existing `_nearest_decision` behavior using same sorted tuple structure. |
| Numeric type coercion differences | Minor report differences | Existing slim index stores numeric metrics as REAL; tests should compare output parity. |
| SQLite artifact accidentally committed | Repo bloat | Keep output under `scratch/`; do not stage scratch. |

## H. Implementation Scope

Exact files that would require modification:

- `tools/joined_records_builder.py`
- `tests/test_joined_records_builder.py`

Files that should not be modified:

- `tools/decision_log_slim_index.py`
- `tests/test_decision_log_slim_index.py`
- `tools/execution_paper_runtime.py`
- `tools/shadow_filter_evaluator.py`
- `main.py`
- `polymarket/`
- `utils/`
- `config/`
- `.env`
- `runtime/`
- source JSONL files
- strategy/risk/sizing/order/live execution files

Implementation should not rebuild the slim index. It should only consume a prebuilt, verified scratch index.

## I. Recommended Validation Plan

### 1. Unit Tests

Add or update `tests/test_joined_records_builder.py`:

1. Slim-index path joins by `(run_id, signal_id)`.
2. Slim-index path joins by `(run_id, candidate_id)`.
3. Slim-index path joins by nearest `(run_id, condition_id, timestamp_utc)`.
4. Slim-index path preserves ambiguous nearest timestamp behavior.
5. Slim-index output matches raw scan output for a synthetic fixture.
6. Missing manifest fails closed.
7. Missing SQLite file fails closed.
8. Stale source file size fails closed.
9. Stale source file `mtime_ns` fails closed.
10. Schema mismatch fails closed.
11. Explicit slim-index mode does not call raw JSONL decision scan.
12. Raw scan mode remains unchanged when no slim index is supplied.
13. `joined_records_report.json` contains `decision_source_mode`.

### 2. Bounded Validation

Run:

```text
py -3.11 tools/joined_records_builder.py ^
  --execution-journal-root scratch/execution_paper_phase_c_full_eligible_replay_rerun/output_root/runtime/quant_data/execution_paper ^
  --trade-journal-root runtime/quant_data/trade_journal ^
  --decision-log-root runtime/quant_data/decision_log ^
  --decision-slim-index-root scratch/decision_log_slim_index_full/output ^
  --output-dir scratch/joined_records_builder_slim_bounded/output ^
  --max-join-seconds 120 ^
  --max-records 50
```

Acceptance:

- completes successfully
- `decision_source_mode=SLIM_INDEX`
- no raw decision-log scan progress sidecar appears
- join rate remains `50/50` if source inputs match prior bounded run
- runtime target `<10s`
- evaluator still runs on output

### 3. Full Validation

Run full joined builder with slim index:

```text
py -3.11 tools/joined_records_builder.py ^
  --execution-journal-root scratch/execution_paper_phase_c_full_eligible_replay_rerun/output_root/runtime/quant_data/execution_paper ^
  --trade-journal-root runtime/quant_data/trade_journal ^
  --decision-log-root runtime/quant_data/decision_log ^
  --decision-slim-index-root scratch/decision_log_slim_index_full/output ^
  --output-dir scratch/joined_records_builder_slim_full/output ^
  --max-join-seconds 120
```

Acceptance:

- completes successfully
- output files exist
- join rate `>=95%`
- evaluator runs successfully
- key filter metrics match prior audits within reasonable tolerance
- runtime target `<60s`
- no code/runtime/source mutations

### 4. Rollback Plan

If slim-index integration fails:

1. Do not delete the raw scan path.
2. Do not modify runtime.
3. Run builder without `--decision-slim-index-root` to restore current behavior.
4. Keep slim-index artifact under `scratch/` for diagnosis.
5. File failure as an offline tooling defect, not a strategy/runtime issue.

## Final Answer

READY_FOR_SLIM_INDEX_INTEGRATION

Justification:

- The full slim index exists and contains 421,571 rows across 43 decision-log files.
- The SQLite schema contains every decision field currently projected and consumed by `joined_records_builder`.
- Lookup indexes match the builder's three decision join paths:
  - `(run_id, signal_id)`
  - `(run_id, candidate_id)`
  - `(run_id, condition_id, timestamp_utc)`
- No required decision field is missing for parity with the current builder.
- The remaining work is a contained offline-tool integration in `tools/joined_records_builder.py` plus focused tests.
- The integration can preserve raw scan fallback and fail closed on stale or invalid slim indexes.
