"""Phase-2 lifecycle/observability builder helpers extracted from PolymarketTrader.

Pure functions (no self.*) are standalone; functions that need trader state
accept ``trader: Any`` and call back via trader method delegation.
``_p2_val_avail`` mirrors ``TraderObservabilityHelper._phase2_value_available``
inline to avoid importing the orchestration layer.
"""
from __future__ import annotations

from typing import Any

from polymarket.observability.trader_lifecycle_observability import (
    diagnostic_float,
    diagnostic_int,
    phase2_elapsed_second,
)


def _p2_val_avail(value: object) -> bool:
    """Mirror of TraderObservabilityHelper._phase2_value_available."""
    return value is not None and value != ""


# ---------------------------------------------------------------------------
# Tier 1 — completely pure (no imports needed beyond stdlib)
# ---------------------------------------------------------------------------


def phase2_book_state_level(state: object) -> int:
    levels = {
        "DISCOVERED": 0,
        "UNKNOWN": 0,
        "TOKEN_READY": 1,
        "BOOK_SEEN": 2,
        "NONZERO_BOOK": 3,
        "SPREAD_NORMALIZED": 4,
        "EXECUTABLE": 5,
        "TRADABLE": 5,
    }
    return levels.get(str(state or "").upper().strip(), -1)


def phase2_pre_model_gate_detail(
    *,
    skip_reason: object = "",
    orderbook_readiness_reason: object = "",
    liquidity_state: object = "",
    spread_normalized: object = None,
    readiness_state: object = "",
    lifecycle_phase: object = "",
    probability_available: bool = False,
) -> dict[str, object]:
    if probability_available:
        return {
            "pre_model_gate_name": "MODEL_OUTPUT_AVAILABLE",
            "pre_model_gate_group": "MODEL_READY",
            "pre_model_gate_reason": "model_output_visible",
            "pre_model_gate_source": "probability_output",
            "pre_model_gate_blocks_probability_model": False,
            "probability_model_call_path": "probability_model_output_serialized",
        }

    reason_text = str(skip_reason or "").strip()
    orderbook_text = str(orderbook_readiness_reason or "").strip()
    readiness_text = str(readiness_state or "").strip()
    liquidity_text = str(liquidity_state or "").strip()
    lifecycle_text = str(lifecycle_phase or "").strip().upper()
    combined = " ".join(
        part.lower()
        for part in (reason_text, orderbook_text, readiness_text, liquidity_text, lifecycle_text)
        if part
    )

    gate_name = "MODEL_GATE_UNKNOWN"
    gate_group = "MODEL_GATE_UNKNOWN"
    source = "unclassified"
    if any(token in combined for token in ("hard_close", "time_unsafe", "cutoff", "entry timing", "late_hard_close_zone")):
        gate_name = "TIME_CUTOFF_GATE"
        gate_group = "TIME_CUTOFF_GATE"
        source = "time_or_cutoff"
    elif lifecycle_text in {"FINAL_DERISK", "CLOSED_OR_UNSAFE"}:
        gate_name = "LIFECYCLE_PHASE_GATE"
        gate_group = "LIFECYCLE_PHASE_GATE"
        source = "lifecycle_phase"
    elif any(token in combined for token in ("stale_feed", "feed", "oracle", "data_stale")):
        gate_name = "DATA_FRESHNESS_GATE"
        gate_group = "DATA_FRESHNESS_GATE"
        source = "market_data_freshness"
    elif any(token in combined for token in ("token_mapping", "missing_token", "token_not_ready", "api_missing_fields", "missing token")):
        gate_name = "TOKEN_MAPPING_GATE"
        gate_group = "ORDERBOOK_GATE"
        source = "token_mapping"
    elif any(token in combined for token in ("orderbook", "empty_book", "warmup", "clob_", "bid/ask", "no_orderbook", "unavailable")):
        gate_name = "ORDERBOOK_COMPLETENESS_GATE"
        gate_group = "ORDERBOOK_GATE"
        source = "orderbook_readiness"
    elif spread_normalized is False or "spread" in combined:
        gate_name = "SPREAD_GATE"
        gate_group = "SPREAD_GATE"
        source = "spread_readiness"
    elif liquidity_text.upper() not in {"", "HEALTHY", "READY", "UNKNOWN"} or "liquidity" in combined or "min shares" in combined:
        gate_name = "LIQUIDITY_GATE"
        gate_group = "LIQUIDITY_GATE"
        source = "liquidity_readiness"
    elif any(token in combined for token in ("max entries", "max 1", "frequency", "cooldown")):
        gate_name = "ENTRY_FREQUENCY_GATE"
        gate_group = "ENTRY_FREQUENCY_GATE"
        source = "entry_frequency"
    elif any(token in combined for token in ("max active", "max position", "position limit")):
        gate_name = "ENTRY_CAPACITY_GATE"
        gate_group = "ENTRY_CAPACITY_GATE"
        source = "entry_capacity"
    elif any(token in combined for token in ("panic sell", "panic_sold")):
        gate_name = "PANIC_COOLDOWN_GATE"
        gate_group = "RUNTIME_SAFETY_GATE"
        source = "panic_cooldown"
    elif "risk_plan_zero" in combined or "zero position" in combined:
        gate_name = "MODEL_GATE_UNKNOWN"
        gate_group = "MODEL_GATE_UNKNOWN"
        source = "post_model_risk_plan_or_unknown"
    elif any(token in combined for token in ("risk", "floor", "balance", "drawdown", "lockdown", "reconciliation")):
        gate_name = "RISK_SAFETY_GATE"
        gate_group = "RUNTIME_SAFETY_GATE"
        source = "runtime_safety"

    reason = orderbook_text or reason_text or readiness_text or liquidity_text or "model_gate_unknown"
    return {
        "pre_model_gate_name": gate_name,
        "pre_model_gate_group": gate_group,
        "pre_model_gate_reason": reason,
        "pre_model_gate_source": source,
        "pre_model_gate_blocks_probability_model": gate_name != "MODEL_GATE_UNKNOWN",
        "probability_model_call_path": (
            "blocked_before_probability_model"
            if gate_name != "MODEL_GATE_UNKNOWN"
            else "probability_model_call_path_unknown"
        ),
    }


def phase2_ev_null_reason(
    *,
    field_name: str,
    skip_reason: object = "",
    orderbook_readiness_reason: object = "",
    liquidity_state: object = "",
    spread_normalized: object = None,
    probability_available: bool = False,
    market_price_available: bool = False,
    ev_available: bool = False,
) -> str:
    reason = str(skip_reason or "").lower()
    orderbook_reason = str(orderbook_readiness_reason or "").lower()
    liquidity = str(liquidity_state or "").upper()
    if "empty_book" in orderbook_reason or "empty_book" in reason:
        return "empty_book"
    if orderbook_reason or "orderbook" in reason or "warmup" in reason:
        return "no_orderbook"
    if "time_unsafe" in reason or "cutoff" in reason:
        return "time_unsafe"
    if liquidity and liquidity not in {"HEALTHY", "UNKNOWN"}:
        return "liquidity_not_ready"
    if spread_normalized is False or "spread" in reason:
        return "spread_not_ready"
    if "risk" in reason or "balance" in reason or "drawdown" in reason or "lockdown" in reason:
        return "risk_blocked_after_ev" if ev_available or probability_available else "candidate_blocked_before_ev"
    if field_name == "market_price":
        return "no_market_price"
    if field_name == "ev_after_spread":
        if not probability_available:
            return "no_probability_model_output"
        if not market_price_available:
            return "no_market_price"
        return "candidate_blocked_before_ev"
    if field_name in {"fair_value", "true_probability"}:
        return "no_probability_model_output"
    return "candidate_blocked_before_ev"


# ---------------------------------------------------------------------------
# Tier 2 — pure with sibling/lifecycle imports; no trader arg
# ---------------------------------------------------------------------------


def phase2_ev_null_reason_detail(
    *,
    fair_value: object,
    market_price: object,
    true_probability: object,
    ev_after_spread: object,
    skip_reason: object = "",
    orderbook_readiness_reason: object = "",
    liquidity_state: object = "",
    spread_normalized: object = None,
) -> dict[str, object]:
    fair_value_available = _p2_val_avail(fair_value)
    market_price_available = _p2_val_avail(market_price)
    true_probability_available = _p2_val_avail(true_probability)
    ev_after_spread_available = _p2_val_avail(ev_after_spread)
    probability_available = fair_value_available or true_probability_available

    skip_text = str(skip_reason or "").lower()
    orderbook_text = str(orderbook_readiness_reason or "").lower()
    pre_model_block = (
        "time_unsafe" in skip_text
        or "cutoff" in skip_text
        or "orderbook" in skip_text
        or "warmup" in skip_text
        or "empty_book" in skip_text
        or bool(orderbook_text)
    )
    if probability_available:
        probability_model_stage = "probability_model_output"
    elif pre_model_block:
        probability_model_stage = "pre_model_skip"
    else:
        probability_model_stage = "no_probability_model_output"

    if ev_after_spread_available:
        ev_calculation_stage = "ev_calculated"
    elif probability_model_stage == "pre_model_skip":
        ev_calculation_stage = "pre_model_skip"
    elif probability_available and not market_price_available:
        ev_calculation_stage = "no_market_price"
    else:
        ev_calculation_stage = "candidate_blocked_before_ev"

    gate_reason = ""
    if probability_available:
        gate_reason = "model_output_visible"
    elif pre_model_block:
        gate_reason = str(orderbook_readiness_reason or skip_reason or "pre_model_gate").strip()
    else:
        gate_reason = "model_output_not_visible"

    gate_detail = phase2_pre_model_gate_detail(
        skip_reason=skip_reason,
        orderbook_readiness_reason=orderbook_readiness_reason,
        liquidity_state=liquidity_state,
        spread_normalized=spread_normalized,
        probability_available=probability_available,
    )
    known_pre_model_gate = str(gate_detail.get("pre_model_gate_name") or "") not in {
        "",
        "MODEL_GATE_UNKNOWN",
        "MODEL_OUTPUT_AVAILABLE",
    }
    if not probability_available and known_pre_model_gate:
        probability_model_stage = "pre_model_skip"
        if not ev_after_spread_available:
            ev_calculation_stage = "pre_model_skip"
        gate_reason = str(gate_detail.get("pre_model_gate_reason") or gate_reason)
    detail: dict[str, object] = {
        "fair_value_available": fair_value_available,
        "fair_value_null_reason": "",
        "market_price_available": market_price_available,
        "market_price_null_reason": "",
        "true_probability_available": true_probability_available,
        "true_probability_null_reason": "",
        "ev_after_spread_available": ev_after_spread_available,
        "ev_after_spread_null_reason": "",
        "probability_model_stage": probability_model_stage,
        "ev_calculation_stage": ev_calculation_stage,
        "model_attempted": bool(probability_available),
        "probability_model_gate_reason": gate_reason,
        "model_not_run_reason": "" if probability_available else gate_reason,
        "probability_model_called": bool(probability_available),
        "probability_model_output_visible": bool(probability_available),
        "model_output_missing_reason": "" if probability_available else gate_reason,
        "model_output_source": "canonical_probability_fields" if probability_available else "",
        "model_handoff_stage": (
            "MODEL_OUTPUT_SERIALIZED"
            if probability_available
            else "PRE_MODEL_GATE" if pre_model_block or known_pre_model_gate else "MODEL_OUTPUT_NOT_VISIBLE"
        ),
        **gate_detail,
    }
    for field_name, value, available in (
        ("fair_value", fair_value, fair_value_available),
        ("market_price", market_price, market_price_available),
        ("true_probability", true_probability, true_probability_available),
        ("ev_after_spread", ev_after_spread, ev_after_spread_available),
    ):
        if available:
            continue
        detail[f"{field_name}_null_reason"] = phase2_ev_null_reason(
            field_name=field_name,
            skip_reason=skip_reason,
            orderbook_readiness_reason=orderbook_readiness_reason,
            liquidity_state=liquidity_state,
            spread_normalized=spread_normalized,
            probability_available=probability_available,
            market_price_available=market_price_available,
            ev_available=ev_after_spread_available,
        )
    return detail


def phase2_authoritative_orderbook_availability(
    payload: dict[str, object],
) -> tuple[bool, str]:
    yes_bid = diagnostic_float(payload.get("yes_bid"))
    yes_ask = diagnostic_float(payload.get("yes_ask"))
    no_bid = diagnostic_float(payload.get("no_bid"))
    no_ask = diagnostic_float(payload.get("no_ask"))
    bid = diagnostic_float(payload.get("best_bid") or payload.get("bid"))
    ask = diagnostic_float(payload.get("best_ask") or payload.get("ask"))
    if yes_bid > 0 and yes_ask > 0 and no_bid > 0 and no_ask > 0:
        return True, "serialized_yes_no_bid_ask"
    if bid > 0 and ask > 0:
        return True, "serialized_best_bid_ask"

    current_fetch_status = str(payload.get("orderbook_current_fetch_status") or "").strip()
    if current_fetch_status == "fresh_fetch_executable":
        return True, "current_fetch_status_fresh_fetch_executable"

    for key, label in (
        ("executable_book_state", "readiness_bucket_current"),
        ("executable_book_state_best_seen", "readiness_bucket_best_seen"),
    ):
        level = phase2_book_state_level(payload.get(key))
        if level >= 5:
            return True, f"{label}_tradable"
        if level >= 4:
            return True, f"{label}_spread_normalized"
        if level >= 3:
            return True, f"{label}_nonzero_book"

    for key, label in (
        ("first_tradable_ts", "readiness_first_tradable_ts"),
        ("first_spread_normalized_ts", "readiness_first_spread_normalized_ts"),
        ("first_nonzero_bidask_ts", "readiness_first_nonzero_bidask_ts"),
    ):
        if str(payload.get(key) or "").strip():
            return True, label

    if (
        bool(payload.get("orderbook_lineage_match"))
        and str(payload.get("last_successful_yes_no_book_token_pair_key") or "").strip()
        and str(payload.get("decision_token_pair_key") or "").strip()
    ):
        return True, "prior_successful_same_token_pair"
    return False, ""


def phase2_orderbook_state_classification(payload: dict[str, object]) -> str:
    authoritative_available, _source = phase2_authoritative_orderbook_availability(payload)
    reason = str(
        payload.get("orderbook_readiness_reason")
        or payload.get("orderbook_unavailable_reason")
        or payload.get("orderbook_error")
        or ""
    ).lower()
    liquidity = str(payload.get("liquidity_state") or "").upper()
    if "token_mapping" in reason or "token" in reason:
        return "token_mapping_unavailable"
    if "empty_book" in reason or "empty_orderbook" in reason or liquidity == "EMPTY":
        return "empty_book"
    if "warmup" in reason:
        return "warmup_pending"
    if "stale" in reason:
        return "stale_orderbook"
    if reason and authoritative_available and any(
        token in reason
        for token in ("orderbook", "unavailable", "bid/ask", "no_orderbook")
    ):
        return "ready"
    if reason:
        return "orderbook_unavailable"

    yes_bid = diagnostic_float(payload.get("yes_bid"))
    yes_ask = diagnostic_float(payload.get("yes_ask"))
    no_bid = diagnostic_float(payload.get("no_bid"))
    no_ask = diagnostic_float(payload.get("no_ask"))
    bid = diagnostic_float(payload.get("best_bid") or payload.get("bid"))
    ask = diagnostic_float(payload.get("best_ask") or payload.get("ask"))
    if (yes_bid > 0 and yes_ask > 0 and no_bid > 0 and no_ask > 0) or (bid > 0 and ask > 0):
        return "ready"
    if any(value is not None for value in (payload.get("yes_bid"), payload.get("yes_ask"), payload.get("no_bid"), payload.get("no_ask"))):
        return "empty_book"
    if authoritative_available:
        return "ready"
    return "unavailable"


def phase2_candidate_block_detail(payload: dict[str, object]) -> tuple[str, str, str]:
    reason = str(
        payload.get("normalized_skip_reason")
        or payload.get("skip_reason")
        or payload.get("raw_skip_reason")
        or payload.get("orderbook_readiness_reason")
        or payload.get("orderbook_unavailable_reason")
        or payload.get("ev_after_spread_null_reason")
        or payload.get("fair_value_null_reason")
        or ""
    ).strip()
    skipped = bool(payload.get("skipped")) or str(payload.get("decision") or "").lower() in {"skip", "skipped"}
    ev_available = bool(payload.get("ev_after_spread_available")) or _p2_val_avail(payload.get("ev_after_spread"))
    model_output_ready = bool(payload.get("true_probability_available")) or bool(payload.get("fair_value_available"))
    probability_stage = str(payload.get("probability_model_stage") or "").lower()
    ev_stage = str(payload.get("ev_calculation_stage") or "").lower()

    if not reason and not skipped:
        return "not_blocked", "not_blocked", "candidate_active_or_approved"
    if not reason:
        reason = "unavailable"

    if "pre_model_skip" in probability_stage or "candidate_blocked_before_ev" in ev_stage:
        stage = "pre_ev"
    elif "risk_blocked_after_ev" in ev_stage or (skipped and (ev_available or model_output_ready)):
        stage = "post_ev"
    elif skipped:
        stage = "pre_ev"
    else:
        stage = "unavailable"

    reason_lower = reason.lower()
    if any(token in reason_lower for token in ("time_unsafe", "cutoff", "hard_close", "too_late")):
        expiry = "time_unsafe"
    elif any(token in reason_lower for token in ("orderbook", "empty_book", "warmup", "liquidity", "spread", "token")):
        expiry = "market_not_ready"
    elif "risk" in reason_lower or "balance" in reason_lower or "drawdown" in reason_lower or "lockdown" in reason_lower:
        expiry = "risk_block"
    elif reason == "unavailable":
        expiry = "unavailable"
    else:
        expiry = "blocked"
    return reason, stage, expiry


# ---------------------------------------------------------------------------
# Tier 3 — trader: Any (need trader._entry_hard_block_seconds())
# ---------------------------------------------------------------------------


def phase2_market_readiness_state(
    trader: Any, payload: dict[str, object], orderbook_state: str
) -> str:
    reason = str(payload.get("active_window_alignment_reason") or "").lower()
    if reason in {"before_active_window", "late_hard_close_zone"}:
        return reason
    seconds = diagnostic_int(payload.get("seconds_remaining") or payload.get("seconds_until_close"))
    try:
        hard_block = trader._entry_hard_block_seconds()
    except Exception:
        hard_block = 0
    if seconds is not None and seconds <= hard_block:
        return "time_unsafe"

    token_ready = bool(
        payload.get("token_id")
        or payload.get("yes_token_id")
        or payload.get("no_token_id")
        or payload.get("token_ready_at")
    )
    if not token_ready:
        return "token_not_ready"
    if orderbook_state != "ready":
        return orderbook_state

    liquidity = str(payload.get("liquidity_state") or "").upper()
    if liquidity and liquidity not in {"HEALTHY", "READY", "UNKNOWN"}:
        return "liquidity_not_ready"
    spread_ready = payload.get("spread_normalized")
    if spread_ready is False:
        return "spread_not_ready"
    return "ready"


def phase2_model_activation_detail(
    trader: Any,
    payload: dict[str, object],
    *,
    lifecycle_phase: str,
    orderbook_state: str,
    readiness_state: str,
    model_output_ready: bool | None,
) -> dict[str, object]:
    producer = str(payload.get("producer_event_type") or payload.get("producer") or "").strip()
    probability_stage = str(payload.get("probability_model_stage") or "").lower()
    gate_reason = str(
        payload.get("probability_model_gate_reason")
        or payload.get("model_not_run_reason")
        or payload.get("active_window_alignment_reason")
        or payload.get("adaptive_cutoff_reason")
        or payload.get("orderbook_readiness_reason")
        or readiness_state
        or ""
    )
    orderbook_available_for_decision = bool(payload.get("orderbook_available_for_decision"))
    orderbook_reason_text = str(
        payload.get("orderbook_readiness_reason")
        or payload.get("orderbook_unavailable_reason")
        or ""
    ).lower()
    generic_orderbook_unavailable = (
        orderbook_available_for_decision
        and any(token in orderbook_reason_text for token in ("orderbook", "unavailable", "bid/ask", "no_orderbook"))
        and not any(token in orderbook_reason_text for token in ("token", "empty", "warmup", "stale"))
    )
    effective_orderbook_reason = "" if generic_orderbook_unavailable else (
        payload.get("orderbook_readiness_reason") or payload.get("orderbook_unavailable_reason") or ""
    )
    if generic_orderbook_unavailable and any(
        token in gate_reason.lower() for token in ("orderbook", "unavailable", "bid/ask", "no_orderbook")
    ):
        gate_reason = str(payload.get("adaptive_cutoff_reason") or readiness_state or "model_output_not_visible")
    seconds_remaining = diagnostic_int(payload.get("seconds_remaining") or payload.get("seconds_until_close"))
    try:
        hard_block_seconds = trader._entry_hard_block_seconds()
    except Exception:
        hard_block_seconds = 0
    effective_cutoff = diagnostic_int(payload.get("effective_cutoff_seconds") or payload.get("entry_cutoff_seconds"))
    pre_model_gate = phase2_pre_model_gate_detail(
        skip_reason=gate_reason,
        orderbook_readiness_reason=effective_orderbook_reason,
        liquidity_state=payload.get("liquidity_state") or "",
        spread_normalized=payload.get("spread_normalized"),
        readiness_state=readiness_state,
        lifecycle_phase=lifecycle_phase,
        probability_available=model_output_ready is True,
    )
    existing_gate_name = str(payload.get("pre_model_gate_name") or "").strip()
    if existing_gate_name and existing_gate_name != "MODEL_GATE_UNKNOWN":
        pre_model_gate["pre_model_gate_name"] = existing_gate_name
        pre_model_gate["pre_model_gate_group"] = str(
            payload.get("pre_model_gate_group") or pre_model_gate["pre_model_gate_group"]
        )
        pre_model_gate["pre_model_gate_reason"] = str(
            payload.get("pre_model_gate_reason") or gate_reason or pre_model_gate["pre_model_gate_reason"]
        )
        pre_model_gate["pre_model_gate_source"] = str(
            payload.get("pre_model_gate_source") or pre_model_gate["pre_model_gate_source"]
        )
        pre_model_gate["pre_model_gate_blocks_probability_model"] = bool(
            payload.get("pre_model_gate_blocks_probability_model", True)
        )
        pre_model_gate["probability_model_call_path"] = str(
            payload.get("probability_model_call_path") or pre_model_gate["probability_model_call_path"]
        )
    explicit_gate_group = str(pre_model_gate.get("pre_model_gate_group") or "")
    explicit_gate_name = str(pre_model_gate.get("pre_model_gate_name") or "")

    if model_output_ready is True:
        state = "MODEL_OUTPUT_VISIBLE"
        group = "MODEL_READY"
        reason = "model_output_visible"
        eligible = True
    elif producer == "market_snapshots":
        state = "PRE_MODEL_OBSERVATION"
        group = "PRODUCER_NOT_RESPONSIBLE"
        reason = gate_reason or "market_snapshot_pre_model_observation"
        pre_model_gate["pre_model_gate_name"] = "PRODUCER_PRE_MODEL_OBSERVATION"
        pre_model_gate["pre_model_gate_group"] = "PRODUCER_NOT_RESPONSIBLE"
        pre_model_gate["pre_model_gate_reason"] = reason
        pre_model_gate["pre_model_gate_source"] = "producer_role"
        pre_model_gate["pre_model_gate_blocks_probability_model"] = False
        pre_model_gate["probability_model_call_path"] = "producer_not_responsible_pre_model_observation"
        eligible = False
    elif explicit_gate_group and explicit_gate_group not in {"MODEL_GATE_UNKNOWN", "MODEL_READY"}:
        state = "BLOCKED_BEFORE_MODEL"
        group = explicit_gate_group
        reason = str(
            payload.get("adaptive_cutoff_reason")
            if explicit_gate_group == "TIME_CUTOFF_GATE" and payload.get("adaptive_cutoff_reason")
            else pre_model_gate.get("pre_model_gate_reason") or explicit_gate_name or gate_reason
        )
        eligible = False
    elif readiness_state == "time_unsafe" or "cutoff" in gate_reason.lower() or "hard_close" in gate_reason.lower():
        state = "BLOCKED_BEFORE_MODEL"
        group = "TIME_CUTOFF_GATE"
        reason = (
            str(payload.get("adaptive_cutoff_reason") or "").strip()
            if gate_reason.lower() in {"", "time_unsafe", "pre_model_gate"}
            else gate_reason
        ) or readiness_state
        eligible = False
    elif readiness_state in {"token_not_ready", "orderbook_unavailable", "empty_book", "warmup_pending", "stale_orderbook"} or orderbook_state != "ready":
        state = "BLOCKED_BEFORE_MODEL"
        group = "ORDERBOOK_GATE"
        reason = gate_reason or readiness_state or orderbook_state
        eligible = False
    elif readiness_state == "liquidity_not_ready":
        state = "BLOCKED_BEFORE_MODEL"
        group = "LIQUIDITY_GATE"
        reason = gate_reason or readiness_state
        eligible = False
    elif readiness_state == "spread_not_ready":
        state = "BLOCKED_BEFORE_MODEL"
        group = "SPREAD_GATE"
        reason = gate_reason or readiness_state
        eligible = False
    elif str(lifecycle_phase).upper() in {"FINAL_DERISK", "CLOSED_OR_UNSAFE"}:
        state = "BLOCKED_BEFORE_MODEL"
        group = "LIFECYCLE_PHASE_GATE"
        reason = gate_reason or lifecycle_phase
        eligible = False
    elif probability_stage == "pre_model_skip":
        state = "BLOCKED_BEFORE_MODEL"
        group = "MODEL_GATE_UNKNOWN"
        reason = gate_reason or "pre_model_skip"
        eligible = False
    elif probability_stage == "no_probability_model_output":
        state = "MODEL_OUTPUT_NOT_VISIBLE"
        group = "MODEL_GATE_UNKNOWN"
        reason = gate_reason or "model_output_not_visible"
        eligible = False
    else:
        state = "MODEL_ELIGIBILITY_UNKNOWN"
        group = "MODEL_GATE_UNKNOWN"
        reason = gate_reason or "model_gate_unknown"
        eligible = False

    lifecycle_second = phase2_elapsed_second(seconds_remaining)
    return {
        "model_activation_state": state,
        "model_activation_block_group": group,
        "model_activation_block_reason": reason,
        "model_attempt_eligible": bool(eligible),
        "model_activation_seconds_remaining": seconds_remaining,
        "model_activation_effective_cutoff_seconds": effective_cutoff,
        "model_activation_hard_block_seconds": hard_block_seconds,
        "model_activation_lifecycle_phase": lifecycle_phase,
        "model_activation_orderbook_state": orderbook_state,
        "model_activation_market_readiness_state": readiness_state,
        "first_model_eligible_second": lifecycle_second if eligible else None,
        "seconds_remaining_when_eligible": seconds_remaining if eligible else None,
        "first_probability_output_second": lifecycle_second if model_output_ready is True else None,
        "seconds_remaining_when_model_output_visible": seconds_remaining if model_output_ready is True else None,
        "model_eligible_at_or_inside_cutoff": bool(
            eligible
            and seconds_remaining is not None
            and effective_cutoff is not None
            and seconds_remaining <= effective_cutoff
        ),
        **pre_model_gate,
    }
