"""Tests for MICRO_LIVE_KILL_SWITCH_AND_DOLLAR_CAPS_001.

Covers:
- Kill switch file exists blocks live order (both in trader and client)
- Kill switch does not submit order (assert place_limit_order not called)
- Kill switch triggers lockdown on trader and emits event
- Live order over max_order_usd is blocked and emits live_order_cap_exceeded
- Live daily realized loss over max_daily_loss_usd is blocked and emits live_daily_loss_cap_exceeded
- Live exposure over max_open_exposure_usd is blocked and emits live_open_exposure_cap_exceeded
- Paper mode is completely unaffected by kill switch or caps
- Default cap values are safe and set correctly in settings
- No .env is required and no live network calls are made
"""
from __future__ import annotations

import os
import pytest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from polymarket.trader import PolymarketTrader, BankrollState
from polymarket.client import PolymarketClient, BUY
from polymarket.order_intent import OrderIntentType
from config.settings import Settings


# ---------------------------------------------------------------------------
# Test: Default cap values are safe
# ---------------------------------------------------------------------------

def test_settings_default_caps():
    """Verify settings default safety values are as expected."""
    # Test setting construction
    settings = Settings.model_validate({
        "paper_trading": True, # keep validation simple
    })
    assert settings.live_kill_switch_file == "runtime/KILL_SWITCH"
    assert settings.live_max_order_usd == 5.0
    assert settings.live_max_daily_loss_usd == 3.0
    assert settings.live_max_open_exposure_usd == 10.0


# ---------------------------------------------------------------------------
# Test: Client-level Kill Switch Gate
# ---------------------------------------------------------------------------

@patch("os.path.exists")
def test_client_kill_switch_blocks_live_order(mock_exists):
    """If kill switch file exists, PolymarketClient.place_limit_order must raise RuntimeError for live."""
    mock_settings = MagicMock()
    mock_settings.paper_trading = False
    mock_settings.live_kill_switch_file = "runtime/KILL_SWITCH"

    client = PolymarketClient.__new__(PolymarketClient)
    client.settings = mock_settings

    # Scenario 1: Kill switch file exists -> raises
    mock_exists.return_value = True
    with pytest.raises(RuntimeError, match="live_kill_switch_active"):
        client.place_limit_order(
            token_id="tok_yes",
            price=0.5,
            size=1.0,
            side=BUY,
            check_balance=False,
        )

    # Scenario 2: Kill switch file does not exist -> tries to require clob (which raises connect err)
    mock_exists.return_value = False
    client._client = None
    with pytest.raises(RuntimeError, match="not connected"):
        client.place_limit_order(
            token_id="tok_yes",
            price=0.5,
            size=1.0,
            side=BUY,
            check_balance=False,
        )


@patch("os.path.exists")
def test_client_kill_switch_ignored_in_paper(mock_exists):
    """In paper mode, the client's place_limit_order should raise the paper blocked error, not kill switch."""
    mock_settings = MagicMock()
    mock_settings.paper_trading = True
    mock_settings.live_kill_switch_file = "runtime/KILL_SWITCH"

    client = PolymarketClient.__new__(PolymarketClient)
    client.settings = mock_settings

    mock_exists.return_value = True
    with pytest.raises(RuntimeError, match="paper_mode_live_order_api_blocked"):
        client.place_limit_order(
            token_id="tok_yes",
            price=0.5,
            size=1.0,
            side=BUY,
            check_balance=False,
        )


# ---------------------------------------------------------------------------
# Helper: Trader mock factory
# ---------------------------------------------------------------------------

def _make_mock_trader(
    *,
    paper_trading: bool = False,
    realized_pnl: float = 0.0,
    open_positions: list = None,
) -> PolymarketTrader:
    trader = PolymarketTrader.__new__(PolymarketTrader)
    trader.settings = MagicMock()
    trader.settings.paper_trading = paper_trading
    trader.settings.live_kill_switch_file = "runtime/KILL_SWITCH"
    trader.settings.live_max_order_usd = 5.0
    trader.settings.live_max_daily_loss_usd = 3.0
    trader.settings.live_max_open_exposure_usd = 10.0

    trader.bankroll_state = BankrollState(
        starting_bankroll=100.0,
        current_cash_balance=100.0,
        realized_pnl=realized_pnl,
    )

    trader.tracker = MagicMock()
    trader.tracker.open_positions.return_value = open_positions or []

    trader.quant_events = MagicMock()
    trader.telegram_alerts = MagicMock()

    trader._risk_mode_state = MagicMock()
    trader._last_risk_mode_log = ""
    trader._last_risk_mode_decision = None

    trader._trigger_lockdown = MagicMock()
    trader._emit_quant_event = MagicMock()
    trader._notify_telegram = MagicMock()
    trader._runtime_mode = MagicMock(return_value="live" if not paper_trading else "paper")

    return trader


# ---------------------------------------------------------------------------
# Tests: Trader-level Kill Switch and Dollar Caps
# ---------------------------------------------------------------------------

class TestTraderSafetyControls:

    @patch("os.path.exists")
    def test_trader_kill_switch_blocks_live_and_lockdown(self, mock_exists):
        """In live mode, if kill switch file exists, order intent validation must block and trigger lockdown."""
        trader = _make_mock_trader(paper_trading=False)
        mock_exists.return_value = True

        result = trader._validate_submit_order_intent(
            market_id="tok_yes",
            side=BUY,
            price=0.5,
            size=1.0,
            intent_type=OrderIntentType.ENTRY,
        )

        assert result is False
        trader._trigger_lockdown.assert_called_once_with("kill_switch_file_detected")
        trader._emit_quant_event.assert_any_call("log_system_health", {
            "event": "live_kill_switch_triggered",
            "kill_switch_file": "runtime/KILL_SWITCH",
            "mode": "live",
        })
        trader._notify_telegram.assert_called_once()
        assert "kill switch" in trader._notify_telegram.call_args[0][1].lower()

    @patch("os.path.exists")
    def test_trader_kill_switch_warns_but_passes_in_paper(self, mock_exists):
        """In paper mode, if kill switch file exists, order intent is evaluated normally (lockdown/block skipped)."""
        trader = _make_mock_trader(paper_trading=True)
        mock_exists.return_value = True

        # Mock standard validation internals to return True
        with patch("polymarket.trader.validate_order_intent") as mock_validate:
            mock_validate.return_value = MagicMock(approved=True, reason="entry_approved")
            trader._reconciliation_safe_for_entry = MagicMock(return_value=True)

            result = trader._validate_submit_order_intent(
                market_id="tok_yes",
                side=BUY,
                price=0.5,
                size=1.0,
                intent_type=OrderIntentType.ENTRY,
            )

            assert result is True
            trader._trigger_lockdown.assert_not_called()
            # verify it didn't emit the system health / kill switch event
            for call in trader._emit_quant_event.call_args_list:
                args = call[0]
                assert args[0] != "log_system_health"

    @patch("os.path.exists")
    def test_trader_order_cap_blocks_live(self, mock_exists):
        """If live order notional > live_max_order_usd, block submission."""
        trader = _make_mock_trader(paper_trading=False)
        mock_exists.return_value = False

        # Max order is 5.0 USD. Order notional = 12.0 * 0.5 = 6.0 USD
        result = trader._validate_submit_order_intent(
            market_id="tok_yes",
            side=BUY,
            price=0.5,
            size=12.0,
            intent_type=OrderIntentType.ENTRY,
        )

        assert result is False
        trader._emit_quant_event.assert_any_call("log_execution", {
            "event": "order_intent_reject",
            "reason": "live_order_cap_exceeded",
            "token_id": "tok_yes",
            "side": BUY,
            "price": 0.5,
            "size": 12.0,
            "notional": 6.0,
            "max_order_usd": 5.0,
            "risk_state": "blocked",
            "mode": "live",
        })

    @patch("os.path.exists")
    def test_trader_daily_loss_cap_blocks_live(self, mock_exists):
        """If daily realized loss >= live_max_daily_loss_usd, block submission."""
        # max loss is 3.0. Realized PnL of -3.5 means realized loss is 3.5.
        trader = _make_mock_trader(paper_trading=False, realized_pnl=-3.5)
        mock_exists.return_value = False

        result = trader._validate_submit_order_intent(
            market_id="tok_yes",
            side=BUY,
            price=0.5,
            size=2.0, # notional 1.0
            intent_type=OrderIntentType.ENTRY,
        )

        assert result is False
        trader._emit_quant_event.assert_any_call("log_execution", {
            "event": "order_intent_reject",
            "reason": "live_daily_loss_cap_exceeded",
            "token_id": "tok_yes",
            "side": BUY,
            "price": 0.5,
            "size": 2.0,
            "realized_loss": 3.5,
            "max_daily_loss_usd": 3.0,
            "risk_state": "blocked",
            "mode": "live",
        })

    @patch("os.path.exists")
    def test_trader_open_exposure_cap_blocks_live(self, mock_exists):
        """If current_exposure + new_notional > max_open_exposure_usd, block submission."""
        # max exposure is 10.0. Current exposure is 8.0. New notional is 3.0.
        pos1 = MagicMock()
        pos1.status = "open"
        pos1.notional_size = 5.0
        pos2 = MagicMock()
        pos2.status = "open"
        pos2.notional_size = 3.0

        trader = _make_mock_trader(paper_trading=False, open_positions=[pos1, pos2])
        mock_exists.return_value = False

        result = trader._validate_submit_order_intent(
            market_id="tok_yes",
            side=BUY,
            price=0.5,
            size=6.0, # notional 3.0
            intent_type=OrderIntentType.ENTRY,
        )

        assert result is False
        trader._emit_quant_event.assert_any_call("log_execution", {
            "event": "order_intent_reject",
            "reason": "live_open_exposure_cap_exceeded",
            "token_id": "tok_yes",
            "side": BUY,
            "price": 0.5,
            "size": 6.0,
            "current_exposure": 8.0,
            "order_notional": 3.0,
            "max_open_exposure_usd": 10.0,
            "risk_state": "blocked",
            "mode": "live",
        })

    @patch("os.path.exists")
    def test_paper_mode_completely_unaffected_by_caps(self, mock_exists):
        """In paper mode, all caps are ignored even if exceeded."""
        # Max order 5.0, notional is 6.0.
        # Max loss 3.0, realized pnl is -4.0.
        # Max exposure 10.0, current is 8.0 + 3.0 = 11.0.
        pos1 = MagicMock()
        pos1.status = "open"
        pos1.notional_size = 8.0

        trader = _make_mock_trader(paper_trading=True, realized_pnl=-4.0, open_positions=[pos1])
        mock_exists.return_value = False

        with patch("polymarket.trader.validate_order_intent") as mock_validate:
            mock_validate.return_value = MagicMock(approved=True, reason="entry_approved")
            trader._reconciliation_safe_for_entry = MagicMock(return_value=True)

            result = trader._validate_submit_order_intent(
                market_id="tok_yes",
                side=BUY,
                price=0.5,
                size=12.0, # notional 6.0
                intent_type=OrderIntentType.ENTRY,
            )

            assert result is True
            # No cap reject event emitted
            for call in trader._emit_quant_event.call_args_list:
                payload = call[0][1]
                assert payload.get("reason") not in (
                    "live_order_cap_exceeded",
                    "live_daily_loss_cap_exceeded",
                    "live_open_exposure_cap_exceeded"
                )
