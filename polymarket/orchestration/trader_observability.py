from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, UTC
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from config.settings import Settings
from polymarket.trader_presentation import TraderPresentationHelper

LOGGER = logging.getLogger(__name__)


class TraderObservabilityHelper:
    """Helper owning display state, recent trades, and health monitoring for PolymarketTrader."""

    def __init__(self, settings: "Settings | None" = None) -> None:
        self.settings = settings
        self._presentation = TraderPresentationHelper()
        self._recent_display_trades: deque[dict[str, Any]] = deque(maxlen=12)
        self._observability_health_display_state: dict[str, Any] = self._presentation.default_observability_health_display_state()
        # Batch 3B-1: orderbook refresh timing state
        self._last_orderbook_refresh_at_utc: dict[str, str] = {}
        self._last_orderbook_refresh_monotonic: dict[str, float] = {}
        self._last_orderbook_refresh_source: dict[str, str] = {}
        self._last_orderbook_refresh_trigger: dict[str, str] = {}
        self._last_orderbook_refresh_token_pair_key: dict[str, str] = {}
        self._last_successful_yes_no_book_at_utc: dict[str, str] = {}
        self._last_successful_yes_no_book_monotonic: dict[str, float] = {}
        self._last_successful_yes_no_book_token_pair_key: dict[str, str] = {}

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

    # ------------------------------------------------------------------
    # Batch 3B-1: orderbook refresh timing helpers
    # ------------------------------------------------------------------

    def _mark_orderbook_refresh(
        self,
        ticker: str,
        *,
        source: str,
        trigger: str,
        now_mono: float,
        now_utc: str,
        token_pair_key: str,
        executable_yes_no_book: bool = False,
    ) -> None:
        """Mutate orderbook refresh timing state. Caller pre-computes now_mono/now_utc/token_pair_key."""
        ticker_key = ticker.upper()
        self._last_orderbook_refresh_monotonic[ticker_key] = now_mono
        self._last_orderbook_refresh_at_utc[ticker_key] = now_utc
        self._last_orderbook_refresh_source[ticker_key] = source
        self._last_orderbook_refresh_trigger[ticker_key] = trigger
        self._last_orderbook_refresh_token_pair_key[ticker_key] = token_pair_key
        if executable_yes_no_book:
            self._last_successful_yes_no_book_monotonic[ticker_key] = now_mono
            self._last_successful_yes_no_book_at_utc[ticker_key] = now_utc
            self._last_successful_yes_no_book_token_pair_key[ticker_key] = token_pair_key

    def _orderbook_refresh_observability_detail(
        self,
        trader: Any,
        ticker: str,
        *,
        current_executable_yes_no_book: bool = False,
        record_decision_cycle: bool = False,
        current_fetch_succeeded: "bool | None" = None,
        condition_id: object = "",
        yes_token_id: object = "",
        no_token_id: object = "",
        market_slug: object = "",
    ) -> "dict[str, object]":
        """Return orderbook refresh observability payload.

        Reads _last_decision_cycle_monotonic and _cycle_started_at_utc from
        trader (deferred fields — not yet migrated to helper). Reads all 8
        moved fields from self.*. Calls trader._orderbook_token_pair_key()
        for the pair-key computation.
        """
        ticker_key = ticker.upper()
        now_mono = time.monotonic()
        last_refresh_mono = self._last_orderbook_refresh_monotonic.get(ticker_key)
        last_success_mono = self._last_successful_yes_no_book_monotonic.get(ticker_key)
        previous_decision_mono = getattr(trader, "_last_decision_cycle_monotonic", {}).get(ticker_key)
        decision_interval = None
        if record_decision_cycle:
            if previous_decision_mono is not None:
                decision_interval = round(max(0.0, now_mono - previous_decision_mono), 3)
            if not hasattr(trader, "_last_decision_cycle_monotonic"):
                trader._last_decision_cycle_monotonic = {}
            trader._last_decision_cycle_monotonic[ticker_key] = now_mono
        refresh_age_ms = (
            int(max(0.0, now_mono - last_refresh_mono) * 1000)
            if last_refresh_mono is not None
            else None
        )
        executable_age_ms = (
            int(max(0.0, now_mono - last_success_mono) * 1000)
            if last_success_mono is not None
            else None
        )
        decision_token_pair_key = trader._orderbook_token_pair_key(
            condition_id=condition_id,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id,
            market_slug=market_slug,
        )
        last_refresh_pair = self._last_orderbook_refresh_token_pair_key.get(ticker_key, "")
        last_success_pair = self._last_successful_yes_no_book_token_pair_key.get(ticker_key, "")
        lineage_match = bool(decision_token_pair_key and last_success_pair and decision_token_pair_key == last_success_pair)
        if current_fetch_succeeded is True and current_executable_yes_no_book:
            fetch_status = "fresh_fetch_executable"
            stale_source = "CURRENT_DECISION_FETCH_EXECUTABLE"
        elif current_fetch_succeeded is True:
            fetch_status = "fresh_fetch_non_executable"
            stale_source = (
                "CURRENT_FETCH_NON_EXECUTABLE_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR"
                if lineage_match
                else "CURRENT_FETCH_NON_EXECUTABLE_PRIOR_EXECUTABLE_DIFFERENT_OR_UNKNOWN_PAIR"
                if last_success_mono is not None
                else "CURRENT_FETCH_NON_EXECUTABLE_NO_PRIOR_EXECUTABLE"
            )
        elif current_fetch_succeeded is False:
            fetch_status = "fresh_fetch_failed"
            stale_source = (
                "CURRENT_FETCH_FAILED_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR"
                if lineage_match
                else "CURRENT_FETCH_FAILED_PRIOR_EXECUTABLE_DIFFERENT_OR_UNKNOWN_PAIR"
                if last_success_mono is not None
                else "CURRENT_FETCH_FAILED_NO_PRIOR_EXECUTABLE"
            )
        else:
            fetch_status = "fresh_fetch_not_attempted_or_unobserved"
            stale_source = (
                "NO_CURRENT_FETCH_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR"
                if lineage_match
                else "NO_CURRENT_FETCH_PRIOR_EXECUTABLE_DIFFERENT_OR_UNKNOWN_PAIR"
                if last_success_mono is not None
                else "NO_CURRENT_FETCH_NO_PRIOR_EXECUTABLE"
            )
        return {
            "decision_cycle_started_at": str(getattr(trader, "_cycle_started_at_utc", "") or ""),
            "last_orderbook_refresh_at": self._last_orderbook_refresh_at_utc.get(ticker_key, ""),
            "orderbook_snapshot_age_ms_at_decision": refresh_age_ms,
            "last_successful_yes_no_book_at": self._last_successful_yes_no_book_at_utc.get(ticker_key, ""),
            "orderbook_refresh_source": self._last_orderbook_refresh_source.get(ticker_key, ""),
            "orderbook_refresh_trigger": self._last_orderbook_refresh_trigger.get(ticker_key, ""),
            "decision_token_pair_key": decision_token_pair_key,
            "last_orderbook_refresh_token_pair_key": last_refresh_pair,
            "last_successful_yes_no_book_token_pair_key": last_success_pair,
            "orderbook_lineage_match": lineage_match,
            "orderbook_current_fetch_status": fetch_status,
            "orderbook_stale_reuse_source": stale_source,
            "decision_cycle_interval_seconds": decision_interval,
            "actual_market_revisit_frequency_seconds": decision_interval,
            "orderbook_reuse_detected": bool(
                last_success_mono is not None and not current_executable_yes_no_book
            ),
            "executable_book_last_seen_age_ms": executable_age_ms,
        }
