from __future__ import annotations

from polymarket.client import ClobOrderbookError


def empty_book_recovery_detail(*, liquidity_state: str = "HEALTHY") -> dict[str, object]:
    return {
        "empty_book_recovery_attempted": False,
        "empty_book_recovery_success": False,
        "empty_book_recovery_failed": False,
        "empty_book_recovery_retry_count": 0,
        "liquidity_state": liquidity_state,
        "empty_book_recovery_research_mode": False,
        "liquidity_recovery_grace_entered": False,
        "liquidity_recovery_grace_success": False,
        "liquidity_recovery_grace_failed": False,
        "recovery_wait_seconds": 0.0,
        "recovered_before_cutoff": False,
        "candidate_survived_recovery": False,
        "recovery_exit_reason": "",
        "recovery_branch_candidate_seen": False,
        "recovery_branch_preempted_by_cutoff": False,
        "recovery_branch_skipped_reason": "",
        "recovery_branch_mode_disabled": False,
        "recovery_branch_enter_condition_failed": False,
    }


def infer_clob_orderbook_error_category(error: object) -> str:
    if isinstance(error, ClobOrderbookError):
        return error.category
    text = str(error or "").lower()
    if not text:
        return ""
    if "empty_orderbook" in text or "invalid_orderbook" in text or "stale_orderbook" in text:
        return ""
    if "timeout" in text or "timed out" in text:
        return "clob_timeout"
    if "429" in text or "rate limit" in text or "too many requests" in text:
        return "clob_rate_limited"
    if "401" in text or "403" in text or "unauthorized" in text or "forbidden" in text:
        return "clob_auth_or_client_issue"
    if "400" in text or "404" in text or "not found" in text or "unknown token" in text or "invalid token" in text:
        return "clob_token_not_found"
    if "not connected" in text or "not installed" in text or "client_not_connected" in text:
        return "clob_client_not_connected"
    if "parse_orderbook_failed" in text or "malformed" in text:
        return "clob_parse_error"
    if "empty_orderbook_response" in text:
        return "clob_empty_response"
    if "http" in text or "api" in text or "status" in text:
        return "clob_http_error"
    return ""
