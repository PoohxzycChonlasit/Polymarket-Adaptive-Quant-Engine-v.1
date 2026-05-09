from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ALLOWED_MODES = {
    "paper",
    "live",
    "verify",
    "polymarket",
    "polymarket-paper",
    "polymarket-realtime",
    "polymarket-backtest",
    "polymarket-5m-dashboard",
    "scalper",
    "dashboard",
    "realtime",
    "hft",
}
ALLOWED_PAPER_BALANCE_SOURCES = {"virtual", "wallet_reference"}
ALLOWED_PAPER_STARTING_BALANCE_SOURCES = {"config", "live_wallet_reference"}
ALLOWED_PAPER_WALLET_SYNC_MODES = {"initialize_only"}
TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
FALSE_VALUES = {"0", "false", "no", "off", "disabled"}
SECRET_KEYS = {"TELEGRAM_BOT_TOKEN", "POLYMARKET_PRIVATE_KEY", "POLYMARKET_API_SECRET"}


class ConfigValidationError(ValueError):
    """Raised for startup configuration errors that must block startup."""


@dataclass
class ConfigValidationResult:
    mode: str
    paper_balance_source: str
    paper_starting_balance_source: str
    paper_wallet_sync_on_start: bool
    paper_wallet_sync_mode: str
    paper_min_balance_fallback: float
    telegram_enabled_requested: bool
    telegram_enabled_effective: bool
    live_trading_enabled: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    env_present: dict[str, bool] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def _strip_inline_comment(value: str) -> str:
    """Strip inline shell comments from a .env value.

    Handles unquoted values only; quoted values have their quotes removed first
    by the caller, so this receives the raw unquoted text.
    Examples::

        wallet_reference # use real wallet  ->  wallet_reference
        virtual                             ->  virtual
    """
    # Only strip if the value is unquoted (no surrounding quotes remain)
    idx = value.find(" #")
    if idx != -1:
        return value[:idx].rstrip()
    return value


def load_env_values(env_path: str | Path = ".env", environ: dict[str, str] | None = None) -> dict[str, str]:
    values: dict[str, str] = {}
    path = Path(env_path)
    if path.exists():
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                # Strip quotes first, then strip inline comments from unquoted values
                stripped = value.strip()
                if (stripped.startswith('"') and stripped.endswith('"')) or \
                        (stripped.startswith("'") and stripped.endswith("'")):
                    # Quoted value — strip quotes; inline comments inside quotes are literal
                    value = stripped[1:-1]
                else:
                    value = _strip_inline_comment(stripped)
                if key:
                    values[key] = value
        except OSError:
            pass
    if environ is None:
        import os

        environ = dict(os.environ)
    for key, value in environ.items():
        if value is not None:
            values[str(key)] = str(value)
    return values


def _normalize_mode(mode: str | None) -> str:
    text = str(mode or "").strip().lower()
    if text in {"polymarket-paper", "polymarket-realtime"}:
        return "paper"
    return text


def _parse_bool(value: str | None, *, default: bool = False) -> tuple[bool, bool]:
    if value is None or not str(value).strip():
        return default, True
    text = str(value).strip().lower()
    if text in TRUE_VALUES:
        return True, True
    if text in FALSE_VALUES:
        return False, True
    return default, False


def _has_secret(value: str | None) -> bool:
    return bool(str(value or "").strip())


def validate_env(
    env: dict[str, str] | None = None,
    *,
    cli_mode: str | None = None,
    env_path: str | Path = ".env",
) -> ConfigValidationResult:
    values = load_env_values(env_path, env) if env is None else dict(env)
    warnings: list[str] = []
    errors: list[str] = []

    mode_raw = values.get("MODE", "")
    mode = _normalize_mode(cli_mode or mode_raw or "paper")
    if "MODE" not in values:
        warnings.append("MODE missing; using CLI/default mode")
    elif _normalize_mode(mode_raw) not in ALLOWED_MODES and _normalize_mode(mode_raw) not in {"paper"}:
        errors.append(
            "Invalid MODE={!r}; allowed values: {}".format(
                mode_raw,
                ", ".join(sorted(ALLOWED_MODES)),
            )
        )

    paper_source_raw = values.get("PAPER_BALANCE_SOURCE", "virtual")
    paper_source = str(paper_source_raw or "virtual").strip().lower()
    if paper_source not in ALLOWED_PAPER_BALANCE_SOURCES:
        warnings.append(
            "Invalid PAPER_BALANCE_SOURCE={!r}; falling back to virtual. Allowed values: {}".format(
                paper_source_raw,
                ", ".join(sorted(ALLOWED_PAPER_BALANCE_SOURCES)),
            )
        )
        paper_source = "virtual"

    starting_source_raw = values.get("PAPER_STARTING_BALANCE_SOURCE")
    if starting_source_raw is None:
        starting_source = "live_wallet_reference" if paper_source == "wallet_reference" else "config"
    else:
        starting_source = str(starting_source_raw or "config").strip().lower()
        starting_source = {
            "virtual": "config",
            "paper_virtual": "config",
            "wallet_reference": "live_wallet_reference",
        }.get(starting_source, starting_source)
    if starting_source not in ALLOWED_PAPER_STARTING_BALANCE_SOURCES:
        warnings.append(
            "Invalid PAPER_STARTING_BALANCE_SOURCE={!r}; falling back to config. Allowed values: {}".format(
                starting_source_raw,
                ", ".join(sorted(ALLOWED_PAPER_STARTING_BALANCE_SOURCES)),
            )
        )
        starting_source = "config"

    sync_on_start, sync_on_start_valid = _parse_bool(values.get("PAPER_WALLET_SYNC_ON_START"), default=True)
    if "PAPER_WALLET_SYNC_ON_START" in values and not sync_on_start_valid:
        warnings.append("Invalid PAPER_WALLET_SYNC_ON_START value; defaulting to true")
        sync_on_start = True

    sync_mode_raw = values.get("PAPER_WALLET_SYNC_MODE", "initialize_only")
    sync_mode = str(sync_mode_raw or "initialize_only").strip().lower()
    if sync_mode not in ALLOWED_PAPER_WALLET_SYNC_MODES:
        warnings.append(
            "Invalid PAPER_WALLET_SYNC_MODE={!r}; falling back to initialize_only. Allowed values: {}".format(
                sync_mode_raw,
                ", ".join(sorted(ALLOWED_PAPER_WALLET_SYNC_MODES)),
            )
        )
        sync_mode = "initialize_only"

    try:
        min_balance_fallback = max(float(values.get("PAPER_MIN_BALANCE_FALLBACK", "0.0") or 0.0), 0.0)
    except ValueError:
        warnings.append("Invalid PAPER_MIN_BALANCE_FALLBACK value; falling back to 0.0")
        min_balance_fallback = 0.0

    telegram_requested, telegram_bool_valid = _parse_bool(values.get("TELEGRAM_ENABLED"), default=False)
    if "TELEGRAM_ENABLED" not in values:
        warnings.append("TELEGRAM_ENABLED missing; Telegram will enable only when token/chat_id are configured")
        telegram_requested = _has_secret(values.get("TELEGRAM_BOT_TOKEN")) or _has_secret(values.get("TELEGRAM_CHAT_ID"))
    elif not telegram_bool_valid:
        warnings.append("Invalid TELEGRAM_ENABLED value; disabling Telegram safely")
        telegram_requested = False

    token_present = _has_secret(values.get("TELEGRAM_BOT_TOKEN"))
    chat_present = _has_secret(values.get("TELEGRAM_CHAT_ID"))
    telegram_effective = telegram_requested and token_present and chat_present
    if telegram_requested and not telegram_effective:
        warnings.append("TELEGRAM_ENABLED=true but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing; disabling Telegram")

    live_enabled, live_bool_valid = _parse_bool(values.get("LIVE_TRADING_ENABLED"), default=False)
    if "LIVE_TRADING_ENABLED" not in values:
        warnings.append("LIVE_TRADING_ENABLED missing; live orders remain disabled unless --mode live preflight passes")
    elif not live_bool_valid:
        errors.append("Invalid LIVE_TRADING_ENABLED={!r}; allowed values: true/false".format(values.get("LIVE_TRADING_ENABLED")))
        live_enabled = False

    if mode == "paper" and live_enabled:
        warnings.append("LIVE_TRADING_ENABLED=true while MODE=paper; keeping execution PAPER ONLY and live orders DISABLED")

    return ConfigValidationResult(
        mode=mode,
        paper_balance_source=paper_source,
        paper_starting_balance_source=starting_source,
        paper_wallet_sync_on_start=sync_on_start,
        paper_wallet_sync_mode=sync_mode,
        paper_min_balance_fallback=min_balance_fallback,
        telegram_enabled_requested=telegram_requested,
        telegram_enabled_effective=telegram_effective,
        live_trading_enabled=live_enabled,
        warnings=warnings,
        errors=errors,
        env_present={
            "MODE": "MODE" in values,
            "PAPER_BALANCE_SOURCE": "PAPER_BALANCE_SOURCE" in values,
            "PAPER_STARTING_BALANCE_SOURCE": "PAPER_STARTING_BALANCE_SOURCE" in values,
            "PAPER_WALLET_SYNC_ON_START": "PAPER_WALLET_SYNC_ON_START" in values,
            "PAPER_WALLET_SYNC_MODE": "PAPER_WALLET_SYNC_MODE" in values,
            "PAPER_MIN_BALANCE_FALLBACK": "PAPER_MIN_BALANCE_FALLBACK" in values,
            "TELEGRAM_ENABLED": "TELEGRAM_ENABLED" in values,
            "TELEGRAM_BOT_TOKEN": token_present,
            "TELEGRAM_CHAT_ID": chat_present,
            "LIVE_TRADING_ENABLED": "LIVE_TRADING_ENABLED" in values,
        },
    )


def validate_runtime_mode(mode: str, *, live_trading_enabled: bool = False) -> dict[str, Any]:
    runtime_mode = _normalize_mode(mode or "paper")
    if runtime_mode not in {"paper", "live", "verify"}:
        runtime_mode = "paper" if runtime_mode.startswith("polymarket") else runtime_mode
    paper = runtime_mode != "live"
    return {
        "mode": "PAPER" if paper else "LIVE",
        "execution": "PAPER ONLY" if paper else "LIVE",
        "live_orders_enabled": bool(not paper and live_trading_enabled),
        "paper": paper,
    }


def apply_validation_to_settings(settings: Any, result: ConfigValidationResult) -> None:
    settings.paper_balance_source = result.paper_balance_source
    settings.paper_starting_balance_source = result.paper_starting_balance_source
    settings.paper_wallet_sync_on_start = result.paper_wallet_sync_on_start
    settings.paper_wallet_sync_mode = result.paper_wallet_sync_mode
    settings.paper_min_balance_fallback = result.paper_min_balance_fallback
    settings.telegram_enabled = "true" if result.telegram_enabled_effective else "false"
    settings.live_trading_enabled = "true" if result.live_trading_enabled and result.mode == "live" else "false"


def build_startup_summary(settings: Any, result: ConfigValidationResult, *, mode: str | None = None) -> str:
    runtime = validate_runtime_mode(mode or result.mode, live_trading_enabled=result.live_trading_enabled)
    paper = bool(runtime["paper"])
    balance_source = "paper_virtual"
    if paper and result.paper_starting_balance_source == "live_wallet_reference" and result.paper_wallet_sync_on_start:
        balance_source = "wallet_reference_paper"
    elif not paper:
        balance_source = "clob_collateral"

    replay_available = Path("tools/replay_analyzer.py").exists()
    lines = [
        "Startup Configuration",
        f"Mode: {runtime['mode']}",
        f"Execution: {runtime['execution']}",
        f"Live Orders: {'ENABLED' if runtime['live_orders_enabled'] else 'DISABLED'}",
        f"Balance Source: {balance_source}",
        f"Paper Starting Balance Source: {result.paper_starting_balance_source}",
        f"Paper Wallet Sync On Start: {'YES' if result.paper_wallet_sync_on_start else 'NO'}",
        f"Paper Wallet Sync Mode: {result.paper_wallet_sync_mode}",
        f"Paper Min Balance Fallback: ${result.paper_min_balance_fallback:.2f}",
        f"Wallet Reference Enabled: {'YES' if paper and result.paper_starting_balance_source == 'live_wallet_reference' and result.paper_wallet_sync_on_start else 'NO'}",
        f"Telegram Enabled: {'YES' if result.telegram_enabled_effective else 'NO'}",
        f"Quant Logging: {'ENABLED' if bool(getattr(settings, 'quant_data_enabled', True)) else 'DISABLED'}",
        f"Replay Analyzer: {'AVAILABLE' if replay_available else 'MISSING'}",
        "RiskAgent: ENABLED",
        "ExitAgent: ENABLED",
    ]
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in result.warnings)
    return "\n".join(lines)


def build_paper_balance_debug_summary(
    env: dict[str, str] | None = None,
    *,
    result: ConfigValidationResult | None = None,
    mode: str | None = None,
    env_path: str | Path = ".env",
) -> str:
    """Return a secret-safe startup debug block for PAPER_BALANCE_SOURCE.

    Prints whether the raw env key was present, the effective value after
    validation, the effective sizing source label, the runtime mode, and the
    execution safety status. Never prints secrets.
    """
    if env is None:
        env = load_env_values(env_path)

    raw_present = "PAPER_BALANCE_SOURCE" in env
    raw_value = env.get("PAPER_BALANCE_SOURCE", "(not set)")

    effective_result = result
    if result is not None:
        effective = result.paper_balance_source
        effective_mode = mode or result.mode
    else:
        # Derive without a pre-computed result
        effective_result = validate_env(env, cli_mode=mode, env_path=env_path)
        effective = effective_result.paper_balance_source
        effective_mode = mode or effective_result.mode

    starting_source = (
        effective_result.paper_starting_balance_source
        if effective_result is not None
        else ("live_wallet_reference" if effective == "wallet_reference" else "config")
    )
    sync_on_start = effective_result.paper_wallet_sync_on_start if effective_result is not None else True
    sync_mode = effective_result.paper_wallet_sync_mode if effective_result is not None else "initialize_only"

    if starting_source == "live_wallet_reference" and sync_on_start:
        sizing_source = "wallet_reference_paper"
    else:
        sizing_source = "paper_virtual"

    runtime = validate_runtime_mode(effective_mode)
    lines = [
        "[PAPER_BALANCE_SOURCE DEBUG]",
        f"  Raw PAPER_BALANCE_SOURCE present: {'yes' if raw_present else 'no'}",
        f"  Raw value in env            : {raw_value if raw_present else '(not set)'}",
        f"  Effective paper_balance_source: {effective}",
        f"  Paper starting balance source : {starting_source}",
        f"  Paper wallet sync on start    : {'true' if sync_on_start else 'false'}",
        f"  Paper wallet sync mode        : {sync_mode}",
        f"  Effective sizing source       : {sizing_source}",
        f"  Mode                         : {runtime['mode']}",
        f"  Execution                    : {runtime['execution']}",
        f"  Live Orders                  : {'ENABLED' if runtime['live_orders_enabled'] else 'DISABLED'}",
    ]
    return "\n".join(lines)


def assert_no_secret_text(text: str, env: dict[str, str]) -> None:
    for key in SECRET_KEYS:
        value = str(env.get(key, "") or "")
        if value and value in text:
            raise AssertionError(f"secret leaked in startup text: {key}")
