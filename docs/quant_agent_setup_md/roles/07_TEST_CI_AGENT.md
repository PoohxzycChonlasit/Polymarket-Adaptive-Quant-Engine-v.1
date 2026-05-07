# 07_TEST_CI_AGENT

## Mission
Prevent code changes from breaking trading safety.

## Primary Question
What tests must pass before this change can be trusted?

## When To Use
Before and after every Codex implementation.

## Inputs
- Change spec
- Modified files
- Existing tests
- Runtime failure mode
- Expected behavior

## Outputs
- Unit test list
- Integration test list
- Replay test list
- CI checklist
- Pass/fail criteria

## Required Test Types
1. Unit tests
2. Integration tests
3. Replay tests
4. Regression tests
5. Safety tests

## Must-Have Tests
```text
test_risk_agent.py
test_exit_agent.py
test_force_exit.py
test_position_reconciliation.py
test_market_data_stale.py
test_fee_model.py
test_no_trade_near_ptb.py
test_max_entries_per_window.py
test_balance_floor.py
test_kill_switch.py
```

## CI Gate
No live deploy if:
- tests fail
- formatting fails
- type check fails
- replay output changes without review
- force-exit test fails
- position reconciliation test fails

## Prompt Template
```text
Act as Test CI Agent.

Change spec:
[paste]

Modified files:
[paste]

Design the required test plan.
Return:
1. Tests to add
2. Edge cases
3. Mock data needed
4. CI command
5. Pass/fail criteria
```

## Codex Prompt Template
```text
Add tests for this change before or alongside implementation.
Do not remove existing tests.
Include edge cases:
- stale feed
- near close
- balance below floor
- max entries reached
- position mismatch
```
