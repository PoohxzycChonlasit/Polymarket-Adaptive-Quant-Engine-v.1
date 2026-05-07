from __future__ import annotations

from polymarket.delta_engine import DeltaRegime
from polymarket.trend_runner import TrendRunnerInput, evaluate_trend_entry, evaluate_trend_runner


def test_trend_runner_requires_positive_ev() -> None:
    result = evaluate_trend_runner(
        TrendRunnerInput(
            side="YES",
            momentum=0.006,
            price_velocity=0.002,
            ev=0.0,
            confidence_score=0.70,
        )
    )

    assert not result.approved
    assert result.reason == "ev_not_positive"


def test_trend_runner_approves_confirmed_yes_trend() -> None:
    result = evaluate_trend_runner(
        TrendRunnerInput(
            side="YES",
            momentum=0.008,
            price_velocity=0.003,
            ev=0.07,
            confidence_score=0.72,
            delta_regime=DeltaRegime.NORMAL,
        )
    )

    assert result.approved
    assert result.side == "YES"
    assert 0.50 <= result.trend_size_multiplier <= 0.75


def test_trend_runner_requires_velocity_confirmation() -> None:
    result = evaluate_trend_runner(
        TrendRunnerInput(
            side="NO",
            momentum=-0.008,
            price_velocity=0.003,
            ev=0.04,
            confidence_score=0.70,
        )
    )

    assert not result.approved
    assert result.reason == "velocity_not_confirmed"


def test_trend_runner_requires_momentum_confirmation() -> None:
    result = evaluate_trend_runner(
        TrendRunnerInput(
            side="YES",
            momentum=-0.008,
            price_velocity=0.003,
            ev=0.04,
            confidence_score=0.70,
        )
    )

    assert not result.approved
    assert result.reason == "momentum_not_confirmed"


def test_trend_runner_blocks_extreme_delta() -> None:
    result = evaluate_trend_runner(
        TrendRunnerInput(
            side="YES",
            momentum=0.008,
            price_velocity=0.003,
            ev=0.04,
            confidence_score=0.70,
            delta_regime=DeltaRegime.EXTREME,
        )
    )

    assert not result.approved
    assert result.reason == "delta_extreme"


def test_trend_runner_blocks_bad_market_quality() -> None:
    wide = evaluate_trend_entry(
        TrendRunnerInput(
            side="YES",
            momentum=0.008,
            price_velocity=0.003,
            ev=0.04,
            confidence_score=0.70,
            spread=0.10,
        )
    )
    thin = evaluate_trend_entry(
        TrendRunnerInput(
            side="YES",
            momentum=0.008,
            price_velocity=0.003,
            ev=0.04,
            confidence_score=0.70,
            liquidity=50.0,
        )
    )

    assert wide.reason == "spread_too_wide"
    assert thin.reason == "liquidity_too_low"
