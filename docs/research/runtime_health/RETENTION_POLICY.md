# Retention Policy

type: reliability governance spec
created: 2026-06-06
status: DESIGN_ONLY
code_changed: No
strategy_changed: No
runtime_changed: No
live_changed: No

---

## Purpose

Define future retention tiers, disk growth expectations, and evidence protection
rules for long-duration paper operation.

This document is policy only. It does not implement deletion, compression,
rotation, archiving, or cleanup.

---

## Retention Principles

1. Trade and execution truth outrank storage savings.
2. Never delete raw evidence needed for active watchlists or verification.
3. Never delete data from an incident window until the incident is closed.
4. Prefer compression before deletion.
5. Prefer category-specific retention over whole-folder cleanup.
6. Keep run-scoped metadata long enough to reconstruct evidence lineage.
7. Do not apply retention to live-risk evidence without separate approval.

---

## Retention Tiers

| Tier | Categories | Proposed retention | Action after retention |
|---|---|---:|---|
| Tier 0: Permanent truth | `trade_journal`, `execution_log`, incident reports, verification snapshots | Indefinite | Compress only |
| Tier 1: Research-critical | `decision_log`, `risk_log`, `path_truth`, `orderbook_lineage` | 365 days | Compress, then archive |
| Tier 2: High-volume context | `market_snapshots`, `research_log`, realtime scan CSV | 90 days | Compress; archive if linked to active research |
| Tier 3: Health telemetry | `system_health`, runtime owner snapshots, bot status snapshots | 180 days | Compress |
| Tier 4: Derived reports | replay reports, data quality reports, paper evaluations | 365 days | Keep JSON summaries; compress bulky CSV |
| Tier 5: Debug logs | application text logs | 30-90 days | Compress, then delete if no incident |

---

## Category Policy

### Keep indefinitely

- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/execution_log/*.jsonl`
- incident reports
- committed research watchlists and verification trackers

Reason:

- These are the canonical trade and execution truth layers.

### Keep at least 365 days

- `runtime/quant_data/decision_log/*.jsonl`
- `runtime/quant_data/risk_log/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- `runtime/quant_data/orderbook_lineage/*.jsonl`
- `runtime/reports/paper_evaluation_*.json`
- `runtime/reports/replay_report_*.json`
- `runtime/reports/quant_data_quality_*.json`

Reason:

- These support replay continuity, watchlist verification, path truth, and
  risk diagnostics.

### Keep at least 90 days

- `runtime/quant_data/market_snapshots/*.jsonl`
- `runtime/quant_data/research_log/*.jsonl`
- `runtime/realtime_logs/**/scan_log_*.csv`

Reason:

- These are high-volume context layers. They are valuable for recent debugging
  and research, but should be summarized into smaller reports.

### Keep at least 180 days

- `runtime/quant_data/system_health/*.jsonl`
- `runtime/ownership/*.json` snapshots if copied by a future incident reporter

Reason:

- These support reliability audit, stale runtime review, and incident timing.

### Keep 30-90 days

- `logs/polytrade_bot_*.log`
- temporary validation logs

Reason:

- Text logs are operationally useful but not the canonical research truth if
  JSONL is healthy.

---

## Disk Growth Estimates

Recent observed daily file sizes from active paper evidence show that high-volume
JSONL can grow quickly.

Example one-day scale:

| Category | Example size |
|---|---:|
| `decision_log` | ~207 MB/day |
| `research_log` | ~110 MB/day |
| `market_snapshots` | ~62 MB/day |
| `risk_log` | ~42 MB/day |
| `orderbook_lineage` | ~25 MB/day |
| `system_health` | ~12 MB/day |
| `trade_journal` | < 1 MB/day in low-trade periods |
| `execution_log` | < 1 MB/day in low-trade periods |

Estimated total in an active day: **~450-500 MB/day**.

Approximate uncompressed growth:

| Duration | Estimate |
|---|---:|
| 7 days | 3-4 GB |
| 30 days | 14-15 GB |
| 90 days | 40-45 GB |
| 365 days | 160-180 GB |

These are estimates only. High-frequency settings, exception storms, or verbose
research events can increase growth materially.

---

## Compression Policy

Preferred future format:

- `.jsonl.zst` or `.jsonl.gz` for old JSONL
- `.csv.gz` for scan logs
- keep small `.json` reports uncompressed unless storage pressure requires it

Compression should preserve:

- filename date
- category
- run_id discoverability
- ability to run offline tools against decompressed copies

Compression must not:

- alter event payloads
- remove malformed lines
- combine categories
- combine contaminated duplicate-runtime windows without labels

---

## Evidence Protection Rules

Do not delete or compress active evidence when:

- a watchlist is in `VERIFICATION_IN_PROGRESS`
- a runtime incident is open
- duplicate runtime contamination is under review
- JSONL integrity failure is under review
- latest paper run has not been evaluated
- the data belongs to a date named in an active research artifact

Before any deletion:

1. Confirm category and date.
2. Confirm no active watchlist depends on the raw data.
3. Confirm no incident is open.
4. Confirm derived reports exist if raw data will be removed.
5. Record deletion plan in a docs-only cleanup audit.
6. Obtain explicit operator approval.

---

## Derived Summary Requirement

Before high-volume context data is archived or deleted, generate or preserve:

- data quality report
- replay report
- paper evaluation report
- run ID list
- event counts by category
- malformed line counts
- date-level and run-scoped summaries

This ensures research can continue without requiring every raw snapshot line.

---

## Retention Safety States

| State | Meaning | Allowed action |
|---|---|---|
| `ACTIVE` | Current date or current run | No deletion/compression |
| `PENDING_EVALUATION` | Run ended but reports not generated | No deletion |
| `INCIDENT_HOLD` | Incident or contamination review open | No deletion/compression |
| `RESEARCH_HOLD` | Active watchlist depends on data | No deletion |
| `ARCHIVE_READY` | Reports exist and no holds apply | Compression allowed |
| `DELETE_READY` | Explicit operator approval after archive | Deletion allowed |

---

## Operator Actions

| Condition | Action |
|---|---|
| Disk free > 20% | No retention action required |
| Disk free 10-20% | Compress archive-ready Tier 2 and Tier 5 |
| Disk free 5-10% | Stop new long-duration paper runs until storage is reviewed |
| Disk free < 5% | Stop paper runtime cleanly if possible; preserve evidence |
| Incident hold active | Do not delete or compress affected files |
| Active verification depends on files | Keep raw or compressed copy with restore path |

---

## Future Implementation Boundaries

Any future retention job must be:

- offline only
- disabled by default until approved
- dry-run capable
- category-aware
- incident-hold aware
- watchlist-hold aware
- log-only on first deployment

Required future tests:

- dry run deletes nothing
- active date is protected
- incident hold is protected
- permanent truth categories are never deleted
- compression preserves line count
- malformed lines are preserved
- deletion requires explicit approval flag

---

## Non-Authorization Clause

This policy is documentation only. It does not change runtime behavior, live
behavior, strategy, risk, execution, config, retention jobs, compression jobs,
or deletion behavior.
