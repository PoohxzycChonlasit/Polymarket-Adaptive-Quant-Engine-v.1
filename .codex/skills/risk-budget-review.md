# Skill: Risk Budget Review

## Purpose

Review Dynamic Quant Risk Budget evidence for paper or planned research tasks.

This skill is for safety review, not for loosening risk gates.

## Required Concepts

Track:

- bankroll
- current equity
- current cash
- open exposure
- realized PnL
- unrealized PnL
- market risk used
- session risk used
- drawdown
- bankroll tier id
- risk mode
- target exposure
- current exposure
- risk guard state

## Review Questions

| Area | Questions |
|------|-----------|
| Bankroll tier | Is the tier correct for current equity and hysteresis? |
| Risk mode | Is NORMAL, DEFENSIVE, MICRO_RECOVERY, or LOCKDOWN justified? |
| Exposure | Is current exposure within per-market and session caps? |
| Drawdown | Is drawdown forcing correct defensive behavior? |
| Sizing | Did zero-size come from tier floor, minimum order, bankroll, or risk guard? |
| Target vs current | Is the future target exposure safely above, below, or equal to current exposure? |
| Reconciliation | Is position truth known before any new entry or exit? |

## Hard Forbids

- No martingale.
- No unlimited averaging down.
- No all-in behavior.
- No risk bypass.
- No stale-book use.
- No OrderIntent bypass.
- No reconciliation bypass.
- No forced-exit or panic-exit bypass.
- No live size change without explicit live-risk scope.

## Output Shape

Report:

1. risk state summary
2. bankroll tier and risk mode
3. exposure and drawdown
4. risk_plan_zero or risk rejection root cause
5. target exposure vs current exposure interpretation
6. safety verdict
7. next safe action

## Boundary

Risk review can recommend evidence to inspect or tests to run. It cannot change risk sizing, thresholds, live flags, or execution behavior unless the user explicitly scopes that implementation.
