from __future__ import annotations

from types import SimpleNamespace

from polymarket.client import BUY, OrderReceipt
from polymarket.trader import BankrollState, PolymarketTrader
from utils.risk_manager import RiskPlan


class _CollectingQuantLogger:
    def __init__(self) -> None:
        self.mode = "paper"
        self.schema_version = "1.0"
        self.events: list[tuple[str, dict]] = []

    def log_trade_open(self, payload: dict) -> bool:
        self.events.append(("trade_open", payload))
        return True


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        paper_trading=True,
        adaptive_entry_hard_block_seconds=45,
        entry_min_seconds_remaining=30,
        exit_agent_entry_cutoff_seconds=45,
        exit_agent_cancel_entries_seconds=35,
        exit_agent_force_exit_seconds=25,
    )


def _trader() -> PolymarketTrader:
    trader = PolymarketTrader.__new__(PolymarketTrader)
    trader.settings = _settings()
    trader.quant_events = _CollectingQuantLogger()
    trader.bankroll_state = BankrollState(
        starting_bankroll=100.0,
        current_cash_balance=100.0,
    )
    trader._market_token_meta = {
        "BTC": {
            "condition_id": "condition-btc",
            "market_id": "btc-market",
            "yes_token_id": "yes-token",
            "no_token_id": "no-token",
            "slug": "btc-up-down",
        }
    }
    trader._real_token_ids = {"BTC": ("yes-token", "no-token")}
    trader._market_first_seen_seconds_remaining = {}
    trader._market_readiness_timestamps = {}
    trader._last_bankroll_rank = None
    trader._last_bankroll_family = None
    trader._last_capital_score = None
    trader.last_quant_details = {}
    trader._observability_health_display_state = {}
    return trader


def _risk_plan() -> RiskPlan:
    return RiskPlan(
        account_balance=100.0,
        entry_price=0.42,
        stop_loss_price=0.30,
        take_profit_price=0.70,
        partial_tp_price=0.60,
        risk_amount=0.84,
        kelly_fraction=0.0,
        capped_fraction=0.01,
        position_size=2.0,
        notional_size=0.84,
        stop_loss_pct=0.08,
    )


def _receipt(token_id: str = "no-token") -> OrderReceipt:
    return OrderReceipt(
        order_id="paper-1",
        status="filled",
        token_id=token_id,
        side=BUY,
        price=0.42,
        size=2.0,
        filled_size=2.0,
    )


def _emit_open(
    trader: PolymarketTrader,
    *,
    outcome: str = "NO",
    token_id: str = "no-token",
    true_probability: float | None = None,
    ev_after_spread: float | None = None,
    confidence: float | None = None,
) -> dict:
    trader._emit_trade_opened_event(
        market_id="btc-market",
        ticker="BTC",
        token_id=token_id,
        outcome=outcome,
        receipt=_receipt(token_id),
        risk_plan=_risk_plan(),
        entry_price=0.42,
        strategy="quant_stack",
        seconds_remaining=180,
        epoch_start=1779072600,
        condition_id="condition-btc",
        true_probability=true_probability,
        ev_after_spread=ev_after_spread,
        confidence=confidence,
    )
    event_type, payload = trader.quant_events.events[-1]
    assert event_type == "trade_open"
    return payload


def test_trade_open_preserves_model_fields_from_decision_context() -> None:
    trader = _trader()
    trader.last_quant_details["BTC"] = {
        "market_id": "btc-market",
        "condition_id": "condition-btc",
        "token_id": "no-token",
        "outcome": "NO",
        "model_probability_yes": 0.37,
        "model_probability_no": 0.63,
        "fair_value_yes": 0.37,
        "fair_value_no": 0.63,
        "ev_after_spread": 0.21,
        "confidence": 0.88,
        "model_output_ready": True,
        "probability_model_output_visible": True,
        "model_not_run_reason": "",
    }

    payload = _emit_open(
        trader,
        outcome="NO",
        token_id="no-token",
        ev_after_spread=0.21,
        confidence=0.88,
    )

    assert payload["model_output_ready"] is True
    assert payload["probability_model_output_visible"] is True
    assert payload["model_not_run_reason"] == ""
    assert payload["true_probability"] == 0.63
    assert payload["fair_value"] == 0.63
    assert payload["ev_after_spread"] == 0.21
    assert payload["expected_value"] == 0.21
    assert payload["ev"] == 0.21
    assert payload["confidence"] == 0.88


def test_trade_open_missing_model_fields_fails_soft_to_default_visibility() -> None:
    trader = _trader()

    payload = _emit_open(trader, outcome="NO", token_id="no-token")

    assert payload.get("model_output_ready") is not True
    assert payload["probability_model_output_visible"] is False
    assert payload.get("true_probability") is None
    assert payload.get("fair_value") is None
    assert payload.get("model_not_run_reason")


def test_trade_open_preserves_confidence_when_model_context_is_visible() -> None:
    trader = _trader()
    trader.last_quant_details["BTC"] = {
        "model_probability_yes": 0.58,
        "model_probability_no": 0.42,
        "ev_after_spread": 0.09,
    }

    payload = _emit_open(
        trader,
        outcome="YES",
        token_id="yes-token",
        ev_after_spread=0.09,
        confidence=0.77,
    )

    assert payload["confidence"] == 0.77


def test_trade_open_selects_side_specific_probability() -> None:
    trader = _trader()
    trader.last_quant_details["BTC"] = {
        "model_probability_yes": 0.58,
        "model_probability_no": 0.42,
        "ev_after_spread": 0.09,
    }

    yes_payload = _emit_open(
        trader,
        outcome="YES",
        token_id="yes-token",
        ev_after_spread=0.09,
        confidence=0.77,
    )
    no_payload = _emit_open(
        trader,
        outcome="NO",
        token_id="no-token",
        ev_after_spread=0.09,
        confidence=0.77,
    )

    assert yes_payload["true_probability"] == 0.58
    assert no_payload["true_probability"] == 0.42


def test_trade_open_preserves_paper_trade_replay_key() -> None:
    trader = _trader()
    trader.last_quant_details["BTC"] = {
        "model_probability_yes": 0.58,
        "model_probability_no": 0.42,
        "ev_after_spread": 0.09,
    }

    payload = _emit_open(
        trader,
        outcome="NO",
        token_id="no-token",
        ev_after_spread=0.09,
        confidence=0.77,
    )

    assert payload["paper_trade_replay_key"] == "condition-btc|1779072600|BTC|NO|no-token"
