from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


def run_5m_dashboard() -> None:
    st.set_page_config(page_title="Polymarket 5M BTC Analysis", layout="wide")
    st.title("Polymarket: 5M BTC Up/Down Analysis")
    st.caption("Visualizing binary event resolution edges based strictly on 1% fixed risk limits.")

    log_dir = Path("runtime/pm_5m_logs")
    
    if not log_dir.exists() or not (log_dir / "summary_5m.json").exists():
        st.warning("No backtest data found. Please run the 5m backtester first.")
        st.code("python -m polymarket.polymarket_backtest_runner")
        return

    try:
        with open(log_dir / "summary_5m.json", "r", encoding="utf-8") as f:
            summary = json.load(f)
            
        trades = pd.read_csv(log_dir / "trades_5m.csv")
    except Exception as e:
        st.error(f"Error loading artifact data: {e}")
        return
    
    col1, col2, col3 = st.columns(3)
    final_bal = summary.get('final_balance', 0)
    start_bal = 10.0
    profit = final_bal - start_bal
    col1.metric("Final Balance", f"${final_bal:.2f}", f"${profit:.2f}")
    col2.metric("Total Trades", len(trades))

    if len(trades) > 0:
        win_rate = (len(trades[trades['profit'] > 0]) / len(trades)) * 100
        col3.metric("Win Rate", f"{win_rate:.2f}%")
        st.subheader("Equity Curve")
        # Line chart showing balance growth
        st.line_chart(trades, x="time", y="balance", use_container_width=True)
        
        st.subheader("Detailed Execution Log")
        st.dataframe(trades, use_container_width=True)
    else:
        col3.metric("Win Rate", "0%")
        st.info("No trades executed during the backtest timeframe.")

if __name__ == "__main__":
    run_5m_dashboard()
