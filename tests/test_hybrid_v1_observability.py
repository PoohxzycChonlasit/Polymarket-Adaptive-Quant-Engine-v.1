import pytest
from unittest.mock import MagicMock, patch
from polymarket.trader import PolymarketTrader, TradeOutcome
from polymarket.gamma_fetcher import GammaMarket
from config.settings import Settings

@pytest.fixture
def mock_settings():
    s = Settings()
    s.paper_trading = True
    s.hybrid_phase_v1_enabled = True
    s.quant_data_enabled = True
    s.research_data_enabled = True
    return s

def test_hybrid_v1_runtime_emission_path(mock_settings):
    """Confirm research snapshots are emitted through the decision event path."""
    trader = PolymarketTrader(settings=mock_settings)
    trader.quant_events = MagicMock()
    # Mock trace identity enrichment
    trader.quant_events._with_candidate_trace_identity = MagicMock(side_effect=lambda p, t: p)
    trader.quant_events.log_research_snapshot.return_value = True
    
    ticker = "BTC"
    outcome = TradeOutcome(
        market_id="pm-5m-btc-123",
        question="Will BTC...",
        decision="skip",
        confidence=0.5,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="confidence_too_low",
        display={"seconds_remaining": 100, "ev": 0.05, "yes_bid": 0.5, "yes_ask": 0.51, "spread": 0.01}
    )
    
    # Patch ptb_tracker to avoid actual lookups
    trader.ptb_tracker.get_market_ptb = MagicMock()
    trader.ptb_tracker.get_market_ptb.return_value.seconds_remaining = 100
    
    # Call _emit_decision_event which now triggers the research snapshot
    trader._emit_decision_event(outcome, ticker=ticker)
    
    # Verify both log_decision AND log_research_snapshot were called
    trader.quant_events.log_decision.assert_called_once()
    trader.quant_events.log_research_snapshot.assert_called_once()
    
    # Check research payload (now enriched by _phase2_observability_payload)
    payload = trader.quant_events.log_research_snapshot.call_args[0][0]
    # In my implementation, _phase2_observability_payload sets "ticker"
    assert payload["ticker"] == "BTC"
    assert payload["actual_decision"] == "skip"
    assert "shadow_inventory" in payload

def test_quant_event_logger_research_config(mock_settings):
    """Verify QuantEventLogger is correctly configured for research snapshots."""
    from utils.quant_event_logger import QuantEventLogger

    logger = QuantEventLogger(mode="paper", enabled=True)
    assert logger.research_enabled is True
    assert "research_snapshot" in logger._CATEGORY_BY_METHOD
    assert logger._CATEGORY_BY_METHOD["research_snapshot"] == "research_log"


def test_snapshot_includes_orderbook_probe_fields(mock_settings):
    """
    Regression: research snapshot must include snapshot_* probe fields from outcome.display.
    These fields let us compare research_log depth against the live display/orderbook path.
    """
    trader = PolymarketTrader(settings=mock_settings)
    trader.quant_events = MagicMock()
    trader.quant_events._with_candidate_trace_identity = MagicMock(side_effect=lambda p, t: p)
    trader.quant_events.log_research_snapshot.return_value = True

    ticker = "BTC"
    outcome = TradeOutcome(
        market_id="pm-5m-btc-123",
        question="Will BTC...",
        decision="skip",
        confidence=0.5,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="hard_close_zone",
        display={
            "seconds_remaining": 28,
            "yes_bid": 0.52,
            "yes_ask": 0.54,
            "yes_bid_size": 150.0,
            "yes_ask_size": 120.0,
            "spread": 0.02,
            "orderbook_age_ms": 800,
            "orderbook_readiness_reason": "empty_book",
            "orderbook_refresh_source": "scheduled_run_single_cycle",
        },
    )
    trader._emit_decision_event(outcome, ticker=ticker)

    trader.quant_events.log_research_snapshot.assert_called_once()
    payload = trader.quant_events.log_research_snapshot.call_args[0][0]

    # All 8 probe fields must be present
    assert "snapshot_bid" in payload, "snapshot_bid missing from research snapshot"
    assert "snapshot_ask" in payload, "snapshot_ask missing from research snapshot"
    assert "snapshot_spread" in payload, "snapshot_spread missing from research snapshot"
    assert "snapshot_best_bid_size" in payload, "snapshot_best_bid_size missing"
    assert "snapshot_best_ask_size" in payload, "snapshot_best_ask_size missing"
    assert "snapshot_orderbook_source" in payload, "snapshot_orderbook_source missing"
    assert "snapshot_orderbook_age_ms" in payload, "snapshot_orderbook_age_ms missing"
    assert "snapshot_orderbook_empty_reason" in payload, "snapshot_orderbook_empty_reason missing"

    # Values must reflect the display path
    assert payload["snapshot_bid"] == 0.52
    assert payload["snapshot_ask"] == 0.54
    assert payload["snapshot_spread"] == 0.02
    assert payload["snapshot_best_bid_size"] == 150.0
    assert payload["snapshot_best_ask_size"] == 120.0
    assert payload["snapshot_orderbook_age_ms"] == 800
    assert payload["snapshot_orderbook_empty_reason"] == "empty_book"
    assert payload["snapshot_orderbook_source"] == "scheduled_run_single_cycle"


def test_snapshot_empty_book_reason_reported(mock_settings):
    """
    When book is genuinely empty (zero bid/ask sizes), snapshot must report
    snapshot_best_bid_size=0, snapshot_best_ask_size=0 and the empty reason field.
    """
    trader = PolymarketTrader(settings=mock_settings)
    trader.quant_events = MagicMock()
    trader.quant_events._with_candidate_trace_identity = MagicMock(side_effect=lambda p, t: p)
    trader.quant_events.log_research_snapshot.return_value = True

    outcome = TradeOutcome(
        market_id="pm-5m-eth-456",
        question="Will ETH...",
        decision="skip",
        confidence=0.5,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="empty_book",
        display={
            "seconds_remaining": 15,
            "yes_bid": 0.0,
            "yes_ask": 0.0,
            "yes_bid_size": 0.0,
            "yes_ask_size": 0.0,
            "spread": 0.0,
            "orderbook_age_ms": 0,
            "orderbook_readiness_reason": "empty_book",
            "orderbook_refresh_source": "",
        },
    )
    trader._emit_decision_event(outcome, ticker="ETH")

    payload = trader.quant_events.log_research_snapshot.call_args[0][0]
    assert payload["snapshot_best_bid_size"] == 0.0
    assert payload["snapshot_best_ask_size"] == 0.0
    assert payload["snapshot_orderbook_empty_reason"] == "empty_book"
    assert payload["snapshot_bid"] == 0.0
    assert payload["snapshot_ask"] == 0.0


def test_snapshot_nonzero_depth_reported_correctly(mock_settings):
    """
    When display carries nonzero bid/ask sizes, snapshot probe fields must reflect
    them — confirming that real depth in the display path reaches the research log.
    """
    trader = PolymarketTrader(settings=mock_settings)
    trader.quant_events = MagicMock()
    trader.quant_events._with_candidate_trace_identity = MagicMock(side_effect=lambda p, t: p)
    trader.quant_events.log_research_snapshot.return_value = True

    outcome = TradeOutcome(
        market_id="pm-5m-btc-789",
        question="Will BTC...",
        decision="skip",
        confidence=0.6,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="confidence_too_low",
        display={
            "seconds_remaining": 180,
            "yes_bid": 0.48,
            "yes_ask": 0.50,
            "yes_bid_size": 500.0,
            "yes_ask_size": 480.0,
            "spread": 0.02,
            "orderbook_age_ms": 250,
            "orderbook_readiness_reason": "",
            "orderbook_refresh_source": "scheduled_run_single_cycle",
        },
    )
    trader._emit_decision_event(outcome, ticker="BTC")

    payload = trader.quant_events.log_research_snapshot.call_args[0][0]
    assert payload["snapshot_best_bid_size"] == 500.0, "Nonzero depth must reach snapshot"
    assert payload["snapshot_best_ask_size"] == 480.0, "Nonzero depth must reach snapshot"
    assert payload["snapshot_bid"] == 0.48
    assert payload["snapshot_ask"] == 0.50


def test_lifecycle_latency_fields_present_in_snapshot_when_epoch_populated(mock_settings):
    """
    When epoch_start is present in display, _emit_hybrid_v1_snapshot must include
    lifecycle latency fields from Lifecycle Latency Observatory v1.
    Fields default to 0 when timestamps are absent — but the keys must exist.
    """
    trader = PolymarketTrader(settings=mock_settings)
    trader.quant_events = MagicMock()
    trader.quant_events._with_candidate_trace_identity = MagicMock(side_effect=lambda p, t: p)
    trader.quant_events.log_research_snapshot.return_value = True

    import time as _time
    epoch_start = int(_time.time()) // 300 * 300

    outcome = TradeOutcome(
        market_id="pm-5m-btc-lat",
        question="Will BTC...",
        decision="skip",
        confidence=0.5,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="confidence_too_low",
        display={
            "seconds_remaining": 150,
            "market_epoch_start": epoch_start,
            "yes_bid": 0.50,
            "yes_ask": 0.51,
            "spread": 0.01,
        },
    )
    trader._emit_decision_event(outcome, ticker="BTC")

    payload = trader.quant_events.log_research_snapshot.call_args[0][0]
    _latency_keys = (
        "discovery_to_token_ready_ms",
        "token_ready_to_book_ms",
        "book_to_nonzero_ms",
        "nonzero_to_normalized_ms",
        "normalized_to_executable_ms",
        "executable_to_decision_ms",
        "total_discovery_to_decision_ms",
        "dominant_latency_stage",
        "lifecycle_latency_classification",
    )
    for key in _latency_keys:
        assert key in payload, f"Latency key '{key}' missing from research snapshot"


def test_lifecycle_latency_decision_complete_ts_written_once(mock_settings):
    """
    decision_complete_ts must be written into the readiness bucket exactly once
    (first call wins; second call must not overwrite it).
    """
    trader = PolymarketTrader(settings=mock_settings)
    trader.quant_events = MagicMock()
    trader.quant_events._with_candidate_trace_identity = MagicMock(side_effect=lambda p, t: p)
    trader.quant_events.log_research_snapshot.return_value = True

    import time as _time
    epoch_start = int(_time.time()) // 300 * 300

    def _make_outcome():
        return TradeOutcome(
            market_id="pm-5m-eth-lat",
            question="Will ETH...",
            decision="skip",
            confidence=0.5,
            risk_plan=None,
            receipt=None,
            skipped=True,
            skip_reason="confidence_too_low",
            display={"seconds_remaining": 100, "market_epoch_start": epoch_start},
        )

    trader._emit_decision_event(_make_outcome(), ticker="ETH")
    bucket = trader._phase2_readiness_store().get(("ETH", epoch_start), {})
    ts_first = bucket.get("decision_complete_ts", "")
    assert ts_first, "decision_complete_ts must be written after first emit"

    trader._emit_decision_event(_make_outcome(), ticker="ETH")
    bucket2 = trader._phase2_readiness_store().get(("ETH", epoch_start), {})
    ts_second = bucket2.get("decision_complete_ts", "")
    assert ts_second == ts_first, "decision_complete_ts must not be overwritten on second emit"


def test_lifecycle_latency_zero_when_epoch_absent(mock_settings):
    """
    When epoch_start is absent (0 or missing), latency fields must default to 0 and
    classification must be empty — no errors, no side-effects.
    """
    trader = PolymarketTrader(settings=mock_settings)
    trader.quant_events = MagicMock()
    trader.quant_events._with_candidate_trace_identity = MagicMock(side_effect=lambda p, t: p)
    trader.quant_events.log_research_snapshot.return_value = True

    outcome = TradeOutcome(
        market_id="pm-5m-btc-noepoch",
        question="Will BTC...",
        decision="skip",
        confidence=0.5,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="no_epoch",
        display={"seconds_remaining": 100},  # no epoch_start
    )
    trader._emit_decision_event(outcome, ticker="BTC")

    payload = trader.quant_events.log_research_snapshot.call_args[0][0]
    # Without epoch, latency fields are absent (bucket not created) or default 0
    assert payload.get("total_discovery_to_decision_ms", 0) == 0
    assert payload.get("lifecycle_latency_classification", "") == ""
    # snapshot probe fields must still be present (other parts of snapshot unaffected)
    assert "snapshot_orderbook_age_ms" in payload
    assert payload["snapshot_orderbook_empty_reason"] == ""
