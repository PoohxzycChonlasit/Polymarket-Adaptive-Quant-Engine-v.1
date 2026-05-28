# Research Index

Last updated: 2026-05-28

Mode: navigation and lineage only. This index does not authorize runtime, strategy, risk, execution, wallet, replay, or live changes.

## Project Overview

This folder is the permanent research memory for the Polymarket Adaptive Quant Engine.

Current research posture:

```text
Runtime mode: PAPER / SIGNAL_MODE
Research phase: PATH_TRUTH / EVIDENCE_FARMING
Executable truth: NOT_REACHED
Growth mode: BLOCKED
Live readiness: NOT_READY
```

The current truth ladder is:

```text
Signal Truth
-> Path Truth
-> Executable Truth
-> Growth Readiness
-> Live Readiness
```

Research docs are evidence and design artifacts. They do not change trading behavior unless a later implementation task explicitly scopes code changes, tests, and runtime validation.

## Research Governance Rules

- Paper evidence is not executable evidence.
- Signal PnL is not executable PnL.
- Path truth continuity is not fill truth.
- Dust-zone trades are not executable proof.
- Session-edge candidates are research-only until a separate approved policy implementation exists.
- Docs may summarize blockers, but docs do not promote S3, Growth Mode, or live readiness.
- Archive is not delete.
- First migration pass must preserve filenames.
- No file moves, deletes, renames, runtime mutation, replay, strategy change, risk change, execution change, or live config change is authorized by this index.

## Recommended Reading Order For New Agents

1. [repository_cleanup_action_plan.md](repository_cleanup_action_plan.md)
2. [docs_research_migration_map.md](docs_research_migration_map.md)
3. [docs_research_migration_dry_run_validation.md](docs_research_migration_dry_run_validation.md)
4. [research_root_index_design.md](research_root_index_design.md)
5. [path_truth_multiday_coverage_monitor.md](path_truth/path_truth_multiday_coverage_monitor.md)
6. [path_join_root_cause_map.md](path_truth/path_join_root_cause_map.md)
7. [runtime_executable_truth_source_audit.md](executable_truth/runtime_executable_truth_source_audit.md)
8. [offline_executable_truth_ledger_audit.md](executable_truth/offline_executable_truth_ledger_audit.md)
9. [executable_truth_frontier_map.md](executable_truth/executable_truth_frontier_map.md)
10. [early_research_gate_review.md](path_truth/early_research_gate_review.md)
11. [signal_rejection_root_cause_audit.md](runtime_health/signal_rejection_root_cause_audit.md)
12. [delta_extreme_gate_audit.md](runtime_health/delta_extreme_gate_audit.md)

Operator guidance: start with active blockers and active reviews, then read the domain section for the work you are about to touch. Do not start from raw runtime data unless a task explicitly requires it.

## Current Project Phase

| Area | Status | Notes |
|---|---|---|
| Signal evidence | `ACTIVE` | Paper signal evidence exists and remains evidence-only. |
| Path Truth | `ACTIVE` | Checkpoint and replay-key identity work is the current continuity layer. |
| Evidence farming | `ACTIVE` | Continue collecting clean paper/path truth evidence before policy changes. |
| Executable Truth | `NOT_REACHED` | Raw ingredients exist, but canonical executable PnL remains blocked. |
| Growth Mode | `BLOCKED` | Blocked by dust/MOS/fill/cancel/partial-fill truth gaps. |
| Live | `NOT_READY` | No live promotion is implied or authorized. |

## Current Top Unlock Chain

```text
1. Keep clean paper evidence farming stable.
2. Preserve Path Truth direct join continuity.
3. Resolve runtime truth and empty_book ambiguity.
4. Establish MOS authority and dust-zone classification.
5. Add fill/cancel/partial-fill truth.
6. Only then evaluate executable PnL.
7. Only after executable PnL truth can Growth readiness be reviewed.
```

## Active Blockers

| Blocker | Area | Status | Source | Required unlock |
|---|---|---|---|---|
| `RUNTIME_TRUTH_UNKNOWN` | runtime health / executable truth | `BLOCKED` | [runtime_executable_truth_source_audit.md](executable_truth/runtime_executable_truth_source_audit.md) | Canonical runtime truth fields and approved ledger semantics. |
| `MOS_UNKNOWN` | executable truth | `BLOCKED` | [minimum_executable_reality_audit.md](executable_truth/minimum_executable_reality_audit.md), [paper_sizing_audit.md](executable_truth/paper_sizing_audit.md) | Authoritative minimum order size / minimum shares source. |
| `EXECUTABLE_PNL_BLOCKED` | executable truth | `BLOCKED` | [offline_executable_truth_ledger_audit.md](executable_truth/offline_executable_truth_ledger_audit.md), [executable_truth_frontier_map.md](executable_truth/executable_truth_frontier_map.md) | Fill truth, cancel truth, partial-fill truth, MOS authority, and non-dust coverage. |
| `empty_book ambiguity` | runtime health | `REVIEW_ONLY` | [signal_rejection_root_cause_audit.md](runtime_health/signal_rejection_root_cause_audit.md), [delta_extreme_gate_audit.md](runtime_health/delta_extreme_gate_audit.md) | Cross-run evidence distinguishing true liquidity absence from parsing/staleness artifacts. |

## Resolved Lineage

| Item | Status | Source | Notes |
|---|---|---|---|
| `PATH_JOIN_0_77` | `RESOLVED_LINEAGE` | [path_join_root_cause_map.md](path_truth/path_join_root_cause_map.md), [path_truth_identity_wiring_spec.md](path_truth/path_truth_identity_wiring_spec.md), [path_truth_replay_key_wiring_validation.md](path_truth/path_truth_replay_key_wiring_validation.md) | Root cause was identity island; direct key target is `(run_id, paper_trade_replay_key)`. |
| Path truth direct join validation | `100_PERCENT_DIRECT_JOIN_VALIDATION` | [path_truth_replay_key_live_validation.md](path_truth/path_truth_replay_key_live_validation.md), [replay_key_validation_after_trade.md](path_truth/replay_key_validation_after_trade.md) | Treat as resolved lineage for post-wiring rows; legacy/null rows remain historical caveats. |

Do not infer executable PnL or live readiness from resolved path joins.

## Active Reviews

| Theme | Status | Primary doc | Notes |
|---|---|---|---|
| Evidence farming | `ACTIVE` | [runtime_evidence_farming_audit.md](runtime_health/runtime_evidence_farming_audit.md) | Current operating posture remains paper evidence collection. |
| Path truth gate | `ACTIVE` | [path_truth_multiday_coverage_monitor.md](path_truth/path_truth_multiday_coverage_monitor.md) | Gate state should be read before path-truth conclusions. |
| Replay-key validation | `RECENT / KEEP_HOT` | [path_truth_replay_key_live_validation.md](path_truth/path_truth_replay_key_live_validation.md) | Keep linked until validation lineage closes. |
| Executable truth | `BLOCKED` | [executable_truth_frontier_map.md](executable_truth/executable_truth_frontier_map.md) | Hermes may ingest signal/blocker/dust evidence, not executable PnL. |
| Session edge | `REVIEW_ONLY` | [early_research_gate_review.md](path_truth/early_research_gate_review.md) | Candidates survive only as research until stronger controls exist. |
| Runtime no-trade / rejection | `REVIEW_ONLY` | [signal_rejection_root_cause_audit.md](runtime_health/signal_rejection_root_cause_audit.md) | No strategy/risk change is implied. |
| Delta extreme | `REVIEW_ONLY` | [delta_extreme_gate_audit.md](runtime_health/delta_extreme_gate_audit.md) | Gate should remain untouched until more evidence. |
| Contradiction review | `ACTIVE_REVIEW` | [session_edge_missing_split_refresh.md](session_edge/session_edge_missing_split_refresh.md), [quote_source_outcome_audit.md](quote_source_outcome_audit.md) | Track weakened/adverse/unavailable splits without changing policy. |

## Executable Truth

Purpose: distinguish signal evidence from executable evidence, keep MOS/dust/fill blockers visible, and prevent premature Growth Mode claims.

Current status: `EXECUTABLE_TRUTH_NOT_REACHED`

Primary docs:

| Doc | Status | Lineage | Do not infer |
|---|---|---|---|
| [runtime_executable_truth_source_audit.md](executable_truth/runtime_executable_truth_source_audit.md) | `PARTIAL_RAW_EVIDENCE` | runtime source inventory | executable PnL |
| [offline_executable_truth_ledger_audit.md](executable_truth/offline_executable_truth_ledger_audit.md) | `LEDGER_SPEC_ONLY` | offline ledger audit | executable approval |
| [executable_truth_frontier_map.md](executable_truth/executable_truth_frontier_map.md) | `FRONTIER_MAP` | Signal Mode -> Executable Truth roadmap | Growth readiness |
| [executable_truth_blocker_observatory_design.md](executable_truth/executable_truth_blocker_observatory_design.md) | `DESIGN_ONLY` | blocker observatory | runtime telemetry exists |
| [minimum_executable_reality_audit.md](executable_truth/minimum_executable_reality_audit.md) | `BLOCKER_EVIDENCE` | MOS/minimum reality | exchange-confirmed MOS |
| [dynamic_executable_expectancy_audit.md](executable_truth/dynamic_executable_expectancy_audit.md) | `RESEARCH_ONLY` | expectancy/MOS scenarios | executable profitability |
| [paper_sizing_audit.md](executable_truth/paper_sizing_audit.md) | `DUST_EVIDENCE` | paper sizing/dust | executable sizing approval |
| [capital_ladder_audit.md](executable_truth/capital_ladder_audit.md) | `RESEARCH_ONLY` | capital ladder | live sizing |
| [executable_reality_overlay_design.md](executable_truth/executable_reality_overlay_design.md) | `DESIGN_ONLY` | overlay design | runtime overlay exists |
| [executable_reality_monitor.md](executable_truth/executable_reality_monitor.md) | `MONITOR` | executable reality tracking | executable PnL |

Warning: executable PnL remains blocked unless source docs prove fill truth, cancel truth, partial-fill truth, MOS authority, and non-dust executable minimum coverage.

## Path Truth

Purpose: preserve path continuity, replay-key linkage, checkpoint coverage, and join reliability.

Current status: `ACTIVE`

Primary docs:

| Doc | Status | Lineage | Do not infer |
|---|---|---|---|
| [path_truth_multiday_coverage_monitor.md](path_truth/path_truth_multiday_coverage_monitor.md) | `ACTIVE` | gate monitor | executable truth |
| [path_join_root_cause_map.md](path_truth/path_join_root_cause_map.md) | `RESOLVED_LINEAGE` | PATH_JOIN_0_77 root cause | future rows all valid without validation |
| [path_truth_identity_wiring_spec.md](path_truth/path_truth_identity_wiring_spec.md) | `SPEC` | replay-key wiring | candidate_id/decision_id wired |
| [path_truth_replay_key_live_validation.md](path_truth/path_truth_replay_key_live_validation.md) | `KEEP_HOT` | live paper validation note | executable PnL |
| [path_truth_replay_key_wiring_validation.md](path_truth/path_truth_replay_key_wiring_validation.md) | `VALIDATION` | direct join validation | legacy rows repaired |
| [path_truth_checkpoint_validation.md](path_truth/path_truth_checkpoint_validation.md) | `VALIDATION` | checkpoint behavior | full lifecycle coverage |
| [path_truth_gate_revision.md](path_truth/path_truth_gate_revision.md) | `GATE_POLICY` | early/implementation gates | implementation approval |
| [path_truth_field_coverage_gap_audit.md](path_truth/path_truth_field_coverage_gap_audit.md) | `GAP_AUDIT` | missing fields | runtime fields exist |
| [replay_join_key_contract.md](path_truth/replay_join_key_contract.md) | `CONTRACT` | join-key contract | executable joins |
| [single_run_path_truth_audit.md](path_truth/single_run_path_truth_audit.md) | `AUDIT` | single-run evidence | multiday proof |

Warning: Path Truth supports evidence continuity. It does not prove fill truth, executable PnL, Growth readiness, or live readiness.

## Session Edge

Purpose: organize session, BTC/ETH, YES/NO, lifecycle, fast-close, and regime/personality candidate research.

Current status: `REVIEW_ONLY`

Primary docs:

| Doc | Status | Lineage | Do not infer |
|---|---|---|---|
| [early_research_gate_review.md](path_truth/early_research_gate_review.md) | `GATE_REVIEW` | 3-date early review | implementation approval |
| [failure_triangle_audit.md](session_edge/failure_triangle_audit.md) | `RESEARCH_ONLY` | BTC/NO/ACTIVE interaction | policy change |
| [fast_close_distribution_audit.md](session_edge/fast_close_distribution_audit.md) | `RESEARCH_ONLY` | fast-close behavior | stop-loss change |
| [no_side_weakness_audit.md](session_edge/no_side_weakness_audit.md) | `RESEARCH_ONLY` | NO side weakness | side filter |
| [session_02h_multiday_validation.md](session_edge/session_02h_multiday_validation.md) | `RESEARCH_ONLY` | 02h hostile candidate | session block |
| [session_09h10h_btc_strength_audit.md](session_edge/session_09h10h_btc_strength_audit.md) | `RESEARCH_ONLY` | 09h10h BTC candidate | BTC policy |
| [session_edge_missing_split_refresh.md](session_edge/session_edge_missing_split_refresh.md) | `CONTRADICTION_REVIEW` | target vs controls | strategy update |
| [session_edge_outside_control_audit.md](session_edge/session_edge_outside_control_audit.md) | `CONTROL_AUDIT` | outside-session controls | session edge confirmed |
| [session_pressure_comparison_audit.md](session_edge/session_pressure_comparison_audit.md) | `RESEARCH_ONLY` | session pressure | executable edge |
| [hourly_market_personality_map.md](session_edge/hourly_market_personality_map.md) | `MAP` | hourly behavior | runtime schedule |

Active contradiction review state:

- 02h remains a hostile-session candidate, but still research-only.
- 09h10h is degraded/partial, not a clean escape.
- BTC and NO weakness require continued controls.
- Fast close is real behavior, but not yet a stop-loss or entry-policy change.

## Runtime Health

Purpose: collect runtime health, no-trade, rejection, quote/timestamp, Telegram, and process-state evidence without changing runtime behavior.

Current status: `WATCH / REVIEW_ONLY`

Primary docs:

| Doc | Status | Lineage | Do not infer |
|---|---|---|---|
| [runtime_evidence_farming_audit.md](runtime_health/runtime_evidence_farming_audit.md) | `ACTIVE` | evidence farming | strategy/risk change |
| [new_day_runtime_gate_audit.md](runtime_health/new_day_runtime_gate_audit.md) | `DAILY_AUDIT` | gate/runtime health | promotion |
| [morning_replay_key_runtime_audit.md](runtime_health/morning_replay_key_runtime_audit.md) | `KEEP_HOT` | replay-key runtime status | validation complete for all future rows |
| [runtime_replay_key_blocker_audit.md](runtime_health/runtime_replay_key_blocker_audit.md) | `KEEP_HOT` | replay-key blocker | runtime fix authorization |
| [no_trade_open_runtime_audit.md](runtime_health/no_trade_open_runtime_audit.md) | `AUDIT` | no-trade evidence | risk/strategy change |
| [signal_rejection_root_cause_audit.md](runtime_health/signal_rejection_root_cause_audit.md) | `ROOT_CAUSE` | rejection blockers | over-filtering proof |
| [delta_extreme_gate_audit.md](runtime_health/delta_extreme_gate_audit.md) | `REVIEW_ONLY` | delta gate evidence | gate change |
| [execution_timestamp_contract_v1.md](runtime_health/execution_timestamp_contract_v1.md) | `CONTRACT` | timestamp fields | implementation complete |
| [quote_lineage_contract_v1.md](quote_lineage_contract_v1.md) | `CONTRACT` | quote lineage | quote truth complete |
| [telegram_telemetry_validation.md](runtime_health/telegram_telemetry_validation.md) | `VALIDATION` | Telegram telemetry | alert policy change |

Warning: Runtime Health docs diagnose observability and evidence cleanliness. They do not authorize trading behavior changes.

## Performance

Purpose: group Research Cockpit, runtime UI, terminal UI, dashboard, and operator console observability work.

Current status: `DESIGN / OBSERVABILITY`

Primary docs:

| Doc | Status | Lineage | Do not infer |
|---|---|---|---|
| [runtime_ui_observability_gap_audit.md](runtime_ui_observability_gap_audit.md) | `GAP_AUDIT` | operator UI gaps | UI implemented |
| [research_cockpit_mounting_spec.md](research_cockpit_mounting_spec.md) | `SPEC` | cockpit mount plan | runtime mount exists |
| [research_cockpit_v2_architecture.md](research_cockpit_v2_architecture.md) | `BLUEPRINT` | cockpit architecture | implementation |
| [research_cockpit_v2_roadmap.md](research_cockpit_v2_roadmap.md) | `ROADMAP` | cockpit build order | runtime behavior change |
| [research_cockpit_frontend_blueprint_v1.md](research_cockpit_frontend_blueprint_v1.md) | `BLUEPRINT` | frontend design | dashboard shipped |
| [terminal_ui_v2_redesign.md](terminal_ui_v2_redesign.md) | `DESIGN` | terminal UI | active display state |
| [telegram_operator_console_design.md](telegram_operator_console_design.md) | `DESIGN` | Telegram console | Telegram behavior |

Warning: Performance docs describe visibility and operator experience. They do not alter strategy, risk, execution, or live behavior.

## Archive And Navigation

Current archive status: `NOT_STARTED`

Archive candidate classes:

| Class | Status | Rule |
|---|---|---|
| cleanup governance docs | `FUTURE_REVIEW` | archive only after migration completes and this index links replacements |
| superseded UI/design drafts | `FUTURE_REVIEW` | archive only after confirming newer docs preserve decisions |
| completed boot/watch notes | `FUTURE_REVIEW` | archive only after validation lineage closes |
| historical daily health docs | `FUTURE_REVIEW` | archive only after summarized by an index |

Archive rules:

- Archive is not delete.
- Never archive active monitors.
- Never archive docs referenced by an open validation task.
- Preserve original filename on first archive pass.
- Record old path, archive path, replacement, and approval note.

## Chronology And Lineage Rules

1. Preserve filenames during the first migration pass.
2. Keep domain research in its domain folder after migration.
3. Keep date-specific evidence packages under `sessions/YYYY-MM-DD/`.
4. If a doc is both domain-specific and date-specific, keep canonical content in the domain folder and link from the session folder only when useful.
5. Do not duplicate full content between domain and session folders.
6. Do not rewrite findings, conclusions, counts, or metric values during migration.
7. After each move batch, update docs-only references with `rg`.
8. Keep an old path -> new path migration table until all references are updated.

Lineage labels:

| Label | Meaning |
|---|---|
| `ACTIVE` | current monitor or current validation input |
| `KEEP_HOT` | recent and should remain easy to find |
| `REVIEW_ONLY` | research candidate with no runtime authority |
| `BLOCKED` | cannot advance without missing truth |
| `RESOLVED_LINEAGE` | prior blocker resolved, preserved for history |
| `SUPERSEDED` | use successor doc but keep for record |
| `ARCHIVE_CANDIDATE` | eligible only after explicit archive approval |

## Research Folder Topology

Planned topology after an approved migration task:

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
    path_truth/
    executable_truth/
    session_edge/
    runtime_health/
    performance/
  sessions/
    YYYY-MM-DD/
```

Current note: most docs still live flat under `docs/research/`. This index links current paths until the move task runs.

## Migration Governance

| Doc | Status | Purpose |
|---|---|---|
| [repository_cleanup_organization_audit.md](repository_cleanup_organization_audit.md) | `ROOT_STAY` | source audit for cleanup/organization state |
| [repository_cleanup_action_plan.md](repository_cleanup_action_plan.md) | `ROOT_STAY` | cleanup policy and staged action sequence |
| [docs_research_migration_map.md](docs_research_migration_map.md) | `ROOT_STAY` | full old path -> target domain map |
| [docs_research_migration_dry_run_validation.md](docs_research_migration_dry_run_validation.md) | `ROOT_STAY` | dry-run validation and move-risk status |
| [research_root_index_design.md](research_root_index_design.md) | `ROOT_STAY` | design source for this index |

Before real moves:

1. approve exact domain batch;
2. create target folders;
3. move one domain at a time;
4. update docs-only references;
5. commit each domain batch separately;
6. archive only in a separate approved task.

## Operator Guidance

- Use this index as a map, not a verdict engine.
- Read source docs before changing any runtime behavior.
- Treat contradictions as research prompts, not implementation permission.
- Keep S3/Growth/live states conservative until executable truth is proven.
- Prefer clean evidence accumulation over policy changes while blockers remain active.

## Final Safety Statement

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Files moved: No

Files renamed: No

Files deleted: No

Code changed: No
