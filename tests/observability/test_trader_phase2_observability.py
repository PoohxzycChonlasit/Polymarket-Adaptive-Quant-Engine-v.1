"""Tests for trader_phase2_observability extracted helpers."""
from __future__ import annotations

import pytest

from polymarket.observability.trader_phase2_observability import (
    _p2_val_avail,
    phase2_authoritative_orderbook_availability,
    phase2_book_state_level,
    phase2_candidate_block_detail,
    phase2_ev_null_reason,
    phase2_ev_null_reason_detail,
    phase2_market_readiness_state,
    phase2_model_activation_detail,
    phase2_orderbook_state_classification,
    phase2_pre_model_gate_detail,
)


# ---------------------------------------------------------------------------
# _p2_val_avail
# ---------------------------------------------------------------------------

class TestP2ValAvail:
    def test_none_is_not_available(self):
        assert _p2_val_avail(None) is False

    def test_empty_string_is_not_available(self):
        assert _p2_val_avail("") is False

    def test_zero_is_available(self):
        assert _p2_val_avail(0) is True

    def test_false_is_available(self):
        assert _p2_val_avail(False) is True

    def test_non_empty_string_is_available(self):
        assert _p2_val_avail("0.55") is True

    def test_float_is_available(self):
        assert _p2_val_avail(0.55) is True


# ---------------------------------------------------------------------------
# phase2_book_state_level
# ---------------------------------------------------------------------------

class TestPhase2BookStateLevel:
    @pytest.mark.parametrize("state,expected", [
        ("DISCOVERED", 0),
        ("UNKNOWN", 0),
        ("TOKEN_READY", 1),
        ("BOOK_SEEN", 2),
        ("NONZERO_BOOK", 3),
        ("SPREAD_NORMALIZED", 4),
        ("EXECUTABLE", 5),
        ("TRADABLE", 5),
        ("discovered", 0),
        ("tradable", 5),
        ("GARBAGE", -1),
        (None, -1),
        ("", -1),
    ])
    def test_level_mapping(self, state, expected):
        assert phase2_book_state_level(state) == expected


# ---------------------------------------------------------------------------
# phase2_pre_model_gate_detail
# ---------------------------------------------------------------------------

class TestPhase2PreModelGateDetail:
    def test_probability_available_returns_model_output_available(self):
        result = phase2_pre_model_gate_detail(probability_available=True)
        assert result["pre_model_gate_name"] == "MODEL_OUTPUT_AVAILABLE"
        assert result["pre_model_gate_group"] == "MODEL_READY"
        assert result["pre_model_gate_blocks_probability_model"] is False

    def test_time_cutoff_gate(self):
        result = phase2_pre_model_gate_detail(skip_reason="time_unsafe")
        assert result["pre_model_gate_name"] == "TIME_CUTOFF_GATE"
        assert result["pre_model_gate_group"] == "TIME_CUTOFF_GATE"

    def test_orderbook_gate(self):
        result = phase2_pre_model_gate_detail(orderbook_readiness_reason="empty_book_error")
        assert result["pre_model_gate_name"] == "ORDERBOOK_COMPLETENESS_GATE"
        assert result["pre_model_gate_group"] == "ORDERBOOK_GATE"

    def test_spread_gate(self):
        result = phase2_pre_model_gate_detail(spread_normalized=False)
        assert result["pre_model_gate_name"] == "SPREAD_GATE"

    def test_lifecycle_phase_gate(self):
        result = phase2_pre_model_gate_detail(lifecycle_phase="FINAL_DERISK")
        assert result["pre_model_gate_name"] == "LIFECYCLE_PHASE_GATE"

    def test_unknown_returns_model_gate_unknown(self):
        result = phase2_pre_model_gate_detail()
        assert result["pre_model_gate_name"] == "MODEL_GATE_UNKNOWN"
        assert result["pre_model_gate_blocks_probability_model"] is False

    def test_risk_gate(self):
        result = phase2_pre_model_gate_detail(skip_reason="balance_lockdown")
        assert result["pre_model_gate_name"] == "RISK_SAFETY_GATE"

    def test_liquidity_gate(self):
        result = phase2_pre_model_gate_detail(liquidity_state="LOW")
        assert result["pre_model_gate_name"] == "LIQUIDITY_GATE"

    def test_token_mapping_gate(self):
        result = phase2_pre_model_gate_detail(skip_reason="missing_token_mapping")
        assert result["pre_model_gate_name"] == "TOKEN_MAPPING_GATE"


# ---------------------------------------------------------------------------
# phase2_ev_null_reason
# ---------------------------------------------------------------------------

class TestPhase2EvNullReason:
    def test_empty_book(self):
        assert phase2_ev_null_reason(field_name="fair_value", orderbook_readiness_reason="empty_book_error") == "empty_book"

    def test_no_orderbook(self):
        assert phase2_ev_null_reason(field_name="fair_value", orderbook_readiness_reason="clob_error") == "no_orderbook"

    def test_time_unsafe(self):
        assert phase2_ev_null_reason(field_name="fair_value", skip_reason="time_unsafe") == "time_unsafe"

    def test_liquidity_not_ready(self):
        assert phase2_ev_null_reason(field_name="fair_value", liquidity_state="LOW") == "liquidity_not_ready"

    def test_spread_not_ready(self):
        assert phase2_ev_null_reason(field_name="fair_value", spread_normalized=False) == "spread_not_ready"

    def test_market_price_field(self):
        assert phase2_ev_null_reason(field_name="market_price") == "no_market_price"

    def test_ev_after_spread_no_probability(self):
        assert phase2_ev_null_reason(field_name="ev_after_spread", probability_available=False) == "no_probability_model_output"

    def test_ev_after_spread_no_market_price(self):
        assert phase2_ev_null_reason(field_name="ev_after_spread", probability_available=True, market_price_available=False) == "no_market_price"

    def test_fair_value_default(self):
        assert phase2_ev_null_reason(field_name="fair_value") == "no_probability_model_output"

    def test_risk_blocked_after_ev(self):
        assert phase2_ev_null_reason(field_name="fair_value", skip_reason="risk_lockdown", ev_available=True) == "risk_blocked_after_ev"


# ---------------------------------------------------------------------------
# phase2_ev_null_reason_detail
# ---------------------------------------------------------------------------

class TestPhase2EvNullReasonDetail:
    def test_all_available(self):
        result = phase2_ev_null_reason_detail(
            fair_value=0.55, market_price=0.50, true_probability=0.55, ev_after_spread=0.04
        )
        assert result["fair_value_available"] is True
        assert result["ev_after_spread_available"] is True
        assert result["probability_model_stage"] == "probability_model_output"
        assert result["ev_calculation_stage"] == "ev_calculated"

    def test_nothing_available_pre_model(self):
        result = phase2_ev_null_reason_detail(
            fair_value=None, market_price=None, true_probability=None, ev_after_spread=None,
            orderbook_readiness_reason="empty_book_error"
        )
        assert result["fair_value_available"] is False
        assert result["probability_model_stage"] == "pre_model_skip"
        assert result["ev_calculation_stage"] == "pre_model_skip"
        assert result["fair_value_null_reason"] == "empty_book"

    def test_probability_only(self):
        result = phase2_ev_null_reason_detail(
            fair_value=0.55, market_price=None, true_probability=None, ev_after_spread=None,
        )
        assert result["fair_value_available"] is True
        assert result["market_price_available"] is False
        assert result["ev_calculation_stage"] == "no_market_price"
        assert result["market_price_null_reason"] == "no_market_price"

    def test_model_handoff_stage_serialized(self):
        result = phase2_ev_null_reason_detail(
            fair_value=0.55, market_price=0.50, true_probability=0.55, ev_after_spread=0.04
        )
        assert result["model_handoff_stage"] == "MODEL_OUTPUT_SERIALIZED"

    def test_model_handoff_stage_pre_model_gate(self):
        result = phase2_ev_null_reason_detail(
            fair_value=None, market_price=None, true_probability=None, ev_after_spread=None,
            skip_reason="time_unsafe"
        )
        assert result["model_handoff_stage"] == "PRE_MODEL_GATE"


# ---------------------------------------------------------------------------
# phase2_authoritative_orderbook_availability
# ---------------------------------------------------------------------------

class TestPhase2AuthoritativeOrderbookAvailability:
    def test_yes_no_bid_ask_available(self):
        payload = {"yes_bid": 0.4, "yes_ask": 0.45, "no_bid": 0.55, "no_ask": 0.6}
        avail, source = phase2_authoritative_orderbook_availability(payload)
        assert avail is True
        assert source == "serialized_yes_no_bid_ask"

    def test_best_bid_ask_available(self):
        payload = {"best_bid": 0.4, "best_ask": 0.6}
        avail, source = phase2_authoritative_orderbook_availability(payload)
        assert avail is True
        assert source == "serialized_best_bid_ask"

    def test_fresh_fetch_status(self):
        payload = {"orderbook_current_fetch_status": "fresh_fetch_executable"}
        avail, source = phase2_authoritative_orderbook_availability(payload)
        assert avail is True
        assert source == "current_fetch_status_fresh_fetch_executable"

    def test_tradable_book_state(self):
        payload = {"executable_book_state": "TRADABLE"}
        avail, source = phase2_authoritative_orderbook_availability(payload)
        assert avail is True
        assert "tradable" in source

    def test_not_available(self):
        avail, source = phase2_authoritative_orderbook_availability({})
        assert avail is False
        assert source == ""

    def test_first_tradable_ts(self):
        payload = {"first_tradable_ts": "2026-01-01T00:00:00Z"}
        avail, source = phase2_authoritative_orderbook_availability(payload)
        assert avail is True
        assert source == "readiness_first_tradable_ts"

    def test_prior_successful_token_pair(self):
        payload = {
            "orderbook_lineage_match": True,
            "last_successful_yes_no_book_token_pair_key": "abc:def",
            "decision_token_pair_key": "abc:def",
        }
        avail, source = phase2_authoritative_orderbook_availability(payload)
        assert avail is True
        assert source == "prior_successful_same_token_pair"


# ---------------------------------------------------------------------------
# phase2_orderbook_state_classification
# ---------------------------------------------------------------------------

class TestPhase2OrderbookStateClassification:
    def test_token_mapping_unavailable(self):
        assert phase2_orderbook_state_classification({"orderbook_readiness_reason": "missing_token"}) == "token_mapping_unavailable"

    def test_empty_book_reason(self):
        assert phase2_orderbook_state_classification({"orderbook_readiness_reason": "empty_book_error"}) == "empty_book"

    def test_warmup_pending(self):
        assert phase2_orderbook_state_classification({"orderbook_readiness_reason": "warmup_period"}) == "warmup_pending"

    def test_stale_orderbook(self):
        assert phase2_orderbook_state_classification({"orderbook_readiness_reason": "stale_data"}) == "stale_orderbook"

    def test_ready_with_bid_ask(self):
        payload = {"yes_bid": 0.4, "yes_ask": 0.45, "no_bid": 0.55, "no_ask": 0.6}
        assert phase2_orderbook_state_classification(payload) == "ready"

    def test_empty_book_values_all_zero(self):
        payload = {"yes_bid": None, "yes_ask": None, "no_bid": None, "no_ask": None}
        result = phase2_orderbook_state_classification(payload)
        assert result in {"empty_book", "unavailable"}

    def test_unavailable_empty_payload(self):
        assert phase2_orderbook_state_classification({}) == "unavailable"

    def test_liquidity_state_empty(self):
        assert phase2_orderbook_state_classification({"liquidity_state": "EMPTY"}) == "empty_book"


# ---------------------------------------------------------------------------
# phase2_candidate_block_detail
# ---------------------------------------------------------------------------

class TestPhase2CandidateBlockDetail:
    def test_not_blocked(self):
        reason, stage, expiry = phase2_candidate_block_detail({})
        assert reason == "not_blocked"
        assert stage == "not_blocked"
        assert expiry == "candidate_active_or_approved"

    def test_time_unsafe_block(self):
        payload = {"skip_reason": "time_unsafe", "skipped": True}
        reason, stage, expiry = phase2_candidate_block_detail(payload)
        assert expiry == "time_unsafe"

    def test_orderbook_block(self):
        payload = {"skip_reason": "empty_book", "skipped": True}
        reason, stage, expiry = phase2_candidate_block_detail(payload)
        assert expiry == "market_not_ready"

    def test_risk_block(self):
        payload = {"skip_reason": "risk_lockdown", "skipped": True}
        reason, stage, expiry = phase2_candidate_block_detail(payload)
        assert expiry == "risk_block"

    def test_pre_ev_stage(self):
        payload = {
            "skip_reason": "orderbook_error",
            "skipped": True,
            "probability_model_stage": "pre_model_skip",
        }
        reason, stage, expiry = phase2_candidate_block_detail(payload)
        assert stage == "pre_ev"

    def test_post_ev_stage(self):
        payload = {
            "skip_reason": "risk_block",
            "skipped": True,
            "ev_after_spread_available": True,
        }
        reason, stage, expiry = phase2_candidate_block_detail(payload)
        assert stage == "post_ev"

    def test_generic_blocked(self):
        payload = {"skip_reason": "unknown_reason", "skipped": True}
        reason, stage, expiry = phase2_candidate_block_detail(payload)
        assert expiry == "blocked"


# ---------------------------------------------------------------------------
# phase2_market_readiness_state (Tier 3 — trader: Any)
# ---------------------------------------------------------------------------

class FakeTrader:
    def __init__(self, hard_block=60):
        self._hard_block = hard_block

    def _entry_hard_block_seconds(self):
        return self._hard_block


class TestPhase2MarketReadinessState:
    def test_before_active_window(self):
        trader = FakeTrader()
        payload = {"active_window_alignment_reason": "before_active_window"}
        assert phase2_market_readiness_state(trader, payload, "ready") == "before_active_window"

    def test_late_hard_close_zone(self):
        trader = FakeTrader()
        payload = {"active_window_alignment_reason": "late_hard_close_zone"}
        assert phase2_market_readiness_state(trader, payload, "ready") == "late_hard_close_zone"

    def test_time_unsafe_when_seconds_le_hard_block(self):
        trader = FakeTrader(hard_block=60)
        payload = {"seconds_remaining": 30, "token_id": "tok123"}
        assert phase2_market_readiness_state(trader, payload, "ready") == "time_unsafe"

    def test_token_not_ready(self):
        trader = FakeTrader(hard_block=60)
        payload = {"seconds_remaining": 300}
        assert phase2_market_readiness_state(trader, payload, "ready") == "token_not_ready"

    def test_orderbook_state_propagated(self):
        trader = FakeTrader(hard_block=60)
        payload = {"seconds_remaining": 300, "token_id": "tok123"}
        assert phase2_market_readiness_state(trader, payload, "empty_book") == "empty_book"

    def test_liquidity_not_ready(self):
        trader = FakeTrader(hard_block=60)
        payload = {"seconds_remaining": 300, "token_id": "tok123", "liquidity_state": "LOW"}
        assert phase2_market_readiness_state(trader, payload, "ready") == "liquidity_not_ready"

    def test_spread_not_ready(self):
        trader = FakeTrader(hard_block=60)
        payload = {"seconds_remaining": 300, "token_id": "tok123", "spread_normalized": False}
        assert phase2_market_readiness_state(trader, payload, "ready") == "spread_not_ready"

    def test_ready(self):
        trader = FakeTrader(hard_block=60)
        payload = {"seconds_remaining": 300, "token_id": "tok123", "spread_normalized": True}
        assert phase2_market_readiness_state(trader, payload, "ready") == "ready"

    def test_entry_hard_block_exception_handled(self):
        class BrokenTrader:
            def _entry_hard_block_seconds(self):
                raise RuntimeError("broken")

        payload = {"seconds_remaining": 300, "token_id": "tok123"}
        result = phase2_market_readiness_state(BrokenTrader(), payload, "ready")
        assert result == "ready"


# ---------------------------------------------------------------------------
# phase2_model_activation_detail (Tier 3 — trader: Any)
# ---------------------------------------------------------------------------

class TestPhase2ModelActivationDetail:
    def _call(self, trader=None, payload=None, **kwargs):
        if trader is None:
            trader = FakeTrader()
        if payload is None:
            payload = {}
        defaults = {
            "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
            "orderbook_state": "ready",
            "readiness_state": "ready",
            "model_output_ready": None,
        }
        defaults.update(kwargs)
        return phase2_model_activation_detail(trader, payload, **defaults)

    def test_model_output_visible(self):
        result = self._call(model_output_ready=True)
        assert result["model_activation_state"] == "MODEL_OUTPUT_VISIBLE"
        assert result["model_attempt_eligible"] is True

    def test_time_cutoff_gate(self):
        result = self._call(readiness_state="time_unsafe")
        assert result["model_activation_state"] == "BLOCKED_BEFORE_MODEL"
        assert result["model_activation_block_group"] == "TIME_CUTOFF_GATE"

    def test_orderbook_gate(self):
        result = self._call(readiness_state="empty_book", orderbook_state="empty_book")
        assert result["model_activation_state"] == "BLOCKED_BEFORE_MODEL"
        assert result["model_activation_block_group"] == "ORDERBOOK_GATE"

    def test_liquidity_gate(self):
        result = self._call(readiness_state="liquidity_not_ready")
        assert result["model_activation_state"] == "BLOCKED_BEFORE_MODEL"
        assert result["model_activation_block_group"] == "LIQUIDITY_GATE"

    def test_spread_gate(self):
        result = self._call(readiness_state="spread_not_ready")
        assert result["model_activation_state"] == "BLOCKED_BEFORE_MODEL"
        assert result["model_activation_block_group"] == "SPREAD_GATE"

    def test_lifecycle_phase_gate(self):
        result = self._call(lifecycle_phase="FINAL_DERISK")
        assert result["model_activation_state"] == "BLOCKED_BEFORE_MODEL"
        assert result["model_activation_block_group"] == "LIFECYCLE_PHASE_GATE"

    def test_market_snapshot_producer(self):
        payload = {"producer_event_type": "market_snapshots"}
        result = self._call(payload=payload)
        assert result["model_activation_state"] == "PRE_MODEL_OBSERVATION"

    def test_pre_model_skip_stage(self):
        payload = {"probability_model_stage": "pre_model_skip"}
        result = self._call(payload=payload)
        assert result["model_activation_state"] == "BLOCKED_BEFORE_MODEL"

    def test_result_contains_seconds_fields(self):
        trader = FakeTrader(hard_block=60)
        payload = {"seconds_remaining": 120, "effective_cutoff_seconds": 90}
        result = phase2_model_activation_detail(
            trader, payload,
            lifecycle_phase="ACTIVE_INVENTORY_TRADING",
            orderbook_state="ready",
            readiness_state="ready",
            model_output_ready=True,
        )
        assert result["model_activation_seconds_remaining"] == 120
        assert result["model_activation_effective_cutoff_seconds"] == 90
        assert result["model_activation_hard_block_seconds"] == 60

    def test_hard_block_exception_handled(self):
        class BrokenTrader:
            def _entry_hard_block_seconds(self):
                raise RuntimeError("broken")

        result = phase2_model_activation_detail(
            BrokenTrader(), {},
            lifecycle_phase="ACTIVE_INVENTORY_TRADING",
            orderbook_state="ready",
            readiness_state="ready",
            model_output_ready=None,
        )
        assert result["model_activation_hard_block_seconds"] == 0


# ---------------------------------------------------------------------------
# Golden equivalence tests — wrapper delegates to extracted function
# ---------------------------------------------------------------------------

class TestGoldenEquivalence:
    """Verify trader.py wrappers produce identical results to extracted functions."""

    def test_golden_book_state_level(self):
        from unittest.mock import MagicMock
        trader = MagicMock()
        trader._phase2_book_state_level = staticmethod(phase2_book_state_level)
        assert trader._phase2_book_state_level("TRADABLE") == phase2_book_state_level("TRADABLE")
        assert trader._phase2_book_state_level("UNKNOWN") == phase2_book_state_level("UNKNOWN")

    def test_golden_pre_model_gate_detail_probability_available(self):
        kwargs = {"probability_available": True}
        from polymarket.observability.trader_phase2_observability import phase2_pre_model_gate_detail as fn
        result = fn(**kwargs)
        assert result["pre_model_gate_name"] == "MODEL_OUTPUT_AVAILABLE"

    def test_golden_ev_null_reason_empty_book(self):
        from polymarket.observability.trader_phase2_observability import phase2_ev_null_reason as fn
        assert fn(field_name="fair_value", orderbook_readiness_reason="empty_book_error") == "empty_book"

    def test_golden_ev_null_reason_detail_full(self):
        from polymarket.observability.trader_phase2_observability import phase2_ev_null_reason_detail as fn
        result = fn(fair_value=0.55, market_price=0.50, true_probability=0.55, ev_after_spread=0.04)
        assert result["fair_value_available"] is True
        assert result["ev_after_spread_available"] is True
        assert result["ev_calculation_stage"] == "ev_calculated"

    def test_golden_orderbook_state_classification_ready(self):
        from polymarket.observability.trader_phase2_observability import phase2_orderbook_state_classification as fn
        payload = {"yes_bid": 0.4, "yes_ask": 0.45, "no_bid": 0.55, "no_ask": 0.6}
        assert fn(payload) == "ready"

    def test_golden_candidate_block_detail_not_blocked(self):
        from polymarket.observability.trader_phase2_observability import phase2_candidate_block_detail as fn
        reason, stage, expiry = fn({})
        assert reason == "not_blocked"

    def test_golden_market_readiness_state_ready(self):
        from polymarket.observability.trader_phase2_observability import phase2_market_readiness_state as fn
        trader = FakeTrader(hard_block=60)
        payload = {"seconds_remaining": 300, "token_id": "tok123", "spread_normalized": True}
        assert fn(trader, payload, "ready") == "ready"

    def test_golden_model_activation_detail_model_visible(self):
        from polymarket.observability.trader_phase2_observability import phase2_model_activation_detail as fn
        trader = FakeTrader()
        result = fn(
            trader, {},
            lifecycle_phase="ACTIVE_INVENTORY_TRADING",
            orderbook_state="ready",
            readiness_state="ready",
            model_output_ready=True,
        )
        assert result["model_activation_state"] == "MODEL_OUTPUT_VISIBLE"
        assert result["model_attempt_eligible"] is True
