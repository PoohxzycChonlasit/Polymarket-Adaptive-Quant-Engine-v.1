# Root Governance And Ambiguous Docs Audit

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Mode: docs-only audit. No files moved, renamed, deleted, archived, or changed outside this document.

## Executive Verdict

Remaining flat root docs are expected after migration batches 1-5.

They fall into three practical groups:

- root governance docs that should remain discoverable at `docs/research/`;
- ambiguous cross-domain docs that require operator/domain review before a later move;
- migration batch reports that should eventually archive after migration closes.

No remaining flat doc should be deleted. No file should move until a separate approved migration or archive task names it.

## Counts

| Metric | Count |
|---|---:|
| Remaining flat `docs/research/*.md` before this audit | 19 |
| Classified docs in this audit | 19 |
| `GOVERNANCE_ROOT` | 6 |
| `AMBIGUOUS_REVIEW_REQUIRED` | 8 |
| `FUTURE_ARCHIVE` | 5 |
| `FUTURE_DOMAIN_MOVE` | 0 |
| `KEEP_AT_ROOT` | 0 |
| Duplicate classifications | 0 |

This audit itself adds one new flat governance doc:

- `root_governance_ambiguous_audit.md`

After creation, the flat root count becomes 20 unless/until it is committed or later archived with the other migration governance docs.

## Classification Table

| File | Classification | Why it still exists at root | Proposed next action |
|---|---|---|---|
| `INDEX.md` | `GOVERNANCE_ROOT` | Root navigation index; intended permanent entry point. | Keep at root. |
| `docs_research_migration_map.md` | `GOVERNANCE_ROOT` | Source migration map used by all batches. | Keep at root until migration completes; later archive only with replacement lineage. |
| `docs_research_migration_dry_run_validation.md` | `GOVERNANCE_ROOT` | Validated migration plan before moves began. | Keep at root until migration closes; later archive with migration package. |
| `repository_cleanup_action_plan.md` | `GOVERNANCE_ROOT` | Current cleanup and archive policy source. | Keep at root until cleanup program closes. |
| `repository_cleanup_organization_audit.md` | `GOVERNANCE_ROOT` | Source audit for cleanup action plan. | Keep at root until action plan/index supersede it. |
| `research_root_index_design.md` | `GOVERNANCE_ROOT` | Design source for `INDEX.md`. | Keep at root until `INDEX.md` is stable; later archive. |
| `disconfirmation_event_audit.md` | `AMBIGUOUS_REVIEW_REQUIRED` | Could belong to `session_edge/` if candidate behavior focused, or `runtime_health/` if incident/root-cause focused. | Review content before domain move. |
| `fast_stop_loss_audit.md` | `AMBIGUOUS_REVIEW_REQUIRED` | Session outcome evidence but stop-loss wording is strategy/risk sensitive. | Review before moving; likely `session_edge/` with safety caveat. |
| `growth_mode_feasibility_audit.md` | `AMBIGUOUS_REVIEW_REQUIRED` | Growth readiness, executable truth, sizing, and performance roadmap overlap. | Review before moving; likely `executable_truth/` if it remains blocker-focused. |
| `opening_scan_harvest_dashboard.md` | `AMBIGUOUS_REVIEW_REQUIRED` | Opening scan domain plus dashboard/performance surface. | Review before moving; likely `performance/` if UI/reporting focused. |
| `outcome_truth_gap_audit.md` | `AMBIGUOUS_REVIEW_REQUIRED` | Could belong to `executable_truth/`, `path_truth/`, or performance depending on emphasis. | Review before moving; likely `executable_truth/` if blocker-focused. |
| `positive_expectancy_zone_deep_dive.md` | `AMBIGUOUS_REVIEW_REQUIRED` | Session-edge hypothesis but may feed executable/performance claims. | Review before moving; likely `session_edge/` with executable caveat. |
| `quote_lineage_contract_v1.md` | `AMBIGUOUS_REVIEW_REQUIRED` | Runtime-health observability contract with path-truth identity implications. | Review before moving; likely `runtime_health/` or `path_truth/`. |
| `quote_source_outcome_audit.md` | `AMBIGUOUS_REVIEW_REQUIRED` | Quote source impacts runtime health and executable truth. | Review before moving; likely `executable_truth/` if outcome claim-focused. |
| `path_truth_migration_batch_report.md` | `FUTURE_ARCHIVE` | Batch report for completed Path Truth migration; kept root-visible during migration program. | Archive to `docs/research/archive/cleanup/` only after all migration batches close. |
| `runtime_health_migration_batch_report.md` | `FUTURE_ARCHIVE` | Batch report for completed Runtime Health migration. | Archive later with migration package. |
| `session_edge_migration_batch_report.md` | `FUTURE_ARCHIVE` | Batch report for completed Session Edge migration. | Archive later with migration package. |
| `executable_truth_migration_batch_report.md` | `FUTURE_ARCHIVE` | Batch report for completed Executable Truth migration. | Archive later with migration package. |
| `performance_migration_batch_report.md` | `FUTURE_ARCHIVE` | Batch report for completed Performance migration. | Archive later with migration package. |

## Proposed Final Root Governance Set

Final steady-state root should be small:

| File | Final root status |
|---|---|
| `INDEX.md` | keep permanently |
| `repository_cleanup_action_plan.md` | keep while cleanup/archive program is active |
| `docs_research_migration_map.md` | keep until all migration references are stable |
| `root_governance_ambiguous_audit.md` | keep until ambiguous docs are resolved |

Likely archive after migration closes:

- `docs_research_migration_dry_run_validation.md`
- `research_root_index_design.md`
- `repository_cleanup_organization_audit.md`
- all `*_migration_batch_report.md`

Archive means preserve under `docs/research/archive/cleanup/`, not delete.

## Unresolved Ambiguity

| Ambiguous doc | Competing domains | Review question |
|---|---|---|
| `disconfirmation_event_audit.md` | `session_edge/`, `runtime_health/` | Is the doc mostly about market/session candidate behavior or runtime rejection/incidents? |
| `fast_stop_loss_audit.md` | `session_edge/`, `runtime_health/`, future risk archive | Does it remain research-only outcome evidence, or does it contain risk-policy language that needs extra caveats? |
| `growth_mode_feasibility_audit.md` | `executable_truth/`, `performance/` | Is it primarily Growth Mode blocker evidence or broader performance roadmap? |
| `opening_scan_harvest_dashboard.md` | `performance/`, `session_edge/` | Is the durable value the dashboard/reporting surface or opening-scan session evidence? |
| `outcome_truth_gap_audit.md` | `executable_truth/`, `path_truth/`, `runtime_health/` | Which truth gap dominates: executable, path continuity, or runtime observability? |
| `positive_expectancy_zone_deep_dive.md` | `session_edge/`, `executable_truth/`, `performance/` | Does it assert only signal/session hypothesis, or does it support executable/performance claims? |
| `quote_lineage_contract_v1.md` | `runtime_health/`, `path_truth/` | Is quote lineage a runtime observability contract or identity/path truth contract? |
| `quote_source_outcome_audit.md` | `executable_truth/`, `runtime_health/` | Is the conclusion about executable outcome truth or runtime quote-source health? |

## Cross-Domain Docs

| File | Cross-domain reason |
|---|---|
| `growth_mode_feasibility_audit.md` | Growth readiness depends on executable truth, sizing, performance, and risk state. |
| `outcome_truth_gap_audit.md` | Outcome truth can touch path truth, runtime health, and executable truth. |
| `positive_expectancy_zone_deep_dive.md` | Positive expectancy is session/performance language but executable truth remains blocked. |
| `quote_lineage_contract_v1.md` | Quote lineage is runtime observability plus identity lineage. |
| `quote_source_outcome_audit.md` | Quote source affects runtime quality and executable outcome claims. |
| `opening_scan_harvest_dashboard.md` | Opening-scan research plus dashboard/operator visibility. |

## Docs That Should Never Move Casually

| File | Reason |
|---|---|
| `INDEX.md` | Root entry point. Moving it breaks the intended navigation contract. |
| `repository_cleanup_action_plan.md` | Active cleanup policy source until cleanup program closes. |
| `docs_research_migration_map.md` | Active migration lineage source until all migration batches and references are stable. |
| `root_governance_ambiguous_audit.md` | Current unresolved-root review record after this task. |

No research doc should be deleted during this cleanup program.

## Recommended Next Step

Run a separate ambiguous-doc resolution task before any further move:

1. inspect the 8 ambiguous docs;
2. choose exactly one final domain for each;
3. update `INDEX.md`;
4. move in one small approved batch;
5. create a dedicated ambiguous-doc resolution report.

Do not archive batch reports until all domain moves and ambiguous reviews close.

## Validation

| Check | Result |
|---|---|
| remaining flat docs before audit | 19 |
| classifications assigned | 19 |
| duplicate classifications | 0 |
| ambiguous docs counted | 8 |
| governance docs counted | 6 |
| future archive docs counted | 5 |
| future domain move docs counted | 0 |
| keep-at-root docs counted | 0 |

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Files moved: No

Files renamed: No

Files deleted: No

Code changed: No
