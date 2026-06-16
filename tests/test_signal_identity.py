from __future__ import annotations

import ast
from pathlib import Path

from polymarket.signal import SignalResult


SIGNAL_PATH = Path(__file__).resolve().parents[1] / "polymarket" / "signal.py"
CANONICAL_SIGNAL_NAMES = {"reversion", "sniper", "trend", "NO_SIGNAL"}
CANONICAL_SIGNAL_REASONS = {
    "feed_not_ready",
    "insufficient_candles",
    "insufficient_after_indicators",
    "no_strategy_met_threshold",
    "reversion_yes_threshold_met",
    "reversion_no_threshold_met",
    "reversion_threshold_not_met",
    "sniper_yes_extreme_zscore",
    "sniper_no_extreme_zscore",
    "sniper_threshold_not_met",
    "trend_yes_adx_ema_confirmed",
    "trend_no_adx_ema_confirmed",
    "trend_threshold_not_met",
}


def test_signal_result_identity_defaults_preserve_existing_constructors() -> None:
    result = SignalResult(
        asset="BTC",
        side="SKIP",
        score=0.0,
        momentum_pct=0.0,
        rsi=50.0,
        vol_ratio=0.0,
        skip_reason="baseline",
    )

    assert result.signal_name == "UNKNOWN_SIGNAL"
    assert result.signal_reason == "unknown_reason"


def test_every_signal_result_producer_declares_canonical_identity_metadata() -> None:
    tree = ast.parse(SIGNAL_PATH.read_text(encoding="utf-8"))
    producer_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "SignalResult"
    ]

    assert producer_calls
    for call in producer_calls:
        keywords = {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg}
        assert "signal_name" in keywords, f"SignalResult producer at line {call.lineno} lacks signal_name"
        assert "signal_reason" in keywords, f"SignalResult producer at line {call.lineno} lacks signal_reason"

        signal_name = ast.literal_eval(keywords["signal_name"])
        signal_reason = ast.literal_eval(keywords["signal_reason"])
        assert signal_name in CANONICAL_SIGNAL_NAMES
        assert signal_reason in CANONICAL_SIGNAL_REASONS
