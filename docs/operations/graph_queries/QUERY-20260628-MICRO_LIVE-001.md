# RUNTIME KNOWLEDGE GRAPH QUERY REPORT

## SECTION 1 — QUERY METADATA

```
query_id:          QUERY-20260628-MICRO_LIVE-001
query_timestamp:   2026-06-28T03:51:00Z
graph_version:     SNAP-20260627-001
graph_files_read:
  - docs/operations/knowledge_graph/REPO_GRAPH_NODES_001.jsonl
  - docs/operations/knowledge_graph/REPO_GRAPH_EDGES_001.jsonl
```

## SECTION 2 — QUERY TYPE

```
query_type:  safety_check
```

## SECTION 3 — TARGET

```
target_raw:     "main.py --mode live"
target_resolved: "task:MICRO_LIVE_1USD_SUPERVISED_RUN_001"
resolved_by:    exact_node_id
is_permanent:   false
is_deferred:    false
```

## SECTION 4 — SAFETY-FIRST CHECK

```
permanent_flag:     false
protecting_rules:   []
severity:           NONE
```

## SECTION 5 — GRAPH FILES READ

```
nodes_inspected: 0
edges_inspected: 0
node_types_relevant: []
```

## SECTION 6 — NODE MATCHES

```
target_node:
  node_id:   task:MICRO_LIVE_1USD_SUPERVISED_RUN_001
  node_type: task
  tags:      [live, execution, validation]
  confidence: 1.0

adjacent_nodes: []
```

## SECTION 7 — EDGE TRAVERSAL SUMMARY

```
traversal_type:   BFS
max_depth:        1
edge_types_traversed: []
nodes_visited:    1
edges_followed:   0
stopped_at:       none
```

## SECTION 8 — SAFETY FINDINGS

`safety_findings: []`

## SECTION 9 — AFFECTED NODES

`affected_nodes: []`

## SECTION 10 — AFFECTED EDGES

`affected_edges: []`

## SECTION 11 — EVIDENCE REFERENCES

`evidence_references: []`

## SECTION 12 — CONFIDENCE SCORE

```
overall_confidence:    1.0
confidence_basis:      all_edges_grade_A
lowest_grade_edge:     A
fallback_required:     false
fallback_reason:       null
```

## SECTION 13 — FALLBACK REQUIREMENT

```
fallback_required: false
fallback_actions: []
```

## SECTION 14 — RECOMMENDED WORKFLOW TIER

```
recommended_tier:   GATE
tier_reason:        Class 8 Live Risk execution task requires human operator supervision and strict verification gates.
blast_radius_score: LOW
safe_extraction_score: 10/10
```

## SECTION 15 — STOP CONDITIONS TRIGGERED

```
stop_conditions_triggered:
  - NONE

status: PASS
```

## SECTION 16 — EXECUTION CONTRACT ATTACHMENT

```json
{
  "graph_query_id": "QUERY-20260628-MICRO_LIVE-001",
  "graph_confidence": 1.0,
  "safety_findings_count": 0,
  "safety_findings": [],
  "affected_nodes_count": 0,
  "affected_edges_count": 0,
  "blast_radius_score": "LOW",
  "safe_extraction_score": "10/10",
  "recommended_workflow_tier": "GATE",
  "fallback_required": false,
  "status": "PASS"
}
```

## SECTION 17 — FINAL QUERY RESULT JSON

```json
{
  "$schema": "rkg_query_output_v1",
  "query_id": "QUERY-20260628-MICRO_LIVE-001",
  "query_type": "safety_check",
  "target": "task:MICRO_LIVE_1USD_SUPERVISED_RUN_001",
  "status": "PASS",
  "safety_findings": [],
  "affected_nodes": [],
  "affected_edges": [],
  "evidence": [],
  "recommended_workflow_tier": "GATE",
  "stop_conditions": [],
  "confidence": 1.0,
  "evidence_grade": "A",
  "execution_contract_attachment": {
    "graph_query_id": "QUERY-20260628-MICRO_LIVE-001",
    "graph_confidence": 1.0,
    "safety_findings_count": 0,
    "safety_findings": [],
    "affected_nodes_count": 0,
    "affected_edges_count": 0,
    "blast_radius_score": "LOW",
    "safe_extraction_score": "10/10",
    "recommended_workflow_tier": "GATE",
    "fallback_required": false,
    "status": "PASS"
  }
}
```
