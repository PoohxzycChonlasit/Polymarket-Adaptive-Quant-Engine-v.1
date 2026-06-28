"""
Paired Trade Identity Continuity Instrumentation v1 tests.

Verifies that trade_open and trade_close events carry stable cross-producer
identity fields enabling replay and maturity tracking.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from utils.quant_event_logger import QuantEventLogger


def _fixed_now() -> datetime:
    return datetime(2026, 5, 18, 2, 50, 6, tzinfo=timezone.utc)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


# ---------------------------------------------------------------------------
# paper_trade_replay_key generation
# ---------------------------------------------------------------------------

def test_compute_paper_trade_replay_key_stable_with_all_fields() -> None:
    payload = {
        "condition_id": "0xabc123",
        "epoch_start_ts": 1779072600,
        "asset": "ETH",
        "side": "NO",
        "token_id": "token-no-eth",
    }
    key = QuantEventLogger._compute_paper_trade_replay_key(payload)
    assert key == "0xabc123|1779072600|ETH|NO|token-no-eth"


def test_compute_paper_trade_replay_key_stable_field_order_invariant() -> None:
    payload_a = {
        "condition_id": "0xabc123",
        "epoch_start_ts": 1779072600,
        "asset": "ETH",
        "side": "NO",
        "token_id": "token-no-eth",
    }
    payload_b = dict(reversed(list(payload_a.items())))
    assert QuantEventLogger._compute_paper_trade_replay_key(payload_a) == \
           QuantEventLogger._compute_paper_trade_replay_key(payload_b)


def test_compute_paper_trade_replay_key_empty_when_condition_id_missing() -> None:
    payload = {
        "epoch_start_ts": 1779072600,
        "asset": "ETH",
        "side": "NO",
        "token_id": "token-no-eth",
    }
    assert QuantEventLogger._compute_paper_trade_replay_key(payload) == ""


def test_compute_paper_trade_replay_key_empty_when_epoch_missing() -> None:
    payload = {
        "condition_id": "0xabc123",
        "asset": "ETH",
        "side": "NO",
        "token_id": "token-no-eth",
    }
    assert QuantEventLogger._compute_paper_trade_replay_key(payload) == ""


def test_compute_paper_trade_replay_key_empty_when_token_id_missing() -> None:
    payload = {
        "condition_id": "0xabc123",
        "epoch_start_ts": 1779072600,
        "asset": "ETH",
        "side": "NO",
    }
    assert QuantEventLogger._compute_paper_trade_replay_key(payload) == ""


def test_compute_paper_trade_replay_key_accepts_aliases() -> None:
    """conditionId alias and tokenId alias resolve to the same key."""
    canonical = {
        "condition_id": "0xabc123",
        "epoch_start_ts": 1779072600,
        "asset": "ETH",
        "side": "NO",
        "token_id": "token-no-eth",
    }
    alias = {
        "conditionId": "0xabc123",
        "epoch_start_ts": 1779072600,
        "ticker": "ETH",
        "asset_side": "NO",
        "tokenId": "token-no-eth",
    }
    assert QuantEventLogger._compute_paper_trade_replay_key(canonical) == \
           QuantEventLogger._compute_paper_trade_replay_key(alias)


# ---------------------------------------------------------------------------
# Logger emits paper_trade_replay_key on trade_open / trade_close events
# ---------------------------------------------------------------------------

def _trade_open_payload() -> dict:
    return {
        "event_type": "trade_open",
        "condition_id": "0xabc123",
        "epoch_start_ts": 1779072600,
        "asset": "ETH",
        "ticker": "ETH",
        "side": "NO",
        "token_id": "token-no-eth",
        "outcome": "NO",
        "entry_price": 0.50,
        "paper_trade_replay_key": "0xabc123|1779072600|ETH|NO|token-no-eth",
        "true_probability": 0.644,
        "ev_after_spread": 0.144,
        "confidence": 0.541,
        "candidate_peak_favorable": None,
        "candidate_peak_adverse": None,
    }


def test_trade_open_event_carries_paper_trade_replay_key(tmp_path: Path) -> None:
    logger = QuantEventLogger(
        base_dir=tmp_path, enabled=True, mode="paper",
        run_id="run-test", now=_fixed_now,
    )
    payload = _trade_open_payload()
    assert logger.log_trade_open(payload)

    events = _read_jsonl(tmp_path / "trade_journal" / "2026-05-18.jsonl")
    assert len(events) == 1
    p = events[0]["payload"]
    assert p["paper_trade_replay_key"] == "0xabc123|1779072600|ETH|NO|token-no-eth"
    assert p["condition_id"] == "0xabc123"
    assert p["epoch_start_ts"] == 1779072600


def test_trade_open_event_carries_model_output_fields(tmp_path: Path) -> None:
    logger = QuantEventLogger(
        base_dir=tmp_path, enabled=True, mode="paper",
        run_id="run-test", now=_fixed_now,
    )
    assert logger.log_trade_open(_trade_open_payload())

    p = _read_jsonl(tmp_path / "trade_journal" / "2026-05-18.jsonl")[0]["payload"]
    assert p["true_probability"] == 0.644
    assert p["ev_after_spread"] == 0.144
    assert p["confidence"] == 0.541
    assert "candidate_peak_favorable" in p
    assert "candidate_peak_adverse" in p


def test_trade_close_event_carries_paper_trade_replay_key(tmp_path: Path) -> None:
    logger = QuantEventLogger(
        base_dir=tmp_path, enabled=True, mode="paper",
        run_id="run-test", now=_fixed_now,
    )
    payload = {
        "condition_id": "0xabc123",
        "epoch_start_ts": 1779072600,
        "asset": "ETH",
        "ticker": "ETH",
        "side": "NO",
        "token_id": "token-no-eth",
        "outcome": "NO",
        "reason": "stop_loss",
        "exit_price": 0.40,
        "exit_timestamp": "2026-05-18T02:54:00Z",
        "hold_seconds": 234,
        "pnl": -0.010050,
        "paper_trade_replay_key": "0xabc123|1779072600|ETH|NO|token-no-eth",
        "candidate_peak_favorable": None,
        "candidate_peak_adverse": None,
    }
    assert logger.log_trade_close(payload)

    p = _read_jsonl(tmp_path / "trade_journal" / "2026-05-18.jsonl")[0]["payload"]
    assert p["paper_trade_replay_key"] == "0xabc123|1779072600|ETH|NO|token-no-eth"
    assert p["exit_timestamp"] == "2026-05-18T02:54:00Z"
    assert p["hold_seconds"] == 234
    assert "candidate_peak_favorable" in p
    assert "candidate_peak_adverse" in p


def test_trade_open_and_close_share_same_replay_key(tmp_path: Path) -> None:
    """The replay key written on open must match the one written on close."""
    logger = QuantEventLogger(
        base_dir=tmp_path, enabled=True, mode="paper",
        run_id="run-test", now=_fixed_now,
    )
    condition_id = "0xb3337dc869c2d8"
    epoch_start_ts = 1779072600
    expected_key = f"{condition_id}|{epoch_start_ts}|ETH|NO|token-no-eth"

    open_payload = {
        "condition_id": condition_id,
        "epoch_start_ts": epoch_start_ts,
        "asset": "ETH",
        "ticker": "ETH",
        "side": "NO",
        "token_id": "token-no-eth",
        "outcome": "NO",
        "entry_price": 0.50,
        "paper_trade_replay_key": expected_key,
        "true_probability": 0.644,
        "ev_after_spread": 0.144,
        "confidence": 0.541,
        "candidate_peak_favorable": None,
        "candidate_peak_adverse": None,
    }
    close_payload = {
        "condition_id": condition_id,
        "epoch_start_ts": epoch_start_ts,
        "asset": "ETH",
        "ticker": "ETH",
        "side": "NO",
        "token_id": "token-no-eth",
        "outcome": "NO",
        "reason": "stop_loss",
        "exit_price": 0.40,
        "exit_timestamp": "2026-05-18T02:54:00Z",
        "hold_seconds": 234,
        "pnl": -0.010050,
        "paper_trade_replay_key": expected_key,
        "candidate_peak_favorable": None,
        "candidate_peak_adverse": None,
    }

    assert logger.log_trade_open(open_payload)
    assert logger.log_trade_close(close_payload)

    events = _read_jsonl(tmp_path / "trade_journal" / "2026-05-18.jsonl")
    assert len(events) == 2
    open_key = events[0]["payload"]["paper_trade_replay_key"]
    close_key = events[1]["payload"]["paper_trade_replay_key"]
    assert open_key == close_key == expected_key


def test_replay_key_auto_computed_by_logger_when_not_in_payload(tmp_path: Path) -> None:
    """Logger computes paper_trade_replay_key automatically from identity fields."""
    logger = QuantEventLogger(
        base_dir=tmp_path, enabled=True, mode="paper",
        run_id="run-test", now=_fixed_now,
    )
    payload = {
        "condition_id": "0xabc123",
        "epoch_start_ts": 1779072600,
        "ticker": "ETH",
        "side": "NO",
        "token_id": "token-no-eth",
        "outcome": "NO",
        "entry_price": 0.50,
    }
    assert logger.log_trade_open(payload)

    p = _read_jsonl(tmp_path / "trade_journal" / "2026-05-18.jsonl")[0]["payload"]
    assert p["paper_trade_replay_key"] == "0xabc123|1779072600|ETH|NO|token-no-eth"


# ---------------------------------------------------------------------------
# Fail-soft: missing optional fields don't crash
# ---------------------------------------------------------------------------

def test_trade_open_without_model_output_fields_writes_successfully(tmp_path: Path) -> None:
    """trade_open without model output fields must not raise."""
    logger = QuantEventLogger(
        base_dir=tmp_path, enabled=True, mode="paper",
        run_id="run-test", now=_fixed_now,
    )
    minimal = {"market_id": "pm-5m-eth", "side": "NO", "entry_price": 0.50}
    assert logger.log_trade_open(minimal)
    events = _read_jsonl(tmp_path / "trade_journal" / "2026-05-18.jsonl")
    assert len(events) == 1


def test_trade_close_without_condition_id_writes_successfully(tmp_path: Path) -> None:
    """trade_close without condition_id must not crash; replay key will be empty."""
    logger = QuantEventLogger(
        base_dir=tmp_path, enabled=True, mode="paper",
        run_id="run-test", now=_fixed_now,
    )
    payload = {
        "market_id": "pm-5m-eth",
        "reason": "stop_loss",
        "exit_price": 0.40,
        "pnl": -0.01,
    }
    assert logger.log_trade_close(payload)
    p = _read_jsonl(tmp_path / "trade_journal" / "2026-05-18.jsonl")[0]["payload"]
    assert p.get("paper_trade_replay_key", "") == ""


def test_trade_close_without_hold_seconds_writes_successfully(tmp_path: Path) -> None:
    """trade_close without hold_seconds is valid; field may be absent or None."""
    logger = QuantEventLogger(
        base_dir=tmp_path, enabled=True, mode="paper",
        run_id="run-test", now=_fixed_now,
    )
    payload = {
        "condition_id": "0xabc123",
        "epoch_start_ts": 1779072600,
        "side": "NO",
        "token_id": "token-no-eth",
        "outcome": "NO",
        "reason": "stop_loss",
        "exit_price": 0.40,
        "pnl": -0.01,
    }
    assert logger.log_trade_close(payload)
    events = _read_jsonl(tmp_path / "trade_journal" / "2026-05-18.jsonl")
    assert len(events) == 1
    # paper_trade_replay_key auto-computed where possible
    p = events[0]["payload"]
    assert "0xabc123" in p.get("paper_trade_replay_key", "")


# ---------------------------------------------------------------------------
# inventory_context_id propagation across producers
# ---------------------------------------------------------------------------

def test_inventory_context_id_stable_across_open_and_close_producers(tmp_path: Path) -> None:
    """Same market_key + time_bucket → same lifecycle_instance_id and inventory_context_id."""
    logger = QuantEventLogger(
        base_dir=tmp_path, enabled=True, mode="paper",
        run_id="run-test", now=_fixed_now,
    )
    shared_fields = {
        "condition_id": "0xabc123",
        "market_key": "pm-5m-eth",
        "epoch_start_ts": 1779072600,
        "side": "NO",
        "token_id": "token-no-eth",
        "lifecycle_phase": "OPENING_SCAN",
    }
    assert logger.log_trade_open({**shared_fields, "entry_price": 0.50})
    assert logger.log_trade_close({**shared_fields, "reason": "stop_loss", "exit_price": 0.40, "pnl": -0.01})

    events = _read_jsonl(tmp_path / "trade_journal" / "2026-05-18.jsonl")
    open_payload = events[0]["payload"]
    close_payload = events[1]["payload"]
    assert open_payload["inventory_context_id"] == close_payload["inventory_context_id"]
    assert open_payload["lifecycle_instance_id"] == close_payload["lifecycle_instance_id"]
