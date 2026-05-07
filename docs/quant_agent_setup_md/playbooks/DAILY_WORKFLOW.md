# DAILY_WORKFLOW

## Goal
Work like a quant desk: review, isolate one problem, implement, test, replay, document.

## Daily Schedule
```text
Session Start
1. Open CURRENT_STATUS.md
2. Check mode and balance
3. Check unresolved bugs
4. Pick one task only

Build Session
5. Ask Project Manager Agent for priority
6. Ask Code Architect Agent for design
7. Send exact implementation spec to Codex
8. Review diff
9. Run tests

Trading/Replay Session
10. Run paper or replay
11. Check RiskAgent decisions
12. Check ExitAgent decisions
13. Check logs

End Session
14. Write TRADE_REVIEW.md
15. Update BUGS_AND_FIXES.md
16. Set tomorrow's one fix
```

## Daily Command Checklist
```bash
pytest -q
python -m pytest tests/test_risk_agent.py tests/test_exit_agent.py
# then run your paper/replay command
```

## Daily Rule
If you cannot explain today’s single task in one sentence, the scope is too large.
