# Executable Truth Migration Batch Report

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Batch: `docs/research/executable_truth/`

Mode: docs-only migration. No deletes, renames, archive actions, code changes, runtime changes, strategy changes, risk changes, execution changes, or live changes.

## Summary

Created `docs/research/executable_truth/` and moved only non-ambiguous files mapped to `docs/research/executable_truth/` in `docs/research/docs_research_migration_map.md`.

Filenames were preserved exactly.

Obvious Markdown references using old explicit paths like `docs/research/<executable-truth-file>.md` were updated to `docs/research/executable_truth/<executable-truth-file>.md`.

`docs/research/INDEX.md` was updated so root-index links to moved Executable Truth docs point into `executable_truth/`.

## Moved Files

| Old path | New path |
|---|---|
| `docs/research/capital_ladder_audit.md` | `docs/research/executable_truth/capital_ladder_audit.md` |
| `docs/research/dynamic_executable_expectancy_audit.md` | `docs/research/executable_truth/dynamic_executable_expectancy_audit.md` |
| `docs/research/executable_overlay_phase_a.md` | `docs/research/executable_truth/executable_overlay_phase_a.md` |
| `docs/research/executable_reality_monitor.md` | `docs/research/executable_truth/executable_reality_monitor.md` |
| `docs/research/executable_reality_overlay_design.md` | `docs/research/executable_truth/executable_reality_overlay_design.md` |
| `docs/research/executable_truth_blocker_observatory_design.md` | `docs/research/executable_truth/executable_truth_blocker_observatory_design.md` |
| `docs/research/executable_truth_frontier_map.md` | `docs/research/executable_truth/executable_truth_frontier_map.md` |
| `docs/research/minimum_executable_reality_audit.md` | `docs/research/executable_truth/minimum_executable_reality_audit.md` |
| `docs/research/offline_executable_truth_ledger_audit.md` | `docs/research/executable_truth/offline_executable_truth_ledger_audit.md` |
| `docs/research/paper_sizing_audit.md` | `docs/research/executable_truth/paper_sizing_audit.md` |
| `docs/research/runtime_executable_truth_source_audit.md` | `docs/research/executable_truth/runtime_executable_truth_source_audit.md` |

Moved count: 11

## Skipped Files

Skipped because they are explicitly ambiguous in `docs_research_migration_map.md`:

- `growth_mode_feasibility_audit.md`
- `quote_source_outcome_audit.md`
- `outcome_truth_gap_audit.md`

Other ambiguous docs intentionally skipped:

- `disconfirmation_event_audit.md`
- `opening_scan_harvest_dashboard.md`
- `positive_expectancy_zone_deep_dive.md`
- `quote_lineage_contract_v1.md`
- `fast_stop_loss_audit.md`

All performance, archive, and remaining governance docs stayed in place for later approved batches.

## Reference Updates

Updated obvious docs-only references from:

```text
docs/research/<moved-file>.md
```

to:

```text
docs/research/executable_truth/<moved-file>.md
```

Updated `docs/research/INDEX.md` relative links for moved Executable Truth docs from:

```text
(<moved-file>.md)
```

to:

```text
(executable_truth/<moved-file>.md)
```

Historical migration docs may still describe the pre-migration state by design.

## Validation

| Check | Result |
|---|---|
| `docs/research/executable_truth/` exists | pass |
| moved files present in target folder | 11 / 11 |
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
| `docs/research/growth_mode_feasibility_audit.md` | still at root |
| `docs/research/quote_source_outcome_audit.md` | still at root |
| `docs/research/outcome_truth_gap_audit.md` | still at root |

## Git Status Summary

Expected git status shape after this batch:

- deletes at old flat Executable Truth paths;
- new files under `docs/research/executable_truth/`;
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

Files moved: Yes, docs-only Executable Truth batch

Code changed: No
