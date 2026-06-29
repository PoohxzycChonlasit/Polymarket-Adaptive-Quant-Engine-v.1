"""Trade lifecycle event payload builders.

Constructs JSONL event dicts for log_trade_open and log_trade_close events.
Pure payload builders (Tier 1) plus one trader-aware context collector (Tier 3).
Extracted from trader_reconciliation_payload.py in Phase 3M.
"""

from typing import Any


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


def build_trade_opened_payload(
    *,
    market_id: str,
    ticker: str,
    token_id: str,
    outcome: str,
    side: object,
    entry_price: float,
    position_size: object,
    notional_size: object,
    receipt_payload: dict[str, object],
    strategy: str,
    condition_id: str = "",
    position_id: str | None = None,
    trade_open_context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the trade-open quant event payload without emitting or reading trader state."""
    context = trade_open_context if isinstance(trade_open_context, dict) else {}
    model_context = context.get("model_context") if isinstance(context.get("model_context"), dict) else {}
    entry_attribution = context.get("entry_attribution")
    phase2_detail = context.get("phase2_detail") if isinstance(context.get("phase2_detail"), dict) else {}
    size_sharp_payload = (
        context.get("size_sharp_payload")
        if isinstance(context.get("size_sharp_payload"), dict)
        else {}
    )
    entry_model_truth_envelope = (
        context.get("entry_model_truth_envelope")
        if isinstance(context.get("entry_model_truth_envelope"), dict)
        else {}
    )
    open_payload = {
        "market_id": market_id,
        "ticker": ticker,
        "token_id": token_id,
        "outcome": outcome,
        "side": side,
        "entry_price": float(entry_price),
        "size": float(position_size),
        "notional_size": float(notional_size),
        "receipt": receipt_payload,
        "strategy": strategy,
        "mode": context.get("runtime_mode"),
        "condition_id": condition_id or "",
        "epoch_start_ts": context.get("epoch_start_ts"),
        "asset": ticker,
        "paper_trade_replay_key": context.get("paper_trade_replay_key"),
        "candidate_peak_favorable": None,
        "candidate_peak_adverse": None,
        "signal_name": model_context.get("signal_name"),
        "signal_reason": model_context.get("signal_reason"),
        "strategy_signal_name": model_context.get("strategy_signal_name"),
        "strategy_signal_reason": model_context.get("strategy_signal_reason"),
        "position_id": position_id,
        "entry_attribution": entry_attribution,
        "entry_attribution_status": "success" if isinstance(entry_attribution, dict) else "missing",
        **phase2_detail,
        "true_probability": context.get("selected_probability"),
        "fair_value": context.get("selected_fair_value"),
        "ev_after_spread": context.get("selected_ev"),
        "expected_value": context.get("selected_ev"),
        "ev": context.get("selected_ev"),
        "confidence": context.get("selected_confidence"),
        **size_sharp_payload,
        "bankroll_rank": context.get("bankroll_rank"),
        "bankroll_family": context.get("bankroll_family"),
        "capital_score": context.get("capital_score"),
        "shadow_policy_decision": model_context.get("shadow_policy_decision"),
        "shadow_policy_reasons": model_context.get("shadow_policy_reasons"),
        "shadow_policy_observed_ev": model_context.get("shadow_policy_observed_ev"),
        "shadow_policy_observed_probability": model_context.get("shadow_policy_observed_probability"),
        "shadow_policy_observed_risk_mode": model_context.get("shadow_policy_observed_risk_mode"),
        "shadow_policy_id": model_context.get("shadow_policy_id"),
        "shadow_policy_confidence": model_context.get("shadow_policy_confidence"),
        **entry_model_truth_envelope,
    }
    if isinstance(entry_attribution, dict):
        for field in ("candidate_id", "candidate_instance_id", "paper_trade_replay_key", "signal_name", "signal_reason"):
            if field in entry_attribution:
                open_payload[field] = entry_attribution[field]
    return open_payload


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
