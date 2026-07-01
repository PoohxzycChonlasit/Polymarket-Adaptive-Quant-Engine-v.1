# EXECUTION CONTRACT: EV_PASS_TO_RISK_APPROVAL_BLOCKER_AUDIT_001

## SECTION 1 - TASK IDENTITY
contract_id: CONTRACT-20260701-DIAGNOSTIC-001
task_id: EV_PASS_TO_RISK_APPROVAL_BLOCKER_AUDIT_001
task_class: 2
workflow_tier: STANDARD
agent_pipeline_id: DIAGNOSTIC_AUDIT
skills: [observability_incident, no_entry_diagnostics]
allowed_files: [docs/reports/]

## SECTION 2 - SAFETY & SCOPE CHECK
safety_memory_required: false
max_repairs: 0
commit_policy: MANUAL_ONLY
evidence_required: B

## SECTION 7 - ARCHITECTURE GOVERNANCE
batch_id: BATCH_N/A
refactor_target: N/A
reasoning: "Diagnostic audit of the EV pass to risk approval funnel to find no-entry blockers"

## SECTION 18 - VERIFICATION CHECKLIST
- [ ] No root markdown created
- [ ] EV pass funnel built and analyzed
- [ ] NO_HARDCODE guardrails respected
