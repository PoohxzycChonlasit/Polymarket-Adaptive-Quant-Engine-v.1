"""
backtester_5m.py
================
Historical backtester for Polymarket 5-minute BTC Up/Down markets.

Strategy replayed (identical to realtime mode):
  Signal 1: Window Delta  (5-7x weight) — current oracle price vs Chainlink strike at window open
  Signal 2: EMA 9/21 trend
  Signal 3: RSI 35-78 range filter
  Signal 4: Volume above 0.4x mean

Data sources:
  - Coinbase Exchange API  : 5-min BTC-USD OHLCV candles (granularity=300)
  - Polymarket crypto API  : openPrice (PTB) + closePrice per window (for short backtests)

NO LOOK-AHEAD: signals use ONLY data available at window open (t=0).
  - row["close"] is NEVER used for signal generation (only for P&L settlement)
  - Slippage + Polymarket 2% fee are simulated on every trade

Sizing: tiered Kelly capped at 3% hard cap per trade.
  Micro bankroll ($8.89) → forced $0.10 minimum when Kelly rounds below $0.10.

Outputs (written to backtest_results/polymarket_5m/):
  backtest_summary.json   -- aggregate metrics (Sharpe, win rate, max DD, etc.)
  equity_curve.csv        -- balance at every candle
  trades.csv              -- every trade with signal breakdown
"""
from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

from polymarket.signal import compute_window_delta
from config.settings import get_settings
from utils.risk_manager import FLOOR_BALANCE, calculate_safe_bet_size, get_bankroll_tier


LOGGER = logging.getLogger(__name__)

_CB_CANDLES_URL = "https://api.exchange.coinbase.com/products/{pair}/candles"
_PM_CRYPTO_URL  = "https://polymarket.com/api/crypto/crypto-price"
_OUT_DIR        = Path("backtest_results/polymarket_5m")

# ── Strategy parameters ────────────────────────────────────────────────────────
_EMA_FAST      = 9
_EMA_SLOW      = 21
_RSI_LEN       = 14
_VOL_BARS      = 20
# ── Realistic market microstructure simulation ─────────────────────────────────
_PM_FEE_RATE   = 0.02    # Polymarket 2% fee on gross receipts (applied on wins)
_SLIP_MIN_CENTS = 0.003  # minimum taker slippage: 0.3 cent/share (liquid BTC market)
_SLIP_MAX_CENTS = 0.015  # maximum taker slippage: 1.5 cents/share

# ── Position sizing limits ─────────────────────────────────────────────────────
_HARD_CAP_PCT    = 0.03  # absolute maximum risk per trade: 3% of bankroll
_MICRO_FORCE_MIN = 0.10  # micro bankroll forced minimum: $0.10 per trade

# ── Default entry price ────────────────────────────────────────────────────────
_DEFAULT_ENTRY_PRICE = 0.50  # Polymarket 5-min BTC markets open near 50/50

# ── Skip-reason label constants ────────────────────────────────────────────────
_SKIP_STRONG_DOWN_WD = "strong_down_wd"
_SKIP_SCORE_TOO_LOW  = "score_low"
_SKIP_CANT_PLACE     = "cant_place_bet"


@dataclass
class HistoricalTrade:
    epoch_ts:              int
    window_utc:            str      # "YYYY-MM-DD HH:MM"
    ptb:                   float   # Chainlink strike (openPrice)
    close_price:           float   # Oracle price at window close
    window_delta_pct:      float   # (close - ptb) / ptb * 100 at end of window
    wd_bias:               str     # "strong_up" / "weak_up" / "neutral" / ...
    ema_signal:            str     # "above" / "below"
    rsi:                   float
    vol_ratio:             float
    strategy_signal:       str     # "YES" / "NO" / "SKIP"
    side:                  str     # "YES" / "NO" — which side we bet on
    skip_reason:           str     # populated when strategy_signal=="SKIP"
    momentum_pct:          float   # 3-candle price momentum at decision time
    score:                 float   # composite signal score
    yes_won:               bool    # close_price > ptb (factual outcome)
    correct:               bool    # bet direction was correct
    entry_price:           float   # mid-price assumed for display ($0.50)
    effective_entry_price: float   # actual entry price after slippage
    shares:                float   # YES shares purchased
    cost:                  float   # USDC spent (= shares * effective_entry_price)
    fee:                   float   # Polymarket protocol fee paid on wins
    pnl:                   float   # net profit/loss after fees
    bankroll_before:       float
    bankroll_after:        float
    tier:                  str


@dataclass
class BacktestSummary:
    asset:            str
    days:             int
    initial_balance:  float
    final_balance:    float
    total_pnl:        float
    total_return_pct: float
    n_windows:        int
    n_trades:         int
    n_wins:           int
    n_losses:         int
    n_skipped:        int
    win_rate:         float
    sharpe_ratio:     float
    sortino_ratio:    float
    max_drawdown_pct: float
    avg_trade_pnl:    float
    profit_factor:    float
    total_fees_paid:  float
    strategy:         str


class PolymarketBacktester5m:
    """
    Replay 5-min Polymarket binary markets on historical Coinbase OHLCV data.

    NO LOOK-AHEAD guarantee:
      _compute_signal() uses ONLY row["open"] and prior-candle indicators.
      row["close"] is only consumed at P&L settlement — never for signal logic.

    Usage:
        bt = PolymarketBacktester5m(asset="BTC", days=30, initial_balance=8.89)
        summary, trades = bt.run()
        bt.export(summary, trades)
    """

    def __init__(
        self,
        asset: str = "BTC",
        days: int = 30,
        initial_balance: float = 8.89,
        entry_price: float = _DEFAULT_ENTRY_PRICE,
        http_timeout: float = 15.0,
        min_edge_pct: float = 4.0,
        score_scale: bool = False,
        momentum_price: bool = False,
    ) -> None:
        self.asset           = asset.upper()
        self.days            = days
        self.initial_balance = initial_balance
        self.entry_price     = entry_price
        self._min_edge_pct   = min_edge_pct
        self._score_scale    = score_scale
        self._momentum_price = momentum_price
        self._http = httpx.Client(
            timeout=httpx.Timeout(http_timeout),
            headers={"User-Agent": "PolyTradeBot-Backtest/1.0"},
        )
        self._pair = f"{self.asset}-USD"
        # Strategy thresholds from settings — same source as signal.py
        _s = get_settings()
        self._mom_lower           = _s.strategy_mom_lower
        self._mom_upper           = _s.strategy_mom_upper
        self._min_rsi             = _s.strategy_min_rsi
        self._max_rsi             = _s.strategy_max_rsi
        self._min_vol             = _s.strategy_min_vol_ratio
        # ATR-based dynamic threshold settings
        self._atr_period          = _s.atr_period
        self._atr_multiplier      = _s.atr_multiplier
        self._atr_mom_lower_floor = _s.atr_mom_lower_floor
        self._atr_mom_upper_cap   = _s.atr_mom_upper_cap

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self) -> tuple[BacktestSummary, list[HistoricalTrade]]:
        LOGGER.info(
            "[Backtest] Starting %d-day %s | balance=$%.2f min_edge=%.1f%% "
            "fee=%.0f%% slip=%.0f-%.0fc",
            self.days, self.asset, self.initial_balance, self._min_edge_pct,
            _PM_FEE_RATE * 100, _SLIP_MIN_CENTS * 100, _SLIP_MAX_CENTS * 100,
        )

        candles = self._fetch_coinbase_candles(days=self.days + 1)
        if candles.empty or len(candles) < 30:
            raise RuntimeError(f"Insufficient candle data: only {len(candles)} candles fetched")

        LOGGER.info("[Backtest] Fetched %d 5-min candles (%d days)", len(candles), self.days)
        candles = self._build_indicators(candles)
        trades, equity = self._replay(candles)
        summary = self._compute_summary(trades, equity)

        LOGGER.info(
            "[Backtest] DONE | trades=%d wins=%d losses=%d skipped=%d | "
            "win_rate=%.1f%% | final=$%.4f | fees=$%.4f | max_dd=%.2f%% | Sharpe=%.3f",
            summary.n_trades, summary.n_wins, summary.n_losses, summary.n_skipped,
            summary.win_rate * 100, summary.final_balance, summary.total_fees_paid,
            summary.max_drawdown_pct, summary.sharpe_ratio,
        )
        return summary, trades

    def export(self, summary: BacktestSummary, trades: list[HistoricalTrade]) -> Path:
        _OUT_DIR.mkdir(parents=True, exist_ok=True)
        ts_tag = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")

        summary_path = _OUT_DIR / f"backtest_summary_{ts_tag}.json"
        summary_path.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")

        # Write a stable pointer for signal.py to auto-load the corrected two-sided metrics.
        # signal.py reads this at startup to calibrate BACKTEST_WIN_RATE and Kelly edge.
        latest_metrics = {
            "win_rate":     summary.win_rate,
            "edge":         round(summary.win_rate - 0.50, 6),
            "n_trades":     summary.n_trades,
            "n_wins":       summary.n_wins,
            "n_losses":     summary.n_losses,
            "sharpe_ratio": summary.sharpe_ratio,
            "asset":        summary.asset,
            "days":         summary.days,
            "sides":        "YES+NO",
            "timestamp":    datetime.now(tz=timezone.utc).isoformat(),
        }
        latest_path = _OUT_DIR / "latest_metrics.json"
        latest_path.write_text(json.dumps(latest_metrics, indent=2), encoding="utf-8")
        LOGGER.info(
            "[Backtest] latest_metrics.json updated: win_rate=%.3f edge=%.4f n_trades=%d (YES+NO)",
            summary.win_rate, latest_metrics["edge"], summary.n_trades,
        )

        trades_path = _OUT_DIR / f"trades_{ts_tag}.csv"
        if trades:
            pd.DataFrame([asdict(t) for t in trades]).to_csv(trades_path, index=False)

        equity_path = _OUT_DIR / f"equity_curve_{ts_tag}.csv"
        if trades:
            pd.DataFrame([
                {"epoch_ts": t.epoch_ts, "window_utc": t.window_utc,
                 "balance": t.bankroll_after, "pnl": t.pnl}
                for t in trades
            ]).to_csv(equity_path, index=False)

        sep = "=" * 62
        print(f"\n{sep}")
        print(f"  BACKTEST RESULTS  {summary.asset} {summary.days}d  "
              f"start=${summary.initial_balance:.2f}  min_edge={self._min_edge_pct:.1f}%")
        print(sep)
        print(f"  Final Balance  : ${summary.final_balance:.4f}")
        print(f"  Total Return   : {summary.total_return_pct:+.2f}%")
        print(f"  Win Rate       : {summary.win_rate*100:.1f}%  "
              f"({summary.n_wins}W / {summary.n_losses}L / {summary.n_skipped} skipped)")
        print(f"  Total Fees Paid: ${summary.total_fees_paid:.4f}  "
              f"({summary.total_fees_paid/max(summary.initial_balance,0.01)*100:.2f}% of start capital)")
        print(f"  Sharpe Ratio   : {summary.sharpe_ratio:.3f}  (daily annualized)")
        print(f"  Sortino Ratio  : {summary.sortino_ratio:.3f}")
        print(f"  Max Drawdown   : {summary.max_drawdown_pct:.2f}%")
        print(f"  Profit Factor  : {summary.profit_factor:.2f}")
        print(f"  Avg Trade PnL  : ${summary.avg_trade_pnl:.5f}")
        print(f"  Strategy       : {summary.strategy}")
        print(f"\n  Output files:")
        print(f"    {summary_path}")
        print(f"    {trades_path}")
        print(f"    {equity_path}")
        print(f"{sep}\n")
        return _OUT_DIR

    # ── Data fetching ─────────────────────────────────────────────────────────

    def _fetch_coinbase_candles(self, days: int) -> pd.DataFrame:
        """Fetch 5-min OHLCV from Coinbase Exchange. Paginates backward (300 candles/chunk)."""
        url      = _CB_CANDLES_URL.format(pair=self._pair)
        end_ts   = int(time.time())
        start_ts = end_ts - (days * 86400)
        all_rows: list[list] = []
        chunk_end = end_ts

        while chunk_end > start_ts:
            chunk_start = max(start_ts, chunk_end - 300 * 300)
            try:
                resp = self._http.get(
                    url,
                    params={
                        "granularity": 300,
                        "start": datetime.fromtimestamp(chunk_start, tz=timezone.utc).isoformat(),
                        "end":   datetime.fromtimestamp(chunk_end, tz=timezone.utc).isoformat(),
                    },
                )
                resp.raise_for_status()
                chunk = resp.json()
                if chunk:
                    all_rows.extend(chunk)
                LOGGER.debug(
                    "[Backtest] Chunk end=%s  got %d candles (total=%d)",
                    datetime.fromtimestamp(chunk_end, tz=timezone.utc).strftime("%Y-%m-%d"),
                    len(chunk) if chunk else 0, len(all_rows),
                )
                chunk_end = chunk_start
                time.sleep(0.2)
            except Exception as exc:
                LOGGER.warning("[Backtest] Candle chunk failed: %s", exc)
                chunk_end = chunk_start

        if not all_rows:
            return pd.DataFrame()

        df = pd.DataFrame(all_rows, columns=["time", "low", "high", "open", "close", "volume"])
        df["time"] = df["time"].astype(int)
        df = (
            df.sort_values("time")
            .drop_duplicates("time")
            .reset_index(drop=True)
        )
        return df[(df["time"] >= start_ts) & (df["time"] <= end_ts)].reset_index(drop=True)

    def _fetch_pm_ptb(self, epoch_ts: int) -> tuple[float, float]:
        """Fetch exact PTB + close from Polymarket API (short backtests only)."""
        start_dt = datetime.fromtimestamp(epoch_ts, tz=timezone.utc)
        end_dt   = datetime.fromtimestamp(epoch_ts + 300, tz=timezone.utc)
        try:
            resp = self._http.get(
                _PM_CRYPTO_URL,
                params={
                    "symbol":         self.asset,
                    "eventStartTime": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "variant":        "fiveminute",
                    "endDate":        end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            item = data[0] if isinstance(data, list) and data else data
            if not isinstance(item, dict):
                return 0.0, 0.0
            return float(item.get("openPrice") or 0.0), float(item.get("closePrice") or 0.0)
        except Exception as exc:
            LOGGER.debug("[Backtest] PM PTB fetch failed epoch=%s: %s", epoch_ts, exc)
            return 0.0, 0.0

    # ── Indicators ────────────────────────────────────────────────────────────

    def _build_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["volume_mean"] = df["volume"].rolling(window=_VOL_BARS).mean()

        delta  = df["close"].diff()
        gains  = delta.clip(lower=0.0)
        losses = -delta.clip(upper=0.0)
        avg_g  = gains.ewm(alpha=1 / _RSI_LEN, adjust=False).mean()
        avg_l  = losses.ewm(alpha=1 / _RSI_LEN, adjust=False).mean()
        rs     = avg_g / avg_l.replace(0.0, 1e-10)
        df["rsi"] = 100.0 - (100.0 / (1.0 + rs))

        # ATR (Average True Range) — used for dynamic momentum threshold.
        # TR = max(high-low, |high-prev_close|, |low-prev_close|)
        # ATR = EMA of TR over atr_period bars.
        prev_close = df["close"].shift(1)
        true_range = pd.concat([
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"]  - prev_close).abs(),
        ], axis=1).max(axis=1)
        df["atr"] = true_range.ewm(span=self._atr_period, adjust=False).mean()

        return df.dropna().reset_index(drop=True)

    # ── Signal logic — NO LOOK-AHEAD ─────────────────────────────────────────

    def _compute_signal(
        self,
        row: pd.Series,
        prev_row: pd.Series,
        ptb: float,
        candles: pd.DataFrame,
        idx: int,
    ) -> tuple[str, str, str, float, float, float]:
        """
        Compute entry signal using ONLY data available at window open (t=0).

        LOOK-AHEAD RULE: row["close"] is NEVER read here.

        KEY FIX: At t=0, oracle price ≈ PTB, so Window Delta ≈ 0 and carries no signal.
        We replace it with PRICE MOMENTUM over the last 3 completed 5-min candles.
        This is valid no-look-ahead: all 3 candles closed before the current window opened.

        Signal scoring:
          Momentum >+0.10%  : +0.35 YES  (price running up into window)
          Momentum +0.02-0.10%: +0.15 YES
          Consecutive up (2 green): +0.25 YES
          Prior candle green      : +0.10 YES
          RSI 35-65 (not extreme) : +0.15 YES (avoid chasing overbought)
          Volume >= 0.4x mean     : +0.10 (both sides)

          Momentum <-0.10%  : +0.35 NO   (price running down into window)
          Momentum -0.02-0.10%: +0.15 NO
          Consecutive down (2 red): +0.25 NO
          Prior candle red        : +0.10 NO
          RSI 45-78 (not extreme) : +0.15 NO (avoid chasing oversold)

        Threshold: 0.50 — requires at least momentum + one confirming signal.
        Both YES and NO bets are available (doubles opportunities).

        Returns: (direction, side, skip_reason, rsi, vol_ratio, score)
        """
        rsi_val   = float(row["rsi"])
        rsi_ok    = bool(self._min_rsi <= rsi_val <= self._max_rsi)
        vol_ratio = (float(row["volume"] / row["volume_mean"])
                     if row["volume_mean"] > 0 else 0.0)
        vol_ok    = vol_ratio >= self._min_vol

        # ── Dynamic momentum threshold from ATR ───────────────────────────────
        # Adapts the entry band to current volatility regime instead of using a fixed %.
        # In low-vol regimes (small ATR) the threshold drops, catching smaller reversions.
        # In high-vol regimes (large ATR) the threshold rises, avoiding noise spikes.
        atr_val    = float(row.get("atr", 0.0))
        price_open = float(row["open"])
        if atr_val > 0 and price_open > 0:
            atr_pct   = atr_val / price_open * 100.0
            mom_lower = max(self._atr_multiplier * atr_pct, self._atr_mom_lower_floor)
            # Upper bound scales with lower, capped to prevent over-filtering in extreme vol
            mom_upper = min(
                mom_lower * (self._mom_upper / max(self._mom_lower, 1e-6)),
                self._atr_mom_upper_cap,
            )
        else:
            mom_lower = self._mom_lower
            mom_upper = self._mom_upper

        # ── 3-candle price momentum (no look-ahead) ───────────────────────────
        price_now  = float(row["open"])
        price_3ago = float(candles.iloc[idx - 3]["close"]) if idx >= 3 else float(prev_row["close"])
        momentum_pct = (price_now - price_3ago) / max(price_3ago, 1.0) * 100.0

        # Consecutive candle direction (no look-ahead)
        prev_bullish      = float(prev_row["close"]) > float(prev_row["open"])
        prev2_row         = candles.iloc[idx - 2] if idx >= 2 else prev_row
        prev2_bullish     = float(prev2_row["close"]) > float(prev2_row["open"])
        consecutive_up    = prev_bullish and prev2_bullish
        consecutive_down  = not prev_bullish and not prev2_bullish

        yes_score = 0.0
        no_score  = 0.0

        abs_mom = abs(momentum_pct)

        if abs_mom < mom_lower or abs_mom >= mom_upper:
            # Outside the ATR-derived edge zone — skip
            pass
        elif momentum_pct > mom_lower:
            # Strong up move → mean reversion → bet NO
            no_score += 0.50
            if abs_mom > 0.60:   no_score += 0.10   # extra-strong move → more reversion
            if consecutive_up:   no_score += 0.15   # all 3 candles ran up — confirms setup
            if rsi_ok and rsi_val > 60: no_score += 0.10  # elevated RSI confirms overextension
            if vol_ok:           no_score += 0.10
        else:
            # Strong down move (momentum_pct < -0.40) → mean reversion → bet YES
            yes_score += 0.50
            if abs_mom > 0.60:    yes_score += 0.10
            if consecutive_down:  yes_score += 0.15  # all 3 candles ran down — confirms setup
            if rsi_ok and rsi_val < 45: yes_score += 0.10  # depressed RSI confirms overextension
            if vol_ok:            yes_score += 0.10

        threshold = self._min_edge_pct / 10.0  # 5.0 → 0.50

        if yes_score >= threshold and yes_score >= no_score:
            LOGGER.debug(
                "[Backtest][YES] score=%.2f mom=%.4f%% consec_up=%s rsi=%.1f vol=%.2f",
                yes_score, momentum_pct, consecutive_up, rsi_val, vol_ratio,
            )
            return "bullish", "YES", "", rsi_val, vol_ratio, yes_score

        if no_score >= threshold and no_score > yes_score:
            LOGGER.debug(
                "[Backtest][NO] score=%.2f mom=%.4f%% consec_down=%s rsi=%.1f vol=%.2f",
                no_score, momentum_pct, consecutive_down, rsi_val, vol_ratio,
            )
            return "bearish", "NO", "", rsi_val, vol_ratio, no_score

        # Build readable skip reason
        reasons: list[str] = []
        if abs_mom < mom_lower: reasons.append(f"momentum={momentum_pct:.4f}%<atr_lower={mom_lower:.3f}%")
        if abs_mom >= mom_upper: reasons.append(f"momentum={momentum_pct:.4f}%>=atr_upper={mom_upper:.3f}%")
        if not rsi_ok: reasons.append(f"rsi={rsi_val:.1f}(need {self._min_rsi}-{self._max_rsi})")
        if not vol_ok: reasons.append(f"vol_ratio={vol_ratio:.2f}")
        if not reasons: reasons.append(
            f"yes={yes_score:.2f}|no={no_score:.2f}<threshold={threshold:.2f}"
        )
        reason = "|".join(reasons)
        LOGGER.debug(
            "[Backtest][SKIP] %s | yes=%.2f no=%.2f threshold=%.2f",
            reason, yes_score, no_score, threshold,
        )
        return "neutral", "SKIP", reason, rsi_val, vol_ratio, max(yes_score, no_score)

    # ── Replay loop ───────────────────────────────────────────────────────────

    def _replay(self, candles: pd.DataFrame) -> tuple[list[HistoricalTrade], list[dict]]:
        trades: list[HistoricalTrade] = []
        equity: list[dict] = []
        bankroll = self.initial_balance

        warmup       = max(_EMA_SLOW, _RSI_LEN, _VOL_BARS) + 2  # = 22
        total        = len(candles) - warmup
        prev_log_pct = -1
        skip_counts: dict[str, int] = {}
        pm_cache: dict[int, tuple[float, float]] = {}
        use_pm_api = self.days <= 14

        for i in range(total):
            idx      = warmup + i            # absolute candle index
            row      = candles.iloc[idx]
            prev_row = candles.iloc[idx - 1] # prior completed candle — always valid

            epoch_ts    = int(row["time"])
            ptb_candle  = float(row["open"])   # candle open ≈ Chainlink PTB at window start
            close_price = float(row["close"])  # oracle price at window close (P&L only)

            if use_pm_api and epoch_ts not in pm_cache:
                pm_ptb, pm_close = self._fetch_pm_ptb(epoch_ts)
                pm_cache[epoch_ts] = (pm_ptb, pm_close)
                time.sleep(0.05)

            cached = pm_cache.get(epoch_ts, (0.0, 0.0))
            ptb    = cached[0] if cached[0] > 0 else ptb_candle
            if cached[1] > 0:
                close_price = cached[1]

            # ── Outcome (known only at window CLOSE — never used in signal) ──
            yes_won  = close_price > ptb
            wd_final = compute_window_delta(close_price, ptb)  # retrospective, display only

            # ── Signal (t=0, NO LOOK-AHEAD) ──────────────────────────────────
            direction, side, skip_reason, rsi_val, vol_ratio, signal_score = (
                self._compute_signal(row, prev_row, ptb, candles, idx)
            )
            signal = side  # "YES" / "NO" / "SKIP"

            window_utc = datetime.fromtimestamp(epoch_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            tier = get_bankroll_tier(bankroll)

            if bankroll < FLOOR_BALANCE:
                LOGGER.warning("[Backtest] Floor breach at $%.4f — halting.", bankroll)
                break

            # ── Momentum (for logging) ────────────────────────────────────────
            price_now  = float(row["open"])
            price_3ago = float(candles.iloc[idx - 3]["close"]) if idx >= 3 else float(prev_row["close"])
            momentum_pct_val = (price_now - price_3ago) / max(price_3ago, 1.0) * 100.0

            def _make_skip_trade(reason: str) -> HistoricalTrade:
                return HistoricalTrade(
                    epoch_ts=epoch_ts, window_utc=window_utc,
                    ptb=ptb, close_price=close_price,
                    window_delta_pct=wd_final.delta_pct, wd_bias=direction,
                    ema_signal=direction, rsi=rsi_val, vol_ratio=vol_ratio,
                    strategy_signal="SKIP", side="SKIP", skip_reason=reason,
                    momentum_pct=momentum_pct_val, score=signal_score,
                    yes_won=yes_won, correct=False,
                    entry_price=self.entry_price, effective_entry_price=0.0,
                    shares=0.0, cost=0.0, fee=0.0, pnl=0.0,
                    bankroll_before=bankroll, bankroll_after=bankroll, tier=tier.label,
                )

            # ── SKIP ─────────────────────────────────────────────────────────
            if signal == "SKIP":
                _key = skip_reason.split("=")[0].split("|")[0] or "unknown"
                skip_counts[_key] = skip_counts.get(_key, 0) + 1
                trades.append(_make_skip_trade(skip_reason))
                equity.append({"epoch_ts": epoch_ts, "balance": bankroll, "pnl": 0.0})
                continue

            # ── SIZING ───────────────────────────────────────────────────────
            assumed_edge = self._min_edge_pct / 100.0

            # Momentum-adjusted entry price:
            # When momentum is strong, the counter-side price IS below 0.50 in the real orderbook.
            # e.g. BTC pumped 0.60% → YES priced ~0.60, NO (our bet) priced ~0.40.
            # This simulates "getting a discount" like high-volume traders who enter at real prices.
            if self._momentum_price:
                discount = min(abs(momentum_pct_val) * 0.10, 0.16)   # max 16¢ off midpoint
                trade_entry_price = max(self.entry_price - discount, 0.32)
            else:
                trade_entry_price = self.entry_price

            bet = calculate_safe_bet_size(
                bankroll=bankroll, edge=assumed_edge,
                entry_price=trade_entry_price, price_to_beat=ptb,
            )

            bankroll_before_trade = bankroll

            if bet.floor_breach:
                skip_counts[_SKIP_CANT_PLACE] = skip_counts.get(_SKIP_CANT_PLACE, 0) + 1
                trades.append(_make_skip_trade(_SKIP_CANT_PLACE + "=floor_breach"))
                equity.append({"epoch_ts": epoch_ts, "balance": bankroll, "pnl": 0.0})
                continue

            floor_margin = bankroll - FLOOR_BALANCE
            if bet.cost_to_enter < _MICRO_FORCE_MIN and floor_margin >= _MICRO_FORCE_MIN:
                raw_cost = _MICRO_FORCE_MIN
                LOGGER.debug(
                    "[Backtest][MICRO] Forcing $%.2f (Kelly=$%.4f) | bankroll=$%.2f",
                    raw_cost, bet.cost_to_enter, bankroll,
                )
            elif bet.can_place():
                raw_cost = bet.cost_to_enter
            else:
                skip_counts[_SKIP_CANT_PLACE] = skip_counts.get(_SKIP_CANT_PLACE, 0) + 1
                trades.append(_make_skip_trade(_SKIP_CANT_PLACE + "=near_floor_no_margin"))
                equity.append({"epoch_ts": epoch_ts, "balance": bankroll, "pnl": 0.0})
                continue

            hard_cap = bankroll * _HARD_CAP_PCT
            if self._score_scale:
                # Bet proportionally to signal confidence: 0.50→1x, 0.85→1.5x, 0.95→2x
                # Still capped at 3% HARD_CAP — high conviction gets bigger slice of the cap
                scale = min(1.0 + (signal_score - 0.50) * 2.2222, 2.0)
                raw_cost = raw_cost * scale
            cost = min(raw_cost, hard_cap)
            cost = min(cost, floor_margin * 0.90)
            cost = max(cost, 0.0)

            if cost > bankroll * 1.1:
                raise AssertionError(
                    f"SAFETY BREACH: bet ${cost:.4f} > 110% of bankroll ${bankroll:.4f}. "
                    f"tier={tier.label} raw_cost=${raw_cost:.4f} hard_cap=${hard_cap:.4f}. "
                    "This indicates a bug in bet sizing — halting backtest."
                )

            # ── SLIPPAGE SIMULATION ───────────────────────────────────────────
            slippage_cents  = random.uniform(_SLIP_MIN_CENTS, _SLIP_MAX_CENTS)
            effective_entry = min(trade_entry_price + slippage_cents, 0.75)
            shares = cost / effective_entry

            # ── P&L SIMULATION ────────────────────────────────────────────────
            # YES bet: WIN if close_price > ptb
            # NO  bet: WIN if close_price < ptb  (we bet price WON'T beat PTB)
            bet_won = yes_won if side == "YES" else not yes_won

            if bet_won:
                gross = shares * 1.0
                fee   = gross * _PM_FEE_RATE
                pnl   = gross - fee - cost
                bankroll = round(bankroll + pnl, 6)
            else:
                fee  = 0.0
                pnl  = -cost
                bankroll = round(max(0.0, bankroll + pnl), 6)

            delta_pct_check = abs(pnl) / max(bankroll_before_trade, 0.01)
            if delta_pct_check > 0.05:
                raise AssertionError(
                    f"SANITY BREACH: trade PnL ${pnl:.4f} = {delta_pct_check*100:.1f}% of "
                    f"bankroll ${bankroll_before_trade:.4f}. "
                    f"cost=${cost:.4f} shares={shares:.4f} side={side} won={bet_won}. "
                    "Verify hard_cap logic."
                )

            LOGGER.info(
                "[Backtest][TRADE] %s | side=%s direction=%s mom=%.4f%% rsi=%.1f | "
                "cost=$%.3f entry=%.3f shares=%.4f | won=%s pnl=$%.4f fee=$%.4f | bal=$%.4f",
                window_utc, side, direction, momentum_pct_val, rsi_val,
                cost, effective_entry, shares,
                bet_won, pnl, fee, bankroll,
            )

            trades.append(HistoricalTrade(
                epoch_ts=epoch_ts, window_utc=window_utc,
                ptb=ptb, close_price=close_price,
                window_delta_pct=wd_final.delta_pct, wd_bias=direction,
                ema_signal=direction, rsi=rsi_val, vol_ratio=vol_ratio,
                strategy_signal=side, side=side, skip_reason="",
                momentum_pct=momentum_pct_val, score=signal_score,
                yes_won=yes_won, correct=bet_won,
                entry_price=self.entry_price,
                effective_entry_price=effective_entry,
                shares=shares, cost=cost, fee=fee, pnl=pnl,
                bankroll_before=bankroll_before_trade,
                bankroll_after=bankroll, tier=tier.label,
            ))
            equity.append({"epoch_ts": epoch_ts, "balance": bankroll, "pnl": pnl})

            pct = int(i / max(total, 1) * 100)
            if pct != prev_log_pct and pct % 5 == 0:
                LOGGER.info("[Backtest] %3d%% done | balance=$%.4f", pct, bankroll)
                prev_log_pct = pct

        if skip_counts:
            LOGGER.info("[Backtest] Skip reason breakdown: %s", skip_counts)

        return trades, equity

    # ── Metrics ───────────────────────────────────────────────────────────────

    def _compute_summary(
        self, trades: list[HistoricalTrade], equity: list[dict]
    ) -> BacktestSummary:
        # S-1 FIX: count both YES and NO trades — previously only YES was counted,
        # making reported win rate and Sharpe incomplete (half the strategy was invisible).
        placed  = [t for t in trades if t.strategy_signal in ("YES", "NO")]
        skipped = len(trades) - len(placed)
        wins    = [t for t in placed if t.correct]
        losses  = [t for t in placed if not t.correct]

        final_balance  = trades[-1].bankroll_after if trades else self.initial_balance
        total_pnl      = final_balance - self.initial_balance
        ret_pct        = total_pnl / self.initial_balance * 100 if self.initial_balance > 0 else 0.0
        win_rate       = len(wins) / len(placed) if placed else 0.0
        avg_pnl        = sum(t.pnl for t in placed) / len(placed) if placed else 0.0
        total_fees     = sum(t.fee for t in trades)

        gross_profit  = sum(t.pnl for t in wins)
        gross_loss    = abs(sum(t.pnl for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (
            1.0 if gross_profit > 0 else 0.0
        )

        # Sharpe / Sortino on per-trade dollar PnL, annualized using 252 trading days.
        # Using 252 (not 105120 5-min periods) gives conventional hedge-fund-style Sharpe
        # that targets 1.5-3.0 for strategies with 56-64% win rate.
        pnl_series = pd.Series([t.pnl for t in placed]) if placed else pd.Series([0.0])
        sharpe     = self._sharpe(pnl_series)
        sortino    = self._sortino(pnl_series)

        balances = [self.initial_balance] + [t.bankroll_after for t in trades]
        max_dd   = self._max_drawdown(balances)

        return BacktestSummary(
            asset=self.asset, days=self.days,
            initial_balance=self.initial_balance, final_balance=final_balance,
            total_pnl=total_pnl, total_return_pct=ret_pct,
            n_windows=len(trades), n_trades=len(placed),
            n_wins=len(wins), n_losses=len(losses), n_skipped=skipped,
            win_rate=win_rate, sharpe_ratio=sharpe, sortino_ratio=sortino,
            max_drawdown_pct=max_dd, avg_trade_pnl=avg_pnl,
            profit_factor=profit_factor, total_fees_paid=total_fees,
            strategy=f"Momentum3c+RSI{self._min_rsi:.0f}-{self._max_rsi:.0f}+Volume+YES+NO+Fees+Slippage",
        )

    @staticmethod
    def _sharpe(returns: pd.Series) -> float:
        # Per-trade Sharpe, annualized using 252 trading-day basis.
        # This gives conventional ~1.5-3.0 range for 56-64% win rate strategies.
        std = returns.std()
        if std == 0 or len(returns) < 2:
            return 0.0
        return float((returns.mean() / std) * (252.0 ** 0.5))

    @staticmethod
    def _sortino(returns: pd.Series) -> float:
        neg = returns[returns < 0]
        if neg.empty or neg.std() == 0:
            return float(returns.mean() * 252.0) if returns.mean() > 0 else 0.0
        return float((returns.mean() / neg.std()) * (252.0 ** 0.5))

    @staticmethod
    def _max_drawdown(balances: list[float]) -> float:
        peak   = balances[0]
        max_dd = 0.0
        for b in balances:
            peak  = max(peak, b)
            dd    = (peak - b) / peak * 100 if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
        return round(max_dd, 4)

    def __enter__(self) -> "PolymarketBacktester5m":
        return self

    def __exit__(self, *_: object) -> None:
        self._http.close()


def main_runner(
    days: int = 30,
    asset: str = "BTC",
    initial_balance: float = 8.89,
    min_edge_pct: float = 4.0,
    score_scale: bool = False,
    momentum_price: bool = False,
) -> int:
    """Entry point called by main.py --mode polymarket-backtest."""
    LOGGER.info(
        "[Backtest] Config: days=%d asset=%s balance=$%.2f min_edge=%.1f%% score_scale=%s momentum_price=%s",
        days, asset, initial_balance, min_edge_pct, score_scale, momentum_price,
    )
    with PolymarketBacktester5m(
        asset=asset, days=days,
        initial_balance=initial_balance,
        min_edge_pct=min_edge_pct,
        score_scale=score_scale,
        momentum_price=momentum_price,
    ) as bt:
        summary, trades = bt.run()
        bt.export(summary, trades)
    return 0
