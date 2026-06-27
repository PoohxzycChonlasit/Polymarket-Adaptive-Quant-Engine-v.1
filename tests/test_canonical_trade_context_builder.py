import json
from pathlib import Path
import pytest
from tools.canonical_trade_context_builder import (
    CanonicalContextBuilder,
    uuid_hash_key,
    _classify_event,
    _diagnose_grade_d,
)

@pytest.fixture
def temp_quant_data(tmp_path):
    # Setup directories
    for cat in ("trade_journal", "decision_log", "execution_log", "risk_log", "path_truth"):
        (tmp_path / cat).mkdir(parents=True)
    return tmp_path

def test_matched_open_close(temp_quant_data):
    # Create matched open and close events
    date_str = "2026-06-28"
    run_id = "test_run_123"
    replay_key = "cond_123|1234567890|BTC|YES|token_123"
    
    open_event = {
        "timestamp_utc": "2026-06-28T10:00:00.000000Z",
        "event_type": "trade_open",
        "run_id": run_id,
        "mode": "paper",
        "payload": {
            "paper_trade_replay_key": replay_key,
            "position_id": "pos_999",
            "ticker": "BTC",
            "outcome": "YES",
            "side": "BUY",
            "entry_price": 0.50,
            "size": 10.0,
            "notional_size": 5.0,
            "signal_name": "PROBABILITY_EV_EDGE",
            "true_probability": 0.60,
            "fair_value": 0.60,
            "ev": 0.10,
            "ev_after_spread": 0.10,
            "lifecycle_phase": "OPENING_SCAN",
            "bankroll_tier_id": "T0_MICRO_SEED",
            "risk_mode": "NORMAL",
        }
    }
    
    close_event = {
        "timestamp_utc": "2026-06-28T10:01:00.000000Z",
        "event_type": "trade_close",
        "run_id": run_id,
        "mode": "paper",
        "payload": {
            "paper_trade_replay_key": replay_key,
            "position_id": "pos_999",
            "ticker": "BTC",
            "outcome": "YES",
            "exit_price": 0.60,
            "pnl": 1.0,
            "pnl_usdc": 1.0,
            "reason": "take_profit",
            "trade_result": "WIN",
        }
    }
    
    with open(temp_quant_data / "trade_journal" / f"{date_str}.jsonl", "w") as f:
        f.write(json.dumps(open_event) + "\n")
        f.write(json.dumps(close_event) + "\n")
        
    builder = CanonicalContextBuilder(temp_quant_data, [date_str])
    builder.load_all()
    rows, summary = builder.compile()
    
    assert len(rows) == 1
    row = rows[0]
    assert row["position_id"] == "pos_999"
    assert row["join_confidence"] == "HIGH"
    assert row["data_quality_grade"] == "A"
    assert row["realized_pnl"] == 1.0
    assert row["intended_price"] == 0.50
    assert row["exit_price"] == 0.60
    assert row["hold_seconds"] == 60.0
    assert "true_probability" not in row["missing_fields"]
    assert summary["pnl_summary"]["total_trades"] == 1
    assert summary["pnl_summary"]["win_rate"] == 1.0

def test_fallback_join_by_position_id(temp_quant_data):
    date_str = "2026-06-28"
    run_id = "test_run_123"
    
    open_event = {
        "timestamp_utc": "2026-06-28T10:00:00.000000Z",
        "event_type": "trade_open",
        "run_id": run_id,
        "payload": {
            "position_id": "pos_999",
            "ticker": "BTC",
            "outcome": "YES",
            "entry_price": 0.50,
            "size": 10.0,
        }
    }
    
    close_event = {
        "timestamp_utc": "2026-06-28T10:01:00.000000Z",
        "event_type": "trade_close",
        "run_id": run_id,
        "payload": {
            "position_id": "pos_999",
            "ticker": "BTC",
            "exit_price": 0.40,
            "pnl": -1.0,
        }
    }
    
    with open(temp_quant_data / "trade_journal" / f"{date_str}.jsonl", "w") as f:
        f.write(json.dumps(open_event) + "\n")
        f.write(json.dumps(close_event) + "\n")
        
    builder = CanonicalContextBuilder(temp_quant_data, [date_str])
    builder.load_all()
    rows, summary = builder.compile()
    
    assert len(rows) == 1
    row = rows[0]
    assert row["position_id"] == "pos_999"
    assert row["join_confidence"] == "MEDIUM"
    assert row["data_quality_grade"] == "B"  # missing sizer specifics but has prices/pnl
    assert row["realized_pnl"] == -1.0
    assert summary["pnl_summary"]["win_rate"] == 0.0

def test_unmatched_open_and_close(temp_quant_data):
    date_str = "2026-06-28"
    
    open_event = {
        "timestamp_utc": "2026-06-28T10:00:00.000000Z",
        "event_type": "trade_open",
        "run_id": "run_1",
        "payload": {
            "position_id": "pos_1",
            "ticker": "BTC",
            "entry_price": 0.50,
            "size": 10.0,
        }
    }
    
    close_event = {
        "timestamp_utc": "2026-06-28T10:01:00.000000Z",
        "event_type": "trade_close",
        "run_id": "run_2",
        "payload": {
            "position_id": "pos_2",
            "ticker": "ETH",
            "exit_price": 0.40,
            "pnl": -1.0,
        }
    }
    
    with open(temp_quant_data / "trade_journal" / f"{date_str}.jsonl", "w") as f:
        f.write(json.dumps(open_event) + "\n")
        f.write(json.dumps(close_event) + "\n")
        
    builder = CanonicalContextBuilder(temp_quant_data, [date_str])
    builder.load_all()
    rows, summary = builder.compile()
    
    assert len(rows) == 2
    assert summary["unmatched_opens"] == 1
    assert summary["unmatched_closes"] == 1
    
    grades = [r["data_quality_grade"] for r in rows]
    assert "D" in grades

def test_does_not_mutate_input_files(temp_quant_data):
    date_str = "2026-06-28"
    path = temp_quant_data / "trade_journal" / f"{date_str}.jsonl"
    
    open_event = {
        "timestamp_utc": "2026-06-28T10:00:00.000000Z",
        "event_type": "trade_open",
        "run_id": "run_1",
        "payload": {"position_id": "pos_1"}
    }
    
    with open(path, "w") as f:
        f.write(json.dumps(open_event) + "\n")
        
    original_content = path.read_text()
    
    builder = CanonicalContextBuilder(temp_quant_data, [date_str])
    builder.load_all()
    builder.compile()
    
    assert path.read_text() == original_content

def test_size_sharp_fields_compile_with_legacy_defaults(temp_quant_data):
    date_str = "2026-06-28"
    replay_key = "cond_123|1234567890|BTC|YES|token_123"

    open_event = {
        "timestamp_utc": "2026-06-28T10:00:00.000000Z",
        "event_type": "trade_open",
        "run_id": "run_size_sharp",
        "payload": {
            "paper_trade_replay_key": replay_key,
            "position_id": "pos_size_sharp",
            "ticker": "BTC",
            "outcome": "YES",
            "entry_price": 0.50,
            "size": 10.0,
            "size_sharp_at_entry": 0.76,
            "size_sharp_bucket": "STRONG",
            "size_sharp_deployment_state": "OBSERVE_STRONG",
            "size_sharp_limiting_factor": "none",
            "size_sharp_confidence_grade": "A",
            "size_sharp_component_scores": {"signal_edge": 0.8, "execution_quality": 0.7},
            "size_sharp_penalties": {"execution": 0.01},
            "size_sharp_boosts": {"clean_edge": 0.03},
            "size_sharp_hard_caps": [],
            "size_sharp_missing_inputs": [],
            "size_sharp_schema_version": "size_sharp_v1",
        },
    }
    close_event = {
        "timestamp_utc": "2026-06-28T10:01:00.000000Z",
        "event_type": "trade_close",
        "run_id": "run_size_sharp",
        "payload": {
            "paper_trade_replay_key": replay_key,
            "position_id": "pos_size_sharp",
            "ticker": "BTC",
            "exit_price": 0.60,
            "pnl": 1.0,
        },
    }
    legacy_open = {
        "timestamp_utc": "2026-06-28T10:02:00.000000Z",
        "event_type": "trade_open",
        "run_id": "run_legacy",
        "payload": {"position_id": "legacy_pos", "ticker": "ETH", "entry_price": 0.40, "size": 5.0},
    }

    with open(temp_quant_data / "trade_journal" / f"{date_str}.jsonl", "w") as f:
        f.write(json.dumps(open_event) + "\n")
        f.write(json.dumps(close_event) + "\n")
        f.write(json.dumps(legacy_open) + "\n")

    builder = CanonicalContextBuilder(temp_quant_data, [date_str])
    builder.load_all()
    rows, _summary = builder.compile()
    by_position = {row["position_id"]: row for row in rows}

    scored = by_position["pos_size_sharp"]
    assert scored["size_sharp_at_entry"] == 0.76
    assert scored["size_sharp_bucket"] == "STRONG"
    assert scored["size_sharp_component_scores"] == {"signal_edge": 0.8, "execution_quality": 0.7}
    assert scored["size_sharp_schema_version"] == "size_sharp_v1"

    legacy = by_position["legacy_pos"]
    assert legacy["size_sharp_at_entry"] is None
    assert legacy["size_sharp_bucket"] == "UNKNOWN"
    assert legacy["size_sharp_schema_version"] == "missing_legacy_metadata"


# ---------------------------------------------------------------------------
# event_classification tests
# ---------------------------------------------------------------------------

def _make_row(**overrides):
    base = {
        "exit_reason": None,
        "realized_pnl": 0.05,
        "replay_key": "cond|epoch|BTC|YES|token",
        "ev": 0.10,
        "join_confidence": "HIGH",
    }
    base.update(overrides)
    return base


def test_classify_signal_driven_trade():
    row = _make_row(exit_reason="stop_loss", replay_key="rkey", ev=0.10)
    result = _classify_event(row, open_event={"x": 1}, close_event={"y": 2})
    assert result == "signal_driven_trade"


def test_classify_test_event_by_exit_reason():
    row = _make_row(exit_reason="test", replay_key=None, ev=None)
    result = _classify_event(row, open_event=None, close_event={"y": 2})
    assert result == "test_event"


def test_classify_test_event_by_round_pnl():
    row = _make_row(exit_reason="forced_exit", replay_key=None, ev=None, realized_pnl=1.0)
    result = _classify_event(row, open_event=None, close_event={"y": 2})
    assert result == "test_event"


def test_classify_settlement_event():
    row = _make_row(exit_reason="binary_settlement", replay_key=None, ev=None, realized_pnl=0.7)
    result = _classify_event(row, open_event=None, close_event={"y": 2})
    assert result == "settlement_event"


def test_classify_forced_exit_legacy():
    row = _make_row(exit_reason="emergency_flatten", replay_key=None, ev=None, realized_pnl=0.03)
    result = _classify_event(row, open_event=None, close_event={"y": 2})
    assert result == "forced_exit_legacy"


def test_classify_unknown_legacy():
    row = _make_row(exit_reason="some_other_reason", replay_key=None, ev=None, realized_pnl=0.03)
    result = _classify_event(row, open_event=None, close_event={"y": 2})
    assert result == "unknown_legacy"


def test_classify_round_pnl_with_ev_is_not_test():
    # If ev is present, even round PnL is not classified as test_event
    row = _make_row(exit_reason="stop_loss", replay_key="rkey", ev=0.10, realized_pnl=1.0)
    result = _classify_event(row, open_event={"x": 1}, close_event={"y": 2})
    assert result == "signal_driven_trade"


# ---------------------------------------------------------------------------
# grade_d_diagnosis tests
# ---------------------------------------------------------------------------

def test_diagnose_test_event():
    row = _make_row(exit_reason="test", replay_key=None, ev=None, event_classification="test_event")
    result = _diagnose_grade_d(row, open_event=None, close_event={"y": 2})
    assert result == "test_event_no_signal_context"


def test_diagnose_settlement():
    row = _make_row(exit_reason="binary_settlement", replay_key=None, ev=None, event_classification="settlement_event")
    result = _diagnose_grade_d(row, open_event=None, close_event={"y": 2})
    assert result == "settlement_event_no_open_matched"


def test_diagnose_forced_exit():
    row = _make_row(exit_reason="emergency_flatten", replay_key=None, ev=None, event_classification="forced_exit_legacy")
    result = _diagnose_grade_d(row, open_event=None, close_event={"y": 2})
    assert result == "forced_exit_no_replay_key"


def test_diagnose_no_replay_key_legacy():
    row = _make_row(exit_reason="stop_loss", replay_key=None, ev=None, event_classification="unknown_legacy", position_id="abc")
    result = _diagnose_grade_d(row, open_event=None, close_event={"y": 2})
    assert "no_replay_key" in result or "run_id_mismatch" in result or "legacy" in result


# ---------------------------------------------------------------------------
# event_classification embedded in builder output
# ---------------------------------------------------------------------------

def test_builder_embeds_event_classification(temp_quant_data):
    date_str = "2026-06-28"
    run_id = "run_class_test"
    replay_key = "cond_class|epoch|BTC|YES|tok"

    open_event = {
        "timestamp_utc": "2026-06-28T10:00:00Z",
        "event_type": "trade_open",
        "run_id": run_id,
        "payload": {
            "paper_trade_replay_key": replay_key,
            "position_id": "pos_class",
            "ticker": "BTC",
            "ev": 0.10,
            "true_probability": 0.60,
            "fair_value": 0.60,
            "bankroll_tier_id": "T0",
            "risk_mode": "NORMAL",
            "entry_price": 0.50,
            "size": 1.0,
        },
    }
    close_event = {
        "timestamp_utc": "2026-06-28T10:01:00Z",
        "event_type": "trade_close",
        "run_id": run_id,
        "payload": {
            "paper_trade_replay_key": replay_key,
            "position_id": "pos_class",
            "exit_price": 0.60,
            "pnl": 0.10,
            "trade_result": "WIN",
            "exit_reason": "take_profit",
        },
    }

    with open(temp_quant_data / "trade_journal" / f"{date_str}.jsonl", "w") as f:
        f.write(json.dumps(open_event) + "\n")
        f.write(json.dumps(close_event) + "\n")

    builder = CanonicalContextBuilder(temp_quant_data, [date_str])
    builder.load_all()
    rows, summary = builder.compile()

    assert len(rows) == 1
    row = rows[0]
    assert row["event_classification"] == "signal_driven_trade"
    assert row["grade_d_diagnosis"] is None
    assert "event_classification_distribution" in summary
    assert summary["event_classification_distribution"].get("signal_driven_trade", 0) == 1
    assert "field_availability" in summary
    assert summary["field_availability"]["signal_driven_trades"] == 1


def test_builder_grade_d_diagnosis_for_test_event(temp_quant_data):
    date_str = "2026-06-28"
    close_event = {
        "timestamp_utc": "2026-06-28T10:01:00Z",
        "event_type": "trade_close",
        "run_id": "run_test_close",
        "payload": {
            "position_id": "pos_test_close",
            "exit_price": 0.40,
            "pnl": 1.0,
            "exit_reason": "test",
            "trade_result": "WIN",
        },
    }

    with open(temp_quant_data / "trade_journal" / f"{date_str}.jsonl", "w") as f:
        f.write(json.dumps(close_event) + "\n")

    builder = CanonicalContextBuilder(temp_quant_data, [date_str])
    builder.load_all()
    rows, summary = builder.compile()

    assert len(rows) == 1
    row = rows[0]
    assert row["data_quality_grade"] == "D"
    assert row["event_classification"] == "test_event"
    assert row["grade_d_diagnosis"] == "test_event_no_signal_context"
    assert summary["grade_d_diagnosis_distribution"].get("test_event_no_signal_context", 0) == 1
    assert summary["event_classification_distribution"].get("test_event", 0) == 1


def test_builder_skip_risk_log_default(temp_quant_data):
    """risk_log is skipped by default — builder still produces correct output."""
    date_str = "2026-06-28"
    risk_event = {
        "timestamp_utc": "2026-06-28T10:00:00Z",
        "event_type": "risk_snapshot",
        "run_id": "run_r",
        "payload": {"risk_mode": "NORMAL", "some_risk_field": 99},
    }
    with open(temp_quant_data / "risk_log" / f"{date_str}.jsonl", "w") as f:
        f.write(json.dumps(risk_event) + "\n")

    builder = CanonicalContextBuilder(temp_quant_data, [date_str], skip_risk_log=True)
    builder.load_all()
    assert len(builder.risks) == 0

    builder2 = CanonicalContextBuilder(temp_quant_data, [date_str], skip_risk_log=False)
    builder2.load_all()
    assert len(builder2.risks) == 1


def test_builder_signal_driven_pnl_in_summary(temp_quant_data):
    """signal_driven_pnl_summary excludes test_event rows."""
    date_str = "2026-06-28"
    run_id = "run_pnl_test"
    rkey = "cond_pnl|epoch|BTC|YES|tok"

    real_open = {
        "timestamp_utc": "2026-06-28T10:00:00Z",
        "event_type": "trade_open",
        "run_id": run_id,
        "payload": {
            "paper_trade_replay_key": rkey,
            "position_id": "pos_real",
            "ticker": "BTC",
            "ev": 0.10,
            "true_probability": 0.60,
            "fair_value": 0.60,
            "bankroll_tier_id": "T0",
            "risk_mode": "NORMAL",
            "entry_price": 0.50,
            "size": 1.0,
        },
    }
    real_close = {
        "timestamp_utc": "2026-06-28T10:01:00Z",
        "event_type": "trade_close",
        "run_id": run_id,
        "payload": {
            "paper_trade_replay_key": rkey,
            "position_id": "pos_real",
            "exit_price": 0.60,
            "pnl": 0.10,
            "exit_reason": "take_profit",
        },
    }
    test_close = {
        "timestamp_utc": "2026-06-28T10:02:00Z",
        "event_type": "trade_close",
        "run_id": "run_test",
        "payload": {
            "position_id": "pos_test",
            "pnl": 1.0,  # round number = test_event
            "exit_reason": "test",
        },
    }

    with open(temp_quant_data / "trade_journal" / f"{date_str}.jsonl", "w") as f:
        f.write(json.dumps(real_open) + "\n")
        f.write(json.dumps(real_close) + "\n")
        f.write(json.dumps(test_close) + "\n")

    builder = CanonicalContextBuilder(temp_quant_data, [date_str])
    builder.load_all()
    rows, summary = builder.compile()

    assert len(rows) == 2
    signal_pnl = summary["signal_driven_pnl_summary"]
    assert signal_pnl["total_trades"] == 1
    assert signal_pnl["total_realized_pnl"] == pytest.approx(0.10, abs=1e-5)
    # test_event row excluded
    assert summary["field_availability"]["test_events_excluded"] == 1
