# Docs Research Migration Dry Run Validation

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Inputs:

- `docs/research/docs_research_migration_map.md`
- `docs/research/repository_cleanup_action_plan.md`

Mode: docs-only dry run. No files moved, renamed, deleted, archived, or changed outside this validation note.

## Executive Verdict

Verdict: `PASS_WITH_GOVERNANCE_DELTAS`

The proposed `docs/research` migration is mechanically safe enough to proceed to an approval-gated migration task after one preparation step: create a root `docs/research/INDEX.md` or refresh the migration map to include the newly created governance docs.

Core checks passed:

- every mapped source file exists;
- no duplicate source mappings were found;
- no duplicate target paths were found;
- no existing target-file conflicts were found;
- ambiguous docs are explicitly marked;
- active archive candidates are not approved for archive;
- the recommended batch order is conservative.

Known caveat:

- The migration map covers 94 move-table rows. At dry-run time, `docs/research/` contained 95 flat Markdown files because `docs_research_migration_map.md` itself was created after the original scan. This validation document will add one more flat governance doc. These should stay at root temporarily or be added to a future cleanup governance/archive section before any real move.

## Validation Method

Checks performed with read-only PowerShell and `rg` commands:

- parsed `## Full Migration Map` from `docs/research/docs_research_migration_map.md`;
- listed current flat `docs/research/*.md`;
- checked each mapped source against the filesystem;
- computed source and target duplicates;
- checked whether proposed target paths already exist;
- checked whether target folders already exist;
- inspected ambiguous and root-stay sections;
- searched docs references to estimate link/lineage risk.

No runtime data, logs, code, tests, replay outputs, strategy modules, risk modules, execution modules, wallet files, or live config were inspected for migration content.

## Map Coverage

| Check | Result |
|---|---|
| Flat `docs/research/*.md` at dry-run time | 95 |
| Rows in `## Full Migration Map` | 94 |
| Mapped sources that exist | 94 / 94 |
| Missing mapped sources | 0 |
| Duplicate mapped sources | 0 |
| Duplicate target paths | 0 |
| Existing target-file conflicts | 0 |
| Unmapped flat file at dry-run time | `docs_research_migration_map.md` |

Interpretation:

- The 94 mapped files are valid and present.
- `docs_research_migration_map.md` is not in the full move table, but it is justified in the root-stay section of the same document.
- After this validation note is created, `docs_research_migration_dry_run_validation.md` should also be treated as a temporary root-stay governance doc.

## Target Distribution

| Target | Count |
|---|---:|
| `docs/research/session_edge/` | 35 |
| `docs/research/runtime_health/` | 20 |
| `docs/research/executable_truth/` | 14 |
| `docs/research/path_truth/` | 14 |
| `docs/research/performance/` | 9 |
| `docs/research/` | 2 |

The distribution is sensible: `session_edge/` is largest because it owns BTC/NO/02h/09h10h/fast-close research, while `runtime_health/` holds daily runtime, rejection, telemetry, and timestamp observability docs.

## Target Folder Conflicts

| Target folder | Exists now? | Conflict |
|---|---:|---|
| `docs/research/path_truth/` | no | none; folder must be created in a future approved move task |
| `docs/research/executable_truth/` | no | none; folder must be created in a future approved move task |
| `docs/research/session_edge/` | no | none; folder must be created in a future approved move task |
| `docs/research/runtime_health/` | no | none; folder must be created in a future approved move task |
| `docs/research/performance/` | no | none; folder must be created in a future approved move task |
| `docs/research/archive/` | no | none; create only when archive batch is approved |

`docs/research/sessions/` already exists and is intentionally outside this flat-doc migration batch.

## Ambiguous Docs

The migration map marks 8 ambiguous docs and gives review rules for each:

| File | Proposed target | Validation |
|---|---|---|
| `disconfirmation_event_audit.md` | `session_edge/` | clearly marked; acceptable if linked from runtime health where needed |
| `opening_scan_harvest_dashboard.md` | `performance/` | clearly marked; dashboard/UI ownership is reasonable |
| `positive_expectancy_zone_deep_dive.md` | `session_edge/` | clearly marked; cross-link executable truth if used for executable claims |
| `quote_lineage_contract_v1.md` | `runtime_health/` | clearly marked; cross-link path truth |
| `quote_source_outcome_audit.md` | `executable_truth/` | clearly marked; cross-link runtime health |
| `growth_mode_feasibility_audit.md` | `executable_truth/` | clearly marked; Growth Mode remains blocked by executable truth |
| `fast_stop_loss_audit.md` | `session_edge/` | clearly marked; no stop-loss implementation authority |
| `outcome_truth_gap_audit.md` | `executable_truth/` | clearly marked; outcome truth blocks executable claims |

Validation: `PASS`

The ambiguous set is visible enough for an operator to review before a move batch.

## Root-Stay Docs

The map justifies these root-stay docs:

| File | Root-stay reason | Validation |
|---|---|---|
| `repository_cleanup_action_plan.md` | current cleanup policy source | valid |
| `repository_cleanup_organization_audit.md` | source audit for cleanup policy | valid while action plan/map reference it |
| `docs_research_migration_map.md` | migration map itself | valid, but not included in the full move table |

Add this validation note to root-stay governance until the first real migration batch:

- `docs_research_migration_dry_run_validation.md`

Validation: `PASS_WITH_NOTE`

Root-stay docs are justified, but the next migration preparation step should create `docs/research/INDEX.md` and list all root governance docs explicitly.

## Archive Candidate Safety

The migration map does not authorize archiving any file during the first migration pass.

Archive candidate classes are safe because they are conditional only:

| Candidate class | Dry-run status |
|---|---|
| Superseded cleanup docs | not safe yet; cleanup audit is actively referenced by action plan and migration map |
| Superseded design drafts | requires decision-preservation review before archive |
| Completed boot/watch notes | not safe while replay-key/path-truth validation remains active or recently referenced |
| Historical daily health docs | requires index summary before archive |

Validation: `PASS`

No active reference is scheduled for archive. Archive work should remain a separate approval task.

## Link And Lineage Risk

Risk: `MEDIUM`

Reason:

- A targeted reference scan excluding `runtime/`, `logs/`, `logs_vps/`, `backtest_results/`, and `research_cockpit/node_modules/` found many docs references to `docs/research/...` paths.
- High-reference files include `path_truth_multiday_coverage_monitor.md`, `dynamic_executable_expectancy_audit.md`, `minimum_executable_reality_audit.md`, `paper_sizing_audit.md`, `capital_ladder_audit.md`, and `session_09h10h_structural_edge.md`.
- Moving files without reference updates would leave stale links in existing research docs.

Required mitigation:

1. Create `docs/research/INDEX.md` before moving files.
2. Move one domain batch at a time.
3. After each batch, run `rg "docs/research/<old-name>" docs`.
4. Update docs-only references.
5. Keep old path -> new path in the index.
6. Do not rewrite findings or metrics while updating links.

Validation: `PASS_WITH_LINK_UPDATE_REQUIRED`

The link risk is manageable if moves are batched and references are updated immediately after each batch.

## Batch Order Review

Proposed order from the map:

1. create target folder skeleton and `docs/research/INDEX.md`;
2. move `performance/` docs;
3. move `executable_truth/` docs;
4. move `path_truth/` docs;
5. move `session_edge/` docs;
6. move `runtime_health/` docs;
7. archive only after separate approval.

Validation: `PASS`

This order is safe because it starts with lower-risk UI/design docs, consolidates executable blockers before path/session evidence, and leaves active runtime-health docs for last.

Suggested adjustment:

- Before step 1, commit or otherwise account for untracked cleanup governance docs so the move batch does not mix migration validation with unrelated research changes.

## Dry-Run Findings

| Area | Status | Finding |
|---|---|---|
| Mapped source existence | `PASS` | All 94 mapped sources exist. |
| Flat-file coverage | `PASS_WITH_NOTE` | All pre-map files are covered; governance docs created after the map need root-stay treatment. |
| Duplicate source mappings | `PASS` | None found. |
| Duplicate target paths | `PASS` | None found. |
| Target folder conflicts | `PASS` | Target folders do not exist yet; no existing target-file conflicts. |
| Ambiguous docs | `PASS` | 8 docs clearly marked with review rules. |
| Root-stay docs | `PASS_WITH_NOTE` | Justified; add this validation note to root governance handling. |
| Archive candidates | `PASS` | No active reference is approved for archive. |
| Link/lineage risk | `PASS_WITH_LINK_UPDATE_REQUIRED` | Many docs links must be updated after each move batch. |
| Batch order | `PASS` | Conservative and suitable. |

## Approval Gate Before Real Move

Do not move files until an operator explicitly approves a migration task that includes:

- target folder creation;
- `docs/research/INDEX.md` creation;
- exact batch name;
- old path -> new path list for that batch;
- docs-only reference update permission;
- no code/runtime/test move permission unless separately scoped.

## What Not To Do

- Do not move all 94 mapped docs in one commit.
- Do not delete or archive during the first migration.
- Do not move active runtime evidence or logs.
- Do not rewrite research conclusions while updating paths.
- Do not touch strategy, risk, execution, wallet, live config, tests, or runtime JSONL.
- Do not run replay or paper runtime for this migration.

## Final Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Files moved: No

Files renamed: No

Files deleted: No

Code changed: No

Tests run: none; docs-only dry-run validation.
