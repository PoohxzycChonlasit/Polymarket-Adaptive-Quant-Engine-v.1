# Session Edge Migration Batch Report

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Batch: `docs/research/session_edge/`

Mode: docs-only migration. No deletes, renames, archive actions, code changes, runtime changes, strategy changes, risk changes, execution changes, or live changes.

## Summary

Created `docs/research/session_edge/` and moved only non-ambiguous files mapped to `docs/research/session_edge/` in `docs/research/docs_research_migration_map.md`.

Filenames were preserved exactly.

Obvious Markdown references using old explicit paths like `docs/research/<session-edge-file>.md` were updated to `docs/research/session_edge/<session-edge-file>.md`.

`docs/research/INDEX.md` was updated so root-index links to moved Session Edge docs point into `session_edge/`.

## Moved Files

| Old path | New path |
|---|---|
| `docs/research/btc_evidence_watch.md` | `docs/research/session_edge/btc_evidence_watch.md` |
| `docs/research/btc_harvest_window_monitor.md` | `docs/research/session_edge/btc_harvest_window_monitor.md` |
| `docs/research/btc_run_schedule.md` | `docs/research/session_edge/btc_run_schedule.md` |
| `docs/research/btc_session_intelligence.md` | `docs/research/session_edge/btc_session_intelligence.md` |
| `docs/research/epoch_timing_outcome_audit.md` | `docs/research/session_edge/epoch_timing_outcome_audit.md` |
| `docs/research/failure_triangle_audit.md` | `docs/research/session_edge/failure_triangle_audit.md` |
| `docs/research/fast_close_distribution_audit.md` | `docs/research/session_edge/fast_close_distribution_audit.md` |
| `docs/research/full_day_regime_audit_2026_05_23.md` | `docs/research/session_edge/full_day_regime_audit_2026_05_23.md` |
| `docs/research/hourly_market_personality_map.md` | `docs/research/session_edge/hourly_market_personality_map.md` |
| `docs/research/no_side_weakness_audit.md` | `docs/research/session_edge/no_side_weakness_audit.md` |
| `docs/research/opening_scan_disconfirmation_monitor.md` | `docs/research/session_edge/opening_scan_disconfirmation_monitor.md` |
| `docs/research/opening_scan_policy_candidate_design.md` | `docs/research/session_edge/opening_scan_policy_candidate_design.md` |
| `docs/research/opening_scan_policy_evidence_monitor.md` | `docs/research/session_edge/opening_scan_policy_evidence_monitor.md` |
| `docs/research/opening_scan_policy_replay_feasibility_audit.md` | `docs/research/session_edge/opening_scan_policy_replay_feasibility_audit.md` |
| `docs/research/opening_scan_survival_audit.md` | `docs/research/session_edge/opening_scan_survival_audit.md` |
| `docs/research/regime_exception_09h_audit.md` | `docs/research/session_edge/regime_exception_09h_audit.md` |
| `docs/research/regime_split_next_hypothesis.md` | `docs/research/session_edge/regime_split_next_hypothesis.md` |
| `docs/research/session_02h_fast_sl_audit.md` | `docs/research/session_edge/session_02h_fast_sl_audit.md` |
| `docs/research/session_02h_multiday_validation.md` | `docs/research/session_edge/session_02h_multiday_validation.md` |
| `docs/research/session_09h10h_btc_strength_audit.md` | `docs/research/session_edge/session_09h10h_btc_strength_audit.md` |
| `docs/research/session_09h10h_early_failure_filter_design.md` | `docs/research/session_edge/session_09h10h_early_failure_filter_design.md` |
| `docs/research/session_09h10h_early_failure_replay_test_plan.md` | `docs/research/session_edge/session_09h10h_early_failure_replay_test_plan.md` |
| `docs/research/session_09h10h_failure_escape_audit.md` | `docs/research/session_edge/session_09h10h_failure_escape_audit.md` |
| `docs/research/session_09h10h_structural_edge.md` | `docs/research/session_edge/session_09h10h_structural_edge.md` |
| `docs/research/session_09h10h_truth_layer_audit.md` | `docs/research/session_edge/session_09h10h_truth_layer_audit.md` |
| `docs/research/session_edge_missing_split_refresh.md` | `docs/research/session_edge/session_edge_missing_split_refresh.md` |
| `docs/research/session_edge_outside_control_audit.md` | `docs/research/session_edge/session_edge_outside_control_audit.md` |
| `docs/research/session_personality_stability.md` | `docs/research/session_edge/session_personality_stability.md` |
| `docs/research/session_pressure_comparison_audit.md` | `docs/research/session_edge/session_pressure_comparison_audit.md` |
| `docs/research/session_regime_09h_recurrence.md` | `docs/research/session_edge/session_regime_09h_recurrence.md` |
| `docs/research/session_regime_09h10h_persistence.md` | `docs/research/session_edge/session_regime_09h10h_persistence.md` |
| `docs/research/session_survival_ranking.md` | `docs/research/session_edge/session_survival_ranking.md` |

Moved count: 32

## Skipped Files

Skipped because they are explicitly ambiguous in `docs_research_migration_map.md`:

- `disconfirmation_event_audit.md`
- `positive_expectancy_zone_deep_dive.md`
- `fast_stop_loss_audit.md`

Other ambiguous docs intentionally skipped:

- `opening_scan_harvest_dashboard.md`
- `quote_lineage_contract_v1.md`
- `quote_source_outcome_audit.md`
- `growth_mode_feasibility_audit.md`
- `outcome_truth_gap_audit.md`

All executable truth, performance, archive, and remaining governance docs stayed in place for later approved batches.

## Reference Updates

Updated obvious docs-only references from:

```text
docs/research/<moved-file>.md
```

to:

```text
docs/research/session_edge/<moved-file>.md
```

Updated `docs/research/INDEX.md` relative links for moved Session Edge docs from:

```text
(<moved-file>.md)
```

to:

```text
(session_edge/<moved-file>.md)
```

Historical migration docs may still describe the pre-migration state by design.

## Validation

| Check | Result |
|---|---|
| `docs/research/session_edge/` exists | pass |
| moved files present in target folder | 32 / 32 |
| moved files still present at old root path | 0 |
| duplicate target filenames | 0 |
| stale old explicit `docs/research/<moved-file>.md` references outside migration report text | 0 found after update |
| ambiguous docs moved | 0 |
| deletes performed | 0 |
| renames performed | 0 |
| archives performed | 0 |
| code/runtime files touched | 0 intended |

## Ambiguous Docs Status

| File | Status |
|---|---|
| `docs/research/disconfirmation_event_audit.md` | still at root |
| `docs/research/positive_expectancy_zone_deep_dive.md` | still at root |
| `docs/research/fast_stop_loss_audit.md` | still at root |

## Git Status Summary

Expected git status shape after this batch:

- deletes at old flat Session Edge paths;
- new files under `docs/research/session_edge/`;
- docs-only modifications where references were updated;
- `docs/research/INDEX.md` updated;
- new batch report.

No code, runtime, strategy, risk, execution, wallet, live config, tests, logs, or JSONL files should appear in this batch.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Files deleted: No

Files renamed: No

Files moved: Yes, docs-only Session Edge batch

Code changed: No
