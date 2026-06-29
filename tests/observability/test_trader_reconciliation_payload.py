"""Unit tests for reconciliation carry helpers and their equivalence with PolymarketTrader wrappers.

Canonical module: trader_reconciliation_carry.py (carry/metadata helpers)
                  trader_trade_event_payload.py  (event payload builders)
Shim:             trader_reconciliation_payload.py (re-exports both)
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest
from unittest.mock import MagicMock
from polymarket.observability.trader_reconciliation_carry import (
    carry_entry_model_truth_from_metadata,
    build_paper_trade_replay_key,
    size_sharp_metadata,
    size_sharp_close_carry,
    build_entry_model_truth_envelope,
    build_trade_position_metadata,
)
from polymarket.observability.trader_trade_event_payload import (
    build_trade_closed_payload,
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


def _legacy_trade_closed_payload(
    *,
    position,
    metadata,
    reason,
    exit_price,
    exit_timestamp,
    hold_seconds,
    size,
    pnl,
    trade_result,
    entry_price,
    partial,
    receipt_payload,
    mode,
    ticker,
    token_id,
    outcome,
    condition_id,
    epoch_start_ts,
    paper_trade_replay_key,
    size_sharp_carry,
    entry_model_truth_carry,
):
    meta = metadata if isinstance(metadata, dict) else {}
    payload = {
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
        "receipt": receipt_payload,
        "mode": mode,
        "condition_id": condition_id,
        "epoch_start_ts": epoch_start_ts,
        "asset": ticker,
        "paper_trade_replay_key": paper_trade_replay_key,
        "candidate_peak_favorable": None,
        "candidate_peak_adverse": None,
        "true_probability": meta.get("true_probability") if isinstance(metadata, dict) else None,
        "fair_value": meta.get("fair_value") if isinstance(metadata, dict) else None,
        "ev": meta.get("entry_ev") if isinstance(metadata, dict) else None,
        "ev_after_spread": meta.get("entry_ev") if isinstance(metadata, dict) else None,
        "confidence": meta.get("confidence") if isinstance(metadata, dict) else None,
        "signal_name": meta.get("signal_name") if isinstance(metadata, dict) else None,
        "signal_reason": meta.get("signal_reason") if isinstance(metadata, dict) else None,
        "strategy_signal_name": meta.get("strategy_signal_name") if isinstance(metadata, dict) else None,
        "strategy_signal_reason": meta.get("strategy_signal_reason") if isinstance(metadata, dict) else None,
        "lifecycle_phase": meta.get("lifecycle_phase") if isinstance(metadata, dict) else None,
        "seconds_remaining": meta.get("seconds_remaining") if isinstance(metadata, dict) else None,
        "bankroll_tier_id": meta.get("bankroll_tier_id") if isinstance(metadata, dict) else None,
        "bankroll_family": meta.get("bankroll_family") if isinstance(metadata, dict) else None,
        "risk_mode": meta.get("risk_mode") if isinstance(metadata, dict) else None,
        "risk_budget": meta.get("risk_budget") if isinstance(metadata, dict) else None,
        "current_exposure": meta.get("current_exposure") if isinstance(metadata, dict) else None,
        "target_exposure": meta.get("target_exposure") if isinstance(metadata, dict) else None,
        "notional_size": meta.get("notional_size") if isinstance(metadata, dict) else None,
        "capital_score": meta.get("capital_score") if isinstance(metadata, dict) else None,
        "capital_state": meta.get("capital_state") if isinstance(metadata, dict) else None,
        "promotion_candidate": meta.get("promotion_candidate") if isinstance(metadata, dict) else None,
        "demotion_candidate": meta.get("demotion_candidate") if isinstance(metadata, dict) else None,
        "expected_risk_profile": meta.get("expected_risk_profile") if isinstance(metadata, dict) else None,
        "bankroll_rank": meta.get("bankroll_rank") if isinstance(metadata, dict) else None,
        "shadow_policy_decision": meta.get("shadow_policy_decision") if isinstance(metadata, dict) else None,
        "shadow_policy_observed_ev": meta.get("shadow_policy_observed_ev") if isinstance(metadata, dict) else None,
        "shadow_policy_observed_probability": (
            meta.get("shadow_policy_observed_probability") if isinstance(metadata, dict) else None
        ),
        "shadow_policy_observed_risk_mode": (
            meta.get("shadow_policy_observed_risk_mode") if isinstance(metadata, dict) else None
        ),
        "shadow_policy_id": meta.get("shadow_policy_id") if isinstance(metadata, dict) else None,
        **size_sharp_carry,
        **entry_model_truth_carry,
    }
    attribution = meta.get("entry_attribution")
    if isinstance(attribution, dict):
        payload["entry_attribution"] = attribution
        payload["entry_attribution_status"] = "success"
        for field in ("candidate_id", "candidate_instance_id", "paper_trade_replay_key", "signal_name", "signal_reason"):
            if field in attribution:
                payload[field] = attribution[field]
    else:
        payload["entry_attribution_status"] = "missing_legacy"
    return payload


def _trade_closed_payload_kwargs(metadata):
    return {
        "position": SimpleNamespace(
            position_id="pos-1",
            symbol="pm-5m-btc",
            side="BUY",
            entry_price=0.42,
            entry_time="2026-06-29T08:30:00Z",
            metadata=metadata,
        ),
        "metadata": metadata,
        "reason": "take_profit_final",
        "exit_price": 0.68,
        "exit_timestamp": "2026-06-29T08:33:00Z",
        "hold_seconds": 180,
        "size": 12.5,
        "pnl": 3.25,
        "trade_result": "TP",
        "entry_price": 0.42,
        "partial": False,
        "receipt_payload": {"order_id": "ord-1", "filled_size": 12.5},
        "mode": "paper",
        "ticker": "BTC",
        "token_id": "tok-yes",
        "outcome": "YES",
        "condition_id": "cond-1",
        "epoch_start_ts": 1710000000,
        "paper_trade_replay_key": "cond-1|1710000000|BTC|YES|tok-yes",
        "size_sharp_carry": {
            "size_sharp_at_entry": 118.0,
            "size_sharp_bucket": "Tier-1",
            "size_sharp_close_carry_status": "carried",
        },
        "entry_model_truth_carry": {
            "entry_model_truth_envelope_v1": {
                "schema_version": "1.0",
                "truth_status": "full",
                "carried_from": "position_metadata",
            }
        },
    }


def test_build_trade_closed_payload_matches_legacy_local_construction():
    metadata = {
        "condition_id": "cond-1",
        "epoch_start_ts": 1710000000,
        "true_probability": 0.64,
        "fair_value": 0.66,
        "entry_ev": 0.08,
        "confidence": 0.91,
        "signal_name": "legacy_signal",
        "signal_reason": "legacy_reason",
        "strategy_signal_name": "strategy_signal",
        "strategy_signal_reason": "strategy_reason",
        "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
        "seconds_remaining": 91,
        "bankroll_tier_id": "T1",
        "bankroll_family": "MAIN",
        "risk_mode": "NORMAL",
        "risk_budget": 44.0,
        "current_exposure": 12.5,
        "target_exposure": 20.0,
        "notional_size": 12.5,
        "capital_score": 0.77,
        "capital_state": "OK",
        "promotion_candidate": False,
        "demotion_candidate": False,
        "expected_risk_profile": "LOW",
        "bankroll_rank": "T1_CORE",
        "shadow_policy_decision": "ALLOW",
        "shadow_policy_observed_ev": 0.08,
        "shadow_policy_observed_probability": 0.64,
        "shadow_policy_observed_risk_mode": "NORMAL",
        "shadow_policy_id": "policy-1",
        "entry_attribution": {
            "candidate_id": "cand-override",
            "candidate_instance_id": "inst-override",
            "paper_trade_replay_key": "attrib-key",
            "signal_name": "attrib_signal",
            "signal_reason": "attrib_reason",
        },
    }
    kwargs = _trade_closed_payload_kwargs(metadata)
    assert build_trade_closed_payload(**kwargs) == _legacy_trade_closed_payload(**kwargs)


def test_build_trade_closed_payload_missing_none_metadata_behavior():
    kwargs = _trade_closed_payload_kwargs(None)
    payload = build_trade_closed_payload(**kwargs)

    assert payload == _legacy_trade_closed_payload(**kwargs)
    assert payload["true_probability"] is None
    assert payload["fair_value"] is None
    assert payload["ev"] is None
    assert payload["entry_attribution_status"] == "missing_legacy"


def test_build_trade_closed_payload_preserves_pnl_exit_replay_and_carry_fields():
    kwargs = _trade_closed_payload_kwargs({})
    kwargs.update(
        reason="stop_loss_hard",
        exit_price=0.12,
        size=4,
        pnl=-1.2,
        trade_result="SL",
        partial=True,
        paper_trade_replay_key="replay-key-2",
    )
    payload = build_trade_closed_payload(**kwargs)

    assert payload["reason"] == "stop_loss_hard"
    assert payload["exit_price"] == 0.12
    assert payload["size"] == 4.0
    assert payload["pnl"] == -1.2
    assert payload["pnl_usdc"] == -1.2
    assert payload["trade_result"] == "SL"
    assert payload["partial"] is True
    assert payload["paper_trade_replay_key"] == "replay-key-2"
    assert payload["size_sharp_close_carry_status"] == "carried"
    assert payload["entry_model_truth_envelope_v1"]["carried_from"] == "position_metadata"


def test_build_trade_closed_payload_has_no_emission_or_trader_dependency():
    signature = inspect.signature(build_trade_closed_payload)
    forbidden_parameters = {"self", "trader", "emit", "emit_quant_event", "logger"}

    assert not (forbidden_parameters & set(signature.parameters))


def test_emit_trade_closed_event_calls_quant_event_once(monkeypatch):
    fixed_now = SimpleNamespace(
        isoformat=lambda: "2026-06-29T08:33:00+00:00",
    )
    monkeypatch.setattr("polymarket.trader.datetime", SimpleNamespace(now=lambda tz: fixed_now, fromisoformat=__import__("datetime").datetime.fromisoformat))

    trader = PolymarketTrader.__new__(PolymarketTrader)
    trader.settings = SimpleNamespace(paper_trading=True)
    emitted = []

    def _capture(event_method, payload):
        emitted.append((event_method, payload))

    trader._emit_quant_event = _capture
    position = SimpleNamespace(
        position_id="pos-emit",
        symbol="pm-5m-btc",
        side="BUY",
        entry_price=0.4,
        entry_time="2026-06-29T08:30:00Z",
        metadata={
            "condition_id": "cond-emit",
            "epoch_start_ts": 1710000000,
            "token_id": "tok-emit",
            "outcome": "YES",
            "entry_attribution": {"candidate_id": "cand-emit"},
        },
    )

    PolymarketTrader._emit_trade_closed_event(
        trader,
        position=position,
        reason="take_profit",
        exit_price=0.7,
        size=3,
        pnl=0.9,
        receipt=None,
        partial=False,
    )

    assert len(emitted) == 1
    event_method, payload = emitted[0]
    assert event_method == "log_trade_close"
    assert payload["position_id"] == "pos-emit"
    assert payload["candidate_id"] == "cand-emit"
    assert payload["paper_trade_replay_key"] == "cond-emit|1710000000|BTC|YES|tok-emit"


class TestCompatibilityShim:
    """Verify the shim re-exports are identical objects to the canonical imports."""

    def test_shim_carry_helpers_are_canonical(self):
        import polymarket.observability.trader_reconciliation_payload as shim
        import polymarket.observability.trader_reconciliation_carry as carry

        assert shim.carry_entry_model_truth_from_metadata is carry.carry_entry_model_truth_from_metadata
        assert shim.build_paper_trade_replay_key is carry.build_paper_trade_replay_key
        assert shim.size_sharp_metadata is carry.size_sharp_metadata
        assert shim.size_sharp_close_carry is carry.size_sharp_close_carry
        assert shim.build_entry_model_truth_envelope is carry.build_entry_model_truth_envelope
        assert shim.build_trade_position_metadata is carry.build_trade_position_metadata

    def test_shim_event_payload_helpers_are_canonical(self):
        import polymarket.observability.trader_reconciliation_payload as shim
        import polymarket.observability.trader_trade_event_payload as event_payload

        assert shim.collect_trade_open_context is event_payload.collect_trade_open_context
        assert shim.build_trade_opened_payload is event_payload.build_trade_opened_payload
        assert shim.build_trade_closed_payload is event_payload.build_trade_closed_payload

    def test_shim_import_path_still_works(self):
        from polymarket.observability.trader_reconciliation_payload import (
            carry_entry_model_truth_from_metadata as shim_carry,
            build_trade_closed_payload as shim_close,
        )
        assert shim_carry({}) == {"entry_model_truth_carry_status": "absent_in_metadata"}
        assert callable(shim_close)
