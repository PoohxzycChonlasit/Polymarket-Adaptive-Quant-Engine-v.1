# 02 Project Rules

## Prime Directive

This repository exists to build a profitable quantitative trading engine for Polymarket Crypto 5-Minute Up/Down markets.

All work must pass the Profit Filter in `00_MISSION.md`.

## Do Not Modify Without Explicit Scope

- Trading thresholds.
- Strategy behavior.
- Risk behavior.
- Sizing behavior.
- Execution behavior.
- Paper/live behavior.
- `config/settings.py`.
- `.env`.
- Production runtime logic.

## Global Python Modular Code Standard

This rule applies to every `.py` file in the repository.

- Main files must stay thin.
- Orchestrators must stay thin.
- No logic dumping into main/runtime files.
- Quant math must live in quant-focused modules.
- Market logic must live in market-focused modules.
- Execution logic must live in execution-focused modules.
- Risk logic must live in risk-focused modules.
- Sizing and portfolio logic must live in portfolio-focused modules.
- Exit logic must live in exit-focused modules.
- Dashboard and telemetry must not contain trading decision logic.
- Modules must have single responsibility.
- Imports and exports must be clear.
- Avoid hidden global-state dependency where practical.
- No big-bang refactor.
- No behavior change during pure extraction.
- Tests are required after extraction.

## Runtime Safety Rules

- Paper mode is the default.
- Paper mode must never sign, submit, cancel, redeem, approve, or mutate live wallet state.
- Live mode requires explicit operator approval.
- Risk, reconciliation, stale-data, OrderIntent, forced-exit, and panic-exit protections outrank profit-seeking.
- No martingale.
- No all-in.
- No unlimited averaging down.
- No fixed live risk escalation.

## Task Routing Rule

Do not follow old `NEXT_TASK` values. `NEXT_TASK` is not authorization.

Before work starts:

1. Read `00_MISSION.md`.
2. Apply the Profit Filter.
3. Lock scope.
4. Define acceptance criteria.
5. Validate evidence before claiming success.
6. Confirm Tech Lead authorization for the specific task.

Agents may propose candidate tasks, blockers, and review topics. They must not auto-start recommended tasks from reports, queue entries, loop memory, or workflow state.

If authorization is unclear, stop and ask for Tech Lead review.

## Backlog Rule

If work does not improve profit evidence, execution realism, risk, runtime safety, operator visibility, or market-time truth, move it to `06_BACKLOG.md`.

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
