# INCIDENT_RESPONSE

## When This Applies
Use when live/paper bot behaves unexpectedly.

## Critical Incidents
- Bot does not exit before close
- Bot enters more than allowed
- Position mismatch
- Unknown open position
- Feed stale while position open
- Daily loss limit hit
- Balance below floor in live mode
- Exception in execution loop

## Immediate Actions
```text
1. Disable new entries
2. Activate kill switch
3. Cancel open orders
4. Reconcile positions
5. Flatten if safe and state is known
6. Save logs
7. Stop live bot
8. Write incident note
```

## Incident Note Template
```text
# Incident Report

Date:
Mode:
Market:
Window:
What happened:
Expected behavior:
Actual behavior:
Position size:
Loss/risk:
Root cause hypothesis:
Files involved:
Fix required:
Test required:
Can live restart? YES/NO
```

## Restart Conditions
Live may restart only when:
- root cause documented
- bug fixed
- test added
- replay passes
- paper test passes
- no position mismatch
