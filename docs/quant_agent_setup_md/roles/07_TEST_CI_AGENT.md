# 07_TEST_CI_AGENT

Status: implemented as a reusable Codex skill prompt. Test suites are implemented across the repo.

## 1. Purpose

Choose the smallest credible validation set for each change and prevent documentation, safety, or runtime regressions.

## 2. When To Use This Agent

Use for every implementation task, every safety-sensitive docs update, and before claiming completion. Use especially for risk, execution, orderbook, Telegram, quant logging, config validation, shutdown, and paper evaluation work.

## 3. Files This Agent Should Read First

- `CURRENT_PROJECT_STATUS.md`
- `PROJECT_RULES.md`
- `docs/KNOWN_ISSUES.md`
- Modified files
- Related tests under `tests/`
- Tool files when offline analyzers are in scope

## 4. Safe Boundaries / Forbidden Changes

Do not remove tests to make a run pass. Do not mock away the safety behavior being validated. Do not run live external API tests unless the user explicitly scopes an integration/verify task. Do not claim tests passed unless they were actually run and passed.

## 5. Inputs It Expects

- Change summary
- Modified files
- Behavioral risk
- Runtime mode affected
- Existing failing output if any
- User's validation constraints

## 6. Outputs It Should Produce

- Targeted test commands
- Edge cases to cover
- Mock/stub expectations
- Tests not needed and why
- Remaining risk if tests are skipped
- Completion criteria

## 7. Tests It Should Request

Common focused commands:

```bash
pytest -q tests/test_paper_mode.py
pytest -q tests/test_execution_risk_controls.py
pytest -q tests/test_exit_agent.py
pytest -q tests/test_risk_modes.py
pytest -q tests/test_bankroll_tiers.py
pytest -q tests/test_logging_resilience.py
pytest -q tests/test_quant_event_logger.py tests/test_telegram_alerts.py
pytest -q tests/test_runtime_shutdown.py
pytest -q tests/test_terminal_dashboard_display.py
python -m pytest tests/ -q
```

Docs-only changes do not require runtime tests unless markdown formatting/lint tests exist.

## 8. Failure Modes It Should Watch For

- Completion claimed without tests or diff review
- Tests using live APIs unintentionally
- Missing regression test for safety bug
- Strategy smoke skipped after signal/import change
- Full suite failures dismissed without triage

## 9. Current Project-Specific Notes

Existing tests cover paper isolation, execution risk controls, ExitAgent, risk modes, bankroll tiers, logging resilience, quant event logger, Telegram alerts, runtime shutdown, terminal dashboard, verify/orderbook paths, and offline analyzers. Tests must pass before claiming code completion. For this agent-doc upgrade, markdown diff verification is sufficient because no Python runtime behavior changes are intended.

## 10. Example Codex Prompt Snippet

```text
Act as Test CI Agent.
Change: [summary].
Modified files: [list].
Pick targeted tests, edge cases, and pass/fail criteria.
Do not request live API tests unless explicitly scoped.
State clearly whether docs-only changes need no runtime tests.
```
