from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


UNKNOWN_REGIME = "UNKNOWN"
VOLATILITY_REGIMES = {"LOW_VOL", "NORMAL_VOL", "HIGH_VOL", "EXTREME_VOL", UNKNOWN_REGIME}
MARKET_REGIMES = {"TREND_UP", "TREND_DOWN", "SIDEWAY", "EXTREME_VOL", "COMPRESSION", UNKNOWN_REGIME}
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
    market_regime: str = UNKNOWN_REGIME
    volatility_regime: str = UNKNOWN_REGIME
    volatility_score: float = 0.0
    trend_regime: str = UNKNOWN_REGIME
    trend_strength: float = 0.0
    bullish_probability: float = 0.5
    bearish_probability: float = 0.5
    reversal_risk: float = 0.0
    compression_score: float = 0.0
    indicator_evidence: str = ""
    regime_reason: str = "missing_market_movement"

    def to_payload(self) -> dict[str, object]:
        return {
            "market_regime": self.market_regime,
            "volatility_regime": self.volatility_regime,
            "volatility_score": round(float(self.volatility_score), 8),
            "trend_regime": self.trend_regime,
            "trend_strength": round(float(self.trend_strength), 8),
            "bullish_probability": round(float(self.bullish_probability), 8),
            "bearish_probability": round(float(self.bearish_probability), 8),
            "reversal_risk": round(float(self.reversal_risk), 8),
            "compression_score": round(float(self.compression_score), 8),
            "indicator_evidence": self.indicator_evidence,
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


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_series(frame: Any, column: str, limit: int) -> list[float]:
    try:
        if frame is None or len(frame) <= 0 or column not in frame:
            return []
        values = frame[column].tail(limit).tolist()
    except Exception:
        return []
    out: list[float] = []
    for value in values:
        number = _as_float(value)
        if number is not None:
            out.append(number)
    return out


def _ema(values: list[float], span: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / float(span + 1)
    out = [values[0]]
    for value in values[1:]:
        out.append((value * alpha) + (out[-1] * (1.0 - alpha)))
    return out


def _direction_persistence(opens: list[float], closes: list[float], *, bullish: bool) -> float:
    pairs = list(zip(opens[-8:], closes[-8:]))
    if not pairs:
        return 0.0
    matched = sum(1 for open_, close in pairs if (close >= open_) == bullish)
    return matched / float(len(pairs))


def _momentum_persistence(closes: list[float], *, bullish: bool) -> float:
    changes = [b - a for a, b in zip(closes[-9:-1], closes[-8:])]
    if not changes:
        return 0.0
    matched = sum(1 for change in changes if (change >= 0.0) == bullish)
    return matched / float(len(changes))


def _latest_frame_value(frame: Any, column: str) -> float | None:
    try:
        if frame is None or len(frame) <= 0 or column not in frame:
            return None
        return _as_float(frame[column].iloc[-1])
    except Exception:
        return None


def classify_candle_regime(
    *,
    recent_1m: Any = None,
    recent_5m: Any = None,
    orderbook_spread: Any = None,
    liquidity_state: Any = "",
) -> RegimeDiagnostics:
    """Classify candle-derived regime evidence for diagnostics only."""
    closes_5m = _safe_series(recent_5m, "close", 40)
    opens_5m = _safe_series(recent_5m, "open", 40)
    highs_5m = _safe_series(recent_5m, "high", 40)
    lows_5m = _safe_series(recent_5m, "low", 40)
    vols_5m = _safe_series(recent_5m, "volume", 40)
    closes_1m = _safe_series(recent_1m, "close", 30)
    opens_1m = _safe_series(recent_1m, "open", 30)

    closes = closes_5m or closes_1m
    opens = opens_5m or opens_1m
    if len(closes) < 5 or not opens:
        return RegimeDiagnostics(
            regime_reason=f"missing_candle_history liq={str(liquidity_state or UNKNOWN_REGIME)}"
        )

    last_close = closes[-1]
    first_close = closes[max(0, len(closes) - 8)]
    signed_move = (last_close - first_close) / first_close if first_close else 0.0

    true_ranges: list[float] = []
    for idx in range(1, min(len(closes), len(highs_5m), len(lows_5m))):
        high = highs_5m[-idx]
        low = lows_5m[-idx]
        prev_close = closes_5m[-idx - 1] if idx < len(closes_5m) else closes_5m[0]
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    atr = sum(true_ranges[-14:]) / float(len(true_ranges[-14:])) if true_ranges else 0.0
    volatility_score = abs(atr / last_close) if last_close else 0.0
    spread = _to_decimal(orderbook_spread)
    if spread is not None and spread > 0:
        volatility_score = max(volatility_score, min(spread * 0.25, 0.02))
    volatility_regime = _volatility_bucket(volatility_score)

    ema_fast = _ema(closes, 9)
    ema_slow = _ema(closes, 21)
    ema_gap = ((ema_fast[-1] - ema_slow[-1]) / last_close) if ema_fast and ema_slow and last_close else 0.0
    ema_slope = ((ema_fast[-1] - ema_fast[-4]) / last_close) if len(ema_fast) >= 4 and last_close else 0.0
    bullish_candle_persistence = _direction_persistence(opens, closes, bullish=True)
    bearish_candle_persistence = _direction_persistence(opens, closes, bullish=False)
    bullish_momentum_persistence = _momentum_persistence(closes, bullish=True)
    bearish_momentum_persistence = _momentum_persistence(closes, bullish=False)
    signed_persistence = (
        (bullish_candle_persistence + bullish_momentum_persistence)
        - (bearish_candle_persistence + bearish_momentum_persistence)
    ) / 2.0
    directional_evidence = (signed_move * 35.0) + (ema_gap * 45.0) + (ema_slope * 60.0) + (signed_persistence * 0.35)
    trend_strength = _clamp(abs(directional_evidence), 0.0, 1.0)

    recent_ranges = []
    if highs_5m and lows_5m:
        recent_ranges = [
            abs(high - low) / close
            for high, low, close in zip(highs_5m[-8:], lows_5m[-8:], closes_5m[-8:])
            if close
        ]
    avg_recent_range = sum(recent_ranges) / float(len(recent_ranges)) if recent_ranges else volatility_score
    compression_score = _clamp((0.003 - avg_recent_range) / 0.003, 0.0, 1.0)

    rsi = _latest_frame_value(recent_5m, "rsi")
    z_score = _latest_frame_value(recent_5m, "z_score")
    vwap_deviation = 0.0
    if vols_5m and sum(vols_5m[-20:]) > 0:
        vwap = sum(price * volume for price, volume in zip(closes_5m[-20:], vols_5m[-20:])) / sum(vols_5m[-20:])
        vwap_deviation = ((last_close - vwap) / vwap) if vwap else 0.0
    reversal_risk = 0.0
    if rsi is not None:
        reversal_risk = max(reversal_risk, _clamp((abs(rsi - 50.0) - 20.0) / 30.0, 0.0, 1.0))
    if z_score is not None:
        reversal_risk = max(reversal_risk, _clamp((abs(z_score) - 1.5) / 2.0, 0.0, 1.0))
    reversal_risk = max(reversal_risk, _clamp((abs(vwap_deviation) - 0.004) / 0.016, 0.0, 1.0))

    bullish_probability = _clamp(0.5 + (directional_evidence * 0.22), 0.05, 0.95)
    if directional_evidence > 0:
        bullish_probability = _clamp(bullish_probability - reversal_risk * 0.08, 0.05, 0.95)
    elif directional_evidence < 0:
        bullish_probability = _clamp(bullish_probability + reversal_risk * 0.08, 0.05, 0.95)
    bearish_probability = 1.0 - bullish_probability

    if volatility_regime == "EXTREME_VOL":
        market_regime = "EXTREME_VOL"
    elif compression_score >= 0.65 and trend_strength < 0.35:
        market_regime = "COMPRESSION"
    elif directional_evidence >= 0.18:
        market_regime = "TREND_UP"
    elif directional_evidence <= -0.18:
        market_regime = "TREND_DOWN"
    else:
        market_regime = "SIDEWAY"

    if market_regime == "TREND_UP":
        trend_regime = "STRONG_UPTREND" if trend_strength >= 0.6 else "WEAK_UPTREND"
    elif market_regime == "TREND_DOWN":
        trend_regime = "STRONG_DOWNTREND" if trend_strength >= 0.6 else "WEAK_DOWNTREND"
    elif reversal_risk >= 0.65:
        trend_regime = "REVERSAL_RISK"
    else:
        trend_regime = "SIDEWAY"

    indicator_evidence = (
        f"rsi={rsi:.1f} " if rsi is not None else "rsi=na "
    ) + f"ema_gap={ema_gap:.5f} atr={volatility_score:.5f} vwap_dev={vwap_deviation:.5f}"
    reason = (
        f"market={market_regime} vol={volatility_regime} trend={trend_regime} "
        f"bull={bullish_probability:.3f} bear={bearish_probability:.3f} "
        f"strength={trend_strength:.3f} reversal={reversal_risk:.3f} "
        f"compression={compression_score:.3f} liq={str(liquidity_state or UNKNOWN_REGIME)}"
    )
    return RegimeDiagnostics(
        market_regime=market_regime,
        volatility_regime=volatility_regime,
        volatility_score=volatility_score,
        trend_regime=trend_regime,
        trend_strength=trend_strength,
        bullish_probability=bullish_probability,
        bearish_probability=bearish_probability,
        reversal_risk=reversal_risk,
        compression_score=compression_score,
        indicator_evidence=indicator_evidence,
        regime_reason=reason,
    )


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
