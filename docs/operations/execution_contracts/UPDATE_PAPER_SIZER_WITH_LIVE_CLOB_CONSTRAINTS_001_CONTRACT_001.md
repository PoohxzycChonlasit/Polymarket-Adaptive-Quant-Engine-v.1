# Execution Contract: UPDATE_PAPER_SIZER_WITH_LIVE_CLOB_CONSTRAINTS_001

## Section 1: Task Identity
- Task: UPDATE_PAPER_SIZER_WITH_LIVE_CLOB_CONSTRAINTS_001
- Class: 3
- Agent: 20_INVENTORY_ENGINE_AGENT

## Section 2: Safe Execution Statement
- No live behavior changes.
- Sizing constraints are enforced in paper logic only.
- Validation logic resides in polymarket/execution/clob_constraints.py.
- Rejections are tracked distinctly from fills in canonical_run_evidence_summary_builder.py.

## Section 7: Tests
- Execution tests written in 	ests/execution/test_clob_constraints.py.
- Result: PASS 4/4

## Section 13: Files Touched
- polymarket/execution/clob_constraints.py (New)
- polymarket/trader.py (Modified)
- 	ools/canonical_run_evidence_summary_builder.py (Modified)
- 	ests/execution/test_clob_constraints.py (New)

## Section 18/19: Rollback
- Revert changes via git checkout origin/main.
