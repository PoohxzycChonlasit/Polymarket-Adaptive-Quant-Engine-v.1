# Daily Quant Workflow Playbook

Status: active daily workflow guidance. This is paper-first and docs/research friendly; it does not authorize live execution.

## Daily Sequence

1. Confirm current status and known blockers.
2. Review the latest paper evidence supplied by the operator.
3. Classify the day by lifecycle bottleneck: scanner, token readiness, orderbook readiness, liquidity/spread, candidate timing, risk, execution, or evidence quality.
4. Check regime/probability field coverage before drawing regime conclusions.
5. Review Dynamic Quant Risk Budget context: bankroll tier, drawdown, exposure, risk mode, and LOCKDOWN status when available.
6. Choose one focused next task.

## Research Focus

- Phase 1: improve regime/probability diagnostics and compact observability.
- Phase 2: run paper-only inventory replay and MFE/MAE analysis.
- Phase 3: design bounded multi-price inventory only after replay evidence.
- Phase 4: consider continuous probabilistic inventory trading only after paper evidence and safety gates.

## Daily Output

- Root Problem
- Evidence
- Quant Interpretation
- Risk / Safety Impact
- Recommended Action
- Tests or checks required
- What not to touch

## Safety Reminders

Do not claim live readiness. Do not loosen thresholds, risk, cutoff, or execution behavior during daily review unless the task explicitly scopes it and safety tests are selected.
