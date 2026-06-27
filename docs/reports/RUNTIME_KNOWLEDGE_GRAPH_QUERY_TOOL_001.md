# RUNTIME_KNOWLEDGE_GRAPH_QUERY_TOOL_001

**Date:** 2026-06-27 · **Tier:** STANDARD Class 4 · **Repairs:** 0

## Files Created

| File | Content |
|------|---------|
| `docs/operations/GRAPH_QUERY_TEMPLATE_001.md` | 17-section query form + 4 complete example fills |

## Template Sections

| Section | Purpose |
|---------|---------|
| 1 — Query Metadata | query_id, timestamp, graph_version, files_read |
| 2 — Query Type | blast_radius / safety_check / why_deferred / evidence_for_commit / ... |
| 3 — Target | target_raw → target_resolved, is_permanent, is_deferred |
| 4 — Safety-First | permanent_flag + protecting_rules + severity → immediate STOP if CRITICAL |
| 5 — Graph Files Read | nodes/edges inspected count |
| 6 — Node Matches | target + adjacent nodes with edge types |
| 7 — Edge Traversal Summary | BFS/DFS, max_depth, nodes_visited |
| 8 — Safety Findings | QS-N rules triggered with action (STOP/WARN/NOTE) |
| 9 — Affected Nodes | reachable nodes with relationship description |
| 10 — Affected Edges | key edges with evidence_grade |
| 11 — Evidence References | reports/validations/commits backing graph data |
| 12 — Confidence Score | overall confidence + lowest_grade_edge + fallback_required |
| 13 — Fallback Requirement | grep commands if confidence < threshold |
| 14 — Recommended Tier | blast_radius_score + safe_extraction_score → tier |
| 15 — Stop Conditions | triggered conditions or NONE |
| 16 — Execution Contract Attachment | JSON block ready to embed in Section 11 |
| 17 — Final Query Result JSON | Complete `rkg_query_output_v1` object |

## Four Example Fills

| Example | Query | Key result |
|---------|-------|-----------|
| 1 | `blast_radius("_phase2_observability_payload")` | STOP — QS-005/006 block, safe_score=3/10 |
| 2 | `safety_check("_last_quote_lineage_context")` | STOP — QS-003 CRITICAL, is_permanent=true |
| 3 | `why_deferred("BATCH_3D_GATE_CHECK_001")` | PASS — 2 QS rules, gate verdict PAUSE_BATCH_3D_DEFER |
| 4 | `evidence_for_commit("3c5b781")` | PASS — grade A (7-cycle paper run + report) |

## Integration with Execution Contract

Section 16 of the filled template produces a JSON block that drops directly into Execution Contract Section 11 "graph_query_attachment". The `safety_findings_count` field triggers Role 29 review if > 0 with CRITICAL severity.

## Limitations

1. **Manual JSONL scanning** — AI must read the JSONL files and apply query logic manually; no programmatic traversal yet (v3 Python tool will automate this)
2. **Alias resolution is manual** — short names like `_phase2_observability_payload` must be matched to full node_ids by scanning `name` fields in the JSONL
3. **Max depth limited to what AI can trace** — complex transitive dependencies may be missed; fallback grep compensates
4. **Graph may be stale** — if graph was last seeded > 30 days ago, runtime refactor queries should set `fallback_required: true`

## Next Recommendation

`RUNTIME_KNOWLEDGE_GRAPH_QUERY_SMOKE_TEST_001` — LOOP tier Class 0. Use the template to execute all 4 example queries against the live seeded graph, verify outputs match expected results, and prove the template is usable before mandating it for CLASS 6+ Execution Contracts.

## Final Verdict

```
RUNTIME_KNOWLEDGE_GRAPH_QUERY_TOOL_COMMITTED
```
