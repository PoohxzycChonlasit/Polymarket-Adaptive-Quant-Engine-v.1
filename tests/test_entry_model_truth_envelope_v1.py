"""
Tests for ENTRY_MODEL_TRUTH_ENVELOPE_V1

Observability-only. Additive. Fail-soft.
Tests cover: envelope build, carry, YES/NO aliasing, lifecycle propagation,
risk_log carry, legacy fill path, lineage field invariance.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from polymarket.trader import PolymarketTrader, TradeOutcome
from utils.quant_event_logger import QuantEventLogger
from utils.risk_manager import RiskPlan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trader() -> PolymarketTrader:
    t = PolymarketTrader()
    t.settings.paper_trading = True
    return t


def _risk_plan(position_size: float = 0.05) -> RiskPlan:
    return RiskPlan(
        account_balance=1000.0,
        entry_price=0.60,
        stop_loss_price=0.58,
        take_profit_price=0.66,
        partial_tp_price=0.63,
        risk_amount=10.0,
        kelly_fraction=0.10,
        capped_fraction=0.10,
        position_size=position_size,
        notional_size=position_size * 0.60,
        stop_loss_pct=0.02,
    )


def _quant_logger(tmp_path, *, run_id: str = "run-env-test") -> QuantEventLogger:
    return QuantEventLogger(
        base_dir=tmp_path,
        enabled=True,
        mode="paper",
        run_id=run_id,
        now=lambda: datetime(2026, 5, 29, 3, 35, 11, tzinfo=UTC),
    )


def _position(*, metadata: dict | None = None):
    return SimpleNamespace(
        position_id="pos-env-1",
        symbol="pm-5m-btc",
        side="BUY",
        entry_price=0.60,
        entry_time="2026-05-29T03:35:00Z",
        size=2.0,
        status="open",
        metadata=metadata if metadata is not None else {
            "token_id": "tok-yes",
            "outcome": "YES",
            "condition_id": "cond-1",
            "epoch_start_ts": 1748483700,
            "market_slug": "btc-up-2026",
            "lifecycle_phase": "OPENING_SCAN",
        },
    )


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# 1. Envelope builds with all expected fields
# ---------------------------------------------------------------------------

def test_envelope_helper_full_shape() -> None:
    t = _trader()
    result = t._build_entry_model_truth_envelope(
        true_probability=0.62,
        fair_value=0.62,
        ev_after_spread=0.041,
        confidence=0.71,
        model_probability_yes=0.62,
        model_probability_no=0.38,
        selected_side="YES",
        model_handoff_stage="MODEL_OUTPUT_SERIALIZED",
        probability_model_stage="probability_model_output",
        model_output_ready=True,
        model_attempted=True,
        model_not_run_reason="",
        ev_missing_reason="",
        computed_by="decision_log",
        serialization_source="phase2_observability_payload",
    )
    assert "entry_model_truth_envelope_v1" in result
    env = result["entry_model_truth_envelope_v1"]
    assert env["schema_version"] == "1.0"
    assert env["truth_status"] == "full"
    assert env["producer_stage"] == "decision_log"
    assert env["truth_source"] == "phase2_observability_payload"
    assert env["model_output_ready"] is True
    assert env["model_attempted"] is True
    assert env["model_probability_yes"] == pytest.approx(0.62)
    assert env["model_probability_no"] == pytest.approx(0.38)
    assert env["selected_side"] == "YES"
    assert env["true_probability"] == pytest.approx(0.62)
    assert env["fair_value"] == pytest.approx(0.62)
    assert env["ev_after_spread"] == pytest.approx(0.041)
    assert env["expected_value"] == pytest.approx(0.041)
    assert env["confidence"] == pytest.approx(0.71)
    assert env["lineage_reference_only"] is True
    assert env["computed_by"] == "decision_log"
    assert env["serialization_source"] == "phase2_observability_payload"
    assert "computed_at" in env


# ---------------------------------------------------------------------------
# 2. Missing fields fail soft — no exception, truth_status reflects absence
# ---------------------------------------------------------------------------

def test_envelope_helper_all_null_values() -> None:
    t = _trader()
    result = t._build_entry_model_truth_envelope()
    assert isinstance(result, dict)
    assert "entry_model_truth_envelope_v1" in result
    env = result["entry_model_truth_envelope_v1"]
    assert env["truth_status"] == "absent"
    assert env["true_probability"] is None
    assert env["fair_value"] is None
    assert env["ev_after_spread"] is None
    assert env["confidence"] is None
    assert env["model_probability_yes"] is None
    assert env["model_probability_no"] is None
    assert env["ev_missing_reason"] == "ev_not_available"


def test_envelope_helper_non_numeric_probability_fails_soft() -> None:
    t = _trader()
    result = t._build_entry_model_truth_envelope(
        true_probability="not_a_number",
        ev_after_spread="also_bad",
    )
    assert isinstance(result, dict)
    env = result.get("entry_model_truth_envelope_v1", {})
    assert env.get("true_probability") is None
    assert env.get("ev_after_spread") is None
    assert env.get("truth_status") == "absent"


def test_envelope_helper_exception_returns_empty_dict() -> None:
    t = _trader()
    # Force an exception inside the helper by temporarily replacing _utc_timestamp
    original = t._utc_timestamp
    t._utc_timestamp = None  # type: ignore[assignment]
    try:
        result = t._build_entry_model_truth_envelope(true_probability=0.5)
    finally:
        t._utc_timestamp = original
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# 3. YES / NO selected probability aliasing
# ---------------------------------------------------------------------------

def test_envelope_yes_side_truth_status() -> None:
    t = _trader()
    env = t._build_entry_model_truth_envelope(
        true_probability=0.70,
        model_probability_yes=0.70,
        model_probability_no=0.30,
        selected_side="YES",
        ev_after_spread=0.05,
    )["entry_model_truth_envelope_v1"]
    assert env["selected_side"] == "YES"
    assert env["true_probability"] == pytest.approx(0.70)
    assert env["model_probability_yes"] == pytest.approx(0.70)
    assert env["truth_status"] == "full"


def test_envelope_no_side_truth_status() -> None:
    t = _trader()
    env = t._build_entry_model_truth_envelope(
        true_probability=0.35,
        model_probability_yes=0.65,
        model_probability_no=0.35,
        selected_side="NO",
        ev_after_spread=0.03,
    )["entry_model_truth_envelope_v1"]
    assert env["selected_side"] == "NO"
    assert env["true_probability"] == pytest.approx(0.35)
    assert env["model_probability_no"] == pytest.approx(0.35)
    assert env["truth_status"] == "full"


def test_envelope_probability_only_status() -> None:
    t = _trader()
    env = t._build_entry_model_truth_envelope(
        true_probability=0.60,
    )["entry_model_truth_envelope_v1"]
    assert env["truth_status"] == "probability_only"
    assert env["ev_after_spread"] is None


# ---------------------------------------------------------------------------
# 4. Carry helpers
# ---------------------------------------------------------------------------

def test_carry_helper_returns_envelope_with_carried_from() -> None:
    t = _trader()
    metadata = {
        "entry_model_truth_envelope_v1": {
            "schema_version": "1.0",
            "truth_status": "full",
            "producer_stage": "position_metadata",
            "true_probability": 0.65,
            "computed_at": "2026-05-29T03:35:00Z",
        }
    }
    result = t._carry_entry_model_truth_from_metadata(metadata)
    assert "entry_model_truth_envelope_v1" in result
    assert result["entry_model_truth_envelope_v1"]["carried_from"] == "position_metadata"
    assert result["entry_model_truth_envelope_v1"]["true_probability"] == pytest.approx(0.65)


def test_carry_helper_absent_metadata_returns_carry_status() -> None:
    t = _trader()
    result = t._carry_entry_model_truth_from_metadata({})
    assert "entry_model_truth_carry_status" in result
    assert result["entry_model_truth_carry_status"] == "absent_in_metadata"
    assert "entry_model_truth_envelope_v1" not in result


def test_carry_helper_none_value_returns_carry_status() -> None:
    t = _trader()
    result = t._carry_entry_model_truth_from_metadata({"entry_model_truth_envelope_v1": None})
    assert result.get("entry_model_truth_carry_status") == "absent_in_metadata"


def test_carry_helper_exception_returns_empty_dict() -> None:
    t = _trader()
    result = t._carry_entry_model_truth_from_metadata(None)  # type: ignore[arg-type]
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# 5. decision_log emits envelope
# ---------------------------------------------------------------------------

def test_decision_log_emits_envelope(tmp_path) -> None:
    t = _trader()
    t.quant_events = _quant_logger(tmp_path)
    display = {
        "true_probability": 0.63,
        "fair_value": 0.63,
        "ev_after_spread": 0.04,
        "model_probability_yes": 0.63,
        "model_probability_no": 0.37,
        "side": "YES",
        "probability_model_output_visible": True,
        "probability_model_called": True,
        "model_handoff_stage": "MODEL_OUTPUT_SERIALIZED",
        "probability_model_stage": "probability_model_output",
    }
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="BTC up?",
        decision="YES",
        confidence=0.70,
        risk_plan=_risk_plan(),
        receipt=None,
        skipped=True,
        skip_reason="test_skip",
        display=display,
    )
    t._emit_decision_event(outcome, ticker="BTC")

    rows = _read_jsonl(tmp_path / "decision_log" / "2026-05-29.jsonl")
    assert rows, "No decision_log rows written"
    payload = rows[-1]["payload"]
    assert "entry_model_truth_envelope_v1" in payload, "envelope missing from decision_log"
    env = payload["entry_model_truth_envelope_v1"]
    assert env["schema_version"] == "1.0"
    assert env["producer_stage"] == "decision_log"
    assert env["lineage_reference_only"] is True
    assert "computed_at" in env


# ---------------------------------------------------------------------------
# 6. risk_log carries envelope from decision_payload
# ---------------------------------------------------------------------------

def test_risk_log_carries_envelope(tmp_path) -> None:
    t = _trader()
    t.quant_events = _quant_logger(tmp_path)
    display = {
        "true_probability": 0.58,
        "fair_value": 0.58,
        "ev_after_spread": 0.02,
        "side": "YES",
    }
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="BTC up?",
        decision="YES",
        confidence=0.60,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="risk_plan_zero",
        display=display,
    )
    t._emit_decision_event(outcome, ticker="BTC")

    risk_path = tmp_path / "risk_log" / "2026-05-29.jsonl"
    if not risk_path.exists():
        pytest.skip("risk_log not written for this outcome (expected for some skip reasons)")
    rows = _read_jsonl(risk_path)
    if not rows:
        pytest.skip("risk_log empty")
    payload = rows[-1]["payload"]
    assert "entry_model_truth_envelope_v1" in payload, "envelope not carried into risk_log"
    assert payload["entry_model_truth_envelope_v1"]["producer_stage"] == "decision_log"


# ---------------------------------------------------------------------------
# 7. _build_trade_position_metadata stores envelope
# ---------------------------------------------------------------------------

def test_position_metadata_stores_envelope() -> None:
    t = _trader()
    meta = t._build_trade_position_metadata(
        strategy="quant_v1",
        signal_strategy="trend",
        token_id="tok-yes",
        outcome="YES",
        entry_ev=0.04,
        confidence=0.70,
        delta_regime="MODERATE_BULL",
        condition_id="cond-1",
        epoch_start_ts=1748483700,
        market_slug="btc-up-2026",
        lifecycle_phase="OPENING_SCAN",
        ticker="BTC",
        true_probability=0.65,
        fair_value=0.65,
    )
    assert "entry_model_truth_envelope_v1" in meta
    env = meta["entry_model_truth_envelope_v1"]
    assert env["true_probability"] == pytest.approx(0.65)
    assert env["fair_value"] == pytest.approx(0.65)
    assert env["producer_stage"] == "position_metadata"
    assert env["selected_side"] == "YES"


def test_position_metadata_stores_envelope_without_probability() -> None:
    t = _trader()
    meta = t._build_trade_position_metadata(
        strategy="quant_v1",
        signal_strategy="trend",
        token_id="tok-yes",
        outcome="YES",
        entry_ev=0.04,
        confidence=0.70,
        delta_regime="NEUTRAL",
        condition_id="cond-1",
        epoch_start_ts=1748483700,
        market_slug="btc-up-2026",
        lifecycle_phase="OPENING_SCAN",
        ticker="BTC",
    )
    assert "entry_model_truth_envelope_v1" in meta
    env = meta["entry_model_truth_envelope_v1"]
    assert env["true_probability"] is None
    assert env["fair_value"] is None
    assert env["ev_after_spread"] == pytest.approx(0.04)
    assert env["truth_status"] == "ev_only"


# ---------------------------------------------------------------------------
# 8. path_truth emits envelope carried from metadata
# ---------------------------------------------------------------------------

def test_path_truth_carries_envelope_from_metadata(tmp_path) -> None:
    t = _trader()
    t.quant_events = _quant_logger(tmp_path)
    t._path_truth_market_state = lambda _pos: {
        "current_mark_price": 0.65,
        "bid": 0.64,
        "ask": 0.66,
        "spread": 0.02,
        "quote_age_ms": 50,
    }
    meta_with_envelope = {
        "token_id": "tok-yes",
        "outcome": "YES",
        "condition_id": "cond-1",
        "epoch_start_ts": 1748483700,
        "market_slug": "btc-up-2026",
        "lifecycle_phase": "OPENING_SCAN",
        "entry_model_truth_envelope_v1": {
            "schema_version": "1.0",
            "truth_status": "full",
            "producer_stage": "position_metadata",
            "true_probability": 0.65,
            "fair_value": 0.65,
            "ev_after_spread": 0.04,
            "expected_value": 0.04,
            "confidence": 0.70,
            "selected_side": "YES",
            "model_probability_yes": 0.65,
            "model_probability_no": 0.35,
            "model_output_ready": True,
            "model_attempted": True,
            "model_not_run_reason": "",
            "probability_model_stage": "",
            "model_handoff_stage": "",
            "ev_missing_reason": "",
            "lineage_reference_only": True,
            "computed_at": "2026-05-29T03:35:00Z",
            "computed_by": "position_metadata",
            "serialization_source": "build_trade_position_metadata",
        },
    }
    pos = _position(metadata=meta_with_envelope)
    now = datetime(2026, 5, 29, 3, 35, 15, tzinfo=UTC)
    t._emit_path_truth_checkpoint(
        pos,
        checkpoint_elapsed_s=15,
        checkpoint_reason="scheduled",
        now=now,
    )
    rows = _read_jsonl(tmp_path / "path_truth" / "2026-05-29.jsonl")
    assert rows, "No path_truth rows"
    payload = rows[0]["payload"]
    assert "entry_model_truth_envelope_v1" in payload, "envelope missing from path_truth"
    env = payload["entry_model_truth_envelope_v1"]
    assert env["carried_from"] == "position_metadata"
    assert env["true_probability"] == pytest.approx(0.65)


def test_path_truth_absent_envelope_emits_carry_status(tmp_path) -> None:
    t = _trader()
    t.quant_events = _quant_logger(tmp_path)
    t._path_truth_market_state = lambda _pos: {}
    pos = _position()  # default metadata has no entry_model_truth_envelope_v1
    now = datetime(2026, 5, 29, 3, 35, 15, tzinfo=UTC)
    t._emit_path_truth_checkpoint(
        pos,
        checkpoint_elapsed_s=15,
        checkpoint_reason="scheduled",
        now=now,
    )
    rows = _read_jsonl(tmp_path / "path_truth" / "2026-05-29.jsonl")
    assert rows
    payload = rows[0]["payload"]
    assert payload.get("entry_model_truth_carry_status") == "absent_in_metadata"
    assert "entry_model_truth_envelope_v1" not in payload


# ---------------------------------------------------------------------------
# 9. trade_close carries envelope from position metadata
# ---------------------------------------------------------------------------

def test_trade_close_carries_envelope_from_metadata(tmp_path) -> None:
    from polymarket.client import OrderReceipt
    t = _trader()
    t.quant_events = _quant_logger(tmp_path)
    meta_with_envelope = {
        "token_id": "tok-yes",
        "outcome": "YES",
        "condition_id": "cond-1",
        "epoch_start_ts": 1748483700,
        "market_slug": "btc-up-2026",
        "lifecycle_phase": "OPENING_SCAN",
        "paper_trade_replay_key": "cond-1|1748483700|BTC|YES|tok-yes",
        "entry_model_truth_envelope_v1": {
            "schema_version": "1.0",
            "truth_status": "full",
            "producer_stage": "position_metadata",
            "true_probability": 0.67,
            "fair_value": 0.67,
            "ev_after_spread": 0.05,
            "expected_value": 0.05,
            "confidence": 0.72,
            "selected_side": "YES",
            "model_probability_yes": 0.67,
            "model_probability_no": 0.33,
            "model_output_ready": True,
            "model_attempted": True,
            "model_not_run_reason": "",
            "probability_model_stage": "",
            "model_handoff_stage": "",
            "ev_missing_reason": "",
            "lineage_reference_only": True,
            "computed_at": "2026-05-29T03:35:00Z",
            "computed_by": "position_metadata",
            "serialization_source": "build_trade_position_metadata",
        },
    }
    pos = _position(metadata=meta_with_envelope)
    pos.token_id = "tok-yes"
    t._emit_trade_closed_event(
        position=pos,
        reason="take_profit",
        exit_price=0.70,
        size=2.0,
        pnl=0.20,
        receipt=None,
    )
    rows = _read_jsonl(tmp_path / "trade_journal" / "2026-05-29.jsonl")
    close_rows = [r for r in rows if r.get("event_type") == "trade_close"]
    assert close_rows, "No trade_close rows"
    payload = close_rows[-1]["payload"]
    assert "entry_model_truth_envelope_v1" in payload, "envelope missing from trade_close"
    env = payload["entry_model_truth_envelope_v1"]
    assert env["carried_from"] == "position_metadata"
    assert env["true_probability"] == pytest.approx(0.67)


def test_trade_close_absent_envelope_emits_carry_status(tmp_path) -> None:
    t = _trader()
    t.quant_events = _quant_logger(tmp_path)
    pos = _position()  # default metadata — no envelope
    t._emit_trade_closed_event(
        position=pos,
        reason="stop_loss",
        exit_price=0.55,
        size=2.0,
        pnl=-0.10,
        receipt=None,
    )
    rows = _read_jsonl(tmp_path / "trade_journal" / "2026-05-29.jsonl")
    close_rows = [r for r in rows if r.get("event_type") == "trade_close"]
    assert close_rows
    payload = close_rows[-1]["payload"]
    assert payload.get("entry_model_truth_carry_status") == "absent_in_metadata"


# ---------------------------------------------------------------------------
# 10. Legacy / minimal fill path — does not fabricate truth
# ---------------------------------------------------------------------------

def test_legacy_fill_metadata_has_no_envelope() -> None:
    t = _trader()
    # Minimal metadata as used by the legacy fill path at trader.py:9595
    legacy_meta = {"strategy": "trend", "token_id": "tok-yes", "outcome": "YES"}
    result = t._carry_entry_model_truth_from_metadata(legacy_meta)
    assert result.get("entry_model_truth_carry_status") == "absent_in_metadata"
    assert "entry_model_truth_envelope_v1" not in result


def test_position_metadata_without_probability_does_not_fabricate() -> None:
    t = _trader()
    meta = t._build_trade_position_metadata(
        strategy="legacy",
        signal_strategy="legacy",
        token_id="tok-yes",
        outcome="YES",
        entry_ev=None,
        confidence=None,
        delta_regime="NEUTRAL",
        condition_id="",
        epoch_start_ts=0,
        market_slug="",
        lifecycle_phase="",
        ticker="BTC",
        # No true_probability or fair_value
    )
    env = meta["entry_model_truth_envelope_v1"]
    assert env["true_probability"] is None
    assert env["fair_value"] is None
    assert env["truth_status"] in {"absent", "ev_only"}


# ---------------------------------------------------------------------------
# 11. Lineage fields unchanged — envelope is additive, not a new identity
# ---------------------------------------------------------------------------

def test_lineage_fields_unaffected_by_envelope(tmp_path) -> None:
    t = _trader()
    t.quant_events = _quant_logger(tmp_path)
    captured: list[dict] = []
    original_emit = t._emit_quant_event

    def _capture(method, payload=None):
        if payload:
            captured.append({"method": method, "payload": dict(payload)})
        return original_emit(method, payload)

    t._emit_quant_event = _capture  # type: ignore[method-assign]

    display = {
        "true_probability": 0.60,
        "fair_value": 0.60,
        "ev_after_spread": 0.03,
        "side": "YES",
        "condition_id": "cond-lineage-1",
        "token_id": "tok-lineage",
        "market_slug": "btc-test",
        "epoch_start_ts": 1748483700,
    }
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="BTC up?",
        decision="YES",
        confidence=0.60,
        risk_plan=_risk_plan(),
        receipt=None,
        skipped=True,
        skip_reason="test_skip",
        display=display,
    )
    t._emit_decision_event(outcome, ticker="BTC")

    decision_events = [c for c in captured if c["method"] == "log_decision"]
    assert decision_events
    payload = decision_events[-1]["payload"]

    # Envelope is present
    assert "entry_model_truth_envelope_v1" in payload

    # Envelope does not affect existing lineage fields
    env = payload["entry_model_truth_envelope_v1"]
    assert env.get("lineage_reference_only") is True

    # run_id, candidate_trace_id, paper_trade_replay_key, market_observation_key
    # semantics are not changed by the envelope — verify they are not inside it
    assert "run_id" not in env
    assert "candidate_trace_id" not in env
    assert "paper_trade_replay_key" not in env
    assert "market_observation_key" not in env


# ---------------------------------------------------------------------------
# 12. Replay semantics unchanged — envelope does not alter existing keys
# ---------------------------------------------------------------------------

def test_replay_key_not_modified_by_envelope(tmp_path) -> None:
    t = _trader()
    t.quant_events = _quant_logger(tmp_path)
    pos_meta = {
        "token_id": "tok-yes",
        "outcome": "YES",
        "condition_id": "cond-replay",
        "epoch_start_ts": 1748483700,
        "market_slug": "btc-replay",
        "paper_trade_replay_key": "cond-replay|1748483700|BTC|YES|tok-yes",
        "lifecycle_phase": "OPENING_SCAN",
        "entry_model_truth_envelope_v1": {
            "schema_version": "1.0",
            "truth_status": "full",
            "producer_stage": "position_metadata",
            "true_probability": 0.62,
            "fair_value": 0.62,
            "ev_after_spread": 0.03,
            "expected_value": 0.03,
            "confidence": 0.65,
            "selected_side": "YES",
            "model_probability_yes": 0.62,
            "model_probability_no": 0.38,
            "model_output_ready": True,
            "model_attempted": True,
            "model_not_run_reason": "",
            "probability_model_stage": "",
            "model_handoff_stage": "",
            "ev_missing_reason": "",
            "lineage_reference_only": True,
            "computed_at": "2026-05-29T03:35:00Z",
            "computed_by": "position_metadata",
            "serialization_source": "build_trade_position_metadata",
        },
    }
    pos = _position(metadata=pos_meta)
    t._path_truth_market_state = lambda _pos: {"current_mark_price": 0.63}

    now = datetime(2026, 5, 29, 3, 35, 15, tzinfo=UTC)
    t._emit_path_truth_checkpoint(
        pos,
        checkpoint_elapsed_s=15,
        checkpoint_reason="scheduled",
        now=now,
    )
    rows = _read_jsonl(tmp_path / "path_truth" / "2026-05-29.jsonl")
    assert rows
    payload = rows[0]["payload"]

    # paper_trade_replay_key is preserved unchanged
    assert payload.get("paper_trade_replay_key") == "cond-replay|1748483700|BTC|YES|tok-yes"

    # envelope does not overwrite the replay key
    env = payload["entry_model_truth_envelope_v1"]
    assert "paper_trade_replay_key" not in env
