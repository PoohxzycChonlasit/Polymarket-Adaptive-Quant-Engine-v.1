# SKILL_ENGINE_001

**Date:** 2026-06-27 · **Destination:** `docs/architecture/` · **Status:** DESIGN v1

---

## 1. Objective

The Skill Engine (SE) defines reusable, composable units of AI capability that sit between Agent roles and Tool commands. A skill packages a common sequence of reasoning + tool invocations into a named, versioned artifact that the Planning Engine can select and sequence.

---

## 2. Difference Between Agent, Tool, and Skill

| Concept | What it is | Example |
|---------|-----------|---------|
| **Agent** | A role with declared responsibilities and context budget | `29_ARCHITECTURE_GOVERNANCE_AGENT`: gate checks, scope enforcement |
| **Tool** | A single command with declared inputs/outputs/grade | `py_compile_runtime`: runs `python -m py_compile {files}` |
| **Skill** | A named sequence of reasoning + tool invocations reusable across tasks | `gate_check`: load memory → grep call sites → score coupling → produce verdict |

Skills are composable: a `low_risk_refactor` skill uses `gate_check` + `compile_verify` + `test_verify` internally.

---

## 3. Skill Definition

```json
{
  "skill_id": "gate_check",
  "version": "1.0",
  "category": "governance",
  "description": "Perform architecture governance gate check for a refactor batch",
  "primary_agent": "29_ARCHITECTURE_GOVERNANCE_AGENT",
  "input_requirements": ["task_id", "candidate_methods", "allowed_scope", "forbidden_scope"],
  "output_contract": ["verdict: PROCEED|PAUSE|STOP", "candidate_matrix", "scope_boundaries"],
  "tool_sequence": ["read_active_workflow_state", "read_loop_memory", "forbidden_scope_diff_check", "write_final_report"],
  "memory_reads": ["quant_safety", "decision", "repository_insight"],
  "memory_writes": ["decision"],
  "evidence_produced": "B",
  "max_duration_minutes": 10,
  "stop_conditions": ["forbidden_scope_requested", "high_risk_keyword_in_scope"],
  "composable_with": ["low_risk_refactor", "docs_housekeeping"],
  "full_accept_policy": "gate_check verdict does not auto-accept — user must approve PROCEED"
}
```

---

## 4. Skill Package Layout

```
docs/operations/skills/
├── SKILL_REGISTRY_001.json          # index of all skills
├── gate_check/
│   ├── SKILL_GATE_CHECK_001.json    # skill definition
│   └── CHECKLIST.md                 # human-readable steps
├── low_risk_refactor/
│   ├── SKILL_LOW_RISK_REFACTOR_001.json
│   └── CHECKLIST.md
├── runtime_validation/
│   ├── SKILL_RUNTIME_VALIDATION_001.json
│   └── CHECKLIST.md
└── ...
```

---

## 5. Skill Registry Schema

```json
{
  "$schema": "skill_registry_v1",
  "skills": [
    {
      "skill_id": "string",
      "version": "string",
      "category": "governance|verification|validation|intelligence|housekeeping|safety",
      "description": "string",
      "primary_agent": "role_id",
      "tool_sequence": ["tool_id array"],
      "memory_reads": ["memory_type array"],
      "evidence_produced": "D|C|B|A",
      "composable_with": ["skill_id array"]
    }
  ]
}
```

---

## 6. Skill Examples

### `gate_check`
**Category:** governance · **Agent:** 29 · **Evidence:** B  
**Steps:** Load quant_safety → grep candidate methods → score coupling → produce verdict table → write to docs/audits/

### `low_risk_refactor`
**Category:** verification · **Agents:** 02, 27, 07 · **Evidence:** C  
**Steps:** Implement extraction → compile → import → pytest targeted → forbidden grep → write report  
**Composes:** `gate_check` (pre) + `runtime_validation` (optional post)

### `runtime_validation`
**Category:** validation · **Agent:** 28, 11 · **Evidence:** A  
**Steps:** Paper run 5 cycles → check exit 0 → check NO LIVE ORDERS → scan JSONL fields → write report

### `docs_housekeeping`
**Category:** housekeeping · **Agent:** 24 · **Evidence:** D  
**Steps:** Classify files → route to correct docs/ dir → git mv if tracked → commit TYPE C → update state/queue/memory

### `repository_audit`
**Category:** intelligence · **Agents:** 24, 02 · **Evidence:** B  
**Steps:** Read git ls-files → classify by type → check file counts → identify drift from expected structure → write audit report

### `jsonl_evidence_scan`
**Category:** validation · **Agent:** 11 · **Evidence:** A  
**Steps:** Identify session PID → scan event stream → count field occurrences → compare to pre-commit baseline → pass/fail per field

### `forbidden_scope_check`
**Category:** safety · **Agent:** 29, 27 · **Evidence:** B  
**Steps:** `git diff | grep forbidden_patterns` → check _phase4_*, _diagnostic_*, _risk_plan_zero → empty output = PASS → else STOP

### `quant_safety_review`
**Category:** safety · **Agent:** 29 · **Evidence:** B  
**Steps:** Load quant_safety memory → cross-reference with task scope → surface any CRITICAL entries that overlap → produce safety_clear or STOP

---

## 6b. Operational Registry (created 2026-06-27)

The skill registry is now operational at:

**`docs/operations/skills/SKILL_REGISTRY_001.json`** — 8 skills with full field schemas: skill_id, version, purpose, task_classes, workflow_tiers, agent_pipeline, tool_pipeline, required_tools, memory_reads/writes, evidence_required, stop_conditions, allowed/forbidden scopes, full_accept_allowed, repair_policy, skill_output_contract.

**Auto-prepend rule embedded in registry:** `quant_safety_review` automatically prepends for any task touching Python files, trading logic, risk/sizing/execution, wallet/bankroll, live trading, or runtime data deletion.

---

## 7. Skill Selection Rules

```
Planning Engine selects skills by:

1. Match task type → primary skill (e.g., Class 6 → low_risk_refactor)
2. Prepend mandatory skills:
   - quant_safety_review is ALWAYS prepended if Python files in scope
   - forbidden_scope_check is ALWAYS in scope for Class 6/7
3. Append post-skills based on evidence requirement:
   - GATE tier → append runtime_validation
   - LOOP tier → optional runtime_validation
4. Compose:
   - low_risk_refactor → [quant_safety_review, gate_check, low_risk_refactor, runtime_validation]
```

---

## 8. Skill/Tool Integration

Each skill declares a `tool_sequence` from `TOOL_REGISTRY_001.json`. The Tool Pipeline executes the sequence. Skills do not bypass tool stop conditions — tool failures propagate up to the skill's `stop_conditions`.

```
Skill → declares tool_sequence
Tool Pipeline → executes tools in order
Tool fails → Skill → REPAIR or STOP per tool's stop_on_fail
```

---

## 9. Skill/Agent Integration

Each skill declares a `primary_agent`. The Agent Pipeline provides the role's context budget and memory access policy. The skill provides the specific action sequence within that role's responsibility boundary.

```
Agent Pipeline → selects roles (who)
Skill Engine → selects skills (what sequence of reasoning)
Together → complete executable loop
```

---

## 10. Skill Memory Integration

Skills write to Cognition Memory after completion:

| Skill | Memory type written |
|-------|-------------------|
| `gate_check` | decision (why PROCEED/STOP) |
| `low_risk_refactor` | decision + repair (if repairs occurred) |
| `runtime_validation` | runtime_evidence (cycle count, JSONL fields) |
| `forbidden_scope_check` | quant_safety (if new violation found) |
| `repository_audit` | repository_insight |

---

## 11. Stop Conditions

Every skill inherits the global stop conditions from the Loop Runtime Engine. Additionally:

| Skill | Additional stop conditions |
|-------|--------------------------|
| `gate_check` | high_risk_method_in_scope |
| `low_risk_refactor` | forbidden_scope_in_diff, new_test_failure |
| `runtime_validation` | exit_code_not_0, attributeerror_in_log, live_orders_detected |
| `quant_safety_review` | CRITICAL quant_safety entry overlaps scope |
| `forbidden_scope_check` | ANY forbidden pattern found |

---

## 12. Migration Roadmap

| Phase | What ships | Trigger |
|-------|-----------|---------|
| v1 | Skill definitions as JSON + CHECKLIST.md | NOW (in docs/operations/skills/) |
| v2 | Skill Registry auto-loaded by Planning Engine | After v2 Planning Engine |
| v3 | Skills as Python functions in tools/skills/ | Phase 3 FLAOS |
| v4 | Skills compose automatically via dependency graph | Phase 4 FLAOS |
| v5 | Autonomous skill discovery from Cognition Memory patterns | Phase 5 FLAOS |
