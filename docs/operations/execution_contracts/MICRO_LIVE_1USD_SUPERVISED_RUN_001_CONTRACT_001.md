# EXECUTION CONTRACT — MICRO_LIVE_1USD_SUPERVISED_RUN_001

**Schema:** `execution_contract_v2.1`  
**Purpose:** Audit record and safety confirmation for Class 8 Live Risk execution.

---

## SECTION 1 — CONTRACT METADATA

```
contract_id:       CONTRACT-20260628-MICROLIVE-001
created_at:        2026-06-28T03:51:00Z
plan_id:           MANUAL
bootstrap_sha:     5e75bae
bootstrap_status:  HEALTHY
safety_memory_status: HEALTHY
safety_memory_count: 10
```

---

## SECTION 2 — TASK IDENTITY

```
task_id:           MICRO_LIVE_1USD_SUPERVISED_RUN_001
task_class:        8
description:       Execute the first supervised $1 micro-live validation run.
source_task:       MICRO_LIVE_1USD_SUPERVISED_RUN_001
```

---

## SECTION 3 — WORKFLOW TIER

```
workflow_tier:     GATE
risk_score:        9
complexity_score:  4
full_accept_override: true
```

---

## SECTION 4 — AGENT PIPELINE

```
agent_pipeline_id: LIVE_RUN_LOOP
role_sequence:     [03_RISK_MANAGER_AGENT, 28_RUNTIME_OPERATIONS_AGENT]
primary_role:      03_RISK_MANAGER_AGENT
```

**Role responsibilities this loop:**
- `03_RISK_MANAGER_AGENT`: Validate that all safety rules, caps, and risk boundaries are active.
- `28_RUNTIME_OPERATIONS_AGENT`: Bounded execution, shutdown, and validation of the live run metrics.

---

## SECTION 5 — TOOL PIPELINE

```
tool_pipeline_id:  LIVE_RUN_PIPELINE
```

**Ordered tool sequence**:
- [x] run_command (verify mode)
- [x] run_command (live runner)
- [ ] view_file (JSONL check)

---

## SECTION 6 — SKILL LIST

```
skills: []
```

---

## SECTION 7 — ALLOWED FILES

```
allowed_files:
  - docs/reports/MICRO_LIVE_1USD_SUPERVISED_RUN_001.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260627_001.json
```

---

## SECTION 8 — FORBIDDEN FILES (ALWAYS)

The following are permanently forbidden regardless of task scope:

```
forbidden_always:
  - _phase4_build_quote_lineage
  - _phase4_quote_lineage_carry
  - _last_quote_lineage_context
  - _risk_plan_zero_diagnostics
  - _diagnostic_float
  - _diagnostic_int
  - polymarket/client.py live methods (modification)
  - .env live flags (unauthorized changes)
  - runtime/ data deletion
  - execution/risk/sizing/reconciliation without GATE

task_specific_forbidden: []
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
- [x] Decision Memory — checked
- [x] Failure Memory — checked

---

## SECTION 10b — KNOWLEDGE GRAPH EVIDENCE

```
graph_query_results_file:  docs/operations/graph_queries/QUERY-20260628-MICRO_LIVE-001.md

knowledge_graph_evidence:
  safety_check_query_id:   QUERY-20260628-MICRO_LIVE-001
  safety_findings:         []
  safety_stop_triggered:   false
  blast_radius_score:      LOW
  blast_radius_query_id:   QUERY-20260628-MICRO_LIVE-001
  evidence_for_commit_grade: A
  evidence_query_id:       QUERY-20260628-MICRO_LIVE-001
  deferred_history:        N/A
  why_deferred_query_id:   N/A
  graph_confidence:        1.0
  graph_timestamp:         2026-06-28
  graph_query_ids:         [QUERY-20260628-MICRO_LIVE-001]
  stop_condition_triggered: false
```

---

## SECTION 11 — REQUIRED TOOLS (ORDERED)

| # | Tool ID | Expected outcome | Evidence grade |
|---|---------|-----------------|----------------|
| 1 | run_command | `main.py --mode verify` returns GO | A |
| 2 | run_command | `main.py --mode live` runs for 1+ cycles | A |
| 3 | run_command | `git status` shows no dirty code files | A |

---

## SECTION 12 — REQUIRED EVIDENCE

```
evidence_required:     A
evidence_plan:
  - D: git_status_clean, scope_check
  - B: py_compile + import_ok
  - C: + pytest
  - A: + live run + jsonl scan
```

**Evidence accumulation log**:
- [x] D — git scope confirmed
- [x] B — compile + import clean
- [x] C — tests pass
- [ ] A — live run completed + JSONL logs scanned

---

## SECTION 13 — STOP CONDITIONS

**Immediate STOP (no repair) if any of:**
- [ ] Forbidden file in `git diff`
- [ ] Live trading override in unauthorized commands
- [ ] Safety memory missing/invalid
- [ ] Runtime data deletion detected
- [ ] Wallet/bankroll/allowance changes in diff
- [ ] Unrelated tracked dirty files at commit time

---

## SECTION 14 — REPAIR POLICY

```
max_repairs:           0
repair_scope_limit:    N/A
```

---

## SECTION 15 — COMMIT POLICY

```
commit_policy:         MANUAL_ONLY
```

---

## SECTION 16 — HUMAN AUTHORIZATION (Class 8 / Destructive only)

```
requires_human_authorization: true
authorization_received: true
authorization_scope: "Execute the first supervised $1 micro-live validation run. This is a Class 8 Live Risk task. Human operator must supervise. Do NOT run uncontrolled continuous live trading. Do NOT increase caps. Do NOT modify strategy, sizing, risk, or execution logic. Do NOT delete runtime evidence."
authorization_timestamp: "2026-06-28T03:51:00Z"
destructive_action: "Place real money orders on Polymarket up to caps (max $1.00 per order, max $2.00 exposure/loss)."
rollback_plan: "Ctrl+C to terminate the process, create runtime/KILL_SWITCH to stop any future orders, and manually verify/close any open positions via the Polymarket web app."
```

---

## SECTION 17 — MEMORY WRITES (Post-Commit)

```
memory_writes_planned:
  - loop: "Micro-live supervised execution run 001"
  - decision: []
  - failure: []
  - repair: []
  - runtime: "First micro-live execution run logs"
```

---

## SECTION 18 — VERIFICATION CHECKLIST

Before final task declaration, confirm ALL:

```
[ ] git diff --name-only shows only allowed_files
[ ] No root markdown created
[ ] Safety memory still loaded
[ ] working_tree contains only allowed staged files
```

---

## SECTION 19 — FINAL OUTPUT CONTRACT

At loop completion, declare:

```
FINAL_VERDICT:     [verdict]
TASK:              MICRO_LIVE_1USD_SUPERVISED_RUN_001
COMMITS:           NONE
FILES_CHANGED:     [N]
TESTS:             N/A
RUNTIME:           [cycles, exit status]
FORBIDDEN_SCOPE:   confirmed
STATE_QUEUE_MEMORY: [updates]
NEXT:              [next_task]
```
