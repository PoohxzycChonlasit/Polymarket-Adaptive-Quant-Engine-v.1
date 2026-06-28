from __future__ import annotations

from types import SimpleNamespace

from polymarket.client import OrderReceipt
from polymarket.trader import PolymarketTrader
from utils.risk_manager import RiskPlan


class _CollectingQuantLogger:
    def __init__(self) -> None:
        self.mode = "paper"
        self.events: list[tuple[str, dict]] = []
        self.disabled_categories: set[str] = set()

    def log_trade_open(self, payload: dict) -> bool:
        self.events.append(("trade_open", payload))
        return True

    def log_trade_close(self, payload: dict) -> bool:
        self.events.append(("trade_close", payload))
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


def _risk_plan() -> RiskPlan:
    return RiskPlan(
        account_balance=100.0,
        entry_price=0.50,
        stop_loss_price=0.46,
        take_profit_price=0.55,
        partial_tp_price=0.53,
        risk_amount=1.0,
        kelly_fraction=0.0,
        capped_fraction=0.01,
        position_size=2.0,
        notional_size=1.0,
        stop_loss_pct=0.08,
    )


def _record_entry_context(trader: PolymarketTrader) -> None:
    trader._record_quant_detail(
        "BTC",
        market_id="pm-5m-btc",
        side="YES",
        candidate_id="candidate_logical",
        candidate_trace_id="ct_legacy",
        candidate_instance_id="candidate_0123456789abcdef0123456789abcdef",
        candidate_instance_trace_id="ct_0123456789abcdef",
        candidate_instance_created_at="2026-06-15T00:00:00Z",
        candidate_instance_identity_schema_version="1.0",
        candidate_instance_identity_source="opportunity_candidate",
        legacy_candidate_identity_source="phase2_market_side_epoch_hash",
        signal_name="trend",
        signal_reason="trend_yes_adx_ema_confirmed",
        true_probability=0.63,
        entry_ev=0.04,
    )


def _build_metadata(trader: PolymarketTrader) -> dict[str, object]:
    return trader._build_trade_position_metadata(
        strategy="ENTER_QUANT",
        signal_strategy="trend",
        token_id="token-yes",
        outcome="YES",
        entry_ev=0.04,
        confidence=0.72,
        delta_regime="TRENDING",
        condition_id="condition-1",
        epoch_start_ts=1770000000,
        market_slug="btc-up-down",
        lifecycle_phase="OPENING_SCAN",
        ticker="BTC",
        true_probability=0.63,
        fair_value=0.63,
    )


def test_position_metadata_stores_immutable_entry_attribution_snapshot() -> None:
    trader = _trader()
    _record_entry_context(trader)

    metadata = _build_metadata(trader)
    attribution = metadata["entry_attribution"]
    trader.last_quant_details["BTC"]["signal_name"] = "mutated_after_birth"

    assert attribution == {
        "candidate_id": "candidate_logical",
        "candidate_trace_id": "ct_legacy",
        "candidate_instance_id": "candidate_0123456789abcdef0123456789abcdef",
        "candidate_instance_trace_id": "ct_0123456789abcdef",
        "candidate_instance_created_at": "2026-06-15T00:00:00Z",
        "candidate_instance_identity_schema_version": "1.0",
        "candidate_instance_identity_source": "opportunity_candidate",
        "legacy_candidate_identity_source": "phase2_market_side_epoch_hash",
        "signal_name": "trend",
        "signal_reason": "trend_yes_adx_ema_confirmed",
        "paper_trade_replay_key": "condition-1|1770000000|BTC|YES|token-yes",
        "entry_ev": 0.04,
        "entry_probability": 0.63,
        "selected_side": "YES",
    }


def test_trade_open_and_close_share_entry_attribution_and_position_id() -> None:
    trader = _trader()
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    _record_entry_context(trader)
    metadata = _build_metadata(trader)
    position = trader.tracker.open_position(
        symbol="pm-5m-btc",
        source="polymarket",
        side="BUY",
        entry_price=0.50,
        size=2.0,
        stop_loss=0.46,
        take_profit=0.55,
        order_id="paper-entry",
        metadata=metadata,
    )
    receipt = OrderReceipt(
        order_id="paper-entry",
        status="paper",
        token_id="token-yes",
        side="BUY",
        price=0.50,
        size=2.0,
    )

    trader._emit_trade_opened_event(
        market_id="pm-5m-btc",
        ticker="BTC",
        token_id="token-yes",
        outcome="YES",
        receipt=receipt,
        risk_plan=_risk_plan(),
        entry_price=0.50,
        strategy="ENTER_QUANT",
        epoch_start=1770000000,
        condition_id="condition-1",
        position_id=position.position_id,
        entry_attribution=metadata["entry_attribution"],
    )
    trader._emit_trade_closed_event(
        position=position,
        reason="take_profit",
        exit_price=0.60,
        size=2.0,
        pnl=0.20,
        receipt=None,
    )

    open_payload = [payload for event, payload in collector.events if event == "trade_open"][-1]
    close_payload = [payload for event, payload in collector.events if event == "trade_close"][-1]
    assert open_payload["position_id"] == close_payload["position_id"] == position.position_id
    assert open_payload["entry_attribution"] == close_payload["entry_attribution"] == metadata["entry_attribution"]
    for field_name in (
        "paper_trade_replay_key",
        "candidate_id",
        "candidate_instance_id",
        "signal_name",
        "signal_reason",
    ):
        assert open_payload[field_name] == close_payload[field_name] == metadata["entry_attribution"][field_name]


def test_legacy_metadata_is_compatible_and_does_not_change_execution_context() -> None:
    trader = _trader()
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    position = SimpleNamespace(
        position_id="legacy-pos",
        symbol="pm-5m-btc",
        side="BUY",
        entry_price=0.50,
        entry_time="2026-06-15T00:00:00Z",
        size=2.0,
        metadata={"token_id": "token-yes", "outcome": "YES"},
    )

    trader._emit_trade_closed_event(
        position=position,
        reason="stop_loss",
        exit_price=0.45,
        size=2.0,
        pnl=-0.10,
        receipt=None,
    )
    execution_payload = trader._execution_payload_with_parent_context(
        {"source_market_id": "pm-5m-btc", "outcome": "YES"}
    )

    close_payload = [payload for event, payload in collector.events if event == "trade_close"][-1]
    assert close_payload["entry_attribution_status"] == "missing_legacy"
    assert "entry_attribution" not in close_payload
    assert "entry_attribution" not in execution_payload


def test_quant_detail_derives_and_preserves_candidate_trace_id() -> None:
    trader = _trader()
    # 1. Test derivation when missing
    detail = trader._record_quant_detail(
        "BTC",
        market_id="pm-5m-btc",
        side="YES",
        candidate_id="logical-id",
        candidate_instance_id="instance-id",
        candidate_instance_created_at="2026-06-15T00:00:00Z",
        candidate_instance_trace_id="ct_instance",
        legacy_candidate_identity_source="phase2_market_side_epoch_hash",
        epoch_start_ts=1770000000,
        condition_id="condition-1",
        token_id="token-yes",
    )
    assert detail.get("candidate_trace_id") is not None
    assert detail["candidate_trace_id"].startswith("ct_")
    assert detail["candidate_instance_trace_id"] == "ct_instance"

    # 2. Test preservation when already present
    detail_explicit = trader._record_quant_detail(
        "BTC",
        market_id="pm-5m-btc",
        side="YES",
        candidate_id="logical-id",
        candidate_trace_id="ct_explicit_trace",
        candidate_instance_id="instance-id",
        candidate_instance_created_at="2026-06-15T00:00:00Z",
        candidate_instance_trace_id="ct_instance",
        legacy_candidate_identity_source="phase2_market_side_epoch_hash",
        epoch_start_ts=1770000000,
        condition_id="condition-1",
        token_id="token-yes",
    )
    assert detail_explicit["candidate_trace_id"] == "ct_explicit_trace"
    assert detail_explicit["candidate_instance_trace_id"] == "ct_instance"

