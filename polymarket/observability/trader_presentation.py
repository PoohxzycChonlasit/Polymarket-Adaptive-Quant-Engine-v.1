"""
Presentation helper for PolymarketTrader.

Contains pure UI/formatting/display logic extracted from trader.py.
No runtime trading logic, no risk logic, no execution logic.
PolymarketTrader keeps all original method names as thin proxy delegates.
"""
from __future__ import annotations

from typing import Any


class TraderPresentationHelper:
    """Stateless helper for UI formatting and display-only computations."""

    # ------------------------------------------------------------------
    # Label formatters — pure functions, no state
    # ------------------------------------------------------------------

    def momentum_label(self, momentum: float) -> str:
        if momentum > 0.0005:
            return "UP"
        if momentum < -0.0005:
            return "DOWN"
        return "FLAT"

    def volatility_label(self, volatility: float) -> str:
        if volatility >= 0.006:
            return "HIGH"
        if volatility >= 0.002:
            return "MEDIUM"
        return "LOW"

    def liquidity_label(self, liquidity: float) -> str:
        if liquidity >= 100.0:
            return "GOOD"
        if liquidity >= 25.0:
            return "OK"
        return "WEAK"

    def edge_label(self, ev: float, min_ev: float) -> str:
        if ev >= min_ev + 0.02:
            return "GOOD"
        if ev >= min_ev:
            return "OK"
        return "BAD"

    # ------------------------------------------------------------------
    # Display field helpers — pure functions on payload dicts
    # ------------------------------------------------------------------

    def display_field_present(self, payload: dict[str, Any], *fields: str) -> bool:
        for field in fields:
            value = payload.get(field)
            if value is not None and str(value).strip() not in {"", "--", "None", "UNKNOWN"}:
                return True
        return False

    def display_visibility_status(self, payload: dict[str, Any], *fields: str) -> str:
        for field in fields:
            if field not in payload:
                continue
            value = payload.get(field)
            if isinstance(value, bool):
                return "YES" if value else "NO"
            if isinstance(value, (int, float)):
                return "YES" if float(value) != 0.0 else "NO"
            return "YES" if self.display_field_present(payload, field) else "NO"
        return "UNKNOWN"

    def display_identity_readiness(self, payload: dict[str, Any]) -> str:
        explicit = str(payload.get("identity_readiness") or payload.get("candidate_trace_confidence") or "").upper()
        if explicit in {"DIRECT", "STRONG", "WEAK", "PROXY", "UNKNOWN"}:
            return explicit
        has_trace = self.display_field_present(payload, "candidate_trace_id")
        has_parent = self.display_field_present(payload, "parent_candidate_trace_id")
        has_market = self.display_field_present(payload, "market_key", "market_slug", "condition_id", "market_id", "source_market_id")
        has_token = self.display_field_present(payload, "token_id")
        has_side = self.display_field_present(payload, "side", "outcome", "best_side")
        has_phase = self.display_field_present(payload, "lifecycle_phase")
        if has_trace and has_parent and has_market and has_token and has_side and has_phase:
            return "DIRECT"
        if has_market and has_token and has_side and has_phase:
            return "STRONG"
        if sum((has_market, has_token, has_side, has_phase)) >= 3:
            return "WEAK"
        if any((has_trace, has_market, has_token, has_side, has_phase)):
            return "PROXY"
        return "UNKNOWN"

    def display_dominant_model_gap(self, payload: dict[str, Any]) -> str:
        for field in (
            "dominant_model_gap",
            "dominant_model_gap_reason",
            "dominant_model_state_gap",
            "model_state_gap",
            "ev_after_spread_null_reason",
            "true_probability_null_reason",
            "fair_value_null_reason",
            "market_price_null_reason",
        ):
            value = str(payload.get(field) or "").strip()
            if value and value not in {"--", "UNKNOWN"}:
                return value
        if self.display_visibility_status(payload, "ev_after_spread", "ev") == "YES":
            return "--"
        return "UNKNOWN"

    # ------------------------------------------------------------------
    # Observability health default state
    # ------------------------------------------------------------------

    def default_observability_health_display_state(self) -> dict[str, Any]:
        return {
            "jsonl_status": "UNKNOWN",
            "jsonl_ok": False,
            "latest_producer": "--",
            "latest_schema_version": "--",
            "trace_enrichment_status": "UNKNOWN",
            "condition_enrichment_status": "UNKNOWN",
            "trace_id_enrichment_ok": False,
            "condition_id_enrichment_ok": False,
            "candidate_trace_id_present": False,
            "condition_id_present": False,
            "token_id_present": False,
            "side_present": False,
            "event_identity_readiness": "UNKNOWN",
            "candidate_chain_trace_confidence": "UNKNOWN",
            "identity_readiness": "UNKNOWN",
            "model_attempted": "UNKNOWN",
            "probability_visible": "UNKNOWN",
            "fair_value_visible": "UNKNOWN",
            "ev_visible": "UNKNOWN",
            "dominant_model_gap": "UNKNOWN",
            "dominant_model_gap_reason": "UNKNOWN",
            "blocked_before_risk_count": 0,
            "dominant_pre_risk_cause": "UNKNOWN",
            "dominant_pre_risk_block_reason": "UNKNOWN",
            "risk_reachability_status": "UNKNOWN",
            "risk_serialization_status": "UNKNOWN",
            "risk_serialization_visibility": "UNKNOWN",
        }

    # ------------------------------------------------------------------
    # Event-driven admission packet price detail
    # ------------------------------------------------------------------

    def event_driven_admission_packet_price_detail(
        self,
        ptb_info: Any,
        symbol: str,
    ) -> dict[str, Any]:
        """Build price-context detail dict for market snapshot admission packets.

        ptb_info: SimpleNamespace with .current_price and .price_to_beat attributes.
        Returns a structured dict describing price availability for the snapshot event.
        """
        current_price_raw = getattr(ptb_info, "current_price", None) if ptb_info is not None else None
        price_to_beat_raw = getattr(ptb_info, "price_to_beat", None) if ptb_info is not None else None

        try:
            oracle_price_available = current_price_raw is not None and float(current_price_raw) > 0.0
        except (TypeError, ValueError):
            oracle_price_available = False

        try:
            target_price_available = price_to_beat_raw is not None and float(price_to_beat_raw) > 0.0
        except (TypeError, ValueError):
            target_price_available = False

        packet: dict[str, Any] = {
            "packet_schema_version": "event_driven_admission_packet_v1",
            "price_enrichment_stage": "analyze_market_quant_pre_orderbook",
            "price_enrichment_source": "ptb_info",
            "underlying_symbol": symbol,
            "ptb_context_available": ptb_info is not None,
            "oracle_price_available": oracle_price_available,
        }

        if oracle_price_available:
            packet["underlying_price"] = float(current_price_raw)
            packet["current_price"] = float(current_price_raw)
            packet["underlying_price_source"] = "polymarket_oracle_feed"

        packet["target_price_available"] = target_price_available

        if target_price_available:
            packet["target_price"] = float(price_to_beat_raw)
            packet["price_to_beat"] = float(price_to_beat_raw)
            packet["target_source"] = "ptb_tracker_price_to_beat"
            packet["event_boundary_source"] = "ptb_tracker_price_to_beat"

        packet_schema_price_fields_present = oracle_price_available and target_price_available
        packet["packet_schema_price_fields_present"] = packet_schema_price_fields_present
        packet["packet_created_before_price_context"] = not packet_schema_price_fields_present

        if not oracle_price_available and not target_price_available:
            packet["enrichment_drop_reason"] = "oracle_and_target_missing"
        elif not oracle_price_available:
            packet["enrichment_drop_reason"] = "oracle_missing"
        elif not target_price_available:
            packet["enrichment_drop_reason"] = "target_missing"
        else:
            packet["enrichment_drop_reason"] = ""

        return packet
