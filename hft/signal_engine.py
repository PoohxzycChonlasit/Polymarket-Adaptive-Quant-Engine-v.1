"""
hft/signal_engine.py
====================
Ultra-fast signal computation for HFT mode.

Strategy:  Window-Delta primary + Counter-momentum entry timing.

p_model (probability BTC ends ABOVE PTB at window close):
  - Window Delta:  sigmoid of (current_price - PTB) / PTB   [primary]
  - Momentum:      3-candle slope on 1m candles              [entry timing]
  - RSI:           fade extremes                              [filter]
  - OB Imbalance:  microstructure confirmation               [+/- 2.5%]
  - Time decay:    confidence grows as window progresses     [scaling]

Signal fires when:
  - EV  > MIN_EV  (2.5%)
  - Edge > MIN_EDGE (4%)
  - |Momentum| > MIN_MOMENTUM (confirms market is moving)
  - seconds_remaining in (MIN_SECS, MAX_SECS)
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from hft import config as C
from hft.utils import (
    clamp, sigmoid, ev_for_yes, ev_for_no, kelly_fraction,
    seconds_remaining, time_progress,
)

LOGGER = logging.getLogger(__name__)


@dataclass
class HFTSignal:
    asset:               str
    side:                str      # "YES" | "NO" | "SKIP"
    p_model:             float    # our win probability estimate for the chosen side
    market_price:        float    # current market price for chosen side
    ev:                  float    # expected value of entering
    edge:                float    # p_model - market_price
    full_kelly:          float    # full Kelly fraction (before multiplying by KELLY_FRACTION)
    entry_price:         float    # recommended entry price
    momentum_pct:        float    # 3-candle momentum %
    window_delta_pct:    float    # (current_spot - ptb) / ptb * 100
    rsi:                 float
    imbalance:           float    # orderbook imbalance [-1, 1]
    seconds_remaining:   int
    skip_reason:         str = ""


class HFTSignalEngine:
    """
    Stateless signal engine — call compute() every SIGNAL_INTERVAL_SEC.

    Uses:
    - polymarket.market_feed.BinanceFeed  for candle data
    - PTB and YES/NO prices passed in from MarketManager
    """

    def __init__(self) -> None:
        self._feed_cache: dict = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    def compute(
        self,
        asset:       str,
        yes_price:   float,
        no_price:    float,
        ptb:         float,
        spot_price:  float,
        epoch:       int,
        imbalance:   float = 0.0,
    ) -> HFTSignal:
        """
        Compute the HFT signal for one asset.

        Parameters
        ----------
        asset       : "BTC"
        yes_price   : Polymarket YES price (0-1)
        no_price    : Polymarket NO price (0-1)
        ptb         : Price To Beat from Gamma (Coinbase oracle)
        spot_price  : Current Binance spot price
        epoch       : Current 5-min window start timestamp
        imbalance   : Orderbook imbalance [-1=all asks, +1=all bids]
        """
        secs_left = seconds_remaining(epoch)

        # Entry timing guard
        if secs_left < C.MIN_SECONDS_REMAINING:
            return self._skip(asset, yes_price, no_price, 0.0, 0.0, secs_left, imbalance,
                              f"too_late:{secs_left}s")
        if secs_left > C.MAX_SECONDS_TO_ENTRY:
            return self._skip(asset, yes_price, no_price, 0.0, 0.0, secs_left, imbalance,
                              f"too_early:{secs_left}s")

        # Get candle data from Binance feed
        df_1m, df_5m = self._get_candles(asset)
        if df_1m is None or len(df_1m) < C.RSI_PERIOD + C.MOMENTUM_CANDLES + 5:
            return self._skip(asset, yes_price, no_price, 0.0, 0.0, secs_left, imbalance,
                              "insufficient_candles")

        # Compute indicators
        rsi       = self._compute_rsi(df_1m)
        momentum  = self._compute_momentum_pct(df_1m)
        win_delta = self._compute_window_delta(spot_price, ptb)

        # Validate PTB — use spot-based momentum fallback if PTB unavailable
        ptb_available = ptb > 0
        if not ptb_available:
            # Estimate window delta from recent 5m candle momentum as proxy
            df_5m = self._get_candles(asset)[1]
            if df_5m is not None and len(df_5m) >= 2:
                prev_close = float(df_5m["close"].iloc[-2])
                curr_close = float(df_5m["close"].iloc[-1])
                win_delta  = (curr_close - prev_close) / max(prev_close, 1.0) * 100.0
            # Still allow signal — just with lower confidence

        # Build p_model for YES side (BTC ends ABOVE PTB)
        p_yes = self._compute_p_yes(
            window_delta_pct = win_delta,
            momentum_pct     = momentum,
            rsi              = rsi,
            imbalance        = imbalance,
            secs_remaining   = secs_left,
        )
        p_no = 1.0 - p_yes

        # Compute EV and edge for both sides
        ev_yes  = ev_for_yes(p_yes, yes_price, C.POLYMARKET_FEE)
        ev_no   = ev_for_no(p_yes, no_price,  C.POLYMARKET_FEE)
        edge_yes = p_yes - yes_price
        edge_no  = p_no  - no_price

        # Momentum filter — need market to be moving to enter
        abs_mom = abs(momentum)
        if abs_mom < C.MIN_MOMENTUM_ABS and abs(win_delta) < C.WINDOW_DELTA_DEADBAND:
            return self._skip(asset, yes_price, no_price, momentum, win_delta, secs_left, imbalance,
                              f"flat:mom={momentum:.3f}% delta={win_delta:.3f}%")

        # Pick best side
        if ev_yes >= ev_no and ev_yes >= C.MIN_EV and edge_yes >= C.MIN_EDGE:
            fk = kelly_fraction(p_yes, yes_price)
            return HFTSignal(
                asset=asset, side="YES", p_model=p_yes,
                market_price=yes_price, ev=ev_yes, edge=edge_yes,
                full_kelly=fk, entry_price=yes_price,
                momentum_pct=momentum, window_delta_pct=win_delta,
                rsi=rsi, imbalance=imbalance, seconds_remaining=secs_left,
            )
        elif ev_no > ev_yes and ev_no >= C.MIN_EV and edge_no >= C.MIN_EDGE:
            fk = kelly_fraction(p_no, no_price)
            return HFTSignal(
                asset=asset, side="NO", p_model=p_no,
                market_price=no_price, ev=ev_no, edge=edge_no,
                full_kelly=fk, entry_price=no_price,
                momentum_pct=momentum, window_delta_pct=win_delta,
                rsi=rsi, imbalance=imbalance, seconds_remaining=secs_left,
            )

        best_ev = max(ev_yes, ev_no)
        best_edge = max(edge_yes, edge_no)
        return self._skip(
            asset, yes_price, no_price, momentum, win_delta, secs_left, imbalance,
            f"ev={best_ev:.4f}<{C.MIN_EV}|edge={best_edge:.4f}<{C.MIN_EDGE}",
        )

    # ── Probability model ──────────────────────────────────────────────────────

    def _compute_p_yes(
        self,
        window_delta_pct: float,
        momentum_pct:     float,
        rsi:              float,
        imbalance:        float,
        secs_remaining:   int,
    ) -> float:
        """
        Compute P(YES wins) = P(BTC ends ABOVE PTB at window close).

        Window Delta is the primary driver: the further above PTB BTC is
        right now, the more likely YES wins. The sigmoid steepens as the
        window nears its close (less time for reversals).

        Counter-momentum is used as an ENTRY TIMING adjustment, not as
        the primary direction — this is the key difference from the existing
        strategy which uses counter-momentum as the primary direction signal.
        """
        progress = time_progress()  # 0.0 → 1.0

        # ── Window Delta (primary) ─────────────────────────────────────────
        # Sensitivity increases as time runs out (less time = delta matters more)
        sensitivity = C.P_MODEL_SENSITIVITY * (0.5 + 0.5 * progress)  # 1.5 → 3.0
        # Clamp delta to avoid overflow in sigmoid
        delta_clamped = clamp(window_delta_pct, -3.0, 3.0)
        p_delta = sigmoid(delta_clamped * sensitivity / 100.0 * 100.0, 1.0)

        # ── Momentum adjustment (entry timing) ────────────────────────────
        # Counter-momentum: if BTC just spiked UP (momentum > 0) but is above
        # PTB (YES winning), the spike may reverse → slight NO bias
        # This helps time the entry against the crowd
        mom_adj = 0.0
        if secs_remaining > 120:  # only apply early in window
            delta_sign   = math.copysign(1, window_delta_pct) if window_delta_pct != 0 else 0
            momentum_sign = math.copysign(1, momentum_pct) if momentum_pct != 0 else 0
            if delta_sign == momentum_sign and abs(momentum_pct) > 0.4:
                # Both delta and momentum agree → crowd is piling in → slight fade
                mom_adj = -0.025 * delta_sign
            elif delta_sign != momentum_sign and abs(momentum_pct) > 0.3:
                # Counter-momentum against delta → bounce expected → reinforce delta
                mom_adj = +0.02 * delta_sign

        # ── RSI filter (avoid extreme reversals) ──────────────────────────
        rsi_adj = 0.0
        if rsi > 75:
            rsi_adj = -0.04  # overbought → slight NO bias
        elif rsi < 25:
            rsi_adj = +0.04  # oversold → slight YES bias

        # ── Orderbook imbalance ────────────────────────────────────────────
        imb_adj = 0.025 * clamp(imbalance, -1.0, 1.0)

        p_yes = p_delta + mom_adj + rsi_adj + imb_adj
        return clamp(p_yes, 0.04, 0.96)

    # ── Indicator helpers ──────────────────────────────────────────────────────

    def _get_candles(self, asset: str) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
        try:
            from polymarket.market_feed import get_feed
            feed = get_feed()
            df_1m = feed.get_candles_df(asset, "1m")
            df_5m = feed.get_candles_df(asset, "5m")
            return (df_1m if not df_1m.empty else None,
                    df_5m if not df_5m.empty else None)
        except Exception as exc:
            LOGGER.debug("[SignalEngine] Candle fetch error: %s", exc)
            return None, None

    def _compute_rsi(self, df: pd.DataFrame, period: int | None = None) -> float:
        n = period or C.RSI_PERIOD
        if len(df) < n + 1:
            return 50.0
        delta  = df["close"].diff().iloc[-n-1:]
        gains  = delta.clip(lower=0.0)
        losses = -delta.clip(upper=0.0)
        avg_g  = gains.ewm(alpha=1/n, adjust=False).mean().iloc[-1]
        avg_l  = losses.ewm(alpha=1/n, adjust=False).mean().iloc[-1]
        if avg_l == 0:
            return 100.0
        rs = avg_g / avg_l
        return float(100.0 - 100.0 / (1.0 + rs))

    def _compute_momentum_pct(self, df: pd.DataFrame) -> float:
        """3-candle momentum on 1m bars: (open_now - close_3ago) / close_3ago * 100."""
        n = C.MOMENTUM_CANDLES
        if len(df) < n + 1:
            return 0.0
        price_now  = float(df["open"].iloc[-1])
        price_past = float(df["close"].iloc[-(n + 1)])
        if price_past <= 0:
            return 0.0
        return (price_now - price_past) / price_past * 100.0

    def _compute_window_delta(self, spot: float, ptb: float) -> float:
        """(spot - PTB) / PTB * 100 — positive means spot is ABOVE PTB (YES winning)."""
        if ptb <= 0 or spot <= 0:
            return 0.0
        return (spot - ptb) / ptb * 100.0

    # ── Helper ─────────────────────────────────────────────────────────────────

    def _skip(
        self, asset, yes_price, no_price, momentum, win_delta, secs, imbalance, reason
    ) -> HFTSignal:
        return HFTSignal(
            asset=asset, side="SKIP", p_model=0.5,
            market_price=yes_price, ev=0.0, edge=0.0,
            full_kelly=0.0, entry_price=yes_price,
            momentum_pct=momentum, window_delta_pct=win_delta,
            rsi=50.0, imbalance=imbalance, seconds_remaining=secs,
            skip_reason=reason,
        )
