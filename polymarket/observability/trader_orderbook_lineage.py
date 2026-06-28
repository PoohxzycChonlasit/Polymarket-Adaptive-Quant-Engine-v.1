"""Orderbook lineage observability helpers extracted from PolymarketTrader.

Part of TRADER_PHASE3A_ORDERBOOK_LINEAGE_OBSERVABILITY_EXTRACTION_001.
Extracts pure observability payload builders and helper functions to reduce
the size and complexity of polymarket/trader.py.
"""
from __future__ import annotations

import hashlib
from typing import Any

from polymarket.observability.trader_lifecycle_observability import (
    diagnostic_float,
    diagnostic_int,
    orderbook_lineage_compact_text,
    orderbook_lineage_raw_count,
    orderbook_lineage_current_fetch_status,
    orderbook_age_ms,
    is_empty_orderbook_error,
)


def orderbook_lineage_side_status(
    trader: Any,
    *,
    ob: object,
    bid: object,
    ask: object,
    current_fetch_status: str,
    orderbook_error: str = "",
) -> str:
    """Classify the lineage side status (executable, empty, stale, etc.) without mutating state."""
    error = str(orderbook_error or "").lower()
    if ob is None:
        if current_fetch_status == "fresh_fetch_failed":
            return "fetch_failed"
        if current_fetch_status == "fresh_fetch_not_attempted":
            return "not_attempted"
        return "unknown"
    if "stale_orderbook" in error or "stale_book" in error:
        return "stale"
    if "invalid_orderbook" in error:
        return "invalid"
    
    # Use imported diagnostic_float (safe, no side-effects)
    bid_value = diagnostic_float(bid)
    ask_value = diagnostic_float(ask)
    
    if bid_value > 0 and ask_value > 0:
        return "executable"
    if bid_value <= 0 and ask_value <= 0:
        return "both_sides_empty"
    if bid_value <= 0:
        return "one_sided_empty_bids"
    return "one_sided_empty_asks"


def build_orderbook_lineage_probe_payload(
    trader: Any,
    *,
    ticker: str,
    market_id: object = "",
    market_slug: object = "",
    condition_id: object = "",
    yes_token_id: object = "",
    no_token_id: object = "",
    yes_ob: object = None,
    no_ob: object = None,
    yes_bid: object = 0.0,
    yes_ask: object = 0.0,
    yes_bid_size: object = 0.0,
    yes_ask_size: object = 0.0,
    no_bid: object = 0.0,
    no_ask: object = 0.0,
    no_bid_size: object = 0.0,
    no_ask_size: object = 0.0,
    yes_orderbook_age_ms: object = None,
    no_orderbook_age_ms: object = None,
    orderbook_fetch_succeeded: bool | None = None,
    current_executable_yes_no_book: bool = False,
    orderbook_refresh_detail: dict[str, object] | None = None,
    orderbook_readiness_reason: object = "",
    orderbook_error: object = "",
    clob_error_detail: dict[str, object] | None = None,
    empty_book_recovery_detail: dict[str, object] | None = None,
    token_mapping_warning: object = "",
    lifecycle_phase: object = "",
    seconds_remaining: object = None,
    fetch_attempt_ts: object = "",
    fetch_complete_ts: object = "",
    fetch_duration_ms: object = None,
    terminal_blocker_reason: object = "",
    terminal_blocker_stage: object = "",
    contextual_blockers: list[str] | None = None,
) -> dict[str, object]:
    """Construct a standardized orderbook lineage probe payload dictionary."""
    detail = dict(orderbook_refresh_detail or {})
    clob_detail = dict(clob_error_detail or {})
    recovery_detail = dict(empty_book_recovery_detail or {})
    ticker_key = str(ticker or "").upper()
    event_ts = trader._utc_timestamp()
    current_fetch_status = orderbook_lineage_current_fetch_status(
        detail,
        orderbook_fetch_succeeded,
        current_executable_yes_no_book,
    )
    token_pair_key = str(
        detail.get("decision_token_pair_key")
        or trader._orderbook_token_pair_key(
            condition_id=condition_id,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id,
            market_slug=market_slug,
        )
    )
    run_id = str(getattr(getattr(trader, "quant_events", None), "run_id", "") or "")
    lineage_raw = "|".join(
        str(part or "")
        for part in (
            run_id,
            ticker_key,
            token_pair_key,
            fetch_attempt_ts,
            current_fetch_status,
        )
    )
    lineage_id = "oblp_" + hashlib.sha1(lineage_raw.encode("utf-8")).hexdigest()[:12]

    yes_age = diagnostic_int(yes_orderbook_age_ms)
    no_age = diagnostic_int(no_orderbook_age_ms)
    current_ages = [age for age in (yes_age, no_age) if age is not None and age > 0]
    cached_age = diagnostic_int(detail.get("executable_book_last_seen_age_ms"))
    quote_age_ms = max(current_ages) if current_ages and current_fetch_status == "fresh_fetch_executable" else cached_age
    if quote_age_ms is None:
        quote_age_source = "not_available"
    elif current_ages and current_fetch_status == "fresh_fetch_executable":
        quote_age_source = "current_fetch_raw_timestamp"
    else:
        quote_age_source = "last_successful_yes_no_book_cache"

    cached_available = bool(detail.get("last_successful_yes_no_book_at") or cached_age is not None)
    cache_match_raw = detail.get("orderbook_lineage_match")
    cache_token_pair_match = bool(cache_match_raw) if cache_match_raw is not None else None
    book_used_source = "unknown"
    cached_used = False
    if current_fetch_status == "fresh_fetch_executable" and current_executable_yes_no_book:
        book_used_source = "current_fetch"
    elif current_fetch_status in {"fresh_fetch_failed", "fresh_fetch_non_executable", "fresh_fetch_not_attempted"}:
        book_used_source = "none"

    contextual = list(contextual_blockers or [])
    readiness = str(orderbook_readiness_reason or "").strip()
    if readiness and readiness not in contextual:
        contextual.append(readiness)
    token_warning = str(token_mapping_warning or "").strip()
    if token_warning and "token_mapping_warning" not in contextual:
        contextual.append("token_mapping_warning")

    error_text = orderbook_lineage_compact_text(orderbook_error)
    error_type = str(
        clob_detail.get("clob_error_category")
        or clob_detail.get("clob_exception_type")
        or ("orderbook_error" if error_text else "")
    )
    terminal = str(terminal_blocker_reason or "").strip()
    terminal_stage_raw = str(terminal_blocker_stage or "").strip()
    terminal_gate_stage = "unknown"
    if terminal:
        terminal_gate_stage = "market_data" if terminal_stage_raw.startswith("market_data") else terminal_stage_raw or "unknown"
    elif current_fetch_status != "unknown":
        terminal_gate_stage = "none"

    yes_fetch_status = orderbook_lineage_side_status(
        trader,
        ob=yes_ob,
        bid=yes_bid,
        ask=yes_ask,
        current_fetch_status=current_fetch_status,
        orderbook_error=error_text,
    )
    no_fetch_status = orderbook_lineage_side_status(
        trader,
        ob=no_ob,
        bid=no_bid,
        ask=no_ask,
        current_fetch_status=current_fetch_status,
        orderbook_error=error_text,
    )

    def normalization_status_for(side_status: str) -> str:
        return {
            "executable": "accepted_executable",
            "one_sided_empty_bids": "rejected_empty_bids",
            "one_sided_empty_asks": "rejected_empty_asks",
            "both_sides_empty": "rejected_empty_both",
            "stale": "rejected_stale",
            "invalid": "rejected_invalid_price",
            "not_attempted": "not_attempted",
        }.get(side_status, "unknown")

    serialized_yes_no_bid_ask_present = bool(current_executable_yes_no_book)
    serialized_book_source = (
        "current_fetch"
        if book_used_source == "current_fetch"
        else "not_serialized"
        if book_used_source == "none"
        else "unknown"
    )
    book_used_for_decision = (
        "current_fetch"
        if book_used_source == "current_fetch"
        else "unavailable"
        if book_used_source == "none"
        else "unknown"
    )
    book_used_token_pair_match = (
        bool(token_pair_key)
        if book_used_source == "current_fetch"
        else cache_token_pair_match
        if book_used_source == "none"
        else None
    )
    contextual_lower = {str(value or "").lower() for value in contextual}
    terminal_lower = terminal.lower()
    if "empty_book" in terminal_lower or "empty_orderbook" in terminal_lower:
        empty_book_role = "terminal"
    elif any("empty_book" in value or "empty_orderbook" in value for value in contextual_lower):
        empty_book_role = "contextual"
    elif current_fetch_status == "unknown" and not readiness:
        empty_book_role = "unknown"
    else:
        empty_book_role = "absent"

    return {
        "probe_id": "ORDERBOOK_LINEAGE_PROBE_V1",
        "schema_version": "orderbook_lineage_probe_v1",
        "event_type": "orderbook_lineage_probe",
        "event_ts": event_ts,
        "producer": "trader.orderbook_lineage_probe",
        "probe_scope": "decision_cycle_fetch",
        "latency_truth_level": "proxy",
        "timestamp_source": "runtime_utc_clock",
        "probe_authority_level": "evidence_only",
        "policy_authority": "none",
        "runtime_decision_authority": False,
        "execution_authority": False,
        "risk_authority": False,
        "asset": ticker_key,
        "ticker": ticker_key,
        "market_id": str(market_id or ""),
        "market_slug": str(market_slug or ""),
        "condition_id": str(condition_id or ""),
        "yes_token_id": str(yes_token_id or ""),
        "no_token_id": str(no_token_id or ""),
        "token_id": str(yes_token_id or ""),
        "outcome": "YES/NO",
        "orderbook_token_pair_key": token_pair_key,
        "orderbook_lineage_id": lineage_id,
        "fetch_attempt_ts": str(fetch_attempt_ts or ""),
        "fetch_complete_ts": str(fetch_complete_ts or ""),
        "fetch_duration_ms": diagnostic_float(fetch_duration_ms, default=0.0) if fetch_duration_ms is not None else None,
        "current_fetch_status": current_fetch_status,
        "current_fetch_succeeded": orderbook_fetch_succeeded,
        "current_fetch_error_type": error_type,
        "current_fetch_error_message": error_text,
        "yes_fetch_status": yes_fetch_status,
        "no_fetch_status": no_fetch_status,
        "yes_bids_count": orderbook_lineage_raw_count(yes_ob, "top_bids"),
        "yes_asks_count": orderbook_lineage_raw_count(yes_ob, "top_asks"),
        "no_bids_count": orderbook_lineage_raw_count(no_ob, "top_bids"),
        "no_asks_count": orderbook_lineage_raw_count(no_ob, "top_asks"),
        "yes_best_bid": diagnostic_float(yes_bid),
        "yes_best_ask": diagnostic_float(yes_ask),
        "yes_best_bid_size": diagnostic_float(yes_bid_size),
        "yes_best_ask_size": diagnostic_float(yes_ask_size),
        "no_best_bid": diagnostic_float(no_bid),
        "no_best_ask": diagnostic_float(no_ask),
        "no_best_bid_size": diagnostic_float(no_bid_size),
        "no_best_ask_size": diagnostic_float(no_ask_size),
        "yes_raw_age_ms": yes_age,
        "no_raw_age_ms": no_age,
        "last_successful_yes_no_book_at": str(detail.get("last_successful_yes_no_book_at") or ""),
        "last_successful_yes_no_book_age_ms": cached_age,
        "last_successful_yes_no_book_token_pair_key": str(detail.get("last_successful_yes_no_book_token_pair_key") or ""),
        "cache_token_pair_match": cache_token_pair_match,
        "cached_executable_book_available": cached_available,
        "cached_book_used_for_decision": cached_used,
        "cache_reuse_reason": str(detail.get("orderbook_stale_reuse_source") or ""),
        "book_used_for_decision_source": book_used_source,
        "book_used_for_decision_token_pair_key": token_pair_key if book_used_source == "current_fetch" else "",
        "book_used_for_decision": book_used_for_decision,
        "book_used_token_pair_match": book_used_token_pair_match,
        "normalization_status": "accepted" if current_executable_yes_no_book else "not_executable",
        "yes_normalization_status": normalization_status_for(yes_fetch_status),
        "no_normalization_status": normalization_status_for(no_fetch_status),
        "serialized_truth_source": (
            "current_fetch_yes_no_top_of_book"
            if current_executable_yes_no_book
            else "unavailable_or_non_executable"
        ),
        "serialized_book_source": serialized_book_source,
        "serialized_yes_no_bid_ask_present": serialized_yes_no_bid_ask_present,
        "serialized_depth_present": bool(serialized_yes_no_bid_ask_present),
        "serialized_spread_present": bool(serialized_yes_no_bid_ask_present),
        "orderbook_readiness_reason": readiness,
        "orderbook_unavailable_reason": readiness,
        "liquidity_state": str(recovery_detail.get("liquidity_state") or ""),
        "terminal_blocker": terminal,
        "terminal_blocker_stage": terminal_stage_raw,
        "terminal_skip_reason": terminal or None,
        "terminal_gate_stage": terminal_gate_stage,
        "contextual_blockers": contextual,
        "empty_book_role": empty_book_role,
        "quote_age_ms": quote_age_ms,
        "quote_age_source": quote_age_source,
        "quote_age_truth_level": "current_fetch" if quote_age_source == "current_fetch_raw_timestamp" else "proxy" if quote_age_ms is not None else "unknown",
        "lifecycle_phase": str(lifecycle_phase or ""),
        "seconds_remaining": diagnostic_int(seconds_remaining),
        "lineage_confidence": "DIRECT" if token_pair_key else "UNKNOWN",
        "source_module": "polymarket.trader",
    }
