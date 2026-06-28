# QUERY-20260628-REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001

## Metadata

- query_timestamp: 2026-06-28
- graph_version: SNAP-20260627-001
- query_target: REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001
- baseline_commit: ac6da13

## Required Queries

| Query | Status | Finding |
|---|---|---|
| safety_check | DEGRADED | Targets (provisional outcome truth tools) not in seeded graph; no QS findings returned. |
| blast_radius | DEGRADED | Targets not in seeded graph; fallback scope is restricted to moving offline provisional tools to tools/outcome_truth/. |
| evidence_for_commit | DEGRADED | Commit `ac6da13` not in seeded graph; fallback uses git and report evidence. |

## Fallback Evidence

- `git status --short` was clean before the move.
- `git branch -vv` observed `main` at `ac6da13`, ahead of `origin/main` by 171 local commits.
- Bootstrap resolved `REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001` as Class 6, `LOW_RISK_REFACTOR_LOOP`, with safety memory loaded.
- Recent QIE Offline Builder run successfully generated 27 Evidence Units and 1 recommendation from dated logs.

## Contract Attachment

```json
{
  "graph_query_ids": [
    "QUERY-20260628-REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001:safety_check",
    "QUERY-20260628-REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001:blast_radius",
    "QUERY-20260628-REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001:evidence_for_commit"
  ],
  "graph_confidence": 0.4,
  "safety_findings_count": 0,
  "safety_findings": [],
  "affected_nodes_count": 0,
  "affected_edges_count": 0,
  "blast_radius_score": "LOW",
  "recommended_workflow_tier": "LOOP",
  "fallback_required": true,
  "status": "DEGRADED_WITH_FALLBACK",
  "stop_conditions": []
}
```
