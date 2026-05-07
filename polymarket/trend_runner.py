from __future__ import annotations

from dataclasses import dataclass

from polymarket.bankroll_tiers import BankrollTier
from polymarket.delta_engine import DeltaRegime


@dataclass(frozen=True, slots=True)
class TrendRunnerInput:
    side: str
    momentum: float
    price_velocity: float
    ev: float
    confidence_score: float
    tier: BankrollTier | str = BankrollTier.MICRO
    spread: float = 0.02
    liquidity: float = 1_000.0
    delta_regime: DeltaRegime | str = DeltaRegime.NORMAL
    min_momentum: float = 0.003
    min_velocity: float = 0.001
    max_spread: float = 0.08
    min_liquidity: float = 100.0


@dataclass(frozen=True, slots=True)
class TrendRunnerResult:
    approved: bool
    side: str
    trend_size_multiplier: float
    reason: str


def _tier(value: BankrollTier | str) -> BankrollTier:
    if isinstance(value, BankrollTier):
        return value
    return BankrollTier[str(value).upper()]


def _regime(value: DeltaRegime | str) -> DeltaRegime:
    if isinstance(value, DeltaRegime):
        return value
    return DeltaRegime[str(value).upper()]


def _confidence_floor(tier: BankrollTier) -> float:
    if tier in {BankrollTier.SEED_TEST, BankrollTier.MICRO, BankrollTier.MICRO_PLUS}:
        return 0.56
    if tier in {BankrollTier.SMALL, BankrollTier.SMALL_PLUS, BankrollTier.BUILDER}:
        return 0.58
    return 0.60


def evaluate_trend_entry(trend_input: TrendRunnerInput) -> TrendRunnerResult:
    side = trend_input.side.upper()
    tier = _tier(trend_input.tier)
    regime = _regime(trend_input.delta_regime)

    if side not in {"YES", "NO"}:
        return TrendRunnerResult(False, "SKIP", 0.0, "invalid_side")
    if trend_input.ev <= 0:
        return TrendRunnerResult(False, "SKIP", 0.0, "ev_not_positive")
    if trend_input.confidence_score < _confidence_floor(tier):
        return TrendRunnerResult(False, "SKIP", 0.0, "confidence_too_low")
    if trend_input.spread > trend_input.max_spread:
        return TrendRunnerResult(False, "SKIP", 0.0, "spread_too_wide")
    if trend_input.liquidity < trend_input.min_liquidity:
        return TrendRunnerResult(False, "SKIP", 0.0, "liquidity_too_low")
    if regime == DeltaRegime.EXTREME:
        return TrendRunnerResult(False, "SKIP", 0.0, "delta_extreme")

    direction = 1.0 if side == "YES" else -1.0
    if trend_input.momentum * direction < trend_input.min_momentum:
        return TrendRunnerResult(False, "SKIP", 0.0, "momentum_not_confirmed")
    if trend_input.price_velocity * direction < trend_input.min_velocity:
        return TrendRunnerResult(False, "SKIP", 0.0, "velocity_not_confirmed")

    multiplier = 0.50
    if trend_input.confidence_score >= 0.70 and trend_input.ev >= 0.06 and regime in {DeltaRegime.LOW, DeltaRegime.NORMAL}:
        multiplier = 0.75
    elif trend_input.confidence_score >= 0.62 and trend_input.ev >= 0.03:
        multiplier = 0.60

    return TrendRunnerResult(True, side, multiplier, "trend_confirmed")


def evaluate_trend_runner(trend_input: TrendRunnerInput) -> TrendRunnerResult:
    return evaluate_trend_entry(trend_input)
