# EXECUTION CONTRACT

**Schema:** `execution_contract_v2.1`  
**Purpose:** Audit record for task execution.  

---

## SECTION 1 — CONTRACT METADATA

```
contract_id:       CONTRACT-20260629-PHASE3A-001
created_at:        2026-06-29T01:45:00Z
plan_id:           MANUAL
bootstrap_sha:     b24741e
bootstrap_status:  HEALTHY
safety_memory_status: LOADED
safety_memory_count: 10
```

---

## SECTION 2 — TASK IDENTITY

```
task_id:           TRADER_PHASE3A_ORDERBOOK_LINEAGE_OBSERVABILITY_EXTRACTION_001
task_class:        6
description:       Extract orderbook lineage observability helpers from polymarket/trader.py into polymarket/observability/trader_orderbook_lineage.py, preserving exact behavior through backward-compatible wrapper delegation.
source_task:       TRADER_PHASE3A_ORDERBOOK_LINEAGE_OBSERVABILITY_EXTRACTION_001

trader_py_lines_before:  13010
expected_line_delta:     -250
```

---

## SECTION 3 — WORKFLOW TIER

```
workflow_tier:     STANDARD
risk_score:        3
complexity_score:  4
full_accept_override: false
```

---

## SECTION 4 — AGENT PIPELINE

```
agent_pipeline_id: LOW_RISK_REFACTOR_PIPELINE
role_sequence:     [02_CODE_ARCHITECT_AGENT, 11_OBSERVABILITY_INCIDENT_AGENT, 07_TEST_CI_AGENT]
primary_role:      02_CODE_ARCHITECT_AGENT
```

**Role responsibilities this loop:**
- `02_CODE_ARCHITECT_AGENT`: Ensure clean separation of concerns and interface fidelity.
- `11_OBSERVABILITY_INCIDENT_AGENT`: Maintain correct fields and types for payload events.
- `07_TEST_CI_AGENT`: Execute tests and verify zero regressions.

---

## SECTION 5 — TOOL PIPELINE

```
tool_pipeline_id: REFACTOR_TOOL_PIPELINE
```

**Ordered tool sequence** (check each when complete):
- [ ] write_to_file
- [ ] replace_file_content
- [ ] run_command

---

## SECTION 6 — SKILL LIST

```
skills: [low_risk_refactor]
```

**Skill outputs required:**
- `low_risk_refactor`: Extracted orderbook lineage module and wrapper delegation.

---

## SECTION 7 — ALLOWED FILES

```
allowed_files:
  - polymarket/trader.py
  - polymarket/observability/trader_orderbook_lineage.py
  - tests/observability/test_trader_orderbook_lineage.py
  - docs/reports/TRADER_PHASE3A_ORDERBOOK_LINEAGE_OBSERVABILITY_EXTRACTION_001.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json
  - docs/operations/graph_queries/QUERY-20260629-TRADER_PHASE3A_ORDERBOOK_LINEAGE_OBSERVABILITY_EXTRACTION_001.md
  - docs/operations/execution_contracts/TRADER_PHASE3A_ORDERBOOK_LINEAGE_OBSERVABILITY_EXTRACTION_001_CONTRACT_001.md
  - docs/operations/repository/symbol_index.json
  - docs/operations/repository/module_registry.json
  - docs/operations/repository/navigation.json
  - docs/operations/repository/dependency_graph.json
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
  - config/settings.py
  - .env
  - polymarket/client.py
  - polymarket/signal.py
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
- [x] Decision Memory — checked TRADER_MODULARIZATION_PROGRAM_001
- [x] Failure Memory — checked prior monkeypatch issue in outcome truth batch
- [x] Repository Memory — checked symbol index for orderbook lineage group

---

## SECTION 10b — KNOWLEDGE GRAPH EVIDENCE (CLASS 6+ MANDATORY)

```
graph_query_results_file:  docs/operations/graph_queries/QUERY-20260629-TRADER_PHASE3A_ORDERBOOK_LINEAGE_OBSERVABILITY_EXTRACTION_001.md

knowledge_graph_evidence:
  safety_check_query_id:   QUERY-20260629-TRADER_PHASE3A_ORDERBOOK_LINEAGE_OBSERVABILITY_EXTRACTION_001
  safety_findings:         []
  safety_stop_triggered:   false
  blast_radius_score:      MEDIUM
  blast_radius_query_id:   QUERY-20260629-TRADER_PHASE3A_ORDERBOOK_LINEAGE_OBSERVABILITY_EXTRACTION_001
  evidence_for_commit_grade: B
  evidence_query_id:       QUERY-20260629-TRADER_PHASE3A_ORDERBOOK_LINEAGE_OBSERVABILITY_EXTRACTION_001
  deferred_history:        N/A
  why_deferred_query_id:   N/A
  graph_confidence:        0.9
  graph_timestamp:         2026-06-28
  graph_query_ids:         [QUERY-20260629-TRADER_PHASE3A_ORDERBOOK_LINEAGE_OBSERVABILITY_EXTRACTION_001]
  stop_condition_triggered: false
```

---

## SECTION 11 — REQUIRED TOOLS (ORDERED)

| # | Tool ID | Expected outcome | Evidence grade |
|---|---------|-----------------|----------------|
| 1 | py_compile | Success on new and changed modules | B |
| 2 | pytest | targeted tests pass (675 tests) | C |

```
evidence_baseline_test_count: 675
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

---

## SECTION 14 — REPAIR POLICY

```
max_repairs:           3
repair_scope_limit:    allowed_files
```

| Failure class | Repairable? | Max | Action |
|--------------|-------------|-----|--------|
| compile_error | YES | 2 | Fix syntax in allowed files |
| import_error | YES | 2 | Fix import path |
| unit_test_failure | YES | 3 | Fix in allowed files only |
| scope_violation | **NO** | 0 | STOP |
| git_state_violation | **NO** | 0 | STOP |

---

## SECTION 15 — COMMIT POLICY

```
commit_policy:         MANUAL_ONLY
```

**Planned commits:**

| Commit # | Files | Type | Message |
|----------|-------|------|---------|
| 1 | polymarket/trader.py polymarket/observability/trader_orderbook_lineage.py tests/observability/test_trader_orderbook_lineage.py docs/ | TYPE A+C | "refactor: extract trader orderbook lineage helpers" |

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
  - loop: extracted orderbook lineage helpers and verified equivalence.
  - decision: none
  - failure: none
  - repair: none
```

---

## SECTION 18 — VERIFICATION CHECKLIST

Before commit, confirm ALL:
```
[ ] git diff --name-only shows only allowed_files
[ ] git diff -- [files] | grep "[forbidden_patterns]" → empty
[ ] No root markdown created
[ ] py_compile PASS
[ ] IMPORT_OK
[ ] Tests pass vs baseline
[ ] Safety memory still loaded
[ ] working_tree contains only allowed staged files
```

---

## SECTION 19 — FINAL OUTPUT CONTRACT

At loop completion, declare final output contract fields.
