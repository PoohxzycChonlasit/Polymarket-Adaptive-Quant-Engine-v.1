"""
hft/strategy_engine.py
======================
3-Pillar Multi-Strategy Engine — runs all strategies concurrently per cycle.

┌─────────────────────────────────────────────────────────────────────────────┐
│  Strategy A — Deep Value / Limit Sniper                                     │
│    Scan CLOB for extreme mispricing (ask < 0.30 or bid > 0.70).            │
│    EV is enormous when market panic-sells to 0.15 but p_model says 0.60.   │
│    Place Maker limit orders at deep prices to capture panic flow.           │
│                                                                             │
│  Strategy B — Multi-Timeframe Momentum (MTF)                                │
│    HTF (5m): previous candle direction → macro bias (Up/Down)              │
│    LTF (1m): pullback into trend + RSI + volume → precision entry          │
│    Math:  p_model = sigmoid(HTF_strength × 0.6 + LTF_score × 0.4)        │
│    Only enter when LTF pulls back INTO the HTF trend direction.            │
│                                                                             │
│  Strategy C — High Conviction Hold                                          │
│    After entry, update Bayesian p_win each cycle.                          │
│    If p_win > 0.92 → disable TP, hold to full $1.00 settlement.            │
│    If p_win drops back < 0.80 → re-enable normal TP.                       │
└─────────────────────────────────────────────────────────────────────────────┘
"""
from __future__ import annotations

import asyncio
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)


# ── Enums & signal dataclass ───────────────────────────────────────────────────

class StrategyID(str, Enum):
    A_DEEP_VALUE = "deep_value"
    B_MTF_MOM    = "mtf_momentum"
    C_HIGH_CONV  = "high_conviction"
    SKIP         = "skip"


@dataclass
class StrategySignal:
    strategy:         StrategyID
    side:             str          # "YES" | "NO" | "SKIP"
    entry_price:      float        # recommended entry price
    p_model:          float        # win probability estimate
    ev:               float        # expected value per dollar
    edge:             float        # p_model - market_price
    confidence:       float        # 0-1, how strong the signal is
    use_limit:        bool = True  # True → place limit order, False → FOK
    limit_price:      float = 0.0  # target limit price (for Strategy A)
    skip_reason:      str  = ""
    htf_bias:         float = 0.0  # Strategy B: 5m macro bias
    ltf_score:        float = 0.0  # Strategy B: 1m micro score
    momentum_pct:     float = 0.0
    window_delta_pct: float = 0.0
    rsi:              float = 50.0
    imbalance:        float = 0.0


@dataclass
class HoldDecision:
    """Strategy C output — controls whether TP is active for a position."""
    pos_id:         str
    hold_to_end:    bool    # True → disable TP, let run to $1
    p_win_now:      float   # current Bayesian win probability
    reason:         str
    emergency_exit: bool = False   # True → immediate market sell, no waiting


# ── Constants ──────────────────────────────────────────────────────────────────

# Strategy A
DEEP_VALUE_ASK_MAX    = 0.32   # max ask price to trigger deep value buy YES
DEEP_VALUE_BID_MIN    = 0.68   # min bid to trigger deep value buy NO
DEEP_VALUE_MIN_EV     = 0.12   # min EV to fire Strategy A (very high bar)
DEEP_VALUE_LIMIT_OFR  = 0.02   # offer above ask when placing limit (improves fill)

# Strategy B — MTF
MTF_HTF_WEIGHT        = 0.60   # weight of 5m macro bias in p_model
MTF_LTF_WEIGHT        = 0.40   # weight of 1m micro score in p_model
MTF_MIN_HTF_STRENGTH  = 0.05   # |5m candle change| must exceed 0.05% to use HTF signal
MTF_PULLBACK_RSI_YES  = 42     # 1m RSI must be below this to confirm YES pullback
MTF_PULLBACK_RSI_NO   = 58     # 1m RSI must be above this to confirm NO pullback
MTF_VOL_MULTIPLIER    = 1.1    # 1m volume must be > 1.1× rolling avg to confirm

# Strategy B — Sharp 1m spike aggressive entry
SPIKE_MOM_THRESHOLD   = -0.15  # 1m momentum < -0.15% triggers spike detection
SPIKE_RSI_EXHAUSTION  = 32     # RSI < 32 = oversold = exhaustion confirmed
SPIKE_EMA_FAST        = 3      # fast EMA period for crossover check
SPIKE_EMA_SLOW        = 9      # slow EMA period
SPIKE_DISCOUNT_PCT    = 0.22   # bid this % below current ask (e.g. ask=0.55 → bid=0.43)

# Strategy C
HIGH_CONV_THRESHOLD   = 0.92   # p_win > 92% → hold to end
HIGH_CONV_REVERT      = 0.80   # p_win drops below 80% → re-enable TP

# General
FEE_RATE              = 0.002
MIN_EDGE_FOK          = 0.05   # minimum edge to allow FOK fallback
MIN_EV_FOK            = 0.05   # minimum EV to allow FOK fallback


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sigmoid(x: float, k: float = 1.0) -> float:
    return 1.0 / (1.0 + math.exp(-k * x))

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def _ev(p: float, price: float) -> float:
    return p - price - FEE_RATE


def _get_candles(asset: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    try:
        from polymarket.market_feed import get_feed
        feed  = get_feed()
        df1m  = feed.get_candles_df(asset, "1m")
        df5m  = feed.get_candles_df(asset, "5m")
        return (df1m if not df1m.empty else None,
                df5m if not df5m.empty else None)
    except Exception as exc:
        LOGGER.debug("[StratEngine] Candle error: %s", exc)
        return None, None


def _rsi(series: pd.Series, period: int = 14) -> float:
    if len(series) < period + 1:
        return 50.0
    delta  = series.diff().iloc[-(period + 1):]
    gain   = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean().iloc[-1]
    loss   = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean().iloc[-1]
    if loss == 0:
        return 100.0
    return float(100.0 - 100.0 / (1.0 + gain / loss))


def _ema(series: pd.Series, period: int) -> float:
    """Exponential moving average of last N bars."""
    if len(series) < period:
        return float(series.iloc[-1])
    return float(series.ewm(span=period, adjust=False).mean().iloc[-1])


def _detect_sharp_spike(df1m: pd.DataFrame) -> tuple:
    """
    Detect a sharp 1m downward spike + exhaustion signals.

    Returns (is_spike: bool, spike_magnitude_pct: float, exhaustion_confirmed: bool)

    Spike criteria:
      1. 3-candle 1m momentum < SPIKE_MOM_THRESHOLD (-0.15%)
      2. Current 1m candle body is RED (close < open) by > 0.10%

    Exhaustion criteria (reversal imminent):
      1. RSI-14 < SPIKE_RSI_EXHAUSTION (oversold)
      2. Fast EMA (3) crosses above Slow EMA (9) — micro-reversal signal

    Logic: spike = sharp sell-off. Exhaustion = selling is running out of steam.
    Both together = high probability the price snaps back up.
    """
    if len(df1m) < 15:
        return False, 0.0, False

    # 3-candle momentum
    p_now  = float(df1m["open"].iloc[-1])
    p_past = float(df1m["close"].iloc[-4]) if len(df1m) >= 4 else p_now
    mom_pct = (p_now - p_past) / max(p_past, 1.0) * 100.0

    # Current candle body direction
    cur_open  = float(df1m["open"].iloc[-1])
    cur_close = float(df1m["close"].iloc[-1])
    candle_bearish = (cur_close - cur_open) / max(cur_open, 1.0) * 100.0 < -0.10

    is_spike = mom_pct <= SPIKE_MOM_THRESHOLD and candle_bearish

    if not is_spike:
        return False, mom_pct, False

    # Exhaustion checks
    rsi     = _rsi(df1m["close"], period=14)
    ema_f   = _ema(df1m["close"], SPIKE_EMA_FAST)
    ema_s   = _ema(df1m["close"], SPIKE_EMA_SLOW)

    rsi_oversold       = rsi < SPIKE_RSI_EXHAUSTION
    ema_cross_bullish  = ema_f > ema_s   # fast crossed above slow → micro reversal

    exhaustion = rsi_oversold or ema_cross_bullish

    LOGGER.info(
        "[StratB] SPIKE DETECTED | mom=%.3f%% rsi=%.1f ema_fast=%.4f ema_slow=%.4f "
        "exhaustion=%s (rsi_oversold=%s ema_cross=%s)",
        mom_pct, rsi, ema_f, ema_s, exhaustion, rsi_oversold, ema_cross_bullish,
    )

    return True, mom_pct, exhaustion


def _orderbook_imbalance(clob_bids: list, clob_asks: list) -> float:
    """
    OB imbalance in [-1, +1].
    +1 = all bids (strong buy pressure), -1 = all asks (strong sell pressure).
    Uses top 5 levels weighted by size × price proximity.
    """
    try:
        bid_vol = sum(float(b["size"]) for b in clob_bids[:5])
        ask_vol = sum(float(a["size"]) for a in clob_asks[:5])
        total   = bid_vol + ask_vol
        if total == 0:
            return 0.0
        return (bid_vol - ask_vol) / total
    except Exception:
        return 0.0


# ── Strategy A — Deep Value / Limit Sniper ─────────────────────────────────────

def _strategy_a(
    asset:     str,
    yes_price: float,
    no_price:  float,
    clob_bids: list,
    clob_asks: list,
    p_model:   float,
) -> StrategySignal:
    """
    Fire when market is pricing extreme discounts vs our p_model estimate.

    YES case: best ask < 0.32 while p_model > 0.50 → massive EV.
    NO case:  best bid > 0.68 while p_model < 0.50 → massive EV on NO side.

    Entry: place Maker limit AT the ask (or 1-2 cents above for fill priority).
    This exploits panic sellers who dump YES tokens below fair value.
    """
    best_ask = float(clob_asks[0]["price"]) if clob_asks else yes_price
    best_bid = float(clob_bids[0]["price"]) if clob_bids else (1.0 - yes_price)
    imb      = _orderbook_imbalance(clob_bids, clob_asks)

    skip = StrategySignal(
        strategy=StrategyID.A_DEEP_VALUE, side="SKIP",
        entry_price=yes_price, p_model=p_model,
        ev=0.0, edge=0.0, confidence=0.0, use_limit=True,
    )

    # YES deep value: ask is very low, we think YES will win
    if best_ask <= DEEP_VALUE_ASK_MAX and p_model > 0.50:
        ev_yes  = _ev(p_model, best_ask)
        edge    = p_model - best_ask
        if ev_yes >= DEEP_VALUE_MIN_EV and edge >= 0.10:
            limit_px = _clamp(best_ask + DEEP_VALUE_LIMIT_OFR, 0.01, 0.99)
            conf     = _clamp((ev_yes - DEEP_VALUE_MIN_EV) / 0.20 + imb * 0.1, 0.0, 1.0)
            LOGGER.info(
                "[StratA] Deep YES ask=%.3f p_model=%.3f EV=%.4f conf=%.2f",
                best_ask, p_model, ev_yes, conf,
            )
            return StrategySignal(
                strategy=StrategyID.A_DEEP_VALUE, side="YES",
                entry_price=best_ask, p_model=p_model,
                ev=ev_yes, edge=edge, confidence=conf,
                use_limit=True, limit_price=limit_px,
                imbalance=imb,
            )

    # NO deep value: bid is very high on YES → NO is cheap
    if best_bid >= DEEP_VALUE_BID_MIN and p_model < 0.50:
        p_no   = 1.0 - p_model
        ev_no  = _ev(p_no, no_price)
        edge   = p_no - no_price
        if ev_no >= DEEP_VALUE_MIN_EV and edge >= 0.10:
            limit_px = _clamp(no_price + DEEP_VALUE_LIMIT_OFR, 0.01, 0.99)
            conf     = _clamp((ev_no - DEEP_VALUE_MIN_EV) / 0.20 - imb * 0.1, 0.0, 1.0)
            LOGGER.info(
                "[StratA] Deep NO bid=%.3f p_no=%.3f EV=%.4f conf=%.2f",
                best_bid, p_no, ev_no, conf,
            )
            return StrategySignal(
                strategy=StrategyID.A_DEEP_VALUE, side="NO",
                entry_price=no_price, p_model=p_no,
                ev=ev_no, edge=edge, confidence=conf,
                use_limit=True, limit_price=limit_px,
                imbalance=imb,
            )

    skip.skip_reason = (
        f"A_skip: ask={best_ask:.3f} bid={best_bid:.3f} "
        f"p_model={p_model:.3f} EV_threshold={DEEP_VALUE_MIN_EV}"
    )
    return skip


# ── Strategy B — Multi-Timeframe Momentum ──────────────────────────────────────

def _strategy_b(
    asset:     str,
    yes_price: float,
    no_price:  float,
    spot:      float,
    ptb:       float,
    epoch:     int,
    secs_left: int,
) -> StrategySignal:
    """
    Multi-Timeframe momentum with pullback entry.

    HTF (5m candle):
      htf_strength = (prev_5m_close - prev_5m_open) / prev_5m_open × 100
      → +htf_strength means macro is bullish (bias YES)
      → -htf_strength means macro is bearish (bias NO)

    LTF (1m candle):
      We want to enter on a PULLBACK into the HTF trend:
        HTF bullish + 1m dip (RSI < 42) + volume confirmation → YES entry
        HTF bearish + 1m bounce (RSI > 58) + volume confirmation → NO entry

    p_model formula:
      htf_prob = sigmoid(htf_strength × 50)        ← maps % change to probability
      ltf_adj  = computed from RSI + momentum score
      p_model  = clamp(htf_prob × 0.60 + ltf_adj × 0.40, 0.04, 0.96)

    This ensures we ride the macro trend but time entries precisely using
    micro-structure, improving average entry price vs pure market buying.
    """
    df1m, df5m = _get_candles(asset)
    skip = StrategySignal(
        strategy=StrategyID.B_MTF_MOM, side="SKIP",
        entry_price=yes_price, p_model=0.5,
        ev=0.0, edge=0.0, confidence=0.0, use_limit=False,
    )

    if df1m is None or df5m is None or len(df1m) < 20 or len(df5m) < 3:
        skip.skip_reason = "B_skip: insufficient_candles"
        return skip

    # ── HTF: read PREVIOUS completed 5m candle ────────────────────────────────
    prev5m_open  = float(df5m["open"].iloc[-2])
    prev5m_close = float(df5m["close"].iloc[-2])
    prev5m_vol   = float(df5m["volume"].iloc[-2]) if "volume" in df5m.columns else 1.0

    htf_strength = (prev5m_close - prev5m_open) / max(prev5m_open, 1.0) * 100.0

    if abs(htf_strength) < MTF_MIN_HTF_STRENGTH:
        skip.skip_reason = f"B_skip: htf_flat={htf_strength:.3f}%"
        return skip

    htf_bias = 1 if htf_strength > 0 else -1     # +1 = macro bullish, -1 = bearish
    htf_prob = _sigmoid(htf_strength * 50, 1.0)  # 0.05% move → ~0.52, 0.3% → ~0.65

    # ── Sharp 1m spike check (aggressive discounted bid) ─────────────────────
    # When 5m regime is UP but 1m shows sharp downward spike → panic selling.
    # If exhaustion confirmed → bid aggressively at heavily discounted YES price.
    if htf_bias == 1:
        is_spike, spike_mag, exhaustion = _detect_sharp_spike(df1m)
        if is_spike:
            best_ask   = yes_price   # use Gamma price as reference
            disc_price = _clamp(best_ask * (1.0 - SPIKE_DISCOUNT_PCT), 0.05, 0.90)
            ev_spike   = _ev(htf_prob, disc_price)
            edge_spike = htf_prob - disc_price
            mode       = "EXHAUSTION+SPIKE" if exhaustion else "SPIKE_ONLY"

            LOGGER.warning(
                "[StratB] *** %s *** | 5m=UP 1m_mom=%.3f%% "
                "htf_prob=%.3f disc_bid=%.4f EV=%.4f edge=%.4f | "
                "placing MAKER LIMIT at %.4f (%.0f%% below ask=%.4f)",
                mode, spike_mag, htf_prob, disc_price,
                ev_spike, edge_spike, disc_price,
                SPIKE_DISCOUNT_PCT * 100, best_ask,
            )

            if ev_spike > 0.01 and edge_spike > 0.05:
                confidence = _clamp(0.60 + (0.20 if exhaustion else 0.0), 0.0, 1.0)
                return StrategySignal(
                    strategy=StrategyID.B_MTF_MOM, side="YES",
                    entry_price=disc_price, p_model=htf_prob,
                    ev=ev_spike, edge=edge_spike, confidence=confidence,
                    use_limit=True,          # MUST be limit — we want the discount
                    limit_price=disc_price,
                    htf_bias=htf_strength, ltf_score=0.0,
                    momentum_pct=spike_mag, window_delta_pct=0.0,
                    rsi=_rsi(df1m["close"], 14),
                )
            else:
                LOGGER.info("[StratB] Spike found but EV insufficient (%.4f) — skipping", ev_spike)

    # ── LTF: 1m pullback detection ────────────────────────────────────────────
    rsi_1m = _rsi(df1m["close"], period=14)

    # 3-candle momentum on 1m
    mom_pct = 0.0
    if len(df1m) >= 4:
        p_now  = float(df1m["open"].iloc[-1])
        p_past = float(df1m["close"].iloc[-4])
        mom_pct = (p_now - p_past) / max(p_past, 1.0) * 100.0

    # Volume confirmation: current 1m volume vs 10-bar average
    vol_confirmed = False
    if "volume" in df1m.columns and len(df1m) >= 11:
        avg_vol = float(df1m["volume"].iloc[-11:-1].mean())
        cur_vol = float(df1m["volume"].iloc[-1])
        vol_confirmed = cur_vol >= avg_vol * MTF_VOL_MULTIPLIER

    # LTF score: how aligned is the micro-structure with the macro bias?
    ltf_score = 0.5  # neutral
    if htf_bias == 1:    # macro bullish → look for 1m dip (pullback into trend)
        if rsi_1m <= MTF_PULLBACK_RSI_YES:
            ltf_score = 0.5 + (MTF_PULLBACK_RSI_YES - rsi_1m) / 100.0
        if mom_pct < -0.05:   # micro dipping → better entry
            ltf_score += 0.05
    else:                # macro bearish → look for 1m bounce (pullback)
        if rsi_1m >= MTF_PULLBACK_RSI_NO:
            ltf_score = 0.5 + (rsi_1m - MTF_PULLBACK_RSI_NO) / 100.0
        if mom_pct > 0.05:    # micro bouncing → better NO entry
            ltf_score += 0.05

    ltf_score = _clamp(ltf_score, 0.0, 1.0)

    # Volume boosts confidence but doesn't block signal
    confidence_boost = 0.10 if vol_confirmed else 0.0

    # ── Combined p_model ─────────────────────────────────────────────────────
    p_yes = _clamp(
        htf_prob * MTF_HTF_WEIGHT + ltf_score * MTF_LTF_WEIGHT,
        0.04, 0.96,
    )
    p_no  = 1.0 - p_yes

    # Window delta as secondary confirmation
    if ptb > 0:
        win_delta = (spot - ptb) / ptb * 100.0
        # If delta aligns with HTF bias, add small boost
        if htf_bias == 1 and win_delta > 0:
            p_yes = _clamp(p_yes + 0.02, 0.04, 0.96)
        elif htf_bias == -1 and win_delta < 0:
            p_yes = _clamp(p_yes - 0.02, 0.04, 0.96)
        p_no = 1.0 - p_yes
    else:
        win_delta = 0.0

    # ── Decide side ───────────────────────────────────────────────────────────
    ev_yes  = _ev(p_yes, yes_price)
    ev_no   = _ev(p_no,  no_price)
    edge_yes = p_yes - yes_price
    edge_no  = p_no  - no_price

    min_ev   = 0.015  # Strategy B has lower EV bar (MTF provides conviction)
    min_edge = 0.025

    confidence_base = abs(htf_strength) / 0.5  # stronger HTF → more confident
    confidence = _clamp(confidence_base + confidence_boost, 0.0, 1.0)

    if ev_yes >= min_ev and edge_yes >= min_edge and htf_bias == 1:
        return StrategySignal(
            strategy=StrategyID.B_MTF_MOM, side="YES",
            entry_price=yes_price, p_model=p_yes,
            ev=ev_yes, edge=edge_yes, confidence=confidence,
            use_limit=False,   # MTF uses market/FOK for speed
            htf_bias=htf_strength, ltf_score=ltf_score,
            momentum_pct=mom_pct, window_delta_pct=win_delta,
            rsi=rsi_1m,
        )
    if ev_no >= min_ev and edge_no >= min_edge and htf_bias == -1:
        return StrategySignal(
            strategy=StrategyID.B_MTF_MOM, side="NO",
            entry_price=no_price, p_model=p_no,
            ev=ev_no, edge=edge_no, confidence=confidence,
            use_limit=False,
            htf_bias=htf_strength, ltf_score=ltf_score,
            momentum_pct=mom_pct, window_delta_pct=win_delta,
            rsi=rsi_1m,
        )

    skip.skip_reason = (
        f"B_skip: htf={htf_strength:+.3f}% ltf={ltf_score:.2f} "
        f"ev_yes={ev_yes:.4f} ev_no={ev_no:.4f}"
    )
    skip.htf_bias    = htf_strength
    skip.ltf_score   = ltf_score
    skip.rsi         = rsi_1m
    return skip


# ── Strategy C — High Conviction Hold ─────────────────────────────────────────

def _strategy_c_hold_decision(
    pos_id:       str,
    pos_side:     str,
    p_model_now:  float,
    p_model_prev: float,   # p_win from previous cycle
    secs_left:    int,
) -> HoldDecision:
    """
    Bayesian hold logic with emergency exit failsafe.

    Normal hold: p_win > 0.92 → disable TP, hold to $1.00
    Emergency:   p_win was > 0.92 last cycle, now dropped < 0.80
                 → massive reversal occurred → immediate market sell

    EV comparison (why hold is better at high conviction):
      EV_hold = p_win × $1.00 − entry_price          (full payout)
      EV_tp   = current_market_price − entry_price   (partial profit)
      At p_win=0.93, EV_hold >> EV_tp for most entry prices.

    Emergency exit math:
      p_win 0.93 → 0.76 = -0.17 swing in one cycle (10s).
      Expected loss of holding: 0.24 × $1.00 = $0.24/share.
      Better to exit immediately at market price.
    """
    was_holding   = p_model_prev >= HIGH_CONV_THRESHOLD
    now_above_thr = p_model_now  >= HIGH_CONV_THRESHOLD
    now_reverted  = p_model_now  <  HIGH_CONV_REVERT

    # Emergency exit: was high-conviction, now collapsed
    if was_holding and now_reverted:
        reason = (
            f"[StratC] *** EMERGENCY EXIT *** | "
            f"p_win collapsed {p_model_prev:.3f} -> {p_model_now:.3f} "
            f"(threshold={HIGH_CONV_REVERT}) | side={pos_side} | {secs_left}s left | "
            f"triggering immediate market sell to lock remaining profit"
        )
        LOGGER.critical(reason)
        return HoldDecision(
            pos_id=pos_id,
            hold_to_end=False,
            p_win_now=p_model_now,
            reason=reason,
            emergency_exit=True,
        )

    if now_above_thr:
        reason = (
            f"[StratC] HIGH CONVICTION HOLD | p_win={p_model_now:.3f} "
            f"> {HIGH_CONV_THRESHOLD} | holding to $1.00 | {secs_left}s left"
        )
        LOGGER.info(reason)
    elif now_reverted:
        reason = f"[StratC] Reverted | p_win={p_model_now:.3f} < {HIGH_CONV_REVERT} — TP re-enabled"
        LOGGER.info(reason)
    else:
        reason = f"[StratC] Normal | p_win={p_model_now:.3f} | TP active"

    return HoldDecision(
        pos_id=pos_id,
        hold_to_end=now_above_thr,
        p_win_now=p_model_now,
        reason=reason,
        emergency_exit=False,
    )


# ── Main engine ────────────────────────────────────────────────────────────────

class StrategyEngine:
    """
    Runs all 3 strategies asynchronously and returns the best signal.

    Priority order:
      1. Strategy A  (highest EV when available)
      2. Strategy B  (second choice, broader conditions)
      3. Strategy C  (hold decision for existing positions, not an entry signal)

    Usage:
        engine = StrategyEngine()
        signal = await engine.compute(asset, yes_price, no_price, clob_bids,
                                      clob_asks, spot, ptb, p_model_base,
                                      epoch, secs_left)
        hold_dec = engine.check_hold(pos_id, pos_side, p_model_now, secs_left)
    """

    def __init__(self) -> None:
        self._p_model_cache: Dict[str, float] = {}   # pos_id → last p_model

    async def compute(
        self,
        asset:      str,
        yes_price:  float,
        no_price:   float,
        clob_bids:  list,
        clob_asks:  list,
        spot:       float,
        ptb:        float,
        p_model_base: float,   # pre-computed baseline p_yes from signal_engine
        epoch:      int,
        secs_left:  int,
    ) -> StrategySignal:
        """
        Run Strategy A and B concurrently, return best signal.
        Strategy C is checked separately via check_hold().
        """
        sig_a, sig_b = await asyncio.gather(
            asyncio.to_thread(
                _strategy_a, asset, yes_price, no_price,
                clob_bids, clob_asks, p_model_base,
            ),
            asyncio.to_thread(
                _strategy_b, asset, yes_price, no_price,
                spot, ptb, epoch, secs_left,
            ),
        )

        # Strategy A has priority if EV is exceptional
        if sig_a.side != "SKIP" and sig_a.ev >= DEEP_VALUE_MIN_EV:
            LOGGER.info("[StratEngine] Strategy A wins: EV=%.4f side=%s", sig_a.ev, sig_a.side)
            return sig_a

        # Strategy B as fallback
        if sig_b.side != "SKIP":
            LOGGER.info("[StratEngine] Strategy B wins: EV=%.4f side=%s", sig_b.ev, sig_b.side)
            return sig_b

        # Both skipped
        return StrategySignal(
            strategy=StrategyID.SKIP, side="SKIP",
            entry_price=yes_price, p_model=p_model_base,
            ev=0.0, edge=0.0, confidence=0.0,
            skip_reason=f"A:{sig_a.skip_reason} | B:{sig_b.skip_reason}",
        )

    def check_hold(
        self,
        pos_id:      str,
        pos_side:    str,
        p_model_now: float,
        secs_left:   int,
    ) -> HoldDecision:
        """Strategy C: check if an open position should hold or emergency exit."""
        p_prev = self._p_model_cache.get(pos_id, p_model_now)
        self._p_model_cache[pos_id] = p_model_now
        return _strategy_c_hold_decision(pos_id, pos_side, p_model_now, p_prev, secs_left)

    def update_p_model(self, pos_id: str, p_model: float) -> None:
        self._p_model_cache[pos_id] = p_model

    def get_cached_p_model(self, pos_id: str) -> float:
        return self._p_model_cache.get(pos_id, 0.5)
