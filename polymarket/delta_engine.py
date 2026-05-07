from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import sqrt


class DeltaRegime(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


@dataclass(frozen=True, slots=True)
class MicroDeltaInput:
    underlying_price: float | None = None
    target_price: float | None = None
    distance_to_target: float | None = None
    time_remaining_seconds: int = 300
    recent_volatility: float | None = None
    recent_price_velocity: float | None = None
    spread: float = 0.0
    liquidity: float = 1_000.0
    current_price: float | None = None
    strike_price: float | None = None
    volatility: float | None = None
    price_velocity: float | None = None


@dataclass(frozen=True, slots=True)
class MicroDeltaResult:
    delta_score: float
    delta_regime: DeltaRegime
    delta_multiplier: float
    reason: str
    new_entry_blocked: bool = False


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _as_decimal_move(value: float) -> float:
    value = float(value)
    if abs(value) > 1.0:
        return value / 100.0
    return value


def _current_price(delta_input: MicroDeltaInput) -> float:
    return float(delta_input.underlying_price if delta_input.underlying_price is not None else delta_input.current_price or 0.0)


def _strike_price(delta_input: MicroDeltaInput) -> float:
    return float(delta_input.target_price if delta_input.target_price is not None else delta_input.strike_price or 0.0)


def _volatility(delta_input: MicroDeltaInput) -> float:
    return float(delta_input.recent_volatility if delta_input.recent_volatility is not None else delta_input.volatility or 0.0)


def _price_velocity(delta_input: MicroDeltaInput) -> float:
    return float(delta_input.recent_price_velocity if delta_input.recent_price_velocity is not None else delta_input.price_velocity or 0.0)


def _distance_pct(delta_input: MicroDeltaInput) -> float:
    strike_price = _strike_price(delta_input)
    if strike_price <= 0:
        return 1.0

    price_distance = abs(_current_price(delta_input) - strike_price)
    if price_distance > 0:
        return price_distance / strike_price

    distance = abs(float(delta_input.distance_to_target or 0.0))
    if distance <= 0.25:
        return distance
    return distance / strike_price


def delta_multiplier_for_score(delta_score: float) -> float:
    regime = classify_delta_regime(delta_score)
    if regime == DeltaRegime.LOW:
        return 1.0
    if regime == DeltaRegime.NORMAL:
        return 0.8
    if regime == DeltaRegime.HIGH:
        return 0.5
    return 0.2


def classify_delta_regime(delta_score: float) -> DeltaRegime:
    score = max(float(delta_score), 0.0)
    if score <= 1.0:
        return DeltaRegime.LOW
    if score <= 2.0:
        return DeltaRegime.NORMAL
    if score <= 4.0:
        return DeltaRegime.HIGH
    return DeltaRegime.EXTREME


def estimate_micro_delta(delta_input: MicroDeltaInput) -> MicroDeltaResult:
    distance_pct = _distance_pct(delta_input)
    time_remaining = max(int(delta_input.time_remaining_seconds), 0)
    volatility = abs(_as_decimal_move(_volatility(delta_input)))
    velocity = abs(_as_decimal_move(_price_velocity(delta_input)))
    spread = max(float(delta_input.spread), 0.0)
    liquidity = max(float(delta_input.liquidity), 0.0)

    if time_remaining <= 90:
        return MicroDeltaResult(
            delta_score=10.0,
            delta_regime=DeltaRegime.EXTREME,
            delta_multiplier=0.0,
            reason="entry_blocked_time_remaining_le_90s",
            new_entry_blocked=True,
        )

    tiny_distance = distance_pct <= 0.0015
    if time_remaining < 120 and tiny_distance:
        return MicroDeltaResult(
            delta_score=8.0,
            delta_regime=DeltaRegime.EXTREME,
            delta_multiplier=0.2,
            reason=f"extreme_near_strike_near_expiry distance_pct={distance_pct:.5f} time={time_remaining}",
        )

    closeness_factor = _clamp(0.006 / max(distance_pct, 0.0003), 0.25, 4.0)
    time_factor = _clamp(sqrt(300.0 / max(time_remaining, 1)), 0.75, 2.0)
    volatility_factor = _clamp(0.75 + (volatility / 0.02), 0.75, 2.5)
    velocity_factor = _clamp(1.0 + (velocity / 0.004), 1.0, 2.5)

    quality_factor = 1.0
    if spread >= 0.08:
        quality_factor += 0.20
    elif spread >= 0.04:
        quality_factor += 0.10

    if liquidity < 100.0:
        quality_factor += 0.20
    elif liquidity < 500.0:
        quality_factor += 0.10

    delta_score = closeness_factor * time_factor * volatility_factor * velocity_factor * quality_factor
    delta_score = round(_clamp(delta_score, 0.0, 10.0), 6)
    regime = classify_delta_regime(delta_score)

    reason = (
        f"distance_pct={distance_pct:.5f};time={time_remaining};"
        f"volatility={volatility:.5f};velocity={velocity:.5f};"
        f"spread={spread:.4f};liquidity={liquidity:.2f}"
    )

    return MicroDeltaResult(
        delta_score=delta_score,
        delta_regime=regime,
        delta_multiplier=delta_multiplier_for_score(delta_score),
        reason=reason,
    )
