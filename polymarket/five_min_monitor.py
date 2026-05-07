"""
five_min_monitor.py
===================
Realtime monitor for Polymarket 5-minute crypto prediction markets

Shows Price To Beat vs Current Price for BTC, ETH, SOL, XRP, DOGE, HYPE, BNB
Refreshes every 30 seconds (configurable)

Usage:
    python polymarket/five_min_monitor.py
    python polymarket/five_min_monitor.py --interval 15 --once
"""
from __future__ import annotations

import argparse
import io
import logging
import signal
import sys
import time
from datetime import datetime, timezone

# Force UTF-8 output on Windows to avoid cp874 encoding errors
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from polymarket.price_to_beat_fetcher import PriceToBeatFetcher, MarketRound

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
LOGGER = logging.getLogger(__name__)
console = Console()

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

PRICE_FORMAT: dict[str, int] = {
    "BTC": 2,
    "ETH": 2,
    "SOL": 3,
    "XRP": 5,
    "DOGE": 5,
    "HYPE": 3,
    "BNB": 2,
}


def _fmt_price(asset: str, price: float) -> str:
    decimals = PRICE_FORMAT.get(asset, 4)
    if price == 0:
        return "N/A"
    return f"${price:,.{decimals}f}"


def _fmt_seconds(secs: float) -> str:
    if secs <= 0:
        return "[red]EXPIRED[/red]"
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    if m > 0:
        return f"{m}m {s:02d}s"
    return f"[bold yellow]{s}s[/bold yellow]"


def _direction_emoji(is_above: bool, pct: float) -> str:
    if abs(pct) < 0.01:
        return "⚡ FLAT"
    if is_above:
        return f"[green]🔼 +{pct:.3f}%[/green]"
    return f"[red]🔽 {pct:.3f}%[/red]"


def _signal_badge(yes_price: float) -> str:
    """Convert YES price to signal badge"""
    if yes_price >= 0.65:
        return "[bold green]^^ BULLISH[/bold green]"
    elif yes_price <= 0.35:
        return "[bold red]vv BEARISH[/bold red]"
    else:
        return "[yellow]-- NEUTRAL[/yellow]"


# ──────────────────────────────────────────────────────────────────────────────
# Table Builder
# ──────────────────────────────────────────────────────────────────────────────

ASSET_ORDER = ["BTC", "ETH", "SOL", "XRP", "DOGE", "HYPE", "BNB"]


def build_table(rounds: list[MarketRound], timestamp: str, errors: list[str]) -> Panel:
    """สร้าง Rich Table สำหรับแสดง Price To Beat monitor"""

    # สร้าง dict for lookup
    rounds_by_asset: dict[str, MarketRound] = {r.asset: r for r in rounds}

    # ── Table ──
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="bright_black",
        expand=True,
        title="",
        min_width=110,
    )

    table.add_column("Asset", style="bold white", width=8, justify="center")
    table.add_column("Price To Beat", style="bold", width=16, justify="right")
    table.add_column("Current Price", style="bold", width=16, justify="right")
    table.add_column("Diff vs PTB", width=18, justify="center")
    table.add_column("YES", width=8, justify="center")
    table.add_column("NO", width=8, justify="center")
    table.add_column("Signal", width=14, justify="center")
    table.add_column("⏱ Remaining", width=14, justify="center")
    table.add_column("Liquidity", width=12, justify="right")

    for asset in ASSET_ORDER:
        rnd = rounds_by_asset.get(asset)

        if rnd is None:
            # ไม่พบ market
            table.add_row(
                f"[dim]{asset}[/dim]",
                "[dim]—[/dim]",
                "[dim]—[/dim]",
                "[dim]No active market[/dim]",
                "[dim]—[/dim]",
                "[dim]—[/dim]",
                "[dim]—[/dim]",
                "[dim]—[/dim]",
                "[dim]—[/dim]",
            )
            continue

        # PTB color: green if current > PTB, red otherwise
        ptb_str = _fmt_price(asset, rnd.price_to_beat)
        if rnd.price_to_beat > 0:
            ptb_display = f"[bold yellow]{ptb_str}[/bold yellow]"
        else:
            ptb_display = f"[dim]{ptb_str}[/dim]"

        # Current price color
        if rnd.is_above_ptb:
            current_display = f"[bold green]{_fmt_price(asset, rnd.current_price)}[/bold green]"
        else:
            current_display = f"[bold red]{_fmt_price(asset, rnd.current_price)}[/bold red]"

        yes_display = f"[cyan]{rnd.yes_price:.2f}[/cyan]"
        no_display = f"[magenta]{rnd.no_price:.2f}[/magenta]"

        liq_str = f"${rnd.liquidity:,.0f}" if rnd.liquidity > 0 else "—"

        table.add_row(
            f"[bold]{rnd.symbol} {asset}[/bold]",
            ptb_display,
            current_display,
            _direction_emoji(rnd.is_above_ptb, rnd.price_diff_pct),
            yes_display,
            no_display,
            _signal_badge(rnd.yes_price),
            _fmt_seconds(rnd.seconds_remaining),
            liq_str,
        )

    # ── Header ──
    now_thai = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    found_count = len(rounds_by_asset)

    title_line = Text()
    title_line.append("🎯 Polymarket 5-Min Price To Beat Monitor", style="bold cyan")
    title_line.append(f"  │  {now_thai}", style="dim")
    title_line.append(f"  │  {found_count}/7 markets active", style="green" if found_count == 7 else "yellow")

    # ── Errors ──
    error_text = ""
    if errors:
        error_text = f"\n[red]⚠ Errors: {' | '.join(errors[:3])}[/red]"

    content = Text.assemble(title_line, "\n")

    # Build panel with table inside
    from rich.console import Group
    from rich import get_console

    panel_content = Group(
        Text.from_markup(f"  {title_line.plain}"),
        table,
    )
    # Simple layout
    header = f"[bold cyan]Polymarket - 5-Min Price To Beat Monitor[/bold cyan]  [dim]{now_thai}[/dim]  [{'green' if found_count == 7 else 'yellow'}]{found_count}/7 markets[/{'green' if found_count == 7 else 'yellow'}]"
    if errors:
        header += f"\n[red dim]WARN: {' | '.join(errors[:2])}[/red dim]"

    panel = Panel(
        table,
        title=Text.from_markup(header),
        border_style="cyan",
        padding=(0, 1),
    )
    return panel


# ──────────────────────────────────────────────────────────────────────────────
# Monitor Loop
# ──────────────────────────────────────────────────────────────────────────────


def run_monitor(interval: int = 30, once: bool = False) -> None:
    """
    Main monitor loop
    
    Args:
        interval: วินาทีระหว่าง refresh (default=30)
        once: ถ้า True แสดงครั้งเดียวแล้วออก
    """
    _stop = [False]

    def _handle_sigint(sig: int, frame: object) -> None:  # noqa: ANN001
        _stop[0] = True
        console.print("\n[yellow]⛔ Stopping monitor...[/yellow]")

    signal.signal(signal.SIGINT, _handle_sigint)

    console.print(
        Panel(
            "[cyan]PolyTrade Crypto Scalper[/cyan] - 5-Min Price To Beat Monitor\n"
            f"Refresh interval: [bold]{interval}s[/bold]  |  Press Ctrl+C to stop",
            border_style="bright_black",
        )
    )

    with PriceToBeatFetcher() as fetcher:
        while not _stop[0]:
            # Fetch data
            try:
                result = fetcher.fetch()
                panel = build_table(result.markets, result.timestamp_utc, result.errors)
            except Exception as exc:
                panel = Panel(
                    f"[red]❌ Fetch error: {exc}[/red]",
                    title="Error",
                    border_style="red",
                )

            console.clear()
            console.print(panel)

            # Log summary
            if hasattr(result, "markets"):
                for mkt in result.markets:
                    LOGGER.info(
                        "%s | PTB=%.4f | Current=%.4f | Above=%s | YES=%.2f",
                        mkt.asset,
                        mkt.price_to_beat,
                        mkt.current_price,
                        mkt.is_above_ptb,
                        mkt.yes_price,
                    )

            if once:
                break

            # Wait with countdown
            for remaining in range(interval, 0, -1):
                if _stop[0]:
                    break
                console.print(
                    f"[dim]  Next refresh in {remaining}s... (Ctrl+C to stop)[/dim]",
                    end="\r",
                )
                time.sleep(1)
            console.print(" " * 50, end="\r")  # clear line

    console.print("[green]Monitor stopped.[/green]")


# ──────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Polymarket 5-Min Price To Beat Realtime Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Refresh interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    run_monitor(interval=args.interval, once=args.once)


if __name__ == "__main__":
    main()
