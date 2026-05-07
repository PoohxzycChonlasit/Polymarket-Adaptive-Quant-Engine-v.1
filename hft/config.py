"""
hft/config.py
=============
All HFT parameters in one place. Edit here — no code changes needed.

To override at runtime, set environment variables with HFT_ prefix:
  HFT_LOOP_INTERVAL=5 python -m hft.main
"""
from __future__ import annotations

import os


def _env(key: str, default: float) -> float:
    return float(os.getenv(f"HFT_{key}", default))


def _env_int(key: str, default: int) -> int:
    return int(os.getenv(f"HFT_{key}", default))


def _env_bool(key: str, default: bool) -> bool:
    v = os.getenv(f"HFT_{key}")
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes")


# ── Loop timing ────────────────────────────────────────────────────────────────
LOOP_INTERVAL_SEC     = _env_int("LOOP_INTERVAL",     10)   # main loop cadence (s)
SIGNAL_INTERVAL_SEC   = _env_int("SIGNAL_INTERVAL",   10)   # recompute signal every N s
MIN_SECONDS_REMAINING = _env_int("MIN_SECS_REMAIN",   30)   # don't enter if < 30s left
MAX_SECONDS_TO_ENTRY  = _env_int("MAX_SECS_ENTRY",   270)   # don't enter in first 30s (< 270 left)

# ── Entry thresholds ───────────────────────────────────────────────────────────
MIN_EV                = _env("MIN_EV",       0.025)   # min expected value (2.5%)
MIN_EDGE              = _env("MIN_EDGE",     0.04)    # min edge = p_model - market_price (4%)
MIN_MOMENTUM_ABS      = _env("MIN_MOM",      0.15)    # min |3-candle momentum %| to confirm
WINDOW_DELTA_DEADBAND = _env("WD_DEADBAND",  0.05)    # ignore delta < 0.05% (flat market)

# ── Sizing & risk ──────────────────────────────────────────────────────────────
KELLY_FRACTION        = _env("KELLY_FRAC",   0.20)    # fractional Kelly multiplier
MAX_WINDOW_EXPOSURE   = _env("MAX_WIN_EXP",  0.12)    # max 12% of bankroll per window
MAX_ENTRIES_PER_WIN   = _env_int("MAX_ENTRIES", 3)    # max scale-in count per window
MIN_BET_USD           = _env("MIN_BET",      0.05)    # minimum bet in USD
MAX_BET_USD           = _env("MAX_BET",     10.00)    # maximum bet per entry in USD
DAILY_DRAWDOWN_LIMIT  = _env("MAX_DD",       0.08)    # pause if daily loss > 8%
FLOOR_BALANCE_USD     = _env("FLOOR_BAL",    5.00)    # stop all trading below this

# ── Model ──────────────────────────────────────────────────────────────────────
BRIER_GOOD_THRESHOLD  = _env("BRIER_GOOD",   0.18)    # Brier < this = increase size 10%
P_MODEL_SENSITIVITY   = _env("P_SENSITIVITY", 3.0)    # sigmoid steepness for window delta
RSI_PERIOD            = _env_int("RSI_PERIOD", 14)
MOMENTUM_CANDLES      = _env_int("MOM_CANDLES",  3)   # 3-candle momentum lookback

# ── Fees ──────────────────────────────────────────────────────────────────────
POLYMARKET_FEE        = _env("PM_FEE",       0.002)   # 0.2% taker fee (approximate)

# ── Assets ────────────────────────────────────────────────────────────────────
ACTIVE_ASSETS: list[str] = ["BTC"]  # extend to ["BTC","ETH"] when ready

# ── Logging / output ──────────────────────────────────────────────────────────
LOG_TRADES_CSV        = _env_bool("LOG_CSV",    True)
TRADES_CSV_PATH       = os.getenv("HFT_CSV_PATH", "runtime/hft_trades.csv")
DASHBOARD_REFRESH_SEC = _env_int("DASH_REFRESH",  1)

# ── Execution ─────────────────────────────────────────────────────────────────
PAPER_TRADING         = _env_bool("PAPER", True)       # override from .env at runtime
ORDER_RETRY_ATTEMPTS  = _env_int("RETRY",     3)
ORDER_RETRY_DELAY_SEC = _env_int("RETRY_DELAY", 3)
