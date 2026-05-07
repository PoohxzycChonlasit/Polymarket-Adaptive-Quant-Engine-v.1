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
        ev=0.028,
        min_ev=0.020,
        delta_regime="NORMAL",
        delta_multiplier=0.80,
        confidence=0.71,
        decision="SKIP",
        skip_reason="ev_below_threshold",
    )

    text = _render_text(display._market_table())

    assert "P_Y" in text
    assert "EV" in text
    assert "+0.028" in text
    assert "0.020" in text
    assert "NORM x0.80" in text
    assert "SKIP ev_below_threshold" in text


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
