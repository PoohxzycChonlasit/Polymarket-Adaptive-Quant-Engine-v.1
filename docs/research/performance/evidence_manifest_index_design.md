# Evidence Manifest And Index Layer Design

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Mode: docs-only design. No implementation, no runtime mutation, no library installs, no replay, no strategy/risk/execution/live changes.

## Executive Verdict

The evidence layer should become a two-step offline discovery system:

```text
raw JSONL evidence
-> compact manifests
-> offline indexes
-> query/report/dashboard consumers
```

The runtime loop should keep doing only one thing: emit compact, append-only truth records. It should not scan history, build indexes, compact files, run DuckDB, write Parquet, or serve dashboard queries.

Recommended path:

1. Define manifest contracts now.
2. Generate manifests asynchronously for completed evidence windows only.
3. Build disposable offline indexes from manifests plus raw JSONL.
4. Use those indexes to route agents quickly to the right date, run, source, and lineage key.
5. Convert to Parquet only after manifest validation proves source counts, parse status, and lineage are stable.

## Design Goals

| Goal | Meaning |
|---|---|
| Avoid repeated 10GB scans | Agents and audits should start from manifests/indexes, not raw folders. |
| Preserve raw truth | JSONL remains canonical and immutable. |
| Keep runtime lightweight | Runtime writes evidence; offline jobs discover and index it later. |
| Preserve lineage | Indexes must center on `date`, `run_id`, and `(run_id, paper_trade_replay_key)`. |
| Separate truth layers | Signal, Path Truth, Executable Truth, and cognition metadata must not collapse into one claim. |
| Support future DuckDB/Parquet | Index contracts should map naturally to columnar storage later. |
| Fail soft | Missing fields produce null/unknown status, not fabricated truth. |

## Non-Goals

- No code implementation.
- No library installation.
- No runtime event changes.
- No JSONL rewrite.
- No archive movement.
- No Parquet generation.
- No DuckDB creation.
- No policy consumer inside trading runtime.
- No executable PnL approval.
- No S3/Growth/live promotion.

## Source Evidence Classes

Primary runtime evidence sources:

| Source class | Typical path | Canonical? | Notes |
|---|---|---|---|
| trade journal | `runtime/quant_data/trade_journal/*.jsonl` | Yes | Open/close outcome records and replay key spine. |
| decision log | `runtime/quant_data/decision_log/*.jsonl` | Yes | Candidate, model, EV, rejection, and decision context. |
| execution log | `runtime/quant_data/execution_log/*.jsonl` | Yes | Submit/fill/cancel/paper execution observability. |
| path truth | `runtime/quant_data/path_truth/*.jsonl` | Yes | Checkpoint path continuity and replay key linkage. |
| system health | `runtime/quant_data/system_health/*.jsonl` | Yes | Runtime health, exceptions, write/telegram/process signals. |
| risk log | `runtime/quant_data/risk_log/*.jsonl` | Yes, if present | Risk visibility and blocker context. |
| research log | `runtime/quant_data/research_log/*.jsonl` | Yes, if present | Regime/research diagnostic fields. |
| market snapshots | `runtime/quant_data/market_snapshots/*.jsonl` | Yes, if present | Quote/orderbook/depth context. |
| runtime logs | `logs/*.log` | Supporting | Incident and process context, not primary quant truth. |
| docs/research | `docs/research/**/*.md` | Cognition | Human/governance layer, not raw execution evidence. |

## Layer Model

```text
Layer 0: Raw evidence
  append-only JSONL and logs

Layer 1: Source manifests
  file-level inventory, counts, schema, checksums, run IDs

Layer 2: Domain indexes
  daily/session/run/path/session-edge/executable summaries

Layer 3: Offline query substrate
  future DuckDB tables and/or Parquet datasets

Layer 4: Cognition and operator navigation
  docs, dashboards, Telegram digests, Hermes notes
```

Only Layer 0 is produced by runtime. Layers 1-4 are offline or cognition layers.

## 1. Evidence Manifest Structure

### File Manifest

One manifest row per source file.

Suggested logical name:

```text
evidence_file_manifest
```

Fields:

| Field | Class | Required | Meaning |
|---|---|---:|---|
| `manifest_version` | runtime-safe metadata | yes | Manifest schema version. |
| `generated_at` | offline-only indexing | yes | When the manifest row was generated. |
| `repo_root` | archive-only fields | yes | Root used for relative paths. |
| `source_path` | runtime-safe metadata | yes | Relative path to raw evidence file. |
| `source_type` | runtime-safe metadata | yes | `trade_journal`, `decision_log`, `execution_log`, etc. |
| `evidence_date` | runtime-safe metadata | yes | UTC date inferred from filename or records. |
| `active_file` | offline-only indexing | yes | Whether file is current active evidence and should not archive. |
| `archive_class` | archive-only fields | yes | `ACTIVE_DO_NOT_ARCHIVE`, `RECENT_KEEP_HOT`, `READY_TO_ARCHIVE`, etc. |
| `bytes` | offline-only indexing | yes | Source file size. |
| `line_count` | offline-only indexing | yes | Physical JSONL lines. |
| `parse_ok_count` | offline-only indexing | yes | Valid JSON rows. |
| `parse_error_count` | offline-only indexing | yes | Invalid JSON rows. |
| `first_ts` | offline-only indexing | if available | Earliest event timestamp. |
| `last_ts` | offline-only indexing | if available | Latest event timestamp. |
| `run_ids` | offline-only indexing | yes | Distinct run IDs present. |
| `event_types` | offline-only indexing | yes | Distinct event types present. |
| `field_presence` | offline-only indexing | yes | Compact field coverage map or reference. |
| `schema_fingerprint` | offline-only indexing | yes | Stable hash of observed field names/types. |
| `sha256` | archive-only fields | yes | Hash for source integrity. |
| `derived_manifest_refs` | cognition-layer metadata | optional | Links to generated domain indexes. |
| `research_refs` | cognition-layer metadata | optional | Docs that cite this file/date/run. |
| `notes` | cognition-layer metadata | optional | Human caveats. |

### Run Manifest

One manifest row per observed run ID.

Suggested logical name:

```text
evidence_run_manifest
```

Fields:

| Field | Class | Required | Meaning |
|---|---|---:|---|
| `run_id` | runtime-safe metadata | yes | Canonical run identity. |
| `pid` | runtime-safe metadata | if available | Runtime process ID inferred from run ID or records. |
| `mode` | runtime-safe metadata | if available | `paper`, `live`, `verify`, etc. |
| `started_at` | offline-only indexing | if available | Earliest event timestamp for the run. |
| `ended_at` | offline-only indexing | if available | Latest event timestamp or shutdown marker. |
| `run_status` | offline-only indexing | yes | `ACTIVE`, `COMPLETED`, `STALE`, `UNKNOWN`, `FAILED`. |
| `source_files` | offline-only indexing | yes | Source file refs containing the run. |
| `trade_open_count` | offline-only indexing | yes | Count from trade journal. |
| `trade_close_count` | offline-only indexing | yes | Count from trade journal. |
| `path_checkpoint_count` | offline-only indexing | yes | Count from path truth. |
| `market_analysis_exception_count` | offline-only indexing | yes | Count from health/log evidence if available. |
| `telegram_failure_count` | offline-only indexing | yes | Count from health/log evidence if available. |
| `write_error_count` | offline-only indexing | yes | Count from health/log evidence if available. |
| `replay_key_coverage` | offline-only indexing | yes | Coverage of `paper_trade_replay_key` where expected. |
| `join_quality` | offline-only indexing | yes | `DIRECT`, `STRONG`, `WEAK`, `PROXY`, `BLOCKED`, or mixed summary. |
| `truth_status` | cognition-layer metadata | yes | Signal/path/executable truth labels. |
| `research_refs` | cognition-layer metadata | optional | Docs referencing this run. |

### Schema Manifest

One row per source type/date/schema fingerprint.

Suggested logical name:

```text
evidence_schema_manifest
```

Fields:

| Field | Class | Required | Meaning |
|---|---|---:|---|
| `source_type` | runtime-safe metadata | yes | Event source. |
| `evidence_date` | runtime-safe metadata | yes | UTC date. |
| `schema_fingerprint` | offline-only indexing | yes | Hash of observed field names/types. |
| `fields_present` | offline-only indexing | yes | Field list. |
| `fields_missing_from_contract` | offline-only indexing | yes | Known expected fields absent. |
| `new_fields` | offline-only indexing | yes | Fields not in prior contract. |
| `null_rate_by_field` | offline-only indexing | optional | Null/absent coverage map. |
| `compatible_with_parquet_contract` | offline-only indexing | yes | Future conversion readiness. |
| `notes` | cognition-layer metadata | optional | Human caveats. |

## 2. Daily / Session / Run Indexes

### Daily Index

Purpose: answer "what happened on this evidence date?" without scanning raw files.

Suggested logical name:

```text
daily_evidence_index
```

Fields:

| Field | Class | Meaning |
|---|---|---|
| `evidence_date` | runtime-safe metadata | UTC evidence date. |
| `source_file_count` | offline-only indexing | Count of raw source files discovered. |
| `total_bytes` | offline-only indexing | Raw source bytes. |
| `total_lines` | offline-only indexing | Raw JSONL line count. |
| `parse_error_count` | offline-only indexing | Total parse errors. |
| `run_count` | offline-only indexing | Distinct run IDs. |
| `run_ids` | offline-only indexing | Compact list or reference. |
| `trade_open_count` | offline-only indexing | Daily trade opens. |
| `trade_close_count` | offline-only indexing | Daily trade closes. |
| `path_truth_line_count` | offline-only indexing | Path Truth rows. |
| `full_coverage_trade_count` | offline-only indexing | Trades with complete checkpoint coverage. |
| `fast_close_count` | offline-only indexing | Fast-close rows/trades. |
| `market_analysis_exception_count` | offline-only indexing | Health exception count. |
| `archive_class` | archive-only fields | Daily archive readiness. |
| `gate_state` | cognition-layer metadata | Path/executable/session gate status. |
| `active_research_refs` | cognition-layer metadata | Docs using this date. |

### Session Index

Purpose: answer "what is the evidence for a UTC hour/session bucket?"

Suggested logical name:

```text
session_evidence_index
```

Fields:

| Field | Class | Meaning |
|---|---|---|
| `evidence_date` | runtime-safe metadata | UTC date. |
| `session_hour_utc` | runtime-safe metadata | Hour bucket, e.g. `02h`, `09h`, `10h`. |
| `session_label` | cognition-layer metadata | `02h_HOSTILE_CANDIDATE`, `09h10h_EDGE_CANDIDATE`, etc. |
| `trade_count` | offline-only indexing | Trades in bucket. |
| `tp_count` | offline-only indexing | TP outcomes. |
| `sl_count` | offline-only indexing | SL outcomes. |
| `win_rate` | offline-only indexing | Signal outcome metric, not executable truth. |
| `btc_count` | offline-only indexing | Asset split. |
| `eth_count` | offline-only indexing | Asset split. |
| `yes_count` | offline-only indexing | Side split. |
| `no_count` | offline-only indexing | Side split. |
| `opening_count` | offline-only indexing | Lifecycle split. |
| `active_count` | offline-only indexing | Lifecycle split. |
| `fast_close_count` | offline-only indexing | Fast-close behavior. |
| `path_join_direct_rate` | offline-only indexing | Direct join coverage. |
| `research_verdict` | cognition-layer metadata | `SUPPORTED`, `WEAKENED`, `ADVERSE`, `UNAVAILABLE`, etc. |

### Run Index

Purpose: answer "where is all evidence for this run?"

Suggested logical name:

```text
run_evidence_index
```

Fields overlap with Run Manifest but are query-optimized:

| Field | Class | Meaning |
|---|---|---|
| `run_id` | runtime-safe metadata | Run identity. |
| `evidence_dates` | offline-only indexing | Dates touched by run. |
| `source_file_refs` | offline-only indexing | File manifest IDs. |
| `trade_journal_refs` | offline-only indexing | Trade files for run. |
| `decision_log_refs` | offline-only indexing | Decision files for run. |
| `execution_log_refs` | offline-only indexing | Execution files for run. |
| `path_truth_refs` | offline-only indexing | Path truth files for run. |
| `system_health_refs` | offline-only indexing | Health files for run. |
| `status` | offline-only indexing | `ACTIVE`, `COMPLETED`, `STALE`, etc. |
| `quality_flags` | cognition-layer metadata | Parse errors, missing keys, stale process caveats. |

## 3. Run Lineage Index

Purpose: map producer-to-producer continuity.

Suggested logical name:

```text
run_lineage_index
```

Primary spine:

```text
(run_id, paper_trade_replay_key)
```

Secondary/future keys:

```text
trade_id
candidate_id
decision_id
candidate_trace_id
quote_lineage_id
order_id
condition_id
token_id
```

Fields:

| Field | Class | Meaning |
|---|---|---|
| `run_id` | runtime-safe metadata | Run identity. |
| `paper_trade_replay_key` | runtime-safe metadata | Direct replay/trade/path key when populated. |
| `trade_id` | runtime-safe metadata | Trade identity if present. |
| `candidate_id` | runtime-safe metadata | Future candidate identity. |
| `decision_id` | runtime-safe metadata | Future decision identity. |
| `asset` | runtime-safe metadata | BTC/ETH. |
| `side` | runtime-safe metadata | YES/NO. |
| `lifecycle_phase` | runtime-safe metadata | OPENING/ACTIVE/etc. |
| `trade_open_ref` | offline-only indexing | Source row pointer. |
| `trade_close_ref` | offline-only indexing | Source row pointer. |
| `decision_refs` | offline-only indexing | Candidate/decision row pointers. |
| `execution_refs` | offline-only indexing | Submit/fill/cancel row pointers. |
| `path_truth_refs` | offline-only indexing | Checkpoint row pointers. |
| `join_confidence` | offline-only indexing | `DIRECT`, `STRONG`, `WEAK`, `PROXY`, `BLOCKED`. |
| `join_failure_reason` | cognition-layer metadata | Missing replay key, null metadata, duplicate key, schema mismatch, etc. |
| `truth_ceiling` | cognition-layer metadata | Highest claim supported: signal/path/executable/etc. |

Join confidence rules:

| Confidence | Definition |
|---|---|
| `DIRECT` | Joined by exact canonical key, preferably `(run_id, paper_trade_replay_key)`. |
| `STRONG` | Joined by stable explicit ID with limited ambiguity. |
| `WEAK` | Joined by partial explicit fields and tight timestamps. |
| `PROXY` | Joined by inferred/timestamp/asset/side proximity only. |
| `BLOCKED` | Missing or contradictory identity. |

## 4. Path Truth Index

Purpose: make checkpoint coverage and direct join health visible without scanning path truth JSONL.

Suggested logical name:

```text
path_truth_index
```

Fields:

| Field | Class | Meaning |
|---|---|---|
| `evidence_date` | runtime-safe metadata | UTC date. |
| `run_id` | runtime-safe metadata | Run identity. |
| `paper_trade_replay_key` | runtime-safe metadata | Direct trade/path key. |
| `trade_id` | runtime-safe metadata | If present. |
| `asset` | runtime-safe metadata | BTC/ETH. |
| `side` | runtime-safe metadata | YES/NO. |
| `lifecycle_phase_at_open` | runtime-safe metadata | Opening phase. |
| `checkpoint_count` | offline-only indexing | Count of checkpoint rows. |
| `has_15s` | offline-only indexing | Checkpoint coverage. |
| `has_30s` | offline-only indexing | Checkpoint coverage. |
| `has_45s` | offline-only indexing | Checkpoint coverage. |
| `has_60s` | offline-only indexing | Checkpoint coverage. |
| `has_event_end` | offline-only indexing | Terminal checkpoint. |
| `full_coverage` | offline-only indexing | Complete checkpoint path. |
| `fast_close` | offline-only indexing | Closed before full path coverage. |
| `hold_seconds` | offline-only indexing | Trade duration. |
| `path_join_status` | offline-only indexing | Direct/legacy/null/blocked. |
| `legacy_null_row` | archive-only fields | Historical row missing replay key. |
| `coverage_gate_state` | cognition-layer metadata | Early/implementation gate impact. |

Current lineage rule:

- Post-wiring rows should prefer `(run_id, paper_trade_replay_key)`.
- Legacy rows with null replay key must remain valid historical rows but should not be silently counted as direct joins.
- Candidate/decision IDs are future enhancements, not required for the first path truth index.

## 5. Session Edge Index

Purpose: track research candidates like 02h hostility, 09h10h edge, BTC weakness, NO weakness, and fast-close behavior.

Suggested logical name:

```text
session_edge_index
```

Fields:

| Field | Class | Meaning |
|---|---|---|
| `evidence_date` | runtime-safe metadata | UTC date. |
| `session_hour_utc` | runtime-safe metadata | Hour/session bucket. |
| `asset` | runtime-safe metadata | BTC/ETH/all. |
| `side` | runtime-safe metadata | YES/NO/all. |
| `lifecycle_phase` | runtime-safe metadata | OPENING/ACTIVE/all. |
| `price_bucket` | runtime-safe metadata | If available. |
| `regime` | runtime-safe metadata | If available. |
| `trade_count` | offline-only indexing | Sample size. |
| `tp_count` | offline-only indexing | TP outcomes. |
| `sl_count` | offline-only indexing | SL outcomes. |
| `win_rate` | offline-only indexing | Signal outcome metric. |
| `median_hold_seconds` | offline-only indexing | Hold profile. |
| `fast_close_rate` | offline-only indexing | Fast-close share. |
| `path_direct_join_rate` | offline-only indexing | Join reliability. |
| `coverage_dates` | offline-only indexing | Distinct dates represented. |
| `candidate_label` | cognition-layer metadata | `02h_HOSTILE`, `BTC_HOSTILE`, etc. |
| `review_status` | cognition-layer metadata | `SUPPORTED`, `WEAKENED`, `ADVERSE`, `INSUFFICIENT`. |
| `policy_authority` | cognition-layer metadata | Always `NONE` until explicit implementation phase. |

This index supports research review only. It must not become a session filter, side filter, or risk rule.

## 6. Executable Truth Index

Purpose: keep executable blockers visible without claiming executable PnL.

Suggested logical name:

```text
executable_truth_index
```

Fields:

| Field | Class | Meaning |
|---|---|---|
| `run_id` | runtime-safe metadata | Run identity. |
| `paper_trade_replay_key` | runtime-safe metadata | Direct join key. |
| `asset` | runtime-safe metadata | BTC/ETH. |
| `side` | runtime-safe metadata | YES/NO. |
| `entry_price` | runtime-safe metadata | Signal/paper entry price. |
| `exit_price` | runtime-safe metadata | Signal/paper exit price. |
| `shares` | runtime-safe metadata | Paper shares/size if present. |
| `pnl_usdc` | runtime-safe metadata | Signal/paper PnL, not executable PnL. |
| `mos_assumption` | offline-only indexing | 1/3/5 share scenario, if evaluated. |
| `dynamic_min_cost` | offline-only indexing | Entry price times MOS assumption. |
| `dust_zone` | offline-only indexing | Derived blocker status. |
| `executable_minimum_met` | offline-only indexing | Derived under assumption, not approved truth. |
| `fill_truth_available` | offline-only indexing | Whether fill truth fields exist. |
| `cancel_truth_available` | offline-only indexing | Whether cancel truth fields exist. |
| `partial_fill_truth_available` | offline-only indexing | Whether partial-fill truth exists. |
| `quote_truth_available` | offline-only indexing | Whether quote age/staleness fields are joinable. |
| `executable_classification` | cognition-layer metadata | `SIGNAL_ONLY`, `DUST_ZONE`, `EXECUTABLE_CANDIDATE`, `BLOCKED_N_A`, etc. |
| `executable_pnl_status` | cognition-layer metadata | Expected to remain `BLOCKED` until unlocks exist. |
| `hermes_ingest_status` | cognition-layer metadata | `BLOCKER_EVIDENCE`, `UNLOCK_EVIDENCE`, `EXECUTABLE_EVIDENCE`, etc. |

Hard rule:

```text
executable_pnl = null / N_A / BLOCKED
until MOS authority, non-dust size, fill truth, cancel truth, and partial-fill truth are all available.
```

## 7. Archive Manifest Strategy

Archive manifests are stricter than query manifests because they preserve evidence integrity.

Suggested archive manifest:

```text
archive/evidence/runtime_quant_data/YYYY-MM-DD/MANIFEST.md
```

Archive manifest fields:

| Field | Required | Meaning |
|---|---:|---|
| `archive_manifest_version` | yes | Archive schema version. |
| `operator_approval_ref` | yes | Required before destructive cleanup. |
| `archive_date` | yes | When archive was created. |
| `evidence_date` | yes | UTC date archived. |
| `source_paths` | yes | Raw paths included. |
| `archive_paths` | yes | Archive output paths. |
| `source_bytes` | yes | Total source bytes. |
| `archive_bytes` | yes | Total archive bytes. |
| `source_line_counts` | yes | Counts by source. |
| `parse_error_counts` | yes | Parse errors by source. |
| `sha256_before` | yes | Source hash before archive. |
| `sha256_after_restore_check` | yes | Hash after restore/check. |
| `run_ids_present` | yes | Runs included. |
| `active_runtime_checked` | yes | Evidence was not active. |
| `research_locks_checked` | yes | No open task locks the source. |
| `raw_jsonl_deleted` | yes | Should be `No` unless separate approval exists. |
| `notes` | optional | Human caveats. |

Archive readiness:

| Class | Meaning | Action |
|---|---|---|
| `ACTIVE_DO_NOT_ARCHIVE` | Active current date or running validation. | Keep hot. |
| `RECENT_KEEP_HOT` | Latest completed date or open audit input. | Keep uncompressed. |
| `LOCKED_BY_RESEARCH` | Cited by active blocker/review. | Keep until closed. |
| `READY_TO_ARCHIVE` | Completed, summarized, and not active. | Archive candidate. |
| `ARCHIVED_VERIFIED` | Archive exists and restore/hash check passed. | Can be cold source. |
| `UNKNOWN` | Insufficient metadata. | Inspect before action. |

Delete policy:

- Delete is never implied by archive.
- Delete requires explicit operator approval and separate task.
- Tests, docs, config, and active runtime evidence are never deletion candidates in this design.

## 8. Query Topology

Recommended query topology:

```text
Agent question
-> docs/research/INDEX.md
-> evidence manifests
-> domain index
-> source row pointers
-> raw JSONL only if needed
```

Query examples:

| Question | First index | Drilldown |
|---|---|---|
| What dates have path truth coverage? | `daily_evidence_index` | `path_truth_index` |
| Where is evidence for this run? | `run_evidence_index` | file manifest refs |
| Can path truth join to trades? | `path_truth_index` | `run_lineage_index` |
| Is 02h still hostile? | `session_edge_index` | relevant trade/path rows |
| Is executable PnL unblocked? | `executable_truth_index` | fill/cancel/MOS fields |
| Which source files are safe to archive? | file manifest | archive manifest candidate |
| Did schema drift? | schema manifest | source file refs |

Future DuckDB view candidates:

```text
v_daily_evidence_summary
v_run_evidence_summary
v_trade_path_join_quality
v_session_edge_candidates
v_executable_truth_blockers
v_schema_drift
v_archive_readiness
```

## 9. JSONL To Manifest To Offline Query Flow

The safe flow:

```text
Runtime writes JSONL
  |
  v
Completed evidence window detected
  |
  v
Offline manifest generator reads file metadata and JSONL rows
  |
  v
File/run/schema manifests emitted
  |
  v
Domain index builders read manifests + selected JSONL rows
  |
  v
Indexes summarize path/session/executable/runtime health
  |
  v
Agents and dashboards query indexes first
  |
  v
Raw JSONL opened only for targeted verification
```

Rules:

- Active runtime files may be inventoried carefully but not archived or compacted.
- Completed files are preferred for full parse, checksum, and future Parquet conversion.
- Manifest generation must be repeatable and idempotent.
- Derived indexes are disposable and rebuildable.
- Raw JSONL remains the audit source of truth.
- Missing fields are recorded as missing; they are never defaulted into false certainty.

## 10. Future Parquet Conversion Boundaries

Parquet conversion should start only after manifest validation exists.

Allowed future boundaries:

| Boundary | Allowed? | Reason |
|---|---|---|
| Completed UTC date | Yes | Stable source window. |
| Source-specific partition | Yes | Preserves schema and source ownership. |
| Active current date | No | File may still be written. |
| Mixed source mega-table | Not first | Schema drift and semantics become muddy. |
| Historical rewrite | No | Raw JSONL must remain immutable. |
| Runtime Parquet writer | No | Too heavy for runtime loop. |

Recommended partition layout:

```text
runtime/derived/parquet/
  source=trade_journal/date=YYYY-MM-DD/*.parquet
  source=decision_log/date=YYYY-MM-DD/*.parquet
  source=execution_log/date=YYYY-MM-DD/*.parquet
  source=path_truth/date=YYYY-MM-DD/*.parquet
  source=system_health/date=YYYY-MM-DD/*.parquet
```

Parquet conversion acceptance checks:

- Source file exists.
- Source file is not active.
- Manifest line count matches converted row count.
- Parse error handling is explicit.
- `run_id` coverage is preserved.
- `paper_trade_replay_key` null/direct coverage is preserved.
- Schema fingerprint is recorded.
- Raw JSONL hash is recorded.
- Parquet output is marked derived and rebuildable.

## Metadata Classification

### Runtime-Safe Metadata

These fields may be emitted by runtime or appear in raw JSONL, but indexes should only read them:

- `timestamp`
- `event_type`
- `run_id`
- `paper_trade_replay_key`
- `trade_id`
- `asset`
- `side`
- `lifecycle_phase`
- `session_hour_utc`
- `market_slug`
- `condition_id`
- `token_id`
- `entry_price`
- `exit_price`
- `shares`
- `pnl_usdc`
- `trade_result`
- `exit_reason`
- `quote_age_ms` / `quote_stale_ms` when present
- `confidence`
- `model_output_ready`

Runtime-safe does not mean runtime should query it historically. It means the field can exist in runtime output without adding heavy runtime work.

### Offline-Only Indexing

Generated after the fact:

- line counts;
- parse error counts;
- file sizes;
- checksums;
- schema fingerprints;
- distinct run ID lists;
- event type lists;
- join rates;
- coverage rates;
- TP/SL distributions;
- fast-close buckets;
- path checkpoint counts;
- MOS scenario calculations;
- executable blocker summaries;
- session-edge aggregates;
- schema drift summaries.

### Archive-Only Fields

Used for evidence custody:

- archive class;
- source/archive paths;
- archive bytes;
- hash before/after;
- restore-check status;
- operator approval reference;
- archive created timestamp;
- deletion approval status;
- research lock status.

### Cognition-Layer Metadata

Used by docs, Hermes, operators, and agents:

- truth status;
- gate status;
- review verdict;
- candidate label;
- blocker label;
- unlock condition;
- Hermes ingest class;
- research doc references;
- active contradiction status;
- policy authority label;
- caveats and human notes.

These fields should not become trading inputs.

## What Should Never Run Inside Runtime Loop

Never run inside the runtime decision/execution loop:

- manifest generation over historical files;
- DuckDB queries;
- Polars scans;
- PyArrow/Parquet conversion;
- archive compression;
- SHA256 hashing of large files;
- directory-wide scans of `runtime/quant_data`;
- dashboard aggregate queries;
- historical lineage joins;
- session-edge candidate recomputation;
- executable truth ledger recomputation;
- cleanup/archive readiness checks;
- Hermes cognition updates;
- Redis-dependent trade approval.

Runtime may emit compact metadata needed by future indexes, but it should never build those indexes in the hot path.

## What Can Be Generated Asynchronously

Asynchronous/offline candidates:

| Artifact | Trigger | File window |
|---|---|---|
| file manifest | scheduled or manual | active files read-light, completed files full |
| run manifest | after run close or periodic | run-scoped |
| daily index | after UTC day close | completed date |
| path truth index | after new path truth rows or day close | run/date |
| session edge index | after enough closes or day close | completed/partial date |
| executable truth index | after closes and required fields exist | run/date |
| schema manifest | after source file update or day close | source/date |
| archive manifest | before archive action | completed date only |
| Parquet conversion | after manifest validation | completed date only |
| DuckDB index | after manifest/index refresh | derived offline |

If generated while runtime is active, the generator must treat active files as read-only and non-archivable.

## Agent Discovery Workflow

Future agents should use this order:

1. Read `runtime/research_state/latest_research_state.md` for compact state.
2. Read `docs/research/INDEX.md` for active blockers and domain docs.
3. Read the relevant domain doc.
4. Query or inspect the evidence manifest/index for date/run/source location.
5. Open raw JSONL only for targeted row verification.
6. Record whether evidence is raw, derived, proxy, or cognition-layer.

Discovery examples:

```text
Need latest clean run?
-> run_evidence_index sorted by started_at/status/quality_flags

Need path truth join status?
-> path_truth_index where path_join_status != DIRECT

Need 02h sample size?
-> session_edge_index where session_hour_utc = 02

Need executable blockers?
-> executable_truth_index where executable_pnl_status = BLOCKED

Need archive candidates?
-> daily_evidence_index where archive_class = READY_TO_ARCHIVE
```

This avoids full raw-data scans during routine research.

## Avoiding Repeated 10GB Scans

Controls:

- Store file-level manifests with bytes, line counts, run IDs, event types, and schema fingerprints.
- Store domain indexes for common questions.
- Track `generated_at` and source `sha256` so stale indexes are obvious.
- Prefer source/date partitions over repo-wide scans.
- Use row pointers or source references to locate only the needed JSONL lines.
- Keep active and completed windows separate.
- Make derived DuckDB/Parquet disposable but manifest-validated.
- Keep docs/research indexes as navigation, not data dumps.

Minimum useful index set:

```text
evidence_file_manifest
evidence_run_manifest
daily_evidence_index
run_lineage_index
path_truth_index
session_edge_index
executable_truth_index
schema_manifest
```

## Future Folder Topology

Design target, not implementation:

```text
runtime/
  quant_data/                         # canonical raw JSONL
  derived/
    manifests/
      file_manifest/
      run_manifest/
      schema_manifest/
    indexes/
      daily/
      run_lineage/
      path_truth/
      session_edge/
      executable_truth/
    parquet/
    duckdb/

archive/
  evidence/
    runtime_quant_data/
    logs/
    runtime_outputs/

docs/
  research/
    performance/
      evidence_manifest_index_design.md
```

Generated runtime-derived indexes should be treated as local/generated artifacts unless a later evidence-pack workflow explicitly scopes source control.

## Validation Requirements Before Implementation

Before future implementation, require:

- manifest payload shape tests;
- parse-error fixture tests;
- active-file fail-soft tests;
- checksum/line-count tests on small fixtures;
- schema drift tests;
- direct/proxy join classification tests;
- legacy null replay-key tests;
- no-runtime-import tests for DuckDB/Polars/PyArrow paths;
- Windows path handling tests;
- completed-date-only archive guard tests;
- raw JSONL unchanged assertion.

Docs-only design does not require tests.

## Future Options

### Option 1 - Safe EV Preservation

Create only manifest/index specs and future validation criteria. Keep raw evidence and runtime untouched.

Best now.

### Option 2 - Aggressive Information Discovery

Later, build a read-only manifest prototype for one completed date and one run, then compare counts against hand inspection.

Useful next, but only after a separate implementation task.

### Option 3 - Structural / Root-Cause Path

Later, introduce a full offline evidence warehouse with Parquet partitions, DuckDB views, and dashboard queries.

Powerful, but premature before manifests prove custody and schema drift handling.

Recommended path: Option 1 now, Option 2 next, Option 3 after validation.

## What Not To Do

- Do not implement this design in this task.
- Do not add DuckDB, Polars, PyArrow, Parquet, Redis, or new runtime libraries.
- Do not modify runtime code.
- Do not run paper or replay.
- Do not archive, move, compress, or delete evidence.
- Do not scan raw evidence broadly during routine agent work.
- Do not derive executable PnL from indexes.
- Do not promote S3, Growth Mode, or live readiness.
- Do not turn session-edge or executable-truth indexes into runtime policy.

## Completion Status

This document is a design only.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Library installs: No

Replay run: No
