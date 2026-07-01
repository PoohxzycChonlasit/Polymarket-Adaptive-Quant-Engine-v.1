# EXECUTION CONTRACT: PAPER_ACCOUNTING_LIVE_REFERENCE_LEAK_FIX_001

## SECTION 1 - TASK IDENTITY
contract_id: CONTRACT-20260701-BUGFIX-001
task_id: PAPER_ACCOUNTING_LIVE_REFERENCE_LEAK_FIX_001
task_class: 3
workflow_tier: STANDARD
agent_pipeline_id: BUG_FIX
skills: [quant_safety_review, low_risk_refactor]
allowed_files: [polymarket/trader.py, tests/observability/test_paper_accounting_telemetry.py, docs/reports/]

## SECTION 2 - SAFETY & SCOPE CHECK
safety_memory_required: false
max_repairs: 3
commit_policy: MANUAL_ONLY
evidence_required: C

## SECTION 7 - ARCHITECTURE GOVERNANCE
```
batch_id: BATCH_N/A
refactor_target: polymarket/trader.py
reasoning: "Fix bug where live wallet balance overwrites paper cash balance."
```

## SECTION 13 - STOP CONDITIONS
Immediate STOP if any of:
- Unexplained hardcoded runtime value or assumption introduced.
- Live trading keyword in any command.

## SECTION 18 - VERIFICATION CHECKLIST
- [ ] git diff --name-only shows only allowed_files
- [ ] py_compile PASS
- [ ] Tests pass vs baseline
- [ ] HARDCODE_AUDIT_STATUS recorded
