"""Schema contract tests for trade-event payload TypedDicts.

Verifies:
  1. All declared TypedDicts are importable from contracts.py
  2. Carry helper return shapes match their contracts
  3. Event builder return shapes match their contracts
  4. Golden payload snapshots for TradeOpenedPayload and TradeClosedPayload
  5. All payloads are JSON-serializable
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from polymarket.observability.contracts import (
    CarryMetadata,
    EntryModelTruthEnvelope,
    EntryModelTruthEnvelopeWrapper,
    SizeSharpCloseCarry,
    SizeSharpMetadata,
    TradeClosedPayload,
    TradeOpenContext,
    TradeOpenedPayload,
    TradePositionMetadata,
)
from polymarket.observability.trader_reconciliation_carry import (
    build_entry_model_truth_envelope,
    build_paper_trade_replay_key,
    build_trade_position_metadata,
    carry_entry_model_truth_from_metadata,
    size_sharp_close_carry,
    size_sharp_metadata,
)
from polymarket.observability.trader_trade_event_payload import (
    build_trade_closed_payload,
    build_trade_opened_payload,
)


# ---------------------------------------------------------------------------
# Import / annotation verification
# ---------------------------------------------------------------------------

class TestContractsImportable:
    def test_all_typedicts_importable(self):
        for cls in (
            EntryModelTruthEnvelope,
            EntryModelTruthEnvelopeWrapper,
            SizeSharpMetadata,
            SizeSharpCloseCarry,
            CarryMetadata,
            TradeOpenContext,
            TradePositionMetadata,
            TradeOpenedPayload,
            TradeClosedPayload,
        ):
            assert hasattr(cls, "__annotations__")

    def test_carry_return_annotation_updated(self):
        import inspect
        hints = {}
        for fn in (
            carry_entry_model_truth_from_metadata,
            size_sharp_metadata,
            size_sharp_close_carry,
            build_entry_model_truth_envelope,
            build_trade_position_metadata,
        ):
            hints[fn.__name__] = fn.__annotations__.get("return")
        assert hints["carry_entry_model_truth_from_metadata"] is CarryMetadata
        assert hints["size_sharp_metadata"] is SizeSharpMetadata
        assert hints["size_sharp_close_carry"] is SizeSharpCloseCarry
        assert hints["build_entry_model_truth_envelope"] is EntryModelTruthEnvelopeWrapper
        assert hints["build_trade_position_metadata"] is TradePositionMetadata

    def test_event_payload_return_annotation_updated(self):
        assert build_trade_opened_payload.__annotations__.get("return") is TradeOpenedPayload
        assert build_trade_closed_payload.__annotations__.get("return") is TradeClosedPayload


# ---------------------------------------------------------------------------
# Carry helper schema contracts
# ---------------------------------------------------------------------------

class TestCarryMetadataContract:
    def test_absent_returns_carry_status_key(self):
        result = carry_entry_model_truth_from_metadata({})
        assert result == {"entry_model_truth_carry_status": "absent_in_metadata"}
        assert "entry_model_truth_envelope_v1" not in result

    def test_carry_returns_envelope_key(self):
        meta = {
            "entry_model_truth_envelope_v1": {
                "schema_version": "1.0",
                "truth_status": "full",
            }
        }
        result = carry_entry_model_truth_from_metadata(meta)
        assert "entry_model_truth_envelope_v1" in result
        assert result["entry_model_truth_envelope_v1"]["truth_status"] == "full"
        assert result["entry_model_truth_envelope_v1"]["carried_from"] == "position_metadata"
        assert "entry_model_truth_carry_status" not in result

    def test_non_dict_envelope_returns_absent(self):
        result = carry_entry_model_truth_from_metadata({"entry_model_truth_envelope_v1": "not-a-dict"})
        assert result == {"entry_model_truth_carry_status": "absent_in_metadata"}

    def test_result_is_json_serializable(self):
        result = carry_entry_model_truth_from_metadata({})
        assert json.dumps(result) is not None


class TestSizeSharpMetadataContract:
    def test_none_result_returns_missing_status(self):
        result = size_sharp_metadata(None)
        assert result == {"size_sharp_close_carry_status": "missing_not_scored"}
        assert len(result) == 1

    def test_dict_result_returns_eleven_fields(self):
        mock_result = {
            "size_sharp": 100.0,
            "size_sharp_bucket": "Tier-1",
            "deployment_state": "active",
            "limiting_factor": "ev_threshold",
            "confidence_grade": "A",
            "component_scores": {"ev": 0.9},
            "penalties": {},
            "boosts": {},
            "hard_caps": [],
            "missing_inputs": [],
            "schema_version": "size_sharp_v1",
        }
        result = size_sharp_metadata(mock_result)
        assert result["size_sharp_at_entry"] == 100.0
        assert result["size_sharp_bucket"] == "Tier-1"
        assert result["size_sharp_schema_version"] == "size_sharp_v1"
        assert "size_sharp_close_carry_status" not in result
        assert len(result) == 11

    def test_result_is_json_serializable(self):
        result = size_sharp_metadata(None)
        assert json.dumps(result) is not None


class TestSizeSharpCloseCarryContract:
    def test_none_metadata_returns_missing(self):
        result = size_sharp_close_carry(None)
        assert result == {"size_sharp_close_carry_status": "missing_legacy_metadata"}

    def test_empty_metadata_returns_missing_status(self):
        result = size_sharp_close_carry({})
        assert result["size_sharp_close_carry_status"] == "missing_legacy_metadata"

    def test_present_fields_carry_with_status(self):
        metadata = {
            "size_sharp_at_entry": 100.0,
            "size_sharp_bucket": "Tier-1",
            "size_sharp_deployment_state": "active",
            "size_sharp_limiting_factor": None,
            "size_sharp_confidence_grade": None,
            "size_sharp_component_scores": {},
            "size_sharp_penalties": {},
            "size_sharp_boosts": {},
            "size_sharp_hard_caps": [],
            "size_sharp_missing_inputs": [],
            "size_sharp_schema_version": "size_sharp_v1",
        }
        result = size_sharp_close_carry(metadata)
        assert result["size_sharp_at_entry"] == 100.0
        assert result["size_sharp_bucket"] == "Tier-1"
        assert result["size_sharp_close_carry_status"] == "carried"

    def test_result_is_json_serializable(self):
        result = size_sharp_close_carry(None)
        assert json.dumps(result) is not None


class TestEntryModelTruthEnvelopeContract:
    def test_full_truth_status_when_both_present(self):
        result = build_entry_model_truth_envelope(
            utc_timestamp="2026-01-01T00:00:00Z",
            true_probability=0.65,
            ev_after_spread=0.03,
            computed_by="test",
            serialization_source="test",
        )
        env = result.get("entry_model_truth_envelope_v1")
        assert env is not None
        assert env["truth_status"] == "full"
        assert env["schema_version"] == "1.0"
        assert env["lineage_reference_only"] is True

    def test_probability_only_when_no_ev(self):
        result = build_entry_model_truth_envelope(
            utc_timestamp="2026-01-01T00:00:00Z",
            true_probability=0.65,
            computed_by="test",
            serialization_source="test",
        )
        env = result["entry_model_truth_envelope_v1"]
        assert env["truth_status"] == "probability_only"

    def test_absent_when_neither_present(self):
        result = build_entry_model_truth_envelope(
            utc_timestamp="2026-01-01T00:00:00Z",
            computed_by="test",
            serialization_source="test",
        )
        env = result["entry_model_truth_envelope_v1"]
        assert env["truth_status"] == "absent"

    def test_required_fields_always_present(self):
        result = build_entry_model_truth_envelope(
            utc_timestamp="2026-01-01T00:00:00Z",
        )
        env = result["entry_model_truth_envelope_v1"]
        required_keys = {
            "schema_version", "truth_status", "truth_source", "producer_stage",
            "model_output_ready", "model_attempted", "lineage_reference_only",
            "computed_at", "computed_by", "serialization_source",
        }
        for key in required_keys:
            assert key in env, f"missing required key: {key}"

    def test_none_utc_timestamp_still_produces_envelope(self):
        # The try/except is fail-soft — None utc_timestamp doesn't raise,
        # it just produces computed_at: None in the envelope.
        result = build_entry_model_truth_envelope(
            utc_timestamp=None,  # type: ignore[arg-type]
        )
        assert "entry_model_truth_envelope_v1" in result
        assert result["entry_model_truth_envelope_v1"]["computed_at"] is None

    def test_result_is_json_serializable(self):
        result = build_entry_model_truth_envelope(
            utc_timestamp="2026-01-01T00:00:00Z",
            true_probability=0.65,
            ev_after_spread=0.03,
        )
        assert json.dumps(result) is not None


# ---------------------------------------------------------------------------
# TradePositionMetadata contract
# ---------------------------------------------------------------------------

class TestTradePositionMetadataContract:
    def _build(self, **overrides):
        defaults = dict(
            last_quant_details={},
            utc_timestamp="2026-01-01T00:00:00Z",
            strategy="test_strategy",
            signal_strategy=None,
            token_id="tok-abc",
            outcome="YES",
            entry_ev=0.03,
            confidence=0.9,
            delta_regime=None,
            condition_id="cond-01",
            epoch_start_ts=1710000000,
            market_slug="btc-slug",
            lifecycle_phase=None,
            ticker="BTC",
            true_probability=0.65,
            fair_value=0.65,
        )
        defaults.update(overrides)
        return build_trade_position_metadata(**defaults)

    def test_required_keys_present(self):
        result = self._build()
        for key in (
            "strategy", "token_id", "outcome", "entry_ev", "confidence",
            "condition_id", "epoch_start_ts", "paper_trade_replay_key",
            "entry_model_truth_envelope_v1", "entry_attribution",
            "true_probability", "fair_value", "bankroll_rank",
        ):
            assert key in result, f"missing key: {key}"

    def test_paper_trade_replay_key_built(self):
        result = self._build()
        assert result["paper_trade_replay_key"] == "cond-01|1710000000|BTC|YES|tok-abc"

    def test_shadow_policy_fields_present(self):
        result = self._build()
        for key in (
            "shadow_policy_decision", "shadow_policy_reasons",
            "shadow_policy_observed_ev", "shadow_policy_observed_probability",
            "shadow_policy_observed_risk_mode", "shadow_policy_id",
            "shadow_policy_confidence",
        ):
            assert key in result, f"missing shadow_policy key: {key}"

    def test_size_sharp_fields_present_when_none(self):
        result = self._build()
        assert result["size_sharp_close_carry_status"] == "missing_not_scored"

    def test_result_is_json_serializable(self):
        result = self._build()
        assert json.dumps(result, default=str) is not None


# ---------------------------------------------------------------------------
# TradeOpenedPayload — golden snapshot
# ---------------------------------------------------------------------------

_OPEN_CONTEXT = {
    "model_context": {
        "signal_name": "breakout",
        "signal_reason": "ev_positive",
    },
    "entry_attribution": None,
    "model_p_yes": None,
    "model_p_no": None,
    "selected_probability": 0.65,
    "selected_fair_value": 0.65,
    "selected_ev": 0.03,
    "selected_confidence": 0.9,
    "model_output_visible": True,
    "phase2_detail": {},
    "epoch_start_ts": 1710000000,
    "paper_trade_replay_key": "cond-01|1710000000|BTC|YES|tok-abc",
    "runtime_mode": "paper",
    "size_sharp_payload": {"size_sharp_close_carry_status": "missing_not_scored"},
    "bankroll_rank": None,
    "bankroll_family": None,
    "capital_score": None,
    "entry_model_truth_envelope": {},
}

_EXPECTED_OPEN_PAYLOAD = {
    "market_id": "pm-5m-btc",
    "ticker": "BTC",
    "token_id": "tok-abc",
    "outcome": "YES",
    "side": "BUY",
    "entry_price": 0.5,
    "size": 10.0,
    "notional_size": 5.0,
    "receipt": {"order_id": "ord-1"},
    "strategy": "test_strategy",
    "mode": "paper",
    "condition_id": "cond-01",
    "epoch_start_ts": 1710000000,
    "asset": "BTC",
    "paper_trade_replay_key": "cond-01|1710000000|BTC|YES|tok-abc",
    "candidate_peak_favorable": None,
    "candidate_peak_adverse": None,
    "signal_name": "breakout",
    "signal_reason": "ev_positive",
    "strategy_signal_name": None,
    "strategy_signal_reason": None,
    "position_id": "pos-001",
    "entry_attribution": None,
    "entry_attribution_status": "missing",
    "true_probability": 0.65,
    "fair_value": 0.65,
    "ev_after_spread": 0.03,
    "expected_value": 0.03,
    "ev": 0.03,
    "confidence": 0.9,
    "size_sharp_close_carry_status": "missing_not_scored",
    "bankroll_rank": None,
    "bankroll_family": None,
    "capital_score": None,
    "shadow_policy_decision": None,
    "shadow_policy_reasons": None,
    "shadow_policy_observed_ev": None,
    "shadow_policy_observed_probability": None,
    "shadow_policy_observed_risk_mode": None,
    "shadow_policy_id": None,
    "shadow_policy_confidence": None,
}


class TestTradeOpenedPayloadGoldenSnapshot:
    def _build(self):
        return build_trade_opened_payload(
            market_id="pm-5m-btc",
            ticker="BTC",
            token_id="tok-abc",
            outcome="YES",
            side="BUY",
            entry_price=0.5,
            position_size=10.0,
            notional_size=5.0,
            receipt_payload={"order_id": "ord-1"},
            strategy="test_strategy",
            condition_id="cond-01",
            position_id="pos-001",
            trade_open_context=_OPEN_CONTEXT,
        )

    def test_golden_snapshot_exact_match(self):
        payload = self._build()
        assert payload == _EXPECTED_OPEN_PAYLOAD

    def test_no_unexpected_keys(self):
        payload = self._build()
        extra = set(payload.keys()) - set(_EXPECTED_OPEN_PAYLOAD.keys())
        assert extra == set(), f"unexpected keys in payload: {extra}"

    def test_required_declared_keys_present(self):
        payload = self._build()
        declared = TradeOpenedPayload.__annotations__.keys()
        # Only check keys that are not conditionally absent (candidate_id etc.)
        skip = {"candidate_id", "candidate_instance_id"}
        for key in declared:
            if key not in skip:
                assert key in payload, f"declared key missing from payload: {key}"

    def test_is_json_serializable(self):
        payload = self._build()
        assert json.dumps(payload) is not None

    def test_condition_id_empty_string_becomes_empty_string(self):
        payload = build_trade_opened_payload(
            market_id="m",
            ticker="BTC",
            token_id="t",
            outcome="YES",
            side="BUY",
            entry_price=0.5,
            position_size=1.0,
            notional_size=0.5,
            receipt_payload={},
            strategy="s",
        )
        assert payload["condition_id"] == ""

    def test_entry_attribution_dict_overrides_fields(self):
        context = dict(_OPEN_CONTEXT)
        context["entry_attribution"] = {
            "candidate_id": "cand-xyz",
            "candidate_instance_id": "inst-abc",
            "paper_trade_replay_key": "override-key",
            "signal_name": "override_signal",
            "signal_reason": "override_reason",
        }
        payload = build_trade_opened_payload(
            market_id="pm-5m-btc",
            ticker="BTC",
            token_id="tok-abc",
            outcome="YES",
            side="BUY",
            entry_price=0.5,
            position_size=10.0,
            notional_size=5.0,
            receipt_payload={},
            strategy="test_strategy",
            trade_open_context=context,
        )
        assert payload["entry_attribution_status"] == "success"
        assert payload["candidate_id"] == "cand-xyz"
        assert payload["paper_trade_replay_key"] == "override-key"
        assert payload["signal_name"] == "override_signal"


# ---------------------------------------------------------------------------
# TradeClosedPayload — golden snapshot
# ---------------------------------------------------------------------------

_CLOSE_METADATA = {
    "true_probability": 0.65,
    "fair_value": 0.65,
    "entry_ev": 0.03,
    "confidence": 0.9,
    "signal_name": "breakout",
    "signal_reason": "ev_positive",
    "strategy_signal_name": None,
    "strategy_signal_reason": None,
    "lifecycle_phase": None,
    "seconds_remaining": None,
    "bankroll_tier_id": None,
    "bankroll_family": None,
    "risk_mode": None,
    "risk_budget": None,
    "current_exposure": None,
    "target_exposure": None,
    "notional_size": 5.0,
    "capital_score": None,
    "capital_state": None,
    "promotion_candidate": None,
    "demotion_candidate": None,
    "expected_risk_profile": None,
    "bankroll_rank": None,
    "shadow_policy_decision": None,
    "shadow_policy_observed_ev": None,
    "shadow_policy_observed_probability": None,
    "shadow_policy_observed_risk_mode": None,
    "shadow_policy_id": None,
}

_EXPECTED_CLOSE_PAYLOAD = {
    "position_id": "pos-001",
    "market_id": "pm-5m-btc",
    "ticker": "BTC",
    "token_id": "tok-abc",
    "outcome": "YES",
    "reason": "take_profit",
    "exit_price": 0.55,
    "exit_timestamp": "2026-01-01T00:00:00Z",
    "hold_seconds": 300,
    "size": 10.0,
    "pnl": 0.5,
    "pnl_usdc": 0.5,
    "trade_result": "win",
    "entry_price": 0.5,
    "partial": False,
    "receipt": {},
    "mode": "paper",
    "condition_id": "cond-01",
    "epoch_start_ts": 1710000000,
    "asset": "BTC",
    "paper_trade_replay_key": "cond-01|1710000000|BTC|YES|tok-abc",
    "candidate_peak_favorable": None,
    "candidate_peak_adverse": None,
    "true_probability": 0.65,
    "fair_value": 0.65,
    "ev": 0.03,
    "ev_after_spread": 0.03,
    "confidence": 0.9,
    "signal_name": "breakout",
    "signal_reason": "ev_positive",
    "strategy_signal_name": None,
    "strategy_signal_reason": None,
    "lifecycle_phase": None,
    "seconds_remaining": None,
    "bankroll_tier_id": None,
    "bankroll_family": None,
    "risk_mode": None,
    "risk_budget": None,
    "current_exposure": None,
    "target_exposure": None,
    "notional_size": 5.0,
    "capital_score": None,
    "capital_state": None,
    "promotion_candidate": None,
    "demotion_candidate": None,
    "expected_risk_profile": None,
    "bankroll_rank": None,
    "shadow_policy_decision": None,
    "shadow_policy_observed_ev": None,
    "shadow_policy_observed_probability": None,
    "shadow_policy_observed_risk_mode": None,
    "shadow_policy_id": None,
    "entry_attribution_status": "missing_legacy",
}


class TestTradeClosedPayloadGoldenSnapshot:
    def _position(self):
        return SimpleNamespace(position_id="pos-001", symbol="pm-5m-btc")

    def _build(self):
        return build_trade_closed_payload(
            position=self._position(),
            metadata=_CLOSE_METADATA,
            reason="take_profit",
            exit_price=0.55,
            exit_timestamp="2026-01-01T00:00:00Z",
            hold_seconds=300,
            size=10.0,
            pnl=0.5,
            trade_result="win",
            entry_price=0.5,
            partial=False,
            receipt_payload=None,
            mode="paper",
            ticker="BTC",
            token_id="tok-abc",
            outcome="YES",
            condition_id="cond-01",
            epoch_start_ts=1710000000,
            paper_trade_replay_key="cond-01|1710000000|BTC|YES|tok-abc",
            size_sharp_carry=None,
            entry_model_truth_carry=None,
        )

    def test_golden_snapshot_exact_match(self):
        payload = self._build()
        assert payload == _EXPECTED_CLOSE_PAYLOAD

    def test_no_unexpected_keys(self):
        payload = self._build()
        extra = set(payload.keys()) - set(_EXPECTED_CLOSE_PAYLOAD.keys())
        assert extra == set(), f"unexpected keys in payload: {extra}"

    def test_is_json_serializable(self):
        payload = self._build()
        assert json.dumps(payload, default=str) is not None

    def test_none_metadata_all_metadata_fields_none(self):
        payload = build_trade_closed_payload(
            position=self._position(),
            metadata=None,
            reason="timeout",
            exit_price=0.5,
            exit_timestamp="2026-01-01T00:00:00Z",
            hold_seconds=None,
            size=1.0,
            pnl=0.0,
            trade_result=None,
            entry_price=None,
            partial=False,
            receipt_payload=None,
            mode="paper",
            ticker="BTC",
            token_id="tok-abc",
            outcome="YES",
            condition_id="cond-01",
            epoch_start_ts=1710000000,
            paper_trade_replay_key="",
        )
        assert payload["true_probability"] is None
        assert payload["ev"] is None
        assert payload["entry_attribution_status"] == "missing_legacy"

    def test_size_sharp_carry_spreads_into_payload(self):
        carry = {
            "size_sharp_at_entry": 100.0,
            "size_sharp_bucket": "Tier-1",
            "size_sharp_close_carry_status": "carried",
        }
        payload = build_trade_closed_payload(
            position=self._position(),
            metadata=None,
            reason="timeout",
            exit_price=0.5,
            exit_timestamp="2026-01-01T00:00:00Z",
            hold_seconds=None,
            size=1.0,
            pnl=0.0,
            trade_result=None,
            entry_price=None,
            partial=False,
            receipt_payload=None,
            mode="paper",
            ticker="BTC",
            token_id="tok-abc",
            outcome="YES",
            condition_id="cond-01",
            epoch_start_ts=1710000000,
            paper_trade_replay_key="",
            size_sharp_carry=carry,
        )
        assert payload["size_sharp_at_entry"] == 100.0
        assert payload["size_sharp_close_carry_status"] == "carried"

    def test_entry_attribution_dict_overrides_status(self):
        metadata = dict(_CLOSE_METADATA)
        metadata["entry_attribution"] = {
            "candidate_id": "cand-xyz",
            "candidate_instance_id": "inst-abc",
        }
        payload = build_trade_closed_payload(
            position=self._position(),
            metadata=metadata,
            reason="take_profit",
            exit_price=0.55,
            exit_timestamp="2026-01-01T00:00:00Z",
            hold_seconds=300,
            size=10.0,
            pnl=0.5,
            trade_result="win",
            entry_price=0.5,
            partial=False,
            receipt_payload=None,
            mode="paper",
            ticker="BTC",
            token_id="tok-abc",
            outcome="YES",
            condition_id="cond-01",
            epoch_start_ts=1710000000,
            paper_trade_replay_key="cond-01|1710000000|BTC|YES|tok-abc",
        )
        assert payload["entry_attribution_status"] == "success"
        assert payload["candidate_id"] == "cand-xyz"
        assert payload["entry_attribution"] == {"candidate_id": "cand-xyz", "candidate_instance_id": "inst-abc"}
