"""
hft_paper_run.py
================
HFT paper trade — Tiered Signal System  (Rich terminal display)
"""
from __future__ import annotations
import argparse, asyncio, csv, io, logging, sys, time, uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8","utf_8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.WARNING, format="%(asctime)s | %(message)s")
for n in ("httpx","httpcore","websockets","hpack","polymarket.market_feed",
          "polymarket.gamma_fetcher","polymarket.quant_indicators"):
    logging.getLogger(n).setLevel(logging.ERROR)

# ── Config ──────────────────────────────────────────────────────────────────────
BALANCE        = 100.0
LOOP_SEC       = 10
TP_PCT         = 0.06    # Take Profit 6%
SL_PCT         = 0.40    # Stop Loss 40%
FLOOR_USD      = 5.0     # หยุดทุกอย่างถ้า bankroll ต่ำกว่านี้

# Tiered signal thresholds
STRONG_EV      = 0.025;  STRONG_EDGE = 0.040;  STRONG_BET  = 1.50;  STRONG_MAX = 3
MEDIUM_EV      = 0.008;  MEDIUM_EDGE = 0.015;  MEDIUM_BET  = 0.75;  MEDIUM_MAX = 2
WEAK_EV        = 0.002;  WEAK_EDGE   = 0.005;  WEAK_BET    = 0.30;  WEAK_MAX   = 2

MAX_WINDOW_EXP = 0.10    # สูงสุด 10% ของ bankroll ต่อ window
ENTRY_MIN_SECS = 20      # เข้าได้จนถึง 20s ก่อนจบ window
ENTRY_MAX_SECS = 280     # เริ่มเข้าได้หลัง 20s แรก

TRADES_CSV     = Path("runtime/hft_trades.csv")
# ───────────────────────────────────────────────────────────────────────────────

_CSV_HEADER = [
    "trade_id","timestamp","asset","window_epoch","side",
    "entry_price","shares","cost_usd","bet_tier",
    "p_model","edge","ev","momentum_pct","window_delta_pct","rsi",
    "secs_at_entry","exit_price","pnl_usd","outcome","bankroll_after",
]

def _ensure_trade_log_schema() -> None:
    TRADES_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not TRADES_CSV.exists() or TRADES_CSV.stat().st_size == 0:
        with TRADES_CSV.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(_CSV_HEADER)
        return
    with TRADES_CSV.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        existing_header = next(reader, [])
    if existing_header != _CSV_HEADER:
        backup = TRADES_CSV.with_name(
            f"{TRADES_CSV.stem}.legacy_{datetime.now().strftime('%Y%m%d_%H%M%S')}{TRADES_CSV.suffix}"
        )
        TRADES_CSV.replace(backup)
        print(f"  [LOG] Existing trade CSV schema changed; archived old log to {backup}", flush=True)
        with TRADES_CSV.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(_CSV_HEADER)


def _log_trade(row: dict) -> None:
    _ensure_trade_log_schema()
    with TRADES_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_CSV_HEADER, extrasaction="ignore")
        w.writerow(row)


@dataclass
class Position:
    side: str
    entry_price: float
    shares: float
    cost: float
    p_model: float
    bet_tier: str       # "STRONG" | "MEDIUM" | "WEAK"
    entry_time: float
    window_epoch: int
    trade_id: str
    edge: float = 0.0
    ev: float = 0.0
    momentum_pct: float = 0.0
    window_delta_pct: float = 0.0
    rsi: float = 50.0
    secs_at_entry: int = 0

    def unrealized(self, cur: float) -> float:
        return (cur - self.entry_price) / max(self.entry_price, 1e-8)

    def pnl(self, exit_price: float) -> float:
        return round(self.shares * (exit_price - self.entry_price), 4)

def current_epoch():
    now = int(time.time())
    return now - (now % 300)

def secs_left(epoch=None):
    ep = epoch or current_epoch()
    return max(0, ep + 300 - int(time.time()))


# ── Market cache ───────────────────────────────────────────────────────────────
_ptb_cache: dict = {}

async def fetch_market():
    from polymarket.gamma_fetcher import GammaFetcher
    from polymarket.market_feed import get_feed

    spot  = get_feed().get_live_price("BTC")
    epoch = current_epoch()

    if epoch not in _ptb_cache:
        _ptb_cache.clear()
        _ptb_cache[epoch] = spot

    f = GammaFetcher()
    m = f.get_exact_5min_ptb("BTC") or f.get_current_5min_market("BTC")

    if m:
        yes_price = float(m.yes_price)
        no_price  = float(getattr(m, "no_price", 1.0 - yes_price))
        ptb       = float(getattr(m, "price_to_beat", 0.0)) or _ptb_cache.get(epoch, spot)
        slug      = m.slug
    else:
        yes_price = 0.5; no_price = 0.5
        ptb       = _ptb_cache.get(epoch, spot)
        slug      = "unknown"

    return yes_price, no_price, ptb, spot, slug


# ── Tiered Signal Engine ───────────────────────────────────────────────────────

def compute_tiered_signal(asset, yes_price, no_price, spot, ptb, epoch):
    """
    คำนวณ signal 3 ระดับ — ไม่มี flat filter สำหรับ WEAK tier
    ทุก cycle หา best side (YES/NO) แล้ว classify ตาม EV/Edge

    Returns: list of (tier, side, entry_price, p_model, ev, edge, mom, delta, rsi)
             เรียงจากแรงที่สุดก่อน
    """
    import math
    import numpy as np
    from polymarket.market_feed import get_feed

    feed = get_feed()
    df1m = feed.get_candles_df(asset, "1m")
    df5m = feed.get_candles_df(asset, "5m")

    if df1m.empty or len(df1m) < 5:
        return []

    # RSI-14
    delta  = df1m["close"].diff().iloc[-15:]
    g = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean().iloc[-1]
    l = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().iloc[-1]
    rsi = 100 - 100 / (1 + g / max(l, 1e-8))

    # 3-candle momentum
    mom = 0.0
    if len(df1m) >= 4:
        mom = (float(df1m["open"].iloc[-1]) - float(df1m["close"].iloc[-4])) \
              / max(float(df1m["close"].iloc[-4]), 1.0) * 100.0

    # Window delta
    if ptb > 0:
        win_delta = (spot - ptb) / ptb * 100.0
    elif len(df5m) >= 2:
        pc = float(df5m["close"].iloc[-2])
        cc = float(df5m["close"].iloc[-1])
        win_delta = (cc - pc) / max(pc, 1.0) * 100.0
    else:
        win_delta = 0.0

    # p_model
    progress = 1.0 - secs_left(epoch) / 300.0
    sigma    = 2.0 + 3.0 * progress      # ยิ่งใกล้จบ ยิ่ง sensitive
    p_delta  = 1.0 / (1.0 + math.exp(-win_delta * sigma / 100.0 * 80))

    # Adjustments
    mom_adj = 0.0
    if abs(mom) > 0.3 and secs_left(epoch) > 90:
        if math.copysign(1, win_delta) == math.copysign(1, mom):
            mom_adj = -0.02
        else:
            mom_adj = +0.015

    rsi_adj  = -0.04 if rsi > 72 else (0.04 if rsi < 28 else 0.0)
    late_adj = 0.0
    if secs_left(epoch) < 60 and abs(win_delta) > 0.05:
        # ใกล้จบ window + delta ชัด → เพิ่ม confidence
        late_adj = 0.03 * (1 if win_delta > 0 else -1)

    p_yes = min(0.96, max(0.04, p_delta + mom_adj + rsi_adj + late_adj))
    p_no  = 1.0 - p_yes

    fee = 0.002
    ev_yes   = p_yes - yes_price - fee
    ev_no    = p_no  - no_price  - fee
    edge_yes = p_yes - yes_price
    edge_no  = p_no  - no_price

    signals = []

    # ประเมิน YES
    for side, ep, pm, ev, edge in [
        ("YES", yes_price, p_yes, ev_yes, edge_yes),
        ("NO",  no_price,  p_no,  ev_no,  edge_no),
    ]:
        if ev <= 0 or edge <= 0:
            continue
        if ev >= STRONG_EV and edge >= STRONG_EDGE:
            tier = "STRONG"
        elif ev >= MEDIUM_EV and edge >= MEDIUM_EDGE:
            tier = "MEDIUM"
        elif ev >= WEAK_EV and edge >= WEAK_EDGE:
            tier = "WEAK"
        else:
            continue
        signals.append((tier, side, ep, pm, ev, edge, mom, win_delta, rsi))

    # เรียง: STRONG → MEDIUM → WEAK แล้ว EV สูงก่อน
    order = {"STRONG": 0, "MEDIUM": 1, "WEAK": 2}
    signals.sort(key=lambda x: (order[x[0]], -x[4]))
    return signals


# ── Close trade logger ─────────────────────────────────────────────────────────

def _close_trade(pos: Position, exit_price: float, bankroll: float) -> float:
    pnl = pos.pnl(exit_price)
    _log_trade({
        "trade_id":         pos.trade_id,
        "timestamp":        datetime.now().isoformat(timespec="seconds"),
        "asset":            "BTC",
        "window_epoch":     pos.window_epoch,
        "side":             pos.side,
        "entry_price":      pos.entry_price,
        "shares":           round(pos.shares, 6),
        "cost_usd":         pos.cost,
        "bet_tier":         pos.bet_tier,
        "p_model":          round(pos.p_model, 4),
        "edge":             round(pos.edge, 4),
        "ev":               round(pos.ev, 4),
        "momentum_pct":     round(pos.momentum_pct, 4),
        "window_delta_pct": round(pos.window_delta_pct, 4),
        "rsi":              round(pos.rsi, 2),
        "secs_at_entry":    pos.secs_at_entry,
        "exit_price":       exit_price,
        "pnl_usd":          pnl,
        "outcome":          "win" if pnl > 0 else "loss",
        "bankroll_after":   round(bankroll + pos.cost + pnl, 4),
    })
    return pnl


# ── Window settlement ──────────────────────────────────────────────────────────

def settle_positions(positions, spot, ptb, bankroll, closed, display=None):
    yes_won = spot > ptb
    for pos in positions:
        exit_price = (1.0 if yes_won else 0.0) if pos.side == "YES" else (0.0 if yes_won else 1.0)
        p = _close_trade(pos, exit_price, bankroll)
        bankroll += pos.cost + p
        trade = {"side": pos.side, "pnl": p, "tier": pos.bet_tier,
                 "entry": pos.entry_price, "exit": exit_price,
                 "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                 "reason": "win" if p > 0 else "loss"}
        closed.append(trade)
        if display:
            display.add_settled(trade)
    return closed, bankroll


# ── Main ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the HFT Polymarket paper trading loop.")
    parser.add_argument("--duration-hours", type=float, default=0.0, help="Stop after N hours; 0 means run forever.")
    parser.add_argument("--duration-minutes", type=float, default=0.0, help="Additional stop duration in minutes.")
    parser.add_argument("--balance", type=float, default=BALANCE, help=f"Starting paper bankroll, default ${BALANCE:.2f}.")
    parser.add_argument("--loop-sec", type=float, default=LOOP_SEC, help=f"Loop interval seconds, default {LOOP_SEC}.")
    parser.add_argument("--no-summary", action="store_true", help="Skip writing a summary when the run exits.")
    return parser.parse_args()


def _duration_seconds(hours: float, minutes: float) -> float | None:
    seconds = max(0.0, hours) * 3600.0 + max(0.0, minutes) * 60.0
    return seconds if seconds > 0 else None


def _write_summary() -> None:
    try:
        from scripts.hft_paper_summary import write_summary
        summary = write_summary(TRADES_CSV)
        print(f"\n  [SUMMARY] {summary['trades']} trades | WR={summary['win_rate_pct']:.1f}% "
              f"PnL=${summary['total_pnl_usd']:+.4f} | report={summary['markdown_path']}", flush=True)
    except Exception as exc:
        print(f"\n  [SUMMARY] Failed to write summary: {exc}", flush=True)


async def main(duration_seconds: float | None = None, balance: float = BALANCE, loop_sec: float = LOOP_SEC, write_final_summary: bool = True):
    from utils.display import HFTPaperDisplay

    deadline = time.time() + duration_seconds if duration_seconds else None
    _ensure_trade_log_schema()

    display = HFTPaperDisplay(
        balance=balance,
        floor_usd=FLOOR_USD,
        loop_sec=loop_sec,
        strong_bet=STRONG_BET,
        medium_bet=MEDIUM_BET,
        weak_bet=WEAK_BET,
        strong_max=STRONG_MAX,
        medium_max=MEDIUM_MAX,
        weak_max=WEAK_MAX,
        max_window_exp=MAX_WINDOW_EXP,
        tp_pct=TP_PCT,
        sl_pct=SL_PCT,
    )

    from polymarket.market_feed import get_feed
    feed = get_feed()
    for _ in range(20):
        if feed.is_ready("BTC"): break
        await asyncio.sleep(0.5)

    bankroll        = balance
    positions       = []
    closed          = []
    cycle           = 0
    last_epoch      = 0
    last_ptb        = 0.0
    window_side_lock: dict = {}   # epoch → "YES" | "NO"  (dominant side lock)

    with display:
        while True:
            cycle += 1
            epoch = current_epoch()
            sl    = secs_left(epoch)

            yes_price, no_price, ptb, spot, slug = await fetch_market()

            # ── window timestamp ──────────────────────────────────────────────
            now_ts   = int(time.time())
            win_start = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%H:%M")
            win_end   = datetime.fromtimestamp(epoch + 300, tz=timezone.utc).strftime("%H:%M")
            window_ts = f"{win_start}-{win_end}"

            # ── Window rollover ───────────────────────────────────────────────
            if epoch != last_epoch and last_epoch != 0 and positions:
                closed, bankroll = settle_positions(positions, spot, last_ptb, bankroll, closed, display)
                positions.clear()
            if epoch != last_epoch:
                window_side_lock.pop(last_epoch, None)
            last_epoch = epoch
            last_ptb   = ptb

            # ── TP / SL ───────────────────────────────────────────────────────
            still_open = []
            for pos in positions:
                cur = yes_price if pos.side == "YES" else no_price
                unr = pos.unrealized(cur)
                if unr >= TP_PCT:
                    p = _close_trade(pos, cur, bankroll)
                    bankroll += pos.cost + p
                    trade = {"side": pos.side, "pnl": p, "tier": pos.bet_tier,
                             "entry": pos.entry_price, "exit": cur,
                             "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                             "reason": "TP"}
                    closed.append(trade)
                    display.add_settled(trade)
                elif unr <= -SL_PCT:
                    p = _close_trade(pos, cur, bankroll)
                    bankroll += pos.cost + p
                    trade = {"side": pos.side, "pnl": p, "tier": pos.bet_tier,
                             "entry": pos.entry_price, "exit": cur,
                             "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                             "reason": "SL"}
                    closed.append(trade)
                    display.add_settled(trade)
                else:
                    still_open.append(pos)
            positions = still_open

            # ── Window exposure tracking ──────────────────────────────────────
            window_positions = [p for p in positions if p.window_epoch == epoch]
            window_cost      = sum(p.cost for p in window_positions)
            window_cap       = bankroll * MAX_WINDOW_EXP

            strong_count = sum(1 for p in window_positions if p.bet_tier == "STRONG")
            medium_count = sum(1 for p in window_positions if p.bet_tier == "MEDIUM")
            weak_count   = sum(1 for p in window_positions if p.bet_tier == "WEAK")

            # ── Signal computation ────────────────────────────────────────────
            entered_this_cycle = []
            stopping  = bool(deadline and time.time() >= deadline)
            can_enter = (
                ENTRY_MIN_SECS <= sl <= ENTRY_MAX_SECS
                and bankroll > FLOOR_USD
                and window_cost < window_cap
                and not stopping
            )
            signal_skip = ""
            sig_meta: dict = {}

            if can_enter:
                signals = compute_tiered_signal("BTC", yes_price, no_price, spot, ptb, epoch)
                if signals:
                    # extract meta from first signal
                    _s = signals[0]
                    sig_meta = {"mom": _s[6], "win_delta": _s[7], "rsi": _s[8]}
                    display.update_signals(signals, sig_meta)

                for tier, side, ep, pm, ev, edge, mom, wdelta, rsi in signals:
                    locked_side = window_side_lock.get(epoch)
                    if locked_side and side != locked_side:
                        continue
                    if tier == "STRONG" and strong_count >= STRONG_MAX: continue
                    if tier == "MEDIUM" and medium_count >= MEDIUM_MAX: continue
                    if tier == "WEAK"   and weak_count   >= WEAK_MAX:   continue

                    bet = {"STRONG": STRONG_BET, "MEDIUM": MEDIUM_BET, "WEAK": WEAK_BET}[tier]
                    if window_cost + bet > window_cap: break
                    if bankroll - bet < FLOOR_USD: break

                    shares      = bet / max(ep, 0.01)
                    bankroll   -= bet
                    window_cost += bet

                    pos = Position(
                        side=side, entry_price=ep, shares=shares,
                        cost=bet, p_model=pm, bet_tier=tier,
                        entry_time=time.time(), window_epoch=epoch,
                        trade_id=uuid.uuid4().hex[:10],
                        edge=edge, ev=ev,
                        momentum_pct=mom, window_delta_pct=wdelta,
                        rsi=rsi, secs_at_entry=sl,
                    )
                    positions.append(pos)
                    entered_this_cycle.append((tier, side, ep, shares, bet, pm, ev, edge))

                    if epoch not in window_side_lock:
                        window_side_lock[epoch] = side

                    if tier == "STRONG": strong_count += 1
                    elif tier == "MEDIUM": medium_count += 1
                    else: weak_count += 1
                    break

                if not signals:
                    signal_skip = "no edge this cycle"
            elif stopping:
                signal_skip = "stopping — no new entries"
            elif sl < ENTRY_MIN_SECS:
                signal_skip = f"too late ({sl}s < {ENTRY_MIN_SECS}s)"
            elif sl > ENTRY_MAX_SECS:
                signal_skip = f"too early ({sl}s > {ENTRY_MAX_SECS}s)"
            else:
                signal_skip = "floor/cap reached"

            # ── Update display ────────────────────────────────────────────────
            locked_side_display = window_side_lock.get(epoch, "FREE")

            display.update_market(
                spot=spot, ptb=ptb, yes=yes_price, no=no_price,
                countdown=sl, slug=slug, window_ts=window_ts,
            )
            display.update_cycle(
                cycle=cycle,
                bankroll=bankroll,
                positions=positions,
                closed=closed,
                strong_count=strong_count,
                medium_count=medium_count,
                weak_count=weak_count,
                window_cost=window_cost,
                window_cap=window_cap,
                locked_side=locked_side_display,
                can_enter=can_enter,
                signal_skip=signal_skip,
            )
            if not can_enter or not signals:
                display.update_signals([], sig_meta)

            if stopping:
                if not positions:
                    break

            await asyncio.sleep(loop_sec)

    if write_final_summary:
        _write_summary()


if __name__ == "__main__":
    args = _parse_args()
    try:
        asyncio.run(main(
            duration_seconds=_duration_seconds(args.duration_hours, args.duration_minutes),
            balance=args.balance,
            loop_sec=args.loop_sec,
            write_final_summary=not args.no_summary,
        ))
    except KeyboardInterrupt:
        print("\n  Stopped.", flush=True)
        if not args.no_summary:
            _write_summary()
