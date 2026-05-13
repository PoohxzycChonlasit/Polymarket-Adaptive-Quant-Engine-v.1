from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Deque, Mapping

import shutil
import sys
import time

from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text


_MAX_TICKS = 18   # rows kept in the price history table
# force_terminal=True + legacy_windows=False -> ANSI mode on Windows (avoids cp874 issues)
_CONSOLE = Console(force_terminal=True, legacy_windows=False)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _price_color(current: float, previous: float | None) -> str:
    if previous is None:
        return "white"
    return "bright_green" if current >= previous else "bright_red"


def _change_color(pct: float) -> str:
    if pct > 0:
        return "bright_green"
    if pct < 0:
        return "bright_red"
    return "white"


def _change_arrow(pct: float) -> str:
    if pct > 0:
        return "▲"
    if pct < 0:
        return "▼"
    return "─"


def _fmt_price(value: float) -> str:
    return f"{value:>12,.2f}"


def _fmt_volume(value: float) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return f"{value:,.0f}"


def _progress_bar_inline(value: float, width: int = 10, color: str = "bright_green") -> Text:
    filled = round(min(max(value, 0.0), 1.0) * width)
    bar = Text()
    bar.append("▓" * filled, style=color)
    bar.append("░" * (width - filled), style="grey23")
    return bar


def _get_field(source: object, name: str, default: object = "--") -> object:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _fmt_optional_float(value: object, decimals: int = 4, signed: bool = False) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "--"
    if number == 0:
        return "--"
    sign = "+" if signed else ""
    return f"{number:{sign}.{decimals}f}"


def _fmt_money_compact(value: object, signed: bool = False) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "$--"
    prefix = "+" if signed and number >= 0 else ""
    return f"{prefix}${number:.2f}"


# ------------------------------------------------------------------
# Ticker display
# ------------------------------------------------------------------

class RealtimeTickerDisplay:
    """Rich Live display for the realtime BTC feed."""

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        exchange: str = "binance",
        paper_trading: bool = True,
        ai_cycle_seconds: int = 0,
    ) -> None:
        self.symbol = symbol
        self.exchange = exchange.upper()
        self.paper_trading = paper_trading
        self.ai_cycle_seconds = ai_cycle_seconds

        self._ticks: Deque[dict[str, object]] = deque(maxlen=_MAX_TICKS)
        self._prev_price: float | None = None
        self._ai: dict[str, object] = {}
        self._portfolio: object | None = None
        self._started_at = datetime.now(tz=UTC)

        self._live = Live(
            self._render(),
            console=_CONSOLE,
            refresh_per_second=4,
            screen=True,
        )

    def __enter__(self) -> RealtimeTickerDisplay:
        self._live.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self._live.__exit__(*args)

    def update_tick(self, tick: object) -> None:
        row = {
            "time": tick.timestamp_utc[11:19],      # type: ignore[attr-defined]
            "price": tick.last_price,                # type: ignore[attr-defined]
            "bid": tick.bid,                         # type: ignore[attr-defined]
            "ask": tick.ask,                         # type: ignore[attr-defined]
            "spread": tick.spread,                   # type: ignore[attr-defined]
            "volume_24h": tick.volume_24h,           # type: ignore[attr-defined]
            "change_pct": tick.change_pct_24h,       # type: ignore[attr-defined]
        }
        self._ticks.append(row)
        self._prev_price = tick.last_price           # type: ignore[attr-defined]
        self._live.update(self._render())

    def update_ai(self, decision: str, confidence: float, edge: object, next_in: int = 0) -> None:
        self._ai = {
            "decision": decision,
            "confidence": confidence,
            "edge": edge,
            "next_in": next_in,
            "at": datetime.now(tz=UTC).strftime("%H:%M:%S"),
        }
        self._live.update(self._render())

    def update_portfolio(self, summary: object) -> None:
        self._portfolio = summary
        self._live.update(self._render())

    def _render(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(self._header(), name="header", size=4),
            Layout(self._price_table(), name="ticker"),
            Layout(name="bottom", size=9),
            Layout(self._footer(), name="footer", size=1),
        )
        layout["bottom"].split_row(
            Layout(self._portfolio_panel(), name="portfolio"),
            Layout(self._ai_panel(), name="ai"),
        )
        return layout

    def _header(self) -> Panel:
        mode_tag = (
            Text(" 📄 PAPER TRADING ", style="bold white on dark_orange")
            if self.paper_trading
            else Text(" 🔴 LIVE TRADING ", style="bold white on red")
        )
        exchange_tag = Text(f" {self.exchange} ", style="bold white on dark_blue")

        line1 = Text()
        line1.append("🎯  ", style="bold bright_yellow")
        line1.append("PolyTrade Bot", style="bold bright_cyan")
        line1.append("  │  ", style="grey42")
        line1.append(f"📊 {self.symbol}", style="bold bright_white")
        line1.append("  │  ", style="grey42")
        line1.append_text(exchange_tag)
        line1.append("  ")
        line1.append_text(mode_tag)

        return Panel(line1, style="bold", border_style="bright_cyan", padding=(0, 1))

    def _price_table(self) -> Panel:
        table = Table(
            show_header=True,
            header_style="bold bright_white on grey19",
            border_style="grey35",
            box=None,
            expand=True,
            padding=(0, 1),
        )
        table.add_column("TIME",        style="grey70",       width=10, justify="left")
        table.add_column("PRICE (USD)", style="white",        width=16, justify="right")
        table.add_column("CHANGE 24H",  style="white",        width=12, justify="right")
        table.add_column("BID",         style="bright_green", width=13, justify="right")
        table.add_column("ASK",         style="bright_red",   width=13, justify="right")
        table.add_column("SPREAD",      style="grey62",       width=10, justify="right")
        table.add_column("VOLUME 24H",  style="bright_yellow",width=14, justify="right")

        rows = list(self._ticks)
        for i, row in enumerate(rows):
            prev_price = rows[i - 1]["price"] if i > 0 else None
            price_col = _price_color(float(row["price"]), float(prev_price) if prev_price else None)
            change_pct = float(row["change_pct"])
            change_col = _change_color(change_pct)
            arrow = _change_arrow(change_pct)

            price_text = Text(_fmt_price(float(row["price"])), style=f"bold {price_col}")
            change_text = Text(f"{arrow} {change_pct:+.2f}%", style=change_col)

            table.add_row(
                str(row["time"]),
                price_text,
                change_text,
                f'{float(row["bid"]):>12,.2f}',
                f'{float(row["ask"]):>12,.2f}',
                f'{float(row["spread"]):.4f}',
                _fmt_volume(float(row["volume_24h"])),
            )

        if not rows:
            table.add_row("[grey50]⏳ Waiting for data...[/grey50]", "", "", "", "", "", "")

        return Panel(table, title="[bold bright_white]📡 Price Feed[/bold bright_white]", border_style="grey42")

    def _portfolio_panel(self) -> Panel:
        s = self._portfolio
        if s is None:
            return Panel(
                Text("  ⏳ No portfolio data yet.", style="grey50"),
                title="[bold bright_white]💼 Portfolio[/bold bright_white]",
                border_style="grey42",
            )

        upnl = float(s.unrealized_pnl)           # type: ignore[attr-defined]
        dpnl = float(s.daily_realized_pnl)        # type: ignore[attr-defined]
        dd   = float(s.daily_drawdown_pct)        # type: ignore[attr-defined]
        exp  = float(s.total_exposure_pct)        # type: ignore[attr-defined]
        cnt  = int(s.open_count)                  # type: ignore[attr-defined]
        maxp = int(s.max_open_positions)          # type: ignore[attr-defined]

        upnl_style = "bright_green" if upnl >= 0 else "bright_red"
        dpnl_style = "bright_green" if dpnl >= 0 else "bright_red"
        dd_style   = "bright_red" if dd > 0.01 else "bright_yellow" if dd > 0 else "bright_green"
        exp_style  = "bright_red" if exp > 0.20 else "bright_yellow" if exp > 0.10 else "bright_green"

        l1 = Text()
        l1.append("  📂 Positions  ", style="grey70")
        l1.append(f"{cnt}/{maxp}", style="bold bright_white")
        l1.append("   🔥 Exposure  ", style="grey70")
        l1.append(f"{exp:.1%}", style=f"bold {exp_style}")
        l1.append("   💹 uPnL  ", style="grey70")
        l1.append(f"{upnl:+.2f}", style=f"bold {upnl_style}")

        l2 = Text()
        l2.append("  📅 Daily PnL  ", style="grey70")
        l2.append(f"{dpnl:+.2f}", style=f"bold {dpnl_style}")
        l2.append("   📉 Drawdown  ", style="grey70")
        l2.append(f"{dd:.2%}", style=f"bold {dd_style}")

        positions = getattr(s, "positions", [])[:3]
        if positions:
            rows: list[str] = []
            for p in positions:
                sym = str(p.symbol)[:10]
                side_style = "bright_green" if p.side == "BUY" else "bright_red"
                upnl_val = float(p.unrealized_pnl)
                upnl_s = "bright_green" if upnl_val >= 0 else "bright_red"
                side_emoji = "📈" if p.side == "BUY" else "📉"
                rows.append(
                    f"  {side_emoji} [{side_style}]{p.side}[/{side_style}] {sym:<10} "
                    f"@ {p.entry_price:.2f}  "
                    f"SL {p.stop_loss:.2f}  TP {p.take_profit:.2f}  "
                    f"[{upnl_s}]{upnl_val:+.4f}[/{upnl_s}]"
                )
            l3 = Text.from_markup("\n".join(rows))
        else:
            l3 = Text("  💤 No open positions.", style="grey50")

        content = Text.assemble(l1, "\n", l2, "\n", l3)
        return Panel(content, title="[bold bright_white]💼 Portfolio[/bold bright_white]", border_style="grey42")

    def _ai_panel(self) -> Panel:
        if not self._ai:
            if self.ai_cycle_seconds > 0:
                msg = Text(f"  🧠 Quant analysis runs every {self.ai_cycle_seconds}s — waiting for first cycle…", style="grey50")
            else:
                msg = Text("  🧠 Quant analysis disabled. Use --ai-cycle N to enable.", style="grey50")
            return Panel(msg, title="[bold bright_white]🧠 Quant Analysis[/bold bright_white]", border_style="grey42")

        decision = str(self._ai.get("decision", "--")).upper()
        confidence = float(self._ai.get("confidence", 0))
        edge = self._ai.get("edge", "n/a")
        next_in = int(self._ai.get("next_in", 0))
        at = str(self._ai.get("at", ""))

        decision_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡", "SKIP": "⭕"}.get(decision, "⚪")
        decision_colors = {
            "BUY": "bold bright_green", "SELL": "bold bright_red",
            "HOLD": "bold bright_yellow", "SKIP": "bold grey62",
        }
        decision_style = decision_colors.get(decision, "bold white")
        confidence_style = "bright_green" if confidence >= 0.65 else "bright_yellow" if confidence >= 0.50 else "bright_red"
        edge_val = float(edge) if edge != "n/a" else None
        edge_style = "bright_green" if edge_val and edge_val > 0 else "bright_red"

        l1 = Text()
        l1.append(f"  {decision_emoji} Decision  ", style="grey70")
        l1.append(f" {decision} ", style=f"{decision_style} on grey15")
        l1.append("   🎯 Confidence  ", style="grey70")
        l1.append(f"{confidence:.0%}", style=f"bold {confidence_style}")
        l1.append("   ⚡ Edge  ", style="grey70")
        l1.append(f"{edge:.4f}" if edge_val is not None else "n/a", style=f"bold {edge_style}")
        l1.append(f"   @ {at}", style="grey50")

        confidence_bar = _progress_bar_block(confidence, width=30, color=confidence_style)
        l2 = Text()
        l2.append("  Confidence  ", style="grey70")
        l2.append_text(confidence_bar)

        l3 = Text()
        if next_in > 0:
            l3.append(f"  ⏱  Next cycle in ", style="grey50")
            l3.append(f"{next_in}s", style="bold bright_cyan")
        else:
            l3.append("  ──", style="grey50")

        content = Text.assemble(l1, "\n", l2, "\n", l3)
        return Panel(content, title="[bold bright_cyan]🧠 Quant Analysis[/bold bright_cyan]", border_style="bright_cyan")

    def _footer(self) -> Text:
        uptime = datetime.now(tz=UTC) - self._started_at
        mins, secs = divmod(int(uptime.total_seconds()), 60)
        now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        return Text(
            f"  🕐 {now}   ⏱ Uptime {mins:02d}:{secs:02d}   Press Ctrl+C to stop",
            style="grey50",
        )

    @staticmethod
    def _progress_bar(value: float, width: int = 30, color: str = "bright_green") -> Text:
        filled = round(min(max(value, 0.0), 1.0) * width)
        bar = Text()
        bar.append("▓" * filled, style=color)
        bar.append("░" * (width - filled), style="grey23")
        bar.append(f" {value:.0%}", style="grey70")
        return bar


# ------------------------------------------------------------------
# Polymarket Realtime Display
# ------------------------------------------------------------------

class _LegacyPolymarketRealtimeDisplay:
    """Legacy pre-V2 Polymarket display kept for reference; runtime uses PolymarketRealtimeDisplay below."""

    _TICKERS = ["BTC", "ETH"]
    _WEAK    = {"BTC"}
    _STRONG  = {"ETH"}

    def __init__(
        self,
        paper_trading: bool = True,
        interval: int = 60,
        snipe_min_edge: float = 0.30,
    ) -> None:
        self.paper_trading   = paper_trading
        self.interval        = interval
        self.snipe_min_edge  = snipe_min_edge

        self._markets: dict[str, dict] = {
            t: {
                "ref_price":    0.0,
                "current_price": 0.0,
                "is_above":     False,
                "price_diff":   0.0,
                "bid":          0.0,
                "ask":          0.0,
                "spread":       0.0,
                "snipe_score":  0.0,
                "signal":       "--",
                "confidence":   0.0,
                "decision":     "--",
                "size":         0.0,
                "risk_tier":    "weak" if t in self._WEAK else "strong" if t in self._STRONG else "normal",
                "countdown":    300,
                "window_ts":    "--:--",
                "edge_pct":     0.0,
                "p_yes":        0.0,
                "p_no":         0.0,
                "ev":           0.0,
                "min_ev":       0.0,
                "delta_regime": "--",
                "delta_multiplier": 0.0,
                "skip_reason":  "",
                "score":        0.0,
                "ask_price":    0.0,
                "final_size":   0.0,
                "frequency_multiplier": 0.0,
                "last_tick_ms": 0,
                "seconds_remaining": 0,
                "first_seen_seconds_remaining": 0,
                "first_evaluable_seconds_remaining": 0,
                "cutoff_policy": "static",
                "effective_cutoff_seconds": 0,
                "adaptive_cutoff_reason": "",
                "adaptive_cutoff_denied_reason": "",
                "micro_timing_branch_entered": False,
                "micro_timing_allowed": False,
                "micro_timing_denied_reason": "",
                "micro_cutoff_policy": "standard",
                "effective_micro_cutoff_seconds": 0,
                "liquidity_state": "HEALTHY",
                "empty_book_recovery_attempted": False,
                "empty_book_recovery_success": False,
                "empty_book_recovery_failed": False,
                "empty_book_recovery_retry_count": 0,
            }
            for t in self._TICKERS
        }

        self._portfolio: object | None = None
        self._cycle_results: list[dict] = []
        self._cycle_num:  int = 0
        self._cycle_at:   str = "--"
        self._next_in:    int = interval
        self._recent_trades: Deque[dict] = deque(maxlen=5)
        self._started_at = datetime.now(tz=UTC)
        self._ai_layer: list[dict] = []
        self._arbitrage: dict[str, dict] = {}
        self._session_summary: dict[str, object] = {}
        self._ws_status: str = "⚠️  connecting"

        self._live = Live(
            self._render(),
            console=_CONSOLE,
            refresh_per_second=4,
            screen=True,
        )

    def __enter__(self) -> "_LegacyPolymarketRealtimeDisplay":
        self._live.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self._live.__exit__(*args)

    # ------------------------------------------------------------------
    # Public update methods  (signatures unchanged)
    # ------------------------------------------------------------------

    def update_market(self, ticker: str, **kwargs: object) -> None:
        if ticker in self._markets:
            self._markets[ticker].update(kwargs)
            self._live.update(self._render())

    def update_cycle(self, results: list[dict], cycle_num: int) -> None:
        self._cycle_results = results
        self._cycle_num     = cycle_num
        self._cycle_at      = datetime.now(tz=UTC).strftime("%H:%M:%S")
        self._live.update(self._render())

    def update_portfolio(self, summary: object) -> None:
        self._portfolio = summary
        self._live.update(self._render())

    def update_countdown(self, next_in: int) -> None:
        self._next_in = next_in
        self._live.update(self._render())

    def update_realtime_batch(self, ticker_updates: dict[str, dict]) -> None:
        import time as _time
        now_ms = int(_time.time() * 1000)
        for ticker, data in ticker_updates.items():
            if ticker in self._markets:
                data["last_tick_ms"] = now_ms
                self._markets[ticker].update(data)
        self._live.update(self._render())

    def update_ai_layer(self, layers: list[dict]) -> None:
        self._ai_layer = layers
        self._live.update(self._render())

    def update_arbitrage(self, ticker: str, **kwargs: object) -> None:
        self._arbitrage[ticker.upper()] = {
            "ticker": ticker.upper(),
            "at": datetime.now(tz=UTC).strftime("%H:%M:%S"),
            **kwargs,
        }
        self._live.update(self._render())

    def update_ws_status(self, status: str) -> None:
        self._ws_status = status

    def add_trade(
        self,
        ticker: str,
        side: str,
        price: float,
        size: float,
        notional: float,
        status: str,
        *,
        exit_price: float | None = None,
        realized_pnl: float = 0.0,
        reason: str = "entry",
        mode: str = "--",
    ) -> None:
        self._recent_trades.appendleft({
            "time":     datetime.now(tz=UTC).strftime("%H:%M:%S"),
            "market":   ticker,
            "ticker":   ticker,
            "side":     side,
            "entry_price": price,
            "exit_price": exit_price,
            "price":    price,
            "size":     size,
            "notional": notional,
            "status":   status,
            "realized_pnl": realized_pnl,
            "reason": reason,
            "mode": mode,
        })
        self._live.update(self._render())

    def update_recent_trades(self, trades: list[dict]) -> None:
        self._recent_trades.clear()
        for trade in reversed(trades[-self._recent_trades.maxlen:]):
            self._recent_trades.appendleft(trade)
        self._live.update(self._render())

    def update_session_summary(self, summary: dict[str, object]) -> None:
        self._session_summary = summary
        self._live.update(self._render())

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _render(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(self._header(),         name="header",   size=4),
            Layout(self._market_table(),   name="markets",  size=12),
            Layout(name="middle",                           size=9),
            Layout(name="bottom",                           size=7),
            Layout(self._footer(),         name="footer",   size=1),
        )
        layout["middle"].split_row(
            Layout(self._portfolio_panel(), name="portfolio"),
            Layout(self._cycle_panel(),     name="cycle"),
        )
        layout["bottom"].split_row(
            Layout(self._arbitrage_panel(), name="arbitrage"),
            Layout(self._quant_detail_panel(), name="quant_detail"),
            Layout(self._trades_panel(),    name="trades"),
        )
        return layout

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _header(self) -> Panel:
        mode_tag = (
            Text(" 📄 PAPER ", style="bold white on dark_orange")
            if self.paper_trading
            else Text(" 🔴 LIVE ", style="bold white on red")
        )
        pm_tag      = Text(" 🌊 POLYMARKET ", style="bold white on dark_blue")
        binary_tag  = Text(" ⏱ 5M BINARY ",  style="bold white on purple4")
        grinder_tag = Text(" ⚙️ MICRO-GRINDER ", style="bold black on bright_yellow")

        line1 = Text()
        line1.append("🎯  ", style="bold bright_yellow")
        line1.append("PolyTrade Bot", style="bold bright_cyan")
        line1.append("  │  ", style="grey35")
        line1.append_text(pm_tag)
        line1.append("  ")
        line1.append_text(binary_tag)
        line1.append("  ")
        line1.append_text(mode_tag)
        line1.append("  ")
        line1.append_text(grinder_tag)

        line2 = Text()
        line2.append("  ⚡  ", style="bright_yellow")
        line2.append("Strategy: Counter-Momentum  ", style="grey70")
        line2.append("│  ", style="grey35")
        line2.append("📊 Markov Bounds 0.40–1.00%  ", style="bright_cyan")
        line2.append("│  ", style="grey35")
        line2.append("⚖️ Kelly Sizing  ", style="grey70")
        line2.append("│  ", style="grey35")
        line2.append("🛑 Floor $5.00", style="bright_red")

        content = Text.assemble(line1, "\n", line2)
        return Panel(content, border_style="bright_cyan", padding=(0, 1))

    # ------------------------------------------------------------------
    # Market overview table
    # ------------------------------------------------------------------

    def _market_table(self) -> Panel:
        table = Table(
            show_header=True,
            header_style="bold bright_white on grey19",
            border_style="grey35",
            box=None,
            expand=True,
            padding=(0, 1),
        )
        table.add_column("MARKET",   style="bold white",    width=10)
        table.add_column("TIER",     style="grey70",        width=7,  justify="center")
        table.add_column("PTB",      style="grey70",        width=12, justify="right")
        table.add_column("ORACLE",   style="white",         width=13, justify="right")
        table.add_column("WINDOW",   style="grey62",        width=11, justify="center")
        table.add_column("⏱",        style="white",         width=6,  justify="right")
        table.add_column("BID",      style="bright_green",  width=8,  justify="right")
        table.add_column("ASK",      style="bright_red",    width=8,  justify="right")
        table.add_column("SPREAD",   style="grey62",        width=8,  justify="right")
        table.add_column("Model_Y",  style="bright_green",  width=8,  justify="right")
        table.add_column("Model_N",  style="bright_red",    width=8,  justify="right")
        table.add_column("EV",       style="bright_cyan",   width=8,  justify="right")
        table.add_column("MIN_EV",   style="grey70",        width=7,  justify="right")
        table.add_column("DELTA",    style="white",         width=12, justify="center")
        table.add_column("CONF",     style="white",         width=6,  justify="right")
        table.add_column("DECISION", style="white",         width=26, justify="left")

        for ticker in self._TICKERS:
            m    = self._markets[ticker]
            tier = m["risk_tier"]

            if tier == "weak":
                tier_text = Text("📉 LOW",  style="bright_red")
            elif tier == "strong":
                tier_text = Text("🔥 HOT",  style="bright_green")
            else:
                tier_text = Text("⚡ MID",  style="bright_yellow")

            ref = float(m["ref_price"])
            if ref >= 1_000:
                ref_str = f"${ref:>9,.2f}"
            elif ref >= 1:
                ref_str = f"${ref:>9,.4f}"
            else:
                ref_str = f"${ref:>9,.6f}"
            ptb_text = Text(ref_str if ref > 0 else "  ──", style="grey62")

            cur  = float(m.get("current_price", 0.0))
            diff = float(m.get("price_diff", 0.0))
            if cur >= 1_000:
                cur_str = f"${cur:>10,.2f}"
            elif cur >= 1:
                cur_str = f"${cur:>10,.4f}"
            else:
                cur_str = f"${cur:>10,.6f}"

            if diff > 0:
                cur_style = "bright_green"
                cur_str = f"▲{cur_str}"
            elif diff < 0:
                cur_style = "bright_red"
                cur_str = f"▼{cur_str}"
            else:
                cur_style = "white"
            cur_text = Text(cur_str if cur > 0 else "     ──", style=cur_style)

            window_text = Text(str(m.get("window_ts", "--:--")), style="grey50")

            countdown = int(m.get("countdown", 0))
            if countdown <= 15:
                cd_style = "bold bright_red"
                cd_str   = f"🔴{countdown}s"
            elif countdown <= 60:
                cd_style = "bright_yellow"
                cd_str   = f"🟡{countdown}s"
            else:
                cd_style = "grey62"
                cd_str   = f"{countdown}s"
            countdown_text = Text(cd_str if countdown > 0 else "──", style=cd_style)

            bid    = float(m["bid"])
            ask    = float(m["ask"])
            spread = float(m["spread"])
            has_orderbook = bid > 0 or ask > 0
            bid_text    = Text(f"{bid:.4f}" if bid    > 0 else "──", style="bright_green")
            ask_text    = Text(f"{ask:.4f}" if ask    > 0 else "──", style="bright_red")
            spread_text = Text(f"{spread:.4f}" if spread > 0 else "──", style="grey62")

            snipe = float(m["snipe_score"])
            if snipe >= self.snipe_min_edge:
                snipe_text = Text(f"🔥{snipe:.2f}", style="bold bright_yellow on grey11")
            elif has_orderbook:
                snipe_style = "bright_green" if snipe > 0 else "bright_red" if snipe < 0 else "grey62"
                snipe_text = Text(f"{snipe:+.2f}", style=snipe_style)
            elif snipe > 0:
                snipe_text = Text(f"  {snipe:.2f}", style="bright_yellow")
            else:
                snipe_text = Text("   ──",          style="grey50")

            edge = float(m.get("edge_pct", 0.0))
            if edge >= 0.05:
                edge_text = Text(f"{edge:.1%}", style="bold bright_cyan")
            elif has_orderbook:
                edge_style = "bright_cyan" if edge > 0 else "bright_red" if edge < 0 else "grey62"
                edge_text = Text(f"{edge:+.1%}", style=edge_style)
            else:
                edge_text = Text("  ──",        style="grey50")

            p_yes = float(m.get("p_yes", 0.0) or 0.0)
            p_no = float(m.get("p_no", 0.0) or 0.0)
            ev = float(m.get("ev", 0.0) or 0.0)
            min_ev = float(m.get("min_ev", 0.0) or 0.0)
            delta_regime = str(m.get("delta_regime", "--") or "--")
            delta_mult = float(m.get("delta_multiplier", 0.0) or 0.0)
            skip_reason = str(m.get("skip_reason", "") or "")
            if not skip_reason:
                if not has_orderbook:
                    skip_reason = "no_orderbook"
                elif p_yes <= 0 and p_no <= 0 and ev == 0 and delta_regime == "--":
                    skip_reason = "model_not_run"
            py_text = Text(f"{p_yes:.2f}" if p_yes > 0 else "--", style="bright_green" if p_yes >= 0.50 else "grey62")
            pn_text = Text(f"{p_no:.2f}" if p_no > 0 else "--", style="bright_red" if p_no >= 0.50 else "grey62")
            ev_style = "bold bright_green" if ev > 0 else "bright_red" if ev < 0 else "grey62"
            ev_text = Text(f"{ev:+.3f}" if ev else "--", style=ev_style)
            min_ev_text = Text(f"{min_ev:.3f}" if min_ev else "--", style="grey70")
            delta_style = "bright_red" if delta_regime == "EXTREME" else "bright_yellow" if delta_regime == "HIGH" else "bright_green" if delta_regime in {"LOW", "NORMAL"} else "grey62"
            delta_text = Text(f"{delta_regime[:4]} x{delta_mult:.2f}" if delta_regime != "--" else "--", style=delta_style)

            signal = str(m["signal"])
            _signal_map: dict[str, tuple[str, str]] = {
                "long":    ("bold bright_green", "📈 LONG"),
                "short":   ("bold bright_red",   "📉 SHORT"),
                "flat":    ("grey50",             "➡  FLAT"),
                "wait":    ("grey62",             "⏳ WAIT"),
                "weak_up": ("bright_yellow",      "⚡ WEAK↑"),
                "--":       ("grey50",             "   ──"),
            }
            sig_style, sig_label = _signal_map.get(signal, ("white", signal.upper()))
            signal_text = Text(sig_label, style=sig_style)

            conf = float(m["confidence"])
            conf_style = (
                "bold bright_green"  if conf >= 0.65 else
                "bright_yellow"      if conf >= 0.50 else
                "bright_red"         if conf >  0    else
                "grey50"
            )
            conf_text = Text(f"{conf:.0%}" if conf > 0 else "──", style=conf_style)

            decision = str(m["decision"])
            if skip_reason and decision in {"", "--"}:
                decision = "SKIP"
            _decision_map: dict[str, tuple[str, str]] = {
                "approved": ("bold bright_green", "🟢 ENTER"),
                "rejected": ("grey50",            "⭕  SKIP"),
                "reduced":  ("bright_yellow",     "🛡  HEDGE"),
                "--":        ("grey50",            "    ──  "),
            }
            d_style, d_label = _decision_map.get(decision, ("white", decision.upper()))
            if decision in {"SKIP", "ENTER", "BEST_TRADE", "WATCHLIST"}:
                d_style = "bold bright_green" if decision in {"ENTER", "BEST_TRADE"} else "bright_yellow" if decision == "WATCHLIST" else "grey50"
                d_label = decision
            if d_label.strip().upper() == "SKIP" and skip_reason:
                d_label = f"SKIP {skip_reason}"
            decision_text = Text(d_label, style=d_style)

            if snipe >= self.snipe_min_edge:
                name_style = "bold bright_yellow"
            elif countdown <= 15 and countdown > 0:
                name_style = "bold bright_red"
            else:
                name_style = "bold white"

            table.add_row(
                Text(f"● {ticker} 5m", style=name_style),
                tier_text,
                ptb_text,
                cur_text,
                window_text,
                countdown_text,
                bid_text,
                ask_text,
                spread_text,
                py_text,
                pn_text,
                ev_text,
                min_ev_text,
                delta_text,
                conf_text,
                decision_text,
            )

        return Panel(
            table,
            title="[bold bright_white]📡 Polymarket 5M — Live Market Overview[/bold bright_white]",
            border_style="bright_blue",
        )

    # ------------------------------------------------------------------
    # Portfolio panel
    # ------------------------------------------------------------------

    def _portfolio_panel(self) -> Panel:
        s = self._portfolio
        if s is None:
            return Panel(
                Text("  ⏳ Waiting for portfolio data…", style="grey50"),
                title="[bold bright_white]💼 Portfolio[/bold bright_white]",
                border_style="grey42",
            )

        upnl    = float(_get_field(s, "unrealized_pnl", 0.0))
        dpnl    = float(_get_field(s, "daily_realized_pnl", _get_field(s, "realized_pnl", 0.0)))
        dd      = float(_get_field(s, "daily_drawdown_pct", _get_field(s, "daily_drawdown", 0.0)))
        exp     = float(_get_field(s, "total_exposure_pct", 0.0))
        cnt     = int(_get_field(s, "open_count", 0))
        maxp    = int(_get_field(s, "max_open_positions", 0))
        balance = float(_get_field(s, "account_balance", _get_field(s, "sizing_bankroll", 0.0)))
        start = float(_get_field(s, "starting_bankroll", balance))
        cash = float(_get_field(s, "cash", balance))
        open_value = float(_get_field(s, "open_value", 0.0))
        equity = float(_get_field(s, "equity", cash + open_value))
        sizing_bankroll = float(_get_field(s, "sizing_bankroll", equity))
        bankroll_tier = str(_get_field(s, "bankroll_tier", "--"))
        risk_off = bool(_get_field(s, "risk_off", False))

        upnl_style  = "bright_green"  if upnl >= 0              else "bright_red"
        dpnl_style  = "bright_green"  if dpnl >= 0              else "bright_red"
        dd_style    = "bright_red"    if dd > 0.10 else "bright_yellow" if dd > 0.02 else "bright_green"
        exp_style   = "bright_red"    if exp > 0.20 else "bright_yellow" if exp > 0.10 else "bright_green"
        eq_style    = "bright_green"  if equity >= balance       else "bright_red"
        bal_emoji   = "📈" if equity >= balance else "📉"

        l1 = Text()
        l1.append("  Start ", style="grey70")
        l1.append(f"${start:.2f}", style="bold white")
        l1.append("   Cash ", style="grey70")
        l1.append(f"${cash:.2f}", style="bold bright_white")
        l1.append("   Open ", style="grey70")
        l1.append(f"${open_value:.2f}", style="bold bright_cyan")
        l1.append("   Equity ", style="grey70")
        l1.append(f"${equity:.2f}", style=f"bold {eq_style}")

        l2 = Text()
        l2.append("  📂 Positions  ", style="grey70")
        l2.append(f"{cnt}/{maxp}", style="bold bright_white")
        l2.append("   🔥 Exposure  ", style="grey70")
        l2.append(f"{exp:.1%}", style=f"bold {exp_style}")
        l2.append("   💹 uPnL  ", style="grey70")
        l2.append(f"{upnl:+.4f}", style=f"bold {upnl_style}")

        dpnl_emoji = "✅" if dpnl >= 0 else "❌"
        l3 = Text()
        l3.append(f"  {dpnl_emoji} Daily PnL  ", style="grey70")
        l3.append(f"{dpnl:+.4f}", style=f"bold {dpnl_style}")
        l3.append("   📉 Drawdown  ", style="grey70")
        l3.append(f"{dd:.2%}", style=f"bold {dd_style}")

        # Equity bar
        safe_balance = max(balance, 0.01)
        eq_ratio = min(equity / safe_balance, 2.0) / 2.0  # normalize 0-2x to 0-100%
        eq_bar = _progress_bar_block(eq_ratio, width=24, color=eq_style)
        l4 = Text()
        l4.append("  Equity  ", style="grey50")
        l4.append_text(eq_bar)

        positions = getattr(s, "positions", [])[:3]  # type: ignore[attr-defined]
        if positions:
            pos_parts: list[object] = []
            for p in positions:
                lbl   = str(p.symbol).replace("pm-5m-", "").upper()[:6]
                ss    = "bright_green" if p.side == "BUY" else "bright_red"
                uv    = float(p.unrealized_pnl)
                us    = "bright_green" if uv >= 0 else "bright_red"
                side_emoji = "📈" if p.side == "BUY" else "📉"
                row   = Text()
                row.append(f"  {side_emoji} [{ss}]{p.side}[/{ss}]")
                row.append(f" {lbl:<6}", style="bold white")
                row.append(f" @{p.entry_price:.4f}", style="cyan")
                row.append("  SL ", style="grey50")
                row.append(f"{p.stop_loss:.4f}", style="bright_red")
                row.append("  TP ", style="grey50")
                row.append(f"{p.take_profit:.4f}", style="bright_green")
                row.append(f"  {uv:+.4f}", style=f"bold {us}")
                pos_parts += [row, "\n"]
            pos_text = Text.assemble(*pos_parts)
        else:
            pos_text = Text("  💤 No open positions.", style="grey50")

        content = Text.assemble(l1, "\n", l2, "\n", l3, "\n", l4, "\n", pos_text)
        return Panel(content, title="[bold bright_white]💼 Portfolio[/bold bright_white]", border_style="grey42")

    def _portfolio_panel(self) -> Panel:
        s = self._portfolio
        if s is None:
            return Panel(
                Text("  Waiting for portfolio data...", style="grey50"),
                title="[bold bright_white]Portfolio[/bold bright_white]",
                border_style="grey42",
            )

        upnl = float(_get_field(s, "unrealized_pnl", 0.0))
        realized = float(_get_field(s, "realized_pnl", _get_field(s, "daily_realized_pnl", 0.0)))
        dd = float(_get_field(s, "daily_drawdown", _get_field(s, "daily_drawdown_pct", 0.0)))
        exp = float(_get_field(s, "total_exposure_pct", 0.0))
        cnt = int(_get_field(s, "open_count", 0))
        maxp = int(_get_field(s, "max_open_positions", 0))
        balance = float(_get_field(s, "account_balance", _get_field(s, "sizing_bankroll", 0.0)))
        start = float(_get_field(s, "starting_bankroll", balance))
        cash = float(_get_field(s, "cash", balance))
        open_value = float(_get_field(s, "open_value", 0.0))
        equity = float(_get_field(s, "equity", cash + open_value))
        sizing = float(_get_field(s, "sizing_bankroll", equity))
        tier = str(_get_field(s, "bankroll_tier", "--"))
        raw_tier = str(_get_field(s, "raw_bankroll_tier", ""))
        risk_mode = str(_get_field(s, "risk_mode", "NORMAL"))
        risk_off = bool(_get_field(s, "risk_off", False))
        source = str(_get_field(s, "balance_source", "--"))

        eq_style = "bright_green" if equity >= start else "bright_red"
        realized_style = "bright_green" if realized >= 0 else "bright_red"
        upnl_style = "bright_green" if upnl >= 0 else "bright_red"
        dd_style = "bright_red" if dd > 0.10 else "bright_yellow" if dd > 0.02 else "bright_green"
        exp_style = "bright_red" if exp > 0.20 else "bright_yellow" if exp > 0.10 else "bright_green"

        l1 = Text()
        l1.append("  Start ", style="grey70")
        l1.append(f"${start:.2f}", style="bold white")
        l1.append(" | Cash ", style="grey70")
        l1.append(f"${cash:.2f}", style="bold bright_white")
        l1.append(" | Open ", style="grey70")
        l1.append(f"${open_value:.2f}", style="bold bright_cyan")
        l1.append(" | Equity ", style="grey70")
        l1.append(f"${equity:.2f}", style=f"bold {eq_style}")

        l2 = Text()
        l2.append("  Sizing ", style="grey70")
        l2.append(f"${sizing:.2f}", style="bold bright_white")
        l2.append(" | Tier ", style="grey70")
        l2.append(tier, style="bold bright_cyan")
        if raw_tier and raw_tier != tier:
            l2.append(" | Raw ", style="grey70")
            l2.append(raw_tier, style="bold bright_yellow")
        if risk_mode and risk_mode != "NORMAL":
            l2.append(" | Mode ", style="grey70")
            l2.append(risk_mode, style="bold bright_yellow" if risk_mode != "LOCKDOWN" else "bold bright_red")
        l2.append(" | Daily DD ", style="grey70")
        l2.append(f"{dd:.1%}", style=f"bold {dd_style}")
        l2.append(" | RiskOff ", style="grey70")
        l2.append(str(risk_off), style="bold bright_red" if risk_off else "bright_green")
        if source and source != "--":
            l2.append(" | Source ", style="grey70")
            l2.append(source, style="bold bright_white")

        l3 = Text()
        l3.append("  Realized ", style="grey70")
        l3.append(f"{realized:+.4f}", style=f"bold {realized_style}")
        l3.append(" | Unrealized ", style="grey70")
        l3.append(f"{upnl:+.4f}", style=f"bold {upnl_style}")
        l3.append(" | Positions ", style="grey70")
        l3.append(f"{cnt}/{maxp}", style="bold bright_white")
        l3.append(" | Exposure ", style="grey70")
        l3.append(f"{exp:.1%}", style=f"bold {exp_style}")

        return Panel(
            Text.assemble(l1, "\n", l2, "\n", l3),
            title="[bold bright_white]Portfolio[/bold bright_white]",
            border_style="grey42",
        )

    # ------------------------------------------------------------------
    def _cycle_panel(self) -> Panel:
        if not self._cycle_results:
            wait_text = Text()
            wait_text.append("  🧠 Waiting for first signal cycle…\n", style="grey50")
            wait_text.append("  ⏱  Next in ", style="grey70")
            wait_text.append(f"{self._next_in}s", style="bold bright_cyan")
            return Panel(
                wait_text,
                title="[bold bright_white]🧠 Quant Engine Results[/bold bright_white]",
                border_style="grey42",
            )

        hdr = Text()
        hdr.append(f"  🔄 Cycle #{self._cycle_num}", style="bold bright_white")
        hdr.append(f"  @ {self._cycle_at}", style="grey50")
        hdr.append("   ⏱  Next in ", style="grey70")
        hdr.append(f"{self._next_in}s", style="bold bright_cyan")

        _decision_map: dict[str, tuple[str, str, str]] = {
            "approved": ("bold bright_green", "🟢", "ENTER"),
            "rejected": ("grey50",            "⭕", "SKIP "),
            "reduced":  ("bright_yellow",     "🛡️", "MINI "),
        }

        rows: list[object] = [hdr, "\n"]
        for r in self._cycle_results:
            ticker   = str(r.get("ticker", "--"))
            decision = str(r.get("decision", "--"))
            conf     = float(r.get("confidence", 0.0))
            snipe    = float(r.get("snipe_score", 0.0))

            d_style, d_emoji, d_lbl = _decision_map.get(decision, ("grey50", "⭕", "SKIP "))
            conf_style = (
                "bold bright_green"  if conf >= 0.65 else
                "bright_yellow"      if conf >= 0.50 else
                "bright_red"
            )
            bar = _progress_bar_inline(conf, width=12, color=conf_style)

            row = Text()
            row.append(f"  {ticker:<5}", style="bold white")
            row.append(f" {d_emoji} [{d_style}]{d_lbl}[/{d_style}]")
            row.append("  ")
            row.append_text(bar)
            row.append(f" {conf:.0%}", style=conf_style)
            if snipe >= self.snipe_min_edge:
                row.append(f"  🔥{snipe:.2f}", style="bold bright_yellow")
            rows += [row, "\n"]

        return Panel(
            Text.assemble(*rows),
            title="[bold bright_cyan]🤖 AI Cycle Results[/bold bright_cyan]",
            border_style="bright_cyan",
        )

    def _cycle_panel(self) -> Panel:
        if not self._cycle_results:
            wait = Text()
            wait.append("  Waiting for first Quant cycle...", style="grey50")
            wait.append(f"  Next in {self._next_in}s", style="bright_cyan")
            return Panel(wait, title="[bold bright_white]AI Cycle Results[/bold bright_white]", border_style="grey42")

        rows: list[object] = []
        hdr = Text()
        hdr.append(f"  Cycle #{self._cycle_num}", style="bold bright_white")
        hdr.append(f" @ {self._cycle_at}", style="grey50")
        hdr.append(f" | Next {self._next_in}s", style="bright_cyan")
        rows += [hdr, "\n"]

        for r in self._cycle_results:
            ticker = str(r.get("ticker", "--"))
            decision = str(r.get("decision", "SKIP")).upper()
            reason = str(r.get("skip_reason", "") or "")
            ev = r.get("ev", None)
            min_ev = r.get("min_ev", None)
            conf = float(r.get("confidence", 0.0) or 0.0)
            style = "bold bright_green" if decision in {"ENTER", "APPROVED", "BEST_TRADE"} else "bright_yellow" if decision == "WATCHLIST" else "grey62"
            row = Text()
            row.append(f"  {ticker:<5}", style="bold white")
            row.append(f" {decision}", style=style)
            if reason and decision in {"SKIP", "REJECTED"}:
                row.append(f" {reason}", style="bright_red" if reason in {"stale_data", "risk_off", "delta_extreme"} else "grey70")
            if ev is not None:
                row.append(f" EV={float(ev):+.3f}", style="bright_green" if float(ev) > 0 else "bright_red")
            if min_ev is not None:
                row.append(f" < {float(min_ev):.3f}" if float(ev or 0.0) < float(min_ev) else f" min={float(min_ev):.3f}", style="grey70")
            row.append(f" CONF={conf:.2f}", style="bright_green" if conf >= 0.65 else "bright_yellow" if conf >= 0.50 else "bright_red")
            rows += [row, "\n"]

        return Panel(
            Text.assemble(*rows),
            title="[bold bright_cyan]AI Cycle Results[/bold bright_cyan]",
            border_style="bright_cyan",
        )

    # ------------------------------------------------------------------
    # AI Layer panel  (5-agent reasoning summary)
    # ------------------------------------------------------------------

    def _ai_layer_panel(self) -> Panel:
        if not self._ai_layer:
            msg = Text()
            msg.append("  🤖 ", style="bold bright_cyan")
            msg.append("AI Layer — waiting for first cycle…  ", style="grey50")
            msg.append(f"⏱  Next in {self._next_in}s", style="bright_cyan")
            return Panel(
                msg,
                title="[bold bright_cyan]🤖 AI Layer — 5-Agent Reasoning[/bold bright_cyan]",
                border_style="bright_cyan",
            )

        rep: dict | None = None
        for layer in self._ai_layer:
            if layer.get("ticker") == "BTC":
                rep = layer
                break
        if rep is None and self._ai_layer:
            rep = self._ai_layer[0]

        rows: list[object] = []

        hdr = Text()
        hdr.append(f"  🔄 Cycle #{self._cycle_num}", style="bold bright_white")
        hdr.append(f"  @ {rep.get('at', '--')}", style="grey50")
        hdr.append("   🎯 Focus: ", style="grey70")
        hdr.append(f"{rep.get('ticker', 'BTC')}", style="bold bright_cyan")
        hdr.append("   ⏱  Next in ", style="grey70")
        hdr.append(f"{self._next_in}s", style="bright_cyan")
        rows += [hdr, "\n"]

        # ── 1. Data Agent ─────────────────────────────────────────────
        quality = str(rep.get("data_quality", "unknown"))
        price   = float(rep.get("data_price", 0.0))
        q_emoji = "✅" if quality == "ok" else "⚠️ " if quality == "incomplete" else "❌"
        q_style = "bright_green" if quality == "ok" else "bright_yellow" if quality == "incomplete" else "bright_red"
        l1 = Text()
        l1.append("  📊 Data     ", style="grey70")
        l1.append(f"{q_emoji} {quality.upper()}", style=q_style)
        l1.append(f"  ${price:,.2f}", style="white")
        ptb    = float(self._markets.get(rep.get("ticker", "BTC"), {}).get("ref_price", 0.0))
        oracle = float(self._markets.get(rep.get("ticker", "BTC"), {}).get("current_price", 0.0))
        if ptb > 0:
            l1.append("  PTB ", style="grey50")
            l1.append(f"${ptb:,.2f}", style="bold white")
        if oracle > 0:
            diff = oracle - ptb
            diff_style = "bright_green" if diff >= 0 else "bright_red"
            arrow = "▲" if diff >= 0 else "▼"
            l1.append(f"  Oracle {arrow}", style=diff_style)
            l1.append(f"${oracle:,.2f}", style=f"bold {diff_style}")
        rows += [l1, "\n"]

        # ── 2. Quant Agent ────────────────────────────────────────────
        edge  = float(rep.get("quant_edge", 0.0))
        ev    = float(rep.get("quant_ev", 0.0))
        qconf = float(rep.get("quant_confidence", 0.0))
        tprob = float(rep.get("quant_true_prob", 0.0))
        edge_style = "bright_green" if edge > 0.03 else "bright_yellow" if edge > 0 else "bright_red"
        ev_style   = "bright_green" if ev > 0 else "bright_red"
        ev_emoji   = "📈" if ev > 0 else "📉"
        l2 = Text()
        l2.append("  ⚡ Quant    ", style="grey70")
        l2.append(f"{ev_emoji} EV ", style=ev_style)
        l2.append(f"{ev:+.2%}", style=f"bold {ev_style}")
        l2.append("  Edge ", style="grey50")
        l2.append(f"{edge:+.2%}", style=f"bold {edge_style}")
        l2.append(f"  Prob {tprob:.2f}", style="white")
        l2.append(f"  Conf {qconf:.0%}", style="grey62")
        rows += [l2, "\n"]

        # ── 3. Strategy Agent ─────────────────────────────────────────
        sig  = str(rep.get("strategy_signal", "--")).lower()
        qual = float(rep.get("strategy_quality", 0.0))
        _sig_map = {
            "long":  ("bold bright_green", "📈 LONG"),
            "short": ("bold bright_red",   "📉 SHORT"),
            "flat":  ("grey50",            "➡  FLAT"),
            "wait":  ("grey62",            "⏳ WAIT"),
        }
        sig_style, sig_label = _sig_map.get(sig, ("white", sig.upper()))
        qual_style  = "bright_green" if qual >= 0.65 else "bright_yellow" if qual >= 0.40 else "bright_red"
        trend_emoji = "🔥" if qual >= 0.70 else "📈" if qual >= 0.50 else "📉"
        setup_bar   = _progress_bar_inline(qual, width=8, color=qual_style)
        l3 = Text()
        l3.append("  📐 Strategy ", style="grey70")
        l3.append(sig_label, style=sig_style)
        l3.append("  Setup ", style="grey50")
        l3.append_text(setup_bar)
        l3.append(f" {qual:.2f}", style=qual_style)
        l3.append(f"  {trend_emoji}", style="white")
        rows += [l3, "\n"]

        # ── 4. Risk Agent ─────────────────────────────────────────────
        rdec  = str(rep.get("risk_decision", "--")).lower()
        rsize = float(rep.get("risk_size", 0.0))
        r_emoji = "✅" if rdec == "approved" else "❌" if rdec == "rejected" else "🛡 "
        r_style = "bright_green" if rdec == "approved" else "bright_red" if rdec == "rejected" else "bright_yellow"
        l4 = Text()
        l4.append("  🛡  Risk     ", style="grey70")
        l4.append(f"{r_emoji} {rdec.upper()}", style=f"bold {r_style}")
        l4.append(f"  Size ", style="grey50")
        l4.append(f"${rsize:.4f}", style="white")
        rows += [l4, "\n"]

        # ── 5. Orchestrator final ─────────────────────────────────────
        final_dec  = str(rep.get("decision", "--")).upper()
        final_conf = float(rep.get("confidence", 0.0))
        _final_map = {
            "BUY":  ("bold bright_green", "🟢 LONG  📈"),
            "SELL": ("bold bright_red",   "🔴 SHORT 📉"),
            "HOLD": ("bright_yellow",     "🟡 HOLD  ⏳"),
            "SKIP": ("grey50",            "⭕ SKIP   "),
        }
        f_style, f_label    = _final_map.get(final_dec, ("white", final_dec))
        f_conf_style        = "bright_green" if final_conf >= 0.65 else "bright_yellow" if final_conf >= 0.50 else "bright_red"
        conf_bar            = _progress_bar_inline(final_conf, width=10, color=f_conf_style)
        l5 = Text()
        l5.append("  🎯 Final    ", style="grey70")
        l5.append(f_label, style=f_style)
        l5.append("  Conf ", style="grey50")
        l5.append_text(conf_bar)
        l5.append(f" {final_conf:.0%}", style=f"bold {f_conf_style}")
        rows += [l5, "\n"]

        # ── Per-ticker mini-summary bar ───────────────────────────────
        sep = Text("  " + "─" * 68, style="grey19")
        rows += [sep, "\n"]
        ticker_row = Text("  ")
        for layer in self._ai_layer:
            tk  = str(layer.get("ticker", "?"))
            dec = str(layer.get("decision", "--")).upper()
            _t_map = {"BUY": "🟢", "HOLD": "🟡", "SKIP": "⭕", "SELL": "🔴"}
            t_emoji = _t_map.get(dec, "·")
            t_style = "bright_green" if dec == "BUY" else "grey50" if dec == "SKIP" else "bright_yellow"
            ticker_row.append(f"{t_emoji} {tk}  ", style=t_style)
        rows.append(ticker_row)

        return Panel(
            Text.assemble(*rows),
            title="[bold bright_cyan]🤖 AI Layer — 5-Agent Reasoning[/bold bright_cyan]",
            border_style="bright_cyan",
        )

    # ------------------------------------------------------------------
    # Recent trades panel
    # ------------------------------------------------------------------

    def _quant_detail_panel(self) -> Panel:
        candidates = [
            m for m in self._markets.values()
            if (
                float(m.get("score", 0.0) or 0.0) > 0
                or float(m.get("ev", 0.0) or 0.0) != 0.0
                or float(m.get("model_p_yes", m.get("p_yes", 0.0)) or 0.0) > 0
                or bool(m.get("skip_reason"))
            )
        ]
        if not candidates:
            return Panel(
                Text("  Best: --\n  Reason: model_not_run", style="grey50"),
                title="[bold bright_white]Quant Detail[/bold bright_white]",
                border_style="grey42",
            )

        best = max(candidates, key=lambda item: float(item.get("score", 0.0) or 0.0))
        ticker = next((tk for tk, data in self._markets.items() if data is best), "--")
        p_yes = float(best.get("model_p_yes", best.get("p_yes", 0.0)) or 0.0)
        p_no = float(best.get("model_p_no", best.get("p_no", 0.0)) or 0.0)
        side = "YES" if p_yes >= p_no else "NO"
        ask = float(best.get("ask_price", 0.0) or best.get("ask", 0.0) or 0.0)
        ev = float(best.get("ev", 0.0) or 0.0)
        min_ev = float(best.get("min_ev", 0.0) or 0.0)
        score = float(best.get("score", 0.0) or 0.0)
        conf = float(best.get("confidence", 0.0) or 0.0)
        delta = str(best.get("delta_regime", "--") or "--")
        delta_mult = float(best.get("delta_multiplier", 0.0) or 0.0)
        size = float(best.get("final_size", 0.0) or 0.0)
        freq = float(best.get("frequency_multiplier", 0.0) or 0.0)
        reason = str(best.get("skip_reason", "") or "")

        l1 = Text()
        l1.append("  Best: ", style="grey70")
        l1.append(f"{ticker} {side}", style="bold bright_white")
        l2 = Text()
        l2.append(f"  Score {score:.2f}", style="bright_cyan")
        l2.append(f" | Model_Y={p_yes:.2f}/Model_N={p_no:.2f}", style="grey70")
        l2.append(f" | ask={ask:.3f}", style="grey70")
        l2.append(f" | EV={ev:+.3f}", style="bright_green" if ev > 0 else "bright_red")
        l2.append(f" | minEV={min_ev:.3f}", style="grey70")
        l3 = Text()
        l3.append(f"  Conf {conf:.2f}", style="bright_green" if conf >= 0.65 else "bright_yellow")
        l3.append(f" | Delta {delta} x{delta_mult:.2f}", style="bright_yellow" if delta == "HIGH" else "bright_red" if delta == "EXTREME" else "bright_green")
        l3.append(f" | Size ${size:.2f}", style="bold bright_cyan")
        l3.append(f" | Freq x{freq:.2f}", style="grey70")
        if reason:
            l3.append(f" | {reason}", style="grey62")
        return Panel(Text.assemble(l1, "\n", l2, "\n", l3), title="[bold bright_white]Quant Detail[/bold bright_white]", border_style="bright_cyan")

    def _arbitrage_panel(self) -> Panel:
        if not self._arbitrage:
            return Panel(
                Text("  Waiting for YES/NO orderbook scan...", style="grey50"),
                title="[bold bright_white]ARB Monitor[/bold bright_white]",
                border_style="grey42",
            )

        table = Table(
            show_header=True,
            header_style="bold bright_white on grey19",
            border_style="grey35",
            box=None,
            expand=True,
            padding=(0, 1),
        )
        table.add_column("MKT",    style="bold white",   width=5)
        table.add_column("Y_ASK",  style="bright_red",   width=7, justify="right")
        table.add_column("N_ASK",  style="bright_red",   width=7, justify="right")
        table.add_column("SUM",    style="grey70",       width=7, justify="right")
        table.add_column("NET",    style="bright_cyan",  width=8, justify="right")
        table.add_column("SIZE",   style="white",        width=8, justify="right")
        table.add_column("PROFIT", style="bright_green", width=8, justify="right")
        table.add_column("RISK",   style="grey70",       width=7, justify="center")
        table.add_column("ACTION", style="white",        width=10, justify="center")

        for ticker in sorted(self._arbitrage):
            a = self._arbitrage[ticker]
            yes_ask = float(a.get("yes_ask", 0.0))
            no_ask = float(a.get("no_ask", 0.0))
            ask_sum = float(a.get("ask_sum", 0.0))
            net = float(a.get("net_edge", 0.0))
            size = float(a.get("max_size", 0.0))
            profit = float(a.get("est_profit", 0.0))
            action = str(a.get("action", "WAIT"))
            risk = str(a.get("fill_risk", "UNKNOWN"))
            executable = bool(a.get("executable", False))

            net_style = "bold bright_green" if net > 0 else "bright_red" if net < 0 else "grey62"
            profit_style = "bold bright_green" if profit > 0 else "grey62"
            risk_style = {"LOW": "bright_green", "MEDIUM": "bright_yellow", "HIGH": "bright_red"}.get(risk, "grey62")
            action_style = "bold bright_green" if executable else "bright_yellow" if action == "EXIT_ARB" else "grey62"

            table.add_row(
                ticker,
                f"{yes_ask:.4f}" if yes_ask > 0 else "--",
                f"{no_ask:.4f}" if no_ask > 0 else "--",
                f"{ask_sum:.4f}" if ask_sum > 0 else "--",
                Text(f"{net:+.2%}", style=net_style),
                f"{size:.2f}" if size > 0 else "--",
                Text(f"${profit:.3f}", style=profit_style),
                Text(risk, style=risk_style),
                Text(action, style=action_style),
            )

        return Panel(
            table,
            title="[bold bright_cyan]ARB Monitor - YES+NO Locked Profit[/bold bright_cyan]",
            border_style="bright_cyan",
        )

    def _trades_panel(self) -> Panel:
        if not self._recent_trades:
            return Panel(
                Text("  💤 No trades yet this session.", style="grey50"),
                title="[bold bright_white]📋 Recent Trades[/bold bright_white]",
                border_style="grey42",
            )

        rows: list[object] = []
        for t in self._recent_trades:
            side   = str(t["side"])
            status = str(t.get("status", "paper"))
            ss     = "bright_green" if side == "BUY" else "bright_red"
            ts     = "grey50" if status == "paper" else "bright_green" if status == "filled" else "bright_yellow"
            side_emoji = "📈" if side == "BUY" else "📉"
            status_emoji = "📄" if status == "paper" else "✅" if status == "filled" else "⏳"

            row = Text()
            row.append(f"  🕐 {t['time']}", style="grey50")
            row.append(f"  {side_emoji} [{ss}]{side:<4}[/{ss}]")
            row.append(f"  {str(t['ticker']):<5}", style="bold bright_white")
            row.append(f"  @ ", style="grey50")
            row.append(f"{float(t['price']):.4f}", style="cyan")
            row.append(f"  qty ", style="grey50")
            row.append(f"{float(t['size']):.2f}", style="white")
            row.append(f"  notional ", style="grey50")
            row.append(f"${float(t['notional']):.2f}", style="bold bright_cyan")
            row.append(f"  {status_emoji} [{ts}]{status}[/{ts}]")
            rows += [row, "\n"]

        return Panel(
            Text.assemble(*rows),
            title="[bold bright_white]📋 Recent Trades[/bold bright_white]",
            border_style="bright_blue",
        )

    def _trades_panel(self) -> Panel:
        if not self._recent_trades:
            return Panel(
                Text("  No trades yet this session.", style="grey50"),
                title="[bold bright_white]Recent Trades[/bold bright_white]",
                border_style="grey42",
            )

        rows: list[object] = []
        for t in self._recent_trades:
            side = str(t.get("side", "--"))
            market = str(t.get("market", t.get("ticker", "--")))
            entry = float(t.get("entry_price", t.get("price", 0.0)) or 0.0)
            exit_price = t.get("exit_price")
            size = float(t.get("size", t.get("notional", 0.0)) or 0.0)
            pnl = float(t.get("realized_pnl", 0.0) or 0.0)
            reason = str(t.get("reason", "--"))
            mode = str(t.get("mode", "--"))
            pnl_style = "bright_green" if pnl >= 0 else "bright_red"
            row = Text()
            row.append(f"  {t.get('time', '--')} ", style="grey50")
            row.append(f"{market:<5}", style="bold white")
            row.append(f" {side:<4}", style="bright_green" if side in {"YES", "BUY"} else "bright_red")
            row.append(f" entry={entry:.3f}", style="grey70")
            if exit_price is not None:
                row.append(f" exit={float(exit_price):.3f}", style="grey70")
            else:
                row.append(" exit=--", style="grey50")
            row.append(f" size=${size:.2f}", style="bright_cyan")
            row.append(f" pnl={pnl:+.3f}", style=f"bold {pnl_style}")
            row.append(f" {reason}", style="grey70")
            row.append(f" {mode}", style="grey50")
            rows += [row, "\n"]

        return Panel(
            Text.assemble(*rows),
            title="[bold bright_white]Recent Trades[/bold bright_white]",
            border_style="bright_blue",
        )

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------

    def _footer(self) -> Text:
        uptime = datetime.now(tz=UTC) - self._started_at
        mins, secs = divmod(int(uptime.total_seconds()), 60)
        now    = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        btc_cd = int(self._markets.get("BTC", {}).get("countdown", 0))
        btc_win = str(self._markets.get("BTC", {}).get("window_ts", "--"))
        return Text(
            f"  🕐 {now}   ⏱ Uptime {mins:02d}:{secs:02d}"
            f"   🔄 Cycle #{self._cycle_num}"
            f"   ⏳ AI {self._next_in}s"
            f"   📊 5m {btc_win} ● {btc_cd}s"
            f"   🌐 WS {self._ws_status}"
            f"   ⌨️  [Ctrl+C] Stop",
            style="grey50",
        )

    def _footer(self) -> Text:
        uptime = datetime.now(tz=UTC) - self._started_at
        mins, secs = divmod(int(uptime.total_seconds()), 60)
        now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        btc_cd = int(self._markets.get("BTC", {}).get("countdown", 0))
        btc_win = str(self._markets.get("BTC", {}).get("window_ts", "--"))
        s = self._session_summary
        if s:
            win_rate = float(s.get("win_rate", 0.0) or 0.0)
            win_txt = "--" if win_rate <= 0 else f"{win_rate * 100:.1f}%"
            session = (
                f" | Session: scanned={s.get('scanned', 0)} opps={s.get('opportunities', 0)} "
                f"entered={s.get('entered', 0)} skipped={s.get('skipped', 0)} canceled={s.get('canceled', 0)} "
                f"win={win_txt} realized={float(s.get('realized_pnl', 0.0) or 0.0):+.2f} "
                f"unrealized={float(s.get('unrealized_pnl', 0.0) or 0.0):+.2f} "
                f"maxDD={float(s.get('max_drawdown', 0.0) or 0.0):.1%} critical={s.get('critical_count', 0)}"
            )
        else:
            session = ""
        return Text(
            f"  {now}   Uptime {mins:02d}:{secs:02d}"
            f"   Cycle #{self._cycle_num}"
            f"   AI {self._next_in}s"
            f"   5m {btc_win} / {btc_cd}s"
            f"   WS {self._ws_status}"
            f"{session}"
            f"   [Ctrl+C] Stop",
            style="grey50",
        )


@dataclass(frozen=True, slots=True)
class DashboardLayout:
    width: int
    height: int
    requested_mode: str
    active_mode: str
    columns: int
    top_height: int
    center_height: int
    bottom_height: int
    log_rows: int
    panel_width: int
    warning: str = ""


class PolymarketRealtimeDisplay:
    """Terminal UI V2: responsive Rich dashboard for Polymarket paper/live runtime."""

    _TICKERS = ["BTC", "ETH"]
    _VALID_UI_MODES = {"auto", "compact", "standard", "wide", "fullscreen"}
    _FPS = {"low": 1, "medium": 4, "high": 8}
    _MIN_WIDTH = 88
    _MIN_HEIGHT = 24
    _RECOMMENDED = "Recommended: 140x40 or wider; fullscreen: 180x48+"

    def __init__(
        self,
        paper_trading: bool = True,
        interval: int = 60,
        snipe_min_edge: float = 0.30,
        ui_mode: str = "auto",
        fps_mode: str = "medium",
        terminal_size_provider: object | None = None,
        console: Console | None = None,
    ) -> None:
        self.paper_trading = paper_trading
        self.interval = interval
        self.snipe_min_edge = snipe_min_edge
        self.ui_mode = ui_mode if ui_mode in self._VALID_UI_MODES else "auto"
        self.fps_mode = fps_mode if fps_mode in self._FPS else "medium"
        self._terminal_size_provider = terminal_size_provider
        self._console = console or _CONSOLE

        self._markets: dict[str, dict] = {
            t: {
                "ref_price": 0.0,
                "current_price": 0.0,
                "is_above": False,
                "price_diff": 0.0,
                "bid": 0.0,
                "ask": 0.0,
                "spread": 0.0,
                "snipe_score": 0.0,
                "signal": "--",
                "confidence": 0.0,
                "decision": "--",
                "size": 0.0,
                "risk_tier": "normal",
                "countdown": 300,
                "window_ts": "--:--",
                "edge_pct": 0.0,
                "p_yes": 0.0,
                "p_no": 0.0,
                "model_p_yes": 0.0,
                "model_p_no": 0.0,
                "yes_bid": 0.0,
                "yes_ask": 0.0,
                "no_bid": 0.0,
                "no_ask": 0.0,
                "yes_mid": 0.0,
                "no_mid": 0.0,
                "clob_source": "CLOB orderbook",
                "orderbook_age_ms": 0,
                "yes_orderbook_age_ms": 0,
                "no_orderbook_age_ms": 0,
                "token_id": "",
                "yes_token_id": "",
                "no_token_id": "",
                "condition_id": "",
                "market_slug": "",
                "outcome": "",
                "token_mapping_warning": "",
                "ev": 0.0,
                "min_ev": 0.0,
                "delta_regime": "--",
                "delta_multiplier": 0.0,
                "skip_reason": "",
                "score": 0.0,
                "ask_price": 0.0,
                "final_size": 0.0,
                "frequency_multiplier": 0.0,
                "last_tick_ms": 0,
                "candidate_trace_id": "",
                "parent_candidate_trace_id": "",
                "trace_link_reason": "",
                "identity_readiness": "",
                "trace_enrichment_status": "",
                "model_attempted": None,
                "probability_visible": None,
                "fair_value_visible": None,
                "ev_visible": None,
                "dominant_model_gap_reason": "",
                "blocked_before_risk_count": 0,
                "dominant_pre_risk_block_reason": "",
                "risk_reachability_status": "",
                "risk_serialization_visibility": "",
                "lifecycle_phase": "",
                "latest_producer": "",
                "latest_schema_version": "",
            }
            for t in self._TICKERS
        }
        self._portfolio: object | None = None
        self._cycle_results: list[dict] = []
        self._cycle_num = 0
        self._cycle_at = "--"
        self._next_in = interval
        self._recent_trades: Deque[dict] = deque(maxlen=8)
        self._rolling_logs: Deque[tuple[str, str, str]] = deque(maxlen=80)
        self._skip_reason_counts: Counter[str] = Counter()
        self._ai_layer: list[dict] = []
        self._arbitrage: dict[str, dict] = {}
        self._session_summary: dict[str, object] = {}
        self._observability_health: dict[str, object] = {}
        self._ws_status = "connecting"
        self._logging_status = "SAFE"
        self._started_at = datetime.now(tz=UTC)
        self._last_layout_signature: tuple[int, int, str] | None = None

        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=self._FPS[self.fps_mode],
            screen=True,
        )

    def __enter__(self) -> "PolymarketRealtimeDisplay":
        self._live.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self._live.__exit__(*args)

    def update_market(self, ticker: str, **kwargs: object) -> None:
        ticker = ticker.upper()
        if ticker in self._markets:
            self._markets[ticker].update(kwargs)
            self._safe_live_update()

    def update_cycle(self, results: list[dict], cycle_num: int) -> None:
        self._cycle_results = results
        self._cycle_num = cycle_num
        self._cycle_at = datetime.now(tz=UTC).strftime("%H:%M:%S")
        for item in results:
            ticker = str(item.get("ticker", "--"))
            decision = str(item.get("decision", "SKIP")).upper()
            reason = str(item.get("skip_reason", "") or "")
            ev = self._as_float(item.get("ev", 0.0))
            if reason:
                self._skip_reason_counts[reason] += 1
            msg = f"{ticker} {decision}"
            if reason:
                msg += f" {reason}"
            msg += f" EV={ev:+.3f}"
            self.add_log(msg, level="WARN" if decision == "SKIP" else "INFO", redraw=False)
        self._safe_live_update()

    def update_portfolio(self, summary: object) -> None:
        self._portfolio = summary
        health = _get_field(summary, "observability_health", None)
        if isinstance(health, Mapping):
            self._observability_health.update(health)
        self._safe_live_update()

    def update_countdown(self, next_in: int) -> None:
        self._next_in = next_in
        self._safe_live_update()

    def update_realtime_batch(self, ticker_updates: dict[str, dict]) -> None:
        now_ms = int(time.time() * 1000)
        for ticker, data in ticker_updates.items():
            ticker = ticker.upper()
            if ticker in self._markets:
                data["last_tick_ms"] = now_ms
                self._markets[ticker].update(data)
        self._safe_live_update()

    def update_ai_layer(self, layers: list[dict]) -> None:
        self._ai_layer = layers
        self._safe_live_update()

    def update_arbitrage(self, ticker: str, **kwargs: object) -> None:
        self._arbitrage[ticker.upper()] = {
            "ticker": ticker.upper(),
            "at": datetime.now(tz=UTC).strftime("%H:%M:%S"),
            **kwargs,
        }
        self._safe_live_update()

    def update_ws_status(self, status: str) -> None:
        self._ws_status = status or "--"
        self._safe_live_update()

    def add_trade(
        self,
        ticker: str,
        side: str,
        price: float,
        size: float,
        notional: float,
        status: str,
        *,
        exit_price: float | None = None,
        realized_pnl: float = 0.0,
        reason: str = "entry",
        mode: str = "--",
    ) -> None:
        trade = {
            "time": datetime.now(tz=UTC).strftime("%H:%M:%S"),
            "market": ticker,
            "ticker": ticker,
            "side": side,
            "entry_price": price,
            "exit_price": exit_price,
            "price": price,
            "size": size,
            "notional": notional,
            "status": status,
            "realized_pnl": realized_pnl,
            "reason": reason,
            "mode": mode,
        }
        self._recent_trades.appendleft(trade)
        label = "PAPER" if self.paper_trading else "LIVE"
        self.add_log(
            f"{label} {reason} {ticker} {side} size=${notional:.2f} price={price:.4f} status={status}",
            level="EXEC",
            redraw=False,
        )
        self._safe_live_update()

    def update_recent_trades(self, trades: list[dict]) -> None:
        self._recent_trades.clear()
        for trade in reversed(trades[-self._recent_trades.maxlen:]):
            self._recent_trades.appendleft(trade)
        self._safe_live_update()

    def update_session_summary(self, summary: dict[str, object]) -> None:
        self._session_summary = summary
        self._safe_live_update()

    def update_observability_health(self, **kwargs: object) -> None:
        self._observability_health.update(kwargs)
        self._safe_live_update()

    def add_log(self, message: str, *, level: str = "INFO", redraw: bool = True) -> None:
        ts = datetime.now(tz=UTC).strftime("%H:%M:%S")
        self._rolling_logs.appendleft((ts, level.upper(), str(message)))
        if "logging" in str(message).lower() and "disabled" in str(message).lower():
            self._logging_status = "FILE DISABLED"
        if redraw:
            self._safe_live_update()

    def _safe_live_update(self) -> None:
        self._live.update(self._render())

    def _terminal_size(self) -> tuple[int, int]:
        provider = self._terminal_size_provider
        if callable(provider):
            width, height = provider()
            return max(20, int(width)), max(10, int(height))
        try:
            size = self._console.size
            return max(20, int(size.width)), max(10, int(size.height))
        except Exception:
            fallback = shutil.get_terminal_size(fallback=(120, 34))
            return max(20, fallback.columns), max(10, fallback.lines)

    def _resolve_layout(self) -> DashboardLayout:
        width, height = self._terminal_size()
        requested = self.ui_mode
        auto_mode = self._auto_mode(width, height)
        active = auto_mode if requested == "auto" else requested
        warning = ""
        if width < self._MIN_WIDTH or height < self._MIN_HEIGHT:
            active = "compact"
            warning = (
                f"Terminal too small ({width}x{height}). Using compact mode. "
                f"Minimum {self._MIN_WIDTH}x{self._MIN_HEIGHT}. {self._RECOMMENDED}"
            )

        if active == "fullscreen":
            columns = 3
            top_height = 7
            center_height = 13
            bottom_height = max(8, height - top_height - center_height - 6)
            log_rows = max(5, min(12, bottom_height - 3))
        elif active == "wide":
            columns = 3
            top_height = 7
            center_height = 12
            bottom_height = max(7, height - top_height - center_height - 6)
            log_rows = max(4, min(10, bottom_height - 3))
        elif active == "standard":
            columns = 2
            top_height = 7
            center_height = 12
            bottom_height = max(7, height - top_height - center_height - 6)
            log_rows = max(4, min(8, bottom_height - 3))
        else:
            columns = 1
            top_height = 7
            center_height = max(8, min(12, height - 18))
            bottom_height = max(6, height - top_height - center_height - 6)
            log_rows = max(3, min(6, bottom_height - 2))

        panel_width = max(24, (width // max(columns, 1)) - 6)
        return DashboardLayout(
            width=width,
            height=height,
            requested_mode=requested,
            active_mode=active,
            columns=columns,
            top_height=top_height,
            center_height=center_height,
            bottom_height=bottom_height,
            log_rows=log_rows,
            panel_width=panel_width,
            warning=warning,
        )

    def _standalone_layout(self) -> DashboardLayout:
        width, height = 180, 48
        return DashboardLayout(
            width=width,
            height=height,
            requested_mode=self.ui_mode,
            active_mode="wide",
            columns=1,
            top_height=7,
            center_height=12,
            bottom_height=10,
            log_rows=8,
            panel_width=width - 8,
            warning="",
        )

    def _auto_mode(self, width: int, height: int) -> str:
        if width >= 176 and height >= 44:
            return "fullscreen"
        if width >= 138 and height >= 34:
            return "wide"
        if width >= 104 and height >= 28:
            return "standard"
        return "compact"

    def _render(self) -> Layout:
        spec = self._resolve_layout()
        signature = (spec.width, spec.height, spec.active_mode)
        if self._last_layout_signature and signature != self._last_layout_signature:
            old_w, old_h, old_mode = self._last_layout_signature
            self.add_log(
                f"resize {old_w}x{old_h}/{old_mode} -> {spec.width}x{spec.height}/{spec.active_mode}",
                level="UI",
                redraw=False,
            )
        self._last_layout_signature = signature

        layout = Layout()
        header_size = 4 if not spec.warning else 5
        layout.split_column(
            Layout(self._header(spec), name="header", size=header_size),
            Layout(name="top", size=spec.top_height),
            Layout(name="center", size=spec.center_height),
            Layout(name="bottom", size=spec.bottom_height),
            Layout(self._footer(), name="footer", size=1),
        )

        if spec.active_mode == "compact":
            layout["top"].split_row(
                Layout(self._portfolio_panel(spec), name="portfolio"),
                Layout(self._risk_panel(spec), name="risk"),
            )
            layout["center"].update(self._market_table(spec))
            layout["bottom"].split_row(
                Layout(self._cycle_panel(spec), name="ai"),
                Layout(self._candidate_observability_panel(spec), name="candidate_obs"),
            )
            return layout

        layout["top"].split_row(
            Layout(self._system_panel(spec), name="system"),
            Layout(self._portfolio_panel(spec), name="portfolio"),
            Layout(self._risk_panel(spec), name="risk"),
        )
        if spec.active_mode == "standard":
            layout["center"].split_row(
                Layout(self._market_card("BTC", spec), name="btc"),
                Layout(self._market_card("ETH", spec), name="eth"),
            )
            layout["bottom"].split_row(
                Layout(self._cycle_panel(spec), name="ai"),
                Layout(self._candidate_observability_panel(spec), name="candidate_obs"),
                Layout(self._rolling_logs_panel(spec), name="logs"),
            )
        else:
            layout["center"].split_row(
                Layout(self._market_card("BTC", spec), name="btc"),
                Layout(self._market_card("ETH", spec), name="eth"),
                Layout(self._cycle_panel(spec), name="ai"),
            )
            layout["bottom"].split_row(
                Layout(self._execution_panel(spec), name="execution"),
                Layout(self._candidate_observability_panel(spec), name="candidate_obs"),
                Layout(self._rolling_logs_panel(spec), name="logs"),
            )
        return layout

    def _header(self, spec: DashboardLayout | None = None) -> Panel:
        spec = spec or self._standalone_layout()
        mode = "PAPER MODE" if self.paper_trading else "LIVE MODE"
        mode_style = "bold white on dark_orange" if self.paper_trading else "bold white on red"
        line1 = Text()
        line1.append(" PolyTrade Bot ", style="bold bright_cyan")
        line1.append(" | Polymarket BTC/ETH 5M Quant Scalper ", style="bold white")
        line1.append(f" {mode} ", style=mode_style)
        line1.append(f" UI={spec.active_mode.upper()} FPS={self.fps_mode.upper()} ", style="grey70")
        line2 = Text()
        line2.append(" Counter-Momentum | Markov Bounds | Kelly Sizing | ExitAgent | Risk Floor", style="grey70")
        if spec.warning:
            line2.append("\n " + self._clip(spec.warning, max(40, spec.width - 8)), style="bold bright_yellow")
        return Panel(Text.assemble(line1, "\n", line2), border_style="bright_cyan", padding=(0, 1))

    def _system_panel(self, spec: DashboardLayout | None = None) -> Panel:
        spec = spec or self._standalone_layout()
        oracle = self._oracle_status()
        orderbook = self._orderbook_status()
        latency = self._latency_ms()
        content = Text()
        self._append_kv(content, "WS", self._clip(self._ws_status, 18), self._status_style(self._ws_status))
        self._append_kv(content, "ORACLE", oracle, self._ok_warn_style(oracle == "OK"))
        self._append_kv(content, "ORDERBOOK", orderbook, self._ok_warn_style(orderbook == "OK"))
        self._append_kv(content, "MODE", "PAPER" if self.paper_trading else "LIVE", "bright_yellow" if self.paper_trading else "bright_red")
        self._append_kv(content, "LATENCY", f"{latency}ms" if latency is not None else "--", "bright_green" if latency is not None and latency <= 1500 else "bright_yellow")
        self._append_kv(content, "LOGGING", self._logging_status, "bright_green" if self._logging_status == "SAFE" else "bright_yellow")
        content.append("\n" + self._clip(self._RECOMMENDED, spec.panel_width), style="grey50")
        return Panel(content, title="[bold bright_white]System Status[/bold bright_white]", border_style="grey42")

    def _portfolio_panel(self, spec: DashboardLayout | None = None) -> Panel:
        spec = spec or self._resolve_layout()
        s = self._portfolio
        if s is None:
            return Panel(Text(" Waiting for portfolio data...", style="grey50"), title="[bold bright_white]Portfolio[/bold bright_white]", border_style="grey42")

        balance = self._as_float(_get_field(s, "account_balance", _get_field(s, "sizing_bankroll", 0.0)))
        start = self._as_float(_get_field(s, "starting_bankroll", balance))
        cash = self._as_float(_get_field(s, "cash", balance))
        open_value = self._as_float(_get_field(s, "open_value", 0.0))
        equity = self._as_float(_get_field(s, "equity", cash + open_value))
        sizing = self._as_float(_get_field(s, "sizing_bankroll", equity))
        realized = self._as_float(_get_field(s, "realized_pnl", _get_field(s, "daily_realized_pnl", 0.0)))
        upnl = self._as_float(_get_field(s, "unrealized_pnl", 0.0))
        source = str(_get_field(s, "balance_source", "--"))
        execution_mode = str(_get_field(s, "execution_mode", "PAPER ONLY" if self.paper_trading else "LIVE"))
        wallet_reference_balance = _get_field(s, "wallet_reference_balance", None)
        wallet_reference_error = str(_get_field(s, "wallet_reference_error", "") or "")
        wallet_reference_label = str(_get_field(s, "wallet_reference_label", "") or "")
        paper_cash = self._as_float(_get_field(s, "paper_cash", cash))
        paper_sizing = self._as_float(_get_field(s, "paper_sizing_balance", sizing))
        tier_id = str(_get_field(s, "bankroll_tier_id", _get_field(s, "bankroll_tier", "--")))
        tier_name = str(_get_field(s, "bankroll_tier_name", ""))
        family = str(_get_field(s, "bankroll_family", "--"))
        profile = str(_get_field(s, "bankroll_risk_profile", "--"))
        bankroll_mode = str(_get_field(s, "bankroll_mode", "STANDARD"))
        micro_active = bool(_get_field(s, "micro_survival_active", False))
        micro_position_size = self._as_float(_get_field(s, "micro_position_size", 0.0))

        eq_style = "bright_green" if equity >= start else "bright_red"
        pnl_style = "bright_green" if realized >= 0 else "bright_red"
        upnl_style = "bright_green" if upnl >= 0 else "bright_red"
        lines = [
            self._line([
                ("Start ", "grey70"), (f"${start:.2f}", "bold white"),
                (" | Cash ", "grey70"), (f"${cash:.2f}", "bold bright_white"),
            ], spec.panel_width),
            self._line([
                ("Open ", "grey70"), (f"${open_value:.2f}", "bold bright_cyan"),
                (" | Equity ", "grey70"), (f"${equity:.2f}", f"bold {eq_style}"),
            ], spec.panel_width),
            self._line([
                ("Sizing ", "grey70"), (f"${sizing:.2f}", "bold white"),
                (" | Source ", "grey70"), (self._clip(source, 18), "bright_white"),
            ], spec.panel_width),
            self._line([
                ("Execution ", "grey70"), (self._clip(execution_mode, 16), "bold bright_yellow" if self.paper_trading else "bold bright_red"),
                (" | ", "grey70"), ("NO LIVE ORDERS" if self.paper_trading else "LIVE ORDERS ENABLED", "bold bright_green" if self.paper_trading else "bold bright_red"),
            ], spec.panel_width),
            self._line([
                ("Realized ", "grey70"), (f"{realized:+.4f}", f"bold {pnl_style}"),
                (" | Unrealized ", "grey70"), (f"{upnl:+.4f}", f"bold {upnl_style}"),
            ], spec.panel_width),
            self._line([
                ("Tier ", "grey70"), (self._clip(tier_id, 18), "bold bright_cyan"),
                (" | ", "grey70"), (self._clip(tier_name, 20), "bright_cyan"),
            ], spec.panel_width),
            self._line([
                ("Family ", "grey70"), (self._clip(family, 12), "bold bright_cyan"),
                (" | Profile ", "grey70"), (self._clip(profile, 22), "bright_yellow"),
            ], spec.panel_width),
            self._line([
                ("Bankroll Mode ", "grey70"), (self._clip(bankroll_mode, 18), "bold bright_yellow" if micro_active else "bright_white"),
                (" | Micro ", "grey70"), ("ON" if micro_active else "OFF", "bold bright_green" if micro_active else "grey62"),
                (" | Size ", "grey70"), (f"${micro_position_size:.4f}" if micro_position_size else "--", "bright_white"),
            ], spec.panel_width),
            self._line([
                ("Legacy Tier ", "grey70"), (str(_get_field(s, "bankroll_tier", "--")), "grey70"),
                (" | RiskOff ", "grey70"), (str(bool(_get_field(s, "risk_off", False))), "bright_red" if bool(_get_field(s, "risk_off", False)) else "bright_green"),
            ], spec.panel_width),
        ]
        if wallet_reference_balance is not None:
            wallet_balance = self._as_float(wallet_reference_balance)
            lines.insert(3, self._line([
                ("Wallet Bankroll ", "grey70"), (f"${wallet_balance:.2f}", "bold bright_cyan"),
                (" | Paper Sizing Balance ", "grey70"), (f"${paper_sizing:.2f}", "bold white"),
            ], spec.panel_width))
            if wallet_reference_label:
                lines.insert(4, self._line([
                    (self._clip(wallet_reference_label, max(20, spec.panel_width - 2)), "bold bright_yellow"),
                ], spec.panel_width))
        elif wallet_reference_error:
            lines.insert(3, self._line([
                ("Wallet bankroll unavailable, fallback to paper_virtual", "bold bright_yellow"),
            ], spec.panel_width))
        if source == "wallet_reference_paper":
            lines.insert(4 if wallet_reference_balance is not None else 3, self._line([
                ("Paper Cash ", "grey70"), (f"${paper_cash:.2f}", "bold bright_white"),
                (" | Source ", "grey70"), ("wallet_reference_paper", "bold bright_white"),
            ], spec.panel_width))
        return Panel(Text.assemble(*self._with_breaks(lines)), title="[bold bright_white]Portfolio[/bold bright_white]", border_style="grey42")

    def _risk_panel(self, spec: DashboardLayout | None = None) -> Panel:
        spec = spec or self._standalone_layout()
        s = self._portfolio or {}
        tier = str(_get_field(s, "bankroll_tier", "--"))
        raw_tier = str(_get_field(s, "raw_bankroll_tier", ""))
        tier_id = str(_get_field(s, "bankroll_tier_id", tier))
        family = str(_get_field(s, "bankroll_family", "--"))
        bankroll_mode = str(_get_field(s, "bankroll_mode", "STANDARD"))
        risk_mode = str(_get_field(s, "risk_mode", "NORMAL"))
        risk_off = bool(_get_field(s, "risk_off", False))
        dd = self._as_float(_get_field(s, "daily_drawdown", _get_field(s, "daily_drawdown_pct", 0.0)))
        exp = self._as_float(_get_field(s, "total_exposure_pct", 0.0))
        cnt = int(self._as_float(_get_field(s, "open_count", 0)))
        maxp = int(self._as_float(_get_field(s, "max_open_positions", 0)))
        mode_style = "bright_green" if risk_mode == "NORMAL" else "bright_yellow" if risk_mode != "LOCKDOWN" else "bold bright_red"
        dd_style = "bright_green" if dd < 0.02 else "bright_yellow" if dd < 0.04 else "bright_red"
        exp_style = "bright_green" if exp < 0.10 else "bright_yellow" if exp < 0.20 else "bright_red"
        lines = [
            self._line([("Mode ", "grey70"), (risk_mode, mode_style), (" | RiskOff ", "grey70"), (str(risk_off), "bright_red" if risk_off else "bright_green")], spec.panel_width),
            self._line([("Tier ", "grey70"), (self._clip(tier_id, 18), "bold bright_cyan"), (" | Family ", "grey70"), (self._clip(family, 10), "bright_cyan")], spec.panel_width),
            self._line([("Bankroll ", "grey70"), (self._clip(bankroll_mode, 18), "bold bright_yellow" if "MICRO" in bankroll_mode else "bright_white"), (" | Raw ", "grey70"), (raw_tier or tier, "bright_yellow" if raw_tier and raw_tier != tier else "grey70")], spec.panel_width),
            self._line([("Exposure ", "grey70"), (f"{exp:.1%}", f"bold {exp_style}"), (" | DD ", "grey70"), (f"{dd:.1%}", f"bold {dd_style}")], spec.panel_width),
            self._line([("Positions ", "grey70"), (f"{cnt}/{maxp}", "bold bright_white"), (" | Guard ", "grey70"), ("LOCKED" if risk_off else "OK", "bright_red" if risk_off else "bright_green")], spec.panel_width),
        ]
        return Panel(Text.assemble(*self._with_breaks(lines)), title="[bold bright_white]Risk[/bold bright_white]", border_style="grey42")

    def _market_table(self, spec: DashboardLayout | None = None) -> Panel:
        spec = spec or self._standalone_layout()
        rows: list[object] = []
        header = Text(" MKT      PTB        ORACLE  YES_BID YES_ASK  NO_BID  NO_ASK SPRD Model_Y Model_N   EV  MIN_EV  DELTA       CONF  DECISION", style="bold grey70")
        rows += [header, "\n"]
        for ticker in self._TICKERS:
            rows += [self._market_line(ticker, spec.panel_width * max(1, spec.columns)), "\n"]
        return Panel(Text.assemble(*rows), title="[bold bright_white]Market Scan[/bold bright_white]", border_style="bright_blue")

    def _market_card(self, ticker: str, spec: DashboardLayout | None = None) -> Panel:
        spec = spec or self._standalone_layout()
        m = self._markets.get(ticker, {})
        price = self._as_float(m.get("current_price", 0.0))
        ptb = self._as_float(m.get("ref_price", 0.0))
        diff = self._as_float(m.get("price_diff", price - ptb if price and ptb else 0.0))
        bid = self._as_float(m.get("bid", 0.0))
        ask = self._as_float(m.get("ask", 0.0))
        spread = self._as_float(m.get("spread", 0.0))
        model_y = self._as_float(m.get("model_p_yes", m.get("p_yes", 0.0)))
        model_n = self._as_float(m.get("model_p_no", m.get("p_no", 0.0)))
        regime = str(m.get("market_regime", m.get("trend_regime", "UNKNOWN")) or "UNKNOWN").upper()
        bull_prob = self._as_float(m.get("bullish_probability", model_y or m.get("p_yes", 0.0)))
        bear_prob = self._as_float(m.get("bearish_probability", model_n or m.get("p_no", 0.0)))
        trend_strength = self._as_float(m.get("signal_trend_strength", m.get("trend_strength", 0.0)))
        vol_score = self._as_float(m.get("signal_volatility_score", m.get("volatility_score", 0.0)))
        yes_bid = self._as_float(m.get("yes_bid", bid if str(m.get("outcome", "")).upper() == "YES" else 0.0))
        yes_ask = self._as_float(m.get("yes_ask", ask if str(m.get("outcome", "")).upper() == "YES" else 0.0))
        no_bid = self._as_float(m.get("no_bid", bid if str(m.get("outcome", "")).upper() == "NO" else 0.0))
        no_ask = self._as_float(m.get("no_ask", ask if str(m.get("outcome", "")).upper() == "NO" else 0.0))
        yes_mid = self._as_float(m.get("yes_mid", (yes_bid + yes_ask) / 2.0 if yes_bid > 0 and yes_ask > 0 else 0.0))
        no_mid = self._as_float(m.get("no_mid", (no_bid + no_ask) / 2.0 if no_bid > 0 and no_ask > 0 else 0.0))
        age_ms = int(self._as_float(m.get("orderbook_age_ms", 0.0)))
        clob_source = str(m.get("clob_source", "CLOB orderbook") or "CLOB orderbook")
        mapping_warning = str(m.get("token_mapping_warning", "") or "")
        ev = self._as_float(m.get("ev", 0.0))
        min_ev = self._as_float(m.get("min_ev", 0.0))
        conf = self._as_float(m.get("confidence", 0.0))
        decision = self._decision_label(m)
        delta = self._delta_label(m)
        remaining = int(self._as_float(m.get("seconds_remaining", m.get("seconds_until_close", 0))))
        first_seen = int(self._as_float(m.get("first_seen_seconds_remaining", 0)))
        first_eval = int(self._as_float(m.get("first_evaluable_seconds_remaining", 0)))
        cutoff_policy = str(m.get("cutoff_policy", m.get("micro_cutoff_policy", "static")) or "static")
        effective_cutoff = int(self._as_float(m.get("effective_cutoff_seconds", m.get("effective_micro_cutoff_seconds", 0))))
        micro_branch = bool(m.get("micro_timing_branch_entered", False))
        micro_allowed = bool(m.get("micro_timing_allowed", False))
        micro_denied = str(m.get("micro_timing_denied_reason", "") or "")
        cutoff_reason = self._compact_deny_reason(m)
        liquidity_state = str(m.get("liquidity_state", "HEALTHY") or "HEALTHY").upper()
        recovery_attempted = bool(m.get("empty_book_recovery_attempted", False))
        recovery_success = bool(m.get("empty_book_recovery_success", False))
        recovery_failed = bool(m.get("empty_book_recovery_failed", False))
        recovery_retries = int(self._as_float(m.get("empty_book_recovery_retry_count", 0)))
        price_style = "bright_green" if diff >= 0 else "bright_red"
        lines = [
            self._line([("Oracle ", "grey70"), (self._fmt_price(price), f"bold {price_style}"), (" | PTB ", "grey70"), (self._fmt_price(ptb), "bold white")], spec.panel_width),
            self._line([("YES Bid ", "grey70"), (self._fmt_prob(yes_bid), "bold bright_green"), (" | YES Ask ", "grey70"), (self._fmt_prob(yes_ask), "bold bright_red")], spec.panel_width),
            self._line([("NO Bid ", "grey70"), (self._fmt_prob(no_bid), "bold bright_green"), (" | NO Ask ", "grey70"), (self._fmt_prob(no_ask), "bold bright_red"), (" | Spread ", "grey70"), (self._fmt_prob(spread), "grey70")], spec.panel_width),
            self._line([("YES Mid ", "grey70"), (self._fmt_prob(yes_mid), "bright_green"), (" | NO Mid ", "grey70"), (self._fmt_prob(no_mid), "bright_red"), (" | Age ", "grey70"), (f"{age_ms}ms" if age_ms else "--", "bright_green" if age_ms and age_ms <= 1500 else "bright_yellow")], spec.panel_width),
            self._line([("Source ", "grey70"), (self._clip(clob_source, 18), "bright_cyan"), (" | Token ", "grey70"), (self._clip(str(m.get("token_id", "") or "--"), 16), "grey62")], spec.panel_width),
            self._line([("Model_Y ", "grey70"), (self._fmt_prob(model_y), "bright_green"), (" | Model_N ", "grey70"), (self._fmt_prob(model_n), "bright_red"), (" | Conf ", "grey70"), (self._fmt_pct(conf), self._confidence_style(conf))], spec.panel_width),
            self._line([("Regime ", "grey70"), (self._clip(regime, 16), "bold bright_cyan"), (" | Bull ", "grey70"), (self._fmt_prob(bull_prob), "bright_green"), (" | Bear ", "grey70"), (self._fmt_prob(bear_prob), "bright_red"), (" | T ", "grey70"), (f"{trend_strength:.2f}", "bright_yellow"), (" V ", "grey70"), (f"{vol_score:.4f}", "grey70")], spec.panel_width),
            self._line([("EV ", "grey70"), (f"{ev:+.3f}" if ev else "--", "bright_green" if ev > 0 else "bright_red" if ev < 0 else "grey62"), (" | Min ", "grey70"), (f"{min_ev:.3f}" if min_ev else "--", "grey70"), (" | ", "grey70"), (delta, "bright_yellow" if "HIGH" in delta else "bright_green")], spec.panel_width),
            self._line([("Decision ", "grey70"), (decision, self._decision_style(decision))], spec.panel_width),
            self._line([
                ("Timing ", "grey70"), (f"remaining={remaining}s" if remaining else "remaining=--", "bright_white"),
                (" | first=", "grey70"), (f"{first_seen}/{first_eval}" if first_seen or first_eval else "--", "bright_cyan"),
            ], spec.panel_width),
            self._line([
                ("Cutoff ", "grey70"), (f"{cutoff_policy} {effective_cutoff}s" if effective_cutoff else cutoff_policy, "bright_yellow"),
                (" | reason ", "grey70"), (self._clip(cutoff_reason or "--", 24), "bright_yellow" if cutoff_reason else "grey62"),
            ], spec.panel_width),
            self._line([
                ("Micro ", "grey70"), (f"branch={self._on_off(micro_branch)} allowed={self._on_off(micro_allowed)}", "bright_green" if micro_allowed else "grey62"),
                (" | deny ", "grey70"), (self._clip(micro_denied or cutoff_reason or "--", 24), "bright_yellow" if micro_denied or cutoff_reason else "grey62"),
            ], spec.panel_width),
            self._line([
                ("Liquidity ", "grey70"), (self._clip(liquidity_state, 12), self._liquidity_style(liquidity_state)),
                (" | Recovery ", "grey70"), (f"a={self._on_off(recovery_attempted)} s={self._on_off(recovery_success)} f={self._on_off(recovery_failed)} r={recovery_retries}", "bright_green" if recovery_success else "bright_red" if recovery_failed else "grey62"),
            ], spec.panel_width),
        ]
        if mapping_warning:
            lines.append(self._line([("Token mapping ", "bold bright_yellow"), (self._clip(mapping_warning, max(12, spec.panel_width - 16)), "bold bright_yellow")], spec.panel_width))
        return Panel(Text.assemble(*self._with_breaks(lines)), title=f"[bold bright_white]{ticker} Market[/bold bright_white]", border_style="bright_blue")

    def _cycle_panel(self, spec: DashboardLayout | None = None) -> Panel:
        spec = spec or self._standalone_layout()
        if not self._cycle_results:
            wait = Text()
            wait.append(" Waiting for first Quant cycle...", style="grey50")
            wait.append(f" Next in {self._next_in}s", style="bright_cyan")
            return Panel(wait, title="[bold bright_white]AI Decision[/bold bright_white]", border_style="grey42")

        rows: list[object] = []
        hdr = Text()
        hdr.append(f" Cycle #{self._cycle_num}", style="bold bright_white")
        hdr.append(f" @ {self._cycle_at}", style="grey50")
        hdr.append(f" | Next {self._next_in}s", style="bright_cyan")
        rows += [hdr, "\n"]

        max_rows = 5 if spec.active_mode in {"wide", "fullscreen"} else 4
        for r in self._cycle_results[:max_rows]:
            ticker = str(r.get("ticker", "--"))
            decision = str(r.get("decision", "SKIP")).upper()
            reason = str(r.get("skip_reason", "") or "")
            compact_reason = self._compact_deny_reason(r) or reason
            ev = self._as_float(r.get("ev", 0.0))
            min_ev = self._as_float(r.get("min_ev", 0.0))
            conf = self._as_float(r.get("confidence", 0.0))
            label = decision
            if compact_reason and decision in {"SKIP", "REJECTED"}:
                label += f" {compact_reason}"
            line = f" {ticker:<4} {label} EV={ev:+.3f}"
            if min_ev:
                line += f" < {min_ev:.3f}" if ev < min_ev else f" min={min_ev:.3f}"
            remaining = int(self._as_float(r.get("seconds_remaining", r.get("seconds_until_close", 0))))
            cutoff = int(self._as_float(r.get("effective_cutoff_seconds", r.get("entry_cutoff_seconds", 0))))
            liquidity = str(r.get("liquidity_state", "") or "")
            regime = str(r.get("market_regime", r.get("trend_regime", "")) or "").upper()
            bull_prob = self._as_float(r.get("bullish_probability", r.get("p_yes", 0.0)))
            bear_prob = self._as_float(r.get("bearish_probability", r.get("p_no", 0.0)))
            vol_score = self._as_float(r.get("signal_volatility_score", r.get("volatility_score", 0.0)))
            micro_on = bool(r.get("micro_timing_branch_entered", False) or r.get("micro_timing_allowed", False))
            context_lines: list[str] = []
            if remaining or cutoff or liquidity or micro_on:
                timing_context = ""
                timing_context += f"remaining={remaining}s" if remaining else ""
                timing_context += f" cutoff={cutoff}s" if cutoff else ""
                timing_context += f" micro={'ON' if micro_on else 'OFF'}"
                context_lines.append(timing_context.strip())
                if liquidity:
                    context_lines.append(f"liquidity={liquidity.upper()}")
            if regime or bull_prob or bear_prob or vol_score:
                context_lines.append(
                    f"regime={regime or '--'} bull={bull_prob:.2f} bear={bear_prob:.2f} vol={vol_score:.4f}"
                )
            line += f" CONF={conf:.2f}"
            rows += [Text(self._clip(line, spec.panel_width), style=self._decision_style(label)), "\n"]
            for context_line in context_lines:
                rows += [Text(self._clip("      " + context_line, spec.panel_width), style="grey70"), "\n"]
        return Panel(Text.assemble(*rows), title="[bold bright_white]AI Decision[/bold bright_white]", border_style="bright_cyan")

    def _candidate_observability_panel(self, spec: DashboardLayout | None = None) -> Panel:
        spec = spec or self._standalone_layout()
        source = self._candidate_observability_source()
        trace_id = self._present_status(source, "candidate_trace_id")
        condition_id = self._present_status(source, "condition_id")
        token_id = self._present_status(source, "token_id")
        side = self._present_status(source, "side", "outcome", "best_side")
        readiness = self._identity_readiness(source)
        chain_confidence = self._candidate_chain_trace_confidence(source)
        trace_status = self._trace_enrichment_status(source)
        model_attempted = self._visibility_status(source, "model_attempted", "ev_visibility_attempted")
        probability_visible = self._visibility_status(source, "probability_visible", "true_probability", "p_yes", "model_p_yes")
        fair_value_visible = self._visibility_status(source, "fair_value_visible", "fair_value")
        ev_visible = self._visibility_status(source, "ev_visible", "ev_after_spread", "ev")
        model_gap = self._first_text_value(
            source,
            "dominant_model_gap",
            "dominant_model_gap_reason",
            "dominant_model_state_gap",
            "model_state_gap",
            "sparse_ev_path_reason",
            "skip_reason",
        ) or "UNKNOWN"
        blocked_before_risk = self._blocked_before_risk_count()
        pre_risk_reason = self._first_text_value(
            source,
            "dominant_pre_risk_cause",
            "dominant_pre_risk_block_reason",
            "dominant_pre_risk_block_cause",
            "pre_risk_block_reason",
            "model_attempt_gate",
        ) or self._compact_deny_reason(source) or "UNKNOWN"
        risk_reachability = self._first_text_value(source, "risk_reachability_status", "decision_to_risk_boundary") or "UNKNOWN"
        risk_serialization = self._first_text_value(source, "risk_serialization_visibility", "risk_serialization_visibility_rate") or "UNKNOWN"
        lifecycle_phase = self._first_text_value(source, "lifecycle_phase") or "UNKNOWN"
        remaining = self._first_text_value(source, "seconds_remaining", "seconds_until_close", "time_remaining_seconds") or "--"
        cutoff_reason = self._compact_deny_reason(source) or self._first_text_value(source, "cutoff_reason") or "--"
        orderbook_ready = self._orderbook_readiness_label(source)
        liquidity = self._first_text_value(source, "liquidity_state") or "--"

        lines = [
            self._line([
                ("Trace ", "grey70"), (trace_id, self._status_word_style(trace_id)),
                (" | Cond ", "grey70"), (condition_id, self._status_word_style(condition_id)),
                (" | Token ", "grey70"), (token_id, self._status_word_style(token_id)),
                (" | Side ", "grey70"), (side, self._status_word_style(side)),
            ], spec.panel_width),
            self._line([
                ("EventID ", "grey70"), (readiness, self._identity_style(readiness)),
                (" | Chain ", "grey70"), (chain_confidence, self._identity_style(chain_confidence)),
            ], spec.panel_width),
            self._line([
                ("Enrich ", "grey70"), (trace_status, self._status_word_style(trace_status)),
            ], spec.panel_width),
            self._line([
                ("Model ", "grey70"), (model_attempted, self._status_word_style(model_attempted)),
                (" | Prob ", "grey70"), (probability_visible, self._status_word_style(probability_visible)),
                (" | FV ", "grey70"), (fair_value_visible, self._status_word_style(fair_value_visible)),
                (" | EV ", "grey70"), (ev_visible, self._status_word_style(ev_visible)),
            ], spec.panel_width),
            self._line([
                ("Gap ", "grey70"), (self._clip(model_gap, max(8, spec.panel_width - 5)), "bright_yellow" if model_gap != "UNKNOWN" else "grey62"),
            ], spec.panel_width),
            self._line([
                ("PreRisk blocked ", "grey70"), (str(blocked_before_risk), "bright_yellow" if blocked_before_risk else "grey62"),
                (" | Cause ", "grey70"), (self._clip(pre_risk_reason, 22), "bright_yellow" if pre_risk_reason != "UNKNOWN" else "grey62"),
            ], spec.panel_width),
            self._line([
                ("Risk reach ", "grey70"), (self._clip(risk_reachability, 16), self._status_word_style(risk_reachability)),
                (" | Serialize ", "grey70"), (self._clip(risk_serialization, 16), self._status_word_style(risk_serialization)),
            ], spec.panel_width),
            self._line([
                ("Phase ", "grey70"), (self._clip(lifecycle_phase, 18), "bright_cyan" if lifecycle_phase != "UNKNOWN" else "grey62"),
                (" | T-", "grey70"), (str(remaining), "bright_white" if remaining != "--" else "grey62"),
                (" | Cutoff ", "grey70"), (self._clip(cutoff_reason, 18), "bright_yellow" if cutoff_reason != "--" else "grey62"),
            ], spec.panel_width),
            self._line([
                ("Orderbook ", "grey70"), (self._clip(orderbook_ready, 14), self._status_word_style(orderbook_ready)),
                (" | Liquidity ", "grey70"), (self._clip(liquidity.upper(), 14), self._liquidity_style(liquidity)),
            ], spec.panel_width),
        ]
        return Panel(
            Text.assemble(*self._with_breaks(lines)),
            title="[bold bright_white]Candidate Observability[/bold bright_white]",
            border_style="bright_magenta",
        )

    def _execution_panel(self, spec: DashboardLayout | None = None) -> Panel:
        spec = spec or self._standalone_layout()
        if not self._recent_trades:
            return Panel(Text(" No orders/fills/exits yet this session.", style="grey50"), title="[bold bright_white]Execution[/bold bright_white]", border_style="grey42")
        rows: list[object] = []
        max_rows = max(3, spec.log_rows)
        for trade in list(self._recent_trades)[:max_rows]:
            side = str(trade.get("side", "--"))
            market = str(trade.get("market", trade.get("ticker", "--")))
            entry = self._as_float(trade.get("entry_price", trade.get("price", 0.0)))
            size = self._as_float(trade.get("size", trade.get("notional", 0.0)))
            pnl = self._as_float(trade.get("realized_pnl", 0.0))
            reason = str(trade.get("reason", "--"))
            line = f" {trade.get('time', '--')} {market:<5} {side:<4} entry={entry:.3f} size=${size:.2f} pnl={pnl:+.3f} {reason}"
            rows += [Text(self._clip(line, spec.panel_width), style="bright_green" if pnl >= 0 else "bright_red"), "\n"]
        return Panel(Text.assemble(*rows), title="[bold bright_white]Execution[/bold bright_white]", border_style="bright_blue")

    def _trades_panel(self, spec: DashboardLayout | None = None) -> Panel:
        return self._execution_panel(spec)

    def _skip_reasons_panel(self, spec: DashboardLayout | None = None) -> Panel:
        spec = spec or self._standalone_layout()
        counts = self._skip_reason_counts.copy()
        for item in self._cycle_results:
            reason = str(item.get("skip_reason", "") or "")
            if reason and reason not in counts:
                counts[reason] = 1
        if not counts:
            return Panel(Text(" No skip reasons recorded yet.", style="grey50"), title="[bold bright_white]Skip Reasons[/bold bright_white]", border_style="grey42")
        rows: list[object] = []
        for reason, count in counts.most_common(max(3, spec.log_rows)):
            rows += [Text(self._clip(f" {count:>3}x {reason}", spec.panel_width), style="grey70"), "\n"]
        return Panel(Text.assemble(*rows), title="[bold bright_white]Skip Reasons[/bold bright_white]", border_style="bright_yellow")

    def _rolling_logs_panel(self, spec: DashboardLayout | None = None) -> Panel:
        spec = spec or self._resolve_layout()
        if not self._rolling_logs:
            msg = " Rolling log window ready. Important decisions and execution events stay here."
            return Panel(Text(self._clip(msg, spec.panel_width), style="grey50"), title="[bold bright_white]Rolling Logs[/bold bright_white]", border_style="grey42")
        rows: list[object] = []
        for ts, level, message in list(self._rolling_logs)[:spec.log_rows]:
            style = "bright_red" if level in {"ERROR", "WARN"} else "bright_cyan" if level in {"EXEC", "UI"} else "grey70"
            rows += [Text(self._clip(f" {ts} {level:<5} {message}", spec.panel_width), style=style), "\n"]
        return Panel(Text.assemble(*rows), title="[bold bright_white]Rolling Logs[/bold bright_white]", border_style="bright_blue")

    def _quant_detail_panel(self) -> Panel:
        return self._cycle_panel()

    def _arbitrage_panel(self) -> Panel:
        return self._system_panel()

    def _footer(self) -> Text:
        uptime = datetime.now(tz=UTC) - self._started_at
        mins, secs = divmod(int(uptime.total_seconds()), 60)
        latency = self._latency_ms()
        risk = str(_get_field(self._portfolio or {}, "risk_mode", "NORMAL"))
        if bool(_get_field(self._portfolio or {}, "risk_off", False)):
            risk = "RISK_OFF"
        parts = [
            f"WS {self._clip(self._ws_status, 16)}",
            f"ORACLE {self._oracle_status()}",
            f"ORDERBOOK {self._orderbook_status()}",
            f"MODE {'PAPER' if self.paper_trading else 'LIVE'}",
            f"RISK {risk}",
            f"LATENCY {latency}ms" if latency is not None else "LATENCY --",
            f"LOGGING {self._logging_status}",
            f"TIER {self._footer_tier_tag()}",
            f"MICRO {self._footer_micro_tag()}",
            f"LIQ {self._footer_liquidity_tag()}",
            f"CUTOFF {self._footer_cutoff_tag()}",
            f"RECOVERY {self._footer_recovery_tag()}",
            f"JSONL {self._footer_jsonl_tag()}",
            f"TRACE {self._footer_trace_tag()}",
            f"COND {self._footer_condition_tag()}",
            f"PROD {self._footer_producer_tag()}",
            f"SCHEMA {self._footer_schema_tag()}",
        ]
        session = ""
        s = self._session_summary
        if s:
            win_rate = self._as_float(s.get("win_rate", 0.0))
            win_txt = "--" if win_rate <= 0 else f"{win_rate * 100:.1f}%"
            session = (
                f" | Session: scanned={s.get('scanned', 0)} opps={s.get('opportunities', 0)} "
                f"entered={s.get('entered', 0)} skipped={s.get('skipped', 0)} canceled={s.get('canceled', 0)} "
                f"win={win_txt} realized={self._as_float(s.get('realized_pnl', 0.0)):+.2f} "
                f"unrealized={self._as_float(s.get('unrealized_pnl', 0.0)):+.2f} "
                f"maxDD={self._as_float(s.get('max_drawdown', 0.0)):.1%} critical={s.get('critical_count', 0)}"
            )
        return Text("  " + " | ".join(parts) + f" | Uptime {mins:02d}:{secs:02d} | Ctrl+C Stop" + session, style="grey50")

    def _market_line(self, ticker: str, width: int) -> Text:
        m = self._markets[ticker]
        decision = self._decision_label(m)
        line = (
            f" {ticker:<4} {self._fmt_price(self._as_float(m.get('ref_price', 0.0))):>10} "
            f"{self._fmt_price(self._as_float(m.get('current_price', 0.0))):>10} "
            f"{self._fmt_prob(self._as_float(m.get('yes_bid', m.get('bid', 0.0)))):>7} "
            f"{self._fmt_prob(self._as_float(m.get('yes_ask', m.get('ask', 0.0)))):>7} "
            f"{self._fmt_prob(self._as_float(m.get('no_bid', 0.0))):>7} "
            f"{self._fmt_prob(self._as_float(m.get('no_ask', 0.0))):>7} "
            f"{self._fmt_prob(self._as_float(m.get('spread', 0.0))):>7} "
            f"{self._fmt_prob(self._as_float(m.get('model_p_yes', m.get('p_yes', 0.0)))):>7} "
            f"{self._fmt_prob(self._as_float(m.get('model_p_no', m.get('p_no', 0.0)))):>7} "
            f"{self._as_float(m.get('ev', 0.0)):+.3f} "
            f"{self._as_float(m.get('min_ev', 0.0)):.3f} "
            f"{self._delta_label(m):<11} "
            f"{self._fmt_pct(self._as_float(m.get('confidence', 0.0))):>5} "
            f"{decision}"
        )
        return Text(self._clip(line, width), style=self._decision_style(decision))

    def _decision_label(self, market: Mapping[str, object]) -> str:
        decision = str(market.get("decision", "--") or "--").upper()
        reason = self._compact_deny_reason(market) or str(market.get("skip_reason", "") or "")
        bid = self._as_float(market.get("bid", 0.0))
        ask = self._as_float(market.get("ask", 0.0))
        if decision in {"", "--"}:
            decision = "SKIP" if reason else "--"
        if decision == "SKIP" and not reason and bid <= 0 and ask <= 0:
            reason = "no_orderbook"
        return f"{decision} {reason}".strip()

    def _compact_deny_reason(self, source: Mapping[str, object]) -> str:
        for key in (
            "micro_timing_denied_reason",
            "adaptive_cutoff_denied_reason",
            "adaptive_cutoff_reason",
            "normalized_skip_reason",
            "orderbook_readiness_reason",
            "orderbook_unavailable_reason",
        ):
            value = str(source.get(key, "") or "").strip()
            if value and value not in {"--", "static_safe", "healthy_late_entry", "micro_healthy_late_entry"}:
                return value
        reason = str(source.get("skip_reason", "") or "").strip()
        lowered = reason.lower()
        if "hard_close_zone" in lowered:
            return "hard_close_zone"
        if "micro_adaptive_window_floor" in lowered:
            return "micro_adaptive_window_floor"
        if "adaptive_cutoff_floor" in lowered:
            return "adaptive_cutoff_floor"
        if "entry cutoff" in lowered:
            return "time_unsafe"
        return reason

    def _on_off(self, value: bool) -> str:
        return "ON" if bool(value) else "OFF"

    def _liquidity_style(self, state: str) -> str:
        state = str(state).upper()
        if state == "HEALTHY":
            return "bright_green"
        if state == "RECOVERING":
            return "bright_yellow"
        if state in {"EMPTY", "THIN"}:
            return "bright_red"
        return "grey62"

    def _footer_tier_tag(self) -> str:
        portfolio = self._portfolio or {}
        tier = str(_get_field(portfolio, "bankroll_tier_id", _get_field(portfolio, "bankroll_tier", "--")) or "--")
        return self._clip(tier.replace("_MICRO_", "_"), 18)

    def _footer_micro_tag(self) -> str:
        portfolio = self._portfolio or {}
        if bool(_get_field(portfolio, "micro_survival_active", False)):
            return "ON"
        if any(bool(m.get("micro_timing_branch_entered") or m.get("micro_timing_allowed")) for m in self._markets.values()):
            return "TIMING"
        return "OFF"

    def _footer_liquidity_tag(self) -> str:
        states = [str(m.get("liquidity_state", "") or "").upper() for m in self._markets.values()]
        for state in ("EMPTY", "THIN", "RECOVERING"):
            if state in states:
                return state
        return "HEALTHY" if "HEALTHY" in states else "--"

    def _footer_cutoff_tag(self) -> str:
        for item in self._cycle_results:
            reason = self._compact_deny_reason(item)
            if reason:
                return self._clip(reason, 18)
        for market in self._markets.values():
            reason = self._compact_deny_reason(market)
            if reason:
                return self._clip(reason, 18)
        return "--"

    def _footer_recovery_tag(self) -> str:
        if any(bool(m.get("empty_book_recovery_failed")) for m in self._markets.values()):
            return "FAIL"
        if any(bool(m.get("empty_book_recovery_success")) for m in self._markets.values()):
            return "OK"
        if any(bool(m.get("empty_book_recovery_attempted")) for m in self._markets.values()):
            return "TRY"
        return "--"

    def _footer_jsonl_tag(self) -> str:
        status = str(self._observability_health.get("jsonl_status", "") or "").upper()
        if status in {"OK", "WARN", "UNKNOWN"}:
            return status
        value = self._observability_health.get("jsonl_ok")
        if value is not None:
            return "OK" if bool(value) else "WARN"
        return "OK" if self._logging_status == "SAFE" else "WARN"

    def _footer_trace_tag(self) -> str:
        value = self._observability_health.get("trace_id_enrichment_ok")
        if value is not None:
            return "OK" if bool(value) else "--"
        return "OK" if self._any_observability_field("candidate_trace_id") else "--"

    def _footer_condition_tag(self) -> str:
        value = self._observability_health.get("condition_id_enrichment_ok")
        if value is not None:
            return "OK" if bool(value) else "--"
        return "OK" if self._any_observability_field("condition_id") else "--"

    def _footer_producer_tag(self) -> str:
        value = self._first_text_value(
            self._observability_health,
            "latest_producer",
            "producer",
            "event_category",
        )
        if not value:
            value = self._first_text_value(
                self._candidate_observability_source(),
                "latest_producer",
                "producer",
                "event_category",
                "source_module",
            )
        return self._clip(value or "--", 16)

    def _footer_schema_tag(self) -> str:
        value = self._first_text_value(
            self._observability_health,
            "latest_schema_version",
            "schema_generation_version",
            "schema_version",
        )
        if not value:
            value = self._first_text_value(
                self._candidate_observability_source(),
                "latest_schema_version",
                "schema_generation_version",
                "schema_version",
            )
        return self._clip(value or "--", 14)

    def _candidate_observability_source(self) -> Mapping[str, object]:
        keys = {
            "candidate_trace_id",
            "candidate_trace_id_present",
            "condition_id",
            "condition_id_present",
            "token_id",
            "token_id_present",
            "side",
            "side_present",
            "outcome",
            "event_identity_readiness",
            "identity_readiness",
            "candidate_chain_trace_confidence",
            "candidate_trace_confidence",
            "model_attempted",
            "probability_visible",
            "fair_value_visible",
            "ev_visible",
            "true_probability",
            "fair_value",
            "ev_after_spread",
            "lifecycle_phase",
            "decision_to_risk_boundary",
            "risk_reachability_status",
        }
        if any(self._observability_health.get(key) not in (None, "") for key in keys):
            return self._observability_health
        for item in self._cycle_results:
            if any(item.get(key) not in (None, "") for key in keys):
                return item
        for market in self._markets.values():
            if any(market.get(key) not in (None, "") for key in keys):
                return market
        return {}

    def _any_observability_field(self, field: str) -> bool:
        if self._observability_health.get(field):
            return True
        if any(bool(item.get(field)) for item in self._cycle_results):
            return True
        return any(bool(market.get(field)) for market in self._markets.values())

    def _present_status(self, source: Mapping[str, object], *fields: str) -> str:
        for field in fields:
            present_key = f"{field}_present"
            if present_key in source:
                return "OK" if bool(source.get(present_key)) else "--"
        return "OK" if any(self._value_present(source.get(field)) for field in fields) else "--"

    def _visibility_status(self, source: Mapping[str, object], *fields: str) -> str:
        for field in fields:
            if field in source:
                value = source.get(field)
                if isinstance(value, bool):
                    return "YES" if value else "NO"
                if isinstance(value, (int, float)):
                    return "YES" if float(value) != 0.0 else "NO"
                if isinstance(value, str) and value.upper() in {"YES", "NO", "UNKNOWN", "OK", "--"}:
                    return "YES" if value.upper() == "OK" else value.upper()
                return "YES" if self._value_present(value) else "NO"
        return "UNKNOWN"

    def _identity_readiness(self, source: Mapping[str, object]) -> str:
        explicit = self._first_text_value(source, "event_identity_readiness", "identity_readiness")
        if explicit:
            upper = explicit.upper()
            if upper in {"DIRECT", "STRONG", "WEAK", "PROXY", "UNKNOWN"}:
                return upper
        has_trace = self._value_present(source.get("candidate_trace_id"))
        has_parent = self._value_present(source.get("parent_candidate_trace_id"))
        has_market = any(self._value_present(source.get(field)) for field in ("market_key", "market_slug", "condition_id", "market_id", "source_market_id"))
        has_token = self._value_present(source.get("token_id"))
        has_side = any(self._value_present(source.get(field)) for field in ("side", "outcome", "best_side"))
        has_phase = self._value_present(source.get("lifecycle_phase"))
        if has_trace and has_parent and has_market and has_token and has_side and has_phase:
            return "DIRECT"
        if has_market and has_token and has_side and has_phase:
            return "STRONG"
        if sum((has_market, has_token, has_side, has_phase)) >= 3:
            return "WEAK"
        if any((has_trace, has_market, has_token, has_side, has_phase)):
            return "PROXY"
        return "UNKNOWN"

    def _candidate_chain_trace_confidence(self, source: Mapping[str, object]) -> str:
        explicit = self._first_text_value(source, "candidate_chain_trace_confidence", "candidate_trace_confidence")
        if explicit:
            upper = explicit.upper()
            if upper in {"DIRECT", "STRONG", "WEAK", "PROXY", "UNKNOWN"}:
                return upper
        return "UNKNOWN"

    def _trace_enrichment_status(self, source: Mapping[str, object]) -> str:
        explicit = self._first_text_value(source, "trace_enrichment_status")
        if explicit:
            return explicit.upper()
        has_trace = self._value_present(source.get("candidate_trace_id"))
        has_condition = self._value_present(source.get("condition_id"))
        if has_trace and has_condition:
            return "TRACE+COND"
        if has_trace:
            return "TRACE_ONLY"
        if has_condition:
            return "COND_ONLY"
        return "UNKNOWN"

    def _blocked_before_risk_count(self) -> int:
        count = int(self._as_float(self._observability_health.get("blocked_before_risk_count", 0)))
        if count:
            return count
        total = 0
        for item in self._cycle_results:
            boundary = str(item.get("decision_to_risk_boundary", "") or "").upper()
            if boundary == "BLOCKED_BEFORE_RISK" or bool(item.get("candidate_blocked_before_risk_visibility")):
                total += 1
        return total

    def _orderbook_readiness_label(self, source: Mapping[str, object]) -> str:
        for key in ("orderbook_readiness_state", "market_readiness_state", "orderbook_state_classification"):
            value = self._first_text_value(source, key)
            if value:
                return value.upper()
        reason = self._first_text_value(source, "orderbook_readiness_reason", "orderbook_unavailable_reason", "orderbook_error")
        if reason:
            return reason
        bid = self._as_float(source.get("bid", 0.0))
        ask = self._as_float(source.get("ask", 0.0))
        return "READY" if bid > 0 and ask > 0 else "UNKNOWN"

    def _first_text_value(self, source: Mapping[str, object], *fields: str) -> str:
        for field in fields:
            value = source.get(field)
            if self._value_present(value):
                return str(value)
        return ""

    def _value_present(self, value: object) -> bool:
        return value is not None and str(value).strip() not in {"", "--", "None", "UNKNOWN"}

    def _status_word_style(self, value: str) -> str:
        upper = str(value).upper()
        if upper in {"OK", "YES", "READY", "TRACE+COND", "DIRECT", "STRONG"}:
            return "bright_green"
        if upper in {"NO", "FAIL", "MISSING", "BLOCKED_BEFORE_RISK"}:
            return "bright_red"
        if upper in {"UNKNOWN", "--"}:
            return "grey62"
        return "bright_yellow"

    def _identity_style(self, value: str) -> str:
        return {
            "DIRECT": "bold bright_green",
            "STRONG": "bright_green",
            "WEAK": "bright_yellow",
            "PROXY": "bright_magenta",
            "UNKNOWN": "grey62",
        }.get(str(value).upper(), "grey62")

    def _decision_style(self, decision: str) -> str:
        upper = decision.upper()
        if any(word in upper for word in ("ENTER", "BUY", "APPROVED", "BEST_TRADE")):
            return "bold bright_green"
        if any(word in upper for word in ("LOCKDOWN", "ERROR", "PANIC")):
            return "bold bright_red"
        if "SKIP" in upper or "REJECT" in upper:
            return "grey62"
        return "bright_yellow"

    def _delta_label(self, market: Mapping[str, object]) -> str:
        regime = str(market.get("delta_regime", "--") or "--").upper()
        mult = self._as_float(market.get("delta_multiplier", 0.0))
        if regime == "--":
            return "--"
        return f"{regime[:4]} x{mult:.2f}"

    def _oracle_status(self) -> str:
        return "OK" if any(self._as_float(m.get("current_price", 0.0)) > 0 for m in self._markets.values()) else "WAIT"

    def _orderbook_status(self) -> str:
        return "OK" if all(self._as_float(m.get("bid", 0.0)) > 0 and self._as_float(m.get("ask", 0.0)) > 0 for m in self._markets.values()) else "WAIT"

    def _latency_ms(self) -> int | None:
        stamps = [int(self._as_float(m.get("last_tick_ms", 0))) for m in self._markets.values() if self._as_float(m.get("last_tick_ms", 0)) > 0]
        if not stamps:
            return None
        return max(0, int(time.time() * 1000) - max(stamps))

    def _status_style(self, value: str) -> str:
        text = str(value).lower()
        if "sync" in text or "ok" in text:
            return "bright_green"
        if "fail" in text or "error" in text:
            return "bright_red"
        return "bright_yellow"

    def _ok_warn_style(self, ok: bool) -> str:
        return "bright_green" if ok else "bright_yellow"

    def _confidence_style(self, value: float) -> str:
        return "bright_green" if value >= 0.65 else "bright_yellow" if value >= 0.50 else "bright_red" if value > 0 else "grey62"

    def _append_kv(self, text: Text, key: str, value: str, style: str) -> None:
        if len(text.plain) > 0:
            text.append("\n")
        text.append(f" {key:<10}", style="grey70")
        text.append(str(value), style=f"bold {style}")

    def _line(self, parts: list[tuple[str, str]], width: int) -> Text:
        text = Text()
        used = 0
        for value, style in parts:
            remaining = max(0, width - used)
            if remaining <= 0:
                break
            clipped = self._clip(value, remaining)
            text.append(clipped, style=style)
            used += len(clipped)
        return text

    def _with_breaks(self, lines: list[Text]) -> list[object]:
        out: list[object] = []
        for idx, line in enumerate(lines):
            out.append(line)
            if idx < len(lines) - 1:
                out.append("\n")
        return out

    def _clip(self, value: object, width: int) -> str:
        text = str(value).replace("\n", " ")
        if width <= 1:
            return ""
        if len(text) <= width:
            return text
        return text[: max(1, width - 1)] + "..."

    def _as_float(self, value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _fmt_price(self, value: float) -> str:
        if value <= 0:
            return "--"
        if value >= 1000:
            return f"${value:,.2f}"
        if value >= 1:
            return f"${value:.4f}"
        return f"${value:.6f}"

    def _fmt_prob(self, value: float) -> str:
        return f"{value:.4f}" if value > 0 else "--"

    def _fmt_pct(self, value: float) -> str:
        return f"{value:.0%}" if value > 0 else "--"


def _progress_bar_block(value: float, width: int = 20, color: str = "bright_green") -> Text:
    filled = round(min(max(value, 0.0), 1.0) * width)
    bar = Text()
    bar.append("▓" * filled, style=color)
    bar.append("░" * (width - filled), style="grey23")
    bar.append(f" {value:.0%}", style="grey62")
    return bar


# ------------------------------------------------------------------
# HFT Paper Trade Display
# ------------------------------------------------------------------

class HFTPaperDisplay:
    """Rich Live terminal display for hft_paper_run.py."""

    def __init__(
        self,
        balance: float,
        floor_usd: float,
        loop_sec: float,
        strong_bet: float,
        medium_bet: float,
        weak_bet: float,
        strong_max: int,
        medium_max: int,
        weak_max: int,
        max_window_exp: float,
        tp_pct: float,
        sl_pct: float,
    ) -> None:
        self._balance        = balance
        self._floor_usd      = floor_usd
        self._loop_sec       = loop_sec
        self._strong_bet     = strong_bet
        self._medium_bet     = medium_bet
        self._weak_bet       = weak_bet
        self._strong_max     = strong_max
        self._medium_max     = medium_max
        self._weak_max       = weak_max
        self._max_window_exp = max_window_exp
        self._tp_pct         = tp_pct
        self._sl_pct         = sl_pct

        self._bankroll:    float = balance
        self._cycle:       int   = 0
        self._spot:        float = 0.0
        self._ptb:         float = 0.0
        self._yes:         float = 0.5
        self._no:          float = 0.5
        self._countdown:   int   = 300
        self._slug:        str   = "—"
        self._win_delta:   float = 0.0
        self._window_ts:   str   = "--:--"

        self._positions:   list  = []
        self._signals:     list  = []
        self._signal_meta: dict  = {}
        self._closed:      list  = []
        self._recent:      list  = []

        self._strong_count: int  = 0
        self._medium_count: int  = 0
        self._weak_count:   int  = 0
        self._window_cost:  float = 0.0
        self._window_cap:   float = 0.0
        self._locked_side:  str  = "FREE"
        self._can_enter:    bool = True
        self._signal_skip:  str  = ""

        self._started_at = datetime.now(tz=UTC)

        self._live = Live(
            self._render(),
            console=_CONSOLE,
            refresh_per_second=2,
            screen=True,
        )

    def __enter__(self) -> "HFTPaperDisplay":
        self._live.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self._live.__exit__(*args)

    def update_market(
        self,
        spot: float, ptb: float, yes: float, no: float,
        countdown: int, slug: str, window_ts: str = "--:--",
    ) -> None:
        self._spot      = spot
        self._ptb       = ptb
        self._yes       = yes
        self._no        = no
        self._countdown = countdown
        self._slug      = slug
        self._window_ts = window_ts
        self._win_delta = (spot - ptb) / ptb * 100.0 if ptb > 0 else 0.0
        self._refresh()

    def update_cycle(
        self,
        cycle: int,
        bankroll: float,
        positions: list,
        closed: list,
        strong_count: int,
        medium_count: int,
        weak_count: int,
        window_cost: float,
        window_cap: float,
        locked_side: str,
        can_enter: bool,
        signal_skip: str,
    ) -> None:
        self._cycle        = cycle
        self._bankroll     = bankroll
        self._positions    = positions
        self._closed       = closed
        self._strong_count = strong_count
        self._medium_count = medium_count
        self._weak_count   = weak_count
        self._window_cost  = window_cost
        self._window_cap   = window_cap
        self._locked_side  = locked_side
        self._can_enter    = can_enter
        self._signal_skip  = signal_skip
        self._refresh()

    def update_signals(self, signals: list, meta: dict | None = None) -> None:
        self._signals     = signals
        self._signal_meta = meta or {}
        self._refresh()

    def add_settled(self, trade: dict) -> None:
        self._recent.insert(0, trade)
        if len(self._recent) > 8:
            self._recent.pop()
        self._refresh()

    def _refresh(self) -> None:
        self._live.update(self._render())

    def _render(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(self._header(),       name="header",   size=4),
            Layout(name="top",                            size=6),
            Layout(self._pos_panel(),    name="pos",      size=7),
            Layout(name="mid",                            size=7),
            Layout(self._recent_panel(), name="recent",   size=6),
            Layout(self._footer(),       name="footer",   size=1),
        )
        layout["top"].split_row(
            Layout(self._market_panel(), name="market"),
            Layout(self._stats_panel(),  name="stats"),
        )
        layout["mid"].split_row(
            Layout(self._signal_panel(),   name="signal"),
            Layout(self._exposure_panel(), name="exposure"),
        )
        return layout

    def _header(self) -> Panel:
        line1 = Text()
        line1.append("🎯  ", style="bold bright_yellow")
        line1.append("PolyTrade HFT", style="bold bright_cyan")
        line1.append("  │  ", style="grey35")
        line1.append(" 🌊 POLYMARKET ", style="bold white on dark_blue")
        line1.append("  ")
        line1.append(" ⏱ 5M BINARY ", style="bold white on purple4")
        line1.append("  ")
        line1.append(" 📄 PAPER TRADE ", style="bold white on dark_orange")

        line2 = Text()
        line2.append("  ⚡ Tiers:  ", style="bright_yellow")
        line2.append(f"🔥 S ${self._strong_bet:.2f}  ", style="bold bright_green")
        line2.append(f"🛡️ M ${self._medium_bet:.2f}  ", style="bold bright_yellow")
        line2.append(f"📉 W ${self._weak_bet:.2f}  ", style="bold bright_red")
        line2.append("│  ", style="grey35")
        line2.append(f"🛑 Floor ${self._floor_usd:.2f}  ", style="bright_red")
        line2.append("│  ", style="grey35")
        line2.append(f"🎯 TP {self._tp_pct*100:.0f}%  ", style="bright_green")
        line2.append(f"🛡️ SL {self._sl_pct*100:.0f}%  ", style="bright_red")
        line2.append("│  ", style="grey35")
        line2.append(f"🔄 Loop {self._loop_sec:g}s", style="grey70")

        content = Text.assemble(line1, "\n", line2)
        return Panel(content, border_style="bright_cyan", padding=(0, 1))

    def _market_panel(self) -> Panel:
        cd = self._countdown
        if cd <= 15:
            cd_style, cd_icon = "bold bright_red", "🔴"
        elif cd <= 60:
            cd_style, cd_icon = "bold bright_yellow", "🟡"
        else:
            cd_style, cd_icon = "grey62", "🟢"

        above       = self._spot > self._ptb
        delta_style = "bright_green" if self._win_delta >= 0 else "bright_red"
        delta_arrow = "▲" if self._win_delta >= 0 else "▼"
        bias_txt    = "✅ YES bias" if above else "❌ NO  bias"
        bias_style  = "bold bright_green" if above else "bold bright_red"

        t = Text()
        t.append("  💰 Spot    ", style="grey70")
        t.append(f"${self._spot:>12,.2f}", style="bold bright_white")
        t.append("\n  🎯 PTB     ", style="grey70")
        t.append(f"${self._ptb:>12,.2f}", style="bold white")
        t.append("\n  📊 Δ Delta ", style="grey70")
        t.append(f"{delta_arrow} {self._win_delta:+.3f}%", style=f"bold {delta_style}")
        t.append("   ")
        t.append(bias_txt, style=bias_style)
        t.append("\n  📈 YES     ", style="grey70")
        t.append(f"{self._yes:.4f}", style="bold bright_green")
        t.append("   📉 NO  ", style="grey70")
        t.append(f"{self._no:.4f}", style="bold bright_red")
        t.append("\n  ⏱  Window  ", style="grey70")
        t.append(f"{self._window_ts}", style="grey62")
        t.append("  ")
        t.append(f"{cd_icon} {cd}s left", style=cd_style)

        return Panel(t, title="[bold bright_white]📡 BTC Market[/bold bright_white]", border_style="bright_blue")

    def _stats_panel(self) -> Panel:
        closed    = self._closed
        wins      = [c for c in closed if c["pnl"] > 0]
        losses    = [c for c in closed if c["pnl"] <= 0]
        total_pnl = sum(c["pnl"] for c in closed)
        wr        = len(wins) / max(len(closed), 1) * 100
        roi       = (self._bankroll - self._balance) / max(self._balance, 0.01) * 100

        pnl_style = "bold bright_green" if total_pnl >= 0 else "bold bright_red"
        wr_style  = "bold bright_green" if wr >= 54 else "bold bright_yellow" if wr >= 50 else "bold bright_red"
        roi_style = "bold bright_green" if roi >= 0 else "bold bright_red"
        bal_style = "bold bright_green" if self._bankroll > self._floor_usd * 2 else "bold bright_red"
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        roi_emoji = "🚀" if roi >= 0 else "🔻"

        t = Text()
        t.append("  💼 Bankroll  ", style="grey70")
        t.append(f"${self._bankroll:.4f}", style=bal_style)
        t.append(f"\n  {roi_emoji} ROI       ", style="grey70")
        t.append(f"{roi:+.2f}%", style=roi_style)
        t.append(f"\n  {pnl_emoji} Total PnL ", style="grey70")
        t.append(f"{total_pnl:+.4f}", style=pnl_style)
        t.append("\n  ✅ Wins  ", style="grey70")
        t.append(f"{len(wins)}", style="bold bright_green")
        t.append("  ❌ Losses  ", style="grey70")
        t.append(f"{len(losses)}", style="bold bright_red")
        t.append("\n  🎯 Win Rate  ", style="grey70")
        t.append(f"{wr:.1f}%", style=wr_style)
        t.append("  Total  ", style="grey70")
        t.append(f"{len(closed)}", style="bold white")

        return Panel(t, title="[bold bright_white]📊 Session Stats[/bold bright_white]", border_style="grey42")

    def _pos_panel(self) -> Panel:
        if not self._positions:
            t = Text("  💤 No open positions this window.", style="grey50")
            return Panel(t, title="[bold bright_white]📂 Open Positions[/bold bright_white]", border_style="grey42")

        table = Table(
            show_header=True,
            header_style="bold bright_white on grey19",
            border_style="grey35",
            box=None,
            expand=True,
            padding=(0, 1),
        )
        table.add_column("TIER",   width=8,  justify="center")
        table.add_column("SIDE",   width=5,  justify="center")
        table.add_column("ENTRY",  width=8,  justify="right")
        table.add_column("CUR",    width=8,  justify="right")
        table.add_column("UNRLZD", width=9,  justify="right")
        table.add_column("COST",   width=7,  justify="right")
        table.add_column("EV",     width=8,  justify="right")
        table.add_column("HELD",   width=7,  justify="right")

        import time as _t
        for pos in self._positions:
            cur   = self._yes if pos.side == "YES" else self._no
            unr   = pos.unrealized(cur)
            held  = int(_t.time() - pos.entry_time)
            tier  = pos.bet_tier

            tier_s = "bold bright_green" if tier == "STRONG" else "bold bright_yellow" if tier == "MEDIUM" else "bold bright_red"
            side_s = "bright_green" if pos.side == "YES" else "bright_red"
            unr_s  = "bright_green" if unr >= 0 else "bright_red"
            arrow  = "▲" if unr >= 0 else "▼"
            tier_icon = "🔥" if tier == "STRONG" else "🛡️" if tier == "MEDIUM" else "📉"
            side_icon = "📈" if pos.side == "YES" else "📉"

            table.add_row(
                Text(f"{tier_icon} {tier}", style=tier_s),
                Text(f"{side_icon} {pos.side}", style=side_s),
                Text(f"{pos.entry_price:.4f}"),
                Text(f"{cur:.4f}"),
                Text(f"{arrow} {abs(unr)*100:.2f}%", style=unr_s),
                Text(f"${pos.cost:.2f}"),
                Text(f"{pos.ev:+.4f}"),
                Text(f"{held}s"),
            )

        return Panel(table, title="[bold bright_white]📂 Open Positions[/bold bright_white]", border_style="bright_blue")

    def _signal_panel(self) -> Panel:
        meta     = self._signal_meta
        rsi      = float(meta.get("rsi",      50.0))
        mom      = float(meta.get("mom",       0.0))
        w_delta  = float(meta.get("win_delta", 0.0))
        p_yes    = float(meta.get("p_yes",     0.5))

        rsi_style = "bright_red" if rsi > 70 else "bright_green" if rsi < 30 else "white"
        mom_style = "bright_green" if mom > 0.3 else "bright_red" if mom < -0.3 else "grey62"
        pd_style  = "bright_green" if w_delta > 0 else "bright_red"
        py_style  = "bright_green" if p_yes > 0.55 else "bright_red" if p_yes < 0.45 else "white"

        t = Text()
        t.append("  📐 RSI-14    ", style="grey70")
        t.append(f"{rsi:.1f}", style=f"bold {rsi_style}")
        t.append("\n  🌊 Momentum  ", style="grey70")
        t.append(f"{mom:+.3f}%", style=f"bold {mom_style}")
        t.append("\n  📊 WinDelta  ", style="grey70")
        t.append(f"{w_delta:+.3f}%", style=f"bold {pd_style}")
        t.append("\n  🎲 P(YES)    ", style="grey70")
        t.append(f"{p_yes:.4f}", style=f"bold {py_style}")

        if self._signals:
            sig   = self._signals[0]
            tier, side, ep, pm, ev, edge = sig[0], sig[1], sig[2], sig[3], sig[4], sig[5]
            ts    = "bold bright_green" if tier == "STRONG" else "bold bright_yellow" if tier == "MEDIUM" else "bold bright_red"
            ev_s  = "bright_green" if ev > 0 else "bright_red"
            t.append("\n  ─── Last Signal ─────────────", style="grey23")
            t.append(f"\n  🔥 Tier  ", style="grey70")
            t.append(f"[{tier}]", style=ts)
            t.append(f" {side} @ {ep:.4f}", style="white")
            t.append(f"\n  ⚡ EV    ", style="grey70")
            t.append(f"{ev:+.4f}", style=f"bold {ev_s}")
            t.append("  Edge  ", style="grey50")
            t.append(f"{edge:+.4f}", style=ev_s)
        elif self._signal_skip:
            t.append("\n  ⭕ Signal ", style="grey70")
            t.append(self._signal_skip, style="grey50")

        return Panel(t, title="[bold bright_cyan]⚡ Signal Engine[/bold bright_cyan]", border_style="bright_cyan")

    def _exposure_panel(self) -> Panel:
        cost   = self._window_cost
        cap    = max(self._window_cap, 0.01)
        pct    = min(cost / cap, 1.0)
        bar_w  = 28
        filled = round(pct * bar_w)
        b_col  = "bright_red" if pct > 0.8 else "bright_yellow" if pct > 0.5 else "bright_green"

        bar = Text()
        bar.append("▓" * filled, style=b_col)
        bar.append("░" * (bar_w - filled), style="grey23")
        bar.append(f" {pct:.0%}", style="grey62")

        lock_s  = "bright_green" if self._locked_side == "YES" else "bright_red" if self._locked_side == "NO" else "grey62"
        enter_s = "bright_green" if self._can_enter else "bright_red"
        enter_t = "✅ CAN ENTER" if self._can_enter else "🚫 NO ENTRY"

        t = Text()
        t.append("  📊 Exposure  ", style="grey70")
        t.append_text(bar)
        t.append(f"\n  💵 Cost      ", style="grey70")
        t.append(f"${cost:.3f}", style="bold white")
        t.append(f" / ${cap:.3f} cap", style="grey50")
        t.append("\n  🔒 Side Lock ", style="grey70")
        t.append(f"{self._locked_side}", style=f"bold {lock_s}")
        t.append("\n  ⚡ Tier Cnt  ", style="grey70")
        t.append(f"🔥 S={self._strong_count}/{self._strong_max}  ", style="bold bright_green")
        t.append(f"🛡️ M={self._medium_count}/{self._medium_max}  ", style="bold bright_yellow")
        t.append(f"📉 W={self._weak_count}/{self._weak_max}", style="bold bright_red")
        t.append("\n  🎯 Entry     ", style="grey70")
        t.append(enter_t, style=f"bold {enter_s}")
        t.append(f"   🔄 Cycle #{self._cycle}", style="grey50")

        return Panel(t, title="[bold bright_white]🪟 Window Exposure[/bold bright_white]", border_style="grey42")

    def _recent_panel(self) -> Panel:
        if not self._recent:
            t = Text("  💤 No settled trades yet.", style="grey50")
            return Panel(t, title="[bold bright_white]📋 Recent Settled[/bold bright_white]", border_style="grey42")

        rows: list[object] = []
        for tr in self._recent:
            pnl    = float(tr["pnl"])
            ps     = "bright_green" if pnl > 0 else "bright_red"
            pe     = "💰" if pnl > 0 else "💥"
            ss     = "bright_green" if tr["side"] == "YES" else "bright_red"
            side_i = "📈" if tr["side"] == "YES" else "📉"
            ts     = "bold bright_green" if tr.get("tier") == "STRONG" else "bold bright_yellow" if tr.get("tier") == "MEDIUM" else "bold bright_red"
            tier_i = "🔥" if tr.get("tier") == "STRONG" else "🛡️" if tr.get("tier") == "MEDIUM" else "📉"
            reason = tr.get("reason", "settle")
            r_emoji = "🎯" if reason == "TP" else "🛑" if reason == "SL" else "⏱️"

            row = Text()
            row.append(f"  🕐 {tr.get('time','--')} ", style="grey50")
            row.append(f"{tier_i} [{tr.get('tier','--'):6s}]", style=ts)
            row.append(f" {side_i} [{ss}]{tr['side']}[/{ss}]")
            row.append(f"  entry={tr.get('entry',0.0):.4f}", style="grey70")
            row.append(f"  exit={tr.get('exit',0.0):.4f}", style="grey70")
            row.append(f"  {pe} ", style="grey70")
            row.append(f"{pnl:+.4f}", style=f"bold {ps}")
            row.append(f"  {r_emoji} [{reason}]", style="grey50")
            rows += [row, "\n"]

        return Panel(
            Text.assemble(*rows),
            title="[bold bright_white]📋 Recent Settled[/bold bright_white]",
            border_style="grey42",
        )

    def _footer(self) -> Text:
        uptime = datetime.now(tz=UTC) - self._started_at
        mins, secs = divmod(int(uptime.total_seconds()), 60)
        now  = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        warn = "   ⚠️  NEAR FLOOR!" if self._bankroll < self._floor_usd * 1.5 else ""
        return Text(
            f"  🕐 {now}   ⏱ Uptime {mins:02d}:{secs:02d}"
            f"   🔄 Cycle #{self._cycle}"
            f"   ⏳ Loop {self._loop_sec:g}s"
            f"   📊 5m {self._window_ts} ● {self._countdown}s"
            f"{warn}   ⌨️  [Ctrl+C] Stop",
            style="grey50",
        )
