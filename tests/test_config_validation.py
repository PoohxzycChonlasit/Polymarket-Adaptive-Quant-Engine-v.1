from __future__ import annotations

from types import SimpleNamespace

from utils.config_validator import (
    apply_validation_to_settings,
    assert_no_secret_text,
    build_paper_balance_debug_summary,
    build_startup_summary,
    load_env_values,
    validate_env,
    validate_runtime_mode,
)


def _env(**overrides: str) -> dict[str, str]:
    values = {
        "MODE": "paper",
        "PAPER_BALANCE_SOURCE": "virtual",
        "TELEGRAM_ENABLED": "false",
        "LIVE_TRADING_ENABLED": "false",
    }
    values.update(overrides)
    return values


def _settings(**overrides):
    values = {
        "paper_balance_source": "virtual",
        "paper_starting_balance_source": "config",
        "paper_wallet_sync_on_start": True,
        "paper_wallet_sync_mode": "initialize_only",
        "paper_min_balance_fallback": 0.0,
        "telegram_enabled": "true",
        "live_trading_enabled": "false",
        "quant_data_enabled": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


# ── Original tests (preserved) ────────────────────────────────────────────────

def test_invalid_mode_is_rejected() -> None:
    result = validate_env(_env(MODE="rocket"))

    assert not result.ok
    assert "Invalid MODE" in result.errors[0]
    assert "paper" in result.errors[0]
    assert "live" in result.errors[0]


def test_invalid_paper_balance_source_falls_back_safely() -> None:
    result = validate_env(_env(PAPER_BALANCE_SOURCE="wallet_live"))
    settings = _settings(paper_balance_source="wallet_live")

    apply_validation_to_settings(settings, result)

    assert result.ok
    assert result.paper_balance_source == "virtual"
    assert settings.paper_balance_source == "virtual"
    assert any("Invalid PAPER_BALANCE_SOURCE" in warning for warning in result.warnings)


def test_telegram_missing_token_disables_telegram() -> None:
    result = validate_env(_env(TELEGRAM_ENABLED="true", TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID="123"))
    settings = _settings()

    apply_validation_to_settings(settings, result)

    assert result.ok
    assert result.telegram_enabled_requested is True
    assert result.telegram_enabled_effective is False
    assert settings.telegram_enabled == "false"
    assert any("disabling Telegram" in warning for warning in result.warnings)


def test_paper_mode_never_enables_live_orders() -> None:
    result = validate_env(_env(MODE="paper", LIVE_TRADING_ENABLED="true"))
    runtime = validate_runtime_mode(result.mode, live_trading_enabled=result.live_trading_enabled)
    settings = _settings()
    apply_validation_to_settings(settings, result)

    assert runtime["mode"] == "PAPER"
    assert runtime["execution"] == "PAPER ONLY"
    assert runtime["live_orders_enabled"] is False
    assert settings.live_trading_enabled == "false"
    assert any("keeping execution PAPER ONLY" in warning for warning in result.warnings)


def test_startup_summary_renders_expected_fields() -> None:
    result = validate_env(_env(
        PAPER_BALANCE_SOURCE="wallet_reference",
        TELEGRAM_ENABLED="true",
        TELEGRAM_BOT_TOKEN="123456:secret-token",
        TELEGRAM_CHAT_ID="987654",
    ))
    summary = build_startup_summary(_settings(), result, mode="paper")

    assert "Mode: PAPER" in summary
    assert "Execution: PAPER ONLY" in summary
    assert "Live Orders: DISABLED" in summary
    assert "Balance Source: wallet_reference_paper" in summary
    assert "Paper Starting Balance Source: live_wallet_reference" in summary
    assert "Paper Wallet Sync On Start: YES" in summary
    assert "Paper Wallet Sync Mode: initialize_only" in summary
    assert "Wallet Reference Enabled: YES" in summary
    assert "Telegram Enabled: YES" in summary
    assert "Quant Logging: ENABLED" in summary
    assert "Replay Analyzer: AVAILABLE" in summary
    assert "RiskAgent: ENABLED" in summary
    assert "ExitAgent: ENABLED" in summary


def test_startup_summary_does_not_print_secrets() -> None:
    env = _env(
        TELEGRAM_ENABLED="true",
        TELEGRAM_BOT_TOKEN="123456:super-secret-token",
        TELEGRAM_CHAT_ID="987654",
    )
    result = validate_env(env)
    summary = build_startup_summary(_settings(), result, mode="paper")

    assert "super-secret-token" not in summary
    assert_no_secret_text(summary, env)


# ── New targeted tests ────────────────────────────────────────────────────────

def test_wallet_reference_env_produces_effective_wallet_reference() -> None:
    """PAPER_BALANCE_SOURCE=wallet_reference in env -> effective value is wallet_reference."""
    result = validate_env(_env(PAPER_BALANCE_SOURCE="wallet_reference"))

    assert result.ok
    assert result.paper_balance_source == "wallet_reference"


def test_validate_env_wallet_reference_applied_to_settings() -> None:
    """apply_validation_to_settings propagates wallet_reference to the settings object."""
    result = validate_env(_env(PAPER_BALANCE_SOURCE="wallet_reference"))
    settings = _settings(paper_balance_source="virtual")

    apply_validation_to_settings(settings, result)

    assert settings.paper_balance_source == "wallet_reference"
    assert settings.paper_starting_balance_source == "live_wallet_reference"
    assert settings.paper_wallet_sync_on_start is True
    assert settings.paper_wallet_sync_mode == "initialize_only"


def test_new_paper_balance_config_keys_are_supported() -> None:
    result = validate_env(_env(
        PAPER_STARTING_BALANCE_SOURCE="live_wallet_reference",
        PAPER_WALLET_SYNC_ON_START="false",
        PAPER_WALLET_SYNC_MODE="initialize_only",
        PAPER_MIN_BALANCE_FALLBACK="7.5",
    ))

    assert result.ok
    assert result.paper_starting_balance_source == "live_wallet_reference"
    assert result.paper_wallet_sync_on_start is False
    assert result.paper_wallet_sync_mode == "initialize_only"
    assert result.paper_min_balance_fallback == 7.5


def test_load_env_values_strips_inline_comments() -> None:
    """Inline # comments must not be included in parsed values."""
    import os
    import tempfile

    content = "PAPER_BALANCE_SOURCE=wallet_reference # use real wallet\nMODE=paper\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp = f.name
    try:
        values = load_env_values(tmp, environ={})
        assert values["PAPER_BALANCE_SOURCE"] == "wallet_reference", (
            f"Expected 'wallet_reference', got {values['PAPER_BALANCE_SOURCE']!r}"
        )
    finally:
        os.unlink(tmp)


def test_cli_paper_mode_does_not_override_paper_balance_source_env() -> None:
    """Passing cli_mode='paper' must not reset PAPER_BALANCE_SOURCE to virtual."""
    result = validate_env(
        _env(PAPER_BALANCE_SOURCE="wallet_reference"),
        cli_mode="paper",
    )

    assert result.ok
    assert result.paper_balance_source == "wallet_reference"


def test_paper_balance_debug_summary_shows_correct_fields() -> None:
    """build_paper_balance_debug_summary shows raw presence, effective value, sizing source, execution."""
    env = _env(PAPER_BALANCE_SOURCE="wallet_reference")
    result = validate_env(env)
    debug = build_paper_balance_debug_summary(env=env, result=result, mode="paper")

    assert "Raw PAPER_BALANCE_SOURCE present: yes" in debug
    assert "Effective paper_balance_source: wallet_reference" in debug
    assert "Paper starting balance source : live_wallet_reference" in debug
    assert "Paper wallet sync mode        : initialize_only" in debug
    assert "Effective sizing source       : wallet_reference_paper" in debug
    assert "Execution                    : PAPER ONLY" in debug
    assert "Live Orders                  : DISABLED" in debug


def test_paper_balance_debug_summary_not_set_shows_no() -> None:
    """When PAPER_BALANCE_SOURCE is absent, debug summary shows 'no' and falls back to virtual."""
    env_no_source = {"MODE": "paper", "TELEGRAM_ENABLED": "false", "LIVE_TRADING_ENABLED": "false"}
    result = validate_env(env_no_source)
    debug = build_paper_balance_debug_summary(env=env_no_source, result=result, mode="paper")

    assert "Raw PAPER_BALANCE_SOURCE present: no" in debug
    assert "Effective paper_balance_source: virtual" in debug
    assert "Paper starting balance source : config" in debug
    assert "Effective sizing source       : paper_virtual" in debug


def test_paper_balance_debug_summary_does_not_leak_secrets() -> None:
    """The debug summary must never print API keys or Telegram tokens."""
    env = _env(
        PAPER_BALANCE_SOURCE="wallet_reference",
        TELEGRAM_BOT_TOKEN="987654:very-secret-telegram",
        POLYMARKET_API_SECRET="my-api-secret-key",
        POLYMARKET_PRIVATE_KEY="0xdeadbeef1234",
    )
    result = validate_env(env)
    debug = build_paper_balance_debug_summary(env=env, result=result, mode="paper")

    assert "very-secret-telegram" not in debug
    assert "my-api-secret-key" not in debug
    assert "0xdeadbeef1234" not in debug
    assert_no_secret_text(debug, env)
