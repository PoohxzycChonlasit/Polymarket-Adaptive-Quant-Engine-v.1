from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from polymarket.trader import PolymarketTrader, TradeOutcome
from utils.quant_event_logger import QuantEventLogger


TRADER_PATH = Path(__file__).resolve().parents[1] / "polymarket" / "trader.py"
SHADOW_FIELDS = {
    "candidate_instance_id",
    "candidate_instance_trace_id",
    "candidate_instance_created_at",
    "candidate_instance_identity_schema_version",
    "candidate_instance_identity_source",
    "legacy_candidate_identity_source",
}


class _CollectingQuantLogger:
    def __init__(self) -> None:
        self.mode = "paper"
        self.schema_version = "test"
        self.disabled_categories: set[str] = set()
        self.events: list[tuple[str, dict]] = []

    def log_decision(self, payload: dict) -> bool:
        self.events.append(("decision", payload))
        return True

    def log_risk_event(self, payload: dict) -> bool:
        self.events.append(("risk", payload))
        return True

    def _with_candidate_trace_identity(self, payload: dict, ticker: str) -> dict:
        return payload


def _trader() -> PolymarketTrader:
    trader = PolymarketTrader()
    trader.settings = SimpleNamespace(
        paper_trading=True,
        dry_run=True,
        account_balance=100.0,
        execution_entry_cutoff_seconds=90,
        hybrid_phase_v1_enabled=False,
    )
    return trader


def test_active_candidate_identity_is_copied_to_quant_detail_with_shadow_names_only() -> None:
    tree = ast.parse(TRADER_PATH.read_text(encoding="utf-8-sig"))
    clob_detail_assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "clob_detail" for target in node.targets)
        and isinstance(node.value, ast.Dict)
    ]

    assert len(clob_detail_assignments) == 1
    keywords = {
        ast.literal_eval(key): value
        for key, value in zip(clob_detail_assignments[0].value.keys, clob_detail_assignments[0].value.values)
        if key is not None
    }
    candidate_fields = {
        "candidate_instance_id": "candidate_id",
        "candidate_instance_trace_id": "candidate_trace_id",
        "candidate_instance_created_at": "candidate_created_at",
        "candidate_instance_identity_schema_version": "candidate_identity_schema_version",
    }
    for shadow_name, candidate_name in candidate_fields.items():
        value = keywords[shadow_name]
        assert isinstance(value, ast.Attribute)
        assert isinstance(value.value, ast.Name)
        assert value.value.id == "candidate"
        assert value.attr == candidate_name

    assert ast.literal_eval(keywords["candidate_instance_identity_source"]) == "opportunity_candidate"
    assert ast.literal_eval(keywords["legacy_candidate_identity_source"]) == "phase2_market_side_epoch_hash"

    string_literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    for field_name in SHADOW_FIELDS:
        assert string_literals.count(field_name) == 2


def test_shadow_identity_reaches_decision_only_and_preserves_legacy_candidate_id() -> None:
    trader = _trader()
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    detail = trader._record_quant_detail(
        "BTC",
        market_id="pm-5m-btc",
        side="SKIP",
        skip_reason="scanner_no_best_trade",
        candidate_id="legacy_logical_candidate",
        candidate_instance_id="candidate_instance",
        candidate_instance_trace_id="ct_instance",
        candidate_instance_created_at="2026-06-15T00:00:00Z",
        candidate_instance_identity_schema_version="1.0",
        candidate_instance_identity_source="opportunity_candidate",
        legacy_candidate_identity_source="phase2_market_side_epoch_hash",
    )
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.60,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="scanner_no_best_trade",
        display=detail,
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    decision_payload = [payload for event, payload in collector.events if event == "decision"][-1]
    risk_payload = [payload for event, payload in collector.events if event == "risk"][-1]
    assert SHADOW_FIELDS <= detail.keys()
    assert decision_payload["candidate_id"] == "legacy_logical_candidate"
    for field_name in SHADOW_FIELDS:
        assert decision_payload[field_name] == detail[field_name]
    assert SHADOW_FIELDS.isdisjoint(risk_payload)


def test_shadow_identity_does_not_reach_execution_or_position_metadata() -> None:
    trader = _trader()
    trader._record_quant_detail(
        "BTC",
        market_id="pm-5m-btc",
        side="YES",
        candidate_instance_id="candidate_instance",
        candidate_instance_trace_id="ct_instance",
        candidate_instance_created_at="2026-06-15T00:00:00Z",
        candidate_instance_identity_schema_version="1.0",
        candidate_instance_identity_source="opportunity_candidate",
        legacy_candidate_identity_source="phase2_market_side_epoch_hash",
    )

    execution_payload = trader._execution_payload_with_parent_context(
        {"source_market_id": "pm-5m-btc", "outcome": "YES"}
    )
    position_metadata = trader._build_trade_position_metadata(
        strategy="test",
        signal_strategy="test",
        token_id="btc-yes-token",
        outcome="YES",
        entry_ev=0.03,
        confidence=0.60,
        delta_regime="NORMAL",
        condition_id="condition-btc",
        epoch_start_ts=1_765_000_000,
        market_slug="btc-updown-5m",
        lifecycle_phase="ACTIVE_INVENTORY_TRADING",
        ticker="BTC",
    )

    assert SHADOW_FIELDS.isdisjoint(execution_payload)
    assert SHADOW_FIELDS.isdisjoint(position_metadata)


def test_pre_signal_skip_does_not_fabricate_candidate_instance_identity() -> None:
    trader = _trader()
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    detail = trader._record_quant_detail(
        "BTC",
        market_id="pm-5m-btc",
        side="SKIP",
        skip_reason="orderbook_unavailable",
    )
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.0,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="orderbook_unavailable",
        display=detail,
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    decision_payload = [payload for event, payload in collector.events if event == "decision"][-1]
    assert SHADOW_FIELDS.isdisjoint(decision_payload)


def test_candidate_instance_trace_does_not_replace_legacy_canonical_trace() -> None:
    legacy_payload = {
        "candidate_id": "legacy_logical_candidate",
        "market_id": "pm-5m-btc",
        "side": "YES",
    }
    shadow_payload = {
        **legacy_payload,
        "candidate_instance_trace_id": "ct_instance",
    }

    timestamp = "2026-06-15T00:00:00Z"
    legacy_identity = QuantEventLogger._candidate_trace_identity_fields(legacy_payload, timestamp)
    shadow_identity = QuantEventLogger._candidate_trace_identity_fields(shadow_payload, timestamp)

    assert shadow_identity["candidate_trace_id"] == legacy_identity["candidate_trace_id"]
    assert shadow_identity["candidate_trace_id"] != shadow_payload["candidate_instance_trace_id"]
