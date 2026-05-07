from __future__ import annotations

import logging
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import get_settings
from dashboard.data_loader import DashboardSnapshot, load_backtest_snapshot
from utils.logger import setup_logger


LOGGER = logging.getLogger(__name__)


def render_summary(snapshot: DashboardSnapshot) -> None:
    summary = snapshot.summary
    columns = st.columns(5)
    columns[0].metric("Starting Balance", f"${summary.get('starting_balance', 0):,.2f}")
    columns[1].metric("Ending Balance", f"${summary.get('ending_balance', 0):,.2f}")
    columns[2].metric("Win Rate", f"{summary.get('win_rate', 0):,.2f}%")
    columns[3].metric("Profit Factor", f"{summary.get('profit_factor', 0):,.2f}")
    columns[4].metric("Max Drawdown", f"{summary.get('max_drawdown_pct', 0):.2f}%")

    secondary_columns = st.columns(3)
    secondary_columns[0].metric("Total Trades", f"{summary.get('total_trades', 0):,.0f}")
    secondary_columns[1].metric("Total Profit", f"{summary.get('total_profit_pct', 0):,.2f}%")
    secondary_columns[2].metric("Artifact Coverage", f"{sum(snapshot.source_status.values())}/3")


def render_equity_curve(snapshot: DashboardSnapshot) -> None:
    chart_data = snapshot.equity_curve.copy()
    chart_data["timestamp"] = chart_data["timestamp"].astype(str)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=chart_data["timestamp"],
            y=chart_data["equity"],
            mode="lines+markers",
            name="Equity",
        )
    )
    if "drawdown_pct" in chart_data.columns:
        figure.add_trace(
            go.Bar(
                x=chart_data["timestamp"],
                y=chart_data["drawdown_pct"],
                name="Drawdown %",
                yaxis="y2",
                opacity=0.25,
            )
        )

    figure.update_layout(
        title="Equity Curve and Drawdown",
        yaxis={"title": "Equity"},
        yaxis2={"title": "Drawdown %", "overlaying": "y", "side": "right"},
        legend={"orientation": "h"},
    )
    st.plotly_chart(figure, use_container_width=True)


def render_trade_analysis(snapshot: DashboardSnapshot) -> None:
    trades = snapshot.trades.copy()

    profit_chart = px.histogram(
        trades,
        x="profit_pct",
        color="result",
        nbins=20,
        title="Trade Return Distribution",
    )
    duration_chart = px.bar(
        trades,
        x="pair",
        y="duration_min",
        color="result",
        title="Trade Duration By Pair",
    )

    col_left, col_right = st.columns(2)
    col_left.plotly_chart(profit_chart, use_container_width=True)
    col_right.plotly_chart(duration_chart, use_container_width=True)

    st.subheader("Recent Trades")
    st.dataframe(trades, use_container_width=True)


def render_pair_breakdown(snapshot: DashboardSnapshot) -> None:
    trades = snapshot.trades.copy()
    if trades.empty or "pair" not in trades.columns or "profit_pct" not in trades.columns:
        st.info("Pair breakdown becomes available once trade artifacts are loaded.")
        return

    pair_profit = trades.groupby("pair", as_index=False)["profit_pct"].sum()
    pair_count = trades.groupby("pair", as_index=False).size().rename(columns={"size": "trade_count"})

    col_left, col_right = st.columns(2)
    col_left.plotly_chart(
        px.bar(pair_profit, x="pair", y="profit_pct", title="Profit % By Pair"),
        use_container_width=True,
    )
    col_right.plotly_chart(
        px.pie(pair_count, names="pair", values="trade_count", title="Trade Share By Pair"),
        use_container_width=True,
    )


def render_artifact_status(snapshot: DashboardSnapshot, runtime_dir: Path) -> None:
    st.sidebar.subheader("Artifact Status")
    st.sidebar.write(f"Directory: `{runtime_dir.as_posix()}`")
    for artifact_name, loaded_flag in snapshot.source_status.items():
        status_label = "loaded" if loaded_flag else "missing"
        st.sidebar.write(f"- {artifact_name}: {status_label}")


def main() -> None:
    settings = get_settings()
    setup_logger(settings.log_level, settings.log_dir)

    st.set_page_config(page_title="PolyTrade Bot Dashboard", layout="wide")
    st.title("PolyTrade Bot Dashboard")
    st.caption("Overview for trading health, backtest performance, and recent trade behavior.")

    runtime_dir = Path(st.sidebar.text_input("Backtest Data Directory", value="runtime"))
    st.sidebar.markdown("Use the `runtime/` folder to drop exported backtest artifacts.")
    st.sidebar.markdown("Expected files: `backtest_summary.json`, `equity_curve.csv`, `trades.csv`")

    snapshot = load_backtest_snapshot(runtime_dir)
    LOGGER.info("Rendering dashboard with %s trades", len(snapshot.trades))
    render_artifact_status(snapshot, runtime_dir)

    render_summary(snapshot)
    st.divider()
    render_equity_curve(snapshot)
    st.divider()
    render_pair_breakdown(snapshot)
    st.divider()
    render_trade_analysis(snapshot)


if __name__ == "__main__":
    main()
