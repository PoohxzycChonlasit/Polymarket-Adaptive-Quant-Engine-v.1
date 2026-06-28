"""Tests for APPROVE_ALLOWANCE_IMPLEMENTATION_001.

Covers:
- Missing private key fails live credential check (B4)
- Missing funder fails live credential check (B4)
- Missing API key fails live credential check (B4)
- Missing API secret fails live credential check (B4)
- Missing API passphrase fails live credential check (B4)
- Invalid signature type fails live credential check (B4)
- All credentials present passes live credential check
- check_allowance_status returns MISSING when allowance=0 (B1)
- check_allowance_status returns INSUFFICIENT when allowance < needed (B1)
- check_allowance_status returns OK when allowance >= needed (B1)
- verify output includes approve_instruction (manual approval message) (B1)
- Settings model raises ValueError for missing live credentials (B4)
- Paper mode is completely unaffected by new validators
- No live order is submitted in any test
- check_live_credential_readiness returns expected shape
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from pydantic import ValidationError

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from polymarket.client import PolymarketClient, BUY


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(
    *,
    paper_trading: bool = False,
    private_key: str = "0x" + "a" * 64,
    funder: str = "0x1234567890abcdef1234567890abcdef12345678",
    api_key: str = "test_api_key",
    api_secret: str = "test_api_secret",
    api_passphrase: str = "test_passphrase",
    sig_type: int = 0,
) -> PolymarketClient:
    """Create a PolymarketClient with mocked settings (no real connection)."""
    mock_settings = MagicMock()
    mock_settings.paper_trading = paper_trading

    # SecretStr-compatible mock
    def _make_secret(value: str) -> MagicMock:
        s = MagicMock()
        s.get_secret_value.return_value = value
        return s

    mock_settings.polymarket_private_key = _make_secret(private_key)
    mock_settings.polymarket_funder = funder
    mock_settings.polymarket_api_key = api_key
    mock_settings.polymarket_api_secret = _make_secret(api_secret)
    mock_settings.polymarket_api_passphrase = api_passphrase
    mock_settings.polymarket_signature_type = sig_type
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


# ---------------------------------------------------------------------------
# Tests: check_live_credential_readiness (B4)
# ---------------------------------------------------------------------------

class TestLiveCredentialReadiness:
    """Verify check_live_credential_readiness catches all missing credentials."""

    def test_all_credentials_present_returns_ok(self):
        """All required credentials present → status=OK."""
        client = _make_client()
        result = client.check_live_credential_readiness()
        assert result["status"] == "OK"
        assert result["failures"] == []
        assert result["approve_required"] is False
        assert "instructions" in result

    def test_missing_private_key_returns_fail(self):
        """Missing private key → FAIL with POLYMARKET_PRIVATE_KEY in failures."""
        client = _make_client(private_key="")
        result = client.check_live_credential_readiness()
        assert result["status"] == "FAIL"
        assert "POLYMARKET_PRIVATE_KEY" in result["failures"]
        assert result["approve_required"] is True

    def test_missing_funder_returns_fail(self):
        """Missing funder → FAIL with POLYMARKET_FUNDER in failures."""
        client = _make_client(funder="")
        result = client.check_live_credential_readiness()
        assert result["status"] == "FAIL"
        assert "POLYMARKET_FUNDER" in result["failures"]
        assert result["approve_required"] is True

    def test_missing_api_key_returns_fail(self):
        """Missing api_key → FAIL with POLYMARKET_API_KEY in failures."""
        client = _make_client(api_key="")
        result = client.check_live_credential_readiness()
        assert result["status"] == "FAIL"
        assert "POLYMARKET_API_KEY" in result["failures"]

    def test_missing_api_secret_returns_fail(self):
        """Missing api_secret → FAIL with POLYMARKET_API_SECRET in failures."""
        client = _make_client(api_secret="")
        result = client.check_live_credential_readiness()
        assert result["status"] == "FAIL"
        assert "POLYMARKET_API_SECRET" in result["failures"]

    def test_missing_api_passphrase_returns_fail(self):
        """Missing api_passphrase → FAIL with POLYMARKET_API_PASSPHRASE in failures."""
        client = _make_client(api_passphrase="")
        result = client.check_live_credential_readiness()
        assert result["status"] == "FAIL"
        assert "POLYMARKET_API_PASSPHRASE" in result["failures"]

    def test_invalid_signature_type_returns_fail(self):
        """sig_type=99 → FAIL with POLYMARKET_SIGNATURE_TYPE in failures."""
        client = _make_client(sig_type=99)
        result = client.check_live_credential_readiness()
        assert result["status"] == "FAIL"
        failure_str = " ".join(str(f) for f in result["failures"])
        assert "POLYMARKET_SIGNATURE_TYPE" in failure_str

    def test_valid_signature_types_0_1_2_pass(self):
        """sig_type in {0, 1, 2} all pass."""
        for sig in (0, 1, 2):
            client = _make_client(sig_type=sig)
            result = client.check_live_credential_readiness()
            assert result["status"] == "OK", f"sig_type={sig} should pass"

    def test_multiple_failures_all_listed(self):
        """Multiple missing credentials → all reported in failures list."""
        client = _make_client(private_key="", funder="", api_key="")
        result = client.check_live_credential_readiness()
        assert result["status"] == "FAIL"
        failures = result["failures"]
        assert "POLYMARKET_PRIVATE_KEY" in failures
        assert "POLYMARKET_FUNDER" in failures
        assert "POLYMARKET_API_KEY" in failures

    def test_fail_instructions_mention_env_file(self):
        """Instructions must tell operator to fix .env file."""
        client = _make_client(private_key="")
        result = client.check_live_credential_readiness()
        assert ".env" in result["instructions"]

    def test_fail_instructions_mention_approve_usdc(self):
        """Instructions must mention USDC allowance approval as a follow-up step."""
        client = _make_client(private_key="")
        result = client.check_live_credential_readiness()
        assert "allowance" in result["instructions"].lower()

    def test_fail_instructions_mention_verify_mode(self):
        """Instructions must direct operator to rerun verify mode."""
        client = _make_client(private_key="")
        result = client.check_live_credential_readiness()
        assert "verify" in result["instructions"].lower()

    def test_result_has_required_keys(self):
        """Result dict must contain status, failures, instructions, approve_required."""
        client = _make_client()
        result = client.check_live_credential_readiness()
        for key in ("status", "failures", "instructions", "approve_required"):
            assert key in result, f"Missing key: {key}"

    def test_no_network_call_made(self):
        """check_live_credential_readiness must not touch _client or make network calls."""
        client = _make_client()
        # _client is None — any access would raise AttributeError or similar
        client._client = None
        # Must not raise
        result = client.check_live_credential_readiness()
        assert result["status"] == "OK"


# ---------------------------------------------------------------------------
# Tests: check_allowance_status with needed param (B1)
# ---------------------------------------------------------------------------

class TestCheckAllowanceStatusNeeded:
    """Verify allowance check properly evaluates needed amount."""

    def test_zero_allowance_returns_missing(self):
        """allowance=0 → MISSING regardless of needed."""
        client = _make_client()
        client.get_balance_allowance = MagicMock(return_value={"balance": 5.0, "allowance": 0.0})
        result = client.check_allowance_status(needed=0.10)
        assert result["status"] == "MISSING"
        assert result["approve_required"] is True
        assert "approve" in result["message"].lower()

    def test_allowance_below_needed_returns_insufficient(self):
        """allowance < needed → INSUFFICIENT (not just MISSING)."""
        client = _make_client()
        client.get_balance_allowance = MagicMock(return_value={"balance": 5.0, "allowance": 0.05})
        result = client.check_allowance_status(needed=0.10)
        assert result["status"] == "INSUFFICIENT"
        assert result["approve_required"] is True

    def test_allowance_exactly_equal_needed_returns_ok(self):
        """allowance == needed (within epsilon) → OK."""
        client = _make_client()
        client.get_balance_allowance = MagicMock(return_value={"balance": 5.0, "allowance": 0.10})
        result = client.check_allowance_status(needed=0.10)
        assert result["status"] == "OK"
        assert result["approve_required"] is False

    def test_allowance_above_needed_returns_ok(self):
        """allowance >> needed → OK."""
        client = _make_client()
        client.get_balance_allowance = MagicMock(return_value={"balance": 5.0, "allowance": 100.0})
        result = client.check_allowance_status(needed=0.10)
        assert result["status"] == "OK"

    def test_needed_zero_with_positive_allowance_returns_ok(self):
        """needed=0 with any positive allowance → OK (default no-needed mode)."""
        client = _make_client()
        client.get_balance_allowance = MagicMock(return_value={"balance": 5.0, "allowance": 1.0})
        result = client.check_allowance_status(needed=0.0)
        assert result["status"] == "OK"

    def test_result_includes_needed_field(self):
        """Result must include the 'needed' field for operator visibility."""
        client = _make_client()
        client.get_balance_allowance = MagicMock(return_value={"balance": 5.0, "allowance": 100.0})
        result = client.check_allowance_status(needed=0.50)
        assert "needed" in result
        assert result["needed"] == 0.50


# ---------------------------------------------------------------------------
# Tests: verify_account_readiness integrates credential check (B4)
# ---------------------------------------------------------------------------

class TestVerifyAccountReadinessCredentials:
    """Verify that verify_account_readiness surfaces credential and allowance state."""

    def _make_trader_with_mocked_client(self, credential_status="OK", allowance_status="OK"):
        """Build a minimal trader with mocked client for verify testing."""
        from polymarket.trader import PolymarketTrader

        trader = PolymarketTrader.__new__(PolymarketTrader)
        trader.settings = MagicMock()
        trader.settings.paper_trading = False
        trader.settings.polymarket_api_key = "key"
        trader.settings.polymarket_api_secret = MagicMock()
        trader.settings.polymarket_api_secret.get_secret_value.return_value = "secret"
        trader.settings.polymarket_private_key = MagicMock()
        trader.settings.polymarket_private_key.get_secret_value.return_value = "0x" + "b" * 64
        trader.settings.polymarket_funder = "0xabc"
        trader.settings.polymarket_proxy_wallet = ""
        trader.settings.polymarket_host = "https://clob.polymarket.com"
        trader.settings.polymarket_chain_id = 137
        trader.settings.polymarket_ws_url = ""
        trader.settings.bankroll_floor = 5.0
        trader.settings.micro_survival_min_position_size = 0.10

        mock_client = MagicMock()
        mock_client.check_live_credential_readiness.return_value = {
            "status": credential_status,
            "failures": [] if credential_status == "OK" else ["POLYMARKET_PRIVATE_KEY"],
            "instructions": "Fix .env and rerun verify",
            "approve_required": credential_status != "OK",
        }
        mock_client.check_allowance_status.return_value = {
            "status": allowance_status,
            "balance": 5.0,
            "allowance": 10.0 if allowance_status == "OK" else 0.0,
            "needed": 0.10,
            "message": "OK" if allowance_status == "OK" else "MISSING",
            "approve_required": allowance_status != "OK",
        }
        mock_client.verify_signing_capability.return_value = {
            "status": "OK", "has_signer": True, "has_builder": True, "sig_type": 0,
            "message": "OK",
        }
        trader.client = mock_client
        trader._connected = False  # simulate no network
        trader._balance_wallet_address = None
        trader._balance_source = "unverified"

        return trader

    def _run_verify(self, trader):
        """Patch trader internals that require heavy setup and call verify_account_readiness."""
        from utils.position_tracker import PositionTracker
        tracker = PositionTracker()
        trader.tracker = tracker
        trader.bankroll_state = MagicMock()
        trader.bankroll_state.current_bankroll_for_sizing = 10.0
        trader.bankroll_state.current_cash_balance = 10.0
        trader._update_bankroll_state = MagicMock(return_value=MagicMock())
        trader._sync_sizing_bankroll = MagicMock()
        trader._record_balance_snapshot = MagicMock()
        trader._fetch_live_balance_snapshot = MagicMock(side_effect=RuntimeError("no_network"))
        trader._refresh_token_ids = MagicMock()
        trader._real_token_ids = {}
        trader._market_token_meta = {}
        trader._select_markets = MagicMock(return_value=[])
        trader.client.connect = MagicMock(side_effect=RuntimeError("no_network"))
        trader.client.get_positions = MagicMock(return_value=[])
        trader.client.get_open_orders = MagicMock(return_value=[])
        return trader.verify_account_readiness()

    def test_credentials_section_present_in_report(self):
        """verify_account_readiness must include a 'credentials' key."""
        trader = self._make_trader_with_mocked_client()
        report = self._run_verify(trader)
        assert "credentials" in report

    def test_approve_instruction_in_wallet_section(self):
        """verify output wallet section must include approve_instruction."""
        trader = self._make_trader_with_mocked_client(allowance_status="MISSING")
        report = self._run_verify(trader)
        wallet = report.get("wallet", {})
        assert "approve_instruction" in wallet
        instruction = wallet["approve_instruction"]
        assert isinstance(instruction, str)
        assert len(instruction) > 0

    def test_missing_allowance_instruction_mentions_polymarket_ui(self):
        """Approve instruction must mention Polymarket UI (no automated Web3 approve)."""
        trader = self._make_trader_with_mocked_client(allowance_status="MISSING")
        report = self._run_verify(trader)
        instruction = report.get("wallet", {}).get("approve_instruction", "")
        # Must NOT claim automatic approval
        assert "approve()" not in instruction.lower() or "not implemented" in instruction.lower()
        # Must tell user to act manually
        assert "manual" in instruction.lower() or "polymarket" in instruction.lower() or "ui" in instruction.lower()



# ---------------------------------------------------------------------------
# Tests: Settings validation (B4)
# ---------------------------------------------------------------------------

class TestSettingsLiveValidation:
    """Verify Settings model raises ValidationError when live credentials missing."""

    def _live_overrides(self, **overrides) -> dict:
        """Build minimum live settings overrides."""
        base = {
            "paper_trading": False,
            "polymarket_private_key": "0x" + "c" * 64,
            "polymarket_funder": "0xabc123",
            "polymarket_api_key": "mykey",
            "polymarket_api_secret": "mysecret",
            "polymarket_api_passphrase": "mypass",
            "polymarket_signature_type": 0,
        }
        base.update(overrides)
        return base

    def _build_settings(self, **overrides):
        """Build Settings with init_kwargs, bypassing .env."""
        from config.settings import Settings
        return Settings.model_validate(self._live_overrides(**overrides))

    def test_missing_private_key_raises(self):
        """live mode + no private key → ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            self._build_settings(polymarket_private_key="")

    def test_missing_funder_raises(self):
        """live mode + no funder → ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            self._build_settings(polymarket_funder="")

    def test_missing_api_key_raises(self):
        """live mode + no api_key → ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            self._build_settings(polymarket_api_key="")

    def test_missing_api_secret_raises(self):
        """live mode + no api_secret → ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            self._build_settings(polymarket_api_secret="")

    def test_missing_api_passphrase_raises(self):
        """live mode + no api_passphrase → ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            self._build_settings(polymarket_api_passphrase="")

    def test_invalid_sig_type_raises(self):
        """live mode + sig_type=99 → ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            self._build_settings(polymarket_signature_type=99)

    def test_paper_mode_no_credential_check(self):
        """paper_trading=True → no credential validation (all fields can be empty)."""
        from config.settings import Settings
        # Should not raise even with all live credentials missing
        settings = Settings.model_validate({
            "paper_trading": True,
            "polymarket_private_key": "",
            "polymarket_funder": "",
            "polymarket_api_key": "",
            "polymarket_api_passphrase": "",
            "polymarket_signature_type": 0,
        })
        assert settings.paper_trading is True


# ---------------------------------------------------------------------------
# Tests: no live order is submitted (safety gate)
# ---------------------------------------------------------------------------

class TestNoOrderSubmission:
    """Ensure credential/allowance check methods never submit live orders."""

    def test_check_live_credential_readiness_never_calls_place_order(self):
        """check_live_credential_readiness must not touch place_limit_order."""
        client = _make_client()
        client.place_limit_order = MagicMock(side_effect=AssertionError("order submitted!"))
        # Must not raise
        result = client.check_live_credential_readiness()
        assert result is not None
        client.place_limit_order.assert_not_called()

    def test_check_allowance_status_never_calls_place_order(self):
        """check_allowance_status must not touch place_limit_order."""
        client = _make_client()
        client.get_balance_allowance = MagicMock(return_value={"balance": 1.0, "allowance": 1.0})
        client.place_limit_order = MagicMock(side_effect=AssertionError("order submitted!"))
        result = client.check_allowance_status(needed=0.10)
        assert result is not None
        client.place_limit_order.assert_not_called()
