"""Tests for proxy wallet allowance check semantics.

Verifies correct handling of standard EOA vs Gnosis/Proxy signature types.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from polymarket.client import PolymarketClient, BUY, SELL
from polymarket.trader import PolymarketTrader


def _make_client(signature_type: int = 0, proxy_wallet: str = "") -> PolymarketClient:
    mock_settings = MagicMock()
    mock_settings.paper_trading = False
    mock_settings.polymarket_api_key = "test_key"
    mock_settings.polymarket_signature_type = signature_type
    mock_settings.polymarket_proxy_wallet = proxy_wallet
    mock_settings.api_retry_attempts = 1
    mock_settings.api_retry_backoff_base = 0.1
    mock_settings.api_circuit_breaker_threshold = 5
    mock_settings.api_circuit_breaker_cooldown = 60
    
    client = PolymarketClient.__new__(PolymarketClient)
    client.settings = mock_settings
    client._client = None
    client._consecutive_failures = 0
    client._circuit_open_until = 0.0
    client._orderbook_health = {}
    return client


class TestEOAAllowanceSemantics:
    """Standard EOA wallet tests (signature_type = 0)."""

    def test_eoa_zero_allowance_fails(self):
        client = _make_client(signature_type=0)
        client.get_balance_allowance = MagicMock(return_value={
            "balance": 10.0,
            "allowance": 0.0,
        })
        with pytest.raises(RuntimeError, match="insufficient USDC allowance"):
            client._preflight_balance_allowance(
                token_id="tok_test",
                price=0.5,
                size=1.0,
                side=BUY,
            )

    def test_eoa_allowance_sufficient_passes(self):
        client = _make_client(signature_type=0)
        client.get_balance_allowance = MagicMock(return_value={
            "balance": 10.0,
            "allowance": 5.0,
        })
        client._preflight_balance_allowance(
            token_id="tok_test",
            price=0.5,
            size=1.0,
            side=BUY,
        )


class TestProxyAllowanceSemantics:
    """Proxy wallet tests (signature_type = 1/2 or proxy_wallet configured)."""

    @pytest.mark.parametrize("sig_type, proxy", [
        (1, ""),       # Gnosis Safe
        (2, ""),       # Proxy signature
        (0, "0x123"),   # Proxy wallet override
    ])
    def test_proxy_collateral_sufficient_passes_with_zero_allowance(self, sig_type, proxy):
        client = _make_client(signature_type=sig_type, proxy_wallet=proxy)
        client.get_balance_allowance = MagicMock(return_value={
            "balance": 10.0,
            "allowance": 0.0,
        })
        client._preflight_balance_allowance(
            token_id="tok_test",
            price=0.5,
            size=1.0,
            side=BUY,
        )

    @pytest.mark.parametrize("sig_type, proxy", [
        (1, ""),
        (2, ""),
        (0, "0x123"),
    ])
    def test_proxy_collateral_insufficient_fails(self, sig_type, proxy):
        client = _make_client(signature_type=sig_type, proxy_wallet=proxy)
        client.get_balance_allowance = MagicMock(return_value={
            "balance": 0.1,
            "allowance": 0.0,
        })
        with pytest.raises(RuntimeError, match="insufficient CLOB collateral balance"):
            client._preflight_balance_allowance(
                token_id="tok_test",
                price=0.5,
                size=1.0,
                side=BUY,
            )


class TestVerifyAccountReadinessSemantics:
    """Verify verify_account_readiness correctly exposes metadata."""

    @patch("polymarket.trader.PolymarketTrader._fetch_live_balance_snapshot")
    @patch("polymarket.trader.PolymarketTrader._record_balance_snapshot")
    def test_verify_exposes_metadata_fields(self, mock_record, mock_fetch):
        mock_settings = MagicMock()
        mock_settings.paper_trading = False
        mock_settings.polymarket_api_key = "test_key"
        mock_settings.polymarket_api_secret = MagicMock(get_secret_value=MagicMock(return_value="secret"))
        mock_settings.polymarket_private_key = MagicMock(get_secret_value=MagicMock(return_value="key"))
        mock_settings.polymarket_signature_type = 2
        mock_settings.polymarket_proxy_wallet = "0xProxy"
        mock_settings.micro_survival_min_position_size = 0.10
        mock_settings.bankroll_floor = 10.0

        trader = PolymarketTrader.__new__(PolymarketTrader)
        trader.settings = mock_settings
        trader._connected = True
        trader.tracker = MagicMock()
        trader.tracker.open_positions = MagicMock(return_value=[])
        trader.client = MagicMock()
        trader.client.connect = MagicMock()
        trader.client.check_live_credential_readiness = MagicMock(return_value={"status": "OK"})
        trader.client.get_balance_allowance = MagicMock(return_value={"balance": 20.0, "allowance": 0.0})
        trader.client.check_allowance_status = MagicMock(return_value={
            "status": "OK_PROXY_COLLATERAL",
            "approve_required": False,
        })
        trader.client.verify_signing_capability = MagicMock(return_value={"status": "OK"})
        trader.client.get_positions = MagicMock(return_value=[])
        trader.client.get_open_orders = MagicMock(return_value=[])
        trader.bankroll_state = MagicMock()
        trader.bankroll_state.peak_bankroll = 0.0
        trader.bankroll_state.starting_bankroll = 20.0
        trader.bankroll_state.current_cash_balance = 20.0
        trader.bankroll_state.daily_start_bankroll = 20.0
        trader.bankroll_rank_engine = MagicMock()
        trader._risk_mgr = MagicMock()
        trader.tracker.closed_positions = MagicMock(return_value=[])
        trader._bankroll_rank_lock = MagicMock()
        trader._update_bankroll_rank_lock = MagicMock()
        trader._update_risk_mode = MagicMock()
        trader._sync_sizing_bankroll = MagicMock()
        trader._emit_quant_event = MagicMock()
        trader._balance_wallet_address = "0xProxy"
        trader._true_empty_start_times = {}
        trader._last_true_empty_alert_times = {}

        mock_snapshot = MagicMock()
        mock_snapshot.balance = 20.0
        mock_snapshot.source = "clob_collateral"
        mock_fetch.return_value = mock_snapshot

        report = trader.verify_account_readiness()
        wallet = report["wallet"]

        assert wallet["wallet_type"] == "PROXY"
        assert wallet["signature_type"] == 2
        assert wallet["balance_source"] == "CLOB_COLLATERAL"
        assert wallet["collateral_balance"] == 20.0
        assert wallet["readiness_status"] == "OK_PROXY_COLLATERAL"
        assert wallet["approve_required"] is False
