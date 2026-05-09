from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import main
from main import build_parser
from polymarket.client import BalanceSnapshot, OrderReceipt, OrderbookSnapshot
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
    assert metrics.skip_reason == "token_mapping_warning"


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

    assert metrics.skip_reason == "no_orderbook"
    assert any("last_successful_orderbook_age_ms=321" in record.message for record in caplog.records)
    assert any("market_slug=btc-updown-5m" in record.message for record in caplog.records)


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
