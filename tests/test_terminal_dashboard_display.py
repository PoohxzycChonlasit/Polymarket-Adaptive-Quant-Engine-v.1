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


def test_market_card_and_cycle_show_regime_probability_context() -> None:
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (180, 48))
    display.update_market(
        "BTC",
        yes_bid=0.52,
        yes_ask=0.54,
        no_bid=0.46,
        no_ask=0.48,
        model_p_yes=0.58,
        model_p_no=0.42,
        confidence=0.66,
        market_regime="TREND_UP",
        bullish_probability=0.62,
        bearish_probability=0.38,
        signal_trend_strength=0.71,
        signal_volatility_score=0.0042,
        decision="SKIP",
    )
    display.update_cycle([
        {
            "ticker": "BTC",
            "decision": "SKIP",
            "skip_reason": "ev_below_threshold",
            "market_regime": "TREND_UP",
            "bullish_probability": 0.62,
            "bearish_probability": 0.38,
            "signal_volatility_score": 0.0042,
            "ev": 0.008,
            "confidence": 0.66,
        }
    ], cycle_num=4)

    card = _render_text(display._market_card("BTC", display._resolve_layout()))
    cycle = _render_text(display._cycle_panel(display._resolve_layout()))

    assert "Regime TREND_UP" in card
    assert "Bull 0.6200" in card
    assert "regime=TREND_UP bull=0.62 bear=0.38 vol=0.0042" in cycle


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


def test_portfolio_panel_shows_bankroll_tier_v2_and_micro_survival_state() -> None:
    display = PolymarketRealtimeDisplay()
    display.update_portfolio({
        "starting_bankroll": 20.0,
        "cash": 20.0,
        "open_value": 0.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "equity": 20.0,
        "sizing_bankroll": 20.0,
        "bankroll_tier": "T0_MICRO_SEED",
        "bankroll_tier_id": "T0_MICRO_SEED",
        "bankroll_tier_name": "Micro Seed",
        "bankroll_family": "MICRO",
        "bankroll_risk_profile": "seed_protection",
        "bankroll_mode": "MICRO_SURVIVAL",
        "micro_survival_active": True,
        "micro_position_size": 0.05,
        "daily_drawdown": 0.0,
        "risk_off": False,
        "open_count": 0,
        "max_open_positions": 3,
        "total_exposure_pct": 0.0,
    })

    text = _render_text(display._portfolio_panel())

    assert "T0_MICRO_SEED" in text
    assert "Micro Seed" in text
    assert "Family MICRO" in text
    assert "Profile seed_protection" in text
    assert "Bankroll Mode MICRO_SURVIVAL" in text
    assert "Micro ON" in text
    assert "$0.0500" in text


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


def test_cycle_panel_shows_compact_cutoff_micro_liquidity_context() -> None:
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (180, 48))
    display.update_cycle([
        {
            "ticker": "BTC",
            "decision": "SKIP",
            "skip_reason": "Entry cutoff: 12s <= 35s",
            "normalized_skip_reason": "time_unsafe",
            "micro_timing_denied_reason": "hard_close_zone",
            "seconds_remaining": 12,
            "effective_cutoff_seconds": 35,
            "micro_timing_branch_entered": True,
            "micro_timing_allowed": False,
            "liquidity_state": "HEALTHY",
            "ev": 0.0,
            "confidence": 0.0,
        }
    ], cycle_num=9)

    text = _render_text(display._cycle_panel(display._resolve_layout()))

    assert "SKIP hard_close_zone" in text
    assert "remaining=12s" in text
    assert "cutoff=35s" in text
    assert "micro=ON" in text
    assert "liquidity=HEALTHY" in text


def test_candidate_observability_panel_shows_trace_model_prerisk_and_lifecycle_state() -> None:
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (180, 48))
    display.update_cycle([
        {
            "ticker": "BTC",
            "decision": "SKIP",
            "candidate_trace_id": "ct_abc",
            "condition_id": "condition-btc",
            "token_id": "yes-token",
            "side": "YES",
            "lifecycle_phase": "OPENING_SCAN",
            "model_attempted": True,
            "true_probability": 0.61,
            "fair_value": 0.61,
            "ev_after_spread": 0.018,
            "dominant_model_gap_reason": "MODEL_ATTEMPTED_OUTPUT_MISSING",
            "decision_to_risk_boundary": "BLOCKED_BEFORE_RISK",
            "dominant_pre_risk_block_reason": "EV_NOT_VISIBLE",
            "risk_reachability_status": "RISK_NOT_REACHED",
            "risk_serialization_visibility": "NO",
            "seconds_remaining": 44,
            "cutoff_reason": "time_unsafe",
            "orderbook_readiness_state": "READY",
            "liquidity_state": "HEALTHY",
        }
    ], cycle_num=10)

    text = _render_text(display._candidate_observability_panel(display._resolve_layout()))

    assert "Candidate Observability" in text
    assert "Trace OK" in text
    assert "Cond OK" in text
    assert "Token OK" in text
    assert "Side OK" in text
    assert "EventID STRONG" in text
    assert "Chain UNKNOWN" in text
    assert "Enrich TRACE+COND" in text
    assert "Model YES" in text
    assert "Prob YES" in text
    assert "FV YES" in text
    assert "EV YES" in text
    assert "MODEL_ATTEMPTED_OUTPUT_MISSING" in text
    assert "PreRisk blocked 1" in text
    assert "EV_NOT_VISIBLE" in text
    assert "Risk reach RISK_NOT_REACHED" in text
    assert "Serialize NO" in text
    assert "Phase OPENING_SCAN" in text
    assert "T-44" in text
    assert "Cutoff time_unsafe" in text
    assert "Orderbook READY" in text
    assert "Liquidity HEALTHY" in text


def test_candidate_observability_panel_preserves_unknowns_when_fields_missing() -> None:
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (118, 30))

    text = _render_text(display._candidate_observability_panel(display._resolve_layout()))

    assert "Trace --" in text
    assert "Cond --" in text
    assert "EventID UNKNOWN" in text
    assert "Chain UNKNOWN" in text
    assert "Model UNKNOWN" in text
    assert "Gap UNKNOWN" in text


def test_observability_footer_shows_jsonl_trace_condition_producer_and_schema() -> None:
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (180, 48))
    display.update_market(
        "BTC",
        candidate_trace_id="ct_abc",
        condition_id="condition-btc",
        latest_producer="decision_log",
        latest_schema_version="1.0",
    )
    display.update_observability_health(jsonl_ok=True)

    footer = str(display._footer())

    assert "JSONL OK" in footer
    assert "TRACE OK" in footer
    assert "COND OK" in footer
    assert "PROD decision_log" in footer
    assert "SCHEMA 1.0" in footer


def test_candidate_observability_panel_consumes_dedicated_health_state() -> None:
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (180, 48))
    display.update_observability_health(
        jsonl_status="OK",
        latest_producer="execution_log",
        latest_schema_version="1.0",
        trace_enrichment_status="TRACE+COND",
        condition_enrichment_status="OK",
        candidate_trace_id_present=True,
        condition_id_present=True,
        token_id_present=True,
        side_present=True,
        event_identity_readiness="DIRECT",
        candidate_chain_trace_confidence="STRONG",
        model_attempted="YES",
        probability_visible="YES",
        fair_value_visible="YES",
        ev_visible="NO",
        dominant_model_gap="no_probability_model_output",
        blocked_before_risk_count=3,
        dominant_pre_risk_cause="EV_NOT_VISIBLE",
        risk_reachability_status="BLOCKED_BEFORE_RISK",
        risk_serialization_status="UNKNOWN",
    )

    panel = _render_text(display._candidate_observability_panel(display._resolve_layout()))
    footer = str(display._footer())

    assert "Trace OK" in panel
    assert "EventID DIRECT" in panel
    assert "Chain STRONG" in panel
    assert "Model YES" in panel
    assert "EV NO" in panel
    assert "no_probability_model_output" in panel
    assert "PreRisk blocked 3" in panel
    assert "EV_NOT_VISIBLE" in panel
    assert "Risk reach BLOCKED_BEFO" in panel
    assert "JSONL OK" in footer
    assert "PROD execution_log" in footer
    assert "SCHEMA 1.0" in footer


def test_portfolio_update_can_carry_observability_health_to_footer() -> None:
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (180, 48))

    display.update_portfolio({
        "starting_bankroll": 20.0,
        "cash": 20.0,
        "open_value": 0.0,
        "equity": 20.0,
        "sizing_bankroll": 20.0,
        "bankroll_tier": "T0_MICRO_SEED",
        "risk_off": False,
        "observability_health": {
            "jsonl_status": "OK",
            "trace_id_enrichment_ok": True,
            "condition_id_enrichment_ok": True,
            "latest_producer": "decision_log",
            "latest_schema_version": "1.0",
        },
    })

    footer = str(display._footer())

    assert "JSONL OK" in footer
    assert "TRACE OK" in footer
    assert "COND OK" in footer
    assert "PROD decision_log" in footer
    assert "SCHEMA 1.0" in footer


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


def test_market_card_and_footer_show_timing_liquidity_recovery_tags() -> None:
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (180, 48))
    display.update_portfolio({
        "starting_bankroll": 20.0,
        "cash": 20.0,
        "open_value": 0.0,
        "equity": 20.0,
        "sizing_bankroll": 20.0,
        "bankroll_tier": "T0_MICRO_SEED",
        "bankroll_tier_id": "T0_MICRO_SEED",
        "bankroll_family": "MICRO",
        "bankroll_mode": "MICRO_SURVIVAL",
        "micro_survival_active": True,
        "micro_position_size": 0.05,
        "risk_mode": "NORMAL",
        "risk_off": False,
    })
    display.update_market(
        "BTC",
        bid=0.52,
        ask=0.54,
        yes_bid=0.52,
        yes_ask=0.54,
        no_bid=0.46,
        no_ask=0.48,
        current_price=100000.0,
        ref_price=99900.0,
        seconds_remaining=40,
        first_seen_seconds_remaining=599,
        first_evaluable_seconds_remaining=564,
        cutoff_policy="micro_adaptive",
        effective_cutoff_seconds=35,
        micro_timing_branch_entered=True,
        micro_timing_allowed=True,
        micro_timing_denied_reason="",
        liquidity_state="RECOVERING",
        empty_book_recovery_attempted=True,
        empty_book_recovery_success=True,
        empty_book_recovery_failed=False,
        empty_book_recovery_retry_count=1,
        decision="SKIP",
        skip_reason="",
    )

    card = _render_text(display._market_card("BTC", display._resolve_layout()))
    footer = str(display._footer())

    assert "remaining=40s" in card
    assert "599/564" in card
    assert "Cutoff micro_adaptive 35s" in card
    assert "Micro branch=ON allowed=ON" in card
    assert "Liquidity RECOVERING" in card
    assert "Recovery a=ON s=ON f=OFF r=1" in card
    assert "TIER T0_SEED" in footer
    assert "MICRO ON" in footer
    assert "LIQ RECOVERING" in footer
    assert "CUTOFF no_orderbook" not in footer
    assert "RECOVERY OK" in footer


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


# ──────────────────────────────────────────────────────────────────────────────
# Terminal UI V2 — lifecycle / preload / depth / research tests
# ──────────────────────────────────────────────────────────────────────────────

def test_market_card_v2_shows_lifecycle_phase_and_executable_state() -> None:
    """Market card must surface lifecycle_phase, executable_book_state, executable_spread_state."""
    # Use standard mode (2 cols) for wider per-panel width so long field values fit
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (120, 40))
    display.update_market(
        "BTC",
        lifecycle_phase="ACTIVE_INVENTORY_TRADING",
        active_window_alignment_reason="inside_window",
        executable_book_state="TRADABLE",
        executable_spread_state="NORMALIZED",
        liquidity_depth_state="STRONG",
        best_bid_size=59.79,
        best_ask_size=178.75,
        min_fillable_size_usd=450.0,
        readiness_confidence=0.8,
        seconds_remaining=120,
        decision="SKIP",
        skip_reason="decision_latency_high",
    )

    text = _render_text(display._market_card("BTC", display._resolve_layout()))

    assert "Phase" in text
    assert "ACTIVE_INVENTORY_TRADING" in text
    assert "ExecBook" in text
    assert "TRADABLE" in text
    assert "ExecSpread" in text
    assert "NORMALIZED" in text


def test_market_card_v2_shows_depth_state_and_sizes() -> None:
    """Market card must surface DepthState, BidSz, AskSz, Fill$ from liquidity probe fields."""
    # Use standard mode (2 cols) for wider per-panel width
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (120, 40))
    display.update_market(
        "BTC",
        liquidity_depth_state="THIN",
        best_bid_size=12.5,
        best_ask_size=8.0,
        min_fillable_size_usd=75.0,
        readiness_confidence=0.4,
        decision="SKIP",
    )

    text = _render_text(display._market_card("BTC", display._resolve_layout()))

    assert "DepthState" in text
    assert "THIN" in text
    assert "BidSz" in text
    assert "12.5" in text
    assert "AskSz" in text
    assert "8.0" in text
    assert "Fill$" in text
    assert "$75" in text


def test_market_card_v2_shows_readiness_confidence_and_blocker() -> None:
    """Readiness confidence and dominant blocker badge must appear in market card."""
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (150, 38))
    display.update_market(
        "ETH",
        readiness_confidence=0.6,
        executable_book_state="BOOK_SEEN",
        executable_spread_state="WIDE",
        liquidity_depth_state="THIN",
        seconds_remaining=80,
        effective_cutoff_seconds=35,
        decision="SKIP",
    )

    text = _render_text(display._market_card("ETH", display._resolve_layout()))

    assert "Readiness" in text
    assert "0.60" in text
    assert "Blocker" in text
    # Spread wide or liquidity thin should trigger a blocker label
    assert any(label in text for label in ("SPREAD_WIDE", "LIQUIDITY_THIN", "SPREAD_UNKNOWN", "EMPTY_BOOK", "TOKEN_READY"))


def test_market_card_v2_shows_timing_milestones() -> None:
    """TokRdy, NoZero, Tradable timing milestone fields must appear in the market card."""
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (150, 38))
    display.update_market(
        "BTC",
        token_ready_seconds_remaining=240,
        first_nonzero_bidask_seconds_remaining=180,
        first_tradable_seconds_remaining=120,
        decision="SKIP",
    )

    text = _render_text(display._market_card("BTC", display._resolve_layout()))

    assert "TokRdy" in text
    assert "240s" in text
    assert "NoZero" in text
    assert "180s" in text
    assert "Tradable" in text
    assert "120s" in text


def test_market_card_v2_shows_preload_state_in_wide_mode() -> None:
    """Preload success/warmed/seconds fields must appear in wide and fullscreen modes."""
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (180, 48))
    display.update_market(
        "BTC",
        preload_success=True,
        preload_orderbook_warmed=True,
        preload_seconds_before_epoch=45,
        preload_failure_reason="",
        decision="SKIP",
    )

    text = _render_text(display._market_card("BTC", display._resolve_layout()))

    assert "Preload" in text
    assert "OK" in text
    assert "Warmed" in text
    assert "ON" in text
    assert "45s" in text


def test_market_card_v2_shows_preload_failure_in_wide_mode() -> None:
    """Preload FAIL and failure reason must appear when preload_success=False."""
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (180, 48))
    display.update_market(
        "ETH",
        preload_success=False,
        preload_orderbook_warmed=False,
        preload_seconds_before_epoch=0,
        preload_failure_reason="timeout",
        decision="SKIP",
    )

    text = _render_text(display._market_card("ETH", display._resolve_layout()))

    assert "Preload" in text
    assert "FAIL" in text
    assert "timeout" in text


def test_market_card_v2_shows_research_fields_in_wide_mode() -> None:
    """Replay chain_id, lifecycle_instance_id, lineage, shadow_inventory must appear in wide mode."""
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (180, 48))
    display.update_market(
        "BTC",
        replay_chain_id="chain_abc123def456",
        lifecycle_instance_id="inst_xyz",
        lineage_confidence=0.91,
        shadow_inventory_decision="skip",
        decision="SKIP",
    )

    text = _render_text(display._market_card("BTC", display._resolve_layout()))

    assert "Chain" in text
    assert "Inst" in text
    assert "Lineage" in text
    assert "0.91" in text
    # Shadow and shadow value appear on the second research line
    assert "Shadow" in text
    assert "skip" in text


def test_market_card_v2_handles_all_missing_v2_fields_safely() -> None:
    """Market card must not crash when all V2 lifecycle/preload/depth fields are absent."""
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (150, 38))
    display.update_market(
        "BTC",
        bid=0.5,
        ask=0.52,
        spread=0.02,
        decision="SKIP",
    )

    # Must not raise; must produce some renderable output
    text = _render_text(display._market_card("BTC", display._resolve_layout()))
    assert "BTC" in text
    assert "Phase" in text
    assert "Blocker" in text


def test_market_card_v2_compact_mode_does_not_crash() -> None:
    """Compact mode market_table (not card) must render without crashing."""
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (82, 22))
    display.update_market(
        "BTC",
        lifecycle_phase="OPENING_SCAN",
        liquidity_depth_state="THIN",
        executable_book_state="BOOK_SEEN",
        decision="SKIP",
        skip_reason="empty_book",
    )

    spec = display._resolve_layout()
    assert spec.active_mode == "compact"
    # compact uses _market_table, not _market_card — must not raise
    text = _render_text(display._market_table(spec))
    assert "BTC" in text
    assert len(text) > 10


def test_market_card_v2_no_raw_json_overflow() -> None:
    """No raw JSON object repr or unbounded string must appear in market card output."""
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (150, 38))
    display.update_market(
        "ETH",
        lifecycle_phase="ACTIVE_INVENTORY_TRADING",
        replay_chain_id="chain_" + "x" * 80,
        lifecycle_instance_id="inst_" + "y" * 60,
        active_window_alignment_reason="inside_window",
        decision="SKIP",
    )

    text = _render_text(display._market_card("ETH", display._resolve_layout()))

    # No line in the card should exceed 220 chars (panel overflow indicator)
    for line in text.splitlines():
        assert len(line) <= 220, f"Line too long ({len(line)}): {line[:80]}..."
    # No raw dict or list repr
    assert "{" not in text
    assert "[" not in text or "BTC" not in text  # rich brackets in markup don't count


def test_system_panel_shows_run_id_when_set() -> None:
    """System panel must display run_id when update_run_id is called."""
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (150, 38))
    display.update_run_id("20260514T120000Z_12345_abc")

    text = _render_text(display._system_panel(display._resolve_layout()))
    assert "RUN_ID" in text
    assert "20260514T120000Z_12345_abc" in text


def test_dominant_blocker_label_returns_ready_for_tradable_market() -> None:
    """READY blocker must be returned when exec_book=TRADABLE, spread=NORMALIZED, depth=STRONG."""
    display = PolymarketRealtimeDisplay()
    m = {
        "executable_book_state": "TRADABLE",
        "executable_spread_state": "NORMALIZED",
        "liquidity_depth_state": "STRONG",
        "seconds_remaining": 120,
        "effective_cutoff_seconds": 35,
        "skip_reason": "",
    }
    assert display._dominant_blocker_label(m) == "READY"


def test_dominant_blocker_label_returns_cutoff_for_hard_close() -> None:
    """CUTOFF blocker must be returned when seconds_remaining <= effective_cutoff_seconds."""
    display = PolymarketRealtimeDisplay()
    m = {
        "executable_book_state": "TRADABLE",
        "executable_spread_state": "NORMALIZED",
        "liquidity_depth_state": "STRONG",
        "seconds_remaining": 20,
        "effective_cutoff_seconds": 35,
        "skip_reason": "hard_close_zone",
    }
    assert display._dominant_blocker_label(m) == "CUTOFF"


def test_dominant_blocker_label_returns_liquidity_thin_for_thin_depth() -> None:
    """LIQUIDITY_THIN must be returned when book is seen but depth is THIN."""
    display = PolymarketRealtimeDisplay()
    m = {
        "executable_book_state": "NONZERO_BOOK",
        "executable_spread_state": "NORMALIZED",
        "liquidity_depth_state": "THIN",
        "seconds_remaining": 120,
        "effective_cutoff_seconds": 35,
        "skip_reason": "liquidity_thin",
    }
    assert display._dominant_blocker_label(m) == "LIQUIDITY_THIN"


# ── Lifecycle Latency Observatory v1 display tests ────────────────────────────

def test_market_card_v2_shows_latency_line_when_values_present() -> None:
    """Latency compact line renders DISC→TOK and Latency badge when ms fields are non-zero."""
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (120, 40))
    display.update_market(
        "BTC",
        discovery_to_token_ready_ms=120,
        token_ready_to_book_ms=350,
        normalized_to_executable_ms=800,
        executable_to_decision_ms=600,
        lifecycle_latency_classification="NORMAL",
        dominant_latency_stage="ORDERBOOK",
    )
    import io
    from rich.console import Console as _C
    buf = io.StringIO()
    c = _C(file=buf, force_terminal=False, width=120, highlight=False)
    c.print(display._market_card("BTC", display._standalone_layout()))
    out = buf.getvalue()
    assert "DISC→TOK" in out, "DISC→TOK latency label must appear"
    assert "120ms" in out, "discovery_to_token_ready_ms=120 must render as 120ms"
    assert "NORMAL" in out, "lifecycle_latency_classification must appear"
    assert "ORDERBOOK" in out, "dominant_latency_stage must appear"


def test_market_card_v2_latency_line_absent_when_all_zero() -> None:
    """Latency compact line must NOT render when all ms fields are zero (avoids noise)."""
    display = PolymarketRealtimeDisplay(terminal_size_provider=lambda: (120, 40))
    display.update_market(
        "BTC",
        discovery_to_token_ready_ms=0,
        token_ready_to_book_ms=0,
        normalized_to_executable_ms=0,
        executable_to_decision_ms=0,
        lifecycle_latency_classification="",
        dominant_latency_stage="",
    )
    import io
    from rich.console import Console as _C
    buf = io.StringIO()
    c = _C(file=buf, force_terminal=False, width=120, highlight=False)
    c.print(display._market_card("BTC", display._standalone_layout()))
    out = buf.getvalue()
    assert "DISC→TOK" not in out, "Latency line must not appear when all ms values are zero"


def test_market_card_v2_latency_classification_critical_renders() -> None:
    """CRITICAL classification renders without crashing at any terminal width."""
    for width in (80, 120, 180):
        display = PolymarketRealtimeDisplay(terminal_size_provider=lambda w=width: (w, 40))
        display.update_market(
            "ETH",
            discovery_to_token_ready_ms=1200,
            token_ready_to_book_ms=8000,
            normalized_to_executable_ms=6000,
            executable_to_decision_ms=2000,
            lifecycle_latency_classification="CRITICAL",
            dominant_latency_stage="TOKEN_READY",
        )
        import io
        from rich.console import Console as _C
        buf = io.StringIO()
        c = _C(file=buf, force_terminal=False, width=width, highlight=False)
        c.print(display._market_card("ETH", display._standalone_layout()))
        out = buf.getvalue()
        assert "CRITICAL" in out, f"CRITICAL must render at width={width}"
