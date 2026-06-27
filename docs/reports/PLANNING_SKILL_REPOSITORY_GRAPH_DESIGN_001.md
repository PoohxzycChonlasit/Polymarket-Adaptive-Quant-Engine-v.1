# PLANNING_SKILL_REPOSITORY_GRAPH_DESIGN_001

**Date:** 2026-06-27 · **Tier:** GATE Class 2 · **Repairs:** 0

## Files Created

| File | Content |
|------|---------|
| `docs/architecture/PLANNING_ENGINE_001.md` | Planning Engine: PlanContract, risk/complexity scoring, full accept override, Mermaid flow, migration v1-v5 |
| `docs/architecture/SKILL_ENGINE_001.md` | Skill Engine: 8 skill examples, registry schema, selection rules, tool/agent/memory integration |
| `docs/architecture/REPOSITORY_GRAPH_ENGINE_001.md` | Repository Graph Engine: 10 node types, 10 edge types, graph schema, impact analysis, quant safety constraints |
| `docs/reports/PLANNING_SKILL_REPOSITORY_GRAPH_DESIGN_001.md` | This report |

## Architecture Summary

**Planning Engine:** Synthesizes all available context (state, queue, memory, pipelines, skills, graph) into a `PlanContract` before execution. Adds risk_score and complexity_score dimensions not present in the Agent or Tool pipelines. Full accept can be blocked by risk_score > 50, quant safety violations, or active question blocks.

**Skill Engine:** Composable units between agent roles and tools. Each skill packages reasoning + tool sequence + memory writes into a named artifact. 8 skills defined: gate_check, low_risk_refactor, runtime_validation, docs_housekeeping, repository_audit, jsonl_evidence_scan, forbidden_scope_check, quant_safety_review. `quant_safety_review` is ALWAYS prepended for tasks touching Python files.

**Repository Graph Engine:** Directed graph with 10 node types (file, module, class, function, test, script, tool, config, runtime_artifact, report) and 10 edge types (imports, calls, tests, writes, reads, owns, documents, validates, is_permanent, proxied_by). Enables blast radius queries, proxy chain traversal, and permanent method protection. Quant safety constraints hardcoded: permanent methods cannot appear in `moved_from` edges.

## Why These Systems Are Needed

1. **Planning Engine:** Agent + Tool pipelines select WHAT to do. The Planning Engine selects WHICH pipeline and adds risk/complexity intelligence to prevent wrong tier selection.
2. **Skill Engine:** Fills the gap between "which role" and "which specific sequence of reasoning". Skills are reusable — the same `runtime_validation` skill can be used by GATE, LOOP, and post-commit validation pipelines.
3. **Repository Graph Engine:** Current grep-based call site discovery is fragile. The graph enables structured impact analysis: "if I move method X, what breaks?" answered from the graph, not from trial and error.

## Recommended Implementation Order

1. **v1 (NOW):** These design specs committed
2. **v2:** Skill Registry JSON (`docs/operations/skills/SKILL_REGISTRY_001.json`) with 8 initial skills — LOOP tier Class 3 task
3. **v3:** Repository Graph Seed (`docs/operations/REPO_GRAPH_SEED_001.json`) with known permanent methods and Batch 3 extraction history — LOOP tier Class 3
4. **v4:** Planning Engine checklist template (v2 Planning Engine) — After Batch 3D gate
5. **v5:** Python AST graph generator — Phase 3 FLAOS

## Next Task Recommendation

**`SKILL_REGISTRY_ENABLEMENT_001`** (LOOP tier, Class 3) — Create `docs/operations/skills/SKILL_REGISTRY_001.json` with 8 initial skills as machine-readable JSON. Low risk, high value for Planning Engine v2.

**OR** `BATCH_3D_GATE_CHECK_001` (GATE tier) — run in parallel with skill registry.

## Final Verdict

```
PLANNING_SKILL_REPOSITORY_GRAPH_DESIGN_COMMITTED
```
