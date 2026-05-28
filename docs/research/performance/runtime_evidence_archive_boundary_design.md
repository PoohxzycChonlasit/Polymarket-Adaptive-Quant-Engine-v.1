# Runtime Evidence Archive Boundary Design

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Mode: docs-only design. No implementation, no runtime mutation, no deletes, no compression execution, no library installs, no replay, no strategy/risk/execution/live changes.

## Executive Verdict

Runtime evidence should move through four custody states:

```text
HOT runtime evidence
-> WARM queryable evidence
-> COLD archived evidence
-> RESTORED / REHYDRATED evidence when needed
```

The boundary rule is simple:

```text
The runtime loop owns active append-only JSONL.
Offline archive jobs own completed evidence windows.
Research agents search manifests/indexes first.
Raw JSONL remains canonical forever unless a separate operator-approved deletion task exists.
```

Archive is a storage-control action, not a truth upgrade. Moving evidence offline must never weaken lineage, hide unresolved blockers, or imply executable PnL, Growth readiness, or live readiness.

## Design Goals

| Goal | Meaning |
|---|---|
| Prevent runtime storage explosion | Define when evidence can move out of hot storage. |
| Preserve lineage | Keep `run_id`, `paper_trade_replay_key`, source path, hashes, row counts, and research references intact. |
| Keep runtime safe | No archive/compression/index work in the runtime loop. |
| Keep research fast | Agents search compact manifests/indexes before raw files. |
| Preserve raw truth | JSONL is never rewritten into a different truth source. |
| Support future Parquet/DuckDB | Derived columnar data is allowed only after manifest validation. |
| Require operator review | Destructive cleanup and active evidence movement require approval. |

## Non-Goals

- No code implementation.
- No archive execution.
- No compression execution.
- No file moves.
- No deletes.
- No runtime data mutation.
- No dependency install.
- No replay run.
- No strategy/risk/execution/live change.

## 1. Hot / Warm / Cold Evidence Tiers

### HOT Tier

Definition: evidence needed for active runtime, latest validation, or immediate operator inspection.

Must stay instantly queryable:

| Evidence | Why |
|---|---|
| Current active UTC date under `runtime/quant_data/` | Runtime may still be appending. |
| Current active runtime log | Needed for health, traceback, write, Telegram, and process status. |
| Latest completed UTC date | Needed for morning audits and quick validation. |
| Latest completed run with open validation tasks | Needed for direct row inspection. |
| Recent path truth replay-key validation files | Active lineage review. |
| Current research index/governance docs | Navigation and blocker state. |

HOT rules:

- Do not compress.
- Do not move.
- Do not rewrite.
- Do not merge/split JSONL.
- Do not compute heavy hashes inside runtime.
- Read only with care if runtime is active.

### WARM Tier

Definition: completed evidence that is no longer active but still likely to be queried during open research.

Typical contents:

- prior completed dates referenced by active audits;
- evidence for unresolved Path Truth, Session Edge, Runtime Health, or Executable Truth blockers;
- completed runs used for comparison/control samples;
- source files with active research references;
- raw JSONL plus optional manifest/index summaries.

WARM rules:

- Raw JSONL remains in place or in a nearby verified evidence area.
- Manifest and index generation is allowed asynchronously.
- Parquet conversion may be proposed but not required.
- Compression is allowed only if restore rules and operator review are satisfied.
- If compressed, a manifest must preserve enough metadata to find and restore it quickly.

### COLD Tier

Definition: completed evidence that has been summarized, manifest-verified, not referenced by active tasks, and safe to move into archive custody.

Typical contents:

- older completed dates;
- old runtime logs with no open incident;
- old validation stdout/stderr outputs;
- prior evidence bundles after summaries exist;
- low-value runtime noise after manifest and review.

COLD rules:

- Archive by UTC evidence date.
- Preserve original filenames inside archive bundle or manifest.
- Store checksums and line counts before and after archive validation.
- Keep raw JSONL recoverable.
- Derived Parquet/DuckDB indexes are rebuildable and secondary.
- Deletion remains separate and approval-required.

### RESTORED / REHYDRATED Tier

Definition: archived evidence temporarily returned to queryable form for audit, replay, comparison, or incident review.

RESTORED rules:

- Restore into a dedicated rehydration area, not over active runtime paths.
- Verify hash and line counts before use.
- Mark restore time, restore path, source archive, and operator/task reason.
- Treat restored copies as read-only.
- Remove restored copies only by separate cleanup approval if they consume significant disk.

## 2. Runtime Retention Windows

Recommended retention windows are policy targets, not implementation.

| Evidence class | HOT retention | WARM retention | COLD candidate |
|---|---:|---:|---|
| Active `runtime/quant_data` JSONL | current UTC date | latest completed date plus active task dates | older completed dates after manifest |
| `trade_journal` | current + latest completed | all dates tied to open path/executable reviews | after summary and lineage manifest |
| `path_truth` | current + latest completed | all gate/control dates | after gate summary and join manifest |
| `decision_log` | current + latest completed | no-trade/rejection/control dates | after blocker summary |
| `execution_log` | current + latest completed | latency/fill/executable review dates | after execution summary |
| `system_health` | current + latest completed | incident/runtime-health dates | after incident closure |
| `market_snapshots` | current + latest completed | quote/execution truth dates | after quote summary |
| runtime logs | active log + current day | prior two completed days or incident logs | older logs after incident summary |
| runtime root outputs | none by default | until matching research summary exists | after manifest and approval |
| generated reports | latest active references | open research lineage | archive when superseded |

Hard retention floor:

- Keep current active date hot.
- Keep latest completed date hot.
- Keep any date locked by an open validation, blocker, gate, or contradiction review warm.

## 3. Archive Thresholds

Archive threshold should combine age, size, activity, and research locks.

### Date-Based Thresholds

| Condition | Archive status |
|---|---|
| Current UTC evidence date | `ACTIVE_DO_NOT_ARCHIVE` |
| Latest completed UTC date | `RECENT_KEEP_HOT` |
| Date referenced by open research task | `LOCKED_BY_RESEARCH` |
| Completed date older than latest completed date, no open locks | `READY_TO_ARCHIVE_REVIEW` |
| Completed date with verified manifest and restore path | `ARCHIVE_SAFE` |

### Size-Based Thresholds

Use these as review triggers, not automatic actions:

| Trigger | Suggested action |
|---|---|
| `runtime/quant_data` exceeds local comfort budget | Generate inventory/manifest before any move. |
| logs approach 1 GB | Review current active log and old logs for archive candidates. |
| one source/date JSONL becomes unusually large | Mark for schema/noise audit before archive. |
| repeated low-value noisy health/log records dominate size | Summarize and classify; do not delete without approval. |

### Quality-Based Thresholds

Do not archive as cold if:

- parse errors are unexplained;
- line counts are unknown;
- source hash is missing;
- run IDs are unknown;
- `paper_trade_replay_key` coverage is under active validation;
- the date is part of a pending gate review;
- a run is suspected stale/dirty and not summarized;
- a runtime incident is unresolved.

## 4. Compression Boundaries

Compression should happen only after manifest validation.

Allowed compression candidates:

- completed date bundles;
- old runtime logs after incident summary;
- old runtime root output logs after research summary;
- raw JSONL copies in archive custody;
- restored evidence after re-archive approval.

Not allowed:

- active UTC date;
- current active log;
- latest completed validation run while under review;
- files currently opened by runtime;
- files without manifest row counts and hashes;
- docs/research governance files;
- tests;
- config;
- code.

Compression format is a future implementation decision. The design allows `.zst` for JSONL and `.zip` for log bundles, matching prior cleanup policy examples, but does not require a library now.

Compression manifest must include:

- source path;
- archive path;
- source bytes;
- compressed bytes;
- source line count;
- parse error count;
- source SHA256;
- archive SHA256 or restore-check SHA256;
- run IDs;
- evidence date;
- research locks checked;
- operator approval reference if destructive cleanup follows.

## 5. Parquet Conversion Candidates

Parquet is a derived query format, not a source of truth.

Best first candidates:

| Source | Candidate status | Reason |
|---|---|---|
| `trade_journal` | high | Smaller, central to run/trade outcomes and replay keys. |
| `path_truth` | high | Useful for checkpoint coverage and direct join queries. |
| `execution_log` | medium | Important for future execution truth, schema may drift. |
| `decision_log` | medium | Useful but potentially high volume and schema-rich. |
| `system_health` | medium | Good for incident summaries, but not quant outcome truth. |
| `research_log` | medium | Useful for regime fields if schema is stable. |
| `market_snapshots` | later | Potentially large; needs careful sampling/partitioning. |
| raw runtime logs | no | Keep as compressed text/log archive, not Parquet-first. |

Parquet boundaries:

- completed date only;
- source-specific partition only;
- manifest row count must match converted row count;
- null coverage must be preserved;
- legacy/null replay-key rows must remain explicit;
- source hash and schema fingerprint must be recorded;
- Parquet files are rebuildable and can be discarded.

Suggested future partitioning:

```text
runtime/derived/parquet/
  source=trade_journal/date=YYYY-MM-DD/*.parquet
  source=path_truth/date=YYYY-MM-DD/*.parquet
  source=execution_log/date=YYYY-MM-DD/*.parquet
  source=decision_log/date=YYYY-MM-DD/*.parquet
  source=system_health/date=YYYY-MM-DD/*.parquet
```

Do not write Parquet from the runtime loop.

## 6. JSONL Preservation Policy

Raw JSONL is canonical.

Preservation rules:

1. Do not rewrite historical JSONL.
2. Do not merge JSONL files during first archive pass.
3. Do not split JSONL files during first archive pass.
4. Do not infer missing fields into historical rows.
5. Do not replace JSONL with Parquet.
6. Do not remove legacy/null rows from historical evidence.
7. Preserve original filenames and source paths in manifests.
8. Preserve line counts, parse errors, hashes, and run IDs.
9. Preserve source-specific semantics: trade, decision, execution, path, health, market snapshots.
10. Keep derived data marked as derived.

JSONL can move into archive custody only after:

- it is no longer active;
- a manifest exists;
- row counts and parse status are known;
- lineage status is recorded;
- open research locks are checked;
- operator review approves the move.

## 7. Archive Manifest Rules

Archive manifests are mandatory for any future archive action.

Suggested archive manifest path:

```text
archive/evidence/runtime_quant_data/YYYY-MM-DD/MANIFEST.md
```

Required fields:

| Field | Required | Notes |
|---|---:|---|
| `archive_manifest_version` | yes | Version the archive schema. |
| `evidence_date` | yes | UTC evidence date. |
| `archive_created_at` | yes | When archive was created. |
| `operator_approval_ref` | yes | Required for moves/compression; separate ref for deletes. |
| `source_paths` | yes | Original evidence paths. |
| `archive_paths` | yes | Archive destinations. |
| `source_bytes` | yes | Total and per-source. |
| `archive_bytes` | yes | Total and per-source. |
| `source_line_counts` | yes | Per JSONL source. |
| `parse_error_counts` | yes | Per JSONL source. |
| `source_sha256` | yes | Per file. |
| `archive_sha256` | yes | Per archive artifact if applicable. |
| `restore_check_sha256` | yes | Required before deletion approval. |
| `run_ids_present` | yes | Distinct run IDs. |
| `event_types_present` | yes | Distinct event types by source. |
| `lineage_keys_present` | yes | Replay key/candidate/decision coverage. |
| `research_refs` | yes | Docs citing this date/run/source. |
| `archive_class_before` | yes | Original readiness state. |
| `archive_class_after` | yes | New custody state. |
| `raw_jsonl_deleted` | yes | Should normally be `No`. |
| `notes` | optional | Caveats and operator notes. |

Manifest must be human-readable and machine-readable in a future implementation. A Markdown wrapper with YAML or JSON block is acceptable later, but this design does not implement it.

## 8. Restore / Rehydration Rules

Restore is required when an archived evidence bundle becomes relevant to an audit, replay, incident, or contradiction review.

Restore workflow:

```text
archive manifest
-> select source/date/run
-> restore to rehydration path
-> verify checksum
-> verify line count
-> verify parse status
-> mark restored copy read-only
-> run targeted audit/query
-> record restore reference in new report
```

Suggested restore target:

```text
runtime/rehydrated/YYYY-MM-DD/<task_or_run_id>/
```

Rules:

- Never restore over active `runtime/quant_data`.
- Never mix restored rows into active runtime files.
- Do not treat restored derived Parquet as canonical unless raw JSONL hash/lineage is verified.
- Restore only the smallest date/source/run needed.
- Keep restored copies out of runtime consumers.
- Add a rehydration note to the audit that used them.

Restore manifest fields:

| Field | Meaning |
|---|---|
| `restore_created_at` | When restored. |
| `archive_manifest_ref` | Archive source. |
| `restore_path` | Where restored copy lives. |
| `requested_by_task` | Audit/task reason. |
| `source_sha256` | Expected hash. |
| `restore_sha256` | Restored hash. |
| `line_count_verified` | Yes/no. |
| `parse_status_verified` | Yes/no. |
| `read_only_expected` | Yes/no. |

## 9. Operator Review Rules

Operator review is required before:

- moving raw runtime evidence into archive custody;
- compressing raw JSONL if it will no longer remain hot;
- deleting any original evidence;
- archiving evidence referenced by open research;
- archiving latest completed validation runs;
- changing retention windows;
- adding Parquet/DuckDB as official evidence layers;
- marking a source as low-value enough to ignore.

Operator review packet should include:

- date/source/run scope;
- current size;
- line counts;
- parse errors;
- run IDs;
- path truth/replay-key coverage;
- research docs referencing the evidence;
- archive class;
- restore plan;
- deletion status, normally `No deletion`.

No silent cleanup.

## 10. Governance Constraints

Project constraints:

- Paper evidence is not executable evidence.
- Signal PnL is not executable PnL.
- Path truth continuity is not fill truth.
- Archive is not delete.
- Runtime loop must remain lightweight.
- Offline analyzers remain offline-only.
- Docs do not promote S3, Growth Mode, or live readiness.
- No strategy/risk/execution/live changes from archive work.
- Tests must never be deleted.
- Config and wallet/live files must not be touched.

Archive governance:

```text
ACTIVE_RUNTIME > RESEARCH_LOCK > MANIFEST_VALIDATION > OPERATOR_REVIEW > ARCHIVE
```

If any earlier gate fails, archive does not proceed.

## Evidence Classification

### Never Archive

Never archive or move casually:

- active UTC date evidence;
- current active runtime log;
- `.env` and config files;
- source code;
- tests;
- docs/research `INDEX.md` and active governance docs;
- current validation inputs;
- files with unknown active writer state;
- evidence without manifest or parse status.

### Archive-Safe

Archive-safe after manifest and review:

- completed dates older than latest completed date;
- source files not referenced by open research;
- completed logs with incident summaries;
- old runtime root output logs with matching research summaries;
- stale generated reports superseded by index docs;
- derived Parquet/DuckDB files that are rebuildable.

### Archive-Only

Evidence that should be preserved but rarely queried hot:

- raw old runtime logs;
- old stdout/stderr validation captures;
- superseded report artifacts;
- closed incident files;
- old generated reports whose conclusions are summarized in docs.

Archive-only does not mean delete.

### Replay-Critical

Keep hot or warm until replay lineage closes:

- `trade_journal`;
- `execution_log`;
- `decision_log`;
- `path_truth`;
- market snapshots tied to quote/fill truth;
- files containing clean run IDs used by validation;
- sources used for `(run_id, paper_trade_replay_key)` join proof.

Replay-critical files can become cold only after the replay/gate report cites the manifest and restore path.

### Cognition-Critical

Keep discoverable:

- `docs/research/INDEX.md`;
- active domain monitor docs;
- active blocker/frontier docs;
- current gate reviews;
- archive manifests;
- evidence manifest/index design docs;
- Hermes cognition notes if mirrored outside repo.

Cognition-critical docs are small and should not be compressed as runtime evidence.

### Low-Value Runtime Noise

Potential low-value evidence after summarization:

- repeated websocket deprecation warnings;
- repeated retry noise with no fatal impact;
- duplicate stdout lines already represented in system health;
- old logs with no traceback/fatal/write failure/Telegram failure;
- stale process logs after cleanup summary exists.

Even low-value noise should be summarized and archived before any deletion review.

## What Must Stay Instantly Queryable

The following should remain hot:

- latest active run ID and active log;
- current UTC `runtime/quant_data` date;
- latest completed UTC date;
- latest path truth validation rows;
- active Path Truth gate monitor;
- active executable truth blocker/frontier docs;
- active runtime health/no-trade/rejection audits;
- research root `INDEX.md`;
- manifest/index design docs;
- archive manifests for recently moved evidence.

Agents should be able to answer current health and latest evidence status without rehydrating archives.

## What Can Move Offline

Can move to warm/cold after review:

- older completed dates;
- older logs after incident summaries;
- old validation stdout/stderr;
- old generated reports summarized by docs;
- raw market snapshots for closed dates after quote/execution summaries;
- daily evidence not part of current gates or contradictions.

Move offline does not mean move out of the truth chain. It means the manifest becomes the first lookup surface and raw files are restorable.

## What Future Agents Should Search First

Search order:

1. `runtime/research_state/latest_research_state.md`
2. `docs/research/INDEX.md`
3. relevant domain monitor/frontier doc
4. future evidence manifest/index
5. archive manifest if evidence is cold
6. restored raw JSONL only if targeted verification is required

For archive questions:

```text
INDEX.md
-> runtime_evidence_archive_boundary_design.md
-> evidence_manifest_index_design.md
-> future file/run/daily manifests
-> archive MANIFEST.md
-> raw/restored JSONL
```

## Preventing Runtime Storage Explosion

Controls:

- Keep only current active date plus latest completed date hot by default.
- Mark all older dates with archive readiness classes.
- Generate manifests for completed dates before they accumulate.
- Summarize active research locks so old files can be released when reviews close.
- Compress old logs after incident summaries.
- Convert high-value completed JSONL sources to Parquet only as derived query copies.
- Keep DuckDB indexes disposable and rebuildable.
- Never let dashboards or agents repeatedly scan all raw JSONL.
- Make low-value noise visible as a count/summary, not repeated raw search.

Storage control must not weaken evidence custody.

## Preserving Lineage Integrity

Lineage preservation fields:

| Field | Required for |
|---|---|
| `run_id` | run lookup and cross-source joining |
| `paper_trade_replay_key` | direct trade/path joining |
| `source_path` | source custody |
| `source_line_number` or row pointer | targeted raw verification |
| `evidence_date` | partition and archive scope |
| `source_type` | schema ownership |
| `sha256` | restore integrity |
| `line_count` | row preservation |
| `parse_error_count` | quality caveat |
| `research_refs` | governance/cognition link |
| `archive_manifest_ref` | cold evidence restore path |

Legacy/null lineage rows must remain explicit. They should never be silently repaired, discarded, or counted as direct joins.

## Future Options

### Option 1 - Safe EV Preservation

Keep current files untouched. Adopt this design as archive boundary policy and require manifest/index design before any archive action.

Best now.

### Option 2 - Aggressive Information Discovery

Later, create a read-only archive-readiness manifest for one completed date and one log bundle. No moves or compression in the first pass.

Useful next implementation candidate.

### Option 3 - Structural / Root-Cause Path

Later, build full hot/warm/cold automation with Parquet conversion and DuckDB indexes. This should wait until manifests, restore checks, and operator approval workflow are proven.

Recommended path: Option 1 now, Option 2 next, Option 3 only after validation.

## What Not To Do

- Do not archive active runtime evidence.
- Do not compress current active files.
- Do not delete raw JSONL.
- Do not rewrite historical JSONL.
- Do not move files without a manifest and operator approval.
- Do not run Parquet conversion in runtime.
- Do not run DuckDB/Polars/PyArrow in runtime.
- Do not treat compressed evidence as lower-quality or higher-quality truth.
- Do not archive evidence locked by active research.
- Do not break `(run_id, paper_trade_replay_key)` lineage.
- Do not use archive work to change strategy, risk, execution, thresholds, wallet, or live config.

## Completion Status

This document is a boundary design only.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Files moved: No

Files deleted: No

Compression executed: No

Library installs: No
