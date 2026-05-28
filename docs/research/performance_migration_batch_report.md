# Performance Migration Batch Report

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Batch: `docs/research/performance/`

Mode: docs-only migration. No deletes, renames, archive actions, code changes, runtime changes, strategy changes, risk changes, execution changes, or live changes.

## Summary

Created `docs/research/performance/` and moved only non-ambiguous files mapped to `docs/research/performance/` in `docs/research/docs_research_migration_map.md`.

Filenames were preserved exactly.

Obvious Markdown references using old explicit paths like `docs/research/<performance-file>.md` were updated to `docs/research/performance/<performance-file>.md`.

`docs/research/INDEX.md` was updated so root-index links to moved Performance docs point into `performance/`.

## Moved Files

| Old path | New path |
|---|---|
| `docs/research/research_cockpit_frontend_blueprint_v1.md` | `docs/research/performance/research_cockpit_frontend_blueprint_v1.md` |
| `docs/research/research_cockpit_mounting_spec.md` | `docs/research/performance/research_cockpit_mounting_spec.md` |
| `docs/research/research_cockpit_ui_redesign_v1.md` | `docs/research/performance/research_cockpit_ui_redesign_v1.md` |
| `docs/research/research_cockpit_v2_architecture.md` | `docs/research/performance/research_cockpit_v2_architecture.md` |
| `docs/research/research_cockpit_v2_roadmap.md` | `docs/research/performance/research_cockpit_v2_roadmap.md` |
| `docs/research/runtime_ui_observability_gap_audit.md` | `docs/research/performance/runtime_ui_observability_gap_audit.md` |
| `docs/research/telegram_operator_console_design.md` | `docs/research/performance/telegram_operator_console_design.md` |
| `docs/research/terminal_ui_v2_redesign.md` | `docs/research/performance/terminal_ui_v2_redesign.md` |

Moved count: 8

## Skipped Files

Skipped because it is explicitly ambiguous in `docs_research_migration_map.md`:

- `opening_scan_harvest_dashboard.md`

Other ambiguous docs intentionally skipped:

- `disconfirmation_event_audit.md`
- `positive_expectancy_zone_deep_dive.md`
- `quote_lineage_contract_v1.md`
- `quote_source_outcome_audit.md`
- `growth_mode_feasibility_audit.md`
- `fast_stop_loss_audit.md`
- `outcome_truth_gap_audit.md`

All archive and remaining governance docs stayed in place for later approved batches.

## Reference Updates

Updated obvious docs-only references from:

```text
docs/research/<moved-file>.md
```

to:

```text
docs/research/performance/<moved-file>.md
```

Updated `docs/research/INDEX.md` relative links for moved Performance docs from:

```text
(<moved-file>.md)
```

to:

```text
(performance/<moved-file>.md)
```

Historical migration docs may still describe the pre-migration state by design.

## Validation

| Check | Result |
|---|---|
| `docs/research/performance/` exists | pass |
| moved files present in target folder | 8 / 8 |
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
| `docs/research/opening_scan_harvest_dashboard.md` | still at root |

## Git Status Summary

Expected git status shape after this batch:

- deletes at old flat Performance paths;
- new files under `docs/research/performance/`;
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

Files moved: Yes, docs-only Performance batch

Code changed: No
