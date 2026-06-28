# QUERY-20260628-REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001

## Metadata

- query_timestamp: 2026-06-28
- graph_version: SNAP-20260627-001
- query_target: REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001
- baseline_commit: c5fc3aa

## Required Queries

| Query | Status | Finding |
|---|---|---|
| safety_check | DEGRADED | Target not in seeded graph; no QS findings returned. |
| blast_radius | DEGRADED | Target not in seeded graph; fallback scope is a one-file offline tool move. |
| evidence_for_commit | DEGRADED | Commit `c5fc3aa` not in seeded graph; fallback uses git and report evidence. |

## Fallback Evidence

- `git status --short` was clean before the move.
- `git branch -vv` observed `main` at `c5fc3aa`, ahead of `origin/main` by 2 local commits.
- Bootstrap resolved `REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001` as Class 6, `LOW_RISK_REFACTOR_LOOP`, with safety memory loaded.
- `docs/reports/REPOSITORY_PHASE1_TOOLS_AUDIT_REORGANIZATION_001.md` identified `tools/silent_zone_selection_probe.py` as the only `NO_IMPORT_RISK` root tool.

## Contract Attachment

```json
{
  "graph_query_ids": [
    "QUERY-20260628-REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001:safety_check",
    "QUERY-20260628-REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001:blast_radius",
    "QUERY-20260628-REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001:evidence_for_commit"
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
