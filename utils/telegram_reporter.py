"""
telegram_reporter.py
====================
ส่งรายงานสรุปประจำวันไป Telegram แบบสวยงาม

รัน standalone:
    python utils/telegram_reporter.py            # รายงานวันนี้
    python utils/telegram_reporter.py --test     # ส่ง test message
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.scan_log_loader import DEFAULT_SCAN_LOG_ROOT, load_scan_rows


# ── Scan log helpers ──────────────────────────────────────────────────────────

def _load_scan_csv(date_str: str, root: str | Path = DEFAULT_SCAN_LOG_ROOT) -> list[dict]:
    return load_scan_rows(date_str, root=root)


def _compute_stats(rows: list[dict]) -> dict:
    total      = len(rows)
    trades     = [r for r in rows if r.get("order_status") == "paper"]
    skipped    = [r for r in rows if r.get("signal") == "SKIP"]
    waits      = [r for r in rows if r.get("signal") == "wait"]

    asset_counts: dict[str, int] = defaultdict(int)
    for r in trades:
        asset_counts[r.get("asset", "?")] += 1

    # bankroll from last row
    bankroll = 0.0
    if rows:
        try:
            bankroll = float(rows[-1].get("bankroll", 0))
        except ValueError:
            bankroll = 0.0

    # daily P&L
    daily_pnl_pct = 0.0
    if rows:
        try:
            daily_pnl_pct = float(rows[-1].get("daily_pnl_pct", 0)) * 100
        except ValueError:
            pass

    # first/last timestamp
    first_ts = rows[0].get("timestamp_utc", "") if rows else ""
    last_ts  = rows[-1].get("timestamp_utc", "") if rows else ""

    return {
        "total_rows":    total,
        "n_trades":      len(trades),
        "n_skipped":     len(skipped),
        "n_wait":        len(waits),
        "asset_counts":  dict(asset_counts),
        "bankroll":      bankroll,
        "daily_pnl_pct": daily_pnl_pct,
        "first_ts":      first_ts,
        "last_ts":       last_ts,
    }


# ── Message builder ───────────────────────────────────────────────────────────

def _bar(n: int, max_n: int, width: int = 8) -> str:
    filled = round((n / max_n) * width) if max_n > 0 else 0
    return "█" * filled + "░" * (width - filled)


def build_daily_message(date_str: str | None = None) -> str:
    tz_th  = ZoneInfo("Asia/Bangkok")
    now    = datetime.now(tz_th)
    date_str = date_str or now.strftime("%Y-%m-%d")

    # ── Thai date label ───────────────────────────────────────────────────────
    months_th = [
        "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
        "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
    ]
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        thai_year = dt.year + 543
        date_label = f"{dt.day} {months_th[dt.month]} {thai_year}"
    except ValueError:
        date_label = date_str

    rows  = _load_scan_csv(date_str)
    stats = _compute_stats(rows)

    bankroll      = stats["bankroll"]
    n_trades      = stats["n_trades"]
    n_skipped     = stats["n_skipped"]
    n_wait        = stats["n_wait"]
    total_rows    = stats["total_rows"]
    asset_counts  = stats["asset_counts"]
    daily_pnl_pct = stats["daily_pnl_pct"]
    pnl_usd       = bankroll * daily_pnl_pct / 100

    # P&L display
    pnl_sign  = "+" if pnl_usd >= 0 else ""
    pnl_emoji = "📈" if pnl_usd >= 0 else "📉"
    pnl_str   = f"{pnl_sign}${abs(pnl_usd):.4f}  ({pnl_sign}{daily_pnl_pct:.2f}%)"

    # Asset signal bar chart
    max_count  = max(asset_counts.values(), default=1)
    asset_lines = ""
    for asset, count in sorted(asset_counts.items(), key=lambda x: -x[1]):
        bar = _bar(count, max_count)
        asset_lines += f"  {asset:<5} {bar}  {count}\n"
    if not asset_lines:
        asset_lines = "  ไม่มี signal วันนี้\n"

    # Mode badge
    mode_badge = "🟡 PAPER TRADING"

    msg = (
        f"🤖 <b>PolyTrade Bot — Daily Report</b>\n"
        f"📅 {date_label}\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"💼 <b>Bankroll</b>\n"
        f"  └ <code>${bankroll:.4f} USDC</code>  {mode_badge}\n"
        f"\n"
        f"{pnl_emoji} <b>P&amp;L วันนี้</b>\n"
        f"  └ <code>{pnl_str}</code>\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"📡 <b>Signal Activity</b>\n"
        f"  ✅ Trades fired   <code>{n_trades} ไม้</code>\n"
        f"  ⏸ Wait signals   <code>{n_wait}</code>\n"
        f"  ⏭ Skip (noise)   <code>{n_skipped:,}</code>\n"
        f"  🔄 Total scans   <code>{total_rows:,}</code>\n"
        f"\n"
        f"📊 <b>Signals by Asset</b>\n"
        f"<pre>{asset_lines}</pre>"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"📐 <b>Strategy Edge (Backtest)</b>\n"
        f"  BTC 60d  <code>+100%  WR 55.9%  📐 1.18</code>\n"
        f"  ETH 60d  <code>+134%  WR 54.6%  📐 0.82</code>\n"
        f"  BTC 90d  <code>+159%  WR 54.7%  📐 0.85</code>\n"
        f"  Breakeven <code>51.02%</code>  →  Current WR <code>55.9% ✅</code>\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"⚠️ <b>Blockers ก่อน Live</b>\n"
        f"  🔴 MATIC = 0  →  เติม ~0.5 MATIC\n"
        f"  🔴 CLOB  = $0 →  deposit USDC\n"
        f"  🟡 Token IDs  →  wire ก่อน go-live\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ Paper deadline: <b>พรุ่งนี้ ~21:15</b>\n"
        f"🎯 เติม MATIC → go-live คืนพรุ่งนี้"
    )
    return msg


def build_startup_alert(
    mode: str,
    status: str,
    interval: int,
    bankroll: float,
    paper: bool,
    wallet: str = "",
    balance_source: str = "",
    wallet_balance: float | None = None,
    paper_cash: float | None = None,
    execution_mode: str = "",
    wallet_reference_error: str = "",
    gas_note: str = "Check MATIC before live orders",
    snipe_min_edge: float = 0.0,
    floor: float = 5.0,
    daily_dd_limit: float = 0.10,
    max_open_positions: int = 0,
) -> str:
    mode_tag = "🟢 LIVE" if not paper else "🟡 PAPER"
    status_tag = "🟢 CONNECTED" if status == "CONNECTED" else "🔴 CONNECTION FAILED"
    wallet_short = f"{wallet[:6]}...{wallet[-4:]}" if wallet else "N/A"
    source_label = balance_source or ("paper_virtual" if paper else "clob_collateral")
    execution_label = execution_mode or ("PAPER ONLY" if paper else "LIVE")
    wallet_line = ""
    if wallet_balance is not None:
        wallet_line = f"  â€¢ Wallet Bankroll <code>${float(wallet_balance):.4f} USDC</code>  REFERENCE ONLY\n"
    paper_cash_line = ""
    if paper and paper_cash is not None:
        paper_cash_line = f"  â€¢ Paper Cash  <code>${float(paper_cash):.4f} USDC</code>\n"
    fallback_line = ""
    if wallet_reference_error:
        fallback_line = "  â€¢ Warning     <code>Wallet bankroll unavailable, fallback to paper_virtual</code>\n"
    return (
        f"🚀 <b>PolyTrade Bot Started</b>  {mode_tag}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧭 <b>Runtime</b>\n"
        f"  • Mode        <code>{escape(mode)}</code>\n"
        f"  • Status      <code>{status_tag}</code>\n"
        f"  • Scan Loop   <code>{interval}s</code>\n"
        f"  • Strategy    <code>Polymarket 5m Counter-Momentum</code>\n"
        f"\n"
        f"💼 <b>Capital</b>\n"
        f"  • Bankroll    <code>${bankroll:.4f} USDC</code>\n"
        f"  • Source      <code>{escape(source_label)}</code>\n"
        f"{wallet_line}"
        f"{paper_cash_line}"
        f"{fallback_line}"
        f"  • Floor Stop  <code>${floor:.2f}</code>\n"
        f"  • Daily DD    <code>{daily_dd_limit * 100:.0f}% hard stop</code>\n"
        f"  • Open Slots  <code>{max_open_positions}</code>\n"
        f"\n"
        f"🎯 <b>Execution Watch</b>\n"
        f"  • Execution   <code>{escape(execution_label)}</code>\n"
        f"  • Live Orders <code>{'NO LIVE ORDERS' if paper else 'ENABLED'}</code>\n"
        f"  • Snipe Edge  <code>{snipe_min_edge * 100:.1f}%+</code>\n"
        f"  • Wallet      <code>{wallet_short}</code>\n"
        f"  • Gas         <code>{escape(gas_note)}</code>\n"
        f"\n"
        f"📩 <b>You will receive alerts for:</b>\n"
        f"  🟢 Entry opened | 🔴 Stop loss | 💰 Take profit\n"
        f"  🏁 Settlement result | 🛑 Risk pause | ❌ Errors\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )


def build_trade_alert(
    asset: str,
    signal: str,
    momentum_pct: float,
    score: float,
    position_size: float,
    bankroll: float,
    entry_price: float = 0.50,
    ptb_display: str = "N/A",
    paper: bool = True,
    confidence: float = 0.0,
    edge_pct: float = 0.0,
    shares: float = 0.0,
    stop_loss: float = 0.0,
    take_profit: float = 0.0,
    order_id: str = "",
    strategy: str = "auto",
    risk_tier: str = "",
) -> str:
    mode_tag = "🟡 PAPER" if paper else "🟢 LIVE"
    direction = "🔴 NO (revert down)" if signal == "NO" else "🟢 YES (revert up)"
    order_line = f"  • Order ID    <code>{escape(order_id)}</code>\n" if order_id else ""
    return (
        f"🔔 <b>ENTRY OPENED</b>  {mode_tag}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🪙 <b>Market</b>\n"
        f"  • Asset       <code>{escape(asset)}</code>\n"
        f"  • Signal      <code>{direction}</code>\n"
        f"  • Strategy    <code>{escape(strategy.upper())}</code>\n"
        f"  • Risk Tier   <code>{escape(risk_tier.upper() or 'N/A')}</code>\n"
        f"\n"
        f"📊 <b>Signal Quality</b>\n"
        f"  • Score       <code>{score:.2f}</code>\n"
        f"  • Confidence  <code>{confidence:.1%}</code>\n"
        f"  • Edge        <code>{edge_pct:+.2f}%</code>\n"
        f"  • Momentum    <code>{momentum_pct:+.3f}%</code>\n"
        f"\n"
        f"💵 <b>Order</b>\n"
        f"  • Entry       <code>{entry_price:.4f}</code>\n"
        f"  • Shares      <code>{shares:.4f}</code>\n"
        f"  • Cost        <code>${position_size:.4f}</code>\n"
        f"  • Stop Loss   <code>{stop_loss:.4f}</code>\n"
        f"  • Take Profit <code>{take_profit:.4f}</code>\n"
        f"{order_line}"
        f"\n"
        f"📍 <b>Window</b>\n"
        f"  • PTB         <code>{escape(ptb_display)}</code>\n"
        f"  • Bankroll    <code>${bankroll:.4f}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )


def build_exit_alert(
    title: str,
    asset: str,
    side: str,
    entry_price: float,
    exit_price: float,
    pnl: float,
    bankroll: float,
    reason: str,
    paper: bool = True,
    shares: float = 0.0,
    unrealized_pct: float = 0.0,
    countdown: int | None = None,
) -> str:
    mode_tag = "🟡 PAPER" if paper else "🟢 LIVE"
    win = pnl >= 0
    result_tag = "🟢 PROFIT" if win else "🔴 LOSS"
    pnl_str = f"+${pnl:.4f}" if win else f"-${abs(pnl):.4f}"
    pct_line = f"  • Move        <code>{unrealized_pct:+.2f}%</code>\n" if unrealized_pct else ""
    countdown_line = f"  • Countdown   <code>{countdown}s</code>\n" if countdown is not None else ""
    return (
        f"{'💰' if win else '🛑'} <b>{escape(title)}</b>  {mode_tag}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏁 <b>Exit Result</b>\n"
        f"  • Result      <code>{result_tag}</code>\n"
        f"  • Asset       <code>{escape(asset)}</code>\n"
        f"  • Side        <code>{escape(side)}</code>\n"
        f"  • Reason      <code>{escape(reason)}</code>\n"
        f"{countdown_line}"
        f"\n"
        f"💵 <b>P&amp;L</b>\n"
        f"  • Entry       <code>{entry_price:.4f}</code>\n"
        f"  • Exit        <code>{exit_price:.4f}</code>\n"
        f"  • Shares      <code>{shares:.4f}</code>\n"
        f"{pct_line}"
        f"  • P&amp;L        <code>{pnl_str}</code>\n"
        f"  • Bankroll    <code>${bankroll:.4f}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )


def build_floor_breach_alert(balance: float, floor: float) -> str:
    return (
        f"🛑 <b>FLOOR BREACH — Trading Suspended</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 Balance    <code>${balance:.4f}</code>\n"
        f"🚧 Floor      <code>${floor:.2f}</code>\n"
        f"📉 Deficit    <code>${floor - balance:.4f}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Bot หยุดเทรดทุก position\n"
        f"💡 เติม USDC ให้ balance &gt; ${floor:.2f} เพื่อ resume"
    )


def build_loss_cluster_alert(streak: int, pause_minutes: int, bankroll: float) -> str:
    return (
        f"⏸ <b>Loss Cluster — Trading Paused</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"❌ แพ้ติดกัน   <code>{streak} ไม้</code>\n"
        f"⏱ พักอีก     <code>{pause_minutes} นาที</code>\n"
        f"💼 Bankroll   <code>${bankroll:.4f}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 Bot จะ resume อัตโนมัติหลังพัก"
    )


def build_daily_drawdown_alert(dd_pct: float, limit_pct: float, bankroll: float) -> str:
    return (
        f"🚨 <b>Daily Drawdown Limit Hit</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📉 Drawdown   <code>{dd_pct:.1f}%</code>\n"
        f"🚧 Limit      <code>{limit_pct:.0f}%</code>\n"
        f"💼 Bankroll   <code>${bankroll:.4f}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⛔ หยุดเทรดวันนี้ — จะ resume พรุ่งนี้ 00:00"
    )


def build_error_alert(module: str, message: str, level: str = "ERROR") -> str:
    safe  = message.replace("<", "&lt;").replace(">", "&gt;")
    emoji = "🏮 <b>CRITICAL</b>" if level == "CRITICAL" else "❌ <b>ERROR</b>"
    return (
        f"{emoji}  —  <code>{module}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{safe[:400]}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )


# ── Send helpers ──────────────────────────────────────────────────────────────

def send_daily_report(date_str: str | None = None) -> bool:
    from utils.logger import get_telegram_notifier
    tg = get_telegram_notifier()
    if tg is None:
        print("[telegram_reporter] notifier not initialised — call setup_logging() first")
        return False
    msg = build_daily_message(date_str)
    tg.send_message(msg)
    return True


def send_message_direct(text: str) -> bool:
    """ส่ง HTML message ตรงๆ โดยไม่ต้องผ่าน setup_logging()"""
    try:
        from config.settings import get_settings
        settings = get_settings()
        token   = settings.telegram_bot_token.get_secret_value()
        chat_id = settings.telegram_chat_id.get_secret_value()
        if not token or not chat_id:
            print("[telegram_reporter] TELEGRAM_BOT_TOKEN / CHAT_ID missing in .env")
            return False
        from utils.logger import TelegramNotifier
        notifier = TelegramNotifier(token, chat_id)
        notifier._send_blocking(text)
        return True
    except Exception as e:
        print(f"[telegram_reporter] send failed: {e}")
        return False

def build_settlement_alert(
    asset: str,
    won: bool,
    pnl: float,
    bankroll: float,
    paper: bool = True,
    entry_price: float = 0.0,
    exit_price: float = 1.0,
    shares: float = 0.0,
    side: str = "",
    reason: str = "binary settlement",
) -> str:
    mode_tag = "🟡 PAPER" if paper else "🟢 LIVE"
    result = "🟢 WIN" if won else "🔴 LOSS"
    pnl_str = f"+${abs(pnl):.4f}" if won else f"-${abs(pnl):.4f}"
    side_line = f"  • Side        <code>{escape(side)}</code>\n" if side else ""
    price_lines = ""
    if entry_price > 0:
        price_lines = (
            f"  • Entry       <code>{entry_price:.4f}</code>\n"
            f"  • Exit        <code>{exit_price:.4f}</code>\n"
            f"  • Shares      <code>{shares:.4f}</code>\n"
        )
    return (
        f"🏁 <b>POSITION SETTLED</b>  {mode_tag}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Result</b>\n"
        f"  • Outcome     <code>{result}</code>\n"
        f"  • Asset       <code>{escape(asset)}</code>\n"
        f"{side_line}"
        f"  • Reason      <code>{escape(reason)}</code>\n"
        f"\n"
        f"💵 <b>P&amp;L</b>\n"
        f"{price_lines}"
        f"  • P&amp;L        <code>{pnl_str}</code>\n"
        f"  • Bankroll    <code>${bankroll:.4f}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="PolyTrade Telegram Reporter")
    parser.add_argument("--date", default=None, help="วันที่ YYYY-MM-DD (default: วันนี้)")
    parser.add_argument("--test", action="store_true", help="ส่ง test ping message")
    parser.add_argument("--preview", action="store_true", help="แสดง message โดยไม่ส่ง")
    args = parser.parse_args()

    if args.test:
        msg = (
            "✅ <b>PolyTrade Bot — Connection Test</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Telegram integration ทำงานปกติ 🎉\n"
            f"⏰ <code>{datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%Y-%m-%d %H:%M:%S')} (TH)</code>"
        )
        ok = send_message_direct(msg)
        print("✅ Sent!" if ok else "❌ Failed")
        return

    msg = build_daily_message(args.date)

    if args.preview:
        # strip HTML tags for terminal preview
        import re
        plain = re.sub(r"<[^>]+>", "", msg)
        print(plain)
        return

    ok = send_message_direct(msg)
    print("✅ Report sent to Telegram!" if ok else "❌ Failed to send")


if __name__ == "__main__":
    main()
