from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from polymarket.trader import PolymarketTrader
from utils.quant_event_logger import QuantEventLogger


def _trader() -> PolymarketTrader:
    trader = PolymarketTrader.__new__(PolymarketTrader)
    trader._runtime_mode = lambda: "paper"
    trader._utc_timestamp = lambda: "2026-05-28T00:00:00Z"
    trader.quant_events = SimpleNamespace(run_id="run_probe_test", schema_version="test")
    return trader


def _ob(
    *,
    token_id: str,
    bid: float,
    ask: float,
    bid_size: float,
    ask_size: float,
    age_ms: int,
    bids_count: int = 1,
    asks_count: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        token_id=token_id,
        condition_id="condition-1",
        best_bid=bid,
        best_ask=ask,
        bid_size=bid_size,
        ask_size=ask_size,
        age_seconds=age_ms / 1000.0,
        raw_response={
            "top_bids": [{"price": bid, "size": bid_size}] * bids_count,
            "top_asks": [{"price": ask, "size": ask_size}] * asks_count,
            "timestamp": "1770000000000",
        },
    )


def test_orderbook_lineage_probe_payload_is_evidence_only_and_bounded() -> None:
    trader = _trader()

    payload = trader._build_orderbook_lineage_probe_payload(
        ticker="BTC",
        market_id="pm-5m-btc",
        market_slug="btc-updown-5m",
        condition_id="condition-1",
        yes_token_id="yes-token",
        no_token_id="no-token",
        yes_ob=_ob(token_id="yes-token", bid=0.44, ask=0.46, bid_size=12, ask_size=10, age_ms=900),
        no_ob=_ob(token_id="no-token", bid=0.54, ask=0.56, bid_size=9, ask_size=8, age_ms=1100),
        yes_bid=0.44,
        yes_ask=0.46,
        yes_bid_size=12,
        yes_ask_size=10,
        no_bid=0.54,
        no_ask=0.56,
        no_bid_size=9,
        no_ask_size=8,
        yes_orderbook_age_ms=900,
        no_orderbook_age_ms=1100,
        orderbook_fetch_succeeded=True,
        current_executable_yes_no_book=True,
        orderbook_refresh_detail={
            "decision_token_pair_key": "condition-1|yes-token|no-token|btc-updown-5m",
            "orderbook_current_fetch_status": "fresh_fetch_executable",
            "orderbook_stale_reuse_source": "CURRENT_DECISION_FETCH_EXECUTABLE",
        },
        fetch_attempt_ts="2026-05-28T00:00:00.100Z",
        fetch_complete_ts="2026-05-28T00:00:00.112Z",
        fetch_duration_ms=12.0,
        lifecycle_phase="OPENING_SCAN",
        seconds_remaining=180,
    )

    assert payload["probe_id"] == "ORDERBOOK_LINEAGE_PROBE_V1"
    assert payload["schema_version"] == "orderbook_lineage_probe_v1"
    assert payload["probe_authority_level"] == "evidence_only"
    assert payload["policy_authority"] == "none"
    assert payload["runtime_decision_authority"] is False
    assert payload["execution_authority"] is False
    assert payload["risk_authority"] is False
    assert "raw_response" not in payload
    assert "bids" not in payload
    assert "asks" not in payload


def test_orderbook_lineage_probe_marks_side_specific_current_fetch_truth() -> None:
    trader = _trader()

    payload = trader._build_orderbook_lineage_probe_payload(
        ticker="ETH",
        market_id="pm-5m-eth",
        market_slug="eth-updown-5m",
        condition_id="condition-eth",
        yes_token_id="yes-token",
        no_token_id="no-token",
        yes_ob=_ob(token_id="yes-token", bid=0.41, ask=0.43, bid_size=5, ask_size=7, age_ms=500),
        no_ob=_ob(token_id="no-token", bid=0.57, ask=0.59, bid_size=6, ask_size=8, age_ms=700),
        yes_bid=0.41,
        yes_ask=0.43,
        no_bid=0.57,
        no_ask=0.59,
        yes_orderbook_age_ms=500,
        no_orderbook_age_ms=700,
        orderbook_fetch_succeeded=True,
        current_executable_yes_no_book=True,
        orderbook_refresh_detail={
            "decision_token_pair_key": "condition-eth|yes-token|no-token|eth-updown-5m",
            "orderbook_current_fetch_status": "fresh_fetch_executable",
        },
    )

    assert payload["current_fetch_status"] == "fresh_fetch_executable"
    assert payload["yes_fetch_status"] == "executable"
    assert payload["no_fetch_status"] == "executable"
    assert payload["book_used_for_decision_source"] == "current_fetch"
    assert payload["book_used_for_decision"] == "current_fetch"
    assert payload["book_used_token_pair_match"] is True
    assert payload["empty_book_role"] == "absent"
    assert payload["serialized_book_source"] == "current_fetch"
    assert payload["serialized_yes_no_bid_ask_present"] is True
    assert payload["serialized_depth_present"] is True
    assert payload["serialized_spread_present"] is True
    assert payload["yes_normalization_status"] == "accepted_executable"
    assert payload["no_normalization_status"] == "accepted_executable"
    assert payload["terminal_skip_reason"] is None
    assert payload["terminal_gate_stage"] == "none"
    assert payload["quote_age_ms"] == 700
    assert payload["quote_age_source"] == "current_fetch_raw_timestamp"


def test_orderbook_lineage_probe_distinguishes_cached_available_from_used() -> None:
    trader = _trader()

    payload = trader._build_orderbook_lineage_probe_payload(
        ticker="BTC",
        market_id="pm-5m-btc",
        market_slug="btc-updown-5m",
        condition_id="condition-1",
        yes_token_id="yes-token",
        no_token_id="no-token",
        orderbook_fetch_succeeded=False,
        current_executable_yes_no_book=False,
        orderbook_error="empty_orderbook bids=0 asks=99 token=yes-token",
        orderbook_readiness_reason="empty_book",
        orderbook_refresh_detail={
            "decision_token_pair_key": "condition-1|yes-token|no-token|btc-updown-5m",
            "last_successful_yes_no_book_token_pair_key": "condition-1|yes-token|no-token|btc-updown-5m",
            "last_successful_yes_no_book_at": "2026-05-28T00:00:00Z",
            "orderbook_lineage_match": True,
            "orderbook_current_fetch_status": "fresh_fetch_failed",
            "orderbook_stale_reuse_source": "CURRENT_FETCH_FAILED_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR",
            "executable_book_last_seen_age_ms": 4500,
        },
        terminal_blocker_reason="empty_book",
        terminal_blocker_stage="market_data_orderbook",
    )

    assert payload["current_fetch_status"] == "fresh_fetch_failed"
    assert payload["yes_fetch_status"] == "fetch_failed"
    assert payload["no_fetch_status"] == "fetch_failed"
    assert payload["cached_executable_book_available"] is True
    assert payload["cache_token_pair_match"] is True
    assert payload["cached_book_used_for_decision"] is False
    assert payload["book_used_for_decision_source"] == "none"
    assert payload["book_used_for_decision"] == "unavailable"
    assert payload["book_used_token_pair_match"] is True
    assert payload["terminal_blocker"] == "empty_book"
    assert payload["terminal_skip_reason"] == "empty_book"
    assert payload["terminal_gate_stage"] == "market_data"
    assert payload["contextual_blockers"] == ["empty_book"]
    assert payload["empty_book_role"] == "terminal"
    assert payload["serialized_book_source"] == "not_serialized"
    assert payload["serialized_yes_no_bid_ask_present"] is False
    assert payload["serialized_depth_present"] is False
    assert payload["serialized_spread_present"] is False
    assert payload["yes_normalization_status"] == "unknown"
    assert payload["no_normalization_status"] == "unknown"
    assert payload["quote_age_ms"] == 4500
    assert payload["quote_age_source"] == "last_successful_yes_no_book_cache"


def test_orderbook_lineage_probe_fails_soft_with_missing_fields() -> None:
    trader = _trader()

    payload = trader._build_orderbook_lineage_probe_payload(ticker="BTC")

    assert payload["asset"] == "BTC"
    assert payload["current_fetch_status"] == "unknown"
    assert payload["yes_fetch_status"] == "unknown"
    assert payload["no_fetch_status"] == "unknown"
    assert payload["quote_age_ms"] is None
    assert payload["book_used_for_decision_source"] == "unknown"
    assert payload["book_used_for_decision"] == "unknown"
    assert payload["empty_book_role"] == "unknown"
    assert payload["serialized_book_source"] == "unknown"
    assert payload["terminal_skip_reason"] is None
    assert payload["terminal_gate_stage"] == "unknown"
    assert payload["yes_normalization_status"] == "unknown"
    assert payload["no_normalization_status"] == "unknown"


def test_orderbook_lineage_probe_marks_contextual_empty_book_role() -> None:
    trader = _trader()

    payload = trader._build_orderbook_lineage_probe_payload(
        ticker="BTC",
        yes_ob=_ob(token_id="yes-token", bid=0.44, ask=0.46, bid_size=12, ask_size=10, age_ms=900),
        no_ob=_ob(token_id="no-token", bid=0.54, ask=0.56, bid_size=9, ask_size=8, age_ms=1100),
        yes_bid=0.44,
        yes_ask=0.46,
        no_bid=0.54,
        no_ask=0.56,
        yes_orderbook_age_ms=900,
        no_orderbook_age_ms=1100,
        orderbook_fetch_succeeded=True,
        current_executable_yes_no_book=True,
        orderbook_refresh_detail={"orderbook_current_fetch_status": "fresh_fetch_executable"},
        contextual_blockers=["empty_book"],
        terminal_blocker_reason="delta_extreme",
        terminal_blocker_stage="ev",
    )

    assert payload["empty_book_role"] == "contextual"
    assert payload["terminal_skip_reason"] == "delta_extreme"
    assert payload["terminal_gate_stage"] == "ev"


def test_emit_orderbook_lineage_probe_is_fail_soft() -> None:
    trader = _trader()
    trader._emit_quant_event = MagicMock(side_effect=RuntimeError("jsonl down"))

    assert trader._emit_orderbook_lineage_probe(ticker="BTC") is False


def test_quant_event_logger_routes_orderbook_lineage_probe_to_category() -> None:
    logger = QuantEventLogger(enabled=False)

    assert logger.log_orderbook_lineage_probe({"asset": "BTC"}) is False
    assert logger._CATEGORY_BY_METHOD["orderbook_lineage_probe"] == "orderbook_lineage"
