# EXECUTION CONTRACT

**Schema:** `execution_contract_v2.1`  
**Purpose:** Audit record for task execution.

---

## SECTION 1 — CONTRACT METADATA

```
contract_id:       CONTRACT-20260628-QIE-BUILDER-001
created_at:        2026-06-28T03:57:30Z
plan_id:           MANUAL
bootstrap_sha:     657016b
bootstrap_status:  HEALTHY
safety_memory_status: LOADED
safety_memory_count: 10
```

---

## SECTION 2 — TASK IDENTITY

```
task_id:           QUANT_INTELLIGENCE_ENGINE_OFFLINE_BUILDER_001
task_class:        4
description:       Implement the offline builder scripts and command-line harness for the Quant Intelligence Engine (QIE).
source_task:       QUANT_INTELLIGENCE_ENGINE_OFFLINE_BUILDER_001
```

---

## SECTION 3 — WORKFLOW TIER

```
workflow_tier:     STANDARD
risk_score:        2
complexity_score:  5
full_accept_override: true
```

---

## SECTION 4 — AGENT PIPELINE

```
agent_pipeline_id: TOOL_PIPELINE_LOOP
role_sequence:     ["29_ARCHITECTURE_GOVERNANCE_AGENT", "27_VERIFICATION_OFFICER_AGENT", "24_REPOSITORY_LIBRARIAN_AGENT"]
primary_role:      29_ARCHITECTURE_GOVERNANCE_AGENT
```

**Role responsibilities this loop:**
- `29_ARCHITECTURE_GOVERNANCE_AGENT`: Enforce safety memory rules and verify no forbidden runtime modifications.
- `27_VERIFICATION_OFFICER_AGENT`: Confirm unit tests and execution outputs match specifications.
- `24_REPOSITORY_LIBRARIAN_AGENT`: Maintain directory structure cleanliness and place new md files in appropriate subdirectories.

---

## SECTION 5 — TOOL PIPELINE

```
tool_pipeline_id:  TOOL_PIPELINE_LOOP
```

**Ordered tool sequence**:
- [ ] write_to_file (create tools/quant_intelligence_engine.py)
- [ ] write_to_file (create tests/test_quant_intelligence_engine.py)
- [ ] run_command (run pytest)
- [ ] run_command (run builder tool on recent data)
- [ ] write_to_file (create task output report)

---

## SECTION 6 — SKILL LIST

```
skills: ["forbidden_scope_check"]
```

**Skill outputs required:**
- `forbidden_scope_check`: Verify no changes to runtime strategy/sizing/risk files.

---

## SECTION 7 — ALLOWED FILES

```
allowed_files:
  - tools/quant_intelligence_engine.py
  - tests/test_quant_intelligence_engine.py
  - docs/reports/QUANT_INTELLIGENCE_ENGINE_OFFLINE_BUILDER_001.md
  - docs/operations/execution_contracts/QUANT_INTELLIGENCE_ENGINE_OFFLINE_BUILDER_001_CONTRACT_001.md
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
  - polymarket/client.py
  - polymarket/trader.py
  - utils/risk_manager.py
  - polymarket/position_sizing.py
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

```
required_memory_reads: ["quant_safety"]
```

**Memory reads performed before execution:**
- [x] Safety Memory (QS-001..010) — checked and loaded.

---

## SECTION 10b — KNOWLEDGE GRAPH EVIDENCE

```
knowledge_graph_evidence:  N/A (Class 4 Tooling task, offline compiler, no runtime dependencies)
```

---

## SECTION 11 — REQUIRED TOOLS (ORDERED)

| # | Tool ID | Expected outcome | Evidence grade |
|---|---------|-----------------|----------------|
| 1 | pytest | Unit tests pass successfully | C |
| 2 | run_command | Offline builder runs successfully against recent runtime data | A |

```
evidence_baseline_test_count: 35
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

**Evidence accumulation log**:
- [x] D — git scope confirmed (no changes in git status)
- [ ] B — compile + import clean
- [ ] C — tests pass

---

## SECTION 13 — STOP CONDITIONS

**Immediate STOP (no repair) if any of:**
- [ ] Forbidden file in `git diff`
- [ ] Live trading keyword in any command
- [ ] Safety memory missing/invalid
- [ ] Runtime data deletion detected
- [ ] Wallet/bankroll/allowance changes in diff
- [ ] Unrelated tracked dirty files at commit time

---

## SECTION 14 — REPAIR POLICY

```
max_repairs:           3
repair_scope_limit:    allowed_files
```

---

## SECTION 15 — COMMIT POLICY

```
commit_policy:         TYPE_B_OR_TYPE_C
```

---

## SECTION 18 — VERIFICATION CHECKLIST

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
