import pytest
from unittest.mock import MagicMock
from pathlib import Path
from polymarket.trader import PolymarketTrader
from utils.position_tracker import PositionTracker
from config.settings import Settings

from dataclasses import dataclass, asdict

@dataclass
class DummyOrderReceipt:
    order_id: str
    status: str
    filled_size: float
    remaining_size: float
    price: float = 0.50
    size: float = 10.0

@pytest.fixture
def mock_settings():
    s = Settings()
    s.paper_trading = True
    s.account_balance = 1000.0
    s.quant_data_enabled = True
    s.quant_data_dir = "runtime/test_quant_data"
    return s

def test_telemetry_backfill_open_to_close(mock_settings, tmp_path):
    mock_settings.quant_data_dir = str(tmp_path / "quant_data")
    
    # Instantiate trader
    trader = PolymarketTrader(settings=mock_settings)
    
    # Mock active components
    market = MagicMock()
    market.market_id = "test-market-123"
    market.question = "Will BTC exceed 100k?"
    
    receipt = DummyOrderReceipt(
        order_id="order_111",
        status="filled",
        filled_size=10.0,
        remaining_size=0.0
    )
    
    risk_plan = MagicMock()
    risk_plan.position_size = 10.0
    risk_plan.notional_size = 5.0
    risk_plan.stop_loss_price = 0.40
    risk_plan.risk_amount = 5.0
    
    timing_detail = {
        "lifecycle_phase": "OPENING_SCAN",
    }
    
    clob_detail = {
        "signal_name": "PROBABILITY_EV_EDGE",
        "signal_reason": "High EV detected",
        "strategy_signal_name": "SCALPER_YES",
        "strategy_signal_reason": "Momentum positive",
    }
    
    ptb_info = MagicMock()
    ptb_info.epoch_start_ts = 1782518400
    ptb_info.seconds_remaining = 120
    
    tier = MagicMock()
    tier.value = "T0_MICRO_SEED"
    trader.bankroll_family = "MICRO"
    
    # Mock emit to capture the events
    emitted_events = []
    trader._emit_quant_event = lambda event_type, payload: emitted_events.append((event_type, payload))
    
    # Reconstruct true prob & fair value
    _true_prob = 0.65
    
    # Call _build_trade_position_metadata and open position
    metadata = trader._build_trade_position_metadata(
        strategy="ENTER",
        signal_strategy="scalper",
        token_id="token_yes",
        outcome="YES",
        entry_ev=0.15,
        confidence=0.80,
        delta_regime="TREND",
        condition_id="cond_abc",
        epoch_start_ts=ptb_info.epoch_start_ts,
        market_slug="btc-100k",
        lifecycle_phase=timing_detail["lifecycle_phase"],
        ticker="BTC",
        true_probability=_true_prob,
        fair_value=_true_prob,
        signal_name=clob_detail["signal_name"],
        signal_reason=clob_detail["signal_reason"],
        strategy_signal_name=clob_detail["strategy_signal_name"],
        strategy_signal_reason=clob_detail["strategy_signal_reason"],
        bankroll_tier_id=tier.value,
        bankroll_family=trader.bankroll_family,
        risk_mode="NORMAL",
        risk_budget=float(risk_plan.risk_amount),
        current_exposure=0.0,
        target_exposure=float(risk_plan.notional_size),
        notional_size=float(risk_plan.notional_size),
        seconds_remaining=int(ptb_info.seconds_remaining),
    )
    
    # Verify metadata fields are packed correctly
    assert metadata["bankroll_tier_id"] == "T0_MICRO_SEED"
    assert metadata["bankroll_family"] == "MICRO"
    assert metadata["risk_mode"] == "NORMAL"
    assert metadata["risk_budget"] == 5.0
    assert metadata["seconds_remaining"] == 120
    
    # Register position in tracker
    position = trader.tracker.open_position(
        symbol=market.market_id,
        source="polymarket",
        side="BUY",
        entry_price=0.50,
        size=risk_plan.position_size,
        stop_loss=risk_plan.stop_loss_price,
        take_profit=0.55,
        order_id=receipt.order_id,
        metadata=metadata,
    )
    
    # Verify position tracker has the metadata
    assert position.metadata["bankroll_family"] == "MICRO"
    
    # Now close the position
    closed_pos = trader.tracker.close_position(
        position_id=position.position_id,
        exit_price=0.55,
        reason="take_profit",
    )
    
    # Emit close event
    trader._emit_trade_closed_event(
        position=closed_pos,
        reason="take_profit",
        exit_price=0.55,
        size=closed_pos.size,
        pnl=0.50,
        receipt=receipt,
    )
    
    # Verify emitted close event has the flat backfilled fields
    close_emissions = [p for e_type, p in emitted_events if e_type == "log_trade_close"]
    assert len(close_emissions) == 1
    close_payload = close_emissions[0]
    
    assert close_payload["true_probability"] == 0.65
    assert close_payload["fair_value"] == 0.65
    assert close_payload["ev"] == 0.15
    assert close_payload["ev_after_spread"] == 0.15
    assert close_payload["confidence"] == 0.80
    assert close_payload["signal_name"] == "PROBABILITY_EV_EDGE"
    assert close_payload["lifecycle_phase"] == "OPENING_SCAN"
    assert close_payload["seconds_remaining"] == 120
    assert close_payload["bankroll_tier_id"] == "T0_MICRO_SEED"
    assert close_payload["bankroll_family"] == "MICRO"
    assert close_payload["risk_mode"] == "NORMAL"
    assert close_payload["risk_budget"] == 5.0
    assert close_payload["current_exposure"] == 0.0
    assert close_payload["target_exposure"] == 5.0
    assert close_payload["notional_size"] == 5.0


def test_trader_orchestrates_position_tracker_persistence(mock_settings, tmp_path):
    mock_settings.quant_data_dir = str(tmp_path / "quant_data")
    trader = PolymarketTrader(settings=mock_settings)
    state_path = tmp_path / "position_tracker_state.json"

    trader._position_tracker_state_path = lambda: state_path  # type: ignore[method-assign]
    trader._position_tracker_persistence_enabled = lambda: True  # type: ignore[method-assign]

    position = trader._open_tracked_position(
        symbol="test-market-123",
        source="polymarket",
        side="BUY",
        entry_price=0.50,
        size=10.0,
        stop_loss=0.40,
        take_profit=0.55,
        order_id="order_222",
        metadata={"strategy": "test"},
    )

    assert state_path.exists()

    closed = trader._close_tracked_position(
        position_id=position.position_id,
        exit_price=0.55,
        reason="take_profit",
    )

    assert closed is not None
    saved = state_path.read_text(encoding="utf-8")
    assert position.position_id in saved


def test_trade_close_carries_size_sharp_fields(mock_settings, tmp_path):
    mock_settings.quant_data_dir = str(tmp_path / "quant_data")
    trader = PolymarketTrader(settings=mock_settings)
    emitted_events = []
    trader._emit_quant_event = lambda event_type, payload: emitted_events.append((event_type, payload))

    metadata = trader._build_trade_position_metadata(
        strategy="ENTER",
        signal_strategy="scalper",
        token_id="token_yes",
        outcome="YES",
        entry_ev=0.15,
        confidence=0.80,
        delta_regime="TREND",
        condition_id="cond_abc",
        epoch_start_ts=1782518400,
        market_slug="btc-100k",
        lifecycle_phase="OPENING_SCAN",
        ticker="BTC",
        true_probability=0.65,
        fair_value=0.65,
        risk_mode="NORMAL",
        current_exposure=0.0,
        target_exposure=5.0,
        notional_size=5.0,
        seconds_remaining=120,
        size_sharp_result={
            "size_sharp": 0.72,
            "size_sharp_bucket": "STRONG",
            "deployment_state": "OBSERVE_STRONG",
            "limiting_factor": "none",
            "confidence_grade": "A",
            "component_scores": {"signal_edge": 0.8},
            "penalties": {"execution": 0.0},
            "boosts": {"clean_edge": 0.03},
            "hard_caps": [],
            "missing_inputs": [],
            "schema_version": "size_sharp_v1",
        },
    )

    position = trader.tracker.open_position(
        symbol="test-market-123",
        source="polymarket",
        side="BUY",
        entry_price=0.50,
        size=10.0,
        stop_loss=0.40,
        take_profit=0.55,
        order_id="order_333",
        metadata=metadata,
    )
    closed_pos = trader.tracker.close_position(position.position_id, 0.55, reason="take_profit")

    trader._emit_trade_closed_event(
        position=closed_pos,
        reason="take_profit",
        exit_price=0.55,
        size=closed_pos.size,
        pnl=0.50,
        receipt=DummyOrderReceipt(order_id="order_333", status="filled", filled_size=10.0, remaining_size=0.0),
    )

    close_payload = [payload for event_type, payload in emitted_events if event_type == "log_trade_close"][0]
    assert close_payload["size_sharp_at_entry"] == 0.72
    assert close_payload["size_sharp_bucket"] == "STRONG"
    assert close_payload["size_sharp_deployment_state"] == "OBSERVE_STRONG"
    assert close_payload["size_sharp_limiting_factor"] == "none"
    assert close_payload["size_sharp_confidence_grade"] == "A"
    assert close_payload["size_sharp_component_scores"] == {"signal_edge": 0.8}
    assert close_payload["size_sharp_penalties"] == {"execution": 0.0}
    assert close_payload["size_sharp_boosts"] == {"clean_edge": 0.03}
    assert close_payload["size_sharp_hard_caps"] == []
    assert close_payload["size_sharp_missing_inputs"] == []
    assert close_payload["size_sharp_schema_version"] == "size_sharp_v1"
    assert close_payload["size_sharp_close_carry_status"] == "carried"
