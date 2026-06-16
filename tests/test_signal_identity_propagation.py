from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from polymarket.trader import PolymarketTrader, TradeOutcome


TRADER_PATH = Path(__file__).resolve().parents[1] / "polymarket" / "trader.py"


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


def _decision_payload(trader: PolymarketTrader, display: dict[str, object]) -> dict:
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.60,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="scanner_no_best_trade",
        display=display,
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    return [payload for event, payload in collector.events if event == "decision"][-1]


def test_active_analysis_handoff_copies_signal_identity_into_quant_detail() -> None:
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
    for field_name in ("signal_name", "signal_reason"):
        assert field_name in keywords
        value = keywords[field_name]
        assert isinstance(value, ast.Attribute)
        assert isinstance(value.value, ast.Name)
        assert value.value.id == "signal"
        assert value.attr == field_name


def test_signal_identity_survives_quant_detail_cache_and_decision_payload() -> None:
    trader = _trader()
    detail = trader._record_quant_detail(
        "BTC",
        market_id="pm-5m-btc",
        side="SKIP",
        signal_name="NO_SIGNAL",
        signal_reason="no_strategy_met_threshold",
    )

    assert trader.last_quant_details["BTC"]["signal_name"] == "NO_SIGNAL"
    assert trader.last_quant_details["BTC"]["signal_reason"] == "no_strategy_met_threshold"

    payload = _decision_payload(trader, detail)
    assert payload["signal_name"] == "NO_SIGNAL"
    assert payload["signal_reason"] == "no_strategy_met_threshold"


def test_pre_signal_decision_does_not_fabricate_signal_identity() -> None:
    trader = _trader()
    detail = trader._record_quant_detail(
        "BTC",
        market_id="pm-5m-btc",
        side="SKIP",
        skip_reason="orderbook_unavailable",
    )

    assert "signal_name" not in detail
    assert "signal_reason" not in detail

    payload = _decision_payload(trader, detail)
    assert "signal_name" not in payload
    assert "signal_reason" not in payload


def test_two_tier_attribution_model_approved_yes() -> None:
    # 1. Model-approved trade YES while strategy is quiet produces PROBABILITY_EV_EDGE
    signal = SimpleNamespace(signal_name="NO_SIGNAL", signal_reason="no_strategy_met_threshold")
    ev_result = SimpleNamespace(approved=True, side="YES")
    model_side = "YES"

    clob_detail = {
        "signal_name": signal.signal_name,
        "signal_reason": signal.signal_reason,
    }

    is_model_trade = model_side in ("YES", "NO") and ev_result is not None and ev_result.approved
    clob_detail["strategy_signal_name"] = signal.signal_name
    clob_detail["strategy_signal_reason"] = signal.signal_reason
    if is_model_trade:
        clob_detail["signal_name"] = "PROBABILITY_EV_EDGE"
        clob_detail["signal_reason"] = f"{model_side.lower()}_ev_above_threshold"

    assert clob_detail["signal_name"] == "PROBABILITY_EV_EDGE"
    assert clob_detail["signal_reason"] == "yes_ev_above_threshold"
    assert clob_detail["strategy_signal_name"] == "NO_SIGNAL"
    assert clob_detail["strategy_signal_reason"] == "no_strategy_met_threshold"


def test_two_tier_attribution_model_approved_no() -> None:
    # 1. Model-approved trade NO while strategy is quiet produces PROBABILITY_EV_EDGE
    signal = SimpleNamespace(signal_name="NO_SIGNAL", signal_reason="no_strategy_met_threshold")
    ev_result = SimpleNamespace(approved=True, side="NO")
    model_side = "NO"

    clob_detail = {
        "signal_name": signal.signal_name,
        "signal_reason": signal.signal_reason,
    }

    is_model_trade = model_side in ("YES", "NO") and ev_result is not None and ev_result.approved
    clob_detail["strategy_signal_name"] = signal.signal_name
    clob_detail["strategy_signal_reason"] = signal.signal_reason
    if is_model_trade:
        clob_detail["signal_name"] = "PROBABILITY_EV_EDGE"
        clob_detail["signal_reason"] = f"{model_side.lower()}_ev_above_threshold"

    assert clob_detail["signal_name"] == "PROBABILITY_EV_EDGE"
    assert clob_detail["signal_reason"] == "no_ev_above_threshold"
    assert clob_detail["strategy_signal_name"] == "NO_SIGNAL"
    assert clob_detail["strategy_signal_reason"] == "no_strategy_met_threshold"


def test_two_tier_attribution_non_model_approved() -> None:
    # 2. Non-model-approved path preserves original strategy signal
    signal = SimpleNamespace(signal_name="reversion", signal_reason="rsi_oversold")
    ev_result = SimpleNamespace(approved=False, side="YES")
    model_side = "YES"

    clob_detail = {
        "signal_name": signal.signal_name,
        "signal_reason": signal.signal_reason,
    }

    is_model_trade = model_side in ("YES", "NO") and ev_result is not None and ev_result.approved
    clob_detail["strategy_signal_name"] = signal.signal_name
    clob_detail["strategy_signal_reason"] = signal.signal_reason
    if is_model_trade:
        clob_detail["signal_name"] = "PROBABILITY_EV_EDGE"
        clob_detail["signal_reason"] = f"{model_side.lower()}_ev_above_threshold"

    assert clob_detail["signal_name"] == "reversion"
    assert clob_detail["signal_reason"] == "rsi_oversold"
    assert clob_detail["strategy_signal_name"] == "reversion"
    assert clob_detail["strategy_signal_reason"] == "rsi_oversold"

