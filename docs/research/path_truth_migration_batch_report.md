# Path Truth Migration Batch Report

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Batch: `docs/research/path_truth/`

Mode: docs-only migration. No deletes, renames, archive actions, code changes, runtime changes, strategy changes, risk changes, execution changes, or live changes.

## Summary

Created `docs/research/path_truth/` and moved only the files mapped to `docs/research/path_truth/` in `docs/research/docs_research_migration_map.md`.

Filenames were preserved exactly.

Obvious Markdown references using old explicit paths like `docs/research/<path-truth-file>.md` were updated to `docs/research/path_truth/<path-truth-file>.md`.

`docs/research/INDEX.md` was updated so root-index links to moved Path Truth docs point into `path_truth/`.

## Moved Files

| Old path | New path |
|---|---|
| `docs/research/early_research_gate_review.md` | `docs/research/path_truth/early_research_gate_review.md` |
| `docs/research/path_join_root_cause_map.md` | `docs/research/path_truth/path_join_root_cause_map.md` |
| `docs/research/path_truth_checkpoint_validation.md` | `docs/research/path_truth/path_truth_checkpoint_validation.md` |
| `docs/research/path_truth_field_coverage_gap_audit.md` | `docs/research/path_truth/path_truth_field_coverage_gap_audit.md` |
| `docs/research/path_truth_gate_revision.md` | `docs/research/path_truth/path_truth_gate_revision.md` |
| `docs/research/path_truth_identity_wiring_spec.md` | `docs/research/path_truth/path_truth_identity_wiring_spec.md` |
| `docs/research/path_truth_implementation_spec.md` | `docs/research/path_truth/path_truth_implementation_spec.md` |
| `docs/research/path_truth_multiday_coverage_monitor.md` | `docs/research/path_truth/path_truth_multiday_coverage_monitor.md` |
| `docs/research/path_truth_observability_design.md` | `docs/research/path_truth/path_truth_observability_design.md` |
| `docs/research/path_truth_replay_key_live_validation.md` | `docs/research/path_truth/path_truth_replay_key_live_validation.md` |
| `docs/research/path_truth_replay_key_wiring_validation.md` | `docs/research/path_truth/path_truth_replay_key_wiring_validation.md` |
| `docs/research/replay_join_key_contract.md` | `docs/research/path_truth/replay_join_key_contract.md` |
| `docs/research/replay_key_validation_after_trade.md` | `docs/research/path_truth/replay_key_validation_after_trade.md` |
| `docs/research/single_run_path_truth_audit.md` | `docs/research/path_truth/single_run_path_truth_audit.md` |

Moved count: 14

## Skipped Files

No ambiguous docs were moved.

Ambiguous docs intentionally skipped:

- `disconfirmation_event_audit.md`
- `opening_scan_harvest_dashboard.md`
- `positive_expectancy_zone_deep_dive.md`
- `quote_lineage_contract_v1.md`
- `quote_source_outcome_audit.md`
- `growth_mode_feasibility_audit.md`
- `fast_stop_loss_audit.md`
- `outcome_truth_gap_audit.md`

Governance docs intentionally stayed at root:

- `INDEX.md`
- `repository_cleanup_action_plan.md`
- `repository_cleanup_organization_audit.md`
- `docs_research_migration_map.md`
- `docs_research_migration_dry_run_validation.md`
- `research_root_index_design.md`
- `path_truth_migration_batch_report.md`

All executable truth, session edge, runtime health, performance, archive, and session docs remain unmoved for later approved batches.

## Reference Updates

Updated obvious docs-only references from:

```text
docs/research/<moved-file>.md
```

to:

```text
docs/research/path_truth/<moved-file>.md
```

Updated `docs/research/INDEX.md` relative links for moved Path Truth docs from:

```text
(<moved-file>.md)
```

to:

```text
(path_truth/<moved-file>.md)
```

Historical migration docs may still describe the pre-migration state by design.

## Validation

| Check | Result |
|---|---|
| `docs/research/path_truth/` exists | pass |
| moved files present in target folder | 14 / 14 |
| moved files still present at old root path | 0 |
| duplicate target filenames | 0 |
| stale old explicit `docs/research/<moved-file>.md` references outside migration lineage/report text | 0 found after update |
| ambiguous docs moved | 0 |
| deletes performed | 0 |
| renames performed | 0 |
| archives performed | 0 |
| code/runtime files touched | 0 intended |

## Git Status Notes

Expected git status shape after this batch:

- deletes at old flat paths;
- new files under `docs/research/path_truth/`;
- docs-only modifications where references were updated;
- new batch report.

No code, runtime, strategy, risk, execution, wallet, live config, tests, logs, or JSONL files should appear in this batch.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Files deleted: No

Files renamed: No

Files moved: Yes, docs-only Path Truth batch

Code changed: No
