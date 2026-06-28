from __future__ import annotations

from typing import Any

from polymarket.orchestration.trader_observability import TraderObservabilityHelper
from polymarket.regime_diagnostics import classify_market_regime_from_payload
from utils.no_entry_diagnostics import classify_time_bucket, normalize_skip_reason


EMPTY_BOOK_RECOVERY_RESEARCH_FIELD_NAMES = (
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
)


def build_decision_diagnostics_payload(source: Any, outcome: Any, *, ticker: str) -> dict[str, object]:
    """Build the decision diagnostics payload without changing trading decisions."""
    self = source
    display = outcome.display or {}
    raw_reason = str(display.get("raw_skip_reason", "") or outcome.skip_reason or "")
    normalized_reason = str(display.get("normalized_skip_reason", "") or normalize_skip_reason(raw_reason))
    seconds_remaining = display.get("seconds_remaining", display.get("time_remaining_seconds"))
    entry_cutoff_seconds = display.get(
        "entry_cutoff_seconds",
        int(self._setting("execution_entry_cutoff_seconds", 90)),
    )
    time_bucket = str(display.get("time_bucket", "") or classify_time_bucket(seconds_remaining, entry_cutoff_seconds))
    edge = display.get("edge", display.get("ev"))
    decision_timestamp = self._utc_timestamp()
    market_close_timestamp = str(
        display.get("market_close_timestamp")
        or display.get("market_end_time")
        or ""
    )
    orderbook_age_ms = self._diagnostic_int(display.get("orderbook_age_ms")) or 0
    oracle_age_ms = self._diagnostic_int(display.get("oracle_age_ms")) or 0
    market_feed_age_ms = self._diagnostic_int(display.get("market_feed_age_ms")) or 0
    regime_detail = classify_market_regime_from_payload(display).to_payload()
    cutoff_block_seconds_remaining = (
        self._diagnostic_int(seconds_remaining)
        if normalized_reason == "time_unsafe" or "cutoff" in raw_reason.lower()
        else None
    )
    candidate_side = str(display.get("side") or display.get("best_side") or display.get("outcome") or outcome.decision)
    fair_value = display.get("fair_value")
    true_probability = display.get("true_probability")
    if fair_value is None or true_probability is None:
        side_upper = candidate_side.upper()
        if side_upper == "YES":
            fair_value = display.get("p_yes", display.get("model_p_yes")) if fair_value is None else fair_value
            true_probability = fair_value if true_probability is None else true_probability
        elif side_upper == "NO":
            fair_value = display.get("p_no", display.get("model_p_no")) if fair_value is None else fair_value
            true_probability = fair_value if true_probability is None else true_probability
    ev_after_spread_value = display.get("ev_after_spread")
    if ev_after_spread_value is None:
        ev_after_spread_value = display.get("ev")
    if ev_after_spread_value is None:
        ev_after_spread_value = edge
    phase2_detail = self._phase2_observability_payload(
        ticker=ticker or self._ticker_from_market_id(outcome.market_id),
        market_id=outcome.market_id,
        side=candidate_side,
        epoch_start=display.get("market_epoch_start", display.get("epoch_start", display.get("epoch_start_ts"))),
        seconds_remaining=seconds_remaining,
        market_price=display.get("market_price", display.get("ask_price", display.get("entry_price"))),
        fair_value=fair_value,
        true_probability=true_probability,
        ev_after_spread=ev_after_spread_value,
        skip_reason=normalized_reason or raw_reason,
        orderbook_readiness_reason=display.get("orderbook_readiness_reason", display.get("orderbook_unavailable_reason", "")),
        liquidity_state=display.get("liquidity_state", ""),
        spread_normalized=display.get("spread_normalized"),
        risk_plan=outcome.risk_plan,
    )
    decision_id = TraderObservabilityHelper._phase2_candidate_hash(
        "decision",
        outcome.market_id,
        (ticker or self._ticker_from_market_id(outcome.market_id) or "UNKNOWN").upper(),
        str(candidate_side or "UNKNOWN").upper(),
        self._diagnostic_int(display.get("market_epoch_start", display.get("epoch_start", display.get("epoch_start_ts")))) or 0,
    )
    for field_name in (
        "lifecycle_phase",
        "candidate_id",
        "signal_id",
        "token_ready_at",
        "token_ready_seconds_remaining",
        "orderbook_ready_at",
        "orderbook_ready_seconds_remaining",
        "liquidity_ready_at",
        "liquidity_ready_seconds_remaining",
        "spread_ready_at",
        "spread_ready_seconds_remaining",
        "first_tradable_at",
        "first_tradable_seconds_remaining",
        "first_evaluable_at",
        "first_evaluable_ready_seconds_remaining",
        "first_seen_second",
        "first_orderbook_ready_second",
        "first_candidate_ready_second",
        "candidate_lifecycle_duration_seconds",
        "candidate_lifecycle_duration",
        "fair_value",
        "fair_value_available",
        "fair_value_null_reason",
        "market_price",
        "market_price_available",
        "market_price_null_reason",
        "true_probability",
        "true_probability_available",
        "true_probability_null_reason",
        "ev_after_spread",
        "ev_after_spread_available",
        "ev_after_spread_null_reason",
        "model_probability_yes",
        "model_probability_no",
        "fair_value_yes",
        "fair_value_no",
        "model_attempted",
        "probability_model_called",
        "probability_model_output_visible",
        "model_output_missing_reason",
        "model_output_source",
        "model_handoff_stage",
        "pre_model_gate_name",
        "pre_model_gate_group",
        "pre_model_gate_reason",
        "pre_model_gate_source",
        "pre_model_gate_blocks_probability_model",
        "probability_model_call_path",
        "model_not_run_reason",
        "probability_model_gate_reason",
        "probability_model_stage",
        "ev_calculation_stage",
        "mfe_candidate_price",
        "mae_candidate_price",
        "candidate_peak_favorable",
        "candidate_peak_adverse",
        "starter_candidate",
        "reload_candidate",
        "unload_candidate",
        "final_derisk_candidate",
        "inventory_action",
        "exposure_before",
        "exposure_after",
        "risk_budget_used",
        "remaining_risk_budget",
        "current_exposure",
        "target_exposure",
        "model_activation_state",
        "model_activation_block_group",
        "model_activation_block_reason",
        "model_attempt_eligible",
        "model_activation_effective_cutoff_seconds",
        "model_activation_hard_block_seconds",
        "model_activation_lifecycle_phase",
        "model_activation_orderbook_state",
        "model_activation_market_readiness_state",
        "token_id",
        "yes_token_id",
        "no_token_id",
        "condition_id",
        "market_slug",
        "cached_token_pair_available",
        "yes_no_token_pair_present",
        "decision_token_handoff_source",
        "yes_bid",
        "yes_ask",
        "no_bid",
        "no_ask",
        "yes_bid_size",
        "yes_ask_size",
        "no_bid_size",
        "no_ask_size",
        "yes_mid",
        "no_mid",
        "spread",
        "spread_normalized",
        "spread_limit",
        "spread_gap_to_limit",
        "orderbook_bid",
        "orderbook_ask",
        "orderbook_bid_size",
        "orderbook_ask_size",
        "first_model_eligible_second",
        "seconds_remaining_when_eligible",
        "first_probability_output_second",
        "seconds_remaining_when_model_output_visible",
        "model_eligible_at_or_inside_cutoff",
        "decision_cycle_started_at",
        "last_orderbook_refresh_at",
        "orderbook_snapshot_age_ms_at_decision",
        "last_successful_yes_no_book_at",
        "orderbook_refresh_source",
        "orderbook_refresh_trigger",
        "decision_cycle_interval_seconds",
        "actual_market_revisit_frequency_seconds",
        "orderbook_reuse_detected",
        "executable_book_last_seen_age_ms",
        "decision_token_pair_key",
        "last_orderbook_refresh_token_pair_key",
        "last_successful_yes_no_book_token_pair_key",
        "orderbook_lineage_match",
        "orderbook_current_fetch_status",
        "orderbook_stale_reuse_source",
        "scheduler_cadence_source",
        "hot_path_timing_source",
        "configured_decision_loop_interval_seconds",
        "intended_decision_loop_target_seconds",
        "effective_outer_loop_interval_seconds",
        "snapshot_sampling_interval_seconds",
        "market_discovery_interval_seconds",
        "outer_loop_poll_interval_seconds",
        "market_evaluation_asset",
        "market_evaluation_started_at",
        "market_evaluation_started_ms_since_cycle",
        "market_evaluation_duration_ms",
        "market_sequence_index",
        "market_sequence_count",
        "cycle_elapsed_ms_at_market_evaluation",
        "candidate_created_at",
        "candidate_enqueue_at",
        "candidate_dequeue_at",
        "candidate_queue_age_ms",
        "hot_path_admission_wait_ms",
        "candidate_queue_age_source",
        "candidate_queue_ownership",
        "candidate_revisit_scheduling_source",
        "hot_path_admission_trigger",
        "event_vs_polling_classification",
        "executable_liquidity_event_role",
        "executable_liquidity_triggered_hot_path",
        "market_snapshot_decision_pipeline_linkage",
        "candidate_handoff_boundary",
        "empty_book_recovery_duration_ms",
        # Observability v1: probability model inputs
        "probability_model_reason",
        "prob_model_momentum_input",
        "prob_model_liquidity_usd",
        # Observability v2: signal and regime inputs (additive, read-only)
        "price_change_pct",
        "realized_volatility",
        "price_velocity",
        "distance_from_ptb_pct",
        # Two-tier signal attribution (Patch 6B)
        "signal_name",
        "signal_reason",
        "strategy_signal_name",
        "strategy_signal_reason",
    ):
        value = display.get(field_name)
        if value is not None and value != "":
            phase2_detail[field_name] = value
    payload: dict[str, object] = {
        "decision_id": decision_id,
        "raw_skip_reason": raw_reason,
        "normalized_skip_reason": normalized_reason,
        "asset": ticker or self._ticker_from_market_id(outcome.market_id),
        "side": str(candidate_side or "UNKNOWN").upper(),
        "market_slug": str(display.get("market_slug", "") or self._market_slug_for_ticker(ticker, outcome.market_id)),
        "edge": self._diagnostic_float(edge),
        "ev": self._diagnostic_float(display.get("ev", edge or 0.0)),
        "decision_timestamp": decision_timestamp,
        "decision_latency_ms": self._cycle_elapsed_ms(),
        "scan_cycle_duration_ms": self._cycle_elapsed_ms(),
        "seconds_remaining": self._diagnostic_int(seconds_remaining),
        "entry_cutoff_seconds": self._diagnostic_int(entry_cutoff_seconds),
        "effective_cutoff_seconds": self._diagnostic_int(display.get("effective_cutoff_seconds", entry_cutoff_seconds)),
        "cutoff_policy": str(display.get("cutoff_policy", "static") or "static"),
        "adaptive_cutoff_allowed": bool(display.get("adaptive_cutoff_allowed", False)),
        "adaptive_cutoff_reason": str(display.get("adaptive_cutoff_reason", "") or ""),
        "late_entry_hard_block": bool(display.get("late_entry_hard_block", False)),
        "micro_timing_allowed": bool(display.get("micro_timing_allowed", False)),
        "micro_timing_denied_reason": str(display.get("micro_timing_denied_reason", "") or ""),
        "effective_micro_cutoff_seconds": self._diagnostic_int(display.get("effective_micro_cutoff_seconds")) or 0,
        "micro_cutoff_policy": str(display.get("micro_cutoff_policy", "") or "standard"),
        "micro_timing_branch_entered": bool(display.get("micro_timing_branch_entered", False)),
        "micro_timing_branch_skipped_reason": str(display.get("micro_timing_branch_skipped_reason", "") or ""),
        "micro_timing_candidate": bool(display.get("micro_timing_candidate", False)),
        "cutoff_block_seconds_remaining": cutoff_block_seconds_remaining,
        "time_bucket": time_bucket,
        "epoch_start": self._diagnostic_int(display.get("epoch_start", display.get("epoch_start_ts"))),
        "market_epoch_start": self._diagnostic_int(display.get("market_epoch_start", display.get("epoch_start_ts"))),
        "market_epoch_end": self._diagnostic_int(display.get("market_epoch_end", display.get("epoch_end_ts"))),
        "seconds_since_open": self._diagnostic_int(display.get("seconds_since_open")),
        "seconds_until_close": self._diagnostic_int(display.get("seconds_until_close", seconds_remaining)),
        "first_seen_seconds_remaining": self._diagnostic_int(display.get("first_seen_seconds_remaining")),
        "first_evaluable_seconds_remaining": self._diagnostic_int(display.get("first_evaluable_seconds_remaining")),
        "first_tradable_seconds_remaining": self._diagnostic_int(display.get("first_tradable_seconds_remaining")),
        "first_seen_second": self._diagnostic_int(display.get("first_seen_second", phase2_detail.get("first_seen_second"))),
        "first_orderbook_ready_second": self._diagnostic_int(display.get("first_orderbook_ready_second", phase2_detail.get("first_orderbook_ready_second"))),
        "first_candidate_ready_second": self._diagnostic_int(display.get("first_candidate_ready_second", phase2_detail.get("first_candidate_ready_second"))),
        "candidate_lifecycle_duration_seconds": self._diagnostic_int(display.get("candidate_lifecycle_duration_seconds", phase2_detail.get("candidate_lifecycle_duration_seconds"))),
        "candidate_lifecycle_duration": self._diagnostic_int(display.get("candidate_lifecycle_duration", phase2_detail.get("candidate_lifecycle_duration"))),
        "first_tradable_at_utc": str(display.get("first_tradable_at_utc", phase2_detail.get("first_tradable_at", "")) or ""),
        **phase2_detail,
        "active_window_alignment_reason": str(display.get("active_window_alignment_reason", "") or ""),
        "market_start_time": str(display.get("market_start_time", "") or ""),
        "market_end_time": str(display.get("market_end_time", "") or ""),
        "market_close_timestamp": market_close_timestamp,
        "token_id": str(display.get("token_id") or phase2_detail.get("token_id") or ""),
        "yes_token_id": str(display.get("yes_token_id") or phase2_detail.get("yes_token_id") or ""),
        "no_token_id": str(display.get("no_token_id") or phase2_detail.get("no_token_id") or ""),
        "condition_id": str(display.get("condition_id") or phase2_detail.get("condition_id") or ""),
        "outcome": str(display.get("outcome", "") or ""),
        "source_module": str(display.get("source_module", "polymarket.trader") or "polymarket.trader"),
        "orderbook_age_ms": orderbook_age_ms,
        "orderbook_age": round(orderbook_age_ms / 1000.0, 3),
        "orderbook_age_seconds": round(orderbook_age_ms / 1000.0, 3),
        "orderbook_readiness_reason": str(display.get("orderbook_readiness_reason", "") or ""),
        "orderbook_unavailable_reason": str(display.get("orderbook_unavailable_reason", "") or ""),
        "orderbook_error": str(display.get("orderbook_error", "") or ""),
        "clob_error_category": str(display.get("clob_error_category", "") or ""),
        "clob_error_class": str(display.get("clob_error_class", "") or ""),
        "clob_exception_type": str(display.get("clob_exception_type", "") or ""),
        "clob_status_code": self._diagnostic_int(display.get("clob_status_code")),
        "clob_token_id_present": bool(display.get("clob_token_id_present", False)),
        "clob_parse_failure": bool(display.get("clob_parse_failure", False)),
        "clob_api_failure": bool(display.get("clob_api_failure", False)),
        "clob_error_rate": self._diagnostic_float(display.get("clob_error_rate")),
        "clob_backoff_active": bool(display.get("clob_backoff_active", False)),
        "clob_circuit_open": bool(display.get("clob_circuit_open", False)),
        "clob_cooldown_seconds_remaining": self._diagnostic_float(display.get("clob_cooldown_seconds_remaining")),
        "clob_recovery_count": self._diagnostic_int(display.get("clob_recovery_count")),
        "market_data_degraded": bool(display.get("market_data_degraded", False)),
        "retry_count": self._diagnostic_int(display.get("retry_count")),
        "empty_book_recovery_attempted": bool(display.get("empty_book_recovery_attempted", False)),
        "empty_book_recovery_success": bool(display.get("empty_book_recovery_success", False)),
        "empty_book_recovery_failed": bool(display.get("empty_book_recovery_failed", False)),
        "empty_book_recovery_retry_count": self._diagnostic_int(display.get("empty_book_recovery_retry_count")) or 0,
        "liquidity_state": str(display.get("liquidity_state", "") or "HEALTHY"),
        **{
            field_name: display.get(field_name, self._empty_book_recovery_detail().get(field_name))
            for field_name in EMPTY_BOOK_RECOVERY_RESEARCH_FIELD_NAMES
        },
        "oracle_age_ms": oracle_age_ms,
        "oracle_age": round(oracle_age_ms / 1000.0, 3),
        "oracle_age_seconds": round(oracle_age_ms / 1000.0, 3),
        "market_feed_age_ms": market_feed_age_ms,
        "market_feed_age_seconds": round(market_feed_age_ms / 1000.0, 3),
        "volatility_regime": str(display.get("volatility_regime", regime_detail["volatility_regime"]) or "UNKNOWN"),
        "volatility_score": self._diagnostic_float(display.get("volatility_score", regime_detail["volatility_score"])),
        "trend_regime": str(display.get("trend_regime", regime_detail["trend_regime"]) or "UNKNOWN"),
        "trend_strength": self._diagnostic_float(display.get("trend_strength", regime_detail["trend_strength"])),
        "market_regime": str(display.get("market_regime", "") or regime_detail.get("market_regime", "UNKNOWN") or "UNKNOWN"),
        "bullish_probability": self._diagnostic_float(display.get("bullish_probability", display.get("p_yes", 0.5))),
        "bearish_probability": self._diagnostic_float(display.get("bearish_probability", display.get("p_no", 0.5))),
        "reversal_risk": self._diagnostic_float(display.get("reversal_risk", 0.0)),
        "compression_score": self._diagnostic_float(display.get("compression_score", 0.0)),
        "signal_trend_strength": self._diagnostic_float(display.get("signal_trend_strength", display.get("trend_strength", 0.0))),
        "signal_volatility_score": self._diagnostic_float(display.get("signal_volatility_score", display.get("volatility_score", 0.0))),
        "indicator_evidence": str(display.get("indicator_evidence", "") or ""),
        "regime_reason": str(display.get("regime_reason", regime_detail["regime_reason"]) or ""),
        "token_mapping_warning": str(display.get("token_mapping_warning", "") or ""),
        "paper_virtual_cash": float(self.bankroll_state.current_cash_balance if self.settings.paper_trading else 0.0),
        "paper_available_balance": float(self._paper_available_balance() if self.settings.paper_trading else 0.0),
        "paper_open_position_value": float(self.bankroll_state.open_position_market_value if self.settings.paper_trading else 0.0),
        **self._bankroll_tier_detail(),
        **self._bankroll_mode_detail(),
        "live_wallet_reference_balance": (
            float(self._wallet_reference_balance)
            if self._wallet_reference_balance is not None and self._paper_wallet_reference_visible()
            else None
        ),
        "risk_per_trade": float(getattr(outcome.risk_plan, "risk_amount", 0.0) or 0.0),
        "calculated_order_size": float(getattr(outcome.risk_plan, "position_size", 0.0) or 0.0),
        "risk_plan_zero_reason": "",
    }
    for key, value in self._scheduler_cadence_observability_detail(
        str(ticker or self._ticker_from_market_id(outcome.market_id) or "")
    ).items():
        if payload.get(key) in (None, ""):
            payload[key] = value
    if not bool(payload.get("ev_after_spread_available")) and not TraderObservabilityHelper._phase2_value_available(payload.get("ev_after_spread")):
        ev_stage = str(payload.get("ev_calculation_stage") or "").lower()
        probability_stage = str(payload.get("probability_model_stage") or "").lower()
        if probability_stage == "pre_model_skip":
            payload["ev_missing_reason"] = "model_not_run"
        elif ev_stage in {"candidate_blocked_before_ev", "pre_model_skip"}:
            payload["ev_missing_reason"] = "not_computed_at_producer"
        else:
            payload["ev_missing_reason"] = str(payload.get("ev_after_spread_null_reason") or "field_not_available")
    if bool(payload.get("model_attempted")):
        payload["model_not_run_reason"] = ""
        payload["probability_model_gate_reason"] = str(
            payload.get("probability_model_gate_reason") or "model_output_visible"
        )
    yes_token_present = bool(str(payload.get("yes_token_id") or "").strip())
    no_token_present = bool(str(payload.get("no_token_id") or "").strip())
    payload["yes_no_token_pair_present"] = bool(yes_token_present and no_token_present)
    if payload["yes_no_token_pair_present"] and str(payload.get("decision_token_handoff_source") or "not_available") == "not_available":
        payload["decision_token_handoff_source"] = "decision_payload_or_cache"
    yes_bid_present = TraderObservabilityHelper._phase2_value_available(payload.get("yes_bid"))
    yes_ask_present = TraderObservabilityHelper._phase2_value_available(payload.get("yes_ask"))
    no_bid_present = TraderObservabilityHelper._phase2_value_available(payload.get("no_bid"))
    no_ask_present = TraderObservabilityHelper._phase2_value_available(payload.get("no_ask"))
    serialized_executable_book = bool(
        yes_bid_present and yes_ask_present and no_bid_present and no_ask_present
    )
    payload["decision_orderbook_bid_fields_present"] = bool(yes_bid_present and no_bid_present)
    payload["decision_orderbook_ask_fields_present"] = bool(yes_ask_present and no_ask_present)
    if serialized_executable_book:
        payload["decision_orderbook_completeness_source"] = "serialized_yes_no_bid_ask"
    elif yes_ask_present or no_ask_present or yes_bid_present or no_bid_present:
        payload["decision_orderbook_completeness_source"] = "partial_serialized_yes_no_book"
    else:
        payload["decision_orderbook_completeness_source"] = "not_serialized_or_unavailable"
    current_fetch_status = str(
        display.get("orderbook_current_fetch_status")
        or phase2_detail.get("orderbook_current_fetch_status")
        or ""
    )
    if current_fetch_status in {"fresh_fetch_executable", "fresh_fetch_non_executable"}:
        current_fetch_succeeded = True
    elif current_fetch_status == "fresh_fetch_failed":
        current_fetch_succeeded = False
    else:
        current_fetch_succeeded = None
    current_fetch_executable = bool(
        serialized_executable_book or current_fetch_status == "fresh_fetch_executable"
    )
    payload.update(
        self._orderbook_refresh_observability_detail(
            str(ticker or self._ticker_from_market_id(outcome.market_id) or ""),
            current_executable_yes_no_book=current_fetch_executable,
            current_fetch_succeeded=current_fetch_succeeded,
            condition_id=display.get("condition_id") or phase2_detail.get("condition_id", ""),
            yes_token_id=display.get("yes_token_id") or phase2_detail.get("yes_token_id", ""),
            no_token_id=display.get("no_token_id") or phase2_detail.get("no_token_id", ""),
            market_slug=display.get("market_slug") or phase2_detail.get("market_slug", ""),
            record_decision_cycle=True,
        )
    )
    authoritative_book_available, authoritative_book_source = self._phase2_authoritative_orderbook_availability(payload)
    payload["orderbook_available_for_decision"] = bool(authoritative_book_available)
    payload["orderbook_availability_source"] = authoritative_book_source or "none"
    if (
        authoritative_book_available
        and payload["decision_orderbook_completeness_source"] == "not_serialized_or_unavailable"
    ):
        payload["decision_orderbook_completeness_source"] = "authoritative_readiness_without_serialized_book"
    orderbook_state = self._phase2_orderbook_state_classification(payload)
    readiness_state = self._phase2_market_readiness_state(payload, orderbook_state)
    payload["orderbook_state_classification"] = orderbook_state
    payload["market_readiness_state"] = readiness_state
    skip_text = " ".join(
        str(part or "").lower()
        for part in (
            normalized_reason,
            raw_reason,
            payload.get("adaptive_cutoff_reason"),
            payload.get("active_window_alignment_reason"),
        )
        if part
    )
    if authoritative_book_available and any(
        token in skip_text for token in ("time_unsafe", "cutoff", "hard_close", "too_late")
    ):
        payload["orderbook_availability_classification"] = "orderbook_available_but_skipped_by_cutoff"
    elif authoritative_book_available and outcome.skipped:
        payload["orderbook_availability_classification"] = "orderbook_available_but_skipped"
    elif authoritative_book_available:
        payload["orderbook_availability_classification"] = "orderbook_available"
    elif orderbook_state in {"unavailable", "orderbook_unavailable"}:
        payload["orderbook_availability_classification"] = "true_orderbook_unavailable"
    else:
        payload["orderbook_availability_classification"] = "orderbook_not_authoritatively_available"
    model_output_ready = (
        bool(payload.get("model_attempted"))
        or bool(payload.get("fair_value_available"))
        or bool(payload.get("true_probability_available"))
        or TraderObservabilityHelper._phase2_value_available(payload.get("fair_value"))
        or TraderObservabilityHelper._phase2_value_available(payload.get("true_probability"))
    )
    payload.update(
        self._phase2_model_activation_detail(
            payload,
            lifecycle_phase=str(payload.get("lifecycle_phase") or "UNKNOWN"),
            orderbook_state=orderbook_state,
            readiness_state=readiness_state,
            model_output_ready=model_output_ready,
        )
    )
    if model_output_ready:
        payload["probability_model_called"] = bool(payload.get("probability_model_called")) or True
        payload["probability_model_output_visible"] = True
        payload["model_handoff_stage"] = "MODEL_OUTPUT_SERIALIZED"
        payload["model_output_missing_reason"] = ""
        payload.setdefault("model_output_source", "decision_payload")
    else:
        payload["probability_model_called"] = bool(payload.get("probability_model_called"))
        payload["probability_model_output_visible"] = False
        payload["model_handoff_stage"] = str(
            payload.get("model_handoff_stage")
            or ("PRE_MODEL_GATE" if payload.get("model_activation_state") == "BLOCKED_BEFORE_MODEL" else "MODEL_OUTPUT_NOT_VISIBLE")
        )
        payload["model_output_missing_reason"] = str(
            payload.get("model_activation_block_reason")
            or payload.get("model_output_missing_reason")
            or payload.get("probability_model_gate_reason")
            or "model_output_not_visible"
        )
        payload.setdefault("model_output_source", "")
    is_zero_plan = (
        outcome.skipped
        and normalized_reason == "risk_plan_zero"
        and outcome.risk_plan is not None
        and float(getattr(outcome.risk_plan, "position_size", 0.0) or 0.0) <= 0.0
    )
    if is_zero_plan:
        payload["risk_plan_zero_reason"] = self._risk_plan_zero_reason(outcome.risk_plan, fallback_reason=raw_reason)
        payload["risk_plan_zero_diagnostics"] = self._risk_plan_zero_diagnostics(
            outcome.risk_plan,
            confidence=outcome.confidence,
            edge=edge,
        )
    elif outcome.skipped and outcome.risk_plan is not None:
        classified = self._risk_plan_zero_reason(outcome.risk_plan, fallback_reason=raw_reason)
        if classified != "unknown":
            payload["risk_plan_zero_reason"] = classified
    # No-Entry Root Cause Classifier v1 - additive observability fields, fail-soft
    try:
        from utils.no_entry_root_cause_classifier import classify_no_entry_root_cause as _classify_root_cause
        _root_cause = _classify_root_cause(payload)
        for _k, _v in _root_cause.items():
            if _k not in payload or payload[_k] in (None, ""):
                payload[_k] = _v
    except Exception:
        pass
    # Market Readiness Admission Probe v1 - additive observability fields, fail-soft
    try:
        from utils.admission_probe_classifier import classify_admission_probe as _classify_probe
        _probe = _classify_probe(payload)
        for _k, _v in _probe.items():
            if _k not in payload or payload[_k] in (None, ""):
                payload[_k] = _v
    except Exception:
        pass
    # Executable State Persistence Probe v1 - additive observability fields, fail-soft
    try:
        from utils.executable_state_persistence_classifier import (
            classify_executable_state_persistence as _classify_persistence,
        )
        _persistence = _classify_persistence(payload)
        for _k, _v in _persistence.items():
            if _k not in payload or payload[_k] in (None, ""):
                payload[_k] = _v
    except Exception:
        pass
    return payload
