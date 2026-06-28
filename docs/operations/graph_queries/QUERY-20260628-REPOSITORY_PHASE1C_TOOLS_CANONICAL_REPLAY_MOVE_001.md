# QUERY-20260628-REPOSITORY_PHASE1C_TOOLS_CANONICAL_REPLAY_MOVE_001

## Metadata

- query_timestamp: 2026-06-28
- graph_version: SNAP-20260627-001
- query_target: REPOSITORY_PHASE1C_TOOLS_CANONICAL_REPLAY_MOVE_001
- baseline_commit: 67b0b4c

## Required Queries

| Query | Status | Finding |
|---|---|---|
| safety_check | DEGRADED | Targets not in seeded graph; no QS findings returned. |
| blast_radius | DEGRADED | Targets not in seeded graph; fallback scope is restricted to moving canonical_regime_export.py and runtime_event_replay.py. |
| evidence_for_commit | DEGRADED | Commit `67b0b4c` not in seeded graph; fallback uses git and report evidence. |

## Fallback Evidence

- `git status --short` was clean before the move.
- `git branch -vv` observed `main` at `67b0b4c`, ahead of `origin/main` by 7 local commits.
- Bootstrap resolved `REPOSITORY_PHASE1C_TOOLS_CANONICAL_REPLAY_MOVE_001` as Class 6, `LOW_RISK_REFACTOR_LOOP`, with safety memory loaded.
- `docs/reports/REPOSITORY_PHASE1C_TOOLS_CANONICAL_REPLAY_MOVE_PLAN_001.md` verified that both tools have zero cross-imports from other tools.

## Contract Attachment

```json
{
  "graph_query_ids": [
    "QUERY-20260628-REPOSITORY_PHASE1C_TOOLS_CANONICAL_REPLAY_MOVE_001:safety_check",
    "QUERY-20260628-REPOSITORY_PHASE1C_TOOLS_CANONICAL_REPLAY_MOVE_001:blast_radius",
    "QUERY-20260628-REPOSITORY_PHASE1C_TOOLS_CANONICAL_REPLAY_MOVE_001:evidence_for_commit"
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
