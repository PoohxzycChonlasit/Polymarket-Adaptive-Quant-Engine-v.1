# MEMORY_OS_V2_DESIGN_001

**Date:** 2026-06-27 · **Tier:** GATE Class 2 · **Repairs:** 0

## Files Created

| File | Content |
|------|---------|
| `docs/architecture/MEMORY_OS_V2_001.md` | 45-section design: 20 memory layers, router, retrieval engine, ranking, confidence, compression, archive policy, index, graph, relationships, tags, lifecycle, versioning, GC, validation, consistency, replay, explainability, provenance, evidence, governance, JSON schema, migration plan v2a–v4, 2 Mermaid diagrams, risks, verification plan |

## Architecture Summary

**20 memory layers:**

| Layer | Lifecycle | Format |
|-------|-----------|--------|
| Working | Session only | In-process dict |
| Session | 7 days | JSONL per session |
| Loop | 30 days → archive | JSONL per day |
| Decision | 90 days | `decision/DECISION_MEMORY.jsonl` |
| Failure | 180 days | `failure/FAILURE_MEMORY.jsonl` |
| Repair | 180 days | `repair/REPAIR_MEMORY.jsonl` |
| Execution | 60 days | `execution/EXECUTION_MEMORY.jsonl` |
| Runtime | 60 days | `runtime/RUNTIME_MEMORY.jsonl` |
| Repository | PERMANENT (extractions) | `repository/REPO_MEMORY.jsonl` |
| Research | 365 days | `research/RESEARCH_MEMORY.jsonl` |
| Quant Knowledge | PERMANENT (validated) | `quant/QUANT_KNOWLEDGE.jsonl` |
| Tool | Rolling 50/tool | `tool/TOOL_MEMORY.jsonl` |
| Skill | 90 days | `skill/SKILL_MEMORY.jsonl` |
| Agent | 90 days | `agent/AGENT_MEMORY.jsonl` |
| Planning | 90 days | `planning/PLANNING_MEMORY.jsonl` |
| **Safety** | **PERMANENT** | **`safety/SAFETY_MEMORY.jsonl`** |
| Permanent | PERMANENT | `permanent/PERMANENT_MEMORY.jsonl` |
| Archive | 5 years | `archive/YYYY/MM/*.jsonl.gz` |
| Memory Health | Snapshot | `MEMORY_HEALTH.json` |

**Key advances over v1:**
- JSONL per-type files instead of daily JSON arrays → grep-able, appendable, no full-file load
- `MEMORY_INDEX.json` with `line_offset` for O(1) record retrieval
- Hot/Warm/Cold/Archive/Permanent compression tiers
- Memory Graph for typed relationships between entries
- Retrieval ranking: recency + task_match + confidence + importance + evidence
- Garbage collection with orphan check before delete
- Memory Kernel enforces governance (Safety Memory: Role 29 only)

**Migration phases:** v2a (migrate v1 JSON → JSONL) → v2b (generate index) → v2c (memory_os.py tool) → v2d (seed safety memory) → v3 (graph) → v4 (health dashboard)

## Next Recommended Task

**`MEMORY_OS_V2_IMPLEMENTATION_001`** — LOOP tier Class 4. Implement:
1. `tools/flaos/memory_migrate.py` — converts v1 daily JSON arrays → JSONL typed files
2. `tools/flaos/memory_os.py` — read/write/query/validate CLI (stdlib only)
3. `MEMORY_INDEX.json` — generated from migrated files
4. Pre-seed `SAFETY_MEMORY.jsonl` with QS-001 through QS-010

## Final Verdict

```
MEMORY_OS_V2_DESIGN_COMMITTED
```
