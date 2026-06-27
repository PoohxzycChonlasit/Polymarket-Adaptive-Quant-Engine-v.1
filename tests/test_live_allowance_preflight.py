"""Tests for live allowance preflight safety — P0.1 implementation.

Tests:
- allowance=0 fails preflight (bug fix)
- allowance below needed fails preflight
- allowance sufficient passes preflight
- balance insufficient fails preflight
- check_allowance_status returns correct status
- verify_signing_capability returns expected shape
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from polymarket.client import PolymarketClient, BUY, SELL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client() -> PolymarketClient:
    """Create a PolymarketClient with mocked settings (no real connection)."""
    mock_settings = MagicMock()
    mock_settings.paper_trading = False
    mock_settings.polymarket_api_key = "test_key"
    mock_settings.api_retry_attempts = 1
    mock_settings.api_retry_backoff_base = 0.1
    mock_settings.api_circuit_breaker_threshold = 5
    mock_settings.api_circuit_breaker_cooldown = 60
    client = PolymarketClient.__new__(PolymarketClient)
    client.settings = mock_settings
    client._client = None
    client._consecutive_failures = 0
    client._circuit_open_until = 0.0
    client._orderbook_health: dict = {}
    return client


# ---------------------------------------------------------------------------
# Tests: _preflight_balance_allowance bug fix
# ---------------------------------------------------------------------------

class TestPreflightBugFix:
    """Verify the zero-allowance bug is fixed."""

    def _preflight(self, client, balance, allowance, needed_price, needed_size, side=BUY):
        client.get_balance_allowance = MagicMock(return_value={
            "balance": balance,
            "allowance": allowance,
        })
        client._preflight_balance_allowance(
            token_id="tok_test",
            price=needed_price,
            size=needed_size,
            side=side,
        )

    def test_zero_allowance_raises_for_buy(self):
        """allowance=0 must raise RuntimeError for BUY (was silently skipped before fix)."""
        client = _make_client()
        with pytest.raises(RuntimeError, match="insufficient USDC allowance"):
            self._preflight(client, balance=10.0, allowance=0.0,
                           needed_price=0.5, needed_size=1.0)

    def test_allowance_below_needed_raises(self):
        """allowance < needed must raise."""
        client = _make_client()
        with pytest.raises(RuntimeError, match="insufficient USDC allowance"):
            self._preflight(client, balance=10.0, allowance=0.3,
                           needed_price=0.5, needed_size=1.0)  # needed=0.5

    def test_allowance_exactly_equal_passes(self):
        """allowance == needed (within float epsilon) must NOT raise."""
        client = _make_client()
        self._preflight(client, balance=10.0, allowance=0.5,
                       needed_price=0.5, needed_size=1.0)

    def test_allowance_sufficient_passes(self):
        """allowance > needed must pass."""
        client = _make_client()
        self._preflight(client, balance=10.0, allowance=5.0,
                       needed_price=0.5, needed_size=1.0)

    def test_balance_insufficient_raises(self):
        """balance < needed must raise (regardless of allowance)."""
        client = _make_client()
        with pytest.raises(RuntimeError, match="insufficient USDC balance"):
            self._preflight(client, balance=0.1, allowance=5.0,
                           needed_price=0.5, needed_size=1.0)

    def test_sell_side_skips_allowance_check(self):
        """SELL orders (token exit) do not require USDC allowance — should not raise."""
        client = _make_client()
        client.get_balance_allowance = MagicMock(return_value={
            "balance": 1.0,   # token balance
            "allowance": 0.0, # USDC allowance irrelevant for SELL
        })
        # For SELL: needed = size (token amount, not USDC)
        client._preflight_balance_allowance(
            token_id="tok_test", price=0.5, size=0.5, side=SELL
        )

    def test_error_message_includes_approval_guidance(self):
        """Error message must mention the approval doc path."""
        client = _make_client()
        with pytest.raises(RuntimeError) as exc_info:
            client.get_balance_allowance = MagicMock(return_value={"balance": 10.0, "allowance": 0.0})
            client._preflight_balance_allowance(token_id="t", price=0.5, size=1.0, side=BUY)
        assert "LIVE_EXECUTION_GAP_ANALYSIS_001" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Tests: check_allowance_status
# ---------------------------------------------------------------------------

class TestCheckAllowanceStatus:
    def test_zero_allowance_returns_missing(self):
        client = _make_client()
        client.get_balance_allowance = MagicMock(return_value={"balance": 5.0, "allowance": 0.0})
        result = client.check_allowance_status(needed=0.5)
        assert result["status"] == "MISSING"
        assert result["approve_required"] is True
        assert "approve" in result["message"].lower()

    def test_sufficient_allowance_returns_ok(self):
        client = _make_client()
        client.get_balance_allowance = MagicMock(return_value={"balance": 5.0, "allowance": 100.0})
        result = client.check_allowance_status(needed=0.5)
        assert result["status"] == "OK"
        assert result["approve_required"] is False

    def test_insufficient_allowance_returns_insufficient(self):
        client = _make_client()
        client.get_balance_allowance = MagicMock(return_value={"balance": 5.0, "allowance": 0.3})
        result = client.check_allowance_status(needed=0.5)
        assert result["status"] == "INSUFFICIENT"
        assert result["approve_required"] is True

    def test_api_failure_returns_fail(self):
        client = _make_client()
        client.get_balance_allowance = MagicMock(side_effect=RuntimeError("connection failed"))
        result = client.check_allowance_status()
        assert result["status"] == "FAIL"
        assert "Failed" in result["message"]

    def test_result_has_required_keys(self):
        client = _make_client()
        client.get_balance_allowance = MagicMock(return_value={"balance": 1.0, "allowance": 5.0})
        result = client.check_allowance_status(needed=0.5)
        for key in ("status", "balance", "allowance", "needed", "message", "approve_required"):
            assert key in result, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Tests: verify_signing_capability
# ---------------------------------------------------------------------------

class TestVerifySigningCapability:
    def test_not_connected_returns_fail(self):
        client = _make_client()
        client._client = None
        result = client.verify_signing_capability()
        assert result["status"] == "FAIL"
        assert result["has_signer"] is False

    def test_connected_with_signer_returns_ok(self):
        client = _make_client()
        mock_clob = MagicMock()
        mock_clob.signer = MagicMock()
        mock_clob.builder = MagicMock()
        mock_clob.builder.sig_type = 0
        client._client = mock_clob
        result = client.verify_signing_capability()
        assert result["status"] == "OK"
        assert result["has_signer"] is True
        assert result["has_builder"] is True
        assert result["sig_type"] == 0

    def test_missing_signer_returns_fail(self):
        client = _make_client()
        mock_clob = MagicMock()
        mock_clob.signer = None
        mock_clob.builder = MagicMock()
        client._client = mock_clob
        result = client.verify_signing_capability()
        assert result["status"] == "FAIL"
        assert result["has_signer"] is False
        assert "private key" in result["message"].lower()

    def test_missing_builder_returns_fail(self):
        client = _make_client()
        mock_clob = MagicMock()
        mock_clob.signer = MagicMock()
        mock_clob.builder = None
        client._client = mock_clob
        result = client.verify_signing_capability()
        assert result["status"] == "FAIL"
        assert result["has_builder"] is False

    def test_result_has_required_keys(self):
        client = _make_client()
        mock_clob = MagicMock()
        mock_clob.signer = MagicMock()
        mock_clob.builder = MagicMock()
        mock_clob.builder.sig_type = 2
        client._client = mock_clob
        result = client.verify_signing_capability()
        for key in ("status", "has_signer", "has_builder", "sig_type", "message"):
            assert key in result
