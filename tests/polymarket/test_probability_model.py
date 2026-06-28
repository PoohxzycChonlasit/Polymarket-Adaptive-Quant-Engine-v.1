from __future__ import annotations

import pytest

from polymarket.probability_model import ProbabilityModelInput, estimate_probability


def _model_input(**overrides: object) -> ProbabilityModelInput:
    values = {
        "underlying_price": 100.50,
        "target_price": 100.00,
        "distance_to_target": 0.50,
        "time_remaining_seconds": 240,
        "recent_price_velocity": 0.001,
        "short_term_momentum": 0.002,
        "volatility": 0.010,
        "orderbook_bid": 0.52,
        "orderbook_ask": 0.54,
        "spread": 0.02,
        "liquidity": 1_500.0,
        "polymarket_implied_probability": 0.53,
        "data_age_seconds": 1.0,
    }
    values.update(overrides)
    return ProbabilityModelInput(**values)


def test_probabilities_sum_to_one() -> None:
    result = estimate_probability(_model_input())

    assert result.p_yes + result.p_no == pytest.approx(1.0)
    assert 0.0 <= result.p_yes <= 1.0
    assert 0.0 <= result.p_no <= 1.0
    assert result.confidence_score > 0.0


def test_requested_input_aliases_are_supported() -> None:
    result = estimate_probability(
        ProbabilityModelInput(
            underlying_price=100.50,
            strike_price=100.00,
            time_remaining_seconds=240,
            price_velocity=0.001,
            momentum=0.002,
            volatility=0.010,
            yes_ask=0.54,
            no_ask=0.48,
            spread=0.02,
            liquidity=1_500.0,
            market_implied_probability=0.53,
            data_age_seconds=1.0,
        )
    )

    assert result.p_yes + result.p_no == pytest.approx(1.0)
    assert not result.skipped


def test_probabilities_are_clamped() -> None:
    result = estimate_probability(
        _model_input(
            underlying_price=10_000.0,
            target_price=1.0,
            distance_to_target=9_999.0,
            recent_price_velocity=5.0,
            short_term_momentum=5.0,
            polymarket_implied_probability=5.0,
        )
    )

    assert 0.0 <= result.p_yes <= 1.0
    assert 0.0 <= result.p_no <= 1.0
    assert result.p_yes + result.p_no == pytest.approx(1.0)


def test_model_leans_yes_when_price_and_momentum_are_above_target() -> None:
    result = estimate_probability(_model_input())

    assert result.p_yes > result.p_no
    assert "leans_yes" in result.model_reason


def test_stale_data_skips_probability_signal() -> None:
    result = estimate_probability(_model_input(data_age_seconds=30.0, max_data_age_seconds=10.0))

    assert result.skipped
    assert result.skip_reason == "data_stale"
    assert result.confidence_score == 0.0
    assert result.p_yes + result.p_no == pytest.approx(1.0)


def test_low_liquidity_reduces_confidence() -> None:
    good = estimate_probability(_model_input(liquidity=1_500.0))
    weak = estimate_probability(_model_input(liquidity=25.0))

    assert weak.confidence_score < good.confidence_score
    assert "weak_liquidity" in weak.model_reason


def test_wide_spread_reduces_confidence() -> None:
    good = estimate_probability(_model_input(spread=0.01, orderbook_bid=0.52, orderbook_ask=0.53))
    wide = estimate_probability(_model_input(spread=0.11, orderbook_bid=0.45, orderbook_ask=0.56))

    assert wide.confidence_score < good.confidence_score
    assert "wide_spread" in wide.model_reason


def test_wide_spread_unstable_volatility_and_weak_liquidity_reduce_confidence() -> None:
    good = estimate_probability(_model_input())
    weak = estimate_probability(
        _model_input(
            spread=0.11,
            volatility=0.08,
            liquidity=25.0,
            orderbook_bid=0.47,
            orderbook_ask=0.58,
        )
    )

    assert weak.confidence_score < good.confidence_score
    assert "wide_spread" in weak.model_reason
    assert "unstable_volatility" in weak.model_reason
    assert "weak_liquidity" in weak.model_reason
