from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import main
from main import build_parser
from polymarket.client import BalanceSnapshot, OrderReceipt, OrderbookSnapshot
from polymarket.order_manager import PolymarketOrderManager
from polymarket.order_intent import OrderIntentType
from polymarket.trader import BankrollState, PolymarketTrader, TradeOutcome
from utils.position_tracker import PositionTracker
from utils.risk_manager import RiskManager, RiskPlan


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
    }
    values.update(overrides)
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
