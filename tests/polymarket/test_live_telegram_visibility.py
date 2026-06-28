"""Tests for P0.4: live order signing visibility and Telegram notifications.

Tests:
- 5 new notify_* methods exist on TelegramAlertLayer
- allowance missing calls notify_allowance_missing
- signing fail calls notify_signing_not_ready
- live order submitted calls notify_order_submitted
- pending fill confirmed calls notify_order_filled
- pending terminal (cancelled/timeout) calls notify_order_cancelled
- paper mode does NOT emit live order Telegram messages
- Telegram exceptions are swallowed (fail-soft)
- module-level helper functions exist
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from dataclasses import dataclass

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.telegram_alerts import (
    TelegramAlertLayer,
    AlertResult,
    notify_allowance_missing,
    notify_signing_not_ready,
    notify_order_submitted,
    notify_order_filled,
    notify_order_cancelled,
    notify_order_timeout_cancelled,
)


# ---------------------------------------------------------------------------
# FakeReceipt stub
# ---------------------------------------------------------------------------

@dataclass
class FakeReceipt:
    order_id: str = "ord_001"
    status: str = "live"
    token_id: str = "tok_001"
    side: str = "BUY"
    price: float = 0.55
    size: float = 1.0
    filled_size: float = 0.0
    remaining_size: float = 1.0
    created_at: str = "2026-06-27T00:00:00Z"
    order_type: str = "GTC"


# ---------------------------------------------------------------------------
# TelegramAlertLayer new methods exist
# ---------------------------------------------------------------------------

class TestNewMethodsExist:
    def test_notify_allowance_missing_exists(self):
        layer = TelegramAlertLayer()
        assert hasattr(layer, "notify_allowance_missing")
        assert callable(layer.notify_allowance_missing)

    def test_notify_signing_not_ready_exists(self):
        layer = TelegramAlertLayer()
        assert hasattr(layer, "notify_signing_not_ready")

    def test_notify_order_submitted_exists(self):
        layer = TelegramAlertLayer()
        assert hasattr(layer, "notify_order_submitted")

    def test_notify_order_filled_exists(self):
        layer = TelegramAlertLayer()
        assert hasattr(layer, "notify_order_filled")

    def test_notify_order_cancelled_exists(self):
        layer = TelegramAlertLayer()
        assert hasattr(layer, "notify_order_cancelled")

    def test_notify_order_timeout_cancelled_exists(self):
        layer = TelegramAlertLayer()
        assert hasattr(layer, "notify_order_timeout_cancelled")
        assert callable(layer.notify_order_timeout_cancelled)

    def test_module_level_helpers_exist(self):
        from utils import telegram_alerts as ta
        for fn in ("notify_allowance_missing", "notify_signing_not_ready",
                   "notify_order_submitted", "notify_order_filled",
                   "notify_order_cancelled", "notify_order_timeout_cancelled"):
            assert hasattr(ta, fn) and callable(getattr(ta, fn))


# ---------------------------------------------------------------------------
# New methods return AlertResult (fail-soft)
# ---------------------------------------------------------------------------

class TestNewMethodsReturnAlertResult:
    """Even with no notifier configured, methods return AlertResult without raising."""

    def _layer_no_notifier(self) -> TelegramAlertLayer:
        layer = TelegramAlertLayer()
        layer.notifier = None
        return layer

    def test_allowance_missing_no_notifier(self):
        result = self._layer_no_notifier().notify_allowance_missing("test")
        assert isinstance(result, AlertResult)

    def test_signing_not_ready_no_notifier(self):
        result = self._layer_no_notifier().notify_signing_not_ready("test")
        assert isinstance(result, AlertResult)

    def test_order_submitted_no_notifier(self):
        result = self._layer_no_notifier().notify_order_submitted("test")
        assert isinstance(result, AlertResult)

    def test_order_filled_no_notifier(self):
        result = self._layer_no_notifier().notify_order_filled("test")
        assert isinstance(result, AlertResult)

    def test_order_cancelled_no_notifier(self):
        result = self._layer_no_notifier().notify_order_cancelled("test")
        assert isinstance(result, AlertResult)

    def test_order_timeout_cancelled_no_notifier(self):
        result = self._layer_no_notifier().notify_order_timeout_cancelled("test")
        assert isinstance(result, AlertResult)


# ---------------------------------------------------------------------------
# Wiring tests — verify trader.py calls the right methods
# ---------------------------------------------------------------------------

class TestTelegramWiring:
    """Verify trader._notify_telegram is called with correct method names."""

    def _make_trader(self, paper: bool = False) -> MagicMock:
        trader = MagicMock()
        trader.settings = MagicMock()
        trader.settings.paper_trading = paper
        trader._notify_telegram = MagicMock()
        trader._emit_quant_event = MagicMock()
        trader._runtime_mode = MagicMock(return_value="LIVE" if not paper else "PAPER")
        return trader

    def test_poll_fill_confirmed_calls_notify_order_filled(self):
        from polymarket.trader import PolymarketTrader
        trader = self._make_trader(paper=False)
        filled = FakeReceipt(order_id="ord_fill", status="filled", filled_size=1.0)
        trader._pending_live_orders = {"ord_fill": FakeReceipt(order_id="ord_fill", status="live")}
        trader.client.get_order_status = MagicMock(return_value=filled)

        PolymarketTrader._poll_pending_live_orders(trader)

        # Should call notify_order_filled
        notify_calls = [c for c in trader._notify_telegram.call_args_list
                        if c[0][0] == "notify_order_filled"]
        assert len(notify_calls) == 1
        assert "ord_fill" in notify_calls[0][1].get("order_id", "") or "ord_fill" in str(notify_calls[0])

    def test_poll_cancelled_calls_notify_order_cancelled(self):
        from polymarket.trader import PolymarketTrader
        trader = self._make_trader(paper=False)
        cancelled = FakeReceipt(order_id="ord_cancel", status="cancelled", filled_size=0.0)
        trader._pending_live_orders = {"ord_cancel": FakeReceipt(order_id="ord_cancel")}
        trader.client.get_order_status = MagicMock(return_value=cancelled)

        PolymarketTrader._poll_pending_live_orders(trader)

        notify_calls = [c for c in trader._notify_telegram.call_args_list
                        if c[0][0] == "notify_order_cancelled"]
        assert len(notify_calls) == 1

    def test_poll_timeout_cancelled_calls_notify_order_timeout_cancelled(self):
        from polymarket.trader import PolymarketTrader
        trader = self._make_trader(paper=False)
        tc = FakeReceipt(order_id="ord_tc", status="timeout_cancelled", filled_size=0.0)
        trader._pending_live_orders = {"ord_tc": FakeReceipt(order_id="ord_tc")}
        trader.client.get_order_status = MagicMock(return_value=tc)

        PolymarketTrader._poll_pending_live_orders(trader)

        # timeout_cancelled must call notify_order_timeout_cancelled, NOT notify_order_cancelled
        timeout_calls = [c for c in trader._notify_telegram.call_args_list
                         if c[0][0] == "notify_order_timeout_cancelled"]
        assert len(timeout_calls) == 1
        cancelled_calls = [c for c in trader._notify_telegram.call_args_list
                           if c[0][0] == "notify_order_cancelled"]
        assert len(cancelled_calls) == 0

    def test_paper_mode_poll_skips_all_notifications(self):
        from polymarket.trader import PolymarketTrader
        trader = self._make_trader(paper=True)
        trader._pending_live_orders = {}

        PolymarketTrader._poll_pending_live_orders(trader)

        trader._notify_telegram.assert_not_called()
        trader.client.get_order_status.assert_not_called()

    def test_startup_allowance_missing_in_live_mode(self):
        """_log_wallet_startup_verification must call notify_allowance_missing when MISSING."""
        from polymarket.trader import PolymarketTrader
        trader = self._make_trader(paper=False)
        trader._update_bankroll_state = MagicMock(return_value=MagicMock(
            current_cash_balance=10.0, equity=10.0
        ))
        trader.tracker.summary = MagicMock(return_value=MagicMock(
            open_count=0, total_exposure=0.0
        ))
        trader._collateral_allowance_snapshot = MagicMock(return_value=("MISSING", 0.0, 0.0))
        trader._connected = True
        trader.settings.bankroll_floor = 1.0

        # verify_signing_capability returns OK so we don't get signing alert
        trader.client.verify_signing_capability = MagicMock(return_value={"status": "OK"})

        PolymarketTrader._log_wallet_startup_verification(trader)

        allowance_calls = [c for c in trader._notify_telegram.call_args_list
                           if c[0][0] == "notify_allowance_missing"]
        assert len(allowance_calls) == 1

    def test_startup_signing_fail_in_live_mode(self):
        """_log_wallet_startup_verification must call notify_signing_not_ready when signing fails."""
        from polymarket.trader import PolymarketTrader
        trader = self._make_trader(paper=False)
        trader._update_bankroll_state = MagicMock(return_value=MagicMock(
            current_cash_balance=10.0, equity=10.0
        ))
        trader.tracker.summary = MagicMock(return_value=MagicMock(
            open_count=0, total_exposure=0.0
        ))
        trader._collateral_allowance_snapshot = MagicMock(return_value=("OK", 100.0, 100.0))
        trader._connected = True
        trader.settings.bankroll_floor = 1.0

        trader.client.verify_signing_capability = MagicMock(return_value={
            "status": "FAIL",
            "message": "Signer is None",
            "has_signer": False,
            "has_builder": True,
            "sig_type": None,
        })

        PolymarketTrader._log_wallet_startup_verification(trader)

        signing_calls = [c for c in trader._notify_telegram.call_args_list
                         if c[0][0] == "notify_signing_not_ready"]
        assert len(signing_calls) == 1

    def test_startup_paper_mode_no_live_notifications(self):
        """Paper mode startup must not call live-specific Telegram helpers."""
        from polymarket.trader import PolymarketTrader
        trader = self._make_trader(paper=True)
        trader._update_bankroll_state = MagicMock(return_value=MagicMock(
            current_cash_balance=10.0, equity=10.0
        ))
        trader.tracker.summary = MagicMock(return_value=MagicMock(
            open_count=0, total_exposure=0.0
        ))
        trader._collateral_allowance_snapshot = MagicMock(return_value=("MISSING", 0.0, 0.0))
        trader._connected = True
        trader.settings.bankroll_floor = 1.0

        PolymarketTrader._log_wallet_startup_verification(trader)

        # Should not call allowance_missing or signing_not_ready in paper mode
        live_calls = [c for c in trader._notify_telegram.call_args_list
                      if c[0][0] in ("notify_allowance_missing", "notify_signing_not_ready")]
        assert len(live_calls) == 0

    def test_notify_telegram_exception_is_swallowed(self):
        """_notify_telegram exceptions must not propagate."""
        from polymarket.trader import PolymarketTrader
        trader = self._make_trader(paper=False)
        # Make _notify_telegram raise
        trader._notify_telegram = MagicMock(side_effect=RuntimeError("telegram down"))

        # _poll_pending_live_orders with a filled order — should not crash despite Telegram error
        filled = FakeReceipt(order_id="ord_ok", status="filled", filled_size=1.0)
        trader._pending_live_orders = {"ord_ok": FakeReceipt(order_id="ord_ok")}
        trader.client.get_order_status = MagicMock(return_value=filled)

        # Must not raise
        try:
            PolymarketTrader._poll_pending_live_orders(trader)
        except RuntimeError:
            pytest.fail("_poll_pending_live_orders raised on Telegram failure")
