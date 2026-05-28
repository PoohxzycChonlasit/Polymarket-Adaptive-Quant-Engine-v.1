# Docs Research Migration Map

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Input: `docs/research/repository_cleanup_action_plan.md`

Mode: docs-only migration map. No files moved, renamed, deleted, archived, or changed outside this document.

## Scope

The prior cleanup audit reported 91 flat root research docs. A fresh scan before writing this map found 94 flat Markdown files directly under `docs/research/`, because newer cleanup and runtime docs were added after the audit.

This map covers all 94 currently flat root docs so the later migration task can move documents in controlled batches without orphaning newer files.

## Migration Rules

- Preserve filenames during the first migration pass.
- Preserve chronology through filename, heading, git history, and a root `docs/research/INDEX.md`.
- Do not duplicate full documents between domain folders and `sessions/YYYY-MM-DD/`.
- Move docs in domain batches, not all at once.
- Update references only in docs after moves.
- Do not touch runtime data, logs, code, tests, strategy, risk, execution, wallet, or live config.
- Archive means move to `docs/research/archive/` only after confirming the document is superseded and linked from an index. It does not mean delete.

## Target Folder Meaning

| Folder | Use |
|---|---|
| `docs/research/path_truth/` | Path truth, replay-key, path joins, identity contracts, checkpoint coverage |
| `docs/research/executable_truth/` | Executable truth, MOS, dust, sizing, executable overlays, growth blockers |
| `docs/research/session_edge/` | Session behavior, BTC/NO weakness, 02h/09h10h, fast close, regime/personality |
| `docs/research/runtime_health/` | Runtime state, daily health, no-trade, rejection blockers, timestamp/quote observability, Telegram telemetry |
| `docs/research/performance/` | Research Cockpit, terminal UI, operator console, dashboards, reporting UX |
| `docs/research/archive/` | Superseded or historical docs after index/backlink confirmation |

## Root Docs That Should Stay At Root For Now

These are cross-domain cleanup/governance docs and should remain at `docs/research/` until the first migration batch creates `docs/research/INDEX.md`.

| File | Reason |
|---|---|
| `docs/research/repository_cleanup_action_plan.md` | Current cleanup policy source |
| `docs/research/repository_cleanup_organization_audit.md` | Source audit for cleanup policy |
| `docs/research/docs_research_migration_map.md` | This migration map |

Longer term, keep only `docs/research/INDEX.md` and active governance docs at root. Completed cleanup audits can later move to `docs/research/archive/cleanup/` if that subfolder is approved.

## Full Migration Map

| Current file | Target | Classification | Lineage / caveat |
|---|---|---|---|
| `btc_evidence_watch.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | BTC candidate evidence; keep linked from BTC/session index. |
| `btc_harvest_window_monitor.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | BTC harvest/session monitoring lineage. |
| `btc_run_schedule.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | BTC window plan; review if still active before archiving later. |
| `btc_session_intelligence.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | BTC session intelligence. |
| `capital_ladder_audit.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Sizing/executable-capital blocker lineage. |
| `daily_runtime_path_truth_audit.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Daily runtime audit with path truth growth; cross-link from path truth index. |
| `delta_extreme_gate_audit.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | No-trade blocker/root-cause lineage. |
| `disconfirmation_event_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Signal/session disconfirmation evidence; ambiguous with runtime health but session edge is stronger. |
| `dynamic_executable_expectancy_audit.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Executable threshold/expectancy lineage. |
| `early_research_gate_review.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Path truth early gate summary; cross-link session candidates. |
| `epoch_timing_outcome_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Timing/session outcome analysis. |
| `executable_overlay_phase_a.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Executable overlay design. |
| `executable_reality_monitor.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Executable reality monitoring. |
| `executable_reality_overlay_design.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Executable overlay design lineage. |
| `executable_truth_blocker_observatory_design.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Current blocker observatory design. |
| `executable_truth_frontier_map.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Current executable frontier source. |
| `execution_reality_daily_monitor.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Runtime execution observability monitor; cross-link executable truth. |
| `execution_timestamp_contract_v1.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Timestamp observability contract; keep contract name unchanged. |
| `failure_triangle_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | BTC/NO/ACTIVE interaction lineage. |
| `fast_close_distribution_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Fast close/session structure evidence. |
| `fast_stop_loss_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Stop-loss outcome behavior audit; no strategy authorization. |
| `full_day_regime_audit_2026_05_23.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Date-specific regime doc; optionally link from `sessions/2026-05-23/`. |
| `growth_mode_feasibility_audit.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Growth readiness depends on executable truth. |
| `hourly_market_personality_map.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Session/hour personality map. |
| `lifecycle_timestamp_coverage_audit.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Timestamp/observability coverage. |
| `minimum_executable_reality_audit.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Minimum executable blocker source. |
| `morning_replay_key_runtime_audit.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Recent replay-key runtime audit; keep hot until validation closes. |
| `morning_runtime_health_check.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Runtime health audit. |
| `new_day_runtime_gate_audit.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Runtime/gate daily health. |
| `new_day_runtime_state_audit.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Runtime/research daily state. |
| `no_side_weakness_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | NO side weakness lineage. |
| `no_trade_open_runtime_audit.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | No-trade runtime root-cause entry. |
| `offline_executable_truth_ledger_audit.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Offline ledger audit source. |
| `opening_scan_disconfirmation_monitor.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Opening scan/session evidence. |
| `opening_scan_harvest_dashboard.md` | `docs/research/performance/` | `MOVE_CANDIDATE` | Dashboard/reporting surface for opening scan evidence. |
| `opening_scan_policy_candidate_design.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Policy design only; no runtime authorization. |
| `opening_scan_policy_evidence_monitor.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Opening scan evidence monitoring. |
| `opening_scan_policy_replay_feasibility_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Replay feasibility for opening scan; no replay output moved. |
| `opening_scan_survival_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Opening scan survival evidence. |
| `outcome_truth_gap_audit.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Outcome truth blocks executable claims. |
| `paper_process_cleanup_audit.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Process cleanup audit, docs-only evidence. |
| `paper_runtime_replay_key_boot.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Runtime boot record for replay-key validation. |
| `paper_sizing_audit.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Sizing/dust/executable blocker lineage. |
| `path_join_root_cause_map.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Canonical PATH_JOIN_0_77 root-cause map. |
| `path_truth_checkpoint_validation.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Path truth checkpoint validation. |
| `path_truth_field_coverage_gap_audit.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Path truth field coverage. |
| `path_truth_gate_revision.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Gate policy. |
| `path_truth_identity_wiring_spec.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Identity wiring spec. |
| `path_truth_implementation_spec.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Path truth implementation spec. |
| `path_truth_multiday_coverage_monitor.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Active gate monitor; keep hot during migration. |
| `path_truth_observability_design.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Path truth observability design. |
| `path_truth_replay_key_live_validation.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Recent validation; keep hot until closed. |
| `path_truth_replay_key_wiring_validation.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Replay-key wiring validation. |
| `positive_expectancy_zone_deep_dive.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Performance/session hypothesis; cross-link executable truth if needed. |
| `post_alignment_runtime_health.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Runtime health state after alignment. |
| `quote_lineage_contract_v1.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Quote lineage observability contract; cross-link path truth. |
| `quote_source_outcome_audit.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Quote source/outcome affects executable truth; ambiguous with runtime health. |
| `regime_exception_09h_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | 09h session/regime exception. |
| `regime_split_next_hypothesis.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Regime/session hypothesis. |
| `replay_join_key_contract.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Join-key identity contract. |
| `replay_key_validation_after_trade.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Replay-key validation lineage. |
| `repository_cleanup_action_plan.md` | `docs/research/` | `STAY_ROOT_FOR_NOW` | Current cleanup governance; archive later only after migration completes. |
| `repository_cleanup_organization_audit.md` | `docs/research/` | `STAY_ROOT_FOR_NOW` | Source cleanup audit; archive later only after action plan is stable. |
| `research_cockpit_frontend_blueprint_v1.md` | `docs/research/performance/` | `MOVE_CANDIDATE` | Research Cockpit/frontend. |
| `research_cockpit_mounting_spec.md` | `docs/research/performance/` | `MOVE_CANDIDATE` | Runtime UI mounting spec. |
| `research_cockpit_ui_redesign_v1.md` | `docs/research/performance/` | `MOVE_CANDIDATE` | UI redesign audit. |
| `research_cockpit_v2_architecture.md` | `docs/research/performance/` | `MOVE_CANDIDATE` | Cockpit architecture. |
| `research_cockpit_v2_roadmap.md` | `docs/research/performance/` | `MOVE_CANDIDATE` | Cockpit roadmap/dependencies. |
| `runtime_evidence_farming_audit.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Runtime evidence farming health. |
| `runtime_executable_truth_source_audit.md` | `docs/research/executable_truth/` | `MOVE_CANDIDATE` | Executable truth source audit. |
| `runtime_replay_key_blocker_audit.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Replay-key blocker runtime audit; keep hot until validation closes. |
| `runtime_ui_observability_gap_audit.md` | `docs/research/performance/` | `MOVE_CANDIDATE` | Runtime UI gap audit. |
| `session_02h_fast_sl_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | 02h hostile candidate lineage. |
| `session_02h_multiday_validation.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | 02h multiday validation. |
| `session_09h10h_btc_strength_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | 09h10h BTC strength. |
| `session_09h10h_early_failure_filter_design.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Design-only session filter, no strategy authorization. |
| `session_09h10h_early_failure_replay_test_plan.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Replay test plan, no replay execution. |
| `session_09h10h_failure_escape_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | 09h10h failure triangle escape. |
| `session_09h10h_structural_edge.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | 09h10h structural edge. |
| `session_09h10h_truth_layer_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | 09h10h truth layer. |
| `session_edge_missing_split_refresh.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Session edge split refresh. |
| `session_edge_outside_control_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Outside control audit. |
| `session_personality_stability.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Session personality stability. |
| `session_pressure_comparison_audit.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Session pressure comparison. |
| `session_regime_09h_recurrence.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | 09h recurrence. |
| `session_regime_09h10h_persistence.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | 09h10h persistence. |
| `session_survival_ranking.md` | `docs/research/session_edge/` | `MOVE_CANDIDATE` | Session survival ranking. |
| `signal_rejection_root_cause_audit.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | No-trade rejection root cause. |
| `single_run_path_truth_audit.md` | `docs/research/path_truth/` | `MOVE_CANDIDATE` | Single-run path truth audit. |
| `telegram_operator_console_design.md` | `docs/research/performance/` | `MOVE_CANDIDATE` | Operator console UI/design. |
| `telegram_route_telemetry_design.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Telegram telemetry routing observability. |
| `telegram_routing_telemetry_audit.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Telegram telemetry audit. |
| `telegram_telemetry_validation.md` | `docs/research/runtime_health/` | `MOVE_CANDIDATE` | Telegram telemetry validation. |
| `terminal_ui_v2_redesign.md` | `docs/research/performance/` | `MOVE_CANDIDATE` | Terminal UI design. |

## Ambiguous Docs Requiring Review Before Move

| File | Proposed target | Why ambiguous | Review rule |
|---|---|---|---|
| `disconfirmation_event_audit.md` | `session_edge/` | Could also be runtime rejection evidence | Move to session edge if it analyzes candidate behavior; runtime health if primarily incident/root-cause. |
| `opening_scan_harvest_dashboard.md` | `performance/` | Opening scan domain plus dashboard surface | Move to performance because it is a UI/dashboard doc; link from session edge. |
| `positive_expectancy_zone_deep_dive.md` | `session_edge/` | Could be performance or executable truth | Move to session edge unless it claims executable PnL; then cross-link executable truth. |
| `quote_lineage_contract_v1.md` | `runtime_health/` | Could be path truth identity contract | Move to runtime health as observability contract; cross-link path truth. |
| `quote_source_outcome_audit.md` | `executable_truth/` | Could be runtime quote observability | Move to executable truth because quote source affects executable outcome claims. |
| `growth_mode_feasibility_audit.md` | `executable_truth/` | Could be performance/growth roadmap | Keep under executable truth because Growth Mode remains blocked by executable truth. |
| `fast_stop_loss_audit.md` | `session_edge/` | Could be strategy/risk sensitive | Move as research only; do not treat as stop-loss implementation authorization. |
| `outcome_truth_gap_audit.md` | `executable_truth/` | Could be path truth or performance | Move to executable truth because outcome truth is a blocker for executable claims. |

## Archive Candidates

No document should be archived during the first migration pass unless the operator approves a specific archive batch.

Candidate archive classes:

| Candidate class | Examples | Requirement before archive |
|---|---|---|
| Superseded cleanup docs | `repository_cleanup_organization_audit.md` after action plan/map stabilize | Must be linked from `INDEX.md` and cleanup report |
| Superseded design drafts | older Cockpit/UI drafts if replaced by newer blueprint/spec | Must verify newer doc preserves decisions |
| Completed boot/watch notes | replay-key boot/watch docs after validation closes | Must preserve run_id lineage in path truth index |
| Historical daily health docs | morning/new-day docs after summarized by a weekly/monthly index | Must preserve date/run references |

Suggested future archive subfolders if approved:

```text
docs/research/archive/cleanup/
docs/research/archive/performance/
docs/research/archive/runtime_health/
docs/research/archive/session_edge/
```

## Chronology And Lineage Preservation

Before moving any doc:

1. Generate `docs/research/INDEX.md` with old path, new path, title, domain, date if inferable, and status.
2. Move files without renaming in the first pass.
3. Use one commit per domain batch.
4. Run `rg "docs/research/<old-name>"` after each batch and update docs-only references.
5. Keep active monitors hot and linked:
   - `path_truth_multiday_coverage_monitor.md`
   - `path_truth_replay_key_live_validation.md`
   - `morning_replay_key_runtime_audit.md`
   - `runtime_replay_key_blocker_audit.md`
6. For date-specific docs, keep canonical content in the domain folder and add only links from `docs/research/sessions/YYYY-MM-DD/` if needed.
7. Do not rewrite findings, conclusions, or metric values during migration.

## Recommended Batch Order

1. Create target folder skeleton and `docs/research/INDEX.md`.
2. Move `performance/` docs first. They are low runtime-risk and mostly design/UI.
3. Move `executable_truth/` docs second. This consolidates Growth Mode blockers.
4. Move `path_truth/` docs third, but keep active validation docs hot and index-linked.
5. Move `session_edge/` docs fourth, because they have the most cross-links and candidate lineage.
6. Move `runtime_health/` docs last, after active run/replay-key validation tasks close.
7. Archive only after a separate approval task.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Files moved: No

Files deleted: No

Code changed: No

Tests run: none; docs-only migration map.
