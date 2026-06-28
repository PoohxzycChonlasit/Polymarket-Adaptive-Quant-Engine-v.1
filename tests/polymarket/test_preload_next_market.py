from unittest.mock import MagicMock, patch, ANY
import unittest
import pytest
import time

from polymarket.trader import PolymarketTrader
from polymarket.gamma_fetcher import ActiveFiveMinMarket
from utils.quant_event_logger import QuantEventLogger

@pytest.fixture
def mock_trader_instance():
    settings = MagicMock()
    settings.paper_trading = True
    settings.trading_enabled = False # Ensure no live trading is accidentally triggered
    
    trader = PolymarketTrader(settings)
    trader._paused_insufficient_funds = False
    trader.gamma = MagicMock()
    trader.quant_events = MagicMock(spec=QuantEventLogger)
    trader._emit_quant_event = MagicMock()
    
    # Mock tracker.summary to avoid complex state dependencies
    trader.tracker = MagicMock()
    trader.tracker.summary.return_value = MagicMock()
    
    # Mock _risk_mgr
    trader._risk_mgr = MagicMock()
    trader._risk_mgr.can_trade.return_value = (True, "")
    
    # Mock various methods that might cause early exit or errors
    trader.reconcile_live_positions = MagicMock()
    trader._update_bankroll_state = MagicMock()
    trader._maybe_emit_risk_state_event = MagicMock()
    trader._maybe_emit_system_health = MagicMock()
    trader._cancel_stale_entry_orders_if_needed = MagicMock()
    trader._check_stalled_positions = MagicMock()
    trader._manage_open_positions_for_cycle = MagicMock()
    
    # Mock _select_markets to avoid complex market selection logic in these tests
    trader._select_markets = MagicMock(return_value=[])
    
    # Mock client
    trader.client = MagicMock()

    return trader

@pytest.fixture
def mock_active_five_min_market():
    market = MagicMock(spec=ActiveFiveMinMarket)
    market.market_id = "test_market_id_next"
    market.condition_id = "test_condition_id_next"
    market.slug = "test-slug-next"
    # Ensure epoch start is a multiple of 300 for consistent testing
    base_time = (int(time.time()) // 300) * 300
    market.epoch_start_ts = base_time + 300 
    market.epoch_end_ts = base_time + 600
    market.yes_token_id = "token_yes"
    market.no_token_id = "token_no"
    return market

def test_preload_success_v1(mock_trader_instance, mock_active_five_min_market):
    trader = mock_trader_instance
    trader.gamma.get_next_5min_market.return_value = mock_active_five_min_market
    
    # Ensure next_expected_epoch matches our mock market
    mock_now = mock_active_five_min_market.epoch_start_ts - 290 # 10s into current epoch
    
    with patch('time.time', return_value=mock_now), \
         patch('time.monotonic', return_value=100.0):
        
        trader._preload_next_market("BTC/ETH")
        
        assert trader._preloaded_next_markets["BTC"] == mock_active_five_min_market
        assert trader._preload_attempted is True
        assert trader._preload_success is True
        assert trader._preload_ticker == "BTC"
        assert trader._preload_market_slug == "test-slug-next"
        assert trader._preload_condition_id == "test_condition_id_next"
        assert trader._preload_yes_token_id_present is True
        assert trader._preload_no_token_id_present is True
        assert trader._preload_orderbook_warmed is True
        assert trader._preload_orderbook_state == "WARMED"
        
        # Verify orderbook warming calls
        assert trader.client.get_orderbook.call_count == 2
        trader.client.get_orderbook.assert_any_call("token_yes")
        trader.client.get_orderbook.assert_any_call("token_no")

        # Verify emitted event
        trader._emit_quant_event.assert_called_once()
        args, _ = trader._emit_quant_event.call_args
        assert args[0] == "log_system_health"
        payload = args[1]
        assert payload["event"] == "preload_next_market_v1"
        assert payload["preload_success"] is True
        assert payload["preload_ticker"] == "BTC"
        assert payload["preload_orderbook_warmed"] is True

def test_preload_cache_hit_v1(mock_trader_instance, mock_active_five_min_market):
    trader = mock_trader_instance
    trader.gamma.get_next_5min_market.return_value = mock_active_five_min_market
    
    # 1. First preload
    mock_now1 = mock_active_five_min_market.epoch_start_ts - 290
    with patch('time.time', return_value=mock_now1):
        trader._preload_next_market("BTC/ETH")
        assert trader._preload_cache_hit is False
    
    # 2. Second preload in same epoch
    mock_now2 = mock_now1 + 5
    with patch('time.time', return_value=mock_now2):
        trader._preload_next_market("BTC/ETH")
        assert trader._preload_cache_hit is True
        assert trader._preload_success is True
        # Should not have called gamma again
        assert trader.gamma.get_next_5min_market.call_count == 1

def test_preload_failure_soft_v1(mock_trader_instance):
    trader = mock_trader_instance
    trader.gamma.get_next_5min_market.return_value = None
    
    trader._preload_next_market("BTC/ETH")
    
    assert trader._preload_success is False
    assert trader._preload_failed_reason == "no_next_market_found"
    # Should not raise exception
    trader._emit_quant_event.assert_called_with("log_system_health", ANY)

def test_preload_exception_soft_v1(mock_trader_instance):
    trader = mock_trader_instance
    trader.gamma.get_next_5min_market.side_effect = Exception("Network Down")
    
    # Should not raise exception to the caller
    trader._preload_next_market("BTC/ETH")
    
    assert trader._preload_success is False
    assert "exception: Network Down" in trader._preload_failed_reason

def test_snapshot_persistence_v1(mock_trader_instance, mock_active_five_min_market):
    trader = mock_trader_instance
    trader.gamma.get_next_5min_market.return_value = mock_active_five_min_market
    
    trader._preload_next_market("BTC/ETH")
    
    # Manually trigger observability payload enrichment
    detail = trader._phase2_complete_lifecycle_observability({
        "market_id": "current_id",
        "ticker": "BTC",
        "side": "YES",
        "epoch_start": int(time.time())
    })
    
    assert detail["preload_success"] is True
    assert detail["preload_ticker"] == "BTC"
    assert detail["preload_market_slug"] == "test-slug-next"
    assert detail["preload_orderbook_warmed"] is True
