# QUERY-20260628-REPOSITORY_PHASE0_ROOT_CLEANUP_001

## Metadata

- query_timestamp: 2026-06-28
- graph_version: SNAP-20260627-001
- graph_files_read:
  - docs/operations/knowledge_graph/REPO_GRAPH_NODES_001.jsonl
  - docs/operations/knowledge_graph/REPO_GRAPH_EDGES_001.jsonl
  - docs/operations/knowledge_graph/GRAPH_INDEX_001.json
- nodes_inspected: 66
- edges_inspected: 45

## Required Queries

| Query | Target | Status | Finding |
|---|---|---|---|
| safety_check | REPOSITORY_PHASE0_ROOT_CLEANUP_001 | DEGRADED | Target not in graph; no QS findings returned. |
| blast_radius | REPOSITORY_PHASE0_ROOT_CLEANUP_001 | DEGRADED | Target not in graph; low blast radius by fallback because scope is docs-only moves. |
| evidence_for_commit | b300c0c | DEGRADED | Commit not in seeded graph; fallback uses git status/log evidence. |

## Fallback Evidence

- `git branch -vv` observed branch `main` tracking `origin/main`.
- `git log -n 3 --oneline` observed HEAD `b300c0c docs: repository folder reorganization audit — 8-phase plan`.
- `git status --short` observed only ops JSON edits from bootstrap repair and root `AI_HANDOFF_*.md` files before file moves.
- `docs/reports/REPOSITORY_FOLDER_REORGANIZATION_AUDIT_001.md` lists the Phase 0 markdown targets as `NO_IMPORT_RISK`.
- Destination collision check found no existing `docs/research/` target files for the six research/planning docs and no existing `docs/operations/VULTR_PAPER_RUN.md`.
- Destination collision check found existing canonical `docs/PROJECT_STRUCTURE.md` and `docs/KNOWN_ISSUES.md`, so root forwarders are intentionally left in place.

## Execution Contract Attachment

```json
{
  "graph_query_ids": [
    "QUERY-20260628-REPOSITORY_PHASE0_ROOT_CLEANUP_001:safety_check",
    "QUERY-20260628-REPOSITORY_PHASE0_ROOT_CLEANUP_001:blast_radius",
    "QUERY-20260628-REPOSITORY_PHASE0_ROOT_CLEANUP_001:evidence_for_commit"
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
