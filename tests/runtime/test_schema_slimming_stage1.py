import pytest
from unittest.mock import MagicMock
from polymarket.trader import PolymarketTrader, TradeOutcome
from config.settings import Settings

@pytest.fixture
def mock_settings():
    s = Settings()
    s.paper_trading = True
    s.quant_data_enabled = True
    s.research_data_enabled = True
    return s

def test_stage_1_key_promotion_success(mock_settings):
    """
    Verifies that all 33 display-only keys are successfully promoted from display to root payload
    for log_decision events, while leaving the display dictionary unchanged.
    """
    trader = PolymarketTrader(settings=mock_settings)
    trader.quant_events = MagicMock()
    # Mock trace identity enrichment
    trader.quant_events._with_candidate_trace_identity = MagicMock(side_effect=lambda p, t: p)
    trader.quant_events.log_decision.return_value = True

    # Build a dictionary containing dummy values for all 33 display-only keys
    display_mock_data = {
        "adaptive_cutoff_denied_reason": "test_reason",
        "ask_price": 0.55,
        "best_market": "btc-5m",
        "best_side": "YES",
        "book_to_tradable_seconds": 12,
        "clob_consecutive_failures": 0,
        "clob_last_error_category": "NONE",
        "clob_last_error_class": "NONE",
        "delta_multiplier": 1.5,
        "delta_regime": "UP",
        "depth_ready": True,
        "discovery_to_book_seconds": 5,
        "distance_from_ptb_pct": 0.02,
        "epoch_end_ts": 1770000000,
        "epoch_start_ts": 1769999700,
        "final_size": 20.0,
        "frequency_multiplier": 1.0,
        "last_successful_orderbook_age_ms": 350,
        "liquidity_ready": True,
        "min_ev": 0.01,
        "mode": "paper",
        "model_p_no": 0.35,
        "model_p_yes": 0.65,
        "no_orderbook_age_ms": 120,
        "p_no": 0.38,
        "p_yes": 0.62,
        "price_change_pct": 0.005,
        "price_velocity": 0.0001,
        "realized_volatility": 0.012,
        "risk_plan_zero_diagnostics": {"reason": "zero_budget"},
        "score": 45.2,
        "total_discovery_to_tradable_seconds": 15,
        "yes_orderbook_age_ms": 110,
    }

    # Also add standard keys that are NOT display-only (should not be overwritten or break)
    display_mock_data["seconds_remaining"] = 120
    display_mock_data["ticker"] = "BTC"

    outcome = TradeOutcome(
        market_id="pm-5m-btc-123",
        question="Will BTC...",
        decision="skip",
        confidence=0.5,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="confidence_too_low",
        display=display_mock_data
    )

    trader.ptb_tracker.get_market_ptb = MagicMock()
    trader.ptb_tracker.get_market_ptb.return_value.seconds_remaining = 120

    # Emit the decision event
    trader._emit_decision_event(outcome, ticker="BTC")

    # Verify log_decision was called
    trader.quant_events.log_decision.assert_called_once()
    payload = trader.quant_events.log_decision.call_args[0][0]

    # Verify:
    # 1. The nested "display" dict still exists and matches display_mock_data exactly
    assert "display" in payload
    assert payload["display"] == display_mock_data

    # 2. Every one of the 33 display-only keys is now present at the root payload level
    display_only_keys = [
        "adaptive_cutoff_denied_reason", "ask_price", "best_market", "best_side",
        "book_to_tradable_seconds", "clob_consecutive_failures", "clob_last_error_category",
        "clob_last_error_class", "delta_multiplier", "delta_regime", "depth_ready",
        "discovery_to_book_seconds", "distance_from_ptb_pct", "epoch_end_ts", "epoch_start_ts",
        "final_size", "frequency_multiplier", "last_successful_orderbook_age_ms",
        "liquidity_ready", "min_ev", "mode", "model_p_no", "model_p_yes",
        "no_orderbook_age_ms", "p_no", "p_yes", "price_change_pct", "price_velocity",
        "realized_volatility", "risk_plan_zero_diagnostics", "score",
        "total_discovery_to_tradable_seconds", "yes_orderbook_age_ms"
    ]

    for key in display_only_keys:
        assert key in payload, f"Promoted key '{key}' missing from root payload"
        # 3. Root value equals display value
        assert payload[key] == display_mock_data[key], f"Value mismatch for key '{key}'"

    # 4. Standard fields (which might already be written) are also intact
    assert payload["ticker"] == "BTC"
    assert payload["decision_type"] == "skipped"
