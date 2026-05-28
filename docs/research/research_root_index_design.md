# Research Root Index Design

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Inputs:

- `docs/research/docs_research_migration_map.md`
- `docs/research/docs_research_migration_dry_run_validation.md`

Mode: docs-only design. No files moved, renamed, deleted, archived, or changed outside this document.

## Purpose

Design the future `docs/research/INDEX.md` before the `docs/research` migration begins.

The root index should be the navigation layer that lets future agents and operators find research by domain, freshness, gate status, and blocker status without scanning all flat Markdown files.

It should not become a second research report. It should point to source docs, preserve lineage, and surface active work.

## Index Responsibilities

`docs/research/INDEX.md` should own:

- top-level research categories;
- active folder map;
- governance docs;
- current active reviews and gates;
- blocker surfacing;
- archive policy and archive index links;
- old path -> new path migration lineage;
- naming, chronology, and linking rules.

`docs/research/INDEX.md` should not own:

- raw runtime evidence;
- rewritten conclusions from source docs;
- duplicated full summaries from every report;
- strategy/risk/execution policy;
- phase promotion decisions.

## Recommended Top-Level Categories

The root index should present these categories in this order:

1. `Active Review`
2. `Blockers`
3. `Research Domains`
4. `Governance`
5. `Chronology`
6. `Archive`
7. `Migration Lineage`
8. `Rules`

Reasoning:

- active review and blockers need to be visible before folder taxonomy;
- research domains then provide stable navigation;
- governance explains why the folder layout exists;
- chronology and archive sections prevent old docs from vanishing intellectually after moves.

## Recommended Folder Structure

```text
docs/research/
  INDEX.md
  path_truth/
  executable_truth/
  session_edge/
  runtime_health/
  performance/
  archive/
    cleanup/
    performance/
    runtime_health/
    session_edge/
  sessions/
    YYYY-MM-DD/
```

Folder notes:

| Folder | Status | Index responsibility |
|---|---|---|
| `path_truth/` | proposed active domain | path joins, replay keys, checkpoints, identity wiring, gate status |
| `executable_truth/` | proposed active domain | MOS, dust zone, executable blockers, Growth Mode gates |
| `session_edge/` | proposed active domain | 02h/09h10h, BTC/NO, fast close, session and regime candidates |
| `runtime_health/` | proposed active domain | runtime audits, no-trade/rejection blockers, telemetry, timestamp/quote observability |
| `performance/` | proposed active domain | Research Cockpit, terminal UI, dashboards, operator console |
| `archive/` | proposed archival domain | superseded docs only after approval and index/backlink confirmation |
| `sessions/YYYY-MM-DD/` | existing active chronology folder | date-specific evidence packages and run/day reports |

## Governance Docs

The root index should list governance docs separately from research domains.

Recommended governance table:

| Doc | Status | Purpose |
|---|---|---|
| `repository_cleanup_organization_audit.md` | root-stay until cleanup closes | source audit for clutter and organization state |
| `repository_cleanup_action_plan.md` | root-stay active | cleanup policy and staged action sequence |
| `docs_research_migration_map.md` | root-stay active | full old path -> target domain map |
| `docs_research_migration_dry_run_validation.md` | root-stay active | dry-run validation and move-risk status |
| `research_root_index_design.md` | root-stay active until `INDEX.md` exists | design for this future index |

After `INDEX.md` is created and the migration completes, these can be reviewed for `docs/research/archive/cleanup/`, not deleted.

## Active Review Surfacing

The index should have an `Active Review` section near the top.

Recommended format:

```markdown
## Active Review

| Theme | Status | Primary doc | Notes |
|---|---|---|---|
| Path Truth replay-key validation | ACTIVE / RECENT | `path_truth/...` | Keep hot until validation closes |
| Executable Truth | BLOCKED | `executable_truth/...` | Signal evidence exists; executable PnL blocked |
| Session Edge | REVIEW_ONLY | `session_edge/...` | No strategy change authorized |
| Runtime Health | WATCH | `runtime_health/...` | Current no-trade/rejection docs remain evidence only |
```

Rules:

- Keep active review rows short.
- Link one primary doc per row.
- Add secondary docs only in the domain section.
- Use status labels, not prose-heavy summaries.

Suggested status labels:

| Label | Meaning |
|---|---|
| `ACTIVE` | currently being validated or monitored |
| `RECENT` | recent but not actively changing |
| `REVIEW_ONLY` | research candidate; no runtime authority |
| `BLOCKED` | cannot advance without missing evidence/fields |
| `SUPERSEDED` | preserved for lineage; use newer doc |
| `ARCHIVE_CANDIDATE` | eligible only after approval |

## Blocker Surfacing

The index should surface blockers without promoting them into policy.

Recommended blocker table:

```markdown
## Blockers

| Blocker | Area | Status | Source | Required unlock |
|---|---|---|---|---|
| Executable PnL | executable truth | BLOCKED | `executable_truth/...` | fill/cancel/partial fill truth and MOS authority |
| Path Join | path truth | ACTIVE / RECENT | `path_truth/...` | stable `paper_trade_replay_key` linkage |
| Dust Zone | executable truth | BLOCKER_EVIDENCE | `executable_truth/...` | non-dust sample under approved MOS |
| Delta Extreme | runtime health | REVIEW_ONLY | `runtime_health/...` | cross-run proof before any gate change |
```

Rules:

- Do not include unverified performance claims.
- Do not mark S3/Growth/live as ready from research docs alone.
- Blocker status must link to source evidence.
- If a blocker is resolved, keep a closed row with date and source instead of deleting the row immediately.

## Domain Index Design

Each domain section should have the same shape so future agents can scan quickly.

Recommended section template:

```markdown
## Path Truth

Purpose: path truth, replay-key, path joins, checkpoint coverage, identity wiring.

Current status: ACTIVE / RECENT

Primary docs:

| Doc | Status | Date | Lineage |
|---|---|---|---|
| `path_truth/path_truth_multiday_coverage_monitor.md` | ACTIVE | n/a | gate monitor |
| `path_truth/path_join_root_cause_map.md` | RECENT | n/a | PATH_JOIN_0_77 root cause |

Open questions:

- ...

Do not infer:

- ...
```

Use the same pattern for:

- `Executable Truth`
- `Session Edge`
- `Runtime Health`
- `Performance`

## Executable Truth Docs

Index purpose:

- keep Signal Mode distinct from Executable Truth;
- keep dust/MOS/evidence blockers visible;
- prevent Hermes or operators from ingesting `executable_pnl` before it exists.

Primary docs to list after migration:

- `executable_truth/runtime_executable_truth_source_audit.md`
- `executable_truth/offline_executable_truth_ledger_audit.md`
- `executable_truth/executable_truth_frontier_map.md`
- `executable_truth/executable_truth_blocker_observatory_design.md`
- `executable_truth/minimum_executable_reality_audit.md`
- `executable_truth/dynamic_executable_expectancy_audit.md`
- `executable_truth/paper_sizing_audit.md`
- `executable_truth/capital_ladder_audit.md`

Index warning:

```text
Executable PnL remains BLOCKED unless a source doc explicitly proves fill truth, cancel truth, partial fill truth, MOS authority, and non-dust executable minimum coverage.
```

## Path Truth Docs

Index purpose:

- make path truth gate and replay-key lineage easy to find;
- keep active validation docs hot;
- preserve old-row/null-key caveats.

Primary docs to list after migration:

- `path_truth/path_truth_multiday_coverage_monitor.md`
- `path_truth/path_join_root_cause_map.md`
- `path_truth/path_truth_identity_wiring_spec.md`
- `path_truth/path_truth_replay_key_live_validation.md`
- `path_truth/path_truth_replay_key_wiring_validation.md`
- `path_truth/replay_join_key_contract.md`
- `path_truth/single_run_path_truth_audit.md`

Index warning:

```text
Path Truth supports evidence continuity. It does not prove executable PnL or live readiness.
```

## Session Edge Docs

Index purpose:

- organize BTC, NO, 02h, 09h10h, fast close, and regime/personality research;
- separate candidate evidence from strategy permission;
- preserve weakened/invalidated candidate lineage.

Primary docs to list after migration:

- `session_edge/early_research_gate_review.md`
- `session_edge/failure_triangle_audit.md`
- `session_edge/fast_close_distribution_audit.md`
- `session_edge/no_side_weakness_audit.md`
- `session_edge/session_edge_missing_split_refresh.md`
- `session_edge/session_edge_outside_control_audit.md`
- `session_edge/session_02h_multiday_validation.md`
- `session_edge/session_09h10h_btc_strength_audit.md`
- `session_edge/session_09h10h_structural_edge.md`

Index warning:

```text
Session Edge docs are research-only unless a future approved task separately implements and tests runtime policy.
```

## Runtime Health Docs

Index purpose:

- surface daily runtime health, no-trade blockers, rejection causes, timestamp/quote observability, and Telegram telemetry;
- keep current/recent active validation docs easy to locate;
- prevent runtime incident docs from being buried in session research.

Primary docs to list after migration:

- `runtime_health/no_trade_open_runtime_audit.md`
- `runtime_health/signal_rejection_root_cause_audit.md`
- `runtime_health/delta_extreme_gate_audit.md`
- `runtime_health/morning_replay_key_runtime_audit.md`
- `runtime_health/runtime_replay_key_blocker_audit.md`
- `runtime_health/execution_timestamp_contract_v1.md`
- `runtime_health/quote_lineage_contract_v1.md`
- `runtime_health/telegram_telemetry_validation.md`

Index warning:

```text
Runtime Health docs diagnose evidence and observability. They do not authorize strategy, risk, or execution changes.
```

## Performance Docs

Index purpose:

- group Research Cockpit, terminal UI, Telegram/operator console, and dashboard/reporting UX;
- separate display/observability design from runtime policy;
- make future UI mounting work discoverable.

Primary docs to list after migration:

- `performance/runtime_ui_observability_gap_audit.md`
- `performance/research_cockpit_mounting_spec.md`
- `performance/research_cockpit_v2_architecture.md`
- `performance/research_cockpit_v2_roadmap.md`
- `performance/research_cockpit_frontend_blueprint_v1.md`
- `performance/terminal_ui_v2_redesign.md`
- `performance/telegram_operator_console_design.md`

Index warning:

```text
Performance docs describe operator visibility and dashboards. They do not alter trading behavior.
```

## Archive Design

Archive folders should remain empty until a separate archive task is approved.

Recommended archive structure:

```text
docs/research/archive/
  cleanup/
  performance/
  runtime_health/
  session_edge/
  path_truth/
  executable_truth/
```

Archive entry template:

```markdown
| Archived doc | Replaced by | Archive date | Reason | Approval |
|---|---|---|---|---|
| `archive/cleanup/old_doc.md` | `../repository_cleanup_action_plan.md` | YYYY-MM-DD | superseded | operator-approved task |
```

Archive rules:

- Archive is not delete.
- Never archive active monitors.
- Never archive a doc without a replacement or index entry.
- Never archive docs referenced by an open validation task.
- Keep original filename on first archive pass.
- Record old path, archive path, replacement, and approval note.

## Chronology Rules

Use these rules in the future `INDEX.md`:

1. Prefer domain folder as canonical location for domain research.
2. Use `sessions/YYYY-MM-DD/` for date-specific evidence packages and daily notes.
3. If a doc is both domain-specific and date-specific, keep canonical content in the domain folder and add a session link only when useful.
4. Do not duplicate full content between domain and session folders.
5. Preserve dates already embedded in filenames.
6. Do not rename files during the first move pass.
7. Use the index to record old path -> new path.

Suggested date fields:

| Field | Meaning |
|---|---|
| `doc_date` | date in title or filename, if present |
| `created_or_migrated` | migration date if doc has no embedded date |
| `source_run_id` | run id if the doc is tied to a run |
| `lineage` | source audit, validation, follow-up, superseded, or current |

## Naming Rules

First migration pass:

- keep existing filenames;
- use lowercase snake_case for new docs;
- use `_audit.md`, `_design.md`, `_spec.md`, `_monitor.md`, `_validation.md`, `_map.md`, or `_plan.md` suffixes;
- do not rename to improve aesthetics during migration;
- do not remove dates from filenames;
- do not add status labels like `_final` unless already present.

Future new docs:

| Suffix | Use |
|---|---|
| `_audit.md` | read-only diagnosis or evidence review |
| `_design.md` | future architecture/design without implementation |
| `_spec.md` | field/interface/contract spec |
| `_monitor.md` | recurring or cumulative evidence state |
| `_validation.md` | post-change or post-run evidence validation |
| `_map.md` | lineage, dependency, or migration map |
| `_plan.md` | staged action plan |

## Lineage Rules

Every future index row should include enough lineage to prevent research amnesia:

| Column | Required? | Notes |
|---|---:|---|
| `Doc` | yes | relative path from `docs/research/` |
| `Status` | yes | `ACTIVE`, `RECENT`, `REVIEW_ONLY`, `BLOCKED`, `SUPERSEDED`, `ARCHIVE_CANDIDATE` |
| `Domain` | yes | path truth, executable truth, session edge, runtime health, performance, governance, archive |
| `Date` | yes if inferable | filename/title date or `n/a` |
| `Lineage` | yes | source audit, follow-up, validation, design, monitor |
| `Do not infer` | recommended | short safety caveat |

For moved docs, add:

| Old path | New path | Move batch | Reference update status |
|---|---|---|---|

## Active Review And Blocker Rules

Active reviews should be surfaced at the top only while they need operator attention.

Promote a doc into `Active Review` when:

- it is the current gate monitor;
- it identifies a top blocker;
- it is a validation after recent observability work;
- it informs whether a future migration/move/archive can proceed.

Remove a doc from `Active Review` when:

- a successor doc supersedes it;
- the blocker is resolved and indexed;
- the validation task closes;
- it is moved into archive with approval.

Blocker rows should use these labels:

| Label | Meaning |
|---|---|
| `BLOCKED` | cannot proceed without missing evidence/field/work |
| `CAUTION` | evidence exists but is not enough for promotion |
| `REVIEW_ONLY` | hypothesis/candidate, no runtime authority |
| `RESOLVED` | closed by later evidence or implementation |
| `UNKNOWN` | source docs conflict or coverage is insufficient |

## Recommended `INDEX.md` Skeleton

```markdown
# Research Index

Last updated: YYYY-MM-DD

Mode: navigation and lineage only. This index does not authorize runtime, strategy, risk, execution, wallet, or live changes.

## Active Review

| Theme | Status | Primary doc | Notes |
|---|---|---|---|

## Blockers

| Blocker | Area | Status | Source | Required unlock |
|---|---|---|---|---|

## Research Domains

| Domain | Folder | Purpose | Status |
|---|---|---|---|
| Path Truth | `path_truth/` | path joins, replay key, checkpoints | active |
| Executable Truth | `executable_truth/` | MOS, dust, executable blockers | active |
| Session Edge | `session_edge/` | session candidates and controls | active |
| Runtime Health | `runtime_health/` | runtime audits and telemetry | active |
| Performance | `performance/` | Cockpit, UI, dashboard visibility | active |

## Governance

| Doc | Status | Purpose |
|---|---|---|

## Path Truth

| Doc | Status | Date | Lineage | Do not infer |
|---|---|---|---|---|

## Executable Truth

| Doc | Status | Date | Lineage | Do not infer |
|---|---|---|---|---|

## Session Edge

| Doc | Status | Date | Lineage | Do not infer |
|---|---|---|---|---|

## Runtime Health

| Doc | Status | Date | Lineage | Do not infer |
|---|---|---|---|---|

## Performance

| Doc | Status | Date | Lineage | Do not infer |
|---|---|---|---|---|

## Sessions

| Date | Folder | Notes |
|---|---|---|

## Archive

| Archived doc | Replaced by | Archive date | Reason | Approval |
|---|---|---|---|---|

## Migration Lineage

| Old path | New path | Batch | Reference update status |
|---|---|---|---|

## Rules

- Archive is not delete.
- First migration pass preserves filenames.
- Runtime, strategy, risk, execution, wallet, live config, tests, logs, and JSONL are out of scope.
- Research docs do not authorize trading behavior changes.
```

## Recommended First Population

Before any move batch, create `docs/research/INDEX.md` with:

1. the safety mode line;
2. governance table;
3. active review table;
4. blocker table;
5. domain table;
6. placeholder domain sections;
7. migration lineage table with `PENDING_MOVE` status.

Do not populate every moved row manually during the same task unless explicitly scoped. A thin but correct index is safer than a huge index that goes stale immediately.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Files moved: No

Files renamed: No

Files deleted: No

Code changed: No

Tests run: none; docs-only index design.
