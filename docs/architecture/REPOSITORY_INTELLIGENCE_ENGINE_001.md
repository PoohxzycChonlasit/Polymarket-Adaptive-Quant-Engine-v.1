# REPOSITORY_INTELLIGENCE_ENGINE_001

**Date:** 2026-06-27  
**Document type:** Architecture design  
**Destination:** `docs/architecture/`  
**Status:** DESIGN — Phase 4 implementation target

---

## 1. Purpose

The Repository Intelligence Engine (RIE) replaces the current ad-hoc "read 5 files in order" context load with a structured, validated snapshot of project state. It runs at session start and produces a `RepositorySnapshot` that all downstream engines consume.

---

## 2. Inputs (read in declared order, < 500 tokens total)

```
1. PROJECT_RULES.md           — governance constraints
2. MASTER_AGENT_ROUTER.md     — role routing
3. ACTIVE_WORKFLOW_STATE_001.json  — current state
4. TASK_QUEUE_001.json         — next actions
5. loop_memory/LOOP_MEMORY_*.json  — recent history
```

Optional (read only if snapshot detects gaps):
```
6. git log -12 --oneline       — commit verification
7. CURRENT_PROJECT_STATUS.md  — if state is stale > 7 days
```

---

## 3. RepositorySnapshot Schema

```json
{
  "$schema": "repository_snapshot_v1",
  "generated_at": "ISO timestamp",
  "phase": "string — from active state",
  "next_task": "string",
  "next_tier": "FAST|LOOP|STANDARD|GATE",
  "blocked": false,
  "active_question_blocks_refactor": false,
  "trader_py_lines": 12775,
  "refactor_batch_current": "3C",
  "refactor_batch_next": "3D",
  "last_runtime_refactor_commit": "3c5b781",
  "last_loop_result": "PASS",
  "last_loop_repairs": 0,
  "last_loop_evidence_grade": "A",
  "loop_memory_entries": 10,
  "git_head_matches_state": true,
  "drift_detected": false,
  "drift_notes": null,
  "recommended_first_reads": ["array of files"],
  "governance": {
    "loop_engineering_enabled": true,
    "lre_version": "v1",
    "awe_status": "design_only"
  }
}
```

---

## 4. Drift Detection

RIE compares `ACTIVE_WORKFLOW_STATE.last_commit` against `git log HEAD --format="%h" -1`. If they differ:

| Condition | Action |
|-----------|--------|
| HEAD is ahead of state by 1-3 commits (docs-only) | Update state silently, no halt |
| HEAD is ahead by runtime commits | Flag `drift_detected: true`, require health check |
| HEAD is behind state (unexpected rewind) | `STOP_AND_ESCALATE` — git state inconsistency |
| Pending memory entries (SHA = "pending") | Flag for cleanup, proceed |

---

## 5. Active Question Evaluation

RIE reads `docs/research/ACTIVE_QUESTION.md` (if exists and < 30 days old) and sets:

```json
"active_question_blocks_refactor": false  // structural refactors not blocked
"active_question_blocks_strategy": true   // signal/sizer/execution changes blocked
```

This prevents the LRE from routing strategy tasks without surfacing the block.

---

## 6. Trader.py Line Count Tracking

RIE reads `trader.py` line count via `git show HEAD:polymarket/trader.py | wc -l` (or equivalent fast path). Stores in snapshot. FLAOS uses this to:

- Track decomposition progress (12,824 → 12,775 → target: ≤1,000)
- Flag if a refactor commit INCREASED the line count (unexpected) → alert

---

## 7. Output Consumption

```
RIE.snapshot → FLAOS routing decision
RIE.snapshot.next_task → LRE.INIT contract
RIE.snapshot.next_tier → LRE.CLASSIFY baseline
RIE.snapshot.drift_detected → force health check
RIE.snapshot.blocked → show notes before any action
```

---

## 8. Migration Plan

| Phase | Implementation |
|-------|---------------|
| v0 (now) | AI reads 5 files in declared order manually |
| v1 | Markdown checklist: AI fills snapshot fields before each session |
| v2 | JSON template: AI writes snapshot to `docs/operations/CURRENT_SNAPSHOT.json` |
| v3 | Shell script: auto-generates snapshot from files |
| v4 | Python module: `from tools.rie import RepositoryIntelligenceEngine; snap = RIE().snapshot()` |
