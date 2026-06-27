# RUNTIME_KNOWLEDGE_GRAPH_QUERY_ENGINE_DESIGN_001

**Date:** 2026-06-27 · **Tier:** GATE Class 2 · **Repairs:** 0

## Files Created

| File | Content |
|------|---------|
| `docs/architecture/RUNTIME_KNOWLEDGE_GRAPH_QUERY_ENGINE_001.md` | 12-section design: 8 core queries, input/output schemas, safety-first behavior, Execution Contract integration, 5 query examples from seeded graph, evidence grading, stop conditions, 3 Mermaid diagrams, migration v1–v5 |

## Architecture Summary

The RKG Query Engine reads the seeded JSONL graph files and exposes 8 standard queries:

| Query | Purpose |
|-------|---------|
| `blast_radius(target)` | What breaks if this moves? |
| `safety_check(target)` | Are QS rules protecting this? |
| `evidence_for_commit(sha)` | What validated this commit? |
| `why_deferred(target)` | Why was this task/method deferred? |
| `runtime_dependencies(target)` | Which JSONL fields depend on this? |
| `tasks_touching(target)` | Which tasks modified this file/method? |
| `method_history(name)` | Full extraction/proxy chain |
| `graph_health()` | Is the graph self-consistent? |

## Safety Behavior

**safety_check always runs first.** It cannot be disabled for Class 6+ tasks. QS nodes with `severity: CRITICAL` produce `status: STOP` immediately — no further traversal. The graph cannot produce `status: PASS` if QS-001..010 overlap the target.

## Execution Contract Integration

Future CLASS 6+ contracts include a `graph_query_attachment` block in Section 11:
- `graph_confidence`: reliability of the graph result
- `safety_findings_count`: 0 = SAFE; >0 = must review
- `blast_radius_score`: LOW/MEDIUM/HIGH
- `fallback_required`: true if graph uncertainty requires grep confirmation

**STOP condition:** If `safety_findings_count > 0` with CRITICAL severity → Role 29 review required before implementation.

## Query Examples from Seeded Graph

| Target | Result |
|--------|--------|
| `_last_quote_lineage_context` | STOP — QS-003 CRITICAL, is_permanent=true |
| `_phase2_observability_payload` | blast_radius=HIGH, QS-005/006, score=3/10, DEFER |
| commit `3c5b781` | evidence_grade=A (7-cycle paper run + report) |
| `TraderObservabilityHelper` | 4 JSONL fields depend on it (grade A) |
| `BATCH_3D_GATE_CHECK_001` | deferred_by gate, QS-005/006, re-gate after AST graph |

## Next Recommendation

`RUNTIME_KNOWLEDGE_GRAPH_QUERY_TOOL_001` — STANDARD tier Class 4. Implement v2: `docs/operations/GRAPH_QUERY_TEMPLATE_001.md` — a Markdown query form that AI fills using the seeded JSONL to produce structured JSON query outputs. Proves queries work before Python implementation.

## Final Verdict

```
RUNTIME_KNOWLEDGE_GRAPH_QUERY_ENGINE_DESIGN_COMMITTED
```
