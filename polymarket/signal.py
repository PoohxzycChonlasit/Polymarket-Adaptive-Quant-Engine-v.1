"""
Realtime counter-momentum signal for Polymarket 5-min markets.

Mirrors _compute_signal() in backtester_5m.py exactly — same thresholds, same
indicator math, same scoring. Uses Binance WebSocket feed (<1 ms latency) instead
of Coinbase REST (5–15 s delay).

Usage:
    from polymarket.signal import compute_realtime_signal
    result = compute_realtime_signal("BTC", imbalance=0.15)
    # result.side == "YES" | "NO" | "SKIP"
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import get_settings
from polymarket.market_feed import get_feed
from polymarket.models.quant_indicators import get_quant_feed
from polymarket.regime_diagnostics import classify_candle_regime

LOGGER = logging.getLogger(__name__)

# ── Indicator periods ─────────────────────────────────────────────────────────
_RSI_LEN  = 14
_VOL_BARS = 20
_WARMUP   = 27  # covers RSI(14), ATR(14), MACD(26), BB(20), volume_mean(20) + warmup buffer

# ── Strategy thresholds — loaded from settings (edit via .env, then re-run 60d backtest)
_s                   = get_settings()
_MIN_RSI             = _s.strategy_min_rsi
_MAX_RSI             = _s.strategy_max_rsi
_MIN_VOL_RATIO       = _s.strategy_min_vol_ratio
_MOM_LOWER           = _s.strategy_mom_lower      # fallback when ATR unavailable
_MOM_UPPER           = _s.strategy_mom_upper      # fallback when ATR unavailable
_THRESHOLD           = _s.strategy_score_threshold
# ATR dynamic threshold parameters — all adjustable via settings / .env
_ATR_PERIOD          = _s.atr_period
_ATR_MULTIPLIER      = _s.atr_multiplier
_ATR_MOM_LOWER_FLOOR = _s.atr_mom_lower_floor
_ATR_MOM_UPPER_CAP   = _s.atr_mom_upper_cap
# 1H EMA higher-timeframe filter
_HTF_EMA_PERIOD  = _s.htf_ema_period
_HTF_EMA_PENALTY = _s.htf_ema_penalty
del _s

# ── Validated backtest metrics — auto-loaded from latest_metrics.json ─────────
# Written by backtester_5m.export() after every --days 60 run.
# Falls back to hardcoded values if no run has been performed yet.
_METRICS_PATH = Path("backtest_results/polymarket_5m/latest_metrics.json")


def _load_validated_metrics() -> tuple[float, float]:
    """Load two-sided (YES+NO) win rate and edge from the latest backtest run."""
    try:
        if _METRICS_PATH.exists():
            data     = json.loads(_METRICS_PATH.read_text(encoding="utf-8"))
            win_rate = float(data.get("win_rate", 0.0))
            edge     = float(data.get("edge", 0.0))
            n_trades = int(data.get("n_trades", 0))
            sides    = data.get("sides", "")
            if sides == "YES+NO" and n_trades >= 100 and 0.40 <= win_rate <= 0.80:
                LOGGER.info(
                    "[Signal] Loaded validated metrics from %s: win_rate=%.3f edge=%.4f n=%d",
                    _METRICS_PATH, win_rate, edge, n_trades,
                )
                return win_rate, edge
    except Exception as exc:
        LOGGER.warning("[Signal] Failed to load latest_metrics.json: %s — using defaults", exc)
    return 0.559, 0.059  # original hardcoded fallback


BACKTEST_WIN_RATE, BACKTEST_EDGE = _load_validated_metrics()


@dataclass
class SignalResult:
    asset:               str
    side:                str    # "YES" | "NO" | "SKIP"
    score:               float  # composite signal score (0.50–0.95)
    momentum_pct:        float  # 3-candle price momentum at decision time
    rsi:                 float
    vol_ratio:           float
    skip_reason:         str
    signal_name:         str = field(default="UNKNOWN_SIGNAL")
    signal_reason:       str = field(default="unknown_reason")
    strategy:            str = field(default="")         # "sniper" | "reversion" | "trend"
    zscore:              float = field(default=0.0)
    adx:                 float = field(default=0.0)
    orderbook_imbalance: float = field(default=0.0)  # [-1,+1]: positive = more bids (bullish)
    log_volatility:      float = field(default=0.0)
    cvd_60s_norm:        float = field(default=0.0)
    vpin_score:          float = field(default=0.0)
    market_regime:       str = field(default="UNKNOWN")
    bullish_probability: float = field(default=0.5)
    bearish_probability: float = field(default=0.5)
    trend_strength:      float = field(default=0.0)
    reversal_risk:       float = field(default=0.0)
    volatility_score:    float = field(default=0.0)
    compression_score:   float = field(default=0.0)
    regime_reason:       str = field(default="")
    indicator_evidence:  str = field(default="")


def _build_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute RSI14, ATR14, volume_mean20 — mirrors backtester_5m._build_indicators()."""
    df = df.copy()
    df["volume_mean"] = df["volume"].rolling(window=_VOL_BARS).mean()

    # RSI
    delta  = df["close"].diff()
    gains  = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_g  = gains.ewm(alpha=1 / _RSI_LEN, adjust=False).mean()
    avg_l  = losses.ewm(alpha=1 / _RSI_LEN, adjust=False).mean()
    rs     = avg_g / avg_l.replace(0.0, 1e-10)
    df["rsi"] = 100.0 - (100.0 / (1.0 + rs))

    # ATR (Average True Range) — feeds the dynamic momentum threshold.
    # TR = max(high-low, |high-prev_close|, |low-prev_close|)
    prev_close = df["close"].shift(1)
    true_range = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"]  - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = true_range.ewm(span=_ATR_PERIOD, adjust=False).mean()

    # ── ML data-collection features (not used in rule-based scoring) ───────
    df["log_ret"]      = np.log(df["close"] / df["close"].shift(1).replace(0, np.nan))
    df["volatility"]   = df["log_ret"].rolling(window=_VOL_BARS).std()
    df["log_volatility"] = np.log(df["volatility"] + 1e-8)

    # VPIN proxy — collected for ML training only
    range_hl       = (df["high"] - df["low"]).replace(0.0, 1e-8)
    df["buy_vol"]  = df["volume"] * (df["close"] - df["low"]) / range_hl
    df["sell_vol"] = df["volume"] * (df["high"] - df["close"]) / range_hl
    df["vpin_score"] = (
        abs(df["buy_vol"].rolling(12).sum() - df["sell_vol"].rolling(12).sum())
        / (df["volume"].rolling(12).sum() + 1e-8)
    )

    # ── v3.4 Multi-Strategy Quant Indicators ──────────────────────────────────
    
    s = get_settings()
    
    # 1. Z-Score (Sniper Strategy) — Detects extreme price deviation from 50-bar mean
    mean_50 = df["close"].rolling(window=50).mean()
    std_50 = df["close"].rolling(window=50).std().replace(0, 1e-8)
    df["z_score"] = (df["close"] - mean_50) / std_50
    
    # 2. EMA 9 and 21 (Trend Strategy)
    df["ema_fast"] = df["close"].ewm(span=s.trend_ema_fast, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=s.trend_ema_slow, adjust=False).mean()
    
    # 3. ADX 14 (Trend Strength)
    # +DM = high - prev_high, -DM = prev_low - low
    up_move = df["high"] - df["high"].shift(1)
    down_move = df["low"].shift(1) - df["low"]
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    tr_smooth = true_range.ewm(alpha=1/14, adjust=False).mean()
    plus_di = 100 * (pd.Series(plus_dm).ewm(alpha=1/14, adjust=False).mean() / tr_smooth)
    minus_di = 100 * (pd.Series(minus_dm).ewm(alpha=1/14, adjust=False).mean() / tr_smooth)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-8)
    df["adx"] = dx.ewm(alpha=1/14, adjust=False).mean()

    # 4. MACD (Moving Average Convergence Divergence)
    ema_12 = df["close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema_12 - ema_26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # 5. Bollinger Bands (20-bar, 2-std dev)
    sma_20 = df["close"].rolling(window=20).mean()
    std_20 = df["close"].rolling(window=20).std().replace(0, 1e-8)
    df["bb_upper"] = sma_20 + (2 * std_20)
    df["bb_lower"] = sma_20 - (2 * std_20)
    df["bb_middle"] = sma_20

    return df.dropna().reset_index(drop=True)


def _build_htf_trend(df_1h: pd.DataFrame) -> tuple[str, float]:
    """
    Compute 1H EMA trend direction for the higher-timeframe context filter.

    Returns
    -------
    trend : "bullish" | "bearish" | "neutral"
    ema_value : float  (0.0 when insufficient data)
    """
    if df_1h.empty or len(df_1h) < _HTF_EMA_PERIOD + 1:
        return "neutral", 0.0
    ema_series  = df_1h["close"].ewm(span=_HTF_EMA_PERIOD, adjust=False).mean()
    last_close  = float(df_1h["close"].iloc[-1])
    last_ema    = float(ema_series.iloc[-1])
    if last_close > last_ema:
        return "bullish", last_ema
    if last_close < last_ema:
        return "bearish", last_ema
    return "neutral", last_ema


def compute_realtime_signal(asset: str, imbalance: float = 0.0) -> SignalResult:
    """
    Fetch Binance 5-min candles and compute counter-momentum signal.

    v3.3 additions vs v3.2:
      - Dynamic momentum threshold: replaces static 0.45–1.00% with ATR-derived band.
      - 1H EMA trend filter: penalises signals that fight the dominant hourly trend.
    """
    feed  = get_feed()
    quant = get_quant_feed().get_quant_data(asset)

    if not feed.is_ready(asset):
        return SignalResult(
            asset=asset, side="SKIP", score=0.0, momentum_pct=0.0,
            rsi=50.0, vol_ratio=0.0, skip_reason="feed_not_ready",
            orderbook_imbalance=imbalance,
            signal_name="NO_SIGNAL", signal_reason="feed_not_ready",
        )

    df    = feed.get_candles_df(asset, "5m")
    df_1m = feed.get_candles_df(asset, "1m")

    if df.empty or len(df) < _WARMUP:
        return SignalResult(
            asset=asset, side="SKIP", score=0.0, momentum_pct=0.0,
            rsi=50.0, vol_ratio=0.0, skip_reason=f"only_{len(df)}_candles",
            orderbook_imbalance=imbalance,
            signal_name="NO_SIGNAL", signal_reason="insufficient_candles",
        )

    df  = _build_indicators(df)
    idx = len(df) - 1
    regime_payload = classify_candle_regime(recent_1m=df_1m, recent_5m=df).to_payload()

    if idx < 3:
        return SignalResult(
            asset=asset, side="SKIP", score=0.0, momentum_pct=0.0,
            rsi=50.0, vol_ratio=0.0, skip_reason="insufficient_after_indicators",
            orderbook_imbalance=imbalance,
            signal_name="NO_SIGNAL", signal_reason="insufficient_after_indicators",
        )

    s = get_settings()
    
    # Extract zscore and adx from the latest row for UI reporting
    zscore_val = float(df.iloc[idx].get("z_score", 0.0))
    adx_val = float(df.iloc[idx].get("adx", 0.0))

    # Check 1m invert rule
    last_1m_bullish = None
    if not df_1m.empty and len(df_1m) >= 2:
        last_1m_bullish = float(df_1m.iloc[-1]["close"]) > float(df_1m.iloc[-1]["open"])

    # ── 1H EMA higher-timeframe trend ─────────────────────────────────────────
    htf_trend = "neutral"
    try:
        df_1h = feed.get_candles_df(asset, "1h")
        htf_trend, htf_ema_val = _build_htf_trend(df_1h)
        LOGGER.debug("[HTF] %s 1H EMA(%d)=%.2f trend=%s", asset, _HTF_EMA_PERIOD, htf_ema_val, htf_trend)
    except Exception as exc:
        pass

    # Evaluate Strategies
    strategies = {}
    
    if s.active_strategy in ("reversion", "auto"):
        strategies["reversion"] = _compute_reversion_signal(asset, df, idx, df_1m, quant, imbalance, htf_trend, last_1m_bullish)
    if s.active_strategy in ("sniper", "auto"):
        strategies["sniper"] = _compute_sniper_signal(asset, df, idx, imbalance, last_1m_bullish)
    if s.active_strategy in ("trend", "auto"):
        strategies["trend"] = _compute_trend_signal(asset, df, idx, imbalance, htf_trend)

    # Pick the best signal (highest score >= threshold)
    best_strategy = "SKIP"
    best_signal = SignalResult(
        asset=asset, side="SKIP", score=0.0, momentum_pct=0.0,
        rsi=50.0, vol_ratio=0.0, skip_reason="no_strategy_met_threshold",
        orderbook_imbalance=imbalance,
        zscore=zscore_val, adx=adx_val,
        signal_name="NO_SIGNAL", signal_reason="no_strategy_met_threshold",
    )
    
    for name, sig in strategies.items():
        if sig.side != "SKIP" and sig.score > best_signal.score:
            best_signal = sig
            best_strategy = name

    if best_signal.side != "SKIP":
        LOGGER.info("[STRATEGY] %s selected %s strategy with score %.2f", asset, best_strategy.upper(), best_signal.score)
        best_signal.strategy = best_strategy

    best_signal.market_regime = str(regime_payload.get("market_regime", "UNKNOWN") or "UNKNOWN")
    best_signal.bullish_probability = float(regime_payload.get("bullish_probability", 0.5) or 0.5)
    best_signal.bearish_probability = float(regime_payload.get("bearish_probability", 0.5) or 0.5)
    best_signal.trend_strength = float(regime_payload.get("trend_strength", 0.0) or 0.0)
    best_signal.reversal_risk = float(regime_payload.get("reversal_risk", 0.0) or 0.0)
    best_signal.volatility_score = float(regime_payload.get("volatility_score", 0.0) or 0.0)
    best_signal.compression_score = float(regime_payload.get("compression_score", 0.0) or 0.0)
    best_signal.regime_reason = str(regime_payload.get("regime_reason", "") or "")
    best_signal.indicator_evidence = str(regime_payload.get("indicator_evidence", "") or "")
    return best_signal


def _compute_reversion_signal(
    asset: str, df: pd.DataFrame, idx: int, df_1m: pd.DataFrame, quant: dict, imbalance: float, htf_trend: str, last_1m_bullish: bool | None
) -> SignalResult:
    """Original Mean Reversion / Counter-Momentum Strategy."""
    row       = df.iloc[idx]
    prev_row  = df.iloc[idx - 1]
    prev2_row = df.iloc[idx - 2]

    rsi_val   = float(row["rsi"])
    rsi_ok    = _MIN_RSI <= rsi_val <= _MAX_RSI
    vol_ratio = float(row["volume"] / row["volume_mean"]) if row["volume_mean"] > 0 else 0.0
    vol_ok    = vol_ratio >= _MIN_VOL_RATIO

    log_volatility = float(row.get("log_volatility", 0.0))
    vpin_score     = float(row.get("vpin_score", 0.0))

    # ── CVD (Cumulative Volume Delta over last 60 × 1m bars) ─────────────────
    cvd_60s_norm = 0.0
    if not df_1m.empty and "taker_buy_volume" in df_1m.columns and len(df_1m) >= 60:
        taker_buy    = df_1m["taker_buy_volume"].iloc[-60:]
        total_vol    = df_1m["volume"].iloc[-60:]
        cvd_60s_norm = float((2 * taker_buy - total_vol).sum() / (total_vol.sum() + 1e-8))

    ls_ratio = quant.get("long_short_ratio", 0.0)

    # ── 3-candle momentum ──
    price_now    = float(row["open"])
    price_3ago   = float(df.iloc[idx - 3]["close"])
    momentum_pct = (price_now - price_3ago) / max(price_3ago, 1.0) * 100.0

    prev_bullish  = float(prev_row["close"])  > float(prev_row["open"])
    prev2_bullish = float(prev2_row["close"]) > float(prev2_row["open"])
    consecutive_up   = prev_bullish and prev2_bullish
    consecutive_down = not prev_bullish and not prev2_bullish

    # ── Dynamic momentum threshold from ATR ──
    # Converts ATR (price units) to a % of current open price, then scales by
    # _ATR_MULTIPLIER. This widens the entry band in calm markets and narrows it
    # in volatile ones — preventing over-trading noise in BTC news events.
    atr_val = float(row.get("atr", 0.0))
    if atr_val > 0 and price_now > 0:
        atr_pct   = atr_val / price_now * 100.0
        mom_lower = max(_ATR_MULTIPLIER * atr_pct, _ATR_MOM_LOWER_FLOOR)
        mom_upper = min(
            mom_lower * (_MOM_UPPER / max(_MOM_LOWER, 1e-6)),
            _ATR_MOM_UPPER_CAP,
        )
    else:
        mom_lower = _MOM_LOWER   # static fallback
        mom_upper = _MOM_UPPER

    # ── Counter-momentum scoring ───────────────────────────────────────────────
    yes_score = 0.0
    no_score  = 0.0
    abs_mom   = abs(momentum_pct)

    # ── MACD & Bollinger Band confluences — extracted once ──────────────────
    macd_hist_val  = float(row.get("macd_hist", 0.0))
    macd_bull      = macd_hist_val > 0  # positive histogram = bullish momentum
    macd_bear      = macd_hist_val < 0
    close_val      = float(row["close"])
    bb_lower_val   = float(row.get("bb_lower", 0.0))
    bb_upper_val   = float(row.get("bb_upper", 0.0))
    near_bb_lower  = bb_lower_val > 0 and close_val <= bb_lower_val * 1.002  # within 0.2% of lower band
    near_bb_upper  = bb_upper_val > 0 and close_val >= bb_upper_val * 0.998  # within 0.2% of upper band

    if mom_lower <= abs_mom < mom_upper:
        if momentum_pct > mom_lower:
            # Strong up move → mean reversion → bet NO
            no_score += 0.50
            if abs_mom > 0.60:           no_score += 0.10
            if consecutive_up:           no_score += 0.15
            if rsi_ok and rsi_val > 60:  no_score += 0.10
            if vol_ok:                   no_score += 0.10
            if cvd_60s_norm > 0.10:      no_score += 0.05  # crowd still buying → strengthens fade
            if ls_ratio > 1.2:           no_score += 0.05  # longs crowded → reversal more likely
            # ── MACD: falling histogram confirms reversal conviction ──
            if macd_bear:                no_score += 0.05
            # ── BB: price touching upper band = exhaustion zone ──
            if near_bb_upper:            no_score += 0.07
        else:
            # Strong down move → mean reversion → bet YES
            yes_score += 0.50
            if abs_mom > 0.60:           yes_score += 0.10
            if consecutive_down:         yes_score += 0.15
            if rsi_ok and rsi_val < 45:  yes_score += 0.10
            if vol_ok:                   yes_score += 0.10
            if cvd_60s_norm < -0.10:     yes_score += 0.05  # crowd still selling → bounce likely
            if 0 < ls_ratio < 0.8:       yes_score += 0.05  # shorts crowded → squeeze risk
            # ── MACD: rising histogram confirms bounce conviction ──
            if macd_bull:                yes_score += 0.05
            # ── BB: price touching lower band = deep value / snap-back zone ──
            if near_bb_lower:            yes_score += 0.07

    # Orderbook imbalance confirmation (+0.05 when >10% imbalance aligns with direction)
    if abs(imbalance) > 0.10:
        if imbalance > 0:   # more bid volume → bullish → supports YES (counter-down)
            yes_score += 0.05
        else:               # more ask volume → bearish → supports NO (counter-up)
            no_score  += 0.05

    # ── 1H EMA trend filter — penalise signals fighting the hourly trend ───────
    # Applied before Anti-Invert so the macro filter takes precedence over micro noise.
    # Only penalises when the score is already non-zero to avoid spurious adjustments.
    if no_score > yes_score and htf_trend == "bullish":
        # Betting price will drop, but hourly trend is up → reduce conviction
        no_score -= _HTF_EMA_PENALTY
        LOGGER.info("[HTF_FILTER] %s NO score penalised %.2f (1H=bullish)", asset, _HTF_EMA_PENALTY)
    elif yes_score > no_score and htf_trend == "bearish":
        yes_score -= _HTF_EMA_PENALTY
        LOGGER.info("[HTF_FILTER] %s YES score penalised %.2f (1H=bearish)", asset, _HTF_EMA_PENALTY)

    # ── Anti-Invert Filter ──
    if last_1m_bullish is not None:
        if yes_score > no_score and not last_1m_bullish:
            yes_score -= 0.10
        elif no_score > yes_score and last_1m_bullish:
            no_score -= 0.10

    # ── Final decision ──
    if yes_score >= _THRESHOLD and yes_score >= no_score:
        return SignalResult(
            asset=asset, side="YES", score=yes_score,
            momentum_pct=momentum_pct, rsi=rsi_val, vol_ratio=vol_ratio,
            skip_reason="", orderbook_imbalance=imbalance,
            log_volatility=log_volatility, cvd_60s_norm=cvd_60s_norm, vpin_score=vpin_score,
            zscore=float(row.get("z_score", 0.0)), adx=float(row.get("adx", 0.0)),
            signal_name="reversion", signal_reason="reversion_yes_threshold_met",
        )
    elif no_score >= _THRESHOLD and no_score > yes_score:
        return SignalResult(
            asset=asset, side="NO", score=no_score,
            momentum_pct=momentum_pct, rsi=rsi_val, vol_ratio=vol_ratio,
            skip_reason="", orderbook_imbalance=imbalance,
            log_volatility=log_volatility, cvd_60s_norm=cvd_60s_norm, vpin_score=vpin_score,
            zscore=float(row.get("z_score", 0.0)), adx=float(row.get("adx", 0.0)),
            signal_name="reversion", signal_reason="reversion_no_threshold_met",
        )

    return SignalResult(
        asset=asset, side="SKIP", score=max(yes_score, no_score),
        momentum_pct=momentum_pct, rsi=rsi_val, vol_ratio=vol_ratio,
        skip_reason=(
            f"yes={yes_score:.2f}|no={no_score:.2f}|mom={momentum_pct:.3f}%"
            f"|band=[{mom_lower:.3f},{mom_upper:.3f}]|htf={htf_trend}"
        ),
        orderbook_imbalance=imbalance,
        log_volatility=log_volatility, cvd_60s_norm=cvd_60s_norm, vpin_score=vpin_score,
        zscore=float(row.get("z_score", 0.0)), adx=float(row.get("adx", 0.0)),
        signal_name="NO_SIGNAL", signal_reason="reversion_threshold_not_met",
    )

def _compute_sniper_signal(
    asset: str, df: pd.DataFrame, idx: int, imbalance: float, last_1m_bullish: bool | None
) -> SignalResult:
    """Sniper (Deep Value) Strategy — enters on extreme z-score deviations."""
    s = get_settings()
    row = df.iloc[idx]

    rsi_val   = float(row["rsi"])
    vol_ratio = float(row["volume"] / row["volume_mean"]) if row["volume_mean"] > 0 else 0.0
    zscore    = float(row.get("z_score", 0.0))

    yes_score = 0.0
    no_score  = 0.0

    if zscore <= -s.sniper_zscore_threshold:
        # Price far below 50-bar mean → deep value → bet YES (bounce)
        yes_score += 0.50
        if zscore <= -(s.sniper_zscore_threshold + 0.5): yes_score += 0.10
        if rsi_val < 40:                                  yes_score += 0.10
        if vol_ratio >= 0.60:                             yes_score += 0.08
        if imbalance > s.sniper_imbalance_threshold - 1:  yes_score += 0.05
        if last_1m_bullish:                               yes_score += 0.05

    elif zscore >= s.sniper_zscore_threshold:
        # Price far above 50-bar mean → overextended → bet NO (fade)
        no_score += 0.50
        if zscore >= (s.sniper_zscore_threshold + 0.5):    no_score += 0.10
        if rsi_val > 60:                                    no_score += 0.10
        if vol_ratio >= 0.60:                               no_score += 0.08
        if imbalance < -(s.sniper_imbalance_threshold - 1): no_score += 0.05
        if last_1m_bullish is False:                        no_score += 0.05

    threshold = get_settings().strategy_score_threshold

    if yes_score >= threshold and yes_score >= no_score:
        return SignalResult(
            asset=asset, side="YES", score=yes_score,
            momentum_pct=0.0, rsi=rsi_val, vol_ratio=vol_ratio,
            skip_reason="", orderbook_imbalance=imbalance,
            zscore=zscore, adx=float(row.get("adx", 0.0)),
            strategy="sniper",
            signal_name="sniper", signal_reason="sniper_yes_extreme_zscore",
        )
    if no_score >= threshold and no_score > yes_score:
        return SignalResult(
            asset=asset, side="NO", score=no_score,
            momentum_pct=0.0, rsi=rsi_val, vol_ratio=vol_ratio,
            skip_reason="", orderbook_imbalance=imbalance,
            zscore=zscore, adx=float(row.get("adx", 0.0)),
            strategy="sniper",
            signal_name="sniper", signal_reason="sniper_no_extreme_zscore",
        )
    return SignalResult(
        asset=asset, side="SKIP", score=max(yes_score, no_score),
        momentum_pct=0.0, rsi=rsi_val, vol_ratio=vol_ratio,
        skip_reason=f"sniper: zscore={zscore:.2f} yes={yes_score:.2f} no={no_score:.2f}",
        orderbook_imbalance=imbalance,
        zscore=zscore, adx=float(row.get("adx", 0.0)),
        signal_name="NO_SIGNAL", signal_reason="sniper_threshold_not_met",
    )


def _compute_trend_signal(
    asset: str, df: pd.DataFrame, idx: int, imbalance: float, htf_trend: str
) -> SignalResult:
    """Trend Following Strategy — enters when ADX confirms a strong directional move."""
    s = get_settings()
    row = df.iloc[idx]

    rsi_val   = float(row["rsi"])
    vol_ratio = float(row["volume"] / row["volume_mean"]) if row["volume_mean"] > 0 else 0.0
    adx_val   = float(row.get("adx", 0.0))
    ema_fast  = float(row.get("ema_fast", 0.0))
    ema_slow  = float(row.get("ema_slow", 0.0))
    macd_hist = float(row.get("macd_hist", 0.0))

    yes_score = 0.0
    no_score  = 0.0

    if adx_val >= s.trend_adx_threshold:
        if ema_fast > ema_slow:
            # Uptrend confirmed → bet YES
            yes_score += 0.45
            if adx_val >= s.trend_adx_threshold + 10:  yes_score += 0.10
            if macd_hist > 0:                           yes_score += 0.07
            if htf_trend == "bullish":                  yes_score += 0.08
            if rsi_val > 50:                            yes_score += 0.05
            if imbalance > 0.10:                        yes_score += 0.05
        elif ema_fast < ema_slow:
            # Downtrend confirmed → bet NO
            no_score += 0.45
            if adx_val >= s.trend_adx_threshold + 10:  no_score += 0.10
            if macd_hist < 0:                           no_score += 0.07
            if htf_trend == "bearish":                  no_score += 0.08
            if rsi_val < 50:                            no_score += 0.05
            if imbalance < -0.10:                       no_score += 0.05

    threshold = get_settings().strategy_score_threshold

    if yes_score >= threshold and yes_score >= no_score:
        return SignalResult(
            asset=asset, side="YES", score=yes_score,
            momentum_pct=0.0, rsi=rsi_val, vol_ratio=vol_ratio,
            skip_reason="", orderbook_imbalance=imbalance,
            zscore=float(row.get("z_score", 0.0)), adx=adx_val,
            strategy="trend",
            signal_name="trend", signal_reason="trend_yes_adx_ema_confirmed",
        )
    if no_score >= threshold and no_score > yes_score:
        return SignalResult(
            asset=asset, side="NO", score=no_score,
            momentum_pct=0.0, rsi=rsi_val, vol_ratio=vol_ratio,
            skip_reason="", orderbook_imbalance=imbalance,
            zscore=float(row.get("z_score", 0.0)), adx=adx_val,
            strategy="trend",
            signal_name="trend", signal_reason="trend_no_adx_ema_confirmed",
        )
    return SignalResult(
        asset=asset, side="SKIP", score=max(yes_score, no_score),
        momentum_pct=0.0, rsi=rsi_val, vol_ratio=vol_ratio,
        skip_reason=f"trend: adx={adx_val:.1f} ema_fast={ema_fast:.2f} ema_slow={ema_slow:.2f}",
        orderbook_imbalance=imbalance,
        zscore=float(row.get("z_score", 0.0)), adx=adx_val,
        signal_name="NO_SIGNAL", signal_reason="trend_threshold_not_met",
    )


# ── Window Delta ──────────────────────────────────────────────────────────────
# Window Delta thresholds — loaded from settings
WD_STRONG_UP   =  get_settings().strategy_wd_strong_up
WD_WEAK_UP     =  get_settings().strategy_wd_weak_up
WD_WEAK_DOWN   = -get_settings().strategy_wd_weak_up
WD_STRONG_DOWN = -get_settings().strategy_wd_strong_up

@dataclass(slots=True)
class WindowDeltaSignal:
    price_to_beat:    float
    current_price:    float
    delta_abs:        float
    delta_pct:        float
    bias:             str
    score_boost:      float
    seconds_elapsed:  int

    @property
    def is_bullish(self) -> bool:
        return self.bias in ("strong_up", "weak_up")

    @property
    def is_bearish(self) -> bool:
        return self.bias in ("strong_down", "weak_down")

    def log_line(self) -> str:
        arrow = "^" if self.delta_pct >= 0 else "v"
        return (
            f"WindowDelta={arrow}{abs(self.delta_pct):.4f}% "
            f"(${self.delta_abs:+.2f}) bias={self.bias} boost={self.score_boost:+.2f}"
        )

def compute_window_delta(
    current_price: float,
    price_to_beat: float,
    seconds_elapsed: int = 0,
) -> WindowDeltaSignal:
    if price_to_beat <= 0 or current_price <= 0:
        return WindowDeltaSignal(
            price_to_beat=price_to_beat, current_price=current_price,
            delta_abs=0.0, delta_pct=0.0,
            bias="neutral", score_boost=0.0, seconds_elapsed=seconds_elapsed,
        )

    delta_abs = current_price - price_to_beat
    delta_pct = delta_abs / price_to_beat * 100.0

    if delta_pct >= WD_STRONG_UP:
        bias = "strong_up"
        score_boost = min(0.15 + (delta_pct - WD_STRONG_UP) * 8.0, 0.40)
    elif delta_pct >= WD_WEAK_UP:
        bias = "weak_up"
        score_boost = min((delta_pct - WD_WEAK_UP) / (WD_STRONG_UP - WD_WEAK_UP) * 0.15, 0.15)
    elif delta_pct > WD_WEAK_DOWN:
        bias = "neutral"
        score_boost = 0.0
    elif delta_pct > WD_STRONG_DOWN:
        bias = "weak_down"
        score_boost = -min((abs(delta_pct) - abs(WD_WEAK_DOWN)) / (abs(WD_STRONG_DOWN) - abs(WD_WEAK_DOWN)) * 0.25, 0.25)
    else:
        bias = "strong_down"
        score_boost = -min(0.25 + (abs(delta_pct) - abs(WD_STRONG_DOWN)) * 8.0, 0.50)

    return WindowDeltaSignal(
        price_to_beat=price_to_beat, current_price=current_price,
        delta_abs=delta_abs, delta_pct=delta_pct,
        bias=bias, score_boost=score_boost, seconds_elapsed=seconds_elapsed,
    )
