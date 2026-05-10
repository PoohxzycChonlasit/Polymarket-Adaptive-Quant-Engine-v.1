from __future__ import annotations

import logging
import time
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

    def log_trade_close(self, payload):
        self.events.append(("trade_close", payload))
        return True

    def log_system_health(self, payload):
        self.events.append(("system_health", payload))
        return True

    def log_decision(self, payload):
        self.events.append(("decision", payload))
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
    assert trader._market_readiness_metrics["empty_book_recovery_success"] == 1


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
    assert detail["liquidity_state"] == "EMPTY"
    assert trader._market_readiness_metrics["empty_book_recovery_failed"] == 1


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
