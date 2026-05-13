from __future__ import annotations

import pandas as pd

from polymarket.regime_diagnostics import classify_candle_regime, classify_market_regime


def _candles(closes: list[float], *, volume: float = 100.0, range_pct: float = 0.001) -> pd.DataFrame:
    rows = []
    previous = closes[0]
    for close in closes:
        open_ = previous
        high = max(open_, close) * (1.0 + range_pct)
        low = min(open_, close) * (1.0 - range_pct)
        rows.append({"open": open_, "high": high, "low": low, "close": close, "volume": volume})
        previous = close
    frame = pd.DataFrame(rows)
    frame["rsi"] = 55.0
    frame["z_score"] = 0.2
    return frame


def test_regime_classifier_missing_fields_returns_unknown() -> None:
    result = classify_market_regime(liquidity_state="HEALTHY", cutoff_reason="none")

    payload = result.to_payload()
    assert payload["volatility_regime"] == "UNKNOWN"
    assert payload["trend_regime"] == "UNKNOWN"
    assert payload["volatility_score"] == 0.0
    assert "missing_market_movement" in payload["regime_reason"]


def test_regime_classifier_volatility_buckets() -> None:
    assert classify_market_regime(realized_volatility=0.001).volatility_regime == "LOW_VOL"
    assert classify_market_regime(realized_volatility=0.003).volatility_regime == "NORMAL_VOL"
    assert classify_market_regime(realized_volatility=0.007).volatility_regime == "HIGH_VOL"
    assert classify_market_regime(realized_volatility=0.012).volatility_regime == "EXTREME_VOL"
    assert classify_market_regime(price_change_pct=0.2).volatility_regime == "NORMAL_VOL"


def test_regime_classifier_trend_buckets() -> None:
    assert classify_market_regime(price_velocity=0.0001).trend_regime == "SIDEWAY"
    assert classify_market_regime(price_velocity=0.0005).trend_regime == "WEAK_UPTREND"
    assert classify_market_regime(price_velocity=0.0014).trend_regime == "STRONG_UPTREND"
    assert classify_market_regime(price_velocity=-0.0005).trend_regime == "WEAK_DOWNTREND"
    assert classify_market_regime(price_velocity=-0.0014).trend_regime == "STRONG_DOWNTREND"
    assert classify_market_regime(price_velocity=0.001, distance_from_ptb_pct=0.8).trend_regime == "BREAKOUT"


def test_regime_classifier_reversal_risk_when_price_and_velocity_conflict() -> None:
    result = classify_market_regime(
        price_velocity=-0.0006,
        distance_from_ptb_pct=0.4,
        seconds_remaining=180,
    )

    assert result.trend_regime == "REVERSAL_RISK"
    assert result.trend_strength > 0


def test_candle_regime_classifier_reports_probabilistic_uptrend() -> None:
    frame = _candles([100, 100.2, 100.4, 100.7, 101.0, 101.3, 101.7, 102.1, 102.5])

    payload = classify_candle_regime(recent_1m=frame.tail(6), recent_5m=frame).to_payload()

    assert payload["market_regime"] == "TREND_UP"
    assert payload["bullish_probability"] > payload["bearish_probability"]
    assert payload["trend_strength"] > 0
    assert "ema_gap" in payload["indicator_evidence"]


def test_candle_regime_classifier_reports_compression_without_trade_signal() -> None:
    frame = _candles([100.00, 100.01, 100.00, 100.01, 100.00, 100.01, 100.00, 100.01], range_pct=0.0001)

    payload = classify_candle_regime(recent_1m=frame.tail(6), recent_5m=frame).to_payload()

    assert payload["market_regime"] == "COMPRESSION"
    assert 0.0 <= payload["compression_score"] <= 1.0
    assert abs(payload["bullish_probability"] - payload["bearish_probability"]) < 0.25


def test_candle_regime_classifier_reports_extreme_volatility() -> None:
    frame = _candles([100, 103, 98, 104, 97, 105, 96, 106, 95])

    payload = classify_candle_regime(recent_1m=frame.tail(6), recent_5m=frame).to_payload()

    assert payload["market_regime"] == "EXTREME_VOL"
    assert payload["volatility_regime"] == "EXTREME_VOL"
