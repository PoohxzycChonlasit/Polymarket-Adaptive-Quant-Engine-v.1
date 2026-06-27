import json
from pathlib import Path
import pytest
from tools.canonical_trade_context_builder import CanonicalContextBuilder, uuid_hash_key

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
