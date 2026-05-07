# CODEX_WORKFLOW

## Purpose
Use Codex as the implementation agent, not as the decision-maker.

## Correct Flow
```text
ChatGPT Project: decide what to build
ChatGPT Project: write exact spec
Codex: implement exact spec
Codex: add tests
You: review diff
You: run tests/paper
ChatGPT Project: review results
```

## Codex Safety Prompt
```text
You are working on my Polymarket BTC/ETH 5-minute trading bot.

Primary goal:
Make the system safer and more deterministic.

Rules:
- Do not bypass RiskAgent.
- Do not bypass ExitAgent.
- Do not change live trading size unless explicitly asked.
- Do not remove tests.
- Do not store secrets in code.
- Keep paper mode working.
- Add tests for every safety rule.
- Show a diff summary.

Task:
[paste one scoped task]

Definition of done:
[paste exact conditions]
```

## Good Codex Tasks
```text
Add max_entries_per_window rule to RiskAgent and tests.
Add force_exit_secs rule to ExitAgent and tests.
Add KILL_SWITCH file check before order placement.
Add pytest.ini so imports work.
Refactor duplicated risk constants into one config file.
```

## Bad Codex Tasks
```text
Make the bot profitable.
Improve everything.
Rewrite the whole project.
Add AI trading.
Make it HFT.
```
