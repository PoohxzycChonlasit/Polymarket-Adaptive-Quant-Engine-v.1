from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, EnvSettingsSource, DotEnvSettingsSource
from pydantic.fields import FieldInfo


class _CommaListEnvSource(EnvSettingsSource):
    """Extend EnvSettingsSource to accept comma-separated strings for list[str] fields."""

    def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
        if isinstance(value, str) and not value.strip().startswith("[") and not value.strip().startswith("{"):
            return value
        return super().decode_complex_value(field_name, field, value)


class _CommaListDotEnvSource(DotEnvSettingsSource):
    """Extend DotEnvSettingsSource to accept comma-separated strings for list[str] fields."""

    def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
        if isinstance(value, str) and not value.strip().startswith("[") and not value.strip().startswith("{"):
            return value
        return super().decode_complex_value(field_name, field, value)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        # Replace the default sources with our comma-aware versions.
        return (
            init_settings,
            _CommaListEnvSource(settings_cls),
            _CommaListDotEnvSource(settings_cls, dotenv_settings.env_file, dotenv_settings.env_file_encoding),
            file_secret_settings,
        )

    app_name: str = "PolyTrade Bot"
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    log_dir: str = "logs"
    verbose_scan_logs: bool = True
    verbose_model_logs: bool = True
    verbose_risk_logs: bool = True
    summary_interval_cycles: int = 5
    quant_data_enabled: bool = True
    research_data_enabled: bool = True
    quant_data_dir: str = "runtime/quant_data"
    quant_event_schema_version: str = "1.0"
    slim_decision_logging: bool = False
    # --- Hybrid Phase v1 settings ---
    hybrid_phase_v1_enabled: bool = True
    research_decision_snapshots_enabled: bool = True
    market_state_snapshots_enabled: bool = True
    lifecycle_phase_classification_enabled: bool = True
    shadow_inventory_tracking_enabled: bool = True
    quant_log_retention_days: int = 90
    market_snapshot_retention_days: int = 14
    trade_journal_retention_days: int = 3650
    compress_old_quant_logs: bool = True
    paper_trading: bool = True
    dry_run: bool = True
    paper_balance_source: str = "virtual"
    paper_starting_balance_source: Literal["config", "live_wallet_reference"] = "config"
    paper_wallet_sync_on_start: bool = True
    paper_wallet_sync_mode: Literal["initialize_only"] = "initialize_only"
    paper_min_balance_fallback: float = 0.0
    wallet_reference_refresh_seconds: int = 300
    show_wallet_reference_balance: bool = True
    telegram_enabled: str = "true"
    live_trading_enabled: str = "false"

    option_d_shadow_enabled: bool = False
    delta_shadow_enabled: bool = False
    shadow_telemetry_enabled: bool = False
    shadow_filters_active: list[str] = [
        "block_btc_shadow",
        "block_normal_vol_shadow",
        "combined_broad_shadow",
        "combined_conservative_shadow"
    ]
    sl_activation_delay_seconds: float = 30.0
    sl_emergency_stop_pct: float = 0.30

    telegram_bot_token: SecretStr = Field(default=SecretStr(""))
    telegram_chat_id: SecretStr = Field(default=SecretStr(""))
    telegram_alert_cooldown_seconds: int = 300
    telegram_summary_interval_minutes: int = 60

    ai_timeout_seconds: int = 8

    polymarket_host: str = "https://clob.polymarket.com"
    polymarket_gamma_url: str = "https://gamma-api.polymarket.com"
    polymarket_chain_id: int = 137
    polymarket_private_key: SecretStr = Field(default=SecretStr(""))
    polymarket_funder: str = ""
    polymarket_proxy_wallet: str = ""
    polymarket_signature_type: int = 0
    # API Keys (For Proxy Wallets)
    polymarket_api_key: str = ""
    polymarket_api_secret: SecretStr | None = None
    polymarket_api_passphrase: str = ""
    
    polymarket_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/"
    alchemy_url: str = ""  # Polygon RPC (Alchemy) for on-chain balance queries

    crypto_exchange: Literal["binance", "bybit", "coinbase"] = "binance"
    crypto_timeframe: str = "5m"
    crypto_pairs: list[str] = Field(default_factory=lambda: ["BTC/USDT", "ETH/USDT"])
    crypto_stake_currency: str = "USDT"
    crypto_dry_run: bool = True
    binance_api_key: SecretStr = Field(default=SecretStr(""))
    binance_api_secret: SecretStr = Field(default=SecretStr(""))
    bybit_api_key: SecretStr = Field(default=SecretStr(""))
    bybit_api_secret: SecretStr = Field(default=SecretStr(""))
    coinbase_api_key: SecretStr = Field(default=SecretStr(""))
    coinbase_api_secret: SecretStr = Field(default=SecretStr(""))
    coinbase_api_passphrase: SecretStr = Field(default=SecretStr(""))

    account_balance: float = 10.0
    max_risk_per_trade: float = 0.005       # Tiered: starts at 0.5% for Micro (<$10)
    max_daily_drawdown: float = 0.10        # Hard limit: stop trading if daily loss > 10%
    default_stop_loss_pct: float = 0.04     # Default SL 4% (dynamic per volatility)
    default_take_profit_pct: float = 0.15   # TP 15% (~3.75:1 RR)
    max_open_positions: int = 3
    max_total_exposure: float = 0.30        # Total exposure across all open positions <= 30%
    kelly_fraction_cap: float = 0.25        # Max Kelly fraction cap (Growth tier ceiling)
    daily_profit_target: float = 0.15       # Target 15% / day
    snipe_min_edge: float = 0.30            # Min relative misprice to trigger snipe entry
    stall_exit_seconds: int = 180           # Exit underwater position after N seconds (MR needs time to play out)

    arb_display_enabled: bool = True        # Scan/display YES+NO locked-profit arbitrage
    arb_auto_execute: bool = False          # Execution must be explicitly enabled
    arb_min_net_edge: float = 0.010         # Minimum net edge after buffers before terminal marks BUY_BOTH_ARB
    arb_min_profit_usdc: float = 0.02       # Paper-mode minimum estimated profit
    arb_live_min_profit_usdc: float = 0.05  # Live-mode minimum estimated profit
    arb_fee_buffer: float = 0.002           # Conservative fee/protocol buffer per share
    arb_slippage_buffer: float = 0.003      # Conservative execution/slippage buffer per share
    arb_fail_risk_buffer: float = 0.003     # Extra buffer for second-leg/unwind risk
    arb_max_leg_spread: float = 0.03        # Skip arb if either YES/NO orderbook spread is wider than this
    arb_entry_min_seconds_remaining: int = 90
    arb_force_cancel_seconds_remaining: int = 60
    arb_leg_fill_timeout_sec: float = 3.0
    arb_second_leg_retry: int = 2
    arb_unwind_on_partial_fill: bool = True
    arb_max_active_markets_small_bankroll: int = 1

    # ── Take Profit & Let Profit Run (v3.1) ────────────────────────────────────
    tp_partial_pct: float = 0.05            # Partial TP at 5% unrealized profit (sell 50%)
    tp_full_pct: float = 0.10               # Full TP at 10% unrealized profit (sell 100%)
    let_profit_run: bool = True             # If True, delay full TP when delta is strong
    let_profit_run_min_seconds: int = 60    # Min seconds remaining to allow profit run

    # ── Panic Sell Slippage Guard (v3.3) ─────────────────────────────────────
    panic_sell_max_slippage: float = 0.08   # Hold to settlement if (fair_value - best_bid) > this
    panic_sell_delta_threshold: float = 5.0 # Min oracle delta ($) to consider position weak/uncertain

    # ── v3.2: Advanced Trading Optimization ───────────────────────────────────
    entry_min_seconds_remaining: int = 30   # Legacy minimum; execution_entry_cutoff_seconds is the hard safety gate
    execution_entry_cutoff_seconds: int = 90
    adaptive_entry_cutoff_enabled: bool = True
    adaptive_entry_cutoff_seconds: int = 45
    adaptive_entry_hard_block_seconds: int = 45
    adaptive_entry_max_orderbook_age_ms: int = 1000
    adaptive_entry_max_oracle_age_ms: int = 5000
    adaptive_entry_max_decision_latency_ms: int = 2000
    adaptive_entry_max_cycle_duration_ms: int = 2500
    adaptive_entry_max_spread: float = 0.06
    orderbook_warmup_pending_threshold: int = 3
    orderbook_empty_recovery_enabled: bool = True
    empty_book_recovery_research_mode: bool = False
    orderbook_empty_recovery_retries: int = 2
    orderbook_empty_recovery_delay_ms: int = 75
    orderbook_empty_recovery_max_total_ms: int = 300
    clob_orderbook_retry_count: int = 1
    clob_orderbook_retry_backoff_ms: int = 150
    clob_rate_limit_cooldown_seconds: int = 30
    clob_market_error_cooldown_seconds: int = 10
    clob_circuit_breaker_threshold: int = 3
    clob_circuit_breaker_window_seconds: int = 60
    execution_force_exit_seconds: int = 60
    exit_agent_entry_cutoff_seconds: int = 45
    exit_agent_cancel_entries_seconds: int = 35
    exit_agent_force_exit_seconds: int = 25
    exit_agent_residual_sweep_seconds: int = 15
    exit_agent_emergency_flatten_seconds: int = 10
    max_feed_age_seconds: float = 10.0
    execution_take_profit_pct: float = 0.10
    execution_stop_loss_pct: float = 0.08
    max_active_positions_per_market: int = 1
    max_entries_per_market: int = 1
    max_risk_per_market: float = 0.06
    micro_survival_bankroll_threshold: float = 100.0
    micro_survival_min_position_size: float = 0.05
    micro_survival_risk_fraction: float = 0.0025
    micro_adaptive_timing_enabled: bool = True
    micro_hard_close_floor_seconds: int = 35
    micro_adaptive_window_min_seconds: int = 35
    close_order_retry_attempts: int = 3
    close_order_retry_delay_seconds: float = 0.5
    min_shares_per_order: int = 1           # User Requested: allow minimum 1 share (dynamic 1-5)
    dynamic_tp_enabled: bool = True         # Auto-adjust TP% when entry price is better than expected
    dynamic_tp_boost_factor: float = 0.5    # TP boost = advantage% × this factor
    api_retry_attempts: int = 3             # Number of retries on API failure
    api_retry_backoff_base: float = 1.0     # Exponential backoff base (seconds)
    api_circuit_breaker_threshold: int = 5  # Consecutive failures before circuit opens
    api_circuit_breaker_cooldown: int = 30  # Seconds to wait when circuit is open

    # ── Counter-momentum strategy parameters (v3.3) ────────────────────────────
    # Change any of these → must re-run `--days 60` backtest → Sharpe>0.8, WinRate>51%, MaxDD<20%
    strategy_mom_lower: float = 0.30       # fallback static momentum lower bound (% ) — used when ATR unavailable
    strategy_mom_upper: float = 1.00       # fallback static momentum upper bound — above this, no reversion
    strategy_score_threshold: float = 0.55 # minimum composite score to enter (reduced to increase frequency)
    strategy_min_rsi: float = 35.0         # RSI lower bound (below = oversold, skip NO)
    strategy_max_rsi: float = 78.0         # RSI upper bound (above = overbought, skip YES)
    strategy_min_vol_ratio: float = 0.40   # minimum volume vs 20-bar mean
    # Window Delta thresholds
    strategy_wd_strong_up: float = 0.010
    strategy_wd_weak_up: float = 0.002

    # ── ATR-Based Dynamic Momentum Threshold (v3.3) ────────────────────────────
    # Replaces the static 0.45–1.00% momentum band with a volatility-regime-aware band.
    # trigger = abs(momentum_pct) > atr_multiplier * (5m_ATR / price * 100)
    atr_period: int = 14                    # ATR averaging period (bars)
    atr_multiplier: float = 0.60            # Multiplier: 0.6 = trigger at 60% of ATR move (more frequent)
    atr_mom_lower_floor: float = 0.15       # Minimum threshold — never trade below this even in calm markets
    atr_mom_upper_cap: float = 1.50         # Maximum threshold cap — filter out black-swan extremes

    # ── 1H EMA Higher-Timeframe Trend Filter (v3.3) ────────────────────────────
    # Penalizes signals that fight the dominant hourly trend (EMA on 1H candles).
    htf_ema_period: int = 21                # 1H EMA period (21 bars ≈ 21 hours)
    htf_ema_penalty: float = 0.15          # Score reduction when signal contradicts 1H EMA direction

    # ── v3.4: Multi-Strategy Engine ────────────────────────────────────────────
    active_strategy: Literal["sniper", "reversion", "trend", "auto"] = "auto"

    # Sniper Strategy Params (Deep Value)
    sniper_zscore_threshold: float = 2.0    # Reduced from 2.5: Catch 2-sigma deviations
    sniper_max_entry_price: float = 0.45    # Allow entries up to $0.45
    sniper_imbalance_threshold: float = 0.70 # Require strong orderbook support
    
    # Trend Following Strategy Params
    trend_adx_threshold: float = 20.0       # ADX must be > 20 to confirm trend (Standard threshold)
    trend_ema_fast: int = 9                 # Fast EMA
    trend_ema_slow: int = 21                # Slow EMA

    # ── Tiered bankroll protection ─────────────────────────────────────────────
    # Safety floor: STOP ALL TRADING if balance drops below this
    bankroll_floor: float = 5.00            # $5.00 hard floor
    max_single_trade_risk: float = 0.03     # Hard cap: never risk > 3% in any single trade
    bankroll_tier_v2_enabled: bool = True
    bankroll_tier_hysteresis_pct: float = 0.05

    bankroll_tiers: list[dict[str, Any]] = Field(default_factory=lambda: [
        # risk scales aggressively as bankroll grows — micro is protected, growth bets near HARD_CAP
        {"min_balance": 0.0,     "max_balance": 10.0,          "label": "micro",        "description": "Micro Bankroll",  "max_risk_pct": 0.005,  "kelly_fraction": 0.10, "min_bet": 0.05, "stop_loss_pct": 0.90},
        {"min_balance": 10.0,    "max_balance": 100.0,         "label": "small",        "description": "Small Bankroll",  "max_risk_pct": 0.010,  "kelly_fraction": 0.15, "min_bet": 0.10, "stop_loss_pct": 0.85},
        {"min_balance": 100.0,   "max_balance": 1000.0,        "label": "conservative", "description": "Conservative",   "max_risk_pct": 0.015,  "kelly_fraction": 0.20, "min_bet": 0.50, "stop_loss_pct": 0.80},
        {"min_balance": 1000.0,  "max_balance": 10000.0,       "label": "balanced",     "description": "Balanced",       "max_risk_pct": 0.020,  "kelly_fraction": 0.25, "min_bet": 2.00, "stop_loss_pct": 0.75},
        {"min_balance": 10000.0, "max_balance": float("inf"),  "label": "growth",       "description": "Growth",         "max_risk_pct": 0.025,  "kelly_fraction": 0.30, "min_bet": 5.00, "stop_loss_pct": 0.70},
    ])

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level={v!r} must be one of {sorted(valid)}")
        return upper

    @field_validator("paper_balance_source")
    @classmethod
    def validate_paper_balance_source(cls, v: str) -> str:
        normalized = str(v or "virtual").strip().lower()
        return normalized if normalized in {"virtual", "wallet_reference"} else "virtual"

    @field_validator("paper_starting_balance_source")
    @classmethod
    def validate_paper_starting_balance_source(cls, v: str) -> str:
        normalized = str(v or "config").strip().lower()
        aliases = {
            "virtual": "config",
            "paper_virtual": "config",
            "wallet_reference": "live_wallet_reference",
        }
        normalized = aliases.get(normalized, normalized)
        return normalized if normalized in {"config", "live_wallet_reference"} else "config"

    @field_validator("paper_min_balance_fallback")
    @classmethod
    def validate_paper_min_balance_fallback(cls, v: float) -> float:
        return max(float(v), 0.0)

    @field_validator("account_balance")
    @classmethod
    def validate_account_balance(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"account_balance={v} must be positive")
        return v

    @field_validator("max_risk_per_trade")
    @classmethod
    def validate_max_risk(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"max_risk_per_trade={v} must be positive")
        if v > 0.03:
            raise ValueError(
                f"max_risk_per_trade={v:.4f} exceeds hard cap 0.03 (3%) — refusing to start. "
                "Set MAX_RISK_PER_TRADE <= 0.03 in .env"
            )
        return v

    @field_validator("max_daily_drawdown")
    @classmethod
    def validate_drawdown(cls, v: float) -> float:
        if not (0.01 <= v <= 0.50):
            raise ValueError(
                f"max_daily_drawdown={v:.3f} must be between 0.01 (1%) and 0.50 (50%)"
            )
        return v

    @field_validator(
        "execution_take_profit_pct",
        "execution_stop_loss_pct",
        "max_risk_per_market",
        "adaptive_entry_max_spread",
        "arb_min_net_edge",
        "arb_min_profit_usdc",
        "arb_live_min_profit_usdc",
        "arb_fee_buffer",
        "arb_slippage_buffer",
        "arb_fail_risk_buffer",
        "arb_max_leg_spread",
        "micro_survival_risk_fraction",
    )
    @classmethod
    def validate_execution_fraction(cls, v: float) -> float:
        if not (0 < v <= 1.0):
            raise ValueError(f"execution risk fraction={v:.3f} must be within (0, 1].")
        return v

    @field_validator("micro_survival_bankroll_threshold")
    @classmethod
    def validate_micro_survival_threshold(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("micro_survival_bankroll_threshold must be positive.")
        return v

    @field_validator("micro_survival_min_position_size")
    @classmethod
    def validate_micro_survival_min_position_size(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("micro_survival_min_position_size must be positive.")
        return v

    @field_validator("bankroll_tier_hysteresis_pct")
    @classmethod
    def validate_bankroll_tier_hysteresis_pct(cls, v: float) -> float:
        if not (0.0 <= v <= 0.50):
            raise ValueError("bankroll_tier_hysteresis_pct must be between 0.0 and 0.50.")
        return v

    @field_validator(
        "execution_entry_cutoff_seconds",
        "adaptive_entry_cutoff_seconds",
        "adaptive_entry_hard_block_seconds",
        "adaptive_entry_max_orderbook_age_ms",
        "adaptive_entry_max_oracle_age_ms",
        "adaptive_entry_max_decision_latency_ms",
        "adaptive_entry_max_cycle_duration_ms",
        "orderbook_warmup_pending_threshold",
        "orderbook_empty_recovery_retries",
        "orderbook_empty_recovery_delay_ms",
        "orderbook_empty_recovery_max_total_ms",
        "micro_hard_close_floor_seconds",
        "micro_adaptive_window_min_seconds",
        "clob_orderbook_retry_count",
        "clob_orderbook_retry_backoff_ms",
        "clob_rate_limit_cooldown_seconds",
        "clob_market_error_cooldown_seconds",
        "clob_circuit_breaker_threshold",
        "clob_circuit_breaker_window_seconds",
        "execution_force_exit_seconds",
        "exit_agent_entry_cutoff_seconds",
        "exit_agent_cancel_entries_seconds",
        "exit_agent_force_exit_seconds",
        "exit_agent_residual_sweep_seconds",
        "exit_agent_emergency_flatten_seconds",
        "max_active_positions_per_market",
        "max_entries_per_market",
        "close_order_retry_attempts",
        "arb_entry_min_seconds_remaining",
        "arb_force_cancel_seconds_remaining",
        "arb_max_active_markets_small_bankroll",
        "summary_interval_cycles",
        "wallet_reference_refresh_seconds",
    )
    @classmethod
    def validate_positive_int(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"execution integer setting={v} must be positive.")
        return v

    @field_validator("crypto_pairs", mode="before")
    @classmethod
    def parse_crypto_pairs(cls, value: object) -> object:
        if isinstance(value, str):
            return [pair.strip() for pair in value.split(",") if pair.strip()]
        return value

    @model_validator(mode="after")
    def validate_live_trading_requirements(self) -> "Settings":
        if not self.paper_trading:
            if not self.polymarket_private_key.get_secret_value():
                raise ValueError(
                    "POLYMARKET_PRIVATE_KEY must be set in .env when PAPER_TRADING=false"
                )
            if not self.polymarket_funder:
                raise ValueError(
                    "POLYMARKET_FUNDER must be set in .env when PAPER_TRADING=false"
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
