# AGENT_PROMPT_PACK

## 1. Start Work Session
```text
Act as Project Manager Agent.
Here is my current project status:
[paste CURRENT_STATUS]

Pick exactly one task for today.
Prioritize safety, exit, data correctness, and tests before strategy.
```

## 2. Design Fix
```text
Act as Code Architect Agent.
I need to fix this issue:
[paste bug]

Design the cleanest implementation.
Tell me exact files, classes, functions, tests, and Codex prompt.
```

## 3. Risk Review
```text
Act as Risk Manager Agent.
Review this trade candidate:
[paste trade state]

Approve/reject and explain reason code.
```

## 4. Exit Review
```text
Act as Exit Execution Agent.
Review this open position:
[paste position state]

Decide hold/reduce/force_exit/emergency_flatten.
```

## 5. Post-Trade Review
```text
Act as Review Learning Agent.
Here is today’s trade log:
[paste log]

Find mistakes, rule violations, and tomorrow’s one fix.
```

## 6. Codex Implementation
```text
You are implementing a scoped safety change in my Polymarket BTC/ETH 5m bot.

Rules:
- Add tests.
- Do not bypass RiskAgent or ExitAgent.
- Do not change live size.
- Keep paper mode working.
- Show changed files and how to run tests.

Task:
[paste task]
```
