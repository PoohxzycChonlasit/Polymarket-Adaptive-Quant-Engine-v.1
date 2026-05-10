from __future__ import annotations

from polymarket.regime_diagnostics import classify_market_regime


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
