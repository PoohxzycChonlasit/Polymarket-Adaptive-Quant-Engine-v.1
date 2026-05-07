from __future__ import annotations

import pytest

from polymarket.risk_modes import (
    RiskMode,
    RiskModeState,
    evaluate_risk_mode,
    trade_quality_allowed,
)


@pytest.mark.parametrize(
    ("losses", "drawdown", "mode", "multiplier"),
    [
        (0, 0.00, RiskMode.NORMAL, 1.00),
        (2, 0.00, RiskMode.DEFENSIVE, 0.50),
        (0, 0.02, RiskMode.DEFENSIVE, 0.50),
        (3, 0.00, RiskMode.MICRO_RECOVERY, 0.25),
        (0, 0.04, RiskMode.MICRO_RECOVERY, 0.25),
    ],
)
def test_risk_mode_ladder_transitions(losses: int, drawdown: float, mode: RiskMode, multiplier: float) -> None:
    decision = evaluate_risk_mode(consecutive_losses=losses, drawdown_pct=drawdown)

    assert decision.mode == mode
    assert decision.size_multiplier == pytest.approx(multiplier)
    assert decision.allow_new_entries is (mode != RiskMode.LOCKDOWN)


def test_lockdown_overrides_recovery_modes() -> None:
    decision = evaluate_risk_mode(
        consecutive_losses=3,
        drawdown_pct=0.04,
        lockdown_reasons=("reconciliation_mismatch",),
    )

    assert decision.mode == RiskMode.LOCKDOWN
    assert decision.size_multiplier == 0.0
    assert not decision.allow_new_entries
    assert decision.reason == "reconciliation_mismatch"


def test_stateful_lockdown_stays_until_operator_reset() -> None:
    state = RiskModeState()
    state.trigger_lockdown("exit_failure")

    decision = state.update(consecutive_losses=0, drawdown_pct=0.0)

    assert decision.mode == RiskMode.LOCKDOWN
    assert decision.lockdown_reasons == ("exit_failure",)


def test_quality_gate_requires_signal_quality_in_reduced_modes() -> None:
    assert trade_quality_allowed(RiskMode.NORMAL, confidence=None) == (True, "normal")
    assert trade_quality_allowed(RiskMode.DEFENSIVE, confidence=None) == (False, "risk_mode_missing_quality")
    assert trade_quality_allowed(RiskMode.DEFENSIVE, confidence=0.64) == (False, "confidence_below_defensive")
    assert trade_quality_allowed(RiskMode.DEFENSIVE, confidence=0.65) == (True, "confidence_ok")
    assert trade_quality_allowed(RiskMode.MICRO_RECOVERY, confidence=0.74) == (False, "confidence_below_micro_recovery")
    assert trade_quality_allowed(RiskMode.MICRO_RECOVERY, confidence=0.75) == (True, "confidence_ok")
