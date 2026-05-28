# Repository Cleanup Action Plan

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Input: `docs/research/repository_cleanup_organization_audit.md`

Mode: docs-only plan. No files deleted, moved, renamed, compressed, archived, or changed outside this plan.

## Goal

Prepare the repository for performance stack setup by reducing evidence clutter, normalizing research document structure, and defining approval gates for generated files.

This plan is intentionally conservative:

- archive evidence, do not delete it;
- keep runtime and live-risk files untouched;
- preserve tests;
- preserve recent research lineage;
- require operator approval before any destructive or path-changing action.

## Guiding Policy

```text
CLEANUP_POLICY: ARCHIVE_FIRST
DELETE_POLICY: APPROVAL_REQUIRED
RUNTIME_POLICY: DO_NOT_MUTATE_ACTIVE_RUNTIME
DOCS_POLICY: MOVE_ONLY_IN_DEDICATED_CLEANUP_TASK
TEST_POLICY: NEVER_DELETE_TESTS
LIVE_POLICY: DO_NOT_TOUCH
```

## Proposed Research Folder Structure

Target structure for future cleanup tasks:

```text
docs/research/
  path_truth/
  executable_truth/
  session_edge/
  runtime_health/
  performance/
  archive/
  sessions/
    YYYY-MM-DD/
```

Folder ownership:

| Folder | Purpose | Examples |
|---|---|---|
| `docs/research/path_truth/` | path truth, replay-key, path join, checkpoint coverage | `path_truth_*`, `path_join_*`, `replay_key_*` |
| `docs/research/executable_truth/` | executable truth, MOS, dust, blocker observatory | `executable_*`, `offline_executable_*`, `minimum_executable_*` |
| `docs/research/session_edge/` | session, BTC/NO/ACTIVE, 02h, 09h10h, fast close | `session_*`, `failure_triangle_*`, `no_side_*`, `fast_close_*` |
| `docs/research/runtime_health/` | runtime state, process cleanup, live validation, no-trade, blocker audits | `runtime_*`, `morning_*`, `new_day_*`, `no_trade_*`, `signal_rejection_*`, `delta_extreme_*` |
| `docs/research/performance/` | cockpit, dashboard, performance-stack, UI observability | `research_cockpit_*`, `runtime_ui_*`, `terminal_ui_*` |
| `docs/research/archive/` | superseded docs whose content is preserved elsewhere | stale or replaced research docs only |
| `docs/research/sessions/YYYY-MM-DD/` | date-specific evidence packages and daily notes | run/day-specific audits and validation notes |

Rule: if a doc is both domain-specific and date-specific, keep the canonical copy in the domain folder and optionally place a session index link in `sessions/YYYY-MM-DD/`. Avoid duplicating the full content.

## Runtime Quant Data Archive Policy

Classification: `ARCHIVE_CANDIDATE`

Scope:

- `runtime/quant_data/decision_log/`
- `runtime/quant_data/research_log/`
- `runtime/quant_data/market_snapshots/`
- `runtime/quant_data/risk_log/`
- `runtime/quant_data/system_health/`
- `runtime/quant_data/execution_log/`
- `runtime/quant_data/trade_journal/`
- `runtime/quant_data/path_truth/`

Policy:

1. Never archive the current active UTC date while paper runtime is active.
2. Never archive a date required by an open validation task.
3. Keep the latest active date plus the latest completed date available uncompressed.
4. Archive completed dates older than the latest completed date into date bundles.
5. Archive by UTC evidence date, not local machine date.
6. Include a manifest before moving/compressing anything.
7. Preserve raw JSONL line integrity.
8. Do not rewrite historical JSONL.
9. Do not split or merge JSONL files during initial cleanup.
10. Do not delete source files until an archive verification step passes and operator approval is explicit.

Suggested archive layout:

```text
archive/evidence/runtime_quant_data/YYYY-MM-DD/
  MANIFEST.md
  decision_log_YYYY-MM-DD.jsonl.zst
  research_log_YYYY-MM-DD.jsonl.zst
  market_snapshots_YYYY-MM-DD.jsonl.zst
  risk_log_YYYY-MM-DD.jsonl.zst
  system_health_YYYY-MM-DD.jsonl.zst
  execution_log_YYYY-MM-DD.jsonl.zst
  trade_journal_YYYY-MM-DD.jsonl.zst
  path_truth_YYYY-MM-DD.jsonl.zst
```

Manifest fields:

| Field | Required |
|---|---|
| source path | yes |
| archive path | yes |
| source bytes | yes |
| archive bytes | yes |
| source line count | yes |
| parse-error count if checked | yes |
| SHA256 before archive | yes |
| SHA256 after restore/check | yes |
| run_ids present | yes |
| date range | yes |
| known research docs referencing the date | yes |
| operator approval id/date | yes |

Archive readiness classes:

| Class | Meaning | Action |
|---|---|---|
| `ACTIVE_DO_NOT_ARCHIVE` | current runtime date or active validation input | keep in place |
| `RECENT_KEEP_HOT` | latest completed date or latest validation run | keep in place |
| `READY_TO_ARCHIVE` | completed date, summarized, not active | archive candidate |
| `LOCKED_BY_RESEARCH` | referenced by open audit or unresolved gate | keep until task closes |
| `UNKNOWN` | insufficient metadata | inspect before action |

## Logs Archive Policy

Classification: `ARCHIVE_CANDIDATE`

Scope:

- `logs/polytrade_bot_*.log`
- rotated `logs/polytrade_bot_*.log.N`
- other generated runtime logs under `logs/`

Policy:

1. Keep current active runtime log in place.
2. Keep the latest run log for the current day in place.
3. Keep incident logs referenced by current docs in place until the incident closes.
4. Compress older logs by date.
5. Preserve original filenames inside archive bundles.
6. Include a log manifest with file sizes, timestamps, and related run_ids if inferable.
7. Do not delete logs after compression unless a separate verification and approval step is completed.

Suggested layout:

```text
archive/evidence/logs/YYYY-MM-DD/
  MANIFEST.md
  logs_YYYY-MM-DD.zip
```

Log retention recommendation:

| Log class | Keep hot | Archive |
|---|---:|---:|
| active run | yes | no |
| current day completed runs | yes | after day close |
| prior 2 days | optional | after daily summary exists |
| older than 2 completed days | no | yes |
| incident/milestone logs | yes until closed | after incident summary exists |

## Runtime Root Output Archive Policy

Classification: `ARCHIVE_CANDIDATE`

Files from the audit:

| File | Recommended archive target |
|---|---|
| `runtime/paper_harvest_20260523_085423.out.log` | `archive/evidence/runtime_outputs/2026-05-23/` |
| `runtime/paper_harvest_stdout.txt` | `archive/evidence/runtime_outputs/2026-05-23/` |
| `runtime/validation_extended_run.log` | `archive/evidence/runtime_outputs/2026-05-14/` |
| `runtime/validation_run_output.log` | `archive/evidence/runtime_outputs/2026-05-14/` |
| `runtime/liquidity_truth_validation.log` | `archive/evidence/runtime_outputs/2026-05-14/` |

Policy:

- confirm each file has a corresponding research summary before archiving;
- archive with manifest and checksums;
- do not delete original until operator explicitly approves after restore check.

## Docs/Research Move Plan

Classification: `MOVE_CANDIDATE`

No moves are authorized by this plan. These are proposed future targets.

### Move To `docs/research/path_truth/`

Candidate files:

- `docs/research/path_truth/path_join_root_cause_map.md`
- `docs/research/path_truth/path_truth_checkpoint_validation.md`
- `docs/research/path_truth/path_truth_field_coverage_gap_audit.md`
- `docs/research/path_truth/path_truth_gate_revision.md`
- `docs/research/path_truth/path_truth_identity_wiring_spec.md`
- `docs/research/path_truth/path_truth_implementation_spec.md`
- `docs/research/path_truth/path_truth_multiday_coverage_monitor.md`
- `docs/research/path_truth/path_truth_observability_design.md`
- `docs/research/path_truth/path_truth_replay_key_live_validation.md`
- `docs/research/path_truth/path_truth_replay_key_wiring_validation.md`
- `docs/research/path_truth/single_run_path_truth_audit.md`

Keep hot until replay-key validation closes:

- `docs/research/path_truth/path_truth_replay_key_live_validation.md`
- `docs/research/runtime_health/morning_replay_key_runtime_audit.md`
- `docs/research/runtime_health/runtime_replay_key_blocker_audit.md`

### Move To `docs/research/executable_truth/`

Candidate files:

- `docs/research/executable_truth/runtime_executable_truth_source_audit.md`
- `docs/research/executable_truth/offline_executable_truth_ledger_audit.md`
- `docs/research/executable_truth/executable_truth_frontier_map.md`
- `docs/research/executable_truth/executable_truth_blocker_observatory_design.md`
- `docs/research/executable_truth/dynamic_executable_expectancy_audit.md`
- `docs/research/executable_truth/minimum_executable_reality_audit.md`
- `docs/research/executable_truth/executable_reality_overlay_design.md`
- `docs/research/executable_truth/executable_overlay_phase_a.md`
- `docs/research/executable_truth/executable_reality_monitor.md`
- `docs/research/executable_truth/paper_sizing_audit.md`
- `docs/research/executable_truth/capital_ladder_audit.md`

### Move To `docs/research/session_edge/`

Candidate files:

- `docs/research/session_edge/failure_triangle_audit.md`
- `docs/research/session_edge/fast_close_distribution_audit.md`
- `docs/research/session_edge/no_side_weakness_audit.md`
- `docs/research/session_edge/session_02h_fast_sl_audit.md`
- `docs/research/session_edge/session_02h_multiday_validation.md`
- `docs/research/session_edge/session_09h10h_btc_strength_audit.md`
- `docs/research/session_edge/session_09h10h_failure_escape_audit.md`
- `docs/research/session_edge/session_09h10h_structural_edge.md`
- `docs/research/session_edge/session_09h10h_truth_layer_audit.md`
- `docs/research/session_edge/session_edge_missing_split_refresh.md`
- `docs/research/session_edge/session_edge_outside_control_audit.md`
- `docs/research/session_edge/session_personality_stability.md`
- `docs/research/session_edge/session_pressure_comparison_audit.md`
- `docs/research/session_edge/session_regime_09h_recurrence.md`
- `docs/research/session_edge/session_regime_09h10h_persistence.md`
- `docs/research/session_edge/session_survival_ranking.md`
- `docs/research/session_edge/regime_exception_09h_audit.md`

### Move To `docs/research/runtime_health/`

Candidate files:

- `docs/research/runtime_health/daily_runtime_path_truth_audit.md`
- `docs/research/runtime_health/morning_runtime_health_check.md`
- `docs/research/runtime_health/new_day_runtime_gate_audit.md`
- `docs/research/runtime_health/new_day_runtime_state_audit.md`
- `docs/research/runtime_health/paper_process_cleanup_audit.md`
- `docs/research/runtime_health/paper_runtime_replay_key_boot.md`
- `docs/research/runtime_health/runtime_evidence_farming_audit.md`
- `docs/research/runtime_health/morning_replay_key_runtime_audit.md`
- `docs/research/runtime_health/no_trade_open_runtime_audit.md`
- `docs/research/runtime_health/signal_rejection_root_cause_audit.md`
- `docs/research/runtime_health/delta_extreme_gate_audit.md`
- `docs/research/runtime_health/runtime_replay_key_blocker_audit.md`

### Move To `docs/research/performance/`

Candidate files:

- `docs/research/performance/research_cockpit_frontend_blueprint_v1.md`
- `docs/research/performance/research_cockpit_mounting_spec.md`
- `docs/research/performance/research_cockpit_ui_redesign_v1.md`
- `docs/research/performance/research_cockpit_v2_architecture.md`
- `docs/research/performance/research_cockpit_v2_roadmap.md`
- `docs/research/performance/runtime_ui_observability_gap_audit.md`
- `docs/research/performance/terminal_ui_v2_redesign.md`
- root `research_cockpit_v2_gap_audit.md`

### Move To `docs/research/sessions/YYYY-MM-DD/`

Candidate root files:

- `runtime_clean_validation_2026-05-19.md` -> `docs/research/sessions/2026-05-19/`
- `overnight_maturity_check_2026-05-19.md` -> `docs/research/sessions/2026-05-19/`
- `stop_loss_concentration_diagnosis_2026-05-19.md` -> `docs/research/sessions/2026-05-19/`
- `repo_canonical_check_2026-05-19.md` -> `docs/research/sessions/2026-05-19/` or `docs/research/runtime_health/`
- `DOC_TRUTH_RECONCILIATION_2026-05-14.md` -> `docs/research/archive/` or `docs/research/runtime_health/`
- `KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md` -> `docs/research/archive/` after confirming issue docs cover it

## Generated Files Requiring Approval Before Deletion

Classification: `DELETE_CANDIDATE_REQUIRES_APPROVAL`

| Path | Why approval is required |
|---|---|
| `.pytest_cache/` | generated, safe to regenerate, but deletion is out of scope without approval |
| `__pycache__/` | generated Python bytecode |
| `config/__pycache__/` | generated Python bytecode |
| `crypto_scalper/__pycache__/` | generated Python bytecode |
| `dashboard/__pycache__/` | generated Python bytecode |
| `polymarket/__pycache__/` | generated Python bytecode |
| `tests/__pycache__/` | generated Python bytecode |
| `tools/__pycache__/` | generated Python bytecode |
| `utils/__pycache__/` | generated Python bytecode |
| `research_cockpit/node_modules/` | generated dependencies, but reinstall path must be confirmed |
| `research_cockpit/dist/` | generated build output, but deployment/reference use must be checked |
| `docs.zip` | likely duplicate artifact, but verify origin before delete |

Approval checklist before deletion:

1. confirm path is ignored by git or intentionally untracked;
2. confirm no active process is reading it;
3. confirm regeneration command exists, if generated;
4. confirm no research doc references it as evidence;
5. get explicit operator approval naming the path.

## Files And Areas That Must Never Be Touched Casually

Classification: `DO_NOT_TOUCH`

- `.env`
- `.env.example` unless config docs task explicitly scopes it
- wallet/API credential helpers
- `config/`
- `polymarket/client.py`
- `polymarket/order_manager.py`
- `polymarket/trader.py` during cleanup
- `utils/risk_manager.py`
- `utils/position_tracker.py`
- live config and allowance paths
- `tests/` contents without a dedicated test migration plan
- current active runtime date under `runtime/quant_data/`
- current active log under `logs/`
- recent replay-key/path-truth validation docs until validation closes
- `archive/` contents unless archive-index cleanup is explicitly scoped

## Staged Cleanup Sequence

### Stage 0 - Freeze And Inventory

Goal: avoid mixing cleanup with active research/runtime changes.

- [ ] Confirm no cleanup will run while a paper runtime is actively writing the target date.
- [ ] Record `git status --short`.
- [ ] Record current active run_id and active log path, if any.
- [ ] Commit or park pending research docs before moving folders.
- [ ] Generate a date-level inventory for `runtime/quant_data`.
- [ ] Generate a date-level inventory for `logs`.
- [ ] Produce a proposed move map for docs only.

Exit criteria:

```text
NO_ACTIVE_TARGETS
PENDING_DOCS_ACCOUNTED_FOR
ARCHIVE_MANIFEST_PLAN_READY
```

### Stage 1 - Archive Runtime Evidence

Goal: reduce disk pressure without losing raw evidence.

- [ ] Select completed UTC dates older than the latest completed date.
- [ ] Exclude dates referenced by open validation tasks.
- [ ] Compute source size, line count, and SHA256 for each JSONL file.
- [ ] Create archive folder under `archive/evidence/runtime_quant_data/YYYY-MM-DD/`.
- [ ] Compress files into the archive folder.
- [ ] Write `MANIFEST.md`.
- [ ] Verify archive files exist and source checksums are recorded.
- [ ] Perform sample restore/read check.
- [ ] Ask for approval before deleting or removing originals.

Exit criteria:

```text
ARCHIVE_CREATED
MANIFEST_CREATED
RESTORE_CHECK_PASSED
ORIGINALS_STILL_PRESENT_UNTIL_APPROVED
```

### Stage 2 - Archive Logs

Goal: reduce log clutter while preserving incident evidence.

- [ ] Identify active log and keep it in place.
- [ ] Identify current-day logs and keep them in place until day close.
- [ ] Group older logs by date.
- [ ] Create `archive/evidence/logs/YYYY-MM-DD/`.
- [ ] Compress grouped logs preserving original filenames.
- [ ] Write a log manifest.
- [ ] Verify archive can be opened.
- [ ] Ask for approval before deleting originals.

Exit criteria:

```text
OLD_LOGS_ARCHIVED
ACTIVE_LOGS_UNTOUCHED
ORIGINALS_STILL_PRESENT_UNTIL_APPROVED
```

### Stage 3 - Organize Research Docs

Goal: make research navigable without breaking lineage.

- [ ] Create the proposed domain folders.
- [ ] Create a move map with old path -> new path.
- [ ] For each moved doc, update a central index.
- [ ] Keep a compatibility index at `docs/research/INDEX.md`.
- [ ] Move docs in small batches by domain.
- [ ] Run `rg` for old path references.
- [ ] Update references only in docs, not code.
- [ ] Commit each domain move separately.

Exit criteria:

```text
DOCS_MOVED_BY_DOMAIN
INDEX_UPDATED
OLD_PATH_REFERENCES_REVIEWED
NO_CODE_CHANGED
```

### Stage 4 - Root Markdown Cleanup

Goal: keep repo root focused on operating docs.

- [ ] Confirm each root dated research note has a target folder.
- [ ] Move root dated research notes to session or domain folders.
- [ ] Keep canonical root docs in place.
- [ ] Review `CLAUDE.md` separately before moving because it may be tool-facing.
- [ ] Review `docs.zip` origin before archive/delete decision.

Exit criteria:

```text
ROOT_CONTAINS_ONLY_OPERATING_DOCS_AND_ENTRYPOINTS
DATED_RESEARCH_NOTES_MOVED_OR_INDEXED
```

### Stage 5 - Generated Cache Cleanup

Goal: remove low-value generated files only after explicit approval.

- [ ] Ask operator to approve cache deletion paths.
- [ ] Confirm no tests/runtime are active.
- [ ] Delete only approved cache folders.
- [ ] Run targeted smoke tests only if requested.
- [ ] Record removed paths in cleanup report.

Exit criteria:

```text
APPROVAL_RECORDED
ONLY_APPROVED_GENERATED_FILES_REMOVED
NO_TEST_FILES_DELETED
```

### Stage 6 - Documentation Sync

Goal: make cleanup visible to future agents.

- [ ] Update `docs/PROJECT_CLEANUP_REPORT.md`.
- [ ] Update `DOCUMENTATION_MAP.md` for new research folders.
- [ ] Update `PROJECT_STRUCTURE.md` or `docs/PROJECT_STRUCTURE.md` only if folder semantics changed.
- [ ] Add archive manifest links.
- [ ] Confirm `AGENTS.md` cleanup rules still match reality.

Exit criteria:

```text
DOC_MAP_UPDATED
CLEANUP_REPORT_UPDATED
FUTURE_AGENTS_CAN_FIND EVIDENCE
```

## Operator Approval Gates

Approval required before:

| Action | Approval required |
|---|---|
| moving any file | yes |
| deleting any file | yes |
| compressing and removing originals | yes |
| touching `.env` | not allowed in cleanup |
| touching runtime code | not allowed in cleanup |
| touching risk/strategy/execution modules | not allowed in cleanup |
| deleting caches | yes |
| changing test layout | separate task required |
| changing docs references after moves | yes, docs-only |

## What This Plan Does Not Authorize

This plan does not authorize:

- deleting runtime evidence;
- deleting logs;
- changing live config;
- changing strategy thresholds;
- changing risk sizing;
- changing execution logic;
- stopping or restarting runtime;
- running replay;
- moving tests;
- changing import paths;
- rewriting historical JSONL;
- claiming performance stack readiness.

## Recommended First Cleanup Batch

When the operator approves an action task, the safest first batch is:

1. commit current pending research docs;
2. archive old completed `runtime/quant_data` dates with manifests, originals retained;
3. archive old `logs/` by date, originals retained;
4. create `docs/research/INDEX.md` and domain folder skeleton;
5. move only one low-risk docs domain first, preferably `performance/` or `executable_truth/`;
6. update `DOCUMENTATION_MAP.md` after the first move batch.

Avoid starting with caches or deletes. Evidence archive first gives the largest benefit with the lowest research risk.

## Final Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Files deleted: No

Files moved: No

Code changed: No

Tests run: none; docs-only cleanup plan.
