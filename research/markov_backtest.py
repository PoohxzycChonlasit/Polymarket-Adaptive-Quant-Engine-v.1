"""
markov_backtest.py
==================
Phase 2: Backtest 3 momentum-bound variants side by side.

Markov analysis found:
  S2 (0.40–0.60%): win rate 56.7%  ← best
  S4 (0.40–0.60% down): win rate 53.9%  ← good
  S0 (>1.00%): win rate 50.0%  ← no edge
  S6 (<-1.00%): win rate 50.5%  ← no edge

Three variants tested on same 60-day data:
  Baseline      current strategy      |mom| > 0.40%               (no upper bound)
  Markov Strict  S2+S4 only           0.40% < |mom| < 0.60%
  Markov Relaxed S2+S4+S1+S5          0.40% < |mom| < 1.00%

Run:
  python research/markov_backtest.py
"""
from __future__ import annotations

import logging
import sys
from dataclasses import asdict

import pandas as pd

sys.path.insert(0, ".")

from polymarket.backtester_5m import (
    PolymarketBacktester5m,
    BacktestSummary,
    _MIN_RSI, _MAX_RSI, _MIN_VOL_RATIO,
)

logging.disable(logging.CRITICAL)   # silence all logs during comparison run

DAYS            = 60
INITIAL_BALANCE = 8.89
MIN_EDGE        = 5.0
ASSET           = "BTC"


class MarkovBacktester(PolymarketBacktester5m):
    """
    Subclass that adds momentum upper bound to _compute_signal.
    All other logic (fees, slippage, Kelly, hard stops) unchanged.
    """

    def __init__(self, mom_lower: float, mom_upper: float, **kwargs):
        super().__init__(**kwargs)
        self._mom_lower = mom_lower   # minimum |momentum| to trade
        self._mom_upper = mom_upper   # maximum |momentum| to trade (inf = no limit)

    def _compute_signal(self, row, prev_row, ptb, candles, idx):
        rsi_val   = float(row["rsi"])
        rsi_ok    = _MIN_RSI <= rsi_val <= _MAX_RSI
        vol_ratio = (float(row["volume"] / row["volume_mean"])
                     if row["volume_mean"] > 0 else 0.0)
        vol_ok = vol_ratio >= _MIN_VOL_RATIO

        price_now  = float(row["open"])
        price_3ago = float(candles.iloc[idx - 3]["close"]) if idx >= 3 else float(prev_row["close"])
        momentum_pct = (price_now - price_3ago) / max(price_3ago, 1.0) * 100.0

        prev_bullish  = float(prev_row["close"]) > float(prev_row["open"])
        prev2_row     = candles.iloc[idx - 2] if idx >= 2 else prev_row
        prev2_bullish = float(prev2_row["close"]) > float(prev2_row["open"])
        consecutive_up   = prev_bullish and prev2_bullish
        consecutive_down = not prev_bullish and not prev2_bullish

        yes_score = 0.0
        no_score  = 0.0
        abs_mom   = abs(momentum_pct)

        # ── Markov bounds: trade only within [lower, upper) ───────────────────
        in_range = self._mom_lower <= abs_mom < self._mom_upper

        if not in_range:
            skip_reason = (
                f"mom={momentum_pct:.4f}% outside [{self._mom_lower},{self._mom_upper})"
            )
            return "neutral", "SKIP", skip_reason, rsi_val, vol_ratio, 0.0

        if momentum_pct > self._mom_lower:
            no_score += 0.50
            if abs_mom > 0.60:               no_score += 0.10
            if consecutive_up:               no_score += 0.15
            if rsi_ok and rsi_val > 60:      no_score += 0.10
            if vol_ok:                       no_score += 0.10
        else:
            yes_score += 0.50
            if abs_mom > 0.60:               yes_score += 0.10
            if consecutive_down:             yes_score += 0.15
            if rsi_ok and rsi_val < 45:      yes_score += 0.10
            if vol_ok:                       yes_score += 0.10

        threshold = self._min_edge_pct / 10.0

        if yes_score >= threshold and yes_score >= no_score:
            return "bullish", "YES", "", rsi_val, vol_ratio, yes_score
        if no_score >= threshold and no_score > yes_score:
            return "bearish", "NO", "", rsi_val, vol_ratio, no_score

        skip_reason = f"yes={yes_score:.2f}|no={no_score:.2f}<{threshold:.2f}"
        return "neutral", "SKIP", skip_reason, rsi_val, vol_ratio, max(yes_score, no_score)


def run_variant(name: str, mom_lower: float, mom_upper: float,
                candles: pd.DataFrame) -> BacktestSummary:
    print(f"  Running {name}  [{mom_lower:.2f}% – {mom_upper:.2f}%)...", flush=True)
    bt = MarkovBacktester(
        mom_lower=mom_lower,
        mom_upper=mom_upper,
        asset=ASSET,
        days=DAYS,
        initial_balance=INITIAL_BALANCE,
        min_edge_pct=MIN_EDGE,
    )
    # Reuse already-fetched candles to avoid re-downloading
    bt._prefetched = candles
    summary, _ = bt.run()
    return summary


class CachedBacktester(MarkovBacktester):
    """Uses pre-fetched candles to avoid repeated Coinbase API calls."""

    def __init__(self, candles: pd.DataFrame, **kwargs):
        super().__init__(**kwargs)
        self._cached_candles = candles

    def run(self):
        import logging as _log
        _log.disable(_log.CRITICAL)
        candles = self._build_indicators(self._cached_candles.copy())
        trades, equity = self._replay(candles)
        summary = self._compute_summary(trades, equity)
        return summary, trades


def print_comparison(results: list[tuple[str, str, BacktestSummary]]) -> None:
    BREAKEVEN = 0.5102
    SEP  = "=" * 92
    SEP2 = "-" * 92

    print(f"\n{SEP}")
    print("  MARKOV BACKTEST COMPARISON  —  BTC 60d  start=$8.89")
    print(SEP2)

    headers = ["Metric", *[r[0] for r in results]]
    col_w   = 26

    def row(label, *vals):
        print(f"  {label:<28}", end="")
        for v in vals:
            print(f"  {v:>{col_w}}", end="")
        print()

    print(f"  {'Metric':<28}", end="")
    for name, bounds, _ in results:
        print(f"  {name:>{col_w}}", end="")
    print()
    print(f"  {'Momentum bounds':<28}", end="")
    for _, bounds, _ in results:
        print(f"  {bounds:>{col_w}}", end="")
    print()
    print(f"  {SEP2}")

    def fmt_pct(v, good_hi=True):
        return f"{v:.2%}"

    def fmt_float(v, decimals=3):
        return f"{v:.{decimals}f}"

    metrics = [
        ("Total Return",    lambda s: f"{s.total_return_pct:+.2f}%"),
        ("Final Balance",   lambda s: f"${s.final_balance:.4f}"),
        ("Win Rate",        lambda s: f"{s.win_rate:.2%}"),
        ("Edge/Trade",      lambda s: f"{s.win_rate - BREAKEVEN:+.2%}"),
        ("Sharpe Ratio",    lambda s: f"{s.sharpe_ratio:.3f}"),
        ("Sortino Ratio",   lambda s: f"{s.sortino_ratio:.3f}"),
        ("Max Drawdown",    lambda s: f"{s.max_drawdown_pct:.2f}%"),
        ("Profit Factor",   lambda s: f"{s.profit_factor:.3f}"),
        ("Total Trades",    lambda s: f"{s.n_trades:,}"),
        ("Wins",            lambda s: f"{s.n_wins:,}"),
        ("Losses",          lambda s: f"{s.n_losses:,}"),
        ("Avg Trade PnL",   lambda s: f"${s.avg_trade_pnl:.5f}"),
        ("Total Fees",      lambda s: f"${s.total_fees_paid:.4f}"),
    ]

    for label, fn in metrics:
        print(f"  {label:<28}", end="")
        for _, _, s in results:
            print(f"  {fn(s):>{col_w}}", end="")
        print()

    print(f"\n{SEP}")
    print("  VERDICT")
    print(SEP2)

    base_s    = results[0][2]
    base_name = results[0][0]

    for name, bounds, s in results[1:]:
        wr_delta     = (s.win_rate - base_s.win_rate) * 100
        sharpe_delta = s.sharpe_ratio - base_s.sharpe_ratio
        trade_delta  = s.n_trades - base_s.n_trades
        dd_delta     = s.max_drawdown_pct - base_s.max_drawdown_pct

        print(f"\n  {name} vs {base_name}:")
        print(f"    Win rate  : {wr_delta:+.2f}pp  "
              f"({'↑ better' if wr_delta > 0 else '↓ worse'})")
        print(f"    Sharpe    : {sharpe_delta:+.3f}  "
              f"({'↑ better' if sharpe_delta > 0 else '↓ worse'})")
        print(f"    Trades    : {trade_delta:+,}  "
              f"({'fewer (quality↑)' if trade_delta < 0 else 'more'})")
        print(f"    Max DD    : {dd_delta:+.2f}%  "
              f"({'↑ worse' if dd_delta > 0 else '↓ better'})")

        # Overall recommendation
        score = sum([
            wr_delta > 0,
            sharpe_delta > 0,
            trade_delta < 0,
            dd_delta < 0,
        ])
        verdict = {4: "✅ UPGRADE — all metrics better",
                   3: "✅ UPGRADE — 3/4 metrics better",
                   2: "⚠️  MIXED  — check individual metrics",
                   1: "❌ NO UPGRADE — worse overall",
                   0: "❌ NO UPGRADE — all metrics worse"}[score]
        print(f"    Verdict   : {verdict}")

    print(f"\n{SEP}")
    print("  NEXT STEP")
    print(SEP2)
    best = max(results, key=lambda r: r[2].sharpe_ratio)
    print(f"\n  Best Sharpe: {best[0]}  ({best[2].sharpe_ratio:.3f})")
    if best[0] != results[0][0]:
        print(f"  → Recommend implementing {best[0]} bounds in _compute_signal()")
        print(f"  → Change _MOM_THRESHOLD range to: {best[1]}")
        print(f"  → Then run 90d backtest to confirm before touching live code")
    else:
        print(f"  → Current baseline is still best — no change needed")
    print()


def main() -> None:
    print("=" * 60)
    print("  Markov Backtest — Phase 2")
    print("=" * 60)

    # Fetch candles once, reuse across all 3 variants
    print("\nFetching candle data (one-time)...")
    base_bt = MarkovBacktester(
        mom_lower=0.40, mom_upper=float("inf"),
        asset=ASSET, days=DAYS,
        initial_balance=INITIAL_BALANCE, min_edge_pct=MIN_EDGE,
    )
    raw_candles = base_bt._fetch_coinbase_candles(days=DAYS + 1)
    print(f"  {len(raw_candles)} candles fetched. Running 3 variants...\n")

    variants = [
        ("Baseline",       "|mom| > 0.40%",          0.40, float("inf")),
        ("Markov Strict",  "0.40% < |mom| < 0.60%",  0.40, 0.60),
        ("Markov Relaxed", "0.40% < |mom| < 1.00%",  0.40, 1.00),
    ]

    results = []
    for name, bounds_label, lower, upper in variants:
        bt = CachedBacktester(
            candles=raw_candles,
            mom_lower=lower,
            mom_upper=upper,
            asset=ASSET,
            days=DAYS,
            initial_balance=INITIAL_BALANCE,
            min_edge_pct=MIN_EDGE,
        )
        summary, _ = bt.run()
        results.append((name, bounds_label, summary))
        print(f"  {name:<20} trades={summary.n_trades:4d}  "
              f"wr={summary.win_rate:.1%}  sharpe={summary.sharpe_ratio:.3f}  "
              f"return={summary.total_return_pct:+.1f}%")

    print_comparison(results)


if __name__ == "__main__":
    main()
