"""Tests for polymarket/observability/trader_orderbook_lineage.py.

Verifies pure helper output, edge cases, error classification, and 
equivalence between the PolymarketTrader wrapper and the extracted helpers.
"""
from __future__ import annotations

from types import SimpleNamespace
import pytest

from polymarket.trader import PolymarketTrader
from polymarket.observability.trader_orderbook_lineage import (
    orderbook_lineage_side_status,
    orderbook_lineage_current_fetch_status,
    build_orderbook_lineage_probe_payload,
    orderbook_age_ms,
    is_empty_orderbook_error,
)


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


def test_orderbook_lineage_side_status() -> None:
    trader = _trader()
    # ob is None cases
    assert orderbook_lineage_side_status(trader, ob=None, bid=0, ask=0, current_fetch_status="fresh_fetch_failed") == "fetch_failed"
    assert orderbook_lineage_side_status(trader, ob=None, bid=0, ask=0, current_fetch_status="fresh_fetch_not_attempted") == "not_attempted"
    assert orderbook_lineage_side_status(trader, ob=None, bid=0, ask=0, current_fetch_status="other") == "unknown"

    # error cases
    assert orderbook_lineage_side_status(trader, ob=object(), bid=0.5, ask=0.6, current_fetch_status="fresh_fetch_executable", orderbook_error="stale_orderbook") == "stale"
    assert orderbook_lineage_side_status(trader, ob=object(), bid=0.5, ask=0.6, current_fetch_status="fresh_fetch_executable", orderbook_error="invalid_orderbook") == "invalid"

    # bid/ask values cases
    ob_obj = object()
    assert orderbook_lineage_side_status(trader, ob=ob_obj, bid=0.5, ask=0.6, current_fetch_status="fresh_fetch_executable") == "executable"
    assert orderbook_lineage_side_status(trader, ob=ob_obj, bid=0.0, ask=0.0, current_fetch_status="fresh_fetch_executable") == "both_sides_empty"
    assert orderbook_lineage_side_status(trader, ob=ob_obj, bid=0.0, ask=0.5, current_fetch_status="fresh_fetch_executable") == "one_sided_empty_bids"
    assert orderbook_lineage_side_status(trader, ob=ob_obj, bid=0.5, ask=0.0, current_fetch_status="fresh_fetch_executable") == "one_sided_empty_asks"


def test_orderbook_lineage_current_fetch_status() -> None:
    detail = {"orderbook_current_fetch_status": "fresh_fetch_not_attempted_or_unobserved"}
    assert orderbook_lineage_current_fetch_status(detail, None, False) == "fresh_fetch_not_attempted"

    detail_custom = {"orderbook_current_fetch_status": "my_custom_status"}
    assert orderbook_lineage_current_fetch_status(detail_custom, None, False) == "my_custom_status"

    assert orderbook_lineage_current_fetch_status({}, True, True) == "fresh_fetch_executable"
    assert orderbook_lineage_current_fetch_status({}, True, False) == "fresh_fetch_non_executable"
    assert orderbook_lineage_current_fetch_status({}, False, False) == "fresh_fetch_failed"
    assert orderbook_lineage_current_fetch_status({}, None, False) == "unknown"


def test_orderbook_age_ms() -> None:
    snap = SimpleNamespace(age_seconds=1.25)
    assert orderbook_age_ms(snap) == 1250

    snap_none = SimpleNamespace(age_seconds=None)
    assert orderbook_age_ms(snap_none) == 0

    assert orderbook_age_ms(None) == 0


def test_is_empty_orderbook_error() -> None:
    assert is_empty_orderbook_error("empty_orderbook") is True
    assert is_empty_orderbook_error("empty_book") is True
    assert is_empty_orderbook_error("clob_empty_response") is True
    assert is_empty_orderbook_error("some random error") is False


def test_payload_builder_equivalence_and_fidelity() -> None:
    trader = _trader()
    yes_ob = _ob(token_id="yes-token", bid=0.44, ask=0.46, bid_size=12, ask_size=10, age_ms=900)
    no_ob = _ob(token_id="no-token", bid=0.54, ask=0.56, bid_size=9, ask_size=8, age_ms=1100)

    kwargs = {
        "ticker": "BTC",
        "market_id": "pm-5m-btc",
        "market_slug": "btc-updown-5m",
        "condition_id": "condition-1",
        "yes_token_id": "yes-token",
        "no_token_id": "no-token",
        "yes_ob": yes_ob,
        "no_ob": no_ob,
        "yes_bid": 0.44,
        "yes_ask": 0.46,
        "yes_bid_size": 12,
        "yes_ask_size": 10,
        "no_bid": 0.54,
        "no_ask": 0.56,
        "no_bid_size": 9,
        "no_ask_size": 8,
        "yes_orderbook_age_ms": 900,
        "no_orderbook_age_ms": 1100,
        "orderbook_fetch_succeeded": True,
        "current_executable_yes_no_book": True,
        "orderbook_refresh_detail": {
            "decision_token_pair_key": "condition-1|yes-token|no-token|btc-updown-5m",
            "orderbook_current_fetch_status": "fresh_fetch_executable",
            "orderbook_stale_reuse_source": "CURRENT_DECISION_FETCH_EXECUTABLE",
        },
        "fetch_attempt_ts": "2026-05-28T00:00:00.100Z",
        "fetch_complete_ts": "2026-05-28T00:00:00.112Z",
        "fetch_duration_ms": 12.0,
        "lifecycle_phase": "OPENING_SCAN",
        "seconds_remaining": 180,
    }

    # Verify helper payload and wrapper payload are identical
    payload_wrapper = trader._build_orderbook_lineage_probe_payload(**kwargs)
    payload_helper = build_orderbook_lineage_probe_payload(trader, **kwargs)

    assert payload_wrapper == payload_helper
    assert payload_helper["probe_id"] == "ORDERBOOK_LINEAGE_PROBE_V1"
    assert payload_helper["schema_version"] == "orderbook_lineage_probe_v1"
