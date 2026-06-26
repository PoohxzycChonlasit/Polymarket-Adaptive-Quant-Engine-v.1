# DECISION_LOG_SLIM_INDEX_DESIGN_001

## Scope

Mode: DESIGN ONLY.

No code changes, commits, pushes, runtime restarts, strategy changes, risk changes, execution changes, config changes, or runtime data mutations are authorized by this document.

## Problem Statement

`tools/joined_records_builder.py` no longer fails from retained-row memory pressure, but it still scans the decision-log corpus on every run.

Observed benchmark:

| Metric | Value |
|---|---:|
| pre-runtime-patch bounded 50 runtime | 35.363s |
| post-runtime-patch bounded 50 runtime | 49.038s |
| decision_rows_seen | 421,539 |
| decision_rows_parsed | 1,303 |
| decision_rows_retained | 1,303 |
| memory_guard_status | OK |

Interpretation:

The bottleneck is not retained rows. The bottleneck is repeatedly walking the raw decision-log corpus, currently measured at approximately 12.49GB for the full corpus.

## Current Builder Flow

Current relevant flow in `tools/joined_records_builder.py`:

1. Load execution paper close events.
2. Load source trade journal indexes.
3. Collect required decision keys from matched trade opens:
   - `run_id`
   - `(run_id, signal_id)`
   - `(run_id, candidate_id)`
   - `(run_id, condition_id)`
4. Scan every `runtime/quant_data/decision_log/*.jsonl` line.
5. Retain only projected matching decision rows.
6. Join by:
   - signal id
   - candidate id
   - nearest condition id within `--max-join-seconds`

The scan stage is now the dominant cost.

## Design Options

### Option 1 - Safe EV Preservation: Scratch SQLite Slim Index

Build a reusable, scratch-only SQLite index from decision logs. The joined records builder reads the SQLite index instead of scanning raw decision logs.

Benefits:

- Uses only Python standard library `sqlite3`.
- Supports indexed lookup by signal, candidate, and condition/time.
- Avoids repeated 12.49GB raw scans.
- Keeps all outputs outside `runtime/`.
- Preserves fail-closed freshness checks.

Trade-off:

- One initial index build still scans the raw corpus.
- SQLite is less transparent than JSONL, but much more appropriate for repeated keyed lookup.

### Option 2 - Aggressive Information Discovery: Required-Key Scratch Index

Have the builder emit `required_keys.json`, then build a smaller scratch index containing only matching rows for that key set.

Benefits:

- Smaller index.
- Faster joined builder load after the scoped index exists.

Trade-off:

- Still scans the full raw decision-log corpus for each new required key set.
- Less reusable across bounded/full reruns and future evaluator passes.
- Does not solve the repeated scan problem as well as a reusable full slim projection.

### Option 3 - Structural Root-Cause Path: Partitioned JSONL Cache

Create partitioned projected JSONL files by `run_id` or date.

Benefits:

- Human-inspectable.
- Simple append/read model.

Trade-off:

- Requires manual secondary lookup structures or repeated partition scans.
- Nearest timestamp lookup is awkward without an index.
- Compressed JSONL reduces disk but worsens random access.
- Date-window pruning is weak for this dataset because the existing audit indicates it would skip only about 1.57%.

## Recommendation

Use Option 1: a scratch-only SQLite slim index.

Final recommended component:

```text
tools/decision_log_slim_index.py
```

Recommended consumer flag:

```text
--decision-slim-index-root scratch/decision_log_slim_index/output
```

The index should be reusable across joined-records runs until the source decision-log corpus changes.

## Index Format Decision

| Format | Verdict | Reason |
|---|---|---|
| SQLite | BEST | Standard library, indexed lookup, manifest table, deterministic, no dependency creep. |
| JSONL | WEAK | Simple but still requires scanning unless heavily partitioned. |
| Compressed JSONL | WEAK | Smaller storage but poor random access and repeated decompression cost. |
| Parquet | REJECT | Good columnar format but adds dependency unless already adopted for this path. |

Chosen format:

```text
SQLite database + JSON manifest/report
```

Expected output layout:

```text
scratch/decision_log_slim_index/output/
  decision_log_slim.sqlite
  decision_log_slim_manifest.json
  decision_log_slim_build_report.json
```

## SQLite Schema

Recommended table:

```sql
CREATE TABLE decision_rows (
  id INTEGER PRIMARY KEY,
  timestamp_utc TEXT,
  run_id TEXT NOT NULL,
  signal_id TEXT,
  candidate_id TEXT,
  condition_id TEXT,
  edge REAL,
  ev REAL,
  ev_after_spread REAL,
  true_probability REAL,
  volatility_regime TEXT,
  trend_regime TEXT,
  source_file TEXT NOT NULL,
  source_line INTEGER NOT NULL,
  source_row_sha256 TEXT NOT NULL
);
```

Recommended uniqueness:

```sql
CREATE UNIQUE INDEX ux_decision_source
ON decision_rows(source_file, source_line);
```

Recommended lookup indexes:

```sql
CREATE INDEX idx_decision_signal
ON decision_rows(run_id, signal_id);

CREATE INDEX idx_decision_candidate
ON decision_rows(run_id, candidate_id);

CREATE INDEX idx_decision_condition_time
ON decision_rows(run_id, condition_id, timestamp_utc);
```

Recommended source manifest table:

```sql
CREATE TABLE source_files (
  path TEXT PRIMARY KEY,
  size_bytes INTEGER NOT NULL,
  mtime_ns INTEGER NOT NULL,
  sha256 TEXT,
  lines_seen INTEGER NOT NULL,
  rows_indexed INTEGER NOT NULL
);
```

The index must store only projected fields. It must not store full raw decision payloads.

## Projection Contract

The slim index may preserve only:

- `timestamp_utc`
- `run_id`
- `signal_id`
- `candidate_id`
- `condition_id`
- `edge`
- `ev`
- `ev_after_spread`
- `true_probability`
- `volatility_regime`
- `trend_regime`
- `source_file`
- `source_line`
- `source_row_sha256`

Rows without `run_id` should be excluded unless a future consumer explicitly needs them.

Rows with none of `signal_id`, `candidate_id`, or `condition_id` should be excluded because they cannot satisfy the joined-records builder decision join.

## Tool Boundary

The index builder should be a separate offline tool:

```text
tools/decision_log_slim_index.py
```

Rationale:

- Keeps `joined_records_builder` focused on joining.
- Makes the expensive scan explicit and reusable.
- Allows independent tests for freshness, projection, and scratch-only safety.
- Prevents hidden background indexing inside evaluator workflows.

Suggested CLI:

```text
py -3.11 tools/decision_log_slim_index.py build ^
  --decision-log-root runtime/quant_data/decision_log ^
  --output-root scratch/decision_log_slim_index/output
```

Suggested verification CLI:

```text
py -3.11 tools/decision_log_slim_index.py verify ^
  --decision-log-root runtime/quant_data/decision_log ^
  --index-root scratch/decision_log_slim_index/output
```

Suggested builder consumption:

```text
py -3.11 tools/joined_records_builder.py ^
  --execution-journal-root scratch/execution_paper_phase_c_full_eligible_replay_rerun/output_root/runtime/quant_data/execution_paper ^
  --trade-journal-root runtime/quant_data/trade_journal ^
  --decision-log-root runtime/quant_data/decision_log ^
  --decision-slim-index-root scratch/decision_log_slim_index/output ^
  --output-dir scratch/joined_records_builder_full/output ^
  --max-join-seconds 120
```

When `--decision-slim-index-root` is supplied, the builder should:

1. Verify index freshness.
2. Query SQLite for required `(run_id, signal_id)`, `(run_id, candidate_id)`, and `(run_id, condition_id)` keys.
3. Build the same in-memory `by_signal`, `by_candidate`, and `by_condition` structures it uses today.
4. Skip raw decision-log scanning entirely.

## Freshness And Invalidation

Default freshness mode should be fast and deterministic:

- source file count
- relative source file paths
- file sizes
- `mtime_ns`
- index schema version
- projection field set

Recommended manifest fields:

```json
{
  "schema_version": "decision_log_slim_index.v1",
  "created_at_utc": "...",
  "decision_log_root": "runtime/quant_data/decision_log",
  "source_file_count": 0,
  "source_total_bytes": 0,
  "source_fingerprint": "...",
  "projection_fields": [],
  "sqlite_path": "decision_log_slim.sqlite",
  "indexed_rows": 0,
  "excluded_rows": 0,
  "malformed_rows": 0
}
```

Optional strict mode:

```text
--strict-source-hash
```

Strict mode computes SHA256 for each source decision-log file. This is more expensive over 12.49GB, so it should be optional. The default fast mode is enough to detect normal append/replace mutations via size and `mtime_ns`.

Fail-closed invalidation:

- missing source file: stale
- added source file: stale
- size mismatch: stale
- `mtime_ns` mismatch: stale
- schema version mismatch: stale
- projection-field mismatch: stale
- missing SQLite database: stale

The joined builder should refuse to use a stale index. It may fall back to raw scanning only if the operator does not provide `--decision-slim-index-root`.

## Partitioning Decision

Do not partition into many JSONL files for v1.

Use one SQLite database with lookup indexes. SQLite already provides the needed partition behavior through indexed keys.

If v1 SQLite becomes too large or slow, a later v2 can shard by `run_id_hash_prefix`, but that should not be built preemptively.

## Performance Targets

Index build:

- May take minutes.
- May scan the full 12.49GB corpus once.
- Should emit progress every N files and rows.
- Should keep memory bounded by streaming JSONL line by line and batching SQLite inserts.

Joined builder with existing fresh index:

| Scenario | Target |
|---|---:|
| bounded 50 records | <10s |
| full eligible joined builder | <60s |
| freshness check using size/mtime manifest | <5s |

The build cost is acceptable because it replaces repeated raw scans.

## Safety Rules

The index builder must:

- write only under `scratch/`
- reject output roots under `runtime/`
- never modify source JSONL files
- never write into `runtime/quant_data/decision_log`
- never import runtime trading modules
- never change strategy, risk, sizing, execution, config, or live trading behavior
- use atomic writes for manifest/report/database replacement

The joined builder must:

- treat a stale index as fail-closed
- never silently mix stale indexed rows with fresh raw rows
- include index manifest metadata in `joined_records_report.json`
- disclose whether decisions came from `RAW_SCAN` or `SLIM_INDEX`

## Required Implementation Changes

### New tool

Add:

```text
tools/decision_log_slim_index.py
```

Responsibilities:

- stream source decision logs
- project only required fields
- insert projected rows into SQLite
- write manifest and build report
- verify freshness
- enforce scratch-only output

### Joined records builder

Modify:

```text
tools/joined_records_builder.py
```

Required changes:

- add CLI option `--decision-slim-index-root`
- add index freshness validation path
- add SQLite-backed decision loading path
- preserve current raw scan path when no slim index is provided
- add report fields:
  - `decision_source_mode`
  - `decision_slim_index_root`
  - `decision_slim_index_schema_version`
  - `decision_slim_index_freshness_status`
  - `decision_slim_index_rows_queried`
  - `decision_slim_index_rows_loaded`

### Tests

Add:

```text
tests/test_decision_log_slim_index.py
```

Update:

```text
tests/test_joined_records_builder.py
```

## Required Tests

Index tool tests:

1. Creates only projected rows.
2. Does not store full raw payloads.
3. Excludes rows missing `run_id`.
4. Excludes rows without `signal_id`, `candidate_id`, or `condition_id`.
5. Creates lookup indexes.
6. Produces deterministic manifest.
7. Detects stale index on source file size change.
8. Detects stale index on source file mtime change.
9. Rejects output outside `scratch/`.
10. Streams input line by line.

Builder integration tests:

1. Builder loads decisions from slim index when `--decision-slim-index-root` is provided.
2. Builder does not call raw decision-log scan when slim index is fresh.
3. Builder fails closed on stale slim index.
4. Builder joins by signal id from slim index.
5. Builder joins by candidate id from slim index.
6. Builder performs nearest condition timestamp join from slim index.
7. Builder output schema remains evaluator-compatible.
8. Builder report identifies `decision_source_mode=SLIM_INDEX`.
9. Raw scan mode remains unchanged when no slim index is supplied.

Performance fixture tests:

1. Large irrelevant decision fixture indexes only useful projected rows.
2. Query path uses indexed lookups rather than full table scan.
3. Bounded builder fixture completes without scanning raw decision-log fixture when index is supplied.

## Rejected Paths

### Persistent cache under `runtime/`

Rejected. Runtime is forbidden for this design. The index is a derived analysis artifact and belongs under `scratch/`.

### `.cache/` in repo root

Not recommended for v1. It is easy to confuse with persistent project state and may be accidentally staged. Use explicit `scratch/decision_log_slim_index/output`.

### Date-window-only filtering

Rejected as primary fix. Existing audit indicates it would skip only about 1.57% of decision logs, so it does not solve the bottleneck.

### Compressed JSONL

Rejected as primary format. It reduces storage but does not provide efficient keyed lookup.

## Readiness Impact

This design unblocks repeated joined-records builder runs without weakening evidence quality:

- raw decision logs remain immutable
- the index is derived and disposable
- freshness is explicit
- source provenance is preserved through `source_file`, `source_line`, and `source_row_sha256`
- stale artifacts fail closed

## Implementation Boundary

Allowed future implementation files:

- `tools/decision_log_slim_index.py`
- `tests/test_decision_log_slim_index.py`
- `tools/joined_records_builder.py`
- `tests/test_joined_records_builder.py`

Files that must remain untouched:

- `runtime/`
- `main.py`
- `polymarket/`
- `utils/`
- `config/`
- `.env`
- strategy/risk/sizing/order/live execution files
- source JSONL files

## Final Verdict

READY_FOR_SLIM_INDEX_IMPLEMENTATION

Reason:

The current evidence shows retained decision rows are already bounded, but raw corpus scanning remains expensive. A scratch-only SQLite slim index is the smallest reusable design that removes repeated 12.49GB scans while preserving deterministic joins, source provenance, and fail-closed freshness.
