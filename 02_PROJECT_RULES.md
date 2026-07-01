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

Do not follow old `NEXT_TASK` blindly. Before work starts:

1. Read `00_MISSION.md`.
2. Apply the Profit Filter.
3. Lock scope.
4. Define acceptance criteria.
5. Validate evidence before claiming success.

## Backlog Rule

If work does not improve profit evidence, execution realism, risk, runtime safety, operator visibility, or market-time truth, move it to `06_BACKLOG.md`.
