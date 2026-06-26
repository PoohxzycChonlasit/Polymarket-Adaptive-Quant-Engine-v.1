# Implementation Plan — Bankroll and Position Sizing Fixes (TASK — BANKROLL_SIZING_RUNTIME_AUDIT_001)

This plan details the code changes and verification steps to address the position sizing pipeline rejections and logging mismatches identified during the forensic audit.

## User Review Required

> [!IMPORTANT]
> The active question `LOW_PRICE_TRUTH_RESOLUTION_001` blocks "sizer changes" and "execution changes" under normal governance. However, since this task explicitly instructs moving to the implementation phase for these sizing bugs, we proceed with this design for user approval.

> [!NOTE]
> There are pre-existing test failures in `test_paper_mode.py`, `test_candidate_instance_shadow_propagation.py`, etc., that are unrelated to position sizing. To isolate and verify our changes cleanly, the verification plan runs only the execution risk controls test suite (`tests/test_execution_risk_controls.py`), which is currently 100% green.

## Proposed Changes

We propose the following code changes grouped by component:

---

### Sizing and Risk Configuration

#### [MODIFY] [settings.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/config/settings.py)
* Update default value of `micro_survival_min_position_size` from `0.05` to `0.10` to match the Polymarket CLOB exchange's hard minimum order limit of $0.10.

---

### Sizing Math and Core Logic

#### [MODIFY] [risk_manager.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/risk_manager.py)
* Fix the math bug in `build_micro_survival_risk_plan` around line 548 where `notional_size = min(max(risk_cap_usd, minimum_usd), risk_cap_usd, account_balance)` is simplified to `min(risk_cap_usd, account_balance)`.
* Change to: `notional_size = min(max(risk_cap_usd, minimum_usd), account_balance)`

#### [MODIFY] [trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py)
* Fix the same math bug in `_micro_position_size` around line 629 where `min(max(self._micro_survival_min_position_size(), risk_cap), risk_cap, balance)` simplifies to `min(risk_cap, balance)`.
* Change to: `notional_size = min(max(risk_cap, self._micro_survival_min_position_size()), balance)`
* Correct the win rate logging mismatch in the `_emit_zero_size_probe_event` caller around line 9856. Change `confidence=confidence` to `confidence=probability.p_yes if model_side == "YES" else probability.p_no` to log the win rate of the actual side traded instead of the directional confidence score.

---

## Verification Plan

### Automated Tests
* Run `python -m pytest tests/test_execution_risk_controls.py` to verify no regressions in the risk control logic.
* Add unit tests in `tests/test_execution_risk_controls.py` to assert correct math behavior for `build_micro_survival_risk_plan` and `_micro_position_size` under small balances.

### Manual Verification
* Run a read-only smoke verification:
  `python main.py --mode verify`
* Monitor a paper trading cycle to verify that log outputs match the expected win rates for skipped trades.
