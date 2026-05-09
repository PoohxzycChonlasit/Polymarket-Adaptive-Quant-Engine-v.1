from __future__ import annotations

import pytest

from polymarket.bankroll_tiers import (
    BankrollRankLock,
    BankrollTier,
    calculate_base_risk_pct,
    get_bankroll_tier,
    get_bankroll_tier_with_hysteresis,
    get_tier_config,
    iter_tier_configs,
)
from polymarket.order_manager import OrderRequest, PolymarketOrderManager
from polymarket.position_sizing import PositionSizingInput, calculate_position_size


@pytest.mark.parametrize(
    ("bankroll", "tier"),
    [
        (0.0, BankrollTier.T0_MICRO_SEED),
        (24.99, BankrollTier.T0_MICRO_SEED),
        (25.0, BankrollTier.T1_MICRO_BUILD),
        (50.0, BankrollTier.T2_MICRO_SURVIVAL),
        (100.0, BankrollTier.T3_BASE_BUILD),
        (250.0, BankrollTier.T4_BASE_STABLE),
        (500.0, BankrollTier.T5_SMALL_GROWTH),
        (1_000.0, BankrollTier.T6_GROWTH_1),
        (2_500.0, BankrollTier.T7_GROWTH_2),
        (5_000.0, BankrollTier.T8_GROWTH_3),
        (10_000.0, BankrollTier.T9_CAPITAL_1),
        (25_000.0, BankrollTier.T10_CAPITAL_2),
        (50_000.0, BankrollTier.T11_CAPITAL_3),
        (100_000.0, BankrollTier.T12_CAPITAL_PRESERVE),
    ],
)
def test_get_bankroll_tier_boundaries(bankroll: float, tier: BankrollTier) -> None:
    assert get_bankroll_tier(bankroll) == tier


def test_get_bankroll_tier_remains_raw_lookup_at_threshold() -> None:
    assert get_bankroll_tier(99.0) == BankrollTier.T2_MICRO_SURVIVAL
    assert get_bankroll_tier(100.0) == BankrollTier.T3_BASE_BUILD
    assert get_bankroll_tier(99.0) == BankrollTier.T2_MICRO_SURVIVAL


def test_tier_metadata_table_is_complete_and_centralized() -> None:
    configs = iter_tier_configs()

    assert [config.tier_id for config in configs] == [
        "T0_MICRO_SEED",
        "T1_MICRO_BUILD",
        "T2_MICRO_SURVIVAL",
        "T3_BASE_BUILD",
        "T4_BASE_STABLE",
        "T5_SMALL_GROWTH",
        "T6_GROWTH_1",
        "T7_GROWTH_2",
        "T8_GROWTH_3",
        "T9_CAPITAL_1",
        "T10_CAPITAL_2",
        "T11_CAPITAL_3",
        "T12_CAPITAL_PRESERVE",
    ]
    assert [config.family for config in configs[:3]] == ["MICRO", "MICRO", "MICRO"]
    assert [config.family for config in configs[3:5]] == ["BASE", "BASE"]
    assert [config.family for config in configs[5:9]] == ["GROWTH", "GROWTH", "GROWTH", "GROWTH"]
    assert [config.family for config in configs[9:]] == ["CAPITAL", "CAPITAL", "CAPITAL", "CAPITAL"]

    for config in configs:
        metadata = config.to_metadata()
        assert metadata["tier_id"] == config.tier.value
        assert metadata["tier_name"]
        assert metadata["risk_profile"]
        assert metadata["description"]
        assert config.lower_bound < config.upper_bound
        assert 0.0 < config.recommended_max_risk_fraction <= 0.10
        assert config.min_position_size_hint <= config.max_position_size_hint


def test_bankroll_rank_lock_holds_active_tier_inside_downgrade_buffer() -> None:
    lock = BankrollRankLock(initial_tier=BankrollTier.T3_BASE_BUILD, buffer_pct=0.05)

    result = lock.update(99.0)
    assert result.active_tier == BankrollTier.T3_BASE_BUILD
    assert result.raw_tier == BankrollTier.T2_MICRO_SURVIVAL
    assert result.reason == "inside_hysteresis"
    assert result.tier_locked
    assert result.hysteresis_active

    assert lock.update(100.0).active_tier == BankrollTier.T3_BASE_BUILD
    assert lock.update(101.0).active_tier == BankrollTier.T3_BASE_BUILD
    assert lock.update(99.0).active_tier == BankrollTier.T3_BASE_BUILD


def test_bankroll_rank_lock_downgrades_after_buffer_breaks() -> None:
    lock = BankrollRankLock(initial_tier=BankrollTier.T3_BASE_BUILD, buffer_pct=0.05)

    result = lock.update(94.99)

    assert result.active_tier == BankrollTier.T2_MICRO_SURVIVAL
    assert result.raw_tier == BankrollTier.T2_MICRO_SURVIVAL
    assert result.reason == "downgraded"
    assert result.changed


def test_bankroll_rank_lock_upgrades_at_boundary_without_aggression_buffer() -> None:
    lock = BankrollRankLock(initial_tier=BankrollTier.T2_MICRO_SURVIVAL, buffer_pct=0.05)

    assert lock.update(99.99).active_tier == BankrollTier.T2_MICRO_SURVIVAL

    result = lock.update(100.0)

    assert result.active_tier == BankrollTier.T3_BASE_BUILD
    assert result.raw_tier == BankrollTier.T3_BASE_BUILD
    assert result.reason == "upgraded"
    assert result.changed


def test_hysteresis_helper_uses_previous_tier_for_downgrades_only() -> None:
    assert (
        get_bankroll_tier_with_hysteresis(99.0, BankrollTier.T3_BASE_BUILD, buffer_pct=0.05)
        == BankrollTier.T3_BASE_BUILD
    )
    assert (
        get_bankroll_tier_with_hysteresis(94.99, BankrollTier.T3_BASE_BUILD, buffer_pct=0.05)
        == BankrollTier.T2_MICRO_SURVIVAL
    )
    assert (
        get_bankroll_tier_with_hysteresis(100.0, BankrollTier.T2_MICRO_SURVIVAL, buffer_pct=0.05)
        == BankrollTier.T3_BASE_BUILD
    )


def test_base_risk_interpolates_inside_tier() -> None:
    assert calculate_base_risk_pct(100.0) == pytest.approx(0.04)
    assert calculate_base_risk_pct(175.0) == pytest.approx(0.035)
    assert calculate_base_risk_pct(249.99) == pytest.approx(0.03, abs=0.00001)


def test_base_risk_stays_inside_configured_tier_range() -> None:
    for bankroll in [10, 40, 75, 200, 400, 750, 2_000, 4_000, 7_500, 20_000, 40_000, 80_000, 250_000]:
        config = get_tier_config(bankroll)
        risk = calculate_base_risk_pct(bankroll)
        assert config.min_risk_pct <= risk <= config.max_risk_pct


def test_position_sizing_uses_all_multipliers() -> None:
    sizing_input = PositionSizingInput(
        bankroll=1_000.0,
        confidence=0.75,
        ev=0.08,
        entry_price=0.50,
        drawdown_pct=0.0,
        spread=0.0,
        liquidity_usd=1_000.0,
        delta=1.0,
        time_remaining_seconds=300,
        trades_last_hour=0,
        min_position_size_usd=1.0,
    )

    result = calculate_position_size(sizing_input)

    assert result.approved
    assert result.tier == BankrollTier.T6_GROWTH_1
    assert result.tier_base_risk_pct == pytest.approx(0.025)
    assert result.final_size_usd == pytest.approx(25.0)
    assert result.shares == pytest.approx(50.0)


def test_position_size_reduces_when_market_quality_is_bad() -> None:
    good = calculate_position_size(
        PositionSizingInput(
            bankroll=1_000.0,
            confidence=0.75,
            ev=0.08,
            spread=0.01,
            liquidity_usd=2_000.0,
            delta=1.0,
            time_remaining_seconds=300,
            min_position_size_usd=1.0,
        )
    )
    weak = calculate_position_size(
        PositionSizingInput(
            bankroll=1_000.0,
            confidence=0.56,
            ev=0.01,
            spread=0.08,
            liquidity_usd=50.0,
            delta=0.1,
            drawdown_pct=0.04,
            time_remaining_seconds=120,
            trades_last_hour=5,
            min_position_size_usd=0.001,
        )
    )

    assert good.approved
    assert weak.approved
    assert weak.final_size_usd < good.final_size_usd


def test_delta_multiplier_directly_reduces_position_size() -> None:
    base = {
        "bankroll": 1_000.0,
        "confidence": 0.75,
        "ev": 0.08,
        "spread": 0.0,
        "liquidity_usd": 1_000.0,
        "time_remaining_seconds": 300,
        "min_position_size_usd": 0.001,
    }

    normal = calculate_position_size(PositionSizingInput(**base, delta_multiplier=1.0))
    high_delta_risk = calculate_position_size(PositionSizingInput(**base, delta_multiplier=0.25))

    assert normal.approved
    assert high_delta_risk.approved
    assert high_delta_risk.final_size_usd == pytest.approx(normal.final_size_usd * 0.25)


def test_high_delta_score_reduces_position_size() -> None:
    base = {
        "bankroll": 1_000.0,
        "confidence": 0.75,
        "ev": 0.08,
        "spread": 0.0,
        "liquidity_usd": 1_000.0,
        "time_remaining_seconds": 300,
        "min_position_size_usd": 0.001,
    }

    low_delta = calculate_position_size(PositionSizingInput(**base, delta=1.0))
    high_delta = calculate_position_size(PositionSizingInput(**base, delta=100.0))

    assert low_delta.approved
    assert high_delta.final_size_usd <= low_delta.final_size_usd


def test_tiny_bankroll_not_blocked_by_one_dollar_minimum_floor() -> None:
    manager = PolymarketOrderManager(
        account_balance=20.0,
        max_risk_per_trade=0.01,
        stop_loss_pct=0.08,
        kelly_fraction_cap=0.25,
    )

    plan = manager.build_order_plan(
        OrderRequest(
            market_id="pm-5m-btc",
            side="YES",
            entry_price=0.50,
            win_rate=0.75,
            reward_risk_ratio=2.0,
            edge=0.08,
            spread=0.0,
            liquidity_usd=1_000.0,
            delta_multiplier=1.0,
            time_remaining_seconds=300,
            min_position_size_usd=1.0,
        )
    )

    assert 0.0 < plan.notional_size < 1.0


def test_order_manager_blocks_non_positive_ev() -> None:
    manager = PolymarketOrderManager(
        account_balance=1_000.0,
        max_risk_per_trade=0.01,
        stop_loss_pct=0.08,
        kelly_fraction_cap=0.25,
    )

    plan = manager.build_order_plan(
        OrderRequest(
            market_id="pm-5m-btc",
            side="YES",
            entry_price=0.50,
            win_rate=0.50,
            reward_risk_ratio=2.0,
            edge=-0.01,
            spread=0.0,
            liquidity_usd=1_000.0,
            delta_multiplier=1.0,
            time_remaining_seconds=300,
            min_position_size_usd=0.001,
        )
    )

    assert plan.notional_size == 0.0


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"daily_loss_limit_reached": True}, "daily_loss_limit_reached"),
        ({"hard_drawdown_reached": True}, "hard_drawdown_reached"),
        ({"time_remaining_seconds": 90}, "time_remaining_le_90s"),
        ({"confidence": 0.50}, "confidence_too_low"),
        ({"ev": 0.0}, "ev_not_positive"),
        ({"spread": 0.11}, "spread_too_wide"),
        ({"liquidity_usd": 5.0}, "liquidity_too_low"),
    ],
)
def test_blocking_guards(overrides: dict[str, object], reason: str) -> None:
    values = {
        "bankroll": 1_000.0,
        "confidence": 0.70,
        "ev": 0.04,
        "spread": 0.01,
        "liquidity_usd": 1_000.0,
        "delta": 1.0,
        "time_remaining_seconds": 180,
        "min_position_size_usd": 1.0,
    }
    values.update(overrides)

    result = calculate_position_size(PositionSizingInput(**values))

    assert not result.approved
    assert reason in result.blocked_reasons


def test_blocks_below_min_position_size() -> None:
    result = calculate_position_size(
        PositionSizingInput(
            bankroll=1_000.0,
            confidence=0.55,
            ev=0.001,
            spread=0.10,
            liquidity_usd=10.0,
            delta_multiplier=1.0,
            time_remaining_seconds=91,
            min_position_size_usd=5.0,
        )
    )

    assert not result.approved
    assert result.final_size_usd > 0
    assert "below_min_position_size" in result.blocked_reasons
