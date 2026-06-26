# POSITION_SIZING_ENGINE_V1_IMPLEMENTATION_001 — Task List

## Phase 1: Code Fixes

- `[/]` Fix `micro_survival_min_position_size` default in `config/settings.py` (0.05 → 0.10)
- `[ ]` Fix math bug in `utils/risk_manager.py` `build_micro_survival_risk_plan` (line 548)
- `[ ]` Fix math bug in `polymarket/trader.py` `_micro_position_size` (line 629)

## Phase 2: Test Updates

- `[ ]` Update `test_execution_risk_controls.py` test expectations to reflect 0.10 floor
  - `test_micro_survival_mode_activates_for_sub_100_paper_bankroll` (line 684)
  - `test_micro_survival_rescues_min_size_zero_plan` (line 714)

## Phase 3: Verification

- `[ ]` Run `python -m pytest tests/test_execution_risk_controls.py -q` → all green
- `[ ]` Run `python main.py --mode verify` smoke check

## Phase 4: Report

- `[ ]` Create `IMPLEMENTATION_REPORT_POSITION_SIZING_V1.md`
