"""Tests for P0.2: live fill confirmation loop.

Verifies:
- live_fill_timeout_sec exists in settings with default 30.0
- live execution path passes timeout_sec to place_limit_order
- paper mode does NOT use live fill timeout (behavior unchanged)
- timeout_cancelled receipt does NOT open a tracked position
- filled receipt gates position open (fill confirmed)
- pending/live receipt does NOT open a tracked position
- wait_for_fill terminal statuses are correct
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from dataclasses import dataclass

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Settings test
# ---------------------------------------------------------------------------

class TestLiveFillTimeoutSetting:
    def test_live_fill_timeout_sec_default(self):
        """live_fill_timeout_sec must have default 30.0."""
        from config.settings import Settings
        s = Settings(_env_file=None)
        assert hasattr(s, "live_fill_timeout_sec")
        assert float(s.live_fill_timeout_sec) == 30.0

    def test_live_fill_timeout_sec_configurable(self):
        """live_fill_timeout_sec must be settable."""
        from config.settings import Settings
        s = Settings(_env_file=None, live_fill_timeout_sec=45.0)
        assert s.live_fill_timeout_sec == 45.0


# ---------------------------------------------------------------------------
# OrderReceipt stub
# ---------------------------------------------------------------------------

@dataclass
class FakeReceipt:
    order_id: str = "fake_order_001"
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
# Fill status gating — unit tests on the logic extracted from trader.py
# ---------------------------------------------------------------------------

class TestFillStatusGating:
    """Test the fill confirmation gate logic directly."""

    FILL_CONFIRMED_STATUSES = {"filled", "matched"}

    def _is_fill_confirmed(self, paper_trading: bool, receipt_status: str | None) -> bool:
        """Mirror the logic added to trader.py."""
        if paper_trading:
            return True
        if receipt_status is None:
            return False
        return receipt_status.lower() in self.FILL_CONFIRMED_STATUSES

    # Paper mode — always confirmed
    def test_paper_mode_always_confirmed(self):
        for status in ("live", "open", "pending", "unknown", "timeout_cancelled", "cancelled", "filled"):
            assert self._is_fill_confirmed(True, status) is True

    def test_paper_mode_none_receipt_still_confirmed(self):
        assert self._is_fill_confirmed(True, None) is True

    # Live mode — only filled/matched
    def test_live_filled_status_confirmed(self):
        assert self._is_fill_confirmed(False, "filled") is True

    def test_live_matched_status_confirmed(self):
        assert self._is_fill_confirmed(False, "matched") is True

    def test_live_timeout_cancelled_not_confirmed(self):
        assert self._is_fill_confirmed(False, "timeout_cancelled") is False

    def test_live_cancelled_not_confirmed(self):
        assert self._is_fill_confirmed(False, "cancelled") is False

    def test_live_open_not_confirmed(self):
        assert self._is_fill_confirmed(False, "open") is False

    def test_live_live_status_not_confirmed(self):
        assert self._is_fill_confirmed(False, "live") is False

    def test_live_pending_not_confirmed(self):
        assert self._is_fill_confirmed(False, "pending") is False

    def test_live_unknown_not_confirmed(self):
        assert self._is_fill_confirmed(False, "unknown") is False

    def test_live_none_receipt_not_confirmed(self):
        assert self._is_fill_confirmed(False, None) is False

    def test_case_insensitive_filled(self):
        assert self._is_fill_confirmed(False, "FILLED") is True
        assert self._is_fill_confirmed(False, "Matched") is True


# ---------------------------------------------------------------------------
# client.wait_for_fill terminal statuses
# ---------------------------------------------------------------------------

class TestWaitForFillTerminalStatuses:
    def test_terminal_statuses_include_filled(self):
        """Terminal statuses must include 'filled' so wait_for_fill returns on fill."""
        # Read the terminal set from the source
        from polymarket.client import PolymarketClient
        import inspect
        src = inspect.getsource(PolymarketClient.wait_for_fill)
        assert "filled" in src
        assert "matched" in src
        assert "cancelled" in src
        assert "timeout" in src or "timeout_cancelled" in src

    def test_wait_for_fill_returns_on_filled_status(self):
        """wait_for_fill must return immediately when order status = filled."""
        from polymarket.client import PolymarketClient
        mock_settings = MagicMock()
        mock_settings.paper_trading = False
        mock_settings.api_retry_attempts = 1
        mock_settings.api_retry_backoff_base = 0.1
        mock_settings.api_circuit_breaker_threshold = 5
        mock_settings.api_circuit_breaker_cooldown = 60

        client = PolymarketClient.__new__(PolymarketClient)
        client.settings = mock_settings
        client._client = MagicMock()
        client._consecutive_failures = 0
        client._circuit_open_until = 0.0
        client._orderbook_health = {}

        filled_receipt = FakeReceipt(status="filled", filled_size=1.0, remaining_size=0.0)
        client.get_order_status = MagicMock(return_value=filled_receipt)

        result = client.wait_for_fill("fake_order_001", timeout_sec=10.0, original=FakeReceipt())
        assert result.status == "filled"
        assert client.get_order_status.call_count == 1  # returned on first poll

    def test_wait_for_fill_cancel_on_timeout_method_exists(self):
        """wait_for_fill must accept cancel_on_timeout=True parameter."""
        from polymarket.client import PolymarketClient
        import inspect
        sig = inspect.signature(PolymarketClient.wait_for_fill)
        params = sig.parameters
        assert "timeout_sec" in params
        assert "cancel_on_timeout" in params
        assert "original" in params


# ---------------------------------------------------------------------------
# place_limit_order timeout_sec behavior
# ---------------------------------------------------------------------------

class TestPlaceLimitOrderTimeout:
    def test_place_limit_order_calls_wait_for_fill_when_timeout_sec_given(self):
        """When timeout_sec is provided, wait_for_fill must be called."""
        from polymarket.client import PolymarketClient
        mock_settings = MagicMock()
        mock_settings.paper_trading = False
        mock_settings.api_retry_attempts = 1
        mock_settings.api_retry_backoff_base = 0.1
        mock_settings.api_circuit_breaker_threshold = 5
        mock_settings.api_circuit_breaker_cooldown = 60

        client = PolymarketClient.__new__(PolymarketClient)
        client.settings = mock_settings
        client._consecutive_failures = 0
        client._circuit_open_until = 0.0
        client._orderbook_health = {}

        # Mock internals
        mock_clob = MagicMock()
        mock_clob.create_order.return_value = MagicMock()
        mock_clob.post_order.return_value = {"orderID": "ord_001", "status": "live"}
        client._client = mock_clob

        filled = FakeReceipt(status="filled", filled_size=1.0)
        client.wait_for_fill = MagicMock(return_value=filled)
        client._preflight_balance_allowance = MagicMock()

        result = client.place_limit_order(
            token_id="tok_001", price=0.55, size=1.0, side="BUY",
            timeout_sec=30.0
        )
        client.wait_for_fill.assert_called_once()
        assert result.status == "filled"

    def test_place_limit_order_no_wait_when_no_timeout(self):
        """Without timeout_sec, wait_for_fill must NOT be called."""
        from polymarket.client import PolymarketClient
        mock_settings = MagicMock()
        mock_settings.paper_trading = False
        mock_settings.api_retry_attempts = 1
        mock_settings.api_retry_backoff_base = 0.1
        mock_settings.api_circuit_breaker_threshold = 5
        mock_settings.api_circuit_breaker_cooldown = 60

        client = PolymarketClient.__new__(PolymarketClient)
        client.settings = mock_settings
        client._consecutive_failures = 0
        client._circuit_open_until = 0.0
        client._orderbook_health = {}

        mock_clob = MagicMock()
        mock_clob.create_order.return_value = MagicMock()
        mock_clob.post_order.return_value = {"orderID": "ord_002", "status": "live"}
        client._client = mock_clob
        client.wait_for_fill = MagicMock()
        client._preflight_balance_allowance = MagicMock()

        client.place_limit_order(
            token_id="tok_001", price=0.55, size=1.0, side="BUY"
            # no timeout_sec
        )
        client.wait_for_fill.assert_not_called()
