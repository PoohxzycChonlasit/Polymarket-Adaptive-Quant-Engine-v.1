# UPDATE_PAPER_SIZER_WITH_LIVE_CLOB_CONSTRAINTS_001

## Final Verdict
VALID_FOR_BLOCKER_DIAGNOSIS (Paper constraints implemented)

The paper-mode execution module has been updated to enforce live Polymarket CLOB minimum order and tick size constraints, ensuring that dust trades (e.g. 0.20 shares for a $0.10 notional budget) are correctly classified as rejected rather than simulated as executable fills.

## Implementation Details
### Paper Open Path
- **Found in:** `polymarket/trader.py` within `_submit_order`. The path correctly handles a `None` return value by logging it as a skipped trade with `NO_FILL` status and does not generate paper positions.
### Constraint Model
- **New Module:** `polymarket/execution/clob_constraints.py` containing `ClobConstraint` dataclass and the function `validate_paper_order`.
- **Defaults Enforced:** `minimum_order_size_shares=15.0`, `minimum_tick_size=0.01` exclusively in the constraint module without modifying settings or `.env`.
### Rejection Behavior
- **Size Rejection:** Checks if `shares < 15.0`. Triggers `PAPER_ONLY_DUST_REJECTED` and `dust_unexecutable_min_order`. 
- **Tick Validation:** Checks if `price` aligns with the 0.01 tick. Returns `PAPER_ONLY_TICK_REJECTED` and `tick_misaligned_rounding_required`.
- **Telemetry:** Logs rejection uniquely as `paper_order_rejected` instead of a `paper_fill` event. Emits new fields: `constraint_source`, `constraint_scope`, `clob_min_order_size_shares`, `clob_min_tick_size`, `proposed_shares`, `proposed_notional`, `minimum_executable_notional`, `clob_size_valid`, `clob_tick_valid`, `execution_realism_status`, `paper_reject_reason`.

## Canonical Builder Updates
The `tools/canonical_run_evidence_summary_builder.py` was updated to accurately capture and report these metrics in `trade_funnel_summary_v1`:
- `paper_dust_rejected_count`
- `min_order_rejected_count`
- `paper_executable_candidate_count`
- `paper_opened_after_clob_constraints_count`

**Evidence Validity Logic:** The validity engine now explicitly forces `INVALID_FOR_PROFIT_CLAIM` if `paper_executable_candidate_count == 0`, maintaining a conservative stance on execution realism.

## Tests Executed
- Executed `tests/execution/test_clob_constraints.py` and `tests/tools/test_clob_min_order_validation.py` using `pytest`.
- **Result:** 7/7 PASSED in 18.9s. Tests confirmed: dust rejection, 15 shares accepted, tick misalignment rejection, and safety against unknown constraints.

## No Live Behavior Change Proof
- Changes were scoped within `if self.settings.paper_trading:` blocks. 
- No modifications to strategy, EV, risk thresholds, sizing math (`position_sizing.py`), configuration (`settings.py`), or environment (`.env`).
- No live orders were executed or structurally touched.

## Remaining Uncertainty
- Whether to resolve dust entry logic by adjusting the minimum sizing thresholds natively in `polymarket/position_sizing.py` (which requires authorization to adjust risk thresholds) or leaving them to simply reject at the execution level.
- Live-tier tick-size formatting (CLOB endpoints accept exact floats versus string representations) was not addressed, as this focuses purely on paper validity screening.

## Tech Lead Review Candidates
- `AUTHORIZE_CLOB_COMPLIANT_MICRO_SIZING_001` (Adjusting the minimum notional size to >= $15 to unblock paper runs from continuous dust rejection).
