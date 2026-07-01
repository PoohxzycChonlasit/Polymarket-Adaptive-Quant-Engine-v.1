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
- Next task.

## Never Follow NEXT_TASK Blindly

`next_task` is a suggestion. The Profit Filter decides whether it is still valid.
