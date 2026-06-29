"""Unit tests for trader_reconciliation_payload.py and their equivalence with PolymarketTrader wrappers."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from polymarket.observability.trader_reconciliation_payload import (
    carry_entry_model_truth_from_metadata,
    build_paper_trade_replay_key,
    size_sharp_metadata,
    size_sharp_close_carry,
    build_entry_model_truth_envelope,
    build_trade_position_metadata,
)
from polymarket.trader import PolymarketTrader


class MockTrader:
    def __init__(self):
        self.last_quant_details = {
            "BTC": {
                "candidate_id": "cand_123",
                "candidate_trace_id": "trace_abc",
                "candidate_instance_id": "inst_456",
                "entry_ev": 0.05,
                "true_probability": 0.65,
                "shadow_policy_decision": "BUY",
                "shadow_policy_reasons": ["high_ev"],
                "shadow_policy_observed_ev": 0.05,
                "shadow_policy_observed_probability": 0.65,
                "shadow_policy_observed_risk_mode": "NORMAL",
                "shadow_policy_id": "sp_789",
                "shadow_policy_confidence": 0.9,
                "size_sharp_result": {
                    "size_sharp": 100.0,
                    "size_sharp_bucket": "Tier-1",
                    "deployment_state": "ACTIVE",
                    "limiting_factor": "liquidity",
                    "confidence_grade": "A",
                }
            }
        }

    def _utc_timestamp(self) -> str:
        return "2026-06-29T14:40:00Z"


def test_carry_entry_model_truth_from_metadata():
    # Empty or wrong type
    assert carry_entry_model_truth_from_metadata({}) == {"entry_model_truth_carry_status": "absent_in_metadata"}
    assert carry_entry_model_truth_from_metadata({"entry_model_truth_envelope_v1": "invalid"}) == {"entry_model_truth_carry_status": "absent_in_metadata"}

    # Happy path
    meta = {
        "entry_model_truth_envelope_v1": {
            "true_probability": 0.65,
            "fair_value": 0.65,
        }
    }
    res = carry_entry_model_truth_from_metadata(meta)
    assert "entry_model_truth_envelope_v1" in res
    assert res["entry_model_truth_envelope_v1"]["carried_from"] == "position_metadata"


def test_build_paper_trade_replay_key():
    # Incomplete inputs
    assert build_paper_trade_replay_key(condition_id="", epoch_start_ts=123, ticker="BTC", outcome="YES", token_id="t123") == ""
    assert build_paper_trade_replay_key(condition_id="c1", epoch_start_ts=0, ticker="BTC", outcome="YES", token_id="t123") == ""

    # Happy path
    res = build_paper_trade_replay_key(
        condition_id="cond_123",
        epoch_start_ts="1710000000",
        ticker="BTC",
        outcome="YES",
        token_id="tok_456"
    )
    assert res == "cond_123|1710000000|BTC|YES|tok_456"


def test_size_sharp_metadata():
    # None input
    assert size_sharp_metadata(None) == {"size_sharp_close_carry_status": "missing_not_scored"}

    # Mock object with as_dict
    mock_result = MagicMock()
    mock_result.as_dict.return_value = {
        "size_sharp": 150.0,
        "size_sharp_bucket": "Tier-2",
        "deployment_state": "ACTIVE",
    }
    res = size_sharp_metadata(mock_result)
    assert res["size_sharp_at_entry"] == 150.0
    assert res["size_sharp_bucket"] == "Tier-2"
    assert res["size_sharp_deployment_state"] == "ACTIVE"


def test_size_sharp_close_carry():
    # Invalid metadata
    assert size_sharp_close_carry(None) == {"size_sharp_close_carry_status": "missing_legacy_metadata"}
    assert size_sharp_close_carry({})["size_sharp_close_carry_status"] == "missing_legacy_metadata"

    # Happy path
    meta = {
        "size_sharp_at_entry": 120.0,
        "size_sharp_bucket": "Tier-1",
        "size_sharp_limiting_factor": "liquidity",
    }
    res = size_sharp_close_carry(meta)
    assert res["size_sharp_at_entry"] == 120.0
    assert res["size_sharp_bucket"] == "Tier-1"
    assert res["size_sharp_close_carry_status"] == "carried"


def test_build_entry_model_truth_envelope():
    res = build_entry_model_truth_envelope(
        utc_timestamp="2026-06-29T14:40:00Z",
        true_probability=0.65,
        fair_value=0.68,
        ev_after_spread=0.03,
        confidence=0.9,
    )
    assert "entry_model_truth_envelope_v1" in res
    envelope = res["entry_model_truth_envelope_v1"]
    assert envelope["truth_status"] == "full"
    assert envelope["true_probability"] == 0.65
    assert envelope["fair_value"] == 0.68
    assert envelope["ev_after_spread"] == 0.03
    assert envelope["computed_at"] == "2026-06-29T14:40:00Z"


def test_build_trade_position_metadata():
    trader = MockTrader()
    res = build_trade_position_metadata(
        last_quant_details=trader.last_quant_details,
        utc_timestamp=trader._utc_timestamp(),
        strategy="trend_runner",
        signal_strategy="trend",
        token_id="tok_123",
        outcome="YES",
        entry_ev=0.05,
        confidence=0.85,
        delta_regime=0.1,
        condition_id="cond_abc",
        epoch_start_ts=1710000000,
        market_slug="btc-above-20k",
        lifecycle_phase="ACTIVE",
        ticker="BTC",
        bankroll_tier_id="T1",
        bankroll_family="BTC",
        risk_mode="NORMAL",
        risk_budget=500.0,
        current_exposure=100.0,
        target_exposure=200.0,
        notional_size=50.0,
        seconds_remaining=300,
        capital_score=0.95,
        capital_state="HEURISTIC",
        promotion_candidate=False,
        demotion_candidate=False,
        expected_risk_profile="LOW",
        bankroll_rank="rank_a",
    )
    assert res["strategy"] == "trend_runner"
    assert res["bankroll_rank"] == "rank_a"
    assert res["shadow_policy_decision"] == "BUY"
    assert res["entry_attribution"]["candidate_id"] == "cand_123"
    assert res["size_sharp_at_entry"] == 100.0


def test_equivalence_with_trader_wrappers():
    # Setup mock / partial trader instance to verify wrapper delegating correctly
    trader = MagicMock(spec=PolymarketTrader)
    trader.last_quant_details = {
        "BTC": {
            "candidate_id": "cand_123",
            "size_sharp_result": {"size_sharp": 100.0, "size_sharp_bucket": "Tier-1"}
        }
    }
    trader._utc_timestamp.return_value = "2026-06-29T14:40:00Z"

    # Verify wrappers delegate correctly by calling original methods on trader class
    wrapper_paper_key = PolymarketTrader._build_paper_trade_replay_key(
        condition_id="c1", epoch_start_ts=123, ticker="BTC", outcome="YES", token_id="t1"
    )
    helper_paper_key = build_paper_trade_replay_key(
        condition_id="c1", epoch_start_ts=123, ticker="BTC", outcome="YES", token_id="t1"
    )
    assert wrapper_paper_key == helper_paper_key

    # Envelope wrapper
    wrapper_envelope = PolymarketTrader._build_entry_model_truth_envelope(
        trader, true_probability=0.6, fair_value=0.6
    )
    helper_envelope = build_entry_model_truth_envelope(
        utc_timestamp="2026-06-29T14:40:00Z", true_probability=0.6, fair_value=0.6
    )
    assert wrapper_envelope == helper_envelope

    # carry wrapper
    assert PolymarketTrader._carry_entry_model_truth_from_metadata(trader, {}) == carry_entry_model_truth_from_metadata({})

    # position metadata wrapper
    wrapper_pos = PolymarketTrader._build_trade_position_metadata(
        trader,
        strategy="trend",
        signal_strategy="trend",
        token_id="tok",
        outcome="YES",
        entry_ev=0.02,
        confidence=0.8,
        delta_regime=0.01,
        condition_id="cond",
        epoch_start_ts=123,
        market_slug="slug",
        lifecycle_phase="ACTIVE",
        ticker="BTC",
    )
    helper_pos = build_trade_position_metadata(
        last_quant_details=trader.last_quant_details,
        utc_timestamp="2026-06-29T14:40:00Z",
        strategy="trend",
        signal_strategy="trend",
        token_id="tok",
        outcome="YES",
        entry_ev=0.02,
        confidence=0.8,
        delta_regime=0.01,
        condition_id="cond",
        epoch_start_ts=123,
        market_slug="slug",
        lifecycle_phase="ACTIVE",
        ticker="BTC",
    )
    assert wrapper_pos == helper_pos
