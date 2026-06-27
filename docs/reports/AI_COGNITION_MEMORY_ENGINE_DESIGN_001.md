# AI_COGNITION_MEMORY_ENGINE_DESIGN_001

**Date:** 2026-06-27 · **Tier:** GATE Class 2 · **Repairs:** 0

## Files Created

| File | Content |
|------|---------|
| `docs/architecture/AI_COGNITION_MEMORY_ENGINE_001.md` | 12-section design: 10 cognition layers, read/write paths, schema, retrieval policy, forget/compact, integration, quant safety, 4 Mermaid diagrams, migration v1-v5 |
| `docs/operations/AI_COGNITION_MEMORY_SCHEMA_001.json` | 8 memory record type schemas with required fields, examples, retention policies |
| `docs/reports/AI_COGNITION_MEMORY_ENGINE_DESIGN_001.md` | This report |

## Why ACME vs Loop Memory

Loop Memory = event log (what happened). ACME = structured knowledge (why it happened, what was learned, how to avoid repeating failures).

## 10 Cognition Layers

| Layer | Storage | Expires |
|-------|---------|---------|
| Working Memory | Session only | After NEXT_OR_STOP |
| Long-Term Loop Memory | LOOP_MEMORY_*.json | Monthly archive |
| Decision Memory | decision/ | 90 days |
| Failure Memory | failure/ | 180 days |
| Repair Memory | repair/ | 180 days |
| Tool Usage Memory | tool_usage/ | Rolling 30 entries |
| Repository Memory | repository_insight/ | PERMANENT |
| **Quant Safety Memory** | **quant_safety/** | **PERMANENT — NEVER EXPIRES** |
| Runtime Evidence Memory | runtime_evidence/ | 60 days |
| Agent Skill Memory | agent_skill/ | 90 days |

## Pre-Seeded Quant Safety Entries (QS-001 through QS-010)

Entries for `_phase4_*`, `_last_quote_lineage_context`, `_risk_plan_zero_diagnostics`, `_diagnostic_float/_int`, live order methods, `.env` live flags, `arb_auto_execute`, runtime data deletion, and wallet/bankroll mutation. All marked severity=CRITICAL, expires=NEVER.

## Schema Summary

8 memory types with required fields, examples, retention policies, and compact rules. `quant_safety` and `repository_insight` are PERMANENT. All others have time/entry-based compaction.

## Migration v1→v5

v1 (NOW): spec only → v2: AI writes JSON entries after each loop → v3: Python query script → v4: vector/semantic search → v5: autonomous memory-assisted planner.

## Final Verdict

```
AI_COGNITION_MEMORY_ENGINE_DESIGN_COMMITTED
```
