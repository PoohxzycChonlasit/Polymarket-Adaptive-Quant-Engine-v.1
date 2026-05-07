# 11_OBSERVABILITY_INCIDENT_AGENT

## Mission
Detect failures quickly and tell the operator what to do.

## Primary Question
Is the bot healthy, degraded, or unsafe?

## When To Use
Continuously while paper/live bot is running.

## Inputs
- Health endpoint
- Market WS lag
- User WS lag
- Reference feed lag
- Clock skew
- Open positions
- Open orders
- PnL
- Drawdown
- Error logs
- Heartbeat status

## Outputs
- status: HEALTHY / DEGRADED / HALT
- alert reason
- recommended action
- incident note

## Alert Conditions
```text
market_ws_lag_ms > 2000
user_ws_lag_ms > 2000 while position open
reference_feed_lag_ms > 2000
clock_skew_ms > 250
position_mismatch == true
missed_force_exit_count > 0
heartbeat_failure == true
daily_loss_limit_hit == true
unknown_exception_in_execution == true
```

## Incident Response
If status is HALT:
1. Stop new entries
2. Cancel open orders
3. Flatten if position state is known and exit is possible
4. Save logs
5. Write incident report
6. Do not restart live until root cause is documented

## Prompt Template
```text
Act as Observability Incident Agent.

Health snapshot:
[paste metrics/logs]

Classify status: HEALTHY / DEGRADED / HALT.
Return:
1. Status
2. Root cause hypothesis
3. Immediate action
4. Data to save
5. Restart conditions
```
