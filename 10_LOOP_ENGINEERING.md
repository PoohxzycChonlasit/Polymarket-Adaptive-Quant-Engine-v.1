# 10 Loop Engineering

## Profit-First Loop Engineering

Every loop must serve the Profit Engine mission.

```text
Mission Check
-> Profit Filter
-> Scope Lock
-> Acceptance Criteria
-> Plan Before Code
-> Execute Small
-> Validate
-> Repair
-> Evidence Pack
-> Final Report
```

## Step 1 - Mission Check

Confirm the work improves at least one Profit Filter category.

If not, move it to `06_BACKLOG.md`.

## Step 2 - Profit Filter

Name which category improves:

- Profitability.
- Expected value.
- Entry throughput.
- Risk/drawdown.
- Execution realism.
- Market reality.
- Position sizing reality.
- Quant math.
- Operator visibility.
- Runtime safety.

## Step 3 - Scope Lock

Define:

- Files allowed.
- Files forbidden.
- Runtime behavior unchanged or explicitly scoped.
- Tests/validation required.
- Hardcode audit required for any code task.

## Step 4 - Acceptance Criteria

Before work starts, define what success means.

No loop may rely on vague "looks good" completion.

## Step 5 - Plan Before Code

For docs-only work, plan sections and outputs.

For code work, identify exact modules and tests before editing.

## Step 6 - Execute Small

Make the smallest change that produces evidence.

No big-bang refactor.

## Step 7 - Validate

Run the validation promised by the task.

Docs-only:

- `git diff --check`.
- JSON validation if JSON touched.

Runtime/risk/sizing/execution:

- Stronger test and paper/runtime evidence required.

Code tasks:

- Run the no-hardcode checklist from `02_PROJECT_RULES.md`.
- Stop if unexplained magic values, hardcoded paths, dates, run IDs, bankroll values, market constants, or thresholds are introduced.
- Prefer metadata, config/schema values, named constants, explicit parameters, or documented defaults with provenance.

## Step 8 - Repair

Max repair attempts: 3.

If blocked after 3 attempts, stop and report. Do not expand scope.

## Step 9 - Evidence Pack

Record:

- Commands.
- Results.
- Files changed.
- Safety boundaries preserved.
- Remaining uncertainty.

## Step 10 - Final Report

Final report must state:

- What changed.
- What did not change.
- Evidence grade.
- `TECH_LEAD_REVIEW_CANDIDATES`.
- `BLOCKERS`.
- `RECOMMENDED_REVIEW_TOPICS`.

## NEXT_TASK Is Not Authorization

Automatic `NEXT_TASK` promotion is disabled.

- `next_task` must be `null` in active workflow state unless preserved only for historical compatibility.
- A `NEXT_TASK` value in an old report, queue entry, loop memory entry, or nested historical object is not authorization.
- Agents must not auto-start `NEXT_TASK`.
- Agents may provide candidate tasks for review only.
- Tech Lead Review is required before every new task.
- If unsure, stop and ask for authorization.

## Daily Loop Memory Rotation

At the start of each workday, `docs/operations/ACTIVE_WORKFLOW_STATE_001.json` must point to the current dated loop memory file.

Required active pointer fields:

- `active_work_date`
- `active_loop_memory_file`
- `workflow_governance.active_loop_memory_file`
- `tech_lead_review_required`
- `no_blind_next_task`

Active loop memory rules:

- There must be exactly one active workday loop memory file.
- Active loop memory files use the current work date in the filename.
- Archived loop memory files must not receive new task entries.
- Old loop memory files must record `status=ARCHIVED`, `read_only=true`, and `superseded_by`.
- If the active pointer date does not match the workday, stop and rotate before continuing.

## No Blind Next Task

After every workday rotation, task promotion requires Tech Lead review.

- `next_task` is not an authorization field.
- `next_authorized_task` must be `TECH_LEAD_REVIEW_REQUIRED` or explicit.
- AI agents must not continue stale `NEXT_TASK` values from archived loop memory.

## Report Output Template

Use these fields instead of `NEXT_TASK`:

- `TECH_LEAD_REVIEW_CANDIDATES`
- `BLOCKERS`
- `RECOMMENDED_REVIEW_TOPICS`

Compatibility note: if an old JSON schema requires `next_task`, keep it as `null` or `TECH_LEAD_REVIEW_REQUIRED`, never as an executable instruction.

## Git Operations Are Part of the Loop

Rules:
1. The AI agent must perform git pre-flight checks before every task:
   - `git status --short`
   - `git branch --show-current`
   - `git log --oneline -5`
   - `git status -sb`

2. The AI agent must stage only task-owned files.

3. The AI agent must never stage unrelated untracked files.

4. The AI agent must run validation before commit:
   - `git diff --check`
   - JSON validation if JSON touched
   - targeted tests if code touched

5. The AI agent must commit only after validation passes.

6. The AI agent must push after commit unless explicitly blocked.

7. The AI agent must run post-flight checks:
   - `git status --short`
   - `git status -sb`
   - `git log --oneline -3`

8. The AI agent must report:
   - commit hash
   - push status
   - branch sync status
   - remaining untracked files
   - whether working tree is clean

9. The human operator should not be asked to perform git commands manually unless:
   - credentials/tool permission are unavailable
   - remote push requires human authentication
   - conflict requires explicit human decision
   - destructive recovery is needed

10. Never force push without explicit operator authorization.

### Stop Conditions
- merge conflict
- branch behind origin
- push rejected
- unknown untracked files
- validation failure
- accidental staging of unrelated files
- runtime files changed outside scope
- unexplained hardcoded runtime value, threshold, path, date, bankroll, market constant, API URL, or semantic label

## No Hardcode Engineering Standard

All loop tasks that touch code must apply the no-hardcode engineering standard in `02_PROJECT_RULES.md`.

Final task output for code tasks must include:

- `HARDCODE_AUDIT_STATUS`
- `NEW_CONSTANTS_ADDED`
- `CONSTANT_PROVENANCE`
- `CONFIG_VALUES_USED`
- `MAGIC_VALUES_FOUND`
- `MAGIC_VALUES_JUSTIFIED`
- `MAGIC_VALUES_REJECTED`
- `NO_HARDCODE_PROOF`

If hardcoding is found, stop before commit and report the file, line, value, and recommended extraction path.
