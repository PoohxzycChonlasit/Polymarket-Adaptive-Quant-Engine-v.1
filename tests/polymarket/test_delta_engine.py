from __future__ import annotations

import pytest

from polymarket.delta_engine import DeltaRegime, MicroDeltaInput, estimate_micro_delta
from polymarket.position_sizing import PositionSizingInput, calculate_position_size


def _delta_input(**overrides: object) -> MicroDeltaInput:
    values = {
        "underlying_price": 101.00,
        "target_price": 100.00,
        "distance_to_target": 1.00,
        "time_remaining_seconds": 300,
        "recent_volatility": 0.005,
        "recent_price_velocity": 0.001,
        "spread": 0.01,
        "liquidity": 1_000.0,
    }
    values.update(overrides)
    return MicroDeltaInput(**values)


def _sizing(delta: float, *, time_remaining_seconds: int = 300):
    return calculate_position_size(
        PositionSizingInput(
            bankroll=1_000.0,
            confidence=0.75,
            ev=0.08,
            entry_price=0.50,
            spread=0.01,
            liquidity_usd=1_000.0,
            delta=delta,
            time_remaining_seconds=time_remaining_seconds,
            min_position_size_usd=0.001,
        )
    )


def _sizing_with_multiplier(delta_multiplier: float, *, time_remaining_seconds: int = 300):
    return calculate_position_size(
        PositionSizingInput(
            bankroll=1_000.0,
            confidence=0.75,
            ev=0.08,
            entry_price=0.50,
            spread=0.01,
            liquidity_usd=1_000.0,
            delta_multiplier=delta_multiplier,
            time_remaining_seconds=time_remaining_seconds,
            min_position_size_usd=0.001,
        )
    )


def test_requested_delta_input_aliases_are_supported() -> None:
    result = estimate_micro_delta(
        MicroDeltaInput(
            current_price=100.05,
            strike_price=100.00,
            time_remaining_seconds=240,
            volatility=0.010,
            price_velocity=0.001,
            spread=0.01,
            liquidity=1_000.0,
        )
    )

    assert result.delta_score > 0
    assert result.delta_regime in set(DeltaRegime)
    assert 0.0 <= result.delta_multiplier <= 1.0


def test_delta_increases_near_strike() -> None:
    far = estimate_micro_delta(_delta_input(underlying_price=101.00, distance_to_target=1.00))
    near = estimate_micro_delta(_delta_input(underlying_price=100.05, distance_to_target=0.05))

    assert near.delta_score > far.delta_score


def test_delta_increases_near_expiry() -> None:
    early = estimate_micro_delta(_delta_input(time_remaining_seconds=300))
    late = estimate_micro_delta(_delta_input(time_remaining_seconds=120))

    assert late.delta_score > early.delta_score


def test_volatility_increases_delta() -> None:
    calm = estimate_micro_delta(_delta_input(recent_volatility=0.004))
    volatile = estimate_micro_delta(_delta_input(recent_volatility=0.040))

    assert volatile.delta_score > calm.delta_score


def test_high_velocity_increases_delta() -> None:
    slow = estimate_micro_delta(_delta_input(recent_price_velocity=0.001))
    fast = estimate_micro_delta(_delta_input(recent_price_velocity=0.010))

    assert fast.delta_score > slow.delta_score


def test_wide_spread_increases_delta_risk() -> None:
    tight = estimate_micro_delta(_delta_input(spread=0.01))
    wide = estimate_micro_delta(_delta_input(spread=0.10))

    assert wide.delta_score > tight.delta_score


def test_low_liquidity_increases_delta_risk() -> None:
    deep = estimate_micro_delta(_delta_input(liquidity=1_000.0))
    thin = estimate_micro_delta(_delta_input(liquidity=50.0))

    assert thin.delta_score > deep.delta_score


def test_high_delta_reduces_position_size() -> None:
    low = _sizing(delta=0.80)
    high = _sizing(delta=3.00)

    assert low.approved
    assert high.approved
    assert high.delta_multiplier == pytest.approx(0.5)
    assert high.final_size_usd < low.final_size_usd


def test_extreme_delta_blocks_or_tiny_size() -> None:
    result = estimate_micro_delta(
        _delta_input(
            underlying_price=100.02,
            distance_to_target=0.02,
            time_remaining_seconds=100,
            recent_volatility=0.04,
            recent_price_velocity=0.006,
        )
    )
    sizing = _sizing(delta=result.delta_score)

    assert result.delta_regime == DeltaRegime.EXTREME
    assert result.delta_multiplier <= 0.25
    assert sizing.delta_multiplier <= 0.25
    assert sizing.final_size_usd < _sizing(delta=0.80).final_size_usd


def test_extreme_delta_multiplier_blocks_or_tiny_size() -> None:
    normal = _sizing_with_multiplier(1.0)
    extreme_blocked = _sizing_with_multiplier(0.0)
    extreme_tiny = _sizing_with_multiplier(0.2)

    assert normal.approved
    assert not extreme_blocked.approved
    assert extreme_tiny.approved
    assert extreme_tiny.final_size_usd <= normal.final_size_usd * 0.25


def test_high_delta_never_increases_position_size() -> None:
    low = _sizing(delta=0.5)
    high = _sizing(delta=4.0)
    extreme = _sizing(delta=8.0)

    assert low.approved
    assert high.final_size_usd <= low.final_size_usd
    assert extreme.final_size_usd <= low.final_size_usd


def test_time_remaining_at_or_below_ninety_seconds_blocks_new_entry() -> None:
    delta = estimate_micro_delta(_delta_input(time_remaining_seconds=90))
    sizing = _sizing(delta=delta.delta_score, time_remaining_seconds=90)

    assert delta.delta_regime == DeltaRegime.EXTREME
    assert delta.delta_multiplier == 0.0
    assert delta.new_entry_blocked
    assert not sizing.approved
    assert "time_remaining_le_90s" in sizing.blocked_reasons
