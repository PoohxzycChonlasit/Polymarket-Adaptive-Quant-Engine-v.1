"""Tests for polymarket/observability/trader_orderbook_details.py.

Verifies pure helper output, edge cases, and golden equivalence between the
PolymarketTrader wrappers and the extracted helper functions.
"""
from __future__ import annotations

import pytest

from polymarket.client import ClobOrderbookError
from polymarket.trader import PolymarketTrader
from polymarket.observability.trader_orderbook_details import (
    empty_book_recovery_detail,
    infer_clob_orderbook_error_category,
)

_EXPECTED_KEYS = {
    "empty_book_recovery_attempted",
    "empty_book_recovery_success",
    "empty_book_recovery_failed",
    "empty_book_recovery_retry_count",
    "liquidity_state",
    "empty_book_recovery_research_mode",
    "liquidity_recovery_grace_entered",
    "liquidity_recovery_grace_success",
    "liquidity_recovery_grace_failed",
    "recovery_wait_seconds",
    "recovered_before_cutoff",
    "candidate_survived_recovery",
    "recovery_exit_reason",
    "recovery_branch_candidate_seen",
    "recovery_branch_preempted_by_cutoff",
    "recovery_branch_skipped_reason",
    "recovery_branch_mode_disabled",
    "recovery_branch_enter_condition_failed",
}


# ---------------------------------------------------------------------------
# empty_book_recovery_detail
# ---------------------------------------------------------------------------


def test_empty_book_recovery_detail_has_all_keys() -> None:
    result = empty_book_recovery_detail()
    assert set(result.keys()) == _EXPECTED_KEYS


def test_empty_book_recovery_detail_defaults() -> None:
    result = empty_book_recovery_detail()
    assert result["liquidity_state"] == "HEALTHY"
    assert result["empty_book_recovery_attempted"] is False
    assert result["empty_book_recovery_success"] is False
    assert result["empty_book_recovery_failed"] is False
    assert result["empty_book_recovery_retry_count"] == 0
    assert result["empty_book_recovery_research_mode"] is False
    assert result["liquidity_recovery_grace_entered"] is False
    assert result["liquidity_recovery_grace_success"] is False
    assert result["liquidity_recovery_grace_failed"] is False
    assert result["recovery_wait_seconds"] == 0.0
    assert result["recovered_before_cutoff"] is False
    assert result["candidate_survived_recovery"] is False
    assert result["recovery_exit_reason"] == ""
    assert result["recovery_branch_candidate_seen"] is False
    assert result["recovery_branch_preempted_by_cutoff"] is False
    assert result["recovery_branch_skipped_reason"] == ""
    assert result["recovery_branch_mode_disabled"] is False
    assert result["recovery_branch_enter_condition_failed"] is False


def test_empty_book_recovery_detail_custom_liquidity_state() -> None:
    result = empty_book_recovery_detail(liquidity_state="EXHAUSTED")
    assert result["liquidity_state"] == "EXHAUSTED"
    # all other boolean/numeric fields unchanged
    assert result["empty_book_recovery_attempted"] is False
    assert result["recovery_wait_seconds"] == 0.0
    assert result["recovery_exit_reason"] == ""


def test_empty_book_recovery_detail_returns_new_dict_each_call() -> None:
    a = empty_book_recovery_detail()
    b = empty_book_recovery_detail()
    assert a is not b


# ---------------------------------------------------------------------------
# infer_clob_orderbook_error_category
# ---------------------------------------------------------------------------


def test_infer_structured_error_returns_category() -> None:
    err = ClobOrderbookError("clob_timeout", "timed out waiting for orderbook")
    assert infer_clob_orderbook_error_category(err) == "clob_timeout"


def test_infer_structured_error_any_category() -> None:
    for cat in ("clob_http_error", "clob_rate_limited", "clob_parse_error", "clob_empty_response"):
        err = ClobOrderbookError(cat, "msg")
        assert infer_clob_orderbook_error_category(err) == cat


def test_infer_none_returns_empty() -> None:
    assert infer_clob_orderbook_error_category(None) == ""


def test_infer_empty_string_returns_empty() -> None:
    assert infer_clob_orderbook_error_category("") == ""


def test_infer_empty_orderbook_text_returns_empty() -> None:
    assert infer_clob_orderbook_error_category("empty_orderbook detected") == ""
    assert infer_clob_orderbook_error_category("invalid_orderbook received") == ""
    assert infer_clob_orderbook_error_category("stale_orderbook fallback") == ""


def test_infer_timeout() -> None:
    assert infer_clob_orderbook_error_category("connection timeout") == "clob_timeout"
    assert infer_clob_orderbook_error_category("request timed out after 30s") == "clob_timeout"


def test_infer_rate_limited() -> None:
    assert infer_clob_orderbook_error_category("429 too many requests") == "clob_rate_limited"
    assert infer_clob_orderbook_error_category("rate limit exceeded") == "clob_rate_limited"


def test_infer_auth_issue() -> None:
    assert infer_clob_orderbook_error_category("401 unauthorized") == "clob_auth_or_client_issue"
    assert infer_clob_orderbook_error_category("403 forbidden") == "clob_auth_or_client_issue"


def test_infer_token_not_found() -> None:
    assert infer_clob_orderbook_error_category("404 not found") == "clob_token_not_found"
    assert infer_clob_orderbook_error_category("unknown token id") == "clob_token_not_found"
    assert infer_clob_orderbook_error_category("invalid token") == "clob_token_not_found"


def test_infer_not_connected() -> None:
    assert infer_clob_orderbook_error_category("client not connected") == "clob_client_not_connected"
    assert infer_clob_orderbook_error_category("client_not_connected") == "clob_client_not_connected"


def test_infer_parse_error() -> None:
    assert infer_clob_orderbook_error_category("parse_orderbook_failed") == "clob_parse_error"
    assert infer_clob_orderbook_error_category("malformed json response") == "clob_parse_error"


def test_infer_empty_orderbook_response() -> None:
    # The "empty_orderbook_response" branch is unreachable via string matching:
    # any text containing "empty_orderbook_response" also contains "empty_orderbook"
    # which is checked first and returns "". Verify the actual behavior.
    assert infer_clob_orderbook_error_category("empty_orderbook_response") == ""
    assert infer_clob_orderbook_error_category("clob_empty_response") == ""


def test_infer_http_error() -> None:
    assert infer_clob_orderbook_error_category("http connection error") == "clob_http_error"
    assert infer_clob_orderbook_error_category("api call failed") == "clob_http_error"
    assert infer_clob_orderbook_error_category("status 503") == "clob_http_error"


def test_infer_unknown_returns_empty() -> None:
    assert infer_clob_orderbook_error_category("some unexpected error text") == ""


# ---------------------------------------------------------------------------
# Golden equivalence: wrapper == extracted function
# ---------------------------------------------------------------------------


def _trader_instance() -> PolymarketTrader:
    return PolymarketTrader.__new__(PolymarketTrader)


def test_golden_empty_book_recovery_detail_default() -> None:
    trader = _trader_instance()
    wrapper_result = PolymarketTrader._empty_book_recovery_detail()
    extracted_result = empty_book_recovery_detail()
    assert wrapper_result == extracted_result


def test_golden_empty_book_recovery_detail_custom_state() -> None:
    for state in ("HEALTHY", "EXHAUSTED", "GRACE", "RECOVERING", ""):
        wrapper_result = PolymarketTrader._empty_book_recovery_detail(liquidity_state=state)
        extracted_result = empty_book_recovery_detail(liquidity_state=state)
        assert wrapper_result == extracted_result, f"Mismatch for liquidity_state={state!r}"


def test_golden_infer_clob_orderbook_error_category() -> None:
    trader = _trader_instance()
    test_inputs: list[object] = [
        None,
        "",
        "timeout occurred",
        "timed out",
        "429 rate limit",
        "401 unauthorized",
        "404 not found",
        "not connected",
        "parse_orderbook_failed",
        "empty_orderbook_response",
        "http error",
        "empty_orderbook xyz",
        "some random string",
        ClobOrderbookError("clob_timeout", "msg"),
        ClobOrderbookError("clob_rate_limited", "msg"),
        ClobOrderbookError("clob_http_error", "msg"),
    ]
    for inp in test_inputs:
        wrapper_result = trader._infer_clob_orderbook_error_category(inp)
        extracted_result = infer_clob_orderbook_error_category(inp)
        assert wrapper_result == extracted_result, f"Mismatch for input={inp!r}"
