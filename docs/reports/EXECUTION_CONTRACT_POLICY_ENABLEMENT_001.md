# EXECUTION_CONTRACT_POLICY_ENABLEMENT_001

**Date:** 2026-06-27 · **Tier:** LOOP Class 3 · **Repairs:** 0

## Policy Changes

### PROJECT_RULES.md
Added **Execution Contract Policy** section:
- Full contract mandatory for CLASS 6/7/8, STANDARD/GATE tier, Python/runtime/tooling/destructive tasks
- Abbreviated contract (Sections 1/2/7/13/18/19) for CLASS 0/3/9 read-only and docs-only
- CLASS 8 requires Section 16 (human authorization, exact scope, irreversibility statement)
- Contract must be completed BEFORE implementation begins or `execute --confirm` runs

### AGENTS.md
Added **Execution Contract Requirement** section:
- Template path, save path, and class-specific requirements
- Stop condition: full contract required but not declared → STOP_AND_ESCALATE

### LOOP_ENGINEERING_PLAYBOOK_001.md
Added **Section 4b — Execution Contract Policy** covering full vs abbreviated requirements and CLASS 8 rules.

## Template Changes (v2 → v2.1)

Two gaps from smoke test (`EXECUTION_CONTRACT_SMOKE_TEST_001`) addressed:

| Gap | Section patched | Change |
|-----|----------------|--------|
| `evidence_baseline` missing | Section 11 | Added `evidence_baseline_test_count` and `evidence_baseline_failures` fields |
| `trader_py_lines_before` missing | Section 2 | Added `trader_py_lines_before` and `expected_line_delta` for refactor tasks |

## Smoke Test Basis

Smoke test (`EXECUTION_CONTRACT_SMOKE_TEST_001`) retrospectively filled the template for `BATCH_3C_IMPLEMENTATION_001`:
- All 19 active sections populated
- 2 non-blocking gaps identified (now patched)
- Template coverage: 100%
- Verdict: SUFFICIENT for mandate

## When Full vs Abbreviated Contract

| Task type | Contract | Sections |
|-----------|---------|---------|
| CLASS 6 LOOP refactor | Full | All 20 |
| CLASS 7 GATE feature | Full | All 20 |
| CLASS 8 destructive/live | Full + Section 16 | All 20 + auth |
| STANDARD/GATE any | Full | All 20 |
| CLASS 0 health check | Abbreviated | 1,2,7,13,18,19 |
| CLASS 3 docs housekeeping | Abbreviated | 1,2,7,13,18,19 |
| CLASS 9 env diagnostics | Abbreviated | 1,2,7,13,18,19 |

## Enforcement Limitations

The policy is currently enforced by convention (AI must fill the contract), not by tooling. The v3 Python executor (`EXECUTION_ENGINE_IMPLEMENTATION_001` Phase 3) will programmatically reject loops that do not declare a valid contract before execution. Until then, contract declaration is a required step in every CLASS 6+ loop prompt.

## Next Recommendation

`RUNTIME_KNOWLEDGE_GRAPH_DESIGN_001` — GATE tier Class 2. Seed the repository knowledge graph with permanent methods (QS-001..006) and Batch 3 extraction history. This creates the first operational Repository Memory records in Memory OS V2 and enables blast-radius queries for future refactor batches.

## Final Verdict

```
EXECUTION_CONTRACT_POLICY_ENABLED
CLASS 6+ mandate: effective immediately
Template: v2.1 (evidence_baseline + trader_py_lines_before added)
```
