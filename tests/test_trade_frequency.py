from __future__ import annotations

import pytest

from polymarket.bankroll_tiers import BankrollTier
from polymarket.position_sizing import PositionSizingInput, calculate_position_size
from polymarket.trade_frequency import (
    COOLDOWN_AFTER_LOSS_SECONDS,
    COOLDOWN_AFTER_WIN_SECONDS,
    MIN_SECONDS_BETWEEN_ENTRIES,
    TradeFrequencyConfig,
    TradeFrequencyInput,
    TradeFrequencyState,
    calculate_frequency_multiplier,
    can_trade_now,
    evaluate_trade_frequency,
)


def _sizing(*, trades_last_hour: int):
    return calculate_position_size(
        PositionSizingInput(
            bankroll=100.0,
            confidence=0.75,
            ev=0.08,
            entry_price=0.50,
            spread=0.01,
            liquidity_usd=1_000.0,
            delta=0.80,
            time_remaining_seconds=300,
            trades_last_hour=trades_last_hour,
            min_position_size_usd=0.001,
        )
    )


def test_high_frequency_reduces_position_size() -> None:
    low_frequency = _sizing(trades_last_hour=0)
    high_frequency = _sizing(trades_last_hour=7)

    assert low_frequency.approved
    assert high_frequency.approved
    assert high_frequency.frequency_multiplier < low_frequency.frequency_multiplier
    assert high_frequency.final_size_usd < low_frequency.final_size_usd


def test_calculate_frequency_multiplier_uses_frequency_buckets() -> None:
    config = TradeFrequencyConfig(tier=BankrollTier.SMALL, max_trades_per_hour=8)

    low = calculate_frequency_multiplier(TradeFrequencyState(trades_last_hour=0), config)
    normal = calculate_frequency_multiplier(TradeFrequencyState(trades_last_hour=2), config)
    high = calculate_frequency_multiplier(TradeFrequencyState(trades_last_hour=4), config)
    very_high = calculate_frequency_multiplier(TradeFrequencyState(trades_last_hour=6), config)

    assert low == 1.0
    assert normal == 0.75
    assert high == 0.50
    assert very_high == 0.25


def test_max_trades_per_hour_blocks_by_tier() -> None:
    result = evaluate_trade_frequency(
        TradeFrequencyInput(tier=BankrollTier.SEED_TEST, trades_last_hour=4)
    )

    assert not result.approved
    assert result.min_trades_per_hour == 2
    assert result.max_trades_per_hour == 4
    assert "max_trades_per_hour_reached" in result.blocked_reasons


def test_can_trade_now_max_trades_per_hour_works() -> None:
    result = can_trade_now(
        TradeFrequencyState(trades_last_hour=4),
        TradeFrequencyConfig(tier=BankrollTier.SEED_TEST),
    )

    assert not result.approved
    assert "max_trades_per_hour_reached" in result.blocked_reasons


def test_cooldown_after_loss_blocks() -> None:
    result = evaluate_trade_frequency(
        TradeFrequencyInput(
            tier=BankrollTier.MICRO,
            seconds_since_last_entry=COOLDOWN_AFTER_LOSS_SECONDS - 1,
            last_trade_result="loss",
        )
    )

    assert not result.approved
    assert "cooldown_after_loss" in result.blocked_reasons


def test_can_trade_now_cooldown_after_loss_works() -> None:
    result = can_trade_now(
        TradeFrequencyState(
            seconds_since_last_entry=COOLDOWN_AFTER_LOSS_SECONDS - 1,
            last_trade_result="loss",
        ),
        TradeFrequencyConfig(tier=BankrollTier.MICRO),
    )

    assert not result.approved
    assert "cooldown_after_loss" in result.blocked_reasons


def test_cooldown_after_win_blocks() -> None:
    result = evaluate_trade_frequency(
        TradeFrequencyInput(
            tier=BankrollTier.MICRO,
            seconds_since_last_entry=COOLDOWN_AFTER_WIN_SECONDS - 1,
            last_trade_result="win",
        )
    )

    assert not result.approved
    assert "cooldown_after_win" in result.blocked_reasons


def test_can_trade_now_cooldown_after_win_works() -> None:
    result = can_trade_now(
        TradeFrequencyState(
            seconds_since_last_entry=COOLDOWN_AFTER_WIN_SECONDS - 1,
            last_trade_result="win",
        ),
        TradeFrequencyConfig(tier=BankrollTier.MICRO),
    )

    assert not result.approved
    assert "cooldown_after_win" in result.blocked_reasons


def test_min_seconds_between_entries_works() -> None:
    result = can_trade_now(
        TradeFrequencyState(seconds_since_last_entry=MIN_SECONDS_BETWEEN_ENTRIES - 1),
        TradeFrequencyConfig(tier=BankrollTier.MICRO),
    )

    assert not result.approved
    assert "min_seconds_between_entries" in result.blocked_reasons


def test_max_trades_per_market_blocks() -> None:
    result = evaluate_trade_frequency(
        TradeFrequencyInput(tier=BankrollTier.MICRO, trades_for_market=1, max_trades_per_market=1)
    )

    assert not result.approved
    assert "max_trades_per_market_reached" in result.blocked_reasons


def test_risk_off_and_reconciliation_unsafe_block() -> None:
    result = evaluate_trade_frequency(
        TradeFrequencyInput(tier=BankrollTier.MICRO, risk_off=True, reconciliation_safe=False)
    )

    assert not result.approved
    assert "risk_off" in result.blocked_reasons
    assert "reconciliation_unsafe" in result.blocked_reasons


def test_growth_plus_thin_liquidity_reduces_frequency_multiplier() -> None:
    liquid = evaluate_trade_frequency(TradeFrequencyInput(tier=BankrollTier.GROWTH, liquidity=1_000.0))
    thin = evaluate_trade_frequency(TradeFrequencyInput(tier=BankrollTier.GROWTH, liquidity=100.0))

    assert thin.frequency_multiplier < liquid.frequency_multiplier
    assert thin.frequency_multiplier == pytest.approx(0.5)
