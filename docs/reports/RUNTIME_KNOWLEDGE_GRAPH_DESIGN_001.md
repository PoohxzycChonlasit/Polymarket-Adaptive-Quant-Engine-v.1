# RUNTIME_KNOWLEDGE_GRAPH_DESIGN_001

**Date:** 2026-06-27 · **Tier:** GATE Class 2 · **Repairs:** 0

## Files Created

| File | Content |
|------|---------|
| `docs/architecture/RUNTIME_KNOWLEDGE_GRAPH_001.md` | 14-section design: 23 node types, 24 edge types, 5 core schemas, safety integration (QS-001..010), runtime integration, Memory OS links, refactor history seeding, 6 query examples, lifecycle, evidence model, Execution Contract integration, 3 Mermaid diagrams, migration v1–v5 |

## Architecture Summary

The Runtime Knowledge Graph (RKG) extends the static Repository Graph into a unified operational knowledge base connecting code, runtime, safety, decisions, and evidence.

**23 node types** covering: code structure (file, module, class, function, field), runtime (session, event, jsonl_field, validation), governance (task, agent_role, tool, skill, pipeline), and memory (memory_entry, safety_rule, decision, quant_question).

**24 edge types** covering: structural (imports, calls, owns, reads, writes), extraction (extracted_to, proxied_by, migrated_in_batch), safety (protects, blocks, requires_safety_memory), and evidence (has_evidence, generated_report, validated, has_memory_entry).

## Safety Integration

QS-001..010 from `SAFETY_MEMORY.jsonl` become permanent `safety_rule` nodes. Every function protected by a QS rule has a `protects` edge. Any blast radius query surfaces these rules immediately before planning.

**Key safety mapping:**
- QS-001/002: `_phase4_*` — execution path
- QS-003: `_last_quote_lineage_context` — execution write
- QS-004..006: `_risk_plan_zero_diagnostics`, `_diagnostic_float/_int` — permanent
- QS-007..010: live trading, .env, runtime data, execution/risk/sizing

## Query Examples Summary

| Query | Answer |
|-------|--------|
| Blast radius of `_phase2_complete_lifecycle_observability` | HIGH risk, QS-005/006, safe_score=5/10, DEFER |
| Safety rules protecting `_last_quote_lineage_context` | QS-003, is_permanent=true |
| Evidence for commit `3c5b781` | Batch 3C report + 7-cycle paper run, 56 JSONL events |
| Runtime deps of `TraderObservabilityHelper` | go_no_go_decision_v1, orderbook_state_changed_v1, 4 JSONL fields |
| All tasks touching `trader.py` | 6 batches (Batch 1 → Batch 3C), -600+ lines cumulative |
| Why Batch 3D deferred | PAUSE_BATCH_3D_DEFER gate, QS-005/006 coupling, 3-5/10 scores |

## Recommended Implementation Order

1. **v2 Seed JSON** — `RUNTIME_KNOWLEDGE_GRAPH_SEED_001` task: create REPO_GRAPH_NODES.jsonl + REPO_GRAPH_EDGES.jsonl with QS rules, Batch 3 extraction history, permanent flags, BATCH_3D defer decision
2. **v3 Query tool** — `tools/flaos/knowledge_graph.py` with blast_radius, safety_check, evidence queries
3. **v4 AST builder** — auto-generate call graph from trader.py using `ast` module
4. **v5 Runtime integration** — connect JSONL fields to function nodes

## Next Recommendation

`RUNTIME_KNOWLEDGE_GRAPH_SEED_001` — LOOP tier Class 4. Create the first operational seed files: `REPO_GRAPH_NODES.jsonl` (QS nodes + extraction history nodes) and `REPO_GRAPH_EDGES.jsonl` (protects, extracted_to, deferred_by, proxied_by edges). No Python tooling yet — pure JSONL authoring following the node/edge schemas.

## Final Verdict

```
RUNTIME_KNOWLEDGE_GRAPH_DESIGN_COMMITTED
```
