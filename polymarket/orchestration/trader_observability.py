from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, UTC
from typing import Any

from config.settings import Settings
from polymarket.trader_presentation import TraderPresentationHelper

LOGGER = logging.getLogger(__name__)


class TraderObservabilityHelper:
    """Helper owning display state, recent trades, and health monitoring for PolymarketTrader."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._presentation = TraderPresentationHelper()
        self._recent_display_trades: deque[dict[str, Any]] = deque(maxlen=12)
        self._observability_health_display_state: dict[str, Any] = self._presentation.default_observability_health_display_state()

    def get_recent_display_trades(self) -> list[dict[str, Any]]:
        return list(self._recent_display_trades)

    def dashboard_observability_health_state(self, trader: Any) -> dict[str, Any]:
        """Return display-only observability health state for terminal UI surfaces."""
        return dict(getattr(self, "_observability_health_display_state", trader._default_observability_health_display_state()))

    def _record_display_trade(
        self,
        *,
        market: str,
        side: str,
        entry_price: float,
        size: float,
        reason: str,
        mode: str,
        exit_price: float | None = None,
        realized_pnl: float = 0.0,
        status: str = "paper",
    ) -> None:
        self._recent_display_trades.appendleft({
            "time": datetime.now(tz=UTC).strftime("%H:%M:%S"),
            "market": market,
            "side": side,
            "entry_price": float(entry_price),
            "exit_price": float(exit_price) if exit_price is not None else None,
            "size": float(size),
            "realized_pnl": float(realized_pnl),
            "reason": reason,
            "mode": mode,
            "status": status,
        })

    def _observability_health_from_payload(
        self,
        trader: Any,
        event_method: str,
        payload: dict[str, object],
        *,
        jsonl_ok: bool,
    ) -> dict[str, object]:
        schema_version = str(getattr(getattr(trader, "quant_events", None), "schema_version", "") or "--")
        producer = trader._event_producer_label(event_method)
        has_trace = trader._display_field_present(payload, "candidate_trace_id")
        has_condition = trader._display_field_present(payload, "condition_id")
        has_token = trader._display_field_present(payload, "token_id")
        has_side = trader._display_field_present(payload, "side", "outcome", "best_side")
        has_probability = trader._display_visibility_status(payload, "true_probability", "p_yes", "model_p_yes")
        has_fair_value = trader._display_visibility_status(payload, "fair_value")
        has_ev = trader._display_visibility_status(payload, "ev_after_spread", "ev")
        model_attempted = trader._display_visibility_status(
            payload,
            "model_attempted",
            "ev_visibility_attempted",
            "probability_model_stage",
            "ev_calculation_stage",
        )
        trace_status = (
            "TRACE+COND"
            if has_trace and has_condition
            else "TRACE_ONLY"
            if has_trace
            else "COND_ONLY"
            if has_condition
            else "UNKNOWN"
        )
        boundary = str(payload.get("decision_to_risk_boundary") or "").upper()
        blocked_before_risk = int(
            bool(payload.get("candidate_blocked_before_risk_visibility"))
            or boundary == "BLOCKED_BEFORE_RISK"
        )
        risk_reachability = str(payload.get("risk_reachability_status") or boundary or "UNKNOWN")
        risk_serialization = str(
            payload.get("risk_serialization_status")
            or payload.get("risk_serialization_visibility")
            or "UNKNOWN"
        )
        pre_risk_cause = str(
            payload.get("dominant_pre_risk_cause")
            or payload.get("dominant_pre_risk_block_reason")
            or payload.get("pre_risk_block_reason")
            or payload.get("normalized_skip_reason")
            or payload.get("skip_reason")
            or "UNKNOWN"
        )
        model_gap = trader._display_dominant_model_gap(payload)
        event_identity = trader._display_identity_readiness(payload)
        chain_confidence = str(
            payload.get("candidate_chain_trace_confidence")
            or payload.get("candidate_trace_confidence")
            or "UNKNOWN"
        ).upper()
        if chain_confidence not in {"DIRECT", "STRONG", "WEAK", "PROXY", "UNKNOWN"}:
            chain_confidence = "UNKNOWN"
        return {
            "jsonl_status": "OK" if jsonl_ok else "WARN",
            "jsonl_ok": bool(jsonl_ok),
            "latest_producer": producer,
            "latest_schema_version": schema_version,
            "trace_enrichment_status": trace_status,
            "condition_enrichment_status": "OK" if has_condition else "UNKNOWN",
            "trace_id_enrichment_ok": has_trace,
            "condition_id_enrichment_ok": has_condition,
            "candidate_trace_id_present": has_trace,
            "condition_id_present": has_condition,
            "token_id_present": has_token,
            "side_present": has_side,
            "event_identity_readiness": event_identity,
            "candidate_chain_trace_confidence": chain_confidence,
            "identity_readiness": event_identity,
            "model_attempted": model_attempted,
            "probability_visible": has_probability,
            "fair_value_visible": has_fair_value,
            "ev_visible": has_ev,
            "dominant_model_gap": model_gap,
            "dominant_model_gap_reason": model_gap,
            "blocked_before_risk_count": blocked_before_risk,
            "dominant_pre_risk_cause": pre_risk_cause,
            "dominant_pre_risk_block_reason": pre_risk_cause,
            "risk_reachability_status": risk_reachability,
            "risk_serialization_status": risk_serialization,
            "risk_serialization_visibility": risk_serialization,
        }
