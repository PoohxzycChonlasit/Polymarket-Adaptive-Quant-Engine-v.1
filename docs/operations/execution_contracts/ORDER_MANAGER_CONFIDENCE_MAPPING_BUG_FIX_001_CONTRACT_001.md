# EXECUTION CONTRACT: ORDER_MANAGER_CONFIDENCE_MAPPING_BUG_FIX_001

## SECTION 1 - TASK IDENTITY
contract_id: CONTRACT-20260701-BUGFIX-001
task_id: ORDER_MANAGER_CONFIDENCE_MAPPING_BUG_FIX_001
task_class: 3
workflow_tier: STANDARD
agent_pipeline_id: BUG_FIX
skills: [observability_incident, test_ci]
allowed_files: [polymarket/trader.py, polymarket/order_manager.py, polymarket/position_sizing.py, tests/execution/]

## SECTION 2 - SAFETY & SCOPE CHECK
safety_memory_required: false
max_repairs: 2
commit_policy: MANUAL_ONLY
evidence_required: C

## SECTION 7 - ARCHITECTURE GOVERNANCE
batch_id: BATCH_N/A
refactor_target: N/A
reasoning: "Fix bug where win_rate is conflated with confidence_score in position sizing."

## SECTION 18 - VERIFICATION CHECKLIST
- [ ] No root markdown created
- [ ] OrderRequest updated to have `confidence_score`
- [ ] order_manager.py passes `confidence_score` to `PositionSizingInput.confidence`
- [ ] tests added
- [ ] NO_HARDCODE guardrails respected
