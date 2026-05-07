from __future__ import annotations

from dataclasses import dataclass

from polymarket.bankroll_tiers import BankrollTier


@dataclass(frozen=True, slots=True)
class LuckyShotInput:
    bankroll: float
    tier: BankrollTier | str
    ev: float
    confidence_score: float
    hard_stop_loss_pct: float
    lucky_shots_last_hour: int = 0
    lucky_shots_today: int = 0
    daily_drawdown_pct: float = 0.0
    consecutive_losses: int = 0
    add_requested: bool = False
    position_is_losing: bool = False
    allow_capital_tiers: bool = False


@dataclass(frozen=True, slots=True)
class LuckyShotResult:
    approved: bool
    size_usd: float
    risk_pct: float
    reason: str


def _tier(value: BankrollTier | str) -> BankrollTier:
    if isinstance(value, BankrollTier):
        return value
    return BankrollTier[str(value).upper()]


def _max_risk_pct(tier: BankrollTier, allow_capital_tiers: bool) -> float:
    if tier == BankrollTier.SEED_TEST:
        return 0.0
    if tier == BankrollTier.MICRO:
        return 0.0025
    if tier == BankrollTier.MICRO_PLUS:
        return 0.0035
    if tier in {BankrollTier.SMALL, BankrollTier.SMALL_PLUS}:
        return 0.0050
    if tier in {BankrollTier.BUILDER, BankrollTier.GROWTH, BankrollTier.GROWTH_PLUS, BankrollTier.SERIOUS}:
        return 0.0035
    if allow_capital_tiers:
        return 0.0025
    return 0.0


def evaluate_lucky_shot(lucky_input: LuckyShotInput) -> LuckyShotResult:
    tier = _tier(lucky_input.tier)
    max_pct = _max_risk_pct(tier, lucky_input.allow_capital_tiers)

    if max_pct <= 0:
        return LuckyShotResult(False, 0.0, 0.0, "lucky_shot_disabled_for_tier")
    if lucky_input.ev <= 0:
        return LuckyShotResult(False, 0.0, 0.0, "ev_not_positive")
    if lucky_input.confidence_score < 0.54:
        return LuckyShotResult(False, 0.0, 0.0, "confidence_too_low")
    if lucky_input.hard_stop_loss_pct <= 0:
        return LuckyShotResult(False, 0.0, 0.0, "hard_stop_loss_required")
    if lucky_input.lucky_shots_last_hour >= 1:
        return LuckyShotResult(False, 0.0, 0.0, "max_one_per_hour")
    if lucky_input.lucky_shots_today >= 2:
        return LuckyShotResult(False, 0.0, 0.0, "max_two_per_day")
    if lucky_input.daily_drawdown_pct > 0.02:
        return LuckyShotResult(False, 0.0, 0.0, "daily_drawdown_gt_2pct")
    if lucky_input.consecutive_losses >= 2:
        return LuckyShotResult(False, 0.0, 0.0, "consecutive_losses_limit")
    if lucky_input.add_requested or lucky_input.position_is_losing:
        return LuckyShotResult(False, 0.0, 0.0, "no_averaging_down")

    loss_penalty = 0.5 if lucky_input.consecutive_losses == 1 else 1.0
    risk_pct = max_pct * loss_penalty
    size_usd = round(max(lucky_input.bankroll, 0.0) * risk_pct, 6)

    return LuckyShotResult(True, size_usd, risk_pct, f"tiny_asymmetric_ev tier={tier.value} risk_pct={risk_pct:.4f}")

