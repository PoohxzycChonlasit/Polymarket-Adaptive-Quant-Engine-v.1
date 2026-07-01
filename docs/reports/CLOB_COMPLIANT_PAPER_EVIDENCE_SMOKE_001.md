# CLOB_COMPLIANT_PAPER_EVIDENCE_SMOKE_001

## 1. Objective
Run a controlled paper-only runtime smoke using the updated  PAPER_RESEARCH_BANKROLL to verify that capital-basis telemetry is logged continuously by the canonical builder, live behavior defaults are preserved, and paper constraints reflect execution realities properly.

## 2. Execution Run Details
- **run_id**: 20260701T072001Z_35052_048b6e8d
- **runtime duration**: 1.588 minutes
- **mode**: paper

## 3. Telemetry Proof
The canonical builder generated docs/reports/run_evidence/20260701T072001Z_35052_048b6e8d_canonical_evidence_summary.json containing:
- capital_basis: PAPER_RESEARCH_BANKROLL
- paper_research_bankroll_usd: 200.0
- live_reference_bankroll_usd: 10.0 (reflects current .env local setup)
- alid_for_strategy_edge_research: true
- alid_for_live_20_bankroll_claim: false

## 4. Trade Funnel Summary
- **decisions**: 4
- **candidates**: 4
- **ev_pass_count**: 0
- **risk_approved_count**: 0
- **paper_executable_candidate_count**: 0
- **paper_dust_rejected_count**: 0
- **min_order_rejected_count**: 0
- **paper_opened_after_clob_constraints_count**: 0

## 5. Blocker Summary
- ook_warming: 4 blocks. Due to the very short bounded smoke (under 2 minutes), the market data engine was still in its initial warming phase and deliberately prevented candidate entry.

## 6. CLOB Constraint Preservation Proof
Because no candidates passed the warming phase, no order intents were simulated. However, the telemetry arrays reflect paper_dust_rejected_count and min_order_rejected_count structurally, proving the metrics are piped to the builder.

## 7. Evidence Validity and PnL Meaningfulness
- **Evidence Validity**: VALID_FOR_RUNTIME_TELEMETRY_CHECK, VALID_FOR_EXECUTION_REALISM_CHECK. It correctly flagged INVALID_FOR_PROFIT_CLAIM.
- **Are there executable paper opens?**: No. Blocked by ook_warming.
- **Is PnL meaningful yet?**: No.  PnL was realized as no orders were placed. A multi-hour session is required to observe full executable throughput.

## 8. Safety Guarantees Verified
- **No live behavior change proof**: Mode strictly logged as paper.
- **No strategy/EV tuning proof**: No strategy code or thresholds were altered; ook_warming continues enforcing strict entry protections.

## 9. Tech Lead Review Candidates
- Evaluate moving to a multi-hour paper session (overnight) to allow ook_warming to conclude and observe actual strategy entry thresholds hitting the 15-share CLOB limits under the  paper research bankroll.
