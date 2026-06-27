# FLAOS Loop Runtime Engine v2 - Operational Checklist

## 1. INIT & State Verification
- [ ] Verify that no duplicate paper runtime is active on the host.
- [ ] Confirm git working tree state matches active workflow state requirements.
- [ ] Initialize loop telemetry and session logging path.

## 2. Bootstrap Check
- [ ] Run `.venv\Scripts\python.exe tools/flaos/bootstrap.py --diagnose`.
- [ ] Confirm bootstrap status returns `HEALTHY`.
- [ ] Ensure that active pipeline and skill registries load without parsing errors.

## 3. Context Bundle Generation
- [ ] Request Context Builder compilation.
- [ ] Confirm compiled `ContextBundle` contains these required fields:
  - `context_id` (UUID format)
  - `task_id`
  - `generated_at` (ISO timestamp)
  - `freshness_status`
  - `safety_memory`
  - `graph_evidence`
  - `memory_refs`
  - `active_questions`
  - `runtime_health`
  - `allowed_scope`
  - `forbidden_scope`

## 4. Safety Memory Verification
- [ ] Verify that Safety Memory is loaded successfully with exactly 10 rules.
- [ ] Assert that rules `QS-001` through `QS-010` are present.

## 5. Runtime Knowledge Graph Check
- [ ] Check if the task class is `Class 6+` (Refactor, Feature, Live Risk).
- [ ] If `Class 6+`, query the Runtime Knowledge Graph for blast-radius and AST coupling constraints.
- [ ] If query output is missing or empty, **STOP** execution immediately.

## 6. Execution Contract Verification
- [ ] Confirm that `docs/operations/execution_contracts/{TASK_ID}_CONTRACT_001.md` exists for Class 6+ tasks.
- [ ] Verify that the contract is fully filled out and contains a valid `knowledge_graph_evidence` block.

## 7. Reasoning Step
- [ ] Pass the compiled `ContextBundle` to the Reasoning Engine.
- [ ] Capture the reasoning output, detailing candidate paths and evidence weights.

## 8. Decision Step
- [ ] Pass reasoning outputs and context to the Decision Engine.
- [ ] Confirm the returned verdict:
  - `PROCEED` -> Continue to execution.
  - `PROCEED_WITH_CONTRACT` -> Continue if execution contract checks pass.
  - `DEFER` -> Halt loop; wait for dependent tasks.
  - `BLOCK` -> Halt loop; mark task blocked.
  - `STOP_AND_ESCALATE` -> Exit immediately.

## 9. Supervisor Route
- [ ] Supervisor parses Decision Engine output.
- [ ] If verdict is `STOP_AND_ESCALATE`, execute the escalation sequence.
- [ ] Check task type: if Class 8 (Live Risk), suspend transition and wait for Operator explicit approval.

## 10. Execution Step
- [ ] Invoke subcommands under locked PID control.
- [ ] Redirect all standard output and standard error streams to isolated logs.

## 11. Verification Step
- [ ] Run the automated test commands (e.g. `pytest`).
- [ ] Check return code of test runner.
- [ ] Scan logs for occurrences of `AttributeError`, `Traceback`, or unexpected warnings.

## 12. Repair Loop
- [ ] If verification fails, increment the repair counter.
- [ ] Feed error logs back into Reasoning context.
- [ ] Execute target fixes.
- [ ] Re-run verification (maximum 3 repair cycles).
- [ ] If repairs are exhausted, escalate and stop.

## 13. Commit Boundary Enforcement
- [ ] Run `git diff` to identify modified files.
- [ ] Assert that no files outside the bundle's `allowed_scope` were changed.
- [ ] Assert that no files inside `forbidden_scope` were changed.
- [ ] Stage and commit verified changes.

## 14. Memory OS Update
- [ ] Update persistent state registries in Memory OS V2.
- [ ] Log realized outcomes of the task.

## 15. State & Queue Synchronization
- [ ] Set current task status to `DONE` in `TASK_QUEUE_001.json`.
- [ ] Set `last_completed_task` to the current task ID in `ACTIVE_WORKFLOW_STATE_001.json`.
- [ ] Append a loop memory history record in `LOOP_MEMORY_20260627_001.json`.
- [ ] Identify and set the next task to `READY`.

## 16. Closeout & Cleanup
- [ ] Release task PID locks.
- [ ] Finalize telemetry payloads and rotate log files.

---

## 17. Stop Invariants
The loop coordinator must abort execution immediately if:
- Safety Memory is missing or corrupted.
- RKG graph query is missing for Class 6+ tasks.
- Forbidden scopes are modified.
- High-risk keywords (e.g., wallet, live) are modified without authorization.
- Maximum repair attempts (3) are exceeded.
- Operator approval is missing for Class 8 tasks.

---

## 18. Operator Authorization (Class 8 Only)
```text
I hereby authorize the execution of task Class 8 (Live Risk) under the specified contract parameters:

Operator Name: __________________________
Signature:     __________________________
Date/Time:     __________________________
```
