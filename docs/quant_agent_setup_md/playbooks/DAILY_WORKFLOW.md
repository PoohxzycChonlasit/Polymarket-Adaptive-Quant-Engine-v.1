# Daily Workflow

> Last synced: 2026-05-08.

## Goal

Work like a small quant desk: review evidence, isolate one problem, implement, test, run paper/replay when needed, and document.

## Daily Schedule

```text
Session Start
1. Open CURRENT_PROJECT_STATUS.md
2. Open CODEX_START_HERE.md and AGENTS.md
3. Open docs/KNOWN_ISSUES.md
4. Check mode, balance source, latest blockers, and unresolved bugs
5. Pick one task only

Build Session
6. Use Project Manager Agent for priority if scope is unclear
7. Use Code Architect Agent for multi-file design
8. Use the relevant safety agent docs
9. Send exact implementation spec to Codex
10. Review diff
11. Run targeted tests

Trading/Replay Session
12. Run paper or replay only when behavior changed
13. Check risk decisions
14. Check exit decisions
15. Check logs, terminal dashboard, and skip reasons

End Session
16. Update CURRENT_PROJECT_STATUS.md if project state changed
17. Update docs/KNOWN_ISSUES.md if bugs/debt changed
18. Update daily note or trade review when applicable
19. Set tomorrow's one fix
```

## Useful Test Commands

```bash
pytest -q tests/test_paper_mode.py tests/test_execution_risk_controls.py tests/test_exit_agent.py
pytest -q tests/test_logging_resilience.py tests/test_terminal_dashboard_display.py
python -m pytest tests/ -q
```

## Daily Rule

If you cannot explain today's single task in one sentence, the scope is too large.
