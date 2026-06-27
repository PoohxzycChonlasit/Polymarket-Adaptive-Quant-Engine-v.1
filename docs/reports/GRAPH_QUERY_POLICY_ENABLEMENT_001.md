# GRAPH_QUERY_POLICY_ENABLEMENT_001

**Date:** 2026-06-27 · **Tier:** LOOP Class 3 · **Repairs:** 0

## Files Changed

| File | Change |
|------|--------|
| `PROJECT_RULES.md` | +Knowledge Graph Query Policy section (CLASS 6+ mandate, stop condition, contract fields) |
| `AGENTS.md` | +Knowledge Graph Query Requirement section |
| `MASTER_AGENT_ROUTER.md` | +Knowledge Graph Query Gate section |
| `docs/operations/LOOP_ENGINEERING_PLAYBOOK_001.md` | +Section 4a (graph query by class) |
| `docs/operations/EXECUTION_CONTRACT_TEMPLATE_001.md` | +Section 10b `knowledge_graph_evidence` block |

## Policy Summary

**CLASS 6 minimum:** `safety_check` + `blast_radius` + `evidence_for_commit`  
**CLASS 7+ additional:** + `why_deferred` + `dependency_tree`

**New stop condition: `GRAPH_QUERY_NOT_EXECUTED`**  
Planner and Execution Engine refuse to proceed with CLASS 6+ loops if the `knowledge_graph_evidence` block is absent from the Execution Contract.

## Execution Contract Update (v2.2)

Section 10b added with 13 required fields:
- `safety_findings` — QS entries triggered
- `blast_radius_score` — LOW/MEDIUM/HIGH
- `deferred_history` — previously-deferred methods in scope
- `evidence_for_commit_grade` — A/B/C/D
- `graph_confidence` — float 0–1
- `graph_timestamp` — ISO date of graph snapshot
- `graph_query_ids` — list of QUERY-* IDs executed
- `stop_condition_triggered` — GRAPH_QUERY_NOT_EXECUTED if missing

## Why This Matters

The smoke test proved all 4 query types work correctly against live seeded JSONL. Policy without mandate = optional tool. Mandate without policy = unenforceable. This commit connects the two: the smoke test proved it works, the policy makes it required.

**Historical example:** Batch 3D would have been correctly predicted as DEFER even without a gate check, if a `blast_radius("_phase2_observability_payload")` query had been run — QS-005/006 blocks edge was already in the seed data.

## Final Verdict

```
GRAPH_QUERY_POLICY_ENABLED
CLASS 6+ mandate: effective immediately
STOP condition GRAPH_QUERY_NOT_EXECUTED: active
Contract template: v2.2 with knowledge_graph_evidence block
```
