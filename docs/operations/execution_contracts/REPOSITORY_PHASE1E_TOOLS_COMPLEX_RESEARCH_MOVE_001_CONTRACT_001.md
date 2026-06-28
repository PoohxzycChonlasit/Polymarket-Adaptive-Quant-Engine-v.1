# REPOSITORY_PHASE1E_TOOLS_COMPLEX_RESEARCH_MOVE_001_CONTRACT_001

## SECTION 1 — CONTRACT METADATA
```
contract_id:       CONTRACT-20260628-REPOSITORY-PHASE1E-MOVE-001
created_at:        2026-06-28T08:42:00Z
plan_id:           MANUAL
bootstrap_sha:     041f357
bootstrap_status:  HEALTHY
safety_memory_status: LOADED
safety_memory_count: 10
```

## SECTION 2 — TASK IDENTITY
```
task_id:           REPOSITORY_PHASE1E_TOOLS_COMPLEX_RESEARCH_MOVE_001
task_class:        6
description:       Execute the Phase 1E Audit Batch tools migration into tools/audit/.
source_task:       TASK_QUEUE entry REPOSITORY_PHASE1E_TOOLS_COMPLEX_RESEARCH_MOVE_001
```

## SECTION 3 — WORKFLOW TIER
```
workflow_tier:     LOOP
risk_score:        1
complexity_score:  2
full_accept_override: false
```

## SECTION 4 — AGENT PIPELINE
```
agent_pipeline_id: TOOLS_MIGRATION
role_sequence:     ["02_CODE_ARCHITECT_AGENT", "24_REPOSITORY_LIBRARIAN_AGENT", "07_TEST_CI_AGENT"]
primary_role:      02_CODE_ARCHITECT_AGENT
```

## SECTION 7 — ALLOWED FILES
```
allowed_files:
  - tools/_audit_cs_btc.py
  - tools/_audit_decision_state.py
  - tools/_audit_w21_w22.py
  - tools/_delta_audit.py
  - tools/_drift_audit.py
  - tools/_opp_capture_audit.py
  - tools/ev_field_coverage_audit.py
  - tools/audit/
  - tests/test_drift_audit.py
  - tests/test_ev_field_coverage_audit.py
  - docs/reports/
  - docs/operations/
```

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
```

## SECTION 9 — SAFETY MEMORY CONFIRMATION
```
safety_memory_required: true
safety_memory_loaded:   true
safety_memory_ids_spot_check:
  - QS-001 present: yes
  - QS-005 present: yes
  - QS-010 present: yes
```

## SECTION 10 — MEMORY READS
```
required_memory_reads:
  - docs/reports/REPOSITORY_PHASE1E_TOOLS_COMPLEX_RESEARCH_MOVE_PLAN_001.md
```

## SECTION 10b — KNOWLEDGE GRAPH EVIDENCE
```
graph_query_results_file:  docs/operations/graph_queries/QUERY-20260628-REPOSITORY_PHASE1E_TOOLS_COMPLEX_RESEARCH_MOVE_001.md
knowledge_graph_evidence:
  safety_check_query_id:   QUERY-20260628-REPOSITORY_PHASE1E_TOOLS_COMPLEX_RESEARCH_MOVE_001
  safety_findings:         []
  safety_stop_triggered:   false
  blast_radius_score:      LOW
  blast_radius_query_id:   QUERY-20260628-REPOSITORY_PHASE1E_TOOLS_COMPLEX_RESEARCH_MOVE_001
  evidence_for_commit_grade: A
  evidence_query_id:       QUERY-20260628-REPOSITORY_PHASE1E_TOOLS_COMPLEX_RESEARCH_MOVE_001
  graph_confidence:        1.0
  graph_timestamp:         2026-06-27
  graph_query_ids:         [QUERY-20260628-REPOSITORY_PHASE1E_TOOLS_COMPLEX_RESEARCH_MOVE_001]
  stop_condition_triggered: false
```

## SECTION 11 — REQUIRED TOOLS (ORDERED)
| # | Tool ID | Expected outcome | Evidence grade |
|---|---------|-----------------|----------------|
| 1 | run_command (mv) | Git move files successfully | B |
| 2 | replace_file_content | Update imports and path references | B |
| 3 | run_command (py_compile) | Verify compilation | B |
| 4 | run_command (pytest) | Verify unit tests pass | C |

```
evidence_baseline_test_count: 32
evidence_baseline_failures:   0
```

## SECTION 12 — REQUIRED EVIDENCE
```
evidence_required:     C
evidence_plan:
  - D: git_status_clean, scope_check
  - B: py_compile + import_ok + scope_check
  - C: + pytest
```

## SECTION 13 — STOP CONDITIONS
* Any diff outside `allowed_files` list.
* Any live trading keyword.

## SECTION 15 — COMMIT POLICY
```
commit_policy:         TYPE_A+C
```

## SECTION 18 — VERIFICATION CHECKLIST
```
[x] git status shows clean tree at start
[x] Graph queries complete and contract signed
```
