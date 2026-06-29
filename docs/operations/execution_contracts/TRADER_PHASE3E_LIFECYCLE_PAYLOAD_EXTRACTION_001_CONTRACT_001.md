# EXECUTION CONTRACT

**Schema:** `execution_contract_v2.1`  
**Task ID:** TRADER_PHASE3E_LIFECYCLE_PAYLOAD_EXTRACTION_001  

---

## SECTION 1 — CONTRACT METADATA

```
contract_id:       CONTRACT-20260629-PHASE3E-001
created_at:        2026-06-29T13:07:50+07:00
plan_id:           MANUAL
bootstrap_sha:     2da4503a
bootstrap_status:  HEALTHY
safety_memory_status: HEALTHY
safety_memory_count: 10
```

---

## SECTION 2 — TASK IDENTITY

```
task_id:           TRADER_PHASE3E_LIFECYCLE_PAYLOAD_EXTRACTION_001
task_class:        6
description:       Extract lifecycle payload/read-only observability helpers from polymarket/trader.py into polymarket/observability/trader_lifecycle_payload.py while preserving exact behavior through backward-compatible wrapper delegation.
source_task:       TRADER_PHASE3E_LIFECYCLE_PAYLOAD_EXTRACTION_001

trader_py_lines_before:  12274
expected_line_delta:     -400
```

---

## SECTION 3 — WORKFLOW TIER

```
workflow_tier:     LOOP
risk_score:        2
complexity_score:  3
full_accept_override: false
```

---

## SECTION 4 — AGENT PIPELINE

```
agent_pipeline_id: REFACTOR_PIPELINE
role_sequence:     [29_ARCHITECTURE_GOVERNANCE, 02_CODE_ARCHITECT, 07_TEST_CI, 24_REPOSITORY_LIBRARIAN]
primary_role:      29_ARCHITECTURE_GOVERNANCE
```

**Role responsibilities this loop:**
- `29_ARCHITECTURE_GOVERNANCE`: Enforces QS rules, confirms forbidden scope (no risk/sizing/live/wallet mods).
- `02_CODE_ARCHITECT`: Refactor design, modular extraction, site wrapping.
- `07_TEST_CI`: Focused test creation, equivalence assertion.
- `24_REPOSITORY_LIBRARIAN`: Document routing, file placement, state updates.

---

## SECTION 5 — TOOL PIPELINE

```
tool_pipeline_id:  REFACTOR_TOOLS
```

**Ordered tool sequence** (check each when complete):
- [ ] `view_file` (inspect methods in trader.py)
- [ ] `write_to_file` (create trader_lifecycle_payload.py)
- [ ] `replace_file_content` (modify trader.py, wrappers)
- [ ] `write_to_file` (create test_trader_lifecycle_payload.py)
- [ ] `run_command` (py_compile and pytest execution)

---

## SECTION 6 — SKILL LIST

```
skills: [uv, workflow-skill-creator]
```

**Skill outputs required:**
- None.

---

## SECTION 7 — ALLOWED FILES

```
allowed_files:
  - polymarket/trader.py
  - polymarket/observability/trader_lifecycle_payload.py
  - tests/observability/test_trader_lifecycle_payload.py
  - docs/reports/TRADER_PHASE3E_LIFECYCLE_PAYLOAD_EXTRACTION_001.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json
```

---

## SECTION 8 — FORBIDDEN FILES (ALWAYS)

The following are permanently forbidden regardless of task scope:

```
forbidden_always:
  - _phase4_build_quote_lineage      (QS-001)
  - _phase4_quote_lineage_carry      (QS-002)
  - _last_quote_lineage_context      (QS-003)
  - _risk_plan_zero_diagnostics      (QS-004)
  - _diagnostic_float                (QS-005)
  - _diagnostic_int                  (QS-006)
  - polymarket/client.py live methods (QS-007)
  - .env live flags                  (QS-008)
  - runtime/ data deletion           (QS-009)
  - execution/risk/sizing/reconciliation without GATE (QS-010)

task_specific_forbidden:
  - Any logic inside risk/sizing/execution/reconciliation/live-ordering paths.
```

---

## SECTION 9 — SAFETY MEMORY CONFIRMATION

```
safety_memory_required: true
safety_memory_loaded:   true
safety_memory_ids_spot_check:
  - QS-001 present: yes
  - QS-005 present: yes
  - QS-010 present: yes
```

---

## SECTION 10 — MEMORY READS

**Memory reads performed before execution:**
- [x] Safety Memory (QS-001..010) — checked
- [x] Decision Memory — Checked Phase 3D report
- [x] Failure Memory — Checked deferred list reasons
- [x] Repository Memory — Checked ACTIVE_WORKFLOW_STATE

---

## SECTION 10b — KNOWLEDGE GRAPH EVIDENCE (CLASS 6+ MANDATORY)

```
graph_query_results_file:  docs/operations/graph_queries/TRADER_PHASE3E_LIFECYCLE_PAYLOAD_EXTRACTION_001.md

knowledge_graph_evidence:
  safety_check_query_id:   QUERY-20260629-PHASE3E-001
  safety_findings:         ["QS-005: calls _diagnostic_float", "QS-006: calls _diagnostic_int"]
  safety_stop_triggered:   false
  blast_radius_score:      LOW
  blast_radius_query_id:   QUERY-20260629-PHASE3E-001
  evidence_for_commit_grade: B
  evidence_query_id:       QUERY-20260629-PHASE3E-001
  deferred_history:        ["_phase2_complete_lifecycle_observability", "_phase2_observability_payload"]
  why_deferred_query_id:   QUERY-20260629-PHASE3E-001
  graph_confidence:        0.9
  graph_timestamp:         2026-06-27
  graph_query_ids:         [QUERY-20260629-PHASE3E-001]
  stop_condition_triggered: false
```

---

## SECTION 11 — REQUIRED TOOLS (ORDERED)

List tools in execution order with expected outcome:

| # | Tool ID | Expected outcome | Evidence grade |
|---|---------|-----------------|----------------|
| 1 | `write_to_file` | Create trader_lifecycle_payload.py | B |
| 2 | `replace_file_content` | Refactor trader.py wrapper methods | B |
| 3 | `write_to_file` | Create test_trader_lifecycle_payload.py | C |
| 4 | `run_command` (py_compile) | Ensure compilation passes | B |
| 5 | `run_command` (pytest) | Targeted unit tests pass | C |

```
evidence_baseline_test_count: 819
evidence_baseline_failures:   0
```

---

## SECTION 12 — REQUIRED EVIDENCE

```
evidence_required:     C
evidence_plan:
  - D: git_status_clean, scope_check
  - B: py_compile + import_ok + scope_check
  - C: + pytest
```

**Evidence accumulation log** (fill during execution):
- [ ] D — git scope confirmed
- [ ] B — compile + import clean
- [ ] C — tests pass

---

## SECTION 13 — STOP CONDITIONS

**Immediate STOP (no repair) if any of:**
- [ ] Forbidden file in `git diff` (QS-001..010 or task_specific_forbidden)
- [ ] Live trading keyword in any command
- [ ] Safety memory missing/invalid for required task
- [ ] Runtime data deletion detected
- [ ] Wallet/bankroll/allowance changes in diff
- [ ] Unrelated tracked dirty files at commit time
- [ ] `repair_count == max_repairs` AND still failing

**Task-specific stop conditions:**
- Modifying any risk, sizer, order submission, or live client path logic in `trader.py`.

---

## SECTION 14 — REPAIR POLICY

```
max_repairs:           3
repair_scope_limit:    allowed_files
```

**Repairable failures:**

| Failure class | Repairable? | Max | Action |
|--------------|-------------|-----|--------|
| compile_error | YES | 2 | Fix syntax in allowed files |
| import_error | YES | 2 | Fix import path |
| unit_test_failure | YES | 3 | Fix in allowed files only |
| scope_violation | **NO** | 0 | STOP |
| git_state_violation | **NO** | 0 | STOP |

**Repair log** (fill during execution):
- Repair #1: N/A
- Repair #2: N/A

---

## SECTION 15 — COMMIT POLICY

```
commit_policy:         TYPE_A_FIRST_THEN_TYPE_C
```

**Planned commits:**

| Commit # | Files | Type | Message |
|----------|-------|------|---------|
| 1 | polymarket/trader.py, polymarket/observability/trader_lifecycle_payload.py, tests/observability/test_trader_lifecycle_payload.py | TYPE A | "refactor: extract trader lifecycle payload helpers" |
| 2 | docs/reports/TRADER_PHASE3E_LIFECYCLE_PAYLOAD_EXTRACTION_001.md, docs/operations/ACTIVE_WORKFLOW_STATE_001.json, docs/operations/TASK_QUEUE_001.json, docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json | TYPE C | "docs: update phase 3e refactor logs" |

---

## SECTION 16 — HUMAN AUTHORIZATION (Class 8 / Destructive only)

```
requires_human_authorization: false
authorization_received: false
```

---

## SECTION 17 — MEMORY WRITES (Post-Commit)

```
memory_writes_planned:
  - loop: Appending Phase 3E extraction summary to LOOP_MEMORY_20260628_001.json
  - decision: N/A
  - failure: N/A
  - repair: N/A
  - runtime: N/A
```

**Memory write checklist** (complete after commit):
- [ ] Loop Memory appended to `LOOP_MEMORY_20260628_001.json`
- [ ] ACTIVE_WORKFLOW_STATE_001.json updated
- [ ] TASK_QUEUE_001.json updated

---

## SECTION 18 — VERIFICATION CHECKLIST

Before commit, confirm ALL:

```
[ ] git diff --name-only shows only allowed_files
[ ] git diff -- [files] | grep "[forbidden_patterns]" → empty
[ ] No root markdown created
[ ] py_compile PASS (if Python files changed)
[ ] IMPORT_OK (if Python files changed)
[ ] Tests pass vs baseline (if applicable)
[ ] Safety memory still loaded (bootstrap --diagnose)
[ ] working_tree contains only allowed staged files
```

---

## SECTION 19 — FINAL OUTPUT CONTRACT

At loop completion, declare:

```
FINAL_VERDICT:     [COMMITTED | STOPPED | ESCALATED]
TASK:              TRADER_PHASE3E_LIFECYCLE_PAYLOAD_EXTRACTION_001
COMMITS:           [sha] — [message]
FILES_CHANGED:     [N] ([detail])
TESTS:             [pass count]
RUNTIME:           N/A
FORBIDDEN_SCOPE:   confirmed
STATE_QUEUE_MEMORY: [what was updated]
NEXT:              [next_task_id]
```
