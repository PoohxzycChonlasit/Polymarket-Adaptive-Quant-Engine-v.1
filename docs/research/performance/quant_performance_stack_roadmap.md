# Quant Performance Stack Roadmap

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Mode: docs-only roadmap. No implementation, no runtime mutation, no library installs, no replay, no strategy/risk/execution/live changes.

## Executive Verdict

The platform needs two separate performance stacks:

1. Runtime stack: small, bounded, fail-soft, and latency-aware. It should continue to prioritize paper/live separation, orderbook freshness, risk gates, and evidence durability over heavy analytics.
2. Research stack: columnar, queryable, and archive-aware. It should absorb the growing `runtime/quant_data` and `logs` volume through offline Parquet, DuckDB, and lineage indexes without becoming a runtime dependency.

Current recommendation:

| Area | Recommendation | Timing | Runtime authority |
|---|---|---|---|
| Archive policy | Adopt now as docs/process. | Now | None |
| Evidence manifest/index design | Adopt now as offline design. | Now | None |
| DuckDB | Offline-only query/index layer. | Next research phase | None |
| Parquet + PyArrow | Offline archival/derived format, raw JSONL retained. | After manifest design | None |
| Polars | Offline transform/audit engine. | After Parquet prototype | None |
| `orjson` | Defer until profiling proves JSON serialization is a bottleneck. | Later runtime micro-optimization | No policy authority |
| `cachetools` | Defer; possible bounded metadata cache only. | Later runtime micro-optimization | No policy authority |
| `asyncio.Queue` | Defer; possible telemetry decoupling only after tests. | Later runtime observability | No trade authority |
| WebSocket/HTTP optimization | Optimize deliberately around freshness, retry, backoff, and connection reuse. | Incremental | No strategy/risk change |
| Redis/event queue | Future infrastructure option for observability/event fanout only. | Later, optional | No decision authority |

The key rule is: runtime emits compact truth; offline systems query, compress, join, and summarize it.

## Current Constraints

Known context from governance and project rules:

- Runtime evidence volume is growing rapidly: `runtime/quant_data` is approximately 10.5 GB.
- Logs are approaching approximately 972 MB.
- Logging budget targets compressed logs and no unbounded runtime files.
- Current research posture is `PAPER / SIGNAL_MODE`, `PATH_TRUTH / EVIDENCE_FARMING`.
- Executable truth remains `NOT_REACHED`; executable PnL is blocked.
- Path Truth direct join lineage has been resolved for post-wiring rows, but that does not imply fill truth.
- The active runtime architecture is paper-safe, websocket-first, risk-first, and evidence-first.
- `requirements.txt` already includes `httpx` and `websockets`.
- `orjson`, `cachetools`, `duckdb`, `polars`, and `pyarrow` are not currently listed in `requirements.txt`.

This roadmap does not authorize adding those libraries. It defines where they belong if a future task explicitly approves implementation and tests.

## Design Principle

```text
Runtime loop:
  observe -> decide -> risk gate -> execute/simulate -> emit compact JSONL

Offline research:
  index -> validate -> join -> compact -> query -> audit -> report

Hard boundary:
  offline analytics never feed automatic trading decisions without a separate approved runtime-policy phase.
```

Runtime should never wait on DuckDB, Polars, Parquet compaction, archive scans, Redis availability, dashboard queries, or large historical joins.

## 1. What Should Be Adopted Now?

Adopt now as policy/design, not code:

| Item | Adopt now? | Why |
|---|---|---|
| Hot/warm/cold evidence archive policy | Yes | Data growth is already material, and archive rules reduce future cleanup risk. |
| Evidence manifests | Yes | Every archive/index action needs counts, bytes, checksums, run IDs, date ranges, and parse status. |
| Raw JSONL immutability rule | Yes | Historical evidence must remain source-of-truth and replayable. |
| Derived-data separation | Yes | Parquet/DuckDB outputs should be generated artifacts, not replacements for JSONL. |
| Query/index schema design | Yes | Lineage joins need stable fields before more data accumulates. |
| Runtime profiling plan | Yes | Runtime libraries should be added only after a measured bottleneck exists. |
| Docs/research performance topology | Yes | The new performance folder should track UI, evidence, and data-stack decisions. |

Adopt now operationally:

- Keep raw JSONL as the canonical truth format.
- Avoid scanning entire `runtime/quant_data` during normal agent tasks.
- Prefer compact state, manifests, and precomputed indexes for research navigation.
- Treat old generated reports/logs as archive candidates, not delete candidates.
- Keep active UTC date and latest completed validation date hot.

Do not adopt now:

- No new runtime serializers.
- No runtime DuckDB.
- No runtime Parquet writer.
- No runtime Polars.
- No Redis dependency.
- No queue refactor.
- No websocket rewrite.

## 2. What Should Remain Offline-Only?

| Technology / Pattern | Offline role | Reason |
|---|---|---|
| DuckDB | Query engine over JSONL/Parquet and generated evidence indexes. | Excellent for structured lineage queries, but should not become runtime dependency. |
| Polars | Batch transforms, lazy scans, grouped distributions, feature audits. | Fast analytics, but heavy for the trade loop and unnecessary for per-tick decisions. |
| PyArrow | Parquet schema, dataset writing, column typing, partition management. | Best for derived storage, not for active runtime emission. |
| Parquet | Derived archival/query format. | Compact and columnar, but raw JSONL remains canonical. |
| Evidence compaction | Convert completed dates into derived partitions. | Compaction can be slow and IO-heavy. |
| Lineage joins | `(run_id, paper_trade_replay_key)` and future candidate/decision joins. | Joins are research truth, not runtime policy. |
| Backfill/reindex jobs | Rebuild derived indexes from raw JSONL. | Must not touch current active runtime files. |
| Large dashboards | Research Cockpit, web dashboards, operator summaries. | Visibility only; no trading authority. |

Offline-only means a batch job or audit may fail without affecting trading, paper collection, or live safety.

## 3. What Should Never Enter The Runtime Loop?

Never put these inside the decision/execution loop:

- DuckDB queries over historical evidence.
- Polars scans or DataFrame joins.
- Parquet compaction or partition writes.
- Full filesystem scans of `runtime/quant_data` or `logs`.
- Archive compression.
- Checksum calculation for large files.
- Dashboard aggregate queries.
- Telegram digest aggregation over large history.
- Redis-dependent decision approval.
- Blocking HTTP enrichment that is not already part of market data acquisition.
- Any calculation that can block orderbook freshness, risk checks, stop/exit safety, or clean JSONL emission.

Allowed runtime behavior should remain narrow:

- compact event emission;
- bounded in-memory state required for current market/window;
- bounded metadata caches only when they cannot make stale data look fresh;
- non-critical telemetry drop policies only when explicitly tested;
- fail-soft observability that cannot block order intent or risk gates.

## 4. What Belongs In Replay / Audit Only?

Replay/audit-only work:

| Workstream | Belongs in replay/audit because |
|---|---|
| Executable truth ledger | It depends on MOS assumptions, dust classification, fill truth, cancel truth, and path joins. |
| Session edge classification | It is research-only until controls and implementation gates are separately approved. |
| Fast-close distributions | They diagnose behavior but do not authorize stop-loss or entry changes. |
| BTC/NO/02h/09h10h candidate reviews | They are hypotheses, not policy. |
| MFE/MAE truth | It needs path and outcome evidence before runtime usage. |
| Quote age distributions | Useful for execution realism, but not a policy input until approved. |
| Path Truth coverage gates | Evidence continuity, not trading authority. |
| Growth readiness | Blocked until executable truth is reached. |

Replay/audit outputs may produce recommendations, but the runtime should not consume them automatically.

## 5. Safe Migration Phases

### Phase 0 - Governance Freeze

Status: should happen now.

Actions:

- Keep this roadmap as the performance-stack source.
- Keep existing research folder governance intact.
- Define archive/index rules before moving or compressing generated evidence.
- Keep all runtime code unchanged.

Deliverables:

- `docs/research/performance/quant_performance_stack_roadmap.md`
- Future archive/index specs, if requested.

### Phase 1 - Evidence Manifest Design

Actions:

- Design a manifest format for each evidence date/source.
- Include source path, byte count, line count, parse error count, SHA256, run IDs, min/max timestamps, and referenced research docs.
- Define active/hot/warm/cold classifications.

Runtime impact: none.

### Phase 2 - Offline JSONL Inventory

Actions:

- Build a read-only inventory of JSONL sources by date, source type, run ID, line count, parse status, and size.
- Output a compact manifest/report.
- Do not rewrite JSONL.

Runtime impact: none.

### Phase 3 - Parquet Derived Dataset Prototype

Actions:

- Convert a small completed historical date to Parquet as a derived copy.
- Keep raw JSONL unchanged.
- Partition by date and source.
- Validate row counts, parse errors, schema drift, and run IDs against the manifest.

Runtime impact: none.

### Phase 4 - DuckDB Evidence Index

Actions:

- Generate an offline DuckDB index from raw JSONL or derived Parquet.
- Support structured lineage queries:
  - by date;
  - by source;
  - by run ID;
  - by `(run_id, paper_trade_replay_key)`;
  - later by candidate/decision identity if wired.
- Treat the database as disposable and rebuildable.

Runtime impact: none.

### Phase 5 - Audit/Replay Consumer Migration

Actions:

- Let offline audits optionally read Parquet/DuckDB indexes.
- Compare outputs against raw JSONL for a fixed validation sample.
- Keep JSONL readers as fallback.
- Mark any derived report with source manifest IDs.

Runtime impact: none.

### Phase 6 - Runtime Micro-Optimization Review

Actions only after profiling:

- Evaluate `orjson` behind a serializer adapter.
- Evaluate `cachetools` for bounded metadata caches.
- Evaluate `asyncio.Queue` for non-critical telemetry decoupling.
- Benchmark and test before adoption.

Runtime impact: observability/performance only, if separately approved.

### Phase 7 - Optional Event Queue / Redis Exploration

Actions:

- Evaluate Redis or another queue for operator-facing event fanout, dashboard streaming, or offline ingestion.
- Keep runtime able to operate if Redis is down.
- Never make Redis a required authority for trade decisions, risk approval, or exits.

Runtime impact: optional observability infrastructure only, if separately approved.

## 6. Windows vs Linux Considerations

### Windows

Risks:

- File locks from active processes and editors.
- Antivirus/Defender IO overhead on large JSONL and Parquet files.
- Long path issues.
- Case-insensitive path behavior.
- PowerShell path escaping around spaces and backslashes.
- Background process inventory can be noisy.
- Redis/service management is less native than Linux.

Recommendations:

- Use `pathlib` in future tools.
- Avoid case-only filename changes.
- Avoid symlink-based archive designs unless explicitly approved.
- Use atomic write-to-temp then rename for derived files.
- Keep active runtime files hot and uncompressed.
- Run Parquet/DuckDB jobs against completed dates only.

### Linux / VPS

Strengths:

- Better service supervision with `systemd`.
- Better long-running IO and cron behavior.
- More natural Redis deployment.
- Easier disk quota monitoring and log rotation.
- Better fit for 24/7 evidence farming.

Risks:

- Small VPS disk constraints.
- File descriptor limits for websocket/http clients.
- Permission and owner drift after deploys.
- Different path separators and line endings from Windows development.

Recommendations:

- Design all paths as portable relative paths from repo root.
- Keep derived data and archive output outside git-tracked docs.
- Set explicit retention budgets before moving to always-on Linux collection.
- Validate on Windows first for docs/research, then Linux for runtime/archive jobs.

## 7. Research vs Runtime Separation

| Concern | Runtime ownership | Research ownership |
|---|---|---|
| Raw JSONL emission | Yes | Reads only |
| Active market state | Yes | Summarizes after the fact |
| Orderbook freshness | Yes | Audits distributions |
| Risk gates | Yes | Reviews outcomes only |
| Paper/live separation | Yes | Documents evidence only |
| Path Truth checkpoints | Runtime emits | Research joins and validates |
| Executable truth | Runtime may emit future fields | Research proves or blocks claims |
| DuckDB/Parquet | No | Yes |
| Dashboards | Observability only | Main consumer |
| Archive manifests | No active-loop dependency | Yes |

Runtime should answer: "What happened now?"

Research should answer: "What did history prove, fail to prove, or block?"

## 8. Performance Risk Areas

### Runtime risks

- JSONL writers growing without retention/rotation.
- Full orderbook or snapshot spam.
- Blocking Telegram sends.
- Blocking HTTP calls in hot paths.
- Websocket reconnect loops creating noisy logs.
- Large dashboard/report reads from active runtime files.
- Expensive serialization inside tight loops.
- Unbounded in-memory caches.
- Unbounded queues hiding backpressure.
- Treating stale cached data as fresh market state.

### Research risks

- Repeated scans of 10 GB+ JSONL for every audit.
- Mixing raw source truth with derived Parquet without manifests.
- Schema drift across dates.
- Proxy joins mistaken for direct joins.
- Old rows with null identity mixed with post-wiring rows.
- Duplicate reports with stale conclusions.
- Path moves breaking lineage links.

### Infrastructure risks

- Disk growth outpacing cleanup.
- Logs and JSONL competing with active runtime disk.
- Compression/archive jobs touching active files.
- Derived indexes becoming stale but treated as truth.
- Redis/event queue deployment increasing operational surface area.

## 9. Data Growth Strategy

### Storage tiers

| Tier | Contents | Retention posture | Access pattern |
|---|---|---|---|
| Hot | Active UTC date plus latest completed date JSONL/logs. | Keep uncompressed. | Runtime, latest audits. |
| Warm | Recent completed dates with open research references. | Raw JSONL retained, optional derived Parquet. | Audits, validation. |
| Cold | Closed historical dates with manifests. | Compressed raw JSONL plus derived Parquet/index. | Historical research. |
| Disposable derived | DuckDB indexes, query caches, generated reports. | Rebuildable. | Fast research queries. |

### Source-of-truth rule

Raw JSONL remains canonical:

```text
raw JSONL -> manifest -> derived Parquet -> DuckDB/index -> report/dashboard
```

Never reverse the direction. Do not edit raw JSONL from derived outputs.

### Suggested partitioning

For derived Parquet:

```text
runtime/derived/parquet/
  source=trade_journal/date=YYYY-MM-DD/*.parquet
  source=decision_log/date=YYYY-MM-DD/*.parquet
  source=execution_log/date=YYYY-MM-DD/*.parquet
  source=path_truth/date=YYYY-MM-DD/*.parquet
  source=system_health/date=YYYY-MM-DD/*.parquet
```

Alternative if source-first is awkward:

```text
runtime/derived/parquet/
  date=YYYY-MM-DD/source=trade_journal/*.parquet
```

Choose one and keep it stable. Source-first is better for source-specific audits; date-first is better for daily bundles.

### Manifest minimum fields

| Field | Required |
|---|---|
| source_path | yes |
| derived_path | yes, if derived |
| evidence_date | yes |
| source_type | yes |
| bytes | yes |
| line_count | yes |
| parse_error_count | yes |
| sha256 | yes |
| run_ids | yes |
| min_ts | yes, if available |
| max_ts | yes, if available |
| schema_version | yes |
| generated_at | yes |
| generator_version | yes |
| active_file | yes/no |
| archive_class | yes |

## 10. Suggested Future Topology

```text
C:\quant\Polymarket-Adaptive-Quant-Engine-v.1\
  runtime\
    quant_data\                       # canonical raw JSONL, hot/warm only
      trade_journal\
      decision_log\
      execution_log\
      path_truth\
      system_health\
    derived\                          # generated, rebuildable, not source truth
      manifests\
      parquet\
      duckdb\
      reports\
  logs\                               # active/recent runtime logs
  archive\
    evidence\
      runtime_quant_data\
      logs\
      runtime_outputs\
  docs\
    research\
      INDEX.md
      performance\
        quant_performance_stack_roadmap.md
```

Future git policy should keep raw runtime evidence, derived Parquet, DuckDB files, and large archives out of normal source-control review unless a dedicated evidence-pack workflow is approved.

## Runtime Technology Evaluation

### `orjson`

Potential use:

- faster JSON serialization for compact JSONL events;
- lower CPU overhead if profiling shows `json.dumps` is material.

Do not adopt until:

- serialization is measured as a bottleneck;
- JSONL byte/string behavior is wrapped behind one adapter;
- datetime, decimals, NaN/null behavior are tested;
- output compatibility with current readers is proven;
- fail-soft logging behavior remains intact.

Risk:

- subtle payload changes can break replay/audit compatibility;
- bytes output can introduce inconsistent writer behavior;
- speed gains may be irrelevant compared with network/orderbook waits.

Recommendation: later runtime micro-optimization only.

### `cachetools`

Potential use:

- bounded TTL cache for stable metadata:
  - market slugs;
  - token IDs;
  - condition IDs;
  - static Gamma metadata;
  - display summaries.

Do not use for:

- orderbook freshness;
- quote age;
- risk approval;
- current price truth;
- position truth;
- fill/cancel truth.

Risk:

- stale cache entries can look like valid market state;
- unbounded caches can hide memory growth.

Recommendation: defer. If adopted, use maxsize + TTL + explicit stale labels.

### `asyncio.Queue`

Potential use:

- decouple non-critical telemetry or UI events from the main loop;
- bounded queue between producer and writer;
- controlled drop policy for low-priority diagnostics.

Do not use to hide:

- failed critical trade journals;
- path truth checkpoint loss;
- risk/execution state loss;
- unbounded backpressure.

Queue rules:

- bounded size;
- observable dropped-count;
- priority classes;
- synchronous fallback for critical records;
- clean shutdown drain with timeout.

Recommendation: future observability refactor only after tests.

### WebSocket / HTTP Optimizations

Already relevant:

- `httpx` and `websockets` are present.

Potential improvements:

- connection reuse where safe;
- clear retry/backoff policy;
- heartbeat and reconnect metrics;
- rate-limit-aware request budgeting;
- separation of websocket freshness from REST fallback;
- compact health events for reconnect and stale data.

Do not do:

- blind parallel REST polling;
- unbounded reconnect spam;
- replacing websocket-first design with high-frequency REST polling;
- treating stale websocket cache as executable truth.

Recommendation: incremental, measured, and scoped to market-data health.

## Research Technology Evaluation

### DuckDB

Best use:

- local structured lineage queries;
- joining JSONL/Parquet by run ID and replay key;
- daily evidence summaries;
- Research Cockpit backends;
- ad hoc audit queries.

Keep it:

- offline;
- rebuildable;
- versioned by manifest;
- optional for readers that can fall back to raw JSONL.

### Polars

Best use:

- fast batch transforms;
- grouped distributions;
- quote-age buckets;
- session/asset/side/lifecycle splits;
- schema normalization before Parquet.

Keep it:

- offline;
- used on completed files;
- guarded by manifest row-count validation.

### PyArrow

Best use:

- Parquet schema control;
- partitioned datasets;
- typed columns for timestamps, floats, booleans, and categorical fields;
- interoperability between Polars and DuckDB.

Keep it:

- offline;
- used for derived data only.

### Parquet

Best use:

- compressed historical evidence;
- faster audit scans;
- structured dashboard/report queries;
- stable daily/source partitions.

Never use it as:

- replacement for raw JSONL;
- active runtime write target;
- live decision input;
- sole source for historical truth.

## Infrastructure Evaluation

### Archive Strategy

Archive should be a controlled evidence lifecycle:

1. Identify completed date/source.
2. Verify not active and not locked by open research.
3. Generate manifest.
4. Validate line count and parse status.
5. Compress/copy raw source.
6. Generate derived Parquet if approved.
7. Verify checksums and row counts.
8. Mark archive class.
9. Keep deletion as approval-required and separate.

Archive is not delete.

### Evidence Indexing

Future index candidates:

| Index | Purpose | Runtime dependency |
|---|---|---|
| daily manifest index | Find dates, run IDs, source files, sizes. | None |
| run index | Locate all files for a run ID. | None |
| replay-key index | Join trade/path/execution rows. | None |
| schema drift index | Track field presence by source/date. | None |
| blocker index | Track MOS/dust/fill/cancel blockers. | None |

Index files should be disposable. The truth is raw JSONL plus manifests.

### Structured Lineage Queries

Required query spine:

```text
date
-> run_id
-> paper_trade_replay_key
-> trade_open / trade_close
-> path_truth checkpoints
-> execution events
-> decision context
-> research summaries
```

Future optional lineage:

```text
candidate_id
decision_id
candidate_trace_id
quote_lineage_id
order_id
condition_id
token_id
```

Do not require future optional keys before current direct path truth joins are stable.

### Redis / Event Queue Possibilities

Potential future use:

- operator console event fanout;
- dashboard live updates;
- queueing non-critical telemetry;
- separating runtime writer from dashboard readers;
- buffering offline ingestion events.

Not allowed:

- Redis as trade approval authority;
- Redis as risk state source;
- Redis as sole position truth;
- Redis outage causing unsafe runtime behavior;
- queue delay hiding stale data.

Recommendation: later infrastructure experiment only. Start with file-based JSONL and offline indexes.

## Library Adoption Matrix

| Library / System | Runtime loop | Runtime observability | Offline research | Replay/audit | Status |
|---|---|---|---|---|---|
| `json` stdlib | Allowed | Current default | Allowed | Allowed | Keep |
| `orjson` | Defer | Possible later | Optional | Optional | Benchmark first |
| `cachetools` | Very limited | Possible metadata cache | Unneeded | Unneeded | Defer |
| `asyncio.Queue` | Not for decisions | Possible writer decoupling | Unneeded | Unneeded | Defer |
| `httpx` | Already used | Health metrics only | Existing use | Existing use | Keep scoped |
| `websockets` | Already used | Health metrics only | Existing use | Existing use | Keep scoped |
| DuckDB | Never | Never | Strong fit | Strong fit | Offline-only future |
| Polars | Never | Never | Strong fit | Strong fit | Offline-only future |
| PyArrow | Never | Never | Strong fit | Strong fit | Offline-only future |
| Parquet | Never | Never | Strong fit | Strong fit | Derived-only future |
| Redis | Never as authority | Optional future | Optional future | Optional future | Later experiment |

## Future Option Rule

### Option 1 - Safe EV Preservation

Keep runtime unchanged. Add only docs, archive policy, manifests, and offline inventory specs. This protects evidence farming and avoids introducing new operational dependencies.

Best for: current state.

### Option 2 - Aggressive Information Discovery

Prototype offline DuckDB/Parquet against a small completed date. Validate row counts and joins against raw JSONL. Use it to accelerate audits without touching runtime.

Best for: next data-scale research step after this roadmap.

### Option 3 - Structural / Root-Cause Path

Design a full event pipeline with bounded queues, event bus, optional Redis, DuckDB-backed indexes, and dashboard ingestion. This may be useful later but is too heavy before archive/index fundamentals are stable.

Best for: future infrastructure phase after executable truth fields mature.

Recommended path: Option 1 now, Option 2 next, Option 3 only after evidence indexing and retention are proven.

## Performance Stack Unlock Chain

```text
1. Freeze archive/index policy.
2. Build read-only evidence manifests.
3. Validate raw JSONL inventory and schema drift.
4. Generate derived Parquet for completed dates only.
5. Build disposable DuckDB indexes.
6. Migrate replay/audit reads behind fallback-capable adapters.
7. Profile runtime JSONL/HTTP/websocket bottlenecks.
8. Only then consider runtime micro-optimizations.
9. Keep executable truth blocked until fill/cancel/partial-fill/MOS truth exists.
```

## What Not To Do

- Do not install libraries as part of this roadmap.
- Do not add DuckDB, Polars, PyArrow, or Parquet writes to runtime.
- Do not replace raw JSONL with derived files.
- Do not archive active runtime dates.
- Do not delete evidence after compression without explicit approval.
- Do not let dashboards read active files in a way that blocks runtime.
- Do not make Redis or any queue required for paper/live safety.
- Do not use performance work to change strategy, risk, sizing, execution, thresholds, or live config.
- Do not claim executable PnL from faster analytics.

## Completion Status

This document is a roadmap only.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Library installs: No

Replay run: No
