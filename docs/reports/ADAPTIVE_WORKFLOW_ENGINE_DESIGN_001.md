# ADAPTIVE_WORKFLOW_ENGINE_DESIGN_001

**Date:** 2026-06-27  
**Mode:** LOOP_ENGINEERING — Task Class 2 (DESIGN_ONLY)  
**Repairs:** 0  
**Destination:** `docs/reports/`

---

## Files Created

| File | Lines | Type |
|------|-------|------|
| `docs/architecture/ADAPTIVE_WORKFLOW_ENGINE_001.md` | ~350 | Design |
| `docs/reports/ADAPTIVE_WORKFLOW_ENGINE_DESIGN_001.md` | This file | Report |

No Python files. No dashboard. No runtime exports. No root markdown.

---

## Design Summary

### Current Workflow → Target Workflow

| Aspect | Current | Target (AWE) |
|--------|---------|-------------|
| Tier selection | Manual — user specifies task class | Automatic — Difficulty Estimator + Context Resolver |
| Memory use | Ad-hoc — AI reads long reports | Structured — Loop Memory JSON as first-read context |
| Repair loops | Manual — user re-prompts | Autonomous — up to 3 repairs within declared scope |
| Evidence collection | Unstructured prose | Graded (A/B/C/D), minimum per tier enforced |
| Report output | Per-step intermediate reports | Single consolidated final report per loop |
| Agent routing | Manual role selection | AI Skill Router — keyword + scope → role mapping |
| Commit planning | Manual type assignment | Commit Planner — file-type-based split |
| Analytics | None | Analytics Engine — weekly loop health metrics |

### 13 Components Designed

Workflow Selector → Difficulty Estimator → Context Resolver → Loop Executor → Repair Engine → Evidence Planner → Runtime Validator → Commit Planner → Loop Memory Engine → Analytics Engine → AI Skill Router → Future Multi-Agent Scheduler + Migration Roadmap

### Key Diagrams

- System-level component graph (Mermaid flowchart)
- Workflow Selector decision tree
- Happy path, repair path, gate path sequence diagrams
- Memory write sequence
- Multi-agent parallel scheduler (Phase 3)
- Repair decision tree
- Tier selection decision tree

### Migration Phases

| Phase | Timing | What ships |
|-------|--------|-----------|
| 0 | COMPLETE | Loop Engineering Playbook, Loop Memory spec, smoke test |
| 1 | Batch 3C period | Memory as first-read, Analytics Engine, AI Skill Router |
| 2 | Post-Batch 3C | Difficulty Estimator, Context Resolver, Evidence Planner formal |
| 3 | Long-term | Multi-Agent Scheduler, automated consolidation, analytics dashboard |

### Top Risks

- Difficulty Estimator under-scoring a high-risk task (HIGH) — mitigated by mandatory GATE for execution/risk/sizing
- Memory file growing beyond context window (MEDIUM) — monthly archive planned
- Parallel loop git conflicts (HIGH) — strict file-level isolation before enabling

---

## Final Verdict

```
ADAPTIVE_WORKFLOW_ENGINE_DESIGN_COMMITTED
```
