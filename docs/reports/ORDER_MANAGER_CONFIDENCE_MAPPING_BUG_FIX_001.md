# ORDER_MANAGER_CONFIDENCE_MAPPING_BUG_FIX_001

## Files Changed
- `polymarket/order_manager.py`
- `polymarket/trader.py`
- `tests/execution/test_order_manager.py` (New file)
- `tests/integration/test_execution_risk_controls.py`
- `tests/polymarket/test_bankroll_tiers.py`

## Old Mapping Behavior
In `trader.py`, `OrderRequest` was instantiated with `win_rate=probability.p_yes` (or `p_no`).
In `order_manager.py`, `PositionSizingInput` was instantiated with `confidence=request.win_rate`.
This meant that the raw probability prediction (win rate) was directly used as the confidence score for position sizing. If the model predicted an underdog (win rate < 0.50), it would be strictly blocked by the `confidence_floor` (0.54) in the position sizing engine, regardless of the actual confidence score of the signal.

## New Mapping Behavior
`OrderRequest` now explicitly accepts a `confidence_score` field.
In `trader.py`, `OrderRequest` is instantiated with both `win_rate=probability.p_yes` (or `p_no`) AND `confidence_score=confidence` (where `confidence` is the locally computed `micro_prob` or `BACKTEST_WIN_RATE` derived confidence).
In `order_manager.py`, `PositionSizingInput` is instantiated with `confidence=request.confidence_score` (falling back to `win_rate` if `confidence_score` is not provided or <= 0 for backward compatibility during partial test coverage).

## Confidence Source
The correct `confidence` variable already existed in `trader.py` (around line 8058), computed from `micro_prob` based on momentum, price anchor, and imbalance. It is now properly passed to `OrderRequest`.

## Win Rate / Confidence Separation Proof
`OrderRequest` now has both `win_rate` and `confidence_score` as separate fields. The mathematical probability (EV edge calculations) still uses `win_rate`, while the risk gate uses `confidence_score`.

## Telemetry Fields Added
No new telemetry fields were explicitly added because `confidence` is already cleanly mapped into the position sizing telemetry via `PositionSizingResult.confidence_multiplier` and logged by `_decision_diagnostics_payload`.

## Tests Run
- Added `tests/execution/test_order_manager.py` with `test_order_manager_confidence_mapping_bug_fix` and `test_low_confidence_score_rejected`.
- Ran full test suite to confirm backward compatibility.

## Regression Result
Underdog signals (win_rate < 0.54) with strong confidence scores (confidence_score >= 0.54) now pass the `confidence_too_low` risk gate, successfully moving to the CLOB sizing constraint checks. Weak confidence scores are still correctly rejected.

## No Threshold Change Proof
`confidence_floor` remains unchanged at `0.54`. The change is strictly a structural mapping fix. No risk, EV, or entry thresholds were modified.

## No Live Behavior Change Proof
Verified via manual preflight that no live configurations were altered.

## No Runtime Trading Behavior Change Proof
Other than fixing the structural gate blockage, no logical paths, sizing mathematics, or trading limits were touched.

## Hardcode Audit Status
**HARDCODE_AUDIT_STATUS**: PASS
**NEW_CONSTANTS_ADDED**: NONE
**CONSTANT_PROVENANCE**: NONE
**MAGIC_VALUES_FOUND**: NONE
**NO_HARDCODE_PROOF**: Followed guardrails strictly. The fix was purely a dataclass modification and kwarg mapping.

## Remaining Uncertainty
It remains to be seen how many EV-pass candidates will now successfully clear the CLOB minimum-size constraint given the corrected confidence multiplier, and whether a new extended paper evidence run is now required.

## Tech Lead Review Candidates
- None (ready for bounded paper run)
