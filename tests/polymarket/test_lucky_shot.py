from __future__ import annotations

from polymarket.bankroll_tiers import BankrollTier
from polymarket.lucky_shot import LuckyShotInput, evaluate_lucky_shot


def test_lucky_shot_size_is_tiny() -> None:
    result = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=100.0,
            tier=BankrollTier.SMALL,
            ev=0.08,
            confidence_score=0.62,
            hard_stop_loss_pct=0.10,
        )
    )

    assert result.approved
    assert result.risk_pct == 0.005
    assert result.size_usd == 0.50


def test_lucky_shot_disabled_for_seed_test_by_default() -> None:
    result = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=20.0,
            tier=BankrollTier.SEED_TEST,
            ev=0.08,
            confidence_score=0.62,
            hard_stop_loss_pct=0.10,
        )
    )

    assert not result.approved
    assert result.reason == "lucky_shot_disabled_for_tier"


def test_lucky_shot_block_rules_work() -> None:
    bad_ev = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=100.0,
            tier=BankrollTier.MICRO,
            ev=0.0,
            confidence_score=0.62,
            hard_stop_loss_pct=0.10,
        )
    )
    low_confidence = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=100.0,
            tier=BankrollTier.MICRO,
            ev=0.08,
            confidence_score=0.50,
            hard_stop_loss_pct=0.10,
        )
    )

    assert bad_ev.reason == "ev_not_positive"
    assert low_confidence.reason == "confidence_too_low"


def test_lucky_shot_blocked_after_drawdown() -> None:
    result = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=100.0,
            tier=BankrollTier.MICRO,
            ev=0.08,
            confidence_score=0.62,
            hard_stop_loss_pct=0.10,
            daily_drawdown_pct=0.021,
        )
    )

    assert not result.approved
    assert result.reason == "daily_drawdown_gt_2pct"


def test_lucky_shot_blocked_after_consecutive_losses() -> None:
    result = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=100.0,
            tier=BankrollTier.MICRO,
            ev=0.08,
            confidence_score=0.62,
            hard_stop_loss_pct=0.10,
            consecutive_losses=2,
        )
    )

    assert not result.approved
    assert result.reason == "consecutive_losses_limit"


def test_no_martingale_behavior_after_one_loss() -> None:
    normal = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=100.0,
            tier=BankrollTier.MICRO,
            ev=0.08,
            confidence_score=0.62,
            hard_stop_loss_pct=0.10,
            consecutive_losses=0,
        )
    )
    after_loss = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=100.0,
            tier=BankrollTier.MICRO,
            ev=0.08,
            confidence_score=0.62,
            hard_stop_loss_pct=0.10,
            consecutive_losses=1,
        )
    )

    assert normal.approved
    assert after_loss.approved
    assert after_loss.size_usd < normal.size_usd


def test_no_averaging_down_or_adding_to_loser() -> None:
    result = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=100.0,
            tier=BankrollTier.MICRO,
            ev=0.08,
            confidence_score=0.62,
            hard_stop_loss_pct=0.10,
            add_requested=True,
            position_is_losing=True,
        )
    )

    assert not result.approved
    assert result.reason == "no_averaging_down"


def test_no_all_in_possible() -> None:
    result = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=1_000_000.0,
            tier=BankrollTier.BUILDER,
            ev=0.20,
            confidence_score=0.90,
            hard_stop_loss_pct=0.10,
        )
    )

    assert result.approved
    assert result.risk_pct <= 0.005
    assert result.size_usd < result.risk_pct * 1_000_000.0 + 0.01


def test_capital_tiers_disabled_by_default() -> None:
    result = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=25_000.0,
            tier=BankrollTier.CAPITAL_PLUS,
            ev=0.08,
            confidence_score=0.62,
            hard_stop_loss_pct=0.10,
        )
    )

    assert not result.approved
    assert result.reason == "lucky_shot_disabled_for_tier"


def test_lucky_shot_limits_and_hard_stop_required() -> None:
    hourly = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=100.0,
            tier=BankrollTier.MICRO,
            ev=0.08,
            confidence_score=0.62,
            hard_stop_loss_pct=0.10,
            lucky_shots_last_hour=1,
        )
    )
    daily = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=100.0,
            tier=BankrollTier.MICRO,
            ev=0.08,
            confidence_score=0.62,
            hard_stop_loss_pct=0.10,
            lucky_shots_today=2,
        )
    )
    no_stop = evaluate_lucky_shot(
        LuckyShotInput(
            bankroll=100.0,
            tier=BankrollTier.MICRO,
            ev=0.08,
            confidence_score=0.62,
            hard_stop_loss_pct=0.0,
        )
    )

    assert hourly.reason == "max_one_per_hour"
    assert daily.reason == "max_two_per_day"
    assert no_stop.reason == "hard_stop_loss_required"
