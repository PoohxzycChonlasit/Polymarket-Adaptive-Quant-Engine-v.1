"""
hft/main.py
===========
Async HFT orchestrator for Polymarket 5-min BTC Up/Down markets.

Loop cadence: every LOOP_INTERVAL_SEC (default 10s).

Per iteration:
  1. Get current window state (YES/NO price, PTB, spot price).
  2. Compute HFT signal (p_model, EV, edge).
  3. If signal fires AND risk allows → place paper/live entry.
  4. Check open positions for TP/SL → close if hit.
  5. Detect window rollover → settle expired positions.
  6. Print real-time dashboard.

Run:
    python -m hft.main
    python -m hft.main --balance 100 --paper
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
import uuid
from datetime import datetime

# Windows UTF-8 fix
import io as _io
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
# Quiet noisy libraries
for _noisy in ("httpx", "httpcore", "websockets", "polymarket.market_feed"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

LOGGER = logging.getLogger("hft.main")

from hft import config as C
from hft.market_manager  import MarketManager, OpenPosition
from hft.signal_engine   import HFTSignalEngine, HFTSignal
from hft.risk_manager    import HFTRiskManager
from hft.execution_engine import ExecutionEngine
from hft.utils           import (
    CSVTradeLogger, TradeRecord, current_epoch, window_label,
    seconds_remaining, ev_for_yes, ev_for_no,
)


# ── Take-profit / Stop-loss thresholds ────────────────────────────────────────
TP_PCT = 0.08   # Sell if YES price moved +8% from entry (unrealized)
SL_PCT = 0.70   # Sell if losing > 70% of entry (binary = low liquidity near expiry)


# ── Dashboard ─────────────────────────────────────────────────────────────────

def _print_dashboard(
    cycle:     int,
    asset:     str,
    window:    object | None,
    signal:    HFTSignal | None,
    risk:      HFTRiskManager,
    stats:     dict,
    last_trade: str,
) -> None:
    sep  = "=" * 72
    secs = seconds_remaining() if window is None else getattr(window, "seconds_remaining", 0)
    ep   = current_epoch()
    wlbl = window_label(ep)

    spot  = getattr(window, "spot_price", 0.0)
    ptb   = getattr(window, "ptb", 0.0)
    yp    = getattr(window, "yes_price", 0.0)
    np_   = getattr(window, "no_price", 0.0)
    delta = (spot - ptb) / max(ptb, 1.0) * 100 if ptb > 0 else 0.0

    print(sep)
    print(
        f"  HFT | {datetime.now().strftime('%H:%M:%S')} | cycle={cycle} | "
        f"window={wlbl} | {secs:3d}s left | "
        f"paper={'YES' if C.PAPER_TRADING else 'NO'}"
    )
    print(sep)
    print(
        f"  {asset} spot=${spot:,.2f}  ptb=${ptb:,.2f}  delta={delta:+.3f}%  "
        f"YES={yp:.4f}  NO={np_:.4f}"
    )
    if signal and signal.side != "SKIP":
        print(
            f"  SIGNAL: {signal.side:3s} | p_model={signal.p_model:.4f} | "
            f"edge={signal.edge:+.4f} | EV={signal.ev:+.4f} | "
            f"mom={signal.momentum_pct:+.3f}% | rsi={signal.rsi:.1f}"
        )
    else:
        reason = getattr(signal, "skip_reason", "no_signal") if signal else "no_signal"
        print(f"  SIGNAL: SKIP ({reason})")

    winfo = risk.window_info(ep)
    print(
        f"  Risk:  bankroll=${risk.bankroll:.4f} | daily_pnl={risk.daily_pnl:+.4f} | "
        f"brier={risk.avg_brier:.4f}"
    )
    print(
        f"  Window: entries={winfo['entries']}/{C.MAX_ENTRIES_PER_WIN} | "
        f"exposure=${winfo['exposure']:.4f}/${winfo['max_exp']:.4f}"
    )
    print(
        f"  Today:  trades={stats['trades_today']} | "
        f"wr={stats['win_rate']:.1%} | pnl={stats['total_pnl']:+.4f} | "
        f"open={stats['open_count']}"
    )
    if last_trade:
        print(f"  Last:   {last_trade}")
    print(sep)
    print(flush=True)


# ── Position lifecycle helpers ─────────────────────────────────────────────────

async def _check_open_positions(
    asset:     str,
    market_mgr: MarketManager,
    risk_mgr:  HFTRiskManager,
    exec_eng:  ExecutionEngine,
    csv_log:   CSVTradeLogger | None,
    window:    object,
) -> str:
    """
    For each open position, check TP/SL.
    Returns a human-readable string describing any action taken.
    """
    actions = []
    for pos in market_mgr.open_positions(asset):
        current_price = (
            window.yes_price if pos.side == "YES" else window.no_price
        )
        unrealized = (current_price - pos.entry_price) / max(pos.entry_price, 1e-8)

        take_profit = unrealized >= TP_PCT
        stop_loss   = unrealized <= -SL_PCT
        expired     = window.epoch > pos.window_epoch  # new window started

        if not (take_profit or stop_loss or expired):
            continue

        reason = "TP" if take_profit else ("SL" if stop_loss else "EXPIRED")

        result = await exec_eng.exit(
            asset=asset, side=pos.side,
            exit_price=current_price, shares=pos.shares,
        )
        if result.status in ("paper", "filled"):
            pnl = pos.shares * (current_price - pos.entry_price)
            outcome = 1.0 if pnl > 0 else 0.0
            risk_mgr.register_exit(
                pnl_usd=pnl + pos.cost_usd,  # cost_usd returned + profit
                p_model=pos.p_model,
                outcome=outcome,
            )
            market_mgr.close_position(pos, current_price, pnl)
            msg = (
                f"[{reason}] {pos.side} exit={current_price:.4f} "
                f"pnl={pnl:+.4f} (entry={pos.entry_price:.4f})"
            )
            actions.append(msg)
            LOGGER.info("[HFT] Position closed: %s", msg)

    return " | ".join(actions)


# ── Main loop ─────────────────────────────────────────────────────────────────

async def run_hft(bankroll: float, paper: bool) -> None:
    # Override config with runtime args
    C.PAPER_TRADING = paper

    LOGGER.info(
        "HFT engine starting | bankroll=$%.2f paper=%s assets=%s loop=%ds",
        bankroll, paper, C.ACTIVE_ASSETS, C.LOOP_INTERVAL_SEC,
    )

    # Bootstrap Binance feed (fills 100 candles immediately via REST)
    LOGGER.info("Starting Binance WebSocket feed...")
    from polymarket.market_feed import get_feed
    feed = get_feed()
    # Wait for BTC feed to be ready (up to 30s)
    deadline = time.time() + 30
    while time.time() < deadline:
        if feed.is_ready("BTC"):
            break
        await asyncio.sleep(0.5)
    if not feed.is_ready("BTC"):
        LOGGER.warning("Binance feed not ready — signals may be degraded")
    else:
        LOGGER.info("Binance feed ready.")

    # Init components
    market_mgr = MarketManager()
    signal_eng = HFTSignalEngine()
    risk_mgr   = HFTRiskManager(initial_bankroll=bankroll)
    exec_eng   = ExecutionEngine(paper=paper)
    csv_log    = CSVTradeLogger(C.TRADES_CSV_PATH) if C.LOG_TRADES_CSV else None

    cycle      = 0
    last_trade = ""

    print("\n  HFT Engine running. Ctrl+C to stop.\n")

    while True:
        cycle += 1
        loop_start = time.monotonic()

        for asset in C.ACTIVE_ASSETS:
            try:
                await _process_asset(
                    asset, cycle, market_mgr, signal_eng, risk_mgr, exec_eng,
                    csv_log, last_trade,
                )
            except Exception as exc:
                LOGGER.exception("[HFT] Unhandled error for %s: %s", asset, exc)

        # Sleep remainder of loop interval
        elapsed = time.monotonic() - loop_start
        sleep_t = max(0.1, C.LOOP_INTERVAL_SEC - elapsed)
        await asyncio.sleep(sleep_t)


async def _process_asset(
    asset:      str,
    cycle:      int,
    market_mgr: MarketManager,
    signal_eng: HFTSignalEngine,
    risk_mgr:   HFTRiskManager,
    exec_eng:   ExecutionEngine,
    csv_log:    CSVTradeLogger | None,
    last_trade: str,
) -> None:
    # ── 1. Get market state ────────────────────────────────────────────────────
    window = market_mgr.get_window(asset)
    if window is None:
        LOGGER.warning("[HFT] No window state for %s — skipping cycle", asset)
        _print_dashboard(cycle, asset, None, None, risk_mgr,
                         market_mgr.get_stats(), last_trade)
        return

    # ── 2. Check existing positions (TP / SL / expiry) ────────────────────────
    action_msg = await _check_open_positions(
        asset, market_mgr, risk_mgr, exec_eng, csv_log, window,
    )
    if action_msg:
        last_trade = action_msg

    # ── 3. Global risk gate ────────────────────────────────────────────────────
    ok, block_reason = risk_mgr.can_trade()
    signal = None
    if ok:
        # ── 4. Compute signal ──────────────────────────────────────────────────
        signal = signal_eng.compute(
            asset       = asset,
            yes_price   = window.yes_price,
            no_price    = window.no_price,
            ptb         = window.ptb,
            spot_price  = window.spot_price,
            epoch       = window.epoch,
            imbalance   = 0.0,  # extend: pull from CLOB orderbook
        )

        # ── 5. Enter if signal fires ───────────────────────────────────────────
        if signal.side != "SKIP":
            size = risk_mgr.compute_size(
                p_model      = signal.p_model,
                entry_price  = signal.entry_price,
                window_epoch = window.epoch,
            )
            if size.allowed:
                result = await exec_eng.enter(
                    asset        = asset,
                    side         = signal.side,
                    entry_price  = signal.entry_price,
                    shares       = size.shares,
                )
                if result.status in ("paper", "filled"):
                    risk_mgr.register_entry(window.epoch, size.cost_usd)
                    pos = market_mgr.open_position(
                        asset        = asset,
                        window_epoch = window.epoch,
                        side         = signal.side,
                        entry_price  = result.filled_price,
                        shares       = result.filled_shares,
                        cost_usd     = size.cost_usd,
                        p_model      = signal.p_model,
                    )

                    trade_id = pos.pos_id
                    last_trade = (
                        f"ENTER {signal.side} | price={result.filled_price:.4f} | "
                        f"shares={result.filled_shares:.4f} | cost=${size.cost_usd:.4f} | "
                        f"EV={signal.ev:+.4f} edge={signal.edge:+.4f}"
                    )
                    LOGGER.info("[HFT] %s", last_trade)

                    if csv_log:
                        rec = TradeRecord(
                            trade_id          = trade_id,
                            timestamp         = datetime.now().isoformat(),
                            asset             = asset,
                            window_epoch      = window.epoch,
                            window_label      = window_label(window.epoch),
                            side              = signal.side,
                            entry_price       = result.filled_price,
                            shares            = result.filled_shares,
                            cost_usd          = size.cost_usd,
                            p_model           = signal.p_model,
                            edge              = signal.edge,
                            ev                = signal.ev,
                            momentum_pct      = signal.momentum_pct,
                            window_delta_pct  = signal.window_delta_pct,
                            rsi               = signal.rsi,
                            seconds_remaining = signal.seconds_remaining,
                            paper             = C.PAPER_TRADING,
                        )
                        csv_log.log(rec)
                else:
                    LOGGER.warning("[HFT] Order rejected: %s", result.error_msg)
            else:
                LOGGER.debug("[HFT] Size blocked: %s", size.block_reason)
    else:
        LOGGER.info("[HFT] Trade gate closed: %s", block_reason)

    # ── 6. Dashboard ──────────────────────────────────────────────────────────
    _print_dashboard(
        cycle=cycle, asset=asset, window=window, signal=signal,
        risk=risk_mgr, stats=market_mgr.get_stats(), last_trade=last_trade,
    )


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="HFT Engine — Polymarket 5-min BTC")
    parser.add_argument("--balance", type=float, default=100.0,
                        help="Starting virtual/real bankroll in USD (default: 100)")
    parser.add_argument("--paper",   action="store_true", default=True,
                        help="Paper trading mode (default: True)")
    parser.add_argument("--live",    action="store_true", default=False,
                        help="Enable live trading (overrides --paper)")
    parser.add_argument("--loop",    type=int,   default=None,
                        help="Loop interval in seconds (overrides config)")
    parser.add_argument("--assets",  type=str,   default=None,
                        help="Comma-separated assets, e.g. BTC,ETH")
    args = parser.parse_args()

    if args.live:
        args.paper = False
    if args.loop:
        C.LOOP_INTERVAL_SEC = args.loop
    if args.assets:
        C.ACTIVE_ASSETS = [a.strip().upper() for a in args.assets.split(",")]

    try:
        asyncio.run(run_hft(bankroll=args.balance, paper=args.paper))
    except KeyboardInterrupt:
        print("\n  HFT stopped by user.")


if __name__ == "__main__":
    main()
