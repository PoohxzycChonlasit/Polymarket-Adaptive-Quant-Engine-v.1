# PAPER_RESEARCH_BANKROLL_SEPARATION_IMPLEMENTATION_001

## 1. Objective
Implement a clear paper research bankroll separation to safely allow scaling paper trades to CLOB minimums (>= 15 shares) without incorrectly labeling the data as valid for a live  bankroll constraint.

## 2. Bankroll Accounting Paths Modified
The accounting for paper versus live bankrolls in polymarket/trader.py was separated during initialization.

- Before: self.bankroll_state initialized from self.settings.account_balance.
- After: If paper_trading is true, the BankrollState is initialized with PAPER_RESEARCH_BANKROLL_USD (from a new module) while maintaining the original live balance purely for reference telemetry.

## 3. Capital Basis Model
Added explicit typing fields to BankrollState:
- capital_basis (PAPER_RESEARCH_BANKROLL vs LIVE_BANKROLL)
- paper_research_bankroll_usd
- live_reference_bankroll_usd
- alid_for_live_20_bankroll_claim
- alid_for_strategy_edge_research

## 4. Bankroll Behaviors
- **Research Bankroll**: Value is fixed at .00 (PAPER_RESEARCH_BANKROLL_USD in polymarket/execution/paper_accounting.py). It is used exclusively when paper_trading is active.
- **Live Reference Bankroll**: Defaults to the original $20.00 configured in .env.

## 5. CLOB Constraint Preservation
CLOB constraints mapped in polymarket/execution/clob_constraints.py (minimum order size shares = 15.0, minimum tick size = 0.01) were **not** modified. Paper traces still reject <15 share dust positions.

## 6. Telemetry Fields Added
A new helper enrich_paper_accounting_telemetry was added to enrich logs with:
- capital_basis
- paper_research_bankroll_usd
- live_reference_bankroll_usd
- position_notional_pct_of_research_bankroll
- position_notional_pct_of_live_reference_bankroll
- alid_for_live_20_bankroll_claim
- alid_for_strategy_edge_research
- clob_compliant_paper_trade

These are aggregated by the canonical builder into standard run evidence summaries.

## 7. Tests Run
Tests added to 	ests/observability/test_paper_accounting_telemetry.py mapped out and verified:
1. 	est_paper_accounting_telemetry_adds_capital_basis: Ensured fields and mathematical percentages (position notional against respective bankroll references) evaluate accurately.
2. 	est_canonical_builder_separation_logic: Tested canonical run summary extraction logic with dummy dataset input to assert exact extraction parity.

All tests passed successfully. Pytest run output is fully clean.

## 8. Evidence Validity
- **Valid for Strategy Edge**: YES. A scaled bankroll isolates prediction probability execution outcomes.
- **Valid for  Live Wallet Claim**: NO. By mathematical definition, the risk limits enforced on a  wallet are fundamentally invalid on a  wallet due to minimums requiring extreme drawdown exposures.

## 9. Safety Guarantees
- No config/settings.py changes.
- No .env modifications.
- Live behaviors strictly unaltered.
- No strategy/EV logic was altered.

## 10. Tech Lead Review Candidates
- None for this specific scope. Await execution.
