"""
live_dashboard.py — PolyTrade Comprehensive Live Dashboard

Tabs:
  🔴 Live     — real-time signals, balance, equity curve today
  📊 History  — multi-day equity, P&L, win rate
  🧪 Backtest — latest backtest results + equity + trade distribution
  📋 Scan Log — full raw scan log with filters
  ⚙️ Strategy — active config, bankroll tiers, hard limits

Run:
    streamlit run dashboard/live_dashboard.py
"""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Constants ──────────────────────────────────────────────────────────────────
BASE     = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE / "runtime" / "realtime_logs"
BT_DIR   = BASE / "backtest_results" / "polymarket_5m"
REFRESH  = 30   # seconds
SERVER_IP = "199.247.29.111"

ASSET_COLORS: dict[str, str] = {
    "BTC": "#F7931A", "ETH": "#627EEA", "SOL": "#9945FF",
    "XRP": "#00AAE4", "DOGE": "#C3A634", "HYPE": "#00FF88", "BNB": "#F3BA2F",
}

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PolyTrade Live",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"]          { background: #0e1117; }
[data-testid="metric-container"]            { background: #1a1d27; border: 1px solid #2d3047;
                                              border-radius: 12px; padding: 16px; }
[data-testid="stHorizontalBlock"] > div     { padding: 0 4px; }
.stTabs [data-baseweb="tab"]                { font-size: 15px; }
div.stDataFrame                             { border: 1px solid #2d3047; border-radius: 8px; }
.status-badge                               { padding: 4px 10px; border-radius: 6px;
                                              font-size: 13px; font-weight: bold; }
.badge-paper  { background:#2d1f00; color:#ffa500; }
.badge-live   { background:#2d0000; color:#ff4444; }
.badge-ok     { background:#002d15; color:#00ff88; }
</style>
""", unsafe_allow_html=True)


# ── Data loading (all cached) ─────────────────────────────────────────────────

def _today_path(filename: str) -> Path:
    for d in [date.today().isoformat(),
              (date.today() - timedelta(days=1)).isoformat()]:
        p = LOGS_DIR / d / filename
        if p.exists():
            return p
    return LOGS_DIR / date.today().isoformat() / filename


@st.cache_data(ttl=REFRESH)
def load_scans() -> pd.DataFrame:
    path = _today_path("scan_log.csv")
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
        if "timestamp_utc" in df.columns:
            df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=REFRESH)
def load_today_summary() -> dict[str, Any]:
    path = _today_path("daily_summary.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@st.cache_data(ttl=60)
def load_all_summaries() -> pd.DataFrame:
    rows: list[dict] = []
    if not LOGS_DIR.exists():
        return pd.DataFrame()
    for d in sorted(LOGS_DIR.iterdir()):
        f = d / "daily_summary.json"
        if f.exists():
            try:
                rows.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def load_latest_backtest() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    if not BT_DIR.exists():
        return {}, pd.DataFrame(), pd.DataFrame()
    summaries = sorted(BT_DIR.glob("backtest_summary_*.json"), reverse=True)
    if not summaries:
        return {}, pd.DataFrame(), pd.DataFrame()
    latest = summaries[0]
    ts = latest.stem.replace("backtest_summary_", "")
    summary = json.loads(latest.read_text(encoding="utf-8"))
    eq = BT_DIR / f"equity_curve_{ts}.csv"
    tr = BT_DIR / f"trades_{ts}.csv"
    equity = pd.read_csv(eq) if eq.exists() else pd.DataFrame()
    trades = pd.read_csv(tr) if tr.exists() else pd.DataFrame()
    return summary, equity, trades


@st.cache_data(ttl=REFRESH)
def load_cfg() -> dict[str, Any]:
    try:
        from config.settings import get_settings
        s = get_settings()
        return {
            "paper":     s.paper_trading,
            "balance":   s.account_balance,
            "floor":     s.bankroll_floor,
            "mom_lower": s.strategy_mom_lower,
            "mom_upper": s.strategy_mom_upper,
            "threshold": s.strategy_score_threshold,
            "min_rsi":   s.strategy_min_rsi,
            "max_rsi":   s.strategy_max_rsi,
            "min_vol":   s.strategy_min_vol_ratio,
        }
    except Exception:
        return {"paper": True, "balance": 0.0, "floor": 5.0}


# ── Chart theme ────────────────────────────────────────────────────────────────

def _theme(fig: go.Figure, height: int = 300) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="#1a1d27", plot_bgcolor="#1a1d27",
        font_color="#cccccc", height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        xaxis=dict(gridcolor="#2d3047", showgrid=True),
        yaxis=dict(gridcolor="#2d3047", showgrid=True),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


# ── Header ─────────────────────────────────────────────────────────────────────

def render_header(cfg: dict, summary: dict) -> None:
    balance = summary.get("end_balance") or cfg.get("balance", 0.0)
    paper   = cfg.get("paper", True)
    badge   = "badge-paper" if paper else "badge-live"
    label   = "🟠 PAPER TRADING" if paper else "🔴 LIVE TRADING"
    now     = datetime.now(timezone.utc).strftime("%Y-%m-%d  %H:%M:%S UTC")

    c1, c2, c3, c4, c5, c6 = st.columns([4, 2, 2, 2, 3, 2])
    c1.markdown("# 🤖 PolyTrade Bot")
    c2.markdown(f'<span class="status-badge {badge}">{label}</span>', unsafe_allow_html=True)
    c3.metric("Balance", f"${balance:.4f}")
    c4.metric("Floor Limit", f"${cfg.get('floor', 5.0):.2f}")
    c5.markdown(f"<div style='padding-top:16px;color:#555'>{now}</div>", unsafe_allow_html=True)
    c6.markdown(f"<div style='padding-top:16px;color:#888'>IP Address: <code>{SERVER_IP}</code></div>", unsafe_allow_html=True)
    st.divider()


# ── Tab 1: Live ────────────────────────────────────────────────────────────────

def render_live(scans: pd.DataFrame, summary: dict) -> None:
    balance = summary.get("end_balance", 0.0)
    net_pnl = summary.get("net_pnl", 0.0)
    ret_pct = summary.get("return_pct", 0.0)
    wr      = summary.get("win_rate", 0.0) * 100
    wins    = summary.get("wins", 0)
    losses  = summary.get("losses", 0)
    trades  = summary.get("trades_executed", 0)
    scans_n = summary.get("total_scans", 0)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Balance",        f"${balance:.4f}",
              delta=f"+${net_pnl:.4f}" if net_pnl >= 0 else f"${net_pnl:.4f}")
    c2.metric("P&L Today",      f"${net_pnl:+.4f}", f"{ret_pct:+.2f}%")
    c3.metric("Win Rate Today", f"{wr:.1f}%",        f"{wins}W / {losses}L")
    c4.metric("Trades",         str(trades))
    c5.metric("Total Scans",    str(scans_n))
    st.divider()

    if scans.empty:
        st.info("📭 Waiting for data — start the bot with:\n```\npython main.py --mode polymarket-realtime --interval 60\n```")
        return

    # ── Signal feed ───────────────────────────────────────────────────────────
    st.subheader("📡 Signal Feed  (latest 40)")

    feed_cols = [c for c in
                 ["timestamp_utc","asset","signal","score","momentum_pct",
                  "rsi","vol_ratio","decision","position_size","order_status",
                  "skip_reason","bankroll"]
                 if c in scans.columns]
    feed = scans[feed_cols].tail(40).iloc[::-1].reset_index(drop=True)

    def _style_signal(val: str) -> str:
        if val == "YES":  return "background:#002d15;color:#00ff88;font-weight:bold"
        if val == "NO":   return "background:#2d0000;color:#ff4444;font-weight:bold"
        if val == "SKIP": return "color:#555"
        return ""

    styled = feed.style
    if "signal" in feed.columns:
        styled = styled.applymap(_style_signal, subset=["signal"])
    if "decision" in feed.columns:
        styled = styled.applymap(
            lambda v: "color:#00ff88" if v == "approved" else "color:#555",
            subset=["decision"],
        )
    st.dataframe(styled, use_container_width=True, height=380)
    st.divider()

    # ── Charts row ────────────────────────────────────────────────────────────
    col_eq, col_asset, col_pie = st.columns([3, 2, 1])

    with col_eq:
        st.subheader("📈 Balance (today)")
        if "bankroll" in scans.columns and "timestamp_utc" in scans.columns:
            eq = scans[["timestamp_utc","bankroll"]].dropna()
            fig = go.Figure(go.Scatter(
                x=eq["timestamp_utc"], y=eq["bankroll"],
                mode="lines", line=dict(color="#00ff88", width=2),
                fill="tozeroy", fillcolor="rgba(0,255,136,0.06)",
            ))
            st.plotly_chart(_theme(fig, 280), use_container_width=True)
        else:
            st.info("Balance column not yet available.")

    with col_asset:
        st.subheader("🎯 Signals by Asset")
        if "asset" in scans.columns and "signal" in scans.columns:
            act = scans[scans["signal"].isin(["YES","NO"])]
            if not act.empty:
                ac = act.groupby("asset").size().reset_index(name="count")
                fig = px.bar(ac, x="asset", y="count",
                             color="asset", color_discrete_map=ASSET_COLORS)
                fig.update_layout(showlegend=False)
                st.plotly_chart(_theme(fig, 280), use_container_width=True)
            else:
                st.info("No YES/NO signals yet.")

    with col_pie:
        st.subheader("📊 Breakdown")
        if "signal" in scans.columns:
            vc = scans["signal"].value_counts()
            fig = go.Figure(go.Pie(
                labels=vc.index, values=vc.values, hole=0.55,
                marker_colors=[
                    {"YES":"#00ff88","NO":"#ff4444",
                     "SKIP":"#333355","WAIT":"#555577"}.get(l,"#aaa")
                    for l in vc.index
                ],
            ))
            fig.update_traces(textinfo="percent+label")
            st.plotly_chart(_theme(fig, 280), use_container_width=True)


# ── Tab 2: History ─────────────────────────────────────────────────────────────

def render_history(hist: pd.DataFrame) -> None:
    if hist.empty:
        st.info("No historical summaries found yet.")
        return

    df = hist.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

    # Multi-day equity
    st.subheader("📈 Multi-Day Balance")
    if "end_balance" in df.columns:
        fig = go.Figure(go.Scatter(
            x=df["date"], y=df["end_balance"],
            mode="lines+markers", line=dict(color="#00ff88", width=2),
            fill="tozeroy", fillcolor="rgba(0,255,136,0.05)",
            marker=dict(size=6),
        ))
        fig.add_hline(y=5.0, line_dash="dash", line_color="#ff4444",
                      annotation_text="Floor $5.00")
        st.plotly_chart(_theme(fig, 280), use_container_width=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.subheader("💰 Daily P&L")
        if "net_pnl" in df.columns:
            colors = ["#00ff88" if v >= 0 else "#ff4444" for v in df["net_pnl"]]
            fig = go.Figure(go.Bar(x=df["date"], y=df["net_pnl"], marker_color=colors))
            fig.add_hline(y=0, line_color="#555")
            st.plotly_chart(_theme(fig, 250), use_container_width=True)

    with c2:
        st.subheader("🎯 Daily Win Rate")
        if "win_rate" in df.columns:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["win_rate"] * 100,
                mode="lines+markers", line=dict(color="#ffa500", width=2),
            ))
            fig.add_hline(y=51.02, line_dash="dash", line_color="#ff4444",
                          annotation_text="Breakeven 51%")
            fig.update_yaxes(range=[0, 100], ticksuffix="%")
            st.plotly_chart(_theme(fig, 250), use_container_width=True)

    with c3:
        st.subheader("📦 Daily Trades")
        if "trades_executed" in df.columns:
            fig = go.Figure(go.Bar(
                x=df["date"], y=df["trades_executed"],
                marker_color="#627EEA",
            ))
            st.plotly_chart(_theme(fig, 250), use_container_width=True)

    st.subheader("📋 Daily Summary Table")
    show = [c for c in
            ["date","start_balance","end_balance","net_pnl","return_pct",
             "trades_executed","wins","losses","win_rate","total_scans","target_hit"]
            if c in df.columns]
    display = df[show].copy()
    if "win_rate" in display.columns:
        display["win_rate"] = (display["win_rate"] * 100).round(1).astype(str) + "%"
    if "return_pct" in display.columns:
        display["return_pct"] = display["return_pct"].round(4).astype(str) + "%"
    st.dataframe(display.iloc[::-1].reset_index(drop=True),
                 use_container_width=True, height=300)


# ── Tab 3: Backtest ────────────────────────────────────────────────────────────

def render_backtest(summary: dict, equity: pd.DataFrame, trades: pd.DataFrame) -> None:
    if not summary:
        st.info("No backtest results found.\n\nRun: `python main.py --mode polymarket-backtest --days 60`")
        return

    # Metrics row
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Return",        f"{summary.get('total_return_pct',0):+.1f}%")
    c2.metric("Final Balance", f"${summary.get('final_balance',0):.4f}")
    c3.metric("Win Rate",      f"{summary.get('win_rate',0)*100:.1f}%")
    c4.metric("Sharpe",        f"{summary.get('sharpe_ratio',0):.3f}")
    c5.metric("Max DD",        f"{summary.get('max_drawdown_pct',0):.2f}%")
    c6.metric("Profit Factor", f"{summary.get('profit_factor',0):.2f}")

    st.caption(
        f"📅 **{summary.get('asset','?')}** {summary.get('days','?')}d  │  "
        f"Trades: {summary.get('n_trades',0)} "
        f"({summary.get('n_wins',0)}W / {summary.get('n_losses',0)}L / "
        f"{summary.get('n_skipped',0)} skipped)  │  "
        f"Fees: ${summary.get('total_fees_paid',0):.4f}  │  "
        f"Sortino: {summary.get('sortino_ratio',0):.2f}"
    )
    st.divider()

    c_eq, c_hist = st.columns([3, 2])

    with c_eq:
        st.subheader("📈 Equity Curve")
        if not equity.empty and "balance" in equity.columns:
            x = "window_utc" if "window_utc" in equity.columns else equity.columns[0]
            fig = go.Figure(go.Scatter(
                x=equity[x], y=equity["balance"],
                mode="lines", line=dict(color="#00ff88", width=1.5),
                fill="tozeroy", fillcolor="rgba(0,255,136,0.04)",
            ))
            st.plotly_chart(_theme(fig, 320), use_container_width=True)
        else:
            st.info("Equity curve file not found.")

    with c_hist:
        st.subheader("📊 P&L Distribution")
        if not trades.empty and "pnl" in trades.columns:
            placed = (trades[trades["strategy_signal"].isin(["YES","NO"])]
                      if "strategy_signal" in trades.columns else trades)
            fig = px.histogram(placed, x="pnl", nbins=35,
                               color_discrete_sequence=["#627EEA"])
            fig.add_vline(x=0, line_dash="dash", line_color="#ff4444",
                          annotation_text="Break-even")
            fig.update_xaxes(tickprefix="$")
            st.plotly_chart(_theme(fig, 320), use_container_width=True)

    # Trades table
    if not trades.empty:
        st.subheader("📋 Backtest Trades  (last 100 placed)")
        placed = (trades[trades["strategy_signal"].isin(["YES","NO"])]
                  if "strategy_signal" in trades.columns else trades)
        show_cols = [c for c in
                     ["window_utc","side","momentum_pct","score","rsi","vol_ratio",
                      "cost","pnl","fee","bankroll_after","tier"]
                     if c in placed.columns]
        st.dataframe(placed[show_cols].tail(100).iloc[::-1].reset_index(drop=True),
                     use_container_width=True, height=320)


# ── Tab 4: Scan Log ────────────────────────────────────────────────────────────

def render_scan_log(scans: pd.DataFrame) -> None:
    if scans.empty:
        st.info("No scan data today.")
        return

    st.subheader(f"📋 Full Scan Log  ({len(scans):,} rows)")

    # Filters
    fc1, fc2, fc3 = st.columns(3)
    assets = ["All"] + sorted(scans["asset"].unique().tolist()) if "asset" in scans.columns else ["All"]
    signals = ["All"] + sorted(scans["signal"].unique().tolist()) if "signal" in scans.columns else ["All"]
    decisions = ["All"] + sorted(scans["decision"].unique().tolist()) if "decision" in scans.columns else ["All"]

    sel_asset  = fc1.selectbox("Asset",    assets)
    sel_signal = fc2.selectbox("Signal",   signals)
    sel_dec    = fc3.selectbox("Decision", decisions)

    filtered = scans.copy()
    if sel_asset  != "All" and "asset"    in filtered.columns: filtered = filtered[filtered["asset"]    == sel_asset]
    if sel_signal != "All" and "signal"   in filtered.columns: filtered = filtered[filtered["signal"]   == sel_signal]
    if sel_dec    != "All" and "decision" in filtered.columns: filtered = filtered[filtered["decision"] == sel_dec]

    st.caption(f"Showing {len(filtered):,} / {len(scans):,} rows")
    st.dataframe(filtered.iloc[::-1].reset_index(drop=True),
                 use_container_width=True, height=600)

    # Download
    csv = filtered.to_csv(index=False)
    st.download_button("⬇ Download CSV", csv, "scan_log_filtered.csv", "text/csv")


# ── Tab 5: Strategy ────────────────────────────────────────────────────────────

def render_strategy(cfg: dict) -> None:
    st.subheader("🧠 Signal Logic")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Counter-Momentum Parameters** *(from settings.py + .env)*")
        st.json({
            "STRATEGY_MOM_LOWER":    cfg.get("mom_lower", 0.40),
            "STRATEGY_MOM_UPPER":    cfg.get("mom_upper", 1.00),
            "STRATEGY_SCORE_THRESHOLD": cfg.get("threshold", 0.50),
            "STRATEGY_MIN_RSI":      cfg.get("min_rsi", 35.0),
            "STRATEGY_MAX_RSI":      cfg.get("max_rsi", 78.0),
            "STRATEGY_MIN_VOL_RATIO": cfg.get("min_vol", 0.40),
        })
        st.caption("Change via `.env` → restart bot → re-run `--days 60` backtest")

    with col2:
        paper = cfg.get("paper", True)
        if paper:
            st.info("🟠 **PAPER TRADING MODE**\nOrders simulated — no real USDC moved")
        else:
            st.error("🔴 **LIVE TRADING MODE**\nReal orders placed on Polymarket CLOB")

        st.markdown("**Validated Baseline (BTC 60d)**")
        st.json({
            "return":       "+100.15%",
            "sharpe":       1.181,
            "win_rate":     "55.9%",
            "max_drawdown": "10.04%",
            "breakeven":    "51.02%",
            "profit_factor": 1.161,
        })

    st.divider()
    st.subheader("🏦 Bankroll Tiers")
    st.dataframe(pd.DataFrame([
        {"Tier":"micro",        "Balance":"$0–$10",   "Max Risk/Trade":"0.5%",  "Kelly":"10%", "Min Bet":"$0.05"},
        {"Tier":"small",        "Balance":"$10–$100", "Max Risk/Trade":"0.75%", "Kelly":"15%", "Min Bet":"$0.10"},
        {"Tier":"conservative", "Balance":"$100–$1K", "Max Risk/Trade":"1.0%",  "Kelly":"20%", "Min Bet":"$0.50"},
        {"Tier":"balanced",     "Balance":"$1K–$10K", "Max Risk/Trade":"1.25%", "Kelly":"25%", "Min Bet":"$2.00"},
        {"Tier":"growth",       "Balance":"$10K+",    "Max Risk/Trade":"1.5%",  "Kelly":"25%", "Min Bet":"$5.00"},
    ]), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🔒 Hard Limits  *(never override in code)*")
    c1, c2, c3 = st.columns(3)
    c1.metric("Floor Balance",      f"${cfg.get('floor', 5.0):.2f}", "Stop all trading")
    c2.metric("Max Risk / Trade",   "3%", "Hard cap on Kelly")
    c3.metric("Daily Drawdown Stop","10%", "Reset next day")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    scans   = load_scans()
    summary = load_today_summary()
    hist    = load_all_summaries()
    bt_sum, bt_eq, bt_tr = load_latest_backtest()
    cfg     = load_cfg()

    render_header(cfg, summary)

    t1, t2, t3, t4, t5 = st.tabs([
        "🔴  Live",
        "📊  History",
        "🧪  Backtest",
        "📋  Scan Log",
        "⚙️  Strategy",
    ])

    with t1: render_live(scans, summary)
    with t2: render_history(hist)
    with t3: render_backtest(bt_sum, bt_eq, bt_tr)
    with t4: render_scan_log(scans)
    with t5: render_strategy(cfg)

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚙️ Dashboard")
        auto = st.checkbox("Auto-refresh (30s)", value=True)
        if st.button("🔄 Refresh Now"):
            st.cache_data.clear()
            st.rerun()
        st.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
        st.divider()
        st.markdown("**Bot Commands**")
        st.code("python main.py --mode polymarket-realtime --interval 60", language="bash")
        st.code("python main.py --mode polymarket-backtest --days 60", language="bash")

    if auto:
        time.sleep(REFRESH)
        st.cache_data.clear()
        st.rerun()


if __name__ == "__main__":
    main()
