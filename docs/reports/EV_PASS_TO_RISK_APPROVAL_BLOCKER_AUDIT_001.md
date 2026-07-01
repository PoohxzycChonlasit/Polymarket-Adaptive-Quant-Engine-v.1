# EV_PASS_TO_RISK_APPROVAL_BLOCKER_AUDIT_001

## Run ID Analyzed
`20260701T104421Z_28776_49a52dd3`

## Files Read
- `docs/reports/CLOB_COMPLIANT_BOUNDED_PAPER_EVIDENCE_RUN_002.md`
- `runtime/quant_data/decision_log/2026-07-01.jsonl`
- `polymarket/trader.py`
- `polymarket/order_manager.py`
- `polymarket/position_sizing.py`
- `polymarket/delta_engine.py`
- `polymarket/bankroll_tiers.py`

## EV-Pass Sample Count
**23 candidates** passed the EV gate in the analyzed 35-minute run.

## EV-Pass to Risk-Approval Funnel
Of the 23 candidates that passed EV thresholds:
- **0** received Risk Approval.
- Blockers for the 23 candidates:
  - `time_unsafe` (`Entry cutoff`): **2**
  - `delta_extreme`: **1**
  - `clob_empty_response`: **1**
  - `risk_plan_zero`: **19**
    - Due to `confidence_too_low`: 18
    - Due to `min_order_size_not_met`: 1

## `risk_plan_zero` Source and Explanation
Source: `polymarket/position_sizing.py` and `polymarket/trader.py`.
There is a **LOGIC BUG** in `polymarket/trader.py`. 
When calling `self.order_manager.build_order_plan(order_request)`, `trader.py` creates the `OrderRequest` by assigning `win_rate = probability.p_yes`. 
Then `order_manager.py` passes `confidence = request.win_rate` directly into `PositionSizingInput`. 
`PositionSizingInput` subsequently compares this `confidence` value against a `confidence_floor` (hardcoded to 0.54 by default).
**Result:** Any candidate with a model probability (win rate) below 54% is artificially rejected by the risk engine as `confidence_too_low`, entirely regardless of its actual `confidence_score`! This effectively prevents the bot from ever taking underdog positions, squashing the vast majority of EV-pass candidates.
When `confidence_too_low` is not triggered (win rate > 54%), it can still hit `min_order_size_not_met` if the combination of `base_risk_pct` and `multipliers` drops the final position size below the $1.00 CLOB minimum. This part is expected and healthy.

## `time_unsafe` Source and Explanation
Source: `polymarket/trader.py` (`_evaluate_entry_cutoff`).
The system correctly blocks candidates near expiry (e.g. `<= 90` seconds). Candidates were correctly blocked by `hard_close_zone` (<= 45s) or because they failed adaptive latency tests (`decision_latency_high`). This is expected behavior for 5-minute markets to prevent execution risk.

## `delta_extreme` Source and Explanation
Source: `polymarket/delta_engine.py` and `polymarket/trader.py`.
Candidates were correctly blocked because their `delta_score` exceeded the threshold for `EXTREME` (e.g., highly volatile, huge velocity, or tiny distance to strike near expiry). This is a vital microstructure protection.

## CLOB Minimum Impact
The CLOB minimum ($1.00) is acting as a binding constraint when candidates barely pass the EV gate and have their size suppressed by multipliers (e.g. poor liquidity, wide spread, or low confidence multipliers). This successfully protects the bot from submitting invalid dust orders.

## Root Cause Classification
`REPORTING_MISMATCH` and `CONFIDENCE_GATE_DOMINANT` (due to the `win_rate` vs `confidence_score` bug).

## Longer Run Justification
A 2-6 hour run in the current state would likely just repeat the same zero-risk-approval pattern for underdogs due to the `win_rate` -> `confidence` bug. We must fix this mapping bug before running an extended paper session.

## Recommended Next Task
**Fix the `win_rate` -> `confidence` bug in `order_manager.py` / `trader.py`**. `OrderRequest` should explicitly accept `confidence_score` and pass it to `PositionSizingInput`, rather than conflating it with `win_rate`.

## No Runtime Trading Behavior Change Proof
No code was modified in `polymarket/` or `config/`.

## No Live Behavior Change Proof
Verified via absence of git diffs.

## No Strategy/Risk/EV Change Proof
Verified via absence of git diffs.

## Hardcode Audit Status
**HARDCODE_AUDIT_STATUS**: PASS
**NEW_CONSTANTS_ADDED**: NONE
**CONSTANT_PROVENANCE**: NONE
**MAGIC_VALUES_FOUND**: NONE
**NO_HARDCODE_PROOF**: Pure read-only audit. No runtime modifications made.

## Remaining Uncertainty
Whether fixing the `win_rate` bug will finally yield CLOB-executable candidates, or whether the `min_order_size_not_met` rejection will dominate once `confidence_too_low` is resolved.

## Tech Lead Review Candidates
- `ORDER_MANAGER_CONFIDENCE_MAPPING_BUG_FIX_001`
