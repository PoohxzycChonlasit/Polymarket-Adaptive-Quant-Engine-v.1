# EXECUTION CONTRACT TEMPLATE v2

**Schema:** `execution_contract_v2.1`  
**Purpose:** AI agents must fill this contract before executing any LOOP/STANDARD/GATE task. The filled contract becomes the audit record for the loop.  
**Usage:** Copy this template, fill all required fields, then execute according to the declared scope.

---

## HOW TO USE

1. Copy this template to a working note (or fill inline before responding)
2. Complete every **required** section for the current task
3. Run bootstrap to confirm health before execution
4. Execute exactly within the declared scope
5. After commit, update State/Queue/Memory per the Memory OS section

**Required sections for every task:** 1–15, 18  
**Required for Class 7/8 or destructive tasks:** + Section 16 (Human Authorization)  
**Required for tasks with memory writes:** + Section 17

---

## SECTION 1 — CONTRACT METADATA

```
contract_id:       [e.g. CONTRACT-20260627-BATCH3C-001]
created_at:        [ISO timestamp]
plan_id:           [from bootstrap --pretty → plan_id if available, else MANUAL]
bootstrap_sha:     [HEAD SHA from git log -1 --format=%h]
bootstrap_status:  HEALTHY  (must be HEALTHY before execution begins)
safety_memory_status: [from bootstrap --pretty → safety_memory_status]
safety_memory_count: [from bootstrap --pretty → safety_memory_count, must be 10]
```

---

## SECTION 2 — TASK IDENTITY

```
task_id:           [e.g. BATCH_3C_IMPLEMENTATION_001]
task_class:        [int 0-9]
description:       [one sentence from task queue]
source_task:       [TASK_QUEUE entry that declared this task]

# For refactor tasks touching trader.py:
trader_py_lines_before:  [wc -l polymarket/trader.py — measure before any edit]
expected_line_delta:     [negative = reduction, positive = increase]
```

---

## SECTION 3 — WORKFLOW TIER

```
workflow_tier:     [FAST | LOOP | STANDARD | GATE]
risk_score:        [int — from Planning Engine scoring or MANUAL estimate]
complexity_score:  [int — from Planning Engine scoring or MANUAL estimate]
full_accept_override: [true | false — true blocks auto-accept]
```

---

## SECTION 4 — AGENT PIPELINE

```
agent_pipeline_id: [from bootstrap --pretty → agent_pipeline_id]
role_sequence:     [from bootstrap --pretty → role_sequence]
primary_role:      [first role in sequence]
```

**Role responsibilities this loop:**
- `[role_id]`: [brief responsibility]
- `[role_id]`: [brief responsibility]

---

## SECTION 5 — TOOL PIPELINE

```
tool_pipeline_id:  [from bootstrap --pretty → tool_pipeline_id]
```

**Ordered tool sequence** (check each when complete):
- [ ] [tool_id_1]
- [ ] [tool_id_2]
- [ ] [tool_id_3]

---

## SECTION 6 — SKILL LIST

```
skills: [from bootstrap --pretty → skills]
```

**Skill outputs required:**
- `[skill_id]`: [output_contract summary]
- `[skill_id]`: [output_contract summary]

---

## SECTION 7 — ALLOWED FILES

```
allowed_files:
  - [file path or glob pattern]
  - [file path or glob pattern]
```

**Note:** Only files in this list may be created or modified. Any diff showing files outside this list is a STOP condition.

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
  - [any additional files forbidden by this task's design]
```

---

## SECTION 9 — SAFETY MEMORY CONFIRMATION

```
safety_memory_required: [true | false]
  (true if task_class in {4,6,7,8} OR tier in {GATE, STANDARD})
safety_memory_loaded:   [from bootstrap → safety_memory_loaded]
safety_memory_ids_spot_check:
  - QS-001 present: [yes | no]
  - QS-005 present: [yes | no]
  - QS-010 present: [yes | no]
```

**STOP if:** `safety_memory_required = true` AND `safety_memory_loaded = false`

---

## SECTION 10 — MEMORY READS

```
required_memory_reads: [from bootstrap --pretty → required_memory_reads]
```

**Memory reads performed before execution:**
- [ ] Safety Memory (QS-001..010) — mandatory
- [ ] Decision Memory — [relevant prior decisions]
- [ ] Failure Memory — [known failure patterns for this task type]
- [ ] Repository Memory — [extraction history relevant to scope]

---

## SECTION 11 — REQUIRED TOOLS (ORDERED)

List tools in execution order with expected outcome:

| # | Tool ID | Expected outcome | Evidence grade |
|---|---------|-----------------|----------------|
| 1 | [tool_id] | [pass criterion] | [D/C/B/A] |
| 2 | [tool_id] | [pass criterion] | [D/C/B/A] |
| ... | | | |

**Minimum evidence required:** `[from bootstrap → required_evidence]`  
**Current evidence grade at start:** D

```
# For test suites — record baseline before any changes:
evidence_baseline_test_count: [N — from pytest -q before edits]
evidence_baseline_failures:   [M pre-existing failures — do not count as regressions]
```

---

## SECTION 12 — REQUIRED EVIDENCE

```
evidence_required:     [D | C | B | A — from bootstrap]
evidence_plan:
  - D: git_status_clean, scope_check
  - B: py_compile + import_ok + scope_check
  - C: + pytest
  - A: + paper_run + jsonl_scan
```

**Evidence accumulation log** (fill during execution):
- [ ] D — git scope confirmed
- [ ] B — compile + import clean
- [ ] C — tests pass
- [ ] A — paper run 5+ cycles, JSONL fields verified

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
- [add any from bootstrap → stop_conditions]

---

## SECTION 14 — REPAIR POLICY

```
max_repairs:           [from bootstrap → max_repairs]
repair_scope_limit:    [repairs must stay within allowed_files]
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
- Repair #1: [failure_class] → [fix_applied] → [pass/fail]
- Repair #2: [failure_class] → [fix_applied] → [pass/fail]

---

## SECTION 15 — COMMIT POLICY

```
commit_policy:         [TYPE_A | TYPE_B | TYPE_C | TYPE_A+C | MANUAL_ONLY]
```

**Planned commits:**

| Commit # | Files | Type | Message |
|----------|-------|------|---------|
| 1 | [file list] | TYPE [X] | "[verb]: [description]" |
| 2 | [file list] | TYPE C | "docs: [description]" |

**Anti-patterns (never do):**
- Mixing TYPE A with TYPE B/D/F in same commit
- Hidden "finalize" commits
- Amending already-committed changes
- Skipping hooks with `--no-verify`

---

## SECTION 16 — HUMAN AUTHORIZATION (Class 8 / Destructive only)

```
requires_human_authorization: [true | false]
authorization_received: [true | false — must be true before execute --confirm]
authorization_scope: "[exact quoted scope from user message]"
authorization_timestamp: "[when user gave authorization]"
destructive_action: "[describe exactly what will be deleted/changed]"
rollback_plan: "[how to recover if something goes wrong]"
```

**STOP if:** `requires_human_authorization = true` AND `authorization_received = false`

---

## SECTION 17 — MEMORY WRITES (Post-Commit)

```
memory_writes_planned:
  - loop: [summary of this loop]
  - decision: [reusable decision if any]
  - failure: [failure entries if any repairs occurred]
  - repair: [repair patterns if any]
  - runtime: [paper run results if applicable]
```

**Memory write checklist** (complete after commit):
- [ ] Loop Memory appended to `LOOP_MEMORY_YYYYMMDD.jsonl`
- [ ] Memory Index updated
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
[ ] Paper run 5+ cycles exit 0 (if Grade A required)
[ ] JSONL fields present (if Grade A required)
[ ] Safety memory still loaded (bootstrap --diagnose)
[ ] working_tree contains only allowed staged files
```

---

## SECTION 19 — FINAL OUTPUT CONTRACT

At loop completion, declare:

```
FINAL_VERDICT:     [COMMITTED | STOPPED | ESCALATED]
TASK:              [task_id]
COMMITS:           [sha] — [message]
FILES_CHANGED:     [N] ([detail])
TESTS:             [N/N pass] or N/A
RUNTIME:           [cycles, exit, JSONL counts] or N/A
FORBIDDEN_SCOPE:   confirmed [or VIOLATION: file]
STATE_QUEUE_MEMORY: [what was updated]
NEXT:              [next_task_id] — [one line]
```

---

## SECTION 20 — EXAMPLES

### Example: Docs housekeeping loop (Class 3, FAST)

```
contract_id:    CONTRACT-20260627-DOCS-001
task_id:        FILE_INDEX_REFRESH_001
task_class:     3
workflow_tier:  FAST
agent_pipeline_id: DOCS_LOOP
tool_pipeline_id:  DOCS_LOOP
skills:         [docs_housekeeping]
allowed_files:  [FILE_INDEX.md, DOCUMENTATION_MAP.md, docs/reports/]
safety_memory_required: false (class 3, FAST — no safety memory stop)
max_repairs:    3
commit_policy:  TYPE_C
evidence_required: D
```

### Example: Low-risk refactor (Class 6, LOOP)

```
contract_id:    CONTRACT-20260627-BATCH3C-001
task_id:        BATCH_3C_IMPLEMENTATION_001
task_class:     6
workflow_tier:  LOOP
agent_pipeline_id: LOW_RISK_REFACTOR_LOOP
skills:         [quant_safety_review, low_risk_refactor]
allowed_files:  [polymarket/trader.py, polymarket/orchestration/trader_observability.py, docs/reports/]
safety_memory_required: true (class 6)
max_repairs:    3
commit_policy:  TYPE_A_FIRST_THEN_TYPE_C
evidence_required: C
```

### Example: Log governance execute (Class 8, requires human auth)

```
contract_id:    CONTRACT-20260627-LOGGOV-001
task_id:        RUNTIME_LOG_GOVERNANCE_EXECUTE_001
task_class:     8
workflow_tier:  GATE
requires_human_authorization: true
authorization_received: true
authorization_scope: "DELETE old polytrade_bot session log groups, age >7 days, PID not running, max 800 actions, no JSONL deletion"
destructive_action: "Permanently delete 800 session log files (~1.4 GB)"
rollback_plan: "JSONL event stream preserves trading history; no position data at risk"
```
