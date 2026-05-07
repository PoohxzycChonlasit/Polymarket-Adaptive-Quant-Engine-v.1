from __future__ import annotations

import logging

import main


def test_missing_env_variable_triggers_warning(monkeypatch):
    for key in (
        "POLYMARKET_API_KEY",
        "POLYMARKET_API_SECRET",
        "POLYMARKET_API_PASSPHRASE",
        "PRIVATE_KEY",
        "POLYMARKET_PRIVATE_KEY",
        "WALLET_ADDRESS",
        "POLYMARKET_PROXY_WALLET",
        "POLYMARKET_FUNDER",
        "RPC_URL",
        "ALCHEMY_URL",
        "CHAIN_ID",
        "POLYMARKET_CHAIN_ID",
    ):
        monkeypatch.delenv(key, raising=False)

    report = main._build_env_verification({})

    assert "missing_env" in report["warnings"]
    assert "missing_env" in report["critical"]


def test_wallet_mismatch_triggers_critical(monkeypatch):
    loaded = {
        "POLYMARKET_API_KEY": "key_1234567890",
        "POLYMARKET_API_SECRET": "secret_1234567890",
        "POLYMARKET_API_PASSPHRASE": "passphrase_1234567890",
        "POLYMARKET_PRIVATE_KEY": "0x" + "1" * 64,
        "WALLET_ADDRESS": "0x0000000000000000000000000000000000000001",
        "POLYMARKET_CHAIN_ID": "137",
    }
    monkeypatch.setattr(main, "_derive_private_key_address", lambda _: ("0x0000000000000000000000000000000000000002", "OK"))

    report = main._build_env_verification(loaded)

    assert "wallet_mismatch" in report["warnings"]
    assert "wallet_mismatch" in report["critical"]


def test_secrets_are_masked_in_env_report(monkeypatch):
    secret = "sk_live_full_secret_value_123456789"
    private_key = "0x" + "2" * 64
    loaded = {
        "POLYMARKET_API_KEY": secret,
        "POLYMARKET_API_SECRET": "super_secret_value_abcdef",
        "POLYMARKET_API_PASSPHRASE": "passphrase_secret_abcdef",
        "POLYMARKET_PRIVATE_KEY": private_key,
        "WALLET_ADDRESS": "0x0000000000000000000000000000000000000002",
        "POLYMARKET_CHAIN_ID": "137",
    }
    monkeypatch.setattr(main, "_derive_private_key_address", lambda _: ("0x0000000000000000000000000000000000000002", "OK"))

    report = main._build_env_verification(loaded)
    rendered = " ".join(str(item["value"]) for item in report["checks"])

    assert secret not in rendered
    assert private_key not in rendered
    assert "sk_liv" in rendered
    assert "6789" in rendered


def test_verify_mode_remains_read_only(monkeypatch):
    class FakeTrader:
        def verify_account_readiness(self):
            return {
                "api": {"auth": "OK", "latency_ms": 1, "endpoint": "OK", "websocket": "SKIPPED", "api_key": "OK", "api_secret": "OK"},
                "wallet": {"signer": "OK", "allowance": "OK"},
                "balance": {"cash": 1.0, "open_value": 0.0, "equity": 1.0, "sizing_bankroll": 1.0, "status": "MATCH"},
                "positions": {"count": 0, "reconciliation": "SAFE", "classification": "FLAT", "reason": ""},
                "markets": [],
                "model": [],
                "warnings": [],
                "fatal": [],
            }

        def place_limit_order(self, *args, **kwargs):  # pragma: no cover - must not be called
            raise AssertionError("verify mode placed an order")

    monkeypatch.setattr(main, "_load_dotenv_explicit", lambda: {})
    monkeypatch.setattr(main, "_validate_dependencies_for_mode", lambda mode: True)
    monkeypatch.setattr(
        main,
        "_build_env_verification",
        lambda _: {
            "checks": [],
            "warnings": [],
            "critical": [],
            "wallet": {
                "configured": "0x0000000000000000000000000000000000000001",
                "derived": "0x0000000000000000000000000000000000000001",
                "derived_status": "OK",
                "match": "TRUE",
                "network": "Polygon",
                "chain_id": "137",
                "rpc_status": "SKIPPED",
            },
        },
    )

    import polymarket.trader

    monkeypatch.setattr(polymarket.trader, "PolymarketTrader", FakeTrader)

    assert main.run_verify_mode() == 0


def test_missing_py_clob_client_warning(caplog, monkeypatch):
    report = [
        {"label": "py-clob-client", "status": "MISSING", "install": "pip install py-clob-client", "features": ("orderbook", "bid/ask", "spread", "live order execution")},
        {"label": "web3", "status": "OK", "install": "pip install web3", "features": ()},
        {"label": "eth-account", "status": "OK", "install": "pip install eth-account", "features": ()},
    ]
    monkeypatch.setattr(main, "_build_dependency_report", lambda: report)

    with caplog.at_level(logging.WARNING):
        assert main._validate_dependencies_for_mode("paper") is True

    text = caplog.text
    assert "[MISSING DEPENDENCY]" in text
    assert "py-clob-client not installed" in text
    assert "pip install py-clob-client" in text
    assert "orderbook" in text


def test_missing_web3_warning(caplog, monkeypatch):
    report = [
        {"label": "py-clob-client", "status": "OK", "install": "pip install py-clob-client", "features": ()},
        {"label": "web3", "status": "MISSING", "install": "pip install web3", "features": ("wallet balance", "USDC balance", "allowance", "Polygon RPC")},
        {"label": "eth-account", "status": "OK", "install": "pip install eth-account", "features": ()},
    ]
    monkeypatch.setattr(main, "_build_dependency_report", lambda: report)

    with caplog.at_level(logging.WARNING):
        assert main._validate_dependencies_for_mode("paper") is True

    text = caplog.text
    assert "web3 not installed" in text
    assert "pip install web3" in text
    assert "USDC balance" in text


def test_live_mode_blocked_when_dependency_missing(monkeypatch):
    report = [
        {"label": "py-clob-client", "status": "MISSING", "install": "pip install py-clob-client", "features": ("orderbook",)},
        {"label": "web3", "status": "OK", "install": "pip install web3", "features": ()},
        {"label": "eth-account", "status": "OK", "install": "pip install eth-account", "features": ()},
    ]
    monkeypatch.setattr(main, "_build_dependency_report", lambda: report)

    assert main._validate_dependencies_for_mode("live") is False


def test_paper_mode_warning_but_allowed(monkeypatch):
    report = [
        {"label": "py-clob-client", "status": "MISSING", "install": "pip install py-clob-client", "features": ("orderbook",)},
        {"label": "web3", "status": "MISSING", "install": "pip install web3", "features": ("wallet balance",)},
        {"label": "eth-account", "status": "OK", "install": "pip install eth-account", "features": ()},
    ]
    monkeypatch.setattr(main, "_build_dependency_report", lambda: report)

    assert main._validate_dependencies_for_mode("paper") is True


def test_verify_mode_explains_missing_features(caplog, monkeypatch):
    report = [
        {"label": "py-clob-client", "status": "MISSING", "install": "pip install py-clob-client", "features": ("orderbook", "bid/ask", "spread", "live order execution")},
        {"label": "web3", "status": "MISSING", "install": "pip install web3", "features": ("wallet balance", "USDC balance", "allowance", "Polygon RPC")},
        {"label": "eth-account", "status": "OK", "install": "pip install eth-account", "features": ()},
    ]
    monkeypatch.setattr(main, "_build_dependency_report", lambda: report)

    with caplog.at_level(logging.INFO):
        assert main._validate_dependencies_for_mode("verify") is False

    text = caplog.text
    assert "[DEPENDENCIES]" in text
    assert "py-clob-client=MISSING" in text
    assert "web3=MISSING" in text
    assert "live order execution" in text
    assert "Polygon RPC" in text
