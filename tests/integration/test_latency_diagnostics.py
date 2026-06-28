import pytest
import json
import os
import time
from unittest.mock import MagicMock, patch
from polymarket.trader import PolymarketTrader, TradeOutcome, MarketDisplayMetrics
from config.settings import Settings

@pytest.fixture
def mock_settings():
    s = Settings()
    s.paper_trading = True
    s.hybrid_phase_v1_enabled = True
    s.quant_data_enabled = True
    s.research_data_enabled = True
    return s

def test_latency_field_calculation(mock_settings):
    """Verify latency fields are correctly populated in snapshots."""
    trader = PolymarketTrader(settings=mock_settings)
    trader.quant_events = MagicMock()
    trader.quant_events._with_candidate_trace_identity = MagicMock(side_effect=lambda p, t: p)
    
    ticker = "BTC"
    market_id = "pm-5m-btc-123"
    
    # Simulate a market that was first seen at 290s, token ready at 270s, and OB ready at 250s
    # We need to mock time.time() to match epoch_start for seconds_since_open calculation
    epoch_start = 1778727900
    
    # 1. First seen at 290s remaining (10s since open)
    with patch("time.time", return_value=epoch_start + 10):
        trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_start + 300,
            seconds_remaining=290,
            token_ids=None,
            orderbook_ready=False
        )
    
    # 2. Token ready at 270s remaining (30s since open)
    with patch("time.time", return_value=epoch_start + 30):
        trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_start + 300,
            seconds_remaining=270,
            token_ids=("token_yes", "token_no"),
            orderbook_ready=False
        )
        
    # Mark readiness in the internal store
    trader._phase2_mark_readiness(ticker=ticker, epoch_start=epoch_start, token_ready=True, seconds_remaining=270)
    
    # 3. Orderbook ready at 250s remaining (50s since open)
    with patch("time.time", return_value=epoch_start + 50):
        trader._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_start + 300,
            seconds_remaining=250,
            token_ids=("token_yes", "token_no"),
            orderbook_ready=True
        )
    trader._phase2_mark_readiness(ticker=ticker, epoch_start=epoch_start, orderbook_ready=True, seconds_remaining=250)

    # 4. Final decision
    outcome = TradeOutcome(
        market_id=market_id,
        question="BTC Above?",
        decision="skip",
        confidence=0.5,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="ev_below_threshold",
        display={
            "seconds_remaining": 250,
            "ev": 0.01,
            "yes_bid": 0.5,
            "yes_ask": 0.51,
            "spread": 0.01,
            "epoch_start": epoch_start
        }
    )
    
    # Patch ptb_tracker to return our mock timing
    trader.ptb_tracker.get_market_ptb = MagicMock()
    trader.ptb_tracker.get_market_ptb.return_value.seconds_remaining = 250
    trader.ptb_tracker.get_market_ptb.return_value.epoch_start_ts = epoch_start
    
    from unittest.mock import patch as patch_context
    with patch_context("time.time", return_value=epoch_start + 50):
        trader._emit_decision_event(outcome, ticker=ticker)
    
    # Verify research snapshot payload
    trader.quant_events.log_research_snapshot.assert_called_once()
    payload = trader.quant_events.log_research_snapshot.call_args[0][0]
    
    # Check fields from timing_payload (_phase2_observability_payload -> _phase2_readiness_timestamps)
    assert payload["token_ready_seconds_remaining"] == 270
    assert payload["orderbook_ready_seconds_remaining"] == 250
    
    # Check shadow inventory decision logic
    assert payload["shadow_inventory"]["theoretical_decision"] == "HOLD"

