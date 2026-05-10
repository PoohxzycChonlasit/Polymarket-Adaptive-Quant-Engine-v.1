from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


UNKNOWN_REGIME = "UNKNOWN"
VOLATILITY_REGIMES = {"LOW_VOL", "NORMAL_VOL", "HIGH_VOL", "EXTREME_VOL", UNKNOWN_REGIME}
TREND_REGIMES = {
    "SIDEWAY",
    "WEAK_UPTREND",
    "STRONG_UPTREND",
    "WEAK_DOWNTREND",
    "STRONG_DOWNTREND",
    "BREAKOUT",
    "REVERSAL_RISK",
    UNKNOWN_REGIME,
}


@dataclass(frozen=True)
class RegimeDiagnostics:
    volatility_regime: str = UNKNOWN_REGIME
    volatility_score: float = 0.0
    trend_regime: str = UNKNOWN_REGIME
    trend_strength: float = 0.0
    regime_reason: str = "missing_market_movement"

    def to_payload(self) -> dict[str, object]:
        return {
            "volatility_regime": self.volatility_regime,
            "volatility_score": round(float(self.volatility_score), 8),
            "trend_regime": self.trend_regime,
            "trend_strength": round(float(self.trend_strength), 8),
            "regime_reason": self.regime_reason,
        }


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _to_decimal(value: Any) -> float | None:
    number = _as_float(value)
    if number is None:
        return None
    if abs(number) > 1.0:
        return number / 100.0
    return number


def _percent_to_decimal(value: Any) -> float | None:
    number = _as_float(value)
    if number is None:
        return None
    return number / 100.0


def _first_decimal(payload: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, Mapping):
            continue
        decimal = _to_decimal(value)
        if decimal is not None:
            return decimal
    return None


def _first_percent_decimal(payload: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, Mapping):
            continue
        decimal = _percent_to_decimal(value)
        if decimal is not None:
            return decimal
    return None


def _volatility_bucket(score: float) -> str:
    if score <= 0.0015:
        return "LOW_VOL"
    if score <= 0.004:
        return "NORMAL_VOL"
    if score <= 0.009:
        return "HIGH_VOL"
    return "EXTREME_VOL"


def _trend_bucket(
    *,
    signed_move: float,
    trend_strength: float,
    distance_from_ptb: float | None,
    velocity_window: float | None,
    seconds_remaining: float | None,
) -> str:
    if (
        distance_from_ptb is not None
        and velocity_window is not None
        and abs(distance_from_ptb) >= 0.003
        and abs(velocity_window) >= 0.002
        and distance_from_ptb * velocity_window < 0
    ):
        return "REVERSAL_RISK"
    if (
        distance_from_ptb is not None
        and abs(distance_from_ptb) >= 0.006
        and trend_strength >= 0.004
        and (seconds_remaining is None or seconds_remaining > 45)
    ):
        return "BREAKOUT"
    if trend_strength < 0.0015:
        return "SIDEWAY"
    if signed_move > 0:
        return "STRONG_UPTREND" if trend_strength >= 0.006 else "WEAK_UPTREND"
    if signed_move < 0:
        return "STRONG_DOWNTREND" if trend_strength >= 0.006 else "WEAK_DOWNTREND"
    return "SIDEWAY"


def classify_market_regime(
    *,
    price_change_pct: Any = None,
    realized_volatility: Any = None,
    price_velocity: Any = None,
    distance_from_ptb_pct: Any = None,
    seconds_remaining: Any = None,
    orderbook_spread: Any = None,
    orderbook_age_ms: Any = None,
    decision_latency_ms: Any = None,
    liquidity_state: Any = "",
    cutoff_reason: Any = "",
) -> RegimeDiagnostics:
    """Classify market regime for diagnostics only; never feeds trade decisions."""
    price_change = _percent_to_decimal(price_change_pct)
    realized_vol = _to_decimal(realized_volatility)
    velocity = _to_decimal(price_velocity)
    distance_from_ptb = _percent_to_decimal(distance_from_ptb_pct)
    spread = _to_decimal(orderbook_spread)
    seconds_left = _as_float(seconds_remaining)
    orderbook_age = _as_float(orderbook_age_ms)
    latency = _as_float(decision_latency_ms)

    velocity_window = velocity * 5.0 if velocity is not None else None
    movement_components = [
        abs(value)
        for value in (price_change, realized_vol, velocity_window)
        if value is not None
    ]
    if not movement_components:
        return RegimeDiagnostics(
            regime_reason=(
                "missing_market_movement "
                f"liq={str(liquidity_state or UNKNOWN_REGIME)} cutoff={str(cutoff_reason or 'none')}"
            )
        )

    volatility_score = max(movement_components)
    if spread is not None and spread > 0:
        volatility_score = max(volatility_score, min(spread * 0.25, 0.02))
    volatility_regime = _volatility_bucket(volatility_score)

    signed_move = 0.0
    for candidate in (velocity_window, price_change, distance_from_ptb):
        if candidate is not None and abs(candidate) > 0:
            signed_move = candidate
            break
    trend_strength = max(
        abs(value)
        for value in (signed_move, distance_from_ptb or 0.0, price_change or 0.0)
    )
    trend_regime = _trend_bucket(
        signed_move=signed_move,
        trend_strength=trend_strength,
        distance_from_ptb=distance_from_ptb,
        velocity_window=velocity_window,
        seconds_remaining=seconds_left,
    )
    reason = (
        f"vol={volatility_regime} trend={trend_regime} "
        f"movement={volatility_score:.5f} strength={trend_strength:.5f} "
        f"spread={(spread or 0.0):.5f} age_ms={(orderbook_age or 0.0):.0f} "
        f"latency_ms={(latency or 0.0):.0f} liq={str(liquidity_state or UNKNOWN_REGIME)} "
        f"cutoff={str(cutoff_reason or 'none')}"
    )
    return RegimeDiagnostics(
        volatility_regime=volatility_regime,
        volatility_score=volatility_score,
        trend_regime=trend_regime,
        trend_strength=trend_strength,
        regime_reason=reason,
    )


def classify_market_regime_from_payload(payload: Mapping[str, Any]) -> RegimeDiagnostics:
    display = payload.get("display") if isinstance(payload.get("display"), Mapping) else {}
    merged: dict[str, Any] = {**dict(display), **dict(payload)}
    price_change = _first_percent_decimal(
        merged,
        "price_change_pct",
        "momentum_pct",
        "price_diff_pct",
    )
    distance_from_ptb = _first_percent_decimal(
        merged,
        "distance_from_ptb_pct",
        "distance_from_open_pct",
    )
    if distance_from_ptb is None:
        distance_decimal = _first_decimal(merged, "distance_to_strike")
        distance_from_ptb_pct = distance_decimal * 100.0 if distance_decimal is not None else None
    else:
        distance_from_ptb_pct = distance_from_ptb * 100.0
    return classify_market_regime(
        price_change_pct=price_change * 100.0 if price_change is not None else None,
        realized_volatility=_first_decimal(
            merged,
            "realized_volatility",
            "recent_volatility",
            "volatility",
            "log_volatility",
        ),
        price_velocity=_first_decimal(merged, "price_velocity", "recent_price_velocity"),
        distance_from_ptb_pct=distance_from_ptb_pct,
        seconds_remaining=merged.get("seconds_remaining", merged.get("seconds_until_close")),
        orderbook_spread=merged.get("spread", merged.get("orderbook_spread")),
        orderbook_age_ms=merged.get("orderbook_age_ms"),
        decision_latency_ms=merged.get("decision_latency_ms"),
        liquidity_state=merged.get("liquidity_state", ""),
        cutoff_reason=merged.get("cutoff_reason", merged.get("adaptive_cutoff_reason", "")),
    )
