from __future__ import annotations

from pathlib import Path

from config.settings import Settings, get_settings


def build_freqtrade_config(settings: Settings | None = None, dry_run: bool | None = None) -> dict[str, object]:
    resolved_settings = settings or get_settings()
    resolved_dry_run = resolved_settings.crypto_dry_run if dry_run is None else dry_run

    exchange_config: dict[str, object] = {
        "name": resolved_settings.crypto_exchange,
        "key": "",
        "secret": "",
        "ccxt_config": {"enableRateLimit": True},
        "ccxt_async_config": {"enableRateLimit": True},
        "pair_whitelist": resolved_settings.crypto_pairs,
        "pair_blacklist": [],
    }

    if resolved_settings.crypto_exchange == "binance":
        exchange_config["key"] = resolved_settings.binance_api_key.get_secret_value()
        exchange_config["secret"] = resolved_settings.binance_api_secret.get_secret_value()
    elif resolved_settings.crypto_exchange == "bybit":
        exchange_config["key"] = resolved_settings.bybit_api_key.get_secret_value()
        exchange_config["secret"] = resolved_settings.bybit_api_secret.get_secret_value()
    elif resolved_settings.crypto_exchange == "coinbase":
        exchange_config["key"] = resolved_settings.coinbase_api_key.get_secret_value()
        exchange_config["secret"] = resolved_settings.coinbase_api_secret.get_secret_value()
        exchange_config["password"] = resolved_settings.coinbase_api_passphrase.get_secret_value()

    return {
        "$schema": "https://schema.freqtrade.io/schema.json",
        "dry_run": resolved_dry_run,
        "dry_run_wallet": resolved_settings.account_balance,
        "stake_currency": resolved_settings.crypto_stake_currency,
        "stake_amount": "unlimited",
        "max_open_trades": resolved_settings.max_open_positions,
        "trading_mode": "spot",
        "timeframe": resolved_settings.crypto_timeframe,
        "exchange": exchange_config,
        "entry_pricing": {"price_side": "same", "use_order_book": True, "order_book_top": 1},
        "exit_pricing": {"price_side": "same", "use_order_book": True, "order_book_top": 1},
        "pairlists": [{"method": "StaticPairList"}],
        "bot_name": "polytrade_bot_scalper",
        "initial_state": "running",
        "force_entry_enable": False,
        "internals": {"process_throttle_secs": 5},
        "api_server": {
            "enabled": False,
            "listen_ip_address": "127.0.0.1",
            "listen_port": 8080,
            "verbosity": "error",
        },
        "strategy": "My5mScalper",
        "strategy_path": str(Path("crypto_scalper/freqtrade_strategies")),
    }


def write_freqtrade_config(path: Path, settings: Settings | None = None, dry_run: bool | None = None) -> Path:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_freqtrade_config(settings=settings, dry_run=dry_run)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
