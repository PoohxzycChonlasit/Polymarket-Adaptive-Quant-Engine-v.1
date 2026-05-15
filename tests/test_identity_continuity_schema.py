"""tests/test_identity_continuity_schema.py

Targeted tests for the additive identity continuity schema patch applied to
QuantEventLogger._with_candidate_trace_identity.

Scope: observability-only.  No runtime, strategy, risk, or execution behavior
is tested or changed here.  All new fields are backward-compatible additions.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from utils.quant_event_logger import QuantEventLogger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fixed_now() -> datetime:
    return datetime(2026, 5, 8, 12, 30, 0, tzinfo=timezone.utc)


def _make_logger(tmp_path: Path, *, run_id: str = "run-abcdefgh", schema_version: str = "1.0") -> QuantEventLogger:
    return QuantEventLogger(
        base_dir=tmp_path,
        enabled=True,
        mode="paper",
        run_id=run_id,
        schema_version=schema_version,
        now=_fixed_now,
    )


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _identity_payload(*, producer: str = "decision_log") -> dict:
    """Minimal payload that carries enough fields for identity derivation."""
    return {
        "market_id": "btc-5m-20260508",
        "condition_id": "condition-1",
        "token_id": "token-yes",
        "side": "YES",
        "lifecycle_phase": "OPENING_SCAN",
        "market_epoch_start": 1770000000,
        "producer_event_type": producer,
        "producer": producer,
    }


TS = "2026-05-08T12:30:00Z"


# ---------------------------------------------------------------------------
# replay_chain_id
# ---------------------------------------------------------------------------

def test_replay_chain_id_present_and_prefixed(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    enriched = logger._with_candidate_trace_identity(_identity_payload(), TS)
    assert "replay_chain_id" in enriched, "replay_chain_id must be emitted when identity is derivable"
    assert enriched["replay_chain_id"].startswith("rc_")


def test_replay_chain_id_stable_across_calls(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    payload = _identity_payload()
    e1 = logger._with_candidate_trace_identity(dict(payload), TS)
    e2 = logger._with_candidate_trace_identity(dict(payload), TS)
    assert e1["replay_chain_id"] == e2["replay_chain_id"], "replay_chain_id must be deterministic"


def test_replay_chain_id_contains_run_fragment(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path, run_id="run-abcdefgh")
    enriched = logger._with_candidate_trace_identity(_identity_payload(), TS)
    assert "run-abcd" in enriched["replay_chain_id"], "replay_chain_id must embed the first 8 chars of run_id"


# ---------------------------------------------------------------------------
# lifecycle_instance_id
# ---------------------------------------------------------------------------

def test_lifecycle_instance_id_present_and_prefixed(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    enriched = logger._with_candidate_trace_identity(_identity_payload(), TS)
    assert "lifecycle_instance_id" in enriched
    assert enriched["lifecycle_instance_id"].startswith("li_")


def test_lifecycle_instance_id_stable_for_same_market_and_time(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    p1 = _identity_payload()
    p1["market_epoch_start"] = 1770000000
    p2 = dict(p1)
    # Different token_id, same market window — lifecycle_instance_id must match
    e1 = logger._with_candidate_trace_identity(p1, TS)
    e2 = logger._with_candidate_trace_identity(p2, TS)
    assert e1["lifecycle_instance_id"] == e2["lifecycle_instance_id"]


# ---------------------------------------------------------------------------
# inventory_context_id
# ---------------------------------------------------------------------------

def test_inventory_context_id_present(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    enriched = logger._with_candidate_trace_identity(_identity_payload(), TS)
    assert "inventory_context_id" in enriched
    assert enriched["inventory_context_id"].startswith("inv_")


# ---------------------------------------------------------------------------
# risk_trace_id (risk_log producer)
# ---------------------------------------------------------------------------

def test_risk_trace_id_emitted_for_risk_producer(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    enriched = logger._with_candidate_trace_identity(_identity_payload(producer="risk_log"), TS)
    assert "risk_trace_id" in enriched, "risk_trace_id must be emitted for risk_log producer"
    assert enriched["risk_trace_id"].startswith("rt_")
    assert enriched["identity_propagation_stage"] == "risk"


def test_risk_trace_id_not_present_for_decision_producer(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    enriched = logger._with_candidate_trace_identity(_identity_payload(producer="decision_log"), TS)
    assert "risk_trace_id" not in enriched
    assert "execution_trace_id" not in enriched
    assert enriched["identity_propagation_stage"] == "decision"


# ---------------------------------------------------------------------------
# execution_trace_id (execution_log producer)
# ---------------------------------------------------------------------------

def test_execution_trace_id_emitted_for_execution_producer(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    enriched = logger._with_candidate_trace_identity(_identity_payload(producer="execution_log"), TS)
    assert "execution_trace_id" in enriched, "execution_trace_id must be emitted for execution_log producer"
    assert enriched["execution_trace_id"].startswith("et_")
    assert enriched["identity_propagation_stage"] == "execution"


def test_execution_trace_id_not_present_for_risk_producer(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    enriched = logger._with_candidate_trace_identity(_identity_payload(producer="risk_log"), TS)
    assert "execution_trace_id" not in enriched


# ---------------------------------------------------------------------------
# packet_schema_version
# ---------------------------------------------------------------------------

def test_packet_schema_version_emitted_on_every_enrichment(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path, schema_version="2.3")
    # With identity derivable
    enriched = logger._with_candidate_trace_identity(_identity_payload(), TS)
    assert enriched.get("packet_schema_version") == "2.3"


def test_packet_schema_version_emitted_even_when_identity_missing(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path, schema_version="1.9")
    # No identity source fields
    enriched = logger._with_candidate_trace_identity(
        {"decision": "SKIP", "producer_event_type": "decision_log"}, TS
    )
    assert enriched.get("packet_schema_version") == "1.9"


# ---------------------------------------------------------------------------
# identity_source and identity_propagation_stage
# ---------------------------------------------------------------------------

def test_identity_source_set_when_derivable(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    enriched = logger._with_candidate_trace_identity(_identity_payload(), TS)
    assert "identity_source" in enriched
    assert enriched["identity_source"] != "not_derivable"


def test_identity_source_set_to_not_derivable_when_missing(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    enriched = logger._with_candidate_trace_identity({"event": "noise"}, TS)
    assert enriched.get("identity_source") == "not_derivable"


# ---------------------------------------------------------------------------
# lineage_confidence classmethod
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload,expected", [
    (
        {
            "candidate_trace_id": "ct_abc",
            "parent_candidate_trace_id": "ct_parent",
            "market_key": "btc-5m",
            "token_id": "tok",
            "side": "YES",
            "lifecycle_phase": "OPENING_SCAN",
        },
        "DIRECT",
    ),
    (
        {
            "candidate_trace_id": "ct_abc",
            "market_key": "btc-5m",
            "token_id": "tok",
            "side": "YES",
            "lifecycle_phase": "OPENING_SCAN",
        },
        "STRONG",
    ),
    (
        {"candidate_trace_id": "ct_abc", "market_key": "btc-5m"},
        "WEAK",
    ),
    (
        {"candidate_trace_id": "ct_abc"},
        "PROXY",
    ),
    (
        {"market_key": "btc-5m", "side": "YES"},
        "UNKNOWN",
    ),
    (
        {},
        "UNKNOWN",
    ),
])
def test_lineage_confidence_levels(payload: dict, expected: str) -> None:
    assert QuantEventLogger._lineage_confidence(payload) == expected


# ---------------------------------------------------------------------------
# lineage_propagation_stage classmethod
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload,expected_stage", [
    ({"producer_event_type": "risk_log"},       "risk"),
    ({"producer_event_type": "risk_event"},     "risk"),
    ({"producer_event_type": "execution_log"},  "execution"),
    ({"producer_event_type": "trade_open"},     "execution"),
    ({"producer_event_type": "decision_log"},   "decision"),
    ({"producer_event_type": "market_snapshots"}, "pre_decision"),
    ({"producer": "risk_log"},                  "risk"),
    ({"producer": "execution_log"},             "execution"),
    ({},                                        "unknown"),
])
def test_lineage_propagation_stage_classification(payload: dict, expected_stage: str) -> None:
    result = QuantEventLogger._lineage_propagation_stage(payload)
    assert result == expected_stage, f"payload={payload!r}: expected {expected_stage!r}, got {result!r}"


# ---------------------------------------------------------------------------
# Missing-reason fields (no identity source)
# ---------------------------------------------------------------------------

def test_missing_identity_emits_candidate_trace_id_missing_reason(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    enriched = logger._with_candidate_trace_identity(
        {"decision": "SKIP", "producer_event_type": "decision_log"}, TS
    )
    assert "candidate_trace_id" not in enriched
    assert enriched.get("candidate_trace_id_missing_reason") == "no_identity_source_fields"
    assert "lineage_drop_reason" in enriched
    assert enriched.get("lineage_confidence") == "UNKNOWN"
    assert enriched.get("identity_source") == "not_derivable"
    assert "replay_chain_id_missing_reason" in enriched


def test_missing_identity_risk_producer_emits_risk_trace_id_missing_reason(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    enriched = logger._with_candidate_trace_identity(
        {"event": "risk_snapshot", "producer_event_type": "risk_log", "producer": "risk_log"},
        TS,
    )
    assert "candidate_trace_id" not in enriched
    assert "risk_trace_id_missing_reason" in enriched
    assert enriched.get("identity_propagation_stage") == "risk"
    assert "execution_trace_id_missing_reason" not in enriched


def test_missing_identity_execution_producer_emits_execution_trace_id_missing_reason(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path)
    enriched = logger._with_candidate_trace_identity(
        {"event": "paper_fill", "producer_event_type": "execution_log", "producer": "execution_log"},
        TS,
    )
    assert "candidate_trace_id" not in enriched
    assert "execution_trace_id_missing_reason" in enriched
    assert enriched.get("identity_propagation_stage") == "execution"
    assert "risk_trace_id_missing_reason" not in enriched


# ---------------------------------------------------------------------------
# Full JSONL round-trip: risk_log carries trace fields
# ---------------------------------------------------------------------------

def test_risk_log_jsonl_carries_canonical_trace_fields(tmp_path: Path) -> None:
    """End-to-end: log_risk_event must persist replay_chain_id and risk_trace_id to JSONL."""
    logger = _make_logger(tmp_path)
    assert logger.log_risk_event({
        "market_id": "btc-5m-20260508",
        "condition_id": "condition-risk",
        "token_id": "token-yes",
        "side": "YES",
        "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
        "market_epoch_start": 1770000000,
        "producer_event_type": "risk_log",
        "producer": "risk_log",
        "risk_decision": "APPROVED",
    })
    event = _read_jsonl(tmp_path / "risk_log" / "2026-05-08.jsonl")[0]
    p = event["payload"]
    assert p.get("candidate_trace_id", "").startswith("ct_"), "candidate_trace_id missing from risk_log JSONL"
    assert p.get("risk_trace_id", "").startswith("rt_"), "risk_trace_id missing from risk_log JSONL"
    assert p.get("replay_chain_id", "").startswith("rc_"), "replay_chain_id missing from risk_log JSONL"
    assert p.get("identity_propagation_stage") == "risk"
    assert "candidate_trace_id_missing_reason" not in p


def test_execution_log_jsonl_carries_canonical_trace_fields(tmp_path: Path) -> None:
    """End-to-end: log_execution must persist execution_trace_id to JSONL."""
    logger = _make_logger(tmp_path)
    assert logger.log_execution({
        "market_id": "btc-5m-20260508",
        "condition_id": "condition-exec",
        "token_id": "token-yes",
        "side": "YES",
        "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
        "market_epoch_start": 1770000000,
        "producer_event_type": "execution_log",
        "producer": "execution_log",
        "event": "paper_order_submitted",
    })
    event = _read_jsonl(tmp_path / "execution_log" / "2026-05-08.jsonl")[0]
    p = event["payload"]
    assert p.get("candidate_trace_id", "").startswith("ct_"), "candidate_trace_id missing from execution_log JSONL"
    assert p.get("execution_trace_id", "").startswith("et_"), "execution_trace_id missing from execution_log JSONL"
    assert p.get("replay_chain_id", "").startswith("rc_"), "replay_chain_id missing from execution_log JSONL"
    assert p.get("identity_propagation_stage") == "execution"


def test_new_fields_are_backward_compatible_additions_only(tmp_path: Path) -> None:
    """New fields must not remove or overwrite existing payload fields."""
    logger = _make_logger(tmp_path)
    original_value = "my_existing_value"
    payload = {
        **_identity_payload(),
        "some_existing_field": original_value,
        "producer_event_type": "decision_log",
    }
    enriched = logger._with_candidate_trace_identity(dict(payload), TS)
    assert enriched["some_existing_field"] == original_value, "existing fields must not be overwritten"


def test_payload_not_mutated_by_enrichment(tmp_path: Path) -> None:
    """The original payload dict must not be mutated by _with_candidate_trace_identity."""
    logger = _make_logger(tmp_path)
    payload = _identity_payload()
    original_keys = set(payload.keys())
    logger._with_candidate_trace_identity(payload, TS)
    assert set(payload.keys()) == original_keys, "original payload must not be mutated"
