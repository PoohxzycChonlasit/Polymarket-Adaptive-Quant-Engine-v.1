from __future__ import annotations

import pytest

from polymarket.expected_value import (
    ExpectedValueInput,
    ExpectedValueTier,
    calculate_binary_ev,
    calculate_ev,
    choose_best_ev_trade,
    dynamic_min_ev,
    evaluate_entry,
)


def _ev_input(**overrides: object) -> ExpectedValueInput:
    values = {
        "p_yes": 0.60,
        "p_no": 0.40,
        "yes_ask": 0.55,
        "no_ask": 0.39,
        "confidence_score": 0.70,
        "spread": 0.02,
        "liquidity": 1_500.0,
        "delta": 0.10,
        "tier": ExpectedValueTier(name="test", min_ev=0.02),
    }
    values.update(overrides)
    return ExpectedValueInput(**values)


def test_binary_ev_is_probability_minus_ask_price() -> None:
    assert calculate_binary_ev(0.61, 0.54) == pytest.approx(0.07)
    assert calculate_ev(0.61, 0.54) == pytest.approx(0.07)


def test_dynamic_min_ev_is_lower_for_low_delta_and_good_liquidity() -> None:
    tier = ExpectedValueTier(name="test", min_ev=0.02)

    good = dynamic_min_ev(
        tier=tier,
        delta=0.10,
        spread=0.01,
        liquidity=2_000.0,
        confidence_score=0.72,
    )
    risky = dynamic_min_ev(
        tier=tier,
        delta=2.00,
        spread=0.08,
        liquidity=75.0,
        confidence_score=0.58,
    )

    assert good < tier.min_ev
    assert risky > tier.min_ev


def test_skip_when_ev_is_below_threshold() -> None:
    result = evaluate_entry(_ev_input(p_yes=0.53, p_no=0.47, yes_ask=0.52, no_ask=0.46))

    assert not result.approved
    assert result.side == "SKIP"
    assert result.skip_reason == "ev_below_threshold"


def test_choose_best_ev_trade_skips_when_ev_below_threshold() -> None:
    result = choose_best_ev_trade(
        p_yes=0.53,
        p_no=0.47,
        yes_ask=0.52,
        no_ask=0.46,
        confidence=0.70,
        min_ev=0.02,
        min_confidence=0.54,
    )

    assert not result.approved
    assert result.side == "SKIP"


def test_skip_when_confidence_is_too_low() -> None:
    result = evaluate_entry(
        _ev_input(
            p_yes=0.70,
            p_no=0.30,
            yes_ask=0.55,
            no_ask=0.25,
            confidence_score=0.50,
        )
    )

    assert not result.approved
    assert result.side == "SKIP"
    assert result.skip_reason == "confidence_too_low"


def test_choose_best_ev_trade_skips_when_confidence_too_low() -> None:
    result = choose_best_ev_trade(
        p_yes=0.70,
        p_no=0.30,
        yes_ask=0.55,
        no_ask=0.25,
        confidence=0.50,
        min_ev=0.02,
        min_confidence=0.54,
    )

    assert not result.approved
    assert result.skip_reason == "confidence_too_low"


def test_choose_yes_when_yes_ev_is_better() -> None:
    result = evaluate_entry(_ev_input(p_yes=0.62, p_no=0.38, yes_ask=0.56, no_ask=0.36))

    assert result.approved
    assert result.side == "YES"
    assert result.ev_yes > result.ev_no


def test_choose_no_when_no_ev_is_better() -> None:
    result = evaluate_entry(_ev_input(p_yes=0.42, p_no=0.58, yes_ask=0.40, no_ask=0.52))

    assert result.approved
    assert result.side == "NO"
    assert result.ev_no > result.ev_yes


def test_choose_best_ev_trade_uses_strictly_better_side() -> None:
    result = choose_best_ev_trade(
        p_yes=0.62,
        p_no=0.38,
        yes_ask=0.56,
        no_ask=0.36,
        confidence=0.70,
        min_ev=0.02,
        min_confidence=0.54,
    )

    assert result.approved
    assert result.side == "YES"


def test_invalid_ask_price_skips() -> None:
    result = evaluate_entry(_ev_input(yes_ask=1.0, no_ask=0.40))

    assert not result.approved
    assert result.side == "SKIP"
    assert result.skip_reason == "invalid_ask_price"
