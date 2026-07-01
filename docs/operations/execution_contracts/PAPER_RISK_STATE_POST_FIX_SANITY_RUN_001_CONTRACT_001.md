# EXECUTION CONTRACT: PAPER_RISK_STATE_POST_FIX_SANITY_RUN_001

## SECTION 1 - TASK IDENTITY
contract_id: CONTRACT-20260701-SANITY-001
task_id: PAPER_RISK_STATE_POST_FIX_SANITY_RUN_001
task_class: 3
workflow_tier: FAST
agent_pipeline_id: PAPER_EVALUATION
skills: [observability_incident, paper_evaluation]
allowed_files: [docs/reports/]

## SECTION 2 - SAFETY & SCOPE CHECK
safety_memory_required: false
max_repairs: 0
commit_policy: MANUAL_ONLY
evidence_required: A

## SECTION 7 - ARCHITECTURE GOVERNANCE
batch_id: BATCH_N/A
refactor_target: N/A
reasoning: "Paper-only sanity run to verify risk state fix"

## SECTION 13 - STOP CONDITIONS
Immediate STOP if any of:
- Live mode detected
- Live order path triggered
- risk_mode_lockdown:hard_drawdown appears immediately again
- capital_basis missing
- next_task policy regression
- unhandled exception

## SECTION 18 - VERIFICATION CHECKLIST
- [ ] No root markdown created
- [ ] Paper run 5+ cycles exit 0
- [ ] JSONL fields verified
- [ ] HARDCODE_AUDIT_STATUS recorded
