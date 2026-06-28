# EXECUTION CONTRACT

**Schema:** `execution_contract_v2.1`
**Task ID:** `REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001`
**Purpose:** Reorganize the three provisional free-source outcome truth tools into tools/outcome_truth/ and update only their targeted tests.

---

## SECTION 1 — CONTRACT METADATA

```
contract_id:       CONTRACT-20260628-OUTCOME_TRUTH_MOVE-001
created_at:        2026-06-28T07:55:00Z
plan_id:           MANUAL
bootstrap_sha:     ac6da13
bootstrap_status:  HEALTHY
safety_memory_status: LOADED
safety_memory_count: 10
```

---

## SECTION 2 — TASK IDENTITY

```
task_id:           REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001
task_class:        6
description:       Move the three provisional free-source outcome truth tools into tools/outcome_truth/ and update only their targeted tests.
source_task:       REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001
```

---

## SECTION 3 — WORKFLOW TIER

```
workflow_tier:     LOOP
risk_score:        2
complexity_score:  2
full_accept_override: false
```

---

## SECTION 4 — AGENT PIPELINE

```
agent_pipeline_id: LOW_RISK_REFACTOR_LOOP
role_sequence:     ['29_ARCHITECTURE_GOVERNANCE_AGENT', '02_CODE_ARCHITECT_AGENT', '27_VERIFICATION_OFFICER_AGENT', '24_REPOSITORY_LIBRARIAN_AGENT', '29_ARCHITECTURE_GOVERNANCE_AGENT']
primary_role:      29_ARCHITECTURE_GOVERNANCE_AGENT
```

**Role responsibilities this loop:**
- `29_ARCHITECTURE_GOVERNANCE_AGENT`: Enforces allowed boundaries, no runtime logic changes.
- `02_CODE_ARCHITECT_AGENT`: Modifies import paths to match moved file location.
- `27_VERIFICATION_OFFICER_AGENT`: Validates targeted test suite correctness.
- `24_REPOSITORY_LIBRARIAN_AGENT`: Verifies file moves and path cleanliness.

---

## SECTION 5 — TOOL PIPELINE

```
tool_pipeline_id:  LOW_RISK_REFACTOR_LOOP
```

**Ordered tool sequence**:
- [ ] Move files (`git mv`)
- [ ] Edit test import references
- [ ] Run python compile check on moved files
- [ ] Run targeted pytests
- [ ] Commit changes
- [ ] Append loop memory entry

---

## SECTION 6 — SKILL LIST

```
skills: ['quant_safety_review', 'low_risk_refactor']
```

---

## SECTION 7 — ALLOWED FILES

```
allowed_files:
  - tools/free_outcome_truth_provisional.py
  - tools/free_outcome_truth_provisional_join.py
  - tools/free_outcome_truth_provisional_readiness.py
  - tools/outcome_truth/free_outcome_truth_provisional.py
  - tools/outcome_truth/free_outcome_truth_provisional_join.py
  - tools/outcome_truth/free_outcome_truth_provisional_readiness.py
  - tests/test_free_outcome_truth_provisional.py
  - tests/test_free_outcome_truth_provisional_join.py
  - tests/test_free_outcome_truth_provisional_readiness.py
  - docs/reports/
  - docs/operations/
```

---

## SECTION 8 — FORBIDDEN FILES (ALWAYS)

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
  - polymarket/trader.py
  - config/settings.py
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

- [x] Safety Memory (QS-001..010)
- [x] Decision Memory
- [x] Failure Memory

---

## SECTION 10b — KNOWLEDGE GRAPH EVIDENCE

```
graph_query_results_file:  docs/operations/graph_queries/QUERY-20260628-REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001.md

knowledge_graph_evidence:
  safety_check_query_id:   QUERY-20260628-REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001:safety_check
  safety_findings:         []
  safety_stop_triggered:   false
  blast_radius_score:      LOW
  blast_radius_query_id:   QUERY-20260628-REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001:blast_radius
  evidence_for_commit_grade: B
  evidence_query_id:       QUERY-20260628-REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001:evidence_for_commit
  deferred_history:        N/A
  why_deferred_query_id:   N/A
  graph_confidence:        0.4
  graph_timestamp:         2026-06-27
  graph_query_ids:         ["QUERY-20260628-REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001:safety_check", "QUERY-20260628-REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001:blast_radius", "QUERY-20260628-REPOSITORY_PHASE1B_OUTCOME_TRUTH_PROVISIONAL_MOVE_001:evidence_for_commit"]
  stop_condition_triggered: false
```

---

## SECTION 11 — REQUIRED TOOLS (ORDERED)

| # | Tool ID | Expected outcome | Evidence grade |
|---|---------|-----------------|----------------|
| 1 | git mv | Files moved to target locations | B |
| 2 | py_compile | Compile check passes | B |
| 3 | pytest | 16/16 targeted tests pass | C |

```
evidence_baseline_test_count: 16
evidence_baseline_failures:   0
```

---

## SECTION 12 — REQUIRED EVIDENCE

```
evidence_required:     B
evidence_plan:
  - D: git_status_clean, scope_check
  - B: py_compile + import_ok + scope_check
  - C: + pytest
```

---

## SECTION 13 — STOP CONDITIONS

**Immediate STOP (no repair) if any of:**
- [x] Forbidden file in `git diff`
- [x] Live trading keyword in any command
- [x] Safety memory missing/invalid for required task
- [x] Runtime data deletion detected
- [x] Wallet/bankroll/allowance changes in diff
- [x] Unrelated tracked dirty files at commit time

---

## SECTION 14 — REPAIR POLICY

```
max_repairs:           3
repair_scope_limit:    repairs must stay within allowed_files
```

---

## SECTION 15 — COMMIT POLICY

```
commit_policy:         TYPE_A_FIRST_THEN_TYPE_C
```

**Planned commits:**

| Commit # | Files | Type | Message |
|----------|-------|------|---------|
| 1 | Moved tools, tests | TYPE A | "refactor: move provisional outcome truth tools" |
| 2 | Operations/Reports | TYPE C | "docs: update workflow state and QIE logs" |

---

## SECTION 16 — HUMAN AUTHORIZATION (Class 8 / Destructive only)

```
requires_human_authorization: false
```

---

## SECTION 17 — MEMORY WRITES (Post-Commit)

```
memory_writes_planned:
  - loop: Outcome truth tools move completed
  - ACTIVE_WORKFLOW_STATE_001.json updated
  - TASK_QUEUE_001.json updated
```

---

## SECTION 18 — VERIFICATION CHECKLIST

Before commit, confirm ALL:

```
[ ] git diff --name-only shows only allowed_files
[ ] No root markdown created
[ ] py_compile PASS
[ ] IMPORT_OK
[ ] Tests pass vs baseline (16/16 passing)
```
