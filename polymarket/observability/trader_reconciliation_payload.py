"""Observability helpers for trader reconciliation, metadata mapping, and carry-forward payload construction.

Part of Phase 3F refactoring to decouple read-only metadata generation from live execution.
"""

from typing import Any


def carry_entry_model_truth_from_metadata(metadata: dict) -> dict[str, object]:
    """ENTRY_MODEL_TRUTH_ENVELOPE_V1 — observability-only, carry from position metadata, fail-soft"""
    try:
        envelope = metadata.get("entry_model_truth_envelope_v1")
        if not isinstance(envelope, dict):
            return {"entry_model_truth_carry_status": "absent_in_metadata"}
        carried = dict(envelope)
        carried["carried_from"] = "position_metadata"
        return {"entry_model_truth_envelope_v1": carried}
    except Exception:
        return {}


def build_paper_trade_replay_key(
    *,
    condition_id: object,
    epoch_start_ts: object,
    ticker: object,
    outcome: object,
    token_id: object,
) -> str:
    """Build paper-trading replay lookup key."""
    try:
        epoch = int(epoch_start_ts or 0)
    except (TypeError, ValueError):
        epoch = 0
    condition_text = str(condition_id or "")
    outcome_text = str(outcome or "")
    token_text = str(token_id or "")
    ticker_text = str(ticker or "")
    if condition_text and epoch and outcome_text and token_text:
        return f"{condition_text}|{epoch}|{ticker_text}|{outcome_text}|{token_text}"
    return ""


def size_sharp_metadata(result: Any) -> dict[str, object]:
    """Format SizeSharpResult or dict as flattened telemetry fields."""
    if result is None:
        return {
            "size_sharp_close_carry_status": "missing_not_scored",
        }
    payload = result.as_dict() if hasattr(result, "as_dict") else dict(result)
    return {
        "size_sharp_at_entry": payload.get("size_sharp"),
        "size_sharp_bucket": payload.get("size_sharp_bucket"),
        "size_sharp_deployment_state": payload.get("deployment_state"),
        "size_sharp_limiting_factor": payload.get("limiting_factor"),
        "size_sharp_confidence_grade": payload.get("confidence_grade"),
        "size_sharp_component_scores": payload.get("component_scores") or {},
        "size_sharp_penalties": payload.get("penalties") or {},
        "size_sharp_boosts": payload.get("boosts") or {},
        "size_sharp_hard_caps": payload.get("hard_caps") or [],
        "size_sharp_missing_inputs": payload.get("missing_inputs") or [],
        "size_sharp_schema_version": payload.get("schema_version") or "size_sharp_v1",
    }


def size_sharp_close_carry(metadata: dict | None) -> dict[str, object]:
    """Retrieve size_sharp entry metadata fields for close payload carry-forward."""
    if not isinstance(metadata, dict):
        return {"size_sharp_close_carry_status": "missing_legacy_metadata"}
    keys = (
        "size_sharp_at_entry",
        "size_sharp_bucket",
        "size_sharp_deployment_state",
        "size_sharp_limiting_factor",
        "size_sharp_confidence_grade",
        "size_sharp_component_scores",
        "size_sharp_penalties",
        "size_sharp_boosts",
        "size_sharp_hard_caps",
        "size_sharp_missing_inputs",
        "size_sharp_schema_version",
    )
    carried = {key: metadata.get(key) for key in keys}
    if carried.get("size_sharp_at_entry") is None and carried.get("size_sharp_bucket") in {None, ""}:
        carried["size_sharp_close_carry_status"] = "missing_legacy_metadata"
    else:
        carried["size_sharp_close_carry_status"] = "carried"
    return carried


def build_entry_model_truth_envelope(
    *,
    utc_timestamp: str,
    true_probability: object = None,
    fair_value: object = None,
    ev_after_spread: object = None,
    confidence: object = None,
    model_probability_yes: object = None,
    model_probability_no: object = None,
    selected_side: object = None,
    model_handoff_stage: object = None,
    probability_model_stage: object = None,
    model_output_ready: object = None,
    model_attempted: object = None,
    model_not_run_reason: object = None,
    ev_missing_reason: object = None,
    computed_by: str = "unknown",
    serialization_source: str = "unknown",
) -> dict[str, object]:
    """ENTRY_MODEL_TRUTH_ENVELOPE_V1 — observability-only, additive, fail-soft"""
    try:
        def _sf(v: object) -> float | None:
            if v is None or v == "":
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        p_true = _sf(true_probability)
        fv = _sf(fair_value)
        ev = _sf(ev_after_spread)
        conf = _sf(confidence)
        p_yes = _sf(model_probability_yes)
        p_no = _sf(model_probability_no)
        side_str = str(selected_side).upper() if selected_side else ""

        if p_true is not None and ev is not None:
            truth_status = "full"
        elif p_true is not None:
            truth_status = "probability_only"
        elif ev is not None:
            truth_status = "ev_only"
        else:
            truth_status = "absent"

        _model_output_ready: bool = (
            bool(model_output_ready)
            if model_output_ready is not None
            else (p_true is not None or fv is not None)
        )
        _model_attempted: bool = (
            bool(model_attempted)
            if model_attempted is not None
            else (p_true is not None or ev is not None)
        )
        _ev_missing_reason = (
            str(ev_missing_reason)
            if ev_missing_reason
            else ("" if ev is not None else "ev_not_available")
        )
        return {
            "entry_model_truth_envelope_v1": {
                "schema_version": "1.0",
                "truth_status": truth_status,
                "truth_source": str(serialization_source),
                "producer_stage": str(computed_by),
                "model_output_ready": _model_output_ready,
                "model_attempted": _model_attempted,
                "model_not_run_reason": str(model_not_run_reason) if model_not_run_reason else "",
                "probability_model_stage": str(probability_model_stage) if probability_model_stage else "",
                "model_handoff_stage": str(model_handoff_stage) if model_handoff_stage else "",
                "model_probability_yes": p_yes,
                "model_probability_no": p_no,
                "selected_side": side_str,
                "true_probability": p_true,
                "fair_value": fv,
                "ev_after_spread": ev,
                "expected_value": ev,
                "confidence": conf,
                "ev_missing_reason": _ev_missing_reason,
                "lineage_reference_only": True,
                "computed_at": utc_timestamp,
                "computed_by": str(computed_by),
                "serialization_source": str(serialization_source),
            }
        }
    except Exception:
        return {}


def _trade_open_context_value_available(value: object) -> bool:
    return value is not None and value != ""


def collect_trade_open_context(
    *,
    trader: Any,
    market_id: str,
    ticker: str,
    token_id: str,
    outcome: str,
    risk_plan: Any,
    entry_price: float,
    seconds_remaining: int | None = None,
    epoch_start: int | None = None,
    condition_id: str = "",
    true_probability: float | None = None,
    fair_value: float | None = None,
    ev_after_spread: float | None = None,
    confidence: float | None = None,
    entry_attribution: dict[str, object] | None = None,
) -> dict[str, object]:
    """Collect trader-aware context for trade-open payload assembly without emitting events."""
    model_context = {}
    last_quant_details = getattr(trader, "last_quant_details", {})
    if isinstance(last_quant_details, dict):
        candidate_context = last_quant_details.get(str(ticker or "").upper(), {})
        if isinstance(candidate_context, dict):
            model_context = candidate_context
    if entry_attribution is None and isinstance(model_context, dict):
        entry_attribution = model_context.get("entry_attribution")

    def first_available(*values: object) -> object:
        for value in values:
            if _trade_open_context_value_available(value):
                return value
        return None

    outcome_upper = str(outcome or "").upper()
    model_p_yes = first_available(
        model_context.get("model_probability_yes"),
        model_context.get("p_yes"),
        model_context.get("model_p_yes"),
        model_context.get("fair_value_yes"),
    )
    model_p_no = first_available(
        model_context.get("model_probability_no"),
        model_context.get("p_no"),
        model_context.get("model_p_no"),
        model_context.get("fair_value_no"),
    )
    selected_probability = first_available(true_probability, model_context.get("true_probability"))
    if selected_probability is None:
        if outcome_upper == "YES":
            selected_probability = model_p_yes
        elif outcome_upper == "NO":
            selected_probability = model_p_no
    selected_fair_value = first_available(fair_value, model_context.get("fair_value"))
    if selected_fair_value is None:
        if outcome_upper == "YES":
            selected_fair_value = first_available(model_context.get("fair_value_yes"), model_p_yes)
        elif outcome_upper == "NO":
            selected_fair_value = first_available(model_context.get("fair_value_no"), model_p_no)
    if selected_fair_value is None:
        selected_fair_value = selected_probability
    selected_ev = first_available(
        ev_after_spread,
        model_context.get("ev_after_spread"),
        model_context.get("expected_value"),
        model_context.get("ev"),
        model_context.get("edge"),
    )
    selected_confidence = first_available(confidence, model_context.get("confidence"))
    model_output_visible = any(
        _trade_open_context_value_available(value)
        for value in (selected_probability, selected_fair_value, model_p_yes, model_p_no)
    )
    phase2_detail = dict(trader._phase2_observability_payload(
        ticker=ticker,
        market_id=market_id,
        side=outcome,
        epoch_start=epoch_start,
        seconds_remaining=seconds_remaining,
        market_price=entry_price,
        fair_value=selected_fair_value,
        true_probability=selected_probability,
        ev_after_spread=selected_ev,
        skip_reason="",
        risk_plan=None,
    ))
    if model_output_visible:
        phase2_detail.update({
            "model_output_ready": True,
            "model_attempted": True,
            "probability_model_called": True,
            "probability_model_output_visible": True,
            "probability_model_stage": "probability_model_output",
            "probability_model_gate_reason": "model_output_visible",
            "model_not_run_reason": "",
            "model_output_missing_reason": "",
            "model_handoff_stage": "MODEL_OUTPUT_SERIALIZED",
        })
    if _trade_open_context_value_available(model_p_yes):
        phase2_detail.update({
            "p_yes": model_p_yes,
            "model_p_yes": model_p_yes,
            "model_probability_yes": model_p_yes,
            "fair_value_yes": first_available(model_context.get("fair_value_yes"), model_p_yes),
        })
    if _trade_open_context_value_available(model_p_no):
        phase2_detail.update({
            "p_no": model_p_no,
            "model_p_no": model_p_no,
            "model_probability_no": model_p_no,
            "fair_value_no": first_available(model_context.get("fair_value_no"), model_p_no),
        })
    exposure_after = float(phase2_detail.get("exposure_after", 0.0) or 0.0)
    exposure_before = max(exposure_after - float(getattr(risk_plan, "notional_size", 0.0) or 0.0), 0.0)
    phase2_detail.update({
        "exposure_before": exposure_before,
        "risk_budget_used": exposure_before,
    })
    epoch_start_ts = int(epoch_start or 0)
    paper_trade_replay_key = trader._build_paper_trade_replay_key(
        condition_id=condition_id,
        epoch_start_ts=epoch_start_ts,
        ticker=ticker,
        outcome=outcome,
        token_id=token_id,
    )
    return {
        "model_context": model_context,
        "entry_attribution": entry_attribution,
        "model_p_yes": model_p_yes,
        "model_p_no": model_p_no,
        "selected_probability": selected_probability,
        "selected_fair_value": selected_fair_value,
        "selected_ev": selected_ev,
        "selected_confidence": selected_confidence,
        "model_output_visible": model_output_visible,
        "phase2_detail": phase2_detail,
        "epoch_start_ts": epoch_start_ts,
        "paper_trade_replay_key": paper_trade_replay_key,
        "runtime_mode": trader._runtime_mode(),
        "size_sharp_payload": trader._size_sharp_metadata(model_context.get("size_sharp_result")),
        "bankroll_rank": getattr(trader, "_last_bankroll_rank", None),
        "bankroll_family": getattr(trader, "_last_bankroll_family", None),
        "capital_score": getattr(trader, "_last_capital_score", None),
        "entry_model_truth_envelope": trader._build_entry_model_truth_envelope(
            true_probability=selected_probability,
            fair_value=selected_fair_value,
            ev_after_spread=selected_ev,
            confidence=selected_confidence,
            model_probability_yes=model_p_yes,
            model_probability_no=model_p_no,
            selected_side=outcome,
            model_handoff_stage=phase2_detail.get("model_handoff_stage"),
            probability_model_stage=phase2_detail.get("probability_model_stage"),
            model_output_ready=model_output_visible,
            model_attempted=phase2_detail.get("probability_model_called") or phase2_detail.get("model_attempted"),
            model_not_run_reason=phase2_detail.get("model_not_run_reason"),
            ev_missing_reason=phase2_detail.get("ev_after_spread_null_reason") or phase2_detail.get("ev_missing_reason"),
            computed_by="trade_open_context",
            serialization_source="last_quant_details",
        ),
    }


def build_trade_closed_payload(
    *,
    position: Any,
    metadata: dict | None,
    reason: str,
    exit_price: float,
    exit_timestamp: str,
    hold_seconds: int | None,
    size: float,
    pnl: float,
    trade_result: str | None,
    entry_price: float | None,
    partial: bool,
    receipt_payload: dict[str, object] | None,
    mode: str,
    ticker: str,
    token_id: str,
    outcome: str,
    condition_id: str,
    epoch_start_ts: int,
    paper_trade_replay_key: str,
    size_sharp_carry: dict[str, object] | None = None,
    entry_model_truth_carry: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the trade-close quant event payload without emitting or mutating trader state."""
    metadata_dict = metadata if isinstance(metadata, dict) else {}
    close_payload = {
        "position_id": getattr(position, "position_id", ""),
        "market_id": getattr(position, "symbol", ""),
        "ticker": ticker,
        "token_id": token_id,
        "outcome": outcome,
        "reason": reason,
        "exit_price": float(exit_price),
        "exit_timestamp": exit_timestamp,
        "hold_seconds": hold_seconds,
        "size": float(size),
        "pnl": float(pnl),
        "pnl_usdc": float(pnl),
        "trade_result": trade_result,
        "entry_price": entry_price,
        "partial": bool(partial),
        "receipt": receipt_payload or {},
        "mode": mode,
        "condition_id": condition_id,
        "epoch_start_ts": epoch_start_ts,
        "asset": ticker,
        "paper_trade_replay_key": paper_trade_replay_key,
        "candidate_peak_favorable": None,
        "candidate_peak_adverse": None,
        "true_probability": metadata_dict.get("true_probability") if isinstance(metadata, dict) else None,
        "fair_value": metadata_dict.get("fair_value") if isinstance(metadata, dict) else None,
        "ev": metadata_dict.get("entry_ev") if isinstance(metadata, dict) else None,
        "ev_after_spread": metadata_dict.get("entry_ev") if isinstance(metadata, dict) else None,
        "confidence": metadata_dict.get("confidence") if isinstance(metadata, dict) else None,
        "signal_name": metadata_dict.get("signal_name") if isinstance(metadata, dict) else None,
        "signal_reason": metadata_dict.get("signal_reason") if isinstance(metadata, dict) else None,
        "strategy_signal_name": metadata_dict.get("strategy_signal_name") if isinstance(metadata, dict) else None,
        "strategy_signal_reason": metadata_dict.get("strategy_signal_reason") if isinstance(metadata, dict) else None,
        "lifecycle_phase": metadata_dict.get("lifecycle_phase") if isinstance(metadata, dict) else None,
        "seconds_remaining": metadata_dict.get("seconds_remaining") if isinstance(metadata, dict) else None,
        "bankroll_tier_id": metadata_dict.get("bankroll_tier_id") if isinstance(metadata, dict) else None,
        "bankroll_family": metadata_dict.get("bankroll_family") if isinstance(metadata, dict) else None,
        "risk_mode": metadata_dict.get("risk_mode") if isinstance(metadata, dict) else None,
        "risk_budget": metadata_dict.get("risk_budget") if isinstance(metadata, dict) else None,
        "current_exposure": metadata_dict.get("current_exposure") if isinstance(metadata, dict) else None,
        "target_exposure": metadata_dict.get("target_exposure") if isinstance(metadata, dict) else None,
        "notional_size": metadata_dict.get("notional_size") if isinstance(metadata, dict) else None,
        "capital_score": metadata_dict.get("capital_score") if isinstance(metadata, dict) else None,
        "capital_state": metadata_dict.get("capital_state") if isinstance(metadata, dict) else None,
        "promotion_candidate": metadata_dict.get("promotion_candidate") if isinstance(metadata, dict) else None,
        "demotion_candidate": metadata_dict.get("demotion_candidate") if isinstance(metadata, dict) else None,
        "expected_risk_profile": metadata_dict.get("expected_risk_profile") if isinstance(metadata, dict) else None,
        "bankroll_rank": metadata_dict.get("bankroll_rank") if isinstance(metadata, dict) else None,
        "shadow_policy_decision": metadata_dict.get("shadow_policy_decision") if isinstance(metadata, dict) else None,
        "shadow_policy_observed_ev": (
            metadata_dict.get("shadow_policy_observed_ev") if isinstance(metadata, dict) else None
        ),
        "shadow_policy_observed_probability": (
            metadata_dict.get("shadow_policy_observed_probability") if isinstance(metadata, dict) else None
        ),
        "shadow_policy_observed_risk_mode": (
            metadata_dict.get("shadow_policy_observed_risk_mode") if isinstance(metadata, dict) else None
        ),
        "shadow_policy_id": metadata_dict.get("shadow_policy_id") if isinstance(metadata, dict) else None,
        **(size_sharp_carry or {}),
        **(entry_model_truth_carry or {}),
    }
    attribution = metadata_dict.get("entry_attribution")
    if isinstance(attribution, dict):
        close_payload["entry_attribution"] = attribution
        close_payload["entry_attribution_status"] = "success"
        for field in ("candidate_id", "candidate_instance_id", "paper_trade_replay_key", "signal_name", "signal_reason"):
            if field in attribution:
                close_payload[field] = attribution[field]
    else:
        close_payload["entry_attribution_status"] = "missing_legacy"
    return close_payload


def build_trade_position_metadata(
    *,
    last_quant_details: dict,
    utc_timestamp: str,
    strategy: object,
    signal_strategy: object,
    token_id: object,
    outcome: object,
    entry_ev: object,
    confidence: object,
    delta_regime: object,
    condition_id: object,
    epoch_start_ts: object,
    market_slug: object,
    lifecycle_phase: object,
    ticker: object,
    true_probability: object = None,
    fair_value: object = None,
    signal_name: object = None,
    signal_reason: object = None,
    strategy_signal_name: object = None,
    strategy_signal_reason: object = None,
    bankroll_tier_id: object = None,
    bankroll_family: object = None,
    risk_mode: object = None,
    risk_budget: object = None,
    current_exposure: object = None,
    target_exposure: object = None,
    notional_size: object = None,
    seconds_remaining: object = None,
    capital_score: object = None,
    capital_state: object = None,
    promotion_candidate: object = None,
    demotion_candidate: object = None,
    expected_risk_profile: object = None,
    size_sharp_result: object = None,
    bankroll_rank: object = None,
) -> dict[str, object]:
    """Construct full position metadata dictionary for tracking/reconciliation."""
    paper_trade_replay_key = build_paper_trade_replay_key(
        condition_id=condition_id,
        epoch_start_ts=epoch_start_ts,
        ticker=ticker,
        outcome=outcome,
        token_id=token_id,
    )
    _envelope = build_entry_model_truth_envelope(
        true_probability=true_probability,
        fair_value=fair_value,
        ev_after_spread=entry_ev,
        confidence=confidence,
        selected_side=outcome,
        computed_by="position_metadata",
        serialization_source="build_trade_position_metadata",
        utc_timestamp=utc_timestamp,
    ).get("entry_model_truth_envelope_v1")
    ticker_key = str(ticker or "").upper()
    quant_details = last_quant_details.get(ticker_key, {})
    entry_attribution = {
        "candidate_id": quant_details.get("candidate_id"),
        "candidate_trace_id": quant_details.get("candidate_trace_id"),
        "candidate_instance_id": quant_details.get("candidate_instance_id"),
        "candidate_instance_trace_id": quant_details.get("candidate_instance_trace_id"),
        "candidate_instance_created_at": quant_details.get("candidate_instance_created_at"),
        "candidate_instance_identity_schema_version": quant_details.get("candidate_instance_identity_schema_version"),
        "candidate_instance_identity_source": quant_details.get("candidate_instance_identity_source"),
        "legacy_candidate_identity_source": quant_details.get("legacy_candidate_identity_source"),
        "signal_name": quant_details.get("signal_name") or signal_name,
        "signal_reason": quant_details.get("signal_reason") or signal_reason,
        "paper_trade_replay_key": paper_trade_replay_key or None,
        "entry_ev": (
            float(entry_ev)
            if entry_ev is not None
            else (float(quant_details.get("entry_ev")) if quant_details.get("entry_ev") is not None else None)
        ),
        "entry_probability": (
            float(true_probability)
            if true_probability is not None
            else (
                float(quant_details.get("true_probability"))
                if quant_details.get("true_probability") is not None
                else None
            )
        ),
        "selected_side": str(outcome or ""),
    }
    metadata = {
        "strategy": strategy,
        "signal_strategy": signal_strategy,
        "token_id": token_id,
        "outcome": outcome,
        "entry_ev": entry_ev,
        "confidence": confidence,
        "delta_regime": delta_regime,
        "condition_id": condition_id,
        "epoch_start_ts": epoch_start_ts,
        "market_slug": market_slug,
        "lifecycle_phase": lifecycle_phase,
        "paper_trade_replay_key": paper_trade_replay_key or None,
        "entry_model_truth_envelope_v1": _envelope,
        "signal_name": signal_name,
        "signal_reason": signal_reason,
        "strategy_signal_name": strategy_signal_name,
        "strategy_signal_reason": strategy_signal_reason,
        "entry_attribution": entry_attribution,
        "bankroll_tier_id": bankroll_tier_id,
        "bankroll_family": bankroll_family,
        "risk_mode": risk_mode,
        "risk_budget": risk_budget,
        "current_exposure": current_exposure,
        "target_exposure": target_exposure,
        "notional_size": notional_size,
        "seconds_remaining": seconds_remaining,
        "true_probability": true_probability,
        "fair_value": fair_value,
        "capital_score": capital_score,
        "capital_state": capital_state,
        "promotion_candidate": promotion_candidate,
        "demotion_candidate": demotion_candidate,
        "expected_risk_profile": expected_risk_profile,
        "bankroll_rank": bankroll_rank,
    }
    # Shadow policy fields from quant_details — carry into position metadata
    for _sp_key in (
        "shadow_policy_decision",
        "shadow_policy_reasons",
        "shadow_policy_observed_ev",
        "shadow_policy_observed_probability",
        "shadow_policy_observed_risk_mode",
        "shadow_policy_id",
        "shadow_policy_confidence",
    ):
        metadata[_sp_key] = quant_details.get(_sp_key)
    if size_sharp_result is None:
        size_sharp_result = quant_details.get("size_sharp_result")
    metadata.update(size_sharp_metadata(size_sharp_result))
    return metadata
