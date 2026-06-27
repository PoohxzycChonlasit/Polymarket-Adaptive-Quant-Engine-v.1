# RUNTIME KNOWLEDGE GRAPH QUERY TEMPLATE v2

**Schema:** `rkg_query_template_v2`  
**Purpose:** Standard form for AI agents to query the seeded graph before refactor/implementation tasks.  
**Source files:** `docs/operations/knowledge_graph/REPO_GRAPH_NODES_001.jsonl` + `REPO_GRAPH_EDGES_001.jsonl`  
**Usage:** Copy and fill before including in Execution Contract Section 11.

---

## HOW TO USE

1. Copy this template
2. Fill Sections 1–16
3. Paste the Section 17 JSON block into Execution Contract → Section 11 "graph_query_attachment"
4. If `fallback_required: true` → also run `git grep` to confirm dependencies

---

## SECTION 1 — QUERY METADATA

```
query_id:          [e.g. QUERY-20260627-BATCH3D-001]
query_timestamp:   [ISO timestamp]
graph_version:     SNAP-20260627-001
graph_files_read:
  - docs/operations/knowledge_graph/REPO_GRAPH_NODES_001.jsonl
  - docs/operations/knowledge_graph/REPO_GRAPH_EDGES_001.jsonl
  - docs/operations/knowledge_graph/GRAPH_INDEX_001.json
```

---

## SECTION 2 — QUERY TYPE

```
query_type:  [blast_radius | safety_check | why_deferred | evidence_for_commit |
              runtime_dependencies | tasks_touching | method_history | graph_health]
```

---

## SECTION 3 — TARGET

```
target_raw:     [e.g. "_phase2_observability_payload" or "commit:3c5b781"]
target_resolved: [e.g. "fn:trader._phase2_observability_payload"]
resolved_by:    [alias_match | exact_node_id | not_found]
is_permanent:   [true | false | not_in_graph]
is_deferred:    [true | false | not_in_graph]
```

---

## SECTION 4 — SAFETY-FIRST CHECK (always complete this section first)

**Step 1:** Search nodes for target's `node_id` in graph  
**Step 2:** Check target's `is_permanent` flag  
**Step 3:** Find all edges WHERE `from_node` starts with `qs:` AND `to_node` = target  
**Step 4:** Record any `blocks` edges from QS nodes to target

```
permanent_flag:     [true | false]
protecting_rules:   [list of QS-N that have protects/blocks edge to target]
severity:           [CRITICAL | HIGH | MEDIUM | NONE]
```

**Decision:**
- If `permanent_flag=true` → STATUS = STOP, no refactor possible
- If protecting_rules contains CRITICAL QS entry → STATUS = STOP
- If protecting_rules contains non-CRITICAL → include in WARNING, proceed with care
- If protecting_rules is empty → proceed to blast radius

---

## SECTION 5 — GRAPH FILES READ

List which nodes you loaded for this query:

```
nodes_inspected: [count]
edges_inspected: [count]
node_types_relevant: [list of node_type values found for target and neighbors]
```

---

## SECTION 6 — NODE MATCHES

List target node and immediately adjacent nodes:

```
target_node:
  node_id:   [e.g. fn:trader._phase2_observability_payload]
  node_type: [function]
  tags:      [deferred_batch_3d, observability]
  confidence: [0.9]

adjacent_nodes:
  - node_id: [e.g. fn:trader._diagnostic_int]
    edge_type: depends_on
    direction: outbound
  - node_id: [e.g. qs:QS-006]
    edge_type: blocks
    direction: inbound
```

---

## SECTION 7 — EDGE TRAVERSAL SUMMARY

Describe the traversal:

```
traversal_type:   [BFS | DFS]
max_depth:        [3]
edge_types_traversed: [depends_on, calls, protects, blocks, deferred_by, ...]
nodes_visited:    [count]
edges_followed:   [count]
stopped_at:       [reason if traversal was cut short]
```

---

## SECTION 8 — SAFETY FINDINGS

List all QS rules triggered:

```
safety_findings:
  - rule_id:   QS-N
    reason:    [why this rule applies]
    severity:  CRITICAL | HIGH | MEDIUM
    evidence:  [edge_id or "from_safety_memory"]
    action:    STOP | WARN | NOTE
```

If no safety findings: `safety_findings: []`

---

## SECTION 9 — AFFECTED NODES

List all nodes reachable from target (within max_depth):

```
affected_nodes:
  - node_id:    [node_id]
    node_type:  [type]
    relationship: [how it relates: "calls target", "target calls this", ...]
    confidence: [float]
```

---

## SECTION 10 — AFFECTED EDGES

List the key edges traversed:

```
affected_edges:
  - edge_id:   [edge_id]
    edge_type: [type]
    from_node: [node_id]
    to_node:   [node_id]
    evidence_grade: [A|B|C|D]
    confidence: [float]
```

---

## SECTION 11 — EVIDENCE REFERENCES

List commits, reports, validations that back up the graph data:

```
evidence_references:
  - node_id:     [e.g. rtval:POST_BATCH_3C]
    type:        [runtime_validation | report | commit | audit]
    grade:       [A | B | C | D]
    description: [brief]
```

---

## SECTION 12 — CONFIDENCE SCORE

```
overall_confidence:    [0.0-1.0]
confidence_basis:      [all_edges_grade_A | mixed_grades | low_confidence_edges]
lowest_grade_edge:     [D | C | B | A]
fallback_required:     [true | false]
fallback_reason:       [null or reason why grep verification needed]
```

---

## SECTION 13 — FALLBACK REQUIREMENT

```
fallback_required: [true | false]
fallback_actions:
  - [grep command if needed, e.g. grep -n "_phase2_observability_payload" polymarket/trader.py]
  - [grep for call sites if confidence < 0.7]
```

---

## SECTION 14 — RECOMMENDED WORKFLOW TIER

```
recommended_tier:   [FAST | LOOP | STANDARD | GATE]
tier_reason:        [based on blast_radius_score + safety_findings]
blast_radius_score: [LOW | MEDIUM | HIGH]
safe_extraction_score: [N/10 if applicable]
```

---

## SECTION 15 — STOP CONDITIONS TRIGGERED

```
stop_conditions_triggered:
  - [condition string, or NONE]

status: [PASS | DEGRADED | STOP | ERROR]
```

---

## SECTION 16 — EXECUTION CONTRACT ATTACHMENT

**This section is the output for Execution Contract Section 11:**

```json
{
  "graph_query_id": "[query_id from Section 1]",
  "graph_confidence": [float from Section 12],
  "safety_findings_count": [int],
  "safety_findings": ["QS-N: reason" or []],
  "affected_nodes_count": [int],
  "affected_edges_count": [int],
  "blast_radius_score": "LOW | MEDIUM | HIGH",
  "safe_extraction_score": "N/10 or null",
  "recommended_workflow_tier": "FAST | LOOP | STANDARD | GATE",
  "fallback_required": [bool],
  "status": "PASS | DEGRADED | STOP | ERROR"
}
```

---

## SECTION 17 — FINAL QUERY RESULT JSON

Paste the complete query output using the `rkg_query_output_v1` schema:

```json
{
  "$schema": "rkg_query_output_v1",
  "query_id": "...",
  "query_type": "...",
  "target": "...",
  "status": "PASS | DEGRADED | STOP | ERROR",
  "safety_findings": [],
  "affected_nodes": [],
  "affected_edges": [],
  "evidence": [],
  "recommended_workflow_tier": "...",
  "stop_conditions": [],
  "confidence": 0.0,
  "evidence_grade": "D | C | B | A",
  "execution_contract_attachment": {}
}
```

---

---

# EXAMPLE FILLS

---

## EXAMPLE 1 — `blast_radius("_phase2_observability_payload")`

**Sections 1–17 filled for Batch 3D planning:**

**Section 1 Metadata:**
```
query_id:       QUERY-20260627-BATCH3D-BLAST-001
query_type:     blast_radius
graph_version:  SNAP-20260627-001
```

**Section 3 Target:**
```
target_raw:      _phase2_observability_payload
target_resolved: fn:trader._phase2_observability_payload
resolved_by:     alias_match (searching nodes for name field)
is_permanent:    false
is_deferred:     true (deferred_batch=Batch-3D)
```

**Section 4 Safety-First:**
```
permanent_flag:    false
protecting_rules:  [QS-005 (blocks), QS-006 (blocks)]
severity:          CRITICAL
```
→ **Status: STOP — QS-005 and QS-006 block extraction**

**Section 8 Safety Findings:**
```
safety_findings:
  - rule_id:  QS-005
    reason:   calls _diagnostic_float (99+ core math paths, blast_radius=MAX)
    severity: CRITICAL
    action:   STOP
  - rule_id:  QS-006
    reason:   calls _diagnostic_int (same blast radius)
    severity: CRITICAL
    action:   STOP
```

**Section 16 Execution Contract Attachment:**
```json
{
  "graph_query_id": "QUERY-20260627-BATCH3D-BLAST-001",
  "graph_confidence": 0.9,
  "safety_findings_count": 2,
  "safety_findings": ["QS-005: calls _diagnostic_float", "QS-006: calls _diagnostic_int"],
  "affected_nodes_count": 2,
  "affected_edges_count": 2,
  "blast_radius_score": "HIGH",
  "safe_extraction_score": "3/10",
  "recommended_workflow_tier": "GATE",
  "fallback_required": false,
  "status": "STOP"
}
```

---

## EXAMPLE 2 — `safety_check("_last_quote_lineage_context")`

**Section 3 Target:**
```
target_raw:      _last_quote_lineage_context
target_resolved: field:trader._last_quote_lineage_context
is_permanent:    true
```

**Section 4 Safety-First:**
```
permanent_flag:    true  ← IMMEDIATE STOP
protecting_rules:  [QS-003]
severity:          CRITICAL
```

**Section 17 Final Result:**
```json
{
  "$schema": "rkg_query_output_v1",
  "query_id": "QUERY-20260627-SAFETY-001",
  "query_type": "safety_check",
  "target": "field:trader._last_quote_lineage_context",
  "status": "STOP",
  "safety_findings": [{"rule": "QS-003", "reason": "PERMANENT — written from execution path inside _phase4_build_quote_lineage", "severity": "CRITICAL"}],
  "affected_nodes": ["qs:QS-003"],
  "affected_edges": ["E003"],
  "evidence": [{"node_id": "audit:BATCH_3D_GATE_CHECK_001", "grade": "B"}],
  "recommended_workflow_tier": "GATE",
  "stop_conditions": ["QS-003 CRITICAL — field is PERMANENT, never extract"],
  "confidence": 1.0,
  "evidence_grade": "B",
  "execution_contract_attachment": {
    "graph_query_id": "QUERY-20260627-SAFETY-001",
    "graph_confidence": 1.0,
    "safety_findings_count": 1,
    "safety_findings": ["QS-003: PERMANENT — execution path write"],
    "affected_nodes_count": 1,
    "affected_edges_count": 1,
    "blast_radius_score": "HIGH",
    "safe_extraction_score": "0/10",
    "recommended_workflow_tier": "GATE",
    "fallback_required": false,
    "status": "STOP"
  }
}
```

---

## EXAMPLE 3 — `why_deferred("BATCH_3D_GATE_CHECK_001")`

**Section 3 Target:**
```
target_raw:      BATCH_3D_GATE_CHECK_001
target_resolved: task:BATCH_3D_GATE_CHECK_001
is_deferred:     true (result=PAUSE_BATCH_3D_DEFER)
```

**Section 7 Edge Traversal:**
```
edges_followed:
  - task:BATCH_3D_GATE_CHECK_001 → deferred_by → audit:BATCH_3D_GATE_CHECK_001
  - qs:QS-005 → blocks → fn:trader._phase2_complete_lifecycle_observability
  - qs:QS-006 → blocks → fn:trader._phase2_observability_payload
```

**Section 17 Final Result:**
```json
{
  "$schema": "rkg_query_output_v1",
  "query_id": "QUERY-20260627-DEFERRED-001",
  "query_type": "why_deferred",
  "target": "task:BATCH_3D_GATE_CHECK_001",
  "status": "PASS",
  "safety_findings": [
    {"rule": "QS-005", "reason": "blocks _phase2_complete_lifecycle_observability", "severity": "CRITICAL"},
    {"rule": "QS-006", "reason": "blocks _phase2_observability_payload", "severity": "CRITICAL"}
  ],
  "affected_nodes": ["audit:BATCH_3D_GATE_CHECK_001", "fn:trader._phase2_complete_lifecycle_observability", "fn:trader._phase2_observability_payload"],
  "affected_edges": ["E009", "E010", "E050", "E051"],
  "evidence": [{"node_id": "audit:BATCH_3D_GATE_CHECK_001", "grade": "B", "description": "PAUSE_BATCH_3D_DEFER verdict"}],
  "recommended_workflow_tier": "GATE",
  "stop_conditions": [],
  "confidence": 1.0,
  "evidence_grade": "B",
  "execution_contract_attachment": {
    "graph_query_id": "QUERY-20260627-DEFERRED-001",
    "graph_confidence": 1.0,
    "safety_findings_count": 2,
    "safety_findings": ["QS-005: blocks lifecycle observability", "QS-006: blocks observability payload"],
    "affected_nodes_count": 3,
    "affected_edges_count": 4,
    "blast_radius_score": "HIGH",
    "recommended_workflow_tier": "GATE",
    "fallback_required": false,
    "status": "PASS"
  }
}
```

---

## EXAMPLE 4 — `evidence_for_commit("3c5b781")`

**Section 3 Target:**
```
target_raw:      3c5b781
target_resolved: commit:3c5b781
resolved_by:     exact_node_id match (sha field)
```

**Section 7 Edge Traversal:**
```
edges_followed:
  - commit:3c5b781 → generated_report → report:TRADER_REFACTOR_BATCH_003C_REPORT (E080)
  - rtval:POST_BATCH_3C → validated_by → commit:3c5b781 (E072)
```

**Section 11 Evidence:**
```
evidence_references:
  - node_id:    report:TRADER_REFACTOR_BATCH_003C_REPORT
    type:       report
    grade:      C
    description: 128/128 tests pass, 0 regressions
  - node_id:    rtval:POST_BATCH_3C
    type:       runtime_validation
    grade:      A
    description: 7 cycles, exit 0, 56 JSONL events
```

**Section 17 Final Result:**
```json
{
  "$schema": "rkg_query_output_v1",
  "query_id": "QUERY-20260627-EVIDENCE-001",
  "query_type": "evidence_for_commit",
  "target": "commit:3c5b781",
  "status": "PASS",
  "safety_findings": [],
  "affected_nodes": ["report:TRADER_REFACTOR_BATCH_003C_REPORT", "rtval:POST_BATCH_3C"],
  "affected_edges": ["E072", "E080"],
  "evidence": [
    {"node_id": "report:TRADER_REFACTOR_BATCH_003C_REPORT", "grade": "C", "description": "128/128 tests, 0 regressions"},
    {"node_id": "rtval:POST_BATCH_3C", "grade": "A", "description": "7 cycles, exit 0, 56 JSONL events, STATUS NO LIVE ORDERS"}
  ],
  "recommended_workflow_tier": "LOOP",
  "stop_conditions": [],
  "confidence": 1.0,
  "evidence_grade": "A",
  "execution_contract_attachment": {
    "graph_query_id": "QUERY-20260627-EVIDENCE-001",
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
