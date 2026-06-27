# LOOP_RUNTIME_STATE_SCHEMA_001

**Date:** 2026-06-27  
**Document type:** Operations schema reference  
**Destination:** `docs/operations/`

---

## Purpose

Quick reference for all JSON schemas used by the Loop Runtime Engine v1. See `docs/architecture/LOOP_RUNTIME_ENGINE_V1.md` for full state machine design.

---

## Schema: `loop_contract_v1` (INIT state)

```json
{
  "$schema": "loop_contract_v1",
  "task_id": "string — e.g. BATCH_3C_GATE_CHECK_001",
  "task_class": "int 0-9",
  "workflow_tier": "FAST | LOOP | STANDARD | GATE",
  "allowed_files": ["array of file paths or glob patterns"],
  "forbidden_scope": ["array — minimum: polymarket/, tests/, runtime/, dashboard/, config/"],
  "acceptance_criteria": {"criterion_name": "description string"},
  "max_repairs": "int 0-3",
  "current_repair_count": 0,
  "evidence_required": "D | C | B | A",
  "commit_policy": "TYPE_A | TYPE_B | TYPE_C | TYPE_D | SPLIT",
  "memory_policy": "append_after_commit",
  "state_update_policy": "update_last_completed_and_next_task",
  "queue_update_policy": "mark_task_complete_advance_next"
}
```

---

## Schema: `loop_memory_v1` (MEMORY_WRITE state)

```json
{
  "$schema": "loop_memory_v1",
  "date": "YYYY-MM-DD",
  "loop_id": "string",
  "task_class": "int",
  "result": "PASS | PARTIAL | FAIL",
  "repairs": "int",
  "evidence_grade": "D | C | B | A",
  "commits": ["array of short SHAs"],
  "forbidden_scope_confirmed": "bool",
  "acceptance_criteria": {"criterion": "bool"},
  "next_recommendation": "string",
  "workflow_tier_recommendation": "optional string"
}
```

---

## Schema: `active_workflow_state_v1` (STATE_UPDATE)

```json
{
  "$schema": "active_workflow_state_v1",
  "last_updated": "YYYY-MM-DD",
  "current_phase": "string",
  "last_completed_task": "string",
  "last_commit": "short SHA",
  "next_task": "string",
  "next_workflow_tier": "FAST | LOOP | STANDARD | GATE",
  "working_tree_expected": "clean | dirty-allowed",
  "blocked": "bool",
  "refactor_state": {"trader_py_lines": "int", "next_batch": "string"},
  "workflow_governance": {"loop_engineering_enabled": "bool"},
  "recommended_first_reads": ["array ordered by read priority"]
}
```

---

## Schema: `task_queue_v1` (QUEUE_UPDATE)

```json
{
  "$schema": "task_queue_v1",
  "queue": [
    {
      "priority": "int",
      "task_id": "string",
      "status": "READY | WAITING_FOR_GATE | BLOCKED_UNTIL_DESIGN_APPROVAL | IN_PROGRESS | DONE | OPTIONAL",
      "workflow_tier": "FAST | LOOP | STANDARD | GATE",
      "task_class": "int",
      "description": "string",
      "blocked_by": "string | null",
      "allowed_scope": ["array"],
      "outputs": ["array of expected output files"],
      "notes": "string"
    }
  ]
}
```

---

## Schema: `loop_analytics_v1` (optional, post-commit)

```json
{
  "$schema": "loop_analytics_v1",
  "task_id": "string",
  "date": "YYYY-MM-DD",
  "workflow_tier": "string",
  "task_class": "int",
  "repair_count": "int",
  "failure_classes": ["array of failure class strings"],
  "evidence_grade": "D | C | B | A",
  "files_changed": "int",
  "net_lines": "int",
  "commit_count": "int",
  "runtime_cycles": "int (0 if no paper run)",
  "token_saving_estimate": "int (approximate tokens saved vs reading full reports)",
  "result": "PASS | PARTIAL | FAIL",
  "stop_reason": "string | null",
  "duration_estimate_minutes": "int"
}
```

---

## Evidence Grade Quick Reference

| Grade | Required when | Commands |
|-------|--------------|---------|
| D | Docs-only loop | `git diff --name-only` |
| C | Any code change + test suite needed | `pytest -q` |
| B | Any code change | `py_compile` + `IMPORT_OK` |
| A | Refactor with runtime telemetry | 5-cycle paper run + JSONL field check |

---

## Workflow Tier Quick Reference

| Tier | Task Classes | Max Repairs | Evidence |
|------|------------|-------------|---------|
| FAST | 0,3,9 (prior PASS) | 1 | D |
| LOOP | 0,3,4,9 | 3 | B |
| LOOP+ | 6-low | 3 | B+C |
| STANDARD | 6-high, 1 | 3 | B+C |
| GATE | 7 | 3 | A+C |
| GATE-LIVE | 8 | 0 (manual) | A+manual |
