"""Reconciliation carry and metadata construction helpers.

Pure, trader-free helpers for position tracking metadata, model truth
envelopes, size sharp state, and replay keys. Extracted from
trader_reconciliation_payload.py in Phase 3M.
"""

from typing import Any

from polymarket.observability.contracts import (
    CarryMetadata,
    EntryModelTruthEnvelopeWrapper,
    SizeSharpCloseCarry,
    SizeSharpMetadata,
    TradePositionMetadata,
)


def carry_entry_model_truth_from_metadata(metadata: dict) -> CarryMetadata:
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


def size_sharp_metadata(result: Any) -> SizeSharpMetadata:
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


def size_sharp_close_carry(metadata: dict | None) -> SizeSharpCloseCarry:
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
) -> EntryModelTruthEnvelopeWrapper:
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
) -> TradePositionMetadata:
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
