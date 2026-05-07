from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProbabilityModelInput:
    underlying_price: float
    target_price: float | None = None
    distance_to_target: float | None = None
    time_remaining_seconds: int = 300
    recent_price_velocity: float | None = None
    short_term_momentum: float | None = None
    volatility: float = 0.0
    orderbook_bid: float | None = None
    orderbook_ask: float | None = None
    spread: float = 0.0
    liquidity: float = 1_000.0
    polymarket_implied_probability: float | None = None
    strike_price: float | None = None
    price_velocity: float | None = None
    momentum: float | None = None
    yes_ask: float | None = None
    no_ask: float | None = None
    market_implied_probability: float | None = None
    data_age_seconds: float = 0.0
    max_data_age_seconds: float = 10.0


@dataclass(frozen=True, slots=True)
class ProbabilityModelResult:
    p_yes: float
    p_no: float
    confidence_score: float
    model_reason: str
    skipped: bool = False
    skip_reason: str = ""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _as_decimal_move(value: float) -> float:
    """Accept either decimal moves, percent moves, or price-unit moves."""
    value = float(value)
    if abs(value) > 1.0:
        return value / 100.0
    return value


def _target_price(model_input: ProbabilityModelInput) -> float:
    return float(model_input.target_price if model_input.target_price is not None else model_input.strike_price or 0.0)


def _price_velocity(model_input: ProbabilityModelInput) -> float:
    return float(model_input.recent_price_velocity if model_input.recent_price_velocity is not None else model_input.price_velocity or 0.0)


def _momentum(model_input: ProbabilityModelInput) -> float:
    return float(model_input.short_term_momentum if model_input.short_term_momentum is not None else model_input.momentum or 0.0)


def _implied_probability(model_input: ProbabilityModelInput) -> float:
    implied = model_input.polymarket_implied_probability
    if implied is None:
        implied = model_input.market_implied_probability
    if implied is None and model_input.yes_ask is not None and model_input.no_ask is not None:
        implied = (float(model_input.yes_ask) + (1.0 - float(model_input.no_ask))) / 2.0
    return float(implied if implied is not None else 0.50)


def _distance_pct(model_input: ProbabilityModelInput) -> float:
    target_price = _target_price(model_input)
    if target_price <= 0:
        return 0.0

    distance = model_input.distance_to_target
    if distance is None or distance == 0:
        distance = model_input.underlying_price - target_price

    if abs(distance) <= 0.25:
        return float(distance)
    return float(distance) / target_price


def _quality_multiplier(model_input: ProbabilityModelInput) -> tuple[float, list[str]]:
    reasons: list[str] = []

    spread = max(float(model_input.spread), 0.0)
    if spread >= 0.10:
        spread_multiplier = 0.45
        reasons.append("wide_spread")
    elif spread >= 0.04:
        spread_multiplier = 0.70
        reasons.append("elevated_spread")
    else:
        spread_multiplier = 1.0

    volatility = abs(_as_decimal_move(model_input.volatility))
    if volatility >= 0.06:
        volatility_multiplier = 0.55
        reasons.append("unstable_volatility")
    elif volatility >= 0.025:
        volatility_multiplier = 0.75
        reasons.append("elevated_volatility")
    else:
        volatility_multiplier = 1.0

    liquidity = max(float(model_input.liquidity), 0.0)
    if liquidity < 50.0:
        liquidity_multiplier = 0.50
        reasons.append("weak_liquidity")
    elif liquidity < 500.0:
        liquidity_multiplier = 0.75
        reasons.append("thin_liquidity")
    else:
        liquidity_multiplier = 1.0

    return spread_multiplier * volatility_multiplier * liquidity_multiplier, reasons


def estimate_probability(model_input: ProbabilityModelInput) -> ProbabilityModelResult:
    implied = _clamp(_implied_probability(model_input), 0.01, 0.99)

    if model_input.data_age_seconds > model_input.max_data_age_seconds:
        return ProbabilityModelResult(
            p_yes=implied,
            p_no=1.0 - implied,
            confidence_score=0.0,
            model_reason="data_stale",
            skipped=True,
            skip_reason="data_stale",
        )

    distance_pct = _clamp(_distance_pct(model_input), -0.02, 0.02)
    velocity = _clamp(_as_decimal_move(_price_velocity(model_input)), -0.02, 0.02)
    momentum = _clamp(_as_decimal_move(_momentum(model_input)), -0.02, 0.02)
    volatility = abs(_as_decimal_move(model_input.volatility))

    minutes_left = _clamp(model_input.time_remaining_seconds / 60.0, 0.25, 5.0)
    time_pressure = _clamp(1.0 + (5.0 - minutes_left) / 12.0, 1.0, 1.35)

    orderbook_mid = 0.0
    if model_input.orderbook_bid and model_input.orderbook_ask and model_input.orderbook_bid > 0 and model_input.orderbook_ask > 0:
        orderbook_mid = (model_input.orderbook_bid + model_input.orderbook_ask) / 2.0
    elif model_input.yes_ask is not None and model_input.no_ask is not None:
        orderbook_mid = (float(model_input.yes_ask) + (1.0 - float(model_input.no_ask))) / 2.0

    price_edge = _clamp(distance_pct / 0.004, -1.0, 1.0) * 0.18 * time_pressure
    velocity_edge = _clamp(velocity / 0.003, -1.0, 1.0) * 0.07
    momentum_edge = _clamp(momentum / 0.004, -1.0, 1.0) * 0.10
    market_edge = _clamp(orderbook_mid - implied, -0.15, 0.15) * 0.20

    raw_edge = price_edge + velocity_edge + momentum_edge + market_edge
    volatility_dampener = _clamp(1.0 - (volatility / 0.08), 0.35, 1.0)
    model_p_yes = 0.50 + raw_edge * volatility_dampener

    p_yes = _clamp((model_p_yes * 0.80) + (implied * 0.20), 0.01, 0.99)
    p_no = 1.0 - p_yes

    quality_multiplier, quality_reasons = _quality_multiplier(model_input)
    confidence = _clamp(0.52 + abs(p_yes - 0.50) * 1.40, 0.0, 0.88)
    confidence = _clamp(confidence * quality_multiplier, 0.0, 0.88)

    direction = "leans_yes" if p_yes >= 0.50 else "leans_no"
    reason_parts = [
        direction,
        f"distance={distance_pct:.5f}",
        f"velocity={velocity:.5f}",
        f"momentum={momentum:.5f}",
    ]
    reason_parts.extend(quality_reasons)

    return ProbabilityModelResult(
        p_yes=p_yes,
        p_no=p_no,
        confidence_score=confidence,
        model_reason=";".join(reason_parts),
    )
