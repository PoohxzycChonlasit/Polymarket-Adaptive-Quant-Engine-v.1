# EXECUTION CONTRACT: CLOB_COMPLIANT_BOUNDED_PAPER_EVIDENCE_RUN_002

## SECTION 1 - TASK IDENTITY
contract_id: CONTRACT-20260701-EVIDENCE-002
task_id: CLOB_COMPLIANT_BOUNDED_PAPER_EVIDENCE_RUN_002
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
reasoning: "Bounded paper-only run to collect evidence of candidate progression past risk_off"

## SECTION 13 - STOP CONDITIONS
Immediate STOP if any of:
- Live mode detected
- Live order path triggered
- risk_mode_lockdown:hard_drawdown appears again
- capital_basis missing
- next_task policy regression
- valid_for_live_reference_bankroll_claim incorrectly true

## SECTION 18 - VERIFICATION CHECKLIST
- [ ] No root markdown created
- [ ] Paper run >30 mins completed
- [ ] JSONL fields verified
- [ ] HARDCODE_AUDIT_STATUS recorded
