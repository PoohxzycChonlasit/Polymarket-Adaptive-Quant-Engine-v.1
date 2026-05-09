from __future__ import annotations

from rich.console import Console

from utils.display import PolymarketRealtimeDisplay


def _render_text(renderable) -> str:
    console = Console(record=True, width=180, color_system=None)
    console.print(renderable)
    return console.export_text()


def test_market_table_shows_quant_scalper_fields() -> None:
    display = PolymarketRealtimeDisplay()
    display.update_market(
        "BTC",
        bid=0.52,
        ask=0.55,
        spread=0.03,
        p_yes=0.61,
        p_no=0.39,
        model_p_yes=0.61,
        model_p_no=0.39,
        yes_bid=0.52,
        yes_ask=0.55,
        no_bid=0.45,
        no_ask=0.48,
        yes_mid=0.535,
        no_mid=0.465,
        clob_source="CLOB orderbook",
        orderbook_age_ms=250,
        token_id="yes-token",
        ev=0.028,
        min_ev=0.020,
        delta_regime="NORMAL",
        delta_multiplier=0.80,
        confidence=0.71,
        decision="SKIP",
        skip_reason="ev_below_threshold",
    )

    text = _render_text(display._market_table())

    assert "Model_Y" in text
    assert "P_Y" not in text
    assert "YES_BID" in text
    assert "NO_ASK" in text
    assert "EV" in text
    assert "+0.028" in text
    assert "0.020" in text
    assert "NORM x0.80" in text
    assert "SKIP ev_below_threshold" in text


def test_market_card_separates_clob_prices_from_model_probability() -> None:
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (150, 38))
    display.update_market(
        "BTC",
        yes_bid=0.10,
        yes_ask=0.11,
        no_bid=0.89,
        no_ask=0.90,
        yes_mid=0.105,
        no_mid=0.895,
        spread=0.01,
        model_p_yes=0.61,
        model_p_no=0.39,
        confidence=0.71,
        clob_source="CLOB orderbook",
        orderbook_age_ms=120,
        token_id="yes-token",
        decision="SKIP",
    )

    text = _render_text(display._market_card("BTC", display._resolve_layout()))

    assert "YES Bid" in text
    assert "YES Ask" in text
    assert "NO Bid" in text
    assert "NO Ask" in text
    assert "YES Mid" in text
    assert "NO Mid" in text
    assert "Source CLOB orderbook" in text
    assert "Model_Y" in text
    assert "Model_N" in text


def test_portfolio_panel_shows_realtime_bankroll_state() -> None:
    display = PolymarketRealtimeDisplay()
    display.update_portfolio({
        "starting_bankroll": 8.70,
        "cash": 7.90,
        "open_value": 0.80,
        "realized_pnl": 0.10,
        "unrealized_pnl": 0.04,
        "equity": 8.84,
        "sizing_bankroll": 8.84,
        "bankroll_tier": "SEED_TEST",
        "daily_drawdown": 0.0,
        "risk_off": False,
        "open_count": 1,
        "max_open_positions": 3,
        "total_exposure_pct": 0.09,
        "positions": [],
    })

    text = _render_text(display._portfolio_panel())

    assert "Start $8.70" in text
    assert "Cash $7.90" in text
    assert "Open $0.80" in text
    assert "Equity $8.84" in text
    assert "Sizing $8.84" in text
    assert "SEED_TEST" in text
    assert "RiskOff False" in text


def test_cycle_and_footer_show_skip_reason_and_session_summary() -> None:
    display = PolymarketRealtimeDisplay()
    display.update_cycle([
        {
            "ticker": "BTC",
            "decision": "SKIP",
            "skip_reason": "no_orderbook",
            "ev": 0.008,
            "min_ev": 0.035,
            "confidence": 0.61,
        }
    ], cycle_num=3)
    display.update_session_summary({
        "scanned": 48,
        "opportunities": 5,
        "entered": 1,
        "skipped": 47,
        "canceled": 0,
        "win_rate": 0.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "max_drawdown": 0.0,
        "critical_count": 0,
    })

    cycle_text = _render_text(display._cycle_panel())
    footer_text = str(display._footer())

    assert "BTC" in cycle_text
    assert "SKIP no_orderbook" in cycle_text
    assert "EV=+0.008" in cycle_text
    assert "Session: scanned=48 opps=5 entered=1 skipped=47 canceled=0" in footer_text


def test_dashboard_auto_layout_modes_by_terminal_size() -> None:
    cases = [
        ((82, 22), "compact"),
        ((118, 30), "standard"),
        ((150, 38), "wide"),
        ((190, 52), "fullscreen"),
    ]

    for size, expected_mode in cases:
        display = PolymarketRealtimeDisplay(terminal_size_provider=lambda s=size: s)
        spec = display._resolve_layout()
        assert spec.active_mode == expected_mode


def test_dashboard_small_terminal_warns_and_falls_back_to_compact() -> None:
    display = PolymarketRealtimeDisplay(
        ui_mode="fullscreen",
        terminal_size_provider=lambda: (70, 18),
    )

    spec = display._resolve_layout()
    text = _render_text(display._header(spec))

    assert spec.active_mode == "compact"
    assert "Terminal too small" in text
    assert "Minimum" in text


def test_dashboard_long_log_message_is_clipped_inside_rolling_window() -> None:
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (96, 28))
    long_message = "locked csv flush failed " + ("x" * 260)

    display.add_log(long_message, level="WARN", redraw=False)
    text = _render_text(display._rolling_logs_panel(display._resolve_layout()))

    assert "locked csv flush failed" in text
    assert "..." in text
    assert "x" * 180 not in text


def test_dashboard_resize_event_is_recorded_without_duplicate_panels() -> None:
    size = [118, 30]
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: tuple(size))

    first = display._resolve_layout()
    display._render()
    size[:] = [150, 38]
    second = display._resolve_layout()
    display._render()
    logs = _render_text(display._rolling_logs_panel(second))

    assert first.active_mode == "standard"
    assert second.active_mode == "wide"
    assert "resize 118x30/standard -> 1" in logs
    assert any(
        message == "resize 118x30/standard -> 150x38/wide"
        for _ts, _level, message in display._rolling_logs
    )


def test_dashboard_bottom_status_line_contains_required_health_fields() -> None:
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (150, 38))
    display.update_ws_status("Synced")
    display.update_realtime_batch({
        "BTC": {"current_price": 100000.0, "bid": 0.51, "ask": 0.53, "spread": 0.02},
        "ETH": {"current_price": 3000.0, "bid": 0.49, "ask": 0.52, "spread": 0.03},
    })

    footer = str(display._footer())

    assert "WS Synced" in footer
    assert "ORACLE OK" in footer
    assert "ORDERBOOK OK" in footer
    assert "MODE PAPER" in footer
    assert "RISK NORMAL" in footer
    assert "LATENCY" in footer
    assert "LOGGING SAFE" in footer


def test_portfolio_panel_wallet_reference_paper_shows_expected_labels() -> None:
    """wallet_reference_paper portfolio must show Wallet Bankroll, Paper Sizing Balance,
    the source label, and NO LIVE ORDERS."""
    display = PolymarketRealtimeDisplay()
    display.update_portfolio({
        "starting_bankroll": 250.0,
        "cash": 250.0,
        "open_value": 0.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "equity": 250.0,
        "sizing_bankroll": 250.0,
        "paper_cash": 250.0,
        "paper_sizing_balance": 250.0,
        "bankroll_tier": "SMALL",
        "daily_drawdown": 0.0,
        "risk_off": False,
        "open_count": 0,
        "max_open_positions": 3,
        "total_exposure_pct": 0.0,
        "balance_source": "wallet_reference_paper",
        "execution_mode": "PAPER ONLY",
        "no_live_orders": True,
        "wallet_reference_balance": 250.0,
        "wallet_reference_label": "REAL WALLET BALANCE (REFERENCE ONLY)",
        "wallet_reference_error": "",
    })

    text = _render_text(display._portfolio_panel())

    assert "Wallet Bankroll" in text
    assert "$250.00" in text
    assert "wallet_reference_paper" in text
    assert "NO LIVE ORDERS" in text


def test_portfolio_panel_paper_virtual_fallback_shows_fallback_warning() -> None:
    """When wallet_reference fetch fails and falls back to paper_virtual the panel must
    show the fallback warning and still show NO LIVE ORDERS."""
    display = PolymarketRealtimeDisplay()
    display.update_portfolio({
        "starting_bankroll": 100.0,
        "cash": 100.0,
        "open_value": 0.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "equity": 100.0,
        "sizing_bankroll": 100.0,
        "paper_cash": 100.0,
        "paper_sizing_balance": 100.0,
        "bankroll_tier": "SEED_TEST",
        "daily_drawdown": 0.0,
        "risk_off": False,
        "open_count": 0,
        "max_open_positions": 3,
        "total_exposure_pct": 0.0,
        "balance_source": "paper_virtual",
        "execution_mode": "PAPER ONLY",
        "no_live_orders": True,
        "wallet_reference_balance": None,
        "wallet_reference_label": "",
        "wallet_reference_error": "connect unavailable",
    })

    text = _render_text(display._portfolio_panel())

    assert "NO LIVE ORDERS" in text
    # Fallback warning line must appear when wallet_reference_error is set
    assert "wallet bankroll unavailable" in text.lower() or "fallback" in text.lower()
