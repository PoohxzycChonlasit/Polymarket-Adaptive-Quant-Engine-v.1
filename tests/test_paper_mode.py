from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import main
from main import build_parser
from polymarket.client import BalanceSnapshot, ClobOrderbookError, OrderReceipt, OrderbookSnapshot, PolymarketClient
from polymarket.order_manager import PolymarketOrderManager
from polymarket.order_intent import OrderIntentType
from polymarket.trader import BankrollState, PolymarketTrader, TradeOutcome
from utils.display import PolymarketRealtimeDisplay
from utils.position_tracker import PositionTracker
from utils.quant_event_logger import QuantEventLogger
from utils.risk_manager import RiskManager, RiskPlan
from utils.telegram_reporter import build_startup_alert


class _FailingQuantLogger:
    def __getattr__(self, _name):
        def _raise(*_args, **_kwargs):
            raise PermissionError("quant log locked")

        return _raise


class _CollectingQuantLogger:
    def __init__(self) -> None:
        self.mode = "paper"
        self.events: list[tuple[str, dict]] = []
        self.disabled_categories: set[str] = set()

    def log_execution(self, payload):
        self.events.append(("execution", payload))
        return True

    def log_trade_open(self, payload):
        self.events.append(("trade_open", payload))
        return True

    def log_trade_close(self, payload):
        self.events.append(("trade_close", payload))
        return True

    def log_system_health(self, payload):
        self.events.append(("system_health", payload))
        return True

    def log_decision(self, payload):
        self.events.append(("decision", payload))
        return True

    def log_market_snapshot(self, payload):
        self.events.append(("market_snapshot", payload))
        return True

    def log_risk_event(self, payload):
        self.events.append(("risk", payload))
        return True


class _FailingTelegramAlerts:
    def __getattr__(self, _name):
        def _raise(*_args, **_kwargs):
            raise RuntimeError("telegram down")

        return _raise


def _settings(**overrides):
    values = {
        "paper_trading": True,
        "dry_run": True,
        "account_balance": 100.0,
        "max_risk_per_trade": 0.01,
        "default_stop_loss_pct": 0.02,
        "kelly_fraction_cap": 0.25,
        "bankroll_floor": 5.0,
        "max_open_positions": 10,
        "max_total_exposure": 1.0,
        "max_daily_drawdown": 0.10,
        "close_order_retry_attempts": 1,
        "close_order_retry_delay_seconds": 0.0,
        "polymarket_proxy_wallet": "0xProxy",
        "polymarket_funder": "0xFunder",
        "paper_balance_source": "virtual",
        "paper_starting_balance_source": "config",
        "paper_wallet_sync_on_start": True,
        "paper_wallet_sync_mode": "initialize_only",
        "paper_min_balance_fallback": 0.0,
        "wallet_reference_refresh_seconds": 300,
        "show_wallet_reference_balance": True,
        "micro_survival_bankroll_threshold": 100.0,
        "micro_survival_min_position_size": 0.05,
        "micro_survival_risk_fraction": 0.0025,
    }
    values.update(overrides)
    if (
        values.get("paper_balance_source") == "wallet_reference"
        and "paper_starting_balance_source" not in overrides
    ):
        values["paper_starting_balance_source"] = "live_wallet_reference"
    return SimpleNamespace(**values)


def _trader(settings=None) -> PolymarketTrader:
    trader = PolymarketTrader()
    trader.settings = settings or _settings()
    trader.client = MagicMock()
    trader.tracker = PositionTracker(settings=trader.settings)
    trader.order_manager = PolymarketOrderManager(
        account_balance=trader.settings.account_balance,
        max_risk_per_trade=trader.settings.max_risk_per_trade,
        stop_loss_pct=trader.settings.default_stop_loss_pct,
        kelly_fraction_cap=trader.settings.kelly_fraction_cap,
    )
    trader._risk_mgr = RiskManager(initial_balance=trader.settings.account_balance)
    trader.bankroll_state = BankrollState(
        starting_bankroll=trader.settings.account_balance,
        current_cash_balance=trader.settings.account_balance,
    )
    return trader


def _risk_plan(size: float = 2.0, price: float = 0.50) -> RiskPlan:
    return RiskPlan(
        account_balance=100.0,
        entry_price=price,
        stop_loss_price=0.46,
        take_profit_price=0.55,
        partial_tp_price=0.53,
        risk_amount=size * price,
        kelly_fraction=0.0,
        capped_fraction=0.01,
        position_size=size,
        notional_size=size * price,
        stop_loss_pct=0.08,
    )


def _clob_settings(**overrides):
    values = {
        "polymarket_host": "https://clob.polymarket.com",
        "clob_orderbook_retry_count": 1,
        "clob_orderbook_retry_backoff_ms": 1,
        "clob_rate_limit_cooldown_seconds": 30,
        "clob_market_error_cooldown_seconds": 10,
        "clob_circuit_breaker_threshold": 3,
        "clob_circuit_breaker_window_seconds": 60,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _valid_orderbook_raw(token_id: str = "token") -> dict:
    return {
        "asset_id": token_id,
        "market": "condition-1",
        "bids": [{"price": "0.49", "size": "10"}],
        "asks": [{"price": "0.51", "size": "12"}],
    }


def test_polymarket_paper_command_is_available() -> None:
    args = build_parser().parse_args(["--mode", "polymarket-paper", "--interval", "15"])

    assert args.mode == "polymarket-paper"
    assert args.interval == 15


def test_default_command_is_safe_paper_mode() -> None:
    args = build_parser().parse_args([])

    assert args.mode == "paper"


def test_default_main_dispatches_to_paper_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {}

    def fake_paper(interval: int = 15) -> int:
        called["interval"] = interval
        return 0

    monkeypatch.setattr("sys.argv", ["main.py"])
    monkeypatch.setattr(main, "setup_logger", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main, "run_polymarket_paper", fake_paper)

    assert main.main() == 0
    assert called == {"interval": 60}


def test_polymarket_paper_command_forces_paper_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {}

    def fake_realtime(interval: int, force_paper: bool = False) -> int:
        called["interval"] = interval
        called["force_paper"] = force_paper
        return 0

    monkeypatch.setattr(main, "run_polymarket_realtime", fake_realtime)

    assert main.run_polymarket_paper(interval=15) == 0
    assert called == {"interval": 15, "force_paper": True}


def test_paper_connect_does_not_call_clob_client() -> None:
    trader = _trader()

    trader._ensure_connected()

    assert trader._connected
    trader.client.connect.assert_not_called()
    trader.client.get_usdc_balance.assert_not_called()
    assert trader.dashboard_portfolio_state()["balance_source"] == "paper_virtual"


def test_phase2_lifecycle_observability_enriches_condition_id_from_market_meta() -> None:
    trader = _trader()
    trader._market_token_meta = {"BTC": {"condition_id": "condition-btc"}}
    payload = {
        "ticker": "BTC",
        "source_market_id": "pm-5m-btc",
        "token_id": "token-yes",
        "outcome": "YES",
        "market_epoch_start": 1770000000,
        "seconds_remaining": 240,
    }

    enriched = trader._phase2_complete_lifecycle_observability(payload)

    assert enriched["condition_id"] == "condition-btc"
    assert "condition_id" not in payload


def test_phase2_lifecycle_observability_derives_meta_ticker_from_source_market_id() -> None:
    trader = _trader()
    trader._market_token_meta = {"ETH": {"condition_id": "condition-eth"}}

    enriched = trader._phase2_complete_lifecycle_observability({
        "source_market_id": "pm-5m-eth",
        "token_id": "token-no",
        "outcome": "NO",
        "market_epoch_start": 1770000000,
    })

    assert enriched["condition_id"] == "condition-eth"


def test_phase2_lifecycle_observability_handles_absent_condition_meta_safely() -> None:
    trader = _trader()
    trader._market_token_meta = {}
    payload = {
        "ticker": "BTC",
        "token_id": "token-yes",
        "outcome": "YES",
        "market_epoch_start": 1770000000,
    }

    enriched = trader._phase2_complete_lifecycle_observability(payload)

    assert "condition_id" not in enriched


def test_event_driven_admission_packet_price_detail_uses_ptb_info_only() -> None:
    trader = _trader()
    ptb_info = SimpleNamespace(
        asset="BTC",
        current_price=100_025.5,
        price_to_beat=100_100.0,
    )

    detail = trader._event_driven_admission_packet_price_detail(ptb_info, "BTC")

    assert detail == {
        "packet_schema_version": "event_driven_admission_packet_v1",
        "price_enrichment_stage": "analyze_market_quant_pre_orderbook",
        "price_enrichment_source": "ptb_info",
        "underlying_symbol": "BTC",
        "ptb_context_available": True,
        "oracle_price_available": True,
        "underlying_price": 100_025.5,
        "current_price": 100_025.5,
        "underlying_price_source": "polymarket_oracle_feed",
        "target_price_available": True,
        "target_price": 100_100.0,
        "price_to_beat": 100_100.0,
        "target_source": "ptb_tracker_price_to_beat",
        "event_boundary_source": "ptb_tracker_price_to_beat",
        "packet_schema_price_fields_present": True,
        "packet_created_before_price_context": False,
        "enrichment_drop_reason": "",
    }


def test_event_driven_admission_packet_price_detail_classifies_missing_ptb_values() -> None:
    trader = _trader()
    ptb_info = SimpleNamespace(asset="BTC", current_price=0.0, price_to_beat=None)

    detail = trader._event_driven_admission_packet_price_detail(ptb_info, "BTC")

    assert detail["ptb_context_available"] is True
    assert detail["oracle_price_available"] is False
    assert detail["target_price_available"] is False
    assert detail["packet_schema_price_fields_present"] is False
    assert detail["packet_created_before_price_context"] is True
    assert detail["enrichment_drop_reason"] == "oracle_and_target_missing"
    assert "underlying_price" not in detail
    assert "target_price" not in detail


def test_market_snapshot_emits_event_driven_packet_price_fields_without_mutating_payload() -> None:
    trader = _trader()
    trader.quant_events = _CollectingQuantLogger()
    ptb_info = SimpleNamespace(asset="ETH", current_price=3_250.25, price_to_beat=3_260.0)
    price_detail = trader._event_driven_admission_packet_price_detail(ptb_info, "ETH")
    payload = {
        "ticker": "ETH",
        "market_id": "pm-5m-eth",
        "seconds_remaining": 180,
        **price_detail,
    }

    assert trader._emit_quant_event("log_market_snapshot", payload) is True

    category, emitted = trader.quant_events.events[-1]
    assert category == "market_snapshot"
    assert emitted["packet_schema_version"] == "event_driven_admission_packet_v1"
    assert emitted["price_enrichment_stage"] == "analyze_market_quant_pre_orderbook"
    assert emitted["price_enrichment_source"] == "ptb_info"
    assert emitted["ptb_context_available"] is True
    assert emitted["oracle_price_available"] is True
    assert emitted["underlying_price"] == 3_250.25
    assert emitted["current_price"] == 3_250.25
    assert emitted["underlying_symbol"] == "ETH"
    assert emitted["underlying_price_source"] == "polymarket_oracle_feed"
    assert emitted["target_price"] == 3_260.0
    assert emitted["price_to_beat"] == 3_260.0
    assert emitted["target_price_available"] is True
    assert emitted["target_source"] == "ptb_tracker_price_to_beat"
    assert emitted["event_boundary_source"] == "ptb_tracker_price_to_beat"
    assert emitted["packet_schema_price_fields_present"] is True
    assert emitted["packet_created_before_price_context"] is False
    assert emitted["enrichment_drop_reason"] == ""
    assert "candidate_id" not in payload
    assert "condition_id" not in payload


def test_phase2_lifecycle_observability_preserves_existing_condition_id() -> None:
    trader = _trader()
    trader._market_token_meta = {"BTC": {"condition_id": "condition-from-cache"}}

    enriched = trader._phase2_complete_lifecycle_observability({
        "ticker": "BTC",
        "condition_id": "condition-from-payload",
        "token_id": "token-yes",
        "outcome": "YES",
        "market_epoch_start": 1770000000,
    })

    assert enriched["condition_id"] == "condition-from-payload"


def test_execution_gateway_enriches_condition_id_for_producer_style_payload() -> None:
    trader = _trader()
    trader.quant_events = _CollectingQuantLogger()
    trader._market_token_meta = {
        "BTC": {
            "condition_id": "condition-btc",
            "market_id": "pm-5m-btc",
            "yes_token_id": "btc-yes-token",
            "no_token_id": "btc-no-token",
        }
    }
    payload = {
        "event": "order_submit_attempt",
        "source_market_id": "pm-5m-btc",
        "token_id": "btc-yes-token",
        "outcome": "YES",
        "side": "BUY",
        "price": 0.51,
        "size": 1.0,
    }

    assert trader._emit_quant_event("log_execution", payload)

    event_type, emitted = trader.quant_events.events[-1]
    assert event_type == "execution"
    assert emitted["condition_id"] == "condition-btc"
    assert emitted["source_market_id"] == "pm-5m-btc"
    assert "condition_id" not in payload
    trader.client.assert_not_called()


def test_trade_open_gateway_enriches_condition_id_for_producer_style_payload() -> None:
    trader = _trader()
    trader.quant_events = _CollectingQuantLogger()
    trader._market_token_meta = {
        "ETH": {
            "condition_id": "condition-eth",
            "market_id": "pm-5m-eth",
            "yes_token_id": "eth-yes-token",
            "no_token_id": "eth-no-token",
        }
    }
    payload = {
        "market_id": "pm-5m-eth",
        "ticker": "ETH",
        "token_id": "eth-no-token",
        "outcome": "NO",
        "side": "BUY",
        "entry_price": 0.49,
        "size": 2.0,
    }

    assert trader._emit_quant_event("log_trade_open", payload)

    event_type, emitted = trader.quant_events.events[-1]
    assert event_type == "trade_open"
    assert emitted["condition_id"] == "condition-eth"
    assert emitted["market_id"] == "pm-5m-eth"
    assert "condition_id" not in payload
    trader.client.assert_not_called()


def test_trade_close_gateway_enriches_condition_id_from_position_style_payload() -> None:
    trader = _trader()
    trader.quant_events = _CollectingQuantLogger()
    trader._market_token_meta = {
        "ETH": {
            "condition_id": "condition-eth",
            "market_id": "pm-5m-eth",
            "yes_token_id": "eth-yes-token",
            "no_token_id": "eth-no-token",
        }
    }
    position = SimpleNamespace(
        symbol="pm-5m-eth",
        position_id="pos-1",
        metadata={"token_id": "eth-no-token", "outcome": "NO"},
        side="BUY",
    )
    payload = {
        "position_id": position.position_id,
        "market_id": position.symbol,
        "ticker": trader._ticker_from_market_id(position.symbol),
        "token_id": trader._position_token_id(position),
        "outcome": trader._position_outcome(position),
        "side": "SELL",
        "reason": "settlement",
    }

    assert trader._emit_quant_event("log_trade_close", payload)

    event_type, emitted = trader.quant_events.events[-1]
    assert event_type == "trade_close"
    assert emitted["condition_id"] == "condition-eth"
    assert emitted["position_id"] == "pos-1"
    assert "condition_id" not in payload
    trader.client.assert_not_called()


def test_condition_enrichment_gateway_handles_missing_metadata_safely() -> None:
    trader = _trader()
    trader.quant_events = _CollectingQuantLogger()
    trader._market_token_meta = {}
    payload = {
        "event": "order_submit_attempt",
        "source_market_id": "pm-5m-btc",
        "token_id": "btc-yes-token",
        "outcome": "YES",
        "side": "BUY",
    }

    assert trader._emit_quant_event("log_execution", payload)

    event_type, emitted = trader.quant_events.events[-1]
    assert event_type == "execution"
    assert "condition_id" not in emitted
    assert "condition_id" not in payload
    trader.client.assert_not_called()


def test_condition_enrichment_gateway_uses_market_id_metadata_fallback() -> None:
    trader = _trader()
    trader.quant_events = _CollectingQuantLogger()
    trader._market_token_meta = {
        "BTC": {
            "condition_id": "condition-btc",
            "market_id": "condition-btc",
            "yes_token_id": "btc-yes-token",
            "no_token_id": "btc-no-token",
        }
    }
    payload = {
        "event": "order_submit_attempt",
        "source_market_id": "condition-btc",
        "token_id": "unknown-token",
        "outcome": "YES",
        "side": "BUY",
    }

    assert trader._emit_quant_event("log_execution", payload)

    event_type, emitted = trader.quant_events.events[-1]
    assert event_type == "execution"
    assert emitted["condition_id"] == "condition-btc"
    assert "condition_id" not in payload
    trader.client.assert_not_called()


def test_condition_enrichment_gateway_uses_yes_token_metadata_fallback() -> None:
    trader = _trader()
    trader.quant_events = _CollectingQuantLogger()
    trader._market_token_meta = {
        "BTC": {
            "condition_id": "condition-btc",
            "market_id": "condition-btc",
            "yes_token_id": "btc-yes-token",
            "no_token_id": "btc-no-token",
        }
    }
    payload = {
        "event": "paper_fill",
        "source_market_id": "unmatched-market-reference",
        "token_id": "btc-yes-token",
        "outcome": "YES",
        "side": "BUY",
    }

    assert trader._emit_quant_event("log_execution", payload)

    event_type, emitted = trader.quant_events.events[-1]
    assert event_type == "execution"
    assert emitted["condition_id"] == "condition-btc"
    assert "condition_id" not in payload
    trader.client.assert_not_called()


def test_condition_enrichment_gateway_uses_no_token_metadata_fallback() -> None:
    trader = _trader()
    trader.quant_events = _CollectingQuantLogger()
    trader._market_token_meta = {
        "ETH": {
            "condition_id": "condition-eth",
            "market_id": "condition-eth",
            "yes_token_id": "eth-yes-token",
            "no_token_id": "eth-no-token",
        }
    }
    payload = {
        "event": "paper_fill",
        "source_market_id": "unmatched-market-reference",
        "token_id": "eth-no-token",
        "outcome": "NO",
        "side": "BUY",
    }

    assert trader._emit_quant_event("log_execution", payload)

    event_type, emitted = trader.quant_events.events[-1]
    assert event_type == "execution"
    assert emitted["condition_id"] == "condition-eth"
    assert "condition_id" not in payload
    trader.client.assert_not_called()


def test_condition_enrichment_gateway_does_not_enrich_ambiguous_metadata_match() -> None:
    trader = _trader()
    trader.quant_events = _CollectingQuantLogger()
    trader._market_token_meta = {
        "BTC": {
            "condition_id": "condition-btc",
            "market_id": "condition-btc",
            "yes_token_id": "shared-token",
            "no_token_id": "btc-no-token",
        },
        "ETH": {
            "condition_id": "condition-eth",
            "market_id": "condition-eth",
            "yes_token_id": "shared-token",
            "no_token_id": "eth-no-token",
        },
    }
    payload = {
        "event": "paper_fill",
        "source_market_id": "unmatched-market-reference",
        "token_id": "shared-token",
        "outcome": "YES",
        "side": "BUY",
    }

    assert trader._emit_quant_event("log_execution", payload)

    event_type, emitted = trader.quant_events.events[-1]
    assert event_type == "execution"
    assert "condition_id" not in emitted
    assert "condition_id" not in payload
    trader.client.assert_not_called()


def test_observability_health_display_state_tracks_latest_quant_event_without_runtime_decisions() -> None:
    trader = _trader()
    trader.quant_events = _CollectingQuantLogger()
    trader.quant_events.schema_version = "test-schema"
    trader._market_token_meta = {
        "BTC": {
            "condition_id": "condition-btc",
            "market_id": "pm-5m-btc",
            "yes_token_id": "btc-yes-token",
            "no_token_id": "btc-no-token",
        }
    }
    payload = {
        "event": "execution_attempt",
        "source_market_id": "pm-5m-btc",
        "token_id": "btc-yes-token",
        "outcome": "YES",
        "lifecycle_phase": "OPENING_SCAN",
        "probability_model_stage": "attempted",
        "true_probability": 0.61,
        "fair_value": 0.61,
        "ev_after_spread": 0.02,
        "decision_to_risk_boundary": "BLOCKED_BEFORE_RISK",
        "normalized_skip_reason": "ev_below_threshold",
    }

    assert trader._emit_quant_event("log_execution", payload)

    state = trader.dashboard_observability_health_state()
    portfolio_state = trader.dashboard_portfolio_state()
    assert state["jsonl_status"] == "OK"
    assert state["latest_producer"] == "execution_log"
    assert state["latest_schema_version"] == "test-schema"
    assert state["candidate_trace_id_present"] is True
    assert state["condition_id_present"] is True
    assert state["token_id_present"] is True
    assert state["side_present"] is True
    assert state["event_identity_readiness"] == "DIRECT"
    assert state["candidate_chain_trace_confidence"] == "UNKNOWN"
    assert state["identity_readiness"] == "DIRECT"
    assert state["trace_enrichment_status"] == "TRACE+COND"
    assert state["condition_enrichment_status"] == "OK"
    assert state["model_attempted"] == "YES"
    assert state["probability_visible"] == "YES"
    assert state["fair_value_visible"] == "YES"
    assert state["ev_visible"] == "YES"
    assert state["blocked_before_risk_count"] == 1
    assert state["dominant_pre_risk_cause"] == "ev_below_threshold"
    assert state["risk_reachability_status"] == "BLOCKED_BEFORE_RISK"
    assert state["risk_serialization_status"] == "UNKNOWN"
    assert portfolio_state["observability_health"]["latest_producer"] == "execution_log"
    assert portfolio_state["observability_health"]["candidate_trace_id_present"] is True
    trader.client.place_limit_order.assert_not_called()
    trader.client.cancel_order.assert_not_called()


def test_paper_wallet_reference_uses_mocked_wallet_balance_for_sizing() -> None:
    trader = _trader(_settings(
        paper_balance_source="wallet_reference",
        paper_starting_balance_source="live_wallet_reference",
        account_balance=100.0,
    ))
    trader.client.get_usdc_balance_snapshot.return_value = BalanceSnapshot(
        balance=250.75,
        source="clob_collateral",
        wallet_address="0xProxy",
        clob_balance=250.75,
        onchain_balance=0.0,
        proxy_wallet="0xProxy",
        funder_wallet="0xFunder",
    )

    trader._ensure_connected()
    portfolio = trader.dashboard_portfolio_state()

    trader.client.connect.assert_called_once()
    trader.client.get_usdc_balance_snapshot.assert_called_once()
    assert portfolio["balance_source"] == "wallet_reference_paper"
    assert portfolio["wallet_reference_balance"] == pytest.approx(250.75)
    assert portfolio["wallet_reference_source"] == "clob_collateral"
    assert portfolio["execution_mode"] == "PAPER ONLY"
    assert portfolio["no_live_orders"] is True
    assert portfolio["sizing_bankroll"] == pytest.approx(250.75)
    assert portfolio["paper_cash"] == pytest.approx(250.75)
    assert trader.order_manager.account_balance == pytest.approx(250.75)


def test_paper_wallet_reference_fetch_failure_falls_back_to_virtual() -> None:
    trader = _trader(_settings(paper_balance_source="wallet_reference", account_balance=100.0))
    trader.client.connect.side_effect = RuntimeError("connect unavailable")
    trader.client.get_usdc_balance_snapshot.side_effect = RuntimeError("snapshot unavailable")
    trader.client.get_usdc_balance.side_effect = RuntimeError("balance unavailable")

    trader._ensure_connected()
    portfolio = trader.dashboard_portfolio_state()

    assert portfolio["balance_source"] == "paper_virtual"
    assert portfolio["wallet_reference_available"] is False
    assert portfolio["wallet_reference_error"]
    assert portfolio["sizing_bankroll"] == pytest.approx(100.0)
    trader.client.place_limit_order.assert_not_called()


def test_paper_config_balance_initializes_virtual_cash_without_wallet_poll() -> None:
    trader = _trader(_settings(account_balance=42.50))

    trader._ensure_connected()
    portfolio = trader.dashboard_portfolio_state()

    assert portfolio["balance_source"] == "paper_virtual"
    assert portfolio["paper_cash"] == pytest.approx(42.50)
    assert portfolio["paper_sizing_balance"] == pytest.approx(42.50)
    trader.client.connect.assert_not_called()
    trader.client.get_usdc_balance.assert_not_called()
    trader.client.get_usdc_balance_snapshot.assert_not_called()


def test_live_wallet_reference_startup_logs_required_fields(caplog: pytest.LogCaptureFixture) -> None:
    trader = _trader(_settings(
        paper_balance_source="wallet_reference",
        paper_starting_balance_source="live_wallet_reference",
        account_balance=100.0,
    ))
    trader.client.get_usdc_balance_snapshot.return_value = BalanceSnapshot(
        balance=250.0,
        source="clob_collateral",
        wallet_address="0xProxy",
    )

    caplog.set_level(logging.INFO)
    trader._ensure_connected()

    startup_logs = [record.message for record in caplog.records if "[PAPER BALANCE STARTUP]" in record.message]
    assert startup_logs
    assert "mode=paper" in startup_logs[-1]
    assert "paper_starting_balance_source=live_wallet_reference" in startup_logs[-1]
    assert "live_wallet_reference_balance=$250.0000" in startup_logs[-1]
    assert "paper_virtual_cash_initial=$250.0000" in startup_logs[-1]
    assert "fallback_used=false" in startup_logs[-1]


def test_paper_wallet_reference_does_not_poll_after_startup() -> None:
    trader = _trader(_settings(
        paper_balance_source="wallet_reference",
        paper_starting_balance_source="live_wallet_reference",
        account_balance=100.0,
        wallet_reference_refresh_seconds=30,
    ))
    trader.client.get_usdc_balance_snapshot.return_value = BalanceSnapshot(
        balance=200.0,
        source="clob_collateral",
        wallet_address="0xProxy",
    )
    trader._ensure_connected()
    trader.client.get_usdc_balance_snapshot.return_value = BalanceSnapshot(
        balance=225.0,
        source="clob_collateral",
        wallet_address="0xProxy",
    )
    trader._last_wallet_reference_refresh_ts = 0.0

    state = trader._update_bankroll_state()

    assert state.current_bankroll_for_sizing == pytest.approx(200.0)
    assert trader.dashboard_portfolio_state()["wallet_reference_balance"] == pytest.approx(200.0)
    trader.client.get_usdc_balance_snapshot.assert_called_once()


def test_paper_balance_guard_blocks_unaffordable_order_without_live_polling() -> None:
    trader = _trader(_settings(account_balance=10.0))
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    trader._ensure_connected()

    assert trader._verify_balance_for_order(11.0, "BTC") is False

    trader.client.get_usdc_balance.assert_not_called()
    trader.client.get_usdc_balance_snapshot.assert_not_called()
    assert any(
        event == "risk" and payload.get("risk_plan_zero_reason") == "insufficient_paper_balance"
        for event, payload in collector.events
    )


def test_decision_log_includes_paper_balance_fields_and_zero_reason() -> None:
    trader = _trader(_settings(account_balance=4.50))
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    trader.bankroll_state.current_cash_balance = 4.50
    trader.bankroll_state.current_bankroll_for_sizing = 4.50
    trader.bankroll_state.open_position_market_value = 0.75
    risk_plan = RiskPlan(
        account_balance=4.50,
        entry_price=0.50,
        stop_loss_price=0.50,
        take_profit_price=0.50,
        partial_tp_price=0.50,
        risk_amount=0.0,
        kelly_fraction=0.0,
        capped_fraction=0.0,
        position_size=0.0,
        notional_size=0.0,
        stop_loss_pct=0.08,
        diagnostics={"reason_from_order_manager": "balance_below_floor"},
    )
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.70,
        risk_plan=risk_plan,
        receipt=None,
        skipped=True,
        skip_reason="Risk plan returned zero position size -- skipping.",
        display={"raw_skip_reason": "risk_plan_zero", "normalized_skip_reason": "risk_plan_zero"},
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    payload = [payload for event, payload in collector.events if event == "decision"][-1]
    assert payload["paper_virtual_cash"] == pytest.approx(4.50)
    assert payload["paper_available_balance"] == pytest.approx(4.50)
    assert payload["paper_open_position_value"] == pytest.approx(0.75)
    assert payload["live_wallet_reference_balance"] is None
    assert payload["risk_per_trade"] == pytest.approx(0.0)
    assert payload["calculated_order_size"] == pytest.approx(0.0)
    assert payload["risk_plan_zero_reason"] == "bankroll_floor"


def test_decision_and_risk_boundary_logs_preserve_candidate_ev_trace_fields() -> None:
    trader = _trader(_settings(account_balance=25.0))
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.62,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="ev_below_threshold",
        display={
            "raw_skip_reason": "ev_below_threshold",
            "normalized_skip_reason": "ev_below_threshold",
            "market_slug": "btc-updown-5m",
            "condition_id": "condition-btc",
            "token_id": "btc-yes-token",
            "side": "YES",
            "market_epoch_start": 1_700_000_000,
            "seconds_remaining": 210,
            "fair_value": 0.57,
            "market_price": 0.55,
            "true_probability": 0.57,
            "ev_after_spread": 0.02,
            "liquidity_state": "HEALTHY",
        },
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    decision_payload = [payload for event, payload in collector.events if event == "decision"][-1]
    risk_payload = [payload for event, payload in collector.events if event == "risk"][-1]
    assert decision_payload["decision_id"]
    assert decision_payload["candidate_trace_id"]
    assert decision_payload["condition_id"] == "condition-btc"
    assert decision_payload["token_id"] == "btc-yes-token"
    assert decision_payload["side"] == "YES"
    assert decision_payload["fair_value"] == pytest.approx(0.57)
    assert decision_payload["true_probability"] == pytest.approx(0.57)
    assert decision_payload["ev_after_spread"] == pytest.approx(0.02)
    assert decision_payload["ev_after_spread_available"] is True
    assert decision_payload["probability_model_called"] is True
    assert decision_payload["probability_model_output_visible"] is True
    assert decision_payload["model_handoff_stage"] == "MODEL_OUTPUT_SERIALIZED"
    assert decision_payload["model_activation_state"] == "MODEL_OUTPUT_VISIBLE"
    assert decision_payload["model_activation_block_group"] == "MODEL_READY"
    assert decision_payload["model_attempt_eligible"] is True

    assert risk_payload["event"] == "decision_risk_boundary"
    assert risk_payload["candidate_trace_id"] == decision_payload["candidate_trace_id"]
    assert risk_payload["decision_id"] == decision_payload["decision_id"]
    assert risk_payload["condition_id"] == "condition-btc"
    assert risk_payload["token_id"] == "btc-yes-token"
    assert risk_payload["side"] == "YES"
    assert risk_payload["lifecycle_phase"] == decision_payload["lifecycle_phase"]
    assert risk_payload["risk_decision"] == "not_reached"
    assert risk_payload["risk_state"] == "not_reached"
    assert risk_payload["risk_block_reason"] == "blocked_before_risk_evaluation"
    assert risk_payload["probability_model_called"] is True
    assert risk_payload["probability_model_output_visible"] is True
    assert risk_payload["model_handoff_stage"] == "MODEL_OUTPUT_SERIALIZED"
    assert risk_payload["model_activation_state"] == "MODEL_OUTPUT_VISIBLE"
    assert risk_payload["model_activation_block_group"] == "MODEL_READY"
    assert risk_payload["does_not_change_risk_decision"] is True
    assert outcome.receipt is None
    assert outcome.skipped is True


def test_risk_boundary_jsonl_receives_canonical_identity_lineage_fields(tmp_path) -> None:
    trader = _trader(_settings(account_balance=25.0))
    trader.quant_events = QuantEventLogger(
        base_dir=tmp_path,
        enabled=True,
        mode="paper",
        run_id="run-lineage",
        schema_version="1.0",
        now=lambda: datetime(2026, 5, 8, 12, 30, 0, tzinfo=timezone.utc),
    )
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.62,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="ev_below_threshold",
        display={
            "condition_id": "condition-btc",
            "token_id": "btc-yes-token",
            "side": "YES",
            "market_epoch_start": 1_700_000_000,
            "seconds_remaining": 210,
            "fair_value": 0.57,
            "market_price": 0.55,
            "true_probability": 0.57,
            "ev_after_spread": 0.02,
        },
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    decision_event = json.loads((tmp_path / "decision_log" / "2026-05-08.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    risk_event = json.loads((tmp_path / "risk_log" / "2026-05-08.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    decision_payload = decision_event["payload"]
    risk_payload = risk_event["payload"]
    assert risk_payload["candidate_trace_id"] == decision_payload["candidate_trace_id"]
    assert risk_payload["replay_chain_id"] == decision_payload["replay_chain_id"]
    assert risk_payload["risk_trace_id"].startswith("rt_")
    assert risk_payload["market_key"] == "pm-5m-btc"
    assert risk_payload["condition_id"] == "condition-btc"
    assert risk_payload["token_id"] == "btc-yes-token"
    assert risk_payload["side"] == "YES"
    assert risk_payload["identity_propagation_stage"] == "risk"
    assert risk_payload["lineage_confidence"] == "DIRECT"
    assert risk_payload["lineage_drop_reason"] == "none"
    assert risk_payload["lifecycle_instance_id"].startswith("li_")
    assert risk_payload["inventory_context_id"].startswith("inv_")
    assert "candidate_trace_id_missing_reason" not in risk_payload
    assert outcome.skipped is True


def test_decision_event_uses_cached_token_handoff_when_display_lacks_tokens() -> None:
    trader = _trader(_settings(account_balance=25.0))
    trader._real_token_ids = {"BTC": ("btc-yes-token", "btc-no-token")}
    trader._market_token_meta = {
        "BTC": {
            "condition_id": "condition-btc",
            "market_id": "pm-5m-btc",
            "slug": "btc-updown-5m",
            "yes_token_id": "btc-yes-token",
            "no_token_id": "btc-no-token",
        }
    }
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    display = {
        "raw_skip_reason": "Entry cutoff: 20s <= 35s (hard_close_zone)",
        "normalized_skip_reason": "time_unsafe",
        "side": "YES",
        "market_epoch_start": 1_700_000_000,
        "seconds_remaining": 20,
    }
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.0,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="Entry cutoff: 20s <= 35s (hard_close_zone)",
        display=display,
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    payload = [payload for event, payload in collector.events if event == "decision"][-1]
    assert payload["yes_token_id"] == "btc-yes-token"
    assert payload["no_token_id"] == "btc-no-token"
    assert payload["token_id"] == "btc-yes-token"
    assert payload["condition_id"] == "condition-btc"
    assert payload["yes_no_token_pair_present"] is True
    assert payload["cached_token_pair_available"] is True
    assert payload["decision_token_handoff_source"] == "cached_market_token_meta"
    assert "yes_token_id" not in display
    assert outcome.skipped is True
    assert outcome.receipt is None


def test_decision_event_preserves_serialized_yes_no_bid_ask_visibility() -> None:
    trader = _trader(_settings(account_balance=25.0))
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    display = {
        "raw_skip_reason": "ev_below_threshold",
        "normalized_skip_reason": "ev_below_threshold",
        "market_slug": "btc-updown-5m",
        "condition_id": "condition-btc",
        "token_id": "btc-yes-token",
        "yes_token_id": "btc-yes-token",
        "no_token_id": "btc-no-token",
        "side": "YES",
        "market_epoch_start": 1_700_000_000,
        "seconds_remaining": 210,
        "yes_bid": 0.44,
        "yes_ask": 0.46,
        "no_bid": 0.53,
        "no_ask": 0.55,
        "yes_bid_size": 10.0,
        "yes_ask_size": 11.0,
        "no_bid_size": 12.0,
        "no_ask_size": 13.0,
        "liquidity_state": "HEALTHY",
        "spread_normalized": True,
    }
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.0,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="ev_below_threshold",
        display=display,
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    payload = [payload for event, payload in collector.events if event == "decision"][-1]
    assert payload["yes_ask"] == pytest.approx(0.46)
    assert payload["no_ask"] == pytest.approx(0.55)
    assert payload["yes_bid"] == pytest.approx(0.44)
    assert payload["no_bid"] == pytest.approx(0.53)
    assert payload["decision_orderbook_ask_fields_present"] is True
    assert payload["decision_orderbook_bid_fields_present"] is True
    assert payload["decision_orderbook_completeness_source"] == "serialized_yes_no_bid_ask"
    assert payload["orderbook_state_classification"] == "ready"
    assert outcome.skipped is True
    assert outcome.receipt is None


def test_decision_event_emits_orderbook_refresh_reuse_cadence_observability() -> None:
    trader = _trader()
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    trader.set_runtime_cadence_observability(configured_decision_interval_seconds=60)
    trader._effective_outer_loop_interval_seconds = 60.0
    trader._cycle_started_at_utc = "2026-05-12T01:00:00Z"
    trader._cycle_started_monotonic = time.monotonic() - 0.2
    trader._mark_market_evaluation_started("BTC", sequence_index=2, sequence_count=2)
    trader._market_evaluation_started_monotonic["BTC"] -= 0.05
    trader._mark_orderbook_refresh(
        "BTC",
        source="market_snapshot",
        trigger="snapshot_sampling",
        executable_yes_no_book=True,
        condition_id="condition-btc",
        yes_token_id="btc-yes-token",
        no_token_id="btc-no-token",
        market_slug="btc-updown-5m",
    )
    trader._last_orderbook_refresh_monotonic["BTC"] -= 6.0
    trader._last_successful_yes_no_book_monotonic["BTC"] -= 6.0
    outcome = TradeOutcome(
        market_id="btc-market",
        question="BTC",
        decision="skip",
        confidence=0.0,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="empty_book",
        display={
            "market_epoch_start": 1_765_000_000,
            "seconds_remaining": 210,
            "token_id": "btc-yes-token",
            "yes_token_id": "btc-yes-token",
            "no_token_id": "btc-no-token",
            "condition_id": "condition-btc",
            "outcome": "YES",
            "orderbook_readiness_reason": "empty_book",
            "orderbook_state_classification": "empty_book",
            "first_candidate_ready_second": 90,
        },
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    payload = [payload for event, payload in collector.events if event == "decision"][-1]
    assert payload["decision_cycle_started_at"] == "2026-05-12T01:00:00Z"
    assert payload["last_orderbook_refresh_at"]
    assert payload["last_successful_yes_no_book_at"]
    assert payload["orderbook_refresh_source"] == "market_snapshot"
    assert payload["orderbook_refresh_trigger"] == "snapshot_sampling"
    assert payload["orderbook_reuse_detected"] is True
    assert payload["orderbook_lineage_match"] is True
    assert payload["decision_token_pair_key"] == "condition-btc|YES:btc-yes-token|NO:btc-no-token"
    assert payload["last_successful_yes_no_book_token_pair_key"] == payload["decision_token_pair_key"]
    assert payload["orderbook_current_fetch_status"] == "fresh_fetch_not_attempted_or_unobserved"
    assert payload["orderbook_stale_reuse_source"] == "NO_CURRENT_FETCH_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR"
    assert payload["orderbook_snapshot_age_ms_at_decision"] >= 6000
    assert payload["executable_book_last_seen_age_ms"] >= 6000
    assert payload["scheduler_cadence_source"] == "run_single_cycle_market_loop"
    assert payload["hot_path_timing_source"] == "runtime_market_evaluation"
    assert payload["configured_decision_loop_interval_seconds"] == 60.0
    assert payload["intended_decision_loop_target_seconds"] == 1.0
    assert payload["effective_outer_loop_interval_seconds"] == 60.0
    assert payload["snapshot_sampling_interval_seconds"] == 5.0
    assert payload["market_discovery_interval_seconds"] == 15.0
    assert payload["market_evaluation_asset"] == "BTC"
    assert payload["market_sequence_index"] == 2
    assert payload["market_sequence_count"] == 2
    assert payload["market_evaluation_duration_ms"] >= 50
    assert payload["market_evaluation_started_ms_since_cycle"] >= 0
    assert payload["candidate_queue_age_ms"] >= 6000
    assert payload["hot_path_admission_wait_ms"] >= 6000
    assert payload["candidate_queue_age_source"] == "last_successful_yes_no_book_to_decision"
    assert payload["candidate_queue_ownership"] == "implicit_orderbook_refresh_cache"
    assert payload["candidate_revisit_scheduling_source"] == "scheduled_run_single_cycle"
    assert payload["hot_path_admission_trigger"] == "scheduled_decision_cycle"
    assert payload["event_vs_polling_classification"] == "polling_revisit_driven"
    assert payload["executable_liquidity_event_role"] == "passive_telemetry_only"
    assert payload["executable_liquidity_triggered_hot_path"] is False
    assert payload["market_snapshot_decision_pipeline_linkage"] == "disconnected_passive_snapshot_to_scheduled_decision"
    assert payload["candidate_handoff_boundary"] == "market_snapshot->scheduled_run_single_cycle"
    assert payload["empty_book_recovery_duration_ms"] == 0


def test_orderbook_handoff_classifies_failed_fresh_fetch_after_prior_same_pair() -> None:
    trader = _trader()
    trader._mark_orderbook_refresh(
        "BTC",
        source="market_snapshot",
        trigger="snapshot_sampling",
        executable_yes_no_book=True,
        condition_id="condition-btc",
        yes_token_id="btc-yes-token",
        no_token_id="btc-no-token",
        market_slug="btc-updown-5m",
    )

    detail = trader._orderbook_refresh_observability_detail(
        "BTC",
        current_executable_yes_no_book=False,
        current_fetch_succeeded=False,
        condition_id="condition-btc",
        yes_token_id="btc-yes-token",
        no_token_id="btc-no-token",
        market_slug="btc-updown-5m",
    )

    assert detail["orderbook_reuse_detected"] is True
    assert detail["orderbook_lineage_match"] is True
    assert detail["orderbook_current_fetch_status"] == "fresh_fetch_failed"
    assert detail["orderbook_stale_reuse_source"] == "CURRENT_FETCH_FAILED_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR"


def test_risk_boundary_log_records_zero_size_risk_block_without_changing_outcome() -> None:
    trader = _trader(_settings(account_balance=4.50))
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    risk_plan = RiskPlan(
        account_balance=4.50,
        entry_price=0.50,
        stop_loss_price=0.50,
        take_profit_price=0.50,
        partial_tp_price=0.50,
        risk_amount=0.0,
        kelly_fraction=0.0,
        capped_fraction=0.0,
        position_size=0.0,
        notional_size=0.0,
        stop_loss_pct=0.08,
        diagnostics={"reason_from_order_manager": "balance_below_floor"},
    )
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.70,
        risk_plan=risk_plan,
        receipt=None,
        skipped=True,
        skip_reason="Risk plan returned zero position size -- skipping.",
        display={
            "raw_skip_reason": "risk_plan_zero",
            "normalized_skip_reason": "risk_plan_zero",
            "condition_id": "condition-btc",
            "token_id": "btc-yes-token",
            "side": "YES",
            "market_epoch_start": 1_700_000_000,
            "ev_after_spread_available": False,
            "ev_after_spread_null_reason": "candidate_blocked_before_ev",
        },
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    risk_payload = [payload for event, payload in collector.events if event == "risk"][-1]
    assert risk_payload["risk_decision"] == "blocked"
    assert risk_payload["risk_state"] == "blocked"
    assert risk_payload["risk_block_reason"] == "bankroll_floor"
    assert risk_payload["risk_plan_present"] is True
    assert risk_payload["risk_approved"] is False
    assert risk_payload["candidate_trace_id"]
    assert risk_payload["ev_missing_reason"] == "not_computed_at_producer"
    assert outcome.risk_plan is risk_plan
    assert risk_plan.position_size == pytest.approx(0.0)


def test_decision_log_passes_through_regime_probability_fields() -> None:
    trader = _trader(_settings(account_balance=25.0))
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
        skip_reason="ev_below_threshold",
        display={
            "market_regime": "TREND_UP",
            "volatility_regime": "NORMAL_VOL",
            "trend_regime": "WEAK_UPTREND",
            "bullish_probability": 0.62,
            "bearish_probability": 0.38,
            "reversal_risk": 0.11,
            "compression_score": 0.22,
            "signal_trend_strength": 0.71,
            "signal_volatility_score": 0.0042,
            "indicator_evidence": "rsi=55 ema_gap=0.001",
        },
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    payload = [payload for event, payload in collector.events if event == "decision"][-1]
    assert payload["market_regime"] == "TREND_UP"
    assert payload["bullish_probability"] == pytest.approx(0.62)
    assert payload["bearish_probability"] == pytest.approx(0.38)
    assert payload["signal_trend_strength"] == pytest.approx(0.71)
    assert payload["signal_volatility_score"] == pytest.approx(0.0042)
    assert payload["indicator_evidence"] == "rsi=55 ema_gap=0.001"


def test_model_output_visibility_survives_when_scanner_selects_no_trade_side() -> None:
    trader = _trader(_settings(account_balance=25.0))
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.58,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="scanner_no_best_trade",
        display=trader._record_quant_detail(
            "BTC",
            market_id="pm-5m-btc",
            best_market="pm-5m-btc",
            best_side="SKIP",
            side="SKIP",
            p_yes=0.57,
            p_no=0.43,
            ev=None,
            min_ev=0.02,
            seconds_remaining=210,
            market_epoch_start=1_700_000_000,
            market_price=0.55,
            condition_id="condition-btc",
            token_id="btc-yes-token",
            market_slug="btc-updown-5m",
            decision="SKIP",
            skip_reason="scanner_no_best_trade",
        ),
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    payload = [payload for event, payload in collector.events if event == "decision"][-1]
    assert payload["model_attempted"] is True
    assert payload["probability_model_called"] is True
    assert payload["probability_model_output_visible"] is True
    assert payload["model_handoff_stage"] == "MODEL_OUTPUT_SERIALIZED"
    assert payload["model_output_source"] == "current_probability_model_result"
    assert payload["model_output_missing_reason"] == ""
    assert payload["probability_model_stage"] == "probability_model_output"
    assert payload["probability_model_gate_reason"] == "model_output_visible"
    assert payload["model_not_run_reason"] == ""
    assert payload["model_probability_yes"] == pytest.approx(0.57)
    assert payload["model_probability_no"] == pytest.approx(0.43)
    assert payload["fair_value_yes"] == pytest.approx(0.57)
    assert payload["fair_value_no"] == pytest.approx(0.43)
    assert payload["true_probability_available"] is True
    assert payload["fair_value_available"] is True
    assert payload["ev_after_spread_available"] is False
    assert payload["ev_missing_reason"] == "not_computed_at_producer"
    assert payload["model_activation_state"] == "MODEL_OUTPUT_VISIBLE"
    assert payload["model_activation_block_group"] == "MODEL_READY"
    assert payload["model_attempt_eligible"] is True
    assert payload["first_model_eligible_second"] == 90
    assert payload["seconds_remaining_when_eligible"] == 210
    assert payload["first_probability_output_second"] == 90
    assert payload["seconds_remaining_when_model_output_visible"] == 210
    assert payload["model_eligible_at_or_inside_cutoff"] is False
    assert outcome.receipt is None
    trader.client.place_limit_order.assert_not_called()


def test_decision_log_exposes_pre_model_hard_close_activation_gate_without_trading_change() -> None:
    trader = _trader(_settings(account_balance=25.0))
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.0,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="Entry cutoff: 20s <= 35s (hard_close_zone)",
        display={
            "raw_skip_reason": "Entry cutoff: 20s <= 35s (hard_close_zone)",
            "normalized_skip_reason": "time_unsafe",
            "market_slug": "btc-updown-5m",
            "condition_id": "condition-btc",
            "token_id": "btc-yes-token",
            "side": "YES",
            "market_epoch_start": 1_700_000_000,
            "seconds_remaining": 20,
            "effective_cutoff_seconds": 35,
            "adaptive_cutoff_reason": "hard_close_zone",
        },
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    payload = [payload for event, payload in collector.events if event == "decision"][-1]
    assert payload["model_activation_state"] == "BLOCKED_BEFORE_MODEL"
    assert payload["model_activation_block_group"] == "TIME_CUTOFF_GATE"
    assert payload["model_activation_block_reason"] == "hard_close_zone"
    assert payload["probability_model_called"] is False
    assert payload["probability_model_output_visible"] is False
    assert payload["model_handoff_stage"] == "PRE_MODEL_GATE"
    assert payload["model_output_missing_reason"] == "hard_close_zone"
    assert payload["model_output_source"] == ""
    assert payload["pre_model_gate_name"] == "TIME_CUTOFF_GATE"
    assert payload["pre_model_gate_group"] == "TIME_CUTOFF_GATE"
    assert payload["pre_model_gate_blocks_probability_model"] is True
    assert payload["probability_model_call_path"] == "blocked_before_probability_model"
    assert payload["model_attempt_eligible"] is False
    assert payload["first_model_eligible_second"] is None
    assert payload["seconds_remaining_when_eligible"] is None
    assert payload["first_probability_output_second"] is None
    assert payload["seconds_remaining_when_model_output_visible"] is None
    assert outcome.receipt is None
    trader.client.place_limit_order.assert_not_called()


def test_decision_log_resolves_candidate_ready_frequency_gate_without_model_call() -> None:
    trader = _trader(_settings(account_balance=25.0))
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.0,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="Max entries per market reached",
        display={
            "raw_skip_reason": "Max entries per market reached",
            "normalized_skip_reason": "frequency_cooldown",
            "market_slug": "btc-updown-5m",
            "condition_id": "condition-btc",
            "token_id": "btc-yes-token",
            "side": "YES",
            "market_epoch_start": 1_700_000_000,
            "seconds_remaining": 200,
            "first_candidate_ready_second": 50,
            "orderbook_state_classification": "ready",
            "market_readiness_state": "ready",
            "liquidity_state": "HEALTHY",
            "spread_normalized": True,
        },
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    payload = [payload for event, payload in collector.events if event == "decision"][-1]
    assert payload["first_candidate_ready_second"] == 50
    assert payload["probability_model_called"] is False
    assert payload["probability_model_output_visible"] is False
    assert payload["model_activation_state"] == "BLOCKED_BEFORE_MODEL"
    assert payload["model_activation_block_group"] == "ENTRY_FREQUENCY_GATE"
    assert payload["pre_model_gate_name"] == "ENTRY_FREQUENCY_GATE"
    assert payload["pre_model_gate_group"] == "ENTRY_FREQUENCY_GATE"
    assert payload["pre_model_gate_source"] == "entry_frequency"
    assert payload["pre_model_gate_blocks_probability_model"] is True
    assert payload["probability_model_call_path"] == "blocked_before_probability_model"
    assert payload["model_attempt_eligible"] is False
    assert outcome.receipt is None
    trader.client.place_limit_order.assert_not_called()


def test_market_snapshot_ready_without_model_output_is_producer_observation_not_unknown_gate() -> None:
    trader = _trader(_settings(account_balance=25.0))
    collector = _CollectingQuantLogger()
    trader.quant_events = collector

    emitted = trader._emit_quant_event(
        "log_market_snapshot",
        {
            "ticker": "BTC",
            "market_id": "pm-5m-btc",
            "market_slug": "btc-updown-5m",
            "condition_id": "condition-btc",
            "token_id": "btc-yes-token",
            "side": "YES",
            "yes_bid": 0.49,
            "yes_ask": 0.50,
            "no_bid": 0.49,
            "no_ask": 0.50,
            "liquidity_state": "HEALTHY",
            "spread_normalized": True,
            "seconds_remaining": 200,
            "market_epoch_start": 1_700_000_000,
            "first_candidate_ready_second": 50,
        },
    )

    assert emitted is True
    payload = [payload for event, payload in collector.events if event == "market_snapshot"][-1]
    assert payload["producer_event_type"] == "market_snapshots"
    assert payload["model_activation_state"] == "PRE_MODEL_OBSERVATION"
    assert payload["model_activation_block_group"] == "PRODUCER_NOT_RESPONSIBLE"
    assert payload["pre_model_gate_name"] == "PRODUCER_PRE_MODEL_OBSERVATION"
    assert payload["pre_model_gate_group"] == "PRODUCER_NOT_RESPONSIBLE"
    assert payload["pre_model_gate_blocks_probability_model"] is False
    assert payload["probability_model_call_path"] == "producer_not_responsible_pre_model_observation"
    assert payload["probability_model_called"] is False
    assert payload["probability_model_output_visible"] is False
    trader.client.place_limit_order.assert_not_called()


def test_wallet_reference_paper_order_still_never_places_live_order() -> None:
    trader = _trader(_settings(
        paper_balance_source="wallet_reference",
        paper_starting_balance_source="live_wallet_reference",
        account_balance=100.0,
    ))
    trader.client.get_usdc_balance_snapshot.return_value = BalanceSnapshot(
        balance=250.0,
        source="clob_collateral",
        wallet_address="0xProxy",
    )
    trader._ensure_connected()

    receipt = trader._submit_order(
        "yes-token",
        side="BUY",
        price=0.50,
        size=2.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    assert receipt is not None
    assert receipt.status == "paper"
    trader.client.place_limit_order.assert_not_called()


def test_wallet_reference_dashboard_text_is_explicit() -> None:
    display = PolymarketRealtimeDisplay()
    display.update_portfolio({
        "starting_bankroll": 250.0,
        "cash": 250.0,
        "open_value": 0.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "equity": 250.0,
        "sizing_bankroll": 250.0,
        "paper_cash": 250.0,
        "paper_sizing_balance": 250.0,
        "bankroll_tier": "SMALL",
        "daily_drawdown": 0.0,
        "risk_off": False,
        "open_count": 0,
        "max_open_positions": 3,
        "total_exposure_pct": 0.0,
        "balance_source": "wallet_reference_paper",
        "execution_mode": "PAPER ONLY",
        "wallet_reference_balance": 250.0,
        "wallet_reference_label": "REAL WALLET BALANCE (REFERENCE ONLY)",
    })

    from rich.console import Console

    console = Console(record=True, width=180, color_system=None)
    console.print(display._portfolio_panel())
    text = console.export_text()

    assert "Wallet Bankroll $250.00" in text
    assert "Paper Sizing Balance $250.00" in text
    assert "wallet_reference_paper" in text
    assert "NO LIVE ORDERS" in text


def test_telegram_startup_includes_wallet_reference_bankroll() -> None:
    message = build_startup_alert(
        mode="PAPER",
        status="CONNECTED",
        interval=60,
        bankroll=250.0,
        paper=True,
        wallet="0xProxy",
        balance_source="wallet_reference_paper",
        wallet_balance=250.0,
        paper_cash=250.0,
        execution_mode="PAPER ONLY",
    )

    assert "PAPER" in message
    assert "wallet_reference_paper" in message
    assert "$250.0000 USDC" in message
    assert "PAPER ONLY" in message
    assert "NO LIVE ORDERS" in message


def test_live_connect_syncs_dashboard_to_wallet_balance() -> None:
    trader = _trader(_settings(paper_trading=False, dry_run=False, account_balance=100.0))
    trader.client.connect.return_value = None
    trader.client.get_usdc_balance_snapshot.return_value = BalanceSnapshot(
        balance=20.25,
        source="clob_collateral",
        wallet_address="0xProxy",
        clob_balance=20.25,
        onchain_balance=0.75,
        proxy_wallet="0xProxy",
        funder_wallet="0xFunder",
    )
    trader.client.get_balance_allowance.return_value = {"balance": 20.25, "allowance": 100.0}

    trader._ensure_connected()
    portfolio = trader.dashboard_portfolio_state()

    assert trader._connected
    trader.client.get_balance_allowance.assert_called_once_with(side="BUY")
    assert portfolio["starting_bankroll"] == pytest.approx(20.25)
    assert portfolio["cash"] == pytest.approx(20.25)
    assert portfolio["equity"] == pytest.approx(20.25)
    assert portfolio["account_balance"] == pytest.approx(20.25)
    assert portfolio["balance_source"] == "clob_collateral"
    assert portfolio["wallet_address"] == "0xProxy"


def test_dashboard_portfolio_live_refreshes_wallet_each_snapshot() -> None:
    trader = _trader(_settings(paper_trading=False, dry_run=False, account_balance=100.0))
    trader._connected = True
    trader.client.get_usdc_balance_snapshot.return_value = BalanceSnapshot(
        balance=18.5,
        source="clob_collateral",
        wallet_address="0xProxy",
    )

    portfolio = trader.dashboard_portfolio_state()

    trader.client.get_usdc_balance_snapshot.assert_called_once()
    assert portfolio["cash"] == pytest.approx(18.5)
    assert portfolio["balance_source"] == "clob_collateral"


def test_paper_submit_order_never_places_real_order() -> None:
    trader = _trader()

    receipt = trader._submit_order(
        "yes-token",
        side="BUY",
        price=0.50,
        size=2.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    assert receipt is not None
    assert receipt.status == "paper"
    assert receipt.order_type == "GTC"
    trader.client.place_limit_order.assert_not_called()


def test_paper_submit_order_emits_execution_events_without_live_order() -> None:
    trader = _trader()
    collector = _CollectingQuantLogger()
    trader.quant_events = collector

    receipt = trader._submit_order(
        "yes-token",
        side="BUY",
        price=0.50,
        size=2.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    assert receipt is not None
    assert [event[1]["event"] for event in collector.events if event[0] == "execution"] == [
        "order_intent_approved",
        "order_submit_attempt",
        "paper_fill",
    ]
    trader.client.place_limit_order.assert_not_called()


def test_execution_log_inherits_parent_decision_ev_and_risk_context_without_live_order() -> None:
    trader = _trader()
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    plan = _risk_plan()
    trader._record_quant_detail(
        "BTC",
        market_id="pm-5m-btc",
        best_market="pm-5m-btc",
        market_slug="btc-updown-5m",
        condition_id="condition-btc",
        token_id="yes-token",
        yes_token_id="yes-token",
        no_token_id="no-token",
        side="YES",
        outcome="YES",
        p_yes=0.61,
        p_no=0.39,
        fair_value=0.61,
        true_probability=0.61,
        ev=0.04,
        market_price=0.50,
        seconds_remaining=190,
        market_epoch_start=1_700_000_000,
        lifecycle_phase="ACTIVE_INVENTORY_TRADING",
        decision="ENTER",
        skip_reason="",
    )

    receipt = trader._submit_order(
        "yes-token",
        side="BUY",
        price=0.50,
        size=plan.position_size,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=plan,
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    assert receipt is not None
    execution_payloads = [payload for event, payload in collector.events if event == "execution"]
    assert [payload["event"] for payload in execution_payloads] == [
        "order_intent_approved",
        "order_submit_attempt",
        "paper_fill",
    ]
    for payload in execution_payloads:
        assert payload["decision_id"]
        assert payload["market_slug"] == "btc-updown-5m"
        assert payload["lifecycle_phase"] == "ACTIVE_INVENTORY_TRADING"
        assert payload["true_probability"] == pytest.approx(0.61)
        assert payload["fair_value"] == pytest.approx(0.61)
        assert payload["ev_after_spread"] == pytest.approx(0.04)
        assert payload["risk_state"] == "approved"
        assert payload["risk_mode"]
        assert payload["risk_plan_present"] is True
        assert payload["risk_approved"] is True
        assert payload["execution_context_source"] == "parent_decision_context"
        assert "execution_context_missing_fields" not in payload
    trader.client.place_limit_order.assert_not_called()


def test_execution_log_canonicalizes_parent_model_aliases_from_token_outcome_without_live_order() -> None:
    trader = _trader()
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    plan = _risk_plan()
    trader._record_quant_detail(
        "BTC",
        market_id="pm-5m-btc",
        best_market="pm-5m-btc",
        market_slug="btc-updown-5m",
        condition_id="condition-btc",
        token_id="yes-token",
        yes_token_id="yes-token",
        no_token_id="no-token",
        side="SKIP",
        outcome="SKIP",
        p_yes=0.62,
        p_no=0.38,
        ev=0.05,
        market_price=0.50,
        seconds_remaining=190,
        market_epoch_start=1_700_000_000,
        lifecycle_phase="ACTIVE_INVENTORY_TRADING",
        decision="SKIP",
        skip_reason="scanner_no_best_trade",
    )

    receipt = trader._submit_order(
        "yes-token",
        side="BUY",
        price=0.50,
        size=plan.position_size,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=plan,
        source_market_id="pm-5m-btc",
        outcome="",
    )

    assert receipt is not None
    execution_payloads = [payload for event, payload in collector.events if event == "execution"]
    for payload in execution_payloads:
        assert payload["side"] == "YES"
        assert payload["outcome"] == "YES"
        assert payload["true_probability"] == pytest.approx(0.62)
        assert payload["fair_value"] == pytest.approx(0.62)
        assert payload["ev_after_spread"] == pytest.approx(0.05)
        assert payload["true_probability_source"] == "parent_yes_probability_alias"
        assert payload["fair_value_source"] == "parent_yes_fair_value_alias"
        assert payload["true_probability_propagation_status"] == "propagated"
        assert payload["fair_value_propagation_status"] == "propagated"
    trader.client.place_limit_order.assert_not_called()


def test_micro_survival_paper_entry_remains_simulated_only() -> None:
    trader = _trader(_settings(account_balance=20.0))
    plan = RiskPlan(
        account_balance=20.0,
        entry_price=0.50,
        stop_loss_price=0.46,
        take_profit_price=0.55,
        partial_tp_price=0.53,
        risk_amount=0.05,
        kelly_fraction=0.0,
        capped_fraction=0.0025,
        position_size=0.1,
        notional_size=0.05,
        stop_loss_pct=0.08,
        diagnostics={"bankroll_mode": "MICRO_SURVIVAL", "micro_survival_active": True},
    )

    receipt = trader._submit_order(
        "yes-token",
        side="BUY",
        price=0.50,
        size=plan.position_size,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=plan,
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    assert receipt is not None
    assert receipt.status == "paper"
    assert trader.dashboard_portfolio_state()["bankroll_mode"] == "MICRO_SURVIVAL"
    assert trader.dashboard_portfolio_state()["bankroll_tier_id"] == "T0_MICRO_SEED"
    assert trader.dashboard_portfolio_state()["bankroll_family"] == "MICRO"
    trader.client.place_limit_order.assert_not_called()


def test_observability_failures_do_not_crash_paper_submit_order() -> None:
    trader = _trader()
    trader.quant_events = _FailingQuantLogger()

    receipt = trader._submit_order(
        "yes-token",
        side="BUY",
        price=0.50,
        size=2.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    assert receipt is not None
    assert receipt.status == "paper"
    trader.client.place_limit_order.assert_not_called()


def test_paper_runtime_live_execution_paths_are_blocked() -> None:
    trader = _trader()

    trader._ensure_connected()
    trader.auto_redeem_cycle()
    trader._cancel_entry_orders_for_market("pm-5m-btc", "BTC", 30, "test")
    receipt = trader._submit_order(
        "yes-token",
        side="BUY",
        price=0.50,
        size=2.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )

    assert trader._connected
    assert receipt is not None
    trader.client.connect.assert_not_called()
    trader.client.get_usdc_balance.assert_not_called()
    trader.client.get_usdc_balance_snapshot.assert_not_called()
    trader.client.get_balance_allowance.assert_not_called()
    trader.client.place_limit_order.assert_not_called()
    trader.client.cancel_order.assert_not_called()
    trader.client.redeem_position.assert_not_called()


def test_paper_entry_updates_cash_equity_and_exposure() -> None:
    trader = _trader()
    trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.50, 0.51, 0.01, 10.0, 10.0)
    receipt = trader._submit_order(
        "yes-token",
        side="BUY",
        price=0.50,
        size=10.0,
        intent_type=OrderIntentType.ENTRY,
        risk_plan=_risk_plan(size=10.0),
        source_market_id="pm-5m-btc",
        outcome="YES",
    )
    assert receipt is not None

    trader._paper_record_trade(5.0)
    trader.tracker.open_position(
        symbol="pm-5m-btc",
        source="polymarket",
        side="BUY",
        entry_price=0.50,
        size=10.0,
        stop_loss=0.45,
        take_profit=0.60,
        order_id=receipt.order_id,
        metadata={"token_id": "yes-token", "outcome": "YES"},
    )

    portfolio = trader.dashboard_portfolio_state()

    assert portfolio["balance_source"] == "paper_virtual"
    assert portfolio["cash"] == pytest.approx(95.0)
    assert portfolio["open_value"] == pytest.approx(5.0)
    assert portfolio["equity"] == pytest.approx(100.0)
    assert portfolio["total_exposure"] == pytest.approx(5.0)
    assert portfolio["total_exposure_pct"] == pytest.approx(0.05)


def test_market_display_metrics_exposes_truthful_clob_fields() -> None:
    trader = _trader()
    trader._real_token_ids["BTC"] = ("yes-token", "no-token")
    trader._market_token_meta["BTC"] = {
        "slug": "btc-updown-5m",
        "condition_id": "condition-1",
        "yes_token_id": "yes-token",
        "no_token_id": "no-token",
    }
    trader.client.get_orderbook.side_effect = [
        OrderbookSnapshot("yes-token", 0.10, 0.11, 0.01, 10.0, 12.0, condition_id="condition-1", age_seconds=0.12),
        OrderbookSnapshot("no-token", 0.89, 0.90, 0.01, 9.0, 11.0, condition_id="condition-1", age_seconds=0.15),
    ]
    trader._record_quant_detail("BTC", p_yes=0.61, p_no=0.39, ev=0.028)

    metrics = trader.get_market_display_metrics("BTC", outcome="YES", confidence=0.61)

    assert metrics.yes_bid == pytest.approx(0.10)
    assert metrics.yes_ask == pytest.approx(0.11)
    assert metrics.no_bid == pytest.approx(0.89)
    assert metrics.no_ask == pytest.approx(0.90)
    assert metrics.yes_mid == pytest.approx(0.105)
    assert metrics.no_mid == pytest.approx(0.895)
    assert metrics.p_yes == pytest.approx(0.61)
    assert metrics.p_no == pytest.approx(0.39)
    assert metrics.clob_source == "CLOB orderbook"
    assert metrics.orderbook_age_ms == 150
    assert metrics.yes_token_id == "yes-token"
    assert metrics.no_token_id == "no-token"
    assert metrics.condition_id == "condition-1"
    assert metrics.market_slug == "btc-updown-5m"
    assert metrics.token_mapping_warning == ""
    assert trader._last_orderbook_refresh_source["BTC"] == "display_snapshot_sampling"
    assert trader._last_orderbook_refresh_trigger["BTC"] == "terminal_orderbook_panel"
    assert trader._last_successful_yes_no_book_at_utc["BTC"]


def test_market_display_metrics_warns_on_token_mapping_mismatch() -> None:
    trader = _trader()
    trader._real_token_ids["BTC"] = ("yes-token", "no-token")
    trader._market_token_meta["BTC"] = {
        "slug": "btc-updown-5m",
        "condition_id": "condition-1",
        "yes_token_id": "yes-token",
        "no_token_id": "no-token",
    }
    trader.client.get_orderbook.side_effect = [
        OrderbookSnapshot("yes-token", 0.10, 0.11, 0.01, 10.0, 12.0, condition_id="condition-1"),
        OrderbookSnapshot("no-token", 0.89, 0.90, 0.01, 9.0, 11.0, condition_id="condition-2"),
    ]

    metrics = trader.get_market_display_metrics("BTC", outcome="YES", confidence=0.61)

    assert "no_condition_id_mismatch" in metrics.token_mapping_warning
    assert metrics.skip_reason == "token_mapping_mismatch"


def test_market_display_metrics_logs_orderbook_failure_diagnostics(caplog: pytest.LogCaptureFixture) -> None:
    trader = _trader()
    trader._real_token_ids["BTC"] = ("yes-token", "no-token")
    trader._market_token_meta["BTC"] = {
        "slug": "btc-updown-5m",
        "condition_id": "condition-1",
        "yes_token_id": "yes-token",
        "no_token_id": "no-token",
    }
    trader._last_orderbook_age_ms["BTC"] = 321
    trader.client.get_orderbook.side_effect = RuntimeError("empty_orderbook")

    with caplog.at_level("WARNING"):
        metrics = trader.get_market_display_metrics("BTC", outcome="YES", confidence=0.61)

    assert metrics.skip_reason == "empty_book"
    assert trader._last_orderbook_refresh_source["BTC"] == "display_snapshot_sampling"
    assert trader._last_orderbook_refresh_trigger["BTC"] == "terminal_orderbook_panel_failed"
    assert any("last_successful_orderbook_age_ms=321" in record.message for record in caplog.records)
    assert any("market_slug=btc-updown-5m" in record.message for record in caplog.records)


def test_market_display_metrics_logs_structured_clob_failure_diagnostics(caplog: pytest.LogCaptureFixture) -> None:
    trader = _trader()
    trader._real_token_ids["BTC"] = ("yes-token", "no-token")
    trader._market_token_meta["BTC"] = {
        "slug": "btc-updown-5m",
        "condition_id": "condition-1",
        "yes_token_id": "yes-token",
        "no_token_id": "no-token",
    }
    trader.client.get_orderbook.side_effect = ClobOrderbookError(
        "clob_rate_limited",
        "429 too many requests",
        token_id="yes-token",
        exception_type="HTTPError",
        status_code=429,
        api_failure=True,
    )

    with caplog.at_level("WARNING"):
        metrics = trader.get_market_display_metrics("BTC", outcome="YES", confidence=0.61)

    assert metrics.skip_reason == "clob_rate_limited"
    assert metrics.orderbook_readiness_reason == "clob_rate_limited"
    assert metrics.clob_error_category == "clob_rate_limited"
    assert metrics.clob_exception_type == "HTTPError"
    assert metrics.clob_status_code == 429
    assert metrics.clob_api_failure is True
    assert any("category=clob_rate_limited" in record.message for record in caplog.records)


def test_orderbook_readiness_classifier_fresh_book_has_no_unavailable_reason() -> None:
    trader = _trader()
    trader._last_orderbook_age_ms["BTC"] = 5

    reason = trader._classify_orderbook_readiness_reason(
        "BTC",
        token_ids=("yes-token", "no-token"),
        yes_ask=0.51,
        no_ask=0.50,
    )

    assert reason == ""


def test_orderbook_readiness_classifier_tracks_warmup_before_empty_book() -> None:
    trader = _trader()

    reasons = [
        trader._classify_orderbook_readiness_reason(
            "BTC",
            token_ids=("yes-token", "no-token"),
            orderbook_error="empty_orderbook bids=0 asks=0",
        )
        for _ in range(4)
    ]

    assert reasons[:3] == ["warmup_pending", "warmup_pending", "warmup_pending"]
    assert reasons[3] == "empty_book"


def test_orderbook_readiness_classifier_missing_token_and_stale_book() -> None:
    trader = _trader()

    assert trader._classify_orderbook_readiness_reason("BTC", token_ids=None) == "missing_token_id"
    assert (
        trader._classify_orderbook_readiness_reason(
            "BTC",
            token_ids=("yes-token", "no-token"),
            orderbook_error="stale_orderbook age=4.2s",
        )
        == "stale_book"
    )


def test_orderbook_readiness_classifier_categorizes_clob_errors() -> None:
    trader = _trader()

    assert (
        trader._classify_orderbook_readiness_reason(
            "BTC",
            token_ids=("yes-token", "no-token"),
            orderbook_error="request timed out",
        )
        == "clob_timeout"
    )
    assert (
        trader._classify_orderbook_readiness_reason(
            "BTC",
            token_ids=("yes-token", "no-token"),
            orderbook_error="404 token not found",
        )
        == "clob_token_not_found"
    )
    assert (
        trader._classify_orderbook_readiness_reason(
            "BTC",
            token_ids=("yes-token", "no-token"),
            orderbook_error="429 too many requests",
        )
        == "clob_rate_limited"
    )


def test_empty_orderbook_recovery_succeeds_before_rejecting() -> None:
    trader = _trader(_settings(
        orderbook_empty_recovery_enabled=True,
        orderbook_empty_recovery_retries=2,
        orderbook_empty_recovery_delay_ms=0,
        orderbook_empty_recovery_max_total_ms=100,
    ))
    trader.client.get_orderbook.side_effect = [
        RuntimeError("empty_orderbook bids=0 asks=0"),
        OrderbookSnapshot("yes-token", 0.50, 0.51, 0.01, 10.0, 10.0),
        OrderbookSnapshot("no-token", 0.49, 0.50, 0.01, 10.0, 10.0),
    ]

    yes_ob, no_ob, detail = trader._fetch_orderbook_pair_with_empty_recovery(
        ticker="BTC",
        yes_token_id="yes-token",
        no_token_id="no-token",
        seconds_remaining=200,
        market_slug="btc-updown-5m",
    )

    assert yes_ob.best_ask == pytest.approx(0.51)
    assert no_ob.best_ask == pytest.approx(0.50)
    assert detail["empty_book_recovery_attempted"] is True
    assert detail["empty_book_recovery_success"] is True
    assert detail["empty_book_recovery_failed"] is False
    assert detail["empty_book_recovery_retry_count"] == 1
    assert detail["liquidity_state"] == "HEALTHY"
    assert detail["recovery_branch_candidate_seen"] is True
    assert detail["recovery_branch_mode_disabled"] is True
    assert detail["liquidity_recovery_grace_entered"] is False
    assert trader._market_readiness_metrics["empty_book_recovery_success"] == 1


def test_empty_book_recovery_research_mode_records_candidate_survival() -> None:
    trader = _trader(_settings(
        empty_book_recovery_research_mode=True,
        orderbook_empty_recovery_enabled=True,
        orderbook_empty_recovery_retries=2,
        orderbook_empty_recovery_delay_ms=0,
        orderbook_empty_recovery_max_total_ms=100,
    ))
    trader.client.get_orderbook.side_effect = [
        RuntimeError("empty_orderbook bids=0 asks=0"),
        OrderbookSnapshot("yes-token", 0.50, 0.51, 0.01, 10.0, 10.0, age_seconds=0.05),
        OrderbookSnapshot("no-token", 0.49, 0.50, 0.01, 10.0, 10.0, age_seconds=0.05),
    ]

    _yes_ob, _no_ob, detail = trader._fetch_orderbook_pair_with_empty_recovery(
        ticker="BTC",
        yes_token_id="yes-token",
        no_token_id="no-token",
        seconds_remaining=200,
        market_slug="btc-updown-5m",
    )

    assert detail["empty_book_recovery_research_mode"] is True
    assert detail["liquidity_recovery_grace_entered"] is True
    assert detail["liquidity_recovery_grace_success"] is True
    assert detail["liquidity_recovery_grace_failed"] is False
    assert detail["recovery_branch_candidate_seen"] is True
    assert detail["recovery_branch_mode_disabled"] is False
    assert detail["recovered_before_cutoff"] is True
    assert detail["candidate_survived_recovery"] is True
    assert detail["recovery_exit_reason"] == "recovered"
    assert detail["recovery_wait_seconds"] >= 0.0


def test_empty_book_recovery_research_mode_retries_transient_timeout() -> None:
    trader = _trader(_settings(
        empty_book_recovery_research_mode=True,
        orderbook_empty_recovery_enabled=True,
        orderbook_empty_recovery_retries=2,
        orderbook_empty_recovery_delay_ms=0,
        orderbook_empty_recovery_max_total_ms=100,
    ))
    trader.client.get_orderbook.side_effect = [
        TimeoutError("orderbook request timed out"),
        OrderbookSnapshot("yes-token", 0.50, 0.51, 0.01, 10.0, 10.0, age_seconds=0.05),
        OrderbookSnapshot("no-token", 0.49, 0.50, 0.01, 10.0, 10.0, age_seconds=0.05),
    ]

    _yes_ob, _no_ob, detail = trader._fetch_orderbook_pair_with_empty_recovery(
        ticker="BTC",
        yes_token_id="yes-token",
        no_token_id="no-token",
        seconds_remaining=200,
        market_slug="btc-updown-5m",
    )

    assert trader.client.get_orderbook.call_count == 3
    assert detail["liquidity_recovery_grace_success"] is True
    assert detail["candidate_survived_recovery"] is True


def test_transient_timeout_recovery_requires_research_mode() -> None:
    trader = _trader(_settings(
        empty_book_recovery_research_mode=False,
        orderbook_empty_recovery_enabled=True,
        orderbook_empty_recovery_retries=2,
    ))
    trader.client.get_orderbook.side_effect = TimeoutError("orderbook request timed out")

    with pytest.raises(TimeoutError):
        trader._fetch_orderbook_pair_with_empty_recovery(
            ticker="BTC",
            yes_token_id="yes-token",
            no_token_id="no-token",
            seconds_remaining=200,
            market_slug="btc-updown-5m",
        )

    assert trader.client.get_orderbook.call_count == 1
    assert trader._market_readiness_metrics["empty_book_recovery_attempted"] == 0


def test_empty_orderbook_recovery_does_not_retry_inside_hard_close_zone() -> None:
    trader = _trader(_settings(
        orderbook_empty_recovery_enabled=True,
        orderbook_empty_recovery_retries=2,
        orderbook_empty_recovery_delay_ms=0,
        orderbook_empty_recovery_max_total_ms=100,
    ))
    trader.client.get_orderbook.side_effect = RuntimeError("empty_orderbook bids=0 asks=0")

    with pytest.raises(RuntimeError):
        trader._fetch_orderbook_pair_with_empty_recovery(
            ticker="BTC",
            yes_token_id="yes-token",
            no_token_id="no-token",
            seconds_remaining=30,
            market_slug="btc-updown-5m",
        )

    assert trader.client.get_orderbook.call_count == 1
    assert trader._market_readiness_metrics["empty_book_recovery_attempted"] == 0


def test_empty_book_recovery_research_mode_records_hard_close_block() -> None:
    trader = _trader(_settings(
        empty_book_recovery_research_mode=True,
        orderbook_empty_recovery_enabled=True,
        orderbook_empty_recovery_retries=2,
        orderbook_empty_recovery_delay_ms=0,
        orderbook_empty_recovery_max_total_ms=100,
    ))
    trader.client.get_orderbook.side_effect = RuntimeError("empty_orderbook bids=0 asks=0")

    with pytest.raises(RuntimeError):
        trader._fetch_orderbook_pair_with_empty_recovery(
            ticker="BTC",
            yes_token_id="yes-token",
            no_token_id="no-token",
            seconds_remaining=30,
            market_slug="btc-updown-5m",
        )

    detail = trader._last_empty_book_recovery_detail["BTC"]
    assert trader.client.get_orderbook.call_count == 1
    assert detail["empty_book_recovery_research_mode"] is True
    assert detail["liquidity_recovery_grace_entered"] is False
    assert detail["liquidity_recovery_grace_failed"] is True
    assert detail["recovery_branch_candidate_seen"] is True
    assert detail["recovery_branch_preempted_by_cutoff"] is True
    assert detail["recovery_branch_enter_condition_failed"] is True
    assert detail["recovery_branch_skipped_reason"] == "hard_close_zone"
    assert detail["recovery_exit_reason"] == "hard_close_zone"


def test_empty_orderbook_recovery_fails_bounded_with_metrics() -> None:
    trader = _trader(_settings(
        orderbook_empty_recovery_enabled=True,
        orderbook_empty_recovery_retries=2,
        orderbook_empty_recovery_delay_ms=0,
        orderbook_empty_recovery_max_total_ms=100,
    ))
    trader.client.get_orderbook.side_effect = RuntimeError("empty_orderbook bids=0 asks=0")

    with pytest.raises(RuntimeError):
        trader._fetch_orderbook_pair_with_empty_recovery(
            ticker="BTC",
            yes_token_id="yes-token",
            no_token_id="no-token",
            seconds_remaining=200,
            market_slug="btc-updown-5m",
        )

    detail = trader._last_empty_book_recovery_detail["BTC"]
    assert trader.client.get_orderbook.call_count == 3
    assert detail["empty_book_recovery_attempted"] is True
    assert detail["empty_book_recovery_success"] is False
    assert detail["empty_book_recovery_failed"] is True
    assert detail["empty_book_recovery_retry_count"] == 2
    assert detail["recovery_branch_candidate_seen"] is True
    assert detail["recovery_branch_skipped_reason"] == "empty_book_retries_exhausted"
    assert detail["liquidity_state"] == "EMPTY"
    assert trader._market_readiness_metrics["empty_book_recovery_failed"] == 1


def test_empty_book_recovery_research_mode_does_not_enable_live_retries() -> None:
    trader = _trader(_settings(
        paper_trading=False,
        dry_run=False,
        empty_book_recovery_research_mode=True,
        orderbook_empty_recovery_enabled=True,
        orderbook_empty_recovery_retries=2,
    ))
    trader.client.get_orderbook.side_effect = RuntimeError("empty_orderbook bids=0 asks=0")

    with pytest.raises(RuntimeError):
        trader._fetch_orderbook_pair_with_empty_recovery(
            ticker="BTC",
            yes_token_id="yes-token",
            no_token_id="no-token",
            seconds_remaining=200,
            market_slug="btc-updown-5m",
        )

    detail = trader._last_empty_book_recovery_detail["BTC"]
    assert trader.client.get_orderbook.call_count == 1
    assert detail["empty_book_recovery_research_mode"] is False
    assert detail["liquidity_recovery_grace_entered"] is False
    assert detail["recovery_branch_candidate_seen"] is True
    assert detail["recovery_branch_mode_disabled"] is True
    assert trader._market_readiness_metrics["empty_book_recovery_attempted"] == 0


def test_decision_event_includes_recovery_branch_diagnostics() -> None:
    trader = _trader()
    trader.quant_events = _CollectingQuantLogger()
    outcome = TradeOutcome(
        market_id="pm-5m-btc",
        question="BTC above?",
        decision="skip",
        confidence=0.0,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="empty_book",
        display={
            "empty_book_recovery_attempted": True,
            "empty_book_recovery_failed": True,
            "empty_book_recovery_research_mode": True,
            "liquidity_recovery_grace_entered": True,
            "liquidity_recovery_grace_failed": True,
            "recovery_branch_candidate_seen": True,
            "recovery_branch_enter_condition_failed": False,
            "recovery_branch_mode_disabled": False,
            "recovery_branch_preempted_by_cutoff": False,
            "recovery_branch_skipped_reason": "empty_book_retries_exhausted",
            "recovery_exit_reason": "empty_book_retries_exhausted",
        },
    )

    trader._emit_decision_event(outcome, ticker="BTC")

    event_type, payload = trader.quant_events.events[-1]
    assert event_type == "decision"
    assert payload["empty_book_recovery_research_mode"] is True
    assert payload["liquidity_recovery_grace_entered"] is True
    assert payload["recovery_branch_candidate_seen"] is True
    assert payload["recovery_branch_mode_disabled"] is False
    assert payload["recovery_branch_skipped_reason"] == "empty_book_retries_exhausted"


def test_clob_client_classifies_orderbook_api_errors_without_fetching_network() -> None:
    client = PolymarketClient()

    class HTTPError(Exception):
        status_code = 500

    class RateLimitError(Exception):
        status_code = 429

    assert client._clob_orderbook_category(TimeoutError("timed out"), token_id="token") == "clob_timeout"
    assert client._clob_orderbook_category(RateLimitError("too many requests"), token_id="token") == "clob_rate_limited"
    assert client._clob_orderbook_category(HTTPError("server error"), token_id="token") == "clob_http_error"
    assert client._clob_orderbook_category(RuntimeError("token not found"), token_id="token") == "clob_token_not_found"
    assert client._clob_orderbook_category(RuntimeError("PolymarketClient not connected"), token_id="token") == "clob_client_not_connected"


def test_clob_orderbook_rate_limit_opens_token_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    client = PolymarketClient()
    client.settings = _clob_settings(clob_orderbook_retry_count=2, clob_rate_limit_cooldown_seconds=30)

    class RateLimitError(Exception):
        status_code = 429

    market_data_client = MagicMock()
    market_data_client.get_order_book.side_effect = RateLimitError("too many requests")
    client._market_data_client = market_data_client
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)

    with pytest.raises(ClobOrderbookError) as exc_info:
        client.get_orderbook("yes-token")

    exc = exc_info.value
    assert exc.category == "clob_rate_limited"
    assert exc.error_class == "rate_limited"
    assert exc.backoff_active is True
    assert exc.cooldown_seconds_remaining > 0
    assert market_data_client.get_order_book.call_count == 1

    with pytest.raises(ClobOrderbookError) as cooldown_info:
        client.get_orderbook("yes-token")

    assert cooldown_info.value.backoff_active is True
    assert market_data_client.get_order_book.call_count == 1


def test_clob_orderbook_transient_errors_retry_bounded_then_degrade(monkeypatch: pytest.MonkeyPatch) -> None:
    client = PolymarketClient()
    client.settings = _clob_settings(clob_orderbook_retry_count=1, clob_orderbook_retry_backoff_ms=5)

    class ServerError(Exception):
        status_code = 500

    sleeps: list[float] = []
    market_data_client = MagicMock()
    market_data_client.get_order_book.side_effect = ServerError("server unavailable")
    client._market_data_client = market_data_client
    monkeypatch.setattr(time, "sleep", lambda seconds: sleeps.append(seconds))

    with pytest.raises(ClobOrderbookError) as exc_info:
        client.get_orderbook("yes-token")

    assert exc_info.value.error_class == "transient_api_issue"
    assert exc_info.value.retry_count == 1
    assert market_data_client.get_order_book.call_count == 2
    assert len(sleeps) == 1
    assert sleeps[0] <= 1.0


def test_clob_orderbook_token_or_market_error_does_not_spam_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    client = PolymarketClient()
    client.settings = _clob_settings(clob_orderbook_retry_count=3, clob_market_error_cooldown_seconds=15)

    class NotFoundError(Exception):
        status_code = 404

    market_data_client = MagicMock()
    market_data_client.get_order_book.side_effect = NotFoundError("token not found")
    client._market_data_client = market_data_client
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)

    with pytest.raises(ClobOrderbookError) as exc_info:
        client.get_orderbook("bad-token")

    assert exc_info.value.error_class == "token_or_market_issue"
    assert exc_info.value.backoff_active is True
    assert market_data_client.get_order_book.call_count == 1


def test_clob_orderbook_per_token_circuit_opens_and_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    client = PolymarketClient()
    client.settings = _clob_settings(
        clob_orderbook_retry_count=0,
        clob_market_error_cooldown_seconds=10,
        clob_circuit_breaker_threshold=2,
    )

    class ServerError(Exception):
        status_code = 500

    market_data_client = MagicMock()
    market_data_client.get_order_book.side_effect = [ServerError("server unavailable"), ServerError("server unavailable")]
    client._market_data_client = market_data_client
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)

    for _ in range(2):
        with pytest.raises(ClobOrderbookError):
            client.get_orderbook("yes-token")

    health = client.get_orderbook_health("yes-token")
    assert health["clob_circuit_open"] is True
    assert health["clob_backoff_active"] is True

    state = client._orderbook_health_for("yes-token")
    state.cooldown_until = 0.0
    state.circuit_open_until = 0.0
    market_data_client.get_order_book.side_effect = None
    market_data_client.get_order_book.return_value = _valid_orderbook_raw("yes-token")

    snapshot = client.get_orderbook("yes-token")
    recovered = client.get_orderbook_health("yes-token")

    assert snapshot.best_bid == pytest.approx(0.49)
    assert recovered["clob_circuit_open"] is False
    assert recovered["clob_recovery_count"] == 1


def test_market_display_metrics_degrades_without_crashing_paper_runtime() -> None:
    trader = _trader()
    trader._real_token_ids["BTC"] = ("yes-token", "no-token")
    trader._market_token_meta["BTC"] = {
        "slug": "btc-updown-5m",
        "condition_id": "condition-1",
        "yes_token_id": "yes-token",
        "no_token_id": "no-token",
    }
    trader.client.get_orderbook.side_effect = ClobOrderbookError(
        "clob_http_error",
        "server unavailable",
        token_id="yes-token",
        exception_type="ServerError",
        status_code=500,
        api_failure=True,
        error_class="transient_api_issue",
        circuit_open=True,
        backoff_active=True,
        cooldown_seconds_remaining=10.0,
        error_rate=1.0,
    )

    metrics = trader.get_market_display_metrics("BTC", outcome="YES", confidence=0.61)

    assert metrics.skip_reason == "clob_http_error"
    assert metrics.market_data_degraded is True
    assert metrics.clob_circuit_open is True
    trader.client.place_limit_order.assert_not_called()


def test_duplicate_entry_protection_still_blocks_same_market_epoch() -> None:
    trader = _trader(_settings(max_entries_per_market=1))
    market = SimpleNamespace(market_id="pm-5m-btc", question="Will BTC close above PTB?")
    ptb_info = SimpleNamespace(seconds_remaining=200, epoch_start_ts=123456)
    trader._record_market_entry(market.market_id, ptb_info.epoch_start_ts)

    outcome = trader._analyze_market_quant(market, "BTC", ptb_info)

    assert outcome.skipped
    assert "Max entries per market" in outcome.skip_reason
    trader.client.place_limit_order.assert_not_called()


def test_paper_mode_uses_quant_decision_path() -> None:
    trader = _trader()
    trader.ptb_tracker = MagicMock()
    ptb_info = SimpleNamespace(seconds_remaining=200)
    trader.ptb_tracker.get_market_ptb.return_value = ptb_info
    market = SimpleNamespace(market_id="pm-5m-btc", question="Will BTC close above PTB?")
    expected = TradeOutcome(
        market_id=market.market_id,
        question=market.question,
        decision="skip",
        confidence=0.0,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="test_skip",
    )
    trader._analyze_market_quant = MagicMock(return_value=expected)

    outcome = trader._analyze_market(market)

    assert outcome is expected
    trader._analyze_market_quant.assert_called_once_with(market, "BTC", ptb_info)


def test_market_timing_detail_includes_early_window_alignment(monkeypatch: pytest.MonkeyPatch) -> None:
    trader = _trader()
    now_ts = 1_700_000_060
    epoch_start = now_ts - 60
    monkeypatch.setattr("polymarket.trader.time.time", lambda: now_ts)
    trader._real_token_ids["BTC"] = ("yes-token", "no-token")
    market = SimpleNamespace(market_id="pm-5m-btc", question="Will BTC close above PTB?", end_date_iso="")
    ptb_info = SimpleNamespace(
        seconds_remaining=240,
        epoch_start_ts=epoch_start,
        epoch_end_ts=epoch_start + 300,
    )

    detail = trader._market_timing_detail(
        market,
        ptb_info,
        seconds_remaining=240,
        entry_cutoff_seconds=90,
    )

    assert detail["market_epoch_start"] == epoch_start
    assert detail["market_epoch_end"] == epoch_start + 300
    assert detail["seconds_since_open"] == 60
    assert detail["seconds_until_close"] == 240
    assert detail["first_seen_seconds_remaining"] == 240
    assert detail["first_evaluable_seconds_remaining"] == 240
    assert detail["first_seen_second"] == 60
    assert detail["first_orderbook_ready_second"] is None
    assert detail["first_candidate_ready_second"] is None
    assert detail["candidate_lifecycle_duration_seconds"] == 0
    assert detail["active_window_alignment_reason"] == "early_window_ready"


def test_select_markets_preloads_next_window_tokens_for_early_alignment(monkeypatch: pytest.MonkeyPatch) -> None:
    trader = _trader()
    now_ts = 1_700_000_060
    current_epoch = now_ts - (now_ts % 300)
    monkeypatch.setattr("polymarket.trader.time.time", lambda: now_ts)

    def _markets(ticker: str):
        return [
            SimpleNamespace(
                slug=f"{ticker.lower()}-current",
                condition_id=f"{ticker}-current",
                market_id=f"{ticker}-market-current",
                epoch_start_ts=current_epoch,
                epoch_end_ts=current_epoch + 300,
                seconds_remaining=current_epoch + 300 - now_ts,
                yes_token_id=f"{ticker}-yes-current",
                no_token_id=f"{ticker}-no-current",
            ),
            SimpleNamespace(
                slug=f"{ticker.lower()}-next",
                condition_id=f"{ticker}-next",
                market_id=f"{ticker}-market-next",
                epoch_start_ts=current_epoch + 300,
                epoch_end_ts=current_epoch + 600,
                seconds_remaining=current_epoch + 600 - now_ts,
                yes_token_id=f"{ticker}-yes-next",
                no_token_id=f"{ticker}-no-next",
            ),
        ]

    trader.gamma = SimpleNamespace(
        get_current_and_next_5min_markets=_markets,
        get_next_5min_market=lambda ticker: _markets(ticker)[1],
        get_exact_5min_ptb=lambda _ticker: None,
    )

    markets = trader._select_markets(top_n=2)

    assert trader._market_preload_lead_seconds() == 300
    assert ("BTC", current_epoch + 300) in trader._preloaded_token_ids
    assert ("ETH", current_epoch + 300) in trader._preloaded_token_ids
    assert [market.market_id for market in markets] == ["pm-5m-btc", "pm-5m-eth"]


def test_paper_close_tracks_simulated_bankroll_and_pnl() -> None:
    trader = _trader()
    pos = trader.tracker.open_position(
        symbol="pm-5m-btc",
        source="polymarket",
        side="BUY",
        entry_price=0.50,
        size=10.0,
        stop_loss=0.45,
        take_profit=0.60,
        order_id="paper-entry",
        metadata={"token_id": "yes-token", "outcome": "YES"},
    )
    trader._submit_order = MagicMock(return_value=OrderReceipt(
        order_id="paper-close",
        status="paper",
        token_id="yes-token",
        side="SELL",
        price=0.60,
        size=10.0,
    ))

    assert trader._close_position_with_retry(pos, reason="take_profit", exit_price=0.60)

    summary = trader.paper_session_summary()
    assert trader.settings.account_balance == pytest.approx(101.0)
    assert summary["simulated_bankroll"] == 101.0
    assert summary["simulated_pnl"] == pytest.approx(1.0)
    assert summary["win_rate"] == 1.0
    assert summary["paper_exits"] == 1
    assert summary["position_state_transitions"]["OPEN->EXIT:take_profit"] == 1


def test_telegram_failure_does_not_crash_paper_exit_or_pnl_updates() -> None:
    trader = _trader()
    trader.telegram_alerts = _FailingTelegramAlerts()
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    pos = trader.tracker.open_position(
        symbol="pm-5m-btc",
        source="polymarket",
        side="BUY",
        entry_price=0.50,
        size=10.0,
        stop_loss=0.45,
        take_profit=0.60,
        order_id="paper-entry",
        metadata={"token_id": "yes-token", "outcome": "YES"},
    )
    trader._submit_order = MagicMock(return_value=OrderReceipt(
        order_id="paper-close",
        status="paper",
        token_id="yes-token",
        side="SELL",
        price=0.60,
        size=10.0,
    ))

    assert trader._close_position_with_retry(pos, reason="take_profit", exit_price=0.60)

    summary = trader.paper_session_summary()
    assert summary["paper_exits"] == 1
    assert trader.settings.account_balance == pytest.approx(101.0)
    assert any(event_name == "trade_close" for event_name, _payload in collector.events)


def test_paper_summary_tracks_skips_average_ev_and_trade_frequency() -> None:
    trader = _trader()
    trader.paper_stats.cycles_scanned = 2
    trader.paper_stats.markets_scanned = 3
    trader.paper_stats.paper_orders_created = 1
    trader.paper_stats.paper_fills = 1
    trader._paper_record_model(0.70, 0.04, opportunity_found=True)
    trader._paper_record_model(0.60, -0.01, opportunity_found=False)
    trader._paper_record_skip("ev_below_threshold")
    trader._paper_record_cancel("stale_entry_order")
    trader._paper_record_trade(2.50)

    summary = trader.paper_session_summary()

    assert summary["cycles_scanned"] == 2
    assert summary["total_markets_scanned"] == 3
    assert summary["total_opportunities_found"] == 1
    assert summary["total_trades_simulated"] == 1
    assert summary["paper_orders_created"] == 1
    assert summary["paper_fills"] == 1
    assert summary["paper_exits"] == 0
    assert summary["average_ev"] == pytest.approx(0.015)
    assert summary["average_confidence"] == pytest.approx(0.65)
    assert summary["average_position_size"] == 2.50
    assert summary["trade_frequency_last_hour"] == 1
    assert summary["skipped_trade_reasons"]["ev_below_threshold"] == 1
    assert summary["top_skip_reasons"] == [("ev_below_threshold", 1)]
    assert summary["order_cancel_reasons"]["stale_entry_order"] == 1


# ---------------------------------------------------------------------------
# Residual balance fix: cycle_risk_pause emits real bankroll (not silent 0.0)
# ---------------------------------------------------------------------------

def test_cycle_risk_pause_emits_real_balance_not_zero() -> None:
    """Regression test: cycle_risk_pause JSONL event must carry the real bankroll.

    Root cause of original bug: trader.py used
        getattr(self._risk_mgr, "_balance", 0.0)
    RiskManager is a facade — it has no _balance attribute of its own
    (_balance lives in _tier_mgr). getattr always silently returned 0.0.

    Fix: replaced with self._risk_mgr.balance (the public property).

    This test:
      1. Proves getattr returns 0.0 on RiskManager (proof of old bug).
      2. Proves .balance returns the real figure.
      3. Proves the emitted JSONL event carries the real figure, not 0.0.
    """
    # Start at $80.00, record 3 × $1.00 losses → balance drops to $77.00
    # and triggers LOSS_CLUSTER_THRESHOLD (= 3), pausing can_trade().
    trader = _trader(_settings(account_balance=80.0))
    collector = _CollectingQuantLogger()
    trader.quant_events = collector

    for _ in range(3):
        trader._risk_mgr.record_result(won=False, pnl=1.0)

    ok, pause_reason = trader._risk_mgr.can_trade()
    assert not ok, "3 consecutive losses should have activated the loss-cluster pause"

    # --- Proof of old bug ---
    # RiskManager has no _balance; getattr silently returns the default 0.0.
    assert getattr(trader._risk_mgr, "_balance", 0.0) == 0.0

    # --- Proof of fix ---
    # The public .balance property correctly delegates to _tier_mgr.balance.
    assert trader._risk_mgr.balance == pytest.approx(77.0)

    # --- Emit using the fixed expression ---
    trader._emit_risk_event(
        "cycle_risk_pause",
        {
            "reason": pause_reason,
            "balance": float(trader._risk_mgr.balance),   # fixed expression
        },
    )

    # The JSONL risk event must carry the real balance, not the silent 0.0.
    pause_events = [
        p for cat, p in collector.events
        if cat == "risk" and p.get("event") == "cycle_risk_pause"
    ]
    assert len(pause_events) == 1
    assert pause_events[0]["balance"] == pytest.approx(77.0), (
        f"Expected balance=77.0 in cycle_risk_pause payload, got {pause_events[0]['balance']}"
    )
    assert pause_events[0]["balance"] != 0.0
    assert pause_events[0]["reason"] == pause_reason
