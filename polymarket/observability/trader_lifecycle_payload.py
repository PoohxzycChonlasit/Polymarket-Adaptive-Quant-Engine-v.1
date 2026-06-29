"""Trader lifecycle payload and read-only helper functions.

Extracted during Phase 3E (TRADER_PHASE3E_LIFECYCLE_PAYLOAD_EXTRACTION_001).
These are read-only payload builders or pure utilities that accept `trader: Any`
and return dictionaries or values, without mutating state or emitting events.
"""
from __future__ import annotations

from typing import Any

from polymarket.observability.trader_lifecycle_observability import (
    diagnostic_float,
    diagnostic_int,
    phase2_elapsed_second,
    phase2_lifecycle_phase,
)
from polymarket.observability.trader_phase2_observability import (
    phase2_orderbook_state_classification,
    phase2_market_readiness_state,
    phase2_candidate_block_detail,
    phase2_model_activation_detail,
    phase2_ev_null_reason_detail,
)
from polymarket.orchestration.trader_observability import TraderObservabilityHelper
from polymarket.bankroll_tiers import get_tier_config


def _p2_val_avail(value: object) -> bool:
    """Mirror of TraderObservabilityHelper._phase2_value_available."""
    return value is not None and value != ""


def compute_lifecycle_latency_ms(bucket: dict[str, object]) -> dict[str, object]:
    """
    Computes wall-clock ms durations between lifecycle milestone timestamps.
    Lifecycle Latency Observatory v1 — observability only, fail-soft.
    All fields default to 0 on any error or missing data.
    """
    _ZERO: dict[str, object] = {
        "discovery_to_token_ready_ms": 0,
        "token_ready_to_book_ms": 0,
        "book_to_nonzero_ms": 0,
        "nonzero_to_normalized_ms": 0,
        "normalized_to_executable_ms": 0,
        "executable_to_decision_ms": 0,
        "total_discovery_to_decision_ms": 0,
        "dominant_latency_stage": "",
        "lifecycle_latency_classification": "",
    }
    try:
        from datetime import datetime as _dt

        def _parse(ts: object) -> _dt | None:
            s = str(ts or "").strip()
            if not s:
                return None
            try:
                return _dt.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                return None

        def _ms(a: _dt | None, b: _dt | None) -> int:
            if a is None or b is None or b <= a:
                return 0
            return max(0, int((b - a).total_seconds() * 1000))

        t_disc = _parse(bucket.get("first_discovered_ts"))
        t_tok = _parse(bucket.get("first_token_ready_ts"))
        t_book = _parse(bucket.get("first_orderbook_seen_ts"))
        t_nonzero = _parse(bucket.get("first_nonzero_bidask_ts"))
        t_norm = _parse(bucket.get("first_spread_normalized_ts"))
        t_exec = _parse(bucket.get("first_tradable_ts"))
        t_dec = _parse(bucket.get("decision_complete_ts"))

        d_disc_tok = _ms(t_disc, t_tok)
        d_tok_book = _ms(t_tok, t_book)
        d_book_nonzero = _ms(t_book, t_nonzero)
        d_nonzero_norm = _ms(t_nonzero, t_norm)
        d_norm_exec = _ms(t_norm, t_exec)
        d_exec_dec = _ms(t_exec, t_dec)
        d_total = _ms(t_disc, t_dec)

        stage_durations = {
            "DISCOVERY": d_disc_tok,
            "TOKEN_READY": d_tok_book,
            "ORDERBOOK": d_book_nonzero,
            "SPREAD_NORMALIZATION": d_nonzero_norm,
            "DECISION": d_norm_exec,
            "CUTOFF": d_exec_dec,
        }
        dominant = max(stage_durations, key=lambda k: stage_durations[k]) if any(stage_durations.values()) else ""

        total = d_total or sum(stage_durations.values())
        if total >= 15000:
            classification = "CRITICAL"
        elif total >= 5000:
            classification = "SLOW"
        elif total >= 2000:
            classification = "NORMAL"
        elif total > 0:
            classification = "FAST"
        else:
            classification = ""

        return {
            "discovery_to_token_ready_ms": d_disc_tok,
            "token_ready_to_book_ms": d_tok_book,
            "book_to_nonzero_ms": d_book_nonzero,
            "nonzero_to_normalized_ms": d_nonzero_norm,
            "normalized_to_executable_ms": d_norm_exec,
            "executable_to_decision_ms": d_exec_dec,
            "total_discovery_to_decision_ms": d_total,
            "dominant_latency_stage": dominant,
            "lifecycle_latency_classification": classification,
        }
    except Exception:
        return dict(_ZERO)


def phase2_readiness_timestamps(trader: Any, ticker: str, epoch_start: int) -> dict[str, object]:
    """Return all cached readiness timestamps for (ticker, epoch_start) or defaults."""
    fields: dict[str, object] = {
        "token_ready_at": "",
        "token_ready_seconds_remaining": 0,
        "orderbook_ready_at": "",
        "orderbook_ready_seconds_remaining": 0,
        "liquidity_ready_at": "",
        "liquidity_ready_seconds_remaining": 0,
        "spread_ready_at": "",
        "spread_ready_seconds_remaining": 0,
        "first_tradable_at": "",
        "first_tradable_seconds_remaining": 0,
        "first_evaluable_at": "",
        "first_evaluable_ready_seconds_remaining": 0,
        # Market Readiness Timing Layer v1
        "first_discovered_ts": "",
        "first_discovered_seconds_remaining": 0,
        "first_token_ready_ts": "",
        "first_token_ready_seconds_remaining": 0,
        "first_orderbook_seen_ts": "",
        "first_orderbook_seen_seconds_remaining": 0,
        "first_nonzero_bidask_ts": "",
        "first_nonzero_bidask_seconds_remaining": 0,
        "first_spread_normalized_ts": "",
        "first_spread_normalized_seconds_remaining": 0,
        "first_tradable_ts": "",
        "first_tradable_seconds_remaining": 0,
        "readiness_confidence": 0.0,
        "executable_book_state": "UNKNOWN",
        "executable_book_state_best_seen": "UNKNOWN",
        "executable_spread_state": "UNKNOWN",
        # Liquidity Depth Observability v1
        "best_bid_size": 0.0,
        "best_ask_size": 0.0,
        "top_bid_depth": 0.0,
        "top_ask_depth": 0.0,
        "total_bid_depth_l1_l3": 0.0,
        "total_ask_depth_l1_l3": 0.0,
        "min_fillable_size_usd": 0.0,
        "liquidity_depth_state": "UNKNOWN",
        "liquidity_depth_confidence": 0.0,
        "time_to_min_depth_seconds": 0,
        "first_min_depth_ts": "",
        "first_min_depth_seconds_remaining": 0,
        "depth_oscillation_count": 0,
        "spread_oscillation_count": 0,
        "tradable_but_thin_count": 0,
    }
    if epoch_start <= 0:
        return fields
    stored = trader._phase2_readiness_store().get((ticker.upper(), int(epoch_start)), {})
    for key in fields:
        if key in stored:
            fields[key] = stored[key]
    return fields


def phase2_exposure_timeline(
    trader: Any,
    market_id: str,
    *,
    risk_plan: Any = None,
    exposure_after: float | None = None,
) -> dict[str, float]:
    """Retrieve pre/post exposure, risk budget used, and remaining risk budget."""
    try:
        current_market_exposure = sum(
            float(getattr(pos, "notional_size", 0.0) or 0.0)
            for pos in trader._open_positions_for_market(market_id)
        )
    except Exception:
        current_market_exposure = 0.0
    state = getattr(trader, "bankroll_state", None)
    current_balance = float(getattr(state, "current_bankroll_for_sizing", 0.0) or 0.0)
    open_exposure = float(getattr(state, "open_position_market_value", current_market_exposure) or 0.0)
    try:
        tier_config = get_tier_config(getattr(state, "current_bankroll_tier", "T0_MICRO_SEED"))
        configured_cap = float(trader._phase2_safe_setting("max_risk_per_market", tier_config.max_market_exposure_pct))
        max_risk_per_market = min(configured_cap, float(tier_config.max_market_exposure_pct))
    except Exception:
        max_risk_per_market = 0.0
    market_budget = max(current_balance * max(max_risk_per_market, 0.0), 0.0)
    if exposure_after is None:
        exposure_after = current_market_exposure
        if risk_plan is not None:
            exposure_after += float(getattr(risk_plan, "notional_size", 0.0) or 0.0)
    return {
        "exposure_before": float(current_market_exposure),
        "exposure_after": float(max(exposure_after, 0.0)),
        "risk_budget_used": float(current_market_exposure),
        "remaining_risk_budget": float(max(market_budget - current_market_exposure, 0.0)),
        "current_exposure": float(open_exposure),
        "target_exposure": float(max(exposure_after, 0.0)),
    }


def phase2_complete_lifecycle_observability(trader: Any, payload: dict[str, object]) -> dict[str, object]:
    """Fill advanced candidate lifecycle details (offsets, state classifications, and metrics)."""
    detail = dict(payload)
    seconds_remaining = detail.get("seconds_remaining", detail.get("seconds_until_close"))
    lifecycle_phase = str(detail.get("lifecycle_phase") or "").strip()
    if not lifecycle_phase:
        lifecycle_phase = (
            trader._phase2_lifecycle_phase(seconds_remaining)
            if diagnostic_int(seconds_remaining) is not None
            else "UNKNOWN"
        )
        detail["lifecycle_phase"] = lifecycle_phase

    market_ref = str(detail.get("market_id") or detail.get("source_market_id") or "")
    ticker = str(detail.get("ticker") or detail.get("asset") or trader._ticker_from_market_id(market_ref) or "UNKNOWN").upper()
    if not detail.get("condition_id"):
        meta_cache = getattr(trader, "_market_token_meta", {})
        if not isinstance(meta_cache, dict):
            meta_cache = {}
        meta = meta_cache.get(ticker, {})
        condition_id = str(meta.get("condition_id", "") or "")
        if not condition_id:
            market_refs = {
                str(value).strip()
                for value in (detail.get("market_id"), detail.get("source_market_id"))
                if str(value or "").strip()
            }
            token_id = str(detail.get("token_id") or "").strip()
            matching_condition_ids: list[str] = []
            for candidate_meta in meta_cache.values():
                if not isinstance(candidate_meta, dict):
                    continue
                candidate_condition_id = str(candidate_meta.get("condition_id", "") or "").strip()
                if not candidate_condition_id:
                    continue
                meta_market_id = str(candidate_meta.get("market_id", "") or "").strip()
                meta_yes_token_id = str(candidate_meta.get("yes_token_id", "") or "").strip()
                meta_no_token_id = str(candidate_meta.get("no_token_id", "") or "").strip()
                market_match = bool(meta_market_id and meta_market_id in market_refs)
                token_match = bool(token_id and token_id in {meta_yes_token_id, meta_no_token_id})
                if market_match or token_match:
                    matching_condition_ids.append(candidate_condition_id)
            if len(matching_condition_ids) == 1:
                condition_id = matching_condition_ids[0]
        if condition_id:
            detail["condition_id"] = condition_id
    market_id = str(detail.get("market_id") or detail.get("condition_id") or detail.get("source_market_id") or f"pm-5m-{ticker.lower()}")
    side = str(detail.get("side") or detail.get("best_side") or detail.get("outcome") or detail.get("decision") or "UNKNOWN").upper()
    epoch_start = diagnostic_int(detail.get("market_epoch_start") or detail.get("epoch_start") or detail.get("epoch_start_ts")) or 0
    if not detail.get("candidate_id"):
        detail["candidate_id"] = TraderObservabilityHelper._phase2_candidate_hash("candidate", market_id, ticker, side, epoch_start)
    if not detail.get("signal_id"):
        detail["signal_id"] = TraderObservabilityHelper._phase2_candidate_hash("signal", market_id, ticker, side, epoch_start)

    start_offset, end_offset = TraderObservabilityHelper._phase2_phase_offsets(lifecycle_phase)
    entered_at = TraderObservabilityHelper._phase2_iso_from_epoch(epoch_start, start_offset)
    exited_at = TraderObservabilityHelper._phase2_iso_from_epoch(epoch_start, end_offset) if end_offset is not None else ""
    detail.setdefault("lifecycle_phase_entered_at", entered_at or None)
    detail.setdefault("lifecycle_phase_exited_at", exited_at or None)
    if not detail.get("lifecycle_phase_transition_reason"):
        detail["lifecycle_phase_transition_reason"] = "epoch_window_direct" if entered_at else "seconds_remaining_direct"

    orderbook_state = phase2_orderbook_state_classification(detail)
    detail.setdefault("orderbook_state_classification", orderbook_state)
    readiness_state = phase2_market_readiness_state(trader, detail, orderbook_state)
    detail.setdefault("market_readiness_state", readiness_state)
    if not detail.get("readiness_transition_reason"):
        detail["readiness_transition_reason"] = str(
            detail.get("active_window_alignment_reason")
            or detail.get("orderbook_readiness_reason")
            or readiness_state
            or "unavailable"
        )

    block_reason, block_stage, expiry_reason = phase2_candidate_block_detail(detail)
    detail.setdefault("candidate_block_reason", block_reason)
    detail.setdefault("candidate_block_stage", block_stage)
    detail.setdefault("candidate_expiry_reason", expiry_reason)
    detail.setdefault("candidate_survival_ms", trader._phase2_candidate_survival_ms(detail))

    model_output_ready = None
    probability_stage = str(detail.get("probability_model_stage") or "").lower()
    if probability_stage in {"probability_model_output", "completed"}:
        model_output_ready = True
    elif probability_stage in {"pre_model_skip", "no_probability_model_output"}:
        model_output_ready = False
    elif bool(detail.get("fair_value_available")) or bool(detail.get("true_probability_available")):
        model_output_ready = True
    detail.setdefault("model_output_ready", model_output_ready)

    ev_candidate_ready = None
    ev_stage = str(detail.get("ev_calculation_stage") or "").lower()
    if ev_stage == "ev_calculated" or bool(detail.get("ev_after_spread_available")):
        ev_candidate_ready = True
    elif any(detail.get(field) for field in ("fair_value_null_reason", "market_price_null_reason", "true_probability_null_reason", "ev_after_spread_null_reason")):
        ev_candidate_ready = False
    detail.setdefault("ev_candidate_ready", ev_candidate_ready)
    activation_detail = phase2_model_activation_detail(
        trader,
        detail,
        lifecycle_phase=lifecycle_phase,
        orderbook_state=orderbook_state,
        readiness_state=readiness_state,
        model_output_ready=model_output_ready,
    )
    for key, value in activation_detail.items():
        detail[key] = value
    detail.setdefault("probability_model_called", bool(model_output_ready))
    detail.setdefault("probability_model_output_visible", bool(model_output_ready))
    if not detail.get("model_handoff_stage"):
        detail["model_handoff_stage"] = (
            "MODEL_OUTPUT_SERIALIZED"
            if model_output_ready is True
            else "PRE_MODEL_GATE"
            if detail.get("model_activation_state") == "BLOCKED_BEFORE_MODEL"
            else "MODEL_OUTPUT_NOT_VISIBLE"
        )
    detail.setdefault(
        "model_output_missing_reason",
        "" if model_output_ready is True else str(detail.get("model_activation_block_reason") or "model_output_not_visible"),
    )
    first_seen_remaining = diagnostic_int(detail.get("first_seen_seconds_remaining"))
    first_orderbook_remaining = diagnostic_int(detail.get("orderbook_ready_seconds_remaining"))
    first_tradable_remaining = diagnostic_int(detail.get("first_tradable_seconds_remaining"))
    current_remaining = diagnostic_int(detail.get("seconds_remaining") or detail.get("seconds_until_close"))
    if first_seen_remaining is not None:
        detail.setdefault("first_seen_second", phase2_elapsed_second(first_seen_remaining))
    if first_orderbook_remaining:
        detail.setdefault("first_orderbook_ready_second", phase2_elapsed_second(first_orderbook_remaining))
    if first_tradable_remaining:
        detail.setdefault("first_candidate_ready_second", phase2_elapsed_second(first_tradable_remaining))
    if first_seen_remaining is not None and current_remaining is not None:
        duration = int(max(0, first_seen_remaining - current_remaining))
        detail.setdefault("candidate_lifecycle_duration_seconds", duration)
        detail.setdefault("candidate_lifecycle_duration", duration)

    # Preload Next Market v1
    detail["preload_attempted"] = getattr(trader, "_preload_attempted", False)
    detail["preload_success"] = getattr(trader, "_preload_success", False)
    detail["preload_failure_reason"] = getattr(trader, "_preload_failed_reason", None)
    detail["preload_ticker"] = getattr(trader, "_preload_ticker", "")
    detail["preload_market_slug"] = getattr(trader, "_preload_market_slug", "")
    detail["preload_condition_id"] = getattr(trader, "_preload_condition_id", "")
    detail["preload_yes_token_id_present"] = getattr(trader, "_preload_yes_token_id_present", False)
    detail["preload_no_token_id_present"] = getattr(trader, "_preload_no_token_id_present", False)
    detail["preload_orderbook_warmed"] = getattr(trader, "_preload_orderbook_warmed", False)
    detail["preload_orderbook_state"] = getattr(trader, "_preload_orderbook_state", "UNKNOWN")
    detail["preload_seconds_before_epoch"] = getattr(trader, "_preload_seconds_before_epoch", 0)
    detail["preload_latency_ms"] = getattr(trader, "_preload_latency_ms", 0)
    detail["preload_cache_hit"] = getattr(trader, "_preload_cache_hit", False)
    detail["preload_cache_age_seconds"] = getattr(trader, "_preload_cache_age_seconds", 0)
    detail["preload_next_epoch_start"] = getattr(trader, "_preload_next_epoch_start", 0)
    detail["preload_next_epoch_remaining_seconds"] = getattr(trader, "_preload_next_epoch_remaining_seconds", 0)

    return detail


def phase2_observability_payload(
    trader: Any,
    *,
    ticker: str,
    market_id: str = "",
    side: str = "",
    epoch_start: object = None,
    seconds_remaining: object = None,
    market_price: object = None,
    fair_value: object = None,
    true_probability: object = None,
    ev_after_spread: object = None,
    skip_reason: object = "",
    orderbook_readiness_reason: object = "",
    liquidity_state: object = "",
    spread_normalized: object = None,
    risk_plan: Any = None,
) -> dict[str, object]:
    """Format a candidate detail dictionary for observability and shadow replay checks."""
    epoch_start_int = diagnostic_int(epoch_start) or 0
    market_id = market_id or f"pm-5m-{ticker.lower()}"
    side = str(side or "UNKNOWN").upper()
    ticker_key = str(ticker or "").upper()
    cached_token_ids = getattr(trader, "_real_token_ids", {}).get(ticker_key) or ()
    cached_meta = getattr(trader, "_market_token_meta", {}).get(ticker_key, {})
    cached_yes_token_id = str(
        (cached_token_ids[0] if len(cached_token_ids) > 0 else "")
        or cached_meta.get("yes_token_id", "")
        or ""
    )
    cached_no_token_id = str(
        (cached_token_ids[1] if len(cached_token_ids) > 1 else "")
        or cached_meta.get("no_token_id", "")
        or ""
    )
    cached_side_token_id = ""
    if side == "YES":
        cached_side_token_id = cached_yes_token_id
    elif side == "NO":
        cached_side_token_id = cached_no_token_id
    cached_condition_id = str(cached_meta.get("condition_id", "") or "")
    cached_market_slug = str(cached_meta.get("slug", "") or cached_meta.get("market_slug", "") or "")
    token_handoff_source = "cached_market_token_meta" if cached_yes_token_id and cached_no_token_id else "not_available"
    lifecycle_phase = trader._phase2_lifecycle_phase(seconds_remaining)
    candidate_id = TraderObservabilityHelper._phase2_candidate_hash("candidate", market_id, ticker_key, side, epoch_start_int)
    signal_id = TraderObservabilityHelper._phase2_candidate_hash("signal", market_id, ticker_key, side, epoch_start_int)
    market_key = (ticker_key, epoch_start_int)
    first_seen_remaining = getattr(trader, "_market_first_seen_seconds_remaining", {}).get(market_key)
    if first_seen_remaining is None:
        first_seen_remaining = diagnostic_int(seconds_remaining)
    readiness_timestamps = trader._phase2_readiness_timestamps(ticker, epoch_start_int)
    first_orderbook_remaining = diagnostic_int(readiness_timestamps.get("orderbook_ready_seconds_remaining"))
    first_tradable_remaining = diagnostic_int(readiness_timestamps.get("first_tradable_seconds_remaining"))
    price = diagnostic_float(market_price, default=0.0)
    exposure = trader._phase2_exposure_timeline(market_id, risk_plan=risk_plan)
    starter_candidate = exposure["exposure_before"] <= 0.0 and lifecycle_phase in {
        "OPENING_SCAN",
        "ACTIVE_INVENTORY_TRADING",
    }
    final_derisk_candidate = exposure["exposure_before"] > 0.0 and lifecycle_phase == "FINAL_DERISK"
    payload: dict[str, object] = {
        "lifecycle_phase": lifecycle_phase,
        "candidate_id": candidate_id,
        "signal_id": signal_id,
        "token_id": cached_side_token_id,
        "yes_token_id": cached_yes_token_id,
        "no_token_id": cached_no_token_id,
        "condition_id": cached_condition_id,
        "market_slug": cached_market_slug,
        "cached_token_pair_available": bool(cached_yes_token_id and cached_no_token_id),
        "yes_no_token_pair_present": bool(cached_yes_token_id and cached_no_token_id),
        "decision_token_handoff_source": token_handoff_source,
        **readiness_timestamps,
        "first_seen_seconds_remaining": first_seen_remaining or 0,
        "first_seen_second": trader._phase2_elapsed_second(first_seen_remaining),
        "first_orderbook_ready_second": (
            trader._phase2_elapsed_second(first_orderbook_remaining) if first_orderbook_remaining else None
        ),
        "first_candidate_ready_second": (
            trader._phase2_elapsed_second(first_tradable_remaining) if first_tradable_remaining else None
        ),
        "fair_value": fair_value,
        "market_price": market_price,
        "true_probability": true_probability,
        "ev_after_spread": ev_after_spread,
        **phase2_ev_null_reason_detail(
            fair_value=fair_value,
            market_price=market_price,
            true_probability=true_probability,
            ev_after_spread=ev_after_spread,
            skip_reason=skip_reason,
            orderbook_readiness_reason=orderbook_readiness_reason,
            liquidity_state=liquidity_state,
            spread_normalized=spread_normalized,
        ),
        "mfe_candidate_price": price if price > 0.0 else None,
        "mae_candidate_price": price if price > 0.0 else None,
        "candidate_peak_favorable": 0.0,
        "candidate_peak_adverse": 0.0,
        "starter_candidate": bool(starter_candidate),
        "reload_candidate": False,
        "unload_candidate": False,
        "final_derisk_candidate": bool(final_derisk_candidate),
        "inventory_action": (
            "FINAL_DERISK_CANDIDATE"
            if final_derisk_candidate
            else "STARTER_CANDIDATE" if starter_candidate else ""
        ),
        **exposure,
    }
    orderbook_state = phase2_orderbook_state_classification(payload)
    payload.setdefault("orderbook_state_classification", orderbook_state)
    readiness_state = phase2_market_readiness_state(trader, payload, orderbook_state)
    payload.setdefault("market_readiness_state", readiness_state)
    model_output_ready = (
        _p2_val_avail(fair_value)
        or _p2_val_avail(true_probability)
    )
    payload.update(
        phase2_model_activation_detail(
            trader,
            payload,
            lifecycle_phase=lifecycle_phase,
            orderbook_state=orderbook_state,
            readiness_state=readiness_state,
            model_output_ready=model_output_ready,
        )
    )
    return payload
