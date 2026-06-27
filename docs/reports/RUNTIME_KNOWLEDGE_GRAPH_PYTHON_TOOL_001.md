# RUNTIME_KNOWLEDGE_GRAPH_PYTHON_TOOL_001

**Date:** 2026-06-27 · **Tier:** STANDARD Class 4 · **Repairs:** 0

## Files Changed

| File | Change |
|------|--------|
| `tools/flaos/knowledge_graph.py` | New — 5 subcommands, BFS traversal, safety-first logic |
| `tests/test_flaos_knowledge_graph.py` | New — 24 tests, all pass |

## CLI Behavior

```bash
python tools/flaos/knowledge_graph.py graph-health
python tools/flaos/knowledge_graph.py safety-check _last_quote_lineage_context
python tools/flaos/knowledge_graph.py blast-radius TraderObservabilityHelper
python tools/flaos/knowledge_graph.py evidence-for-commit 3c5b781
python tools/flaos/knowledge_graph.py why-deferred BATCH_3D_GATE_CHECK_001
```

Options: `--pretty` (before subcommand), `--nodes PATH`, `--edges PATH`

## Query Output Schema

Every query returns `rkg_query_output_v1`:
```json
{
  "$schema": "rkg_query_output_v1",
  "query_type": "...",
  "target": "...",
  "status": "PASS|DEGRADED|STOP_REQUIRED|GATE",
  "safety_findings": [],
  "affected_nodes": [],
  "affected_edges": [],
  "evidence": [],
  "recommended_workflow_tier": "LOOP|STANDARD|GATE",
  "stop_conditions": [],
  "confidence": 0.0,
  "fallback_required": false,
  "execution_contract_attachment": {
    "safety_findings_count": 0,
    "blast_radius_score": "LOW|MEDIUM|HIGH",
    "recommended_workflow_tier": "...",
    "fallback_required": false,
    "status": "..."
  }
}
```

## Tests (24/24 pass)

| Category | Tests | Key assertions |
|----------|-------|---------------|
| Graph loading | 4 | 66 nodes, 45 edges, 10 safety_rule nodes, no polymarket import |
| graph-health | 3 | 66/45, QS complete, schema fields |
| safety-check | 5 | QS-003 for permanent field, STOP for _phase4_*, missing=DEGRADED |
| blast-radius | 4 | safety included, safe target PASS, missing=DEGRADED, deferred flag |
| evidence-for-commit | 4 | Batch 3C evidence PASS, batch field, missing=DEGRADED, attachment |
| why-deferred | 4 | BATCH_3D found, method deferred, missing=DEGRADED, attachment |

## Limitations

1. **Orphaned edges (4)** — seed has edges to placeholder node IDs (`fn:trader._mark_orderbook_refresh_original`); graph-health reports DEGRADED. Known seed artifact, not a tool bug.
2. **Alias resolution** — short names matched by substring; multiple matches return first result. v4 AST graph will provide exact qualified names.
3. **why_deferred** — for task nodes (vs method nodes), traversal logic finds edges via task_id suffix matching. May miss some task→method deferral chains. Accurate for direct deferred_by edges.
4. **Graph stale check** — not yet enforced by the tool. Future: add `--max-age-days` check.

## Next Recommendation

`RUNTIME_KNOWLEDGE_GRAPH_PYTHON_TOOL_SMOKE_TEST_001` — LOOP tier Class 0. Run the 4 CLI queries against live graph and compare to manual template smoke test results from `GRAPH_QUERY_SMOKE_TEST_RESULTS_001.md`.

## Final Verdict

```
RUNTIME_KNOWLEDGE_GRAPH_PYTHON_TOOL_COMMITTED
24/24 tests pass
5 subcommands working
No polymarket imports
```
