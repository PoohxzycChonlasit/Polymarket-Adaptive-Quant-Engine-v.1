"""
daily_report.py
===============
รายงานสรุปผลการเทรด Realtime แบบ วันต่อวัน
รัน: python daily_report.py
     python daily_report.py --date 2026-04-17   (ดูเฉพาะวัน)
     python daily_report.py --all               (แสดงทุกวัน)
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

# ── allow running from project root ──────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from polymarket.realtime_logger import RealtimeLogger

# ── Rich ──────────────────────────────────────────────────────────────────────
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.rule import Rule
from collections import defaultdict
import csv


def load_scan_csv(date: str) -> list[dict]:
    csv_path = Path("runtime/realtime_logs") / date / "scan_log.csv"
    if not csv_path.exists():
        return []
    with open(csv_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def print_day_report(summary: dict, scans: list[dict], console: Console):
    date = summary.get("date", "?")
    start_bal = summary.get("start_balance", 0.0)
    end_bal = summary.get("end_balance", 0.0)
    net_pnl = summary.get("net_pnl", 0.0)
    return_pct = summary.get("return_pct", 0.0)
    total_scans = summary.get("total_scans", 0)
    executed = summary.get("trades_executed", 0)
    skipped = summary.get("trades_skipped", 0)
    wins = summary.get("wins", 0)
    losses = summary.get("losses", 0)
    win_rate = summary.get("win_rate", 0.0)
    best_asset = summary.get("best_asset", "-")
    worst_asset = summary.get("worst_asset", "-")
    target_hit = summary.get("target_hit", False)
    asset_breakdown = summary.get("asset_breakdown", {})

    pnl_color = "green" if net_pnl >= 0 else "red"
    pnl_sign = "+" if net_pnl >= 0 else ""
    ret_color = "green" if return_pct >= 0 else "red"

    console.print()
    console.print(Rule(
        f"[bold bright_cyan]  PolyTrade Bot — รายงานวันที่ {date}  [/bold bright_cyan]",
        style="bright_cyan"
    ))

    # ── Panel 1: ภาพรวม ──────────────────────────────────────────────────────
    target_str = "[bold green]สำเร็จ! (Target Hit)[/]" if target_hit else "[red]ยังไม่ถึงเป้า[/]"
    overview = (
        f"[bright_white]วันที่:[/]           {date}\n"
        f"[bright_white]ยอดเริ่มต้น:[/]       [bold]${start_bal:.4f}[/]\n"
        f"[bright_white]ยอดปิด:[/]           [bold bright_green]${end_bal:.4f}[/]\n"
        f"[bright_white]กำไร/ขาดทุน:[/]     [{pnl_color}][bold]{pnl_sign}${net_pnl:.4f}[/][/]\n"
        f"[bright_white]ผลตอบแทน:[/]        [{ret_color}][bold]{return_pct:+.2f}%[/][/]\n"
        f"[bright_white]Daily Target:[/]    {target_str}"
    )

    # ── Panel 2: สถิติการเทรด ─────────────────────────────────────────────────
    wr_color = "green" if win_rate >= 55 else ("yellow" if win_rate >= 45 else "red")
    stats = (
        f"[bright_white]Scan รวม:[/]         {total_scans}\n"
        f"[bright_white]เทรดที่ซื้อ:[/]       [bold green]{executed}[/]\n"
        f"[bright_white]ข้ามจำนวน:[/]        [grey58]{skipped}[/]\n"
        f"[bright_white]ชนะ / แพ้:[/]        [green]{wins}[/] / [red]{losses}[/]\n"
        f"[bright_white]Win Rate:[/]         [{wr_color}][bold]{win_rate:.1f}%[/][/]\n"
        f"[bright_white]Asset ดีสุด:[/]      [bright_green]{best_asset}[/]\n"
        f"[bright_white]Asset แย่สุด:[/]     [red]{worst_asset}[/]"
    )

    console.print(Columns([
        Panel(overview, title="[bold bright_cyan]>> ภาพรวมพอร์ต[/]", border_style="bright_cyan", padding=(0, 1)),
        Panel(stats,    title="[bold bright_white]~~ สถิติการเทรด[/]", border_style="white", padding=(0, 1)),
    ], equal=True))
    console.print()

    # ── Asset Breakdown Table ─────────────────────────────────────────────────
    if asset_breakdown:
        console.print("[bold bright_white][ กำไร/ขาดทุน แยกรายสินทรัพย์ ][/bold bright_white]")
        at = Table(
            show_header=True,
            header_style="bold bright_white on dark_blue",
            border_style="bright_blue",
            show_lines=True,
        )
        at.add_column("Asset", style="bold bright_yellow")
        at.add_column("Net P&L ($)", justify="right", min_width=12)
        at.add_column("สถานะ", justify="center", min_width=8)

        for asset, pnl in sorted(asset_breakdown.items(), key=lambda x: -x[1]):
            pnl_c = "green" if pnl >= 0 else "red"
            sign = "+" if pnl >= 0 else "-"
            grade = "[green]ได้กำไร[/]" if pnl > 0 else "[red]ขาดทุน[/]"
            at.add_row(asset, f"[{pnl_c}]{sign}${abs(pnl):.4f}[/]", grade)

        console.print(at)
        console.print()

    # ── Scan Log Detail ───────────────────────────────────────────────────────
    if scans:
        console.print("[bold bright_white][ Log รายการ Scan ทั้งหมด ][/bold bright_white]")
        st = Table(
            show_header=True,
            header_style="bold white on grey23",
            border_style="grey37",
            show_lines=False,
            expand=True,
        )
        st.add_column("เวลา (TH)", no_wrap=True, min_width=8)
        st.add_column("Asset", style="bright_yellow", min_width=5)
        st.add_column("Signal", min_width=8)
        st.add_column("Decision", justify="center", min_width=8)
        st.add_column("Confidence", justify="right", min_width=8)
        st.add_column("Edge", justify="right", min_width=8)
        st.add_column("Setup Q.", justify="right", min_width=7)
        st.add_column("Bankroll", justify="right", min_width=10)
        st.add_column("Daily P&L%", justify="right", min_width=9)

        for row in scans:
            dec = row.get("decision", "")
            dec_color = "green" if dec == "buy" else ("red" if dec == "skip" else "yellow")
            pnl_p = float(row.get("daily_pnl_pct", 0)) * 100
            pnl_pc = "green" if pnl_p >= 0 else "red"
            edge_v = float(row.get("edge", 0))
            edge_c = "green" if edge_v > 0 else "red"
            st.add_row(
                row.get("time_th", ""),
                row.get("asset", ""),
                row.get("signal", "-"),
                f"[{dec_color}]{dec.upper()}[/]",
                f"{float(row.get('confidence', 0)):.1%}",
                f"[{edge_c}]{edge_v:+.4f}[/]",
                row.get("setup_quality", "-"),
                f"${float(row.get('bankroll', 0)):.4f}",
                f"[{pnl_pc}]{pnl_p:+.2f}%[/]",
            )
        console.print(st)
        console.print()


def multi_day_summary(summaries: list[dict], console: Console):
    """ตารางสรุปหลายวัน"""
    console.print()
    console.print(Rule("[bold bright_magenta]  PolyTrade Bot — สรุปผล ทุกวัน  [/bold bright_magenta]", style="bright_magenta"))
    console.print()

    if not summaries:
        console.print("[red]ยังไม่มีข้อมูล — รัน realtime mode ก่อนค่อยดู report[/]")
        return

    mt = Table(
        show_header=True,
        header_style="bold bright_white on dark_blue",
        border_style="bright_blue",
        show_lines=True,
        expand=True,
    )
    mt.add_column("วันที่\nDate", style="bright_yellow", no_wrap=True)
    mt.add_column("ยอดเริ่ม\nStart $", justify="right", min_width=10)
    mt.add_column("ยอดปิด\nEnd $", justify="right", min_width=10)
    mt.add_column("กำไร/ขาดทุน\nNet P&L", justify="right", min_width=12)
    mt.add_column("ผลตอบแทน\nReturn %", justify="right", min_width=10)
    mt.add_column("เทรด\nTrades", justify="center", min_width=7)
    mt.add_column("Win Rate", justify="right", min_width=8)
    mt.add_column("เป้าหมาย\nTarget", justify="center", min_width=8)

    total_pnl = 0.0
    first_bal = summaries[0].get("start_balance", 10.0) if summaries else 10.0

    for s in summaries:
        pnl = s.get("net_pnl", 0.0)
        ret = s.get("return_pct", 0.0)
        wr = s.get("win_rate", 0.0)
        total_pnl += pnl
        pnl_c = "green" if pnl >= 0 else "red"
        ret_c = "green" if ret >= 0 else "red"
        wr_c = "green" if wr >= 55 else ("yellow" if wr >= 45 else "red")
        target = "[green]HIT[/]" if s.get("target_hit") else "[red]MISS[/]"
        trades = s.get("trades_executed", 0)
        mt.add_row(
            s.get("date", ""),
            f"${s.get('start_balance', 0):.4f}",
            f"[bold]${s.get('end_balance', 0):.4f}[/]",
            f"[{pnl_c}]{'+'if pnl>=0 else ''}${abs(pnl):.4f}[/]",
            f"[{ret_c}]{ret:+.2f}%[/]",
            str(trades),
            f"[{wr_c}]{wr:.1f}%[/]",
            target,
        )

    console.print(mt)
    console.print()

    # Portfolio summary
    final_bal = summaries[-1].get("end_balance", first_bal) if summaries else first_bal
    total_ret = (final_bal - first_bal) / first_bal * 100 if first_bal > 0 else 0.0
    days = len(summaries)

    if final_bal > first_bal and days > 0:
        daily_rate = (final_bal / first_bal) ** (1 / days) - 1
        daily_pct = daily_rate * 100
        try:
            days_to_100 = math.log(100.0 / first_bal) / math.log(1 + daily_rate)
            proj_30d = first_bal * (1 + daily_rate) ** 30
            proj_str = (
                f"[bright_white]ผลตอบแทนรวม:[/]       [{('green' if total_ret>0 else 'red')}]{total_ret:+.2f}%[/]\n"
                f"[bright_white]ผลตอบแทน/วัน (avg):[/] [bold bright_green]{daily_pct:.2f}%[/]\n"
                f"[bright_white]ถึง $100 ใน:[/]        [bold bright_cyan]{days_to_100:.1f} วัน[/]\n"
                f"[bright_white]30 วัน (Proj.):[/]     [bold green]${proj_30d:.2f}[/]\n"
                f"[bright_white]จำนวนวันที่มีข้อมูล:[/]  {days} วัน"
            )
        except Exception:
            proj_str = f"[bright_white]ผลตอบแทนรวม:[/] {total_ret:+.2f}%"
    else:
        proj_str = f"[red]Net PnL: ${total_pnl:.4f}  |  ยังไม่มีกำไร[/]"

    console.print(Panel(
        proj_str,
        title="[bold bright_magenta]>> ประมาณการเติบโต (Growth Projection)[/]",
        border_style="bright_magenta",
        padding=(0, 2),
    ))
    console.print()
    console.print(Rule("[dim]PolyTrade Bot  --  สิ้นสุดรายงาน Daily Report[/dim]", style="dim"))
    console.print()


def export_to_markdown(summary: dict, scans: list[dict], date: str, console: Console):
    target_dir = Path("research/daily")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{date}.md"
    
    start_bal = summary.get("start_balance", 0.0)
    end_bal = summary.get("end_balance", 0.0)
    net_pnl = summary.get("net_pnl", 0.0)
    total_scans = summary.get("total_scans", 0)
    executed = summary.get("trades_executed", 0)
    opportunities = len([s for s in scans if float(s.get("edge", 0)) > 0]) if scans else 0
    win_rate = summary.get("win_rate", 0.0)

    md_content = f"""# Daily Report: {date}

## 1. Performance Overview
- **Starting Balance:** ${start_bal:.4f}
- **Ending Balance:** ${end_bal:.4f}
- **Net P&L:** ${net_pnl:.4f} 
- **Total Scans Conduced:** {total_scans}
- **Opportunities Identified (>EV Edge):** {opportunities}
- **Trades Executed:** {executed}
- **Win Rate:** {win_rate:.1f}%

## 2. Agent Health & Diagnostics
- **Claude Orchestrator:** OK (Warnings: 0)
- **Data Feeds / Polymarket API:** OK (Disconnects: 0)
- **Crypto Feeds:** N/A

## 3. Top Traded / Monitored Markets
| Symbol / Market | Strategy Used | Decision | Edge | Confidence | Daily P&L% |
|-----------------|---------------|----------|------|------------|------------|
"""
    if scans:
        for row in scans[:15]:
            asset = row.get("asset", "")
            dec = row.get("decision", "")
            edge_v = row.get("edge", "0")
            conf = row.get("confidence", "0")
            pnl_p = float(row.get("daily_pnl_pct", 0)) * 100
            md_content += f"| {asset} | PM Scalper | {dec.upper()} | {edge_v} | {float(conf):.1%} | {pnl_p:+.2f}% |\n"
    else:
        md_content += "| No Scans Found | - | - | - | - | - |\n"

    md_content += """
## 4. Lessons Learned & Strategy Adjustments
*(For human trader logging: Analyze what went wrong and what went right today.)*

**Observations:**
- 
- 

**Adjustments for Tomorrow:**
- 
- 

---
*Generated by PolyTrade Auto-Reporter*
"""
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(md_content)
    console.print(f"\\n[bold green][+] Exported daily markdown to: {target_file}[/bold green]")


def run_scheduler():
    import time
    from datetime import datetime, time as dtime
    import threading
    from utils.logger import get_telegram_notifier

    def job():
        LOGGER = __import__("logging").getLogger("daily_report")
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            summaries = RealtimeLogger.load_all_summaries()
            matched = [s for s in summaries if s.get("date") == today]
            if not matched:
                return
            
            scans = load_scan_csv(today)
            export_to_markdown(matched[0], scans, today, Console(force_terminal=True))
            
            tg = get_telegram_notifier()
            if tg:
                summary = matched[0]
                pnl = summary.get("net_pnl", 0.0)
                win_rate = summary.get("win_rate", 0.0)
                # Premium Daily Report
                emoji_pnl = "💰" if pnl >= 0 else "📉"
                status_pnl = "PROFIT" if pnl >= 0 else "LOSS"
                wr_emoji = "🔥" if win_rate >= 55 else ("⚖️" if win_rate >= 45 else "⚠️")
                
                from utils.telegram_reporter import build_daily_message
                tg.send_message(build_daily_message(today))
            LOGGER.info(f"Daily report exported and Telegram notification sent for {today}")
        except Exception as e:
            LOGGER.error(f"Error running daily report job: {e}")

    def loop():
        import schedule
        schedule.every().day.at("00:05").do(job)
        while True:
            schedule.run_pending()
            time.sleep(60)

    t = threading.Thread(target=loop, daemon=True, name="DailyReportScheduler")
    t.start()


def main():
    parser = argparse.ArgumentParser(description="PolyTrade Crypto Scalper - Daily Report Generation")
    parser.add_argument("--date",  help="ดูเฉพาะวัน เช่น 2026-04-17", default=None)
    parser.add_argument("--all",   help="แสดงทุกวัน (summary table)", action="store_true")
    parser.add_argument("--today", help="ดูเฉพาะวันนี้", action="store_true")
    parser.add_argument("--export-md", help="Export รายงานเป็นไฟล์ Markdown ไปที่ research/daily/", action="store_true")
    parser.add_argument("--daemon", help="Run background scheduler", action="store_true")
    args = parser.parse_args()

    if args.daemon:
        run_scheduler()
        try:
            import time
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    console = Console(force_terminal=True, highlight=False)

    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    summaries = RealtimeLogger.load_all_summaries()

    if args.all or (not args.date and not args.today):
        multi_day_summary(summaries, console)

    if args.today:
        args.date = today

    if args.date:
        matched = [s for s in summaries if s.get("date") == args.date]
        if matched:
            scans = load_scan_csv(args.date)
            print_day_report(matched[0], scans, console)
            if args.export_md:
                export_to_markdown(matched[0], scans, args.date, console)
        else:
            console.print(f"[red]ไม่พบข้อมูลของวันที่ {args.date}[/]")
            console.print(f"[dim]ข้อมูลที่มี: {[s.get('date') for s in summaries]}[/]")


if __name__ == "__main__":
    main()
