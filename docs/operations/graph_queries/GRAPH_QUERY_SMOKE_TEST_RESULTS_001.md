# GRAPH QUERY SMOKE TEST RESULTS 001

**Date:** 2026-06-27  
**Graph version:** SNAP-20260627-001  
**Graph files:**
- `docs/operations/knowledge_graph/REPO_GRAPH_NODES_001.jsonl` (66 nodes)
- `docs/operations/knowledge_graph/REPO_GRAPH_EDGES_001.jsonl` (45 edges)

---

## QUERY 1 — `safety_check("_last_quote_lineage_context")`

### Sections 1–4

```
query_id:       QUERY-20260627-SMOKE-001
query_type:     safety_check
target_raw:     _last_quote_lineage_context
target_resolved: field:trader._last_quote_lineage_context
resolved_by:    alias_match (name field scan)
is_permanent:   true  ← NODE FLAG CONFIRMED IN JSONL
```

**Safety-First (Section 4):**
```
permanent_flag:    true  ← IMMEDIATE STOP
protecting_rules:
  - qs:QS-003 (edge E003, edge_type=protects, from_node=qs:QS-003, to_node=field:trader._last_quote_lineage_context)
severity:          CRITICAL
```

### Section 8 — Safety Findings
```
safety_findings:
  - rule_id:  QS-003
    reason:   PERMANENT — written from execution path inside _phase4_build_quote_lineage
    severity: CRITICAL
    evidence: edge E003 in REPO_GRAPH_EDGES_001.jsonl (confidence=1.0, grade=B)
    action:   STOP
```

### Section 16 — Execution Contract Attachment
```json
{
  "graph_query_id": "QUERY-20260627-SMOKE-001",
  "graph_confidence": 1.0,
  "safety_findings_count": 1,
  "safety_findings": ["QS-003: PERMANENT — execution path write"],
  "affected_nodes_count": 2,
  "affected_edges_count": 1,
  "blast_radius_score": "HIGH",
  "safe_extraction_score": "0/10",
  "recommended_workflow_tier": "GATE",
  "fallback_required": false,
  "status": "STOP"
}
```

### Section 17 — Final Result
```json
{
  "$schema": "rkg_query_output_v1",
  "query_id": "QUERY-20260627-SMOKE-001",
  "query_type": "safety_check",
  "target": "field:trader._last_quote_lineage_context",
  "status": "STOP",
  "safety_findings": [{"rule": "QS-003", "reason": "PERMANENT — written from execution path", "severity": "CRITICAL"}],
  "affected_nodes": ["qs:QS-003", "field:trader._last_quote_lineage_context"],
  "affected_edges": ["E003"],
  "evidence": [{"node_id": "qs:QS-003", "grade": "B", "description": "safety_rule node, memory_reference_id=QS-003, is_permanent=true"}],
  "recommended_workflow_tier": "GATE",
  "stop_conditions": ["QS-003 CRITICAL — field is PERMANENT, never extract or move"],
  "confidence": 1.0,
  "evidence_grade": "B",
  "execution_contract_attachment": {
    "graph_query_id": "QUERY-20260627-SMOKE-001",
    "graph_confidence": 1.0,
    "safety_findings_count": 1,
    "safety_findings": ["QS-003: PERMANENT execution path write"],
    "affected_nodes_count": 2,
    "affected_edges_count": 1,
    "blast_radius_score": "HIGH",
    "safe_extraction_score": "0/10",
    "recommended_workflow_tier": "GATE",
    "fallback_required": false,
    "status": "STOP"
  }
}
```

**Expected vs Observed:**  
Expected: QS-003 surfaced, CRITICAL, STOP → **MATCH ✓**

---

## QUERY 2 — `why_deferred("BATCH_3D_GATE_CHECK_001")`

### Sections 1–4

```
query_id:       QUERY-20260627-SMOKE-002
query_type:     why_deferred
target_raw:     BATCH_3D_GATE_CHECK_001
target_resolved: task:BATCH_3D_GATE_CHECK_001
is_permanent:   false
is_deferred:    true (result=PAUSE_BATCH_3D_DEFER in node)
```

**Safety-First (Section 4):**
```
permanent_flag:    false
protecting_rules:  [] (no QS rules protect the task node itself)
severity:          NONE — proceed to traversal
```

### Section 7 — Edge Traversal

Traversal from `task:BATCH_3D_GATE_CHECK_001` and linked audit node:
- `fn:trader._phase2_complete_lifecycle_observability` → deferred_by → `audit:BATCH_3D_GATE_CHECK_001` (E050)
- `fn:trader._phase2_observability_payload` → deferred_by → `audit:BATCH_3D_GATE_CHECK_001` (E051)
- `qs:QS-005` → blocks → `fn:trader._phase2_complete_lifecycle_observability` (E009)
- `qs:QS-006` → blocks → `fn:trader._phase2_observability_payload` (E010)

### Section 16 — Execution Contract Attachment
```json
{
  "graph_query_id": "QUERY-20260627-SMOKE-002",
  "graph_confidence": 1.0,
  "safety_findings_count": 2,
  "safety_findings": ["QS-005: blocks _phase2_complete_lifecycle_observability", "QS-006: blocks _phase2_observability_payload"],
  "affected_nodes_count": 4,
  "affected_edges_count": 4,
  "blast_radius_score": "HIGH",
  "recommended_workflow_tier": "GATE",
  "fallback_required": false,
  "status": "PASS"
}
```

### Section 17 — Final Result
```json
{
  "$schema": "rkg_query_output_v1",
  "query_id": "QUERY-20260627-SMOKE-002",
  "query_type": "why_deferred",
  "target": "task:BATCH_3D_GATE_CHECK_001",
  "status": "PASS",
  "safety_findings": [
    {"rule": "QS-005", "reason": "blocks _phase2_complete_lifecycle_observability — calls _diagnostic_float", "severity": "CRITICAL"},
    {"rule": "QS-006", "reason": "blocks _phase2_observability_payload — calls _diagnostic_int", "severity": "CRITICAL"}
  ],
  "affected_nodes": [
    "fn:trader._phase2_complete_lifecycle_observability",
    "fn:trader._phase2_observability_payload",
    "audit:BATCH_3D_GATE_CHECK_001",
    "qs:QS-005", "qs:QS-006"
  ],
  "affected_edges": ["E009", "E010", "E050", "E051"],
  "evidence": [{"node_id": "audit:BATCH_3D_GATE_CHECK_001", "grade": "B", "description": "PAUSE_BATCH_3D_DEFER verdict, safe_scores 5/10 and 3/10"}],
  "recommended_workflow_tier": "GATE",
  "stop_conditions": [],
  "confidence": 1.0,
  "evidence_grade": "B",
  "execution_contract_attachment": {
    "graph_query_id": "QUERY-20260627-SMOKE-002",
    "graph_confidence": 1.0,
    "safety_findings_count": 2,
    "safety_findings": ["QS-005: blocks lifecycle observability", "QS-006: blocks observability payload"],
    "affected_nodes_count": 5,
    "affected_edges_count": 4,
    "blast_radius_score": "HIGH",
    "recommended_workflow_tier": "GATE",
    "fallback_required": false,
    "status": "PASS"
  }
}
```

**Expected vs Observed:**  
Expected: PAUSE_BATCH_3D_DEFER, 2 deferred methods, QS-005/006 blocking → **MATCH ✓**

---

## QUERY 3 — `evidence_for_commit("3c5b781")`

### Sections 1–4

```
query_id:       QUERY-20260627-SMOKE-003
query_type:     evidence_for_commit
target_raw:     3c5b781
target_resolved: commit:3c5b781
resolved_by:    sha field match in nodes
batch:          Batch-3C
```

**Safety-First:** Not applicable for evidence query (commit node, no QS rules target commits directly).

### Section 7 — Edge Traversal

- `commit:3c5b781` → generated_report → `report:TRADER_REFACTOR_BATCH_003C_REPORT` (E080, grade=C)
- `commit:3c5b781` → validated_by → `rtval:POST_BATCH_3C` (E072, grade=A)

**Runtime validation node details:**
- cycles=7, exit_code=0, jsonl_events=56, evidence_grade=A

### Section 11 — Evidence References
```
evidence_references:
  - node_id:  report:TRADER_REFACTOR_BATCH_003C_REPORT
    type:     report
    grade:    C
    description: 128/128 tests pass, 0 regressions, trader.py -49 lines
  - node_id:  rtval:POST_BATCH_3C
    type:     runtime_validation
    grade:    A
    description: 7 cycles, exit 0, 56 JSONL events, STATUS NO LIVE ORDERS
```

### Section 17 — Final Result
```json
{
  "$schema": "rkg_query_output_v1",
  "query_id": "QUERY-20260627-SMOKE-003",
  "query_type": "evidence_for_commit",
  "target": "commit:3c5b781",
  "status": "PASS",
  "safety_findings": [],
  "affected_nodes": ["report:TRADER_REFACTOR_BATCH_003C_REPORT", "rtval:POST_BATCH_3C"],
  "affected_edges": ["E072", "E080"],
  "evidence": [
    {"node_id": "report:TRADER_REFACTOR_BATCH_003C_REPORT", "grade": "C", "description": "128/128 tests, 0 regressions"},
    {"node_id": "rtval:POST_BATCH_3C", "grade": "A", "description": "7 cycles, exit 0, 56 JSONL events"}
  ],
  "recommended_workflow_tier": "LOOP",
  "stop_conditions": [],
  "confidence": 1.0,
  "evidence_grade": "A",
  "execution_contract_attachment": {
    "graph_query_id": "QUERY-20260627-SMOKE-003",
    "graph_confidence": 1.0,
    "safety_findings_count": 0,
    "safety_findings": [],
    "affected_nodes_count": 2,
    "affected_edges_count": 2,
    "blast_radius_score": "LOW",
    "recommended_workflow_tier": "LOOP",
    "fallback_required": false,
    "status": "PASS"
  }
}
```

**Expected vs Observed:**  
Expected: Batch 3C, 0 errors, JSONL verified, paper run evidence → **MATCH ✓**

---

## QUERY 4 — `blast_radius("TraderObservabilityHelper")`

### Sections 1–4

```
query_id:       QUERY-20260627-SMOKE-004
query_type:     blast_radius
target_raw:     TraderObservabilityHelper
target_resolved: class:TraderObservabilityHelper
is_permanent:   false
```

**Safety-First (Section 4):**
```
permanent_flag:    false
protecting_rules:  [] (no QS rules target the helper class directly)
severity:          NONE — safe to proceed with blast radius
```

### Section 7 — Edge Traversal (depth=2)

Level 1 (from class):
- `class:TraderObservabilityHelper` → owns → `fn:helper._mark_orderbook_refresh`
- `class:TraderObservabilityHelper` → owns → `fn:helper._scheduler_cadence_observability_detail`
- `class:TraderObservabilityHelper` → owns → `fn:helper._phase2_candidate_hash`

Level 2 (from owned methods):
- `fn:helper._mark_orderbook_refresh` → emits/writes → `jfield:orderbook_refresh_source`
- `fn:helper._scheduler_cadence_observability_detail` → emits → `jfield:market_evaluation_duration_ms`
- 4 methods extracted_to this class from trader.py (reverse direction)

No direct execution/risk/sizing connections found.

### Section 9 — Affected Nodes

```
affected_nodes:
  - class:TraderObservabilityHelper (target)
  - fn:helper._mark_orderbook_refresh (owns)
  - fn:helper._scheduler_cadence_observability_detail (owns)
  - fn:helper._phase2_candidate_hash (owns)
  - jfield:orderbook_refresh_source (emits/writes from _mark_orderbook_refresh)
  - jfield:market_evaluation_duration_ms (emits from _scheduler_cadence)
  - commit:a491820 (migrated_in_batch — Batch 3B-1)
  - commit:381cbc4 (migrated_in_batch — Batch 3B-2)
  - commit:3c5b781 (migrated_in_batch — Batch 3C)
```

### Section 16 — Execution Contract Attachment
```json
{
  "graph_query_id": "QUERY-20260627-SMOKE-004",
  "graph_confidence": 0.9,
  "safety_findings_count": 0,
  "safety_findings": [],
  "affected_nodes_count": 9,
  "affected_edges_count": 8,
  "blast_radius_score": "MEDIUM",
  "recommended_workflow_tier": "LOOP",
  "fallback_required": false,
  "status": "PASS",
  "note": "Moving this class would break 2 JSONL fields: orderbook_refresh_source, market_evaluation_duration_ms"
}
```

### Section 17 — Final Result
```json
{
  "$schema": "rkg_query_output_v1",
  "query_id": "QUERY-20260627-SMOKE-004",
  "query_type": "blast_radius",
  "target": "class:TraderObservabilityHelper",
  "status": "PASS",
  "safety_findings": [],
  "affected_nodes": [
    "fn:helper._mark_orderbook_refresh",
    "fn:helper._scheduler_cadence_observability_detail",
    "fn:helper._phase2_candidate_hash",
    "jfield:orderbook_refresh_source",
    "jfield:market_evaluation_duration_ms"
  ],
  "affected_edges": ["E023", "E024", "E025", "E032", "E033", "E090", "E091", "E121"],
  "evidence": [
    {"node_id": "rtval:POST_BATCH_3B1", "grade": "A", "description": "7 cycles, 53 orderbook_refresh_source events"},
    {"node_id": "rtval:POST_BATCH_3B2", "grade": "A", "description": "6 cycles, 28 market_evaluation_duration_ms events"}
  ],
  "recommended_workflow_tier": "LOOP",
  "stop_conditions": [],
  "confidence": 0.9,
  "evidence_grade": "A",
  "execution_contract_attachment": {
    "graph_query_id": "QUERY-20260627-SMOKE-004",
    "graph_confidence": 0.9,
    "safety_findings_count": 0,
    "safety_findings": [],
    "affected_nodes_count": 9,
    "affected_edges_count": 8,
    "blast_radius_score": "MEDIUM",
    "recommended_workflow_tier": "LOOP",
    "fallback_required": false,
    "status": "PASS"
  }
}
```

**Expected vs Observed:**  
Expected: runtime events/JSONL fields, extraction history, no execution/risk/sizing → **MATCH ✓**
