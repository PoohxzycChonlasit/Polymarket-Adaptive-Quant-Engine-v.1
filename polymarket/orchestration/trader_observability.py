from __future__ import annotations

import hashlib
import logging
import time
from collections import deque
from datetime import datetime, UTC
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from config.settings import Settings
from polymarket.observability.trader_presentation import TraderPresentationHelper

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
        # Batch 3B-2: cadence / scheduler timing state
        self._last_decision_cycle_monotonic: dict[str, float] = {}
        self._market_evaluation_started_monotonic: dict[str, float] = {}
        self._market_evaluation_started_at_utc: dict[str, str] = {}
        self._current_cycle_market_sequence_index: dict[str, int] = {}
        self._current_cycle_market_sequence_count: dict[str, int] = {}

    def get_recent_display_trades(self) -> list[dict[str, Any]]:
        return list(self._recent_display_trades)

    def dashboard_observability_health_state(self, trader: Any) -> dict[str, Any]:
        """Return display-only observability health state for terminal UI surfaces."""
        return dict(getattr(self, "_observability_health_display_state", self._presentation.default_observability_health_display_state()))

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
        producer = self._event_producer_label(event_method)
        has_trace = self._presentation.display_field_present(payload, "candidate_trace_id")
        has_condition = self._presentation.display_field_present(payload, "condition_id")
        has_token = self._presentation.display_field_present(payload, "token_id")
        has_side = self._presentation.display_field_present(payload, "side", "outcome", "best_side")
        has_probability = self._presentation.display_visibility_status(payload, "true_probability", "p_yes", "model_p_yes")
        has_fair_value = self._presentation.display_visibility_status(payload, "fair_value")
        has_ev = self._presentation.display_visibility_status(payload, "ev_after_spread", "ev")
        model_attempted = self._presentation.display_visibility_status(
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
        model_gap = self._presentation.display_dominant_model_gap(payload)
        event_identity = self._presentation.display_identity_readiness(payload)
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
    # Batch 3B-2: cadence / scheduler / event-producer helpers
    # ------------------------------------------------------------------

    def _event_producer_label(self, event_method: str) -> str:
        return {
            "log_market_snapshot": "market_snapshots",
            "log_decision": "decision_log",
            "log_execution": "execution_log",
            "log_risk_event": "risk_log",
            "log_trade_open": "trade_journal",
            "log_trade_close": "trade_journal",
            "log_trade_path_checkpoint": "path_truth",
            "log_orderbook_lineage_probe": "orderbook_lineage",
            "log_system_health": "system_health",
        }.get(event_method, "unknown")

    def _scheduler_cadence_observability_detail(
        self,
        trader: Any,
        ticker: str,
    ) -> "dict[str, object]":
        """Expose cycle/market hot-path timing without changing cadence or gates."""
        ticker_key = ticker.upper()
        now_mono = time.monotonic()
        cycle_started = float(getattr(trader, "_cycle_started_monotonic", 0.0) or 0.0)
        market_started = self._market_evaluation_started_monotonic.get(ticker_key)
        last_success_mono = self._last_successful_yes_no_book_monotonic.get(ticker_key)
        recovery_detail = getattr(trader, "_last_empty_book_recovery_detail", {}).get(ticker_key, {})
        try:
            recovery_seconds = float(recovery_detail.get("recovery_wait_seconds", 0.0) or 0.0)
        except (TypeError, ValueError):
            recovery_seconds = 0.0
        detail: "dict[str, object]" = {
            "scheduler_cadence_source": "run_single_cycle_market_loop",
            "hot_path_timing_source": "runtime_market_evaluation",
            "configured_decision_loop_interval_seconds": getattr(trader, "_configured_decision_loop_interval_seconds", None),
            "intended_decision_loop_target_seconds": getattr(trader, "_intended_decision_loop_target_seconds", 1.0),
            "effective_outer_loop_interval_seconds": getattr(trader, "_effective_outer_loop_interval_seconds", None),
            "snapshot_sampling_interval_seconds": getattr(trader, "_snapshot_sampling_interval_seconds", 5.0),
            "market_discovery_interval_seconds": getattr(trader, "_market_discovery_interval_seconds", 15.0),
            "outer_loop_poll_interval_seconds": getattr(trader, "_outer_loop_poll_interval_seconds", 0.25),
            "market_evaluation_asset": ticker_key,
            "market_evaluation_started_at": self._market_evaluation_started_at_utc.get(ticker_key, ""),
            "market_sequence_index": self._current_cycle_market_sequence_index.get(ticker_key, 0),
            "market_sequence_count": self._current_cycle_market_sequence_count.get(
                ticker_key,
                int(getattr(trader, "_current_cycle_market_count", 0) or 0),
            ),
            "cycle_elapsed_ms_at_market_evaluation": trader._cycle_elapsed_ms(),
            "empty_book_recovery_duration_ms": int(max(0.0, recovery_seconds) * 1000),
        }
        if market_started is not None:
            detail["market_evaluation_duration_ms"] = int(max(0.0, now_mono - market_started) * 1000)
            if cycle_started > 0:
                detail["market_evaluation_started_ms_since_cycle"] = int(
                    max(0.0, market_started - cycle_started) * 1000
                )
        if last_success_mono is not None:
            candidate_queue_age_ms = int(max(0.0, now_mono - last_success_mono) * 1000)
            detail.update({
                "candidate_created_at": self._last_successful_yes_no_book_at_utc.get(ticker_key, ""),
                "candidate_enqueue_at": self._last_successful_yes_no_book_at_utc.get(ticker_key, ""),
                "candidate_dequeue_at": trader._utc_timestamp(),
                "candidate_queue_age_ms": candidate_queue_age_ms,
                "hot_path_admission_wait_ms": candidate_queue_age_ms,
                "candidate_queue_age_source": "last_successful_yes_no_book_to_decision",
            })
        detail.update({
            "candidate_queue_ownership": "implicit_orderbook_refresh_cache",
            "candidate_revisit_scheduling_source": "scheduled_run_single_cycle",
            "hot_path_admission_trigger": "scheduled_decision_cycle",
            "event_vs_polling_classification": "polling_revisit_driven",
            "executable_liquidity_event_role": "passive_telemetry_only",
            "executable_liquidity_triggered_hot_path": False,
            "market_snapshot_decision_pipeline_linkage": "disconnected_passive_snapshot_to_scheduled_decision",
            "candidate_handoff_boundary": (
                f"{self._last_orderbook_refresh_source.get(ticker_key, 'unknown')}->scheduled_run_single_cycle"
            ),
        })
        return detail

    def _emit_hybrid_v1_snapshot(
        self,
        trader: Any,
        ticker: str,
        outcome: Any,
        timing_payload: "dict[str, object]",
    ) -> None:
        """
        Emits a hybrid observability snapshot combining research and live metrics.
        Includes Preload Next Market v1 observability fields.
        Offline-only research evidence — does not affect strategy, risk, or execution.
        """
        _next_market = getattr(trader, "_preloaded_next_markets", {}).get(ticker)
        snapshot_payload = {
            **timing_payload,
            "ticker": ticker,
            "market_id": outcome.market_id,
            "actual_decision": outcome.decision,
            "actual_skip_reason": outcome.skip_reason or "",
            "preload_started_ts": getattr(trader, "_preload_started_ts", 0),
            "preload_success_ts": getattr(trader, "_preload_success_ts", 0),
            "preload_failed_reason": getattr(trader, "_preload_failed_reason", None),
            "preload_lead_seconds": getattr(trader, "_preload_lead_seconds", 0),
            "preload_book_ready_ts": getattr(trader, "_preload_book_ready_ts", 0),
            "preloaded_market_id": _next_market.market_id if _next_market else None,
            "preloaded_condition_id": _next_market.condition_id if _next_market else None,
            "preloaded_epoch_start_ts": _next_market.epoch_start_ts if _next_market else None,
            "shadow_inventory": {
                "theoretical_decision": "HOLD" if outcome.skipped else "WOULD_OPEN",
                "scope": "shadow_research_v1",
                "offline_only": True,
            },
        }
        _display = outcome.display or {}
        snapshot_payload["snapshot_bid"] = float(_display.get("yes_bid", 0.0) or 0.0)
        snapshot_payload["snapshot_ask"] = float(_display.get("yes_ask", 0.0) or 0.0)
        snapshot_payload["snapshot_spread"] = float(_display.get("spread", 0.0) or 0.0)
        snapshot_payload["snapshot_best_bid_size"] = float(_display.get("yes_bid_size", 0.0) or 0.0)
        snapshot_payload["snapshot_best_ask_size"] = float(_display.get("yes_ask_size", 0.0) or 0.0)
        snapshot_payload["snapshot_orderbook_source"] = str(_display.get("orderbook_refresh_source", "") or "")
        snapshot_payload["snapshot_orderbook_age_ms"] = int(_display.get("orderbook_age_ms", 0) or 0)
        snapshot_payload["snapshot_orderbook_empty_reason"] = str(_display.get("orderbook_readiness_reason", "") or "")
        try:
            _resolved_ticker = ticker or trader._ticker_from_market_id(outcome.market_id)
            _epoch = int(
                (outcome.display or {}).get(
                    "market_epoch_start",
                    (outcome.display or {}).get("epoch_start", (outcome.display or {}).get("epoch_start_ts", 0)),
                ) or 0
            )
            if _epoch > 0:
                _bucket = trader._phase2_readiness_store().setdefault(
                    (_resolved_ticker.upper(), _epoch), {}
                )
                if not _bucket.get("decision_complete_ts"):
                    _bucket["decision_complete_ts"] = trader._utc_timestamp()
                _latency = trader._compute_lifecycle_latency_ms(_bucket)
                snapshot_payload.update(_latency)
        except Exception:
            pass
        trader._emit_quant_event("log_research_snapshot", snapshot_payload)

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

        Reads _cycle_started_at_utc from trader (permanent on trader).
        Reads all moved fields (3B-1 and 3B-2) from self.*.
        Calls trader._orderbook_token_pair_key() for pair-key computation.
        """
        ticker_key = ticker.upper()
        now_mono = time.monotonic()
        last_refresh_mono = self._last_orderbook_refresh_monotonic.get(ticker_key)
        last_success_mono = self._last_successful_yes_no_book_monotonic.get(ticker_key)
        previous_decision_mono = self._last_decision_cycle_monotonic.get(ticker_key)
        decision_interval = None
        if record_decision_cycle:
            if previous_decision_mono is not None:
                decision_interval = round(max(0.0, now_mono - previous_decision_mono), 3)
            self._last_decision_cycle_monotonic[ticker_key] = now_mono
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

    # ------------------------------------------------------------------
    # Batch 3C: static phase2 utility methods (moved from trader.py)
    # ------------------------------------------------------------------

    @staticmethod
    def _phase2_candidate_hash(prefix: str, *parts: object) -> str:
        raw = "|".join(str(part or "") for part in parts)
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
        return f"{prefix}_{digest}"

    @staticmethod
    def _phase2_value_available(value: object) -> bool:
        return value is not None and value != ""

    @staticmethod
    def _phase2_iso_from_epoch(epoch_start: int, offset_seconds: int) -> str:
        if epoch_start <= 0:
            return ""
        try:
            return datetime.fromtimestamp(epoch_start + offset_seconds, UTC).isoformat().replace("+00:00", "Z")
        except (OSError, OverflowError, ValueError):
            return ""

    @staticmethod
    def _phase2_phase_offsets(lifecycle_phase: str) -> "tuple[int, int | None]":
        phase = str(lifecycle_phase or "").upper()
        if phase == "OPENING_SCAN":
            return 0, 35
        if phase == "ACTIVE_INVENTORY_TRADING":
            return 35, 240
        if phase == "PROFIT_MANAGEMENT":
            return 240, 270
        if phase == "FINAL_DERISK":
            return 270, 300
        if phase == "CLOSED_OR_UNSAFE":
            return 300, None
        return 0, None
